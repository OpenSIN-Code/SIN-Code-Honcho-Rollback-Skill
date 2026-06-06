"""Purpose: sin-honcho-rollback — snapshot, diff, restore, audit sin-brain memory.

Docs: lib/__init__.doc.md

This package provides the "time-travel" layer for sin-brain (and conceptually
for Honcho peer memory). It exposes:

    - RollbackStorage  — SQLite storage for snapshots + audit log
    - SnapshotManager  — create / list / delete named snapshots
    - diff_snapshots   — compare two snapshots or snapshot vs current
    - RollbackExecutor — restore sin-brain to a previous snapshot
    - AuditLogger      — read-only audit log of all memory changes
    - mcp server       — 4 tools exposed via FastMCP stdio
"""

from .storage import RollbackStorage, Snapshot
from .snapshot import SnapshotManager
from .diff import diff_snapshots
from .rollback import RollbackExecutor
from .audit import AuditLogger

__all__ = [
    "RollbackStorage",
    "Snapshot",
    "SnapshotManager",
    "diff_snapshots",
    "RollbackExecutor",
    "AuditLogger",
]

__version__ = "0.1.0"
