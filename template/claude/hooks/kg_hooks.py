#!/usr/bin/env python3
"""Knowledge-graph upkeep hooks.

  kg_hooks.py track  (PostToolUse Write|Edit|MultiEdit|NotebookEdit) -> record edited paths
  kg_hooks.py stop   (Stop)  -> if pending changes are significant, block once and ask the
                                main agent to delegate a KG update to knowledge-keeper.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from common import emit, load_config, project_dir, rel_to, run_soft, state_dir  # noqa: E402
import kg as kgmod  # noqa: E402


def track(event):
    proj = project_dir(event)
    ti = event.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        return
    rel = rel_to(proj, path)
    if rel.startswith("..") or rel.startswith(".claude/"):
        return
    with open(os.path.join(state_dir(proj), "kg-pending"), "a", encoding="utf-8") as fh:
        fh.write(rel + "\n")


def stop(event):
    reason = stop_reason(event)
    if reason:
        emit({"decision": "block", "reason": reason})


def stop_reason(event):
    """The [harness:kg] instruction when pending edits matter, else None."""
    if event.get("stop_hook_active"):
        return None  # already continued once for this stop; never loop
    proj = project_dir(event)
    cfg = load_config(proj)["knowledge"]
    kg = kgmod.KG(proj)
    pending = [p for p in kgmod.read_pending(kg) if not kgmod.is_ignored(kg, p)]
    obsolete = kgmod.obsolete_nodes(kg)
    ref = kgmod.referencing(kg)
    referenced = [p for p in pending if p in ref or any(p.startswith(d + "/") and d.count("/") >= 1 for d in ref)]
    # Edits in areas the graph does not cover yet wait until enough files are pending, so a small change
    # does not force an extra turn.
    if not (obsolete or referenced or len(pending) >= int(cfg["pending_trigger_count"])):
        return None
    parts = []
    if pending:
        parts.append("Changed: " + ", ".join(pending[:12]) + (f" (+{len(pending) - 12} more)" if len(pending) > 12 else ""))
    if obsolete:
        parts.append("Obsolete nodes (sources deleted): " + ", ".join(obsolete[:12]))
    return (
        "[harness:kg] Knowledge graph update needed before finishing. " + ". ".join(parts) + ". "
        "Delegate to the `knowledge-keeper` subagent with: \"Update the KG for pending changes "
        "(run `python3 .claude/tools/kg.py pending` and `kg.py prune`). Record only major info (architecture, modules, "
        "entry points, APIs, data models, commands, decisions, gotchas) with path:line pointers, remove what is "
        "obsolete, then run `kg.py index && kg.py validate` and `kg.py pending --clear`.\" If nothing major changed "
        "and nothing is obsolete, just run `python3 .claude/tools/kg.py pending --clear`. Then finish your reply with a "
        "1-3 line recap of the outcome (not the full answer again) and one line on the KG update.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    run_soft({"track": track, "stop": stop}.get(mode, lambda e: None))
