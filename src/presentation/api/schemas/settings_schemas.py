from typing import Optional
from pydantic import BaseModel

class AppSettingsSchema(BaseModel):
    env: str
    log_levels: str

class VectorSettingsSchema(BaseModel):
    store_type: str
    weaviate_host: str
    weaviate_port: int
    weaviate_grpc_port: int
    weaviate_collection: str

class ModelSettingsSchema(BaseModel):
    name: str

class SQLSettingsSchema(BaseModel):
    type: Optional[str] = None
    database: Optional[str] = None

class SettingsResponse(BaseModel):
    app: AppSettingsSchema
    vector: VectorSettingsSchema
    model: ModelSettingsSchema
    sql: SQLSettingsSchema

class HealthCheckResponse(BaseModel):
    status: str
    latency_ms: Optional[int] = None
    message: Optional[str] = None
