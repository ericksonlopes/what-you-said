"""Component for rendering ingestion task history."""

import streamlit as st

@st.fragment(run_every="5s")
def _show_history_fragment(ig_service):
    try:
        selected_sid = st.session_state.get("selected_subject_id")
        if not selected_sid:
            st.caption("Select a subject to see history.")
            return
        
        from uuid import UUID
        try:
            sid = UUID(selected_sid)
        except Exception:
            sid = selected_sid
            
        jobs = ig_service.list_recent_jobs_by_subject(sid, limit=4)
        if not jobs:
            st.caption("No recent ingestion jobs.")
            return

        all_cards_html = ""
        for job in jobs:
            # Extract clean status string
            status_obj = job.status
            status_val = status_obj.value if hasattr(status_obj, "value") else str(status_obj).lower()
            
            # Dynamic color and label mapping
            status_map = {
                "finished": {"color": "#10b981", "label": "Completed", "stats": "1 success, 0 failed"},
                "processing": {"color": "#3b82f6", "label": "Processing", "stats": "In progress..."},
                "started": {"color": "#f59e0b", "label": "Started", "stats": "Queued"},
                "failed": {"color": "#ef4444", "label": "Failed", "stats": "0 success, 1 failed"}
            }
            
            s_info = status_map.get(status_val, {"color": "#71717a", "label": status_val.capitalize(), "stats": ""})
            
            # Time formatting
            ts = job.created_at.strftime("%H:%M")
            
            # Duration calculation
            dur_str = ""
            if job.finished_at and job.started_at:
                dur = (job.finished_at - job.started_at).total_seconds()
                if dur < 60:
                    dur_str = f"{int(dur)}s"
                else:
                    dur_str = f"{int(dur // 60)}m {int(dur % 60)}s"
            
            stats_display = s_info["stats"]

            # Add each card to the combined HTML string
            all_cards_html += f"""
                <div class="task-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <b style="color: white; font-size: 0.9em;">Ingestion | {job.ingestion_type.capitalize() if job.ingestion_type else 'Generic'}</b>
                        <span style="color: {s_info['color']}; font-size: 0.8em; font-weight: 600;">{s_info['label']}</span>
                    </div>
                    <div style="font-size: 0.8em; color: #71717a; margin-top: 6px; line-height: 1.4;">
                        ID: <span style="font-family: monospace; font-size: 0.85em;">{str(job.id)[:8]}</span> <br>
                        {stats_display} • {ts} {f'({dur_str})' if dur_str else ''}
                    </div>
                </div>
            """
        
        # Render all cards at once to ensure consistent spacing controlled by CSS
        st.html(f'<div class="notifications-container">{all_cards_html}</div>')

    except Exception as e:
        st.error(f"Failed to load notifications: {e}")


def render_ingestion_history(ig_service):
    st.markdown("### 🔔 Notifications")
    st.caption("RECENT NOTIFICATIONS")
    _show_history_fragment(ig_service)
