import argparse
import logging

from cli.commands.task import add_task_subparser, handle_task_command
from cli.commands.user_agent import add_user_agent_subparser, handle_user_agent_commands
from src.core.database import db_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def create_parser():
    parser = argparse.ArgumentParser(prog="dwell", description="Dwell CLI")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    add_task_subparser(subparsers)
    add_user_agent_subparser(subparsers)

    return parser


async def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize database
    db_manager.init_db()

    if args.command == "task":
        success = handle_task_command(args)
    elif args.command == "user_agent":
        success = await handle_user_agent_commands(args)
    else:
        parser.print_help()
        return 1

    return 0 if success else 1
