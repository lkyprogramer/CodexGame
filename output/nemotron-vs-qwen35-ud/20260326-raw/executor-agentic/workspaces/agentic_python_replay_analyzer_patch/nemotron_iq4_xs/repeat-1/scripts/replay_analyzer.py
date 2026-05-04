import json
from collections import defaultdict

def analyze(path: str) -> dict:
    malformed_lines = 0
    sessions = defaultdict(lambda: {"turns": 0, "invalid_output": 0})
    
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                session_id = record.get("sessionId")
                if session_id is None:
                    raise ValueError("Missing sessionId")
                session_type = record.get("type")
                if session_type == "agent.turn":
                    sessions[session_id]["turns"] += 1
                elif session_type == "error" and record.get("code") == "invalid_output":
                    sessions[session_id]["invalid_output"] += 1
                # Other types are ignored
            except (json.JSONDecodeError, ValueError):
                malformed_lines += 1
    
    # Convert defaultdict to regular dict for JSON serialization compatibility
    return {
        "malformed_lines": malformed_lines,
        "sessions": dict(sessions)
    }
