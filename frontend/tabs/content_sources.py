"""Content Sources tab renderer."""

from uuid import UUID

import streamlit as st


def _render_header_and_button(services, safe_rerun):
    with st.container(horizontal=True):
        st.header("Content Sources")
        st.space("stretch")

        if st.button("Sync", key="sync_btn"):
            st.rerun()

        if st.button("Add Knowledge", key="add_knowledge_btn", type="primary"):
            try:
                from frontend.dialogs.add_knowledge_dialog import open_add_knowledge
                open_add_knowledge(services, safe_rerun)
            except Exception as e:
                st.error(f"Erro ao abrir diálogo de Add Knowledge: {e}")


def _fetch_content_sources(services):
    cs = services["cs_service"]
    selected_subject_id = st.session_state.get("selected_subject_id")
    
    if not selected_subject_id:
        return []

    try:
        try:
            sid = UUID(selected_subject_id)
        except Exception:
            sid = selected_subject_id
        return cs.list_by_subject(subject_id=sid)
    except Exception as e:
        st.error(f"Error listing content sources: {e}")
        return []


def _build_rows(content_sources, settings):
    table_rows = []
    source_ids = []
    if content_sources:
        for c in content_sources:
            # Main title from database, fallback to ID/Source
            title = getattr(c, 'title', None) or getattr(c, 'external_source', None) or str(getattr(c, 'id', ''))
            ext_source = getattr(c, 'external_source', None) or ""
            
            stype = getattr(c, 'source_type', None)
            if stype is not None:
                try:
                    ctype = stype.value if hasattr(stype, 'value') else str(stype)
                except Exception:
                    ctype = str(stype)
            else:
                ctype = getattr(c, 'mime_type', None) or "application/pdf"
                
            chunks = getattr(c, 'chunks', 0)
            embedding = getattr(c, 'embedding_model', "N/A")
            dims = getattr(c, 'dimensions', 0)
            status = getattr(c, 'processing_status', getattr(c, 'status', 'pending'))
            
            table_rows.append({
                "title": title,
                "external_source": ext_source,
                "type": ctype,
                "chunks": chunks,
                "embedding": embedding,
                "dims": dims,
                "status": str(status).lower(),
            })
            source_ids.append(str(getattr(c, 'id', '')))
    return table_rows, source_ids


def _render_table(table_rows, source_ids, selected_subject_name):
    if not selected_subject_name:
        st.info("Please select a Subject in the sidebar to view content sources.")
        return

    st.caption(f"Showing sources for: **{selected_subject_name}**")

    if not table_rows:
        st.info(f"No content sources found for '{selected_subject_name}'.")
        return

    # Build the entire table as a single HTML string
    rows_html = ""
    for i, r in enumerate(table_rows):
        src_id = source_ids[i]
        link = f"?source={src_id}"
        status_class = f"badge-{r['status']}" if r['status'] in ['done', 'processing', 'pending', 'error'] else "badge-active"
        # Shorten model name with safety check for None
        raw_embedding = r.get('embedding')
        if raw_embedding and isinstance(raw_embedding, str):
            model_name = raw_embedding.split('/')[-1] if '/' in raw_embedding else raw_embedding
        else:
            model_name = "N/A"

        table_html_row = f"""
            <tr>
                <td>
                    <div class="source-info">
                        <a href="{link}" class="source-title" target="_self">{r['title']}</a>
                        <span class="source-sub">{r['external_source']}</span>
                    </div>
                </td>
                <td><span class="meta-text">{r['type'].upper()}</span></td>
                <td><span class="meta-text">{r['chunks']}</span></td>
                <td><span class="meta-text" title="{raw_embedding or ''}">{model_name}</span></td>
                <td><span class="meta-text">{r['dims']}</span></td>
                <td><span class="badge {status_class}">{r['status']}</span></td>
                <td style="text-align: right;"><span class="action-dots">⋮</span></td>
            </tr>
        """
        rows_html += table_html_row

    table_html = f"""
    <table class="content-table">
        <thead>
            <tr>
                <th style="width: 35%;">Source</th>
                <th style="width: 10%;">Type</th>
                <th style="width: 8%;">Chunks</th>
                <th style="width: 17%;">Model</th>
                <th style="width: 10%;">Dims</th>
                <th style="width: 15%;">Status</th>
                <th style="width: 5%; text-align: right;"></th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    
    st.html(table_html)

    # Footer / Pagination
    st.markdown("<div style='margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;'></div>", unsafe_allow_html=True)
    st.caption(f"Total: {len(table_rows)} items")


def render(services, settings, safe_rerun):
    # Header + Add Knowledge button (Keep outside fragment to avoid widget issues)
    _render_header_and_button(services, safe_rerun)

    chunk_service = services["chunk_service"]

    # Detect if we should show the chunks dialog based on query params
    source_id_to_view = None
    try:
        # Use query_params instead of modern Streamlit
        params = st.query_params
        if 'source' in params:
            source_id_to_view = params['source']
    except Exception:
        pass

    @st.fragment(run_every="3s")
    def table_fragment():
        content_sources = _fetch_content_sources(services)
        table_rows, source_ids = _build_rows(content_sources, settings)

        # If a source is selected via URL, show the dialog
        if source_id_to_view:
            # Find the title for the selected source
            source_title = "Selected Source"
            for i, sid in enumerate(source_ids):
                if sid == source_id_to_view:
                    source_title = table_rows[i]['title']
                    break
            
            from frontend.dialogs.source_chunks_dialog import show_source_chunks_dialog
            
            # Clear the query param so the dialog doesn't keep popping up on every rerun
            st.query_params.clear()
            
            show_source_chunks_dialog(source_id_to_view, source_title, chunk_service)

        selected_subject_name = st.session_state.get("sidebar_selected_subject")
        _render_table(table_rows, source_ids, selected_subject_name)

    table_fragment()
