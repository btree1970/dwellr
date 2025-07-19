import logging

from cli.core.formatters import TaskFormatter, get_formatter
from cli.core.task_manager import TaskManager
from src.jobs.job_types import JobType

logger = logging.getLogger(__name__)


def add_task_subparser(subparsers):
    task_parser = subparsers.add_parser("task", help="Task management operations")
    task_subparsers = task_parser.add_subparsers(
        dest="task_action", help="Task actions"
    )

    # Sync command
    sync_parser = task_subparsers.add_parser("sync", help="Run sync listings task")
    sync_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    sync_parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=300,
        help="Timeout in seconds (default: 300)",
    )
    sync_parser.add_argument(
        "--no-wait", action="store_true", help="Submit task without waiting"
    )

    # Evaluate command
    eval_parser = task_subparsers.add_parser(
        "evaluate", help="Run evaluation listings task"
    )
    eval_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    eval_parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=300,
        help="Timeout in seconds (default: 300)",
    )
    eval_parser.add_argument(
        "--no-wait", action="store_true", help="Submit task without waiting"
    )

    # Status command
    status_parser = task_subparsers.add_parser("status", help="Check task status")
    status_parser.add_argument("task_id", help="Task ID to check")
    status_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )

    # List command
    list_parser = task_subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument(
        "--type", choices=["sync", "evaluate"], help="Filter by task type"
    )
    list_parser.add_argument(
        "--status",
        choices=["pending", "in_progress", "completed", "failed"],
        help="Filter by status",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of tasks to show (default: 10)",
    )


def handle_task_command(args):
    task_manager = TaskManager()

    if args.task_action == "sync":
        return run_task(task_manager, JobType.SYNC_LISTINGS, args)
    elif args.task_action == "evaluate":
        return run_task(task_manager, JobType.EVALUATE_LISTINGS, args)
    elif args.task_action == "status":
        return show_task_status(task_manager, args)
    elif args.task_action == "list":
        return list_tasks(task_manager, args)
    else:
        print("Error: No task action specified")
        return False


def run_task(task_manager: TaskManager, job_type: JobType, args) -> bool:
    task_name = job_type.value.replace("_", " ")
    print(f"🚀 Starting {task_name} operation...")
    logger.info(f"Starting {task_name} operation")

    try:
        task_id = task_manager.submit_task(job_type)
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        print(f"❌ Failed to submit task: {e}")
        return False

    if args.no_wait:
        print(f"📋 Task {task_id} submitted successfully")
        print(f"   Use 'dwell task status {task_id}' to check progress")
        return True

    success = task_manager.monitor_task(task_id, args.verbose, args.timeout)

    if success:
        task = task_manager.get_task_status(task_id)
        if task and task.result:
            formatter = get_formatter(task)
            if formatter:
                formatter.format_results(task, args.verbose)

    return success


def show_task_status(task_manager: TaskManager, args) -> bool:
    task = task_manager.get_task_status(args.task_id)
    if not task:
        print(f"❌ Task {args.task_id} not found")
        return False

    TaskFormatter.format_task_status(task, args.verbose)

    if task.status == "completed":
        formatter = get_formatter(task)
        if formatter:
            formatter.format_results(task, args.verbose)
    elif task.status == "failed":
        formatter = get_formatter(task)
        if formatter:
            formatter.format_error(task, args.verbose)

    return True


def list_tasks(task_manager: TaskManager, args) -> bool:
    tasks = task_manager.list_tasks(args.type, args.status, args.limit)
    TaskFormatter.format_task_list(tasks)
    return True
