"""Purpose: Bad example — anti-patterns to avoid.

Docs: examples/bad.py

# Don't do these things

| # | Anti-pattern | Why |
|---|--------------|-----|
| 1 | Mutate without snapshot | No way to recover |
| 2 | Skip dry-run | You commit to changes you haven't reviewed |
| 3 | Use `exact` by default | Destructive — wipes all current work |
| 4 | Hardcoded snapshot names | Duplicates will fail confusingly mid-loop |

# Run it (purely to see the errors)

```bash
python examples/bad.py
```
"""
