# 🔒 Security model

How mkclaude keeps secrets, personal data and destructive commands away from Claude, and where that protection ends. Several independent layers enforce the policy, so one gap doesn't expose everything.

<!-- toc -->
## 📑 Contents

- [Layers](#-layers)
  - [The Bash guard in detail](#-the-bash-guard-in-detail)
- [Detection rules](#-detection-rules)
- [Allowed and blocked](#-allowed-and-blocked)
- [Git policy](#-git-policy)
- [Deletion and cleanup](#-deletion-and-cleanup)
- [Locked security files](#-locked-security-files)
- [Known limits](#-known-limits)

<!-- /toc -->

## 🧱 Layers

| Layer | What it stops |
|---|---|
| `guard_prompt.py` (UserPromptSubmit) | Secrets/PII pasted into a prompt. The prompt is blocked and suppressed. |
| `guard_read.py` (Read, Grep) | Credential files by path, and any file whose **content** contains secrets/PII. The content is scanned *before* Claude sees it; for a ranged read of a big file, only the requested lines are scanned. Grep results are pre-scanned too. |
| `guard_write.py` (Write, Edit, …) | Secrets/PII written into files; writes to `.env`/keys; edits to harness config and to anything under `.git/`. Asks before a change to a file that runs on its own or that Claude follows in later sessions: `.mcp.json`, agents, skills, commands, `CLAUDE.md`, `AGENTS.md`, CI workflows, `.husky/`, `.vscode/tasks.json`. |
| `guard_bash.py` (Bash) | `rm`, `sudo`, force-push, `reset --hard`, `clean -f`, infra destroy, DB drops, `curl \| sh`, `cat .env`, `printenv`, keychain/cloud-credential reads, file uploads, `git --output` into harness files. See [The Bash guard in detail](#-the-bash-guard-in-detail). |
| `guard_egress.py` (WebFetch, WebSearch, MCP) | Secrets/PII sent to external services. MCP recipient fields such as `to` are exempt from the PII check. |
| `redact_output.py` (PostToolUse) | Defense in depth: masks anything that still shows up in Bash/Grep/Web/MCP output. |
| `settings.json` | 129 deny rules (Read/Edit of credential paths, destructive Bash), 16 ask rules, 56 allow rules for read-only commands, harness tools and the common test runners, bypass mode disabled, Bash sandbox with credential directories unreadable. |

How one tool call passes through the hooks:

![How a tool call passes through the harness hooks](diagrams/tool-call-flow.svg)

### 🪝 The Bash guard in detail

- **Parsing.** It reads `&&`, `;`, pipes, `$( )`, `bash -lc`, wrappers with options (`nice -n`, `timeout -s`), here-strings, heredocs, `xargs` and `find -exec`.
- **Asking.** It asks before discarding a single file's changes, or before inline code that deletes files.
- **Paths and variables.** It resolves relative paths from the directory the shell is in, follows a variable set earlier in the same command, and denies inline code that names harness files.
- **Supply chain.** Package installs must pass `--ignore-scripts` (`supply_chain.install_scripts`), a new package asks in plain words, and fetched code cannot run unread in any common form (`curl | sh`, `sh -c "$(curl …)"`, `bash <(curl …)`, download then run).

## 🔍 Detection rules

**Secrets:**

- private keys (the whole block, body included)
- AWS, GitHub, GitLab, Slack, Stripe, Google, Anthropic, OpenAI, npm and SendGrid keys
- JWTs
- credentials inside connection strings
- high-entropy `password`/`token`/`api_key` assignments

**PII:**

- emails and phone numbers: block on web and MCP calls, and locally only in bulk (20 or more distinct values in one text, `scan.pii_bulk_threshold`); a single contributor address passes
- US SSNs and Canadian SINs (Luhn-checked)
- credit card numbers (Luhn-checked)
- IBANs (mod-97)

## ✅ Allowed and blocked

- **Block messages** name the detector, never the value.
- **Placeholders pass:** `user@example.com`, `555-0100`, Stripe test cards, `${VAR}` placeholders, well-known local dev values (`postgres`, `guest`, `django-insecure-...`) and AWS's documented example key are not flagged.
- **Allowlist:** for genuine exceptions, a human edits `.claude/security/allowlist` (`path:<glob>`, `sha256:<hash>` or `detector:<name>`). `python3 .claude/tools/safe_read.py --hash`, run in a terminal, prints the `sha256:` line for one value.

## 🔀 Git policy

| Policy | Commands |
|---|---|
| **Allowed** | status, diff, log, show, add, commit, branch, switch, checkout -b, stash list/push, fetch, blame |
| **Asks first** | push, rebase, `--amend`, tag, new dependencies, `restore <file>` / `checkout -- <file>`, `switch -f`, `--output` to a file |
| **Denied** | force-push, `reset --hard`, `clean -f`, `branch -D`, `checkout .` / `restore .`, history rewrites, `git -c` settings that run commands |

## 🧹 Deletion and cleanup

- `rm` and every other delete command stay blocked; build output goes through `cleanup.py` instead (below).
- Claude Code asks before any Write/Edit inside `.claude/`, so agents save knowledge-graph nodes, hand-off notes and scratch files with `python3 .claude/tools/save.py`. It is pre-approved, writes only to those three places, and runs the same secret/PII scan as the write guard.
- Agents remove only their own leftovers, through `python3 .claude/tools/cleanup.py remove <path>`: files in `.claude/scratch/`, untracked files an agent created this session, or build output: a git-ignored folder named in `cleanup.build_dirs` (`dist/`, `node_modules/` and similar) that holds no tracked files. Tracked, sensitive and harness files are refused, and so is other git-ignored data such as a local database or an uploads folder.
- Removed files go to `.claude/state/trash/` and can be restored with `cleanup.py restore <path>` until the trash is emptied (7 days by default).
- At the end of a turn, a `[harness:cleanup]` message lists anything that looks temporary (`tmp_*`, `debug_*`, `*.log`, ...) so the agent cleans up once its tests pass. Each file is raised once, so a file the agent keeps on purpose is not asked about again. Scratch files older than a day are cleared at session start.

## 🔐 Locked security files

The security files are locked: the guard hooks (`guard_*.py`, `redact_output.py`), the shared detectors in `hooks/lib/`, `.claude/security/` and `tools/save.py`.

- **Restored on every run.** Install and upgrade always restore them to the release, and back up your version first.
- **Checked in CI.** `install.py --check` exits 1 if a locked file was changed or removed, or if a harness deny rule or hook was taken out of `settings.json`. Run it in CI on the committed files.
- **Changed through config.** To change how a guard behaves for your project, use `harness.json` or the allowlist, or ask the security owners.
- **Reviewed by owners.** If `codeowners` is set in `harness.json` (or you pass `--codeowners`), the installer adds a marked block to your CODEOWNERS file so edits to the locked files need those owners' review. Allowlist entries stay yours, but that block covers them too.

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
- **Masked view of credential files:** the Bash sandbox blocks `.env` and other credential files for every command, including `safe_read.py`, so `/safe-read` can show them only when a person runs it in their own terminal. This is deliberate: no command gets past the sandbox.
- **Context limit:** the limit is a strong instruction that repeats, not a hard stop. Auto-compact is the backstop.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
