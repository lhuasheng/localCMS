---
name: change-scoping
description: 'Define guardrails for touched-file count and line delta, when to split work, and how to stage commits atomically.'
argument-hint: 'Intended change description and list of initially identified files'
user-invocable: true
---

# Change Scoping

## When to Use
- Before starting any multi-file implementation.
- When a task grows beyond its initial boundary during implementation.
- When planning atomic commits or staged delivery.

## Default Guardrails

| Metric | Normal limit | Soft-warning threshold |
|---|---|---|
| Files touched | <= 5 | > 5 requires rationale |
| Net line delta (added + removed) | <= 300 | > 300 requires rationale |
| Commits per PR | <= 3 | > 3 requires stage plan |

These limits apply to a single task slice. They are not hard blocks but require documented rationale when exceeded.

## When to Split Work
- The change touches separate modules with independent acceptance criteria.
- One part of the change can be delivered and validated before the rest.
- A refactor and a behavior change are entangled; split the refactor into its own commit or slice.
- Exceeding the normal limits in both metrics at once is a strong signal to split.

## Atomic Commit Strategy
- Each commit must pass all checks independently.
- Group changes by logical unit: one commit per feature behavior, one per test update, one per config change.
- Do not mix refactoring and behavior changes in the same commit.
- Use a brief, specific commit subject line (50 characters or fewer when possible).

## Exceptions and Required Rationale
Larger changes are acceptable when:
- The task is a bulk rename or mechanical transformation with no logic change.
- The change is a dependency update that touches many lock or generated files.
- An architecture decision explicitly authorizes the scope.

For any exception, state: what the exception is, why it applies, and what additional validation was performed to compensate for the larger blast radius.

## Output Format
- **Scope plan**: list of files to touch and estimated line delta per file.
- **Split rationale**: whether the work was split and why (or why not).
- **Commit plan**: intended commits in order with a one-line description each.
- **Risk notes**: files or modules where the change is highest risk and what mitigation is used.
