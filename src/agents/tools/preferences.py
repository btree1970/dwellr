from typing import Any, Dict

from pydantic_ai import RunContext
from returns.result import Success

from src.agents.deps import UserAgentDependencies
from src.services.user_service import (
    UserNotFound,
    UserPreferenceUpdates,
    UserService,
)


def update_user_preferences(
    ctx: RunContext[UserAgentDependencies], preferences: UserPreferenceUpdates
) -> Dict[str, Any]:
    """Update user preferences based on conversational input"""
    print("how are you doing")
    try:
        user_service = UserService(ctx.deps.db)
        result = user_service.update_user_preferences(ctx.deps.user.id, preferences)

        if isinstance(result, Success):
            updated_user = result.unwrap()
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
        else:
            return {
                "success": False,
                "message": f"Validation error: {result.failure()}",
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
