---
created_at: '2026-04-08'
project: project-alpha
title: Demo Workflow
---

# Demo Workflow

This is the demo task implementation guide.

Related issue: ISSUE-004

## Demo Goal

Show a full lifecycle for project, issue, and docs using real commands.

## Demo Source

Use the script at examples/demo_cli_flow.py.

## Run Demo

From repository root:

python examples/demo_cli_flow.py

## What It Does

1. Creates project-demo.
2. Creates ISSUE-001 in project-demo.
3. Creates a doc in project-demo/docs.
4. Lists issues in grouped format.
5. Marks ISSUE-001 as done.
6. Prints the issue JSON payload.

## Verification

- project-demo exists under projects.
- project-demo/issues has markdown issue files with frontmatter.
- project-demo/docs has demo docs.
- The script ends with "Demo flow complete.".

See also: ../docs/quickstart.md