from __future__ import annotations

from .session import Snapshot
from .threads import ThreadBootstrapper
from .types import RuntimeState


def restore(snapshot: Snapshot, state: RuntimeState, bootstrapper: ThreadBootstrapper) -> RuntimeState:
    state.phase = "running"
    state.thread_ids = {}
    for agent_id in snapshot.agent_ids:
        if agent_id not in state.thread_ids:
            state.thread_ids[agent_id] = bootstrapper.ensure_thread(agent_id)
    state.connected = True
    return state
