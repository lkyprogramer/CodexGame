from dataclasses import dataclass, field


@dataclass
class RuntimeState:
    phase: str = "idle"
    connected: bool = False
    thread_ids: dict[str, str] = field(default_factory=dict)
