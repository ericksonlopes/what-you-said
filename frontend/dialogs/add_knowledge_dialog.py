"""Dialog to add knowledge sources.

Provides open_add_knowledge(services, settings, safe_rerun) which shows a dialog/modal/expander
with tabs for different insertion types. Currently implements YouTube tab; Upload File and Site
are present as placeholder tabs.
"""

from urllib.parse import urlparse, parse_qs

import streamlit as st
import json
from streamlit.components.v1 import html as components_html
from frontend.utils.background_jobs import submit_job, ensure_status_server_running, mark_notified


def _extract_video_id_from_url(url: str) -> str | None:
    """Extract a YouTube video id from common URL formats.

    Uses a consolidated regex for common YouTube URL patterns first, then
    falls back to checking the query param 'v', and finally searches for an
    11-character id anywhere in the URL.
    """
    if not url:
        return None
    import re

    # Match many common YouTube URL patterns (short and long forms)
    m = re.search(
        r"(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([A-Za-z0-9_-]{11})",
        url,
    )
    if m:
        return m.group(1)

    # Fallback: try query parameter 'v'
    try:
        parsed = urlparse(url)
        q = parse_qs(parsed.query)
        if "v" in q and q["v"]:
            return q["v"][0]
    except Exception:
        pass

    # Final fallback: any 11-char candidate in the url
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
    selected_subject_name = st.selectbox(
        "Subject",
        options=subject_names,
        index=0 if subject_names else None,
        key="add_knowledge_subject_select",
    )
    selected_subject = (
        next((s for s in subjects if s.name == selected_subject_name), None)
        if selected_subject_name
        else None
    )
    return selected_subject


def _youtube_tab_body(services, safe_rerun, selected_subject):
    """Render the YouTube ingestion tab body and trigger ingestion when requested."""
    st.markdown("#### YouTube")
    st.write("Cole o link do vídeo do YouTube que deseja ingerir.")
    
    yt_url = st.text_input("YouTube URL", key="add_knowledge_youtube_url")
    st.caption("Atualmente apenas vídeos avulsos são suportados (playlist não implementado).")

    # Use a normal button instead of on_click callback to avoid st.rerun() issues
    if st.button("Adicionar YouTube", key="add_knowledge_youtube_ingest"):
        url = st.session_state.get("add_knowledge_youtube_url", "").strip()
        if not url:
            st.error("URL do YouTube é obrigatória")
        elif not selected_subject:
            st.error("Selecione um Subject válido")
        else:
            from frontend.streamlit_app import get_raw_services
            try:
                video_id = _extract_video_id_from_url(url)
                if not video_id:
                    st.error("Não foi possível extrair o ID do vídeo desta URL.")
                    return

                # Create services for foreground operations
                cs_service = services.get("cs_service")
                ingestion_service = services.get("ingestion_service")
                
                from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
                from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
                from src.domain.entities.enums.source_type_enum_entity import SourceType
                from src.config.settings import settings
                
                # 1. Check if already exists to avoid duplicates in UI
                existing = cs_service.get_by_source_info(source_type=SourceType.YOUTUBE, external_source=video_id)
                if existing and existing.processing_status == "done":
                    st.info("Este vídeo já foi processado anteriormente.")
                    return
                
                # 2. Create ContentSource in PENDING status
                source_entity = existing
                if not source_entity:
                    source_entity = cs_service.create_source(
                        subject_id=selected_subject.id,
                        source_type=SourceType.YOUTUBE,
                        external_source=video_id,
                        title=f"YouTube Video {video_id}", # Fallback title until ingestion extracts real one
                        status=ContentSourceStatus.ACTIVE,
                        processing_status="pending"
                    )
                
                # 3. Create IngestionJob linked to the source
                job_entity = ingestion_service.create_job(
                    content_source_id=source_entity.id,
                    status=IngestionJobStatus.STARTED,
                    embedding_model=settings.model_embedding.name,
                    pipeline_version="1.0"
                )
                job_id = job_entity.id

                # Helper for background ingest (logic only)
                def _background_run_ingest(get_services_func, video_url, subject_id, pre_job_id):
                    fs = get_services_func()
                    if not fs or not fs.get('ok'):
                        raise RuntimeError(f"Failed to initialize services")
                    svc = fs['services']
                    from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
                    from src.application.dtos.enums.youtube_data_type import YoutubeDataType
                    from src.application.use_cases.ingest_youtube_use_case import IngestYoutubeUseCase

                    use_case = IngestYoutubeUseCase(
                        ks_service=svc.get("ks_service"),
                        cs_service=svc.get("cs_service"),
                        ingestion_service=svc.get("ingestion_service"),
                        model_loader_service=svc.get("model_loader"),
                        embedding_service=svc.get("embedding_service"),
                        chunk_service=svc.get("chunk_service"),
                        vector_service=svc.get("vector_service"),
                    )
                    cmd = IngestYoutubeCommand(
                        video_url=video_url, 
                        subject_id=subject_id, 
                        data_type=YoutubeDataType.VIDEO,
                        ingestion_job_id=str(pre_job_id)
                    )
                    use_case.execute(cmd)

                submit_job(_background_run_ingest, get_raw_services, url, str(selected_subject.id), job_id)
                
                st.session_state["ingest_success_job"] = job_id
                
                # Now we can safely rerun the app to refresh everything.
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao iniciar: {e}")

    # Render success message if just happened
    if "ingest_success_job" in st.session_state:
        jid = st.session_state.pop("ingest_success_job")
        st.toast(f"Iniciando ingestão... (Job: {jid})", icon="🚀")



def _upload_tab_body():
    st.markdown("#### Upload File")
    uploaded = st.file_uploader("Escolha um arquivo para upload", key="add_knowledge_file_uploader")
    if uploaded is not None:
        st.info("Upload recebido — processamento ainda não implementado.")
    if st.button("Adicionar arquivo (não implementado)", key="add_knowledge_file_add"):
        st.info("Inserção via upload de arquivo não está implementada ainda.")


def _site_tab_body():
    st.markdown("#### Site / URL")
    site_url = st.text_input("Site URL", key="add_knowledge_site_url")
    st.caption("Inserção via site ainda não implementada — apenas espaço reservado.")
    if st.button("Adicionar site (não implementado)", key="add_knowledge_site_add"):
        if not site_url or not str(site_url).strip():
            st.error("Site URL é obrigatória")
        else:
            st.info(f"Site received: {site_url} — processing not implemented yet.")


def _create_body(services, safe_rerun):
    """Top-level create body that delegates tab rendering to smaller helpers."""
    selected_subject = _render_subject_selector(services)

    tabs = st.tabs(["YouTube", "Upload File", "Site"])

    with tabs[0]:
        _youtube_tab_body(services, safe_rerun, selected_subject)
    with tabs[1]:
        _upload_tab_body()
    with tabs[2]:
        _site_tab_body()


def open_add_knowledge(services, safe_rerun):
    """Open the add-knowledge dialog/modal/expander.

    Uses st.dialog when available, otherwise falls back to st.modal or st.expander.
    """
    if hasattr(st, "dialog"):
        @st.dialog("Add Knowledge")
        def _dialog():
            _create_body(services, safe_rerun)

        return _dialog()

    try:
        if hasattr(st, "modal"):
            with st.modal("Add Knowledge"):
                _create_body(services, safe_rerun)
        else:
            with st.expander("Add Knowledge", expanded=True):
                _create_body(services, safe_rerun)
    except Exception:
        with st.expander("Add Knowledge", expanded=True):
            _create_body(services, safe_rerun)
