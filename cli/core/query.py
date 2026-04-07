from __future__ import annotations

from pathlib import Path

from cli.core import parser, storage
from cli.core.models import IssueRecord


def iter_issue_records(root: Path, project: str) -> list[IssueRecord]:
    folder = storage.issues_dir(root, project)
    if not folder.exists():
        return []
    records: list[IssueRecord] = []
    for file in sorted(folder.glob("*.md")):
        metadata, content = parser.load_markdown(file)
        record = IssueRecord.from_payload(file, project, metadata, content)
        if record.issue_id:
            records.append(record)
    return records


def find_issue(root: Path, issue_id: str, project: str | None = None) -> IssueRecord:
    target = storage.issue_id_from_text(issue_id) or issue_id
    if project:
        for record in iter_issue_records(root, project):
            if record.issue_id == target:
                return record
        raise FileNotFoundError(f"Issue not found: {target} in project {project}")

    matches: list[IssueRecord] = []
    for project_name in storage.list_projects(root):
        for record in iter_issue_records(root, project_name):
            if record.issue_id == target:
                matches.append(record)

    if not matches:
        raise FileNotFoundError(f"Issue not found: {target}")
    if len(matches) > 1:
        raise RuntimeError(f"Issue ID {target} exists in multiple projects; pass --project")
    return matches[0]
