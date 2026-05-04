from __future__ import annotations

from collections import Counter
from .models import Discrepancy


def render_summary(discrepancies: list[Discrepancy]) -> str:
    counts = Counter(d.kind for d in discrepancies)
    parts = [f"{kind}={count}" for kind, count in sorted(counts.items())]
    return ", ".join(parts) if parts else "no discrepancies"
