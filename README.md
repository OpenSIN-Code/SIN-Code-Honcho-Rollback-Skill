# sin-honcho-rollback

Snapshot + rollback + audit log layer for `sin-brain` and Honcho peer memory. Adds the missing "undo" capability to agent memory.

## Quick-start

```bash
# Install
cd ~/.config/opencode/skills/sin-honcho-rollback
pip install -e .
pip install -e .[mcp]   # for the MCP server
pip install -e .[brain] # to wire up real sin-brain rollback

# Use
sin-honcho-rollback snapshot "before-refactor" --description "Pre-auth state"
sin-honcho-rollback list
sin-honcho-rollback diff "before-refactor"
sin-honcho-rollback restore "before-refactor" --dry-run
sin-honcho-rollback audit --since-hours 24
```

## What it does

Agents are fallible. A bad `remember()` call writes garbage into long-term memory and pollutes every future decision. Without rollback, there's no way back.

`sin-honcho-rollback` adds four things to sin-brain (and conceptually to Honcho peer memory):

1. **Named snapshots** — checkpoint memory state at any point in time
2. **Diff** — see what changed between any two snapshots
3. **Restore** — roll back, with three strategies:
   - `merge` (default, safe) — re-add what was missing, update modified, keep what was added since
   - `exact` (destructive) — delete all current, restore exact snapshot state
   - `patch` (gentle) — only update modified entries
4. **Audit log** — append-only log of every memory mutation

## Storage

Per-project `.sin/rollback.db` (SQLite). Auto-created on first use. Gitignore it.

```
.sin/rollback.db
├── snapshots       — name, description, created_at, memory_count, memory_hash
└── memory_changes  — timestamp, action, memory_id, old_content, new_content
```

The audit log is **append-only** — entries are never updated or deleted, even when their parent snapshot is removed.

## Architecture

```
MCP/JSON-RPC (4 tools)
    ↓
SnapshotManager / diff_snapshots / RollbackExecutor / AuditLogger
    ↓
RollbackStorage (.sin/rollback.db, SQLite)
    ↓
brain_adapter (sin-brain | Honcho | custom)
```

The skill is decoupled from sin-brain's internals. The `brain_adapter` interface is:

```python
class BrainAdapter:
    def list_memories(self) -> list[dict]: ...
    def remember(self, memory_id: str, content: str) -> None: ...
    def forget(self, memory_id: str) -> None: ...
```

Any system that implements this interface can be rolled back. sin-brain comes with a built-in adapter that reads `.db` files directly.

## 4 MCP tools

| Tool | What it does |
|------|--------------|
| `rollback_snapshot` | Create a named snapshot |
| `rollback_diff` | Diff two snapshots (or vs current) |
| `rollback_restore` | Restore to a previous snapshot |
| `rollback_audit_log` | List memory changes in last N hours |

## CLI commands

| Command | Purpose |
|---------|---------|
| `sin-honcho-rollback snapshot NAME [--description ...]` | Create snapshot |
| `sin-honcho-rollback list` | List all snapshots |
| `sin-honcho-rollback diff A [B]` | Diff snapshots (or A vs current) |
| `sin-honcho-rollback restore NAME [--dry-run/--apply]` | Restore |
| `sin-honcho-rollback audit [--since-hours 24]` | Audit log |
| `sin-honcho-rollback serve` | MCP server (stdio) |

All commands emit JSON to stdout.

## Development

```bash
pip install -e .[test]
pytest
```

## License

MIT
