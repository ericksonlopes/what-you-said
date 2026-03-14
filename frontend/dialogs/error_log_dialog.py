"""Dialog to display detailed error logs for failed jobs."""

import streamlit as st

def open_error_log(job_id, error_message):
    """Open a dialog showing the full error details."""
    @st.dialog(f"Error Log - Ingestion {str(job_id)[:8]}")
    def _dialog():
        st.error("An error occurred during this ingestion process.")
        
        st.markdown("### Error Details")
        st.code(error_message or "No detailed error message available.", language="text")
        
        st.markdown("### Troubleshooting Suggestions")
        if "transcript" in (error_message or "").lower():
            st.info("The video might not have available transcripts or they might be disabled.")
        elif "connection" in (error_message or "").lower():
            st.info("Check your internet connection or the status of the external service (YouTube/Weaviate).")
        
        if st.button("Close"):
            st.rerun()

    return _dialog()
