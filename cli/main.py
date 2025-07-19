import argparse
import logging
import sys

from cli.commands.task import add_task_subparser, handle_task_command
from src.database.db import db_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def create_parser():
    parser = argparse.ArgumentParser(prog="dwell", description="Dwell CLI")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    add_task_subparser(subparsers)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize database
    db_manager.init_db()

    if args.command == "task":
        success = handle_task_command(args)
        return 0 if success else 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
