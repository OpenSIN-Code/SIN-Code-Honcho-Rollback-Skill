"""Purpose: Tests for `diff_snapshots()`.

Docs: tests/test_diff.py

Covers:
  - Diff between two named snapshots (added / removed / modified / unchanged)
  - Modified entries expose `old` and `new` content
  - snapshot vs current (with brain_adapter)
  - snapshot vs current without a brain (graceful empty)
  - Missing-snapshot error paths
  - Identical snapshots → no changes
"""
