from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from ..models.listing import Listing


class BaseScraper(ABC):
    def __init__(self, 
                 rate_limit_seconds: float = 1.0,
                 max_retries: int = 3,
                 timeout: int = 30):
        self.rate_limit_seconds = rate_limit_seconds
        self.max_retries = max_retries
        self.timeout = timeout
        self.last_request_time = 0
        self.session = requests.Session()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the source website"""
        pass
    
    @abstractmethod
    def parse_listing(self, listing_element: Any) -> Optional[Listing]:
        """Parse a single listing element into a Listing object"""
        pass
    
    @abstractmethod
    def get_listing_elements(self, soup: BeautifulSoup) -> List[Any]:
        """Extract all listing elements from the page"""
        pass
    
    @abstractmethod
    def build_search_url(self, **kwargs) -> str:
        """Build the search URL with given parameters"""
        pass
    
    def _respect_rate_limit(self):
        """Ensure we don't make requests too quickly"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_seconds:
            sleep_time = self.rate_limit_seconds - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retries and error handling"""
        for attempt in range(self.max_retries):
            try:
                self._respect_rate_limit()
                
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                return response.text
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error fetching {url} (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
                    return None
    
    def scrape(self, **search_params) -> List[Listing]:
        """Main scraping method"""
        listings = []
        
        # Build search URL
        url = self.build_search_url(**search_params)
        self.logger.info(f"Scraping {url}")
        
        # Fetch page
        html = self._fetch_page(url)
        if not html:
            return listings
        
        # Parse page
        soup = BeautifulSoup(html, 'html.parser')
        listing_elements = self.get_listing_elements(soup)
        
        self.logger.info(f"Found {len(listing_elements)} listings")
        
        # Parse each listing
        for element in listing_elements:
            try:
                listing = self.parse_listing(element)
                if listing:
                    listing.source_site = self.source_name
                    listings.append(listing)
            except Exception as e:
                self.logger.error(f"Error parsing listing: {e}")
                continue
        
        self.logger.info(f"Successfully parsed {len(listings)} listings")
        return listings
    
    def scrape_multiple_pages(self, pages: int = 1, **search_params) -> List[Listing]:
        """Scrape multiple pages of results"""
        all_listings = []
        
        for page in range(1, pages + 1):
            self.logger.info(f"Scraping page {page}")
            search_params['page'] = page
            listings = self.scrape(**search_params)
            all_listings.extend(listings)
            
            if not listings:  # No more results
                break
        
        return all_listings