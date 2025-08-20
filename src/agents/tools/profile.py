from typing import Any, Dict

from pydantic_ai import RunContext
from returns.result import Success

from src.agents.deps import UserAgentDependencies
from src.services.user_service import UserNotFound, UserService


def mark_profile_complete(ctx: RunContext[UserAgentDependencies]) -> Dict[str, Any]:
    """Mark user profile as complete if all requirements are met"""
    try:
        user_service = UserService(ctx.deps.db)
        result = user_service.mark_profile_complete(ctx.deps.user.id)

        if isinstance(result, Success):
            updated_user = result.unwrap()
            return {
                "success": True,
                "message": "Profile marked as complete successfully! You now have a comprehensive preference profile.",
                "profile_status": {
                    "is_complete": updated_user.profile_completed,
                    "completed_at": (
                        updated_user.profile_completed_at.isoformat()
                        if updated_user.profile_completed_at
                        else None
                    ),
                    "preference_version": updated_user.preference_version,
                },
            }
        else:
            error_message = result.failure()
            return {
                "success": False,
                "message": error_message,
                "profile_status": {
                    "is_complete": False,
                    "completed_at": None,
                },
            }

    except UserNotFound as e:
        return {
            "success": False,
            "message": f"User error: {str(e)}",
            "profile_status": {},
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to mark profile as complete: {str(e)}",
            "profile_status": {},
        }
