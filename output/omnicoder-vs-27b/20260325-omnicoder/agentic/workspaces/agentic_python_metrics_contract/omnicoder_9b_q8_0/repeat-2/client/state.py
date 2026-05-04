from __future__ import annotations


def reduce_client_state(message: dict, state: dict) -> dict:
    if message["type"] == "session.state":
        payload = message["payload"]
        state["phase"] = payload["phase"]
        state["runtime"] = payload["runtime"]
    if message["type"] == "world.snapshot":
        state["world"] = message["payload"]["world"]
    return state


