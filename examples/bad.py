"""Purpose: Example — anti-patterns to avoid with sin-honcho-rollback.

Docs: examples/bad.doc.md

This file shows the WRONG ways to use the skill. Each section is
followed by a comment explaining why it's bad and what to do instead.

DO NOT COPY THIS INTO PRODUCTION. It is here purely as a teaching aid.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from lib.rollback import RollbackExecutor  # noqa: E402
from lib.snapshot import SnapshotManager  # noqa: E402


class DemoBrain:
    def __init__(self):
        self.memories = {"x": "old"}

    def list_memories(self):
        return [{"id": k, "content": v, "kind": "fact"} for k, v in self.memories.items()]

    def remember(self, memory_id, content):
        self.memories[memory_id] = content

    def forget(self, memory_id):
        self.memories.pop(memory_id, None)


def main() -> None:
    brain = DemoBrain()

    # ── BAD #1: Mutate brain without a snapshot ──────────────────
    # Why bad: if the mutation is wrong, you have no way to recover.
    # Instead: ALWAYS create a snapshot before a batch of changes.
    print("BAD #1: mutating without snapshot")
    brain.remember("x", "BOOM-uncorrectable")  # No snapshot → no rollback
    print(f"  brain is now: {brain.memories}  (no way to undo)")

    # Reset for next example
    brain = DemoBrain()
    mgr = SnapshotManager(brain_adapter=brain)
    mgr.create("baseline", source="manual")

    # ── BAD #2: Apply rollback without dry-run ───────────────────
    # Why bad: you skip the safety check. The action plan may include
    # things you didn't expect (e.g. forgetting memories you actually
    # wanted to keep).
    # Instead: dry-run first, inspect, then apply.
    print("\nBAD #2: apply without dry-run")
    brain.remember("x", "v2")
    executor = RollbackExecutor(brain_adapter=brain)
    executor.restore("baseline", dry_run=False)  # ← skipped dry-run!
    print(f"  brain is now: {brain.memories}  (you had no chance to review)")

    # Reset
    brain = DemoBrain()
    brain.remember("x", "v2")
    brain.remember("y", "fresh")
    executor = RollbackExecutor(brain_adapter=brain)

    # ── BAD #3: Use `exact` strategy by default ───────────────────
    # Why bad: `exact` DELETES all current state and restores the
    # snapshot. If the agent has been doing good work since the
    # snapshot, all of that is lost.
    # Instead: use `merge` (safe) unless you really mean to wipe.
    print("\nBAD #3: exact strategy by default")
    print(f"  before: {brain.memories}")
    executor.restore("baseline", dry_run=False, strategy="exact")
    print(f"  after:  {brain.memories}  ('y' was lost — should have used merge)")

    # ── BAD #4: Non-unique snapshot names ────────────────────────
    # Why bad: the storage layer rejects duplicates, so you'll get a
    # confusing error in the middle of an agent loop.
    # Instead: include a timestamp or hash in the snapshot name.
    print("\nBAD #4: hardcoded snapshot names")
    mgr2 = SnapshotManager(brain_adapter=brain)
    try:
        mgr2.create("baseline", source="manual")  # ← already exists
    except Exception as e:
        print(f"  raised: {type(e).__name__}: {e}")
        print("  fix: use f'baseline-{datetime.now().isoformat()}' or similar")


if __name__ == "__main__":
    main()
