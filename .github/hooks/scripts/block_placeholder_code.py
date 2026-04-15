#!/usr/bin/env python3
"""Block placeholder-like code insertion in write/edit tool invocations."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\bXXX\b", re.IGNORECASE),
    re.compile(r"\bHACK\b", re.IGNORECASE),
    re.compile(r"\bCHANGEME\b", re.IGNORECASE),
    re.compile(r"\bNotImplementedError\b", re.IGNORECASE),
    re.compile(r"\bpass\s*#\s*TODO\b", re.IGNORECASE),
]

WRITE_TOOL_HINTS = (
    "apply_patch",
    "create_file",
    "edit_notebook_file",
    "create_or_update_file",
    "push_files",
    "write_file",
    "str_replace_editor",
    "edit_file",
)


def _safe_get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_command_text(payload: dict[str, Any]) -> str:
    candidates: list[str] = []

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

    for path in [
        ("toolInput", "input"),
        ("tool_input", "input"),
        ("toolArguments", "input"),
        ("tool_arguments", "input"),
        ("arguments", "input"),
    ]:
        value = _safe_get(payload, *path)
        if isinstance(value, str):
            candidates.append(value)

    if not candidates:
        candidates.append(json.dumps(payload, ensure_ascii=True))

    return "\n".join(candidates)


def _extract_tool_name(payload: dict[str, Any]) -> str:
    for path in [
        ("toolName",),
        ("tool_name",),
        ("tool", "name"),
        ("toolInput", "tool"),
        ("tool_input", "tool"),
    ]:
        value = _safe_get(payload, *path)
        if isinstance(value, str):
            return value.lower()
    return ""


def _is_write_action(tool_name: str, command_text: str) -> bool:
    if any(hint in tool_name for hint in WRITE_TOOL_HINTS):
        return True

    lowered = command_text.lower()
    write_signals = (
        "*** begin patch",
        "*** update file:",
        "*** add file:",
        "*** delete file:",
    )
    return any(signal in lowered for signal in write_signals)


def _has_placeholder(command_text: str) -> bool:
    return any(pattern.search(command_text) for pattern in PLACEHOLDER_PATTERNS)


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Never block if hook input is malformed; fail open.
        return 0

    tool_name = _extract_tool_name(payload)
    command_text = _extract_command_text(payload)

    if _is_write_action(tool_name, command_text) and _has_placeholder(command_text):
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Blocked placeholder/stub-like code markers in write/edit command."
            },
            "stopReason": "Placeholder/stub code marker blocked by workspace policy."
        }
        sys.stdout.write(json.dumps(response))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
