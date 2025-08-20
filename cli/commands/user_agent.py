import logging

from rich.console import Console
from rich.live import Live
from rich.text import Text

from src.agents.user_agent import UserAgent
from src.core.database import get_db_manager
from src.services.user_service import UserService

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


def add_user_agent_subparser(subparsers):
    user_agent_parser = subparsers.add_parser("user_agent", help="User Agent chat CLI")
    user_agent_parser.add_argument(
        "--user-id", "-uid", type=str, required=True, help="User ID to chat with"
    )
    return user_agent_parser


async def handle_user_agent_commands(args):
    """Handle user agent chat commands."""
    try:
        with get_db_manager().get_session() as db:
            logger.info(f"Starting chat session for user: {args.user_id}")

            user_service = UserService(db)
            user = user_service.get_user_by_id(args.user_id)

            user_agent = UserAgent(db_session=db, user=user)
            console = Console()

            # Load historical messages
            message_history = user_agent.get_message_history()

            if message_history:
                console.print("\n[bold blue]📜 Conversation History[/bold blue]")

                for message in message_history:
                    if message.role == "user":
                        user_text = Text(f"😊 You: {message.content}")
                        user_text.stylize("cyan")
                        console.print(user_text)

                    elif message.role == "assistant":
                        bot_text = Text(f"🤖 Bot: {message.content}")
                        bot_text.stylize("green")
                        console.print(bot_text)

                        # Show tool calls if any
                        if message.tool_calls:
                            for tool_call in message.tool_calls:
                                tool_text = Text(
                                    f"🔧 Tool Call: {tool_call.tool_name}({tool_call.args})"
                                )
                                tool_text.stylize("yellow")
                                console.print(tool_text)

                console.print("\n" + "─" * 50 + "\n")

            console.print(
                "\n[bold green]💬 Chat started! Type 'quit' or 'exit' to end the conversation.[/bold green]\n"
            )

            while True:
                if user_agent.is_new_session:
                    user_prompt = ""
                    console.print("[dim]Agent will initiate the conversation...[/dim]")
                else:
                    try:
                        user_prompt = input("😊 You: ").strip()
                        if user_prompt.lower() in ["quit", "exit", "q"]:
                            break
                    except (EOFError, KeyboardInterrupt):
                        break

                response_text = ""
                try:
                    with Live("🤖: ", refresh_per_second=15) as live:
                        async for event in user_agent.chat(user_prompt=user_prompt):
                            event_data = event.model_dump()

                            if event_data["type"] == "tool_call":
                                # Show tool call
                                tool_text = f"🔧 {event_data['tool_name']}"
                                console.print(tool_text, style="yellow")

                            elif event_data["type"] == "text_start":
                                # Start text response
                                response_text = event_data["content"]
                                live.update(f"🤖: {response_text}")

                            elif event_data["type"] == "text_chunk":
                                # Add to ongoing text response
                                response_text += event_data["content"]
                                live.update(f"🤖: {response_text}")

                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    console.print(f"\n❌ Error: {e}", style="red")
                    console.print(
                        "💡 You can try asking again or rephrase your question.",
                        style="dim",
                    )

                print()  # Add newline after response completes
            # Create dependencies and start chat

            return True

    except KeyboardInterrupt:
        logger.info("Chat session interrupted by user")
        return True

    except Exception as e:
        logger.error(f"Error in user agent chat: {e}")
        return False
