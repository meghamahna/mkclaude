import json
import os
import shutil
import subprocess
import sys
import unittest

import re

from helpers import FAKE, TOOLS, run_hook, slurp, spit, tmp_project


def write_transcript(path, used, model="claude-opus-5-5", sidechain_used=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    recs = [{"type": "user", "message": {"content": "hi"}}]
    if sidechain_used:
        recs.append({"type": "assistant", "isSidechain": True,
                     "message": {"model": model, "usage": {"input_tokens": sidechain_used}}})
    recs.append({"type": "assistant", "isSidechain": False, "requestedModel": model,
                 "message": {"model": model, "usage": {"input_tokens": 2, "cache_read_input_tokens": used - 102,
                                                       "cache_creation_input_tokens": 50, "output_tokens": 50}}})
    with open(path, "w") as fh:
        fh.write("\n".join(json.dumps(r) for r in recs) + "\n")


class TestContextGuard(unittest.TestCase):
    def setUp(self):
        self.proj = tmp_project()
        self.tp = os.path.join(self.proj, "t", "sess.jsonl")

    def tearDown(self):
        shutil.rmtree(self.proj)

    def ctx(self, **ev):
        out = run_hook("context_guard.py", {"hook_event_name": "PostToolUse", "transcript_path": self.tp, **ev}, self.proj)
        return (out.get("hookSpecificOutput") or {}).get("additionalContext", "")

    def test_thresholds_main(self):
        write_transcript(self.tp, 30_000)
        self.assertEqual(self.ctx(), "")
        write_transcript(self.tp, 101_000)
        self.assertEqual(self.ctx(), "")  # 50% is under the default budget
        write_transcript(self.tp, 141_000)
        self.assertIn("WARN 70%", self.ctx())
        self.assertEqual(self.ctx(), "")  # warn only once
        write_transcript(self.tp, 151_000)
        msg = self.ctx()
        self.assertIn("LIMIT 76%", msg)
        self.assertIn("orchestrator", msg)
        self.assertEqual([bool(self.ctx()) for _ in range(25)], [False] * 24 + [True])  # reminded every 25th call
        write_transcript(self.tp, 30_000)  # new session, /clear or compaction
        self.assertEqual(self.ctx(), "")
        write_transcript(self.tp, 141_000)
        self.assertIn("WARN", self.ctx())  # warns again

    def test_subagent_limit_repeats_every_call(self):
        write_transcript(os.path.join(self.proj, "t", "sess", "subagents", "agent-abc.jsonl"), 160_000)
        self.assertTrue(all("LIMIT" in self.ctx(agent_id="abc", agent_type="coding-agent") for _ in range(3)))

    def test_ignores_sidechain_in_main(self):
        write_transcript(self.tp, 10_000, sidechain_used=150_000)
        self.assertEqual(self.ctx(), "")

    def test_subagent_transcript(self):
        write_transcript(self.tp, 10_000)
        write_transcript(os.path.join(self.proj, "t", "sess", "subagents", "agent-abc.jsonl"), 160_000)
        msg = self.ctx(agent_id="abc", agent_type="coding-agent")
        self.assertIn("LIMIT 80%", msg)
        self.assertIn("STATUS: HANDOFF", msg)
        self.assertIn("coding-agent", msg)

    def test_statusline_window_size(self):
        write_transcript(self.tp, 160_000)
        os.makedirs(os.path.join(self.proj, ".claude", "state"), exist_ok=True)
        with open(os.path.join(self.proj, ".claude", "state", "window-s1.json"), "w") as fh:
            json.dump({"window": 1_000_000}, fh)
        self.assertEqual(self.ctx(session_id="s1"), "")  # 16% of 1M
        self.assertIn("LIMIT", self.ctx(session_id="other"))  # 80% of 200k

    def test_override_window(self):
        with open(os.path.join(self.proj, ".claude", "harness.json"), "w") as fh:
            json.dump({"context": {"window_tokens": 400_000}}, fh)
        write_transcript(self.tp, 150_000)
        self.assertEqual(self.ctx(), "")


class TestHandoffWatch(unittest.TestCase):
    def setUp(self):
        self.proj = tmp_project()

    def tearDown(self):
        shutil.rmtree(self.proj)

    def test_respawn_instruction(self):
        resp = {"content": [{"type": "text", "text": "STATUS: HANDOFF .claude/knowledge/handoffs/coding-agent-1.md\nSUMMARY: x"}]}
        out = run_hook("handoff_watch.py", {"tool_name": "Agent", "tool_input": {"subagent_type": "coding-agent"},
                                            "tool_response": resp}, self.proj)
        msg = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("FRESH `coding-agent`", msg)
        self.assertIn("handoffs/coding-agent-1.md", msg)

    def test_pending_parent_write(self):
        out = run_hook("handoff_watch.py", {"tool_name": "Agent", "tool_input": {"subagent_type": "code-reviewer"},
                                            "tool_response": "STATUS: HANDOFF pending-parent-write"}, self.proj)
        self.assertIn("save the handoff content", out["hookSpecificOutput"]["additionalContext"])

    def test_done_is_silent(self):
        self.assertEqual(run_hook("handoff_watch.py", {"tool_name": "Agent", "tool_response": "STATUS: DONE"}, self.proj), {})


def kg(proj, *args):
    return subprocess.run([sys.executable, os.path.join(TOOLS, "kg.py"), "--root", proj, *args],
                          capture_output=True, text=True)


class TestKnowledgeGraph(unittest.TestCase):
    def setUp(self):
        self.proj = tmp_project()
        os.makedirs(os.path.join(self.proj, "src", "auth"))
        with open(os.path.join(self.proj, "src", "auth", "jwt.py"), "w") as fh:
            fh.write("\n".join(f"line {i}" for i in range(1, 101)) + "\n")
        with open(os.path.join(self.proj, "README.md"), "w") as fh:
            fh.write("# Demo\n\n## Setup\n")

    def tearDown(self):
        shutil.rmtree(self.proj)

    def test_seed_index_query_validate(self):
        self.assertEqual(kg(self.proj, "seed").returncode, 0)
        r = kg(self.proj, "upsert", "module-auth-jwt", "--kind", "module", "--summary", "JWT issue and verify",
               "--tags", "auth,jwt", "--sources", "src/auth/jwt.py:10-40", "--links", "depends_on:architecture-overview")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(kg(self.proj, "index").returncode, 0)
        idx = slurp(os.path.join(self.proj, ".claude", "knowledge", "INDEX.md"))
        self.assertIn("**module-auth-jwt**", idx)
        self.assertIn("src/auth/jwt.py:10-40", idx)
        q = kg(self.proj, "query", "jwt")
        self.assertTrue(q.stdout.startswith("module-auth-jwt"), q.stdout)
        v = kg(self.proj, "validate")
        self.assertEqual(v.returncode, 0, v.stdout)
        nb = kg(self.proj, "neighbors", "module-auth-jwt")
        self.assertIn("architecture-overview", nb.stdout)
        graph = json.loads(slurp(os.path.join(self.proj, ".claude", "knowledge", "graph.json")))
        self.assertIn({"from": "module-auth-jwt", "to": "architecture-overview", "type": "depends_on"}, graph["edges"])

    def test_validate_catches_errors(self):
        kg(self.proj, "upsert", "module-a", "--kind", "module", "--summary", "A",
           "--sources", "src/auth/jwt.py:90-500,src/missing.py", "--links", "calls:module-ghost")
        kg(self.proj, "index")
        out = kg(self.proj, "validate")
        self.assertEqual(out.returncode, 1)
        for needle in ("past end of file", "source missing", "dangling link"):
            self.assertIn(needle, out.stdout)

    def test_index_line_cap(self):
        with open(os.path.join(self.proj, ".claude", "harness.json"), "w") as fh:
            json.dump({"knowledge": {"max_index_lines": 40}}, fh)
        for i in range(60):
            kg(self.proj, "upsert", f"module-m{i}", "--kind", "module", "--summary", f"module {i}", "--tags", f"t{i}")
        kg(self.proj, "index")
        idx = slurp(os.path.join(self.proj, ".claude", "knowledge", "INDEX.md")).splitlines()
        self.assertLessEqual(len(idx), 40)
        self.assertTrue(any("more" in l for l in idx))

    def edit(self, rel):
        run_hook("kg_hooks.py", {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(self.proj, rel)}}, self.proj, "track")

    def test_pending_and_stop_hook(self):
        kg(self.proj, "upsert", "module-auth-jwt", "--kind", "module", "--summary", "JWT", "--sources", "src/auth/jwt.py:1-5")
        self.edit("src/auth/jwt.py")
        self.edit("tests/t.py")
        self.assertIn("module-auth-jwt", kg(self.proj, "pending").stdout)
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop"), {})  # one covered edit waits for a batch
        for rel in ("src/a.py", "src/b.py", "src/c.py", "src/d.py"):
            self.edit(rel)
        out = run_hook("kg_hooks.py", {"hook_event_name": "Stop"}, self.proj, "stop")
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("knowledge-keeper", out["reason"])
        self.assertNotIn("tests/t.py", out["reason"])
        self.assertEqual(run_hook("kg_hooks.py", {"stop_hook_active": True}, self.proj, "stop"), {})
        kg(self.proj, "pending", "--clear")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop"), {})

    def test_a_skipped_batch_is_not_asked_again(self):
        for i in range(5):
            self.edit(f"src/m{i}.py")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop").get("decision"), "block")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop"), {})  # the agent left it: no nag next turn
        for i in range(5, 9):
            self.edit(f"src/m{i}.py")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop"), {})
        self.edit("src/m9.py")  # a second full batch asks again
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop").get("decision"), "block")
        kg(self.proj, "pending", "--clear")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop"), {})
        for i in range(5):  # after a clear, the next batch counts from zero
            self.edit(f"src/n{i}.py")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop").get("decision"), "block")

    def test_batch_after_clear_is_not_missed(self):
        for i in range(5):
            self.edit(f"src/m{i}.py")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop").get("decision"), "block")
        kg(self.proj, "pending", "--clear")  # knowledge-keeper clears inside the continued turn
        for i in range(7):  # 7 is not below the 5 asked about before, but it is a new full batch
            self.edit(f"src/n{i}.py")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop").get("decision"), "block")

    def test_minor_unreferenced_edit_does_not_block(self):
        kg(self.proj, "upsert", "module-auth-jwt", "--kind", "module", "--summary", "JWT", "--sources", "src/auth/jwt.py:1-5")
        run_hook("kg_hooks.py", {"tool_input": {"file_path": os.path.join(self.proj, "src", "util.py")}}, self.proj, "track")
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop"), {})

    def test_stale_without_git(self):
        kg(self.proj, "upsert", "module-auth-jwt", "--kind", "module", "--summary", "JWT", "--sources", "src/auth/jwt.py:1-5")
        p = os.path.join(self.proj, ".claude", "knowledge", "nodes", "module-auth-jwt.md")
        txt = re.sub(r"(?m)^updated: .*$", "updated: 2000-01-01", slurp(p))
        spit(p, re.sub(r"(?m)^verified_commit: .*$", "verified_commit: none", txt))
        self.assertIn("module-auth-jwt", kg(self.proj, "stale").stdout)

    def test_obsolete_nodes_are_flagged_and_pruned(self):
        kg(self.proj, "upsert", "module-auth-jwt", "--kind", "module", "--summary", "JWT", "--sources", "src/auth/jwt.py:1-5")
        kg(self.proj, "upsert", "api-login", "--kind", "api", "--summary", "Login", "--sources", "README.md",
           "--links", "calls:module-auth-jwt")
        self.assertIn("nothing to prune", kg(self.proj, "prune").stdout)
        os.remove(os.path.join(self.proj, "src", "auth", "jwt.py"))  # deleted outside Claude: nothing pending
        out = run_hook("kg_hooks.py", {"hook_event_name": "Stop"}, self.proj, "stop")
        self.assertIn("Obsolete nodes (sources deleted): module-auth-jwt", out["reason"])
        self.assertIn("obsolete module-auth-jwt", kg(self.proj, "prune").stdout)
        self.assertEqual(kg(self.proj, "prune", "--apply").returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.proj, ".claude", "knowledge", "nodes", "module-auth-jwt.md")))
        self.assertNotIn("module-auth-jwt", slurp(os.path.join(self.proj, ".claude", "knowledge", "nodes", "api-login.md")))
        self.assertEqual(kg(self.proj, "validate").returncode, 0)
        self.assertEqual(run_hook("kg_hooks.py", {}, self.proj, "stop"), {})

    def test_remove_node(self):
        kg(self.proj, "upsert", "module-auth-jwt", "--kind", "module", "--summary", "JWT", "--sources", "src/auth/jwt.py:1-5")
        self.assertIn("removed module-auth-jwt", kg(self.proj, "remove", "module-auth-jwt").stdout)
        self.assertNotIn("module-auth-jwt", slurp(os.path.join(self.proj, ".claude", "knowledge", "INDEX.md")))
        self.assertEqual(kg(self.proj, "remove", "module-auth-jwt").returncode, 2)


class TestSafeRead(unittest.TestCase):
    def test_masks_values(self):
        proj = tmp_project()
        p = os.path.join(proj, ".env")
        with open(p, "w") as fh:
            fh.write(f"DB_HOST=localhost\nDB_PASSWORD=hunter2isweak\nGH={FAKE['github']}\n")
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "safe_read.py"), p], capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": proj})
        self.assertNotIn("hunter2isweak", r.stdout)
        self.assertNotIn(FAKE["github"], r.stdout)
        self.assertIn("DB_HOST=", r.stdout)
        shutil.rmtree(proj)


if __name__ == "__main__":
    unittest.main()
