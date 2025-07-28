import logging

from src.agents.user_agent import UserAgentDependencies, user_agent
from src.database.db import get_db_session
from src.services.user_service import UserService

logger = logging.getLogger(__name__)


def add_user_agent_subparser(subparsers):
    user_agent_parser = subparsers.add_parser("user_agent", help="User Agent chat CLI")
    user_agent_parser.add_argument(
        "--user-id", "-uid", type=str, required=True, help="User ID to chat with"
    )
    return user_agent_parser


async def handle_user_agent_commands(args):
    """Handle user agent chat commands."""
    try:
        with get_db_session() as db:
            user_service = UserService(db)

            user = user_service.get_user_by_id(args.user_id)
            if user is None:
                logger.error(f"User with ID '{args.user_id}' not found")
                print(f"Error: User with ID '{args.user_id}' not found")
                return False

            logger.info(f"Starting chat session for user: {args.user_id}")

            # Create dependencies and start chat
            deps = UserAgentDependencies(db=db, user=user)
            await user_agent.to_cli(deps=deps, prog_name="dwell")

            return True

    except KeyboardInterrupt:
        logger.info("Chat session interrupted by user")
        print("\nChat session ended.")
        return True

    except Exception as e:
        logger.error(f"Error in user agent chat: {e}")
        print(f"Error: Failed to start chat session - {e}")
        return False
