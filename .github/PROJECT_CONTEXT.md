# Project Context
**Single source of truth for runtime project facts used by agents, skills, and tools.**

---

## Repository Metadata

| Key | Value | Notes |
|-----|-------|-------|
| **Owner** | (inferred at runtime) | Discovered via `git config` or GitHub CLI |
| **Repo Name** | (inferred at runtime) | Discovered via `git config` or GitHub CLI |
| **Default Branch** | `main` | Used for base comparisons and default PR target |
| **Primary Stack** | Python (backend) + Next.js (frontend) | Agents load role-specific skills for each stack |

---

## GitHub Configuration

### Default Tool Entry Points
- **Issue Tracker**: GitHub Issues (not Linear)
- **Project Tracker**: GitHub ProjectV2 (if enabled for this repo)
- **CI/CD**: GitHub Actions
- **SCM**: Git + GitHub

### GitHub Conventions
- **Branch naming**: Follow `<issue-type>/<issue-number>-<description>` pattern (defined in [git-dev-loop](./skills/git-dev-loop/SKILL.md) skill)
- **PR templates**: Use [`.github/pull_request_template.md`](.github/pull_request_template.md) if present
- **Commit scope**: Keep commits focused to a single issue or feature
- **PR reviews**: Security, tests, docs, and behavioral validation (see [qa-review](./skills/qa-review/SKILL.md) skill)

### ProjectV2 Field Names (if used)
- **Status**: (e.g., `Status`, `State`, or `Workflow`)
- **Priority**: (e.g., `Priority`, `Severity`)
- **Assignee**: (e.g., `Assignee`)
- **Iteration/Cycle**: (e.g., `Sprint`, `Milestone`)

> **Note**: Infer exact field names from `gh project field-list <owner>/<repo>` or GitHub UI. Update this file when field names change.

---

## Stack-Specific Paths

### Backend (Python)
- **Code Root**: `./backend/` or `./app/` (if monorepo)
- **Entry Point**: `./app/main.py` or equivalent
- **Tests**: `./tests/` directory
- **Skill**: [python-dev-loop](./skills/python-dev-loop/SKILL.md)

### Frontend (Next.js)
- **Code Root**: `./app/` or `./src/app/` (App Router convention)
- **Entry Point**: `./app/layout.tsx` and route handlers
- **Tests**: `./app/**/__tests__/` or `./tests/`
- **Skill**: [nextjs-frontend-dev-loop](./skills/nextjs-frontend-dev-loop/SKILL.md)

---

## Agent Scope Boundaries

| Agent | Default Tools | When to Invoke |
|-------|----------------|----------------|
| **Architect** | read, search, todo, agent, github/* | Technical design, decomposition, interface definition |
| **Product Manager** | web, read, search, todo, agent, github/* | Product definition, prioritization, acceptance criteria |
| **Scrum Master** | read, search, todo, agent, github/* | Sprint planning, sequencing, blocker tracking |
| **Coder** | read, search, edit, execute, todo, agent, github/* | Feature implementation, bug fixes, refactoring |
| **Reviewer** | read, search, todo, agent | Code review, QA, acceptance validation (strict: no execution) |
| **Docs** | read, search, edit, todo, agent, github/* | Technical writing, README, architecture docs, runbooks |
| **Research** | web, read, search, todo, agent, github/* | Technical investigation, feasibility, dependency evaluation |
| **DevOps** | read, search, edit, execute, todo, agent, github/* | CI/CD, environments, release operations |

---

## Delegation Rules

### Single-Agent Work
- Product discovery, research, code review, documentation: Start with domain expert role
- No parallel delegation; findings inform next step

### Parallel Delegation (Only When Truly Independent)
- **Backend + Frontend**: Python backend and Next.js frontend modules with no shared database schema changes, no API contract changes, no shared types
- **Docs + Implementation**: Documentation can run in parallel only if implementation details are frozen or documented

### Anti-Pattern: Parallel Code Review + Implementation
- Reviewer → Coder → Reviewer again always in sequence
- Never run implementation and review in parallel for same change

---

## Common Tool Invocation Parameters

Tools require explicit project context at invocation time. Agents should provide:

```yaml
# GitHub tools (all agents with github/*)
owner: <owner>          # e.g., "my-org"
repo: <repo-name>       # e.g., "linear"
issue_number: <int>     # if targeting an issue
pull_number: <int>      # if targeting a PR
branch: <name>          # if creating or switching branches

# Git operations (via git-dev-loop skill)
commit_message: <msg>   # Clear, scoped to issue
base_branch: "main"     # Default

# Search/discovery (read, search, web tools)
query: <string>         # Specific and bounded
maxResults: <int>       # Limit scope (default: 50)
```

---

## Initialization Checklist

When working in this repository for the first time, agents should:

- [ ] Verify `owner` and `repo` via local git config
- [ ] Confirm default branch (typically `main`)
- [ ] List GitHub ProjectV2 fields (if project tracking is enabled)
- [ ] Discover stack layout: where is backend code? where is frontend code?
- [ ] Read [AGENTS.md](./AGENTS.md) for local team model and delegation graph
- [ ] Load appropriate skill based on task type and stack area

---

## Scope Limits

### Do Not Hard-Code
- Specific issue numbers or PR numbers (infer from context at tool time)
- Specific file paths (infer from stack discovery)
- Specific team member names (reference `@mention` only when explicitly asked)

### Always Reference
- This file (`PROJECT_CONTEXT.md`) as source of truth for runtime facts
- [AGENTS.md](./AGENTS.md) for delegation rules and role descriptions
- Skill files (e.g., [python-dev-loop](./skills/python-dev-loop/SKILL.md)) for workflow steps

---

## References

- [AGENTS.md](./AGENTS.md) — Complete role model and delegation graph
- [git-dev-loop](./skills/git-dev-loop/SKILL.md) — Safe git operations for this project
- [python-dev-loop](./skills/python-dev-loop/SKILL.md) — Backend Python workflow
- [nextjs-frontend-dev-loop](./skills/nextjs-frontend-dev-loop/SKILL.md) — Frontend Next.js workflow
- GitHub CLI docs — https://cli.github.com/manual/
