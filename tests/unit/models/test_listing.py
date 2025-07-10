"""Unit tests for Listing model methods"""

import pytest
from datetime import datetime
from src.models.listing import Listing, PricePeriod
from tests.fixtures.test_data import create_simple_listing


class TestListingPriceCalculations:
    """Test Listing price calculation methods"""
    
    def test_calculate_total_cost_daily(self):
        """Test listing price calculation for daily rates"""
        listing = create_simple_listing("test_daily", 150.0, PricePeriod.DAY)
        
        # Test various durations
        assert listing.calculate_total_cost_for_duration(1) == 150.0  # 1 day
        assert listing.calculate_total_cost_for_duration(7) == 1050.0  # 1 week
        assert listing.calculate_total_cost_for_duration(30) == 4500.0  # 1 month
        assert listing.calculate_total_cost_for_duration(15) == 2250.0  # 15 days
    
    def test_calculate_total_cost_weekly(self):
        """Test listing price calculation for weekly rates"""
        listing = create_simple_listing("test_weekly", 1050.0, PricePeriod.WEEK)
        
        # Test various durations
        assert listing.calculate_total_cost_for_duration(7) == 1050.0  # 1 week
        assert listing.calculate_total_cost_for_duration(14) == 2100.0  # 2 weeks
        assert listing.calculate_total_cost_for_duration(30) == pytest.approx(4500.0, rel=1e-2)  # ~1 month
        assert listing.calculate_total_cost_for_duration(3.5) == 525.0  # 0.5 weeks
    
    def test_calculate_total_cost_monthly(self):
        """Test listing price calculation for monthly rates"""
        listing = create_simple_listing("test_monthly", 4500.0, PricePeriod.MONTH)
        
        # Test various durations
        assert listing.calculate_total_cost_for_duration(30) == 4500.0  # 1 month
        assert listing.calculate_total_cost_for_duration(60) == 9000.0  # 2 months
        assert listing.calculate_total_cost_for_duration(15) == 2250.0  # 0.5 months
        assert listing.calculate_total_cost_for_duration(45) == 6750.0  # 1.5 months
    
    def test_calculate_total_cost_zero_duration(self):
        """Test price calculation with zero duration"""
        listing = create_simple_listing("test", 100.0, PricePeriod.DAY)
        assert listing.calculate_total_cost_for_duration(0) == 0.0
    
    def test_calculate_total_cost_null_price(self):
        """Test price calculation with null price"""
        listing = Listing(
            id="test", url="https://test.com", title="Test",
            price=None, price_period=PricePeriod.DAY
        )
        assert listing.calculate_total_cost_for_duration(30) == 0.0
    
    def test_calculate_total_cost_null_period(self):
        """Test price calculation with null period"""
        listing = Listing(
            id="test", url="https://test.com", title="Test",
            price=100.0, price_period=None
        )
        assert listing.calculate_total_cost_for_duration(30) == 0.0


class TestPriceEquivalence:
    """Test that equivalent prices across periods yield same total costs"""
    
    def test_equivalent_prices_same_total_cost(self):
        """Test that $150/day = $1050/week = $4500/month"""
        daily_listing = create_simple_listing("daily", 150.0, PricePeriod.DAY)
        weekly_listing = create_simple_listing("weekly", 1050.0, PricePeriod.WEEK)
        monthly_listing = create_simple_listing("monthly", 4500.0, PricePeriod.MONTH)
        
        # Test equivalence for various durations
        durations = [1, 7, 14, 30, 45, 60]
        
        for duration in durations:
            daily_cost = daily_listing.calculate_total_cost_for_duration(duration)
            weekly_cost = weekly_listing.calculate_total_cost_for_duration(duration)
            monthly_cost = monthly_listing.calculate_total_cost_for_duration(duration)
            
            # Allow small floating point differences
            assert abs(daily_cost - weekly_cost) < 0.01, f"Daily vs Weekly mismatch for {duration} days"
            assert abs(daily_cost - monthly_cost) < 0.01, f"Daily vs Monthly mismatch for {duration} days"
            assert abs(weekly_cost - monthly_cost) < 0.01, f"Weekly vs Monthly mismatch for {duration} days"
    
    def test_different_equivalent_sets(self):
        """Test multiple equivalent price sets"""
        # Set 1: $100/day = $700/week = $3000/month
        daily_1 = create_simple_listing("daily_1", 100.0, PricePeriod.DAY)
        weekly_1 = create_simple_listing("weekly_1", 700.0, PricePeriod.WEEK)
        monthly_1 = create_simple_listing("monthly_1", 3000.0, PricePeriod.MONTH)
        
        # Set 2: $200/day = $1400/week = $6000/month
        daily_2 = create_simple_listing("daily_2", 200.0, PricePeriod.DAY)
        weekly_2 = create_simple_listing("weekly_2", 1400.0, PricePeriod.WEEK)
        monthly_2 = create_simple_listing("monthly_2", 6000.0, PricePeriod.MONTH)
        
        test_duration = 21  # 3 weeks
        
        # Test set 1 equivalence
        daily_1_cost = daily_1.calculate_total_cost_for_duration(test_duration)
        weekly_1_cost = weekly_1.calculate_total_cost_for_duration(test_duration)
        monthly_1_cost = monthly_1.calculate_total_cost_for_duration(test_duration)
        
        assert abs(daily_1_cost - weekly_1_cost) < 0.01
        assert abs(daily_1_cost - monthly_1_cost) < 0.01
        
        # Test set 2 equivalence
        daily_2_cost = daily_2.calculate_total_cost_for_duration(test_duration)
        weekly_2_cost = weekly_2.calculate_total_cost_for_duration(test_duration)
        monthly_2_cost = monthly_2.calculate_total_cost_for_duration(test_duration)
        
        assert abs(daily_2_cost - weekly_2_cost) < 0.01
        assert abs(daily_2_cost - monthly_2_cost) < 0.01
        
        # Test that different sets are actually different
        assert abs(daily_1_cost - daily_2_cost) > 100  # Should be significantly different