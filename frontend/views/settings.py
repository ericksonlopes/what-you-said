"""Settings view containing Diagnostics and System Info tabs."""

import streamlit as st
from frontend.tabs.diagnostics import render as render_diagnostics
from frontend.utils.services import init_full_services

def render_settings_view(settings):
    """Renders the settings and information view."""
    # Back button to return to content sources
    if st.button("← Back to Content Sources"):
        st.session_state["main_view"] = "dashboard"
        st.rerun()
        
    st.title("⚙️ Settings & Diagnostics")
    st.markdown("---")
    
    # Wrap main settings area in scrollable container
    with st.container(height=700, border=False):
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
