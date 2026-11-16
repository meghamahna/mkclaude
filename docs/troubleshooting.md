# 🐛 Troubleshooting

Fixes for the problems people hit most often. Start with `/harness-doctor` inside Claude Code: it checks dependencies, settings, hooks and the knowledge graph.

<!-- toc -->
## 📑 Contents

- [Blocked commands and files](#-blocked-commands-and-files)
- [Permission prompts](#-permission-prompts)
- [Failing checks](#-failing-checks)

<!-- /toc -->

## 🚫 Blocked commands and files

| Problem | Fix |
|---|---|
| A command I need is blocked | Run it yourself in a terminal. The guards apply to Claude, not to you. To delete build output that git ignores (`dist/`, `node_modules/`), Claude can use `python3 .claude/tools/cleanup.py remove <path>`, which moves it to a restorable trash. |
| A file read or write is blocked by a detector | The message names the detector and the lines. Claude can read just the lines it needs, or use `/safe-read` for a masked view. For a false positive, add `path:<glob>` to `.claude/security/allowlist`, or allow one value: run `python3 .claude/tools/safe_read.py --hash` in a terminal, type the value at the hidden prompt, and paste the `sha256:` line it prints. |
| `npm install` is blocked | Installs must pass `--ignore-scripts`, because install scripts are how most malicious packages attack. Claude re-runs with the flag on its own. If a package needs its build step (native modules), run `npm rebuild <package>` yourself, or set `supply_chain.install_scripts` to `ask` in `.claude/harness.json`. |
| `/safe-read .env` says "access denied" | Expected. The Bash sandbox blocks credential files for every command, including the masked viewer, so nothing inside Claude can open them. Run `python3 .claude/tools/safe_read.py .env` in your own terminal for the masked view. |
| `@file` mentions show a secret file | Re-run the installer with `--user-env`, then restart Claude Code. |

## 🛂 Permission prompts

| Problem | Fix |
|---|---|
| Too many permission prompts | The common test runners (`pytest`, `python3 -m unittest`, `npm test`, `go test`, `cargo test` and similar) are already allowed. For anything else, add your own `allow` rules to `.claude/settings.json`; they survive upgrades. Lockfile installs (`npm ci --ignore-scripts`, `uv sync`) and `npx` for a binary already in `node_modules` follow those rules. Adding a new dependency always asks. |

## ✅ Failing checks

| Problem | Fix |
|---|---|
| Hooks fail with `python3: command not found` | Install Python 3.9+ and make sure `python3` is on the `PATH` Claude Code sees. Without it the guards cannot run, so nothing is checked; `/harness-doctor` reports this. |
| `/harness-doctor` reports a failure | Re-run the installer. If a file shows as modified and you want the stock version back, re-run with `--force`. Locked security files are restored on every run without it. |
| `--check` fails in CI | A locked security file, a harness deny rule or a harness hook was changed. Re-run the installer to restore it, or ask the security owners. |

The limits that are known and documented are listed under [Known limits](security.md#-known-limits).
