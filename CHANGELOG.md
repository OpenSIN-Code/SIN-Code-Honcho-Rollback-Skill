# Changelog

All notable changes to `sin-honcho-rollback` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-06-05

### Added

- Initial SOTA release.
- `RollbackStorage` — SQLite storage layer with two tables (`snapshots`, `memory_changes`).
- `SnapshotManager` — create / list / delete named snapshots.
- `diff_snapshots()` — O(n) hash-by-id diff with `added` / `removed` / `modified` / `unchanged_count` output.
- `RollbackExecutor` — restore with three strategies (`merge`, `exact`, `patch`); defaults to `dry_run=True`.
- `AuditLogger` — read-only view of the append-only `memory_changes` table.
- FastMCP server exposing 4 tools:
  - `rollback_snapshot(name, description)`
  - `rollback_diff(snapshot_a, snapshot_b)`
  - `rollback_restore(snapshot_name, dry_run, strategy)`
  - `rollback_audit_log(since_hours, limit)`
- CLI: `sin-honcho-rollback` with `snapshot` / `list` / `diff` / `restore` / `audit` / `serve` subcommands.
- CoDocs (`.doc.md` companions) for every code file.
- `examples/good.py` and `examples/bad.py`.
- `templates/cron_rollback.sh` — auto-snapshot via cron.
- `hooks/post_install.sh` — post-install verification.
- Pytest test suite (5 files, ~30 tests).
