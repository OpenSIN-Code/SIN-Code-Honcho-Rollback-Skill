"""Purpose: FastMCP server exposing 4 rollback tools over stdio.

Docs: mcp_server.doc.md
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.stderr.write(
        "[sin-honcho-rollback] Missing dependency: 'mcp[cli]>=1.2'\n"
        "[sin-honcho-rollback] Install with: pip install 'mcp[cli]>=1.2'\n"
    )
    raise SystemExit(1)

from .audit import AuditLogger
from .diff import diff_snapshots
from .rollback import RollbackExecutor
from .snapshot import SnapshotManager
from .storage import RollbackStorage

# The default DB path used by MCP tools. Agents can override via env
# `SIN_ROLLBACK_DB` if they want per-project state without args.
import os
_DEFAULT_DB = os.environ.get("SIN_ROLLBACK_DB", ".sin/rollback.db")

# Shared state — one storage instance per MCP server lifetime. The
# brain adapter is None by default; agents that need real rollback
# can wire one up via the `brain_adapter` global below.
_storage = RollbackStorage(_DEFAULT_DB)
_brain_adapter = None  # type: ignore[var-annotated]


def set_brain_adapter(adapter) -> None:
    """Set the brain adapter used by `rollback_restore`.

    Call this from your agent's bootstrap code if you want rollback
    to actually mutate sin-brain. Without it, `rollback_restore`
    can plan but not apply.
    """
    global _brain_adapter
    _brain_adapter = adapter


mcp = FastMCP("sin-honcho-rollback")


def _json_default(obj):
    """JSON encoder fallback for dataclass / Path / datetime values."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)


@mcp.tool()
def rollback_snapshot(name: str, description: str = "") -> str:
    """Create a snapshot of the current sin-brain state.

    Args:
        name: unique snapshot name (e.g. "before-refactor-auth").
        description: optional human-readable description of the snapshot.

    Returns:
        JSON: {"success": true, "snapshot": {...}} or {"error": "..."}.
    """
    try:
        mgr = SnapshotManager(db_path=_DEFAULT_DB, brain_adapter=_brain_adapter)
        snap = mgr.create(name=name, description=description, source="manual")
        return json.dumps(
            {"success": True, "snapshot": snap.to_dict()},
            indent=2, default=_json_default,
        )
    except Exception as e:
        return json.dumps({"error": str(e), "name": name})


@mcp.tool()
def rollback_diff(snapshot_a: str, snapshot_b: str = "") -> str:
    """Show what changed between two snapshots (or a snapshot vs current).

    Args:
        snapshot_a: name of the first (older) snapshot.
        snapshot_b: name of the second snapshot, or empty for current state.

    Returns:
        JSON diff with `added`, `removed`, `modified`, `unchanged_count`.
    """
    try:
        storage = RollbackStorage(_DEFAULT_DB)
        b = snapshot_b if snapshot_b else None
        result = diff_snapshots(storage, snapshot_a, b, brain_adapter=_brain_adapter)
        return json.dumps(result, indent=2, default=_json_default)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def rollback_restore(
    snapshot_name: str,
    dry_run: bool = True,
    strategy: str = "merge",
) -> str:
    """Restore sin-brain to a previous snapshot.

    Args:
        snapshot_name: which snapshot to restore to.
        dry_run: if True (default), show what would change without applying.
        strategy: "merge" (safe) | "exact" (destructive) | "patch" (update-only).

    Returns:
        JSON plan / result. Always check `"errors"` before relying on
        the restore — partial application is possible.
    """
    try:
        executor = RollbackExecutor(
            db_path=_DEFAULT_DB, brain_adapter=_brain_adapter,
        )
        result = executor.restore(
            snapshot_name, dry_run=dry_run, strategy=strategy,
        )
        return json.dumps(result, indent=2, default=_json_default)
    except Exception as e:
        return json.dumps({"error": str(e), "snapshot": snapshot_name})


@mcp.tool()
def rollback_audit_log(since_hours: float = 24.0, limit: int = 100) -> str:
    """List all memory changes in the last N hours.

    Args:
        since_hours: how far back to look (default 24).
        limit: max entries to return (default 100).

    Returns:
        JSON list of audit entries, newest first.
    """
    try:
        audit = AuditLogger(_storage)
        return json.dumps(
            audit.list_changes(since_hours=since_hours, limit=limit),
            indent=2, default=_json_default,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


def main() -> None:
    """Run the FastMCP server on stdio."""
    sys.stderr.write(
        f"[sin-honcho-rollback] MCP server starting "
        f"(db={_DEFAULT_DB}, brain={'wired' if _brain_adapter else 'none'}).\n"
    )
    sys.stderr.flush()
    mcp.run()


if __name__ == "__main__":
    main()
