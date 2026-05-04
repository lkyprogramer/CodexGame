from __future__ import annotations

def make_session_state(phase: str, runtime: dict) -> dict:
    return {
        "type": "session.state",
        "payload": {
            "phase": phase,
            "runtime": runtime,
        },
    }


def make_world_snapshot(tick: int, world: dict) -> dict:
    return {
        "type": "world.snapshot",
        "payload": {
            "tick": tick,
            "world": world,
        },
    }
