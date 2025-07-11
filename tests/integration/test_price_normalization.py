"""Integration tests for price normalization and filtering"""

from datetime import datetime

from src.database.db import get_db_session
from src.models.listing import Listing, ListingType, PricePeriod
from src.models.user import User
from src.services.listing_agent import ListingAgent


class TestPriceNormalizationIntegration:
    """Test complete price normalization workflow with database"""

    def test_monthly_user_filtering(self, db_with_test_data):
        """Test filtering for user with monthly price preferences"""
        with get_db_session() as db:
            monthly_user = db.query(User).filter_by(id="user_monthly").first()
            agent = ListingAgent(db=db, evaluator=None)

            candidates = agent._get_candidate_listings(monthly_user)
            candidate_ids = [listing.id for listing in candidates]

            # Monthly user: $3000-5000/month for 31 days
            # Expected total costs for 31 days:
            # - equiv_daily_1: $150 * 31 = $4650 ✓
            # - equiv_weekly_1: $1050 * (31/7) = $4650 ✓
            # - equiv_monthly_1: $4500 * (31/30) = $4650 ✓
            # - equiv_daily_2: $100 * 31 = $3100 ✓
            # - equiv_weekly_2: $700 * (31/7) = $3100 ✓
            # - equiv_monthly_2: $3000 * (31/30) = $3100 ✓
            # - expensive_daily: $200 * 31 = $6200 ✗ (too expensive)

            expected_ids = [
                "equiv_daily_1",
                "equiv_weekly_1",
                "equiv_monthly_1",
                "equiv_daily_2",
                "equiv_weekly_2",
                "equiv_monthly_2",
            ]

            assert len(candidates) == 6, f"Expected 6 candidates, got {len(candidates)}"
            assert set(candidate_ids) == set(
                expected_ids
            ), f"Expected {expected_ids}, got {candidate_ids}"

    def test_daily_user_filtering(self, db_with_test_data):
        """Test filtering for user with daily price preferences"""
        with get_db_session() as db:
            daily_user = db.query(User).filter_by(id="user_daily").first()
            agent = ListingAgent(db=db)

            candidates = agent._get_candidate_listings(daily_user)
            candidate_ids = [listing.id for listing in candidates]

            # Daily user: $100-175/day for 14 days
            # Expected total costs for 14 days:
            # - equiv_daily_1: $150 * 14 = $2100 ✓
            # - equiv_weekly_1: $1050 * (14/7) = $2100 ✓
            # - equiv_monthly_1: $4500 * (14/30) = $2100 ✓
            # - equiv_daily_2: $100 * 14 = $1400 ✓
            # - equiv_weekly_2: $700 * (14/7) = $1400 ✓
            # - equiv_monthly_2: $3000 * (14/30) = $1400 ✓
            # - expensive_daily: $200 * 14 = $2800 ✗ (too expensive)

            expected_ids = [
                "equiv_daily_1",
                "equiv_weekly_1",
                "equiv_monthly_1",
                "equiv_daily_2",
                "equiv_weekly_2",
                "equiv_monthly_2",
            ]

            assert len(candidates) == 6, f"Expected 6 candidates, got {len(candidates)}"
            assert set(candidate_ids) == set(
                expected_ids
            ), f"Expected {expected_ids}, got {candidate_ids}"

    def test_weekly_user_filtering(self, db_with_test_data):
        """Test filtering for user with weekly price preferences"""
        with get_db_session() as db:
            weekly_user = db.query(User).filter_by(id="user_weekly").first()
            agent = ListingAgent(db=db)

            candidates = agent._get_candidate_listings(weekly_user)
            candidate_ids = [listing.id for listing in candidates]

            # Weekly user: $700-1200/week for 21 days
            # Expected total costs for 21 days:
            # - equiv_daily_1: $150 * 21 = $3150 ✓
            # - equiv_weekly_1: $1050 * (21/7) = $3150 ✓
            # - equiv_monthly_1: $4500 * (21/30) = $3150 ✓
            # - equiv_daily_2: $100 * 21 = $2100 ✓
            # - equiv_weekly_2: $700 * (21/7) = $2100 ✓
            # - equiv_monthly_2: $3000 * (21/30) = $2100 ✓
            # - expensive_daily: $200 * 21 = $4200 ✗ (too expensive)

            expected_ids = [
                "equiv_daily_1",
                "equiv_weekly_1",
                "equiv_monthly_1",
                "equiv_daily_2",
                "equiv_weekly_2",
                "equiv_monthly_2",
            ]

            assert len(candidates) == 6, f"Expected 6 candidates, got {len(candidates)}"
            assert set(candidate_ids) == set(
                expected_ids
            ), f"Expected {expected_ids}, got {candidate_ids}"

    def test_cross_period_consistency(self, db_with_test_data):
        """Test that equivalent user preferences yield same results across periods"""
        with get_db_session() as db:
            # Create equivalent users with different price periods
            # All should have same total budget for 30 days: $3000
            daily_user = User(
                id="equiv_daily_user",
                name="Daily Equivalent User",
                email="equiv_daily@test.com",
                min_price=100.0,  # $100/day * 30 = $3000
                max_price=100.0,
                price_period=PricePeriod.DAY,
                preferred_start_date=datetime(2025, 8, 1),
                preferred_end_date=datetime(2025, 8, 31),  # 30 days
                preferred_listing_type=ListingType.SUBLET,
                date_flexibility_days=0,
            )

            weekly_user = User(
                id="equiv_weekly_user",
                name="Weekly Equivalent User",
                email="equiv_weekly@test.com",
                min_price=700.0,  # $700/week * (30/7) = $3000
                max_price=700.0,
                price_period=PricePeriod.WEEK,
                preferred_start_date=datetime(2025, 8, 1),
                preferred_end_date=datetime(2025, 8, 31),  # 30 days
                preferred_listing_type=ListingType.SUBLET,
                date_flexibility_days=0,
            )

            monthly_user = User(
                id="equiv_monthly_user",
                name="Monthly Equivalent User",
                email="equiv_monthly@test.com",
                min_price=3000.0,  # $3000/month * (30/30) = $3000
                max_price=3000.0,
                price_period=PricePeriod.MONTH,
                preferred_start_date=datetime(2025, 8, 1),
                preferred_end_date=datetime(2025, 8, 31),  # 30 days
                preferred_listing_type=ListingType.SUBLET,
                date_flexibility_days=0,
            )

            # Add users to database
            db.add(daily_user)
            db.add(weekly_user)
            db.add(monthly_user)
            db.commit()

            agent = ListingAgent(db=db)

            # Get candidates for each user
            daily_candidates = agent._get_candidate_listings(daily_user)
            weekly_candidates = agent._get_candidate_listings(weekly_user)
            monthly_candidates = agent._get_candidate_listings(monthly_user)

            # All should return the same listings (equiv_daily_2, equiv_weekly_2, equiv_monthly_2)
            daily_ids = set([listing.id for listing in daily_candidates])
            weekly_ids = set([listing.id for listing in weekly_candidates])
            monthly_ids = set([listing.id for listing in monthly_candidates])

            expected_ids = {"equiv_daily_2", "equiv_weekly_2", "equiv_monthly_2"}

            assert (
                daily_ids == expected_ids
            ), f"Daily user got {daily_ids}, expected {expected_ids}"
            assert (
                weekly_ids == expected_ids
            ), f"Weekly user got {weekly_ids}, expected {expected_ids}"
            assert (
                monthly_ids == expected_ids
            ), f"Monthly user got {monthly_ids}, expected {expected_ids}"

            # All should have same number of candidates
            assert (
                len(daily_candidates)
                == len(weekly_candidates)
                == len(monthly_candidates)
            )


