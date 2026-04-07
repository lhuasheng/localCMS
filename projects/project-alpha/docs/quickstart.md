---
created_at: '2026-04-08'
project: project-alpha
title: Quickstart Guide
---

# Quickstart Guide

This guide shows the fastest path to start using the local project tracker.

Related issues: ISSUE-002, ISSUE-004

## 1. Install

1. Create or activate your Python environment.
2. Install in editable mode from repository root.

Example command:

python -m pip install -e .

## 2. Initialize a project

Example:

python -m cli.main project init project-alpha

## 3. Create and track issues

Example:

python -m cli.main issue create "Fix login bug" --project project-alpha --priority high --tag backend
python -m cli.main issue list --project project-alpha
python -m cli.main issue update ISSUE-001 --project project-alpha --status in-progress
python -m cli.main issue done ISSUE-001 --project project-alpha

## 4. Create docs and link context

Example:

python -m cli.main doc create architecture --project project-alpha --title "Architecture"
python -m cli.main link issue-links ISSUE-001 --project project-alpha

## 5. Machine-readable mode

Add --json to commands used by automation.

Example:

python -m cli.main issue list --project project-alpha --json

See also: ../docs/demo-workflow.md