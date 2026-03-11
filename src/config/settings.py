import logging
from typing import List, Annotated, Optional

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class WeaviateConfig(BaseSettings):
    host: str = Field(default="localhost", description="WeaviateConfig host URL")
    port: int = Field(default=8081, description="WeaviateConfig port")
    api_key: Optional[str] = Field(default=None, description="WeaviateConfig API key for authentication")
    grpc_port: int = Field(default=50051, description="WeaviateConfig gRPC port for local connections")
    collection_name_youtube_transcripts: str = Field(default="YoutubeTranscripts",
                                                     description="WeaviateConfig collection name for YouTube transcripts")

    @property
    def url(self) -> str:
        """Construct the full URL for WeaviateConfig connection."""
        return f"http://{self.host}:{self.port}"


class App(BaseSettings):
    env: str = Field(default="development", description="Application environment (e.g., 'development', 'production', "
                                                        "'testing')")

    @field_validator('env')
    @classmethod
    def _validate_env(cls, v):
        """Validate that the environment variable is one of the allowed values."""
        allowed_envs = {"development", "production", "testing"}
        if v not in allowed_envs:
            raise ValueError(f"env must be one of {allowed_envs}, got '{v}'")
        return v

    list_log_levels: Annotated[List[str], NoDecode] = Field(
        default=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        description="Comma-separated list of log levels to enable (e.g., 'DEBUG,INFO,WARNING')"
    )

    @field_validator('list_log_levels', mode='before')
    @classmethod
    def _parse_list_log_levels(cls, v) -> List[str]:
        """Parse a comma-separated string into a list of log levels. If it's already a list, return it as is."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v

    @property
    def allowed_log_levels(self) -> set:
        """Return allowed logging levels as a set of ints."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return {level_map[level] for level in self.list_log_levels if level in level_map}


class ModelEmbedding(BaseSettings):
    name: str = Field(default="all-MiniLM-L6-v2", description="Name of the embedding model to use")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__'
    )
    app: App = Field(default_factory=App, description="Application settings")
    weaviate: WeaviateConfig = Field(default_factory=WeaviateConfig, description="WeaviateConfig connection settings")
    model_embedding: ModelEmbedding = Field(default_factory=ModelEmbedding, description="Model embedding settings")


settings = Settings()
