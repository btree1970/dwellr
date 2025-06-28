from src.scrapers.listing_project_scraper import ListingProjectScraper
import json


def main():
    scraper = ListingProjectScraper()
    
    print("Testing listing extraction...")
    
    listings = scraper.get_listings(city="new-york-city", listing_type="sublets", max_pages = 2)

    print(f'Found {len(listings)} listings')

    for listing in listings[:5]:
        print(json.dumps(listing.to_dict(), indent=2))

    

if __name__ == "__main__":
    main()
