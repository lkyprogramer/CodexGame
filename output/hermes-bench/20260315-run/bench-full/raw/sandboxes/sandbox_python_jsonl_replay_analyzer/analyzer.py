from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def summarize(path: Path) -> dict[str, int]:
    # TODO: tolerate malformed lines and count events by type.
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    counts = Counter(row["event"] for row in rows)
    return dict(counts)
