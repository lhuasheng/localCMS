---
name: github-coder-task-projects
description: 'Create and execute GitHub development tasks from issues: scope work, branch, implement, open PR, and update issue state. Use for coder delivery linked to GitHub tasks and project milestones.'
argument-hint: 'GitHub task context, target repo/branch, and definition of done'
user-invocable: true
---

# GitHub Coder Task Projects

## When to Use
- Implementing a single GitHub issue end-to-end.
- Turning a sprint task into a branch, commit, and PR.
- Updating issue state with delivery evidence.
- Managing GitHub ProjectV2 items tied to delivery.

## Inputs to Confirm
1. Repository owner and name.
2. Issue number or task description.
3. Base branch and branch naming convention.
4. Definition of done and required checks.
5. Target GitHub ProjectV2 identifier and status field conventions.

## Procedure
1. Validate task target.
   - If issue number exists, fetch and summarize acceptance criteria.
   - If no issue exists, create one with clear scope, labels, and project linkage intent.
2. Plan the implementation slice.
   - Keep scope to one deliverable.
   - Split follow-up work into separate issues when scope grows.
3. Create a working branch.
   - Use a task-linked branch name such as `feat/issue-123-short-name`.
4. Implement and verify locally.
   - Apply minimal code changes.
   - Run relevant tests and collect evidence.
5. Commit and push.
   - Use focused commits tied to issue intent.
6. Open a pull request.
   - Reference the issue in the PR body.
   - Include test evidence and risk notes.
7. Sync GitHub task state.
   - Update ProjectV2 item status to reflect implementation status.
   - Add a status comment with PR link.

## Decision Points
- Missing or vague acceptance criteria:
  - Request clarification before coding.
- Scope no longer fits one PR:
  - Create follow-up issue(s) and keep the original PR narrow.
- Blocked dependency:
  - Mark issue blocked and document unblock condition.
- Failing checks:
  - Keep PR as draft until checks pass.
- ProjectV2 automation unavailable in current environment:
   - Fall back to labels/milestones and report the gap.

## Completion Checks
1. Issue has explicit acceptance criteria.
2. PR is linked to issue and contains validation evidence.
3. Tests for changed behavior pass.
4. Issue status comment explains current state and next action.
5. Any residual work is tracked in new issue(s), not hidden in PR notes.
6. ProjectV2 item is updated to match delivery state.

## Suggested GitHub Operations
- Issue lifecycle: `mcp_github_issue_write`
- Branch creation: `mcp_github_create_branch`
- PR creation: `mcp_github_create_pull_request`
- Copilot review: `mcp_github_request_copilot_review`
- Task decomposition: `mcp_github_sub_issue_write`
- ProjectV2 updates: GitHub Project automation tool or CLI path when available
