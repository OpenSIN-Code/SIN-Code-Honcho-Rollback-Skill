"""Purpose: Diff two memory snapshots.

Docs: lib/diff.py

# Mental model

`diff_snapshots(storage, "A", "B")` answers:
  "What changed in sin-brain between snapshot A and snapshot B?"

Output:
```json
{
  "snapshot_a": {"name": "A", "memory_count": 10, "memory_hash": "..."},
  "snapshot_b": {"name": "B", "memory_count": 12, "memory_hash": "..."},
  "added":     [{"id": "m11", "content": "..."}, ...],   // new in B
  "removed":   [{"id": "m3",  "content": "..."}, ...],   // gone in B
  "modified":  [{"id": "m7", "old": "...", "new": "..."}, ...],
  "unchanged_count": 7
}
```

# Strategies for "current" target

When `snapshot_b=None` we read live state from `brain_adapter`. The
adapter can be:
  - a `str`/`Path` to a sin-brain SQLite DB (queried directly)
  - any object with `list_memories()` returning `[{id, content, kind}]`
  - `None` (returns empty `[]` — useful for testing)

# Algorithm

O(n) hash-by-id diff:
  - `added`     = new_ids − base_ids
  - `removed`   = base_ids − new_ids
  - `modified`  = intersection where content differs
  - `unchanged` = intersection where content matches

This is the standard "two-set diff with content comparison" and runs
in linear time on the size of the smaller snapshot.
"""
