#!/usr/bin/env python3
"""Generate deterministic synthetic result files for report-pipeline tests.

These rows are not model benchmark results and must never be quoted as such.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.catalog import load_suite
from qcb.util import utc_now


def record(task, model: str, seed: int, passed: bool, score: float, index: int, invalid: bool = False):
    return {
        "schema_version": "1.0.0",
        "synthetic": True,
        "run_id": f"synthetic-{model}-{task.id}-{seed}",
        "started_at": "2026-08-20T00:00:00.000Z",
        "completed_at": utc_now(),
        "suite": "smoke",
        "lane": "normalized",
        "seed": seed,
        "model": {
            "id": model,
            "family": "SYNTHETIC-NOT-A-REAL-MODEL",
            "file": "",
            "sha256": "",
            "hash_status": "not_checked",
            "quantization": "Q4_K_M",
            "template_id": "synthetic",
        },
        "inference": {
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 0,
            "min_p": 0.0,
            "max_tokens": 8192,
            "context_size": 32768,
            "reasoning_effort": "medium",
            "mtp_enabled": False,
            "tool_mode": True,
            "system_prompt_sha256": "synthetic",
        },
        "task": {
            "id": task.id,
            "title": task.title,
            "category": task.category,
            "language": task.language,
            "difficulty": task.difficulty,
            "weight": task.weight,
            "task_type": task.task_type,
        },
        "outcome": "invalid_output" if invalid else "completed",
        "verification": {
            "passed": passed,
            "tests_passed": int(round(score * 10)),
            "tests_total": 10,
            "score": score,
            "verifier_exit_code": 0 if passed else 1,
        },
        "usage": {
            "prompt_tokens": 1000 + index * 17,
            "completion_tokens": 500 + index * 19,
            "total_tokens": 1500 + index * 36,
            "reasoning_tokens": 180 + index * 7,
        },
        "timing": {"wall_seconds": 20.0 + index * 1.25 + (seed % 7)},
        "agent": {
            "tool_calls": 4 + index % 4,
            "invalid_tool_calls": 1 if invalid else 0,
            "patch_bytes": 300 + index * 5,
        },
        "gpu": {"available": True, "peak_memory_used_mb": 18300 + index * 13},
        "artifacts": "synthetic/no-artifacts",
    }


def write(path: Path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    tasks = load_suite(ROOT, "smoke")
    seeds = [11, 29, 47]
    original_rows = []
    candidate_rows = []
    for seed in seeds:
        for index, task in enumerate(tasks):
            original_pass = (index + seed) % 5 != 0
            candidate_pass = original_pass or (index + seed) % 7 == 0
            original_rows.append(record(task, "synthetic-original", seed, original_pass, 1.0 if original_pass else 0.5, index))
            candidate_rows.append(record(task, "synthetic-candidate", seed, candidate_pass, 1.0 if candidate_pass else 0.6, index, invalid=(index == 10 and seed == 29)))
    write(ROOT / "examples" / "synthetic-original-normalized-smoke.jsonl", original_rows)
    write(ROOT / "examples" / "synthetic-candidate-normalized-smoke.jsonl", candidate_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
