"""Database management CLI commands."""

import logging

from rich.console import Console
from rich.table import Table

from src.core.database import db_manager

logger = logging.getLogger(__name__)
console = Console()


def add_db_subparser(subparsers):
    """Add database subparser to the main CLI."""
    db_parser = subparsers.add_parser("db", help="Database management commands")
    db_subparsers = db_parser.add_subparsers(
        dest="db_command", help="Database commands"
    )

    db_subparsers.add_parser("init", help="Initialize database with migrations")

    migrate_parser = db_subparsers.add_parser("migrate", help="Run pending migrations")
    migrate_parser.add_argument(
        "--target", default="head", help="Target revision (default: head)"
    )

    rollback_parser = db_subparsers.add_parser("rollback", help="Rollback migrations")
    rollback_parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Number of migrations to rollback (default: 1)",
    )

    reset_parser = db_subparsers.add_parser(
        "reset", help="Reset database (WARNING: destroys all data)"
    )
    reset_parser.add_argument(
        "--confirm", action="store_true", help="Confirm database reset"
    )

    db_subparsers.add_parser("status", help="Show migration status")

    history_parser = db_subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed information"
    )

    create_parser = db_subparsers.add_parser(
        "create-migration", help="Create a new migration"
    )
    create_parser.add_argument("message", help="Migration description")
    create_parser.add_argument(
        "--empty", action="store_true", help="Create empty migration (no autogenerate)"
    )

    db_subparsers.add_parser("verify", help="Verify database schema")

    stamp_parser = db_subparsers.add_parser(
        "stamp", help="Stamp database with a revision"
    )
    stamp_parser.add_argument(
        "--revision", default="head", help="Revision to stamp (default: head)"
    )


def handle_db_command(args) -> bool:
    """Handle database commands.

    Args:
        args: Parsed command line arguments

    Returns:
        True if command succeeded, False otherwise
    """
    try:
        if args.db_command == "init":
            return handle_init()
        elif args.db_command == "migrate":
            return handle_migrate(args.target)
        elif args.db_command == "rollback":
            return handle_rollback(args.steps)
        elif args.db_command == "reset":
            return handle_reset(args.confirm)
        elif args.db_command == "status":
            return handle_status()
        elif args.db_command == "history":
            return handle_history(args.verbose)
        elif args.db_command == "create-migration":
            return handle_create_migration(args.message, args.empty)
        elif args.db_command == "verify":
            return handle_verify()
        elif args.db_command == "stamp":
            return handle_stamp(args.revision)
        else:
            console.print(f"[red]Unknown database command: {args.db_command}[/red]")
            return False
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.exception("Database command failed")
        return False


def handle_init() -> bool:
    """Initialize database with migrations."""
    console.print("[yellow]Initializing database with migrations...[/yellow]")

    try:
        db_manager.init_db()
        console.print("[green]✓ Database initialized successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize database: {str(e)}[/red]")
        return False


def handle_migrate(target: str = "head") -> bool:
    """Run pending migrations."""
    status = db_manager.check_migration_status()

    if status["is_up_to_date"]:
        console.print("[green]Database is already up to date[/green]")
        return True

    console.print(
        f"[yellow]Running {status['pending_count']} pending migration(s)...[/yellow]"
    )

    try:
        db_manager.upgrade(target)
        console.print("[green]✓ Migrations completed successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Migration failed: {str(e)}[/red]")
        return False


def handle_rollback(steps: int = 1) -> bool:
    """Rollback migrations."""
    console.print(f"[yellow]Rolling back {steps} migration(s)...[/yellow]")

    try:
        for _ in range(steps):
            db_manager.downgrade("-1")
        console.print(f"[green]✓ Rolled back {steps} migration(s)[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Rollback failed: {str(e)}[/red]")
        return False


def handle_reset(confirm: bool = False) -> bool:
    """Reset database."""
    if not confirm:
        console.print("[red]WARNING: This will destroy all data in the database![/red]")
        console.print("Use --confirm flag to proceed")
        return False

    console.print("[yellow]Resetting database...[/yellow]")

    try:
        db_manager.reset_db()
        console.print("[green]✓ Database reset successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Reset failed: {str(e)}[/red]")
        return False


def handle_status() -> bool:
    """Show migration status."""
    status = db_manager.check_migration_status()

    table = Table(title="Migration Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Current Revision", status["current_revision"] or "None")
    table.add_row("Head Revision", status["head_revision"])
    table.add_row("Up to Date", "✓" if status["is_up_to_date"] else "✗")
    table.add_row("Pending Migrations", str(status["pending_count"]))

    console.print(table)

    if status["pending_migrations"]:
        console.print("\n[yellow]Pending migrations:[/yellow]")
        for rev in status["pending_migrations"]:
            console.print(f"  • {rev}")

    return True


def handle_history(verbose: bool = False) -> bool:
    """Show migration history."""
    history = db_manager.get_history(verbose)

    if not history:
        console.print("[yellow]No migrations found[/yellow]")
        return True

    table = Table(title="Migration History")
    table.add_column("Revision", style="cyan")
    table.add_column("Message", style="white")
    table.add_column("Status", style="green")

    if verbose:
        table.add_column("Down Revision", style="dim")
        table.add_column("Branch Labels", style="dim")

    for entry in history:
        status = ""
        if entry["is_current"]:
            status = "CURRENT"
        if entry["is_head"]:
            status = f"{status} HEAD" if status else "HEAD"

        row = [entry["revision"][:8], entry["message"] or "No message", status]

        if verbose:
            down_rev = entry.get("down_revision")
            row.append(down_rev[:8] if down_rev else "None")
            row.append(", ".join(entry.get("branch_labels", [])) or "None")

        table.add_row(*row)

    console.print(table)
    return True


def handle_create_migration(message: str, empty: bool = False) -> bool:
    """Create a new migration."""
    console.print(f"[yellow]Creating migration: {message}[/yellow]")

    try:
        revision = db_manager.create_migration(message, autogenerate=not empty)
        console.print(f"[green]✓ Created migration {revision[:8]}: {message}[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to create migration: {str(e)}[/red]")
        return False


def handle_verify() -> bool:
    """Verify database schema."""
    result = db_manager.verify_schema()

    table = Table(title="Schema Verification")
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="white")

    table.add_row("Database Tables", str(len(result["database_tables"])))
    table.add_row("Model Tables", str(len(result["model_tables"])))
    table.add_row("Schema Valid", "✓" if result["is_valid"] else "✗")

    console.print(table)

    if result["missing_in_db"]:
        console.print("\n[red]Tables missing in database:[/red]")
        for table in result["missing_in_db"]:
            console.print(f"  • {table}")

    if result["extra_in_db"]:
        console.print("\n[yellow]Extra tables in database:[/yellow]")
        for table in result["extra_in_db"]:
            console.print(f"  • {table}")

    return result["is_valid"]


def handle_stamp(revision: str = "head") -> bool:
    """Stamp database with a revision."""
    console.print(f"[yellow]Stamping database with revision: {revision}[/yellow]")

    try:
        db_manager.stamp(revision)
        console.print(f"[green]✓ Database stamped with revision: {revision}[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to stamp database: {str(e)}[/red]")
        return False
