from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import typer

from cli.core import parser, query, storage
from cli.core.models import IssueRecord
from cli.core.render import emit_json

app = typer.Typer(help="Manage issues")
feedback_app = typer.Typer(help="Manage issue feedback and completion notes")
app.add_typer(feedback_app, name="feedback")


def _root(ctx: typer.Context) -> Path:
    return ctx.obj["root"]


def _validate_status(root: Path, project: str, status: str) -> None:
    config = storage.load_project_config(root, project)
    if status not in config.statuses:
        allowed = ", ".join(config.statuses)
        raise typer.BadParameter(f"Invalid status '{status}'. Allowed: {allowed}")


def _print_grouped(records: list[IssueRecord]) -> None:
    grouped: dict[str, list[IssueRecord]] = {}
    for record in records:
        grouped.setdefault(record.status, []).append(record)

    order = ["todo", "in-progress", "done"]
    statuses = order + [s for s in grouped.keys() if s not in order]

    for status in statuses:
        items = grouped.get(status, [])
        if not items:
            continue
        typer.echo(f"[{status.upper()}]")
        for item in items:
            typer.echo(f"  {item.issue_id} {item.title}")
        typer.echo("")


def _normalize_issue_id(value: str) -> str:
    return storage.issue_id_from_text(value) or value


