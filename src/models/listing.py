from typing import Optional, Any
from enum import Enum
from sqlalchemy import Column, String, Float, DateTime, Boolean, Enum as SQLEnum
from src.database.db import Base

class ListingType(Enum):
    SUBLET = "sublet"
    RENTAL = "rental"

class PricePeriod(Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

class Listing(Base):  
    __tablename__ = "listings"
    
    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    price_period = Column(SQLEnum(PricePeriod), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    neighborhood = Column(String, nullable=True)
    brief_description = Column(String, nullable=True)
    full_description = Column(String, nullable=True)
    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    source_site = Column(String, nullable=False, default="")
    listing_type = Column(SQLEnum(ListingType), nullable=False, default=ListingType.SUBLET)
    detail_fetched = Column(Boolean, nullable=False, default=False)
    scraped_at = Column(DateTime, nullable=True)
    
    
    def __repr__(self):
        return f"<Listing(id='{self.id}', title='{self.title}', price={self.price}, price_period={self.price_period}, start_date={self.start_date}, end_date={self.end_date})>"
    
    def calculate_total_cost_for_duration(self, duration_days: int) -> float:
        """Calculate total cost for a specific duration in days
        
        Args:
            duration_days: Number of days for the stay
            
        Returns:
            Total cost for the duration
        """
        if not self.price or not self.price_period:
            return 0.0
            
        if self.price_period == PricePeriod.DAY:
            return self.price * duration_days
        elif self.price_period == PricePeriod.WEEK:
            return self.price * (duration_days / 7)
        elif self.price_period == PricePeriod.MONTH:
            return self.price * (duration_days / 30)
        else:
            # Fallback for unknown periods
            return self.price * duration_days
    
