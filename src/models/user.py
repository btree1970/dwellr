from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from src.database.db import Base
from src.models.listing import ListingType, PricePeriod


class User(Base):
    __tablename__ = "users"
    
    # Core user information
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    
    # Hard filter preferences (database-level filtering only)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    price_period = Column(SQLEnum(PricePeriod), nullable=False, default=PricePeriod.MONTH)  # Period for price preferences
    preferred_start_date = Column(DateTime, nullable=True)
    preferred_end_date = Column(DateTime, nullable=True)
    preferred_listing_type = Column(SQLEnum(ListingType), nullable=True)
    date_flexibility_days = Column(Integer, nullable=False, default=0)  # Days of flexibility for date filtering
    
    preference_profile = Column(String, nullable=True)     # Comprehensive LLM-managed preference description
    preference_history = Column(JSON, nullable=True)       # Track preference evolution over time
    preference_version = Column(Integer, nullable=False, default=1)  # Version number for tracking updates
    last_preference_update = Column(DateTime, nullable=True)  # When preferences were last modified
    
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id='{self.id}', name='{self.name}', email='{self.email}')>"
    
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
        filters = {}
        
        if self.min_price is not None:
            filters['min_price'] = self.min_price
        if self.max_price is not None:
            filters['max_price'] = self.max_price
        
        # Always include price period for normalization
        filters['price_period'] = self.price_period
        
        if self.preferred_start_date is not None:
            filters['preferred_start_date'] = self.preferred_start_date
        if self.preferred_end_date is not None:
            filters['preferred_end_date'] = self.preferred_end_date
        if self.preferred_listing_type is not None:
            filters['preferred_listing_type'] = self.preferred_listing_type
        
        # Always include date flexibility for filtering logic
        filters['date_flexibility_days'] = self.date_flexibility_days
        
        # Include stay duration and pre-calculated normalized price bounds
        stay_duration = self.get_stay_duration_days()
        if stay_duration:
            filters['stay_duration_days'] = stay_duration
            
            # Pre-calculate normalized price bounds for efficient filtering
            if self.min_price is not None:
                filters['min_total_cost'] = round(self._calculate_total_cost(self.min_price, stay_duration), 2)
            if self.max_price is not None:
                filters['max_total_cost'] = round(self._calculate_total_cost(self.max_price, stay_duration), 2)
            
        return filters
