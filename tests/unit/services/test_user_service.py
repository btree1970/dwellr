from datetime import datetime

import pytest

from src.core.database import get_db_with_context
from src.services.user_service import (
    UserNotFound,
    UserPreferenceUpdates,
    UserService,
    UserValidationError,
)


class TestUserService:
    def test_create_user_basic(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            assert user.name == "Test User"
            assert user.id is not None
            assert user.evaluation_credits == 0.0  # default

    def test_create_user_with_kwargs(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(
                name="Test User",
                occupation="Engineer",
                bio="Software engineer with passion for tech",
                evaluation_credits=10.0,
            )

            assert user.name == "Test User"
            assert user.occupation == "Engineer"
            assert user.bio == "Software engineer with passion for tech"
            assert user.evaluation_credits == 10.0

    def test_get_user_by_id(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            created_user = user_service.create_user(name="Test User")

            retrieved_user = user_service.get_user_by_id(created_user.id)
            assert retrieved_user.id == created_user.id
            assert retrieved_user.name == "Test User"

    def test_get_user_by_id_not_found(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)

            with pytest.raises(UserNotFound):
                user_service.get_user_by_id("nonexistent-id")

    def test_find_or_create_user_creates_new(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.find_or_create_user(
                auth_user_id="auth123", name="Test User", evaluation_credits=5.0
            )

            assert user.name == "Test User"
            assert user.auth_user_id == "auth123"
            assert user.evaluation_credits == 5.0
            assert user.id is not None

    def test_find_or_create_user_finds_existing(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)

            # Create a user first
            original_user = user_service.create_user(
                name="Original User", auth_user_id="auth123", evaluation_credits=10.0
            )

            # Try to find_or_create with same auth_user_id
            found_user = user_service.find_or_create_user(
                auth_user_id="auth123",
                name="Different Name",  # This should be ignored
                evaluation_credits=20.0,  # This should be ignored
            )

            assert found_user.id == original_user.id
            assert found_user.name == "Original User"  # Original name preserved
            assert found_user.evaluation_credits == 10.0  # Original credits preserved
            assert found_user.auth_user_id == "auth123"


class TestUpdateUserPreferences:
    def test_update_basic_fields(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

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

    def test_update_price_preferences(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            updates = UserPreferenceUpdates(min_price=1000.0, max_price=3000.0)

            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.min_price == 1000.0
            assert updated_user.max_price == 3000.0

    def test_update_date_preferences(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

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
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", occupation="Engineer")

            # Set some initial preferences
            user.max_price = 2000.0
            db.commit()

            updates = UserPreferenceUpdates(min_price=1500.0)
            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.min_price == 1500.0
            assert updated_user.max_price == 2000.0  # unchanged
            assert updated_user.occupation == "Engineer"  # unchanged

    def test_tracking_fields_updated(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            original_version = user.preference_version

            updates = UserPreferenceUpdates(preference_profile="Updated preferences")
            updated_user = user_service.update_user_preferences(user.id, updates)

            assert updated_user.preference_version == original_version + 1
            assert updated_user.last_preference_update is not None
            assert updated_user.last_preference_update > user.created_at

    def test_price_range_validation_error(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            updates = UserPreferenceUpdates(min_price=3000.0, max_price=1000.0)

            with pytest.raises(
                UserValidationError, match="Minimum price cannot exceed maximum price"
            ):
                user_service.update_user_preferences(user.id, updates)

    def test_date_range_validation_error(self, clean_database):
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

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
        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

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
        with get_db_with_context() as db:
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
            UserPreferenceUpdates(invalid_field="test value")
