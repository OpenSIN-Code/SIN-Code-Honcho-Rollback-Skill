"""Purpose: Shared pytest fixtures for the test suite.

Docs: tests/conftest.py

# Fixtures

| Fixture | What |
|---------|------|
| `tmp_db_path` | A path under tmp_path for `.sin/rollback.db` (parent dir auto-created by storage) |
| `storage` | A fresh `RollbackStorage` instance using `tmp_db_path` |
| `sample_memories` | Deterministic 3-memory list for snapshot tests |

# FakeBrain

A minimal in-memory brain adapter that satisfies the `BrainAdapter` protocol.
Used to test `RollbackExecutor` end-to-end without needing a real
sin-brain installation.
"""
