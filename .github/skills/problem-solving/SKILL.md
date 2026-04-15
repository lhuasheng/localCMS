---
name: problem-solving
description: 'Systematic problem analysis using Pólya-inspired methodology: understand, plan, execute, and reflect. Use for complex multi-step tasks that benefit from structured decomposition.'
argument-hint: 'Problem statement, constraints, and expected outcome'
user-invocable: true
---

# Problem Solving

## When to Use
- Complex multi-step tasks that benefit from structured decomposition.
- Unfamiliar problem domains where upfront analysis reduces wasted effort.
- Tasks where the first approach failed and a reset is needed.
- Any request where the path from inputs to outputs is not immediately obvious.

**Skip this skill** for simple queries (definitions, quick facts, straightforward syntax) — answer those directly.

## Workflow

### Step 1 — Understand the Problem
- Clarify the request: what are the inputs, outputs, and constraints?
- Classify the type: factual query, coding task, research question, or multi-step problem.
- Assess complexity: does this need the full workflow, or is it straightforward?
- Restate the problem in your own words when there is any ambiguity.
- Identify what "done" looks like — tests passing, behavior change, output format, or acceptance criteria.

### Step 2 — Devise a Plan
Choose appropriate strategies before writing any code:
- Break down into subproblems.
- Look for analogous solved problems in the codebase or conversation.
- Work backward from the goal.
- Solve a simpler version first, then generalize.
- Determine which existing tools or functions can help.
- Decide if new reusable tools need to be created.

Identify resources needed:
- Tools available and information to gather.
- Code to read before code to write.
- Dependencies or environment prerequisites.

### Step 3 — Execute the Plan
- Execute each step carefully, one at a time.
- Use existing tools when available; create new ones for repeated operations.
- Show intermediate results — do not skip to the final answer.
- Persist but adapt: if a strategy is not working after a reasonable attempt, switch approaches rather than repeating the same failing path.

### Step 4 — Verify and Reflect
**Verification checklist:**
- Does the solution actually answer the original question?
- Do tests pass? Are edge cases handled?
- Is error handling appropriate at system boundaries?

**Code quality check:**
- Readable and maintainable?
- Follows project conventions (confirmed via pattern reuse)?
- Efficient enough — no obvious performance issues?

**Reusability check:**
- Can parts be extracted into utilities for future use?
- What patterns emerged that are worth remembering?

## Tool Creation Guidelines
When the solution involves writing a reusable tool:
- Write in the project's primary language.
- Include clear type hints and docstrings.
- Make the tool general enough to reuse, but not so abstract it obscures intent.
- Only create tools for operations that will genuinely repeat — do not abstract one-time logic.

## Anti-Patterns
- Jumping to code before understanding the problem.
- Continuing a failing strategy past 2 attempts without reassessing.
- Creating abstractions or helpers for one-time operations.
- Skipping verification because the code "looks right."
- Adding unrequested features or scope during execution.

## Output Format
- **Problem understood**: one-sentence restatement and classification.
- **Plan**: numbered steps with strategy chosen for each.
- **Execution evidence**: commands run, outputs observed, intermediate results.
- **Verification**: what was checked and the pass/fail result.
- **Reflection**: what worked, what didn't, and any reusable patterns identified.
