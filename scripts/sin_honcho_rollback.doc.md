"""Purpose: sin-honcho-rollback CLI entry script.

Docs: scripts/sin_honcho_rollback.py

# Commands

| Command | What |
|---------|------|
| `sin-honcho-rollback snapshot NAME [--description ...]` | Create a snapshot |
| `sin-honcho-rollback list` | List all snapshots |
| `sin-honcho-rollback diff A [B]` | Diff two snapshots (or A vs current) |
| `sin-honcho-rollback restore NAME [--dry-run/--apply] [--strategy merge|exact|patch]` | Restore |
| `sin-honcho-rollback audit [--since-hours 24] [--limit 100]` | Audit log |
| `sin-honcho-rollback serve` | Start MCP server (stdio) |

# Output format

Every command emits JSON to stdout so it composes well with `jq` and
agent tooling. Errors are also JSON: `{"error": "..."}`.

# Run as a module

You can also invoke without installing:

```bash
python -m scripts.sin_honcho_rollback snapshot "test"
```
"""