class TestDateFlexibilityIntegration:
    """Test date flexibility filtering"""

    def test_date_flexibility_filtering(self, db_with_test_data):
        """Test that date flexibility expands candidate pool"""
        with get_db_session() as db:
            # Create a listing that's slightly outside the preferred date range
            flexible_listing = Listing(
                id="flexible_listing",
                url="https://test.com/flexible",
                title="Flexible Date Listing",
                price=3500.0,
                price_period=PricePeriod.MONTH,
                start_date=datetime(
                    2025, 7, 28
                ),  # 4 days before user's preferred start
                end_date=datetime(2025, 8, 28),
                listing_type=ListingType.SUBLET,
                scraped_at=datetime.utcnow(),
            )

            db.add(flexible_listing)
            db.commit()

            # Get user with date flexibility
            flexible_user = db.query(User).filter_by(id="user_flexible").first()

            agent = ListingAgent(db=db)
            candidates = agent._get_candidate_listings(flexible_user)
            candidate_ids = [listing.id for listing in candidates]

            # Should include the flexible listing since it's within 5 days flexibility
            assert (
                "flexible_listing" in candidate_ids
            ), f"Flexible listing not found in {candidate_ids}"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_no_matching_listings(self, clean_database):
        """Test filtering when no listings match criteria"""
        with get_db_session() as db:
            # Create user with very restrictive budget
            restrictive_user = User(
                id="restrictive_user",
                name="Restrictive User",
                email="restrictive@test.com",
                min_price=10000.0,  # Very high minimum
                max_price=20000.0,
                price_period=PricePeriod.MONTH,
                preferred_start_date=datetime(2025, 8, 1),
                preferred_end_date=datetime(2025, 9, 1),
                preferred_listing_type=ListingType.SUBLET,
                date_flexibility_days=0,
            )

            # Create a cheap listing
            cheap_listing = Listing(
                id="cheap_listing",
                url="https://test.com/cheap",
                title="Cheap Listing",
                price=1000.0,
                price_period=PricePeriod.MONTH,
                start_date=datetime(2025, 8, 1),
                end_date=datetime(2025, 9, 1),
                listing_type=ListingType.SUBLET,
                scraped_at=datetime.utcnow(),
            )

            db.add(restrictive_user)
            db.add(cheap_listing)
            db.commit()

            agent = ListingAgent(db=db)
            candidates = agent._get_candidate_listings(restrictive_user)

            # Should return no candidates
            assert (
                len(candidates) == 0
            ), f"Expected no candidates, got {len(candidates)}"

    def test_single_day_stay(self, clean_database):
        """Test filtering for single day stays"""
        with get_db_session() as db:
            single_day_user = User(
                id="single_day_user",
                name="Single Day User",
                email="single@test.com",
                min_price=100.0,
                max_price=200.0,
                price_period=PricePeriod.DAY,
                preferred_start_date=datetime(2025, 8, 1),
                preferred_end_date=datetime(2025, 8, 2),  # 1 day
                preferred_listing_type=ListingType.SUBLET,
                date_flexibility_days=0,
            )

            daily_listing = Listing(
                id="daily_listing",
                url="https://test.com/daily",
                title="Daily Listing",
                price=150.0,
                price_period=PricePeriod.DAY,
                start_date=datetime(2025, 8, 1),
                end_date=datetime(2025, 8, 2),
                listing_type=ListingType.SUBLET,
                scraped_at=datetime.utcnow(),
            )

            db.add(single_day_user)
            db.add(daily_listing)
            db.commit()

            agent = ListingAgent(db=db)
            candidates = agent._get_candidate_listings(single_day_user)

            # Should find the daily listing
            assert len(candidates) == 1
            assert candidates[0].id == "daily_listing"
