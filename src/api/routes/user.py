import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import CurrentUser, get_db
from src.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile")
async def get_user_profile(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get the current user's profile including completion status.

    Returns all user data needed by the frontend to determine:
    - Whether to continue chat or show listings
    - What preferences are set
    - What requirements are missing
    """
    user_service = UserService(db)
    has_requirements, missing = user_service.has_minimum_profile_requirements(
        current_user
    )

    return {
        "id": current_user.id,
        "name": current_user.name,
        "occupation": current_user.occupation,
        "bio": current_user.bio,
        # Profile completion status
        "profile_completed": current_user.profile_completed,
        "profile_completed_at": (
            current_user.profile_completed_at.isoformat()
            if current_user.profile_completed_at
            else None
        ),
        "has_minimum_requirements": has_requirements,
        "missing_requirements": missing,
        # Preferences
        "min_price": current_user.min_price,
        "max_price": current_user.max_price,
        "price_period": (
            current_user.price_period.value if current_user.price_period else None
        ),
        "preferred_start_date": (
            current_user.preferred_start_date.isoformat()
            if current_user.preferred_start_date
            else None
        ),
        "preferred_end_date": (
            current_user.preferred_end_date.isoformat()
            if current_user.preferred_end_date
            else None
        ),
        "date_flexibility_days": current_user.date_flexibility_days,
        "preferred_listing_type": (
            current_user.preferred_listing_type.value
            if current_user.preferred_listing_type
            else None
        ),
        "preference_profile": current_user.preference_profile,
        "preference_version": current_user.preference_version,
        "last_preference_update": (
            current_user.last_preference_update.isoformat()
            if current_user.last_preference_update
            else None
        ),
        # Other metadata
        "evaluation_credits": current_user.evaluation_credits,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat(),
    }
