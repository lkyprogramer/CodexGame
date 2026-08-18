#!/usr/bin/env python3
"""Qwopus3.6 27B MTP Q4_K_M evaluation on RTX 4090."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


RUN_DIR = Path("/home/hhtele/qwopus36-27b-v2-mtp-4090-20260525")
BIN = "/home/hhtele/llama.cpp-master-qwopus-20260525/build/bin/llama-server"
QWEN_MODEL = "/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf"
QWOPUS_MODEL = "/data/models/qwen/qwopus/Qwopus3.6-27B-v2-MTP-Q4_K_M.gguf"
BASE_URL = "http://127.0.0.1:19343"
PORT = "19343"


def config(
    cid: str,
    model: str,
    model_label: str,
    ctx: int,
    spec_n: int | None,
    p_min: float | None = 0.75,
    phase: str = "phase1",
    long_tokens: int = 512,
    marker_words: int = 0,
) -> dict[str, Any]:
    return {
        "id": cid,
        "model": model,
        "model_label": model_label,
        "ctx": ctx,
        "spec_n": spec_n,
        "p_min": p_min,
        "phase": phase,
        "long_tokens": long_tokens,
        "marker_words": marker_words,
    }


PHASE0 = [
    config("qwen_udq4xl_draft_n2_p075_ctx32", QWEN_MODEL, "qwen_udq4xl", 32768, 2, phase="phase0"),
    config("qwen_udq4xl_draft_n4_p075_ctx32", QWEN_MODEL, "qwen_udq4xl", 32768, 4, phase="phase0"),
]

PHASE1 = [
    config("qwopus_q4km_no_spec_ctx32", QWOPUS_MODEL, "qwopus_q4km", 32768, None, None, "phase1"),
    config("qwopus_q4km_draft_n1_p075_ctx32", QWOPUS_MODEL, "qwopus_q4km", 32768, 1, 0.75, "phase1"),
    config("qwopus_q4km_draft_n2_p075_ctx32", QWOPUS_MODEL, "qwopus_q4km", 32768, 2, 0.75, "phase1"),
    config("qwopus_q4km_draft_n3_p075_ctx32", QWOPUS_MODEL, "qwopus_q4km", 32768, 3, 0.75, "phase1"),
    config("qwopus_q4km_draft_n4_p075_ctx32", QWOPUS_MODEL, "qwopus_q4km", 32768, 4, 0.75, "phase1"),
    config("qwopus_q4km_draft_n6_p075_ctx32", QWOPUS_MODEL, "qwopus_q4km", 32768, 6, 0.75, "phase1"),
    config("qwopus_q4km_draft_n4_p000_ctx32", QWOPUS_MODEL, "qwopus_q4km", 32768, 4, 0.0, "phase1"),
]


def phase2_qwen() -> list[dict[str, Any]]:
    return [
        config("qwen_udq4xl_draft_n2_p075_ctx128", QWEN_MODEL, "qwen_udq4xl", 131072, 2, 0.75, "phase2", 2048, 1600),
        config("qwen_udq4xl_draft_n4_p075_ctx128", QWEN_MODEL, "qwen_udq4xl", 131072, 4, 0.75, "phase2", 2048, 1600),
    ]


def phase2_qwopus(src: dict[str, Any]) -> dict[str, Any]:
    suffix = src["id"].replace("qwopus_q4km_", "").replace("_ctx32", "_ctx128")
    return config(
        f"qwopus_q4km_{suffix}",
        QWOPUS_MODEL,
        "qwopus_q4km",
        131072,
        src["spec_n"],
        src["p_min"],
        "phase2",
        2048,
        1600,
    )


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


def wait_ready(timeout_s: int = 900) -> dict[str, Any]:
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
        nums = lambda key: [s.get(key) for s in self.samples if isinstance(s.get(key), (int, float))]
        return {
            "sample_count": len(self.samples),
            "max_memory_used_mib": max(nums("memory_used_mib"), default=None),
            "max_power_w": max(nums("power_w"), default=None),
            "max_utilization_gpu_pct": max(nums("utilization_gpu_pct"), default=None),
            "last": self.samples[-1] if self.samples else None,
        }

    def _run(self) -> None:
        while not self._stop.is_set():
            sample = nvidia_query()
            sample["ts"] = time.time()
            self.samples.append(sample)
            time.sleep(1)


def server_cmd(conf: dict[str, Any]) -> list[str]:
    cmd = [
        BIN,
        "-m",
        conf["model"],
        "--alias",
        f"openclaw/{conf['id']}",
        "-ngl",
        "99",
        "-c",
        str(conf["ctx"]),
        "-np",
        "1",
        "-fa",
        "on",
        "-ctk",
        "q4_0",
        "-ctv",
        "q4_0",
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
    if conf["ctx"] >= 131072:
        cmd.extend(["--cache-reuse", "256", "--slot-prompt-similarity", "0.10"])
    if conf["spec_n"] is not None:
        cmd.extend(["--spec-type", "draft-mtp", "--spec-draft-n-max", str(conf["spec_n"])])
        if conf["p_min"] is not None:
            cmd.extend(["--spec-draft-p-min", str(conf["p_min"])])
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


def system_msg() -> dict[str, str]:
    return {
        "role": "system",
        "content": (
            "You are OpenClaw's local coding agent model. Follow exact output format requirements. "
            "Do not use markdown fences unless explicitly requested."
        ),
    }


def run_chat(conf: dict[str, Any], case_id: str, messages: list[dict[str, str]], max_tokens: int, timeout: int = 1800) -> dict[str, Any]:
    payload = {
        "model": f"openclaw/{conf['id']}",
        "messages": messages,
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
        "empty_output": ok and not content.strip(),
        "slash_repetition": content.strip().startswith("/") and len(set(content.strip()[:80])) <= 2,
        "content": content,
        "content_prefix": content[:700],
        "usage": usage,
        "timings": timings,
        "error": error,
        "raw_error_body": response.get("body") if isinstance(response, dict) else None,
    }


def run_stream_ttft(conf: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": f"openclaw/{conf['id']}",
        "messages": [system_msg(), {"role": "user", "content": "Reply with OK only."}],
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
                piece = (choices[0].get("delta") or {}).get("content") or ""
                if piece and first_token_s is None:
                    first_token_s = time.perf_counter() - started
                if piece:
                    content_parts.append(piece)
        content = "".join(content_parts)
        return {
            "case_id": "stream_ttft_ok",
            "ok": True,
            "elapsed_s": time.perf_counter() - started,
            "ttft_s": first_token_s,
            "content": content,
            "content_prefix": content[:200],
            "score": score_short(content),
            "empty_output": not content.strip(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "case_id": "stream_ttft_ok",
            "ok": False,
            "elapsed_s": time.perf_counter() - started,
            "ttft_s": first_token_s,
            "content": "".join(content_parts),
            "error": repr(exc),
            "score": {"format_score": 0.0, "quality_score": 0.0, "notes": ["request failed"]},
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


def history_messages() -> list[dict[str, str]]:
    return [
        system_msg(),
        {"role": "user", "content": "Tool failed because JSON was wrapped in markdown. Diagnose briefly."},
        {
            "role": "assistant",
            "content": "<think>\nThe next answer must be raw JSON only.\n</think>\nThe output violated the JSON-only contract.",
        },
        {
            "role": "user",
            "content": "Return only minified JSON with keys cause,next_patch,test.",
        },
    ]


def cases_for(conf: dict[str, Any]) -> list[dict[str, Any]]:
    base = [system_msg()]
    long_tokens = int(conf.get("long_tokens", 512))
    cases = [
        {"case_id": "short_ok", "messages": base + [{"role": "user", "content": "Reply with OK only."}], "max_tokens": 8, "kind": "short"},
        {
            "case_id": "json_tool",
            "messages": base
            + [
                {
                    "role": "user",
                    "content": (
                        "Return only valid minified JSON for a coding agent tool call with keys "
                        "action,file,risk,tests. Use action=\"edit\", file=\"apps/game-runtime/src/runtime/GameRuntimeServer.ts\", "
                        "risk=\"low\", tests=[\"pnpm test\"]. No markdown."
                    ),
                }
            ],
            "max_tokens": 160,
            "kind": "json",
        },
        {
            "case_id": "patch_unified_diff",
            "messages": base
            + [
                {
                    "role": "user",
                    "content": (
                        "Return only a unified diff patch. No markdown fence.\n"
                        "File: src/score.ts\n"
                        "Current content:\n"
                        "export function formatScore(value: number | null): string {\n"
                        "  return String(value);\n"
                        "}\n"
                        "Required change: null must return \"N/A\" and numbers must return value.toFixed(2)."
                    ),
                }
            ],
            "max_tokens": 512,
            "kind": "patch",
        },
        {
            "case_id": "code_review_cn",
            "messages": base
            + [
                {
                    "role": "user",
                    "content": (
                        "用中文做一次简短 code review，只列出最重要的问题。代码：\n"
                        "async function save(items) { items.forEach(async item => { await db.insert(item); }); return true; }\n"
                        "要求：不要泛泛而谈，指出并发/一致性/错误传播问题。"
                    ),
                }
            ],
            "max_tokens": 512,
            "kind": "review",
        },
        {"case_id": "agent_history_json", "messages": history_messages(), "max_tokens": 220, "kind": "agent_history_json"},
        {
            "case_id": f"long_generation_{long_tokens}",
            "messages": base
            + [
                {
                    "role": "user",
                    "content": (
                        "Write a dense benchmark analysis for a local coding agent model on RTX 4090. Cover MTP speculative "
                        "decoding, prompt cache, long-context prefill, JSON/tool formatting, patch generation, and quality tradeoffs. "
                        "Keep writing until the token budget is nearly exhausted. No markdown tables."
                    ),
                }
            ],
            "max_tokens": long_tokens,
            "kind": "long_generation",
        },
    ]
    if conf["phase"] == "phase2":
        cases.append(
            {
                "case_id": "long_generation_1024",
                "messages": base
                + [
                    {
                        "role": "user",
                        "content": (
                            "Write a practical OpenClaw deployment evaluation. Compare candidate model risks, strict JSON behavior, "
                            "patch generation quality, long-context prompt cache, and speculative decoding acceptance. No markdown tables."
                        ),
                    }
                ],
                "max_tokens": 1024,
                "kind": "long_generation",
            }
        )
    marker_words = int(conf.get("marker_words") or 0)
    if marker_words:
        marker = f"OPENCLAW_QWOPUS_{conf['id']}".replace("-", "_")
        prompt = marker_prompt(marker_words, marker)
        cases.extend(
            [
                {"case_id": "long_context_marker_cold", "messages": base + [{"role": "user", "content": prompt}], "max_tokens": 48, "kind": "long_context_marker", "expected": marker},
                {"case_id": "long_context_marker_warm", "messages": base + [{"role": "user", "content": prompt}], "max_tokens": 48, "kind": "long_context_marker", "expected": marker},
            ]
        )
    return cases


def score_short(content: str) -> dict[str, Any]:
    stripped = content.strip()
    fmt = 5.0 if stripped == "OK" else 3.0 if "OK" in stripped else 1.0
    return {"format_score": fmt, "quality_score": fmt, "notes": [] if fmt == 5.0 else ["not exact OK"]}


def score_case(result: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    content = result.get("content") or ""
    if not result.get("ok"):
        return {"format_score": 0.0, "quality_score": 0.0, "notes": ["request failed"]}
    notes: list[str] = []
    if result.get("think_leak"):
        notes.append("think leak")
    if result.get("empty_output"):
        notes.append("empty output")
    if result.get("slash_repetition"):
        notes.append("slash repetition")
    kind = case["kind"]
    stripped = content.strip()
    fmt = 0.0
    quality = 0.0
    if kind == "short":
        return score_short(content)
    if kind == "json":
        try:
            parsed = json.loads(stripped)
            fmt = 5.0
            quality = 5.0 if {"action", "file", "risk", "tests"}.issubset(parsed.keys()) else 3.5
        except json.JSONDecodeError:
            fmt, quality = 1.0, 2.0
            notes.append("invalid json")
    elif kind == "agent_history_json":
        try:
            parsed = json.loads(stripped)
            fmt = 5.0
            quality = 5.0 if {"cause", "next_patch", "test"}.issubset(parsed.keys()) else 3.5
        except json.JSONDecodeError:
            fmt, quality = 1.0, 2.0
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
        fmt = 4.5 if 20 <= len(content) < 1400 else 2.0
        quality = 4.5 if has_issue else 2.5
    elif kind == "long_generation":
        target = int(case["max_tokens"] * 0.70)
        fmt = 4.5 if not result.get("think_leak") and not result.get("empty_output") else 2.0
        quality = 4.0 if result.get("completion_tokens", 0) >= target else 3.0
    elif kind == "long_context_marker":
        exact = stripped == case.get("expected")
        fmt = 5.0 if exact else 1.0
        quality = 5.0 if exact else 1.0
        if not exact:
            notes.append("marker mismatch")
    if result.get("think_leak") or result.get("empty_output") or result.get("slash_repetition"):
        fmt = min(fmt, 2.0)
        quality = min(quality, 3.0)
    return {"format_score": fmt, "quality_score": quality, "notes": notes}


def avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(conf: dict[str, Any], results: list[dict[str, Any]], gpu: dict[str, Any], startup_s: float | None, models: dict[str, Any] | None) -> dict[str, Any]:
    ok = [r for r in results if r.get("ok")]
    decode = [r["decode_tokens_per_s"] for r in ok if isinstance(r.get("decode_tokens_per_s"), (int, float))]
    response = [r["response_tokens_per_s"] for r in ok if isinstance(r.get("response_tokens_per_s"), (int, float))]
    accept = [r["draft_accept_rate"] for r in ok if isinstance(r.get("draft_accept_rate"), (int, float))]
    fmt = [r["score"]["format_score"] for r in ok if "score" in r]
    qual = [r["score"]["quality_score"] for r in ok if "score" in r]
    cold = next((r for r in ok if r["case_id"] == "long_context_marker_cold"), None)
    warm = next((r for r in ok if r["case_id"] == "long_context_marker_warm"), None)
    strict_ids = {"short_ok", "json_tool", "patch_unified_diff", "agent_history_json"}
    strict = [r for r in ok if r["case_id"] in strict_ids]
    strict_pass = all((r.get("score") or {}).get("format_score", 0) >= 5.0 for r in strict) and len(strict) == len(strict_ids)
    long_candidates = [r for r in ok if str(r["case_id"]).startswith("long_generation")]
    long_decode = [r["decode_tokens_per_s"] for r in long_candidates if isinstance(r.get("decode_tokens_per_s"), (int, float))]
    warm_speedup = None
    if cold and warm and cold.get("elapsed_s") and warm.get("elapsed_s"):
        warm_speedup = cold["elapsed_s"] / warm["elapsed_s"]
    return {
        "id": conf["id"],
        "phase": conf["phase"],
        "model_label": conf["model_label"],
        "ctx": conf["ctx"],
        "spec_n": conf["spec_n"],
        "p_min": conf["p_min"],
        "case_count": len(results),
        "ok_count": len(ok),
        "error_count": len(results) - len(ok),
        "empty_output_count": sum(1 for r in ok if r.get("empty_output")),
        "slash_repetition_count": sum(1 for r in ok if r.get("slash_repetition")),
        "think_leak_count": sum(1 for r in ok if r.get("think_leak")),
        "strict_pass": strict_pass,
        "avg_decode_tokens_per_s": avg(decode),
        "avg_response_tokens_per_s": avg(response),
        "avg_draft_accept_rate": avg(accept),
        "avg_format_score": avg(fmt),
        "avg_quality_score": avg(qual),
        "best_long_decode_tokens_per_s": max(long_decode, default=None),
        "long_context_warm_speedup": warm_speedup,
        "long_context_cold": {
            "elapsed_s": cold.get("elapsed_s") if cold else None,
            "prompt_ms": cold.get("prompt_ms") if cold else None,
            "cache_n": cold.get("cache_n") if cold else None,
            "prompt_tokens": cold.get("prompt_tokens") if cold else None,
        },
        "long_context_warm": {
            "elapsed_s": warm.get("elapsed_s") if warm else None,
            "prompt_ms": warm.get("prompt_ms") if warm else None,
            "cache_n": warm.get("cache_n") if warm else None,
            "prompt_tokens": warm.get("prompt_tokens") if warm else None,
        },
        "gpu_summary": gpu,
        "startup_s": startup_s,
        "models": models,
        "server_cmd": server_cmd(conf),
    }


def run_config(conf: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    cid = conf["id"]
    log_dir = out_dir / "server_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = server_cmd(conf)
    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")
    results: list[dict[str, Any]] = []
    with (log_dir / f"{cid}.out.log").open("wb") as stdout, (log_dir / f"{cid}.err.log").open("wb") as stderr:
        proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, env=env)
        sampler = GpuSampler()
        sampler.start()
        started = time.perf_counter()
        try:
            models = wait_ready()
            startup_s = time.perf_counter() - started
            stream = run_stream_ttft(conf)
            results.append(stream)
            for case in cases_for(conf):
                result = run_chat(conf, case["case_id"], case["messages"], case["max_tokens"])
                result["score"] = score_case(result, case)
                result["kind"] = case["kind"]
                results.append(result)
                print(json.dumps({
                    "config": cid,
                    "case": result["case_id"],
                    "ok": result.get("ok"),
                    "elapsed_s": result.get("elapsed_s"),
                    "decode_tps": result.get("decode_tokens_per_s"),
                    "accept": result.get("draft_accept_rate"),
                    "cache_n": result.get("cache_n"),
                    "format": result["score"]["format_score"],
                    "quality": result["score"]["quality_score"],
                    "notes": result["score"].get("notes", []),
                }, ensure_ascii=False), flush=True)
            gpu = sampler.stop()
            summary = summarize(conf, results, gpu, startup_s, models)
        except Exception as exc:  # noqa: BLE001
            gpu = sampler.stop()
            summary = {
                "id": cid,
                "phase": conf["phase"],
                "model_label": conf["model_label"],
                "ctx": conf["ctx"],
                "spec_n": conf["spec_n"],
                "p_min": conf["p_min"],
                "startup_or_suite_error": repr(exc),
                "gpu_summary": gpu,
                "server_cmd": cmd,
            }
        finally:
            stop_process(proc)
            time.sleep(5)
    (out_dir / f"{cid}.json").write_text(json.dumps({"config": conf, "summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def phase0_pass(summaries: list[dict[str, Any]]) -> bool:
    return all(
        not s.get("startup_or_suite_error")
        and s.get("error_count") == 0
        and s.get("strict_pass")
        and (s.get("avg_quality_score") or 0) >= 4.5
        and s.get("empty_output_count") == 0
        and s.get("slash_repetition_count") == 0
        for s in summaries
    )


def candidate_pass(s: dict[str, Any], qwen_long_floor: float) -> bool:
    if s.get("startup_or_suite_error") or s.get("error_count") != 0 or not s.get("strict_pass"):
        return False
    if (s.get("avg_quality_score") or 0) < 4.6:
        return False
    if s.get("spec_n") is not None and (s.get("avg_draft_accept_rate") or 0) < 0.65:
        return False
    if (s.get("best_long_decode_tokens_per_s") or 0) < qwen_long_floor * 0.95:
        return False
    if s.get("empty_output_count") or s.get("slash_repetition_count") or s.get("think_leak_count"):
        return False
    return True


def main() -> None:
    out_dir = RUN_DIR / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_summaries: list[dict[str, Any]] = []
    phase2_selected: list[str] = []

    for conf in PHASE0:
        print(f"=== RUN {conf['id']} ===", flush=True)
        summary = run_config(conf, out_dir)
        all_summaries.append(summary)
        (out_dir / "summary.json").write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if not phase0_pass(all_summaries):
        (out_dir / "gate.json").write_text(json.dumps({"phase0_pass": False, "reason": "qwen baseline failed on latest llama.cpp"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    qwen_long_floor = max((s.get("best_long_decode_tokens_per_s") or 0) for s in all_summaries if s["phase"] == "phase0")
    phase1_summaries: list[dict[str, Any]] = []
    for conf in PHASE1:
        print(f"=== RUN {conf['id']} ===", flush=True)
        summary = run_config(conf, out_dir)
        all_summaries.append(summary)
        phase1_summaries.append(summary)
        (out_dir / "summary.json").write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

    by_id = {c["id"]: c for c in PHASE1}
    candidates = [s for s in phase1_summaries if candidate_pass(s, qwen_long_floor)]
    candidates.sort(key=lambda s: ((s.get("best_long_decode_tokens_per_s") or 0), (s.get("avg_quality_score") or 0)), reverse=True)
    selected = candidates[:2]
    phase2_selected = [s["id"] for s in selected]
    (out_dir / "gate.json").write_text(json.dumps({
        "phase0_pass": True,
        "qwen_long_floor": qwen_long_floor,
        "phase1_selected_for_128k": phase2_selected,
        "phase1_candidate_count": len(candidates),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    phase2_configs = phase2_qwen() + [phase2_qwopus(by_id[s["id"]]) for s in selected]
    for conf in phase2_configs:
        print(f"=== RUN {conf['id']} ===", flush=True)
        summary = run_config(conf, out_dir)
        all_summaries.append(summary)
        (out_dir / "summary.json").write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

    print(json.dumps({"done": True, "phase2_selected": phase2_selected}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
