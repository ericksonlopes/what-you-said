"""Dialog helpers for the Streamlit frontend.

Provides open_create_subject(sidebar_ks, safe_rerun) which uses the
@st.dialog API when available and falls back to st.modal or st.expander.
"""

import streamlit as st


def _create_subject_body(sidebar_ks, safe_rerun):
    """Render the form body used by dialog/modal/expander."""
    _new_name = st.text_input("Novo Subject - Nome", key="dialog_create_subject_name")
    _new_desc = st.text_area("Descrição", key="dialog_create_subject_desc")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Criar", key="dialog_create_subject_submit"):
            if not _new_name or not str(_new_name).strip():
                st.error("Nome é obrigatório")
            else:
                try:
                    created = sidebar_ks.create_subject(name=str(_new_name).strip(), description=_new_desc)
                    st.success(f"Criado: {created.name}")
                    # trigger a rerun so the sidebar list updates
                    safe_rerun()
                except Exception as e:
                    st.error(f"Erro ao criar subject: {e}")
    with c2:
        if st.button("Cancelar", key="dialog_create_subject_cancel"):
            safe_rerun()


def open_create_subject(sidebar_ks, safe_rerun):
    """Open the create-subject dialog/modal/expander.

    When st.dialog is available, defines a decorated dialog and opens it.
    Otherwise falls back to st.modal or st.expander.
    """
    # Prefer the decorator dialog API when available
    if hasattr(st, "dialog"):
        @st.dialog("Criar Subject")
        def _dialog():
            _create_subject_body(sidebar_ks, safe_rerun)

        # Call the decorated function to show the dialog
        return _dialog()

    # Fallback to modal or expander
    try:
        if hasattr(st, "modal"):
            with st.modal("Criar Subject"):
                _create_subject_body(sidebar_ks, safe_rerun)
        else:
            with st.expander("Criar Subject", expanded=True):
                _create_subject_body(sidebar_ks, safe_rerun)
    except Exception:
        # Last-resort fallback
        with st.expander("Criar Subject", expanded=True):
            _create_subject_body(sidebar_ks, safe_rerun)
