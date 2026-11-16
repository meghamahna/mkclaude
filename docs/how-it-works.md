# 🧭 How it works

The agents, skills, knowledge graph and context budget that mkclaude installs, and which tools they work with.

<!-- toc -->
## 📑 Contents

- [Agents](#-agents)
- [Skills](#-skills)
- [Knowledge graph](#-knowledge-graph)
- [Context budget](#-context-budget)
- [Which tools it works with](#-which-tools-it-works-with)

<!-- /toc -->

## 🤖 Agents

| Model | Agents |
|---|---|
| **Opus** (coding and supervision) | orchestrator, coding-agent, frontend-ui-builder, code-reviewer, security-auditor |
| **Sonnet** (docs and diagrams) | doc-writer, doc-reviewer, diagram-builder, diagram-reviewer |
| **Haiku** (basic, cheap) | knowledge-keeper, repo-explorer, commit-helper, lint-fixer |

The aliases `opus`, `sonnet` and `haiku` always resolve to the latest model in each tier.

Work moves through fixed pipelines:

| Work | Pipeline |
|---|---|
| Code | coding-agent → code-reviewer → security-auditor (when the change touches auth, input, data access, crypto, I/O or dependencies) → commit-helper |
| UI | frontend-ui-builder → code-reviewer → security-auditor (same rule) → commit-helper |
| Docs | doc-writer → doc-reviewer |
| Diagrams | diagram-builder → diagram-reviewer |
| Any task that changed code or docs | knowledge-keeper runs once, **last and alone**, after every other agent has returned |
| Fast path | A single lookup, or a change in one file under about 20 lines that touches nothing sensitive, is done directly with tests run, no pipeline |

Independent read-only work runs in parallel, writers never share files, and knowledge-keeper never runs alongside another agent. `AGENTS.md` in your project holds the full routing rules.

## 🧩 Skills

| Skill | Purpose |
|---|---|
| `simple-design` | YAGNI, no abstraction with one consumer, standard library before new dependencies, single-purpose changes, small public interfaces (Hyrum's law) |
| `dsa-conscious-coding` | Data-structure choice by access pattern, Big-O notes, worst-case inputs, cache-friendly layouts, performance anti-patterns |
| `diagram-maker` | Mermaid/SVG diagrams built to a precision standard (8px grid, exact alignment, equal spacing, no crossing edges) with one light/dark palette, checked by `svg_lint.py` |
| `token-budget` | KG-first lookups, ranged reads, delegation, terse output |
| `knowledge-graph` | How to query and update the project KG |
| `secure-coding` | OWASP Top 10, input validation, secrets handling, dependencies |
| `test-driven-dev` | Red → green → refactor, hermetic tests, fakes over mocks, equivalence partitioning and boundaries |
| `frontend-a11y-design` | Design tokens, WCAG 2.2 AA, keyboard/focus, responsive, reduced motion |
| `doc-standards` | README / ADR / API / runbook templates; every doc gets a linked table of contents and one emoji per heading, checked by `doc_format.py` |
| `safe-read` | View a sensitive file with values masked |
| `/ask-me`, `/clean-me-up`, `/kg-bootstrap`, `/handoff`, `/resume-handoff`, `/harness-doctor` | User commands |

## 🧠 Knowledge graph

`.claude/knowledge/` is the project's index-based memory. A lookup goes from the index to an exact line:

1. `INDEX.md` (generated, at most 200 lines) lists every node by kind, one line each.
2. `nodes/<kind>-<slug>.md` holds a short list of facts, each ending in an exact pointer such as `→ src/auth/jwt.py:20-27`.
3. `graph.json` holds typed edges: `depends_on`, `implements`, `calls`, `documented_in`, `decided_by`.
4. `python3 .claude/tools/kg.py query <terms>` returns ranked nodes, pointers and matching facts.

It maintains itself:

- **Seeding.** The installer seeds the layout, entry points, commands and README sections. `/kg-bootstrap` builds the graph out in depth.
- **Updates.** Hooks record each edited file. Updates are batched: once 5 edited files are waiting (`knowledge.pending_trigger_count`), or a node's sources were deleted, Claude delegates an update to **knowledge-keeper** at the end of the turn, after every other agent has finished. If it skips one, it is not asked again until the next batch. Test files and lockfiles never count.
- **Validation.** `kg.py validate` catches dangling links, missing files and line ranges past the end of a file. `kg.py stale` lists nodes whose sources changed since `verified_commit`.
- **Pruning.** When source files are deleted, knowledge-keeper removes the nodes that describe them, and drops facts that no longer hold. The graph stays lean so it costs little context.

The node format and protocols are in [contracts.md](contracts.md#-knowledge-graph).

## ⏳ Context budget

`context_guard.py` reads each agent's own transcript after every tool call. It takes the real token usage and compares it with the real context window; for the main session it uses the window size reported to the status line, which handles 1M sessions correctly.

| Usage | What happens |
|---|---|
| ≥ 70% | One warning: finish the current unit of work and delegate exploration. |
| ≥ 75% | The agent must save a hand-off note (`save.py handoff`, written to `.claude/knowledge/handoffs/<agent>-<timestamp>.md`) and return `STATUS: HANDOFF <path>`. A hook then tells the parent to spawn a **fresh agent of the same type** that resumes from the hand-off note. A subagent is told on every call until it stops; the main session is reminded every 25th call. |

For the main session, auto-compact at 75% (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`) is the backstop. The limit and warning are set in `.claude/harness.json`, and auto-compact in `.claude/settings.json`; keep the limit and auto-compact equal (see [Configuration](configuration.md#-harness-settings)).

## 🔌 Which tools it works with

**Any editor.** The harness runs inside Claude Code, which works in the terminal, VS Code, Cursor, Windsurf and JetBrains IDEs, and in the desktop and web apps. Everything works the same in all of them.

**Other AI agents.** `AGENTS.md` follows the open [AGENTS.md](https://agents.md) convention, so agents that read it (such as Codex, Cursor's agent and GitHub Copilot) follow the same roles, routing, security rules and git policy. What they don't get is enforcement, because hooks and subagents are Claude Code features:

| Feature | Claude Code | Other agents |
|---|---|---|
| Roles, routing, rules and git policy (`AGENTS.md`) | Yes | Yes |
| Secret/PII and dangerous-command blocking | Enforced by hooks | Not enforced: rules only |
| 13 model-tiered agents, 16 skills, `/ask-me`, `/clean-me-up` | Yes | No |
| Knowledge graph | Read and kept up to date | Readable, not updated |
| 75% context hand-off | Yes | No |
