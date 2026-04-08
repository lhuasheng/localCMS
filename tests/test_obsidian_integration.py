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