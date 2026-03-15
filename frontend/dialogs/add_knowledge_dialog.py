"""Dialog to add knowledge sources."""

from urllib.parse import urlparse, parse_qs
import uuid
import streamlit as st
from frontend.utils.background_jobs import submit_job, get_job


def _extract_video_id_from_url(url: str) -> str | None:
    """Extract a YouTube video id from common URL formats."""
    if not url:
        return None
    import re
    m = re.search(
        r"(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([A-Za-z0-9_-]{11})",
        url,
    )
    if m:
        return m.group(1)
    try:
        parsed = urlparse(url)
        q = parse_qs(parsed.query)
        if "v" in q and q["v"]:
            return q["v"][0]
    except Exception:
        pass
    m2 = re.search(r"([A-Za-z0-9_-]{11})", url)
    if m2:
        return m2.group(1)
    return None


def _render_subject_selector(services):
    """Render and return the selected subject object (or None)."""
    ks_service = services.get("ks_service")
    subjects = []
    try:
        if ks_service:
            subjects = ks_service.list_subjects(limit=200)
    except Exception:
        subjects = []

    subject_names = [s.name for s in subjects] if subjects else []
    sidebar_selection = st.session_state.get("sidebar_selected_subject")
    default_index = 0
    if sidebar_selection in subject_names:
        default_index = subject_names.index(sidebar_selection)
    elif not subject_names:
        default_index = None

    selected_subject_name = st.selectbox(
        "Subject",
        options=subject_names,
        index=default_index,
        key="add_knowledge_subject_select",
    )
    return next((s for s in subjects if s.name == selected_subject_name), None) if selected_subject_name else None


def _job_status_poller(job_id: str, safe_rerun):
    """Show background job status. Auto-refresh is handled by the main app containers."""
    if not job_id:
        return

    job = get_job(job_id)
    if not job:
        st.warning("Job not found.")
        return

    status = job.get("status")
    if status == "running":
        st.info("🔄 Processing in background...")
        st.spinner("This may take a few minutes...")
        if st.button("Refresh Status", key="refresh_status_manual"):
            st.rerun()
    elif status == "done":
        st.success("✅ Ingestion completed successfully!")
        if st.button("Create New Knowledge", key="new_knowledge_success"):
            st.session_state.pop("current_ingestion_job_id", None)
            st.rerun()
    elif status == "error":
        st.error(f"❌ Ingestion error: {job.get('exception')}")
        if st.button("Back", key="close_dialog_error"):
            st.session_state.pop("current_ingestion_job_id", None)
            st.rerun()


