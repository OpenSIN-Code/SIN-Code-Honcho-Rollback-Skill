"""Purpose: Read-only audit log of all memory changes.

Docs: audit.doc.md
"""

from __future__ import annotations

from typing import Any, Dict, List

from .storage import RollbackStorage


class AuditLogger:
    """Read-only view onto the `memory_changes` audit log.

    The audit log is append-only — there's no `update` or `delete`
    on the `memory_changes` table. This is by design: the log IS the
    history. Even if a snapshot is deleted, the entries that were
    created with it remain (just with `snapshot_id` pointing to a
    missing row — they're still readable via this class).
    """

    def __init__(self, storage: RollbackStorage):
        self.storage = storage

    def list_changes(
        self,
        since_hours: float = 24.0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit-log entries from the last N hours, newest first.

        Args:
            since_hours: how far back to look. 24.0 = 1 day.
            limit: max entries to return (defensive cap).
        """
        return self.storage.get_audit_log(since_hours, limit)
