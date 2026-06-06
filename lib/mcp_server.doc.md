"""Purpose: FastMCP server for sin-honcho-rollback.

Docs: lib/mcp_server.py

# 4 tools exposed

| Tool | Purpose |
|------|---------|
| `rollback_snapshot`   | Create a named snapshot |
| `rollback_diff`       | Diff between two snapshots or vs current |
| `rollback_restore`    | Restore to a previous snapshot |
| `rollback_audit_log`  | List memory changes in last N hours |

# Wiring up sin-brain

By default the MCP server runs with `brain_adapter=None`, which means
`rollback_restore` can PLAN a restore but not APPLY it. To enable
real rollback, call `set_brain_adapter(adapter)` in your agent's
bootstrap code:

```python
from lib.mcp_server import set_brain_adapter
from sin_brain import MemoryStore

set_brain_adapter(MemoryStore("sin-brain.db"))
```

# Transport

The server speaks MCP/JSON-RPC over stdio. Launch with:

```bash
sin-honcho-rollback serve
```

Then add the MCP server to your opencode.json or other MCP-aware
client config.

# Config

| Env var | Default | What |
|---------|---------|------|
| `SIN_ROLLBACK_DB` | `.sin/rollback.db` | Path to the SQLite DB file |
"""
