import traceback
import sys
from pathlib import Path

# Ensure project root is on sys.path
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import streamlit as st
from src.config.settings import settings

def init_basic_services():
    from src.infrastructure.repositories.sql.knowledge_subject_repository import KnowledgeSubjectSQLRepository
    from src.infrastructure.services.knowledge_subject_service import KnowledgeSubjectService
    from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository
    from src.infrastructure.services.content_source_service import ContentSourceService
    from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
    from src.infrastructure.services.ingestion_job_service import IngestionJobService
    from src.infrastructure.repositories.sql.chunk_index_repository import ChunkIndexSQLRepository
    from src.infrastructure.services.chunk_index_service import ChunkIndexService

    return {
        "ks_service": KnowledgeSubjectService(KnowledgeSubjectSQLRepository()),
        "cs_service": ContentSourceService(ContentSourceSQLRepository()),
        "ingestion_service": IngestionJobService(IngestionJobSQLRepository()),
        "chunk_service": ChunkIndexService(ChunkIndexSQLRepository()),
    }

def get_raw_services():
    basic = init_basic_services()
    try:
        from src.infrastructure.services.model_loader_service import ModelLoaderService
        from src.infrastructure.services.embeddding_service import EmbeddingService
        from src.infrastructure.repositories.vector.weaviate.weaviate_client import WeaviateClient
        from src.infrastructure.repositories.vector.weaviate.chunk_repository import ChunkWeaviateRepository
        from src.infrastructure.services.chunk_vector_service import ChunkVectorService

        model_loader = ModelLoaderService(settings.model_embedding.name)
        embedding_service = EmbeddingService(model_loader)
        weaviate_client = WeaviateClient(settings.vector)
        vector_repo = ChunkWeaviateRepository(weaviate_client=weaviate_client, embedding_service=embedding_service,
                                              collection_name=settings.vector.weaviate_collection_name_chunks,
                                              text_key="content")
        vector_service = ChunkVectorService(repository=vector_repo)

        full_services = {
            **basic,
            "model_loader": model_loader,
            "embedding_service": embedding_service,
            "vector_service": vector_service,
        }
        return {"ok": True, "services": full_services}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

@st.cache_resource
def init_full_services():
    return get_raw_services()

def list_subjects(ks_service):
    try:
        return ks_service.list_subjects(limit=200)
    except Exception as e:
        st.error(f"Error listing subjects: {e}")
        return []

def log_toast(message, icon="ℹ️"):
    if "toast_logs" not in st.session_state:
        st.session_state["toast_logs"] = []
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state["toast_logs"].insert(0, {"msg": message, "icon": icon, "time": timestamp})
    st.session_state["toast_logs"] = st.session_state["toast_logs"][:20]
