import math
from numbers import Real

def _valid(value):
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)

def merge_intervals(intervals, *, merge_touching=False):
    try:
        raw = list(intervals)
    except TypeError as exc:
        raise ValueError("intervals must be iterable") from exc
    items = []
    for item in raw:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("each interval must contain two values")
        start, end = item
        if not _valid(start) or not _valid(end) or start > end:
            raise ValueError("invalid interval")
        items.append((start, end))
    items.sort(key=lambda x: (x[0], x[1]))
    result = []
    for start, end in items:
        if not result:
            result.append([start, end])
            continue
        overlap = start < result[-1][1] or (merge_touching and start == result[-1][1])
        if overlap:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return [tuple(item) for item in result]
