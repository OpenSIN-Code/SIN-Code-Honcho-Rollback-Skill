"""Purpose: CLI entry for sin-honcho-rollback (`sin-honcho-rollback` command).

Docs: scripts/sin_honcho_rollback.doc.md

Subcommands:
  snapshot  — create a new snapshot
  list      — list all snapshots
  diff      — diff two snapshots (or vs current)
  restore   — restore to a previous snapshot
  audit     — list memory changes in last N hours
  serve     — start MCP server (stdio)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow `python -m scripts.sin_honcho_rollback` to find the `lib` package
# without requiring the package to be installed.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

import typer  # noqa: E402

from lib.audit import AuditLogger  # noqa: E402
from lib.diff import diff_snapshots  # noqa: E402
from lib.rollback import RollbackExecutor  # noqa: E402
from lib.snapshot import SnapshotManager  # noqa: E402
from lib.storage import RollbackStorage  # noqa: E402

app = typer.Typer(
    name="sin-honcho-rollback",
    help="Snapshot + rollback + audit log for sin-brain / Honcho memory.",
    no_args_is_help=True,
    add_completion=False,
)


def _json_default(obj):
    """JSON fallback for dataclass / Path values."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)


def _default_db() -> str:
    return os.environ.get("SIN_ROLLBACK_DB", ".sin/rollback.db")


@app.command()
def snapshot(
    name: str = typer.Argument(..., help="Unique snapshot name."),
    description: str = typer.Option("", "--description", "-d", help="Snapshot description."),
    source: str = typer.Option("manual", "--source", "-s", help="Source: manual | auto-pre-commit | auto-scheduled."),
    db: str = typer.Option(None, "--db", help="Path to .sin/rollback.db."),
):
    """Create a new snapshot of the current sin-brain state."""
    storage = RollbackStorage(db or _default_db())
    mgr = SnapshotManager(db_path=db or _default_db(), brain_adapter=None)
    try:
        snap = mgr.create(name=name, description=description, source=source)
    except ValueError as e:
        typer.echo(json.dumps({"error": str(e)}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps(
        {"success": True, "snapshot": snap.to_dict()},
        indent=2, default=_json_default,
    ))


@app.command("list")
def list_cmd(
    db: str = typer.Option(None, "--db", help="Path to .sin/rollback.db."),
):
    """List all snapshots, newest first."""
    mgr = SnapshotManager(db_path=db or _default_db())
    snaps = mgr.list()
    if not snaps:
        typer.echo(json.dumps({"snapshots": []}, indent=2))
        return
    typer.echo(json.dumps(
        {"snapshots": [s.to_dict() for s in snaps]},
        indent=2, default=_json_default,
    ))


@app.command()
def diff(
    snapshot_a: str = typer.Argument(..., help="First (older) snapshot name."),
    snapshot_b: str = typer.Argument("", help="Second snapshot, or empty for current."),
    db: str = typer.Option(None, "--db", help="Path to .sin/rollback.db."),
):
    """Diff two snapshots (or snapshot vs current state)."""
    storage = RollbackStorage(db or _default_db())
    try:
        result = diff_snapshots(
            storage, snapshot_a,
            snapshot_b if snapshot_b else None,
        )
    except ValueError as e:
        typer.echo(json.dumps({"error": str(e)}))
        raise typer.Exit(code=1)
    typer.echo(json.dumps(result, indent=2, default=_json_default))


@app.command()
def restore(
    snapshot_name: str = typer.Argument(..., help="Name of snapshot to restore to."),
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Plan only (default) or apply."),
    strategy: str = typer.Option("merge", "--strategy", help="merge | exact | patch."),
    db: str = typer.Option(None, "--db", help="Path to .sin/rollback.db."),
):
    """Restore sin-brain to a previous snapshot."""
    executor = RollbackExecutor(db_path=db or _default_db(), brain_adapter=None)
    result = executor.restore(
        snapshot_name, dry_run=dry_run, strategy=strategy,
    )
    if "error" in result and result.get("actions_taken") is None and result.get("actions_planned") is None:
        typer.echo(json.dumps(result, indent=2, default=_json_default))
        raise typer.Exit(code=1)
    typer.echo(json.dumps(result, indent=2, default=_json_default))


@app.command()
def audit(
    since_hours: float = typer.Option(24.0, "--since-hours", help="Look back N hours."),
    limit: int = typer.Option(100, "--limit", help="Max entries to return."),
    db: str = typer.Option(None, "--db", help="Path to .sin/rollback.db."),
):
    """List memory changes in the last N hours."""
    storage = RollbackStorage(db or _default_db())
    logger = AuditLogger(storage)
    typer.echo(json.dumps(
        logger.list_changes(since_hours=since_hours, limit=limit),
        indent=2, default=_json_default,
    ))


@app.command()
def serve():
    """Start the MCP server on stdio (for opencode / other MCP clients)."""
    from lib.mcp_server import main
    main()


@app.callback()
def main_callback(
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show version."),
):
    """sin-honcho-rollback CLI."""
    if version:
        from lib import __version__
        typer.echo(f"sin-honcho-rollback {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
