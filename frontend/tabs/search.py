"""Search tab renderer."""

import traceback

import streamlit as st


def render(init_full_services):
    st.header("Semantic Search")
    query = st.text_input("Query")
    top_k = st.slider("Top K", min_value=1, max_value=20, value=5)
    if st.button("Search"):
        # Validate input early to avoid backend exceptions
        if not query or not str(query).strip():
            st.error("Please provide a search query")
            return

        with st.spinner("Performing search... (Weaviate must be available)"):
            full = init_full_services()
            if not full.get("ok"):
                st.error("Vector services not initialized: " + full.get("error", ""))
            else:
                svc = full["services"]
                vector_service = svc.get("vector_service")
                if vector_service is None:
                    st.error("Vector service unavailable")
                else:
                    try:
                        results = vector_service.search(query=str(query).strip(), top_k=top_k)

                        if not results:
                            st.info("No results found")
                        else:
                            # Fetch services needed for metadata
                            basic_services = init_full_services().get("services", {})
                            cs_service = basic_services.get("cs_service")

                            # Deduplicate results while preserving order.
                            seen = set()
                            unique_results = []
                            for r in results:
                                rid = getattr(r, "id", None)
                                # Fallback key if ID is missing
                                key = str(rid) if rid else (str(getattr(r, "subject_id", "")), (getattr(r, "content") or "")[:200])
                                
                                if key in seen:
                                    continue
                                seen.add(key)
                                unique_results.append(r)

                            if not unique_results:
                                st.info("No results found")
                            else:
                                st.markdown(f"Showing top {len(unique_results)} relevant chunks:")
                                
                                for r in unique_results:
                                    # Try to fetch Content Source details for better identification
                                    source_info_html = ""
                                    if cs_service and hasattr(r, 'content_source_id'):
                                        try:
                                            source = cs_service.get_by_id(r.content_source_id)
                                            if source:
                                                stype = source.source_type.value if hasattr(source.source_type, 'value') else str(source.source_type)
                                                source_info_html = f"""
                                                    <div style="margin-bottom: 8px;">
                                                        <span class="badge badge-active" style="text-transform: uppercase; font-size: 0.65rem;">{stype}</span>
                                                        <span style="color: #e6eef7; font-weight: 600; font-size: 0.85rem; margin-left: 8px;">{source.title or 'Untitled Source'}</span>
                                                        <br><span style="color: #71717a; font-size: 0.7rem; font-family: monospace;">{source.external_source}</span>
                                                    </div>
                                                """
                                        except Exception:
                                            pass

                                    # Render as a card matching the Dashboard style
                                    st.markdown(f"""
                                        <div class="chunk-card">
                                            {source_info_html}
                                            <div class="chunk-content" style="margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px;">
                                                {r.content or "(no content)"}
                                            </div>
                                            <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
                                                <span style="color: #3f3f46; font-size: 10px;">CHUNK ID: {str(r.id)[:18]}...</span>
                                                <span class="chunk-meta" style="font-size: 9px;">Score: {getattr(r, 'score', 'N/A')}</span>
                                            </div>
                                        </div>
                                    """, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Search error: {e}")
                        st.code(traceback.format_exc())
