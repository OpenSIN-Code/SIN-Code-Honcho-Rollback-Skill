"""Purpose: Post-install verification script.

Docs: hooks/post_install.sh

# What it checks

| Step | What | Skip flag |
|------|------|-----------|
| 1 | `lib` package is importable, version is reported | — |
| 2 | CLI: `snapshot`, `list`, `diff`, `audit` all work end-to-end | `--skip-cli` |
| 3 | MCP server starts and advertises 4 tools | `--skip-mcp` |

# Usage

```bash
# Run all checks
hooks/post_install.sh

# Skip MCP check (e.g. mcp not installed yet)
hooks/post_install.sh --skip-mcp
```

The script is idempotent — it creates a fresh tmpdir each run, so no
state leaks between calls.
"""
