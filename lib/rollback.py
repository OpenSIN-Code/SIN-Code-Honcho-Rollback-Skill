"""Purpose: Restore sin-brain to a previous snapshot.

Docs: rollback.doc.md
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .diff import diff_snapshots
from .storage import RollbackStorage, Snapshot

logger = logging.getLogger(__name__)


# Three restore strategies — chosen by the caller based on risk appetite.
STRATEGY_MERGE = "merge"     # add missing, update modified, keep added-since
STRATEGY_EXACT = "exact"     # delete all, restore exact snapshot state
STRATEGY_PATCH = "patch"     # only update modified, don't add/remove

_VALID_STRATEGIES = {STRATEGY_MERGE, STRATEGY_EXACT, STRATEGY_PATCH}


class RollbackExecutor:
    """Restore sin-brain (or any brain adapter) to a previous snapshot.

    The executor never touches sin-brain directly — it goes through
    `brain_adapter.remember()` and `brain_adapter.forget()`. This keeps
    the skill decoupled from sin-brain's internal storage.
    """

    def __init__(
        self,
        db_path: str = ".sin/rollback.db",
        brain_adapter: Any = None,
    ):
        self.storage = RollbackStorage(db_path)
        self.brain = brain_adapter

    def restore(
        self,
        snapshot_name: str,
        dry_run: bool = True,
        strategy: str = STRATEGY_MERGE,
    ) -> Dict[str, Any]:
        """Restore to a previous snapshot.

        Args:
            snapshot_name: which snapshot to restore to.
            dry_run: if True (default), plan actions but don't apply.
            strategy: one of "merge" (safe), "exact" (destructive), "patch".

        Returns:
            {
                "dry_run": bool,
                "snapshot": {...},
                "actions_planned": [...],
                "actions_taken": [...]   (only when not dry_run),
                "errors": [...],
            }

        On error (e.g. snapshot not found, no adapter wired), returns
        a dict with an "error" key instead of raising — agents reading
        JSON shouldn't have to wrap every call in try/except.
        """
        if strategy not in _VALID_STRATEGIES:
            return {
                "error": f"Invalid strategy '{strategy}'. "
                         f"Must be one of: {sorted(_VALID_STRATEGIES)}",
            }

        snap = self.storage.get_snapshot(snapshot_name)
        if not snap:
            return {"error": f"Snapshot '{snapshot_name}' not found"}

        if not self.brain:
            # Without a brain we can still plan, but not apply.
            return {
                "error": "No brain adapter wired — cannot actually restore.",
                "snapshot": snap.to_dict(),
                "dry_run": dry_run,
            }

        # Compute the diff: snapshot_a = current, snapshot_b = target.
        # In our API: snapshot_a is the "older" / "from", snapshot_b is
        # the "newer" / "to". So we pass target as A, current as B.
        diff = diff_snapshots(
            self.storage, snapshot_name, None, brain_adapter=self.brain,
        )

        actions = self._plan_actions(diff, strategy)

        if dry_run:
            return {
                "dry_run": True,
                "snapshot": snap.to_dict(),
                "strategy": strategy,
                "actions_planned": actions,
                "actions_taken": [],
                "errors": [],
            }

        # Apply actions one at a time so a single failure doesn't break
        # the rest. Each successful mutation is logged to the audit table.
        errors: List[Dict[str, Any]] = []
        for act in actions:
            try:
                if act["action"] == "forget":
                    self.brain.forget(act["memory_id"])
                elif act["action"] == "remember":
                    self.brain.remember(act["memory_id"], act["content"])
                self.storage.log_change(
                    action=act["action"],
                    memory_id=act.get("memory_id", ""),
                    old_content=act.get("old_content"),
                    new_content=act.get("content"),
                    source=f"rollback:{snapshot_name}",
                )
            except Exception as e:
                logger.error("rollback action failed: %s — %s", act, e)
                errors.append({"action": act, "error": str(e)})

        return {
            "dry_run": False,
            "snapshot": snap.to_dict(),
            "strategy": strategy,
            "actions_planned": actions,
            "actions_taken": actions if not errors else [
                a for a in actions if a not in [e["action"] for e in errors]
            ],
            "errors": errors,
        }

    @staticmethod
    def _plan_actions(diff: Dict[str, Any], strategy: str) -> List[Dict[str, Any]]:
        """Translate a diff into an action plan for the given strategy.

        "merge"  → re-add removed-since, update modified, keep added-since
        "exact"  → delete added-since, re-add removed-since, update modified
        "patch"  → only update modified (no add/remove)
        """
        actions: List[Dict[str, Any]] = []

        # `removed` here means "in the snapshot we want to restore to, but
        # not in the current state" → we need to re-add them.
        for m in diff.get("removed", []):
            if strategy in (STRATEGY_MERGE, STRATEGY_EXACT):
                actions.append({
                    "action": "remember",
                    "memory_id": m["id"],
                    "content": m["content"],
                })

        # `added` means "in current but not in target" → delete them.
        for m in diff.get("added", []):
            if strategy == STRATEGY_EXACT:
                actions.append({"action": "forget", "memory_id": m["id"]})

        # `modified` means "in both but content differs" → overwrite with
        # the TARGET (snapshot) value. The diff convention is `old` = A
        # (snapshot, what we want) and `new` = B (current, what we have).
        for m in diff.get("modified", []):
            if strategy in (STRATEGY_MERGE, STRATEGY_EXACT, STRATEGY_PATCH):
                actions.append({
                    "action": "remember",
                    "memory_id": m["id"],
                    # Restore to the snapshot value (= A = `old` in diff terms).
                    "content": m.get("old", m.get("new")),
                    "old_content": m.get("new"),
                })

        return actions
