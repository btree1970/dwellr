from pydantic import BaseModel, Field
from typing import Literal, Optional


class ListingProjectSearchParams(BaseModel):
    """Search parameters for Listing Project scraper"""

    # TODO: restrict the available cities here
    city: str = Field(
        default="new-york-city",
        description="City slug (e.g., 'new-york-city', 'san-francisco')"
    )
    
    listing_type: Literal["sublets", "apartments", "rooms"] = Field(
        default="sublets",
        description="Type of listing to search for"
    )
    
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Page number for pagination"
    )
    
    max_pages: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Maximum number of pages to scrape"
    )
