---
name: debug-recovery-loop
description: 'Structured failure triage, root-cause isolation, minimal fix, and re-run strategy with retry budget and escalation criteria.'
argument-hint: 'Failing check or command output, touched files, and expected behavior'
user-invocable: true
---

# Debug Recovery Loop

## When to Use
- A check, test, or command fails during or after implementation.
- A regression appears after a change.
- A tool invocation returns an unexpected error or non-zero exit code.

## Workflow

### Step 1 - First Failure Triage
- Capture the exact failure message: command, exit code, and full error text.
- Classify the failure: syntax error, import error, assertion error, runtime error, or environmental.
- Do not modify any file at this step; read and observe only.

### Step 2 - Isolate Root Cause
- Identify the smallest unit that reproduces the failure (single file, single test, single function).
- Trace the error to the originating symbol or line using search or read tools.
- Rule out environment or dependency issues before assuming a logic error.
- Confirm the hypothesis by citing the exact line or condition that causes the failure.

### Step 3 - Minimal Fix
- Apply the smallest change that addresses the root cause.
- Do not refactor, rename, or reorganize while fixing a regression.
- Verify the changed symbol or path exists before writing the edit.

### Step 4 - Rerun Strategy
- Rerun the failing check first.
- If that passes, rerun any check that directly exercises the changed code.
- Do not run the full suite speculatively; stay targeted.

### Step 5 - Retry Budget
- Allow up to 3 fix-rerun cycles per failure.
- If the failure persists after 3 cycles, stop and escalate.
- Record what was tried and what each run produced.

### Escalation Criteria
- Failure root cause is outside the current task scope (e.g., missing dependency, broken environment).
- Fix requires a design change (new interface, changed contract, cross-module refactor).
- Three cycles have been exhausted without meaningful progress.
- The fix would require touching more than 3 unrelated files.

## Output Format
- **Failure captured**: exact command and error text.
- **Root cause**: file, line, and hypothesis.
- **Fix applied**: description of the minimal change.
- **Evidence commands**: commands run in order with pass/fail result.
- **Unresolved blockers**: any remaining failure or escalation reason.
