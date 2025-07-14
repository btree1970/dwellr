import re
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.crawlers.base_crawler import BaseCrawler, CrawlResult
from src.database.db import get_db_session
from src.models.listing import Listing, ListingType, PricePeriod


class ListingProjectCrawlerConfig(BaseModel):
    # Credentials
    email: Optional[str] = Field(default=None, description="Email for authentication")
    password: Optional[str] = Field(
        default=None, description="Password for authentication"
    )

    # Crawling parameters
    supported_cities: List[str] = Field(
        default=["new-york-city"],
        description="List of city slugs to crawl (e.g., ['new-york-city', 'san-francisco'])",
    )
    listing_type: ListingType = Field(
        default=ListingType.SUBLET, description="Type of listing to search for"
    )
    max_pages: int = Field(
        default=5, ge=1, le=100, description="Maximum number of pages to scrape"
    )
    delay_between_pages: float = Field(
        default=1.0, ge=0, le=10, description="Seconds to wait between page fetches"
    )
    delay_between_listings: float = Field(
        default=0,
        ge=0,
        le=10,
        description="Seconds to wait between processing listings",
    )
    skip_errors: bool = Field(
        default=True, description="Continue if individual listing extraction fails"
    )

    # Optional pagination override
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Specific page number for pagination (overrides max_pages)",
    )


