"""Purpose: Diff two snapshots (or a snapshot vs current state).

Docs: diff.doc.md
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .storage import RollbackStorage

logger = logging.getLogger(__name__)


# Output keys — kept stable for downstream tooling and tests.
_KEY_SNAP_A = "snapshot_a"
_KEY_SNAP_B = "snapshot_b"
_KEY_ADDED = "added"
_KEY_REMOVED = "removed"
_KEY_MODIFIED = "modified"
_KEY_UNCHANGED = "unchanged_count"


def diff_snapshots(
    storage: RollbackStorage,
    snapshot_a: str,
    snapshot_b: Optional[str] = None,
    brain_adapter: Any = None,
) -> Dict[str, Any]:
    """Compare two snapshots. If `snapshot_b` is None, compare against current.

    Args:
        storage: a `RollbackStorage` instance.
        snapshot_a: name of the first (older) snapshot.
        snapshot_b: name of the second (newer) snapshot, or None for current.
        brain_adapter: optional adapter to read live sin-brain state when
            `snapshot_b` is None.

    Returns:
        {
            "snapshot_a":      dict (the A snapshot),
            "snapshot_b":      dict or {"name": "current", "memory_hash": "<live>"},
            "added":           [m]  (in B but not in A),
            "removed":         [m]  (in A but not in B),
            "modified":        [{id, old, new}, ...],
            "unchanged_count": int,
        }

    Raises:
        ValueError: if `snapshot_a` (or `snapshot_b`, if given) is missing.
    """
    snap_a = storage.get_snapshot(snapshot_a)
    if not snap_a:
        raise ValueError(f"Snapshot '{snapshot_a}' not found")

    base = storage.get_snapshot_memories(snap_a.id)

    if snapshot_b is None:
        snap_b_data: Dict[str, Any] = {
            "name": "current",
            "memory_hash": "<live>",
        }
        current = _read_current(brain_adapter)
    else:
        snap_b = storage.get_snapshot(snapshot_b)
        if not snap_b:
            raise ValueError(f"Snapshot '{snapshot_b}' not found")
        snap_b_data = snap_b.to_dict()
        current = storage.get_snapshot_memories(snap_b.id)

    # Index by id for O(n) diff.
    base_by_id: Dict[str, Dict[str, str]] = {m["id"]: m for m in base}
    new_by_id: Dict[str, Dict[str, str]] = {m["id"]: m for m in current}

    added = [m for mid, m in new_by_id.items() if mid not in base_by_id]
    removed = [m for mid, m in base_by_id.items() if mid not in new_by_id]
    modified = [
        {
            "id": mid,
            "old": base_by_id[mid]["content"],
            "new": new_by_id[mid]["content"],
        }
        for mid in base_by_id
        if mid in new_by_id
        and base_by_id[mid]["content"] != new_by_id[mid]["content"]
    ]
    unchanged = len(set(base_by_id) & set(new_by_id)) - len(modified)

    return {
        _KEY_SNAP_A: snap_a.to_dict(),
        _KEY_SNAP_B: snap_b_data,
        _KEY_ADDED: added,
        _KEY_REMOVED: removed,
        _KEY_MODIFIED: modified,
        _KEY_UNCHANGED: unchanged,
    }


def _read_current(brain_adapter: Any) -> List[Dict[str, str]]:
    """Read current memory state. Graceful no-op."""
    if brain_adapter is None:
        return []
    if isinstance(brain_adapter, (str, Path)):
        # Best-effort: read sin-brain SQLite directly.
        from .snapshot import SnapshotManager
        return SnapshotManager._read_from_sin_brain_db(Path(brain_adapter))
    if hasattr(brain_adapter, "list_memories"):
        try:
            return brain_adapter.list_memories()
        except Exception as e:
            logger.warning("list_memories failed: %s", e)
    return []
