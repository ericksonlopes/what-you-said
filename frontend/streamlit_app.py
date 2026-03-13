import sys
import traceback
from pathlib import Path

import streamlit as st

# Ensure repository root is on sys.path so 'frontend' package imports work when running this file directly
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.config.settings import settings

st.set_page_config(page_title="WhatYouSaid UI", layout="wide")

# Styles for Source table (darkish)
TABLE_CSS = """<style>
.table { width:100%; border-collapse: collapse; }
.table th { text-align:left; padding:10px 8px; font-size:13px; color:#9aa4ad; border-bottom:1px solid rgba(255,255,255,0.04) }
.table td { padding:12px 8px; border-bottom:1px solid rgba(255,255,255,0.02); vertical-align:middle; color:#e6eef7 }
.badge { padding:4px 8px; border-radius:999px; font-size:12px; }
.badge.green { background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.18) }
.badge.gray { background: rgba(255,255,255,0.02); color: #9aa4ad }
.action-dots { color: #9aa4ad; font-size:20px; cursor:pointer }
.small { font-size:14px; color:#9aa4ad }
.btn-sync { background: transparent; border:1px solid rgba(255,255,255,0.06); color: #e6eef7; padding:6px 10px; border-radius:8px }
</style>"""
st.markdown(TABLE_CSS, unsafe_allow_html=True)


def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        # Fallback for Streamlit versions without experimental_rerun
        st.session_state["_rerun_token"] = st.session_state.get("_rerun_token", 0) + 1
        try:
            st.stop()
        except Exception:
            pass


@st.cache_resource
def init_basic_services():
    # Imports that are safe/lightweight are done lazily here
    from src.infrastructure.repositories.sql.knowledge_subject_repository import KnowledgeSubjectSQLRepository
    from src.infrastructure.services.knowledge_subject_service import KnowledgeSubjectService
    from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository
    from src.infrastructure.services.content_source_service import ContentSourceService
    from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
    from src.infrastructure.services.ingestion_job_service import IngestionJobService
    from src.infrastructure.repositories.sql.chunk_index_repository import ChunkIndexSQLRepository
    from src.infrastructure.services.chunk_index_service import ChunkIndexService

    ks_repo = KnowledgeSubjectSQLRepository()
    ks_service = KnowledgeSubjectService(ks_repo)

    cs_repo = ContentSourceSQLRepository()
    cs_service = ContentSourceService(cs_repo)

    ingestion_repo = IngestionJobSQLRepository()
    ingestion_service = IngestionJobService(ingestion_repo)

    chunk_repo = ChunkIndexSQLRepository()
    chunk_service = ChunkIndexService(chunk_repo)

    return {
        "ks_service": ks_service,
        "cs_service": cs_service,
        "ingestion_service": ingestion_service,
        "chunk_service": chunk_service,
    }


@st.cache_resource
def init_full_services():
    """Initialize model + vector services. Returns dict with services or error details."""
    basic = init_basic_services()
    try:
        # Import heavy modules lazily to avoid startup failures when not needed
        from src.infrastructure.services.model_loader_service import ModelLoaderService
        from src.infrastructure.services.embeddding_service import EmbeddingService
        from src.infrastructure.repositories.vector.weaviate.weaviate_client import WeaviateClient
        from src.infrastructure.repositories.vector.weaviate.chunk_repository import ChunkWeaviateRepository
        from src.infrastructure.services.youtube_vector_service import YouTubeVectorService

        model_loader = ModelLoaderService(settings.model_embedding.name)
        embedding_service = EmbeddingService(model_loader)

        weaviate_client = WeaviateClient(settings.vector)
        vector_repo = ChunkWeaviateRepository(weaviate_client=weaviate_client,
                                              embedding_service=embedding_service,
                                              collection_name=settings.vector.weaviate_collection_name_chunks,
                                              text_key="content")
        vector_service = YouTubeVectorService(repository=vector_repo)

        basic.update({
            "model_loader": model_loader,
            "embedding_service": embedding_service,
            "weaviate_client": weaviate_client,
            "vector_repo": vector_repo,
            "vector_service": vector_service,
        })
        return {"ok": True, "services": basic}

    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


def list_subjects(ks_service):
    try:
        subjects = ks_service.list_subjects(limit=200)
        return subjects
    except Exception as e:
        # Error while listing subjects
        st.error(f"Error listing subjects: {e}")
        return []


st.title("WhatYouSaid — Interface (Streamlit)")

tabs = st.tabs(["Content Sources", "Search", "Diagnostics"])

# Sidebar subjects: always visible
services_for_sidebar = init_basic_services()
sidebar_ks = services_for_sidebar["ks_service"]
_side_subs = list_subjects(sidebar_ks)
if _side_subs:
    _options = [s.name for s in _side_subs]
    selected_name = st.sidebar.selectbox("Subjects", options=_options, key="sidebar_selected_subject")
    selected_subject_obj = next((s for s in _side_subs if s.name == selected_name), None)
    if selected_subject_obj:
        st.session_state["selected_subject_id"] = str(selected_subject_obj.id)
    else:
        st.session_state.pop("selected_subject_id", None)
else:
    # No subjects found
    st.sidebar.info("No subjects found")

st.sidebar.markdown("---")

# Prefer to delegate dialog to frontend.dialogs.subject_dialog when present
try:
    from frontend.dialogs.subject_dialog import open_create_subject
except Exception:
    open_create_subject = None

# New Subject
if st.sidebar.button("New Subject", key="open_create_subject_btn"):
    if open_create_subject:
        open_create_subject(sidebar_ks, safe_rerun)
    else:
        # Final fallback: inline expander
        with st.expander("Create Subject", expanded=True):
            _new_name = st.text_input("New Subject - Name", key="create_subject_name_inline")
            _new_desc = st.text_area("Description", key="create_subject_desc_inline")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Create", key="create_subject_submit_inline"):
                    if not _new_name or not str(_new_name).strip():
                        st.error("Name is required")
                    else:
                        try:
                            created = sidebar_ks.create_subject(name=str(_new_name).strip(), description=_new_desc)
                            st.success(f"Created: {created.name}")
                            safe_rerun()
                        except Exception as e:
                            st.error(f"Error creating subject: {e}")
            with c2:
                if st.button("Cancel", key="create_subject_cancel_inline"):
                    safe_rerun()

# Content Sources tab
from frontend.tabs.content_sources import render as render_content_sources
from frontend.tabs.search import render as render_search
from frontend.tabs.diagnostics import render as render_diagnostics

with tabs[0]:
    services = init_basic_services()
    # expose init_full_services to child renderers/dialogs to avoid importing streamlit_app
    services["init_full_services"] = init_full_services
    render_content_sources(services, settings, safe_rerun)

# Search tab
with tabs[1]:
    render_search(init_full_services)

# Diagnostics tab
with tabs[2]:
    render_diagnostics(init_full_services, settings)

st.sidebar.markdown("\n---\nRun: `streamlit run frontend\\streamlit_app.py`")
