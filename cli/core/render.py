from __future__ import annotations

import json
from typing import Any

import typer


def emit_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=False))


def emit_kv(title: str, value: Any) -> None:
    typer.echo(f"{title}: {value}")
