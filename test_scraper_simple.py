from src.crawlers.listing_project import ListingProject
from src.database.db import db_manager 


from src.config import settings


def main():

    db_manager.init_db()

    scraper = ListingProject(email=settings.listings_email, password=settings.listings_password)
    
    print("Testing listing extraction...")
    
    listings = scraper.store_listings(city="new-york-city", listing_type="sublets", max_pages = 1)

    print(f'Found {len(listings)} listings')


    

if __name__ == "__main__":
    main()
