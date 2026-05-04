from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    agent_ids: list[str]
