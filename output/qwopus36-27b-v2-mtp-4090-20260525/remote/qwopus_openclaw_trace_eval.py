#!/usr/bin/env python3
"""Focused OpenClaw agent trace evaluation for Qwopus MTP on RTX 4090."""

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
OUT_DIR = RUN_DIR / "trace-results"
BIN = "/home/hhtele/llama.cpp-master-qwopus-20260525/build/bin/llama-server"
QWEN_MODEL = "/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf"
QWOPUS_MODEL = "/data/models/qwen/qwopus/Qwopus3.6-27B-v2-MTP-Q4_K_M.gguf"
BASE_URL = "http://127.0.0.1:19343"
PORT = "19343"


def cfg(cid: str, model: str, label: str, spec_n: int, p_min: float) -> dict[str, Any]:
    return {
        "id": cid,
        "model": model,
        "label": label,
        "ctx": 131072,
        "spec_n": spec_n,
        "p_min": p_min,
    }


CONFIGS = [
    cfg("qwen_udq4xl_n4_p075_openclaw_trace_ctx128", QWEN_MODEL, "qwen_udq4xl", 4, 0.75),
    cfg("qwopus_q4km_n2_p075_openclaw_trace_ctx128", QWOPUS_MODEL, "qwopus_q4km_stable", 2, 0.75),
    cfg("qwopus_q4km_n4_p000_openclaw_trace_ctx128", QWOPUS_MODEL, "qwopus_q4km_fast_p000", 4, 0.0),
]


def system_msg() -> dict[str, str]:
    return {
        "role": "system",
        "content": (
            "You are OpenClaw's local coding agent model. Output must follow the user's exact contract. "
            "Never reveal hidden reasoning. Do not use markdown fences unless explicitly requested."
        ),
    }


def server_cmd(conf: dict[str, Any]) -> list[str]:
    return [
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
        "--cache-reuse",
        "256",
        "--slot-prompt-similarity",
        "0.10",
        "--host",
        "127.0.0.1",
        "--port",
        PORT,
        "--spec-type",
        "draft-mtp",
        "--spec-draft-n-max",
        str(conf["spec_n"]),
        "--spec-draft-p-min",
        str(conf["p_min"]),
    ]


def json_request(payload: dict[str, Any], timeout: int = 1800) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str, timeout: int = 5) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_ready(timeout_s: int = 900) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        try:
            models = get_json(f"{BASE_URL}/v1/models")
            if "data" in models or "models" in models:
                return models
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
        time.sleep(2)
    raise RuntimeError(f"server not ready: {last_error}")


def extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    return ((choices[0].get("message") or {}).get("content") or "")


def chat(conf: dict[str, Any], case_id: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
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
        response = json_request(payload)
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
    prompt_tokens = usage.get("prompt_tokens") or 0
    prompt_ms = timings.get("prompt_ms") or 0
    predicted_ms = timings.get("predicted_ms") or 0
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
        "markdown_fence": "```" in content,
        "content": content,
        "content_prefix": content[:900],
        "usage": usage,
        "timings": timings,
        "error": error,
        "raw_error_body": response.get("body") if isinstance(response, dict) else None,
    }


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


