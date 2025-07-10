"""Pytest configuration and shared fixtures for tests"""

import os
import sys
import pytest

# Set test environment before any imports
os.environ['ENV'] = 'test'

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db import DatabaseManager, get_db_session
from tests.fixtures.test_data import create_equivalent_price_test_listings, create_test_users


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
