"""Purpose: SQLite storage for rollback snapshots and audit log.

Docs: storage.doc.md

Per-project `.sin/rollback.db` (SQLite, auto-created on first use).
Two tables:

  - `snapshots`     — named, hashable checkpoints of memory state
  - `memory_changes` — append-only audit log of every mutation

The hash in `snapshots.memory_hash` is a SHA-256 truncated to 16 hex
chars of the sorted (id, kind, content) tuples. This gives a cheap
fingerprint so two snapshots with the same hash are byte-equivalent.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    memory_count INTEGER NOT NULL,
    memory_hash TEXT NOT NULL,
    source TEXT NOT NULL,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS memory_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    memory_id TEXT,
    old_content TEXT,
    new_content TEXT,
    source TEXT NOT NULL,
    snapshot_id INTEGER,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON memory_changes(timestamp);
CREATE INDEX IF NOT EXISTS idx_changes_snapshot ON memory_changes(snapshot_id);
"""


# Why a 16-char hex hash: full SHA-256 is 64 chars and overkill for a
# change-detector fingerprint inside a single project. 64 bits of entropy
# is still collision-safe up to ~4B entries (birthday bound).
_HASH_LEN = 16

# Default timestamp format — ISO 8601 with trailing Z for clarity.
_UTC_SUFFIX = "Z"


@dataclass
class Snapshot:
    """A named, hashable checkpoint of memory state.

    `metadata` is open-form JSON — tags, scope, source-cli, etc.
    """

    id: int
    name: str
    description: str
    created_at: str
    memory_count: int
    memory_hash: str
    source: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "memory_count": self.memory_count,
            "memory_hash": self.memory_hash,
            "source": self.source,
            "metadata": self.metadata,
        }


class RollbackStorage:
    """Per-project `.sin/rollback.db` for snapshots + audit log.

    Thread-safety: each public method opens its own connection, so
    concurrent callers will not block on each other for reads, but
    SQLite's default journal mode serializes writes.
    """

    def __init__(self, db_path: str = ".sin/rollback.db"):
        self.db_path = Path(db_path)
        # Auto-create the parent dir so first-run just works.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        # Enforce foreign-key constraints (SQLite needs explicit PRAGMA).
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ── Snapshot CRUD ────────────────────────────────────────────

    def create_snapshot(
        self,
        name: str,
        description: str,
        source: str,
        memories: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Snapshot:
        """Create a snapshot of current memory state.

        Args:
            name: unique snapshot name (e.g. "before-refactor-auth").
            description: what this snapshot captures.
            source: "manual" | "auto-pre-commit" | "auto-scheduled".
            memories: list of {"id": str, "content": str, "kind": str}.

        Raises:
            ValueError: if `name` is already taken.
        """
        h = self._hash_memories(memories)
        ts = self._utc_now()

        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id FROM snapshots WHERE name = ?", (name,),
            ).fetchone()
            if existing:
                raise ValueError(f"Snapshot '{name}' already exists")

            cur = conn.execute(
                """INSERT INTO snapshots
                   (name, description, created_at, memory_count, memory_hash, source, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, description, ts, len(memories), h, source,
                 json.dumps(metadata or {})),
            )
            snapshot_id = cur.lastrowid

            # Audit-log every memory as part of this snapshot. action='snapshot'
            # marks it as a "creation" event for diff/restore later.
            for m in memories:
                conn.execute(
                    """INSERT INTO memory_changes
                       (timestamp, action, memory_id, old_content,
                        new_content, source, snapshot_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (ts, "snapshot", m["id"], None, m["content"],
                     source, snapshot_id),
                )

        return Snapshot(
            id=snapshot_id, name=name, description=description,
            created_at=ts, memory_count=len(memories), memory_hash=h,
            source=source, metadata=metadata or {},
        )

    def list_snapshots(self) -> List[Snapshot]:
        """List all snapshots, newest first."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM snapshots ORDER BY id DESC"
            ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def get_snapshot(self, name: str) -> Optional[Snapshot]:
        """Return the snapshot with the given name, or None."""
        with self._conn() as conn:
            r = conn.execute(
                "SELECT * FROM snapshots WHERE name = ?", (name,),
            ).fetchone()
        return self._row_to_snapshot(r) if r else None

    def delete_snapshot(self, name: str) -> bool:
        """Delete a snapshot. Returns True if it existed."""
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM snapshots WHERE name = ?", (name,),
            )
            return cur.rowcount > 0

    # ── Audit log ────────────────────────────────────────────────

    def log_change(
        self,
        action: str,
        memory_id: str,
        old_content: Optional[str],
        new_content: Optional[str],
        source: str = "sin-brain-mcp",
    ) -> None:
        """Append a memory-mutation event to the audit log.

        `action` is one of: "remember" | "forget" | "pin" | "unpin" | "link"
        | "snapshot" | "rollback".
        """
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO memory_changes
                   (timestamp, action, memory_id, old_content,
                    new_content, source, snapshot_id)
                   VALUES (?, ?, ?, ?, ?, ?, NULL)""",
                (self._utc_now(), action, memory_id, old_content,
                 new_content, source),
            )

    def get_audit_log(
        self,
        since_hours: float = 24.0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit-log entries from the last N hours, newest first.

        Uses SQLite's relative-time modifier (e.g. "-24 hours") so the
        call is timezone-agnostic — the DB stores UTC ISO timestamps.
        """
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT timestamp, action, memory_id, old_content,
                          new_content, source
                   FROM memory_changes
                   WHERE timestamp >= datetime('now', ?)
                   ORDER BY id DESC LIMIT ?""",
                (f"-{since_hours} hours", limit),
            ).fetchall()
        return [
            {
                "timestamp": r[0], "action": r[1], "memory_id": r[2],
                "old_content": r[3], "new_content": r[4], "source": r[5],
            }
            for r in rows
        ]

    # ── Snapshot memory lookup (used by diff/rollback) ───────────

    def get_snapshot_memories(self, snapshot_id: int) -> List[Dict[str, Any]]:
        """Return the memory entries that made up the given snapshot."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT memory_id, new_content FROM memory_changes
                   WHERE snapshot_id = ? AND action = 'snapshot'""",
                (snapshot_id,),
            ).fetchall()
        return [{"id": r[0], "content": r[1]} for r in rows if r[1]]

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _utc_now() -> str:
        # Use timezone-aware UTC instead of the deprecated `datetime.utcnow()`.
        return datetime.now(timezone.utc).isoformat().replace("+00:00", _UTC_SUFFIX)

    @staticmethod
    def _row_to_snapshot(r) -> Snapshot:
        return Snapshot(
            id=r[0], name=r[1], description=r[2], created_at=r[3],
            memory_count=r[4], memory_hash=r[5], source=r[6],
            metadata=json.loads(r[7] or "{}"),
        )

    @staticmethod
    def _hash_memories(memories: List[Dict[str, Any]]) -> str:
        """Deterministic SHA-256-truncated hash of memory state.

        Sorts by `id:kind:content` so the same memory set always
        produces the same hash regardless of insertion order.
        """
        norm = sorted(
            f"{m['id']}:{m.get('kind', 'fact')}:{m['content']}"
            for m in memories
        )
        return hashlib.sha256("\n".join(norm).encode()).hexdigest()[:_HASH_LEN]
