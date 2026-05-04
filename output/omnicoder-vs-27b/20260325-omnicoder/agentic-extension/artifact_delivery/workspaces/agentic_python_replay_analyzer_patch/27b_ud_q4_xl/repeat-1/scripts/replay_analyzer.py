import json


def analyze(path: str) -> dict:
    malformed_lines = 0
    sessions = {}
    
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                malformed_lines += 1
                continue
            
            session_id = data.get("sessionId")
            if session_id is None:
                continue
            
            if session_id not in sessions:
                sessions[session_id] = {"turns": 0, "invalid_output": 0}
            
            turn_type = data.get("type")
            if turn_type == "agent.turn":
                sessions[session_id]["turns"] += 1
            elif turn_type == "error" and data.get("code") == "invalid_output":
                sessions[session_id]["invalid_output"] += 1
    
    return {"malformed_lines": malformed_lines, "sessions": sessions}
