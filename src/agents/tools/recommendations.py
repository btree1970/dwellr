from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext

from src.agents.user_agent import UserAgentDependencies, user_agent
from src.services.listing_agent import ListingAgent


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of recommendations to return"
    )


@user_agent.tool
def get_listing_recommendations(
    ctx: RunContext[UserAgentDependencies], **params: Any
) -> Dict[str, Any]:
    """Get personalized listing recommendations for user"""
    try:
        request = RecommendationRequest(**params)
        listing_agent = ListingAgent(ctx.deps.db)

        recommendations = listing_agent.get_recommendations(
            ctx.deps.user, limit=request.limit
        )

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
