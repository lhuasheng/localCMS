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

## Root Resolution

Precedence for data root:

1. `--root` option
2. `CLI_CMS_ROOT` environment variable
3. Repository root
