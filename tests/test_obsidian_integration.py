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


class ObsidianVaultGraphTests(unittest.TestCase):
    """Tests for the graph-query methods added in Issue #10."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        _write_demo_project(self.root, issue_counter=2)

        # guide.md → issue-001.md (markdown link)
        _write_markdown(
            self.root / "projects" / "demo" / "docs" / "guide.md",
            """
            ---
            created_at: '2026-04-09'
            project: demo
            title: Guide
            ---

            # Guide

            See [First task](../issues/ISSUE-001-first-task.md).
            """,
        )
        # issue-001.md → issue-002.md (wiki link)
        _write_markdown(
            self.root / "projects" / "demo" / "issues" / "ISSUE-001-first-task.md",
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
            Depends on [[ISSUE-002-second-task]].
            """,
        )
        # issue-002.md has no outbound links → orphan candidate unless referenced
        _write_markdown(
            self.root / "projects" / "demo" / "issues" / "ISSUE-002-second-task.md",
            """
            ---
            id: ISSUE-002
            title: Second task
            status: todo
            priority: medium
            created_at: '2026-04-09'
            tags: []
            ---

            ## Description
            Stand-alone task.
            """,
        )

        self.vault = ObsidianVault.scan(self.root)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_get_all_files_returns_all_notes(self) -> None:
        files = self.vault.get_all_files()
        self.assertEqual(len(files), 3)
        stems = {n.path.stem for n in files}
        self.assertIn("guide", stems)
        self.assertIn("ISSUE-001-first-task", stems)
        self.assertIn("ISSUE-002-second-task", stems)

    def test_get_backlinks_returns_outbound_links(self) -> None:
        guide = self.root / "projects" / "demo" / "docs" / "guide.md"
        links = self.vault.get_backlinks(guide)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].link_type, "markdown")
        self.assertTrue(links[0].is_resolved)

    def test_get_backlinks_unknown_file_returns_empty(self) -> None:
        links = self.vault.get_backlinks(self.root / "projects" / "demo" / "docs" / "nonexistent.md")
        self.assertEqual(links, [])

    def test_get_backlinks_to_returns_inbound_links(self) -> None:
        issue_001 = (self.root / "projects" / "demo" / "issues" / "ISSUE-001-first-task.md").resolve()
        inbound = self.vault.get_backlinks_to(issue_001)
        self.assertEqual(len(inbound), 1)
        # The link originates from guide.md
        self.assertEqual(inbound[0].source_path.stem, "guide")

    def test_get_backlinks_to_no_inbound_returns_empty(self) -> None:
        guide = (self.root / "projects" / "demo" / "docs" / "guide.md").resolve()
        inbound = self.vault.get_backlinks_to(guide)
        self.assertEqual(inbound, [])

    def test_find_orphaned_docs_excludes_referenced_files(self) -> None:
        orphans = self.vault.find_orphaned_docs()
        # guide.md is not referenced by anyone → orphan
        # issue-001 is referenced by guide.md → not orphan
        # issue-002 is referenced by issue-001 → not orphan
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].path.stem, "guide")

    def test_find_broken_links_detects_missing_targets(self) -> None:
        _write_markdown(
            self.root / "projects" / "demo" / "docs" / "broken.md",
            """
            ---
            created_at: '2026-04-09'
            project: demo
            title: Broken
            ---

            # Broken

            See [Gone](gone.md).
            """,
        )
        vault = ObsidianVault.scan(self.root)
        broken = vault.find_broken_links()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0].raw_target, "gone.md")

    def test_find_cycles_detects_circular_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_demo_project(root)
            # A → B → A (cycle)
            _write_markdown(
                root / "projects" / "demo" / "docs" / "a.md",
                """
                ---
                created_at: '2026-04-09'
                project: demo
                title: A
                ---
                [[b]]
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
                [[a]]
                """,
            )
            vault = ObsidianVault.scan(root)
            cycles = vault.find_cycles()
            self.assertEqual(len(cycles), 1)
            cycle_stems = {p.stem for p in cycles[0]}
            self.assertIn("a", cycle_stems)
            self.assertIn("b", cycle_stems)

    def test_find_cycles_no_cycles_in_dag(self) -> None:
        # Current fixture has A→B→C with no back-edges
        cycles = self.vault.find_cycles()
        self.assertEqual(cycles, [])

    def test_links_are_cached(self) -> None:
        guide = self.root / "projects" / "demo" / "docs" / "guide.md"
        first = self.vault.get_backlinks(guide)
        second = self.vault.get_backlinks(guide)
        # Should be the exact same list object (cache hit)
        self.assertIs(first, second)

    def test_all_links_are_cached(self) -> None:
        first = self.vault.all_links()
        second = self.vault.all_links()
        self.assertIs(first, second)


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
