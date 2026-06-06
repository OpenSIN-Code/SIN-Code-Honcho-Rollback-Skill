"""Purpose: Tests for the diff between two snapshots.

Docs: tests/test_diff.doc.md
"""
from __future__ import annotations

import pytest

from lib.diff import diff_snapshots
from lib.snapshot import SnapshotManager
from tests.conftest import FakeBrain


def _setup_two_snapshots(tmp_db_path):
    """Create two snapshots with a known diff between them."""
    brain = FakeBrain(initial=[
        {"id": "a", "content": "alpha", "kind": "fact"},
        {"id": "b", "content": "beta", "kind": "fact"},
        {"id": "c", "content": "charlie-old", "kind": "fact"},
    ])
    mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=brain)
    snap_a = mgr.create("A", source="manual")

    # Mutate the brain for snapshot B
    brain.remember("c", "charlie-new")  # modify
    brain.remember("d", "delta")        # added
    brain.forget("a")                   # removed
    snap_b = mgr.create("B", source="manual")
    return snap_a, snap_b, brain


class TestDiffSnapshots:
    def test_diff_between_two_snapshots(self, storage, tmp_db_path):
        snap_a, snap_b, _ = _setup_two_snapshots(tmp_db_path)
        result = diff_snapshots(storage, "A", "B")
        assert result["snapshot_a"]["name"] == "A"
        assert result["snapshot_b"]["name"] == "B"
        added_ids = {m["id"] for m in result["added"]}
        removed_ids = {m["id"] for m in result["removed"]}
        assert added_ids == {"d"}
        assert removed_ids == {"a"}
        # 'c' was modified: charlie-old -> charlie-new
        modified_ids = {m["id"] for m in result["modified"]}
        assert modified_ids == {"c"}
        # 'b' is unchanged
        assert result["unchanged_count"] == 1

    def test_modified_includes_old_and_new(self, storage, tmp_db_path):
        _setup_two_snapshots(tmp_db_path)
        result = diff_snapshots(storage, "A", "B")
        c_mod = next(m for m in result["modified"] if m["id"] == "c")
        assert c_mod["old"] == "charlie-old"
        assert c_mod["new"] == "charlie-new"

    def test_diff_snapshot_vs_current_with_brain(self, storage, tmp_db_path):
        """When snapshot_b=None, diff against the live brain state."""
        brain = FakeBrain(initial=[
            {"id": "x", "content": "xold", "kind": "fact"},
            {"id": "y", "content": "y", "kind": "fact"},
        ])
        mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=brain)
        mgr.create("base", source="manual")

        # Live state diverges
        brain.remember("x", "xnew")
        brain.remember("z", "z")
        brain.forget("y")

        result = diff_snapshots(storage, "base", None, brain_adapter=brain)
        assert result["snapshot_b"]["name"] == "current"
        added = {m["id"] for m in result["added"]}
        removed = {m["id"] for m in result["removed"]}
        modified = {m["id"] for m in result["modified"]}
        assert added == {"z"}
        assert removed == {"y"}
        assert modified == {"x"}

    def test_diff_snapshot_vs_current_no_brain(self, storage, tmp_db_path):
        """Without a brain adapter, snapshot vs current is empty (graceful)."""
        mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=None)
        mgr.create("base", source="manual")
        result = diff_snapshots(storage, "base", None)
        assert result["snapshot_b"]["name"] == "current"
        assert result["added"] == []
        assert result["removed"] == []
        assert result["modified"] == []
        assert result["unchanged_count"] == 0

    def test_diff_with_missing_snapshot_a_raises(self, storage):
        with pytest.raises(ValueError, match="not found"):
            diff_snapshots(storage, "does-not-exist", None)

    def test_diff_with_missing_snapshot_b_raises(self, storage, mgr):
        mgr.create("A")
        with pytest.raises(ValueError, match="not found"):
            diff_snapshots(storage, "A", "does-not-exist")

    def test_identical_snapshots_show_no_changes(self, storage, tmp_db_path):
        brain = FakeBrain(initial=[
            {"id": "a", "content": "alpha", "kind": "fact"},
            {"id": "b", "content": "beta", "kind": "fact"},
        ])
        mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=brain)
        mgr.create("A")
        mgr.create("B")  # no mutations between
        result = diff_snapshots(storage, "A", "B")
        assert result["added"] == []
        assert result["removed"] == []
        assert result["modified"] == []
        assert result["unchanged_count"] == 2
