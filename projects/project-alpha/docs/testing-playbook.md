---
created_at: '2026-04-08'
project: project-alpha
title: Testing Playbook
---

# Testing Playbook

This playbook documents a repeatable smoke test for the CLI.

Related issue: ISSUE-003

## Smoke Test Checklist

- [ ] Initialize a new project
- [ ] Create at least one issue with tags
- [ ] List issues and verify status grouping
- [ ] Update issue status
- [ ] Mark issue as done
- [ ] Create a doc
- [ ] Validate link scanning
- [ ] Validate JSON output shape

## Command Sequence

python -m cli.main project init project-test
python -m cli.main issue create "Smoke scenario" --project project-test --tag testing
python -m cli.main issue list --project project-test
python -m cli.main issue update ISSUE-001 --project project-test --status in-progress
python -m cli.main issue done ISSUE-001 --project project-test
python -m cli.main doc create runbook --project project-test --title "Runbook"
python -m cli.main link issue-links ISSUE-001 --project project-test
python -m cli.main issue view ISSUE-001 --project project-test --json

## Expected Outcomes

1. All commands return exit code 0.
2. Files are created under projects/project-test.
3. Issue markdown contains frontmatter with id, status, tags, created_at.
4. Project counter increments in project.yaml.