"""Purpose: sin-honcho-rollback package — adds time-travel to sin-brain.

Docs: README.md

# sin-honcho-rollback

Snapshot + rollback + audit log layer for `sin-brain` (and conceptually
for Honcho peer memory). Adds the missing "undo" capability.

## What's inside

| Module | What |
|--------|------|
| `lib/storage.py` | SQLite storage for `.sin/rollback.db` |
| `lib/snapshot.py` | create / list / delete snapshots |
| `lib/diff.py` | diff two snapshots or snapshot vs current |
| `lib/rollback.py` | restore a previous snapshot (merge/exact/patch) |
| `lib/audit.py` | read-only audit log of memory changes |
| `lib/mcp_server.py` | FastMCP server exposing 4 tools |
| `scripts/sin_honcho_rollback.py` | CLI (`sin-honcho-rollback`) |

## 4 MCP tools

| Tool | What |
|------|------|
| `rollback_snapshot` | Create named snapshot of current sin-brain state |
| `rollback_diff` | Diff two snapshots (or snapshot vs current) |
| `rollback_restore` | Restore to a previous snapshot |
| `rollback_audit_log` | List all memory changes in last N hours |

## CLI quick-reference

```bash
sin-honcho-rollback snapshot "before-refactor" --description "..."
sin-honcho-rollback list
sin-honcho-rollback diff "snap-a" "snap-b"
sin-honcho-rollback restore "snap-a" --dry-run
sin-honcho-rollback audit --since-hours 24
sin-honcho-rollback serve
```

## Storage

Per-project `.sin/rollback.db` (SQLite). Auto-created on first use.
Gitignored by convention — never commit your memory audit log.

## Versioning

Follows semver. v0.1.0 is the initial SOTA release.
"""
