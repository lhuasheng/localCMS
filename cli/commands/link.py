from __future__ import annotations

import re
from pathlib import Path

import typer

from cli.core import parser, query
from cli.core.render import emit_json

app = typer.Typer(help="Inspect links between issues and docs")

ISSUE_PATTERN = re.compile(r"\bISSUE-\d{3,}\b")
DOC_PATTERN = re.compile(r"\.\./docs/[\w\-./]+\.md")


def _root(ctx: typer.Context) -> Path:
    return ctx.obj["root"]


@app.command("issue-links")
def issue_links(
    ctx: typer.Context,
    issue_id: str = typer.Argument(..., help="Issue ID"),
    project: str | None = typer.Option(None, "--project", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    record = query.find_issue(root, issue_id, project)
    metadata, _ = parser.load_markdown(record.path)
    explicit_links = metadata.get("linked_issues", [])
    if not isinstance(explicit_links, list):
        explicit_links = []

    referenced_issues = sorted(set(ISSUE_PATTERN.findall(record.content)) - {record.issue_id})
    referenced_docs = sorted(set(DOC_PATTERN.findall(record.content)))

    payload = {
        "issue": record.issue_id,
        "project": record.project,
        "linked_issues": explicit_links,
        "referenced_issues": referenced_issues,
        "referenced_docs": referenced_docs,
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Links for {record.issue_id} ({record.project})")
    typer.echo("Linked issues (metadata):")
    if explicit_links:
        for item in explicit_links:
            issue_value = item.get("issue", "") if isinstance(item, dict) else ""
            project_value = item.get("project", "") if isinstance(item, dict) else ""
            relation_value = item.get("relation", "relates-to") if isinstance(item, dict) else "relates-to"
            typer.echo(f"- {issue_value} ({project_value}) relation={relation_value}")
    else:
        typer.echo("- none")

    typer.echo("Referenced issues:")
    if referenced_issues:
        for item in referenced_issues:
            typer.echo(f"- {item}")
    else:
        typer.echo("- none")

    typer.echo("Referenced docs:")
    if referenced_docs:
        for item in referenced_docs:
            typer.echo(f"- {item}")
    else:
        typer.echo("- none")
