from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext

from src.agents.deps import UserAgentDependencies
from src.services.listing_service import ListingService


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of recommendations to return"
    )


def get_listing_recommendations(
    ctx: RunContext[UserAgentDependencies], **params: Any
) -> Dict[str, Any]:
    """Get personalized listing recommendations for user"""
    try:
        request = RecommendationRequest(**params)
        listing_service = ListingService(ctx.deps.db)

        recommendations = listing_service.get_recommendations(
            ctx.deps.user, limit=request.limit
        )

        serializedRecommendation: List[Tuple[Dict[str, Any], Dict[str, Any]]] = [
            (x.to_dict(), y.to_dict()) for x, y in recommendations
        ]

        return {
            "success": True,
            "message": f"Found {len(serializedRecommendation)} recommendations",
            "recommendations": serializedRecommendation,
            "total_found": len(serializedRecommendation),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get recommendations: {str(e)}",
            "recommendations": [],
            "total_found": 0,
        }
