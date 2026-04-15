#!/usr/bin/env python3
"""Require test evidence before PR create/edit or git push in PreToolUse hooks."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

# These command substrings trigger scrutiny.
_SUBMIT_SIGNALS = (
    "gh pr create",
    "gh pr edit",
    "git push",
)

# Evidence patterns: at least one must appear in the command text.
_EVIDENCE_PATTERNS = [
    re.compile(r"\b(pytest|jest|cargo\s+test|go\s+test|npm\s+test|make\s+test)\b", re.IGNORECASE),
    re.compile(r"\b(lint|mypy|tsc|eslint|clippy|ruff|flake8)\b", re.IGNORECASE),
    re.compile(r"\b(check[s]?|verify|validated|passed|assert|ci)\b", re.IGNORECASE),
    re.compile(r"(✓|✅|PASS\b|OK\b)"),
]

_DENY_REASON = (
    "Blocked: submitting code (push/PR) with no test or check evidence in the command context. "
    "Run tests before pushing or include validation evidence in the PR body."
)


def _safe_get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_command(payload: dict[str, Any]) -> str:
    for path in [
        ("toolInput", "command"),
        ("tool_input", "command"),
        ("toolArguments", "command"),
        ("arguments", "command"),
    ]:
        value = _safe_get(payload, *path)
        if isinstance(value, str):
            return value
    return json.dumps(payload, ensure_ascii=True)


def _is_submit_action(command: str) -> bool:
    lowered = command.lower()
    return any(signal in lowered for signal in _SUBMIT_SIGNALS)


def _has_evidence(command: str) -> bool:
    return any(pat.search(command) for pat in _EVIDENCE_PATTERNS)


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    try:
        command = _extract_command(payload)

        if not _is_submit_action(command):
            return 0

        if _has_evidence(command):
            return 0

        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": _DENY_REASON,
            },
            "stopReason": _DENY_REASON,
        }
        sys.stdout.write(json.dumps(response))
        return 2

    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
