"""Dashboard view containing Content Sources and Search tabs."""

import streamlit as st
from frontend.tabs.content_sources import render as render_content_sources
from frontend.tabs.search import render as render_search
from frontend.utils.services import init_basic_services, get_raw_services, init_full_services

def render_dashboard_view(safe_rerun):
    tabs = st.tabs(["Content Sources", "Search"])

    with tabs[0]:
        services = init_basic_services()
        services["init_full_services"] = get_raw_services
        render_content_sources(services, safe_rerun)

    with tabs[1]:
        render_search(init_full_services)
