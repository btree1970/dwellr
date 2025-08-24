from datetime import datetime, timezone
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator
from returns.result import Failure, Result, Success
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


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Required fields
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    # Optional profile fields
    age: Optional[int] = Field(None, ge=0, le=150)
    occupation: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = Field(None, max_length=1000)

    # Auth and system fields
    auth_user_id: Optional[str] = Field(None, max_length=100)
    evaluation_credits: float = Field(default=5.0, ge=0)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("occupation", "bio")
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=150)
    occupation: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = Field(None, max_length=1000)

    @field_validator("first_name", "last_name", "occupation", "bio")
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


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


def _validate_price_range(
    min_price: Optional[float], max_price: Optional[float]
) -> Result[None, str]:
    """Validate that min_price doesn't exceed max_price."""
    if min_price is not None and max_price is not None and min_price > max_price:
        return Failure("Minimum price cannot exceed maximum price")
    return Success(None)


def _validate_date_range(
    start_date: Optional[datetime], end_date: Optional[datetime]
) -> Result[None, str]:
    """Validate that start_date is before end_date."""
    if start_date is not None and end_date is not None and start_date >= end_date:
        return Failure("End date must be after start date")
    return Success(None)


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: CreateUserRequest) -> User:
        try:
            user = User(**user_data.model_dump())
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

    def find_or_create_user(self, user_data: CreateUserRequest) -> User:
        """Find existing user by auth_user_id or create new one"""
        if not user_data.auth_user_id:
            raise UserValidationError("auth_user_id is required for find_or_create")

        try:
            # Try to find existing user
            user = (
                self.db.query(User)
                .filter(User.auth_user_id == user_data.auth_user_id)
                .first()
            )
            if user:
                # Update user info with non-None values from request
                update_data = user_data.model_dump(
                    exclude_unset=True, exclude={"auth_user_id", "evaluation_credits"}
                )
                for field, value in update_data.items():
                    if value is not None:
                        setattr(user, field, value)
                self.db.commit()
                self.db.refresh(user)
                return user

            # Create new user
            return self.create_user(user_data)
        except Exception as e:
            self.db.rollback()
            raise UserServiceException(f"Error finding or creating user: {e}")

    def get_user_by_id(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFound(f"User with ID {user_id} not found")
        return user

    def update_user_profile(self, user_id: str, update_data: UpdateUserRequest) -> User:
        try:
            user = self.get_user_by_id(user_id)

            # Update only provided fields (exclude_unset=True)
            for field, value in update_data.model_dump(exclude_unset=True).items():
                setattr(user, field, value)

            self.db.commit()
            self.db.refresh(user)
            return user
        except UserNotFound:
            raise
        except Exception as e:
            self.db.rollback()
            raise UserServiceException(f"Error updating user profile: {e}")

    def update_user_preferences(
        self, user_id: str, updates: UserPreferenceUpdates
    ) -> Result[User, str]:
        """Update user preferences with validation.

        Returns:
            Success(User) if update succeeded
            Failure(str) if validation failed

        Raises:
            UserNotFound: If user doesn't exist (truly exceptional)
            UserServiceException: For database errors (truly exceptional)
        """
        try:
            user = self.get_user_by_id(user_id)

            # Validate price range
            min_price = (
                updates.min_price if updates.min_price is not None else user.min_price
            )
            max_price = (
                updates.max_price if updates.max_price is not None else user.max_price
            )
            price_validation = _validate_price_range(min_price, max_price)
            if isinstance(price_validation, Failure):
                return price_validation

            # Validate date range
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
            date_validation = _validate_date_range(start_date, end_date)
            if isinstance(date_validation, Failure):
                return date_validation

            # Update provided fields
            update_data = updates.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(user, key, value)

            # Update tracking fields
            user.preference_version += 1
            user.last_preference_update = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(user)
            return Success(user)

        except UserNotFound:
            # Let truly exceptional cases bubble up
            raise
        except Exception as e:
            self.db.rollback()
            # Database errors are truly exceptional
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

    def mark_profile_complete(self, user_id: str) -> Result[User, str]:
        """Mark user profile as complete if all requirements are met.

        Returns:
            Success(User) if profile was marked complete
            Failure(str) if requirements are missing
        """
        user = self.get_user_by_id(user_id)

        has_reqs, missing = self.has_minimum_profile_requirements(user)
        if not has_reqs:
            return Failure(
                f"Cannot mark profile complete. Missing: {', '.join(missing)}"
            )

        user.profile_completed = True
        user.profile_completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(user)
        return Success(user)

    def reset_profile_completion(self, user_id: str) -> User:
        user = self.get_user_by_id(user_id)

        user.profile_completed = False
        user.profile_completed_at = None

        self.db.commit()
        self.db.refresh(user)
        return user
