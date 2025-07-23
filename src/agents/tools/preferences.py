from typing import Any, Dict

from sqlalchemy.orm import Session

from src.models.user import User
from src.services.user_service import (
    UserNotFound,
    UserPreferenceUpdates,
    UserService,
    UserValidationError,
)


def update_user_preferences(
    user: User, db: Session, **preferences: Any
) -> Dict[str, Any]:
    """Update user preferences based on conversational input"""
    try:
        user_service = UserService(db)
        updates = UserPreferenceUpdates(**preferences)
        updated_user = user_service.update_user_preferences(user.id, updates)

        return {
            "success": True,
            "message": "Preferences updated successfully",
            "updated_preferences": {
                "preference_version": updated_user.preference_version,
                "last_update": (
                    updated_user.last_preference_update.isoformat()
                    if updated_user.last_preference_update
                    else None
                ),
            },
        }

    except UserValidationError as e:
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "updated_preferences": {},
        }
    except UserNotFound as e:
        return {
            "success": False,
            "message": f"User error: {str(e)}",
            "updated_preferences": {},
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to update preferences: {str(e)}",
            "updated_preferences": {},
        }


PREFERENCES_TOOL_DEFINITION: Dict[str, Any] = {
    "name": "update_user_preferences",
    "description": "Update user housing preferences based on conversation insights",
    "parameters": UserPreferenceUpdates.model_json_schema(),
}
