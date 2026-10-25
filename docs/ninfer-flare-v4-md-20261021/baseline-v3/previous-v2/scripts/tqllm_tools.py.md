# V2 支撑材料：`scripts/tqllm_tools.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: scripts/tqllm_tools.py -->
<!-- payload-sha256: 8ea120ee85d0dfd565eedf3eb8b5a005ae2c72099fc523e354ba19d5415bf775 -->
<!-- payload-bytes: 7305 -->

<!-- payload-begin -->
````python
"""CPU planning aids, not inference implementations or GPU qualification.

All sizes use bytes. Budget inputs must be measured device allocations to justify
BUDGET_GO; a model's download size alone is not a device-memory measurement.
"""
from __future__ import annotations
import math
from collections.abc import Mapping, Sequence
from typing import Any


def _integer(value: Any, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < (1 if positive else 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'}")
    return value


def estimate_budget(config: Mapping[str, Any]) -> dict[str, Any]:
    """Compute incremental memory; never certify runtime or model accuracy.

    aggregate_archive_tokens counts all retained sessions, not tokens per lane.
    Explicit byte fields (staging/index/scratch/graphs/checkpoints) are aggregate
    allocations; only gpu_ring_rows is multiplied by resident_draft_lanes.
    A reclaim is a measured disjoint allocation removed from baseline, never a
    hoped-for MTP saving. The external phase gate must inspect reclaim_evidence.
    """
    size_fields = (
        "total_gpu_bytes", "baseline_gpu_peak_bytes", "total_host_bytes",
        "baseline_host_peak_bytes", "draft_weights_bytes", "draft_layers",
        "draft_kv_heads", "draft_head_dim", "draft_hidden", "target_feature_layers",
        "aggregate_archive_tokens", "gpu_ring_rows", "resident_draft_lanes",
        "staging_bytes", "index_bytes", "scratch_bytes", "graph_bytes",
        "draft_head_extra_bytes", "checkpoint_bytes", "pinned_transfer_bytes",
        "gpu_reserve_bytes", "host_reserve_bytes", "reclaimed_gpu_bytes",
    )
    try:
        n = {key: _integer(config[key], key) for key in size_fields}
        archive = config["archive_kind"]
        measured = config["inputs_measured"]
        reclaim_evidence = config["reclaim_evidence"]
    except KeyError as exc:
        raise ValueError(f"missing required field: {exc.args[0]}") from exc
    for key in ("total_gpu_bytes", "total_host_bytes", "draft_layers", "draft_kv_heads",
                "draft_head_dim", "draft_hidden", "target_feature_layers", "resident_draft_lanes"):
        _integer(n[key], key, positive=True)
    if not isinstance(measured, bool):
        raise ValueError("inputs_measured must be boolean")
    if archive not in ("projected_bf16", "raw_features_bf16"):
        raise ValueError("archive_kind must be projected_bf16 or raw_features_bf16; target KV is not draft features")
    if not isinstance(reclaim_evidence, str):
        raise ValueError("reclaim_evidence must be a string")
    if n["reclaimed_gpu_bytes"] and not reclaim_evidence.strip():
        raise ValueError("reclaimed_gpu_bytes requires measured owned-slab evidence")
    if n["reclaimed_gpu_bytes"] > n["baseline_gpu_peak_bytes"]:
        raise ValueError("reclaim exceeds baseline")
    kv_bpt = n["draft_layers"] * n["draft_kv_heads"] * n["draft_head_dim"] * 2 * 2
    archive_bpt = n["draft_hidden"] * 2
    if archive == "raw_features_bf16":
        archive_bpt *= n["target_feature_layers"]
    ring = n["gpu_ring_rows"] * n["resident_draft_lanes"] * kv_bpt
    host_archive = n["aggregate_archive_tokens"] * archive_bpt
    gpu_extra = ring + sum(n[key] for key in (
        "draft_weights_bytes", "staging_bytes", "index_bytes", "scratch_bytes",
        "graph_bytes", "draft_head_extra_bytes", "checkpoint_bytes"))
    gpu_peak = n["baseline_gpu_peak_bytes"] - n["reclaimed_gpu_bytes"] + gpu_extra
    host_peak = n["baseline_host_peak_bytes"] + host_archive + n["pinned_transfer_bytes"]
    fits = (gpu_peak + n["gpu_reserve_bytes"] <= n["total_gpu_bytes"] and
            host_peak + n["host_reserve_bytes"] <= n["total_host_bytes"])
    verdict = ("BUDGET_GO_NOT_GPU_QUALIFIED" if fits else "BUDGET_NO_GO") if measured else "ILLUSTRATIVE_ONLY"
    return {
        "scope": "CPU_ESTIMATE_NOT_INFERENCE_TEST", "verdict": verdict,
        "fits_with_reserve": fits, "draft_kv_bytes_per_token": kv_bpt,
        "hypothetical_full_draft_kv_bytes": n["aggregate_archive_tokens"] * kv_bpt,
        "host_archive_bytes": host_archive, "gpu_ring_bytes": ring,
        "gpu_incremental_bytes": gpu_extra, "projected_gpu_peak_bytes": gpu_peak,
        "projected_host_peak_bytes": host_peak,
        "gpu_headroom_after_reserve_bytes": n["total_gpu_bytes"] - gpu_peak - n["gpu_reserve_bytes"],
        "host_headroom_after_reserve_bytes": n["total_host_bytes"] - host_peak - n["host_reserve_bytes"],
        "reclaim_evidence": reclaim_evidence,
    }


def eligible_remote_chunks(total_tokens: int, recent: int, chunk_size: int = 16) -> list[int]:
    """Exhaustive CPU oracle; unlike tqLLM's prototype, does not truncate to 4096.

    Only complete chunks wholly before the recent window are returned. Production
    GPU code must perform hierarchical selection; this list is not its algorithm.
    """
    _integer(total_tokens, "total_tokens")
    _integer(recent, "recent")
    _integer(chunk_size, "chunk_size", positive=True)
    return list(range(max(0, total_tokens - recent) // chunk_size))


def select_pages(scores: Mapping[int, float], k: int) -> list[int]:
    """CPU top-k oracle: descending finite score, then ascending page id."""
    _integer(k, "k")
    for page, score in scores.items():
        _integer(page, "page")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            raise ValueError("page score must be finite")
    return sorted(scores, key=lambda page: (-scores[page], page))[:k]


def summarize_rounds(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize a chain-only sequence of nonoverlapping measured execution rounds.

    committed includes the correction/bonus token, accepted_drafts does not.
    round_wall_ns is the measured critical path, not a sum of overlapping spans.
    This is NOT a multi-request throughput/TTFT or tree-acceptance calculator.
    """
    if not rows:
        raise ValueError("at least one measured round is required")
    totals = dict(committed_tokens=0, accepted_drafts=0, drafted_tokens=0, round_wall_ns=0)
    for index, row in enumerate(rows):
        try:
            values = {key: _integer(row[key], f"row[{index}].{key}", positive=key == "round_wall_ns")
                      for key in totals}
        except KeyError as exc:
            raise ValueError(f"row[{index}] missing {exc.args[0]}") from exc
        if values["accepted_drafts"] > values["drafted_tokens"]:
            raise ValueError("accepted drafts exceed proposed drafts")
        if values["committed_tokens"] > values["accepted_drafts"] + 1:
            raise ValueError("chain committed tokens exceed accepted drafts plus one")
        for key in totals:
            totals[key] += values[key]
    return {**totals, "rounds": len(rows),
            "effective_tokens_per_second": totals["committed_tokens"] * 1e9 / totals["round_wall_ns"],
            "draft_acceptance": (totals["accepted_drafts"] / totals["drafted_tokens"]
                                 if totals["drafted_tokens"] else None),
            "scope": "CHAIN_EXECUTION_ROUNDS_ONLY"}
````
<!-- payload-end -->
