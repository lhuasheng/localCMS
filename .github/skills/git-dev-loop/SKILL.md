---
name: git-dev-loop
description: 'Handle repository git workflows safely: branch setup, status review, focused commits, push, and change summaries for this project.'
argument-hint: 'Git task and target changes'
user-invocable: true
---

# Git Dev Loop

## When to Use
- You need to stage and commit completed code changes.
- You need a clean summary of tracked and untracked edits.
- You need to push a branch and set upstream.
- You need a safe release of changes without destructive commands.

## Procedure
1. Inspect repository state with `git status` and `git diff`.
2. Stage only intended files using focused `git add <path>` commands.
3. Commit with a clear message describing user-visible impact.
4. Push with upstream when needed: `git push -u origin <branch>`.
5. Report commit hash, changed files, and any residual local changes.

## Safety Rules
- Do not run destructive commands such as `git reset --hard` unless explicitly requested.
- Do not rewrite history unless explicitly requested.
- Do not stage unrelated files.

## Output Checklist
1. Branch and sync status
2. Staged files
3. Commit message and hash
4. Push result
5. Remaining local modifications
