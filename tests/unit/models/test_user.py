"""Unit tests for User model methods"""

import pytest
from datetime import datetime
from src.models.user import User
from src.models.listing import PricePeriod
from tests.fixtures.test_data import create_simple_user


class TestUserPriceCalculations:
    """Test User price calculation methods"""
    
    def test_calculate_total_cost_monthly(self):
        """Test user price calculation for monthly preferences"""
        user = create_simple_user("test_monthly", 3000.0, 5000.0, PricePeriod.MONTH, 30)
        
        # Test various durations
        assert user._calculate_total_cost(3000.0, 30) == 3000.0  # 1 month
        assert user._calculate_total_cost(3000.0, 60) == 6000.0  # 2 months
        assert user._calculate_total_cost(3000.0, 15) == 1500.0  # 0.5 months
        assert user._calculate_total_cost(3000.0, 45) == 4500.0  # 1.5 months
    
    def test_calculate_total_cost_daily(self):
        """Test user price calculation for daily preferences"""
        user = create_simple_user("test_daily", 100.0, 200.0, PricePeriod.DAY, 14)
        
        # Test various durations
        assert user._calculate_total_cost(100.0, 1) == 100.0  # 1 day
        assert user._calculate_total_cost(100.0, 7) == 700.0  # 1 week
        assert user._calculate_total_cost(100.0, 30) == 3000.0  # 1 month
    
    def test_calculate_total_cost_weekly(self):
        """Test user price calculation for weekly preferences"""
        user = create_simple_user("test_weekly", 700.0, 1200.0, PricePeriod.WEEK, 21)
        
        # Test various durations
        assert user._calculate_total_cost(700.0, 7) == 700.0  # 1 week
        assert user._calculate_total_cost(700.0, 14) == 1400.0  # 2 weeks
        assert user._calculate_total_cost(700.0, 30) == pytest.approx(3000.0, rel=1e-2)  # ~1 month


class TestUserHardFilters:
    """Test User get_hard_filters method"""
    
    def test_get_hard_filters_basic(self):
        """Test basic hard filters without dates"""
        user = User(
            name="Test User",
            email="test@example.com",
            min_price=2000.0,
            max_price=4000.0,
            price_period=PricePeriod.MONTH,
            preferred_listing_type=None,
            date_flexibility_days=3
        )
        
        filters = user.get_hard_filters()
        
        assert filters['min_price'] == 2000.0
        assert filters['max_price'] == 4000.0
        assert filters['price_period'] == PricePeriod.MONTH
        assert filters['date_flexibility_days'] == 3
        assert 'preferred_listing_type' not in filters  # Should not include None values
        assert 'stay_duration_days' not in filters  # No dates provided
    
    def test_get_hard_filters_with_dates(self):
        """Test hard filters with date preferences"""
        user = User(
            name="Test User",
            email="test@example.com",
            min_price=3000.0,
            max_price=5000.0,
            price_period=PricePeriod.MONTH,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 9, 1),  # 31 days
            date_flexibility_days=5
        )
        
        filters = user.get_hard_filters()
        
        assert filters['preferred_start_date'] == datetime(2025, 8, 1)
        assert filters['preferred_end_date'] == datetime(2025, 9, 1)
        assert filters['stay_duration_days'] == 31
        assert filters['date_flexibility_days'] == 5
    
    def test_get_hard_filters_with_price_normalization(self):
        """Test that get_hard_filters() pre-calculates normalized price bounds"""
        user = User(
            name="Test User",
            email="test@example.com",
            min_price=3000.0,
            max_price=5000.0,
            price_period=PricePeriod.MONTH,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 9, 1),  # 31 days
        )
        
        filters = user.get_hard_filters()
        
        # Check that normalized total costs are calculated
        assert 'min_total_cost' in filters
        assert 'max_total_cost' in filters
        assert filters['stay_duration_days'] == 31
        
        # $3000/month for 31 days = $3000 * (31/30) = $3100
        assert filters['min_total_cost'] == pytest.approx(3100.0, rel=1e-2)
        # $5000/month for 31 days = $5000 * (31/30) = $5166.67
        assert filters['max_total_cost'] == pytest.approx(5166.67, rel=1e-2)
    
    def test_get_hard_filters_daily_preferences(self):
        """Test get_hard_filters() with daily price preferences"""
        user = User(
            name="Test User",
            email="test@example.com",
            min_price=100.0,
            max_price=200.0,
            price_period=PricePeriod.DAY,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 8, 15),  # 14 days
        )
        
        filters = user.get_hard_filters()
        
        # $100/day for 14 days = $1400
        assert filters['min_total_cost'] == 1400.0
        # $200/day for 14 days = $2800
        assert filters['max_total_cost'] == 2800.0
    
    def test_get_hard_filters_weekly_preferences(self):
        """Test get_hard_filters() with weekly price preferences"""
        user = User(
            name="Test User",
            email="test@example.com",
            min_price=700.0,
            max_price=1200.0,
            price_period=PricePeriod.WEEK,
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 8, 22),  # 21 days
        )
        
        filters = user.get_hard_filters()
        
        # $700/week for 21 days = $700 * (21/7) = $2100
        assert filters['min_total_cost'] == 2100.0
        # $1200/week for 21 days = $1200 * (21/7) = $3600
        assert filters['max_total_cost'] == 3600.0


class TestUserStayDuration:
    """Test User stay duration calculation"""
    
    def test_get_stay_duration_days(self):
        """Test stay duration calculation"""
        user = User(
            name="Test User",
            email="test@example.com",
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 8, 15),
        )
        
        assert user.get_stay_duration_days() == 14
    
    def test_get_stay_duration_days_no_dates(self):
        """Test stay duration with missing dates"""
        user = User(
            name="Test User",
            email="test@example.com",
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=None,
        )
        
        assert user.get_stay_duration_days() is None
    
    def test_get_stay_duration_days_single_day(self):
        """Test stay duration for single day"""
        user = User(
            name="Test User",
            email="test@example.com",
            preferred_start_date=datetime(2025, 8, 1),
            preferred_end_date=datetime(2025, 8, 2),
        )
        
        assert user.get_stay_duration_days() == 1
