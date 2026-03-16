"""Dashboard view containing Content Sources, Search and Monitor tabs."""

import streamlit as st
from frontend.tabs.content_sources import render as render_content_sources
from frontend.tabs.search import render as render_search
from frontend.tabs.activity_monitor import render as render_monitor
from frontend.utils.services import init_basic_services, get_raw_services, init_full_services

def render_dashboard_view(safe_rerun, settings):
    tabs = st.tabs(["🗂️ Content Sources", "🔍 Search", "🚀 Activity Monitor"])

    services = init_basic_services()
    services["init_full_services"] = get_raw_services

    with tabs[0]:
        render_content_sources(services, safe_rerun)

    with tabs[1]:
        render_search(init_full_services)
        
    with tabs[2]:
        render_monitor(services, safe_rerun)
