---
name: prompt-grounding-and-pattern-reuse
description: 'Gather acceptance criteria, locate nearest code patterns, map intended change onto existing patterns, and prove symbol existence before editing.'
argument-hint: 'Intended change description, target files or modules, and acceptance criteria'
user-invocable: true
---

# Prompt Grounding and Pattern Reuse

## When to Use
- Before implementing any non-trivial code change.
- When a task touches an unfamiliar file or module.
- When you need to prove that an import, symbol, or API path exists before using it.

## Workflow

### Step 1 - Gather Acceptance Criteria
- Restate the intended behavior change in one or two sentences.
- Confirm the definition of done: what outputs, tests, or behaviors must be satisfied.
- If acceptance criteria are missing or ambiguous, resolve by reading the issue, conversation, or nearest related test.

### Step 2 - Locate Nearest Code Patterns
- Search for 1-2 existing implementations that are closest in structure to the intended change.
- Prefer patterns in the same module or domain over unrelated examples.
- Read the candidate files; do not rely on search result snippets alone.

### Step 3 - Map Intended Change onto Existing Pattern
- Identify which parts of the found pattern can be reused directly.
- Identify which parts must be adapted and why.
- Keep the structural shape (function signature, class layout, import style) consistent with the pattern.

### Step 4 - Prove Symbol and Import Existence
- Before writing any code that references a symbol or import path, confirm it exists in the workspace.
- Use search or read tools to verify the exact name, path, and public interface.
- Never assume a function, class, or constant exists based on plausible naming.

## Anti-Invention Checklist
- [ ] Every import path has been confirmed to exist in the workspace.
- [ ] Every function or class referenced has been read, not inferred.
- [ ] No new utility or abstraction is introduced unless the task explicitly requires it.
- [ ] Pattern selected is from this codebase, not from general knowledge.
- [ ] Acceptance criteria are stated explicitly, not assumed from the task title.

## Output Format
- **Evidence sources**: files and line ranges read during grounding.
- **Selected pattern references**: file path and function/class name for each reused pattern.
- **Intended delta**: what changes and what stays the same relative to the pattern.
- **Assumptions**: any gap that could not be confirmed from workspace evidence.
