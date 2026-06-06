"""Purpose: Tests for SnapshotManager.

Docs: tests/test_snapshot.py

Covers:
  - Empty snapshots (no brain adapter)
  - Snapshots with a FakeBrain adapter
  - Snapshots from a sin-brain-style DB (path-string adapter)
  - list / get / delete round-trips
  - Duplicate-name detection
  - metadata JSON round-trip
"""
