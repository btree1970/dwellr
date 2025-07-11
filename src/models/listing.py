from typing import Optional
from enum import Enum
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
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
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    price: Mapped[Optional[float]] = mapped_column(Float)
    price_period: Mapped[Optional[PricePeriod]] = mapped_column(SQLEnum(PricePeriod))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    neighborhood: Mapped[Optional[str]] = mapped_column(String)
    brief_description: Mapped[Optional[str]] = mapped_column(String)
    full_description: Mapped[Optional[str]] = mapped_column(String)
    contact_name: Mapped[Optional[str]] = mapped_column(String)
    contact_email: Mapped[Optional[str]] = mapped_column(String)
    source_site: Mapped[str] = mapped_column(String, default="")
    listing_type: Mapped[ListingType] = mapped_column(SQLEnum(ListingType), default=ListingType.SUBLET)
    detail_fetched: Mapped[bool] = mapped_column(Boolean, default=False)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    
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
    
