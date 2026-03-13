from typing import List, Optional, Union, Protocol, Any
from uuid import UUID

from weaviate.collections.classes.filters import _Filters as Filters, Filter


class VectorRetriever(Protocol):
    """Protocol for objects that expose a retriever method used by the use case.

    This is intentionally narrow (structural typing) so tests can pass simple fakes.
    """

    def retriever(self, query: str, top_kn: int = 5, filters: Optional[Any] = None) -> List[Any]:
        ...


class SearchChunksUseCase:
    """Use case para pesquisa de chunks via vector service com filtro por knowledge_subject.

    Pode filtrar por subject_id (UUID ou str) ou por subject_name (requer ks_service).
    """

    def __init__(self, vector_service: VectorRetriever, ks_service=None):
        self.vector_service: VectorRetriever = vector_service
        self.ks_service = ks_service

    def execute(
            self,
            query: str,
            top_k: int = 5,
            subject_id: Optional[Union[str, UUID]] = None,
            subject_name: Optional[str] = None,
    ) -> List:
        # validações
        if subject_id and subject_name:
            raise ValueError("Provide only one of subject_id or subject_name")

        filters: Optional[Filters] = None
        filters_list = []

        # se passado subject_name, resolve para id usando ks_service
        if subject_name:
            if not self.ks_service:
                raise ValueError("ks_service is required to filter by subject_name")
            subject = self.ks_service.get_by_name(subject_name)
            if subject is None:
                # não encontrou subject: retorna lista vazia
                return []
            subject_id = subject.id

        if subject_id is not None:
            # weaviate espera o valor comparável - usar string do UUID
            filters_list.append(Filter.by_property("subject_id").equal(str(subject_id)))

        if filters_list:
            filters = Filter.all_of(filters_list)

        return self.vector_service.retriever(query, top_kn=top_k, filters=filters)