class ListingProject(BaseCrawler):
    """Scraper for Listing Project website"""

    BASE_URL = "https://www.listingsproject.com"

    def __init__(self, config: ListingProjectCrawlerConfig):
        self.session = requests.Session()
        self.authenticated = False

        self.config = config

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Authenticate if credentials provided
        if self.config.email and self.config.password:
            self.authenticated = self._login(self.config.email, self.config.password)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ListingProject":
        """
        Create ListingProject crawler from complete configuration dictionary

        Args:
            config: Complete configuration dictionary containing:
                - credentials: Dict with 'email' and 'password' keys
                - All crawling parameters (city, max_pages, delays, etc.)
                - Any other configuration

        Returns:
            Fully configured ListingProject instance ready to crawl
        """
        credentials = config.get("credentials", {})

        # Create typed config object from dictionary
        typed_config = ListingProjectCrawlerConfig(
            email=credentials.get("email"),
            password=credentials.get("password"),
            supported_cities=config.get("supported_cities", ["new-york-city"]),
            listing_type=config.get("listing_type", ListingType.SUBLET),
            max_pages=config.get("max_pages", 5),
            delay_between_pages=config.get("delay_between_pages", 1.0),
            delay_between_listings=config.get("delay_between_listings", 0),
            skip_errors=config.get("skip_errors", True),
            page=config.get("page"),
        )

        return cls(config=typed_config)

    def store_listings(
        self,
        city: str,
    ) -> Dict[str, int]:
        """Scrape listings and store via ListingService

        Args:
            city: A city to get listings of
        Returns:
            Dictionary with scraping statistics
        """

        stats = {
            "total_processed": 0,
            "new_listings": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "pages_processed": 0,
        }

        # Use configuration from stored typed config
        params = self.config

        # If specific page requested, just fetch that page
        if params.page:
            pages_to_fetch = [params.page]
        else:
            # Otherwise fetch from page 1 to max_pages
            pages_to_fetch = range(1, params.max_pages + 1)

        for page_num in pages_to_fetch:
            # Build URL - map enum values to website URL format
            listing_type_url = (
                "sublets" if params.listing_type == ListingType.SUBLET else "rentals"
            )
            url = f"{self.BASE_URL}/real-estate/{city}/{listing_type_url}"
            print(url)
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
                stats["errors"] += 1
                continue

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Find all listing card containers
            listing_containers: List[Tag] = [
                tag
                for tag in soup.find_all("div", class_="flex flex-col md:flex-row mb-6")
                if isinstance(tag, Tag)
            ]

            # If no listings found, we've probably reached the end
            if not listing_containers:
                print(f"No listings found on page {page_num}, stopping pagination")
                break

            stats["pages_processed"] += 1
            page_new_count = 0

            # Process listing containers
            for container in listing_containers:
                # Find the listing link within this container
                link = container.find("a", href=re.compile(r"^/listings/[^/]+$"))
                if not link or not isinstance(link, Tag):
                    continue

                href = link.get("href", "")
                listing_id = str(href).split("/")[-1] if href else None

                if not listing_id:
                    continue

                stats["total_processed"] += 1

                # Check if listing already exists in database (deduplication)
                with get_db_session() as db:
                    db: Session
                    existing_listing = (
                        db.query(Listing).filter(Listing.id == listing_id).first()
                    )
                    if existing_listing:
                        print(f"Skipping duplicate listing: {listing_id}")
                        stats["duplicates_skipped"] += 1
                        continue

                try:
                    # Extract data from the listing card container
                    listing_data = self._extract_listing_data(container)

                    if listing_data:
                        # Fetch additional details from the individual listing page
                        detail_data = self._fetch_and_extract_details(
                            f"{self.BASE_URL}{href}"
                        )

                        # Merge card data with detail data
                        if detail_data:
                            listing_data.update(detail_data)

                        # Create listing object
                        listing = Listing(
                            id=listing_id,
                            url=f"{self.BASE_URL}{href}",
                            title=listing_data.get("title", "No title"),
                            price=listing_data.get("price"),
                            price_period=listing_data.get("price_period"),
                            start_date=listing_data.get("start_date"),
                            end_date=listing_data.get("end_date"),
                            neighborhood=listing_data.get("neighborhood"),
                            brief_description=listing_data.get("description"),
                            full_description=listing_data.get("full_description"),
                            contact_name=listing_data.get("name"),
                            contact_email=listing_data.get("email"),
                            listing_type=ListingType.SUBLET,
                            source_site=self.get_source_name(),
                        )

                        # Store directly to database
                        try:
                            with get_db_session() as db:
                                db: Session
                                db.add(listing)
                                db.commit()
                                page_new_count += 1
                                stats["new_listings"] += 1
                                print(f"Stored listing: {listing_id}")
                        except Exception as e:
                            print(f"Failed to store listing {listing_id}: {e}")
                            stats["errors"] += 1

                        # Rate limiting between listings
                        if self.config.delay_between_listings > 0:
                            time.sleep(self.config.delay_between_listings)

                except Exception as e:
                    print(f"Error processing listing {listing_id}: {e}")
                    stats["errors"] += 1
                    if not self.config.skip_errors:
                        raise
                    # Continue to next listing if skip_errors is True

            print(
                f"Found {len(listing_containers)} containers on page {page_num}, stored {page_new_count} new listings"
            )

            # Rate limiting between pages (except for the last page)
            if page_num < max(pages_to_fetch) and self.config.delay_between_pages > 0:
                time.sleep(self.config.delay_between_pages)

        print(f"Scraping complete. Stats: {stats}")
        return stats

    def _extract_listing_data(self, listing_element: Any) -> Optional[Dict[str, Any]]:
        """Extract data from a listing card element (the <a> tag containing all card info)"""
        try:
            # Extract title from h4 tag
            title = None
            h4 = listing_element.find("h4")
            if h4:
                title = h4.get_text(strip=True)

            # Get all text content for parsing
            full_text = listing_element.get_text(" ", strip=True)

            # Extract price using element selectors
            price, price_period = self._extract_price_from_element(listing_element)

            # Extract dates using element selectors
            start_date, end_date = self._extract_dates_from_element(listing_element)

            # Extract neighborhood from title
            neighborhood = self._extract_neighborhood_form_element(listing_element)

            # Brief description (text after filtering out structured data)
            description = self._extract_brief_description(
                listing_element, title, full_text
            )

            return {
                "title": title,
                "price": price,
                "price_period": price_period,
                "start_date": start_date,
                "end_date": end_date,
                "neighborhood": neighborhood,
                "description": description,
            }

        except Exception as e:
            print(f"Error extracting listing data: {e}")
            return None

    def _extract_neighborhood_form_element(self, element: Any) -> str:
        """Extract neigboorhood information from element"""
        elem = element.select_one("div.text-grey-dark.font-semibold.text-smish")
        if elem is None:
            return ""
        text = elem.get_text(strip=True).split("|")[0]
        return "".join(text.split())

    def _extract_price_from_element(
        self, element: Any
    ) -> tuple[Optional[float], Optional[Any]]:
        """Extract price from specific elements in the listing card"""
        # Look for text containing $ symbol in any element
        for text_elem in element.find_all(string=re.compile(r"\$")):
            text = str(text_elem).strip()
            price_match = re.search(
                r"\$\s?([\d,]+)(?:\s?/\s?(month|mo|week|wk|day|night))?",
                text,
                re.IGNORECASE,
            )

            if price_match:
                price_str = price_match.group(1).replace(",", "")
                period = price_match.group(2) if price_match.group(2) else "month"

                try:
                    price = float(price_str)
                    original_period = period.lower()

                    # Normalize to monthly price
                    if original_period in ["day", "night"]:
                        return price, PricePeriod.DAY
                    elif original_period in ["week", "wk"]:
                        return price, PricePeriod.WEEK
                    else:
                        return price, PricePeriod.MONTH

                except ValueError:
                    continue

        return None, None

    def _extract_dates_from_element(
        self, element: Any
    ) -> tuple[Optional[Any], Optional[Any]]:
        """Extract dates from the specific date span element"""
        from dateutil import parser

        # Look for the specific date span with bg-teal-light class
        full_text = element.get_text(" ", strip=True)
        if full_text:
            # Look for date range pattern: "July 1, 2025 - August 26, 2025"
            date_range_pattern = (
                r"([A-Za-z]+ \d{1,2},? \d{4})\s*[-–]\s*([A-Za-z]+ \d{1,2},? \d{4})"
            )
            match = re.search(date_range_pattern, full_text)

            if match:
                try:
                    start_date = parser.parse(match.group(1))
                    end_date = parser.parse(match.group(2))
                    return start_date, end_date
                except Exception:
                    pass

        return None, None

    def _extract_brief_description(
        self, element: Any, title: Optional[str], full_text: str
    ) -> Optional[str]:
        """Extract brief description from listing card"""
        # Get all text strings from the element
        text_parts: list[str] = []

        for text in element.stripped_strings:
            text = text.strip()
            if not text:
                continue

            # Skip if it's the title
            if title and text == title:
                continue
            # Skip if it looks like price
            if "$" in text:
                continue
            # Skip if it looks like a date (contains 4-digit year)
            if re.search(r"\b20\d{2}\b", text):
                continue
            # Skip very short fragments
            if len(text) < 10:
                continue

            text_parts.append(text)

        # Join and clean up
        description = " ".join(text_parts)

        # Remove extra whitespace
        description = re.sub(r"\s+", " ", description).strip()

        # Truncate if too long
        if len(description) > 200:
            description = description[:197] + "..."

        return description if description and len(description) > 20 else None

    def _fetch_and_extract_details(self, listing_url: str) -> Dict[str, Any]:
        """Fetch individual listing page and extract detailed information"""
        try:
            print(f"Fetching details from: {listing_url}")

            # Fetch the individual listing page
            response = self.session.get(listing_url, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            div = soup.find("div", class_="text-grey-darkest")

            # Extract full description using html_to_clean_text for LLM processing
            full_description = div.getText(" ", strip=True) if div else ""

            name = None
            email = None

            name_div = soup.find("strong", string="Name:")
            if name_div:
                name_span = name_div.find_next_sibling("span")
                if name_span:
                    name = name_span.get_text(strip=True)

            email_link = soup.find("a", class_="contact__a")
            if email_link:
                email = email_link.get_text(strip=True)

            return {
                "full_description": full_description,
                "detail_fetched": True,
                "name": name,
                "email": email,
            }

        except Exception as e:
            print(f"Error fetching details from {listing_url}: {e}")
            return {"detail_fetched": False}

    def _login(self, email: str, password: str) -> bool:
        """Authenticate with the Listings Project website"""
        try:
            print(f"Attempting to login with email: {email}")

            # Step 1: Get login page to extract CSRF token
            login_page_url = f"{self.BASE_URL}/user_sessions"
            response = self.session.get(login_page_url)
            response.raise_for_status()

            # Parse the login page to extract authenticity token
            soup = BeautifulSoup(response.text, "html.parser")
            token_input = soup.find("input", {"name": "authenticity_token"})

            if not token_input or not isinstance(token_input, Tag):
                print("Could not find authenticity token on login page")
                return False

            authenticity_token = token_input.get("value")
            if isinstance(authenticity_token, list):
                authenticity_token = authenticity_token[0] if authenticity_token else ""
            elif authenticity_token is None:
                authenticity_token = ""

            print(f"Extracted authenticity token: {authenticity_token[:20]}...")

            # Step 2: Submit login credentials
            login_data: Dict[str, str] = {
                "authenticity_token": authenticity_token,
                "user_session[email]": email,
                "user_session[wants_to]": "signin",
                "user_session[password]": password,
                "commit": "Next",
            }

            response = self.session.post(login_page_url, data=login_data)

            # Step 3: Check if login was successful
            # Successful login should redirect (status 302) or return 200 with no error messages
            if response.status_code in [200, 302]:
                # Check if we got authentication cookies
                if "user_credentials" in self.session.cookies:
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

    def crawl(self) -> CrawlResult:
        try:
            total_stats = {
                "total_processed": 0,
                "new_listings": 0,
                "duplicates_skipped": 0,
                "errors": 0,
                "pages_processed": 0,
            }

            for city in self.config.supported_cities:
                city_stats = self.store_listings(
                    city=city,
                )

                for key in total_stats:
                    total_stats[key] += city_stats.get(key, 0)

                print(
                    f"Completed crawl for {city}: {city_stats.get('new_listings', 0)} new listings"
                )

            stats = total_stats

            return CrawlResult(
                source=self.get_source_name(),
                total_processed=stats.get("total_processed", 0),
                new_listings=stats.get("new_listings", 0),
                duplicates_skipped=stats.get("duplicates_skipped", 0),
                errors=stats.get("errors", 0),
                pages_processed=stats.get("pages_processed", 0),
                success=stats.get("errors", 0) == 0,
                error_message=None,
            )

        except Exception as e:
            return CrawlResult(
                source=self.get_source_name(),
                total_processed=0,
                new_listings=0,
                duplicates_skipped=0,
                errors=1,
                pages_processed=0,
                success=False,
                error_message=str(e),
            )

    def get_source_name(self) -> str:
        return "listing_project"
