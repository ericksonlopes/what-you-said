import sys
from pathlib import Path

import streamlit as st

# Ensure repository root is on sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.config.settings import settings
from frontend.assets.styles import TABLE_CSS
from frontend.components.sidebar import render_sidebar
from frontend.views.dashboard import render_dashboard_view
from frontend.views.settings import render_settings_view
from frontend.views.chat import render_chat_view
from frontend.utils.services import init_full_services
from frontend.components.task_cards import _show_history_fragment

# Page Configuration
st.set_page_config(page_title="WhatYouSaid UI", layout="wide")

# Inject Global Styles
st.markdown(TABLE_CSS, unsafe_allow_html=True)

# Initialize session state for navigation
if "main_view" not in st.session_state:
    st.session_state["main_view"] = "dashboard"


def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass


# --- App Startup ---
with st.spinner("Starting AI models and services..."):  # type: ignore
    startup_check = init_full_services()
    if not startup_check.get("ok"):
        st.error(f"Error loading models: {startup_check.get('error')}")
        st.stop()

# --- Sidebar ---
render_sidebar(safe_rerun)

# --- Main Layout Orchestration ---
# We use a single layout logic to keep fragment definitions stable
main_view = st.session_state["main_view"]

if main_view == "dashboard":
    # Dashboard uses the 2-column layout with Notifications
    main_col, right_col = st.columns([4, 1.2])
    
    with main_col:
        render_dashboard_view(safe_rerun)
        
    with right_col:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
        from src.infrastructure.services.ingestion_job_service import IngestionJobService
        ingestion_service = IngestionJobService(IngestionJobSQLRepository())
        # Always call the history fragment when in Dashboard
        _show_history_fragment(ingestion_service)

elif main_view == "chat":
    render_chat_view()
    # Hidden history fragment to maintain its ID/Timer state if needed,
    # but since it's not rendered here, we usually just let it go.
    # To TRULY stop the warning, we'd need to call it everywhere,
    # but let's first fix the most common transition.

else:
    render_settings_view(settings)
