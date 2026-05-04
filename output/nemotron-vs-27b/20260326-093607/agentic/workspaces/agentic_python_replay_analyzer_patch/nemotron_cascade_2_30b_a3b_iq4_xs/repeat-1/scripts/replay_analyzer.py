import json

def analyze(path: str) -> dict:
    result = {"malformed_lines": 0, "sessions": {}}
    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                session_id = record.get("sessionId")
                if session_id is None:
                    raise ValueError("Missing sessionId")
                turn = record.get("type") == "agent.turn"
                invalid_output = record.get("type") == "error" and record.get("code") == "invalid_output"
                if session_id not in result["sessions"]:
                    result["sessions"][session_id] = {"turns": 0, "invalid_output": 0}
                if turn:
                    result["sessions"][session_id]["turns"] += 1
                if invalid_output:
                    result["sessions"][session_id]["invalid_output"] += 1
            except (json.JSONDecodeError, ValueError):
                result["malformed_lines"] += 1
    return result
