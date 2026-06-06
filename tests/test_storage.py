"""Purpose: Tests for the SQLite storage layer.

Docs: tests/test_storage.doc.md
"""
from __future__ import annotations

import json
import pytest

from lib.storage import RollbackStorage, Snapshot


class TestRollbackStorage:
    def test_init_creates_db_and_parent_dir(self, tmp_db_path):
        """DB file and `.sin/` parent dir are created on first use."""
        from pathlib import Path
        assert not Path(tmp_db_path).exists()
        RollbackStorage(tmp_db_path)
        assert Path(tmp_db_path).exists()
        assert Path(tmp_db_path).parent.exists()

    def test_init_is_idempotent(self, tmp_db_path):
        """Re-opening the DB does not raise and preserves data."""
        s1 = RollbackStorage(tmp_db_path)
        s1.create_snapshot(
            name="a", description="", source="manual", memories=[],
        )
        s2 = RollbackStorage(tmp_db_path)
        assert len(s2.list_snapshots()) == 1

    def test_create_snapshot_basic(self, storage, sample_memories):
        """create_snapshot returns a Snapshot with the right fields."""
        snap = storage.create_snapshot(
            name="v1", description="first", source="manual",
            memories=sample_memories,
        )
        assert isinstance(snap, Snapshot)
        assert snap.id > 0
        assert snap.name == "v1"
        assert snap.memory_count == 3
        assert len(snap.memory_hash) == 16  # truncated SHA-256
        assert snap.source == "manual"
        assert snap.metadata == {}

    def test_duplicate_name_raises(self, storage, sample_memories):
        """Creating two snapshots with the same name raises ValueError."""
        storage.create_snapshot(
            name="dup", description="", source="manual", memories=[],
        )
        with pytest.raises(ValueError, match="already exists"):
            storage.create_snapshot(
                name="dup", description="", source="manual", memories=[],
            )

    def test_list_snapshots_newest_first(self, storage, sample_memories):
        """list_snapshots returns rows in DESC id order."""
        storage.create_snapshot(name="a", description="", source="manual", memories=[])
        storage.create_snapshot(name="b", description="", source="manual", memories=[])
        storage.create_snapshot(name="c", description="", source="manual", memories=[])
        names = [s.name for s in storage.list_snapshots()]
        assert names == ["c", "b", "a"]

    def test_get_snapshot_by_name(self, storage):
        """get_snapshot returns the matching snapshot or None."""
        storage.create_snapshot(name="x", description="d", source="manual", memories=[])
        s = storage.get_snapshot("x")
        assert s is not None and s.name == "x"
        assert storage.get_snapshot("nope") is None

    def test_delete_snapshot(self, storage):
        """delete_snapshot returns True if it existed, False otherwise."""
        storage.create_snapshot(name="x", description="", source="manual", memories=[])
        assert storage.delete_snapshot("x") is True
        assert storage.delete_snapshot("x") is False
        assert storage.get_snapshot("x") is None

    def test_snapshot_hash_is_deterministic(self, sample_memories):
        """Same memories → same hash, regardless of input order."""
        from lib.storage import RollbackStorage
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "x.db")
            s1 = RollbackStorage(db)
            snap1 = s1.create_snapshot(
                name="a", description="", source="manual",
                memories=sample_memories,
            )
            # Reorder inputs
            reordered = [sample_memories[2], sample_memories[0], sample_memories[1]]
            s2 = RollbackStorage(db)
            snap2 = s2.create_snapshot(
                name="b", description="", source="manual",
                memories=reordered,
            )
            assert snap1.memory_hash == snap2.memory_hash

    def test_snapshot_hash_changes_with_content(self, sample_memories):
        """Different content → different hash."""
        from lib.storage import RollbackStorage
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "x.db")
            s = RollbackStorage(db)
            snap1 = s.create_snapshot(
                name="a", description="", source="manual",
                memories=sample_memories,
            )
            modified = [dict(m, content="DIFFERENT") for m in sample_memories]
            snap2 = s.create_snapshot(
                name="b", description="", source="manual",
                memories=modified,
            )
            assert snap1.memory_hash != snap2.memory_hash

    def test_log_change_appends_to_audit(self, storage):
        """log_change inserts a row that get_audit_log returns."""
        storage.log_change("remember", "m1", None, "hello", source="test")
        storage.log_change("forget", "m2", "bye", None, source="test")
        rows = storage.get_audit_log(since_hours=1, limit=10)
        assert len(rows) == 2
        # Newest first
        assert rows[0]["action"] == "forget"
        assert rows[1]["action"] == "remember"

    def test_get_audit_log_respects_limit(self, storage):
        """Limit caps the number of rows returned."""
        for i in range(5):
            storage.log_change("remember", f"m{i}", None, f"c{i}", source="t")
        assert len(storage.get_audit_log(since_hours=1, limit=3)) == 3

    def test_get_audit_log_respects_time_window(self, storage):
        """The since_hours filter is applied (entries exist)."""
        storage.log_change("remember", "m1", None, "c1", source="t")
        rows = storage.get_audit_log(since_hours=0.001, limit=10)
        assert len(rows) == 1

    def test_get_snapshot_memories(self, storage, sample_memories):
        """get_snapshot_memories returns the memories that made the snapshot."""
        snap = storage.create_snapshot(
            name="x", description="", source="manual",
            memories=sample_memories,
        )
        mems = storage.get_snapshot_memories(snap.id)
        assert len(mems) == 3
        ids = {m["id"] for m in mems}
        assert ids == {"m1", "m2", "m3"}
