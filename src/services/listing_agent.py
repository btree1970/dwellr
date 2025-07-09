from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import sessionmaker

from src.database.db import get_db_session
from src.models.user import User
from src.models.listing import Listing, ListingType
from src.models.listing_evaluation import ListingEvaluation
from src.services.listing_evaluator import ListingEvaluator, EvaluationResult


class BudgetExceededException(Exception):
    """Raised when cost budget is exceeded during evaluation"""
    pass


class ListingAgent:
    """Digital real estate agent that finds, evaluates, and recommends listings for users"""
    
    def __init__(self, db, evaluator: Optional[ListingEvaluator] = None):
        """Initialize the ListingAgent
        
        Args:
            db: Database session to use for all operations
            evaluator: ListingEvaluator instance (creates default if None)
        """
        self.db = db
        self.evaluator = evaluator or ListingEvaluator()
    
    def find_and_evaluate_listings(
        self, 
        user: User, 
        max_evaluations: int = 50, 
        max_cost: float = 2.00
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
            'candidate_listings_found': 0,
            'evaluations_completed': 0,
            'total_cost': 0.0,
            'average_score': 0.0,
            'budget_exceeded': False,
            'error_count': 0
        }
        
        # Get candidate listings (hard filtered, not yet evaluated)
        candidate_listings = self._get_candidate_listings(user, limit=max_evaluations)
        stats['candidate_listings_found'] = len(candidate_listings)
        
        if not candidate_listings:
            return stats
        
        # Estimate cost before starting
        estimated_cost = self._estimate_evaluation_cost(len(candidate_listings))
        if estimated_cost > max_cost:
            stats['budget_exceeded'] = True
            # Reduce to fit budget
            max_affordable = int(max_cost / (estimated_cost / len(candidate_listings)))
            candidate_listings = candidate_listings[:max_affordable]
        
        # Evaluate listings in batches
        evaluations = []
        total_cost = 0.0
        
        for listing in candidate_listings:
            try:
                # Check budget before each evaluation
                if total_cost >= max_cost:
                    stats['budget_exceeded'] = True
                    break
                
                # Evaluate listing
                evaluation = self.evaluator.evaluate_listing(user, listing)
                evaluations.append(evaluation)
                total_cost += evaluation.cost_usd
                
                # Store in database
                self._store_evaluation(evaluation)
                
                stats['evaluations_completed'] += 1
                
            except Exception as e:
                print(f"Error evaluating listing {listing.id}: {e}")
                stats['error_count'] += 1
                continue
        
        # Calculate final statistics
        stats['total_cost'] = total_cost
        if evaluations:
            stats['average_score'] = sum(e.score for e in evaluations) / len(evaluations)
        
        return stats
    
    def get_recommendations(self, user: User, limit: int = 20) -> List[Tuple[Listing, ListingEvaluation]]:
        """Get top-rated listings for a user
        
        Args:
            user: User to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of (Listing, ListingEvaluation) tuples ordered by score desc
        """
        # Query for top-rated evaluations with their listings
        query = self.db.query(ListingEvaluation, Listing).join(
            Listing, ListingEvaluation.listing_id == Listing.id
        ).filter(
            ListingEvaluation.user_id == user.id
        ).order_by(
            ListingEvaluation.score.desc(),
            ListingEvaluation.evaluated_at.desc()
        ).limit(limit)
        
        results = []
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
        total_evaluations = self.db.query(ListingEvaluation).filter(
            ListingEvaluation.user_id == user.id
        ).count()
        
        if total_evaluations == 0:
            return {
                'total_evaluations': 0,
                'total_cost': 0.0,
                'average_score': 0.0,
                'latest_evaluation': None
            }
        
        # Get statistics using SQLAlchemy functions
        from sqlalchemy import func
        stats_query = self.db.query(
            func.count(ListingEvaluation.id).label('count'),
            func.sum(ListingEvaluation.cost_usd).label('total_cost'),
            func.avg(ListingEvaluation.score).label('avg_score')
        ).filter(
            ListingEvaluation.user_id == user.id
        ).first()
        
        # Get latest evaluation
        latest_eval = self.db.query(ListingEvaluation).filter(
            ListingEvaluation.user_id == user.id
        ).order_by(ListingEvaluation.evaluated_at.desc()).first()
        
        return {
            'total_evaluations': stats_query.count,
            'total_cost': float(stats_query.total_cost or 0.0),
            'average_score': float(stats_query.avg_score or 0.0),
            'latest_evaluation': latest_eval.evaluated_at if latest_eval else None
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
        query = self.db.query(Listing).outerjoin(
            ListingEvaluation,
            and_(
                Listing.id == ListingEvaluation.listing_id,
                ListingEvaluation.user_id == user.id
            )
        ).filter(
            ListingEvaluation.id.is_(None)  # Only listings not yet evaluated
        )
        
        # Apply hard filters
        if 'min_price' in hard_filters:
            query = query.filter(Listing.price >= hard_filters['min_price'])
        
        if 'max_price' in hard_filters:
            query = query.filter(Listing.price <= hard_filters['max_price'])
        
        if 'preferred_start_date' in hard_filters:
            query = query.filter(Listing.start_date >= hard_filters['preferred_start_date'])
        
        if 'preferred_end_date' in hard_filters:
            query = query.filter(Listing.end_date <= hard_filters['preferred_end_date'])
        
        if 'preferred_listing_type' in hard_filters:
            query = query.filter(Listing.listing_type == hard_filters['preferred_listing_type'])
        
        # Order by most recent and limit
        query = query.order_by(Listing.scraped_at.desc()).limit(limit)
        
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
        input_cost = 800 * model_costs.get('input', 0.0001)
        output_cost = 100 * model_costs.get('output', 0.0003)
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
