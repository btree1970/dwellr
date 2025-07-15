import argparse
import logging
import sys
import time
from datetime import datetime
from typing import Optional

from src.database.db import db_manager, get_db_session
from src.jobs.job_types import JobType
from src.jobs.scheduler import JobScheduler
from src.models.task import Task

# Set up basic logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Test log message
logger.info("TEST LOG MESSAGE - If you see this, logging is working!")
print("=== END LOGGING DEBUG ===")

# Also ensure other modules can log
logging.getLogger().setLevel(logging.INFO)


class SyncCLI:
    def __init__(self):
        self.scheduler = JobScheduler()

    def submit_sync_task(self) -> str:
        logger.info("Submitting new sync_listings task")
        task_id = self.scheduler.schedule_job(
            job_type=JobType.SYNC_LISTINGS, context={}
        )
        logger.info(f"Sync task submitted with ID: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Task]:
        with get_db_session() as db:
            task = db.query(Task).filter_by(id=task_id).first()
            db.expunge_all()
            return task

    def monitor_task(
        self, task_id: str, verbose: bool = False, timeout: int = 300
    ) -> bool:
        print(f"📋 Task {task_id} submitted to Celery queue")
        print("⏳ Monitoring task progress...")

        start_time = time.time()
        last_status = None

        while True:
            if time.time() - start_time > timeout:
                print(f"⚠️  Task monitoring timed out after {timeout} seconds")
                print(f"   Task {task_id} may still be running in the background")
                return False

            task = self.get_task_status(task_id)
            if not task:
                print(f"❌ Task {task_id} not found in database")
                return False

            if task.status != last_status:
                timestamp = datetime.now().strftime("%H:%M:%S")
                if task.status == "pending":
                    print(f"[{timestamp}] 📋 Task is pending...")
                elif task.status == "in_progress":
                    print(f"[{timestamp}] 🔄 Task is running...")
                elif task.status == "completed":
                    print(f"[{timestamp}] ✅ Task completed successfully!")
                    self.display_task_results(task, verbose)
                    return True
                elif task.status == "failed":
                    print(f"[{timestamp}] ❌ Task failed!")
                    self.display_task_error(task, verbose)
                    return False

                last_status = task.status

            time.sleep(2)

    def display_task_results(self, task: Task, verbose: bool = False):
        if not task.result:
            print("   No results available")
            return

        result = task.result
        print("\n📊 Sync Results:")
        print(f"   Sources synced: {result.get('sources_synced', 0)}")

        stats = result.get("stats", {})
        print(f"   📈 Total new listings: {stats.get('total_new_listings', 0)}")
        print(f"   📋 Total processed: {stats.get('total_processed', 0)}")
        print(f"   ❌ Total errors: {stats.get('total_errors', 0)}")

        if verbose and "sources" in stats:
            print("\n📋 Per-source breakdown:")
            for source, source_stats in stats["sources"].items():
                status_emoji = "✅" if source_stats["success"] else "❌"
                print(f"   {status_emoji} {source}:")
                print(f"      New listings: {source_stats['new_listings']}")
                print(f"      Processed: {source_stats['total_processed']}")
                print(f"      Errors: {source_stats['errors']}")

        print(f"\n💬 {result.get('message', 'Sync completed')}")

    def display_task_error(self, task: Task, verbose: bool = False):
        print(f"   Error: {task.error_message}")

        if verbose and task.result:
            print(f"   Additional details: {task.result}")

    def run_sync(
        self, verbose: bool = False, timeout: int = 300, no_wait: bool = False
    ) -> bool:
        print("🚀 Starting sync operation...")
        logger.info("Starting sync operation")

        try:
            task_id = self.submit_sync_task()
        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            print(f"❌ Failed to submit task: {e}")
            return False

        if no_wait:
            print(f"📋 Task {task_id} submitted successfully")
            print("   Use 'python sync_cli.py --status <task_id>' to check progress")
            return True

        return self.monitor_task(task_id, verbose, timeout)

    def check_task_status(self, task_id: str, verbose: bool = False):
        """Check the status of a specific task"""
        task = self.get_task_status(task_id)
        if not task:
            print(f"❌ Task {task_id} not found")
            return

        print(f"📋 Task {task_id} status: {task.status}")

        if task.status == "completed":
            self.display_task_results(task, verbose)
        elif task.status == "failed":
            self.display_task_error(task, verbose)
        elif task.status == "in_progress":
            if task.started_at:
                elapsed = datetime.now() - task.started_at.replace(tzinfo=None)
                print(f"   Running for: {elapsed}")

        if verbose:
            print(f"   Created: {task.created_at}")
            if task.started_at:
                print(f"   Started: {task.started_at}")
            if task.completed_at:
                print(f"   Completed: {task.completed_at}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="CLI for triggering sync_listings")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )

    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=300,
        help="Timeout in seconds for task monitoring (default: 300)",
    )

    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Submit task and exit without waiting for completion",
    )

    parser.add_argument("--status", type=str, help="Check status of a specific task ID")

    args = parser.parse_args()

    db_manager.drop_db()
    db_manager.init_db()

    cli = SyncCLI()

    if args.status:
        cli.check_task_status(args.status, args.verbose)
    else:
        success = cli.run_sync(args.verbose, args.timeout, args.no_wait)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
