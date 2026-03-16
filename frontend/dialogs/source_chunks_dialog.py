import streamlit as st
from uuid import UUID

@st.dialog("Source Chunks", width="large")
def show_source_chunks_dialog(source_id, source_title, chunk_service):
    st.markdown(f"### Chunks for: **{source_title}**")
    st.caption(f"Source ID: {source_id}")
    st.divider()

    try:
        cs_uuid = UUID(str(source_id))
        chunks = chunk_service.list_by_content_source(content_source_id=cs_uuid)
        
        if not chunks:
            st.info("Nenhum chunk encontrado para esta fonte.")
            return

        for idx, chunk in enumerate(chunks):
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 1, 1])
                content = chunk.content or ""
                
                with c1:
                    st.markdown(f"**Chunk #{idx + 1}**")
                with c2:
                    st.markdown(f"📏 **Chars:** {len(content)}")
                with c3:
                    lang = chunk.language or "Unknown"
                    st.markdown(f"🌐 **Lang:** {lang.upper()}")
                
                st.text_area("Content", value=content, height=150, key=f"chunk_text_{chunk.id}", disabled=True)
                
                # Metadata Expander
                with st.expander("Ver metadados completos"):
                    st.json({
                        "id": str(chunk.id),
                        "job_id": str(chunk.job_id),
                        "embedding_model": chunk.embedding_model,
                        "created_at": str(chunk.created_at),
                        "extra": chunk.extra
                    })
    except Exception as e:
        st.error(f"Erro ao carregar chunks: {e}")

    if st.button("Fechar", width='stretch'):
        st.rerun()
