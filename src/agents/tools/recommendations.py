from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.models.user import User
from src.services.listing_agent import ListingAgent


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of recommendations to return"
    )


def get_listing_recommendations(
    user: User, db: Session, **params: Any
) -> Dict[str, Any]:
    """Get personalized listing recommendations for user"""
    try:
        request = RecommendationRequest(**params)
        listing_agent = ListingAgent(db)

        recommendations = listing_agent.get_recommendations(user, limit=request.limit)

        return {
            "success": True,
            "message": f"Found {len(recommendations)} recommendations",
            "recommendations": recommendations,
            "total_found": len(recommendations),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get recommendations: {str(e)}",
            "recommendations": [],
            "total_found": 0,
        }


RECOMMENDATIONS_TOOL_DEFINITION: Dict[str, Any] = {
    "name": "get_listing_recommendations",
    "description": "Get personalized listing recommendations based on user preferences",
    "parameters": RecommendationRequest.model_json_schema(),
}
