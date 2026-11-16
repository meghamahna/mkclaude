# 🔧 Configuration

Every installer option and every `harness.json` key, plus how to update and uninstall.

<!-- toc -->
## 📑 Contents

- [Installer options](#-installer-options)
- [How the installer treats your existing files](#-how-the-installer-treats-your-existing-files)
- [Harness settings](#-harness-settings)
- [Update](#-update)
- [Uninstall](#-uninstall)

<!-- /toc -->

## 📦 Installer options

```bash
python3 ~/mkclaude/install.py DIR="/path/to/your/project" [options]
```

| Option | Effect |
|---|---|
| `--dry-run` | Print every action, write nothing. |
| `--force` | Also overwrite harness files you modified (backups kept). |
| `--user-env` | Set `CLAUDE_CODE_DISABLE_FILE_MENTIONS=1` in `~/.claude/settings.json`. |
| `--no-sandbox` | Omit the Bash sandbox settings. |
| `--no-seed` | Skip knowledge-graph seeding. |
| `--uninstall` | Remove the harness (see [Uninstall](#-uninstall)). |
| `--check` | Exit 1 if locked security files or rules were changed (for CI). |
| `--codeowners "@org/security"` | Route edits to locked files to these owners. |

## 📁 How the installer treats your existing files

- `.claude/settings.json` is deep-merged: your rules and values win, and a `.bak` copy is written first.
- `CLAUDE.md` and `AGENTS.md`: the harness only edits its block between `<!-- harness:start -->` and `<!-- harness:end -->`. Everything outside it is yours.
- `.claude/.harness-manifest.json` tracks the hash of every installed file, so files you changed are never overwritten silently.

## 🧰 Harness settings

Tune behavior in `.claude/harness.json`.

| Key | What it controls |
|---|---|
| `context.limit_pct`, `context.warn_pct`, `context.window_tokens` | The context budget: hand off at 75%, warn once at 70%. To change the limit, also set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` in `.claude/settings.json` to the same number. |
| `scan.block_pii`, `scan.pii_detectors` | Which personal-data detectors run. |
| `scan.pii_action` | Per detector, `block` (default) or `warn`. Emails and phone numbers ship as `warn`: a few in a file, command or prompt pass, and `scan.pii_bulk_threshold` (20) or more distinct values in one text still block, which is what a customer export looks like. Every detector still blocks on web and MCP calls. Set a detector to `block` for the strict behavior. |
| `scan.max_file_bytes` (5 MB), `scan.grep_max_files` (2,000), `scan.grep_max_bytes` (50 MB) | How much the read guards pre-scan. A bigger file can still be read in ranges, and a bigger Grep runs with its output masked instead of pre-scanned. |
| `cleanup.trash_days`, `cleanup.scratch_hours`, `cleanup.handoff_days` | How long removed files stay restorable in the trash, and how old scratch files and hand-off notes get before session start clears them. |
| `cleanup.build_dirs` | The git-ignored folders agents may clear as build output. Anything else git ignores stays. |
| `supply_chain.install_scripts` | `block` (default) denies an npm, pnpm, yarn or bun install without `--ignore-scripts`; `ask` asks instead; `allow` switches the check off. A new package asks in every mode. |
| `diagrams.theme` | `light` (default), `dark`, or `auto` (follows the viewer's setting) for every diagram the agents draw. |
| `knowledge.max_index_lines`, `knowledge.pending_trigger_count` | The size of the knowledge-graph index (200 lines), and how many edited files make a batch that triggers an update (5). Set it to 1 to update after every edit. |
| `prompt_budgets` | Size caps for agent prompts, skills, an agent plus the skills it preloads (`spawn_chars`), and `CLAUDE.md` + `AGENTS.md` (loaded every session). `/harness-doctor` warns when a prompt grows past its cap. |

## 🔄 Update

```bash
git -C ~/mkclaude pull
python3 ~/mkclaude/install.py DIR="/path/to/your/project"
```

Re-running the installer is an upgrade. Harness files you haven't touched are refreshed, files you changed are skipped (pass `--force` to overwrite them, with backups), and rules from the old version are swapped for the new ones.

The security files are the exception: install and upgrade always restore them to the release. See [Locked security files](security.md#-locked-security-files). [CHANGELOG.md](../CHANGELOG.md) lists what changed in each release.

## 🧹 Uninstall

```bash
python3 ~/mkclaude/install.py DIR="/path/to/your/project" --uninstall
```

This removes the harness files you haven't modified and the harness rules in `settings.json`. Your own settings, your content in `CLAUDE.md` and `AGENTS.md`, and the knowledge-graph nodes stay.
