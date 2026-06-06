"""Purpose: Tests for the read-only audit logger.

Docs: tests/test_audit.doc.md
"""
from __future__ import annotations

from lib.audit import AuditLogger


class TestAuditLogger:
    def test_empty_log_returns_empty_list(self, storage):
        audit = AuditLogger(storage)
        assert audit.list_changes(since_hours=24, limit=100) == []

    def test_list_changes_returns_recent(self, storage):
        storage.log_change("remember", "m1", None, "c1", source="t")
        storage.log_change("forget", "m2", "c2", None, source="t")
        audit = AuditLogger(storage)
        rows = audit.list_changes(since_hours=24, limit=10)
        assert len(rows) == 2

    def test_list_changes_respects_limit(self, storage):
        for i in range(10):
            storage.log_change("remember", f"m{i}", None, f"c{i}", source="t")
        audit = AuditLogger(storage)
        assert len(audit.list_changes(since_hours=24, limit=3)) == 3

    def test_list_changes_newest_first(self, storage):
        storage.log_change("remember", "m1", None, "c1", source="t")
        storage.log_change("forget", "m2", "c2", None, source="t")
        storage.log_change("pin", "m3", "c3", "c3", source="t")
        rows = AuditLogger(storage).list_changes(since_hours=24, limit=10)
        # Newest first
        assert [r["action"] for r in rows] == ["pin", "forget", "remember"]

    def test_list_changes_preserves_all_fields(self, storage):
        storage.log_change(
            "remember", "m1", "old", "new", source="sin-brain-mcp",
        )
        row = AuditLogger(storage).list_changes(since_hours=24, limit=1)[0]
        assert row["memory_id"] == "m1"
        assert row["old_content"] == "old"
        assert row["new_content"] == "new"
        assert row["source"] == "sin-brain-mcp"
        assert "timestamp" in row

    def test_log_change_with_no_old_content(self, storage):
        storage.log_change("remember", "m1", None, "fresh", source="t")
        row = AuditLogger(storage).list_changes(since_hours=24, limit=1)[0]
        assert row["old_content"] is None
        assert row["new_content"] == "fresh"
