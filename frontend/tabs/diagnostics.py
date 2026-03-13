"""Diagnostics tab renderer."""

import traceback

import streamlit as st


def render(init_full_services, settings):
    st.header("Diagnostics")
    st.subheader("Main Configurations")
    st.json({
        "vector": {
            "store_type": settings.vector.store_type,
            "weaviate_host": settings.vector.weaviate_host,
            "weaviate_port": settings.vector.weaviate_port,
            "collection": settings.vector.weaviate_collection_name_chunks,
        },
        "model_embedding": settings.model_embedding.name,
        "sql_url": settings.sql.url,
    })

    if st.button("Check Model Loading"):
        with st.spinner("Loading model (this may take a while)..."):
            try:
                full = init_full_services()
                if not full.get("ok"):
                    st.error(full.get("error", ""))
                    st.code(full.get("traceback", ""))
                else:
                    ml = full["services"].get("model_loader")
                    if ml:
                        try:
                            dims = ml.dimensions
                        except Exception:
                            dims = "(error retrieving dimensions)"
                        st.success(f"Model loaded: {ml.model_name} • device: {ml.device} • dims: {dims}")
            except Exception as e:
                st.error(f"Error loading model: {e}")
                st.code(traceback.format_exc())

    if st.button("Check Weaviate Connection"):
        with st.spinner("Checking Weaviate..."):
            try:
                from src.infrastructure.repositories.vector.weaviate.weaviate_client import WeaviateClient

                wc = WeaviateClient(settings.vector)
                try:
                    # Use context manager without assigning an unused name to avoid SonarQube warning
                    with wc:
                        st.success("Weaviate successfully connected")
                except Exception as e:
                    st.error(f"Error connecting to Weaviate: {e}")
            except Exception as e:
                st.error(f"Weaviate module unavailable or error: {e}")
                st.code(traceback.format_exc())
