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


if __name__ == "__main__":
    unittest.main()