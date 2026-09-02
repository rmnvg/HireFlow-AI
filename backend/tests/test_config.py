from pydantic import SecretStr

from app.config import Settings


def test_direct_supabase_url_can_use_session_pooler_without_exposing_password() -> None:
    settings = Settings(
        database_url=SecretStr(
            "postgresql://postgres:password%40value@db.projectref.supabase.co:5432/postgres"
        ),
        database_ssl=True,
        supabase_pooler_host="aws-0-ap-south-1.pooler.supabase.com",
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+psycopg://postgres.projectref:password%40value@"
        "aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    )


def test_pooler_url_is_not_rewritten() -> None:
    database_url = (
        "postgresql://postgres.projectref:password@"
        "aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    )
    settings = Settings(
        database_url=SecretStr(database_url),
        database_ssl=True,
        supabase_pooler_host="aws-0-ap-south-1.pooler.supabase.com",
    )

    assert settings.sqlalchemy_database_url == database_url.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
