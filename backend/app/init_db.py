import logging

from sqlalchemy.exc import SQLAlchemyError

from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        init_db()
    except SQLAlchemyError:
        logger.error("Database initialization failed")
        raise SystemExit(1) from None
    logger.info("Database tables initialized")


if __name__ == "__main__":
    main()
