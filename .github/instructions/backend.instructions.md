---
applyTo: "**/*.py"
---

# Python Backend Conventions

- Follow existing project patterns for imports, error handling, and module layout.
- Use type hints on public function signatures.
- Run the repository's test and lint commands after changes — do not invent commands.
- Keep error handling at system boundaries; do not add defensive checks for internal-only paths.
- When changing public behavior, update related tests and docs.
