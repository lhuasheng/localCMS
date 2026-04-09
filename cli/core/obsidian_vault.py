from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

from cli.core import parser, storage

MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)(?:\[[^\]]*\])\(([^)\n]+)\)")
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
FENCED_CODE_BLOCK_PATTERN = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")
RESERVED_SCHEMES = {"http", "https", "mailto", "obsidian"}


@dataclass(frozen=True)
class VaultLink:
    source_path: Path
    source_project: str
    raw_target: str
    link_type: str
    resolved_path: Path | None
    is_resolved: bool
    reason: str | None = None
    line_number: int | None = None

    @property
    def is_note_link(self) -> bool:
        return self.resolved_path is not None and self.resolved_path.suffix.lower() == ".md"


@dataclass(frozen=True)
class VaultNote:
    path: Path
    relative_path: Path
    project: str
    category: str
    metadata: dict[str, object]
    content: str


class ObsidianVault:
    def __init__(self, root: Path, notes: list[VaultNote]) -> None:
        self.root = root.resolve()
        self.notes = notes
        self._notes_by_path = {note.path.resolve(): note for note in notes}
        self._notes_by_stem: dict[str, list[VaultNote]] = defaultdict(list)
        self._notes_by_relative_key: dict[str, VaultNote] = {}
        for note in notes:
            self._notes_by_stem[note.path.stem].append(note)
            self._notes_by_relative_key[self._relative_key(note.relative_path)] = note

    @classmethod
    def scan(cls, root: Path, project: str | None = None) -> "ObsidianVault":
        resolved_root = root.resolve()
        notes: list[VaultNote] = []
        for project_name in storage.list_projects(resolved_root):
            if project is not None and project_name != project:
                continue
            base_dir = storage.project_dir(resolved_root, project_name)
            for file_path in sorted(base_dir.rglob("*.md")):
                metadata, content = parser.load_markdown(file_path)
                relative_path = file_path.resolve().relative_to(resolved_root)
                notes.append(
                    VaultNote(
                        path=file_path.resolve(),
                        relative_path=relative_path,
                        project=project_name,
                        category=relative_path.parts[2] if len(relative_path.parts) > 2 else "notes",
                        metadata=metadata,
                        content=content,
                    )
                )
        return cls(resolved_root, notes)

    def all_links(self) -> list[VaultLink]:
        links: list[VaultLink] = []
        for note in self.notes:
            links.extend(self.links_for(note))
        return links

    def unresolved_links(self) -> list[VaultLink]:
        return [link for link in self.all_links() if not link.is_resolved]

    def orphan_notes(self) -> list[VaultNote]:
        inbound_counts = self.inbound_link_counts()
        return [note for note in self.notes if inbound_counts.get(note.path.resolve(), 0) == 0]

    def inbound_link_counts(self) -> dict[Path, int]:
        inbound: dict[Path, int] = defaultdict(int)
        for link in self.all_links():
            if link.is_resolved and link.is_note_link and link.resolved_path is not None:
                inbound[link.resolved_path.resolve()] += 1
        return dict(inbound)

    def link_cycles(self) -> list[list[Path]]:
        """Return lists of note paths that form link cycles in the note graph."""
        graph: dict[Path, list[Path]] = defaultdict(list)
        for link in self.all_links():
            if link.is_resolved and link.is_note_link and link.resolved_path is not None:
                src = link.source_path.resolve()
                dst = link.resolved_path.resolve()
                if src != dst:
                    graph[src].append(dst)

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[Path, int] = {note.path.resolve(): WHITE for note in self.notes}
        cycles: list[list[Path]] = []
        found_cycle_starts: set[Path] = set()
        path_stack: list[Path] = []

        def _dfs(node: Path) -> None:
            color[node] = GRAY
            path_stack.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    if neighbor not in found_cycle_starts:
                        found_cycle_starts.add(neighbor)
                        idx = path_stack.index(neighbor)
                        cycles.append(list(path_stack[idx:]))
                elif color[neighbor] == WHITE:
                    _dfs(neighbor)
            path_stack.pop()
            color[node] = BLACK

        for note in self.notes:
            node = note.path.resolve()
            if color.get(node) == WHITE:
                _dfs(node)

        return cycles

    def summary_by_project(self) -> list[dict[str, object]]:
        inbound_counts = self.inbound_link_counts()
        unresolved = self.unresolved_links()
        unresolved_by_project: dict[str, int] = defaultdict(int)
        for link in unresolved:
            unresolved_by_project[link.source_project] += 1

        links_by_project: dict[str, int] = defaultdict(int)
        note_links_by_project: dict[str, int] = defaultdict(int)
        for link in self.all_links():
            links_by_project[link.source_project] += 1
            if link.is_note_link:
                note_links_by_project[link.source_project] += 1

        notes_by_project: dict[str, list[VaultNote]] = defaultdict(list)
        for note in self.notes:
            notes_by_project[note.project].append(note)

        summary: list[dict[str, object]] = []
        for project_name in sorted(notes_by_project):
            project_notes = notes_by_project[project_name]
            summary.append(
                {
                    "project": project_name,
                    "notes": len(project_notes),
                    "docs": sum(1 for note in project_notes if note.category == "docs"),
                    "issues": sum(1 for note in project_notes if note.category == "issues"),
                    "outbound_links": links_by_project.get(project_name, 0),
                    "note_links": note_links_by_project.get(project_name, 0),
                    "orphans": sum(1 for note in project_notes if inbound_counts.get(note.path.resolve(), 0) == 0),
                    "unresolved_links": unresolved_by_project.get(project_name, 0),
                }
            )
        return summary

    def circular_dependencies(self) -> list[list[Path]]:
        """Return all simple cycles in the note-to-note link graph (each as an ordered list of Paths)."""
        graph: dict[Path, list[Path]] = defaultdict(list)
        for link in self.all_links():
            if link.is_resolved and link.is_note_link and link.resolved_path is not None:
                src = link.source_path.resolve()
                dst = link.resolved_path.resolve()
                if src != dst:
                    graph[src].append(dst)

        cycles: list[list[Path]] = []
        visited: set[Path] = set()
        rec_stack: list[Path] = []
        in_stack: set[Path] = set()

        def _dfs(node: Path) -> None:
            visited.add(node)
            rec_stack.append(node)
            in_stack.add(node)
            for neighbour in graph.get(node, []):
                if neighbour not in visited:
                    _dfs(neighbour)
                elif neighbour in in_stack:
                    cycle_start = rec_stack.index(neighbour)
                    cycle = list(rec_stack[cycle_start:])
                    normalized = _normalize_cycle(cycle)
                    if normalized not in [_normalize_cycle(c) for c in cycles]:
                        cycles.append(cycle)
            rec_stack.pop()
            in_stack.discard(node)

        for note in self.notes:
            node = note.path.resolve()
            if node not in visited:
                _dfs(node)

        return cycles

    def links_for(self, note: VaultNote) -> list[VaultLink]:
        sanitized_content = _strip_code_spans_preserve_lines(note.content)
        links: list[VaultLink] = []

        for match in MARKDOWN_LINK_PATTERN.finditer(sanitized_content):
            raw_target = match.group(1).strip()
            resolved_path, reason = self._resolve_markdown_target(note.path, raw_target)
            line_number = sanitized_content[: match.start()].count("\n") + 1
            links.append(
                VaultLink(
                    source_path=note.path,
                    source_project=note.project,
                    raw_target=raw_target,
                    link_type="markdown",
                    resolved_path=resolved_path,
                    is_resolved=resolved_path is not None,
                    reason=reason,
                    line_number=line_number,
                )
            )

        for match in WIKI_LINK_PATTERN.finditer(sanitized_content):
            raw_target = match.group(1).strip()
            resolved_path, reason = self._resolve_wiki_target(note.path, raw_target)
            line_number = sanitized_content[: match.start()].count("\n") + 1
            links.append(
                VaultLink(
                    source_path=note.path,
                    source_project=note.project,
                    raw_target=raw_target,
                    link_type="wiki",
                    resolved_path=resolved_path,
                    is_resolved=resolved_path is not None,
                    reason=reason,
                    line_number=line_number,
                )
            )

        return links

    def _resolve_markdown_target(self, source_path: Path, raw_target: str) -> tuple[Path | None, str | None]:
        candidate = _clean_link_target(raw_target)
        if not candidate:
            return source_path.resolve(), None

        if candidate.startswith("#"):
            return source_path.resolve(), None

        parsed = urlparse(candidate)
        if parsed.scheme.lower() in RESERVED_SCHEMES:
            return source_path.resolve(), None

        path_text = unquote(parsed.path)
        if not path_text:
            return source_path.resolve(), None

        resolved_path = self._resolve_path_candidate(source_path, path_text)
        if resolved_path is None:
            return None, "target not found"
        return resolved_path, None

    def _resolve_wiki_target(self, source_path: Path, raw_target: str) -> tuple[Path | None, str | None]:
        target_text = raw_target.split("|", maxsplit=1)[0].strip()
        target_text = target_text.split("#", maxsplit=1)[0].strip()
        if not target_text:
            return None, "empty wiki target"

        normalized = target_text.replace("\\", "/")
        if "/" in normalized or normalized.startswith("."):
            resolved_path = self._resolve_path_candidate(source_path, normalized)
            if resolved_path is None:
                return None, "target not found"
            if resolved_path.suffix.lower() != ".md":
                return None, "wiki links must resolve to markdown notes"
            return resolved_path, None

        matches = self._notes_by_stem.get(Path(normalized).stem, [])
        if not matches:
            return None, "target not found"
        if len(matches) > 1:
            return None, "ambiguous wiki target"
        return matches[0].path.resolve(), None

    def _resolve_path_candidate(self, source_path: Path, path_text: str) -> Path | None:
        candidate_path = Path(path_text)
        raw_candidates: list[Path] = []
        if path_text.startswith("/"):
            raw_candidates.append((self.root / path_text.lstrip("/")))
        else:
            raw_candidates.append((source_path.parent / candidate_path))
            raw_candidates.append((self.root / candidate_path))

        checked: set[Path] = set()
        for raw_candidate in raw_candidates:
            for candidate in _candidate_variants(raw_candidate):
                resolved_candidate = candidate.resolve()
                if resolved_candidate in checked:
                    continue
                checked.add(resolved_candidate)
                if not resolved_candidate.exists():
                    continue
                try:
                    resolved_candidate.relative_to(self.root)
                except ValueError:
                    continue
                return resolved_candidate
        return None

    @staticmethod
    def _relative_key(relative_path: Path) -> str:
        return relative_path.as_posix().removesuffix(".md")


