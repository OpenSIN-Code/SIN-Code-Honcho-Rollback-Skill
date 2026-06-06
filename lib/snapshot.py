"""Purpose: Create / list / delete snapshots of sin-brain state.

Docs: snapshot.doc.md
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audit import AuditLogger
from .storage import RollbackStorage, Snapshot

logger = logging.getLogger(__name__)


class SnapshotManager:
    """High-level wrapper around `RollbackStorage` for snapshot operations.

    `brain_adapter` is optional. If supplied, it must implement:

        - remember(memory_id: str, content: str) -> None
        - forget(memory_id: str) -> None
        - list_memories() -> List[Dict[str, str]]

    If not supplied, snapshots are created EMPTY (still useful for
    testing and for capturing manual state markers).
    """

    def __init__(
        self,
        db_path: str = ".sin/rollback.db",
        brain_adapter: Any = None,
    ):
        self.storage = RollbackStorage(db_path)
        self.audit = AuditLogger(self.storage)
        self.brain = brain_adapter

    def create(
        self,
        name: str,
        description: str = "",
        source: str = "manual",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Snapshot:
        """Create a snapshot. Pulls current sin-brain state if adapter wired.

        Args:
            name: unique snapshot name.
            description: human-readable context for the snapshot.
            source: "manual" | "auto-pre-commit" | "auto-scheduled".
            metadata: extra JSON metadata (tags, scope, etc.).
        """
        memories = self._read_current_memories()
        snap = self.storage.create_snapshot(
            name=name, description=description, source=source,
            memories=memories, metadata=metadata,
        )
        logger.info(
            "snapshot created: name=%s count=%d hash=%s",
            snap.name, snap.memory_count, snap.memory_hash,
        )
        return snap

    def list(self) -> List[Snapshot]:
        """List all snapshots, newest first."""
        return self.storage.list_snapshots()

    def delete(self, name: str) -> bool:
        """Delete a snapshot by name. Returns True if it existed."""
        existed = self.storage.delete_snapshot(name)
        if existed:
            logger.info("snapshot deleted: name=%s", name)
        return existed

    def get(self, name: str) -> Optional[Snapshot]:
        """Get a snapshot by name, or None."""
        return self.storage.get_snapshot(name)

    def _read_current_memories(self) -> List[Dict[str, str]]:
        """Read all memories from sin-brain. Graceful no-op if missing.

        Supports the sin-brain API when installed. If `self.brain` is a
        callable or exposes `list_memories()`, use that. If it's a path
        to a sin-brain SQLite DB, query that directly.
        """
        if self.brain is None:
            return []

        # Adapter object with list_memories()
        if hasattr(self.brain, "list_memories"):
            try:
                return self.brain.list_memories()
            except Exception as e:
                logger.warning("brain.list_memories() failed: %s", e)
                return []

        # Path-like: read sin-brain SQLite directly
        if isinstance(self.brain, (str, Path)):
            return self._read_from_sin_brain_db(Path(self.brain))

        return []

    @staticmethod
    def _read_from_sin_brain_db(db_path: Path) -> List[Dict[str, str]]:
        """Best-effort read of a sin-brain `.db` file.

        sin-brain schema: `memories(id TEXT, content TEXT, kind TEXT, ...)`.
        We only need id/content/kind for a useful snapshot.
        """
        if not db_path.exists():
            return []
        try:
            import sqlite3
            with sqlite3.connect(str(db_path)) as conn:
                rows = conn.execute(
                    "SELECT id, content, kind FROM memories"
                ).fetchall()
            return [
                {"id": r[0], "content": r[1], "kind": r[2] or "fact"}
                for r in rows
            ]
        except Exception as e:
            logger.warning("read_from_sin_brain_db failed: %s", e)
            return []
