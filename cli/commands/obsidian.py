from __future__ import annotations

from datetime import datetime, timezone
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


def audit_graph(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project", help="Restrict audit to one project"),
    output: Path | None = typer.Option(None, "--output", help="Write Markdown report to this file instead of auto-save"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON summary (skips Markdown save)"),
) -> None:
    root = _root(ctx)
    vault = ObsidianVault.scan(root, project)
    all_links = vault.all_links()
    unresolved = vault.unresolved_links()
    orphan_notes = vault.orphan_notes()
    cycles = vault.circular_dependencies()
    proj_summary = vault.summary_by_project()

    has_critical = bool(unresolved or cycles)

    if json_output:
        payload = {
            "project": project,
            "notes": len(vault.notes),
            "links": len(all_links),
            "errors": len(unresolved) + len(cycles),
            "has_critical": has_critical,
            "orphans": [str(note.relative_path) for note in orphan_notes],
            "unresolved": [
                {
                    "path": str(item.source_path.relative_to(root)),
                    "line": item.line_number,
                    "project": item.source_project,
                    "type": item.link_type,
                    "target": item.raw_target,
                    "reason": item.reason,
                }
                for item in unresolved
            ],
            "cycles": [
                [str(p.relative_to(root)) for p in cycle]
                for cycle in cycles
            ],
            "summary": proj_summary,
        }
        emit_json(payload)
        if has_critical:
            raise typer.Exit(code=1)
        return

    now = datetime.now(tz=timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    report = _build_markdown_report(
        root=root,
        project=project,
        timestamp=timestamp,
        vault=vault,
        all_links=all_links,
        unresolved=unresolved,
        orphan_notes=orphan_notes,
        cycles=cycles,
        proj_summary=proj_summary,
    )

    # Determine output path
    if output is not None:
        report_path = output
    else:
        file_ts = now.strftime("%Y-%m-%d-%H%M%S")
        if project:
            audit_dir = storage.project_dir(root, project) / "audit-reports"
        else:
            audit_dir = storage.projects_dir(root) / "audit-reports"
        audit_dir.mkdir(parents=True, exist_ok=True)
        report_path = audit_dir / f"{file_ts}.md"

    report_path.write_text(report, encoding="utf-8")
    typer.echo(f"Audit report saved to: {report_path}")
    typer.echo(report)

    if has_critical:
        raise typer.Exit(code=1)


def _build_markdown_report(
    *,
    root: Path,
    project: str | None,
    timestamp: str,
    vault: ObsidianVault,
    all_links: list,
    unresolved: list,
    orphan_notes: list,
    cycles: list,
    proj_summary: list,
) -> str:
    lines: list[str] = []

    scope = project if project else "all projects"
    lines.append(f"# Graph Audit Report")
    lines.append(f"")
    lines.append(f"**Generated:** {timestamp}  ")
    lines.append(f"**Scope:** {scope}")
    lines.append(f"")

    # Summary
    error_count = len(unresolved) + len(cycles)
    lines.append("## Summary")
    lines.append(f"")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total files | {len(vault.notes)} |")
    lines.append(f"| Total links | {len(all_links)} |")
    lines.append(f"| Broken links | {len(unresolved)} |")
    lines.append(f"| Orphaned documents | {len(orphan_notes)} |")
    lines.append(f"| Circular dependencies | {len(cycles)} |")
    lines.append(f"| **Total errors** | **{error_count}** |")
    lines.append(f"")

    # Per-project breakdown
    if proj_summary:
        lines.append("## Per-Project Summary")
        lines.append(f"")
        lines.append(f"| Project | Notes | Docs | Issues | Links | Orphans | Broken |")
        lines.append(f"|---------|-------|------|--------|-------|---------|--------|")
        for item in proj_summary:
            lines.append(
                f"| {item['project']} | {item['notes']} | {item['docs']} | {item['issues']} "
                f"| {item['outbound_links']} | {item['orphans']} | {item['unresolved_links']} |"
            )
        lines.append(f"")

    # Broken links
    lines.append("## Broken Links")
    lines.append(f"")
    if unresolved:
        lines.append("| File | Line | Reference | Reason | Suggestion |")
        lines.append("|------|------|-----------|--------|------------|")
        for item in unresolved:
            rel = item.source_path.relative_to(root).as_posix()
            line = str(item.line_number) if item.line_number is not None else "—"
            reason = item.reason or "unresolved"
            suggestion = _suggest_broken_link(item.raw_target, item.link_type)
            lines.append(f"| `{rel}` | {line} | `{item.raw_target}` | {reason} | {suggestion} |")
    else:
        lines.append("_No broken links found. ✓_")
    lines.append(f"")

    # Orphaned documents
    lines.append("## Orphaned Documents")
    lines.append(f"")
    if orphan_notes:
        lines.append("These files have no incoming links and may be unused:")
        lines.append(f"")
        for note in orphan_notes:
            suggestion = "Link to this document from a relevant index or hub note, or delete if no longer needed."
            lines.append(f"- `{note.relative_path.as_posix()}` — {suggestion}")
    else:
        lines.append("_No orphaned documents found. ✓_")
    lines.append(f"")

    # Circular dependencies
    lines.append("## Circular Dependencies")
    lines.append(f"")
    if cycles:
        lines.append("The following note cycles were detected:")
        lines.append(f"")
        for cycle in cycles:
            cycle_str = " → ".join(p.relative_to(root).as_posix() for p in cycle)
            cycle_str += f" → {cycle[0].relative_to(root).as_posix()}"
            lines.append(f"- {cycle_str}")
            lines.append(f"  - **Suggestion:** Break the cycle by removing or redirecting one of the links above.")
    else:
        lines.append("_No circular dependencies found. ✓_")
    lines.append(f"")

    # Overall health
    lines.append("## Health")
    lines.append(f"")
    if error_count == 0:
        lines.append("✅ **Graph is healthy.** No broken links or circular dependencies detected.")
    else:
        lines.append(f"❌ **{error_count} issue(s) require attention** (broken links and/or circular dependencies).")
    lines.append(f"")

    return "\n".join(lines)


def _suggest_broken_link(raw_target: str, link_type: str) -> str:
    if link_type == "wiki":
        return f"Create a note named `{raw_target}` or update the link to an existing note."
    return f"Verify the file exists at `{raw_target}` or update the link to the correct path."
