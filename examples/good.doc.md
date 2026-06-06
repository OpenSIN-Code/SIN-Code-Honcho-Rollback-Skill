"""Purpose: Good example — proper snapshot/rollback workflow.

Docs: examples/good.py

# Run it

```bash
python examples/good.py
```

Expected output: a baseline snapshot is created, the brain is mutated
(the "risky work"), the diff shows what changed, and the rollback
restores the original state.

# The pattern

1. **Snapshot before risky work** — never modify memory without a way back.
2. **Dry-run before apply** — see the plan, then commit.
3. **Use `merge` as the default strategy** — it's safe and additive.
"""
