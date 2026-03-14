import sys
import traceback
from pathlib import Path

import streamlit as st

# Ensure repository root is on sys.path so 'frontend' package imports work when running this file directly
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.config.settings import settings
from frontend.tabs.content_sources import render as render_content_sources
from frontend.tabs.search import render as render_search
from frontend.tabs.diagnostics import render as render_diagnostics

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
    
    /* Task Cards for Ingestion History */
    .task-card {
        background-color: #121212;
        border: 1px solid #27272a;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
</style>"""
st.markdown(TABLE_CSS, unsafe_allow_html=True)


def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass


def init_basic_services():
    from src.infrastructure.repositories.sql.knowledge_subject_repository import KnowledgeSubjectSQLRepository
    from src.infrastructure.services.knowledge_subject_service import KnowledgeSubjectService
    from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository
    from src.infrastructure.services.content_source_service import ContentSourceService
    from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
    from src.infrastructure.services.ingestion_job_service import IngestionJobService
    from src.infrastructure.repositories.sql.chunk_index_repository import ChunkIndexSQLRepository
    from src.infrastructure.services.chunk_index_service import ChunkIndexService

    return {
        "ks_service": KnowledgeSubjectService(KnowledgeSubjectSQLRepository()),
        "cs_service": ContentSourceService(ContentSourceSQLRepository()),
        "ingestion_service": IngestionJobService(IngestionJobSQLRepository()),
        "chunk_service": ChunkIndexService(ChunkIndexSQLRepository()),
    }


def get_raw_services():
    basic = init_basic_services()
    try:
        from src.infrastructure.services.model_loader_service import ModelLoaderService
        from src.infrastructure.services.embeddding_service import EmbeddingService
        from src.infrastructure.repositories.vector.weaviate.weaviate_client import WeaviateClient
        from src.infrastructure.repositories.vector.weaviate.chunk_repository import ChunkWeaviateRepository
        from src.infrastructure.services.youtube_vector_service import YouTubeVectorService

        model_loader = ModelLoaderService(settings.model_embedding.name)
        embedding_service = EmbeddingService(model_loader)
        weaviate_client = WeaviateClient(settings.vector)
        vector_repo = ChunkWeaviateRepository(weaviate_client=weaviate_client, embedding_service=embedding_service,
                                              collection_name=settings.vector.weaviate_collection_name_chunks,
                                              text_key="content")
        vector_service = YouTubeVectorService(repository=vector_repo)

        basic.update({
            "model_loader": model_loader,
            "embedding_service": embedding_service,
            "vector_service": vector_service,
        })
        return {"ok": True, "services": basic}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


@st.cache_resource
def init_full_services():
    return get_raw_services()


def list_subjects(ks_service):
    try:
        return ks_service.list_subjects(limit=200)
    except Exception as e:
        st.error(f"Error listing subjects: {e}")
        return []


def log_toast(message, icon="ℹ️"):
    if "toast_logs" not in st.session_state:
        st.session_state["toast_logs"] = []
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state["toast_logs"].insert(0, {"msg": message, "icon": icon, "time": timestamp})
    st.session_state["toast_logs"] = st.session_state["toast_logs"][:20]


def render_ingestion_history(ingestion_service):
    st.markdown("### 🔔 Tasks")
    st.caption("RECENT TASKS")

    # If something triggered a need for a refresh (like adding a source), 
    # the fragment will rerun on its own cycle, but we can also force it here
    # if we are outside the fragment or by just letting it run.

    @st.fragment(run_every="3s")
    def show_history():
        try:
            selected_sid = st.session_state.get("selected_subject_id")
            if not selected_sid:
                st.caption("Select a subject to see history.")
                return
            
            from uuid import UUID
            try:
                sid = UUID(selected_sid)
            except Exception:
                sid = selected_sid
                
            jobs = ingestion_service.list_recent_jobs_by_subject(sid, limit=20)
            if not jobs:
                st.caption("No recent ingestion jobs.")
                return

            for job in jobs:
                # Extract clean status string
                status_obj = job.status
                status_val = status_obj.value if hasattr(status_obj, "value") else str(status_obj).lower()
                
                # Dynamic color and label mapping
                status_map = {
                    "finished": {"color": "#10b981", "label": "Completed", "stats": "1 success, 0 failed"},
                    "processing": {"color": "#3b82f6", "label": "Processing", "stats": "In progress..."},
                    "started": {"color": "#f59e0b", "label": "Started", "stats": "Queued"},
                    "failed": {"color": "#ef4444", "label": "Failed", "stats": "0 success, 1 failed"}
                }
                
                s_info = status_map.get(status_val, {"color": "#71717a", "label": status_val.capitalize(), "stats": ""})
                
                # Time formatting
                ts = job.created_at.strftime("%H:%M")
                
                # Duration calculation
                dur_str = ""
                if job.finished_at and job.started_at:
                    dur = (job.finished_at - job.started_at).total_seconds()
                    if dur < 60:
                        dur_str = f"{int(dur)}s"
                    else:
                        dur_str = f"{int(dur // 60)}m {int(dur % 60)}s"
                
                stats_display = s_info["stats"]
                if status_val == "failed" and job.error_message:
                    stats_display = f"Error: {job.error_message[:30]}..."

                card_html = f"""
                    <div class="task-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <b style="color: white; font-size: 0.9em;">Task {job.id.hex[:8]}</b>
                            <span style="color: {s_info['color']}; font-size: 0.8em; font-weight: 500;">{s_info['label']}</span>
                        </div>
                        <div style="font-size: 0.8em; color: #71717a; margin-top: 6px; line-height: 1.4;">
                            {ts} {f'• {dur_str}' if dur_str else ''} <br>
                            {stats_display}
                        </div>
                    </div>
                """
                st.html(card_html)
        except Exception as e:
            st.error(f"Failed to load history: {e}")
        except Exception as e:
            st.error(f"Failed to load history: {e}")

    show_history()


# --- App Body ---
st.title("WhatYouSaid — Interface (Streamlit)")

with st.spinner("Iniciando modelos de IA e serviços..."):
    startup_check = init_full_services()
    if not startup_check.get("ok"):
        st.error(f"Erro ao carregar modelos: {startup_check.get('error')}")
        st.stop()

# --- Sidebar (Left) - MOVED TO TOP OF LAYOUT LOGIC ---
st.sidebar.header("Navigation")
with st.sidebar.expander("Subjects", expanded=True):
    services_for_sidebar = init_basic_services()
    sidebar_ks = services_for_sidebar["ks_service"]
    _side_subs = list_subjects(sidebar_ks)
    if _side_subs:
        _options = [s.name for s in _side_subs]
        current_selected = st.session_state.get("sidebar_selected_subject")
        try:
            default_index = _options.index(current_selected) if current_selected in _options else 0
        except ValueError:
            default_index = 0

        selected_name = st.selectbox("Select Subject", options=_options, index=default_index,
                                     key="sidebar_selected_subject")
        selected_subject_obj = next((s for s in _side_subs if s.name == selected_name), None)
        if selected_subject_obj:
            st.session_state["selected_subject_id"] = str(selected_subject_obj.id)
    else:
        st.info("No subjects found")

st.sidebar.markdown("---")

try:
    from frontend.dialogs.subject_dialog import open_create_subject
except Exception:
    open_create_subject = None

if st.sidebar.button("New Subject", key="open_create_subject_btn"):
    if open_create_subject:
        open_create_subject(sidebar_ks, safe_rerun)

st.sidebar.markdown("Run: `streamlit run frontend/streamlit_app.py`")

# --- Main Layout ---
main_col, history_col = st.columns([3, 1])

with main_col:
    tabs = st.tabs(["Content Sources", "Search", "Diagnostics"])

    with tabs[0]:
        services = init_basic_services()
        services["init_full_services"] = get_raw_services
        render_content_sources(services, settings, safe_rerun)

    with tabs[1]:
        render_search(init_full_services)

    with tabs[2]:
        render_diagnostics(init_full_services, settings)

with history_col:
    # Using fresh instances in this column to ensure all new service methods are available
    from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
    from src.infrastructure.services.ingestion_job_service import IngestionJobService
    ingestion_service = IngestionJobService(IngestionJobSQLRepository())
    render_ingestion_history(ingestion_service)
