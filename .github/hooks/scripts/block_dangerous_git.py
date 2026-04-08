#!/usr/bin/env python3
"""Block dangerous git reset invocations in PreToolUse hooks."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

DANGEROUS_PATTERNS = [
    re.compile(r"(^|\s)git\s+reset\s+--hard(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)git\s+reset\s+--keep(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)git\s+reset\s+--merge(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)git\s+reset\s+HEAD~\d*(\s|$)", re.IGNORECASE),
    re.compile(r"(^|\s)git\s+reset\s+HEAD\^(\s|$)", re.IGNORECASE),
]


def _safe_get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_command_text(payload: dict[str, Any]) -> str:
    candidates: list[str] = []

    # Known likely locations for tool args in hook payloads.
    for path in [
        ("toolInput", "command"),
        ("tool_input", "command"),
        ("toolArguments", "command"),
        ("tool_arguments", "command"),
        ("arguments", "command"),
    ]:
        value = _safe_get(payload, *path)
        if isinstance(value, str):
            candidates.append(value)

    # Fall back to scanning serialized payload if shape differs.
    if not candidates:
        candidates.append(json.dumps(payload, ensure_ascii=True))

    return "\n".join(candidates)


def _is_dangerous(command_text: str) -> bool:
    return any(pattern.search(command_text) for pattern in DANGEROUS_PATTERNS)


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Never block if hook input is malformed; fail open.
        return 0

    command_text = _extract_command_text(payload)

    if _is_dangerous(command_text):
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Blocked dangerous git reset command. Use non-destructive git workflow instead."
            },
            "stopReason": "Dangerous git reset command blocked by workspace policy."
        }
        sys.stdout.write(json.dumps(response))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
