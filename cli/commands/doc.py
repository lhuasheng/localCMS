from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from cli.core import parser, storage
from cli.core.render import emit_json

app = typer.Typer(help="Manage documentation")


def _root(ctx: typer.Context) -> Path:
    return ctx.obj["root"]


@app.command("create")
def create_doc(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Document slug or name"),
    project: str = typer.Option(..., "--project", help="Project name"),
    title: str | None = typer.Option(None, "--title", help="Document title"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    file_path = storage.doc_file_path(root, project, name)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "title": title or name,
        "created_at": date.today().isoformat(),
        "project": project,
    }
    content = f"# {title or name}\n\nDescribe this document.\n"
    parser.save_markdown(file_path, metadata, content)

    payload = {"ok": True, "project": project, "path": str(file_path)}
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Created doc {file_path.name}")


@app.command("list")
def list_docs(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    folder = storage.docs_dir(root, project)
    docs = sorted([f.name for f in folder.glob("*.md")]) if folder.exists() else []

    if json_output:
        emit_json({"project": project, "count": len(docs), "docs": docs})
        return

    if not docs:
        typer.echo("No docs found")
        return
    typer.echo(f"Docs ({project}):")
    for doc in docs:
        typer.echo(f"- {doc}")


@app.command("view")
def view_doc(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Document name or slug"),
    project: str = typer.Option(..., "--project", help="Project name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    path = storage.doc_file_path(root, project, name)
    if not path.exists() and not name.endswith(".md"):
        path = storage.docs_dir(root, project) / name

    if not path.exists():
        raise typer.BadParameter(f"Doc not found: {name}")

    metadata, content = parser.load_markdown(path)
    payload = {
        "project": project,
        "path": str(path),
        "metadata": metadata,
        "content": content,
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Doc: {path.name}")
    for key, value in metadata.items():
        typer.echo(f"{key}: {value}")
    typer.echo("")
    typer.echo(content)
