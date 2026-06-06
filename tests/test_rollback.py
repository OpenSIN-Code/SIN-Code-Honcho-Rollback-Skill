"""Purpose: Tests for RollbackExecutor and the three restore strategies.

Docs: tests/test_rollback.doc.md
"""
from __future__ import annotations

import pytest

from lib.rollback import RollbackExecutor
from lib.snapshot import SnapshotManager
from tests.conftest import FakeBrain


def _setup_diverged_state(tmp_db_path):
    """Create a snapshot, then mutate the brain. Return (brain, mgr, snap_name)."""
    brain = FakeBrain(initial=[
        {"id": "a", "content": "alpha", "kind": "fact"},
        {"id": "b", "content": "beta", "kind": "fact"},
        {"id": "c", "content": "charlie", "kind": "fact"},
    ])
    mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=brain)
    mgr.create("baseline", source="manual")

    # Divergence:
    #   a → modified  (alpha → alpha-V2)
    #   b → removed   (we forget it)
    #   d → added     (we add a new one)
    brain.remember("a", "alpha-V2")
    brain.forget("b")
    brain.remember("d", "delta")
    return brain, mgr, "baseline"


class TestRollbackExecutor:
    def test_missing_snapshot_returns_error(self, storage):
        executor = RollbackExecutor(brain_adapter=FakeBrain())
        result = executor.restore("nope")
        assert "error" in result

    def test_invalid_strategy_returns_error(self, tmp_db_path):
        brain, _mgr, name = _setup_diverged_state(tmp_db_path)
        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=brain)
        result = executor.restore(name, strategy="BOGUS")
        assert "error" in result
        assert "BOGUS" in result["error"]

    def test_no_brain_adapter_returns_error(self, tmp_db_path):
        _brain, _mgr, name = _setup_diverged_state(tmp_db_path)
        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=None)
        result = executor.restore(name, dry_run=True)
        assert "error" in result

    def test_merge_strategy_re_adds_and_updates_keeps_added(self, tmp_db_path):
        brain, mgr, name = _setup_diverged_state(tmp_db_path)
        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=brain)
        # dry-run first
        plan = executor.restore(name, dry_run=True, strategy="merge")
        assert plan["dry_run"] is True
        assert plan["strategy"] == "merge"
        actions = plan["actions_planned"]
        # merge should re-add 'b', update 'a', and NOT touch 'd'
        action_kinds = {(a["action"], a.get("memory_id")) for a in actions}
        assert ("remember", "b") in action_kinds
        assert ("remember", "a") in action_kinds
        assert not any(a["action"] == "forget" and a["memory_id"] == "d" for a in actions)

        # Apply
        result = executor.restore(name, dry_run=False, strategy="merge")
        assert result["dry_run"] is False
        assert result["errors"] == []
        # Brain should now have a (alpha), b (beta), c (charlie), d (delta)
        assert brain.memories["a"] == "alpha"
        assert brain.memories["b"] == "beta"
        assert brain.memories["c"] == "charlie"
        assert brain.memories["d"] == "delta"

    def test_exact_strategy_deletes_added(self, tmp_db_path):
        brain, _mgr, name = _setup_diverged_state(tmp_db_path)
        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=brain)
        result = executor.restore(name, dry_run=False, strategy="exact")
        assert result["dry_run"] is False
        assert result["errors"] == []
        # 'd' should be gone; 'a' and 'b' restored
        assert "d" not in brain.memories
        assert brain.memories["a"] == "alpha"
        assert brain.memories["b"] == "beta"

    def test_patch_strategy_only_updates_modified(self, tmp_db_path):
        brain, _mgr, name = _setup_diverged_state(tmp_db_path)
        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=brain)
        result = executor.restore(name, dry_run=False, strategy="patch")
        assert result["errors"] == []
        # 'a' is updated; 'b' and 'd' are untouched
        assert brain.memories["a"] == "alpha"
        assert "b" not in brain.memories  # still gone — patch doesn't re-add
        assert brain.memories["d"] == "delta"  # still there — patch doesn't remove

    def test_restore_logs_to_audit(self, storage, tmp_db_path):
        brain, _mgr, name = _setup_diverged_state(tmp_db_path)
        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=brain)
        executor.restore(name, dry_run=False, strategy="merge")
        # Audit log should now have entries from the restore
        audit_rows = storage.get_audit_log(since_hours=1, limit=50)
        sources = {r["source"] for r in audit_rows}
        assert any(s.startswith("rollback:") for s in sources)

    def test_dry_run_does_not_mutate_brain(self, tmp_db_path):
        brain, _mgr, name = _setup_diverged_state(tmp_db_path)
        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=brain)
        before = dict(brain.memories)
        executor.restore(name, dry_run=True, strategy="merge")
        assert brain.memories == before

    def test_restore_handles_brain_exception_gracefully(self, tmp_db_path):
        """If a single remember() fails, the error is captured, others continue."""
        from lib.snapshot import SnapshotManager
        from tests.conftest import FakeBrain

        class FlakyBrain(FakeBrain):
            def remember(self, memory_id, content):
                # Fail only when the restore tries to write 'b' back.
                if memory_id == "b" and content == "beta":
                    raise RuntimeError("simulated failure")
                super().remember(memory_id, content)

        brain = FlakyBrain(initial=[
            {"id": "a", "content": "alpha", "kind": "fact"},
            {"id": "b", "content": "beta", "kind": "fact"},
        ])
        mgr = SnapshotManager(db_path=tmp_db_path, brain_adapter=brain)
        mgr.create("base", source="manual")
        # Now divergence (use direct dict mutation to bypass FlakyBrain.remember
        # so we can set up the diverged state without triggering the failure).
        brain.memories.pop("a")
        brain.memories["b"] = "beta-V2"

        executor = RollbackExecutor(db_path=tmp_db_path, brain_adapter=brain)
        result = executor.restore("base", dry_run=False, strategy="merge")
        # The merge plan re-adds 'a' and rewrites 'b' → 'b' write fails.
        assert any("simulated failure" in str(e.get("error", "")) for e in result["errors"])
