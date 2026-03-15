"""Search tab renderer."""

import traceback
import textwrap
import streamlit as st
from src.application.use_cases.search_chunks_use_case import SearchChunksUseCase


def render(init_full_services):
    st.header("Semantic Search")
    
    # Filter by current subject if selected
    selected_sid = st.session_state.get("selected_subject_id")
    selected_sname = st.session_state.get("sidebar_selected_subject")
    
    if selected_sname:
        st.caption(f"Searching in context: **{selected_sname}**")
    
    query = st.text_input("Query", placeholder="What are you looking for?")
    top_k = st.slider("Top K", min_value=1, max_value=20, value=5)
    
    if st.button("Search", type="primary"):
        if not query or not str(query).strip():
            st.error("Please provide a search query")
            return

        with st.spinner("Searching knowledge base..."):
            full = init_full_services()
            if not full.get("ok"):
                st.error("Services not initialized: " + full.get("error", ""))
            else:
                svc = full["services"]
                try:
                    # Use the refactored Use Case
                    use_case = SearchChunksUseCase(
                        vector_service=svc["vector_service"],
                        ks_service=svc["ks_service"]
                    )
                    
                    result = use_case.execute(
                        query=str(query).strip(),
                        top_k=top_k,
                        subject_id=selected_sid
                    )

                    if not result.results:
                        st.info("No relevant chunks found for this query.")
                    else:
                        cs_service = svc.get("cs_service")
                        st.markdown(f"Found **{result.total_count}** relevant chunks:")
                        
                        # Sorting is already handled by vector store (relevance), 
                        # but we ensure it here just in case.
                        sorted_results = sorted(result.results, key=lambda x: getattr(x, 'score', 0.0) or 0.0, reverse=True)

                        for r in sorted_results:
                            source_info_html = ""
                            if cs_service and hasattr(r, 'content_source_id') and r.content_source_id:
                                try:
                                    source = cs_service.get_by_id(r.content_source_id)
                                    if source:
                                        stype = source.source_type.value if hasattr(source.source_type, 'value') else str(source.source_type)
                                        source_info_html = textwrap.dedent(f"""
                                            <div style="margin-bottom: 8px;">
                                                <span class="badge badge-active" style="text-transform: uppercase; font-size: 0.65rem;">{stype}</span>
                                                <span style="color: #e6eef7; font-weight: 600; font-size: 0.85rem; margin-left: 8px;">{source.title or 'Untitled Source'}</span>
                                                <br><span style="color: #71717a; font-size: 0.7rem; font-family: monospace;">{source.external_source}</span>
                                            </div>
                                        """).strip()
                                except Exception:
                                    pass

                            # Metadata formatting
                            content_text = r.content or ""
                            char_count = len(content_text)
                            score_val = getattr(r, 'score', 0.0)
                            score_display = f"{score_val:.4f}" if isinstance(score_val, (int, float)) else "N/A"
                            
                            card_html = textwrap.dedent(f"""
                                <div class="chunk-card">
                                    {source_info_html}
                                    <div class="chunk-content" style="margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">
                                        {content_text or "(no content)"}
                                    </div>
                                    <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
                                        <div style="display: flex; gap: 8px;">
                                            <span class="chunk-meta" style="font-size: 9px; background: rgba(59,130,246,0.1); color: #3b82f6;">Score: {score_display}</span>
                                            <span class="chunk-meta" style="font-size: 9px;">{char_count} chars</span>
                                            <span class="chunk-meta" style="font-size: 9px;">{getattr(r, 'tokens_count', 0) or 'N/A'} tokens</span>
                                            <span class="chunk-meta" style="font-size: 9px;">Version: {getattr(r, 'version_number', 1)}</span>
                                        </div>
                                        <span style="color: #3f3f46; font-size: 10px;">CHUNK ID: {str(r.id)[:18]}...</span>
                                    </div>
                                </div>
                            """).strip()
                            
                            st.markdown(card_html, unsafe_allow_html=True)
                            
                except Exception as e:
                    st.error(f"Search error: {e}")
                    st.code(traceback.format_exc())