def stop_process(proc: subprocess.Popen[Any] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def long_repo_context(blocks: int = 1300) -> str:
    parts = []
    for i in range(blocks):
        parts.append(
            f"TRACE_BLOCK_{i:05d}: file=apps/game-runtime/src/runtime/GameRuntimeServer.ts; "
            "protocol=session.start,god.send,build.request,agent.pause,agent.resume; "
            "rules=strict-json,no-markdown,atomic-content-store,deterministic-seed; "
            "recent-error=invalid_agent_output_due_to_markdown_fence; "
            "expected-fix=preserve schema and retry once; "
            "cache-key=OpenClawTraceCacheStablePrefix."
        )
    return "\n".join(parts)


BASE_HISTORY = long_repo_context()


def suite_multi_turn_json_tools(conf: dict[str, Any]) -> list[dict[str, Any]]:
    messages = [
        system_msg(),
        {
            "role": "user",
            "content": (
                "We are driving OpenClaw. For each request, return only minified JSON with keys "
                "tool,args,risk,expected. Do not add text."
            ),
        },
        {"role": "assistant", "content": '{"tool":"ack","args":{},"risk":"low","expected":"ready"}'},
    ]
    tasks = [
        ("inspect runtime config", "read_file", "apps/game-runtime/src/runtime/config.ts"),
        ("patch retry prompt", "edit_file", "apps/game-runtime/src/runtime/prompting.ts"),
        ("run focused tests", "run_shell", "pnpm test -- agentOutput"),
        ("summarize replay issue", "read_file", "data/replay/latest.jsonl"),
        ("prepare final report", "write_report", "output/openclaw/report.md"),
        ("decide deployment", "final_decision", "qwen-vs-qwopus"),
    ]
    results = []
    for idx, (task, tool, target) in enumerate(tasks, 1):
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Step {idx}: {task}. Use tool={tool}. target={target}. "
                    "Return valid minified JSON only."
                ),
            }
        )
        result = chat(conf, f"multi_turn_json_tool_{idx}", messages, 220)
        result["score"] = score_json_tool(result, expected_tool=tool)
        results.append(result)
        if result["ok"] and result["content"].strip().startswith("{"):
            messages.append({"role": "assistant", "content": result["content"].strip()})
        else:
            messages.append({"role": "assistant", "content": '{"tool":"format_error","args":{},"risk":"high","expected":"retry"}'})
    return results


def suite_patch_review(conf: dict[str, Any]) -> list[dict[str, Any]]:
    diff = """diff --git a/apps/game-runtime/src/runtime/GameRuntimeServer.ts b/apps/game-runtime/src/runtime/GameRuntimeServer.ts
@@
-      const output = JSON.parse(text);
-      await this.applyAction(output.action);
+      const output = JSON.parse(text);
+      setTimeout(() => this.applyAction(output.action), 0);
+      return true;
diff --git a/packages/protocol/src/messages.ts b/packages/protocol/src/messages.ts
@@
-export const runtimeProtocolVersion = 'v1';
+export const runtimeProtocolVersion = 'v2';
"""
    base = [
        system_msg(),
        {
            "role": "user",
            "content": (
                "You are reviewing an OpenClaw runtime patch. First answer: return only minified JSON "
                "with keys findings,verdict,tests. findings must mention async ordering and protocol compatibility if present.\n\n"
                + diff
            ),
        },
    ]
    first = chat(conf, "patch_review_findings_json", base, 700)
    first["score"] = score_patch_review_json(first)
    followup = base + [
        {"role": "assistant", "content": first["content"] if first["ok"] else "{}"},
        {
            "role": "user",
            "content": (
                "Now return only a unified diff patch that removes the async setTimeout change and restores protocol v1. "
                "No markdown fence."
            ),
        },
    ]
    second = chat(conf, "patch_review_fix_diff", followup, 700)
    second["score"] = score_patch_diff(second)
    tests = followup + [
        {"role": "assistant", "content": second["content"] if second["ok"] else ""},
        {"role": "user", "content": "Return only minified JSON with keys test_commands and risk after this fix."},
    ]
    third = chat(conf, "patch_review_test_plan_json", tests, 300)
    third["score"] = score_test_plan_json(third)
    return [first, second, third]


