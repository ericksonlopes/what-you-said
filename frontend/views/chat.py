"""Chat view for interacting with the knowledge base."""

import streamlit as st
import textwrap
from frontend.utils.services import init_basic_services, init_full_services, list_subjects
from src.application.use_cases.search_chunks_use_case import SearchChunksUseCase

def render_chat_view():
    st.title("💬 Knowledge Chat")
    st.caption("Ask questions about your ingested content.")
    
    st.markdown("---")

    # Fetch all available knowledge subjects
    basic_services = init_basic_services()
    ks_service = basic_services["ks_service"]
    all_subjects = list_subjects(ks_service)
    subject_names = [s.name for s in all_subjects] if all_subjects else []

    # Initialize empty selection if not present
    if "chat_selected_knowledge" not in st.session_state:
        st.session_state["chat_selected_knowledge"] = []

    # Knowledge selection
    selected_knowledge = st.multiselect(
        "Select Knowledge Base(s)",
        options=subject_names,
        key="chat_selected_knowledge",
        help="Choose which subjects to include in the chat context."
    )

    st.markdown("---")
    
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "context" in message:
                with st.expander("Retrieved Context"):
                    st.write(message["context"])

    # React to user input
    if prompt := st.chat_input("What would you like to know?"):
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Process search for context
        retrieved_context = ""
        with st.spinner("Searching knowledge base..."):
            full = init_full_services()
            if full.get("ok") and selected_knowledge:
                svc = full["services"]
                try:
                    use_case = SearchChunksUseCase(
                        vector_service=svc["vector_service"],
                        ks_service=svc["ks_service"]
                    )
                    
                    # Search across all selected subjects
                    all_results = []
                    for subject_name in selected_knowledge:
                        res = use_case.execute(query=prompt, top_k=2, subject_name=subject_name)
                        all_results.extend(res.results)
                    
                    # Sort combined results by score
                    all_results.sort(key=lambda x: getattr(x, 'score', 0.0) or 0.0, reverse=True)
                    
                    if all_results:
                        context_parts = []
                        for i, r in enumerate(all_results[:3]): # Top 3 across all selected
                            context_parts.append(f"Source: {r.external_source}\nContent: {r.content}")
                        retrieved_context = "\n\n---\n\n".join(context_parts)
                except Exception as e:
                    st.error(f"Context retrieval error: {e}")

        # Assistant response
        if retrieved_context:
            response = "I found some information in your knowledge base that might help:\n\n(This is a preview of the RAG context. LLM generation is coming soon!)"
        else:
            response = "I couldn't find any specific information in the selected knowledge bases."

        with st.chat_message("assistant"):
            st.markdown(response)
            if retrieved_context:
                with st.expander("Retrieved Context"):
                    st.write(retrieved_context)
        
        # Save to history
        msg_entry = {"role": "assistant", "content": response}
        if retrieved_context:
            msg_entry["context"] = retrieved_context
        st.session_state.messages.append(msg_entry)
