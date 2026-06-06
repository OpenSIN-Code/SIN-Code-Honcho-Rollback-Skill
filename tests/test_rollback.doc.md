"""Purpose: Tests for RollbackExecutor.

Docs: tests/test_rollback.py

Covers:
  - Error paths: missing snapshot, invalid strategy, no brain adapter
  - merge strategy (safe default) — re-add + update + keep added
  - exact strategy — destructive: delete added, restore exact state
  - patch strategy — gentle: only update modified
  - dry-run safety (brain not mutated)
  - Audit-log entries on apply
  - Graceful per-action error capture (one failure doesn't break the rest)
"""
