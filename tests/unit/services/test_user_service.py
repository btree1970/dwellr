from datetime import datetime

import pytest
from returns.result import Failure, Success

from src.services.user_service import (
    UserNotFound,
    UserPreferenceUpdates,
    UserService,
)


class TestUserService:
    def test_create_user_basic(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            assert user.name == "Test User"
            assert user.id is not None
            assert user.evaluation_credits == 0.0  # default

    def test_create_user_with_kwargs(self, clean_database):
        with clean_database.get_session() as db:
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
        with clean_database.get_session() as db:
            user_service = UserService(db)
            created_user = user_service.create_user(name="Test User")

            retrieved_user = user_service.get_user_by_id(created_user.id)
            assert retrieved_user.id == created_user.id
            assert retrieved_user.name == "Test User"

    def test_get_user_by_id_not_found(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)

            with pytest.raises(UserNotFound):
                user_service.get_user_by_id("nonexistent-id")

    def test_find_or_create_user_creates_new(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.find_or_create_user(
                auth_user_id="auth123", name="Test User", evaluation_credits=5.0
            )

            assert user.name == "Test User"
            assert user.auth_user_id == "auth123"
            assert user.evaluation_credits == 5.0
            assert user.id is not None

    def test_find_or_create_user_finds_existing(self, clean_database):
        with clean_database.get_session() as db:
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
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            updates = UserPreferenceUpdates(
                min_price=1000.0,
                max_price=3000.0,
                preference_profile="Looking for a quiet neighborhood with good transit access",
            )

            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            updated_user = result.unwrap()

            assert updated_user.min_price == 1000.0
            assert updated_user.max_price == 3000.0
            assert (
                updated_user.preference_profile
                == "Looking for a quiet neighborhood with good transit access"
            )

    def test_update_price_preferences(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            updates = UserPreferenceUpdates(min_price=1000.0, max_price=3000.0)

            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            updated_user = result.unwrap()

            assert updated_user.min_price == 1000.0
            assert updated_user.max_price == 3000.0

    def test_update_date_preferences(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 2, 1)

            updates = UserPreferenceUpdates(
                preferred_start_date=start_date,
                preferred_end_date=end_date,
                date_flexibility_days=7,
            )

            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            updated_user = result.unwrap()

            assert updated_user.preferred_start_date == start_date
            assert updated_user.preferred_end_date == end_date
            assert updated_user.date_flexibility_days == 7

    def test_partial_update(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User", occupation="Engineer")

            # Set some initial preferences
            user.max_price = 2000.0
            db.commit()

            updates = UserPreferenceUpdates(min_price=1500.0)
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            updated_user = result.unwrap()

            assert updated_user.min_price == 1500.0
            assert updated_user.max_price == 2000.0  # unchanged
            assert updated_user.occupation == "Engineer"  # unchanged

    def test_tracking_fields_updated(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            original_version = user.preference_version

            updates = UserPreferenceUpdates(preference_profile="Updated preferences")
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            updated_user = result.unwrap()

            assert updated_user.preference_version == original_version + 1
            assert updated_user.last_preference_update is not None
            assert updated_user.last_preference_update > user.created_at

    def test_price_range_validation_error(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            updates = UserPreferenceUpdates(min_price=3000.0, max_price=1000.0)

            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Failure)
            assert "Minimum price cannot exceed maximum price" in result.failure()

    def test_date_range_validation_error(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            start_date = datetime(2024, 2, 1)
            end_date = datetime(2024, 1, 1)

            updates = UserPreferenceUpdates(
                preferred_start_date=start_date, preferred_end_date=end_date
            )

            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Failure)
            assert "End date must be after start date" in result.failure()

    def test_cross_field_validation_with_existing_data(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            # Set existing max_price
            user.max_price = 2000.0
            db.commit()

            # Try to set min_price higher than existing max_price
            updates = UserPreferenceUpdates(min_price=3000.0)

            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Failure)
            assert "Minimum price cannot exceed maximum price" in result.failure()

    def test_user_not_found(self, clean_database):
        with clean_database.get_session() as db:
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


class TestProfileCompletion:
    def test_has_minimum_requirements_all_met(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            updates = UserPreferenceUpdates(
                min_price=1000.0,
                max_price=3000.0,
                preference_profile="Looking for a 2BR apartment in Brooklyn with good transit access. Need pet-friendly building with laundry in unit or building.",
                preferred_start_date=datetime(2024, 2, 1),
                preferred_end_date=datetime(2024, 3, 1),
            )
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is True
            assert missing == []

    def test_has_minimum_requirements_missing_profile(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            # Test with no preference_profile
            updates = UserPreferenceUpdates(
                min_price=1000.0,
                max_price=3000.0,
                preferred_start_date=datetime(2024, 2, 1),
            )
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is False
            assert "detailed preferences (min 100 characters)" in missing

            # Test with too-short preference_profile
            updates = UserPreferenceUpdates(preference_profile="Too short")
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is False
            assert "detailed preferences (min 100 characters)" in missing

    def test_has_minimum_requirements_missing_budget(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            long_profile = "Looking for a 2BR apartment in Brooklyn with good transit access. Need pet-friendly building with laundry in unit or building."

            # Missing both min and max price
            updates = UserPreferenceUpdates(
                preference_profile=long_profile,
                preferred_start_date=datetime(2024, 2, 1),
            )
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is False
            assert "minimum budget" in missing
            assert "maximum budget" in missing

            # Missing only max price
            updates = UserPreferenceUpdates(min_price=1000.0)
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is False
            assert "minimum budget" not in missing
            assert "maximum budget" in missing

    def test_has_minimum_requirements_dates_or_flexibility(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            long_profile = "Looking for a 2BR apartment in Brooklyn with good transit access. Need pet-friendly building with laundry in unit or building."

            # Test with neither dates nor flexibility
            updates = UserPreferenceUpdates(
                min_price=1000.0, max_price=3000.0, preference_profile=long_profile
            )
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is False
            assert "move-in timeline or date flexibility" in missing

            # Test with date flexibility but no specific dates (should pass)
            updates = UserPreferenceUpdates(date_flexibility_days=14)
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is True
            assert missing == []

            # Reset flexibility and add specific date (should pass)
            updates = UserPreferenceUpdates(
                date_flexibility_days=0, preferred_start_date=datetime(2024, 2, 1)
            )
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            has_reqs, missing = user_service.has_minimum_profile_requirements(user)
            assert has_reqs is True
            assert missing == []

    def test_mark_profile_complete_success(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            # Set up user with all requirements
            updates = UserPreferenceUpdates(
                min_price=1000.0,
                max_price=3000.0,
                preference_profile="Looking for a 2BR apartment in Brooklyn with good transit access. Need pet-friendly building with laundry in unit or building.",
                preferred_start_date=datetime(2024, 2, 1),
                preferred_end_date=datetime(2024, 3, 1),
            )
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            # Verify initial state
            assert user.profile_completed is False
            assert user.profile_completed_at is None

            # Mark profile complete
            result = user_service.mark_profile_complete(user.id)
            assert isinstance(result, Success)
            completed_user = result.unwrap()

            assert completed_user.profile_completed is True
            assert completed_user.profile_completed_at is not None
            assert completed_user.profile_completed_at > completed_user.created_at

    def test_mark_profile_complete_missing_requirements(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            # User with incomplete profile
            updates = UserPreferenceUpdates(min_price=1000.0)
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()

            result = user_service.mark_profile_complete(user.id)
            assert isinstance(result, Failure)
            error_message = result.failure()

            # Verify error message contains missing items
            assert "Cannot mark profile complete. Missing:" in error_message
            assert "detailed preferences" in error_message
            assert "maximum budget" in error_message
            assert "move-in timeline" in error_message

    def test_mark_profile_complete_user_not_found(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)

            with pytest.raises(UserNotFound):
                user_service.mark_profile_complete("nonexistent-id")

    def test_reset_profile_completion(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            # Set up and complete profile
            updates = UserPreferenceUpdates(
                min_price=1000.0,
                max_price=3000.0,
                preference_profile="Looking for a 2BR apartment in Brooklyn with good transit access. Need pet-friendly building with laundry in unit or building.",
                preferred_start_date=datetime(2024, 2, 1),
            )
            result = user_service.update_user_preferences(user.id, updates)
            assert isinstance(result, Success)
            user = result.unwrap()
            result = user_service.mark_profile_complete(user.id)
            assert isinstance(result, Success)
            completed_user = result.unwrap()

            assert completed_user.profile_completed is True
            assert completed_user.profile_completed_at is not None

            # Reset profile
            reset_user = user_service.reset_profile_completion(user.id)

            assert reset_user.profile_completed is False
            assert reset_user.profile_completed_at is None
            # Preferences should remain intact
            assert reset_user.min_price == 1000.0
            assert reset_user.max_price == 3000.0

    def test_reset_profile_already_incomplete(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)
            user = user_service.create_user(name="Test User")

            # User starts with incomplete profile
            assert user.profile_completed is False
            assert user.profile_completed_at is None

            # Reset should work without error
            reset_user = user_service.reset_profile_completion(user.id)

            assert reset_user.profile_completed is False
            assert reset_user.profile_completed_at is None

    def test_reset_profile_user_not_found(self, clean_database):
        with clean_database.get_session() as db:
            user_service = UserService(db)

            with pytest.raises(UserNotFound):
                user_service.reset_profile_completion("nonexistent-id")
