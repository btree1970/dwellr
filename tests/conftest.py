import os
import sys

import pytest

# Set test environment before any imports
os.environ["ENV"] = "test"

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.db import DatabaseManager, get_db_session
from tests.fixtures.test_data import (
    create_equivalent_price_test_listings,
    create_multiple_listings,
    create_standard_listing,
    create_test_users,
    create_user_with_credits,
)


@pytest.fixture(scope="session")
def celery_config():
    """Configuration for Celery testing - uses in-memory broker"""
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
    """Celery modules to include for testing"""
    return ["src.workers.tasks"]


@pytest.fixture(scope="session")
def celery_worker_parameters():
    """Parameters for Celery worker during tests"""
    return {
        "queues": ("test_queue",),
        "exclude_queues": ("celery",),
    }


@pytest.fixture(scope="function")
def celery_app_and_worker(celery_app, celery_worker):
    """Fixture that provides both celery app and worker for integration tests"""
    yield celery_app, celery_worker


@pytest.fixture(scope="function")
def clean_database():
    """Provide a clean database for each test"""
    db_manager = DatabaseManager()
    db_manager.drop_db()
    db_manager.init_db()
    yield
    # Cleanup is handled by the next test's setup


@pytest.fixture(scope="function")
def db_with_test_data(clean_database):
    """Provide database with standard test data loaded"""
    listings = create_equivalent_price_test_listings()
    users = create_test_users()

    with get_db_session() as db:
        for listing in listings:
            db.add(listing)
        for user in users:
            db.add(user)
        db.commit()

    yield db


@pytest.fixture
def equivalent_listings():
    """Provide equivalent test listings without database storage"""
    return create_equivalent_price_test_listings()


@pytest.fixture
def test_users():
    """Provide test users without database storage"""
    return create_test_users()


@pytest.fixture
def user_with_credits():
    """Provide a user with evaluation credits - can be customized per test"""
    return create_user_with_credits()


@pytest.fixture
def standard_listing():
    """Provide a standard test listing - can be customized per test"""
    return create_standard_listing()


@pytest.fixture
def multiple_listings():
    """Provide multiple test listings - can be customized per test"""
    return create_multiple_listings()
