"""Offline P01 observations; never infer a dependency DAG from aggregate timings.

summarize_windows accepts UTF-8 engine/server logs and REQUESTS/WINDOWS JSONL.
Request rows use frontier contracts or legacy {name, metrics: {...}} records.
Window rows use contracts.WINDOWS_SCHEMA (engine_id/request_id/window_id/start/
end/unit/clock_domain). Interval union additionally requires caller-attested
identity.clock_evidence = {verified: true, engine_id, clock_domain, evidence_ref}.
The caller must establish that evidence from originals; naming a clock alone is
not verification. Union is observed coverage, never removable time or speedup.
All recognized records retain path, 1-based line and exact original text.
"""
import json
import math
import re
from pathlib import Path


_NUMBER = r"(\d+(?:\.\d+)?)"
_DECODE = re.compile(
    r"strata decode timing: (\d+) windows, avg T " + _NUMBER
    + r", " + _NUMBER + r" tokens/window, " + _NUMBER + r" ms/window"
)
_SERVE = re.compile(
    r"strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in "
    + _NUMBER + r" ms \([^)]*\), (\d+) generated in " + _NUMBER + r" ms"
)
_DONE = re.compile(
    r"\[strata\] done: (\d+) tokens in " + _NUMBER
    + r" s \(" + _NUMBER + r" tok/s\) \(([^,]+), cancel=(True|False)\)"
)
_REQUEST_FIELDS = (
    "engine_id", "request_id", "name", "prime_or_append", "execution_status",
    "stop_reason", "prompt_tokens", "read_tokens", "reused_tokens",
    "completion_tokens", "generated_tokens", "decode_ms", "prompt_ms",
    "wall_ms", "wall_s", "response_error", "failure_kind", "valid",
)


def summarize_windows(trace_paths, identity) -> dict:
    """Read originals without mutation. Bad JSON/windows raise ValueError.

    Missing files and UTF-8 errors remain explicit I/O exceptions. Unrecognized
    native lines are counted, not interpreted as missing/zero duration. This
    adapter always returns INSUFFICIENT: it does not verify CPU/CUDA dependencies.
    """
    requests, timings, windows, sources = [], [], [], []
    window_ids = set()
    for trace_path in trace_paths:
        path = Path(trace_path)
        count = 0
        recognized = 0
        with path.open(encoding="utf-8") as stream:
            for count, raw in enumerate(stream, 1):
                line = raw.rstrip("\r\n")
                source = {"path": str(path), "line": count, "text": line}
                if not line.strip():
                    continue
                if path.suffix.lower() == ".jsonl":
                    try:
                        row = json.loads(line)
                    except ValueError as exc:
                        raise ValueError(f"{path}:{count}: invalid JSON") from exc
                    if not isinstance(row, dict):
                        raise ValueError(f"{path}:{count}: expected JSON object")
                    if "window_id" in row:
                        key = tuple(row.get(k) for k in ("engine_id", "request_id", "window_id"))
                        if not all(isinstance(k, str) and k for k in key):
                            raise ValueError(f"{path}:{count}: missing window identity")
                        if key in window_ids:
                            raise ValueError(f"{path}:{count}: duplicate window {key}")
                        window_ids.add(key)
                        windows.append({**row, "source": source})
                    elif "request_id" in row or "metrics" in row or "name" in row:
                        metrics = row.get("metrics", {})
                        if not isinstance(metrics, dict):
                            raise ValueError(f"{path}:{count}: metrics must be an object")
                        # Preserve explicit nulls and failures; never infer token counts from SSE.
                        fields = {k: row[k] if k in row else metrics[k]
                                  for k in _REQUEST_FIELDS if k in row or k in metrics}
                        requests.append({**fields, "source": source})
                    else:
                        continue
                elif match := _DECODE.search(line):
                    timings.append({
                        "kind": "decode_aggregate", "windows": int(match[1]),
                        "avg_draft_tokens": float(match[2]),
                        "tokens_per_window": float(match[3]),
                        "ms_per_window": float(match[4]), "source": source,
                        "request_id": None,
                    })
                elif match := _SERVE.search(line):
                    timings.append({
                        "kind": "native_request_aggregate", "prompt_tokens": int(match[1]),
                        "reused_tokens": int(match[2]), "read_tokens": int(match[3]),
                        "prompt_ms": float(match[4]), "generated_tokens": int(match[5]),
                        "decode_ms": float(match[6]), "request_id": None, "source": source,
                    })
                elif match := _DONE.search(line):
                    timings.append({
                        "kind": "server_done", "generated_tokens": int(match[1]),
                        "rounded_wall_s": float(match[2]), "reported_decode_tps": float(match[3]),
                        "stop_reason": match[4], "cancelled": match[5] == "True",
                        "request_id": None, "source": source,
                    })
                elif "strata prefill timing:" in line:
                    # Native versions differ: keep exact original, without guessing components.
                    timings.append({"kind": "prefill_aggregate", "request_id": None, "source": source})
                else:
                    continue
                recognized += 1
        sources.append({"path": str(path), "lines": count, "recognized_records": recognized})

    reasons = []
    coverage = None
    proof = identity.get("clock_evidence", {})
    if not windows:
        reasons.append("No real per-window start/end records; aggregate window counts are not window traces")
    else:
        intervals = []
        for row in windows:
            start, end = row.get("start"), row.get("end")
            if (isinstance(start, bool) or isinstance(end, bool)
                    or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                    or not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start):
                raise ValueError(f"{row['source']['path']}:{row['source']['line']}: invalid window interval")
            if row.get("unit") not in ("ns", "ms", "s"):
                raise ValueError("window unit must be ns, ms or s")
            if (not isinstance(proof, dict) or proof.get("verified") is not True
                    or not proof.get("evidence_ref") or not proof.get("clock_domain")
                    or proof.get("clock_domain") != row.get("clock_domain")
                    or proof.get("engine_id") != row.get("engine_id")):
                reasons.append("Window clock/engine is not covered by verified clock evidence")
                break
            factor = {"ns": 1e-6, "ms": 1, "s": 1000}[row["unit"]]
            intervals.append((start * factor, end * factor))
        if len(intervals) == len(windows):
            # Union is descriptive elapsed coverage; no sums of CPU/GPU/pool waits.
            merged = []
            for start, end in sorted(intervals):
                if merged and start <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], end)
                else:
                    merged.append([start, end])
            coverage = sum(end - start for start, end in merged)
    reasons.append("CPU completion/CUDA dependency edges are not established by this adapter")
    return {
        "REQUESTS": requests, "TIMING_OBSERVATIONS": timings,
        "WINDOWS": windows, "SOURCES": sources,
        "OBSERVED_WINDOW_UNION_MS": coverage,
        "DEPENDENCIES": {"status": "UNKNOWN", "nodes": [], "edges": [],
                         "unknown_dependencies": ["CPU completion to join/commit", "CUDA stream/event dependencies"],
                         "expert_dtype": None, "expert_nt": None,
                         "missing_reasons": {"expert_dtype": "No verified per-window dispatch evidence",
                                             "expert_nt": "No verified per-window dispatch evidence"}},
        "QUALIFICATION": {"status": "INSUFFICIENT", "reasons": list(dict.fromkeys(reasons)),
                          "removable_ms": None, "performance_gate": "NOT_RUN"},
    }
