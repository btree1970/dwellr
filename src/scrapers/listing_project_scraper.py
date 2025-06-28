from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import re

from ..models.listing import Listing, ListingType
from ..models.search_params import ListingProjectSearchParams

class ListingProjectScraper():
    """Scraper for Listing Project website"""
    
    BASE_URL = "https://www.listingsproject.com"

    def __init__(self):
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    
    @property
    def source_name(self) -> str:
        return "listing_project"
    
    def get_listings(self, **search_params) -> List[Listing]:
        """Scrape listings from the website"""
        # Parse search parameters
        params = ListingProjectSearchParams(**search_params)
        
        all_listings = []
        seen_ids = set()  # Track unique listing IDs
        
        # If specific page requested, just fetch that page
        if params.page:
            pages_to_fetch = [params.page]
        else:
            # Otherwise fetch from page 1 to max_pages
            pages_to_fetch = range(1, params.max_pages + 1)
        
        for page_num in pages_to_fetch:
            # Build URL
            url = f"{self.BASE_URL}/real-estate/{params.city}/{params.listing_type}"
            if page_num > 1:
                url += f"?page={page_num}"
            
            print(f"Fetching page {page_num}: {url}")
            
            # Fetch the page
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                html = response.text
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                continue
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all listing card containers
            listing_containers = soup.find_all('div', class_=re.compile(r'flex.*mb-6'))
            
            
            # If no listings found, we've probably reached the end
            if not listing_containers:
                print(f"No listings found on page {page_num}, stopping pagination")
                break
            
            # Convert to Listing objects
            page_new_count = 0
            for container in listing_containers:
                # Find the listing link within this container
                link = container.find('a', href=re.compile(r'^/listings/[^/]+$'))
                if not link:
                    continue
                    
                href = link.get('href', '')
                listing_id = href.split('/')[-1] if href else None
                
                if listing_id and listing_id not in ['listings', ''] and listing_id not in seen_ids:
                    seen_ids.add(listing_id)
                    
                    # Extract data from the listing card container
                    listing_data = self._extract_listing_data(container)
                    
                    if listing_data:
                        # Fetch additional details from the individual listing page
                        detail_data = self._fetch_and_extract_details(f"{self.BASE_URL}{href}")
                        
                        # Merge card data with detail data
                        if detail_data:
                            listing_data.update(detail_data)
                        page_new_count += 1
                        listing = Listing(
                            id=listing_id,
                            url=f"{self.BASE_URL}{href}",
                            title=listing_data.get('title', 'No title'),
                            price=listing_data.get('price'),
                            price_period=listing_data.get('price_period'),
                            start_date=listing_data.get('start_date'),
                            end_date=listing_data.get('end_date'),
                            neighborhood=listing_data.get('neighborhood'),
                            brief_description=listing_data.get('description'),
                            full_description=listing_data.get('full_description'),
                            listing_type=ListingType.SUBLET,
                            source_site=self.source_name,
                            detail_fetched=listing_data.get('detail_fetched', False)
                        )
                        all_listings.append(listing)
            
            print(f"Found {len(listing_containers)} containers on page {page_num}, added {page_new_count} new unique listings")
        
        return all_listings
    
    def _extract_listing_data(self, listing_element) -> dict:
        """Extract data from a listing card element (the <a> tag containing all card info)"""
        try:
            # Extract title from h4 tag
            title = None
            h4 = listing_element.find('h4')
            if h4:
                title = h4.get_text(strip=True)
            
            # Get all text content for parsing
            full_text = listing_element.get_text(' ', strip=True)
            
            # Extract price using element selectors
            price, price_period = self._extract_price_from_element(listing_element)
            
            # Extract dates using element selectors
            start_date, end_date = self._extract_dates_from_element(listing_element)
            
            # Extract neighborhood from title
            neighborhood = self._extract_neighborhood_form_element(listing_element)
            
            # Brief description (text after filtering out structured data)
            description = self._extract_brief_description(listing_element, title, full_text)
            
            return {
                'title': title,
                'price': price,
                'price_period': price_period,
                'start_date': start_date,
                'end_date': end_date,
                'neighborhood': neighborhood,
                'description': description
            }
            
        except Exception as e:
            print(f"Error extracting listing data: {e}")
            return None
    
    def _extract_price(self, text: str) -> tuple:
        """Extract price from text and normalize to monthly rate"""
        # Match patterns like $3,200/month, $150/day, $800/week
        price_pattern = r'\$\s?([\d,]+)(?:\s?/\s?(month|mo|week|wk|day|night))?'
        price_match = re.search(price_pattern, text, re.IGNORECASE)
        
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            period = price_match.group(2) if price_match.group(2) else 'month'

            try:
                price = float(price_str)
                original_period = period.lower()
                
                if original_period in ['day', 'night']:
                    return price, 'day'
                elif original_period in ['week', 'wk']:
                    return price, 'week'
                else:
                    # Already monthly
                    return price, 'month'
                    
            except ValueError:
                pass
        
        return None, None

    def _extract_neighborhood_form_element(self, element) -> str:
        """Extract neigboorhood information from element"""
        elem = element.select_one('div.text-grey-dark.font-semibold.text-smish')
        text = elem.get_text(strip=True).split('|')[0]
        return ''.join(text.split())

    
    def _extract_price_from_element(self, element) -> tuple:
        """Extract price from specific elements in the listing card"""
        # Look for text containing $ symbol in any element
        for text_elem in element.find_all(string=re.compile(r'\$')):
            text = str(text_elem).strip()
            price_match = re.search(r'\$\s?([\d,]+)(?:\s?/\s?(month|mo|week|wk|day|night))?', text, re.IGNORECASE)
            
            if price_match:
                price_str = price_match.group(1).replace(',', '')
                period = price_match.group(2) if price_match.group(2) else 'month'
                
                try:
                    price = float(price_str)
                    original_period = period.lower()
                    
                    # Normalize to monthly price
                    if original_period in ['day', 'night']:
                        return price, 'day'
                    elif original_period in ['week', 'wk']:
                        return price, 'week'
                    else:
                        return price, 'month'
                        
                except ValueError:
                    continue
        
        return None, None
    
    def _extract_dates_from_element(self, element) -> tuple:
        """Extract dates from the specific date span element"""
        from dateutil import parser
        
        # Look for the specific date span with bg-teal-light class
        full_text = element.get_text(' ', strip=True)
        if full_text:
            
            # Look for date range pattern: "July 1, 2025 - August 26, 2025"
            date_range_pattern = r'([A-Za-z]+ \d{1,2},? \d{4})\s*[-–]\s*([A-Za-z]+ \d{1,2},? \d{4})'
            match = re.search(date_range_pattern, full_text)
            
            if match:
                try:
                    start_date = parser.parse(match.group(1))
                    end_date = parser.parse(match.group(2))
                    return start_date, end_date
                except:
                    pass
        
        return None, None
    
    def _extract_neighborhood_from_title(self, title: str) -> Optional[str]:
        """Extract neighborhood from title - text before |"""
        if not title or '|' not in title:
            return None
            
        neighborhood = title.split('|')[0].strip()
        return neighborhood if neighborhood else None
    
    def _extract_brief_description(self, element, title, full_text) -> str:
        """Extract brief description from listing card"""
        # Get all text strings from the element
        text_parts = []
        
        for text in element.stripped_strings:
            text = text.strip()
            if not text:
                continue
                
            # Skip if it's the title
            if title and text == title:
                continue
            # Skip if it looks like price
            if '$' in text:
                continue
            # Skip if it looks like a date (contains 4-digit year)
            if re.search(r'\b20\d{2}\b', text):
                continue
            # Skip very short fragments
            if len(text) < 10:
                continue
                
            text_parts.append(text)
        
        # Join and clean up
        description = ' '.join(text_parts)
        
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Truncate if too long
        if len(description) > 200:
            description = description[:197] + '...'
        
        return description if description and len(description) > 20 else None
    
    def _fetch_and_extract_details(self, listing_url: str) -> dict:
        """Fetch individual listing page and extract detailed information"""
        try:
            print(f"Fetching details from: {listing_url}")
            
            # Fetch the individual listing page
            response = self.session.get(listing_url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            div = soup.find('div', class_='text-grey-darkest')          

            # Extract full description using html_to_clean_text for LLM processing
            full_description = div.getText(" ", strip=True)
            
            # Extract any additional details that might be on the page
            # For now, we'll just get the cleaned full content
            return {
                'full_description': full_description,
                'detail_fetched': True
            }
            
        except Exception as e:
            print(f"Error fetching details from {listing_url}: {e}")
            return {
                'detail_fetched': False
            }