def _load_feedback(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    raw = metadata.get("feedback", [])
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _next_feedback_id(feedback_items: list[dict[str, Any]]) -> str:
    highest = 0
    for item in feedback_items:
        value = str(item.get("id", ""))
        if value.startswith("FB-"):
            try:
                highest = max(highest, int(value.split("-", maxsplit=1)[1]))
            except ValueError:
                continue
    return f"FB-{highest + 1:03d}"


def _load_links(metadata: dict[str, Any]) -> list[dict[str, str]]:
    raw = metadata.get("linked_issues", [])
    if isinstance(raw, list):
        links: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            issue = str(item.get("issue", "")).strip()
            project = str(item.get("project", "")).strip()
            relation = str(item.get("relation", "relates-to")).strip() or "relates-to"
            if issue and project:
                links.append({"issue": issue, "project": project, "relation": relation})
        return links
    return []


def _normalize_link_entry(item: dict[str, Any]) -> dict[str, str]:
    return {
        "issue": str(item.get("issue", "")).strip(),
        "project": str(item.get("project", "")).strip(),
        "relation": str(item.get("relation", "relates-to")).strip() or "relates-to",
    }


def _normalize_feedback_entry(item: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {
        "id": str(item.get("id", "")).strip(),
        "type": str(item.get("type", "comment")).strip() or "comment",
        "author": str(item.get("author", "system")).strip() or "system",
        "created_at": str(item.get("created_at", "")).strip(),
        "message": str(item.get("message", "")).strip(),
    }
    parent_id = str(item.get("parent_id", "")).strip()
    if parent_id:
        normalized["parent_id"] = parent_id
    return normalized


def _ordered_issue_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}

    linked_issues = [_normalize_link_entry(item) for item in _load_links(metadata)]
    feedback_items = [_normalize_feedback_entry(item) for item in _load_feedback(metadata)]

    core_keys = ["id", "title", "status", "priority", "created_at", "tags", "linked_issues", "feedback"]
    for key in core_keys:
        if key == "linked_issues" and linked_issues:
            ordered[key] = linked_issues
            continue
        if key == "feedback" and feedback_items:
            ordered[key] = feedback_items
            continue
        if key in metadata:
            ordered[key] = metadata[key]

    for key, value in metadata.items():
        if key not in ordered:
            ordered[key] = value

    return ordered


def _append_feedback_to_body(content: str, entry: dict[str, str]) -> str:
    marker = "## Feedback Log"
    lines = content.rstrip().splitlines()
    if marker not in lines:
        lines.extend(["", marker, "- none"])

    entry_id = entry.get("id", "")
    entry_type = entry.get("type", "comment")
    author = entry.get("author", "system")
    created_at = entry.get("created_at", "")
    message = entry.get("message", "")
    parent_id = entry.get("parent_id", "")

    message_line = f"- {entry_id} [{entry_type}] by {author} on {created_at}: {message}"
    if parent_id:
        message_line += f" (reply-to {parent_id})"

    marker_index = lines.index(marker)
    insert_index = marker_index + 1
    while insert_index < len(lines) and not lines[insert_index].startswith("## "):
        insert_index += 1

    section_start = marker_index + 1
    section_lines = lines[section_start:insert_index]

    has_placeholder = any(line.strip() == "- none" for line in section_lines)
    if has_placeholder:
        cleaned_section = [line for line in section_lines if line.strip() != "- none"]
        while cleaned_section and cleaned_section[0].strip() == "":
            cleaned_section.pop(0)
        while cleaned_section and cleaned_section[-1].strip() == "":
            cleaned_section.pop()
        lines[section_start:insert_index] = cleaned_section
        insert_index = section_start + len(cleaned_section)

    lines.insert(insert_index, message_line)

    return "\n".join(lines).rstrip() + "\n"


@app.command("create")
def create_issue(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Issue title"),
    project: str = typer.Option(..., "--project", help="Project name"),
    description: str = typer.Option("", "--description", help="Issue description"),
    priority: str = typer.Option("medium", "--priority", help="Priority"),
    tags: list[str] = typer.Option([], "--tag", help="Issue tag. Repeat flag for multiple tags."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    issue_id = storage.next_issue_id(root, project)
    config = storage.load_project_config(root, project)
    metadata = {
        "id": issue_id,
        "title": title,
        "status": config.default_status,
        "priority": priority,
        "created_at": date.today().isoformat(),
        "tags": tags,
    }
    content = "## Description\n"
    content += (description or "TODO") + "\n\n"
    content += "## Tasks\n"
    content += "- [ ] implement\n"
    content += "- [ ] test\n"
    content += "- [ ] document\n\n"
    content += "## Implementation Notes\n"
    content += "- pending\n\n"
    content += "## Feedback Log\n"
    content += "- none\n\n"
    content += "## Evidence\n"
    content += "- pending\n"

    path = storage.issue_file_path(root, project, issue_id, title)
    parser.save_markdown(path, _ordered_issue_metadata(metadata), content)

    payload = {
        "ok": True,
        "project": project,
        "id": issue_id,
        "title": title,
        "path": str(path),
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Created {issue_id}")


@app.command("list")
def list_issues(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project", help="Project name"),
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    tag: str | None = typer.Option(None, "--tag", help="Filter by tag"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    records = query.iter_issue_records(root, project)

    if status:
        records = [r for r in records if r.status == status]
    if tag:
        records = [r for r in records if tag in r.tags]

    records = sorted(records, key=lambda r: r.issue_id)

    if json_output:
        emit_json(
            {
                "project": project,
                "count": len(records),
                "issues": [
                    {
                        "id": r.issue_id,
                        "title": r.title,
                        "status": r.status,
                        "priority": r.priority,
                        "tags": r.tags,
                        "path": str(r.path),
                    }
                    for r in records
                ],
            }
        )
        return

    typer.echo(f"PROJECT: {project}\n")
    if not records:
        typer.echo("No issues found")
        return
    _print_grouped(records)


@app.command("view")
def view_issue(
    ctx: typer.Context,
    issue_id: str = typer.Argument(..., help="Issue ID"),
    project: str | None = typer.Option(None, "--project", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    record = query.find_issue(root, issue_id, project)

    payload = {
        "project": record.project,
        "id": record.issue_id,
        "title": record.title,
        "status": record.status,
        "priority": record.priority,
        "created_at": record.created_at,
        "tags": record.tags,
        "path": str(record.path),
        "content": record.content,
    }
    metadata, _ = parser.load_markdown(record.path)
    payload["linked_issues"] = _load_links(metadata)
    payload["feedback"] = _load_feedback(metadata)

    if json_output:
        emit_json(payload)
        return

    typer.echo(f"{record.issue_id} - {record.title}")
    typer.echo(f"Project: {record.project}")
    typer.echo(f"Status: {record.status}")
    typer.echo(f"Priority: {record.priority}")
    typer.echo(f"Created: {record.created_at}")
    typer.echo("Tags: " + ", ".join(record.tags or []))
    linked_issues = payload["linked_issues"]
    feedback_items = payload["feedback"]
    typer.echo(f"Linked issues: {len(linked_issues)}")
    typer.echo(f"Feedback entries: {len(feedback_items)}")
    typer.echo("")
    typer.echo(record.content)


@app.command("update")
def update_issue(
    ctx: typer.Context,
    issue_id: str = typer.Argument(..., help="Issue ID"),
    project: str | None = typer.Option(None, "--project", help="Project name"),
    status: str | None = typer.Option(None, "--status", help="New status"),
    priority: str | None = typer.Option(None, "--priority", help="New priority"),
    title: str | None = typer.Option(None, "--title", help="New title"),
    add_tags: list[str] = typer.Option([], "--add-tag", help="Add tag. Repeat flag for multiple tags."),
    remove_tags: list[str] = typer.Option([], "--remove-tag", help="Remove tag. Repeat flag for multiple tags."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    record = query.find_issue(root, issue_id, project)
    metadata, content = parser.load_markdown(record.path)

    if status is not None:
        _validate_status(root, record.project, status)
        metadata["status"] = status
    if priority is not None:
        metadata["priority"] = priority
    if title is not None:
        metadata["title"] = title

    current_tags = list(metadata.get("tags", []))
    for tag in add_tags:
        if tag not in current_tags:
            current_tags.append(tag)
    for tag in remove_tags:
        current_tags = [value for value in current_tags if value != tag]
    metadata["tags"] = current_tags

    parser.save_markdown(record.path, _ordered_issue_metadata(metadata), content)

    payload = {
        "ok": True,
        "id": record.issue_id,
        "project": record.project,
        "path": str(record.path),
        "updated": {
            "status": metadata.get("status"),
            "priority": metadata.get("priority"),
            "title": metadata.get("title"),
            "tags": metadata.get("tags", []),
        },
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Updated {record.issue_id}")


@app.command("done")
def done_issue(
    ctx: typer.Context,
    issue_id: str = typer.Argument(..., help="Issue ID"),
    project: str | None = typer.Option(None, "--project", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    record = query.find_issue(root, issue_id, project)
    metadata, content = parser.load_markdown(record.path)
    _validate_status(root, record.project, "done")
    metadata["status"] = "done"
    parser.save_markdown(record.path, _ordered_issue_metadata(metadata), content)

    payload = {
        "ok": True,
        "id": record.issue_id,
        "project": record.project,
        "status": "done",
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Marked {record.issue_id} as done")


@app.command("link")
def link_issue(
    ctx: typer.Context,
    issue_id: str = typer.Argument(..., help="Source issue ID"),
    target: str = typer.Option(..., "--target", help="Target issue ID"),
    project: str | None = typer.Option(None, "--project", help="Source project name"),
    target_project: str | None = typer.Option(None, "--target-project", help="Target project name"),
    relation: str = typer.Option("relates-to", "--relation", help="Relationship label"),
    bidirectional: bool = typer.Option(True, "--bidirectional/--one-way", help="Write reverse link too"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    source_record = query.find_issue(root, issue_id, project)
    target_record = query.find_issue(root, target, target_project)

    source_metadata, source_content = parser.load_markdown(source_record.path)
    source_links = _load_links(source_metadata)
    normalized_target = _normalize_issue_id(target_record.issue_id)
    if not any(item["issue"] == normalized_target and item["project"] == target_record.project for item in source_links):
        source_links.append(
            {
                "issue": normalized_target,
                "project": target_record.project,
                "relation": relation,
            }
        )
    source_metadata["linked_issues"] = source_links
    parser.save_markdown(source_record.path, _ordered_issue_metadata(source_metadata), source_content)

    if bidirectional:
        target_metadata, target_content = parser.load_markdown(target_record.path)
        target_links = _load_links(target_metadata)
        normalized_source = _normalize_issue_id(source_record.issue_id)
        if not any(item["issue"] == normalized_source and item["project"] == source_record.project for item in target_links):
            target_links.append(
                {
                    "issue": normalized_source,
                    "project": source_record.project,
                    "relation": relation,
                }
            )
        target_metadata["linked_issues"] = target_links
        parser.save_markdown(target_record.path, _ordered_issue_metadata(target_metadata), target_content)

    payload = {
        "ok": True,
        "source": {
            "issue": source_record.issue_id,
            "project": source_record.project,
        },
        "target": {
            "issue": target_record.issue_id,
            "project": target_record.project,
        },
        "relation": relation,
        "bidirectional": bidirectional,
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(
        f"Linked {source_record.issue_id} ({source_record.project}) -> {target_record.issue_id} ({target_record.project})"
    )


@feedback_app.command("add")
def add_feedback(
    ctx: typer.Context,
    issue_id: str = typer.Argument(..., help="Issue ID"),
    message: str = typer.Argument(..., help="Feedback message"),
    project: str | None = typer.Option(None, "--project", help="Project name"),
    author: str = typer.Option("system", "--author", help="Feedback author"),
    parent_feedback_id: str | None = typer.Option(None, "--parent-feedback-id", help="Reply to a feedback entry"),
    completion: bool = typer.Option(False, "--completion", help="Mark this as completion feedback"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    record = query.find_issue(root, issue_id, project)
    metadata, content = parser.load_markdown(record.path)
    feedback_items = _load_feedback(metadata)

    if parent_feedback_id is not None and not any(str(item.get("id")) == parent_feedback_id for item in feedback_items):
        raise typer.BadParameter(f"Feedback entry not found: {parent_feedback_id}")

    feedback_id = _next_feedback_id(feedback_items)
    entry = {
        "id": feedback_id,
        "author": author,
        "type": "completion" if completion else "comment",
        "created_at": date.today().isoformat(),
        "message": message,
    }
    if parent_feedback_id is not None:
        entry["parent_id"] = parent_feedback_id

    feedback_items.append(entry)
    metadata["feedback"] = feedback_items
    updated_content = _append_feedback_to_body(content, entry)
    parser.save_markdown(record.path, _ordered_issue_metadata(metadata), updated_content)

    payload = {
        "ok": True,
        "project": record.project,
        "issue": record.issue_id,
        "feedback": entry,
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Added feedback {feedback_id} on {record.issue_id}")


@feedback_app.command("list")
def list_feedback(
    ctx: typer.Context,
    issue_id: str = typer.Argument(..., help="Issue ID"),
    project: str | None = typer.Option(None, "--project", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    record = query.find_issue(root, issue_id, project)
    metadata, _ = parser.load_markdown(record.path)
    feedback_items = _load_feedback(metadata)

    payload = {
        "project": record.project,
        "issue": record.issue_id,
        "count": len(feedback_items),
        "feedback": feedback_items,
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Feedback for {record.issue_id} ({record.project})")
    if not feedback_items:
        typer.echo("- none")
        return

    for item in feedback_items:
        item_id = str(item.get("id", ""))
        item_type = str(item.get("type", "comment"))
        author = str(item.get("author", "system"))
        created_at = str(item.get("created_at", ""))
        message = str(item.get("message", ""))
        parent_id = str(item.get("parent_id", "")).strip()

        typer.echo(f"- {item_id} [{item_type}] by {author} on {created_at}")
        if parent_id:
            typer.echo(f"  reply-to: {parent_id}")
        typer.echo(f"  {message}")
