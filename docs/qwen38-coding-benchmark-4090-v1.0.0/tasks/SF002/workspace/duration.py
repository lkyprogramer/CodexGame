import re

def parse_duration(text: str) -> int:
    total = 0
    for number, unit in re.findall(r"(\d+)([a-z]+)", text):
        total += int(number) * {"d": 86400000, "h": 3600000, "m": 60000, "s": 1000, "ms": 1}[unit]
    return total
