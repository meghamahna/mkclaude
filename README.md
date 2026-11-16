# 🧰 mkclaude

[![CI](https://img.shields.io/github/actions/workflow/status/meghamahna/mkclaude/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white)](https://github.com/meghamahna/mkclaude/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](#-requirements)
[![License: MIT](https://img.shields.io/badge/license-MIT-D4A72C)](LICENSE)
[![Platform: macOS | Linux](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-57606A)](#-requirements)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-1F883D)](#-requirements)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-8250DF)](CONTRIBUTING.md)

Set up Claude Code in any project with one command. You get a complete, opinionated `.claude/` folder:
- **13 agents in three model tiers**: Opus for coding and supervision, Sonnet for docs, Haiku for cheap lookups
- **16 skills** for design, testing, security, docs, diagrams and token use, including the `/ask-me` and `/clean-me-up` commands
- **blocking of secrets and PII** in prompts, file reads, writes, shell commands and web calls, tuned so ordinary project files (an author email, local dev credentials) still work
- **dangerous-command blocking**, such as `rm -rf`, force-push, `reset --hard` and `terraform destroy`
- an **index-based knowledge graph** that Claude reads before searching, and keeps up to date as it works
- a **50% context budget** per agent, with an automatic hand-off to a fresh agent

```bash
git clone https://github.com/meghamahna/mkclaude.git ~/mkclaude
python3 ~/mkclaude/install.py DIR="/path/to/your/project"
```

The installer is plain Python with no dependencies. It merges with any Claude Code setup you already have, and `--uninstall` removes it again.

Full enforcement runs in [Claude Code](https://docs.anthropic.com/en/docs/claude-code), in whatever editor you use. Other AI agents get the shared rules through `AGENTS.md`; see [Which tools it works with](#-which-tools-it-works-with).

<!-- toc -->
## 📑 Contents

- [Requirements](#-requirements)
- [Which tools it works with](#-which-tools-it-works-with)
- [Quick start](#-quick-start)
- [What gets installed](#-what-gets-installed)
- [Using it day to day](#-using-it-day-to-day)
- [Agents](#-agents)
- [Skills](#-skills)
- [Security model](#-security-model)
- [Knowledge graph](#-knowledge-graph)
- [Context budget (50% per agent)](#-context-budget-50-per-agent)
- [Configuration](#-configuration)
- [Update and uninstall](#-update-and-uninstall)
- [Troubleshooting](#-troubleshooting)
- [Known limits](#-known-limits)
- [Roadmap](#-roadmap)
- [Repo layout](#-repo-layout)
- [Contributing](#-contributing)
- [Security](#-security)
- [License](#-license)

<!-- /toc -->

## 📦 Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code), tested with 2.1.310
- Python 3.9 or newer, available as `python3`. The installer, hooks and tools use only the standard library: no pip, node or jq.
- macOS or Linux. CI tests both. Windows is untested.
- Git is recommended. The knowledge graph uses commit hashes to spot stale entries, and falls back to file times without it.

## 🔌 Which tools it works with

**Any editor.** The harness runs inside Claude Code, which works in the terminal, VS Code, Cursor, Windsurf and JetBrains IDEs, and in the desktop and web apps. Everything below works the same in all of them.

**Other AI agents.** `AGENTS.md` follows the open [AGENTS.md](https://agents.md) convention, so agents that read it (such as Codex, Cursor's agent and GitHub Copilot) follow the same roles, routing, security rules and git policy. What they don't get is enforcement, because hooks and subagents are Claude Code features:

| Feature | Claude Code | Other agents |
|---|---|---|
| Roles, routing, rules and git policy (`AGENTS.md`) | Yes | Yes |
| Secret/PII and dangerous-command blocking | Enforced by hooks | Not enforced: rules only |
| 13 model-tiered agents, 16 skills, `/ask-me`, `/clean-me-up` | Yes | No |
| Knowledge graph | Read and kept up to date | Readable, not updated |
| 50% context hand-off | Yes | No |

Native support for more agents is on the [roadmap](#-roadmap).

## 🚀 Quick start

1. **Get the harness.** Clone it once, anywhere on your machine:

   ```bash
   git clone https://github.com/meghamahna/mkclaude.git ~/mkclaude
   ```

2. **Preview the install.** This prints every action it would take and changes nothing:

   ```bash
   python3 ~/mkclaude/install.py DIR="/path/to/your/project" --dry-run
   ```

3. **Install.** The installer detects your stack, writes `.claude/`, `CLAUDE.md` and `AGENTS.md`, seeds the knowledge graph, and finishes with a self-test of every guard:

   ```bash
   python3 ~/mkclaude/install.py DIR="/path/to/your/project"
   ```

   Optional: add `--user-env` so `@file` mentions also pass through the read guard (see [Known limits](#-known-limits)).

4. **Open Claude Code in the project** and check the install:

   ```bash
   cd /path/to/your/project
   claude
   ```

   ```text
   /harness-doctor     checks dependencies, settings, hooks and the knowledge graph
   /kg-bootstrap       builds the knowledge graph out in depth (one time, uses tokens)
   ```

5. **Fill in the project purpose.** Open `CLAUDE.md` and replace the `TODO(human)` line with one paragraph on what the project does and who uses it.

6. **Commit the setup** so your team gets it too:

   ```bash
   git add .claude CLAUDE.md AGENTS.md .gitignore
   git commit -m "chore: add mkclaude"
   ```

   Runtime state, scratch files and hand-off notes are already gitignored.

## 📁 What gets installed

```
your-project/
├── CLAUDE.md                     # harness block between <!-- harness:start/end --> (your content is preserved)
├── AGENTS.md                     # agent roster, routing, protocols (readable by any agent tool)
└── .claude/
    ├── settings.json             # deny/ask/allow rules, hooks, sandbox, status line (merged with yours)
    ├── harness.json              # tunables: context %, scan limits, KG limits
    ├── agents/                   # 13 subagents
    ├── skills/                   # 16 skills (9 knowledge, 6 commands, safe-read)
    ├── hooks/                    # security, context-budget and knowledge-graph hooks
    ├── tools/                    # kg.py, save.py, safe_read.py, svg_lint.py, doc_format.py, cleanup.py, doctor.py, stack.py, statusline.py
    ├── security/allowlist        # human-only detector exceptions
    └── knowledge/                # INDEX.md → nodes/*.md → exact path:line answers
```

## ⚡ Using it day to day

Work with Claude as usual. The harness shows up in these places:

| You see | What it means |
|---|---|
| Status line `ctx NN%/50%` | How much of the current agent's context is used, and the hand-off limit. |
| `[harness:security] ... blocked` | A guard stopped a secret, PII or a dangerous command. The message names the detector, never the value. |
| `[harness:kg]` at the end of a turn | Files the knowledge graph covers changed, so Claude delegates an update to knowledge-keeper. |
| `[harness:context] WARN` or `LIMIT` | The agent is near or at its context budget and will hand off. |
| `[harness:cleanup]` | Files that look temporary are left over, and the agent should remove its own. |
| `[harness:docs]` | A Markdown file the agent just wrote is missing the doc format (linked contents, one emoji per heading), and the agent fixes it. |

Commands you can run inside Claude Code:

| Command | Does |
|---|---|
| `/ask-me <question>` | Answers a question about the code cheaply: the Haiku repo-explorer checks the knowledge graph first and replies with `path:line` pointers. The search stays out of your main session's context. |
| `/clean-me-up` | Removes leftovers: temporary files agents made, scratch files, obsolete knowledge-graph nodes, old trash and hand-off notes. Nothing git tracks is touched, and removed files stay restorable. |
| `/harness-doctor` | Health check of the whole install. |
| `/kg-bootstrap` | Builds the knowledge graph in depth. |
| `/handoff` | Writes a hand-off note now, so you can `/clear` and continue fresh. |
| `/resume-handoff <file>` | Continues from a hand-off note. |
| `/safe-read <file>` | Shows a sensitive file with its values masked. |

From a terminal in the project, `python3 .claude/tools/kg.py query <terms>` searches the knowledge graph.

## 🤖 Agents

| Model | Agents |
|---|---|
| **Opus** (coding & supervision) | orchestrator, coding-agent, frontend-ui-builder, code-reviewer, security-auditor |
| **Sonnet** (docs & diagrams) | doc-writer, doc-reviewer, diagram-builder, diagram-reviewer |
| **Haiku** (basic, cheap) | knowledge-keeper, repo-explorer, commit-helper, lint-fixer |

The aliases `opus`, `sonnet` and `haiku` always resolve to the latest model in each tier.

Pipelines:
- code → code-reviewer (→ security-auditor when the change touches auth, input, data access, crypto, I/O or dependencies) → commit-helper
- docs → doc-reviewer
- diagrams → diagram-reviewer
- knowledge-keeper runs once at the end of a task that changed code or docs
- fast path: a single lookup, or a change in one file under about 20 lines that touches nothing sensitive, is done directly with tests run, no pipeline

See `AGENTS.md` in your project for routing rules.

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

## 🔒 Security model

Several independent layers enforce the policy, so one gap doesn't expose everything.

| Layer | What it stops |
|---|---|
| `guard_prompt.py` (UserPromptSubmit) | Secrets/PII pasted into a prompt. The prompt is blocked and suppressed. |
| `guard_read.py` (Read, Grep) | Credential files by path, and any file whose **content** contains secrets/PII. The content is scanned *before* Claude sees it; for a ranged read of a big file, only the requested lines are scanned. Grep results are pre-scanned too. |
| `guard_write.py` (Write, Edit, …) | Secrets/PII written into files; writes to `.env`/keys; edits to harness config and to anything under `.git/`. Asks before a change to a file that runs on its own or that Claude follows in later sessions: `.mcp.json`, agents, skills, commands, `CLAUDE.md`, `AGENTS.md`, CI workflows, `.husky/`, `.vscode/tasks.json`. |
| `guard_bash.py` (Bash) | `rm`, `sudo`, force-push, `reset --hard`, `clean -f`, infra destroy, DB drops, `curl \| sh`, `cat .env`, `printenv`, keychain/cloud-credential reads, file uploads, `git --output` into harness files. Parses `&&`, `;`, pipes, `$( )`, `bash -lc`, wrappers with options (`nice -n`, `timeout -s`), here-strings, heredocs, `xargs` and `find -exec`. Asks before discarding a single file's changes or before inline code that deletes files. Resolves relative paths from the directory the shell is in, follows a variable set earlier in the same command, and denies inline code that names harness files. **Supply chain:** package installs must pass `--ignore-scripts` (`supply_chain.install_scripts`), a new package asks in plain words, and fetched code cannot run unread in any common form (`curl \| sh`, `sh -c "$(curl …)"`, `bash <(curl …)`, download then run). |
| `guard_egress.py` (WebFetch, WebSearch, MCP) | Secrets/PII sent to external services. MCP recipient fields such as `to` are exempt from the PII check. |
| `redact_output.py` (PostToolUse) | Defense in depth: masks anything that still shows up in Bash/Grep/Web/MCP output. |
| `settings.json` | 129 deny rules (Read/Edit of credential paths, destructive Bash), 16 ask rules, 42 allow rules for read-only and harness commands, bypass mode disabled, Bash sandbox with credential directories unreadable. |

How one tool call passes through the hooks:

![How a tool call passes through the harness hooks](docs/diagrams/tool-call-flow.svg)

**Detection rules:**
- **Secrets:**
  - private keys (the whole block, body included)
  - AWS, GitHub, GitLab, Slack, Stripe, Google, Anthropic, OpenAI, npm and SendGrid keys
  - JWTs
  - credentials inside connection strings
  - high-entropy `password`/`token`/`api_key` assignments
- **PII:**
  - emails and phone numbers: block on web and MCP calls, and locally only in bulk (20 or more distinct values in one text, `scan.pii_bulk_threshold`); a single contributor address passes
  - US SSNs and Canadian SINs (Luhn-checked)
  - credit card numbers (Luhn-checked)
  - IBANs (mod-97)

**Allowed vs blocked:**
- **Block messages** name the detector, never the value.
- **Placeholders pass:** `user@example.com`, `555-0100`, Stripe test cards, `${VAR}` placeholders, well-known local dev values (`postgres`, `guest`, `django-insecure-...`) and AWS's documented example key are not flagged.
- **Allowlist:** for genuine exceptions, a human edits `.claude/security/allowlist` (`path:<glob>`, `sha256:<hash>` or `detector:<name>`). `python3 .claude/tools/safe_read.py --hash`, run in a terminal, prints the `sha256:` line for one value.

**Git policy:**
- **Allowed:** status, diff, log, show, add, commit, branch, switch, checkout -b, stash list/push, fetch, blame.
- **Asks first:** push, rebase, `--amend`, tag, new dependencies, `restore <file>` / `checkout -- <file>`, `switch -f`, `--output` to a file.
- **Denied:** force-push, `reset --hard`, `clean -f`, `branch -D`, `checkout .` / `restore .`, history rewrites, `git -c` settings that run commands.

**Deletion and cleanup:**
- `rm` and every other delete command stay blocked; build output goes through `cleanup.py` instead (below).
- Claude Code asks before any Write/Edit inside `.claude/`, so agents save knowledge-graph nodes, hand-off notes and scratch files with `python3 .claude/tools/save.py`. It is pre-approved, writes only to those three places, and runs the same secret/PII scan as the write guard.
- Agents remove only their own leftovers, through `python3 .claude/tools/cleanup.py remove <path>`: files in `.claude/scratch/`, untracked files an agent created this session, or build output: a git-ignored folder named in `cleanup.build_dirs` (`dist/`, `node_modules/` and similar) that holds no tracked files. Tracked, sensitive and harness files are refused, and so is other git-ignored data such as a local database or an uploads folder.
- Removed files go to `.claude/state/trash/` and can be restored with `cleanup.py restore <path>` until the trash is emptied (7 days by default).
- At the end of a turn, a `[harness:cleanup]` message lists anything that looks temporary (`tmp_*`, `debug_*`, `*.log`, ...) so the agent cleans up once its tests pass. Scratch files older than a day are cleared at session start.

## 🧠 Knowledge graph

`.claude/knowledge/` is the project's index-based memory.

**How lookups work:**
1. `INDEX.md` (≤ 200 lines, generated) lists nodes by kind, one line each; in a big graph each kind shows its first entries and points to `kg.py query` for the rest: `` - **<id>**: <summary> → `nodes/<id>.md` · `<first source>` ``.
2. `nodes/<kind>-<slug>.md` holds a short list of facts, each ending in an exact pointer such as `→ src/auth/jwt.py:20-27`.
3. `graph.json` holds typed edges: `depends_on`, `implements`, `calls`, `documented_in`, `decided_by`.
4. `python3 .claude/tools/kg.py query <terms>` returns ranked nodes, pointers and matching facts.

**How it is maintained:**
- The installer seeds the layout, entry points, commands and README sections. `/kg-bootstrap` builds the graph out in depth.
- Hooks record each edited file. At the end of a turn, if edits touch files the KG references (or a new area), Claude is asked to delegate an update to **knowledge-keeper**. Test files, lockfiles and small unrelated edits never trigger an update.
- `kg.py validate` catches dangling links, missing files and line ranges past the end of a file. `kg.py stale` lists nodes whose sources changed since `verified_commit`.
- The graph stays lean so it costs little context. When source files are deleted, the end-of-turn check flags the nodes that describe them and knowledge-keeper removes them (`kg.py prune --apply`). It also deletes facts that no longer hold when it updates a node. Hand-off notes older than 7 days are deleted at session start (`cleanup.handoff_days`).

## ⏳ Context budget (50% per agent)

`context_guard.py` reads each agent's own transcript after every tool call. It takes the real token usage and compares it with the real context window; for the main session it uses the window size reported to the status line, which handles 1M sessions correctly.

| Usage | What happens |
|---|---|
| ≥ 40% | One warning: finish the current unit of work and delegate exploration. |
| ≥ 50% | The agent must save a hand-off note (`save.py handoff`, written to `.claude/knowledge/handoffs/<agent>-<timestamp>.md`) and return `STATUS: HANDOFF <path>`. A hook then tells the parent to spawn a **fresh agent of the same type** that resumes from the handoff note. |

For the main session, auto-compact at 50% (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`) is the backstop.

## 🔧 Configuration

Installer options:

```bash
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --dry-run     # print every action, write nothing
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --force       # also overwrite harness files you modified (backups kept)
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --user-env    # set CLAUDE_CODE_DISABLE_FILE_MENTIONS=1 in ~/.claude/settings.json
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --no-sandbox  # omit Bash sandbox settings
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --no-seed     # skip knowledge-graph seeding
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --uninstall   # remove the harness (see below)
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --check       # exit 1 if locked security files or rules were changed (for CI)
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --codeowners "@org/security"  # route edits to locked files to these owners
```

**How the installer treats your existing files:**
- `.claude/settings.json` is deep-merged: your rules and values win, and a `.bak` copy is written first.
- `CLAUDE.md` and `AGENTS.md`: the harness only edits its block between `<!-- harness:start -->` and `<!-- harness:end -->`. Everything outside it is yours.
- `.claude/.harness-manifest.json` tracks the hash of every installed file, so files you changed are never overwritten silently.

Tune behavior in `.claude/harness.json`:
- `context.limit_pct`, `context.warn_pct`, `context.window_tokens`. To change the limit, also set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` in `.claude/settings.json` to the same number. The prompts no longer hard-code 50%.
- `scan.block_pii`, `scan.pii_detectors`: which personal-data detectors run
- `scan.pii_action`: per detector, `block` (default) or `warn`. Emails and phone numbers ship as `warn`: a few in a file, command or prompt pass, and `scan.pii_bulk_threshold` (20) or more distinct values in one text still block, which is what a customer export looks like. Every detector still blocks on web and MCP calls. Set a detector to `block` for the strict behavior.
- `scan.max_file_bytes` (5 MB), `scan.grep_max_files` (2,000), `scan.grep_max_bytes` (50 MB): how much the read guards pre-scan. A bigger file can still be read in ranges, and a bigger Grep runs with its output masked instead of pre-scanned.
- `cleanup.trash_days`, `cleanup.scratch_hours`, `cleanup.handoff_days`: how long removed files stay restorable in the trash, and how old scratch files and hand-off notes get before session start clears them
- `cleanup.build_dirs`: the git-ignored folders agents may clear as build output. Anything else git ignores stays.
- `supply_chain.install_scripts`: `block` (default) denies an npm, pnpm, yarn or bun install without `--ignore-scripts`; `ask` asks instead; `allow` switches the check off. A new package asks in every mode.
- `diagrams.theme`: `light` (default), `dark`, or `auto` (follows the viewer's setting) for every diagram the agents draw
- `knowledge.max_index_lines`, `knowledge.pending_trigger_count`
- `prompt_budgets`: size caps for agent prompts, skills, an agent plus the skills it preloads (`spawn_chars`), and `CLAUDE.md` + `AGENTS.md` (loaded every session); `/harness-doctor` warns when a prompt grows past its cap

## 🔄 Update and uninstall

**Update** to the latest harness:

```bash
git -C ~/mkclaude pull
python3 ~/mkclaude/install.py DIR="/path/to/your/project"
```

Re-running the installer is an upgrade. Harness files you haven't touched are refreshed, files you changed are skipped (pass `--force` to overwrite them, with backups), and rules from the old version are swapped for the new ones.

The security files are locked: the guard hooks (`guard_*.py`, `redact_output.py`), the shared detectors in `hooks/lib/`, `.claude/security/` and `tools/save.py`. Install and upgrade always restore them to the release, and back up your version first. `--check` exits 1 if a locked file was changed or removed, or if a harness deny rule or hook was taken out of `settings.json`. Run it in CI on the committed files. To change how a guard behaves for your project, use `harness.json` or the allowlist, or ask the security owners. If `codeowners` is set in `harness.json` (or you pass `--codeowners`), the installer adds a marked block to your CODEOWNERS file so edits to the locked files need those owners' review. Allowlist entries stay yours, but that block covers them too. See [CHANGELOG.md](CHANGELOG.md) for what changed.

**Uninstall:**

```bash
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --uninstall
```

This removes the harness files you haven't modified and the harness rules in `settings.json`. Your own settings, your content in `CLAUDE.md` and `AGENTS.md`, and the knowledge-graph nodes stay.

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| A command I need is blocked | Run it yourself in a terminal. The guards apply to Claude, not to you. To delete build output that git ignores (`dist/`, `node_modules/`), Claude can use `python3 .claude/tools/cleanup.py remove <path>`, which moves it to a restorable trash. |
| A file read or write is blocked by a detector | The message names the detector and the lines. Claude can read just the lines it needs, or use `/safe-read` for a masked view. For a false positive, add `path:<glob>` to `.claude/security/allowlist`, or allow one value: run `python3 .claude/tools/safe_read.py --hash` in a terminal, type the value at the hidden prompt, and paste the `sha256:` line it prints. |
| Too many permission prompts | Add your own `allow` rules to `.claude/settings.json`; they survive upgrades. Lockfile installs (`npm ci --ignore-scripts`, `uv sync`) and `npx` for a binary already in `node_modules` follow those rules. Adding a new dependency always asks. |
| `npm install` is blocked | Installs must pass `--ignore-scripts`, because install scripts are how most malicious packages attack. Claude re-runs with the flag on its own. If a package needs its build step (native modules), run `npm rebuild <package>` yourself, or set `supply_chain.install_scripts` to `ask` in `.claude/harness.json`. |
| Hooks fail with `python3: command not found` | Install Python 3.9+ and make sure `python3` is on the `PATH` Claude Code sees. Without it the guards cannot run, so nothing is checked; `/harness-doctor` reports this. |
| `/harness-doctor` reports a failure | Re-run the installer. If a file shows as modified and you want the stock version back, re-run with `--force`. Locked security files are restored on every run without it. |
| `--check` fails in CI | A locked security file, a harness deny rule or a harness hook was changed. Re-run the installer to restore it, or ask the security owners. |
| `@file` mentions show a secret file | Re-run the installer with `--user-env`, then restart Claude Code. |

## 🚫 Known limits

- **@-mentions:** `@file` mentions skip hooks unless `CLAUDE_CODE_DISABLE_FILE_MENTIONS=1` is set at user or shell level, which `--user-env` does. Project settings cannot set it. Read deny rules still apply to mentions on a best-effort basis.
- **Scripts:** a script that reads a secret file at runtime (e.g. `python app.py` loading `.env`) is not inspected. The sandbox, the `.env` deny rules and output redaction reduce this risk without removing it.
- **Blocked prompts:** the text of a blocked prompt can remain in the local transcript and history files on your machine.
- **Indirection:** the Bash guard reads the command text. It follows variables, `cd` and nested shells within one command, but a script on disk, or a value built at runtime, is not inspected. Install scripts are switched off for npm, pnpm, yarn and bun only; pip, cargo and other installers ask without that protection.
- **Detection:** regex and entropy detection catches common formats. Unusual secret formats can slip through, and some PII false positives are expected; the allowlist covers those.
- **Very large searches:** a Grep over more than `scan.grep_max_files` files or `scan.grep_max_bytes` isn't pre-scanned, so it relies on output masking (`redact_output.py`), the same layer that covers Bash output.
- **Context measurement:** context % is measured after each tool call, so a single huge read can overshoot before the hand-off triggers.
- **Python required:** hooks are Python; if `python3` is missing, or a guard runs past its time limit, the tool call goes ahead unchecked. A guard whose files are damaged denies the call. `/harness-doctor` flags a missing `python3`.
- **Shell parsing:** the Bash guard reads common command forms (wrappers, `bash -c`, heredocs, pipes). Variable indirection such as `X=rm; $X file` and scripts that delete files through their own code are not caught; the permission prompt and the sandbox are the backstop.
- **Context limit:** the limit is a strong instruction that repeats, not a hard stop. Auto-compact is the backstop.

## 🎯 Roadmap

- **More AI agents.** Generate each tool's own instruction files (Cursor rules, Copilot instructions, `GEMINI.md`) from the same source, and port the guards to tools that support hooks, with tests per tool.
- **Windows support** and a Windows CI job.
- **Plugin packaging** so the harness can also be installed as a Claude Code plugin, under a name without the reserved `claude-` prefix.

Ideas and votes are welcome in the issues.

## 📂 Repo layout

| Path | Contents |
|---|---|
| `install.py` | The single entry point. |
| `template/` | An exact mirror of what lands in a project: `claude/` becomes `.claude/`, plus `AGENTS.md` and `CLAUDE.md.tmpl`. Edit here to change the harness. |
| `docs/` | `contracts.md` (shared conventions: paths, node format, handoff schema, return block, detector names) and `diagrams/`. |
| `tests/` | The unit test suite (`python3 -m unittest discover -s tests`). |
| `evals/` | Behavioral evals that run real headless Claude Code sessions and grade them with fixed checks. See [evals/README.md](evals/README.md). |
| `scripts/` | Maintainer scripts, such as `gen_diagram_templates.py`. |
| `.github/` | CI workflow, issue and pull request templates, and Dependabot config. |

## 🙋 Contributing

Contributions are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers setup, tests, evals, and how to add an agent, skill, detector or guard rule. Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md). Release notes are in [CHANGELOG.md](CHANGELOG.md).

## 🛂 Security

Report vulnerabilities privately through the repository's Security tab ("Report a vulnerability"), never in a public issue. [SECURITY.md](SECURITY.md) lists what is in scope and what to include.

## 📜 License

Released under the [MIT License](LICENSE).
