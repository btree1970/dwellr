from datetime import datetime, timezone

from src.models.listing import Listing, ListingType, PricePeriod
from src.models.user import User


def create_equivalent_price_test_listings():
    """Create test listings with known price relationships for testing"""
    return [
        # Equivalent set 1: $150/day = $1050/week = $4500/month
        Listing(
            id="equiv_daily_1",
            url="https://test.com/d1",
            title="Daily 150",
            price=150.0,
            price_period=PricePeriod.DAY,
            start_date=datetime(2025, 8, 1),
            end_date=datetime(2025, 9, 1),
            listing_type=ListingType.SUBLET,
        ),
        Listing(
            id="equiv_weekly_1",
            url="https://test.com/w1",
            title="Weekly 1050",
            price=1050.0,
            price_period=PricePeriod.WEEK,
            start_date=datetime(2025, 8, 1),
            end_date=datetime(2025, 9, 1),
            listing_type=ListingType.SUBLET,
        ),
        Listing(
            id="equiv_monthly_1",
            url="https://test.com/m1",
            title="Monthly 4500",
            price=4500.0,
            price_period=PricePeriod.MONTH,
            start_date=datetime(2025, 8, 1),
            end_date=datetime(2025, 9, 1),
            listing_type=ListingType.SUBLET,
        ),
        # Equivalent set 2: $100/day = $700/week = $3000/month
        Listing(
            id="equiv_daily_2",
            url="https://test.com/d2",
            title="Daily 100",
            price=100.0,
            price_period=PricePeriod.DAY,
            start_date=datetime(2025, 8, 1),
            end_date=datetime(2025, 9, 1),
            listing_type=ListingType.SUBLET,
        ),
        Listing(
            id="equiv_weekly_2",
            url="https://test.com/w2",
            title="Weekly 700",
            price=700.0,
            price_period=PricePeriod.WEEK,
            start_date=datetime(2025, 8, 1),
            end_date=datetime(2025, 9, 1),
            listing_type=ListingType.SUBLET,
        ),
        Listing(
            id="equiv_monthly_2",
            url="https://test.com/m2",
            title="Monthly 3000",
            price=3000.0,
            price_period=PricePeriod.MONTH,
            start_date=datetime(2025, 8, 1),
            end_date=datetime(2025, 9, 1),
            listing_type=ListingType.SUBLET,
        ),
        # Expensive option: $200/day = $1400/week = $6000/month
        Listing(
            id="expensive_daily",
            url="https://test.com/exp",
            title="Expensive",
            price=200.0,
            price_period=PricePeriod.DAY,
            start_date=datetime(2025, 8, 1),
            end_date=datetime(2025, 9, 1),
            listing_type=ListingType.SUBLET,
        ),
    ]


def create_test_users():
    """Create test users with different price preferences and durations"""
    return [
        # User with monthly preferences
        User(
            id="user_monthly",
            name="Monthly User",
            min_price=3000.0,
            max_price=5000.0,
            price_period=PricePeriod.MONTH,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 9, 1),  # 31 days
            preferred_listing_type=ListingType.SUBLET,
            date_flexibility_days=0,
        ),
        # User with daily preferences
        User(
            id="user_daily",
            name="Daily User",
            min_price=100.0,
            max_price=175.0,
            price_period=PricePeriod.DAY,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 8, 15),  # 14 days
            preferred_listing_type=ListingType.SUBLET,
            date_flexibility_days=0,
        ),
        # User with weekly preferences
        User(
            id="user_weekly",
            name="Weekly User",
            min_price=700.0,
            max_price=1200.0,
            price_period=PricePeriod.WEEK,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 8, 22),  # 21 days
            preferred_listing_type=ListingType.SUBLET,
            date_flexibility_days=0,
        ),
        # User with date flexibility
        User(
            id="user_flexible",
            name="Flexible User",
            min_price=2500.0,
            max_price=4500.0,
            price_period=PricePeriod.MONTH,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 9, 1),
            preferred_listing_type=ListingType.SUBLET,
            date_flexibility_days=5,  # 5 days flexibility
        ),
    ]


def create_simple_listing(
    listing_id: str, price: float, period: PricePeriod
) -> Listing:
    """Create a simple listing for unit testing"""
    return Listing(
        id=listing_id,
        url=f"https://test.com/{listing_id}",
        title=f"Test Listing {listing_id}",
        price=price,
        price_period=period,
        start_date=datetime(2025, 8, 1),
        end_date=datetime(2025, 9, 1),
        listing_type=ListingType.SUBLET,
    )


def create_simple_user(
    user_id: str,
    min_price: float,
    max_price: float,
    period: PricePeriod,
    duration_days: int,
) -> User:
    """Create a simple user for unit testing"""
    start_date = datetime(2025, 8, 1)
    end_date = datetime(2025, 8, 1 + duration_days)

    return User(
        id=user_id,
        name=f"Test User {user_id}",
        min_price=min_price,
        max_price=max_price,
        price_period=period,
        preferred_start_date=start_date,
        preferred_end_date=end_date,
        preferred_listing_type=ListingType.SUBLET,
        date_flexibility_days=0,
    )


def create_user_with_credits(
    name: str = "Test User",
    credits: float = 5.00,
    preference_profile: str = "Looking for apartments",
    **kwargs,
) -> User:
    """Create a user with evaluation credits - flexible for different test scenarios"""
    user_data = {
        "name": name,
        "evaluation_credits": credits,
        "preference_profile": preference_profile,
    }
    user_data.update(kwargs)  # Allow any additional User fields
    return User(**user_data)


def create_standard_listing(
    title: str = "Test Listing",
    price: float = 800.0,
    price_period: PricePeriod = PricePeriod.MONTH,
    listing_type: ListingType = ListingType.RENTAL,
    source_site: str = "test_source",
    **kwargs,
) -> Listing:
    """Create a standard listing - flexible for different test scenarios"""
    listing_data = {
        "id": f"test_{hash(title) % 10000}",
        "url": f"https://test.com/listing/{hash(title) % 10000}",
        "title": title,
        "price": price,
        "price_period": price_period,
        "listing_type": listing_type,
        "start_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "end_date": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "source_site": source_site,
    }
    listing_data.update(kwargs)  # Allow any additional Listing fields
    return Listing(**listing_data)


def create_multiple_listings(
    count: int = 3, base_price: float = 800.0
) -> list[Listing]:
    """Create multiple listings with varying prices for testing"""
    listings = []
    for i in range(count):
        listings.append(
            create_standard_listing(
                title=f"Apartment {i + 1}",
                price=base_price + (i * 100),
                source_site=f"multi_test_{i + 1}",
            )
        )
    return listings
