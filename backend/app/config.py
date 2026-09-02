from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Runtime configuration loaded exclusively from environment variables."""

    database_url: SecretStr
    database_ssl: bool = False
    database_init_on_startup: bool = True
    supabase_pooler_host: str | None = None
    frontend_url: str = "http://localhost:3000"
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    apollo_api_key: SecretStr | None = None
    apollo_contacts_url: str = "https://api.apollo.io/api/v1/contacts/search"
    apollo_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    hunar_api_key: SecretStr | None = None
    hunar_base_url: str = "https://api.voice.hunar.ai/external/v1"
    hunar_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    public_backend_url: str = "http://localhost:8000"
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
                url = url.replace(prefix, "postgresql+psycopg://", 1)

        pooler_host = (self.supabase_pooler_host or "").strip()
        if not pooler_host:
            return url

        parsed = make_url(url)
        direct_host = parsed.host or ""
        host_parts = direct_host.split(".")
        if (
            len(host_parts) >= 3
            and host_parts[0] == "db"
            and direct_host.endswith(".supabase.co")
        ):
            project_ref = host_parts[1]
            username = parsed.username or "postgres"
            if username == "postgres":
                username = f"postgres.{project_ref}"
            parsed = parsed.set(host=pooler_host, port=5432, username=username)
            return parsed.render_as_string(hide_password=False)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