def _normalize_cycle(cycle: list[Path]) -> frozenset[tuple[Path, Path]]:
    """Represent a cycle as a canonical frozenset of edges for deduplication."""
    edges: list[tuple[Path, Path]] = []
    for i in range(len(cycle)):
        edges.append((cycle[i], cycle[(i + 1) % len(cycle)]))
    return frozenset(edges)


def _strip_code_spans(content: str) -> str:
    without_fences = FENCED_CODE_BLOCK_PATTERN.sub("", content)
    without_indented_blocks = _strip_indented_code_blocks(without_fences)
    return INLINE_CODE_PATTERN.sub("", without_indented_blocks)


def _strip_code_spans_preserve_lines(content: str) -> str:
    """Strip code blocks while preserving newline positions so line numbers remain accurate."""
    without_fences = FENCED_CODE_BLOCK_PATTERN.sub(
        lambda m: "\n" * m.group(0).count("\n"), content
    )
    without_indented_blocks = _strip_indented_code_blocks(without_fences)
    return INLINE_CODE_PATTERN.sub("", without_indented_blocks)


def _strip_indented_code_blocks(content: str) -> str:
    stripped_lines: list[str] = []
    in_code_block = False

    for line in content.splitlines():
        is_indented = line.startswith("    ") or line.startswith("\t")

        if in_code_block:
            if is_indented or not line.strip():
                stripped_lines.append("")
                continue
            in_code_block = False

        if is_indented and (not stripped_lines or not stripped_lines[-1].strip()):
            in_code_block = True
            stripped_lines.append("")
            continue

        stripped_lines.append(line)

    return "\n".join(stripped_lines)


def _clean_link_target(raw_target: str) -> str:
    candidate = raw_target.strip()
    if candidate.startswith("<") and candidate.endswith(">"):
        candidate = candidate[1:-1].strip()
    title_match = re.match(r'^(\S+)(?:\s+["\'][^"\']*["\'])?$', candidate)
    if title_match:
        return title_match.group(1)
    return candidate


def _candidate_variants(candidate: Path) -> list[Path]:
    variants = [candidate]
    if candidate.suffix:
        return variants
    variants.append(candidate.with_suffix(".md"))
    return variants