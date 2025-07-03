from typing import Optional
import re


class PriceConverter:
    """Utility class for converting rental prices between different periods"""
    
    # Standard conversion multipliers to monthly equivalent
    PERIOD_MULTIPLIERS = {
        'day': 30.0,
        'night': 30.0,
        'week': 4.33,  # Average weeks per month (52/12)
        'wk': 4.33,
        'month': 1.0,
        'mo': 1.0,
        'monthly': 1.0
    }
    
    @classmethod
    def to_monthly(cls, amount: float, period: str) -> float:
        """Convert price to monthly equivalent
        
        Args:
            amount: The price amount
            period: The price period (day, week, month, etc.)
            
        Returns:
            Monthly equivalent price
        """
        if not amount or not period:
            return amount
        
        period_lower = period.lower().strip()
        multiplier = cls.PERIOD_MULTIPLIERS.get(period_lower, 1.0)
        
        return amount * multiplier
    
    @classmethod
    def convert(cls, amount: float, from_period: str, to_period: str) -> float:
        """Convert price from one period to another
        
        Args:
            amount: The price amount
            from_period: Source period
            to_period: Target period
            
        Returns:
            Converted price
        """
        if not amount or not from_period or not to_period:
            return amount
        
        # Convert to monthly first, then to target period
        monthly_amount = cls.to_monthly(amount, from_period)
        
        to_period_lower = to_period.lower().strip()
        target_multiplier = cls.PERIOD_MULTIPLIERS.get(to_period_lower, 1.0)
        
        # Divide by target multiplier to get target period amount
        return monthly_amount / target_multiplier
    
    @classmethod
    def parse_price_string(cls, price_str: str) -> tuple[Optional[float], Optional[str]]:
        """Parse price string like '$500/week' into amount and period
        
        Args:
            price_str: Price string to parse
            
        Returns:
            Tuple of (amount, period) or (None, None) if parsing fails
        """
        if not price_str:
            return None, None
        
        # Remove whitespace and make lowercase for matching
        clean_str = price_str.strip()
        
        # Match patterns like "$500/week", "$1,200 per month", "$50 / day"
        price_pattern = r'\$\s?([\d,]+)(?:\s?(?:/|per)\s?(day|night|week|wk|month|mo|monthly))?'
        
        match = re.search(price_pattern, clean_str, re.IGNORECASE)
        
        if not match:
            return None, None
        
        try:
            # Parse amount (remove commas)
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            
            # Parse period (default to month if not specified)
            period = match.group(2) if match.group(2) else 'month'
            
            return amount, period.lower()
            
        except (ValueError, AttributeError):
            return None, None
    
    @classmethod
    def format_monthly_price(cls, amount: float, period: str) -> str:
        """Format price as monthly equivalent with annotation
        
        Args:
            amount: The price amount
            period: The price period
            
        Returns:
            Formatted string like "$2,000/month (from $500/week)"
        """
        if not amount or not period:
            return f"${amount:.0f}" if amount else "Price not available"
        
        monthly_price = cls.to_monthly(amount, period)
        
        if period.lower() in ['month', 'mo', 'monthly']:
            return f"${monthly_price:,.0f}/month"
        else:
            return f"${monthly_price:,.0f}/month (from ${amount:,.0f}/{period})"
    
    @classmethod
    def is_valid_period(cls, period: str) -> bool:
        """Check if period is a recognized pricing period
        
        Args:
            period: Period string to validate
            
        Returns:
            True if period is recognized
        """
        if not period:
            return False
        
        return period.lower().strip() in cls.PERIOD_MULTIPLIERS