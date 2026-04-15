#!/usr/bin/env python3
"""Enforce commit-message quality standards in PreToolUse hooks."""

from __future__ import annotations

import json
import sys
import re
from typing import Any

GENERIC_BAD_MESSAGES = frozenset(
    {"fix", "update", "changes", "wip", "temp", "misc", "test", "asdf", "asd"}
)
MIN_LENGTH = 10


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
    ]:
        value = _safe_get(payload, *path)
        if isinstance(value, str):
            return value.lower()
    return ""


def _extract_message(payload: dict[str, Any]) -> str | None:
    # 1. Structured message fields.
    for key in ("message", "commit_message"):
        for path in [
            ("toolInput", key),
            ("tool_input", key),
            ("toolArguments", key),
            ("arguments", key),
        ]:
            value = _safe_get(payload, *path)
            if isinstance(value, str):
                return value

    # 2. Shell-embedded: git commit -m "..." or git commit -m '...'
    for path in [
        ("toolInput", "command"),
        ("tool_input", "command"),
        ("toolArguments", "command"),
        ("arguments", "command"),
    ]:
        value = _safe_get(payload, *path)
        if isinstance(value, str):
            match = re.search(r'git\s+commit\b.*?-m\s+["\']([^"\']+)["\']', value, re.IGNORECASE)
            if match:
                return match.group(1)

    return None


def _applies_to_commit(tool_name: str, serialised: str) -> bool:
    if "commit" in tool_name:
        return True
    if "git commit" in serialised:
        return True
    return False


def _check_message(message: str) -> str | None:
    """Return a denial reason string, or None if the message is acceptable."""
    if not message.strip():
        return "Rule 1: commit message is empty or only whitespace."
    if message.strip().lower() in GENERIC_BAD_MESSAGES:
        return f"Rule 2: commit message '{message.strip()}' matches a generic bad-message pattern."
    if len(message.strip()) < MIN_LENGTH:
        return (
            f"Rule 3: commit message is too short "
            f"({len(message.strip())} chars; minimum {MIN_LENGTH})."
        )
    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Fail open on parse error.
        return 0

    try:
        tool_name = _extract_tool_name(payload)
        serialised = json.dumps(payload, ensure_ascii=True)

        if not _applies_to_commit(tool_name, serialised):
            return 0

        message = _extract_message(payload)
        if message is None:
            # No recognisable message field; fail open.
            message = serialised

        reason = _check_message(message)
        if reason is None:
            return 0

        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Commit message rejected: {reason}",
            },
            "stopReason": f"Commit message rejected by workspace policy: {reason}",
        }
        sys.stdout.write(json.dumps(response))
        return 2

    except Exception:
        # Fail open on any unexpected error.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
