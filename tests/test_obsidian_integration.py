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


class FrontmatterValidationTests(unittest.TestCase):
    """Tests for auto-validation of issue frontmatter against the default template."""

    _STANDARD_TEMPLATE = textwrap.dedent(
        """
        ---
        id: {{id}}
        title: {{title}}
        status: {{status}}
        priority: {{priority}}
        created_at: {{created_at}}
        tags: {{tags_inline}}
        ---
        """
    ).strip()

    _EXTENDED_TEMPLATE = textwrap.dedent(
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
        """
    ).strip()

    def _setup_root(self, temp_dir: str, template_text: str | None = None) -> Path:
        root = Path(temp_dir)
        _write_demo_project(root)
        if template_text is not None:
            (root / ".obsidian" / "templates").mkdir(parents=True)
            (root / ".obsidian" / "templates" / "issue-template.md").write_text(
                template_text + "\n", encoding="utf-8"
            )
        return root

    def _create_issue(self, runner: object, root: Path, extra_args: list[str] | None = None) -> object:
        args = ["--root", str(root), "issue", "create", "Test task", "--project", "demo"]
        if extra_args:
            args.extend(extra_args)
        return runner.invoke(app, args)

    def _write_issue(self, root: Path, issue_id: str, extra_metadata: str = "") -> Path:
        path = root / "projects" / "demo" / "issues" / f"{issue_id}-test-task.md"
        path.write_text(
            textwrap.dedent(
                f"""
                ---
                id: {issue_id}
                title: Test task
                status: todo
                priority: medium
                created_at: '2026-01-01'
                tags: []
                {extra_metadata}
                ---

                ## Description
                demo
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        return path

    # ------------------------------------------------------------------ create

    def test_create_passes_when_no_template_exists(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, template_text=None)
            result = self._create_issue(runner, root)
            self.assertEqual(result.exit_code, 0, result.stdout)

    def test_create_passes_with_standard_template(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._STANDARD_TEMPLATE)
            result = self._create_issue(runner, root)
            self.assertEqual(result.exit_code, 0, result.stdout)

    def test_create_blocked_when_required_field_missing(self) -> None:
        """Template requires 'reviewer'; create without it must fail with a clear message."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._EXTENDED_TEMPLATE)
            result = self._create_issue(runner, root)
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("reviewer", result.output)
            self.assertIn("Cannot create issue", result.output)

    def test_create_skip_validation_bypasses_check(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._EXTENDED_TEMPLATE)
            result = self._create_issue(runner, root, extra_args=["--skip-validation"])
            self.assertEqual(result.exit_code, 0, result.stdout)

    def test_create_blocked_does_not_consume_issue_id(self) -> None:
        """A failed validation must not increment the issue counter."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._EXTENDED_TEMPLATE)
            failed = self._create_issue(runner, root)
            self.assertNotEqual(failed.exit_code, 0)
            config = parser.read_yaml(root / "projects" / "demo" / "project.yaml")
            self.assertEqual(config["issue_counter"], 0)

    # ------------------------------------------------------------------ update

    def test_update_passes_when_no_template_exists(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, template_text=None)
            self._write_issue(root, "ISSUE-001")
            result = runner.invoke(
                app, ["--root", str(root), "issue", "update", "ISSUE-001", "--project", "demo", "--status", "done"]
            )
            self.assertEqual(result.exit_code, 0, result.stdout)

    def test_update_passes_with_all_required_fields_present(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._STANDARD_TEMPLATE)
            self._write_issue(root, "ISSUE-001")
            result = runner.invoke(
                app, ["--root", str(root), "issue", "update", "ISSUE-001", "--project", "demo", "--status", "done"]
            )
            self.assertEqual(result.exit_code, 0, result.stdout)

    def test_update_blocked_when_required_field_missing(self) -> None:
        """Template requires 'reviewer'; updating an issue that lacks it must fail."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._EXTENDED_TEMPLATE)
            self._write_issue(root, "ISSUE-001")
            result = runner.invoke(
                app, ["--root", str(root), "issue", "update", "ISSUE-001", "--project", "demo", "--status", "done"]
            )
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("reviewer", result.output)
            self.assertIn("Cannot update issue", result.output)

    def test_update_blocked_does_not_persist_changes(self) -> None:
        """When validation blocks an update the file must not be modified."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._EXTENDED_TEMPLATE)
            path = self._write_issue(root, "ISSUE-001")
            original_text = path.read_text(encoding="utf-8")
            runner.invoke(
                app, ["--root", str(root), "issue", "update", "ISSUE-001", "--project", "demo", "--status", "done"]
            )
            self.assertEqual(path.read_text(encoding="utf-8"), original_text)

    def test_update_skip_validation_bypasses_check(self) -> None:
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._setup_root(temp_dir, self._EXTENDED_TEMPLATE)
            self._write_issue(root, "ISSUE-001")
            result = runner.invoke(
                app,
                [
                    "--root", str(root),
                    "issue", "update", "ISSUE-001",
                    "--project", "demo",
                    "--status", "done",
                    "--skip-validation",
                ],
            )
            self.assertEqual(result.exit_code, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()