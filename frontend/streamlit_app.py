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

# Process pending toasts from session state
if "pending_toast" in st.session_state:
    st.toast(st.session_state.pop("pending_toast"), icon="🚀")

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
main_view = st.session_state["main_view"]

# Common logic for history tracking (for st.toast)
from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
from src.infrastructure.services.ingestion_job_service import IngestionJobService
ingestion_service = IngestionJobService(IngestionJobSQLRepository())

if main_view == "dashboard":
    # Full width dashboard
    render_dashboard_view(safe_rerun, settings)
    
    # Run the history fragment invisibly to trigger toasts
    _show_history_fragment(ingestion_service, visible=False)

elif main_view == "chat":
    render_chat_view()
    # Also track history in chat to show toasts while chatting
    _show_history_fragment(ingestion_service, visible=False)

else:
    render_settings_view(settings)
    # Track history in settings too
    _show_history_fragment(ingestion_service, visible=False)
