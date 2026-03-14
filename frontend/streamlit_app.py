import sys
from pathlib import Path

import streamlit as st

# Ensure repository root is on sys.path so 'frontend' package imports work when running this file directly
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.config.settings import settings
from frontend.assets.styles import TABLE_CSS
from frontend.components.sidebar import render_sidebar
from frontend.views.dashboard import render_dashboard_view
from frontend.views.settings import render_settings_view
from frontend.utils.services import init_full_services

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

# --- Main Layout with Right Column for Notifications ---
main_col, right_col = st.columns([4, 1.2])

with main_col:
    if st.session_state["main_view"] == "dashboard":
        render_dashboard_view(safe_rerun, settings)
    else:
        render_settings_view(settings)

with right_col:
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
    from src.infrastructure.services.ingestion_job_service import IngestionJobService
    from frontend.components.task_cards import render_ingestion_history

    ingestion_service = IngestionJobService(IngestionJobSQLRepository())
    render_ingestion_history(ingestion_service)

