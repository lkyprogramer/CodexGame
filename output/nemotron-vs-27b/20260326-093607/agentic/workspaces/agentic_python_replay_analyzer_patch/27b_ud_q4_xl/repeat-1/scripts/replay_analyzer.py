import json
from collections import defaultdict


def analyze(path: str) -> dict:
    sessions: dict = defaultdict(lambda: {"turns": 0, "invalid_output": 0})
    malformed_lines = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed_lines += 1
                continue

            session_id = record.get("sessionId")
            if session_id is None:
                malformed_lines += 1
                continue

            record_type = record.get("type")
            if record_type == "agent.turn":
                sessions[session_id]["turns"] += 1
            elif record_type == "error" and record.get("code") == "invalid_output":
                sessions[session_id]["invalid_output"] += 1

    return {
        "malformed_lines": malformed_lines,
        "sessions": dict(sessions),
    }
