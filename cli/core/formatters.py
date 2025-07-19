from datetime import datetime

from src.models.task import Task


class TaskFormatter:
    @staticmethod
    def format_task_list(tasks: list[Task]):
        if not tasks:
            print("No tasks found")
            return

        print(f"📋 Found {len(tasks)} tasks:\n")
        for task in tasks:
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(task.status, "❓")

            task_type = "sync" if task.task_type == "sync_listings" else "evaluate"
            print(f"{status_emoji} {task.id[:8]}... ({task_type}) - {task.status}")
            print(f"   Created: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if task.status == "failed" and task.error_message:
                print(f"   Error: {task.error_message[:100]}...")
            print()

    @staticmethod
    def format_task_status(task: Task, verbose: bool = False):
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌",
        }.get(task.status, "❓")

        task_type = "sync" if task.task_type == "sync_listings" else "evaluate"
        print(f"{status_emoji} Task {task.id} ({task_type}) - {task.status}")

        if task.status == "in_progress" and task.started_at:
            elapsed = datetime.now() - task.started_at.replace(tzinfo=None)
            print(f"   Running for: {elapsed}")

        if verbose:
            print(f"   Created: {task.created_at}")
            if task.started_at:
                print(f"   Started: {task.started_at}")
            if task.completed_at:
                print(f"   Completed: {task.completed_at}")


class SyncResultFormatter:
    @staticmethod
    def format_results(task: Task, verbose: bool = False):
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

    @staticmethod
    def format_error(task: Task, verbose: bool = False):
        print(f"   Error: {task.error_message}")
        if verbose and task.result:
            print(f"   Additional details: {task.result}")


class EvaluationResultFormatter:
    @staticmethod
    def format_results(task: Task, verbose: bool = False):
        if not task.result:
            print("   No results available")
            return

        result = task.result
        print("\n📊 Evaluation Results:")
        print(f"   Users found: {result.get('users_found', 0)}")
        print(f"   Tasks created: {result.get('tasks_created', 0)}")
        print(f"   Success: {result.get('success', False)}")

        if verbose and result.get("message"):
            print(f"\n💬 {result['message']}")

    @staticmethod
    def format_error(task: Task, verbose: bool = False):
        print(f"   Error: {task.error_message}")
        if verbose and task.result:
            print(f"   Additional details: {task.result}")


def get_formatter(task: Task):
    if task.task_type == "sync_listings":
        return SyncResultFormatter
    elif task.task_type == "evaluate_listings":
        return EvaluationResultFormatter
    else:
        return None
