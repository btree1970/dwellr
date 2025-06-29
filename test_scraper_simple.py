from src.scrapers.listing_project_scraper import ListingProjectScraper
import json
import os

from dotenv import load_dotenv

load_dotenv()


def main():
    email = os.getenv('LISTINGS_EMAIL')
    password = os.getenv('LISTINGS_PASSWORD')

    scraper = ListingProjectScraper(email=email, password=password)
    
    print("Testing listing extraction...")
    
    listings = scraper.get_listings(city="new-york-city", listing_type="sublets", max_pages = 1)

    print(f'Found {len(listings)} listings')

    for listing in listings[:5]:
        print(json.dumps(listing.to_dict(), indent=2))

    

if __name__ == "__main__":
    main()
