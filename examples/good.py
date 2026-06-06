"""Purpose: Example — proper snapshot+rollback workflow for a real project.

Docs: examples/good.doc.md

This is the pattern you should follow in your agent or CI:

  1. Snapshot before a risky batch of memory writes
  2. Do the work
  3. If anything looks wrong, dry-run the rollback
  4. If the plan is correct, apply

Run from the project root:
    python examples/good.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `lib` importable when running this file directly.
_SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from lib.diff import diff_snapshots  # noqa: E402
from lib.rollback import RollbackExecutor  # noqa: E402
from lib.snapshot import SnapshotManager  # noqa: E402
from lib.storage import RollbackStorage  # noqa: E402


class InMemoryBrain:
    """A toy brain adapter that demonstrates the interface."""

    def __init__(self):
        self.memories = {
            "user-name": "Jeremy",
            "user-prefers": "tabs",
            "project-stack": "Python/aiohttp",
        }

    def list_memories(self):
        return [
            {"id": k, "content": v, "kind": "fact"} for k, v in self.memories.items()
        ]

    def remember(self, memory_id, content):
        self.memories[memory_id] = content

    def forget(self, memory_id):
        self.memories.pop(memory_id, None)


def main() -> None:
    db = ".sin/rollback.db"
    brain = InMemoryBrain()
    storage = RollbackStorage(db)
    mgr = SnapshotManager(brain_adapter=brain)

    # 1) Snapshot the current state
    print("→ Creating baseline snapshot")
    snap = mgr.create(
        "baseline",
        description="State before risky batch",
        source="manual",
        metadata={"tag": "example", "version": "1.0"},
    )
    print(f"  snapshot id={snap.id} count={snap.memory_count} hash={snap.memory_hash}")

    # 2) Do the risky work
    print("\n→ Mutating brain (the 'risky work')")
    brain.remember("user-name", "BOOM-corrupted")
    brain.forget("user-prefers")
    brain.remember("new-fact", "this is fine")

    # 3) Audit what changed
    print("\n→ Diff between baseline and current:")
    diff = diff_snapshots(storage, "baseline", None, brain_adapter=brain)
    print(f"  added:    {[m['id'] for m in diff['added']]}")
    print(f"  removed:  {[m['id'] for m in diff['removed']]}")
    print(f"  modified: {[m['id'] for m in diff['modified']]}")

    # 4) Dry-run the rollback
    print("\n→ Dry-run rollback to baseline (strategy=merge)")
    executor = RollbackExecutor(brain_adapter=brain)
    plan = executor.restore("baseline", dry_run=True, strategy="merge")
    print(f"  actions planned: {len(plan['actions_planned'])}")

    # 5) Apply
    print("\n→ Applying rollback")
    result = executor.restore("baseline", dry_run=False, strategy="merge")
    print(f"  errors: {result['errors']}")
    print(f"  brain is now: {brain.memories}")


if __name__ == "__main__":
    main()
