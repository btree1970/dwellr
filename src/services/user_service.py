from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.listing import ListingType, PricePeriod
from src.models.user import User


class UserServiceException(Exception):
    pass


class UserNotFound(UserServiceException):
    pass


class UserValidationError(UserServiceException):
    pass


class UserPreferenceUpdates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Price preferences
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    price_period: Optional[PricePeriod] = Field(
        None, description="Price period (day, week, month)"
    )

    # Date preferences
    preferred_start_date: Optional[datetime] = Field(
        None, description="Preferred start date for stay"
    )
    preferred_end_date: Optional[datetime] = Field(
        None, description="Preferred end date for stay"
    )
    date_flexibility_days: Optional[int] = Field(
        None, ge=0, le=30, description="Date flexibility in days"
    )

    # Listing preferences
    preferred_listing_type: Optional[ListingType] = Field(
        None, description="Preferred type of listing"
    )

    # Natural language preferences
    preference_profile: Optional[str] = Field(
        None, description="Detailed preferences and requirements in natural language"
    )


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, name: str, **kwargs: Any) -> User:
        """Create a new user (typically called during first authentication)"""
        try:
            user = User(name=name, **kwargs)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            if "auth_user_id" in str(e):
                raise UserValidationError("User already exists for this auth provider")
            raise UserValidationError(f"Database constraint violation: {e}")
        except Exception as e:
            self.db.rollback()
            raise UserServiceException(f"Error creating user: {e}")

    def find_or_create_user(self, auth_user_id: str, name: str, **kwargs: Any) -> User:
        """Find existing user by auth_user_id or create new one (for auth integration)"""
        try:
            # Try to find existing user
            user = self.db.query(User).filter(User.auth_user_id == auth_user_id).first()
            if user:
                return user

            # Create new user
            return self.create_user(name=name, auth_user_id=auth_user_id, **kwargs)
        except Exception as e:
            self.db.rollback()
            raise UserServiceException(f"Error finding or creating user: {e}")

    def get_user_by_id(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFound(f"User with ID {user_id} not found")
        return user

    def update_user_preferences(
        self, user_id: str, updates: UserPreferenceUpdates
    ) -> User:
        try:
            user = self.get_user_by_id(user_id)

            # Cross-field validation that Pydantic can't handle
            min_price = (
                updates.min_price if updates.min_price is not None else user.min_price
            )
            max_price = (
                updates.max_price if updates.max_price is not None else user.max_price
            )
            if (
                min_price is not None
                and max_price is not None
                and min_price > max_price
            ):
                raise UserValidationError("Minimum price cannot exceed maximum price")

            start_date = (
                updates.preferred_start_date
                if updates.preferred_start_date is not None
                else user.preferred_start_date
            )
            end_date = (
                updates.preferred_end_date
                if updates.preferred_end_date is not None
                else user.preferred_end_date
            )
            if (
                start_date is not None
                and end_date is not None
                and start_date >= end_date
            ):
                raise UserValidationError("End date must be after start date")

            # Update provided fields
            update_data = updates.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(user, key, value)

            # Update tracking fields
            user.preference_version += 1
            user.last_preference_update = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(user)
            return user

        except (UserNotFound, UserValidationError):
            raise
        except Exception as e:
            self.db.rollback()
            raise UserServiceException(f"Error updating user preferences: {e}")

    def has_minimum_profile_requirements(self, user: User) -> Tuple[bool, List[str]]:
        missing: List[str] = []

        # 100 chars ensures we have enough context for meaningful recommendations
        if not user.preference_profile or len(user.preference_profile) < 100:
            missing.append("detailed preferences (min 100 characters)")

        if user.min_price is None:
            missing.append("minimum budget")
        if user.max_price is None:
            missing.append("maximum budget")

        # Either specific dates OR flexibility is required to search listings
        if not user.preferred_start_date and user.date_flexibility_days == 0:
            missing.append("move-in timeline or date flexibility")

        return (len(missing) == 0, missing)

    def mark_profile_complete(self, user_id: str) -> User:
        user = self.get_user_by_id(user_id)

        has_reqs, missing = self.has_minimum_profile_requirements(user)
        if not has_reqs:
            raise UserValidationError(
                f"Cannot mark profile complete. Missing: {', '.join(missing)}"
            )

        user.profile_completed = True
        user.profile_completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_profile_completion(self, user_id: str) -> User:
        user = self.get_user_by_id(user_id)

        user.profile_completed = False
        user.profile_completed_at = None

        self.db.commit()
        self.db.refresh(user)
        return user
