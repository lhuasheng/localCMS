from __future__ import annotations

from pathlib import Path

import typer

from cli.commands.doc import app as doc_app
from cli.commands.issue import app as issue_app
from cli.commands.link import app as link_app
from cli.commands.project import app as project_app
from cli.core.storage import resolve_root

app = typer.Typer(help="CLI CMS: local-first multi-project issue and docs tracker")
app.add_typer(project_app, name="project")
app.add_typer(issue_app, name="issue")
app.add_typer(doc_app, name="doc")
app.add_typer(link_app, name="link")


@app.callback()
def main(
    ctx: typer.Context,
    root: Path | None = typer.Option(None, "--root", help="Override workspace root"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["root"] = resolve_root(root)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
