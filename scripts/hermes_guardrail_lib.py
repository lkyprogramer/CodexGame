#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOOL_TRACE_PREFIXES = (
    "┊ 🔎",
    "┊ 💻",
    "┊ 📖",
    "┊ 🔧",
    "🔎",
    "💻",
    "📖",
    "🔧",
)

SPINNER_PREFIXES = tuple("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")


@dataclass(frozen=True)
class RecoveredOutput:
    final_output: str
    output_source: str
    json_parse_success: bool
    had_fenced_json: bool
    tool_used: bool


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def strip_ansi(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    return text.replace("\r", "\n")


def extract_session_id(*texts: str) -> str:
    pattern = re.compile(r"session_id:\s*([0-9_]+[a-z0-9]*)", re.IGNORECASE)
    for text in texts:
        match = pattern.search(text or "")
        if match:
            return match.group(1)
    return ""


def load_session_final_content(session_path: Path | None) -> str:
    if not session_path or not session_path.exists():
        return ""
    try:
        data = load_json(session_path)
    except Exception:
        return ""
    messages = data.get("messages")
    if not isinstance(messages, list):
        return ""
    for item in reversed(messages):
        if not isinstance(item, dict):
            continue
        if item.get("role") != "assistant":
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def session_used_tool(session_path: Path | None) -> bool:
    if not session_path or not session_path.exists():
        return False
    try:
        data = load_json(session_path)
    except Exception:
        return False
    messages = data.get("messages")
    if not isinstance(messages, list):
        return False
    return any(isinstance(item, dict) and item.get("role") == "tool" for item in messages)


def extract_fenced_json(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    candidate = match.group(1).strip()
    try:
        json.loads(candidate)
    except Exception:
        return ""
    return candidate


def extract_json_tail(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        json.loads(stripped)
        return stripped
    except Exception:
        pass

    for open_char, close_char in (("{", "}"), ("[", "]")):
        end = stripped.rfind(close_char)
        if end == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for idx in range(end, -1, -1):
            ch = stripped[idx]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == close_char:
                depth += 1
            elif ch == open_char:
                depth -= 1
                if depth == 0:
                    candidate = stripped[idx : end + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        break
    return ""


def extract_json_payload(text: str) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if not stripped:
        return ""
    for extractor in (lambda value: value, extract_fenced_json, extract_json_tail):
        candidate = extractor(stripped)
        if not candidate:
            continue
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            continue
    return ""


def normalize_cli_output(text: str) -> str:
    cleaned = strip_ansi(text)
    lines = [line.rstrip() for line in cleaned.splitlines()]
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("session_id:"):
            continue
        if stripped.startswith("WARNING:"):
            continue
        if stripped.startswith("To increase the performance of the tunnel"):
            continue
        if stripped[:1] in SPINNER_PREFIXES:
            continue
        if stripped.startswith(TOOL_TRACE_PREFIXES):
            continue
        kept.append(stripped)
    return "\n".join(kept).strip()


def is_retryable_cli_error(stderr_text: str) -> bool:
    lowered = stderr_text.lower()
    patterns = (
        "importerror: cannot import name 'main' from 'cli'",
        "syntaxerror:",
        "unterminated string literal",
        "unterminated triple-quoted string literal",
        "traceback (most recent call last)",
        "connection reset",
        "broken pipe",
        "timed out",
    )
    return any(pattern in lowered for pattern in patterns)


def recover_final_output(
    mode: str,
    stdout_text: str,
    stderr_text: str,
    session_path: Path | None,
    fallback_text: str = "",
) -> RecoveredOutput:
    session_content = load_session_final_content(session_path)
    tool_used = session_used_tool(session_path) or ("💻" in stdout_text) or ("┊ 💻" in stdout_text)
    prefer_json = mode == "json"

    candidates = [
        ("session", session_content),
        ("stdout", normalize_cli_output(stdout_text)),
        ("stderr", normalize_cli_output(stderr_text)),
        ("fallback", str(fallback_text or "").strip()),
    ]

    first_text = ""
    first_source = ""
    had_fenced_json = False

    for source, raw_text in candidates:
        text = str(raw_text or "").strip()
        if not text:
            continue
        had_fenced_json = had_fenced_json or bool(extract_fenced_json(text))
        if prefer_json:
            payload = extract_json_payload(text)
            if payload:
                return RecoveredOutput(
                    final_output=payload,
                    output_source=source,
                    json_parse_success=True,
                    had_fenced_json=had_fenced_json,
                    tool_used=tool_used,
                )
            if not first_text:
                first_text = text
                first_source = source
        else:
            return RecoveredOutput(
                final_output=text,
                output_source=source,
                json_parse_success=False,
                had_fenced_json=had_fenced_json,
                tool_used=tool_used,
            )

    return RecoveredOutput(
        final_output=first_text,
        output_source=first_source,
        json_parse_success=bool(extract_json_payload(first_text)) if prefer_json else False,
        had_fenced_json=had_fenced_json,
        tool_used=tool_used,
    )
