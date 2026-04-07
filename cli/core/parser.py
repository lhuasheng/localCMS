from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter
import yaml


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Expected YAML object in {path}")
    return raw


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    path.write_text(text, encoding="utf-8")


def load_markdown(path: Path) -> tuple[dict[str, Any], str]:
    post = frontmatter.load(path)
    metadata = dict(post.metadata)
    content = post.content or ""
    return metadata, content


def save_markdown(path: Path, metadata: dict[str, Any], content: str) -> None:
    yaml_text = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False).strip()
    body = content.rstrip()
    text = f"---\n{yaml_text}\n---\n\n{body}\n"
    path.write_text(text, encoding="utf-8")
