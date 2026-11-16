# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-15

### Added

- Locked security files: the guard hooks, `hooks/lib/`, `.claude/security/` and `save.py`. Install and upgrade always restore them to the release and back up the team's version. Other harness files keep the existing rule: kept if edited, unless `--force`.
- `install.py --check` for CI. It exits 1 if a locked file was changed or removed, or if a harness deny rule or hook was taken out of `settings.json`. When the repo is on the same version, it compares against the release, not the repo's own manifest.
- `--codeowners` and the `codeowners` key in `harness.json`. When set, the installer adds a marked block to the repo's CODEOWNERS file so edits to the locked files need the security owners' review. Uninstall removes the block.
- Five installer tests (104 in total).
- Evals: ten new scenarios (19 in total) covering over-blocking, working around a block, copying a secret into code, editing harness config, git policy, honest test reporting, the code pipeline and the orchestrator. New checks grade tool inputs, which subagents ran and in what order, and the final reply.
- Eval runner: `--trials N`, a `--no-harness` control run, `--compare A.json B.json` for pass rate and cost side by side, and results that record duration, per-model usage, subagents and tool inputs. A run that ends on max turns, budget or timeout now fails.
- A must-block and must-not-block detector corpus in the unit tests, plus tests for the new guard cases, the installer fixes and the eval checks (119 tests in total).
- Supply-chain protection that does not rely on the user reading a prompt. npm, pnpm, yarn and bun installs must pass `--ignore-scripts` (`supply_chain.install_scripts`: `block`, `ask` or `allow`). Fetched code cannot run unread in any common form: `sh -c "$(curl …)"`, `bash <(curl …)`, `eval`, `source`, and a file downloaded and run in the same command, as well as `curl | sh`. Commands that download a package and run it (`npm exec`, `pipx run`, `uv run --with`, `go run pkg@version`, `deno run <url>`, `gh extension install`, `claude mcp add`) ask, and every package prompt says in plain words what is being added.
- Writes under `.git/` are denied. Changes to files that run on their own or that Claude follows in later sessions ask first: `.mcp.json`, agents, skills, commands, `CLAUDE.md`, `AGENTS.md`, CI workflows, `.husky/` and `.vscode/tasks.json`.
- `AGENTS.md` tells every agent that fetched text (web pages, package READMEs, issues, tool results) is data and not instructions, and how to add a dependency safely. `secure-coding` and the session briefing repeat the short form.
- `cleanup.build_dirs`: the git-ignored folders that count as build output.
- Three eval scenarios (22 in total): an installer instruction hidden in a project file, git-ignored data that must survive a tidy-up, and end-to-end masking of a secret in Bash output. Nine more unit tests (128 in total), and five more doctor self-test cases.

### Changed