def suite_long_history_incremental_cache(conf: dict[str, Any]) -> list[dict[str, Any]]:
    marker = f"OPENCLAW_INCREMENTAL_MARKER_{conf['label']}"
    prefix = (
        "Long OpenClaw trace follows. It is stable across calls and should be cache-reused. "
        "Return only minified JSON with keys marker,turn,decision. marker must equal the exact marker.\n\n"
        f"{BASE_HISTORY}\n\nEXACT_MARKER={marker}\n"
    )
    results = []
    for turn in range(1, 5):
        user = (
            prefix
            + f"\nNEW_INCREMENTAL_EVENT_{turn}: runtime observed build.request queue depth {turn}; "
            f"agent patch id patch-{turn:03d}; decide whether to continue.\n"
            + "Return only minified JSON now."
        )
        result = chat(conf, f"long_history_incremental_cache_turn_{turn}", [system_msg(), {"role": "user", "content": user}], 180)
        result["score"] = score_marker_json(result, marker)
        results.append(result)
    return results


def suite_repeated_similar_cache(conf: dict[str, Any]) -> list[dict[str, Any]]:
    marker = f"OPENCLAW_REPEATED_SIMILAR_{conf['label']}"
    shared = (
        "Stable OpenClaw agent trace for prompt-cache reuse measurement. "
        "Return only minified JSON with keys marker,case,action. "
        f"marker must be {marker}.\n\n{BASE_HISTORY}\n\n"
    )
    results = []
    for idx in range(1, 6):
        user = shared + f"Small delta: inspect file chunk {idx} and choose action continue."
        result = chat(conf, f"repeated_similar_prompt_cache_{idx}", [system_msg(), {"role": "user", "content": user}], 180)
        result["score"] = score_marker_json(result, marker)
        results.append(result)
    return results


def suite_devops_runbook(conf: dict[str, Any]) -> list[dict[str, Any]]:
    user = (
        "Return a concise DevOps incident runbook for this OpenClaw issue in Chinese. "
        "Context: llama-server behind token-gated NGINX, 18343 backend, 28343 public local proxy, "
        "systemd service openclaw-qwen36-mtp4-128k.service, symptom: JSON tool calls intermittently fail "
        "after long-context cache warm-up. Include checks for service state, nginx auth, llama-server logs, "
        "prompt cache reuse, and rollback. No markdown table."
    )
    result = chat(conf, "devops_incident_runbook_cn", [system_msg(), {"role": "user", "content": user}], 900)
    result["score"] = score_devops_runbook(result)
    return [result]


def score_json_tool(result: dict[str, Any], expected_tool: str) -> dict[str, Any]:
    notes: list[str] = []
    content = result.get("content", "").strip()
    if result.get("think_leak"):
        notes.append("think leak")
    if result.get("markdown_fence"):
        notes.append("markdown fence")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"format_score": 1.0, "quality_score": 2.0, "notes": notes + ["invalid json"]}
    has_keys = {"tool", "args", "risk", "expected"}.issubset(parsed.keys())
    tool_ok = parsed.get("tool") == expected_tool
    return {
        "format_score": 5.0 if has_keys and not notes else 3.0,
        "quality_score": 5.0 if has_keys and tool_ok else 3.5 if has_keys else 2.0,
        "notes": notes + ([] if tool_ok else [f"tool mismatch: {parsed.get('tool')} != {expected_tool}"]),
    }


def score_patch_review_json(result: dict[str, Any]) -> dict[str, Any]:
    notes: list[str] = []
    content = result.get("content", "").strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"format_score": 1.0, "quality_score": 2.0, "notes": ["invalid json"]}
    text = json.dumps(parsed, ensure_ascii=False)
    found_async = any(term in text for term in ["setTimeout", "async", "ordering", "顺序", "异步"])
    found_protocol = any(term in text for term in ["protocol", "v1", "v2", "兼容"])
    has_keys = {"findings", "verdict", "tests"}.issubset(parsed.keys())
    return {
        "format_score": 5.0 if has_keys else 3.0,
        "quality_score": 5.0 if found_async and found_protocol else 3.5,
        "notes": notes if found_async and found_protocol else ["missed async or protocol risk"],
    }


