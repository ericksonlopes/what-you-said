import time
from typing import Annotated

import sqlalchemy
from src.config.settings import Settings

from fastapi import Depends, APIRouter, HTTPException
from src.presentation.api.dependencies import get_vector_repository, get_settings
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.presentation.api.schemas.settings_schemas import (
    SettingsResponse, 
    AppSettingsSchema, 
    VectorSettingsSchema, 
    ModelSettingsSchema, 
    SQLSettingsSchema,
    HealthCheckResponse
)
from src.infrastructure.repositories.sql.connector import Connector

router = APIRouter()

@router.get("", response_model=SettingsResponse)
def get_current_settings(settings: Annotated[Settings, Depends(get_settings)]):
    """Return current application settings (sanitized)"""
    return SettingsResponse(
        app=AppSettingsSchema(
            env=settings.app.env,
            log_levels=", ".join(settings.app.list_log_levels)
        ),
        vector=VectorSettingsSchema(
            store_type=settings.vector.store_type.value,
            weaviate_host=settings.vector.weaviate_host,
            weaviate_port=settings.vector.weaviate_port,
            weaviate_grpc_port=settings.vector.weaviate_grpc_port,
            weaviate_collection=settings.vector.collection_name_chunks
        ),
        model=ModelSettingsSchema(
            name=settings.model_embedding.name
        ),
        sql=SQLSettingsSchema(
            type=settings.sql.type or "sqlite",
            database=settings.sql.database or "app.sqlite"
        )
    )

@router.get(
    "/check/{component}",
    response_model=HealthCheckResponse,
    responses={
        400: {"description": "Unknown component provided"}
    }
)
def check_component_health(
    component: str,
    vector_repo: Annotated[IVectorRepository, Depends(get_vector_repository)]
):
    """Perform health check for a specific component"""
    start_time = time.time()
    
    try:
        if component == "api":
            latency = int((time.time() - start_time) * 1000)
            return HealthCheckResponse(status="success", latency_ms=latency, message="API is responding")
            
        elif component == "sql":
            with Connector() as session:
                session.execute(sqlalchemy.text("SELECT 1"))
            latency = int((time.time() - start_time) * 1000)
            return HealthCheckResponse(status="success", latency_ms=latency, message="SQL connection successful")
            
        elif component == "vector":
            if vector_repo.is_ready():
                latency = int((time.time() - start_time) * 1000)
                return HealthCheckResponse(status="success", latency_ms=latency, message="Vector store is ready")
            else:
                return HealthCheckResponse(status="error", message="Vector store is not ready")
                    
        elif component == "model":
            # For now, we just assume it's okay if it loaded correctly at startup
            # A more robust check would involve reaching out to a model health endpoint if exists
            latency = int((time.time() - start_time) * 1000)
            return HealthCheckResponse(status="success", latency_ms=latency, message="Model configuration active")
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown component: {component}")
            
    except Exception as e:
        return HealthCheckResponse(status="error", message=str(e))
