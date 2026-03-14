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
                            # Wrap results in a scrollable container
                            with st.container(height=600, border=False):
                                # Deduplicate results while preserving order. Use id when available,
                                # fallback to (subject_id, external_source, content preview).
                                seen = set()
                                unique_results = []
                                for r in results:
                                    rid = getattr(r, "id", None)
                                    if rid is None:
                                        key = (
                                            str(getattr(r, "subject_id", "")),
                                            str(getattr(r, "external_source", "")),
                                            (getattr(r, "content") or "")[:200],
                                        )
                                    else:
                                        key = str(rid)
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                    unique_results.append(r)

                                if not unique_results:
                                    st.info("No results found")
                                else:
                                    for r in unique_results:
                                        st.markdown(r.content or "(no content)")
                                        st.caption(f"subject_id: {r.subject_id} • external_source: {r.external_source}")
                                        st.divider()
                    except Exception as e:
                        st.error(f"Search error: {e}")
                        st.code(traceback.format_exc())
