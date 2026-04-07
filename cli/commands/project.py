from __future__ import annotations

from pathlib import Path

import typer

from cli.core import parser, storage
from cli.core.models import ProjectConfig
from cli.core.render import emit_json

app = typer.Typer(help="Manage projects")


def _root(ctx: typer.Context) -> Path:
    return ctx.obj["root"]


@app.command("init")
def init_project(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    storage.ensure_base_dirs(root)
    storage.ensure_project_dirs(root, name)
    config = ProjectConfig(name=name)
    storage.save_project_config(root, name, config)

    result = {
        "ok": True,
        "project": name,
        "path": str(storage.project_dir(root, name)),
    }
    if json_output:
        emit_json(result)
        return

    typer.echo(f"Created project {name}")


@app.command("list")
def list_projects(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    projects = storage.list_projects(root)

    if json_output:
        emit_json({"projects": projects, "count": len(projects)})
        return

    if not projects:
        typer.echo("No projects found")
        return

    typer.echo("Projects:")
    for project in projects:
        typer.echo(f"- {project}")


@app.command("view")
def view_project(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    config = storage.load_project_config(root, name)
    issues_count = len(list(storage.issues_dir(root, name).glob("*.md")))
    docs_count = len(list(storage.docs_dir(root, name).glob("*.md")))
    payload = {
        "name": config.name,
        "default_status": config.default_status,
        "statuses": config.statuses,
        "issue_counter": config.issue_counter,
        "issues_count": issues_count,
        "docs_count": docs_count,
    }

    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Project: {config.name}")
    typer.echo(f"Default status: {config.default_status}")
    typer.echo("Statuses: " + ", ".join(config.statuses))
    typer.echo(f"Issue counter: {config.issue_counter}")
    typer.echo(f"Issues: {issues_count}")
    typer.echo(f"Docs: {docs_count}")
