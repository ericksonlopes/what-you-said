"""Content Sources tab renderer."""

from uuid import UUID

import streamlit as st


def render(services, settings, safe_rerun):
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
                open_add_knowledge(services, settings, safe_rerun)
            except Exception as e:
                st.error(f"Erro ao abrir diálogo de Add Knowledge: {e}")

    """Render the Content Sources tab using provided services."""
    cs = services["cs_service"]
    chunk_service = services["chunk_service"]
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
        return

    # Build table rows
    table_rows = []
    if content_sources:
        for c in content_sources:
            source = getattr(c, 'title', None) or getattr(c, 'external_source', None) or str(getattr(c, 'id', ''))
            stype = getattr(c, 'source_type', None)
            if stype is not None:
                try:
                    ctype = stype.value
                except Exception:
                    ctype = str(stype)
            else:
                ctype = getattr(c, 'mime_type', None) or "application/pdf"
            chunks = getattr(c, 'chunks', 0)
            embedding = getattr(c, 'embedding_model', settings.model_embedding.name or "text-embedding-3-small")
            dims = getattr(c, 'dimensions', 1536)
            status = getattr(c, 'processing_status', getattr(c, 'status', 'Active'))
            table_rows.append({"source": source, "type": ctype, "chunks": chunks, "embedding": embedding, "dims": dims,
                               "status": status})

    def _set_viewing_source(src_id: str):
        st.session_state['cs_viewing_source'] = str(src_id)
        safe_rerun()

    source_ids = [str(getattr(c, 'id', '')) for c in content_sources] if content_sources else []

    try:
        params = st.experimental_get_query_params()
        if 'source' in params and params.get('source'):
            qp = params.get('source')[0]
            if qp:
                st.session_state['cs_viewing_source'] = qp
    except Exception:
        pass

    viewing = st.session_state.get('cs_viewing_source')

    if viewing:
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
        else:
            try:
                cs_uuid = UUID(str(viewing))
                chunks = chunk_service.list_by_content_source(content_source_id=cs_uuid)
                if not chunks:
                    st.info("No chunks found for this content source.")
                else:
                    num_cols = 3
                    cols = st.columns(num_cols)
                    for idx, chunk in enumerate(chunks):
                        col = cols[idx % num_cols]
                        with col:
                            st.markdown(f"**Chunk {idx + 1}**")
                            content_preview = (chunk.content[:400] + "...") if chunk.content and len(
                                chunk.content) > 400 else (chunk.content or "")
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

    else:
        selected_subject_name = st.session_state.get("sidebar_selected_subject")
        if selected_subject_name:
            st.markdown(f"**Filtering by:** {selected_subject_name}")
        else:
            st.markdown("**Filtering by:** All")

        header_cols = st.columns([3, 1, 0.7, 1.2, 0.6, 0.4, 0.4])
        header_cols[0].markdown("**Source**")
        header_cols[1].markdown("**Type**")
        header_cols[2].markdown("**Chunks**")
        header_cols[3].markdown("**Embedding model**")
        header_cols[4].markdown("**Dimensions**")
        header_cols[5].markdown("**Status**")
        header_cols[6].markdown("")

        for i, r in enumerate(table_rows):
            row_cols = st.columns([3, 1, 0.7, 1.2, 0.6, 0.4, 0.4])
            src_id = source_ids[i]
            link = f"?source={src_id}"
            row_cols[0].markdown(f"[{r['source']}]({link})", unsafe_allow_html=True)
            row_cols[1].markdown(f"<div class='small'>{r.get('type', '')}</div>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<div class='small'>{r.get('chunks', '')}</div>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<div class='small'>{r.get('embedding', '')}</div>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<div class='small'>{r.get('dims', '')}</div>", unsafe_allow_html=True)
            row_cols[5].markdown(f"<span class='badge green'>{r.get('status', '')}</span>", unsafe_allow_html=True)
            row_cols[6].markdown("<span class='action-dots'>⋯</span>", unsafe_allow_html=True)

        st.markdown("<div style='display:flex; justify-content:space-between; align-items:center; margin-top:12px'>",
                    unsafe_allow_html=True)
        st.markdown("<div class='small'>Page Size: <b>25</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='small'>1 to 25 of {len(table_rows)}</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='display:flex; gap:8px'><button class='btn-sync'>&lt;</button> <button class='btn-sync'>&gt;</button></div>",
            unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
