from __future__ import annotations

import os
import re
from pathlib import Path

from cli.core import parser
from cli.core.models import ProjectConfig

ENV_ROOT = "CLI_CMS_ROOT"
ID_PATTERN = re.compile(r"ISSUE-(\d+)")


def slugify(text: str) -> str:
    lowered = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return cleaned or "item"


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_root(explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        return explicit_root.resolve()
    env_root = os.getenv(ENV_ROOT)
    if env_root:
        return Path(env_root).resolve()
    return default_repo_root()


def projects_dir(root: Path) -> Path:
    return root / "projects"


def global_dir(root: Path) -> Path:
    return root / "global"


def project_dir(root: Path, project: str) -> Path:
    return projects_dir(root) / project


def project_config_path(root: Path, project: str) -> Path:
    return project_dir(root, project) / "project.yaml"


def issues_dir(root: Path, project: str) -> Path:
    return project_dir(root, project) / "issues"


def docs_dir(root: Path, project: str) -> Path:
    return project_dir(root, project) / "docs"


def audit_reports_dir(root: Path, project: str) -> Path:
    return project_dir(root, project) / "audit-reports"


def ensure_base_dirs(root: Path) -> None:
    projects_dir(root).mkdir(parents=True, exist_ok=True)
    global_dir(root).mkdir(parents=True, exist_ok=True)


def ensure_project_dirs(root: Path, project: str) -> None:
    project_dir(root, project).mkdir(parents=True, exist_ok=True)
    issues_dir(root, project).mkdir(parents=True, exist_ok=True)
    docs_dir(root, project).mkdir(parents=True, exist_ok=True)


def list_projects(root: Path) -> list[str]:
    base = projects_dir(root)
    if not base.exists():
        return []
    return sorted([item.name for item in base.iterdir() if item.is_dir() and (item / "project.yaml").exists()])


def load_project_config(root: Path, project: str) -> ProjectConfig:
    path = project_config_path(root, project)
    payload = parser.read_yaml(path)
    if not payload:
        raise FileNotFoundError(f"Project config not found: {path}")
    return ProjectConfig(
        name=str(payload.get("name", project)),
        default_status=str(payload.get("default_status", "todo")),
        statuses=list(payload.get("statuses", ["todo", "in-progress", "done"])),
        issue_counter=int(payload.get("issue_counter", 0)),
    )


def save_project_config(root: Path, project: str, config: ProjectConfig) -> None:
    payload = {
        "name": config.name,
        "default_status": config.default_status,
        "statuses": config.statuses,
        "issue_counter": config.issue_counter,
    }
    parser.write_yaml(project_config_path(root, project), payload)


def next_issue_id(root: Path, project: str) -> str:
    config = load_project_config(root, project)
    config.issue_counter += 1
    save_project_config(root, project, config)
    return f"ISSUE-{config.issue_counter:03d}"


def issue_file_path(root: Path, project: str, issue_id: str, title: str) -> Path:
    return issues_dir(root, project) / f"{issue_id}-{slugify(title)}.md"


def doc_file_path(root: Path, project: str, name: str) -> Path:
    return docs_dir(root, project) / f"{slugify(name)}.md"


def issue_id_from_text(text: str) -> str | None:
    match = ID_PATTERN.search(text)
    if not match:
        return None
    return f"ISSUE-{int(match.group(1)):03d}"
