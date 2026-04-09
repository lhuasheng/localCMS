from __future__ import annotations

import json
import tempfile
from pathlib import Path
import textwrap
import unittest

from typer.testing import CliRunner

from cli.core import parser
from cli.core.obsidian_vault import ObsidianVault
from cli.main import app


def _write_demo_project(root: Path, issue_counter: int = 0) -> None:
    (root / "projects" / "demo" / "issues").mkdir(parents=True)
    (root / "projects" / "demo" / "docs").mkdir(parents=True)
    (root / "projects" / "demo" / "project.yaml").write_text(
        textwrap.dedent(
            f"""
            name: demo
            default_status: todo
            statuses:
              - todo
              - in-progress
              - done
            issue_counter: {issue_counter}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def _write_markdown(path: Path, text: str) -> None:
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


class ObsidianVaultTests(unittest.TestCase):
    def test_repo_scan_has_no_unresolved_links(self) -> None:
        root = Path(__file__).resolve().parents[1]
        vault = ObsidianVault.scan(root)

        self.assertGreater(len(vault.notes), 0)
        self.assertEqual(vault.unresolved_links(), [])

    def test_wiki_links_resolve_by_stem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root, issue_counter=1)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "guide.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Guide
                ---

                # Guide

                See [[ISSUE-001-first-task]].
                """,
            )
            _write_markdown(
                root / "projects" / "demo" / "issues" / "ISSUE-001-first-task.md",
                """
                ---
                id: ISSUE-001
                title: First task
                status: todo
                priority: medium
                created_at: '2026-04-09'
                tags: []
                ---

                ## Description
                Demo
                """,
            )

            vault = ObsidianVault.scan(root)

            self.assertEqual(vault.unresolved_links(), [])

    def test_indented_code_blocks_do_not_create_link_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "guide.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Guide
                ---

                # Guide

                    [Broken](missing.md)
                    [[Missing note]]

                Plain text only.
                """,
            )

            vault = ObsidianVault.scan(root)

            self.assertEqual(vault.all_links(), [])
            self.assertEqual(vault.unresolved_links(), [])


class IssueTemplateTests(unittest.TestCase):
    def test_issue_create_can_use_obsidian_template(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".obsidian" / "templates").mkdir(parents=True)
            _write_demo_project(root)
            _write_markdown(
                root / ".obsidian" / "templates" / "issue-template.md",
                """
                ---
                id: {{id}}
                title: {{title}}
                status: {{status}}
                priority: {{priority}}
                created_at: {{created_at}}
                tags: {{tags_inline}}
                ---

                ## Description
                {{description}}
                """,
            )

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "issue",
                    "create",
                    "Template: driven task",
                    "--project",
                    "demo",
                    "--description",
                    "Use the opt-in template: keep YAML safe",
                    "--tag",
                    "backend",
                    "--template",
                    "issue-template",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)

            created = root / "projects" / "demo" / "issues" / "ISSUE-001-template-driven-task.md"
            self.assertTrue(created.exists())
            metadata, content = parser.load_markdown(created)
            self.assertEqual(metadata["title"], "Template: driven task")
            self.assertEqual(metadata["tags"], ["backend"])
            self.assertEqual(content.strip(), "## Description\nUse the opt-in template: keep YAML safe")

    def test_template_failure_does_not_consume_issue_id(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".obsidian" / "templates").mkdir(parents=True)
            _write_demo_project(root)
            _write_markdown(
                root / ".obsidian" / "templates" / "broken-template.md",
                """
                ---
                id: {{id}}
                title: {{title}}
                status: {{status}}
                priority: {{priority}}
                created_at: {{created_at}}
                tags: {{tags_inline}}
                reviewer: {{reviewer}}
                ---

                ## Description
                {{description}}
                """,
            )

            failed = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "issue",
                    "create",
                    "Broken template task",
                    "--project",
                    "demo",
                    "--template",
                    "broken-template",
                ],
            )

            self.assertNotEqual(failed.exit_code, 0)
            self.assertEqual(parser.read_yaml(root / "projects" / "demo" / "project.yaml")["issue_counter"], 0)
            self.assertEqual(list((root / "projects" / "demo" / "issues").glob("*.md")), [])

            succeeded = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "issue",
                    "create",
                    "Recovered task",
                    "--project",
                    "demo",
                ],
            )

            self.assertEqual(succeeded.exit_code, 0, succeeded.stdout)
            self.assertTrue((root / "projects" / "demo" / "issues" / "ISSUE-001-recovered-task.md").exists())
            self.assertEqual(parser.read_yaml(root / "projects" / "demo" / "project.yaml")["issue_counter"], 1)

    def test_issue_create_stores_assignee_and_project_in_metadata(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "issue",
                    "create",
                    "Assignee test task",
                    "--project",
                    "demo",
                    "--assignee",
                    "alice",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            created = root / "projects" / "demo" / "issues" / "ISSUE-001-assignee-test-task.md"
            self.assertTrue(created.exists())
            metadata, _ = parser.load_markdown(created)
            self.assertEqual(metadata["assignee"], "alice")
            self.assertEqual(metadata["project"], "demo")

    def test_issue_create_warns_on_missing_required_fields(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "issue",
                    "create",
                    "No assignee task",
                    "--project",
                    "demo",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Warning", result.output)
            self.assertIn("assignee", result.output)

    def test_issue_create_with_full_required_fields_no_warning(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "issue",
                    "create",
                    "Fully specified task",
                    "--project",
                    "demo",
                    "--assignee",
                    "bob",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertNotIn("Warning", result.output)

    def test_issue_template_with_assignee_and_project_placeholders(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".obsidian" / "templates").mkdir(parents=True)
            _write_demo_project(root)
            _write_markdown(
                root / ".obsidian" / "templates" / "issue-template.md",
                """
                ---
                # localCMS issue template
                id: {{id}}
                title: {{title}}
                status: {{status}}
                assignee: {{assignee}}
                created_at: {{created_at}}
                project: {{project}}
                priority: {{priority}}
                tags: {{tags_inline}}
                ---

                ## Description
                {{description}}
                """,
            )

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "issue",
                    "create",
                    "Full template task",
                    "--project",
                    "demo",
                    "--assignee",
                    "carol",
                    "--description",
                    "Testing full template",
                    "--template",
                    "issue-template",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            created = root / "projects" / "demo" / "issues" / "ISSUE-001-full-template-task.md"
            self.assertTrue(created.exists())
            metadata, _ = parser.load_markdown(created)
            self.assertEqual(metadata["assignee"], "carol")
            self.assertEqual(metadata["project"], "demo")


class ObsidianCommandTests(unittest.TestCase):
    def test_validate_backlinks_reports_unresolved_links_and_exits_non_zero(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "guide.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Guide
                ---

                # Guide

                See [Missing note](missing-note.md).
                """,
            )

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "validate-backlinks",
                    "--project",
                    "demo",
                    "--json",
                ],
            )

            self.assertEqual(result.exit_code, 1, result.stdout)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["unresolved_count"], 1)
            self.assertEqual(payload["unresolved"][0]["target"], "missing-note.md")

    def test_audit_graph_detects_cycles_and_saves_report(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root, issue_counter=2)
            _write_markdown(
                root / "projects" / "demo" / "issues" / "ISSUE-001-alpha.md",
                """
                ---
                id: ISSUE-001
                title: Alpha
                status: todo
                priority: medium
                created_at: '2026-04-09'
                tags: []
                ---

                ## Description
                See [[ISSUE-002-beta]].
                """,
            )
            _write_markdown(
                root / "projects" / "demo" / "issues" / "ISSUE-002-beta.md",
                """
                ---
                id: ISSUE-002
                title: Beta
                status: todo
                priority: medium
                created_at: '2026-04-09'
                tags: []
                ---

                ## Description
                See [[ISSUE-001-alpha]].
                """,
            )

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "audit-graph",
                    "--project",
                    "demo",
                    "--json",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload["cycles"]), 1)
            self.assertIn("report_path", payload)
            report_path = Path(payload["report_path"])
            self.assertTrue(report_path.exists())
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("Vault Audit Report", report_text)
            self.assertIn("Link Cycles", report_text)
            self.assertIn("ISSUE-001-alpha", report_text)

    def test_audit_graph_no_save_report_skips_file(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "guide.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Guide
                ---

                # Guide

                Plain text only.
                """,
            )

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "audit-graph",
                    "--project",
                    "demo",
                    "--no-save-report",
                    "--json",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertNotIn("report_path", payload)
            reports_dir = root / "projects" / "demo" / "audit-reports"
            self.assertFalse(reports_dir.exists())

    def test_audit_graph_no_cycles_clean_vault(self) -> None:
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root, issue_counter=1)
            _write_markdown(
                root / "projects" / "demo" / "issues" / "ISSUE-001-clean.md",
                """
                ---
                id: ISSUE-001
                title: Clean
                status: todo
                priority: medium
                created_at: '2026-04-09'
                tags: []
                ---

                ## Description
                No links.
                """,
            )

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "audit-graph",
                    "--project",
                    "demo",
                    "--no-save-report",
                    "--json",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["cycles"], [])


class AuditGraphCommandTests(unittest.TestCase):
    def _setup_clean_project(self, root: Path) -> None:
        _write_demo_project(root, issue_counter=1)
        _write_markdown(
            root / "projects" / "demo" / "docs" / "index.md",
            """
            ---
            created_at: '2026-04-09'
            project: demo
            title: Index
            ---

            # Index

            See [[ISSUE-001-first-task]].
            """,
        )
        _write_markdown(
            root / "projects" / "demo" / "issues" / "ISSUE-001-first-task.md",
            """
            ---
            id: ISSUE-001
            title: First task
            status: todo
            priority: medium
            created_at: '2026-04-09'
            tags: []
            ---

            ## Description
            Demo
            """,
        )

    def test_audit_graph_exits_zero_when_no_critical_issues(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._setup_clean_project(root)

            result = runner.invoke(
                app,
                ["--root", str(root), "audit-graph", "--project", "demo"],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)

    def test_audit_graph_exits_one_when_broken_links_exist(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "guide.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Guide
                ---

                # Guide

                See [Missing](missing.md).
                """,
            )

            result = runner.invoke(
                app,
                ["--root", str(root), "audit-graph", "--project", "demo"],
            )

            self.assertEqual(result.exit_code, 1, result.stdout)

    def test_audit_graph_saves_report_to_audit_reports_dir(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._setup_clean_project(root)

            result = runner.invoke(
                app,
                ["--root", str(root), "audit-graph", "--project", "demo"],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            audit_dir = root / "projects" / "demo" / "audit-reports"
            self.assertTrue(audit_dir.exists())
            reports = list(audit_dir.glob("*.md"))
            self.assertEqual(len(reports), 1)
            content = reports[0].read_text(encoding="utf-8")
            self.assertIn("# Graph Audit Report", content)
            self.assertIn("## Summary", content)
            self.assertIn("## Broken Links", content)
            self.assertIn("## Orphaned Documents", content)
            self.assertIn("## Circular Dependencies", content)

    def test_audit_graph_output_flag_writes_to_custom_path(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._setup_clean_project(root)
            custom_output = root / "custom-report.md"

            result = runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "audit-graph",
                    "--project",
                    "demo",
                    "--output",
                    str(custom_output),
                ],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            self.assertTrue(custom_output.exists())
            content = custom_output.read_text(encoding="utf-8")
            self.assertIn("# Graph Audit Report", content)

    def test_audit_graph_json_includes_all_fields(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._setup_clean_project(root)

            result = runner.invoke(
                app,
                ["--root", str(root), "audit-graph", "--project", "demo", "--json"],
            )

            self.assertEqual(result.exit_code, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertIn("notes", payload)
            self.assertIn("links", payload)
            self.assertIn("errors", payload)
            self.assertIn("orphans", payload)
            self.assertIn("unresolved", payload)
            self.assertIn("cycles", payload)
            self.assertIn("summary", payload)
            self.assertFalse(payload["has_critical"])

    def test_audit_graph_json_exits_one_on_broken_links(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "guide.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Guide
                ---

                # Guide

                See [Missing](missing.md).
                """,
            )

            result = runner.invoke(
                app,
                ["--root", str(root), "audit-graph", "--project", "demo", "--json"],
            )

            self.assertEqual(result.exit_code, 1, result.stdout)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["has_critical"])
            self.assertEqual(len(payload["unresolved"]), 1)
            self.assertIsNotNone(payload["unresolved"][0]["line"])

    def test_audit_graph_report_contains_timestamp(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._setup_clean_project(root)
            custom_output = root / "report.md"

            runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "audit-graph",
                    "--project",
                    "demo",
                    "--output",
                    str(custom_output),
                ],
            )

            content = custom_output.read_text(encoding="utf-8")
            self.assertIn("**Generated:**", content)
            self.assertIn("UTC", content)

    def test_audit_graph_markdown_report_includes_broken_link_line_number(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "guide.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Guide
                ---

                # Guide

                See [Missing](missing.md).
                """,
            )
            custom_output = root / "report.md"

            runner.invoke(
                app,
                [
                    "--root",
                    str(root),
                    "audit-graph",
                    "--project",
                    "demo",
                    "--output",
                    str(custom_output),
                ],
            )

            content = custom_output.read_text(encoding="utf-8")
            self.assertIn("missing.md", content)
            # The line number column should be present in the table
            self.assertIn("| Line |", content)


class CircularDependencyTests(unittest.TestCase):
    def test_circular_dependencies_detects_simple_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "a.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: A
                ---
                See [[b]].
                """,
            )
            _write_markdown(
                root / "projects" / "demo" / "docs" / "b.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: B
                ---
                See [[a]].
                """,
            )

            vault = ObsidianVault.scan(root)
            cycles = vault.circular_dependencies()

            self.assertEqual(len(cycles), 1)
            cycle_stems = {p.stem for p in cycles[0]}
            self.assertIn("a", cycle_stems)
            self.assertIn("b", cycle_stems)

    def test_circular_dependencies_returns_empty_when_no_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root, issue_counter=1)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "index.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: Index
                ---
                See [[ISSUE-001-task]].
                """,
            )
            _write_markdown(
                root / "projects" / "demo" / "issues" / "ISSUE-001-task.md",
                """
                ---
                id: ISSUE-001
                title: Task
                status: todo
                priority: medium
                created_at: '2026-04-09'
                tags: []
                ---
                ## Description
                No back-link.
                """,
            )

            vault = ObsidianVault.scan(root)
            cycles = vault.circular_dependencies()

            self.assertEqual(cycles, [])

    def test_audit_graph_exits_one_on_cycles(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_demo_project(root)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "a.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: A
                ---
                See [[b]].
                """,
            )
            _write_markdown(
                root / "projects" / "demo" / "docs" / "b.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: B
                ---
                See [[a]].
                """,
            )

            result = runner.invoke(
                app,
                ["--root", str(root), "audit-graph", "--project", "demo"],
            )

            self.assertEqual(result.exit_code, 1, result.stdout)
            self.assertIn("Circular Dependencies", result.stdout)


if __name__ == "__main__":
    unittest.main()
