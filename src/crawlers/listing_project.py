from typing import List, Optional, Generator
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import re
import time


from src.models.listing import Listing, ListingType
from src.models.search_params import ListingProjectSearchParams
from src.database.db import get_db_session

class ListingProject():
    """Scraper for Listing Project website"""
    
    BASE_URL = "https://www.listingsproject.com"

    def __init__(self, email=None, password=None):
        self.session = requests.Session()
        self.authenticated = False

        # Set default headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Authenticate if credentials provided
        if email and password:
         self.authenticated = self._login(email, password)
        
    
    @property
    def source_name(self) -> str:
        return "listing_project"
    
    
    def store_listings(self, delay_between_listings: float = 0, delay_between_pages: float = 1, 
                      skip_errors: bool = True, **search_params) -> dict:
        """Scrape listings and store via ListingService
        
        Args:
            delay_between_listings: Seconds to wait between processing listings (default: 0)
            delay_between_pages: Seconds to wait between page fetches (default: 1)
            skip_errors: Continue if individual listing extraction fails (default: True)
            **search_params: Search parameters for ListingProjectSearchParams
            
        Returns:
            Dictionary with scraping statistics
        """
        
        stats = {
            'total_processed': 0,
            'new_listings': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'pages_processed': 0
        }
        
        # Parse search parameters
        params = ListingProjectSearchParams(**search_params)
        
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
                stats['errors'] += 1
                continue
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all listing card containers
            listing_containers = soup.find_all('div', class_='flex flex-col md:flex-row mb-6')
            
            # If no listings found, we've probably reached the end
            if not listing_containers:
                print(f"No listings found on page {page_num}, stopping pagination")
                break
            
            stats['pages_processed'] += 1
            page_new_count = 0
            
            # Process listing containers
            for container in listing_containers:
                # Find the listing link within this container
                link = container.find('a', href=re.compile(r'^/listings/[^/]+$'))
                if not link:
                    continue
                    
                href = link.get('href', '')
                listing_id = href.split('/')[-1] if href else None
                
                if not listing_id:
                    continue
                
                stats['total_processed'] += 1
                
                # Check if listing already exists in database (deduplication)
                with get_db_session() as db:
                    existing_listing = db.query(Listing).filter(Listing.id == listing_id).first()
                    if existing_listing:
                        print(f"Skipping duplicate listing: {listing_id}")
                        stats['duplicates_skipped'] += 1
                        continue
                    
                try:
                    # Extract data from the listing card container
                    listing_data = self._extract_listing_data(container)
                    
                    if listing_data:
                        # Fetch additional details from the individual listing page
                        detail_data = self._fetch_and_extract_details(f"{self.BASE_URL}{href}")
                        
                        # Merge card data with detail data
                        if detail_data:
                            listing_data.update(detail_data)
                        
                        # Create listing object
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
                            contact_name=listing_data.get('name'),
                            contact_email=listing_data.get('email'),
                            listing_type=ListingType.SUBLET,
                            source_site=self.source_name,
                        )
                        
                        # Store directly to database
                        try:
                            with get_db_session() as db:
                                db.add(listing)
                                db.commit()
                                page_new_count += 1
                                stats['new_listings'] += 1
                                print(f"Stored listing: {listing_id}")
                        except Exception as e:
                            print(f"Failed to store listing {listing_id}: {e}")
                            stats['errors'] += 1
                        
                        # Rate limiting between listings
                        if delay_between_listings > 0:
                            time.sleep(delay_between_listings)
                            
                except Exception as e:
                    print(f"Error processing listing {listing_id}: {e}")
                    stats['errors'] += 1
                    if not skip_errors:
                        raise
                    # Continue to next listing if skip_errors is True
            
            print(f"Found {len(listing_containers)} containers on page {page_num}, stored {page_new_count} new listings")
            
            # Rate limiting between pages (except for the last page)
            if page_num < max(pages_to_fetch) and delay_between_pages > 0:
                time.sleep(delay_between_pages)
        
        print(f"Scraping complete. Stats: {stats}")
        return stats
    
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
    
    def _normalize_price_to_monthly(self, price: Optional[float], price_period: Optional[str]) -> Optional[float]:
        """Convert price to monthly equivalent for filtering
        
        Args:
            price: The original price
            price_period: The period (day, week, month)
            
        Returns:
            Monthly equivalent price
        """
        if not price or not price_period:
            return price
            
        period = price_period.lower()
        
        if period in ['day', 'night']:
            return price * 30  # Approximate monthly conversion
        elif period in ['week', 'wk']:
            return price * 4.33  # Average weeks per month
        else:
            # Already monthly
            return price
    
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

            divs = soup.find_all('div', class_='mb-2')

            name = None
            email = None

            name_div = soup.find('strong', string='Name:')
            if name_div:
                name_span = name_div.find_next_sibling('span')
                if name_span:
                    name = name_span.get_text(strip=True)

            email_link = soup.find('a', class_='contact__a')
            if email_link:
                email = email_link.get_text(strip=True)



            
            # Extract any additional details that might be on the page
            # For now, we'll just get the cleaned full content
            return {
                'full_description': full_description,
                'detail_fetched': True,
                'name': name,
                'email': email
            }
            
        except Exception as e:
            print(f"Error fetching details from {listing_url}: {e}")
            return {
                'detail_fetched': False
            }
    
    def _login(self, email: str, password: str) -> bool:
        """Authenticate with the Listings Project website"""
        try:
            print(f"Attempting to login with email: {email}")
            
            # Step 1: Get login page to extract CSRF token
            login_page_url = f"{self.BASE_URL}/user_sessions"
            response = self.session.get(login_page_url)
            response.raise_for_status()
            
            # Parse the login page to extract authenticity token
            soup = BeautifulSoup(response.text, 'html.parser')
            token_input = soup.find('input', {'name': 'authenticity_token'})
            
            if not token_input:
                print("Could not find authenticity token on login page")
                return False
            
            authenticity_token = token_input.get('value')
            print(f"Extracted authenticity token: {authenticity_token[:20]}...")
            
            # Step 2: Submit login credentials
            login_data = {
                'authenticity_token': authenticity_token,
                'user_session[email]': email,
                'user_session[wants_to]': 'signin',
                'user_session[password]': password,
                'commit': 'Next'
            }
            
            response = self.session.post(login_page_url, data=login_data)
            
            # Step 3: Check if login was successful
            # Successful login should redirect (status 302) or return 200 with no error messages
            if response.status_code in [200, 302]:
                # Check if we got authentication cookies
                if 'user_credentials' in self.session.cookies:
                    print("Login successful - authentication cookies received")
                    return True
                else:
                    print("Login may have failed - no user_credentials cookie found")
                    return False
            else:
                print(f"Login failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
