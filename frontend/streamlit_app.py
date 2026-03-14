import sys
import traceback
from pathlib import Path

import streamlit as st

# Ensure repository root is on sys.path so 'frontend' package imports work when running this file directly
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.config.settings import settings  # noqa: E402

st.set_page_config(page_title="WhatYouSaid UI", layout="wide")

# Styles for a modern dashboard look
TABLE_CSS = """<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    .main { font-family: 'Inter', sans-serif; }
    
    .content-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        background: transparent;
    }
    
    .content-table th {
        text-align: left;
        padding: 12px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        color: #9aa4ad;
        font-weight: 500;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .content-table td {
        padding: 16px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        vertical-align: middle;
    }
    
    .content-table tr:hover {
        background: rgba(255,255,255,0.02);
    }
    
    .source-info {
        display: flex;
        flex-direction: column;
    }
    
    .source-title {
        font-weight: 500;
        color: #e6eef7;
        font-size: 0.9rem;
        text-decoration: none !important;
        margin-bottom: 2px;
    }
    
    .source-sub {
        color: #6a737d;
        font-size: 0.75rem;
    }
    
    .meta-text {
        color: #9aa4ad;
        font-size: 0.8rem;
    }
    
    /* Modern Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        display: inline-block;
        text-transform: capitalize;
        white-space: nowrap;
    }
    .badge-done { background: rgba(16,185,129,0.1); color: #10b981; border: 1px solid rgba(16,185,129,0.2); }
    .badge-processing { background: rgba(59,130,246,0.1); color: #3b82f6; border: 1px solid rgba(59,130,246,0.2); }
    .badge-pending { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.2); }
    .badge-error { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.2); }
    .badge-active { background: rgba(139,92,246,0.1); color: #8b5cf6; border: 1px solid rgba(139,92,246,0.2); }
    
    .action-dots {
        color: #4b5563;
        font-size: 1.1rem;
        text-align: right;
    }
</style>"""
st.markdown(TABLE_CSS, unsafe_allow_html=True)


def safe_rerun():
    try:
        st.rerun()
    except Exception:
        # Fallback for older Streamlit versions
        st.session_state["_rerun_token"] = st.session_state.get("_rerun_token", 0) + 1
        try:
            st.stop()
        except Exception:
            pass


def init_basic_services():
    # Removed @st.cache_resource to ensure fresh connections during development if needed, 
    # but services are lightweight anyway.
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

# 1. Global Notification Logic (Runs on every app rerun)
try:
    from frontend.utils.background_jobs import list_jobs, mark_notified
    _jobs = list_jobs()
    for _jid, _meta in _jobs.items():
        _status = _meta.get("status")
        if not _meta.get("notified", False) and _status in ("done", "error"):
            if _status == "done":
                _res = _meta.get("result") or "Completed successfully"
                st.toast(f"Background job finished: {_res}", icon="✅")
            else:
                _exc = _meta.get("exception") or "Unknown error"
                st.toast(f"Background job failed: {_exc}", icon="❌")
            mark_notified(_jid)
except Exception:
    pass

# 2. Polling Fragment (Triggers rerun to keep UI updated)
@st.fragment(run_every=3)
def job_polling_fragment():
    """Polls background jobs and triggers a full app rerun while jobs are active or just finished."""
    try:
        from frontend.utils.background_jobs import list_jobs
        jobs = list_jobs()
        for jid, meta in jobs.items():
            status = meta.get("status")
            # Trigger rerun if job is running (to update table status)
            # OR if it just finished (to trigger the global toast notification)
            if status == "running" or (not meta.get("notified", False) and status in ("done", "error")):
                st.rerun()
                break
    except Exception:
        pass

# Initialize polling fragment
job_polling_fragment()

tabs = st.tabs(["Content Sources", "Search", "Diagnostics"])

# Sidebar subjects: always visible
services_for_sidebar = init_basic_services()
sidebar_ks = services_for_sidebar["ks_service"]
_side_subs = list_subjects(sidebar_ks)
if _side_subs:
    _options = [s.name for s in _side_subs]
    
    # Explicitly find the index for the selected subject to ensure robustness
    current_selected = st.session_state.get("sidebar_selected_subject")
    try:
        default_index = _options.index(current_selected) if current_selected in _options else 0
    except ValueError:
        default_index = 0

    selected_name = st.sidebar.selectbox(
        "Subjects", 
        options=_options, 
        index=default_index,
        key="sidebar_selected_subject"
    )
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
                            st.session_state["sidebar_selected_subject"] = created.name
                            safe_rerun()
                        except Exception as e:
                            st.error(f"Error creating subject: {e}")
            with c2:
                if st.button("Cancel", key="create_subject_cancel_inline"):
                    safe_rerun()

# Content Sources tab
from frontend.tabs.content_sources import render as render_content_sources  # noqa: E402
from frontend.tabs.search import render as render_search  # noqa: E402
from frontend.tabs.diagnostics import render as render_diagnostics  # noqa: E402

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
