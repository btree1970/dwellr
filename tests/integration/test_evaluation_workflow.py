from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.agents.listing_agent import EvaluationResult
from src.core.database import get_db_with_context
from src.models.user import User
from src.workers.tasks import evaluate_user_listings
from tests.fixtures.test_data import create_multiple_listings, create_user_with_credits


class TestEvaluationWorkflow:
    """Integration tests for the complete evaluation workflow"""

    def test_end_to_end_evaluation_workflow(self, clean_database, celery_app):
        user: User = create_user_with_credits(
            name="Test User",
            credits=5.00,
            preference_profile="Looking for apartments in downtown",
        )

        listings = create_multiple_listings(count=3, base_price=800.0)

        with get_db_with_context() as db:
            db.add(user)
            db.add_all(listings)
            db.commit()
            user_id = user.id
            listing_id = listings[0].id

        with patch("src.services.listing_service.ListingAgent") as mock_evaluator_class:
            mock_evaluator = Mock()
            mock_eval_result = EvaluationResult(
                user_id=user_id,
                listing_id=listing_id,
                score=8,
                reasoning="Great location and price",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.75,
                evaluation_time_ms=1200,
                model_used="gpt-4o-mini",
                evaluated_at=datetime.now(timezone.utc),
            )
            mock_evaluator.evaluate_listing.return_value = mock_eval_result
            mock_evaluator_class.return_value = mock_evaluator

            result = evaluate_user_listings.apply(args=[user_id]).get()

            assert result["success"] is True
            assert result["user_id"] == user_id
            assert result["evaluations_completed"] > 0
            assert result["total_cost"] > 0.0

        with get_db_with_context() as db:
            updated_user = db.query(User).filter_by(id=user_id).first()
            assert updated_user.evaluation_credits < 5.00
            assert updated_user.evaluation_credits > 0.0

    def test_workflow_with_insufficient_credits(self, clean_database, celery_app):
        user = create_user_with_credits(
            name="Poor User",
            credits=0.05,
            preference_profile="Looking for cheap places",
        )

        with get_db_with_context() as db:
            db.add(user)
            db.commit()
            user_id = user.id

        # Test the actual Celery task execution - should fail due to insufficient credits
        result = evaluate_user_listings.apply(args=[user_id]).get()

        assert result["success"] is False
        assert result["error"] == "Insufficient credits"

    def test_workflow_with_no_preference_profile(self, clean_database, celery_app):
        user = create_user_with_credits(
            name="No Prefs User",
            credits=5.00,
            preference_profile=None,
        )

        with get_db_with_context() as db:
            db.add(user)
            db.commit()
            user_id = user.id

        result = evaluate_user_listings.apply(args=[user_id]).get()

        assert result["success"] is True
        assert result["evaluations_completed"] == 0

    def test_real_credit_deduction_workflow(self, clean_database, celery_app):
        user = create_user_with_credits(
            name="Credit Test User",
            credits=2.00,
            preference_profile="Looking for affordable housing",
        )
        listings = create_multiple_listings(count=1, base_price=500.0)

        with get_db_with_context() as db:
            db.add(user)
            db.add_all(listings)
            db.commit()
            user_id = user.id
            listing_id = listings[0].id

        with patch("src.services.listing_service.ListingAgent") as mock_evaluator_class:
            mock_evaluator = Mock()
            mock_eval_result = EvaluationResult(
                user_id=user_id,
                listing_id=listing_id,
                score=7,
                reasoning="Good value for money",
                input_tokens=80,
                output_tokens=40,
                total_tokens=120,
                cost_usd=0.50,
                evaluation_time_ms=1000,
                model_used="gpt-4o-mini",
                evaluated_at=datetime.now(timezone.utc),
            )
            mock_evaluator.evaluate_listing.return_value = mock_eval_result
            mock_evaluator_class.return_value = mock_evaluator

            result = evaluate_user_listings.apply(args=[user_id]).get()

            assert result["success"] is True
            assert result["user_id"] == user_id
            assert result["evaluations_completed"] == 1
            assert result["total_cost"] == 0.50
            assert result["remaining_credits"] == 1.50

        with get_db_with_context() as db:
            updated_user = db.query(User).filter_by(id=user_id).first()
            assert updated_user.evaluation_credits == 1.50
