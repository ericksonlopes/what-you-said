import sys
from pathlib import Path

import streamlit as st

# Ensure repository root is on sys.path so 'frontend' package imports work when running this file directly
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.config.settings import settings
from frontend.tabs.content_sources import render as render_content_sources  # noqa: E402
from frontend.tabs.search import render as render_search  # noqa: E402
from frontend.tabs.diagnostics import render as render_diagnostics  # noqa: E402
from frontend.utils.services import (  # noqa: E402
    init_basic_services, 
    get_raw_services, 
    init_full_services, 
    list_subjects
)


st.set_page_config(page_title="WhatYouSaid UI", layout="wide")

# Initialize session state for navigation
if "main_view" not in st.session_state:
    st.session_state["main_view"] = "dashboard"

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

    /* Chunk Cards */
    .chunk-card {
        background-color: #121212;
        border: 1px solid #27272a;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .chunk-header { 
        display: flex; 
        justify-content: space-between; 
        margin-bottom: 12px; 
        align-items: center;
    }
    .chunk-title { color: white; font-weight: bold; font-size: 14px; }
    .chunk-meta { 
        background: #18181b; 
        color: #71717a; 
        font-size: 10px; 
        padding: 2px 8px; 
        border-radius: 4px; 
        border: 1px solid #27272a; 
        margin-left: 8px;
    }
    .chunk-content { color: #a1a1aa; font-size: 14px; line-height: 1.6; }
</style>"""
st.markdown(TABLE_CSS, unsafe_allow_html=True)


def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass


@st.fragment(run_every="5s")
def _show_history_fragment(ig_service):
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
            
        jobs = ig_service.list_recent_jobs_by_subject(sid, limit=20)
        if not jobs:
            st.caption("No recent ingestion jobs.")
            return

        all_cards_html = ""
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

            all_cards_html += f"""
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
        
        # Wrap all cards in a scrollable div
        st.html(f"""
            <div style="max-height: 450px; overflow-y: auto; padding-right: 10px; margin-bottom: 10px;">
                {all_cards_html}
            </div>
        """)

    except Exception as e:
        st.error(f"Failed to load history: {e}")


def render_ingestion_history(ig_service):
    st.markdown("### 🔔 Tasks")
    st.caption("RECENT TASKS")
    _show_history_fragment(ig_service)


def render_settings_view():
    """Renders the settings and information view."""
    # Back button to return to dashboard
    if st.button("← Back to Content Sources"):
        st.session_state["main_view"] = "dashboard"
        st.rerun()
        
    st.title("⚙️ Settings & Diagnostics")
    st.markdown("---")
    
    tab_diag, tab_info = st.tabs(["🔍 Diagnostics", "ℹ️ System Info"])
    
    with tab_diag:
        render_diagnostics(init_full_services, settings)
        
    with tab_info:
        st.subheader("🛠️ Advanced Info")
        st.caption("Current running environment and configurations.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Environment", settings.app.env.upper())
            st.metric("Vector Store", settings.vector.store_type.upper())
        with col2:
            st.metric("Embedding Model", settings.model_embedding.name.split('/')[-1])
            st.metric("SQL Driver", settings.sql.url.split(':')[0])
            
        st.markdown("---")
        st.write("**Run command:**")
        st.code("streamlit run frontend/streamlit_app.py", language="bash")
        
        st.write("**Database URL:**")
        st.code(settings.sql.url)


# --- App Body ---
with st.spinner("Starting AI models and services..."):  # type: ignore
    startup_check = init_full_services()
    if not startup_check.get("ok"):
        st.error(f"Error loading models: {startup_check.get('error')}")
        st.stop()

# --- Sidebar (Left) ---
with st.sidebar:
    st.title("🎙️ WhatYouSaid")
    st.caption("Person-centric Knowledge Hub")
    st.markdown("---")

    st.subheader("📚 Subjects")
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

        selected_name = st.selectbox(
            "Current Context", 
            options=_options, 
            index=default_index,
            key="sidebar_selected_subject",
            label_visibility="collapsed"
        )
        selected_subject_obj = next((s for s in _side_subs if s.name == selected_name), None)
        if selected_subject_obj:
            st.session_state["selected_subject_id"] = str(selected_subject_obj.id)
    else:
        st.info("No subjects found. Create one to get started.")

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    from frontend.dialogs.subject_dialog import open_create_subject

    if st.button("➕ New Subject", key="open_create_subject_btn", use_container_width=True):
        if callable(open_create_subject):
            open_create_subject(sidebar_ks, safe_rerun)

    if st.button("⚙️ Settings", key="sidebar_settings_btn", use_container_width=True):
        st.session_state["main_view"] = "settings"
        st.rerun()

    st.markdown("---")
    # Ingestion history is always shown
    from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
    from src.infrastructure.services.ingestion_job_service import IngestionJobService
    ingestion_service = IngestionJobService(IngestionJobSQLRepository())
    render_ingestion_history(ingestion_service)


# --- Main Layout ---
if st.session_state["main_view"] == "dashboard":
    tabs = st.tabs(["Content Sources", "Search"])

    with tabs[0]:
        services = init_basic_services()
        services["init_full_services"] = get_raw_services
        render_content_sources(services, safe_rerun)

    with tabs[1]:
        render_search(init_full_services)
else:
    render_settings_view()
