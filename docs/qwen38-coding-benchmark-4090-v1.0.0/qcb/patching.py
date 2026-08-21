from __future__ import annotations

import re
from pathlib import Path

from .util import run_process


_DIFF_FENCE = re.compile(r"```(?:diff|patch)?\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)


def extract_unified_diff(text: str) -> str | None:
    candidates = _DIFF_FENCE.findall(text)
    for candidate in candidates:
        if "--- " in candidate and "+++ " in candidate:
            return candidate.strip() + "\n"
    marker = text.find("--- ")
    if marker >= 0 and "+++ " in text[marker:]:
        return text[marker:].strip() + "\n"
    return None


def initialize_git(workspace: str | Path) -> None:
    workspace = Path(workspace)
    run_process(["git", "init", "-q"], cwd=workspace)
    run_process(["git", "config", "user.email", "qcb@example.invalid"], cwd=workspace)
    run_process(["git", "config", "user.name", "QCB Runner"], cwd=workspace)
    run_process(["git", "add", "-A"], cwd=workspace)
    run_process(["git", "commit", "-q", "-m", "baseline"], cwd=workspace)


def apply_unified_diff(workspace: str | Path, patch: str) -> tuple[bool, str]:
    result = run_process(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=workspace,
        stdin=patch,
        timeout=30,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output


def git_diff(workspace: str | Path) -> str:
    result = run_process(["git", "diff", "--no-ext-diff"], cwd=workspace, timeout=30)
    return result.stdout