def _youtube_tab_body(services, safe_rerun, selected_subject):
    """Render the YouTube ingestion tab body."""
    # Check if there's a job running for this session
    current_job_id = st.session_state.get("current_ingestion_job_id")
    if current_job_id:
        _job_status_poller(current_job_id, safe_rerun)
        return

    st.markdown("#### YouTube")
    st.write("Paste the link to the YouTube video or playlist you want to ingest.")
    
    st.text_input("YouTube URL", key="add_knowledge_youtube_url")
    data_col1, _ = st.columns(2)
    with data_col1:
        st.radio("Content Type", options=["Single Video", "Playlist"], horizontal=True, key="add_knowledge_youtube_type")
    
    # Dynamic limit from model loader
    model_loader = services.get("model_loader")
    max_tokens = getattr(model_loader, "max_seq_length", 512)
    
    # Ensure the slider allows at least 1024 if the model supports it or if we want to allow it as a common standard
    # BGE-M3 supports 8192, but we cap UI at 2048 for better UX
    display_max_tokens = max(max_tokens, 1024)
    
    with st.expander("🛠️ Splitting Configuration", expanded=False):
        st.slider("Tokens per chunk", min_value=128, max_value=display_max_tokens, value=min(512, display_max_tokens), step=64, key="add_knowledge_tokens")
        st.slider("Chunk overlap (tokens)", min_value=0, max_value=display_max_tokens // 4, value=min(50, display_max_tokens // 10), step=10, key="add_knowledge_overlap")

    if st.button("Add YouTube", key="add_knowledge_youtube_ingest"):
        url = st.session_state.get("add_knowledge_youtube_url", "").strip()
        is_playlist = st.session_state.get("add_knowledge_youtube_type") == "Playlist"
        tokens = st.session_state.get("add_knowledge_tokens", 512)
        overlap = st.session_state.get("add_knowledge_overlap", 50)
        
        if not url:
            st.error("YouTube URL is required")
        elif not selected_subject:
            st.error("Select a valid Subject")
        else:
            with st.spinner("Preparing ingestion..."):
                try:
                    from src.application.dtos.enums.youtube_data_type import YoutubeDataType
                    dtype = YoutubeDataType.PLAYLIST if is_playlist else YoutubeDataType.VIDEO
                    
                    # For single video, we still want to validate the ID early if possible
                    if not is_playlist:
                        video_id = _extract_video_id_from_url(url)
                        if not video_id:
                            st.error("Could not extract video ID from this URL.")
                            return
                    
                    cs_service = services.get("cs_service")
                    ingestion_service = services.get("ingestion_service")
                    
                    from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
                    from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
                    from src.domain.entities.enums.source_type_enum_entity import SourceType
                    from src.config.settings import settings
                    from frontend.utils.services import get_raw_services
                    from frontend.utils.ingestion_jobs import run_youtube_ingestion
                    
                    # 1. Check if already exists (only for single video)
                    if not is_playlist:
                        video_id = _extract_video_id_from_url(url)
                        existing = cs_service.get_by_source_info(source_type=SourceType.YOUTUBE, external_source=video_id)
                        if existing and existing.processing_status == "done":
                            st.info("This video has already been processed.")
                            return
                    
                    # 2. Source and Job Creation
                    source_id_for_job = None
                    job_id_for_backend = None

                    if not is_playlist:
                        video_id = _extract_video_id_from_url(url)
                        source_entity = cs_service.get_by_source_info(source_type=SourceType.YOUTUBE, external_source=video_id)
                        if not source_entity:
                            source_entity = cs_service.create_source(
                                subject_id=selected_subject.id,
                                source_type=SourceType.YOUTUBE,
                                external_source=video_id,
                                title=f"YouTube Video {video_id}",
                                status=ContentSourceStatus.ACTIVE,
                                processing_status="pending"
                            )
                        source_id_for_job = source_entity.id
                        
                        job_entity = ingestion_service.create_job(
                            content_source_id=source_id_for_job,
                            status=IngestionJobStatus.STARTED,
                            embedding_model=settings.model_embedding.name,
                            pipeline_version="1.0",
                            ingestion_type="youtube"
                        )
                        job_id_for_backend = str(job_entity.id)
                    
                    # Submit to background executor. For playlists, job_id_for_backend is None.
                    job_id = submit_job(run_youtube_ingestion, get_raw_services, url, str(selected_subject.id), job_id_for_backend, dtype, tokens, overlap)
                    st.session_state["current_ingestion_job_id"] = job_id
                    st.session_state["pending_toast"] = "YouTube ingestion started successfully!"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error starting: {e}")


def _upload_tab_body(selected_subject):
    st.markdown("#### Upload File")
    uploaded = st.file_uploader("Choose a file to upload", key="add_knowledge_file_uploader", type=["txt", "md", "pdf"])
    
    if uploaded is not None:
        st.info(f"File '{uploaded.name}' selected.")
        if st.button("Process File", key="add_knowledge_file_process"):
            if not selected_subject:
                st.error("Select a valid Subject")
                return
                
            # Basic implementation for Upload: Create ContentSource and Job (Simulation)
            st.warning("File upload processing will be implemented soon.")
            raise NotImplementedError("TODO: Implement FileExtractor and FileProcessService")


def _site_tab_body(selected_subject):
    st.markdown("#### Site / URL")
    site_url = st.text_input("Site URL", key="add_knowledge_site_url", placeholder="https://example.com/article")
    
    if st.button("Add Site", key="add_knowledge_site_add"):
        if not site_url or not str(site_url).strip():
            st.error("Site URL is required")
        elif not selected_subject:
            st.error("Select a valid Subject")
        else:
            st.info(f"Site received: {site_url}")
            st.warning("Web scraping will be implemented soon.")
            raise NotImplementedError("TODO: Implement WebExtractor and WebProcessService")


def _create_body(services, safe_rerun):
    """Top-level create body that delegates tab rendering to smaller helpers."""
    # Check if there's a job running for this session - if so, only show status poller
    current_job_id = st.session_state.get("current_ingestion_job_id")
    if current_job_id:
        _job_status_poller(current_job_id, safe_rerun)
        return

    selected_subject = _render_subject_selector(services)
    tabs = st.tabs(["YouTube", "Upload File", "Site"])

    with tabs[0]:
        _youtube_tab_body(services, safe_rerun, selected_subject)
    with tabs[1]:
        _upload_tab_body(selected_subject)
    with tabs[2]:
        _site_tab_body(selected_subject)


def open_add_knowledge(services, safe_rerun):
    """Open the add-knowledge dialog."""
    if hasattr(st, "dialog"):
        @st.dialog("Add Knowledge")
        def _dialog():
            _create_body(services, safe_rerun)
        return _dialog()
    else:
        with st.expander("Add Knowledge", expanded=True):
            _create_body(services, safe_rerun)
            return None
