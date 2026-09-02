from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def create_database_engine() -> Engine:
    settings = get_settings()
    connect_args: dict[str, str] = {}
    if settings.database_ssl and settings.sqlalchemy_database_url.startswith("postgresql"):
        connect_args["sslmode"] = "require"

    return create_engine(
        settings.sqlalchemy_database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models here so all table metadata is registered before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