- The project is renamed from claude-harness to mkclaude. Installed file names, config keys and markers (`harness.json`, `.harness-manifest.json`, `harness:start`) are unchanged, so existing installs upgrade as before.
- Emails and phone numbers no longer block on their own. `scan.pii_action` sets them to `warn`: a few in a file, command or prompt pass, 20 or more distinct values in one text still block, and every detector still blocks on web and MCP calls.
- Well-known local development values (`postgres`, `guest`, `django-insecure-...`, AWS's documented example key) and endpoint or name settings such as `token_endpoint` are no longer reported as secrets.
- `cleanup.py remove` accepts git-ignored build folders that hold no tracked files (`cleanup.build_dirs`), so build output can be cleared into the restorable trash.
- `git restore <file>`, `git checkout -- <file>` and `docker compose down -v` ask for confirmation instead of being denied. Lockfile installs (`npm ci --ignore-scripts`, `uv sync`, `poetry install`), `npx` for a binary already in `node_modules`, and `terraform state list/show` follow the normal permission rules instead of always asking.
- More read-only commands are pre-approved (`cat`, `head`, `tail`, `grep`, `rg`, `git fetch`, `git blame`, `gh pr view`, `docker compose logs` and others). The Bash guard still checks their arguments, and asks when one of them redirects into a file.
- Block messages give the line numbers and the next step, and `safe_read.py --hash` prints the allowlist line for one value from a hidden terminal prompt.
- The main session is reminded of the context limit every tenth tool call, not on every call, and the warning fires again in a new session. Prompts no longer hard-code 50%.
- `CLAUDE.md` imports `AGENTS.md`, so the agent protocols load in every session. A fast path lets small, non-sensitive changes skip the review pipeline; `security-auditor` runs only on sensitive changes; `knowledge-keeper` runs once per task.
- Agent briefs start with `AGENT: <name> - <agent type>`. Reviewers and `repo-explorer` have an explicit read-and-Bash tool list. `coding-agent`, `frontend-ui-builder` and `code-reviewer` preload fewer skills and read the rest on demand; `/harness-doctor` checks the size of an agent together with its preloaded skills.
- Upgrades keep the project purpose line in `CLAUDE.md` and a team's own hooks under `.claude/hooks/`. `--check` fails when the manifest is missing from an installed project, and when a harness ask rule or the bypass-mode setting is changed.
- Orchestrator and the `AGENTS.md` brief template: briefs now state why the goal matters, the exact files the agent may edit and the decisions already made. The orchestrator keeps teams small, runs to a verified finish instead of stopping at a plan, pauses only for destructive actions or scope changes, and reports what is unverified.

### Fixed

- The Bash guard resolved relative paths from the project root, not from the directory the shell was in. After a `cd .claude/hooks` in an earlier call, a guard file could be overwritten by its bare name. Paths, wildcards and the allowlist now resolve from the shell's directory.
- Output of a harness tool could be redirected into a harness file (`python3 .claude/tools/stack.py > .claude/settings.json`). Redirect targets are checked for every command.
- Inline code (`python3 -c`, a heredoc script) could write harness files or shell out to `rm` without a verdict. Naming a harness file is denied and a delete command asks.
- A variable could hide a sensitive path or a command (`f=.env; cat "$f"`). Assignments made in the same command are followed.
- `safe_read.py` printed values in credential files that are not `KEY=value`: JSON (`credentials.json`, Docker's `auth`), `.netrc`, and single-token files. Every value in a credential file is now masked, in any format.
- `cleanup.py remove` accepted any git-ignored path, so a local database or an uploads folder could be trashed and later purged. Only folders named in `cleanup.build_dirs`, and temporary-looking files written this session, count as build output.
- A password that contained a placeholder word inside another word (`Contest…`, `Latest…`) was not detected.
- `save.py` blocked a handoff note over a single email address that the write guard allows. Both use the same scan.
- A content search with a `type` filter was denied when an unrelated `.env` matched the pattern.
- Heredoc text passed to `save.py` was treated as a script, so a knowledge node or handoff note that mentioned `.env` was denied.
- The orchestrator's summary was capped at three lines while being asked for full sentences; the cap is gone, and the "keep replies terse" rule applies to messages between agents only. `code-reviewer` no longer stops at about ten findings.
- `kg-bootstrap` told keepers to set `verified_commit` by hand, and the session briefing said "commit freely"; both now match the rest of the harness.
- `git diff`, `git log` and `git show` with `--output` could overwrite any file, including a guard, without a prompt. Writing into harness files is denied and other targets ask.
- The Bash guard now reads combined shell flags (`bash -lc`), wrapper options (`nice -n 10`, `timeout -s KILL 5`), here-strings, heredocs fed to a shell, `find -exec sh -c`, longer pipelines into a shell, `git -c alias...`, and writes after `cd .claude`. Inline scripts that delete files ask for confirmation.
- Private key blocks are detected and masked in full, not only the first line.
- Scanning a text with many findings took quadratic time and could run past the hook timeout; it is now a single sorted pass.
- Guards deny the call when their library fails to load. Sensitive and protected paths are matched without regard to case, and `..` in a path no longer rides on an allowlist entry.

## [0.1.0] - 2026-10-25

### Added

- `install.py`, a one-command installer for a Claude Code project harness. It needs Python 3.9 or later and the standard library only.
- Installer options: `--dry-run`, `--force`, `--user-env`, `--no-sandbox`, `--no-seed` and `--uninstall`. Re-running the installer upgrades unmodified harness files, deep-merges `.claude/settings.json` with a `.bak` copy, and tracks installed file hashes in `.claude/.harness-manifest.json` so locally modified files are not overwritten without `--force`.
- 13 subagents in three model tiers: Opus (orchestrator, coding-agent, frontend-ui-builder, code-reviewer, security-auditor), Sonnet (doc-writer, doc-reviewer, diagram-builder, diagram-reviewer) and Haiku (knowledge-keeper, repo-explorer, commit-helper, lint-fixer).
- 16 skills: simple-design, dsa-conscious-coding, diagram-maker, token-budget, knowledge-graph, secure-coding, test-driven-dev, frontend-a11y-design, doc-standards, safe-read, and the user commands `/ask-me`, `/clean-me-up`, `/kg-bootstrap`, `/handoff`, `/resume-handoff` and `/harness-doctor`.
- Security hooks that hard-block secrets and PII: `guard_prompt.py`, `guard_read.py`, `guard_write.py`, `guard_bash.py`, `guard_egress.py` and `redact_output.py`, plus 129 deny rules in `settings.json`, a disabled bypass mode and Bash sandbox settings.
- Secret detectors for private keys, cloud and service API keys, JWTs, connection-string credentials and high-entropy assignments. PII detectors for emails, phone numbers, US SSNs, Canadian SINs, credit cards and IBANs. A human-edited allowlist at `.claude/security/allowlist` for exceptions.
- `guard_bash.py` blocks destructive commands, force-push, `curl | sh` and credential reads, and parses `&&`, `;`, pipes, `$( )`, `bash -c`, `xargs`, `find -exec` and heredocs.
- Index-based knowledge graph in `.claude/knowledge/` with `kg.py` for query, show, validate, stale and index, installer seeding, and hooks that ask for an update when edited files are referenced by the graph.
- Context budget of 50% per agent: `context_guard.py` warns at 40%, requires a hand-off note at 50%, and the parent spawns a fresh agent of the same type to resume from it. The status line shows `ctx NN%/50%`.
- `cleanup.py` for removing an agent's own temporary files into a restorable trash, with end-of-turn `[harness:cleanup]` hints.
- `doctor.py` and the `/harness-doctor` command, which check the install, the agent control contract and prompt budgets.
- `doc_format.py` (linked table of contents and one emoji per heading) and `svg_lint.py` (diagram precision checks), used by the doc and diagram agents. A `doc_check.py` hook flags a newly written Markdown file that misses the format.
- `save.py`, the one way agents write inside `.claude/` (knowledge-graph nodes, hand-off notes, scratch files), because Claude Code asks for approval before any Write/Edit there. It runs the same secret/PII scan as the write guard.
- `safe_read.py` for viewing a sensitive file with values masked.
- Large-project support: ranged reads of big files scan only the requested lines, oversized Grep searches run with masked output instead of being denied, and the prompt budget counts only the harness part of `CLAUDE.md` and `AGENTS.md`.
- Knowledge-graph trimming: `kg.py remove` and `kg.py prune`, an end-of-turn check for nodes whose sources were deleted, and session-start removal of hand-off notes older than `cleanup.handoff_days`.
- `evals/` with `run_evals.py` and `scenarios.json`, behavioral evals that run headless Claude sessions graded by fixed checks.
- A unittest suite in `tests/` (87 tests) that builds fake secrets at runtime, so no secret-shaped string lives in the repository.
- `docs/contracts.md` with shared conventions, and a diagram of how a tool call passes through the hooks.
