import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings

# Configure logging
logging.basicConfig()
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for all models
class Base(DeclarativeBase):
    pass


# Database session management
@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


# Database operations
class DatabaseManager:
    """Database management operations."""

    @staticmethod
    def init_db():
        """Create all tables."""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    @staticmethod
    def drop_db():
        """Drop all tables."""
        try:
            Base.metadata.drop_all(bind=engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise

    @staticmethod
    def reset_db():
        """Drop and recreate all tables."""
        DatabaseManager.drop_db()
        DatabaseManager.init_db()

    @staticmethod
    def check_connection():
        """Check if database connection is working."""
        try:
            with engine.connect() as connection:
                from sqlalchemy import text

                connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False


# Initialize database manager
db_manager = DatabaseManager()
