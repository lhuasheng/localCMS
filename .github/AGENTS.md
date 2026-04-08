# Agent Map

This workspace defines a generic coding-team agent setup for repositories that are primarily Python backend and Next.js frontend.

The purpose of these agents is to control context exposure for the LLM. Each agent should stay narrow, use only the tools and skills appropriate to its role, and delegate when a task crosses role boundaries.

## Core Principles

- Agents are role filters, not project-specific personas.
- Skills hold repeatable workflows; agents hold decision scope and delegation rules.
- GitHub is the default planning and execution surface.
- Delegation is single-agent first.
- Parallel delegation is allowed only for clearly independent workstreams.

## Agent -> Skill Mapping

| Agent file | Primary role | Primary skills | Tool profile |
|---|---|---|---|
| `.github/agents/architect.agent.md` | Technical design, decomposition, and risk framing | none required | `read`, `search`, `todo`, `agent`, `github/*` |
| `.github/agents/product-manager.agent.md` | Product definition, prioritization, and acceptance criteria | `/product-research` | `web`, `read`, `search`, `todo`, `agent`, `github/*` |
| `.github/agents/scrum-master.agent.md` | GitHub-first planning, sequencing, and delivery coordination | `/github-scrum-task-projects` | `read`, `search`, `execute`, `todo`, `agent`, `github/*` |
| `.github/agents/coder.agent.md` | Implementation, debugging, tests, and issue-to-PR delivery | `/git-dev-loop`, `/github-coder-task-projects`, `/python-dev-loop`, `/nextjs-frontend-dev-loop` | `read`, `search`, `edit`, `execute`, `todo`, `agent`, `github/*` |
| `.github/agents/reviewer.agent.md` | Code review, QA, risk review, and acceptance validation | `/qa-review` | `read`, `search`, `edit`, `execute`, `todo`, `agent` |
| `.github/agents/docs.agent.md` | Technical writing, architecture docs, migration docs, and release notes | `/docs-generation` | `read`, `search`, `edit`, `todo`, `agent`, `github/*` |
| `.github/agents/research.agent.md` | Technical investigation, dependency comparison, and feasibility analysis | `/research-discovery` | `web`, `read`, `search`, `todo`, `agent`, `github/*` |
| `.github/agents/devops.agent.md` | CI/CD, environments, release operations, and deployment workflows | `/git-dev-loop` | `read`, `search`, `edit`, `execute`, `todo`, `agent`, `github/*` |

## Delegation Map

- `product-manager` -> `architect`, `scrum-master`, `research`
  - Use when product ideas need technical shaping, planning, or external validation.
- `architect` -> `coder`, `reviewer`, `docs`, `research`
  - Use when design work needs implementation spikes, risk review, documentation, or deeper investigation.
- `scrum-master` -> `coder`, `reviewer`, `docs`
  - Use when scoped delivery work is ready for execution, validation, or documentation.
- `coder` -> `reviewer`, `docs`, `architect`
  - Use when implementation needs focused validation, documentation updates, or design clarification.
- `reviewer` -> `coder`
  - Use when review findings require concrete fixes.
- `docs` -> `coder`, `architect`
  - Use when documentation gaps require implementation details or architectural clarification.
- `research` -> `architect`, `product-manager`
  - Use when investigation results need design or product decisions.
- `devops` -> `coder`, `docs`, `reviewer`
  - Use when operational work requires code fixes, release notes, runbooks, or validation.

## Parallel Delegation Rules

- Use parallel delegation only when workstreams are independent by module, file area, or workflow phase.
- Good candidates include Python backend work and unrelated Next.js frontend work.
- Good candidates include implementation and documentation when the acceptance criteria are already stable.
- Avoid parallel delegation when tasks share the same files, APIs, data contracts, or sequencing constraints.
- When parallel work is used, the delegating agent must define a clear boundary and a definition of done for each track.

## Role Notes

- `Architect` owns system shape, interfaces, constraints, and decomposition. It should not become the primary implementer.
- `Product Manager` owns problem framing, scope, acceptance criteria, and prioritization.
- `Scrum Master` owns sequencing, GitHub task state, blocker visibility, and delivery coordination.
- `Coder` owns implementation and should load Python or Next.js workflow skills based on the task.
- `Reviewer` is the generic replacement for the old Word-specific review role.
- `Docs` is a first-class role, not an afterthought of implementation.
- `Research` handles options analysis and feasibility without turning into product strategy by default.
- `DevOps` handles release and operational work, escalating to Coder when code changes are necessary.

## Skill Strategy

- Keep a small reusable core skill set.
- Use stack-specific overlays for Python backend and Next.js frontend work.
- Avoid encoding repo-specific commands or domain assumptions in agent files unless they are true constraints of the role.

## Current Baseline

- Default tracker: GitHub issues and pull requests.
- Default implementation stack: Python backend and Next.js frontend.
- Default delivery mode: single-agent execution with explicit handoffs.
- Optional delivery mode: parallel delegation for independent backend, frontend, review, or docs tracks.

## Validation Checklist

1. Each agent description is discoverable from likely user prompts.
2. Each agent has only the minimum tool scopes needed for its role.
3. Each skill is attached to the agent that actually needs it.
4. Python and Next.js behavior lives in skills, not in agent identity.
5. Delegation paths are explicit and symmetric enough to support handoffs.
6. Documentation work can be delegated independently of implementation.

## Next Step

- Add a Mermaid diagram of this delegation graph after the role layout stabilizes.