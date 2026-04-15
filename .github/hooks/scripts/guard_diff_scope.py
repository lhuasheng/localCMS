#!/usr/bin/env python3
"""Block write/edit tool invocations that exceed safe diff scope thresholds."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

# Maximum allowed counts before suggesting a split.
MAX_CHANGED_FILES = 5
MAX_LINE_DELTA = 500

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


def _count_changed_files(text: str) -> int:
    """Count distinct file paths referenced in unified-diff or patch-style headers."""
    patterns = [
        re.compile(r"^\+\+\+\s+\S+", re.MULTILINE),
        re.compile(r"^\*\*\*\s+(?:update|add|delete)\s+file:", re.MULTILINE | re.IGNORECASE),
    ]
    seen: set[str] = set()
    for pat in patterns:
        for match in pat.finditer(text):
            seen.add(match.group(0).strip())
    return len(seen)


def _count_line_delta(text: str) -> int:
    """Count added and removed lines in unified-diff format."""
    added = sum(
        1 for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in text.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )
    return added + removed


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Never block if hook input is malformed; fail open.
        return 0

    tool_name = _extract_tool_name(payload)
    command_text = _extract_command_text(payload)

    if not _is_write_action(tool_name, command_text):
        return 0

    changed_files = _count_changed_files(command_text)
    line_delta = _count_line_delta(command_text)

    if changed_files > MAX_CHANGED_FILES or line_delta > MAX_LINE_DELTA:
        parts: list[str] = []
        if changed_files > MAX_CHANGED_FILES:
            parts.append("{} files changed (limit {})".format(changed_files, MAX_CHANGED_FILES))
        if line_delta > MAX_LINE_DELTA:
            parts.append("{} lines added/removed (limit {})".format(line_delta, MAX_LINE_DELTA))
        reason = (
            "Diff scope too large: {}. "
            "Split the change into smaller independent slices."
        ).format(", ".join(parts))

        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
            "stopReason": reason,
        }
        sys.stdout.write(json.dumps(response))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
