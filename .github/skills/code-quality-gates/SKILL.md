---
name: code-quality-gates
description: 'Run and report pre-merge quality gates with clear pass/fail evidence and residual risk.'
argument-hint: 'Touched files/domains, available toolchain, and required checks'
user-invocable: true
---

# Code Quality Gates

## When to Use
- Before merge for implementation changes.
- After a fix cycle to verify regressions were not introduced.
- When reviewers request stronger validation evidence.

## Ordered Pre-Merge Checks
1. Syntax and import sanity checks.
2. Lint and style checks.
3. Type checks if configured.
4. Targeted tests for changed behavior.
5. Full tests for touched domain.
6. Security or static checks if available.

## Execution Notes
- Stop early only on blockers that invalidate downstream checks.
- Prefer the smallest command set that still proves behavior and regression safety.
- If a check is not configured, mark it as "not available" and continue.

## Output Format
- Commands run: exact commands in execution order.
- Pass/fail summary: per check gate.
- Failures: failing gate, concise error signal, and likely blast radius.
- Residual risk: unverified paths, deferred checks, or environment limits.
