"""Purpose: Tests for the storage layer.

Docs: tests/test_storage.py

Covers:
  - DB file + parent dir auto-creation
  - Idempotent re-init
  - create_snapshot / get / list / delete
  - Duplicate-name detection
  - Hash determinism (input-order invariance, content sensitivity)
  - Audit log: append, ordering, limit, time window
  - get_snapshot_memories lookup
"""
