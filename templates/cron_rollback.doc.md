"""Purpose: Cron template for auto-snapshotting sin-brain state.

Docs: templates/cron_rollback.sh

# Install

```bash
chmod +x templates/cron_rollback.sh
./templates/cron_rollback.sh install --project ~/dev/myproject --time "03:00"
```

This adds a single line to your crontab:

```
# sin-honcho-rollback-auto
0 3 * * * /usr/bin/env bash /path/to/cron_rollback.sh run --project /path/to/project
```

# Uninstall

```bash
./templates/cron_rollback.sh uninstall
```

# Run manually (for testing)

```bash
./templates/cron_rollback.sh run --project .
```

# What it does

1. Creates a snapshot named `auto-<UTC-ISO>` in the project's `.sin/rollback.db`
2. Tags it with `source: "auto-scheduled"` in the audit log
3. (Future) prunes snapshots beyond `MAX_SNAPSHOTS_TO_KEEP=30`

# Why not a hook into opencode?

cron is the right tool for "do X every day at 3am, regardless of
whether the agent is running". Skills that need agent-coordination
should subscribe to audit-log events instead.
"""
