#!/usr/bin/env python3
"""DiffusionGemma 26B-A4B Q4_K_M benchmark on RTX 4090."""

from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


RUN_DIR = Path("/home/hhtele/diffusiongemma-26b-a4b-4bit-4090-20260612")
SRC_DIR = Path("/home/hhtele/llama.cpp-diffusiongemma-pr24423-20260612")
BIN = SRC_DIR / "build/bin/llama-diffusion-cli"
MODEL = Path("/data/models/gemma/diffusiongemma/diffusiongemma-26B-A4B-it-Q4_K_M.gguf")
OUT_DIR = RUN_DIR / "results"
PROMPT_DIR = OUT_DIR / "prompts"
RAW_DIR = OUT_DIR / "raw"
SUMMARY_PATH = OUT_DIR / "summary.json"


def nvidia_query() -> dict[str, Any]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=5).strip()
        used, free, util, power, temp = [part.strip() for part in out.split(",")]
        return {
            "memory_used_mib": float(used),
            "memory_free_mib": float(free),
            "utilization_gpu_pct": float(util),
            "power_w": float(power),
            "temperature_c": float(temp),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


class GpuSampler:
    def __init__(self) -> None:
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        self._thread.join(timeout=3)
        nums = lambda key: [s.get(key) for s in self.samples if isinstance(s.get(key), (int, float))]
        return {
            "sample_count": len(self.samples),
            "max_memory_used_mib": max(nums("memory_used_mib"), default=None),
            "max_power_w": max(nums("power_w"), default=None),
            "max_utilization_gpu_pct": max(nums("utilization_gpu_pct"), default=None),
            "max_temperature_c": max(nums("temperature_c"), default=None),
            "last": self.samples[-1] if self.samples else None,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            sample = nvidia_query()
            sample["ts"] = time.time()
            self.samples.append(sample)
            time.sleep(1)


def make_prompt(target_tokens: int, marker: str, kind: str) -> str:
    if target_tokens <= 256:
        return (
            f"You are benchmarking DiffusionGemma Q4_K_M on RTX 4090. Marker: {marker}. "
            "Explain the performance tradeoff between diffusion generation and autoregressive decoding. "
            "Keep the answer coherent and include the marker once."
        )
    blocks = []
    block_count = max(1, target_tokens // 24)
    for i in range(block_count):
        blocks.append(
            f"CTX_{i:06d} OpenClaw DiffusionGemma benchmark context. "
            "This repeated repository trace mentions prompt cache, llama.cpp, GPU memory, "
            "token generation speed, 4-bit GGUF, and deterministic marker retrieval. "
        )
    return (
        f"Task kind: {kind}. Exact marker: {marker}.\n"
        "Use the context below as benchmark filler. In the final answer, explain what affects generation speed "
        "and include the exact marker once. Do not output a table.\n\n"
        + "\n".join(blocks)
        + f"\n\nFinal instruction: answer in complete sentences and include marker {marker} once."
    )


def normalize_output(stdout: str, stderr: str) -> str:
    # The PR runner may print logs to either stream. Keep stdout as primary model output.
    text = stdout.strip()
    if text:
        return text
    lines = []
    for line in stderr.splitlines():
        lowered = line.lower()
        if any(skip in lowered for skip in ["llama_", "ggml", "load_", "main:", "time", "cuda", "warning"]):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def parse_metrics(text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    patterns = [
        ("tokens_per_s", r"([0-9]+(?:\.[0-9]+)?)\s*(?:tokens|tok)/s"),
        ("tokens_per_s", r"([0-9]+(?:\.[0-9]+)?)\s*tokens per second"),
        ("predicted_tokens", r"predicted\s+([0-9]+)\s+tokens"),
        ("predicted_tokens", r"generated\s+([0-9]+)\s+tokens"),
        ("elapsed_s", r"([0-9]+(?:\.[0-9]+)?)\s*s(?:ec|econds)?\b"),
    ]
    for key, pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches and key not in metrics:
            value = matches[-1]
            metrics[key] = float(value) if "." in str(value) else int(value)
    return metrics


def looks_repetitive(text: str) -> bool:
    stripped = re.sub(r"\s+", " ", text.strip())
    if len(stripped) < 200:
        return False
    chunks = [stripped[i : i + 40] for i in range(0, min(len(stripped), 1200), 40)]
    return len(set(chunks)) <= max(3, len(chunks) // 5)


def run_once(case: dict[str, Any]) -> dict[str, Any]:
    cid = case["id"]
    prompt = make_prompt(case["prompt_target_tokens"], case["marker"], case["suite"])
    prompt_path = PROMPT_DIR / f"{cid}.txt"
    stdout_path = RAW_DIR / f"{cid}.stdout.txt"
    stderr_path = RAW_DIR / f"{cid}.stderr.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    cmd = [
        str(BIN),
        "-m",
        str(MODEL),
        "-ngl",
        "99",
        "-c",
        "131072",
        "-fa",
        "on",
        "-ctk",
        "q4_0",
        "-ctv",
        "q4_0",
        "--perf",
        "-n",
        str(case["n_predict"]),
        "-f",
        str(prompt_path),
    ]
    if case.get("extra_args"):
        cmd.extend(case["extra_args"])

    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")

    sampler = GpuSampler()
    sampler.start()
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=case.get("timeout_s", 2400),
            env=env,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(cmd, 124, exc.stdout or "", exc.stderr or "")
        timed_out = True
    elapsed_s = time.perf_counter() - started
    gpu = sampler.stop()

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    stdout_path.write_text(stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(stderr, encoding="utf-8", errors="replace")
    output = normalize_output(stdout, stderr)
    parsed = parse_metrics(stdout + "\n" + stderr)
    tokens_for_rate = parsed.get("predicted_tokens") or case["n_predict"]
    token_source = "parsed_predicted_tokens" if parsed.get("predicted_tokens") else "n_predict"
    cli_tps = parsed.get("tokens_per_s")
    effective_tps = cli_tps if isinstance(cli_tps, (int, float)) else tokens_for_rate / elapsed_s if elapsed_s else None

    return {
        "id": cid,
        "suite": case["suite"],
        "variant": case.get("variant", "default"),
        "run_index": case.get("run_index"),
        "warmup": case.get("warmup", False),
        "prompt_target_tokens": case["prompt_target_tokens"],
        "n_predict": case["n_predict"],
        "marker": case["marker"],
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0 and bool(output.strip()) and not timed_out,
        "timed_out": timed_out,
        "elapsed_s": elapsed_s,
        "effective_tokens_per_s": effective_tps,
        "cli_tokens_per_s": cli_tps,
        "tokens_for_rate": tokens_for_rate,
        "token_count_source": token_source,
        "parsed_metrics": parsed,
        "output_chars": len(output),
        "output_prefix": output[:1200],
        "empty_output": not bool(output.strip()),
        "repetitive_output": looks_repetitive(output),
        "marker_present": case["marker"] in output,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "prompt_path": str(prompt_path),
        "gpu": gpu,
    }


def cases() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    result.append({
        "id": "smoke_n256",
        "suite": "smoke",
        "prompt_target_tokens": 128,
        "n_predict": 256,
        "marker": "DG_SMOKE_Q4KM",
    })

    for n_predict in [256, 512, 1024, 2048, 4096]:
        base = {
            "suite": "output_length",
            "prompt_target_tokens": 128,
            "n_predict": n_predict,
            "marker": f"DG_OUTPUT_N{n_predict}",
        }
        result.append({"id": f"output_n{n_predict}_warmup", **base, "warmup": True, "run_index": 0})
        for run in range(1, 4):
            result.append({"id": f"output_n{n_predict}_run{run}", **base, "run_index": run})

    for prompt_tokens in [128, 1024, 4096, 16384, 65536, 131072]:
        marker = f"DG_PROMPT_{prompt_tokens}"
        for variant in ["cold", "warm"]:
            result.append({
                "id": f"prompt_{prompt_tokens}_{variant}",
                "suite": "prompt_length",
                "variant": variant,
                "prompt_target_tokens": prompt_tokens,
                "n_predict": 1024,
                "marker": marker,
                "timeout_s": 3000,
            })

    for prompt_tokens, n_predict in [
        (128, 256),
        (128, 1024),
        (4096, 1024),
        (16384, 1024),
        (65536, 1024),
        (65536, 2048),
        (131072, 1024),
    ]:
        for run in range(1, 3):
            result.append({
                "id": f"matrix_p{prompt_tokens}_n{n_predict}_run{run}",
                "suite": "matrix",
                "prompt_target_tokens": prompt_tokens,
                "n_predict": n_predict,
                "marker": f"DG_MATRIX_P{prompt_tokens}_N{n_predict}",
                "run_index": run,
                "timeout_s": 3000,
            })
    return result


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return sorted(values)[min(len(values) - 1, int(round((len(values) - 1) * 0.95)))]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        if row.get("warmup"):
            continue
        key = f"{row['suite']}|p{row['prompt_target_tokens']}|n{row['n_predict']}|{row.get('variant','default')}"
        groups.setdefault(key, []).append(row)
    summaries = []
    for key, rows in sorted(groups.items()):
        ok_rows = [r for r in rows if r.get("ok")]
        tps = [r["effective_tokens_per_s"] for r in ok_rows if isinstance(r.get("effective_tokens_per_s"), (int, float))]
        elapsed = [r["elapsed_s"] for r in ok_rows if isinstance(r.get("elapsed_s"), (int, float))]
        summaries.append({
            "key": key,
            "suite": rows[0]["suite"],
            "prompt_target_tokens": rows[0]["prompt_target_tokens"],
            "n_predict": rows[0]["n_predict"],
            "variant": rows[0].get("variant", "default"),
            "count": len(rows),
            "ok_count": len(ok_rows),
            "error_count": len(rows) - len(ok_rows),
            "median_effective_tokens_per_s": median(tps),
            "p95_effective_tokens_per_s": p95(tps),
            "median_elapsed_s": median(elapsed),
            "p95_elapsed_s": p95(elapsed),
            "max_memory_used_mib": max([r.get("gpu", {}).get("max_memory_used_mib") for r in ok_rows if isinstance(r.get("gpu", {}).get("max_memory_used_mib"), (int, float))], default=None),
            "max_power_w": max([r.get("gpu", {}).get("max_power_w") for r in ok_rows if isinstance(r.get("gpu", {}).get("max_power_w"), (int, float))], default=None),
            "max_temperature_c": max([r.get("gpu", {}).get("max_temperature_c") for r in ok_rows if isinstance(r.get("gpu", {}).get("max_temperature_c"), (int, float))], default=None),
            "empty_output_count": sum(1 for r in rows if r.get("empty_output")),
            "repetitive_output_count": sum(1 for r in rows if r.get("repetitive_output")),
            "marker_present_count": sum(1 for r in rows if r.get("marker_present")),
            "token_count_sources": sorted(set(str(r.get("token_count_source")) for r in rows)),
        })
    return {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model": str(MODEL),
        "binary": str(BIN),
        "result_count": len(results),
        "ok_count": sum(1 for r in results if r.get("ok")),
        "error_count": sum(1 for r in results if not r.get("ok")),
        "groups": summaries,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for case in cases():
        print(f"=== RUN {case['id']} ===", flush=True)
        row = run_once(case)
        results.append(row)
        (OUT_DIR / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = summarize(results)
        SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "id": row["id"],
            "suite": row["suite"],
            "ok": row["ok"],
            "returncode": row["returncode"],
            "elapsed_s": row["elapsed_s"],
            "effective_tokens_per_s": row["effective_tokens_per_s"],
            "token_count_source": row["token_count_source"],
            "empty": row["empty_output"],
            "repetitive": row["repetitive_output"],
            "marker": row["marker_present"],
            "gpu": row["gpu"],
        }, ensure_ascii=False), flush=True)
    print(json.dumps({"done": True, "summary": str(SUMMARY_PATH)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
