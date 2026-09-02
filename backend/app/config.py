from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded exclusively from environment variables."""

    database_url: SecretStr
    database_ssl: bool = False
    database_init_on_startup: bool = True
    frontend_url: str = "http://localhost:3000"
    backend_host: str = "0.0.0.0"
    backend_port: int = Field(default=8000, ge=1, le=65535)

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @field_validator("frontend_url")
    @classmethod
    def frontend_url_must_not_be_empty(cls, value: str) -> str:
        if not any(origin.strip() for origin in value.split(",")):
            raise ValueError("FRONTEND_URL must contain at least one origin")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.frontend_url.split(",")
            if origin.strip()
        ]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize common PostgreSQL URLs to SQLAlchemy's psycopg 3 dialect."""

        url = self.database_url.get_secret_value()
        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
            if url.startswith(prefix):
                return url.replace(prefix, "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
