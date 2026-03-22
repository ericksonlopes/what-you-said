from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException

from src.config.logger import Logger
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)
from src.application.use_cases.knowledge_subject_use_case import KnowledgeSubjectUseCase
from src.presentation.api.dependencies import get_ks_service, get_ks_use_case
from src.presentation.api.schemas.subject_schemas import (
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)

logger = Logger()
router = APIRouter()


@router.post(
    "",
    response_model=SubjectResponse,
    status_code=201,
    responses={500: {"description": "Internal server error"}},
)
def create_subject(
    subject: Annotated[SubjectCreate, Body()],
    ks_service: Annotated[KnowledgeSubjectService, Depends(get_ks_service)],
):
    """Create a new knowledge subject"""
    try:
        created = ks_service.create_subject(
            name=subject.name,
            description=subject.description,
            icon=subject.icon,
            external_ref=subject.external_ref,
        )
        return created
    except Exception as e:
        logger.error(e, context={"action": "create_subject"})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "",
    response_model=List[SubjectResponse],
    responses={500: {"description": "Internal server error"}},
)
def get_subjects(
    ks_service: Annotated[KnowledgeSubjectService, Depends(get_ks_service)],
):
    """Retrieve all knowledge subjects"""
    try:
        subjects = ks_service.list_subjects()
        return subjects
    except Exception as e:
        logger.error(e, context={"action": "list_subjects"})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/{subject_id}",
    status_code=204,
    responses={
        404: {"description": "Subject not found"},
        500: {"description": "Internal server error"},
    },
)
def update_subject(
    subject_id: UUID,
    subject: Annotated[SubjectUpdate, Body()],
    ks_service: Annotated[KnowledgeSubjectService, Depends(get_ks_service)],
):
    """Update an existing knowledge subject"""
    try:
        ks_service.update_subject(
            id=subject_id,
            name=subject.name,
            description=subject.description,
            icon=subject.icon,
        )
    except Exception as e:
        logger.error(
            e, context={"action": "update_subject", "subject_id": str(subject_id)}
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{subject_id}",
    status_code=204,
    responses={
        404: {"description": "Subject not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_subject(
    subject_id: UUID,
    ks_use_case: Annotated[KnowledgeSubjectUseCase, Depends(get_ks_use_case)],
):
    """Delete a knowledge subject"""
    try:
        success = ks_use_case.delete_knowledge(subject_id=subject_id)
        if not success:
            raise HTTPException(status_code=404, detail="Subject not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            e, context={"action": "delete_subject", "subject_id": str(subject_id)}
        )
        raise HTTPException(status_code=500, detail="Internal server error")
