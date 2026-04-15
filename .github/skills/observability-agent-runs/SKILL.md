---
name: observability-agent-runs
description: 'Capture structured evidence of agent run outcomes for hook threshold tuning and quality trend tracking.'
argument-hint: 'Task type, hooks fired, outcome (pass/fail), and false-positive or false-negative observations'
user-invocable: true
---

# Observability: Agent Run Evidence

## When to Use
- After completing a task to record hook outcomes and quality signals.
- When a hook fired incorrectly (false positive) or missed a real problem (false negative).
- When reviewing aggregate quality trends across a batch of tasks.

## What to Record per Run

| Field | Description |
|---|---|
| Task type | Feature, bugfix, refactor, docs, config |
| First-pass result | Pass or fail before reviewer handoff |
| Retry count | Number of fix-validate cycles before acceptance |
| Hooks fired | Which PreToolUse hooks triggered and whether correctly |
| False positives | Hooks that denied valid work (note which and why) |
| False negatives | Quality problems that reached review missed by hooks |
| Files changed | Count of touched files |
| Line delta | Net lines added/removed |

## Threshold Tuning Protocol
- Collect at least 10 task observations before adjusting any hook threshold.
- Adjust only one threshold at a time.
- Record the before/after threshold and the observation that prompted the change.
- If a hook produces more than 2 false positives in 10 runs, widen its threshold or downgrade it from deny to warn.
- If a hook misses more than 1 real problem in 10 runs, tighten its pattern or threshold.

## Output Format
- **Run summary**: task type, outcome, hooks fired.
- **Anomalies**: false positives or false negatives with description.
- **Threshold recommendation**: if tuning is warranted, state current value, proposed value, and rationale.
