import json


def analyze(path: str) -> dict:
    malformed_lines = 0
    sessions: dict = {}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                malformed_lines += 1
                continue

            session_id = record.get("sessionId")
            if session_id is None:
                malformed_lines += 1
                continue

            if session_id not in sessions:
                sessions[session_id] = {"turns": 0, "invalid_output": 0}

            record_type = record.get("type")
            if record_type == "agent.turn":
                sessions[session_id]["turns"] += 1
            elif record_type == "error" and record.get("code") == "invalid_output":
                sessions[session_id]["invalid_output"] += 1

    return {"malformed_lines": malformed_lines, "sessions": sessions}
