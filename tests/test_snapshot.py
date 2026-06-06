"""Purpose: Tests for SnapshotManager and snapshot creation flows.

Docs: tests/test_snapshot.doc.md
"""
from __future__ import annotations

import sqlite3

import pytest

from lib.snapshot import SnapshotManager


class TestSnapshotManager:
    def test_create_empty_snapshot_without_brain(self, mgr):
        """With no brain_adapter, snapshots are created empty (0 memories)."""
        snap = mgr.create("empty", description="nothing yet", source="manual")
        assert snap.name == "empty"
        assert snap.memory_count == 0
        assert snap.description == "nothing yet"
        assert snap.source == "manual"

    def test_create_snapshot_with_brain_adapter(self, tmp_db_path):
        """With a FakeBrain, snapshot captures the current memory state."""
        from tests.conftest import FakeBrain
        brain = FakeBrain(initial=[
            {"id": "a", "content": "alpha", "kind": "fact"},
            {"id": "b", "content": "beta", "kind": "fact"},
        ])
        mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=brain)
        snap = mgr.create("v1", description="", source="manual")
        assert snap.memory_count == 2
        # Hash should be deterministic for these 2 memories
        assert len(snap.memory_hash) == 16

    def test_create_snapshot_with_db_path_adapter(self, tmp_db_path, tmp_path):
        """A path string to a sin-brain-style DB is read automatically."""
        from tests.conftest import FakeBrain  # noqa: F401
        # Create a fake sin-brain DB
        db = tmp_path / "sin_brain.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                "CREATE TABLE memories (id TEXT, content TEXT, kind TEXT)"
            )
            conn.executemany(
                "INSERT INTO memories VALUES (?, ?, ?)",
                [("x", "x-content", "fact"), ("y", "y-content", "fact")],
            )
        mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=str(db))
        snap = mgr.create("db-snap", description="from-db", source="manual")
        assert snap.memory_count == 2

    def test_list_returns_all_snapshots(self, mgr):
        mgr.create("a")
        mgr.create("b")
        mgr.create("c")
        names = [s.name for s in mgr.list()]
        assert names == ["c", "b", "a"]

    def test_get_returns_snapshot_or_none(self, mgr):
        mgr.create("a")
        assert mgr.get("a") is not None
        assert mgr.get("nope") is None

    def test_delete_returns_true_if_existed(self, mgr):
        mgr.create("a")
        assert mgr.delete("a") is True
        assert mgr.delete("a") is False

    def test_duplicate_name_raises(self, mgr):
        mgr.create("a")
        with pytest.raises(Exception):
            mgr.create("a")

    def test_metadata_round_trips(self, mgr):
        meta = {"tag": "release", "version": "1.2.3"}
        snap = mgr.create("v1.2.3", metadata=meta)
        assert snap.metadata == meta
        # And survives a re-fetch
        fetched = mgr.get("v1.2.3")
        assert fetched.metadata == meta
