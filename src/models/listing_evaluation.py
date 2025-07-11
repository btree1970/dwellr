import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.db import Base


class ListingEvaluation(Base):
    """Database model for storing LLM evaluations of listings for users"""

    __tablename__ = "listing_evaluations"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign keys
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    listing_id: Mapped[str] = mapped_column(String, ForeignKey("listings.id"))

    # Evaluation results
    score: Mapped[int] = mapped_column(Integer)  # 1-10 rating
    reasoning: Mapped[str] = mapped_column(String)  # LLM explanation

    # Cost tracking
    cost_usd: Mapped[float] = mapped_column(Float)
    tokens_used: Mapped[int] = mapped_column(Integer)
    model_used: Mapped[str] = mapped_column(String)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<ListingEvaluation(id='{self.id}', user_id='{self.user_id}', listing_id='{self.listing_id}', score={self.score})>"

    @classmethod
    def from_evaluation_result(cls, evaluation_result: Any) -> "ListingEvaluation":
        """Create a ListingEvaluation from an EvaluationResult"""
        return cls(
            user_id=evaluation_result.user_id,
            listing_id=evaluation_result.listing_id,
            score=evaluation_result.score,
            reasoning=evaluation_result.reasoning,
            cost_usd=evaluation_result.cost_usd,
            tokens_used=evaluation_result.total_tokens,
            model_used=evaluation_result.model_used,
            evaluated_at=evaluation_result.evaluated_at,
        )
