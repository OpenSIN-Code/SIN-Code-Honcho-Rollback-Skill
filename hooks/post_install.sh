#!/usr/bin/env bash
# Purpose: Post-install verification for sin-honcho-rollback.
# Docs: hooks/post_install.doc.md
#
# Run after `pip install -e .` to verify the install worked end-to-end:
#   - CLI is on PATH
#   - All subcommands work
#   - The MCP server starts and lists its 4 tools
#   - The lib package is importable
#
# Idempotent: safe to re-run.
#
# Usage:
#   hooks/post_install.sh [--skip-mcp] [--skip-cli]

set -euo pipefail

err()  { echo "[post-install] ERROR: $*" >&2; }
info() { echo "[post-install] $*"; }

SKIP_MCP=0
SKIP_CLI=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-mcp) SKIP_MCP=1; shift ;;
        --skip-cli) SKIP_CLI=1; shift ;;
        *) err "unknown arg: $1"; exit 1 ;;
    esac
done

# ── 1. Library importable ──────────────────────────────────────────

info "1/3 — Verifying lib package is importable"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if ! python3 -c "import sys; sys.path.insert(0, '$SKILL_DIR'); import lib; print('  lib version:', lib.__version__)" 2>/dev/null; then
    if ! python3 -c "import lib; print('  lib version:', lib.__version__)"; then
        err "lib package is not importable. Run 'pip install -e .' first."
        exit 1
    fi
fi

# ── 2. CLI subcommands ─────────────────────────────────────────────

if [[ $SKIP_CLI -eq 0 ]]; then
    info "2/3 — Verifying CLI is on PATH and works"
    if ! command -v sin-honcho-rollback >/dev/null 2>&1; then
        err "sin-honcho-rollback is not on PATH"
        exit 1
    fi

    TMPDIR="$(mktemp -d)"
    trap 'rm -rf "$TMPDIR"' EXIT
    DB="$TMPDIR/.sin/rollback.db"

    info "  creating test snapshot"
    sin-honcho-rollback snapshot "post-install-smoke" \
        --description "smoke test" --source "manual" \
        --db "$DB" >/dev/null

    info "  listing snapshots"
    sin-honcho-rollback list --db "$DB" >/dev/null

    info "  diffing (empty vs current)"
    sin-honcho-rollback diff "post-install-smoke" --db "$DB" >/dev/null

    info "  querying audit log"
    sin-honcho-rollback audit --since-hours 1 --db "$DB" >/dev/null

    info "  ✓ CLI smoke test passed"
else
    info "2/3 — Skipping CLI checks (--skip-cli)"
fi

# ── 3. MCP server (stdio JSON-RPC) ─────────────────────────────────

if [[ $SKIP_MCP -eq 0 ]]; then
    info "3/3 — Verifying MCP server starts and lists 4 tools"
    if ! python3 -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
        err "mcp[cli] not installed. Run: pip install -e .[mcp]"
        exit 1
    fi

    # Send a JSON-RPC initialize + tools/list to the server over stdio.
    REQUEST='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"post-install","version":"0.1.0"}}}'
    REQUEST2='{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

    RESPONSE="$( (printf '%s\n%s\n' "$REQUEST" "$REQUEST2"; sleep 1) \
        | sin-honcho-rollback serve 2>/dev/null \
        | head -50 )"

    if ! echo "$RESPONSE" | grep -q "rollback_snapshot"; then
        err "MCP server didn't advertise rollback_snapshot"
        echo "$RESPONSE" | head -20 >&2
        exit 1
    fi
    if ! echo "$RESPONSE" | grep -q "rollback_diff"; then
        err "MCP server didn't advertise rollback_diff"
        exit 1
    fi
    if ! echo "$RESPONSE" | grep -q "rollback_restore"; then
        err "MCP server didn't advertise rollback_restore"
        exit 1
    fi
    if ! echo "$RESPONSE" | grep -q "rollback_audit_log"; then
        err "MCP server didn't advertise rollback_audit_log"
        exit 1
    fi

    info "  ✓ MCP server smoke test passed (4/4 tools present)"
else
    info "3/3 — Skipping MCP check (--skip-mcp)"
fi

info ""
info "✓ sin-honcho-rollback post-install verification complete"
