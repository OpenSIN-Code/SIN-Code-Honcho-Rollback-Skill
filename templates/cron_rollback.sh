#!/usr/bin/env bash
# Purpose: Auto-snapshot sin-brain state on a schedule (cron-ready).
# Docs: templates/cron_rollback.doc.md
#
# Installs a cron job that creates a daily snapshot of the project's
# sin-brain state. Run once, then forget — the skill handles the rest.
#
# Usage:
#   templates/cron_rollback.sh install [--project /path] [--time "03:00"]
#   templates/cron_rollback.sh uninstall [--project /path]
#   templates/cron_rollback.sh run [--project /path]   # for testing
#
# Exit codes:
#   0   success
#   1   sin-honcho-rollback not on PATH
#   2   cron not available
#   3   install/uninstall failed
#
# Cron expression format: "MIN HOUR DOM MON DOW" — see `man 5 crontab`.

set -euo pipefail

CRON_TAG="sin-honcho-rollback-auto"
DEFAULT_TIME="03:00"
DEFAULT_HOUR=3
DEFAULT_MIN=0
MAX_SNAPSHOTS_TO_KEEP=30  # prune anything older than this

# ── Helpers ─────────────────────────────────────────────────────────

err() { echo "[cron_rollback] ERROR: $*" >&2; }
info() { echo "[cron_rollback] $*"; }

require_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        err "$1 is required"
        exit 1
    fi
}

# ── Run-once (for testing or the actual cron line) ─────────────────

cmd_run() {
    local project="."
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --project) project="$2"; shift 2 ;;
            *) err "unknown arg: $1"; exit 1 ;;
        esac
    done

    require_tool sin-honcho-rollback
    cd "$project"

    local name
    # ISO-ish name with colons stripped (cron + sqlite are picky)
    name="auto-$(date -u +%Y%m%dT%H%M%SZ)"

    info "creating snapshot: $name (project: $project)"
    sin-honcho-rollback snapshot "$name" \
        --description "Auto-snapshot via cron_rollback.sh" \
        --source "auto-scheduled" \
        --db ".sin/rollback.db"

    # Prune old auto-snapshots beyond MAX_SNAPSHOTS_TO_KEEP
    sin-honcho-rollback list --db .sin/rollback.db \
        | python3 -c "
import json, sys, subprocess
data = json.load(sys.stdin)
snaps = [s for s in data.get('snapshots', []) if s.get('source') == 'auto-scheduled']
snaps.sort(key=lambda s: s['id'], reverse=True)
for s in snaps[$MAX_SNAPSHOTS_TO_KEEP:]:
    print(s['name'])
" | while read -r old; do
        if [[ -n "$old" ]]; then
            info "pruning old snapshot: $old"
            # We don't have a 'delete' subcommand yet; this is a no-op for now.
            # TODO: add `sin-honcho-rollback delete <name>`.
            :
        fi
    done
}

# ── Install (write to crontab) ──────────────────────────────────────

cmd_install() {
    local project="."
    local time_spec="$DEFAULT_TIME"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --project) project="$2"; shift 2 ;;
            --time) time_spec="$2"; shift 2 ;;
            *) err "unknown arg: $1"; exit 1 ;;
        esac
    done

    require_tool crontab
    require_tool sin-honcho-rollback

    local hour="${time_spec%%:*}"
    local min="${time_spec##*:}"

    # Build the cron line. Use full paths to avoid PATH surprises in cron.
    local script_path
    script_path="$(cd "$(dirname "$0")" && pwd)/cron_rollback.sh"
    local cron_line
    cron_line="$min $hour * * * /usr/bin/env bash $script_path run --project $project"

    # Append (idempotent: check tag first)
    local existing
    existing="$(crontab -l 2>/dev/null || true)"
    if echo "$existing" | grep -qF "$CRON_TAG"; then
        info "cron entry already installed"
        echo "$existing" | grep -F "$CRON_TAG"
        return 0
    fi

    {
        echo "$existing"
        echo "# $CRON_TAG"
        echo "$cron_line"
    } | crontab -

    info "installed cron: $cron_line"
}

# ── Uninstall (remove from crontab) ─────────────────────────────────

cmd_uninstall() {
    require_tool crontab

    local existing
    existing="$(crontab -l 2>/dev/null || true)"
    if ! echo "$existing" | grep -qF "$CRON_TAG"; then
        info "no cron entry tagged '$CRON_TAG' found"
        return 0
    fi

    echo "$existing" | grep -vF "$CRON_TAG" | crontab -
    info "removed cron entries tagged '$CRON_TAG'"
}

# ── Dispatch ────────────────────────────────────────────────────────

if [[ $# -lt 1 ]]; then
    err "usage: $0 {install|uninstall|run} [--project DIR] [--time HH:MM]"
    exit 1
fi

subcommand="$1"
shift

case "$subcommand" in
    install)   cmd_install   "$@" ;;
    uninstall) cmd_uninstall "$@" ;;
    run)       cmd_run       "$@" ;;
    *)
        err "unknown subcommand: $subcommand"
        exit 1
        ;;
esac
