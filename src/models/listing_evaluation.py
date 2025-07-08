from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
import uuid

from src.database.db import Base


class ListingEvaluation(Base):
    """Database model for storing LLM evaluations of listings for users"""
    __tablename__ = "listing_evaluations"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False)
    
    # Evaluation results
    score = Column(Integer, nullable=False)  # 1-10 rating
    reasoning = Column(String, nullable=False)  # LLM explanation
    
    # Cost tracking
    cost_usd = Column(Float, nullable=False)
    tokens_used = Column(Integer, nullable=False)
    model_used = Column(String, nullable=False)
    
    # Timestamps
    evaluated_at = Column(DateTime, nullable=False, default=func.now())
    
    def __repr__(self):
        return f"<ListingEvaluation(id='{self.id}', user_id='{self.user_id}', listing_id='{self.listing_id}', score={self.score})>"
    
    @classmethod
    def from_evaluation_result(cls, evaluation_result):
        """Create a ListingEvaluation from an EvaluationResult"""
        return cls(
            user_id=evaluation_result.user_id,
            listing_id=evaluation_result.listing_id,
            score=evaluation_result.score,
            reasoning=evaluation_result.reasoning,
            cost_usd=evaluation_result.cost_usd,
            tokens_used=evaluation_result.total_tokens,
            model_used=evaluation_result.model_used,
            evaluated_at=evaluation_result.evaluated_at
        )