"""Redact common credential forms; not a general-purpose secret detector."""
import re
from pathlib import Path

def redact(text: str) -> str:
    text = re.sub(r'(?im)^.*\[sudo\]\s*password[^\n]*$', '[REDACTED sudo credential line]', text)
    text = re.sub(r'(?i)(Bearer\s+)[^\s"\',}]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:api[_-]?key|password|passwd|access[_-]?token|secret)\s*[=:]\s*["\']?)[^\s"\',}]+', r'\1[REDACTED]', text)
    text = re.sub(r'\bsk-[A-Za-z0-9_-]{12,}\b', '[REDACTED key]', text)
    return text

def safe_child(root: Path, rel: str) -> Path:
    root = root.resolve()
    p = (root / rel).resolve()
    if p == root or root not in p.parents:
        raise ValueError('path escapes or aliases root')
    return p
