import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.listing import ListingType, PricePeriod


class User(Base):
    __tablename__ = "users"

    # Core user information
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    auth_user_id: Mapped[Optional[str]] = mapped_column(
        String, unique=True, index=True
    )  # Links to Supabase auth.users.id
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    age: Mapped[Optional[int]] = mapped_column(Integer)
    occupation: Mapped[Optional[str]] = mapped_column(String)
    bio: Mapped[Optional[str]] = mapped_column(String)

    # Hard filter preferences (database-level filtering only)
    min_price: Mapped[Optional[float]] = mapped_column(Float)
    max_price: Mapped[Optional[float]] = mapped_column(Float)
    price_period: Mapped[PricePeriod] = mapped_column(
        SQLEnum(PricePeriod), default=PricePeriod.MONTH
    )
    preferred_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    preferred_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    preferred_listing_type: Mapped[Optional[ListingType]] = mapped_column(
        SQLEnum(ListingType)
    )
    date_flexibility_days: Mapped[int] = mapped_column(Integer, default=0)

    preference_profile: Mapped[Optional[str]] = mapped_column(String)
    preference_history: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    preference_version: Mapped[int] = mapped_column(Integer, default=1)
    last_preference_update: Mapped[Optional[datetime]] = mapped_column(DateTime)

    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    evaluation_credits: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<User(id='{self.id}', name='{self.first_name} {self.last_name}')>"

    def get_stay_duration_days(self) -> Optional[int]:
        """Calculate stay duration in days from preferred dates"""
        if self.preferred_start_date and self.preferred_end_date:
            duration = self.preferred_end_date - self.preferred_start_date
            return duration.days
        return None

    def _calculate_total_cost(self, price: float, duration_days: int) -> float:
        """Calculate total cost for user's price period and stay duration

        Args:
            price: Price in user's preferred period
            duration_days: Duration of stay in days

        Returns:
            Total cost for the duration
        """
        if self.price_period == PricePeriod.DAY:
            return price * duration_days
        elif self.price_period == PricePeriod.WEEK:
            return price * (duration_days / 7)
        elif self.price_period == PricePeriod.MONTH:
            return price * (duration_days / 30)
        else:
            return price * duration_days

    def get_hard_filters(self) -> Dict[str, Any]:
        """Return database-level filtering criteria"""
        filters: Dict[str, Any] = {}

        if self.min_price is not None:
            filters["min_price"] = self.min_price
        if self.max_price is not None:
            filters["max_price"] = self.max_price

        # Always include price period for normalization
        filters["price_period"] = self.price_period

        if self.preferred_start_date is not None:
            filters["preferred_start_date"] = self.preferred_start_date
        if self.preferred_end_date is not None:
            filters["preferred_end_date"] = self.preferred_end_date
        if self.preferred_listing_type is not None:
            filters["preferred_listing_type"] = self.preferred_listing_type

        # Always include date flexibility for filtering logic
        filters["date_flexibility_days"] = self.date_flexibility_days

        # Include stay duration and pre-calculated normalized price bounds
        stay_duration = self.get_stay_duration_days()
        if stay_duration:
            filters["stay_duration_days"] = stay_duration

            # Pre-calculate normalized price bounds for efficient filtering
            if self.min_price is not None:
                filters["min_total_cost"] = round(
                    self._calculate_total_cost(self.min_price, stay_duration), 2
                )
            if self.max_price is not None:
                filters["max_total_cost"] = round(
                    self._calculate_total_cost(self.max_price, stay_duration), 2
                )

        return filters
