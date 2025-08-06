#!/usr/bin/env -S uv run python
"""Create test users for deployment testing."""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import db_manager, get_db_with_context  # noqa: E402
from src.models.listing import ListingType, PricePeriod  # noqa: E402
from src.services.user_service import UserService, UserServiceException  # noqa: E402


def parse_date(date_str):
    """Parse date string in various formats."""
    try:
        return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"Invalid date format: {date_str}. Use YYYY-MM-DD or ISO format."
            )


def create_parser():
    parser = argparse.ArgumentParser(
        description="Create test users for deployment testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test user
  ./scripts/create_test_user.py --name "Test User" --email "test@example.com"

  # Comprehensive test user
  ./scripts/create_test_user.py \\
    --name "John Doe" \\
    --email "john@test.com" \\
    --phone "555-0123" \\
    --occupation "Product Manager" \\
    --bio "Looking for short-term housing" \\
    --min-price 2000 \\
    --max-price 4000 \\
    --preference-profile "Need pet-friendly apartment in downtown area" \\
    --date-flexibility 7 \\
    --start-date 2025-08-01 \\
    --end-date 2025-09-01
        """,
    )

    # Required arguments
    parser.add_argument("--name", required=True, help="User's full name")
    parser.add_argument("--email", required=True, help="User's email address")

    # Optional user details
    parser.add_argument("--phone", help="Phone number")
    parser.add_argument(
        "--occupation",
        default="Software Engineer",
        help="User's occupation (default: Software Engineer)",
    )
    parser.add_argument(
        "--bio",
        default="Test user for development",
        help="User bio (default: Test user for development)",
    )

    # Financial
    parser.add_argument(
        "--credits", type=float, default=10.0, help="Evaluation credits (default: 10.0)"
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=1000,
        help="Minimum price preference (default: 1000)",
    )
    parser.add_argument(
        "--max-price",
        type=float,
        default=3000,
        help="Maximum price preference (default: 3000)",
    )
    parser.add_argument(
        "--price-period",
        choices=["day", "week", "month"],
        default="month",
        help="Price period (default: month)",
    )

    # Preferences
    parser.add_argument(
        "--preference-profile",
        default="Looking for modern apartments",
        help="User's listing preferences (default: Looking for modern apartments)",
    )
    parser.add_argument(
        "--date-flexibility",
        type=int,
        default=5,
        help="Date flexibility in days (default: 5)",
    )
    parser.add_argument(
        "--listing-type",
        choices=["rental", "sublet"],
        default="rental",
        help="Preferred listing type (default: rental)",
    )

    # Stay dates
    parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Preferred start date (YYYY-MM-DD, default: 30 days from now)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        help="Preferred end date (YYYY-MM-DD, default: 60 days from start)",
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    # Set default dates if not provided
    if not args.start_date:
        args.start_date = datetime.now(timezone.utc) + timedelta(days=30)

    if not args.end_date:
        args.end_date = args.start_date + timedelta(days=60)

    # Convert string enums to actual enum values
    price_period = PricePeriod(args.price_period)
    listing_type = ListingType(args.listing_type)

    # Prepare user data
    user_data = {
        "name": args.name,
        "email": args.email,
        "phone": args.phone,
        "occupation": args.occupation,
        "bio": args.bio,
        "evaluation_credits": args.credits,
        "min_price": args.min_price,
        "max_price": args.max_price,
        "price_period": price_period,
        "preference_profile": args.preference_profile,
        "date_flexibility_days": args.date_flexibility,
        "preferred_listing_type": listing_type,
        "preferred_start_date": args.start_date,
        "preferred_end_date": args.end_date,
    }

    # Remove None values
    user_data = {k: v for k, v in user_data.items() if v is not None}

    try:
        # Initialize database if needed
        db_manager.init_db()

        with get_db_with_context() as db:
            user_service = UserService(db)
            user = user_service.create_user(**user_data)

            print("✅ Test user created successfully!")
            print(f"   ID: {user.id}")
            print(f"   Name: {user.name}")
            print(f"   Email: {user.email}")
            print(f"   Occupation: {user.occupation}")
            print(f"   Credits: ${user.evaluation_credits:.2f}")
            print(
                f"   Price range: ${user.min_price:.0f}-${user.max_price:.0f}/{user.price_period.value}"
            )
            print(
                f"   Stay: {user.preferred_start_date.strftime('%Y-%m-%d')} to {user.preferred_end_date.strftime('%Y-%m-%d')}"
            )
            print(f"   Date flexibility: {user.date_flexibility_days} days")
            print(f"   Preference: {user.preference_profile}")

            return 0

    except UserServiceException as e:
        print(f"❌ Error creating user: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
