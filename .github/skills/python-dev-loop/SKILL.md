---
name: python-dev-loop
description: 'Implement, test, review, and document Python backend changes. Use for services, APIs, libraries, scripts, and backend regressions in Python repositories.'
argument-hint: 'Backend behavior, files to change, and validation needed'
user-invocable: true
---

# Python Dev Loop

## When to Use
- Implementing or refactoring Python backend behavior.
- Fixing regressions, failing tests, or integration issues.
- Updating backend docs when behavior changes.

## Procedure
1. Inspect the affected Python modules, tests, and configuration.
2. Implement the minimal coherent backend change.
3. Run the relevant test, lint, or validation commands used by the repository.
4. Update documentation or examples when behavior or setup changes.
5. Summarize the change, validation, and follow-up risk.

## Review Checklist
- Public behavior is preserved or intentionally changed.
- Error handling and edge cases are covered.
- Validation evidence matches the change risk.
- Docs or examples stay aligned.