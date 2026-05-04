from __future__ import annotations

from .models import Discrepancy


def render_summary(discrepancies: list[Discrepancy]) -> str:
    from collections import Counter
    counts = Counter(d.kind for d in discrepancies)
    parts = [f"{kind}={count}" for kind, count in sorted(counts.items())]
    return ", ".join(parts) if parts else "no discrepancies"
