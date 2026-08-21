import re

_TOKEN = re.compile(r"(\d+)(ms|d|h|m|s)")
_ORDER = {"d": 0, "h": 1, "m": 2, "s": 3, "ms": 4}
_FACTOR = {"d": 86_400_000, "h": 3_600_000, "m": 60_000, "s": 1_000, "ms": 1}

def parse_duration(text: str) -> int:
    if not isinstance(text, str) or not text:
        raise ValueError("duration must be a non-empty string")
    position = 0
    previous_order = -1
    seen = set()
    total = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            raise ValueError("invalid duration syntax")
        number = int(match.group(1))
        unit = match.group(2)
        order = _ORDER[unit]
        if unit in seen or order <= previous_order:
            raise ValueError("units must be unique and descending")
        seen.add(unit)
        previous_order = order
        total += number * _FACTOR[unit]
        position = match.end()
    if total <= 0:
        raise ValueError("duration must be positive")
    return total
