"""Component for tracking ingestion task history and showing notifications via st.toast."""

import streamlit as st
from frontend.utils.services import init_basic_services

@st.fragment(run_every="2s")
def _show_history_fragment(ig_service, visible=True):
    """
    Tracks ingestion jobs and shows notifications.
    If visible=True, renders the Notification UI with progress bars.
    """
    if visible:
        st.markdown("### 🔔 Monitor")
        st.caption("ACTIVE & RECENT TASKS")
    
    try:
        # Fetch global recent jobs to show overall system activity
        jobs = ig_service.list_recent_jobs(limit=5)
        if not jobs:
            if visible:
                st.caption("No recent ingestion jobs.")
            return

        # --- Initialization of tracking state for toasts ---
        if "notification_state_global" not in st.session_state:
            st.session_state["notification_state_global"] = {}

        # Fetch CS service to get source titles
        services = init_basic_services()
        cs_service = services.get("cs_service")

        active_count = 0
        all_cards_html = ""
        
        for job in jobs:
            job_id_str = str(job.id)
            status_obj = job.status
            status_val = status_obj.value if hasattr(status_obj, "value") else str(status_obj).lower()
            
            # --- Toast Notification Logic ---
            last_status = st.session_state["notification_state_global"].get(job_id_str)
            if last_status and last_status != status_val:
                source_title = "Unknown"
                if cs_service and job.content_source_id:
                    try:
                        source = cs_service.get_by_id(job.content_source_id)
                        if source:
                            source_title = source.title or source.external_source
                    except Exception: pass

                item_info = f"[{job.ingestion_type.capitalize() if job.ingestion_type else 'Job'}] {source_title}"
                if status_val == "finished": st.toast(f"✅ **Finished**: {item_info}", icon="🎉")
                elif status_val == "failed": st.toast(f"❌ **Failed**: {item_info}", icon="🚨")
            
            st.session_state["notification_state_global"][job_id_str] = status_val

            # --- UI Card Rendering ---
            if visible:
                is_processing = status_val == "processing"
                if is_processing: active_count += 1
                
                status_map = {
                    "finished": {"color": "#10b981", "label": "Completed", "icon": "✅"},
                    "processing": {"color": "#3b82f6", "label": "Processing", "icon": "⚙️"},
                    "started": {"color": "#f59e0b", "label": "Started", "icon": "🆕"},
                    "failed": {"color": "#ef4444", "label": "Failed", "icon": "❌"}
                }
                s_info = status_map.get(status_val, {"color": "#71717a", "label": status_val.capitalize(), "icon": "•"})
                
                title = "Ingestion Task"
                if cs_service and job.content_source_id:
                    try:
                        source = cs_service.get_by_id(job.content_source_id)
                        if source: title = source.title or source.external_source
                    except Exception: pass

                # Progress Bar Calculation
                progress_html = ""
                step_msg = job.status_message or s_info['label']
                if is_processing and job.current_step and job.total_steps:
                    pct = int((job.current_step / job.total_steps) * 100)
                    progress_html = f"""
                        <div style="width: 100%; background-color: #3f3f46; border-radius: 10px; height: 4px; margin: 8px 0;">
                            <div style="width: {pct}%; background-color: #3b82f6; height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out;"></div>
                        </div>
                        <div style="font-size: 0.65em; color: #3b82f6; font-weight: 500;">Step {job.current_step}/{job.total_steps}: {step_msg}</div>
                    """
                elif status_val == "failed":
                    progress_html = f'<div style="font-size: 0.65em; color: #ef4444; margin-top: 4px;">Error: {job.error_message[:50] if job.error_message else "Unknown error"}...</div>'
                else:
                    progress_html = f'<div style="font-size: 0.65em; color: #71717a; margin-top: 4px;">{step_msg}</div>'

                all_cards_html += f"""
                    <div class="task-card" style="border-left: 3px solid {s_info['color']}; background: rgba(255,255,255,0.03); padding: 10px; border-radius: 4px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: start; gap: 10px;">
                            <div style="font-size: 0.85em; font-weight: 600; color: white; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;">{title}</div>
                            <span style="font-size: 0.7em; color: {s_info['color']}; white-space: nowrap;">{s_info['icon']} {s_info['label']}</span>
                        </div>
                        {progress_html}
                        <div style="font-size: 0.65em; color: #52525b; margin-top: 4px; display: flex; justify-content: space-between;">
                            <span>{job.ingestion_type.upper() if job.ingestion_type else 'GENERIC'}</span>
                            <span>{job.created_at.strftime("%H:%M")}</span>
                        </div>
                    </div>
                """
        
        if visible:
            if active_count > 0:
                st.info(f"🚀 {active_count} tasks in progress")
            st.markdown(all_cards_html, unsafe_allow_html=True)

    except Exception as e:
        if visible: st.error(f"Failed to load monitor: {e}")

def render_ingestion_history(ig_service):
    _show_history_fragment(ig_service, visible=True)
