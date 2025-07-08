from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from src.database.db import Base
from src.models.listing import ListingType


class User(Base):
    """User model with integrated listing preferences"""
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
    preferred_start_date = Column(DateTime, nullable=True)
    preferred_end_date = Column(DateTime, nullable=True)
    preferred_listing_type = Column(SQLEnum(ListingType), nullable=True)
    
    # LLM-managed preferences (consolidated)
    preference_profile = Column(String, nullable=True)     # Comprehensive LLM-managed preference description
    preference_history = Column(JSON, nullable=True)       # Track preference evolution over time
    preference_version = Column(Integer, nullable=False, default=1)  # Version number for tracking updates
    last_preference_update = Column(DateTime, nullable=True)  # When preferences were last modified
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id='{self.id}', name='{self.name}', email='{self.email}')>"
    
    def get_hard_filters(self) -> Dict[str, Any]:
        """Return database-level filtering criteria"""
        filters = {}
        
        if self.min_price is not None:
            filters['min_price'] = self.min_price
        if self.max_price is not None:
            filters['max_price'] = self.max_price
        if self.preferred_start_date is not None:
            filters['preferred_start_date'] = self.preferred_start_date
        if self.preferred_end_date is not None:
            filters['preferred_end_date'] = self.preferred_end_date
        if self.preferred_listing_type is not None:
            filters['preferred_listing_type'] = self.preferred_listing_type
            
        return filters