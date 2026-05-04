from __future__ import annotations

from .models import Discrepancy
from collections import Counter


def render_summary(discrepancies: list[Discrepancy]) -> str:
    if not discrepancies:
        return "no discrepancies"
    counter = Counter(d.kind for d in discrepancies)
    parts = [f"{kind}={count}" for kind, count in sorted(counter.items())]
    return ", ".join(parts)
