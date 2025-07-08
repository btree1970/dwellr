from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy import Column, String, Float, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.database.db import Base

class ListingType(Enum):
    SUBLET = "sublet"
    RENTAL = "rental"

class Listing(Base):  # Remove @dataclass
    __tablename__ = "listings"
    
    # SQLAlchemy column definitions
    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    price_period = Column(String, nullable=True)
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
    
    # Relationship
    # communications = relationship("Communication", back_populates="listing")
    
    def __repr__(self):
        return f"<Listing(id='{self.id}', title='{self.title}', price={self.price})>"
    
