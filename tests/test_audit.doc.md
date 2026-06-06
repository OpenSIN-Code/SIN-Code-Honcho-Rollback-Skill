"""Purpose: Tests for the audit logger.

Docs: tests/test_audit.py

Covers:
  - Empty DB → empty list
  - Returns recent changes within the time window
  - Respects `limit` cap
  - Newest-first ordering
  - All fields preserved (timestamp, action, memory_id, old/new, source)
  - None old_content is allowed (fresh inserts)
"""
