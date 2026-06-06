"""Purpose: RollbackExecutor — restore memory to a previous snapshot.

Docs: lib/rollback.py

# Three strategies

| Strategy | Behavior | Risk |
|----------|----------|------|
| `merge` (default) | Add what was missing in target, update modified, keep added-since | Low |
| `exact` | Delete added-since, re-add removed-since, update modified | High |
| `patch` | Only update modified entries (no add/remove) | Lowest |

# Default to dry-run

`restore()` defaults to `dry_run=True` — agents should always see the
plan before applying. To actually apply:

```python
executor = RollbackExecutor(brain_adapter=adapter)
plan = executor.restore("pre-refactor")        # dry run
applied = executor.restore("pre-refactor", dry_run=False, strategy="merge")
```

# Decoupling from sin-brain

`RollbackExecutor` never imports sin-brain. It talks to whatever
`brain_adapter` you give it via two methods:
  - `remember(memory_id, content) -> None`
  - `forget(memory_id) -> None`

This means the same executor can roll back sin-brain, Honcho peer
cards, or any other system with a compatible interface.
"""
