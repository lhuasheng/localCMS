---
applyTo: "**/*.{tsx,jsx,ts}"
---

# Next.js Frontend Conventions

- Use the App Router (`app/` directory) patterns already in the project.
- Keep server and client component boundaries intentional — add `"use client"` only when needed.
- Handle loading, error, and empty states for data-fetching components.
- Run lint and typecheck after changes — do not invent commands.
- When changing routes or component props, verify upstream and downstream usage.
