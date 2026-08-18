#!/usr/bin/env python3
"""Focused long-prompt retry for DiffusionGemma with explicit ubatch sizing."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from diffusiongemma_4bit_eval import (
    BIN,
    MODEL,
    RUN_DIR,
    GpuSampler,
    looks_repetitive,
    make_prompt,
    normalize_output,
)


OUT_DIR = RUN_DIR / "results_longprompt_retry"
PROMPT_DIR = OUT_DIR / "prompts"
RAW_DIR = OUT_DIR / "raw"

THROUGHPUT_RE = re.compile(
    r"throughput:\s*([0-9.]+) tok/s \(([0-9]+) tok in ([0-9.]+)ms\), in-step parallel ([0-9.]+) tok/s"
)
TOTAL_RE = re.compile(r"total time:\s*([0-9.]+)ms, time per step: ([0-9.]+)ms \(([0-9]+) steps over ([0-9]+) blocks")
UBATCH_RE = re.compile(r"set -ub and -c >= n_input \+ canvas_length = ([0-9]+) \+ ([0-9]+) = ([0-9]+)")
TOO_LONG_RE = re.compile(r"input too long \(([0-9]+) tokens\), max context is ([0-9]+)")


def parse_stdout(stdout: str, stderr: str) -> dict[str, Any]:
    text = stdout + "\n" + stderr
    parsed: dict[str, Any] = {}
    if match := THROUGHPUT_RE.search(stdout):
        parsed.update(
            {
                "generation_tokens_per_s": float(match.group(1)),
                "generated_tokens": int(match.group(2)),
                "generation_ms": float(match.group(3)),
                "in_step_parallel_tokens_per_s": float(match.group(4)),
            }
        )
    if match := TOTAL_RE.search(stdout):
        parsed.update(
            {
                "total_ms": float(match.group(1)),
                "step_ms": float(match.group(2)),
                "steps": int(match.group(3)),
                "blocks": int(match.group(4)),
            }
        )
    if match := UBATCH_RE.search(text):
        parsed["ubatch_required"] = {
            "n_input": int(match.group(1)),
            "canvas_length": int(match.group(2)),
            "required": int(match.group(3)),
        }
    if match := TOO_LONG_RE.search(text):
        parsed["input_too_long"] = {
            "input_tokens": int(match.group(1)),
            "max_context": int(match.group(2)),
        }
    return parsed


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    cid = case["id"]
    prompt = make_prompt(case["prompt_builder_tokens"], case["marker"], "longprompt_retry")
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
        str(case["ctx"]),
        "-ub",
        str(case["ubatch"]),
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
            timeout=case.get("timeout_s", 3600),
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
    parsed = parse_stdout(stdout, stderr)
    has_error = " E error:" in stdout or " E error:" in stderr or proc.returncode != 0 or timed_out
    marker_present = case["marker"] in output
    valid = (
        proc.returncode == 0
        and not timed_out
        and not has_error
        and bool(output.strip())
        and marker_present
        and "generation_tokens_per_s" in parsed
    )

    generated_tokens = parsed.get("generated_tokens")
    return {
        "id": cid,
        "desired_prompt_tokens": case["desired_prompt_tokens"],
        "prompt_builder_tokens": case["prompt_builder_tokens"],
        "n_predict": case["n_predict"],
        "ctx": case["ctx"],
        "ubatch": case["ubatch"],
        "marker": case["marker"],
        "cmd": cmd,
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "valid": valid,
        "has_error": has_error,
        "elapsed_s": elapsed_s,
        "generated_tokens": generated_tokens,
        "e2e_generated_tokens_per_s": generated_tokens / elapsed_s if isinstance(generated_tokens, int) and elapsed_s else None,
        "parsed": parsed,
        "output_chars": len(output),
        "output_prefix": output[:1200],
        "empty_output": not bool(output.strip()),
        "repetitive_output": looks_repetitive(output),
        "marker_present": marker_present,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "prompt_path": str(prompt_path),
        "gpu": gpu,
    }


def cases() -> list[dict[str, Any]]:
    # The first full run showed the synthetic prompt tokenizes at roughly 2.13x
    # the builder target. Keep retry prompts below the requested real token size.
    specs = [
        (4096, 1900, 1024, 8192),
        (16384, 7700, 1024, 32768),
        (65536, 30800, 1024, 73728),
        (65536, 30800, 2048, 73728),
        (128000, 59000, 1024, 131072),
    ]
    result: list[dict[str, Any]] = []
    for desired, builder, n_predict, ubatch in specs:
        marker = f"DG_RETRY_P{desired}_N{n_predict}"
        for variant in ["cold", "warm"]:
            result.append(
                {
                    "id": f"retry_p{desired}_n{n_predict}_{variant}",
                    "desired_prompt_tokens": desired,
                    "prompt_builder_tokens": builder,
                    "n_predict": n_predict,
                    "ctx": 131072,
                    "ubatch": ubatch,
                    "marker": marker,
                    "variant": variant,
                    "timeout_s": 3600,
                }
            )
    return result


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for case in cases():
        print(f"=== RETRY {case['id']} ===", flush=True)
        row = run_case(case)
        rows.append(row)
        (OUT_DIR / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "id": row["id"],
                    "valid": row["valid"],
                    "returncode": row["returncode"],
                    "elapsed_s": row["elapsed_s"],
                    "generation_tokens_per_s": row["parsed"].get("generation_tokens_per_s"),
                    "generated_tokens": row.get("generated_tokens"),
                    "e2e_generated_tokens_per_s": row.get("e2e_generated_tokens_per_s"),
                    "marker": row["marker_present"],
                    "parsed": row["parsed"],
                    "gpu": row["gpu"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    print(json.dumps({"done": True, "results": str(OUT_DIR / "results.json")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
