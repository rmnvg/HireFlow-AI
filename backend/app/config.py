from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded exclusively from environment variables."""

    database_url: str
    cors_origins: str = "http://localhost:3000"
    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=8000, ge=1, le=65535)

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
