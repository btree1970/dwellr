import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.orm.session import sessionmaker

from src.core.config import settings

logging.basicConfig()
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.project_root = Path(__file__).parent.parent.parent
        self.alembic_cfg_path = self.project_root / "alembic.ini"

        if self.alembic_cfg_path.exists():
            self.alembic_cfg = Config(str(self.alembic_cfg_path))
            self.alembic_cfg.set_main_option(
                "script_location", str(self.project_root / "migrations")
            )
            self.alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            self.has_alembic = True
        else:
            self.has_alembic = False
            logger.warning(
                "Alembic configuration not found, migration features unavailable"
            )

    def init_db(self) -> None:
        """Initialize database using Alembic migrations."""
        if self.has_alembic:
            status = self.check_migration_status()
            if status["is_up_to_date"]:
                logger.info("Database is already up to date")
            else:
                logger.info(f"Running {status['pending_count']} pending migrations")
                self.upgrade("head")
        else:
            logger.warning("Migrations not available, using create_all")
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")

    def drop_db(self) -> None:
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise

    def reset_db(self) -> None:
        """Reset database using migrations if available."""
        logger.warning("Resetting database - all data will be lost!")

        if self.has_alembic:
            # Drop all tables including enum types
            with self.engine.connect() as conn:
                # Drop all tables
                conn.execute(text("DROP SCHEMA public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
                conn.commit()

            # Run migrations to recreate tables
            self.upgrade("head")
            logger.info("Database reset complete")
        else:
            self.drop_db()
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database reset successfully")

    def check_connection(self) -> bool:
        """Check database connection."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def get_current_revision(self) -> Optional[str]:
        """Get the current database revision.

        Returns:
            The current revision ID or None if no migrations have been applied.
        """
        if not self.has_alembic:
            return None

        with self.engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()

    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations.

        Returns:
            List of pending migration revision IDs.
        """
        if not self.has_alembic:
            return []

        script = ScriptDirectory.from_config(self.alembic_cfg)
        current = self.get_current_revision()

        pending: List[str] = []
        for revision in script.walk_revisions():
            if current is None or revision.revision != current:
                pending.append(revision.revision)
                if revision.revision == current:
                    break

        return list(reversed(pending[:-1] if current else pending))

    def create_migration(self, message: str, autogenerate: bool = True) -> str:
        """Create a new migration.

        Args:
            message: Description of the migration
            autogenerate: Whether to autogenerate the migration from model changes

        Returns:
            The revision ID of the created migration.
        """
        if not self.has_alembic:
            raise RuntimeError("Alembic not configured")

        logger.info(f"Creating migration: {message}")

        if autogenerate:
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
        else:
            command.revision(self.alembic_cfg, message=message)

        script = ScriptDirectory.from_config(self.alembic_cfg)
        head = script.get_current_head()
        logger.info(f"Created migration {head}: {message}")
        return head or ""

    def upgrade(self, revision: str = "head") -> None:
        """Upgrade database to a revision.

        Args:
            revision: Target revision (default: "head" for latest)
        """
        if not self.has_alembic:
            raise RuntimeError("Alembic not configured")

        logger.info(f"Upgrading database to {revision}")
        command.upgrade(self.alembic_cfg, revision)
        logger.info(f"Database upgraded to {revision}")

    def downgrade(self, revision: str = "-1") -> None:
        """Downgrade database to a revision.

        Args:
            revision: Target revision (default: "-1" for one revision back)
        """
        if not self.has_alembic:
            raise RuntimeError("Alembic not configured")

        logger.info(f"Downgrading database to {revision}")
        command.downgrade(self.alembic_cfg, revision)
        logger.info(f"Database downgraded to {revision}")

    def get_history(self, verbose: bool = False) -> List[Dict[str, Any]]:
        """Get migration history.

        Args:
            verbose: Include detailed information

        Returns:
            List of migration history entries.
        """
        if not self.has_alembic:
            return []

        script = ScriptDirectory.from_config(self.alembic_cfg)
        current = self.get_current_revision()

        history: List[Dict[str, Any]] = []
        for revision in script.walk_revisions():
            entry: Dict[str, Any] = {
                "revision": revision.revision,
                "message": revision.doc,
                "is_current": revision.revision == current,
                "is_head": revision.is_head,
            }

            if verbose:
                entry["branch_labels"] = list(revision.branch_labels or [])
                entry["dependencies"] = revision.dependencies
                entry["down_revision"] = revision.down_revision

            history.append(entry)

        return history

    def check_migration_status(self) -> Dict[str, Any]:
        """Check the current migration status.

        Returns:
            Dictionary with migration status information.
        """
        if not self.has_alembic:
            return {
                "current_revision": None,
                "head_revision": None,
                "is_up_to_date": True,
                "pending_migrations": [],
                "pending_count": 0,
            }

        current = self.get_current_revision()
        pending = self.get_pending_migrations()

        script = ScriptDirectory.from_config(self.alembic_cfg)
        head = script.get_current_head()

        return {
            "current_revision": current,
            "head_revision": head,
            "is_up_to_date": current == head,
            "pending_migrations": pending,
            "pending_count": len(pending),
        }

    def stamp(self, revision: str = "head") -> None:
        """Stamp the database with a specific revision without running migrations.

        Args:
            revision: The revision to stamp (default: "head")

        This is useful when you've created the database schema manually
        and want to mark it as being at a specific migration version.
        """
        if not self.has_alembic:
            raise RuntimeError("Alembic not configured")

        logger.info(f"Stamping database with revision {revision}")
        command.stamp(self.alembic_cfg, revision)
        logger.info(f"Database stamped with revision {revision}")

    def verify_schema(self) -> Dict[str, Any]:
        """Verify that the database schema matches the models.

        Returns:
            Dictionary with verification results.
        """
        inspector = inspect(self.engine)
        db_tables = set(inspector.get_table_names())
        model_tables = set(Base.metadata.tables.keys())

        return {
            "database_tables": sorted(db_tables),
            "model_tables": sorted(model_tables),
            "missing_in_db": sorted(model_tables - db_tables),
            "extra_in_db": sorted(db_tables - model_tables - {"alembic_version"}),
            "is_valid": model_tables.issubset(db_tables | {"alembic_version"}),
        }

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session from this manager's engine."""
        db: Session = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            db.close()


# Global db_manager instance - can be replaced by tests
db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


@contextmanager
def get_db_with_context() -> Generator[Session, None, None]:
    with get_db_manager().get_session() as db:
        yield db


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session"""
    manager = get_db_manager()
    session = sessionmaker(autocommit=False, autoflush=False, bind=manager.engine)()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
