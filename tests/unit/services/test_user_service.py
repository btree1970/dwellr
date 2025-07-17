import pytest

from src.database.db import get_db_session
from src.services.user_service import UserNotFound, UserService, UserValidationError


class TestUserService:
    def test_create_user_basic(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            assert user.name == "Test User"
            assert user.email == "test@example.com"
            assert user.id is not None

    def test_create_user_with_kwargs(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(
                name="Test User",
                email="test@example.com",
                phone="555-1234",
                occupation="Engineer",
            )

            assert user.name == "Test User"
            assert user.email == "test@example.com"
            assert user.phone == "555-1234"
            assert user.occupation == "Engineer"

    def test_create_user_duplicate_email(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user_service.create_user(name="User 1", email="test@example.com")

            with pytest.raises(UserValidationError, match="already exists"):
                user_service.create_user(name="User 2", email="test@example.com")

    def test_get_user_by_id(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            created_user = user_service.create_user(
                name="Test User", email="test@example.com"
            )

            retrieved_user = user_service.get_user_by_id(created_user.id)
            assert retrieved_user.id == created_user.id
            assert retrieved_user.name == "Test User"
            assert retrieved_user.email == "test@example.com"

    def test_get_user_by_id_not_found(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)

            with pytest.raises(UserNotFound):
                user_service.get_user_by_id("nonexistent-id")
