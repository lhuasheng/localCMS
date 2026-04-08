---
name: nextjs-frontend-dev-loop
description: 'Implement, test, review, and document Next.js frontend changes. Use for app router work, UI updates, data fetching, forms, and frontend regressions.'
argument-hint: 'Frontend behavior, routes or components, and validation needed'
user-invocable: true
---

# Next.js Frontend Dev Loop

## When to Use
- Implementing or refactoring Next.js frontend behavior.
- Changing routes, layouts, components, or frontend data flows.
- Fixing UI regressions or hydration, rendering, or form issues.

## Procedure
1. Inspect the affected route, component, and data boundary.
2. Make the smallest coherent frontend change.
3. Run relevant checks such as lint, typecheck, tests, or the local app validation path used by the repo.
4. Update user-facing docs when the behavior or setup changes.
5. Summarize the change, validation, and follow-up risk.

## Review Checklist
- Server and client boundaries remain intentional.
- Loading, error, and empty states are handled where relevant.
- Types, props, and API assumptions stay consistent.
- User-visible behavior is covered by validation.