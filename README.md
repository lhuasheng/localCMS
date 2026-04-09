# CLI CMS

A local-first, file-based task and documentation tracker inspired by tools like Notion and Linear.

## Principles

- Files are the source of truth.
- Everything is human-readable and git-friendly.
- CLI is the mutation/control layer.
- Keep architecture lightweight and extensible.

## Data Layout

```text
projects/
  <project>/
    project.yaml
    issues/
      ISSUE-001-some-title.md
    docs/
      architecture.md
global/
  tags.yaml
  users.yaml
```

## Install

```bash
pip install -e .
```

## Commands (MVP)

```bash
cms project init project-alpha
cms issue create "Fix login bug" --project project-alpha
cms issue list --project project-alpha
cms issue view ISSUE-001
cms issue update ISSUE-001 --status in-progress
cms issue done ISSUE-001
cms doc create architecture --project project-alpha --title "System Architecture"
cms link issue-links ISSUE-001

# Explicit task linking (Linear-like)
cms issue link ISSUE-001 --project project-alpha --target ISSUE-002 --target-project project-alpha --relation blocks

# Feedback and add-on replies
cms issue feedback add ISSUE-001 "Implementation complete and ready for review" --project project-alpha --author leow --completion
cms issue feedback add ISSUE-001 "Added benchmark evidence after review" --project project-alpha --author leow --parent-feedback-id FB-001
cms issue feedback list ISSUE-001 --project project-alpha
cms validate-backlinks
cms audit-graph
```

## Obsidian Integration

- Repo-owned Obsidian settings live under `.obsidian/`.
- Templates live under `.obsidian/templates/`.
- `cms validate-backlinks` scans project markdown for broken markdown links and wiki links.
- `cms audit-graph` reports orphan notes, unresolved links, and per-project note counts.
- Optional issue scaffolding templates can be used with `cms issue create ... --template issue-template`.

## Pre-commit Hook

A pre-commit hook runs `cms validate-backlinks` before every commit to catch broken links early.

### Install (Unix / WSL / macOS)

```bash
bash scripts/install-hooks.sh
```

### Install (Windows — PowerShell)

```powershell
.\scripts\install-hooks.ps1
```

Both scripts copy the appropriate hook into `.git/hooks/pre-commit` and make it executable.

### What the hook does

Before each commit the hook runs:

```bash
cms validate-backlinks
```

If any unresolved links are found the commit is **blocked** and the broken links are printed.  Fix the reported issues and retry.

### Bypass the hook

To skip validation for a specific commit (not recommended for regular use):

```bash
git commit --no-verify
```

### Hook source files

| File | Purpose |
|------|---------|
| `scripts/hooks/pre-commit` | Bash hook script (Unix/WSL/macOS) |
| `scripts/hooks/pre-commit.ps1` | PowerShell hook script (Windows) |
| `scripts/install-hooks.sh` | Installer for Unix/WSL/macOS |
| `scripts/install-hooks.ps1` | Installer for Windows |

## Root Resolution

Precedence for data root:

1. `--root` option
2. `CLI_CMS_ROOT` environment variable
3. Repository root
