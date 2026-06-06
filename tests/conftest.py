"""Shared pytest fixtures for sin-honcho-rollback tests.

Docs: tests/conftest.doc.md
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make the `lib` package importable without installing the package.
_SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SKILL_ROOT))


@pytest.fixture
def tmp_db_path(tmp_path) -> str:
    """Yield a temporary path for `.sin/rollback.db` (parent auto-created)."""
    return str(tmp_path / ".sin" / "rollback.db")


@pytest.fixture
def storage(tmp_db_path):
    """Yield a fresh `RollbackStorage` backed by a tmp DB."""
    from lib.storage import RollbackStorage
    return RollbackStorage(tmp_db_path)


@pytest.fixture
def mgr(tmp_db_path):
    """Yield a SnapshotManager wired to the same tmp DB as `storage`."""
    from lib.snapshot import SnapshotManager
    return SnapshotManager(db_path=tmp_db_path, brain_adapter=None)


@pytest.fixture
def sample_memories():
    """A deterministic list of memory dicts for snapshot tests."""
    return [
        {"id": "m1", "content": "user prefers tabs", "kind": "preference"},
        {"id": "m2", "content": "project uses aiohttp", "kind": "fact"},
        {"id": "m3", "content": "deploys via launchd", "kind": "fact"},
    ]


class FakeBrain:
    """A minimal brain adapter for testing rollback end-to-end.

    Implements the `BrainAdapter` protocol:
      - list_memories() -> [dict]
      - remember(id, content) -> None
      - forget(id) -> None
    """

    def __init__(self, initial=None):
        self.memories = {m["id"]: m["content"] for m in (initial or [])}

    def list_memories(self):
        return [
            {"id": i, "content": c, "kind": "fact"}
            for i, c in sorted(self.memories.items())
        ]

    def remember(self, memory_id, content):
        self.memories[memory_id] = content

    def forget(self, memory_id):
        self.memories.pop(memory_id, None)
