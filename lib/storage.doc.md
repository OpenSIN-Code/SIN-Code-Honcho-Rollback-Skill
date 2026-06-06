"""Purpose: SQLite storage layer for sin-honcho-rollback.

Docs: lib/storage.py

`RollbackStorage` owns the `.sin/rollback.db` SQLite file. Two tables:

  - `snapshots`       — named, hashable memory checkpoints
  - `memory_changes`  — append-only audit log

# Usage

```python
from lib.storage import RollbackStorage

storage = RollbackStorage(".sin/rollback.db")
snap = storage.create_snapshot(
    name="pre-refactor",
    description="Before auth refactor",
    source="manual",
    memories=[{"id": "m1", "content": "user likes tabs", "kind": "fact"}],
)
for s in storage.list_snapshots():
    print(s.name, s.memory_count)
```

# Why a separate file?

sin-brain stores memories in its own DB. Rollback state is metadata
about the memory state, not the memory itself. Keeping them separate
means:
  - the rollback DB is safe to `.gitignore` while the memory DB is not
  - we can drop the entire rollback history without losing a single memory
  - a corrupt memory DB doesn't destroy the ability to audit/diff/restore

# Schema design

`memory_hash` is a SHA-256 truncated to 16 hex chars (64 bits). That
gives collision-safety up to ~4B entries (birthday bound) which is
vastly more than any human agent's working set.
"""
