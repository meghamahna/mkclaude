#!/usr/bin/env python3
"""Stop: one combined end-of-turn check (knowledge graph upkeep + cleanup of leftovers).

Blocks at most once per stop (stop_hook_active), with every pending instruction in one message.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, HERE)
from common import emit, run_soft  # noqa: E402
import housekeeping  # noqa: E402
import kg_hooks  # noqa: E402


def main(event):
    reasons = [r for r in (kg_hooks.stop_reason(event), housekeeping.stop_reason(event)) if r]
    if reasons:
        emit({"decision": "block", "reason": " ".join(reasons)})


if __name__ == "__main__":
    run_soft(main)
