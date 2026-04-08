---
name: github-scrum-task-projects
description: 'Plan and manage sprint tasks in GitHub using issues, ProjectV2, labels, and sub-issues. Use for scrum ceremonies, backlog grooming, and project-level execution tracking in GitHub.'
argument-hint: 'Team goal, sprint window, and target repository'
user-invocable: true
---

# GitHub Scrum Task Projects

## When to Use
- Running sprint planning on top of GitHub issues.
- Grooming backlog and prioritizing deliverables.
- Structuring project work with ProjectV2, labels, and sub-issues.
- Producing standup/review updates from repository task state.

## Inputs to Confirm
1. Repository owner and name.
2. Sprint objective and timebox.
3. Existing label taxonomy and ProjectV2 field/status convention.
4. Team capacity and ownership constraints.

## Procedure
1. Build current-state snapshot.
   - Collect open issues relevant to the sprint objective.
   - Group by ProjectV2 status, labels, and assignee.
2. Normalize task structure.
   - Ensure each task has one clear outcome.
   - Convert oversized tasks into sub-issues.
3. Prioritize and schedule.
   - Assign ProjectV2 status/iteration and ordering.
   - Balance workload by assignee and complexity.
4. Create missing tasks.
   - Add new issues only when needed to satisfy sprint objective.
   - Apply labels and acceptance criteria immediately.
5. Track execution.
   - Update issue state through planning, in-progress, blocked, done.
   - Keep blockers explicit in comments.
6. Prepare ceremony artifacts.
   - Standup view: done, next, blocked.
   - Review view: completed tasks and carry-over.

## Decision Points
- No consistent label/milestone system:
   - Define and apply a minimal label and ProjectV2 field convention before planning.
- Work exceeds sprint capacity:
   - Move lower-priority issues to a later ProjectV2 iteration and document trade-offs.
- Dependencies between tasks:
  - Represent as parent/sub-issue links and sequence explicitly.
- Urgent unplanned work arrives:
  - Rebaseline sprint scope and note displaced tasks.

## Completion Checks
1. Sprint-relevant issues have owners, labels, and ProjectV2 state.
2. Parent/sub-issue relationships are explicit for decomposed work.
3. Each in-sprint issue has acceptance criteria.
4. Blocked tasks include unblock condition and owner.
5. Sprint summary states committed scope, at-risk scope, and carry-over.

If direct ProjectV2 automation is unavailable, temporarily map sprint state through labels/milestones and report the limitation.

## Suggested GitHub Operations
- Create/update sprint tasks: `mcp_github_issue_write`
- Create task hierarchies: `mcp_github_sub_issue_write`
- Discover active PRs: `mcp_github_search_pull_requests`
- Delegate implementation: `mcp_github_create_pull_request_with_copilot`
- Track coding-agent progress: `mcp_github_get_copilot_job_status`
- ProjectV2 updates: GitHub Project automation tool or CLI path when available
