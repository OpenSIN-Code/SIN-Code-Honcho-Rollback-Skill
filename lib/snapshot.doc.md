"""Purpose: SnapshotManager — high-level snapshot CRUD.

Docs: lib/snapshot.py

# Usage

```python
from lib.snapshot import SnapshotManager

mgr = SnapshotManager(brain_adapter=None)         # empty snapshot
snap = mgr.create("pre-refactor", "Before auth", source="manual")

# Or with a real sin-brain DB
mgr = SnapshotManager(brain_adapter="path/to/sin-brain.db")
snap = mgr.create("pre-refactor", "Real state")

# Or with a custom adapter
class MyAdapter:
    def list_memories(self): return [{"id": "x", "content": "y", "kind": "fact"}]
    def remember(self, mid, content): ...
    def forget(self, mid): ...
mgr = SnapshotManager(brain_adapter=MyAdapter())
```

# Brain adapters

The skill is decoupled from sin-brain's internals — it just needs three
methods. Today it supports:

  - **None** — empty snapshots (good for testing, manual markers)
  - **str / Path** — path to a sin-brain SQLite DB (auto-queried)
  - **Object** — anything with `list_memories()`, `remember()`, `forget()`

This means sin-honcho-rollback can roll back to ANY system that exposes
those three methods, not only sin-brain. Honcho peer-cards work too
with a thin adapter.
"""
