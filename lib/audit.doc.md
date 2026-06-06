"""Purpose: AuditLogger — read-only audit log of memory changes.

Docs: lib/audit.py

# Why read-only?

The audit log is the source of truth for "what changed in my memory,
and when". Allowing edits to the log would defeat the purpose — the
whole point is that `rollback_audit_log` answers forensic questions
like "what did the agent do at 03:00 last night?".

# Actions logged

| action | when |
|--------|------|
| `snapshot`  | a snapshot was created |
| `remember`  | a memory was added or updated |
| `forget`    | a memory was removed |
| `pin` / `unpin` | a memory was pinned for retention |
| `link`      | evidence-link created between memories |
| `rollback`  | a restore was performed |

# Storage

Backed by the `memory_changes` table in `.sin/rollback.db` (see
`lib/storage.py`). Append-only — entries are never updated or deleted,
even when their parent snapshot is removed. This is intentional: the
log captures the historical truth, not the current truth.
"""
