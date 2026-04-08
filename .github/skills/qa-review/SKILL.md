---
name: qa-review
description: 'Review code and behavior for correctness, regressions, and acceptance criteria. Use for code review, QA review, and test-gap analysis.'
argument-hint: 'Change under review, intended behavior, and risk areas'
user-invocable: true
---

# QA Review

## When to Use
- Reviewing a change for bugs, regressions, or missing tests.
- Validating behavior against acceptance criteria.
- Producing a high-signal review with prioritized findings.

## Procedure
1. Understand the intended behavior and scope.
2. Inspect the changed logic and validation evidence.
3. Identify correctness issues, regression risk, and missing coverage.
4. Report findings in priority order.
5. Capture remaining test gaps and assumptions.

## Review Checklist
- Behavior matches stated intent.
- Edge cases are handled or explicitly deferred.
- Validation evidence is adequate for the risk level.
- Findings are concrete and actionable.