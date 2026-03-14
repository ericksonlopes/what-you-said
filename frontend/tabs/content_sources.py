"""Content Sources tab renderer."""

from uuid import UUID

import streamlit as st


def _render_header_and_button(services, safe_rerun):
    with st.container(horizontal=True):
        st.header("Content Sources")
        st.space("stretch")

        theme_type = st.context.theme.type
        if theme_type == "dark":
            btn_color = "white"
            btn_text_color = "black"
        else:
            btn_color = "black"
            btn_text_color = "white"

        st.html(f"""
            <style>
            div.st-key-add_knowledge_btn > div.stButton > button {{
                background-color: {btn_color};
                color: {btn_text_color};
                border: 1px solid gray;
            }}
            </style>
        """)

        if st.button("Add Knowledge", key="add_knowledge_btn"):
            try:
                from frontend.dialogs.add_knowledge_dialog import open_add_knowledge
                open_add_knowledge(services, safe_rerun)
            except Exception as e:
                st.error(f"Erro ao abrir diálogo de Add Knowledge: {e}")


def _fetch_content_sources(services):
    cs = services["cs_service"]
    ks = services["ks_service"]

    selected_subject_id = st.session_state.get("selected_subject_id")
    content_sources = []
    try:
        if selected_subject_id:
            try:
                sid = UUID(selected_subject_id)
            except Exception:
                sid = selected_subject_id
            content_sources = cs.list_by_subject(subject_id=sid)
        else:
            subjects = ks.list_subjects(limit=200)
            for s in subjects:
                try:
                    content_sources.extend(cs.list_by_subject(subject_id=s.id))
                except Exception:
                    continue
    except Exception as e:
        st.error(f"Error listing content sources: {e}")
        return []

    return content_sources


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
            status = getattr(c, 'processing_status', getattr(c, 'status', 'pending'))
            
            table_rows.append({
                "title": title,
                "external_source": ext_source,
                "type": ctype,
                "chunks": chunks,
                "embedding": embedding,
                "status": str(status).lower(),
            })
            source_ids.append(str(getattr(c, 'id', '')))
    return table_rows, source_ids


def _render_viewing(viewing,chunk_service, safe_rerun, table_rows):
    st.markdown(f"### Chunks for source: {viewing}")
    if st.button("Back to sources"):
        st.session_state['cs_viewing_source'] = None
        try:
            st.experimental_set_query_params()
        except Exception:
            pass
        safe_rerun()

    if str(viewing).startswith("mock-"):
        try:
            idx = int(viewing.split('-')[1])
        except Exception:
            idx = 0
        mock_chunks = [
            {"content": f"Mock chunk 1 for {table_rows[idx]['source']}",
             "extra": {"window_start": 0.0, "token_count": 120}},
            {"content": f"Mock chunk 2 for {table_rows[idx]['source']}",
             "extra": {"window_start": 12.5, "token_count": 90}},
        ]
        cols = st.columns(2)
        for i_ch, ch in enumerate(mock_chunks):
            col = cols[i_ch % 2]
            with col:
                st.markdown(f"**Chunk {i_ch + 1}**")
                st.write(ch['content'])
                st.caption(f"start: {ch['extra']['window_start']} • tokens: {ch['extra']['token_count']}")
                st.divider()
        return

    try:
        cs_uuid = UUID(str(viewing))
        chunks = chunk_service.list_by_content_source(content_source_id=cs_uuid)
        if not chunks:
            st.info("No chunks found for this content source.")
            return

        num_cols = 3
        cols = st.columns(num_cols)
        for idx, chunk in enumerate(chunks):
            col = cols[idx % num_cols]
            with col:
                st.markdown(f"**Chunk {idx + 1}**")
                content_preview = (chunk.content[:400] + "...") if chunk.content and len(chunk.content) > 400 else (
                        chunk.content or "")
                st.write(content_preview)
                extra = getattr(chunk, 'extra', {}) or {}
                meta_parts = []
                if 'window_start' in extra:
                    meta_parts.append(f"start: {extra.get('window_start')}")
                if 'token_count' in extra:
                    meta_parts.append(f"tokens: {extra.get('token_count')}")
                if meta_parts:
                    st.caption(" • ".join(meta_parts))
                st.caption(f"id: {getattr(chunk, 'id', '')}")
                st.divider()
    except Exception as e:
        st.error(f"Error loading chunks: {e}")


def _render_table(table_rows, source_ids, selected_subject_name):
    if selected_subject_name:
        st.caption(f"Showing sources for: **{selected_subject_name}**")
    else:
        st.caption("Showing all sources")

    if not table_rows:
        st.info("No content sources found for this subject.")
        return

    # Build the entire table as a single HTML string
    rows_html = ""
    for i, r in enumerate(table_rows):
        src_id = source_ids[i]
        link = f"?source={src_id}"
        status_class = f"badge-{r['status']}" if r['status'] in ['done', 'processing', 'pending', 'error'] else "badge-active"
        model_name = r['embedding'].split('/')[-1] if '/' in r['embedding'] else r['embedding']
        
        rows_html += f"""
            <tr>
                <td>
                    <div class="source-info">
                        <a href="{link}" class="source-title" target="_self">{r['title']}</a>
                        <span class="source-sub">{r['external_source']}</span>
                    </div>
                </td>
                <td><span class="meta-text">{r['type'].upper()}</span></td>
                <td><span class="meta-text">{r['chunks']}</span></td>
                <td><span class="meta-text" title="{r['embedding']}">{model_name}</span></td>
                <td><span class="badge {status_class}">{r['status']}</span></td>
                <td style="text-align: right;"><span class="action-dots">⋮</span></td>
            </tr>
        """

    table_html = f"""
    <table class="content-table">
        <thead>
            <tr>
                <th style="width: 40%;">Source</th>
                <th style="width: 10%;">Type</th>
                <th style="width: 10%;">Chunks</th>
                <th style="width: 20%;">Model</th>
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
    # Header + Add Knowledge button
    _render_header_and_button(services, safe_rerun)

    chunk_service = services["chunk_service"]

    # Apply query param override for viewing a source
    try:
        params = st.experimental_get_query_params()
        if 'source' in params and params.get('source'):
            qp = params.get('source')[0]
            if qp:
                st.session_state['cs_viewing_source'] = qp
    except Exception:
        pass

    content_sources = _fetch_content_sources(services)
    table_rows, source_ids = _build_rows(content_sources, settings)

    viewing = st.session_state.get('cs_viewing_source')

    if viewing:
        _render_viewing(viewing, chunk_service, safe_rerun, table_rows)
        return

    selected_subject_name = st.session_state.get("sidebar_selected_subject")
    _render_table(table_rows, source_ids, selected_subject_name)
