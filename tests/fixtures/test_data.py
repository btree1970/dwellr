"""Reusable test data for price normalization and date flexibility tests"""

from datetime import datetime

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
            scraped_at=datetime.utcnow(),
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
            scraped_at=datetime.utcnow(),
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
            scraped_at=datetime.utcnow(),
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
            scraped_at=datetime.utcnow(),
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
            scraped_at=datetime.utcnow(),
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
            scraped_at=datetime.utcnow(),
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
            scraped_at=datetime.utcnow(),
        ),
    ]


def create_test_users():
    """Create test users with different price preferences and durations"""
    return [
        # User with monthly preferences
        User(
            id="user_monthly",
            name="Monthly User",
            email="monthly@test.com",
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
            email="daily@test.com",
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
            email="weekly@test.com",
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
            email="flexible@test.com",
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
        scraped_at=datetime.utcnow(),
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
        email=f"{user_id}@test.com",
        min_price=min_price,
        max_price=max_price,
        price_period=period,
        preferred_start_date=start_date,
        preferred_end_date=end_date,
        preferred_listing_type=ListingType.SUBLET,
        date_flexibility_days=0,
    )
