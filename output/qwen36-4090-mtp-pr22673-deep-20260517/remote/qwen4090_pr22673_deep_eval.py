#!/usr/bin/env python3
"""Deep Qwen3.6 MTP PR22673 evaluation on RTX 4090.

The script starts one llama-server process per config, runs OpenAI-compatible
quality/performance probes, samples GPU memory, then writes JSONL summaries.
It intentionally does not manage the production systemd service; stop/restore
that outside this script.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MODEL_PATH = "/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf"
OLD_BIN = "/home/hhtele/llama.cpp-mtp-unsloth-20260513/build/bin/llama-server"
NEW_BIN = "/home/hhtele/llama.cpp-master-pr22673-20260517/build/bin/llama-server"
BASE_URL = "http://127.0.0.1:19343"
PORT = "19343"


CONFIGS: list[dict[str, Any]] = [
    {
        "id": "old_mtp_n4_q4_ctx32",
        "binary": OLD_BIN,
        "ctx": 32768,
        "kv": "q4_0",
        "spec": ["--spec-type", "mtp", "--spec-draft-n-max", "4"],
        "category": "baseline",
    },
    {
        "id": "new_draft_n2_p075_q4_ctx32",
        "binary": NEW_BIN,
        "ctx": 32768,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "2"],
        "category": "draft-mtp",
    },
    {
        "id": "new_draft_n3_p075_q4_ctx32",
        "binary": NEW_BIN,
        "ctx": 32768,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "3"],
        "category": "draft-mtp",
    },
    {
        "id": "new_draft_n4_p075_q4_ctx32",
        "binary": NEW_BIN,
        "ctx": 32768,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "4"],
        "category": "draft-mtp",
    },
    {
        "id": "new_draft_n4_p000_q4_ctx32",
        "binary": NEW_BIN,
        "ctx": 32768,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.0", "--spec-draft-n-max", "4"],
        "category": "draft-mtp-regression-check",
    },
    {
        "id": "new_draft_n6_p075_q4_ctx32",
        "binary": NEW_BIN,
        "ctx": 32768,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "6"],
        "category": "draft-mtp",
    },
    {
        "id": "new_ngram_draft_n2_p075_q4_ctx32",
        "binary": NEW_BIN,
        "ctx": 32768,
        "kv": "q4_0",
        "spec": [
            "--spec-type",
            "ngram-mod,draft-mtp",
            "--spec-draft-p-min",
            "0.75",
            "--spec-draft-n-max",
            "2",
            "--spec-ngram-mod-n-match",
            "24",
            "--spec-ngram-mod-n-min",
            "48",
            "--spec-ngram-mod-n-max",
            "64",
        ],
        "category": "ngram-draft-mtp",
    },
    {
        "id": "new_draft_n2_p075_q8_ctx32",
        "binary": NEW_BIN,
        "ctx": 32768,
        "kv": "q8_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "2"],
        "category": "kv-q8",
    },
    {
        "id": "new_draft_n2_p075_q4_ctx64",
        "binary": NEW_BIN,
        "ctx": 65536,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "2"],
        "category": "ctx64",
    },
    {
        "id": "new_draft_n2_p075_q8_ctx64",
        "binary": NEW_BIN,
        "ctx": 65536,
        "kv": "q8_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "2"],
        "category": "ctx64-kv-q8",
    },
    {
        "id": "new_draft_n2_p075_q4_ctx128_cache",
        "binary": NEW_BIN,
        "ctx": 131072,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "2"],
        "category": "ctx128",
        "marker_words": 1400,
        "marker_repeats": 2,
    },
    {
        "id": "new_draft_n4_p075_q4_ctx128_cache",
        "binary": NEW_BIN,
        "ctx": 131072,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "4"],
        "category": "ctx128",
        "marker_words": 1400,
        "marker_repeats": 2,
    },
    {
        "id": "new_draft_n6_p075_q4_ctx128_probe",
        "binary": NEW_BIN,
        "ctx": 131072,
        "kv": "q4_0",
        "spec": ["--spec-type", "draft-mtp", "--spec-draft-p-min", "0.75", "--spec-draft-n-max", "6"],
        "category": "ctx128-risk",
        "marker_words": 700,
        "marker_repeats": 1,
    },
]


def json_request(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str, timeout: int) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_ready(timeout_s: int = 600) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        try:
            models = get_json(f"{BASE_URL}/v1/models", 5)
            if "data" in models or "models" in models:
                return models
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
        time.sleep(2)
    raise RuntimeError(f"server not ready: {last_error}")


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
        used = [s.get("memory_used_mib") for s in self.samples if isinstance(s.get("memory_used_mib"), (int, float))]
        power = [s.get("power_w") for s in self.samples if isinstance(s.get("power_w"), (int, float))]
        util = [s.get("utilization_gpu_pct") for s in self.samples if isinstance(s.get("utilization_gpu_pct"), (int, float))]
        return {
            "sample_count": len(self.samples),
            "max_memory_used_mib": max(used, default=None),
            "max_power_w": max(power, default=None),
            "max_utilization_gpu_pct": max(util, default=None),
            "last": self.samples[-1] if self.samples else None,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            sample = nvidia_query()
            sample["ts"] = time.time()
            self.samples.append(sample)
            time.sleep(1)


def build_server_cmd(config: dict[str, Any]) -> list[str]:
    cmd = [
        config["binary"],
        "-m",
        MODEL_PATH,
        "--alias",
        f"openclaw/{config['id']}",
        "-ngl",
        "99",
        "-c",
        str(config["ctx"]),
        "-np",
        "1",
        "-fa",
        "on",
        "-ctk",
        config["kv"],
        "-ctv",
        config["kv"],
        "-rea",
        "off",
        "--temp",
        "0",
        "--top-p",
        "1",
        "--cache-prompt",
        "--cache-ram",
        "2048",
        "--host",
        "127.0.0.1",
        "--port",
        PORT,
    ]
    cmd.extend(config["spec"])
    return cmd


def stop_process(proc: subprocess.Popen[Any] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or ""


def run_chat(config_id: str, case_id: str, prompt: str, max_tokens: int, timeout: int = 900) -> dict[str, Any]:
    payload = {
        "model": f"openclaw/{config_id}",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": max_tokens,
        "stream": False,
    }
    started = time.perf_counter()
    try:
        response = json_request(f"{BASE_URL}/v1/chat/completions", payload, timeout)
        ok = True
        error = None
    except urllib.error.HTTPError as exc:
        ok = False
        response = {"status": exc.code, "body": exc.read().decode("utf-8", errors="replace")}
        error = repr(exc)
    except Exception as exc:  # noqa: BLE001
        ok = False
        response = {}
        error = repr(exc)
    elapsed_s = time.perf_counter() - started

    content = extract_content(response) if ok else ""
    usage = response.get("usage") or {}
    timings = response.get("timings") or {}
    completion_tokens = usage.get("completion_tokens") or 0
    predicted_ms = timings.get("predicted_ms") or 0
    prompt_tokens = usage.get("prompt_tokens") or 0
    prompt_ms = timings.get("prompt_ms") or 0
    draft_n = timings.get("draft_n") or 0
    draft_acc = timings.get("draft_n_accepted") or 0

    return {
        "case_id": case_id,
        "ok": ok,
        "elapsed_s": elapsed_s,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "response_tokens_per_s": completion_tokens / elapsed_s if completion_tokens else None,
        "prompt_tokens_per_s": prompt_tokens / (prompt_ms / 1000) if prompt_ms else None,
        "decode_tokens_per_s": completion_tokens / (predicted_ms / 1000) if predicted_ms else None,
        "draft_n": draft_n,
        "draft_n_accepted": draft_acc,
        "draft_accept_rate": draft_acc / draft_n if draft_n else None,
        "cache_n": timings.get("cache_n"),
        "prompt_ms": prompt_ms,
        "predicted_ms": predicted_ms,
        "think_leak": content.lstrip().startswith("<think>"),
        "content": content,
        "content_prefix": content[:500],
        "usage": usage,
        "timings": timings,
        "error": error,
        "raw_error_body": response.get("body") if isinstance(response, dict) else None,
    }


def run_stream_ttft(config_id: str) -> dict[str, Any]:
    payload = {
        "model": f"openclaw/{config_id}",
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 8,
        "stream": True,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    first_token_s = None
    content_parts: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content") or ""
                if piece and first_token_s is None:
                    first_token_s = time.perf_counter() - started
                if piece:
                    content_parts.append(piece)
        return {
            "case_id": "stream_ttft_ok",
            "ok": True,
            "elapsed_s": time.perf_counter() - started,
            "ttft_s": first_token_s,
            "content": "".join(content_parts),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "case_id": "stream_ttft_ok",
            "ok": False,
            "elapsed_s": time.perf_counter() - started,
            "ttft_s": first_token_s,
            "content": "".join(content_parts),
            "error": repr(exc),
        }


def marker_prompt(words: int, marker: str) -> str:
    prefix = " ".join(
        f"openclaw_file_{i:05d}: stable repository context, protocol schema, patch hunk, tool argument, "
        f"runtime log, deterministic cache probe, repeated identifier OpenClawBenchmarkToken."
        for i in range(words)
    )
    suffix = " ".join(
        f"tail_note_{i:05d}: scheduler observation, cache retention note, response validator."
        for i in range(max(20, words // 20))
    )
    return (
        "You are testing long-context exact retrieval. Return only the exact marker string. "
        "No quotes, no markdown, no explanation.\n\n"
        f"{prefix}\n\nEXACT_MARKER: {marker}\n\n{suffix}\n\nReturn only the exact marker string."
    )


def build_cases(config: dict[str, Any]) -> list[dict[str, Any]]:
    cases = [
        {
            "case_id": "short_ok",
            "prompt": "Reply with OK only.",
            "max_tokens": 8,
            "kind": "short",
        },
        {
            "case_id": "json_tool",
            "prompt": (
                "Return only valid minified JSON for a coding agent tool call with keys "
                "action, file, risk, tests. Use action=\"edit\", file=\"apps/game-runtime/src/runtime/GameRuntimeServer.ts\", "
                "risk=\"low\", tests=[\"pnpm test\"]. No markdown."
            ),
            "max_tokens": 160,
            "kind": "json",
        },
        {
            "case_id": "patch_unified_diff",
            "prompt": (
                "Return only a unified diff patch. No markdown fence. Modify a TypeScript function named "
                "formatScore so that null returns \"N/A\" and numbers return value.toFixed(2). Include file path "
                "src/score.ts."
            ),
            "max_tokens": 512,
            "kind": "patch",
        },
        {
            "case_id": "code_review_cn",
            "prompt": (
                "用中文做一次简短 code review，只列出最重要的问题。代码：\n"
                "async function save(items) { items.forEach(async item => { await db.insert(item); }); return true; }\n"
                "要求：不要泛泛而谈，指出并发/一致性问题。"
            ),
            "max_tokens": 512,
            "kind": "review",
        },
        {
            "case_id": "long_generation_1024",
            "prompt": (
                "Write a dense benchmark analysis for a local coding agent model on RTX 4090. Cover MTP speculative "
                "decoding, prompt cache, long-context prefill, JSON/tool formatting, patch generation, and quality "
                "tradeoffs. Keep writing until the token budget is nearly exhausted. No markdown tables."
            ),
            "max_tokens": 1024,
            "kind": "long_generation",
        },
    ]
    words = config.get("marker_words")
    repeats = config.get("marker_repeats", 0)
    if words:
        marker = f"OPENCLAW_PR22673_{config['id']}_WORDS_{words}".replace("-", "_")
        prompt = marker_prompt(int(words), marker)
        for idx in range(int(repeats)):
            cases.append(
                {
                    "case_id": f"long_context_marker_rep{idx + 1}",
                    "prompt": prompt,
                    "max_tokens": 48,
                    "kind": "long_context_marker",
                    "expected": marker,
                }
            )
    return cases


def score_case(result: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    content = result.get("content") or ""
    ok = bool(result.get("ok"))
    fmt = 0.0
    quality = 0.0
    notes: list[str] = []
    if not ok:
        return {"format_score": 0.0, "quality_score": 0.0, "notes": ["request failed"]}
    if result.get("think_leak"):
        notes.append("think leak")
    kind = case["kind"]
    stripped = content.strip()
    if kind == "short":
        fmt = 5.0 if stripped == "OK" else 3.0 if "OK" in stripped else 1.0
        quality = fmt
    elif kind == "json":
        try:
            parsed = json.loads(stripped)
            fmt = 5.0
            expected_keys = {"action", "file", "risk", "tests"}
            quality = 5.0 if expected_keys.issubset(parsed.keys()) else 3.5
        except json.JSONDecodeError:
            fmt = 1.0
            quality = 2.0
            notes.append("invalid json")
    elif kind == "patch":
        has_fence = "```" in content
        has_diff = "--- " in content and "+++ " in content and "@@" in content
        fmt = 5.0 if has_diff and not has_fence else 3.0 if has_diff else 1.0
        quality = 4.5 if has_diff and "toFixed(2)" in content and "N/A" in content else 2.5
        if has_fence:
            notes.append("markdown fence")
    elif kind == "review":
        has_issue = ("forEach" in content or "Promise" in content or "await" in content) and (
            "并发" in content or "一致" in content or "等待" in content or "错误" in content
        )
        fmt = 4.5 if len(content) < 1200 else 3.5
        quality = 4.5 if has_issue else 2.5
    elif kind == "long_generation":
        fmt = 4.5 if not result.get("think_leak") else 2.0
        quality = 4.0 if result.get("completion_tokens", 0) >= 800 else 3.0
    elif kind == "long_context_marker":
        expected = case.get("expected")
        exact = stripped == expected
        fmt = 5.0 if exact else 1.0
        quality = 5.0 if exact else 1.0
        if not exact:
            notes.append("marker mismatch")
    if result.get("think_leak"):
        fmt = min(fmt, 2.0)
        quality = min(quality, 3.0)
    return {"format_score": fmt, "quality_score": quality, "notes": notes}


def summarize_config(config: dict[str, Any], results: list[dict[str, Any]], gpu_summary: dict[str, Any]) -> dict[str, Any]:
    ok = [r for r in results if r.get("ok")]
    decode = [r["decode_tokens_per_s"] for r in ok if isinstance(r.get("decode_tokens_per_s"), (int, float))]
    prompt = [r["prompt_tokens_per_s"] for r in ok if isinstance(r.get("prompt_tokens_per_s"), (int, float))]
    response_tps = [r["response_tokens_per_s"] for r in ok if isinstance(r.get("response_tokens_per_s"), (int, float))]
    accept = [r["draft_accept_rate"] for r in ok if isinstance(r.get("draft_accept_rate"), (int, float))]
    fmt = [r["score"]["format_score"] for r in ok if "score" in r]
    qual = [r["score"]["quality_score"] for r in ok if "score" in r]
    cache_cases = [r for r in ok if r["case_id"].startswith("long_context_marker")]
    warm_speedup = None
    if len(cache_cases) >= 2 and cache_cases[0].get("elapsed_s") and cache_cases[1].get("elapsed_s"):
        warm_speedup = cache_cases[0]["elapsed_s"] / cache_cases[1]["elapsed_s"]
    return {
        "id": config["id"],
        "category": config.get("category"),
        "ctx": config["ctx"],
        "kv": config["kv"],
        "spec": config["spec"],
        "case_count": len(results),
        "ok_count": len(ok),
        "error_count": len(results) - len(ok),
        "think_leak_count": sum(1 for r in ok if r.get("think_leak")),
        "avg_decode_tokens_per_s": avg(decode),
        "max_decode_tokens_per_s": max(decode, default=None),
        "avg_response_tokens_per_s": avg(response_tps),
        "avg_prompt_tokens_per_s": avg(prompt),
        "avg_draft_accept_rate": avg(accept),
        "avg_format_score": avg(fmt),
        "avg_quality_score": avg(qual),
        "long_context_warm_speedup": warm_speedup,
        "gpu_summary": gpu_summary,
    }


def avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def run_config(config: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    config_id = config["id"]
    log_dir = out_dir / "server_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{config_id}.out.log"
    stderr_path = log_dir / f"{config_id}.err.log"
    cmd = build_server_cmd(config)
    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")

    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        started = time.perf_counter()
        proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, env=env)
        sampler = GpuSampler()
        sampler.start()
        results: list[dict[str, Any]] = []
        summary: dict[str, Any]
        try:
            models = wait_ready()
            startup_s = time.perf_counter() - started
            stream_result = run_stream_ttft(config_id)
            stream_result["score"] = {"format_score": 5.0 if stream_result.get("content", "").strip() == "OK" else 2.0, "quality_score": 5.0 if stream_result.get("content", "").strip() == "OK" else 2.0, "notes": []}
            results.append(stream_result)
            for case in build_cases(config):
                result = run_chat(config_id, case["case_id"], case["prompt"], case["max_tokens"])
                result["score"] = score_case(result, case)
                result["kind"] = case["kind"]
                results.append(result)
                print(json.dumps({
                    "config": config_id,
                    "case": result["case_id"],
                    "ok": result["ok"],
                    "elapsed_s": result.get("elapsed_s"),
                    "decode_tps": result.get("decode_tokens_per_s"),
                    "draft_accept": result.get("draft_accept_rate"),
                    "format": result["score"]["format_score"],
                    "quality": result["score"]["quality_score"],
                }, ensure_ascii=False), flush=True)
            gpu_summary = sampler.stop()
            summary = summarize_config(config, results, gpu_summary)
            summary["startup_s"] = startup_s
            summary["models"] = models
            summary["server_cmd"] = cmd
        except Exception as exc:  # noqa: BLE001
            gpu_summary = sampler.stop()
            summary = {
                "id": config_id,
                "category": config.get("category"),
                "ctx": config["ctx"],
                "kv": config["kv"],
                "spec": config["spec"],
                "startup_or_suite_error": repr(exc),
                "server_cmd": cmd,
                "gpu_summary": gpu_summary,
            }
        finally:
            stop_process(proc)
            time.sleep(5)

    raw_path = out_dir / f"{config_id}.json"
    raw_path.write_text(json.dumps({"config": config, "summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/home/hhtele/qwen36-mtp-pr22673-deep-20260517/results")
    parser.add_argument("--only", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    wanted = {item.strip() for item in args.only.split(",") if item.strip()}
    selected = [config for config in CONFIGS if not wanted or config["id"] in wanted]
    all_summaries = []
    for config in selected:
        print(f"=== RUN {config['id']} ===", flush=True)
        summary = run_config(config, out_dir)
        all_summaries.append(summary)
        (out_dir / "summary.json").write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()

