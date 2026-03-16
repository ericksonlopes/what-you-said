"""Content Sources tab renderer with pagination."""

from uuid import UUID
import math
import streamlit as st

PAGE_SIZE = 10
CHUNKS_PAGE_SIZE = 5

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
                st.error(f"Error opening Add Knowledge dialog: {e}")


def _fetch_content_sources(services, page=1):
    cs = services["cs_service"]
    selected_subject_id = st.session_state.get("selected_subject_id")
    
    if not selected_subject_id:
        return [], 0

    try:
        try:
            sid = UUID(selected_subject_id)
        except Exception:
            sid = selected_subject_id
            
        offset = (page - 1) * PAGE_SIZE
        total_count = cs.count_by_subject(subject_id=sid)
        sources = cs.list_by_subject(subject_id=sid, limit=PAGE_SIZE, offset=offset)
        
        return sources, total_count
    except Exception as e:
        st.error(f"Error listing content sources: {e}")
        return [], 0


def _build_rows(content_sources):
    table_rows = []
    source_ids = []
    if content_sources:
        for c in content_sources:
            # Main title from database, fallback to ID/Source
            title = getattr(c, 'title', None) or getattr(c, 'external_source', None) or str(getattr(c, 'id', ''))
            ext_source = getattr(c, 'external_source', None) or ""
            
            # Normalize Type
            stype = getattr(c, 'source_type', None)
            if stype is not None:
                ctype = stype.value if hasattr(stype, 'value') else str(stype)
            else:
                ctype = getattr(c, 'mime_type', None) or "youtube"
                
            chunks = getattr(c, 'chunks', 0)
            embedding = getattr(c, 'embedding_model', "N/A")
            dims = getattr(c, 'dimensions', 0)
            
            # Normalize Status
            raw_status = getattr(c, 'processing_status', getattr(c, 'status', 'pending'))
            status = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
            
            # Format date and time
            created_at = getattr(c, 'created_at', None)
            date_str = created_at.strftime("%d/%m/%Y %H:%M") if created_at else "N/A"
            
            table_rows.append({
                "title": title,
                "external_source": ext_source,
                "type": str(ctype).lower(),
                "chunks": chunks,
                "embedding": embedding,
                "dims": dims,
                "status": str(status).lower(),
                "date": date_str,
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

    # Inject CSS to make native components look like the original HTML table
    st.markdown("""
        <style>
        /* Style to simulate table rows */
        .source-row {
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding: 10px 0;
            transition: background 0.2s;
        }
        
        /* Modifying only tertiary buttons (for table titles)
           so we don't break default (secondary) buttons in the rest of the app */
        div.stButton > button[kind="tertiary"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
            color: #e6eef7 !important;
            text-align: left !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            transition: color 0.2s ease, transform 0.1s ease !important;
            min-height: unset !important;
            line-height: 1.2 !important;
            box-shadow: none !important;
            
            /* Truncation to avoid line breaks */
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            display: block !important;
            width: 100% !important;
        }
        
        /* Style for subtext (URL/ID) to also avoid breaking */
        .source-sub {
            color: #6a737d;
            font-size: 0.7rem;
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-top: -2px;
        }
        
        /* Title Hover Effect */
        div.stButton > button[kind="tertiary"]:hover {
            color: #3b82f6 !important;
            background: transparent !important;
            text-decoration: none !important;
        }
        
        /* Click feedback */
        div.stButton > button[kind="tertiary"]:active {
            transform: translateY(1px);
            color: #2563eb !important;
        }

        /* Button container adjustment to avoid layout jumps */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
            gap: 0px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    h_cols = st.columns([28, 8, 8, 15, 8, 12, 16, 5])
    headers = ["Source", "Type", "Chunks", "Model", "Dims", "Status", "Date", ""]
    for col, header in zip(h_cols, headers):
        if header:
            col.markdown(f'<span style="color: #9aa4ad; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{header}</span>', unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 8px; border-bottom: 1px solid rgba(255,255,255,0.1);'></div>", unsafe_allow_html=True)

    # Linhas da "Tabela"
    for i, r in enumerate(table_rows):
        src_id = source_ids[i]
        
        # Container para simular a linha (tr)
        with st.container():
            c_src, c_type, c_chunks, c_model, c_dims, c_status, c_date, c_actions = st.columns([28, 8, 8, 15, 8, 12, 16, 5])
            
            with c_src:
                # Botão estilizado como link (Título) que agora troca para a vista de chunks
                if st.button(r['title'], key=f"btn_title_{src_id}", type="tertiary"):
                    st.session_state["view_source_id"] = src_id
                    st.session_state["view_source_title"] = r['title']
                    st.session_state["chunks_current_page"] = 1
                    st.rerun()
                st.markdown(f'<span class="source-sub">{r["external_source"]}</span>', unsafe_allow_html=True)
            
            with c_type:
                st.markdown(f'<span class="meta-text">{r["type"].upper()}</span>', unsafe_allow_html=True)
            
            with c_chunks:
                st.markdown(f'<span class="meta-text">{r["chunks"]}</span>', unsafe_allow_html=True)
            
            with c_model:
                raw_emb = r.get('embedding')
                m_name = raw_emb.split('/')[-1] if raw_emb and '/' in raw_emb else (raw_emb or "N/A")
                st.markdown(f'<span class="meta-text" title="{raw_emb or ""}">{m_name}</span>', unsafe_allow_html=True)
            
            with c_dims:
                st.markdown(f'<span class="meta-text">{r["dims"]}</span>', unsafe_allow_html=True)
            
            with c_status:
                # Correctly map status to CSS class
                s_key = r['status']
                s_class = f"badge-{s_key}" if s_key in ['done', 'processing', 'pending', 'error', 'failed'] else "badge-active"
                st.markdown(f'<span class="badge {s_class}">{s_key}</span>', unsafe_allow_html=True)
            
            with c_date:
                st.markdown(f'<span class="meta-text">{r["date"]}</span>', unsafe_allow_html=True)
            
            with c_actions:
                st.markdown('<span class="action-dots">⋮</span>', unsafe_allow_html=True)
            
            # Row divider
            st.markdown("<div style='border-bottom: 1px solid rgba(255,255,255,0.05); margin: 8px 0;'></div>", unsafe_allow_html=True)


def _render_pagination_controls(total_count, current_page, state_key, page_size=PAGE_SIZE):
    total_pages = max(1, math.ceil(total_count / page_size))
    
    # Navigation container at the bottom
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_page > 1:
            if st.button("← Previous", key=f"prev_{state_key}", width='stretch'):
                st.session_state[state_key] = current_page - 1
                st.rerun()
        else:
            st.button("← Previous", key=f"prev_{state_key}_disabled", width='stretch', disabled=True)
    
    with col2:
        st.markdown(f"<p style='text-align: center; color: #9aa4ad; font-size: 0.9rem; margin-top: 5px; font-weight: 500;'>Page {current_page} of {total_pages}<br><span style='font-size: 0.75rem; font-weight: 400;'>({total_count} total items)</span></p>", unsafe_allow_html=True)
        
    with col3:
        if current_page < total_pages:
            if st.button("Next →", key=f"next_{state_key}", width='stretch'):
                st.session_state[state_key] = current_page + 1
                st.rerun()
        else:
            st.button("Next →", key=f"next_{state_key}_disabled", width='stretch', disabled=True)


def _render_chunks_view(source_id, source_title, services):
    """Render the chunk cards view for a specific source with pagination."""
    if st.button("← Back to Sources", key="back_to_sources"):
        st.session_state.pop("view_source_id", None)
        st.session_state.pop("view_source_title", None)
        st.session_state.pop("chunks_current_page", None)
        st.rerun()

    st.title(source_title)
    st.caption(f"Source ID: {source_id}")

    chunk_service = services["chunk_service"]
    cs_service = services["cs_service"]
    ingestion_service = services["ingestion_service"]
    
    try:
        from uuid import UUID
        sid_uuid = UUID(str(source_id))
        
        # Check source status first
        source_entity = cs_service.get_by_id(sid_uuid)
        
        # Extract clean status string
        raw_status = getattr(source_entity, 'processing_status', getattr(source_entity, 'status', None))
        status_val = str(raw_status.value if hasattr(raw_status, 'value') else raw_status).lower()
        is_failed = status_val in ['failed', 'error']

        # Pagination logic
        current_page = st.session_state.get("chunks_current_page", 1)
        offset = (current_page - 1) * CHUNKS_PAGE_SIZE
        
        total_count = chunk_service.count_by_content_source(sid_uuid)
        chunks = chunk_service.list_by_content_source(content_source_id=sid_uuid, limit=CHUNKS_PAGE_SIZE, offset=offset)

        if not chunks and total_count == 0:
            if is_failed:
                st.error("### ❌ Ingestion Failed")
                # Fetch the last job for this source to get the error message
                jobs = ingestion_service.list_by_content_source(sid_uuid)
                if jobs:
                    last_job = jobs[0] # assuming sorted by date or most recent
                    st.markdown("**Error Details:**")
                    st.code(last_job.error_message or "No detailed error message available.", language="text")
                    
                    st.markdown("---")
                    st.info("💡 **Suggestion:** Check if the YouTube video has transcripts enabled or try a different video.")
            else:
                st.info("No chunks found for this source.")
            return

        st.markdown(f"Total chunks: **{total_count}**")
        
        # Render chunks naturally without fixed height container
        for idx, chunk in enumerate(chunks):
            real_idx = offset + idx + 1
            content = chunk.content or ""
            char_count = len(content)

            st.markdown(f"""
                <div class="chunk-card">
                    <div class="chunk-header">
                        <div>
                            <span class="chunk-title">Chunk {real_idx}</span>
                            <span class="chunk-meta">{char_count} chars</span>
                            <span class="chunk-meta">{chunk.tokens_count or 'N/A'} tokens</span>
                            <span class="chunk-meta">{chunk.language or 'PT'}</span>
                        </div>
                        <span style="color: #3f3f46; font-size: 10px;">ID: {str(chunk.id)[:8]}</span>
                    </div>
                    <div class="chunk-content">{content}</div>
                </div>
            """, unsafe_allow_html=True)
        # Pagination controls fixed below
        _render_pagination_controls(total_count, current_page, "chunks_current_page", CHUNKS_PAGE_SIZE)

        # Bottom "Back to Sources" button for convenience
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        if st.button("← Back to Sources", key="back_to_sources_bottom", width='stretch'):
            st.session_state.pop("view_source_id", None)
            st.session_state.pop("view_source_title", None)
            st.session_state.pop("chunks_current_page", None)
            st.rerun()


    except Exception as e:
        st.error(f"Error loading chunks: {e}")


@st.fragment(run_every="2s")
def _table_fragment_internal(services, safe_rerun):
    # Determine view state inside fragment to ensure fragment is always in the execution path
    view_source_id = st.session_state.get("view_source_id")

    if view_source_id:
        source_title = st.session_state.get("view_source_title", "Selected Source")
        _render_chunks_view(view_source_id, source_title, services)
    else:
        selected_subject_name = st.session_state.get("sidebar_selected_subject")
        
        # Handle Pagination State
        current_page = st.session_state.get("cs_current_page", 1)
        content_sources, total_count = _fetch_content_sources(services, page=current_page)
        table_rows, source_ids = _build_rows(content_sources)
        
        # Render table naturally without fixed height container
        _render_table(table_rows, source_ids, selected_subject_name)
        
        # Show pagination controls
        _render_pagination_controls(total_count, current_page, "cs_current_page", PAGE_SIZE)


def render(services, safe_rerun):
    # Reset page if subject changes
    selected_sid = st.session_state.get("selected_subject_id")
    if st.session_state.get("last_sid_cs") != selected_sid:
        st.session_state["cs_current_page"] = 1
        st.session_state["last_sid_cs"] = selected_sid

    # Fixed Header (Only shown when NOT in chunks view)
    if not st.session_state.get("view_source_id"):
        _render_header_and_button(services, safe_rerun)
    
    # Always call the fragment for the main content area
    _table_fragment_internal(services, safe_rerun)
