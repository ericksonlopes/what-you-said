import logging
from typing import List, Annotated

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    ENV: str = Field(default="development", description="Application environment (e.g., 'development', 'production')")

    LIST_LOG_LEVELS: Annotated[List[str], NoDecode] = Field(
        default=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        description="Comma-separated list of log levels to enable (e.g., 'DEBUG,INFO,WARNING')"
    )

    MODEL_EMBEDDING_NAME: str = Field(default="all-MiniLM-L6-v2", description="Name of the embedding model to use")

    @field_validator('LIST_LOG_LEVELS', mode='before')
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
        return {level_map[level] for level in self.LIST_LOG_LEVELS if level in level_map}

    model_config = {
        'env_file': '.env'
    }


settings = Settings()
