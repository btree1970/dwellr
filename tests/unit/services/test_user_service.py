from datetime import datetime

import pytest

from src.database.db import get_db_session
from src.services.user_service import (
    UserNotFound,
    UserPreferenceUpdates,
    UserService,
    UserValidationError,
)


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


class TestUpdateUserPreferences:
    def test_update_basic_fields(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            updates = UserPreferenceUpdates(
                min_price=1000.0,
                max_price=3000.0,
                preference_profile="Looking for a quiet neighborhood with good transit access",
            )

            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.min_price == 1000.0
            assert updated_user.max_price == 3000.0
            assert (
                updated_user.preference_profile
                == "Looking for a quiet neighborhood with good transit access"
            )
            assert updated_user.email == "test@example.com"  # unchanged

    def test_update_price_preferences(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            updates = UserPreferenceUpdates(min_price=1000.0, max_price=3000.0)

            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.min_price == 1000.0
            assert updated_user.max_price == 3000.0

    def test_update_date_preferences(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 2, 1)

            updates = UserPreferenceUpdates(
                preferred_start_date=start_date,
                preferred_end_date=end_date,
                date_flexibility_days=7,
            )

            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.preferred_start_date == start_date
            assert updated_user.preferred_end_date == end_date
            assert updated_user.date_flexibility_days == 7

    def test_partial_update(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(
                name="Test User", email="test@example.com", phone="555-0000"
            )

            # Set some initial preferences
            user.max_price = 2000.0
            db.commit()

            updates = UserPreferenceUpdates(min_price=1500.0)
            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.min_price == 1500.0
            assert updated_user.max_price == 2000.0  # unchanged
            assert updated_user.email == "test@example.com"  # unchanged

    def test_tracking_fields_updated(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            original_version = user.preference_version

            updates = UserPreferenceUpdates(preference_profile="Updated preferences")
            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.preference_version == original_version + 1
            assert updated_user.last_preference_update is not None
            assert updated_user.last_preference_update > user.created_at

    def test_price_range_validation_error(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            updates = UserPreferenceUpdates(min_price=3000.0, max_price=1000.0)

            with pytest.raises(
                UserValidationError, match="Minimum price cannot exceed maximum price"
            ):
                user_service.update_user_preferences(user.id, updates)

    def test_date_range_validation_error(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            start_date = datetime(2024, 2, 1)
            end_date = datetime(2024, 1, 1)

            updates = UserPreferenceUpdates(
                preferred_start_date=start_date, preferred_end_date=end_date
            )

            with pytest.raises(
                UserValidationError, match="End date must be after start date"
            ):
                user_service.update_user_preferences(user.id, updates)

    def test_cross_field_validation_with_existing_data(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", email="test@example.com")

            # Set existing max_price
            user.max_price = 2000.0
            db.commit()

            # Try to set min_price higher than existing max_price
            updates = UserPreferenceUpdates(min_price=3000.0)

            with pytest.raises(
                UserValidationError, match="Minimum price cannot exceed maximum price"
            ):
                user_service.update_user_preferences(user.id, updates)

    def test_user_not_found(self, clean_database):
        with get_db_session() as db:
            user_service = UserService(db)

            updates = UserPreferenceUpdates(min_price=1000.0)

            with pytest.raises(UserNotFound):
                user_service.update_user_preferences("nonexistent-id", updates)

    def test_pydantic_validation_negative_price(self):
        with pytest.raises(
            ValueError, match="Input should be greater than or equal to 0"
        ):
            UserPreferenceUpdates(min_price=-100.0)

    def test_pydantic_validation_date_flexibility_out_of_range(self):
        with pytest.raises(
            ValueError, match="Input should be less than or equal to 30"
        ):
            UserPreferenceUpdates(date_flexibility_days=50)

    def test_pydantic_forbids_extra_fields(self):
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            UserPreferenceUpdates(name="Test User", email="test@example.com")

    def test_pydantic_forbids_onboarding_fields(self):
        onboarding_fields = ["name", "email", "phone", "occupation", "bio"]

        for field in onboarding_fields:
            with pytest.raises(ValueError, match="Extra inputs are not permitted"):
                UserPreferenceUpdates(**{field: "test value"})
