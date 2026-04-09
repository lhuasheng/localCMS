from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class ProjectConfig:
    name: str
    default_status: str = "todo"
    statuses: list[str] = field(default_factory=lambda: ["todo", "in-progress", "done"])
    issue_counter: int = 0


@dataclass
class IssueRecord:
    path: Path
    project: str
    issue_id: str
    title: str
    status: str
    priority: str
    created_at: str
    tags: list[str]
    content: str

    @classmethod
    def from_payload(cls, path: Path, project: str, payload: dict[str, Any], content: str) -> "IssueRecord":
        return cls(
            path=path,
            project=project,
            issue_id=str(payload.get("id", "")),
            title=str(payload.get("title", "")),
            status=str(payload.get("status", "todo")),
            priority=str(payload.get("priority", "medium")),
            created_at=str(payload.get("created_at", date.today().isoformat())),
            tags=list(payload.get("tags", [])),
            content=content,
        )
