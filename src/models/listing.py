from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class ListingType(Enum):
    SUBLET = "sublet"
    RENTAL = "rental"
    ROOM = "room"


@dataclass
class Listing:
    # Required fields
    id: str
    url: str
    title: str
    
    # Core fields from listing card
    price: Optional[float] = None  # Monthly price (normalized)
    price_period: Optional[str] = None  # Original period (day/week/month)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None  # For temporary sublets
    neighborhood: Optional[str] = None  # Specific area within city (from title)
    
    # Content fields
    brief_description: Optional[str] = None  # Preview text from card
    full_description: Optional[str] = None  # Complete listing text from detail page

    contact_name = Optional[str] = None
    contact_email = Option[str] = None
    
    # Metadata
    source_site: str = ""
    listing_type: ListingType = ListingType.SUBLET
    detail_fetched: bool = False  # Whether we've fetched the full page
    scraped_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now()
    
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "price_period": self.price_period,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "neighborhood": self.neighborhood,
            "listing_type": self.listing_type.value,
            "brief_description": self.brief_description,
            "full_description": self.full_description,
            "source_site": self.source_site,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "detail_fetched": self.detail_fetched
        }
