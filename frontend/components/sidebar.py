"""Sidebar component for navigation and subject management."""

import streamlit as st
from frontend.utils.services import init_basic_services, list_subjects
from frontend.components.task_cards import render_ingestion_history

def render_sidebar(safe_rerun):
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

        st.markdown("---")

        if st.button("⚙️ Settings", key="sidebar_settings_btn", use_container_width=True):
            st.session_state["main_view"] = "settings"
            st.rerun()