def score_patch_diff(result: dict[str, Any]) -> dict[str, Any]:
    content = result.get("content", "")
    notes: list[str] = []
    has_diff = "--- " in content and "+++ " in content and "@@" in content
    fixes_async = "setTimeout" in content and "-      setTimeout" in content
    fixes_protocol = "runtimeProtocolVersion" in content and "'v1'" in content
    if "```" in content:
        notes.append("markdown fence")
    return {
        "format_score": 5.0 if has_diff and not notes else 2.5 if has_diff else 1.0,
        "quality_score": 5.0 if fixes_async and fixes_protocol else 3.0,
        "notes": notes + ([] if fixes_async and fixes_protocol else ["missing expected fix hunk"]),
    }


def score_test_plan_json(result: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = json.loads(result.get("content", "").strip())
    except json.JSONDecodeError:
        return {"format_score": 1.0, "quality_score": 2.0, "notes": ["invalid json"]}
    text = json.dumps(parsed, ensure_ascii=False)
    has_tests = "pnpm" in text or "test" in text
    has_risk = "risk" in parsed
    return {
        "format_score": 5.0 if {"test_commands", "risk"}.issubset(parsed.keys()) else 3.0,
        "quality_score": 5.0 if has_tests and has_risk else 3.0,
        "notes": [] if has_tests and has_risk else ["weak test plan"],
    }


def score_marker_json(result: dict[str, Any], marker: str) -> dict[str, Any]:
    try:
        parsed = json.loads(result.get("content", "").strip())
    except json.JSONDecodeError:
        return {"format_score": 1.0, "quality_score": 2.0, "notes": ["invalid json"]}
    marker_ok = parsed.get("marker") == marker
    return {
        "format_score": 5.0 if {"marker"}.issubset(parsed.keys()) else 3.0,
        "quality_score": 5.0 if marker_ok else 2.0,
        "notes": [] if marker_ok else [f"marker mismatch: {parsed.get('marker')}"],
    }


def score_devops_runbook(result: dict[str, Any]) -> dict[str, Any]:
    content = result.get("content", "")
    checks = ["systemctl", "nginx", "18343", "28343", "cache", "rollback"]
    hit = sum(1 for term in checks if term.lower() in content.lower())
    return {
        "format_score": 4.5 if 200 <= len(content) <= 2600 and "```" not in content else 3.0,
        "quality_score": 5.0 if hit >= 5 else 3.5,
        "notes": [] if hit >= 5 else [f"missing runbook checks: {hit}/6"],
    }


def avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarize(conf: dict[str, Any], results: list[dict[str, Any]], gpu: dict[str, Any], startup_s: float, models: dict[str, Any]) -> dict[str, Any]:
    ok = [r for r in results if r.get("ok")]
    fmt = [r["score"]["format_score"] for r in ok if r.get("score")]
    qual = [r["score"]["quality_score"] for r in ok if r.get("score")]
    decode = [r["decode_tokens_per_s"] for r in ok if isinstance(r.get("decode_tokens_per_s"), (int, float))]
    accept = [r["draft_accept_rate"] for r in ok if isinstance(r.get("draft_accept_rate"), (int, float))]
    response = [r["response_tokens_per_s"] for r in ok if isinstance(r.get("response_tokens_per_s"), (int, float))]
    strict = [r for r in ok if any(key in r["case_id"] for key in ["json", "diff", "tool"])]
    cache_cases = [r for r in ok if "cache" in r["case_id"]]
    cache_warm = [r for r in cache_cases if isinstance(r.get("cache_n"), int) and r.get("cache_n", 0) > 0]
    cache_ratios = [
        r["cache_n"] / r["prompt_tokens"]
        for r in cache_warm
        if isinstance(r.get("cache_n"), int) and isinstance(r.get("prompt_tokens"), int) and r["prompt_tokens"] > 0
    ]
    first_cache = next((r for r in cache_cases if r["case_id"].endswith("_1") or r["case_id"].endswith("turn_1")), None)
    later_cache = [r for r in cache_cases if r is not first_cache]
    return {
        "id": conf["id"],
        "label": conf["label"],
        "ctx": conf["ctx"],
        "spec_n": conf["spec_n"],
        "p_min": conf["p_min"],
        "case_count": len(results),
        "ok_count": len(ok),
        "error_count": len(results) - len(ok),
        "strict_format_pass_count": sum(1 for r in strict if r.get("score", {}).get("format_score") == 5.0),
        "strict_case_count": len(strict),
        "avg_format_score": avg(fmt),
        "avg_quality_score": avg(qual),
        "avg_decode_tokens_per_s": avg(decode),
        "avg_response_tokens_per_s": avg(response),
        "avg_draft_accept_rate": avg(accept),
        "cache_case_count": len(cache_cases),
        "cache_warm_case_count": len(cache_warm),
        "avg_cache_ratio_when_warm": avg(cache_ratios),
        "first_cache_prompt_ms": first_cache.get("prompt_ms") if first_cache else None,
        "avg_later_cache_prompt_ms": avg([r["prompt_ms"] for r in later_cache if isinstance(r.get("prompt_ms"), (int, float))]),
        "max_memory_used_mib": gpu.get("max_memory_used_mib"),
        "max_power_w": gpu.get("max_power_w"),
        "max_temperature_c": gpu.get("max_temperature_c"),
        "startup_s": startup_s,
        "models": models,
        "server_cmd": server_cmd(conf),
    }


def run_config(conf: dict[str, Any]) -> dict[str, Any]:
    cid = conf["id"]
    log_dir = OUT_DIR / "server_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")
    results: list[dict[str, Any]] = []
    with (log_dir / f"{cid}.out.log").open("wb") as stdout, (log_dir / f"{cid}.err.log").open("wb") as stderr:
        proc = subprocess.Popen(server_cmd(conf), stdout=stdout, stderr=stderr, env=env)
        sampler = GpuSampler()
        sampler.start()
        started = time.perf_counter()
        try:
            models = wait_ready()
            startup_s = time.perf_counter() - started
            suites = [
                ("multi_turn_json_tools", suite_multi_turn_json_tools),
                ("patch_review", suite_patch_review),
                ("long_history_incremental_cache", suite_long_history_incremental_cache),
                ("repeated_similar_cache", suite_repeated_similar_cache),
                ("devops_runbook", suite_devops_runbook),
            ]
            for suite_name, suite_fn in suites:
                for result in suite_fn(conf):
                    result["suite"] = suite_name
                    results.append(result)
                    print(
                        json.dumps(
                            {
                                "config": cid,
                                "suite": suite_name,
                                "case": result["case_id"],
                                "ok": result.get("ok"),
                                "elapsed_s": result.get("elapsed_s"),
                                "prompt_tokens": result.get("prompt_tokens"),
                                "completion_tokens": result.get("completion_tokens"),
                                "decode_tps": result.get("decode_tokens_per_s"),
                                "accept": result.get("draft_accept_rate"),
                                "cache_n": result.get("cache_n"),
                                "prompt_ms": result.get("prompt_ms"),
                                "format": result.get("score", {}).get("format_score"),
                                "quality": result.get("score", {}).get("quality_score"),
                                "notes": result.get("score", {}).get("notes", []),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
            gpu = sampler.stop()
            summary = summarize(conf, results, gpu, startup_s, models)
        except Exception as exc:  # noqa: BLE001
            gpu = sampler.stop()
            summary = {
                "id": cid,
                "startup_or_suite_error": repr(exc),
                "gpu_summary": gpu,
                "server_cmd": server_cmd(conf),
            }
        finally:
            stop_process(proc)
            time.sleep(5)
    (OUT_DIR / f"{cid}.json").write_text(json.dumps({"config": conf, "summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for conf in CONFIGS:
        print(f"=== TRACE RUN {conf['id']} ===", flush=True)
        summary = run_config(conf)
        summaries.append(summary)
        (OUT_DIR / "summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(json.dumps({"done": True, "configs": [c["id"] for c in CONFIGS]}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
