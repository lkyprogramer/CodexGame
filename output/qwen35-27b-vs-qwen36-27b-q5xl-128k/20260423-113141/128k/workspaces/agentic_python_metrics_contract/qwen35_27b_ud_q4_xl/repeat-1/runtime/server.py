from __future__ import annotations

from protocol.messages import make_session_state, make_world_snapshot


def emit_state(phase: str, metrics_snapshot: dict) -> tuple[dict, dict]:
    session_state = make_session_state(
        phase,
        {
            "model": "local-qwen",
            "tick_ms": 200,
            "metrics": metrics_snapshot,
        },
    )
    world_snapshot = make_world_snapshot(10, {"tiles": []})
    return session_state, world_snapshot
