import sys
from pathlib import Path

# Ensure project root is on sys.path
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus

@st.fragment(run_every="2s")
def _render_monitor_fragment(services):
    ig_service = services.get("ingestion_service")
    cs_service = services.get("cs_service")

    if not ig_service:
        st.error("Ingestion service not found.")
        return

    # Use a container to avoid duplication issues during fast refreshes
    container = st.container()

    with container:
        # 1. Fetch Data
        all_jobs = ig_service.list_recent_jobs(limit=100)
        
        # Filter for last 24h
        now = datetime.now()
        last_24h = [j for j in all_jobs if (now - j.created_at.replace(tzinfo=None)) < timedelta(days=1)]
        
        success_count = len([j for j in last_24h if str(j.status.value if hasattr(j.status, "value") else j.status).lower() == "finished"])
        failed_count = len([j for j in last_24h if str(j.status.value if hasattr(j.status, "value") else j.status).lower() in ["failed", "error"]])
        active_jobs = [j for j in all_jobs if str(j.status.value if hasattr(j.status, "value") else j.status).lower() == "processing"]

        # 2. Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Active Tasks", len(active_jobs))
        m2.metric("Success (24h)", success_count)
        m3.metric("Failed (24h)", failed_count, delta_color="inverse")
        total_chunks = sum([j.chunks_count or 0 for j in last_24h])
        m4.metric("Chunks Created", total_chunks)

        st.markdown("---")

        # 3. Active Tasks
        if active_jobs:
            st.subheader("🔥 Live Processing")
            for job in active_jobs:
                title = "Unknown Source"
                if cs_service and job.content_source_id:
                    source = cs_service.get_by_id(job.content_source_id)
                    if source: title = source.title or source.external_source
                
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{title}**")
                        step_msg = job.status_message or "Processing..."
                        st.caption(f"Status: {step_msg}")
                        
                        if job.current_step and job.total_steps:
                            progress = job.current_step / job.total_steps
                            st.progress(progress, text=f"Step {job.current_step} of {job.total_steps}")
                        else:
                            st.progress(0.1)
                    with c2:
                        st.write("")
                        st.write("")
                        st.button("Logs", key=f"mon_log_{job.id}", disabled=True)
            st.markdown("---")

        # 4. History Table
        st.subheader("📋 Recent History")
        
        history_list = []
        for j in all_jobs[:20]:
            status_val = str(j.status.value if hasattr(j.status, "value") else j.status).lower()
            source_title = "N/A"
            if cs_service and j.content_source_id:
                try:
                    s = cs_service.get_by_id(j.content_source_id)
                    if s: source_title = s.title or s.external_source
                except: pass

            icon = "🟢" if status_val == "finished" else "🔴" if status_val in ["failed", "error"] else "🟡"
            
            duration = ""
            if j.finished_at and j.started_at:
                d = (j.finished_at - j.started_at).total_seconds()
                duration = f"{int(d)}s" if d < 60 else f"{int(d//60)}m {int(d%60)}s"

            history_list.append({
                "Time": j.created_at.strftime("%H:%M:%S"),
                "Status": f"{icon} {status_val.upper()}",
                "Source": source_title,
                "Type": (j.ingestion_type or "Generic").upper(),
                "Chunks": j.chunks_count or 0,
                "Duration": duration,
                "Message": j.status_message or j.error_message or ""
            })

        if history_list:
            df = pd.DataFrame(history_list)
            # Use st.dataframe instead of st.table for more reliable dynamic updates
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No history records found.")

def render(services, safe_rerun):
    st.header("🚀 Activity Monitor")
    st.write("Track your ingestion pipeline performance and active tasks in real-time.")
    
    # Always call the fragment
    _render_monitor_fragment(services)
