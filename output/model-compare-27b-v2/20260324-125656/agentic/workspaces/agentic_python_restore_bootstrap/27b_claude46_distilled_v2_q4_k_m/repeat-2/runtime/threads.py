from __future__ import annotations


class ThreadBootstrapper:
    def __init__(self) -> None:
        self.created: list[str] = []

    def ensure_thread(self, agent_id: str) -> str:
        thread_id = f"thread-{agent_id}"
        self.created.append(thread_id)
        return thread_id
