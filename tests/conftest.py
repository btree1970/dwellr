import os
import sys

import pytest
from testcontainers.postgres import PostgresContainer

# Set test environment before any imports
os.environ["ENV"] = "test"

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.database import DatabaseManager
from tests.fixtures.test_data import (
    create_equivalent_price_test_listings,
    create_multiple_listings,
    create_standard_listing,
    create_test_users,
    create_user_with_credits,
)


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": True,
        "task_eager_propagates": True,
        "task_routes": {
            "src.workers.tasks.*": {"queue": "test_queue"},
        },
    }


@pytest.fixture(scope="session")
def celery_includes():
    return ["src.workers.tasks"]


@pytest.fixture(scope="session")
def celery_worker_parameters():
    return {
        "queues": ("test_queue",),
        "exclude_queues": ("celery",),
    }


@pytest.fixture(scope="function")
def celery_app_and_worker(celery_app, celery_worker):
    yield celery_app, celery_worker


@pytest.fixture(scope="function")
def clean_database(postgres_container):
    test_db_manager = DatabaseManager(database_url=postgres_container)

    # Replace the global db_manager with our test one
    import src.core.database

    src.core.database.db_manager = test_db_manager

    # Reset the database
    test_db_manager.reset_db()

    yield test_db_manager


@pytest.fixture(scope="function")
def db_with_test_data(clean_database):
    listings = create_equivalent_price_test_listings()
    users = create_test_users()

    with clean_database.get_session() as db:
        for listing in listings:
            db.add(listing)
        for user in users:
            db.add(user)
        db.commit()
        yield db


@pytest.fixture
def equivalent_listings():
    return create_equivalent_price_test_listings()


@pytest.fixture
def test_users():
    return create_test_users()


@pytest.fixture
def user_with_credits():
    return create_user_with_credits()


@pytest.fixture
def standard_listing():
    return create_standard_listing()


@pytest.fixture
def multiple_listings():
    return create_multiple_listings()
