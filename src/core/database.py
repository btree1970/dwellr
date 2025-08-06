import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm.session import sessionmaker

from src.core.config import settings

logging.basicConfig()
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_db_with_context() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session"""
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class DatabaseManager:
    @staticmethod
    def init_db():
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    @staticmethod
    def drop_db():
        try:
            Base.metadata.drop_all(bind=engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise

    @staticmethod
    def reset_db():
        DatabaseManager.drop_db()
        DatabaseManager.init_db()

    @staticmethod
    def check_connection():
        try:
            with engine.connect() as connection:
                from sqlalchemy import text

                connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False


db_manager = DatabaseManager()
