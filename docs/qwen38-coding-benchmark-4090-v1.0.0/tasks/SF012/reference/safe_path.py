import os
import re
from pathlib import Path, PureWindowsPath

def safe_join(root, user_path):
    try:
        base = Path(root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("invalid root") from exc
    if not base.is_dir(): raise ValueError("root is not a directory")
    if not isinstance(user_path, str) or not user_path or "\x00" in user_path:
        raise ValueError("invalid user path")
    win = PureWindowsPath(user_path)
    if Path(user_path).is_absolute() or win.is_absolute() or win.drive:
        raise ValueError("absolute paths are forbidden")
    normalized = user_path.replace('\\','/')
    if any(part == '..' for part in normalized.split('/')):
        raise ValueError("parent traversal is forbidden")
    try:
        candidate = (base / Path(normalized)).resolve(strict=False)
        if os.path.commonpath([str(base), str(candidate)]) != str(base):
            raise ValueError("path escapes root")
    except (OSError, RuntimeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc) == "path escapes root": raise
        raise ValueError("invalid path") from exc
    return candidate
