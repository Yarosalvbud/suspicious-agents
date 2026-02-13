from __future__ import annotations

from pydantic import Field
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    LANGUAGE_MODEL_LINK: str = Field(...)
    TOGETHER_API_KEY: SecretStr = Field(...)
    LOG_DIR: str = Field(...)
    LOGGER_LOG_LEVEL: str = Field(...)
    TIMEOUT: int = Field(...)
    CLIENT_MIN_PARAMS: int = Field(...)
    CLIENT_MAX_PARAMS: int = Field(...)
    GRAPH_DELAY: float = Field(...)

    LOG_FILE_PATH: str = Field(...)
    NIFI_FLOW_FILE_PATH: str = Field(...)
    LOG_LEVEL: str = Field(...)
    MINUTES_DELTA: str = Field(...)
    CONTAINER_NAME: str = Field(...)
    NIFI_BASE_URL: str = Field(...)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


Settings.model_rebuild()
settings = Settings()
