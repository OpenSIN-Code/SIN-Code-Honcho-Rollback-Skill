---
name: sin-honcho-rollback
description: Snapshot + rollback + audit log for sin-brain / Honcho memory. Use when the agent says "take a snapshot", "create a checkpoint", "rollback memory", "what changed in memory", "undo memory change", "audit log of memory", "restore previous state of memory", or "diff between two memory states". Adds the missing "undo" capability to sin-brain — named snapshots, diff between any two points in time, restore to a previous state with 3 strategies (merge/exact/patch), and an append-only audit log of every memory mutation. Triggers on "snapshot", "rollback", "restore memory", "audit log", "memory diff", "undo remember", "checkpoint".
license: MIT
---

# sin-honcho-rollback

## What it does

Adds **time-travel** to your agent's memory. Today you can `forget_tool(id)` but there's no "undo" or "show me what changed yesterday". This skill provides:

- **Snapshots** — named checkpoints of memory state
- **Diff** — what changed between two snapshots
- **Restore** — roll back to a previous snapshot (3 strategies)
- **Audit log** — every memory change is logged

## Why

Agents make mistakes. They `remember()` wrong facts, overwrite good memories, or accumulate drift. Without rollback:

- A bad `remember()` corrupts future decisions forever
- No audit trail = no compliance
- No way to test "what would happen if I removed this memory"

## 4 MCP tools

| Tool | Purpose |
|------|---------|
| `rollback_snapshot` | Create named snapshot of current sin-brain state |
| `rollback_diff` | Show changes between 2 snapshots (or vs current) |
| `rollback_restore` | Restore to a previous snapshot |
| `rollback_audit_log` | List all memory changes in last N hours |

## Storage

Per-project `.sin/rollback.db` (SQLite). Auto-created on first use. Gitignored by convention — never commit your memory audit log.

## When to use this skill

| Trigger phrase | Use case |
|----------------|----------|
| "take a snapshot" / "checkpoint" | Capture current state before risky op |
| "rollback" / "restore previous" | Undo a series of bad memory writes |
| "what changed" / "memory diff" | Audit what the agent did between two points |
| "audit log" / "memory history" | See all mutations in the last N hours |
| "undo my last remember" | Quick revert of a single bad fact |

**Do not** use this skill for:

- Code rollback (use `git` / `git-immortal-commit` skill)
- Configuration rollback (use your config-management tool)
- sin-brain's own operational state (the brain handles its own retention)

## Install

```bash
cd ~/.config/opencode/skills/sin-honcho-rollback
pip install -e .
pip install -e .[mcp]   # for the MCP server
pip install -e .[brain] # to wire up real sin-brain rollback
```

## Usage

### CLI

```bash
sin-honcho-rollback snapshot "before-refactor" --description "Pre-auth-refactor state"
sin-honcho-rollback list
sin-honcho-rollback diff "before-refactor"                    # vs current
sin-honcho-rollback diff "snap1" "snap2"                      # between two snapshots
sin-honcho-rollback restore "before-refactor" --dry-run       # safe default
sin-honcho-rollback restore "before-refactor" --apply --strategy=merge
sin-honcho-rollback audit --since-hours 24
sin-honcho-rollback serve                                     # MCP server (stdio)
```

### MCP (from agent)

```python
# Before risky operation
rollback_snapshot("before-risk-1", "About to refactor auth")

# ... agent does work, maybe wrong ...

# Check what changed
rollback_diff("before-risk-1", "")  # empty = vs current

# If bad, undo (default: dry-run, safe)
plan = rollback_restore("before-risk-1", dry_run=True)
print(plan)  # see what would change

# Apply if it looks right
rollback_restore("before-risk-1", dry_run=False, strategy="merge")
```

### Programmatic (from a script or test)

```python
from lib.storage import RollbackStorage
from lib.snapshot import SnapshotManager

storage = RollbackStorage(".sin/rollback.db")
mgr = SnapshotManager(brain_adapter="path/to/sin-brain.db")
snap = mgr.create("v1.0", "Release v1.0 memory state")
```

## Strategies

| Strategy | Behavior | Risk |
|----------|----------|------|
| **merge** (default, safe) | Add what was missing, update what changed, keep what was added since | Low |
| **exact** (destructive) | Delete all current, restore exact snapshot state | High |
| **patch** (gentle) | Only update modified entries, don't add/remove | Lowest |

## Files

- `SKILL.md` — this file
- `README.md` — user-facing docs
- `CHANGELOG.md` — version history
- `scripts/sin_honcho_rollback.py` — CLI + MCP entry
- `lib/storage.py` — SQLite ops
- `lib/snapshot.py` — create/list/delete
- `lib/diff.py` — compare two states
- `lib/rollback.py` — restore with strategy
- `lib/audit.py` — read-only log
- `lib/mcp_server.py` — FastMCP (4 tools)
- `tests/` — pytest test suite
- `examples/good.py` / `examples/bad.py` — usage patterns
- `templates/cron_rollback.sh` — auto-snapshot via cron
- `hooks/post_install.sh` — post-install verification
- `pyproject.toml` — package config

## Version

`0.1.0` — initial SOTA release.
