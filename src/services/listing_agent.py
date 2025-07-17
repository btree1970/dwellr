from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.models.listing import Listing
from src.models.listing_evaluation import ListingEvaluation
from src.models.user import User
from src.services.listing_evaluator import EvaluationResult, ListingEvaluator


class BudgetExceededException(Exception):
    """Raised when cost budget is exceeded during evaluation"""

    pass


class ListingAgent:
    """Digital real estate agent that finds, evaluates, and recommends listings for users"""

    def __init__(self, db: Session, evaluator: Optional[ListingEvaluator] = None):
        """Initialize the ListingAgent

        Args:
            db: Database session to use for all operations
            evaluator: ListingEvaluator instance (creates default if None)
        """
        self.db = db
        self.evaluator = evaluator or ListingEvaluator()

    def find_and_evaluate_listings(
        self, user: User, max_evaluations: int = 50, max_cost: float = 2.00
    ) -> Dict[str, Any]:
        """Find candidate listings and evaluate them with LLM

        Args:
            user: User to find listings for
            max_evaluations: Maximum number of listings to evaluate
            max_cost: Maximum cost to spend on evaluations (USD)

        Returns:
            Dictionary with evaluation statistics and results
        """
        stats = {
            "candidate_listings_found": 0,
            "evaluations_completed": 0,
            "total_cost": 0.0,
            "average_score": 0.0,
            "budget_exceeded": False,
            "error_count": 0,
        }

        # Get candidate listings (hard filtered, not yet evaluated)
        candidate_listings = self._get_candidate_listings(user, limit=max_evaluations)
        stats["candidate_listings_found"] = len(candidate_listings)

        if not candidate_listings:
            return stats

        # Estimate cost before starting
        # TODO: Find a good way to handle this good for now
        estimated_cost = self._estimate_evaluation_cost(len(candidate_listings))
        if estimated_cost > max_cost:
            stats["budget_exceeded"] = True
            # Reduce to fit budget
            max_affordable = int(max_cost / (estimated_cost / len(candidate_listings)))
            candidate_listings = candidate_listings[:max_affordable]

        # Evaluate listings in batches
        evaluations: List[EvaluationResult] = []
        total_cost = 0.0

        for listing in candidate_listings:
            try:
                # Check budget before each evaluation
                if total_cost >= max_cost:
                    stats["budget_exceeded"] = True
                    break

                # Evaluate listing
                evaluation = self.evaluator.evaluate_listing(user, listing)
                evaluations.append(evaluation)
                total_cost += evaluation.cost_usd

                # Store in database
                self._store_evaluation(evaluation)

                stats["evaluations_completed"] += 1

            except Exception as e:
                print(f"Error evaluating listing {listing.id}: {e}")
                stats["error_count"] += 1
                continue

        # Calculate final statistics
        stats["total_cost"] = total_cost
        if evaluations:
            stats["average_score"] = sum(e.score for e in evaluations) / len(
                evaluations
            )

        return stats

    def get_recommendations(
        self, user: User, limit: int = 20
    ) -> List[Tuple[Listing, ListingEvaluation]]:
        """Get top-rated listings for a user

        Args:
            user: User to get recommendations for
            limit: Maximum number of recommendations to return

        Returns:
            List of (Listing, ListingEvaluation) tuples ordered by score desc
        """
        # Query for top-rated evaluations with their listings
        query = (
            self.db.query(ListingEvaluation, Listing)
            .join(Listing, ListingEvaluation.listing_id == Listing.id)
            .filter(ListingEvaluation.user_id == user.id)
            .order_by(
                ListingEvaluation.score.desc(), ListingEvaluation.created_at.desc()
            )
            .limit(limit)
        )

        results: List[Tuple[Listing, ListingEvaluation]] = []
        for evaluation, listing in query.all():
            results.append((listing, evaluation))

        return results

    def get_evaluation_status(self, user: User) -> Dict[str, Any]:
        """Get evaluation status and statistics for a user

        Args:
            user: User to get status for

        Returns:
            Dictionary with evaluation statistics
        """
        # Count total evaluations
        total_evaluations = (
            self.db.query(ListingEvaluation)
            .filter(ListingEvaluation.user_id == user.id)
            .count()
        )

        if total_evaluations == 0:
            return {
                "total_evaluations": 0,
                "total_cost": 0.0,
                "average_score": 0.0,
                "latest_evaluation": None,
            }

        # Get statistics using SQLAlchemy functions
        from sqlalchemy import func

        stats_query = (
            self.db.query(
                func.count(ListingEvaluation.id).label("count"),
                func.sum(ListingEvaluation.cost_usd).label("total_cost"),
                func.avg(ListingEvaluation.score).label("avg_score"),
            )
            .filter(ListingEvaluation.user_id == user.id)
            .first()
        )

        # Get latest evaluation
        latest_eval = (
            self.db.query(ListingEvaluation)
            .filter(ListingEvaluation.user_id == user.id)
            .order_by(ListingEvaluation.created_at.desc())
            .first()
        )

        return {
            "total_evaluations": stats_query.count if stats_query else 0,
            "total_cost": float(stats_query.total_cost or 0.0) if stats_query else 0.0,
            "average_score": (
                float(stats_query.avg_score or 0.0) if stats_query else 0.0
            ),
            "latest_evaluation": latest_eval.created_at if latest_eval else None,
        }

    def _get_candidate_listings(self, user: User, limit: int = 100) -> List[Listing]:
        """Get listings that match user's hard filters and haven't been evaluated

        Args:
            user: User to get candidates for
            limit: Maximum number of candidates to return

        Returns:
            List of Listing objects
        """
        hard_filters = user.get_hard_filters()

        # Base query - exclude already evaluated listings
        query = (
            self.db.query(Listing)
            .outerjoin(
                ListingEvaluation,
                and_(
                    Listing.id == ListingEvaluation.listing_id,
                    ListingEvaluation.user_id == user.id,
                ),
            )
            .filter(ListingEvaluation.id.is_(None))  # Only listings not yet evaluated
        )

        # Apply price filters with normalization for user's stay duration
        stay_duration = hard_filters.get("stay_duration_days")
        if stay_duration and (
            "min_total_cost" in hard_filters or "max_total_cost" in hard_filters
        ):
            from sqlalchemy import case

            from src.models.listing import PricePeriod

            # Get pre-calculated normalized price bounds from hard filters
            user_min_total = hard_filters.get("min_total_cost")
            user_max_total = hard_filters.get("max_total_cost")

            # Create SQL expression for listing's total cost
            from sqlalchemy import func

            listing_total_cost = func.round(
                case(
                    (
                        Listing.price_period == PricePeriod.DAY,
                        Listing.price * stay_duration,
                    ),
                    (
                        Listing.price_period == PricePeriod.WEEK,
                        Listing.price * (stay_duration / 7.0),
                    ),
                    (
                        Listing.price_period == PricePeriod.MONTH,
                        Listing.price * (stay_duration / 30.0),
                    ),
                    else_=Listing.price * stay_duration,
                ),
                2,
            )

            # Apply price filters in SQL
            if user_min_total is not None:
                query = query.filter(listing_total_cost >= user_min_total)
            if user_max_total is not None:
                query = query.filter(listing_total_cost <= user_max_total)

        elif not stay_duration:
            # Fallback to direct price comparison if no stay duration
            if "min_price" in hard_filters:
                query = query.filter(Listing.price >= hard_filters["min_price"])

            if "max_price" in hard_filters:
                query = query.filter(Listing.price <= hard_filters["max_price"])

        # Apply date filters with flexibility
        # Logic: Find listings that are available during the user's preferred period
        flexibility_days = hard_filters.get("date_flexibility_days", 0)

        if (
            "preferred_start_date" in hard_filters
            and "preferred_end_date" in hard_filters
        ):
            from datetime import timedelta

            preferred_start = hard_filters["preferred_start_date"]
            preferred_end = hard_filters["preferred_end_date"]

            # Apply flexibility to user's dates
            latest_user_start = preferred_start + timedelta(days=flexibility_days)
            earliest_user_end = preferred_end - timedelta(days=flexibility_days)

            # Listing must be available during user's (flexible) stay period
            # Listing.start_date <= user's latest start (listing available by then)
            # Listing.end_date >= user's earliest end (listing available until then)
            query = query.filter(
                Listing.start_date <= latest_user_start,
                Listing.end_date >= earliest_user_end,
            )

        if "preferred_listing_type" in hard_filters:
            query = query.filter(
                Listing.listing_type == hard_filters["preferred_listing_type"]
            )

        # Order by most recent and limit
        query = query.order_by(Listing.created_at.desc()).limit(limit)

        return query.all()

    def _estimate_evaluation_cost(self, num_listings: int) -> float:
        """Estimate cost for evaluating a number of listings

        Args:
            num_listings: Number of listings to evaluate

        Returns:
            Estimated cost in USD
        """
        # Use average cost from evaluator's token costs
        # Estimate ~800 input tokens and ~100 output tokens per evaluation
        model_costs = self.evaluator.token_costs.get(self.evaluator.model, {})
        input_cost = 800 * model_costs.get("input", 0.0001)
        output_cost = 100 * model_costs.get("output", 0.0003)
        cost_per_evaluation = input_cost + output_cost

        return num_listings * cost_per_evaluation

    def _store_evaluation(self, evaluation_result: EvaluationResult) -> None:
        """Store evaluation result in database

        Args:
            evaluation_result: EvaluationResult to store
        """
        evaluation = ListingEvaluation.from_evaluation_result(evaluation_result)

        self.db.merge(evaluation)
        self.db.commit()
