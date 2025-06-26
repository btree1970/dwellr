from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ListingType(Enum):
    SUBLET = "sublet"
    RENTAL = "rental"
    ROOM = "room"
    ENTIRE_PLACE = "entire_place"


@dataclass
class Listing:
    id: str
    url: str
    title: str
    price: float
    location: str
    available_date: datetime
    listing_type: ListingType
    
    description: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    amenities: List[str] = None
    images: List[str] = None
    contact_info: Optional[str] = None
    
    source_site: str = ""
    scraped_at: datetime = None
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.amenities is None:
            self.amenities = []
        if self.images is None:
            self.images = []
        if self.scraped_at is None:
            self.scraped_at = datetime.now()
        if self.raw_data is None:
            self.raw_data = {}
    
    def matches_price_range(self, min_price: float, max_price: float) -> bool:
        return min_price <= self.price <= max_price
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "location": self.location,
            "available_date": self.available_date.isoformat(),
            "listing_type": self.listing_type.value,
            "description": self.description,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "square_feet": self.square_feet,
            "amenities": self.amenities,
            "images": self.images,
            "contact_info": self.contact_info,
            "source_site": self.source_site,
            "scraped_at": self.scraped_at.isoformat()
        }