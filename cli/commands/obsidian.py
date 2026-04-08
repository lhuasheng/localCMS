from __future__ import annotations

from pathlib import Path

import typer

from cli.core.obsidian_vault import ObsidianVault
from cli.core.render import emit_json


def _root(ctx: typer.Context) -> Path:
    return ctx.obj["root"]


def validate_backlinks(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", help="Restrict validation to one project"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    vault = ObsidianVault.scan(root, project)
    links = vault.all_links()
    unresolved = vault.unresolved_links()

    payload = {
        "ok": len(unresolved) == 0,
        "project": project,
        "notes": len(vault.notes),
        "links_checked": len(links),
        "unresolved_count": len(unresolved),
        "unresolved": [
            {
                "path": str(item.source_path.relative_to(root)),
                "project": item.source_project,
                "type": item.link_type,
                "target": item.raw_target,
                "reason": item.reason,
            }
            for item in unresolved
        ],
    }
    if json_output:
        emit_json(payload)
        if unresolved:
            raise typer.Exit(code=1)
        return

    if not unresolved:
        typer.echo(f"Validated {len(vault.notes)} notes and {len(links)} links. No unresolved links found.")
        return

    typer.echo(f"Detected {len(unresolved)} unresolved links across {len(vault.notes)} notes:")
    for item in unresolved:
        relative_path = item.source_path.relative_to(root)
        typer.echo(f"- {relative_path} [{item.link_type}] -> {item.raw_target} ({item.reason or 'unresolved'})")
    raise typer.Exit(code=1)


def audit_graph(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", help="Restrict audit to one project"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    root = _root(ctx)
    vault = ObsidianVault.scan(root, project)
    unresolved = vault.unresolved_links()
    orphan_notes = vault.orphan_notes()
    summary = vault.summary_by_project()

    payload = {
        "project": project,
        "notes": len(vault.notes),
        "orphans": [str(note.relative_path) for note in orphan_notes],
        "unresolved": [
            {
                "path": str(item.source_path.relative_to(root)),
                "project": item.source_project,
                "type": item.link_type,
                "target": item.raw_target,
                "reason": item.reason,
            }
            for item in unresolved
        ],
        "summary": summary,
    }
    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Audited {len(vault.notes)} notes")
    typer.echo("")
    typer.echo("Per-project summary:")
    for item in summary:
        typer.echo(
            f"- {item['project']}: notes={item['notes']}, docs={item['docs']}, issues={item['issues']}, "
            f"outbound_links={item['outbound_links']}, orphans={item['orphans']}, unresolved={item['unresolved_links']}"
        )

    typer.echo("")
    typer.echo("Orphan notes:")
    if orphan_notes:
        for note in orphan_notes:
            typer.echo(f"- {note.relative_path}")
    else:
        typer.echo("- none")

    typer.echo("")
    typer.echo("Unresolved links:")
    if unresolved:
        for item in unresolved:
            typer.echo(f"- {item.source_path.relative_to(root)} [{item.link_type}] -> {item.raw_target}")
    else:
        typer.echo("- none")