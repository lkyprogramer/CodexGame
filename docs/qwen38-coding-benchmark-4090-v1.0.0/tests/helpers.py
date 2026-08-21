from __future__ import annotations

from typing import Any


def row(
    task_id: str,
    category: str,
    *,
    model: str = "model-a",
    passed: bool = True,
    score: float | None = None,
    seed: int = 42,
    wall: float = 10.0,
    completion_tokens: int = 100,
    reasoning_tokens: int | None = 20,
    outcome: str = "completed",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "run_id": f"{model}-{task_id}-{seed}",
        "suite": "smoke",
        "lane": "normalized",
        "seed": seed,
        "model": {"id": model, "quantization": "Q4_K_M"},
        "task": {
            "id": task_id,
            "title": task_id,
            "category": category,
            "language": "java",
            "difficulty": 3,
            "weight": 1.0,
            "task_type": "patch",
        },
        "outcome": outcome,
        "verification": {
            "passed": passed,
            "tests_passed": 1 if passed else 0,
            "tests_total": 1,
            "score": float(passed) if score is None else score,
        },
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": completion_tokens,
            "total_tokens": 200 + completion_tokens,
            "reasoning_tokens": reasoning_tokens,
        },
        "timing": {"wall_seconds": wall},
        "agent": {"tool_calls": 2, "invalid_tool_calls": 0},
        "gpu": {"available": False},
    }
