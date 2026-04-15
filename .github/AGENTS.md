# Agent Map

This workspace defines a generic coding-team agent setup for repositories that are primarily Python backend and Next.js frontend.

The purpose of these agents is to control context exposure for the LLM. Each agent should stay narrow, use only the tools and skills appropriate to its role, and delegate when a task crosses role boundaries.

## Core Principles

- Agents are role filters, not project-specific personas.
- Skills hold repeatable workflows; agents hold decision scope and delegation rules.
- GitHub is the default planning and execution surface.
- Delegation is single-agent first.
- Parallel delegation is allowed only for clearly independent workstreams.

## Quality-First Delivery Loop

- The main thread orchestrates: it invokes agents, receives results, and decides the next step.
- Agents do not chain into each other for dependent work. Each agent returns its output to the caller.
- Typical flow: main thread calls `Coder`, then calls `Reviewer` on the result, then calls `Coder` again to fix findings.
- Parallelization is disallowed when workstreams share files, APIs, contracts, test fixtures, or acceptance criteria.

## Agent -> Skill Mapping

| Agent file | Primary role | Primary skills | Tool profile |
|---|---|---|---|
| `.github/agents/architect.agent.md` | Technical design, decomposition, and risk framing | none required | `read`, `search`, `todo`, `agent`, `github/*` |
| `.github/agents/product-manager.agent.md` | Product definition, prioritization, and acceptance criteria | `/product-research` | `web`, `read`, `search`, `todo`, `agent`, `github/*` |
| `.github/agents/coder.agent.md` | Implementation, debugging, tests, and issue-to-PR delivery | `/git-dev-loop`, `/github-coder-task-projects`, `/python-dev-loop`, `/nextjs-frontend-dev-loop` (others on demand) | `read`, `search`, `edit`, `execute`, `todo`, `agent`, `github/*` |
| `.github/agents/reviewer.agent.md` | Code review, QA, risk review, and acceptance validation | `/qa-review`, `/observability-agent-runs` | `read`, `search`, `edit`, `execute`, `todo`, `agent` |
| `.github/agents/docs.agent.md` | Technical writing, architecture docs, migration docs, and release notes | `/docs-generation` | `read`, `search`, `edit`, `todo`, `agent`, `github/*` |
| `.github/agents/research.agent.md` | Technical investigation, dependency comparison, and feasibility analysis | `/research-discovery` | `web`, `read`, `search`, `todo`, `agent`, `github/*` |
| `.github/agents/devops.agent.md` | CI/CD, environments, release operations, and deployment workflows | `/git-dev-loop` | `read`, `search`, `edit`, `execute`, `todo`, `agent`, `github/*` |

## Delegation Map

Agents only delegate to other agents for independent work. Dependent next-step work returns to the caller.

- `product-manager` -> `research`
  - Use for external comparison, dependency scans, or feasibility investigation.
- `architect` -> `research`, `docs`
  - Use for feasibility investigation or architecture records.
- `coder` -> `reviewer`, `docs`
  - Use for independent code review or documentation updates.
- `reviewer` -> *(none)*
  - Returns findings to the caller.
- `docs` -> *(none)*
  - Returns documentation and open questions to the caller.
- `research` -> *(none)*
  - Returns findings and recommendations to the caller.
- `devops` -> `docs`, `reviewer`
  - Use for release notes, runbooks, or validation of release-critical changes.

## Parallel Delegation Rules

- Use parallel delegation only when workstreams are independent by module, file area, or workflow phase.
- Good candidates include Python backend work and unrelated Next.js frontend work.
- Good candidates include implementation and documentation when the acceptance criteria are already stable.
- Avoid parallel delegation when tasks share the same files, APIs, data contracts, or sequencing constraints.
- When parallel work is used, the delegating agent must define a clear boundary and a definition of done for each track.

## Role Notes

- `Architect` owns system shape, interfaces, constraints, and decomposition. Returns designs to the caller.
- `Product Manager` owns problem framing, scope, acceptance criteria, and prioritization.
- `Coder` owns implementation and should load Python or Next.js workflow skills based on the task.
- `Reviewer` is a leaf agent — returns findings, does not chain into fixes.
- `Docs` is a leaf agent — returns documentation and open questions.
- `Research` is a leaf agent — returns findings and recommendations.
- `DevOps` handles release and operational work, returning app-code fix needs to the caller.

## Auto-Loading Instructions

Path-based instructions that inject stack context automatically when matching files are open or edited.

| File | Applies to | Purpose |
|---|---|---|
| `.github/instructions/backend.instructions.md` | `**/*.py` | Python backend conventions |
| `.github/instructions/frontend.instructions.md` | `**/*.{tsx,jsx,ts}` | Next.js frontend conventions |
| `.github/instructions/testing.instructions.md` | `**/*.{test,spec}.*` | Testing conventions |

These replace the need for agents to manually load skills for routine stack guidance.

## Slash Command Prompts

Reusable workflow entry points invoked via `/` in Copilot Chat.

| Prompt | Description |
|---|---|
| `/start-issue` | Research, plan, and implement a GitHub issue |
| `/review` | Review current changeset for bugs and regressions |
| `/plan` | Create an implementation plan before coding |
| `/debug` | Debug a failing test, error, or unexpected behavior |

## Skill Strategy

- Keep a small reusable core skill set.
- Use stack-specific overlays for Python backend and Next.js frontend work.
- Auto-loading instructions handle routine stack conventions; skills handle complex multi-step workflows.
- Avoid encoding repo-specific commands or domain assumptions in agent files unless they are true constraints of the role.

## Current Baseline

- Default tracker: GitHub issues and pull requests.
- Default implementation stack: Python backend and Next.js frontend.
- Default delivery mode: caller-orchestrated, single-agent execution. Each agent returns results; the caller decides the next step.
- Optional delivery mode: parallel delegation for independent research, review, or docs tracks.

## Validation Checklist

1. Each agent description is discoverable from likely user prompts.
2. Each agent has only the minimum tool scopes needed for its role.
3. Each skill is attached to the agent that actually needs it.
4. Python and Next.js behavior lives in skills, not in agent identity.
5. Delegation paths only go to independent work; dependent next steps return to the caller.
6. Documentation work can be delegated independently of implementation.