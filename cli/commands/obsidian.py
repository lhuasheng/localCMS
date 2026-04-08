from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer

from cli.core.obsidian_vault import ObsidianVault
from cli.core.render import emit_json
from cli.core import storage


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


def _build_audit_report(
    root: Path,
    project: str | None,
    vault: ObsidianVault,
    timestamp: str,
) -> str:
    unresolved = vault.unresolved_links()
    orphan_notes = vault.orphan_notes()
    cycles = vault.link_cycles()
    summary = vault.summary_by_project()

    lines: list[str] = []
    lines.append(f"# Vault Audit Report")
    lines.append(f"")
    lines.append(f"**Generated:** {timestamp}")
    if project:
        lines.append(f"**Project:** {project}")
    lines.append(f"**Notes scanned:** {len(vault.notes)}")
    lines.append(f"")

    lines.append(f"## Per-Project Summary")
    lines.append(f"")
    lines.append(f"| Project | Notes | Docs | Issues | Links | Orphans | Unresolved |")
    lines.append(f"|---------|-------|------|--------|-------|---------|------------|")
    for item in summary:
        lines.append(
            f"| {item['project']} | {item['notes']} | {item['docs']} | {item['issues']} "
            f"| {item['outbound_links']} | {item['orphans']} | {item['unresolved_links']} |"
        )
    lines.append(f"")

    lines.append(f"## Broken Links ({len(unresolved)})")
    lines.append(f"")
    if unresolved:
        for item in unresolved:
            rel = item.source_path.relative_to(root)
            lines.append(f"- `{rel}` [{item.link_type}] → `{item.raw_target}` ({item.reason or 'unresolved'})")
    else:
        lines.append(f"No broken links found.")
    lines.append(f"")

    lines.append(f"## Orphaned Notes ({len(orphan_notes)})")
    lines.append(f"")
    if orphan_notes:
        for note in orphan_notes:
            lines.append(f"- `{note.relative_path}`")
    else:
        lines.append(f"No orphaned notes found.")
    lines.append(f"")

    lines.append(f"## Link Cycles ({len(cycles)})")
    lines.append(f"")
    if cycles:
        for i, cycle in enumerate(cycles, start=1):
            node_names = " → ".join(str(node_path.relative_to(root)) for node_path in cycle)
            lines.append(f"{i}. {node_names} → *(cycle)*")
    else:
        lines.append(f"No link cycles detected.")
    lines.append(f"")

    return "\n".join(lines)


def audit_graph(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", help="Restrict audit to one project"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    save_report: bool = typer.Option(True, "--save-report/--no-save-report", help="Save audit report to disk"),
) -> None:
    root = _root(ctx)
    vault = ObsidianVault.scan(root, project)
    unresolved = vault.unresolved_links()
    orphan_notes = vault.orphan_notes()
    cycles = vault.link_cycles()
    summary = vault.summary_by_project()

    payload = {
        "project": project,
        "notes": len(vault.notes),
        "orphans": [str(note.relative_path) for note in orphan_notes],
        "cycles": [
            [str(p.relative_to(root)) for p in cycle]
            for cycle in cycles
        ],
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

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_file = datetime.now().strftime("%Y%m%d-%H%M%S")

    if save_report and project:
        report_text = _build_audit_report(root, project, vault, timestamp)
        reports_dir = storage.audit_reports_dir(root, project)
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"audit-{timestamp_file}.md"
        report_path.write_text(report_text, encoding="utf-8")
        payload["report_path"] = str(report_path)

    if json_output:
        emit_json(payload)
        return

    typer.echo(f"Audited {len(vault.notes)} notes  [{timestamp}]")
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

    typer.echo("")
    typer.echo("Link cycles:")
    if cycles:
        for cycle in cycles:
            node_names = " -> ".join(str(p.relative_to(root)) for p in cycle)
            typer.echo(f"- {node_names} -> (cycle)")
    else:
        typer.echo("- none")

    if save_report and project:
        typer.echo("")
        typer.echo(f"Report saved to: {payload['report_path']}")