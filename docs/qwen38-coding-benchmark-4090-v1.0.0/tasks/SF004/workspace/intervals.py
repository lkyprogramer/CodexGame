def merge_intervals(intervals, *, merge_touching=False):
    items = sorted(intervals)
    if not items:
        return []
    result = [list(items[0])]
    for start, end in items[1:]:
        if start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return [tuple(x) for x in result]
