#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import tarfile
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT = "project-d4e4f88c-f262-47af-b5b"
ZONE = "us-central1-a"
INSTANCE = "instance-20260222-145427"
REMOTE_USER = "hhtele"
REMOTE_PASSWORD = "hhtele"
REMOTE_HOST = "100.107.189.100"

LOCAL_LUCEBOX = Path("/Users/luo/Documents/github/lucebox-hub")
REMOTE_ROOT = "/home/hhtele/lucebox-hub-main-maxperf-qwen36"
REMOTE_DFLASH = f"{REMOTE_ROOT}/dflash"
REMOTE_RESULT_BASE = "/tmp/qwen36_lucebox_fix_results"

PATCHED_FILES = [
    "dflash/test/test_dflash.cpp",
    "dflash/scripts/run.py",
    "dflash/scripts/server.py",
    "pflash/tests/bench_niah_cpp.py",
]


def run_command(cmd: list[str], *, capture: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, text=True, capture_output=capture, timeout=timeout)
    if completed.returncode != 0:
        if capture:
            if completed.stdout:
                print(completed.stdout, end="")
            if completed.stderr:
                print(completed.stderr, end="", file=os.sys.stderr)
        raise subprocess.CalledProcessError(
            completed.returncode, cmd, output=completed.stdout, stderr=completed.stderr
        )
    return completed


def gcloud_base() -> list[str]:
    return [
        "gcloud", "compute", "ssh",
        "--project", PROJECT,
        "--zone", ZONE,
        INSTANCE,
        "--tunnel-through-iap",
        "--ssh-flag=-o ServerAliveInterval=30",
        "--ssh-flag=-o ServerAliveCountMax=6",
    ]


def run_jump(command: str, *, capture: bool = True, timeout: int | None = None) -> str:
    completed = run_command(gcloud_base() + [f"--command={command}"], capture=capture, timeout=timeout)
    return completed.stdout if capture else ""


def run_remote(command: str, *, capture: bool = True, timeout: int | None = None) -> str:
    nested = "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {command}".format(
        password=shlex.quote(REMOTE_PASSWORD),
        user=REMOTE_USER,
        host=REMOTE_HOST,
        command=shlex.quote(command),
    )
    return run_jump(nested, capture=capture, timeout=timeout)


def scp_to_jump(local_path: Path, remote_path: str) -> None:
    run_command([
        "gcloud", "compute", "scp",
        "--project", PROJECT,
        "--zone", ZONE,
        "--tunnel-through-iap",
        str(local_path),
        f"{INSTANCE}:{remote_path}",
    ], capture=True, timeout=600)


def scp_from_jump(remote_path: str, local_path: Path) -> None:
    run_command([
        "gcloud", "compute", "scp",
        "--project", PROJECT,
        "--zone", ZONE,
        "--tunnel-through-iap",
        f"{INSTANCE}:{remote_path}",
        str(local_path),
    ], capture=True, timeout=1200)


def scp_text_to_remote(text: str, jump_path: str, remote_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(text)
    try:
        scp_to_jump(tmp, jump_path)
    finally:
        tmp.unlink(missing_ok=True)
    run_jump(
        "sshpass -p {password} scp -o StrictHostKeyChecking=no {jump_path} {user}@{host}:{remote_path}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            jump_path=shlex.quote(jump_path),
            user=REMOTE_USER,
            host=REMOTE_HOST,
            remote_path=shlex.quote(remote_path),
        ),
        capture=False,
        timeout=600,
    )


def sync_sources() -> None:
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as handle:
        tar_path = Path(handle.name)
    try:
        with tarfile.open(tar_path, "w") as tar:
            for rel in PATCHED_FILES:
                tar.add(LOCAL_LUCEBOX / rel, arcname=rel)
        jump_tar = "/tmp/qwen36_lucebox_fix_sources.tar"
        scp_to_jump(tar_path, jump_tar)
    finally:
        tar_path.unlink(missing_ok=True)
    run_jump(
        "sshpass -p {password} scp -o StrictHostKeyChecking=no {jump_tar} {user}@{host}:/tmp/qwen36_lucebox_fix_sources.tar && "
        "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {remote_cmd}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            jump_tar=shlex.quote(jump_tar),
            user=REMOTE_USER,
            host=REMOTE_HOST,
            remote_cmd=shlex.quote(
                "set -euo pipefail; "
                f"cd {shlex.quote(REMOTE_ROOT)}; "
                "ts=$(date +%Y%m%d-%H%M%S); "
                "mkdir -p /home/hhtele/lucebox-fix-backups/$ts; "
                "cp dflash/test/test_dflash.cpp dflash/scripts/run.py dflash/scripts/server.py "
                "pflash/tests/bench_niah_cpp.py /home/hhtele/lucebox-fix-backups/$ts/; "
                "tar -xf /tmp/qwen36_lucebox_fix_sources.tar; "
                "python3 -m py_compile dflash/scripts/run.py dflash/scripts/server.py pflash/tests/bench_niah_cpp.py; "
                "echo synced"
            ),
        ),
        capture=False,
        timeout=900,
    )


def build_remote() -> None:
    run_remote(
        "set -euo pipefail; "
        f"cd {shlex.quote(REMOTE_DFLASH)}; "
        "export PATH=/usr/local/cuda/bin:$PATH; "
        "export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}; "
        "cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89 "
        "-DDFLASH27B_ENABLE_BSA=ON -DDFLASH27B_FA_ALL_QUANTS=ON > /tmp/qwen36_fix_cmake.log 2>&1; "
        "cmake --build build --target test_dflash test_flashprefill_kernels -j "
        "> /tmp/qwen36_fix_build.log 2>&1; "
        "tail -n 80 /tmp/qwen36_fix_build.log",
        timeout=7200,
    )


REMOTE_VALIDATOR = r'''
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("/home/hhtele/lucebox-hub-main-maxperf-qwen36")
REMOTE_RESULT_BASE = "/tmp/qwen36_lucebox_fix_results"
DFLASH = ROOT / "dflash"
PFLASH = ROOT / "pflash"
PY = DFLASH / ".venv/bin/python"
if not PY.exists():
    PY = Path("python3")

TARGET = "/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf"
DRAFT = "/data/models/qwen/dflash-draft-qwen36-q8/dflash-draft-3.6-q8_0.gguf"
DRAFTER = "/data/models/qwen/Qwen3-0.6B-BF16.gguf"
TOKENIZER = str(DFLASH / "tokenizers/qwen36_27b")
DRAFTER_TOKENIZER = str(DFLASH / "tokenizers/qwen3_0p6b")
BIN = str(DFLASH / "build/test_dflash")
PASSWORD = "hhtele"
LIVE_SERVICE = "qwen35-35b-a3b-uncensored"
BENCH_SERVICE = "openclaw-executor"


def run(cmd: list[str] | str, *, cwd: Path | None = None, env: dict[str, str] | None = None,
        input_text: str | None = None, timeout: int | None = None) -> dict[str, Any]:
    shell = isinstance(cmd, str)
    started = time.time()
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        shell=shell,
        timeout=timeout,
    )
    return {
        "cmd": cmd if isinstance(cmd, str) else " ".join(cmd),
        "returncode": completed.returncode,
        "elapsed_s": time.time() - started,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def sudo(cmd: str) -> dict[str, Any]:
    wrapped = "printf '%s\n' {pw} | sudo -S -p '' bash -lc {cmd}".format(
        pw=PASSWORD,
        cmd=json.dumps(cmd),
    )
    return run(wrapped, timeout=120)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_run_stderr(stderr: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r"\[run\] prompt (\d+) tokens, streaming up to (\d+) tokens, max_ctx=(\d+)", stderr)
    if m:
        out["prompt_tokens"] = int(m.group(1))
        out["requested_gen_tokens"] = int(m.group(2))
        out["max_ctx"] = int(m.group(3))
    m = re.search(r"\[run\] generated (\d+) visible tokens \(raw=(\d+), stop_token_hit=(True|False), raw_first_token_ids=\[([^\]]*)\]\)", stderr)
    if m:
        out["visible_tokens"] = int(m.group(1))
        out["raw_tokens"] = int(m.group(2))
        out["stop_token_hit"] = m.group(3) == "True"
        ids = [x.strip() for x in m.group(4).split(",") if x.strip()]
        out["raw_first_token_ids"] = [int(x) for x in ids]
    m = re.search(r"([0-9.]+)\s+tok/s", stderr)
    if m:
        out["tok_s"] = float(m.group(1))
    return out


def parse_niah(stdout: str, stderr: str) -> dict[str, Any]:
    text = stdout + "\n" + stderr
    out: dict[str, Any] = {
        "bad_header": "bad header length" in text,
        "oom": "out of memory" in text.lower() or "cuda oom" in text.lower(),
    }
    m = re.search(r"compressed=(\d+) ratio=([0-9.]+)x score_s=([0-9.]+)", text)
    if m:
        out["compressed_tokens"] = int(m.group(1))
        out["compression_ratio"] = float(m.group(2))
        out["score_s"] = float(m.group(3))
    m = re.search(r"gen_s=([0-9.]+) ttft=([0-9.]+) ok=(True|False) ans=([0-9]+)", text)
    if m:
        out["gen_s"] = float(m.group(1))
        out["ttft_s"] = float(m.group(2))
        out["needle_hit"] = m.group(3) == "True"
        out["answer"] = m.group(4)
    m = re.search(r"accuracy:\s*(\d+)/(\d+)", text)
    if m:
        out["accuracy"] = {"correct": int(m.group(1)), "total": int(m.group(2))}
    return out


def leakage(text: str) -> bool:
    low = text.lower()
    return "<think" in low or "thinking process" in low or "we need answer" in low


def chat_template(tokenizer, messages: list[dict]) -> str:
    kwargs = {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False}
    try:
        return tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs)


def make_long_prompt(ctx: int) -> str:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TOKENIZER, trust_remote_code=True)
    target = ctx - 768
    header = (
        "You are reviewing a Java payment/order backend. The context below contains repeated "
        "service snippets, invariants, logs, and failure notes. Use the details to produce a "
        "concrete coding/agent answer. Do not answer with only a stop token.\n\n"
    )
    chunk = (
        "Module PaymentCallbackService: callback_id must be idempotent; transaction commits before "
        "outbox publish; optimistic lock version is required on order updates; Redis cache must be "
        "invalidated after database commit; partial batch import must preserve row-level errors. "
        "Observed bug: duplicate callback can publish two settlement events when retry races with "
        "manual reconciliation. Test expectation: exactly one outbox event and a conflict response "
        "for stale version updates.\n"
    )
    tail = (
        "\nTask: Start your answer with LONG_AGENT_RESULT. Identify the three highest-risk bugs, "
        "give the minimal Java/Spring patch strategy, and list focused regression tests. "
        "Return at least 8 bullet points and include one code block."
    )
    def rendered_len(text: str) -> int:
        rendered = chat_template(tok, [{"role": "user", "content": text}])
        return len(tok.encode(rendered, add_special_tokens=False))

    fixed_len = rendered_len(header + tail)
    chunk_len = max(1, len(tok.encode(chunk, add_special_tokens=False)))
    repeat = max(1, (target - fixed_len) // chunk_len)
    text = header + (chunk * repeat) + tail
    for _ in range(8):
        n_tokens = rendered_len(text)
        if target - 256 <= n_tokens <= target:
            return text
        if n_tokens < target:
            repeat += max(1, (target - n_tokens) // chunk_len)
        else:
            repeat = max(1, repeat - max(1, (n_tokens - target) // chunk_len))
        text = header + (chunk * repeat) + tail
    return text


def run_smoke(result_root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env.update({
        "DFLASH_TARGET": TARGET,
        "DFLASH_DRAFT": DRAFT,
        "DFLASH_TOKENIZER": TOKENIZER,
        "DFLASH27B_KV_TQ3": "1",
        "DFLASH27B_FA_WINDOW": "2048",
    })
    kernel = run([str(DFLASH / "build/test_flashprefill_kernels")], cwd=DFLASH, env=env, timeout=600)
    save_text(result_root / "smoke/test_flashprefill_kernels.stdout.log", kernel["stdout"])
    save_text(result_root / "smoke/test_flashprefill_kernels.stderr.log", kernel["stderr"])

    prompt = "Write a Python fibonacci function. Start with CODE_RESULT and do not include thinking text."
    one_shot = run([
        str(PY), "scripts/run.py",
        "--target", TARGET,
        "--draft", DRAFT,
        "--bin", BIN,
        "--budget", "26",
        "--n-gen", "128",
        "--kv-tq3",
        "--fa-window", "2048",
    ], cwd=DFLASH, env=env, input_text=prompt, timeout=1800)
    save_text(result_root / "smoke/run_py.stdout.log", one_shot["stdout"])
    save_text(result_root / "smoke/run_py.stderr.log", one_shot["stderr"])
    parsed = parse_run_stderr(one_shot["stderr"])
    parsed.update({
        "returncode": one_shot["returncode"],
        "elapsed_s": one_shot["elapsed_s"],
        "content_len": len(one_shot["stdout"]),
        "thinking_leakage": leakage(one_shot["stdout"]),
    })
    return {
        "kernel": {"returncode": kernel["returncode"], "elapsed_s": kernel["elapsed_s"]},
        "run_py": parsed,
    }


def run_pflash(result_root: Path) -> list[dict[str, Any]]:
    env = os.environ.copy()
    env.update({
        "DFLASH27B_KV_TQ3": "1",
        "DFLASH27B_FA_WINDOW": "0",
        "DFLASH_FP_USE_BSA": "1",
        "DFLASH_FP_ALPHA": "0.85",
    })
    cases = [
        ("32k", 32768, 0.10),
        ("64k", 65536, 0.05),
        ("128k", 131072, 0.02),
    ]
    results = []
    for label, ctx, keep in cases:
        case_path = result_root / f"bench/niah_{label}.jsonl"
        case_path.parent.mkdir(parents=True, exist_ok=True)
        gen = run([
            str(PY), str(PFLASH / "tests/niah_gen.py"),
            "--n", "1",
            "--ctx", str(ctx),
            "--out", str(case_path),
            "--tokenizer", TOKENIZER,
        ], cwd=ROOT, env=env, timeout=900)
        save_text(result_root / f"bench/niah_{label}_gen.stdout.log", gen["stdout"])
        save_text(result_root / f"bench/niah_{label}_gen.stderr.log", gen["stderr"])
        bench = run([
            str(PY), str(PFLASH / "tests/bench_niah_cpp.py"),
            "--cases", str(case_path),
            "--n", "1",
            "--bin", BIN,
            "--target", TARGET,
            "--draft-spec", DRAFT,
            "--drafter-gguf", DRAFTER,
            "--target-tokenizer", TOKENIZER,
            "--drafter-tokenizer", DRAFTER_TOKENIZER,
            "--max-ctx", "16384",
            "--keep-ratio", str(keep),
            "--n-gen", "96",
        ], cwd=ROOT, env=env, timeout=3600)
        save_text(result_root / f"bench/pflash_niah_{label}.stdout.log", bench["stdout"])
        save_text(result_root / f"bench/pflash_niah_{label}.stderr.log", bench["stderr"])
        parsed = parse_niah(bench["stdout"], bench["stderr"])
        parsed.update({
            "label": label,
            "ctx": ctx,
            "keep_ratio": keep,
            "returncode": bench["returncode"],
            "elapsed_s": bench["elapsed_s"],
        })
        results.append(parsed)
    return results


def run_long_decode(result_root: Path) -> list[dict[str, Any]]:
    env_base = os.environ.copy()
    env_base.update({
        "DFLASH_TARGET": TARGET,
        "DFLASH_DRAFT": DRAFT,
        "DFLASH_TOKENIZER": TOKENIZER,
    })
    cases = [
        ("tq3_32k", 32768, "tq3"),
        ("tq3_64k", 65536, "tq3"),
        ("tq3_128k", 131072, "tq3"),
        ("q4_32k", 32768, "q4"),
    ]
    results = []
    prompts: dict[int, str] = {}
    for _, ctx, _ in cases:
        prompts.setdefault(ctx, make_long_prompt(ctx))
    for label, ctx, kv in cases:
        env = env_base.copy()
        env["DFLASH27B_FA_WINDOW"] = "2048"
        args = [
            str(PY), "scripts/run.py",
            "--target", TARGET,
            "--draft", DRAFT,
            "--bin", BIN,
            "--budget", "26",
            "--n-gen", "128",
            "--max-ctx", str(ctx),
            "--fa-window", "2048",
        ]
        if kv == "tq3":
            env["DFLASH27B_KV_TQ3"] = "1"
            args.append("--kv-tq3")
        else:
            env["DFLASH27B_KV_Q4"] = "1"
            args.append("--kv-q4")
        res = run(args, cwd=DFLASH, env=env, input_text=prompts[ctx], timeout=3600)
        save_text(result_root / f"bench/{label}.stdout.log", res["stdout"])
        save_text(result_root / f"bench/{label}.stderr.log", res["stderr"])
        parsed = parse_run_stderr(res["stderr"])
        parsed.update({
            "label": label,
            "ctx": ctx,
            "kv": kv,
            "returncode": res["returncode"],
            "elapsed_s": res["elapsed_s"],
            "content_len": len(res["stdout"]),
            "thinking_leakage": leakage(res["stdout"]),
            "starts_with_marker": res["stdout"].lstrip().startswith("LONG_AGENT_RESULT"),
        })
        results.append(parsed)
    return results


def post_json(url: str, payload: dict[str, Any], timeout: int = 1800) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    started = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return {"status": resp.status, "elapsed_s": time.time() - started, "body": json.loads(body)}


def stream_chat(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    started = time.time()
    chunks = []
    with urllib.request.urlopen(req, timeout=1800) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            payload_line = json.loads(line[6:])
            delta = payload_line.get("choices", [{}])[0].get("delta", {})
            if "content" in delta:
                chunks.append(delta["content"])
    text = "".join(chunks)
    return {"elapsed_s": time.time() - started, "content": text, "content_len": len(text)}


def wait_url(url: str, timeout_s: int = 300) -> None:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:
            last = exc
        time.sleep(2)
    raise RuntimeError(f"timed out waiting for {url}: {last}")


def run_server_loop(result_root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env.update({
        "DFLASH27B_KV_TQ3": "1",
        "DFLASH27B_FA_WINDOW": "0",
        "DFLASH_FP_USE_BSA": "1",
        "DFLASH_FP_ALPHA": "0.85",
    })
    stdout_path = result_root / "api/server.stdout.log"
    stderr_path = result_root / "api/server.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PY), "scripts/server.py",
        "--host", "127.0.0.1",
        "--port", "18345",
        "--target", TARGET,
        "--draft", DRAFT,
        "--bin", BIN,
        "--tokenizer", TOKENIZER,
        "--max-ctx", "131072",
        "--budget", "26",
        "--cache-type-k", "tq3_0",
        "--cache-type-v", "tq3_0",
        "--fa-window", "0",
        "--prefix-cache-slots", "4",
        "--prefill-cache-slots", "4",
        "--prefill-compression", "auto",
        "--prefill-threshold", "32000",
        "--prefill-keep-ratio", "0.05",
        "--prefill-drafter", DRAFTER,
        "--prefill-drafter-tokenizer", DRAFTER_TOKENIZER,
    ]
    subprocess.run("pkill -f 'scripts/server.py.*18345' || true", shell=True)
    proc = subprocess.Popen(
        cmd, cwd=str(DFLASH), env=env,
        stdout=open(stdout_path, "w", encoding="utf-8"),
        stderr=open(stderr_path, "w", encoding="utf-8"),
        text=True,
    )
    try:
        wait_url("http://127.0.0.1:18345/health", 420)
        with urllib.request.urlopen("http://127.0.0.1:18345/v1/models", timeout=30) as resp:
            models = json.loads(resp.read().decode("utf-8"))
        base = "http://127.0.0.1:18345/v1/chat/completions"
        short_payload = {
            "model": "luce-dflash",
            "messages": [{"role": "user", "content": "Return CODE_RESULT and a Python fibonacci function. No thinking text."}],
            "max_tokens": 96,
        }
        short = post_json(base, short_payload)
        short_text = short["body"]["choices"][0]["message"]["content"]
        stream = stream_chat(base, {**short_payload, "stream": True})

        context = make_long_prompt(32768)
        turns = []
        for i in range(5):
            payload = {
                "model": "luce-dflash",
                "messages": [{
                    "role": "user",
                    "content": (
                        context
                        + f"\n\nAgent turn {i + 1}: produce a concrete patch/checklist. "
                          "Start with LONG_AGENT_RESULT and include no thinking text."
                    ),
                }],
                "max_tokens": 128,
            }
            res = post_json(base, payload)
            text = res["body"]["choices"][0]["message"]["content"]
            turns.append({
                "turn": i + 1,
                "status": res["status"],
                "elapsed_s": res["elapsed_s"],
                "content_len": len(text),
                "completion_tokens": res["body"].get("usage", {}).get("completion_tokens"),
                "thinking_leakage": leakage(text),
                "starts_with_marker": text.lstrip().startswith("LONG_AGENT_RESULT"),
                "preview": text[:240],
            })
        time.sleep(2)
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        diag = []
        for line in stderr.splitlines():
            if line.startswith("[dflash_diag] "):
                try:
                    diag.append(json.loads(line[len("[dflash_diag] "):]))
                except Exception:
                    pass
        cache_stats = {
            "prefix_cache_hits": sum(1 for item in diag if item.get("prefix_cache_hit")),
            "full_cache_hits": sum(1 for item in diag if item.get("full_cache_hit")),
            "compression_fired": sum(1 for item in diag if item.get("compression_fired")),
            "diag_entries": len(diag),
            "snapshot_oom": "snap failed" in stderr or "out of memory" in stderr.lower(),
        }
        return {
            "models": models,
            "short_nonstream": {
                "status": short["status"],
                "elapsed_s": short["elapsed_s"],
                "content_len": len(short_text),
                "thinking_leakage": leakage(short_text),
                "preview": short_text[:240],
            },
            "short_stream": {
                "elapsed_s": stream["elapsed_s"],
                "content_len": stream["content_len"],
                "thinking_leakage": leakage(stream["content"]),
                "preview": stream["content"][:240],
            },
            "agent_loop": turns,
            "cache_stats": cache_stats,
            "diag": diag,
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()


def service_status(name: str) -> str:
    return run(f"systemctl is-active {name} || true", timeout=30)["stdout"].strip()


def verify_live_service() -> dict[str, Any]:
    out = {
        "qwen35-35b-a3b-uncensored": service_status(LIVE_SERVICE),
        "openclaw-executor": service_status(BENCH_SERVICE),
    }
    last_exc = None
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:18343/v1/models", timeout=10) as resp:
                out["models"] = json.loads(resp.read().decode("utf-8"))
                return out
        except Exception as exc:
            last_exc = exc
            time.sleep(3)
    out["models_error"] = repr(last_exc)
    return out


def write_report(result_root: Path, summary: dict[str, Any]) -> None:
    pflash = summary.get("pflash_niah", [])
    long_decode = summary.get("long_decode", [])
    server = summary.get("server_cache_agent_loop", {})

    pflash_hits = [x for x in pflash if x.get("needle_hit")]
    pflash_bad_header = any(x.get("bad_header") for x in pflash)
    long_128 = next((x for x in long_decode if x.get("label") == "tq3_128k"), {})
    agent_turns = server.get("agent_loop", [])
    agent_ok = bool(agent_turns) and all(
        t.get("content_len", 0) > 0 and not t.get("thinking_leakage") for t in agent_turns
    )
    no_think_ok = (
        not server.get("short_nonstream", {}).get("thinking_leakage", True)
        and not server.get("short_stream", {}).get("thinking_leakage", True)
    )
    cache_stats = server.get("cache_stats", {})
    cache_hit_total = cache_stats.get("prefix_cache_hits", 0) + cache_stats.get("full_cache_hits", 0)
    long_ok = (
        long_128.get("returncode") == 0
        and long_128.get("visible_tokens", 0) >= 64
        and not long_128.get("thinking_leakage")
    )

    lines = [
        "# Lucebox Qwen3.6 Long/Agent + PFlash 修复验证报告",
        "",
        "## 结论",
        "",
        f"- GGUF draft restore bad header: {'未复现' if not pflash_bad_header else '仍复现'}",
        f"- PFlash NIAH: {len(pflash_hits)}/{len(pflash)} 命中",
        f"- TQ3 128K long decode: visible_tokens={long_128.get('visible_tokens')}, stop_token_hit={long_128.get('stop_token_hit')}, thinking_leakage={long_128.get('thinking_leakage')}",
        f"- Server/cache agent loop: {'5/5 可用' if agent_ok else '未达到 winner 条件'}",
        f"- Server cache hit: prefix={cache_stats.get('prefix_cache_hits')}, full={cache_stats.get('full_cache_hits')}, snapshot_oom={cache_stats.get('snapshot_oom')}",
        f"- no-thinking: {'通过' if no_think_ok else '仍有泄漏'}",
        "",
        "## 判定",
        "",
    ]
    if agent_ok and no_think_ok and long_ok:
        lines.append("- long/agent 生成链路可以进入下一轮质量评测；这不是上线结论。")
    else:
        lines.append("- long/agent winner 仍不建议上线；必须同时满足 128K 有效生成、无 thinking 泄漏、agent loop 5/5 非空。")
    if cache_hit_total == 0:
        lines.append("- server/cache 不能判为 cache winner：本轮 prefix/full cache hit 为 0，需继续解决 snapshot OOM 或降低 cache slots/context。")
    if pflash_hits and not pflash_bad_header:
        lines.append("- PFlash loader 问题已修复，命中样例可作为候选配置继续扩大样本。")
    elif not pflash_bad_header:
        lines.append("- PFlash loader 问题已修复，但 NIAH 未命中，不能作为 winner。")
    else:
        lines.append("- PFlash 仍存在 GGUF draft restore 问题，需要继续修 daemon loader。")
    lines.extend([
        "",
        "## 关键指标",
        "",
        "### PFlash NIAH",
        "",
        "| case | keep | compressed | ratio | score_s | gen_s | hit | bad_header |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ])
    for row in pflash:
        lines.append(
            f"| {row.get('label')} | {row.get('keep_ratio')} | {row.get('compressed_tokens')} | "
            f"{row.get('compression_ratio')} | {row.get('score_s')} | {row.get('gen_s')} | "
            f"{row.get('needle_hit')} | {row.get('bad_header')} |"
        )
    lines.extend([
        "",
        "### Long Decode",
        "",
        "| case | prompt | visible | raw | stop | elapsed_s | leak |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- |",
    ])
    for row in long_decode:
        lines.append(
            f"| {row.get('label')} | {row.get('prompt_tokens')} | {row.get('visible_tokens')} | "
            f"{row.get('raw_tokens')} | {row.get('stop_token_hit')} | "
            f"{row.get('elapsed_s'):.1f} | {row.get('thinking_leakage')} |"
        )
    lines.extend([
        "",
        "### Server/cache",
        "",
        f"- short non-stream: len={server.get('short_nonstream', {}).get('content_len')}, leak={server.get('short_nonstream', {}).get('thinking_leakage')}",
        f"- short stream: len={server.get('short_stream', {}).get('content_len')}, leak={server.get('short_stream', {}).get('thinking_leakage')}",
        f"- diag entries: {len(server.get('diag', []))}",
        f"- cache stats: prefix_hits={cache_stats.get('prefix_cache_hits')}, full_hits={cache_stats.get('full_cache_hits')}, compression_fired={cache_stats.get('compression_fired')}, snapshot_oom={cache_stats.get('snapshot_oom')}",
        "",
        "| turn | len | completion_tokens | elapsed_s | leak | marker |",
        "| ---: | ---: | ---: | ---: | --- | --- |",
    ])
    for turn in agent_turns:
        lines.append(
            f"| {turn.get('turn')} | {turn.get('content_len')} | {turn.get('completion_tokens')} | "
            f"{turn.get('elapsed_s'):.1f} | {turn.get('thinking_leakage')} | {turn.get('starts_with_marker')} |"
        )
    lines.extend([
        "",
        "## 服务恢复",
        "",
        "```json",
        json.dumps(summary.get("restore_status", {}), ensure_ascii=False, indent=2),
        "```",
        "",
    ])
    save_text(result_root / "summary/final_report.md", "\n".join(lines))


def main() -> None:
    timestamp = os.environ.get("QWEN36_FIX_TS") or datetime.now().strftime("%Y%m%d-%H%M%S")
    result_root = Path(f"{REMOTE_RESULT_BASE}/{timestamp}")
    result_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {"timestamp": timestamp}
    summary["preflight"] = {
        "nvidia_smi": run("nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv", timeout=60),
        "df": run("df -h /data /home /tmp", timeout=60),
        "services_before": verify_live_service(),
    }
    save_json(result_root / "summary/preflight.json", summary["preflight"])

    stopped = False
    try:
        sudo(f"systemctl stop {LIVE_SERVICE} || true")
        sudo(f"systemctl stop {BENCH_SERVICE} || true")
        stopped = True
        summary["services_stopped"] = verify_live_service()

        summary["smoke"] = run_smoke(result_root)
        save_json(result_root / "smoke/smoke_fixed.json", summary["smoke"])

        summary["pflash_niah"] = run_pflash(result_root)
        save_json(result_root / "bench/pflash_niah_fixed.json", summary["pflash_niah"])

        summary["long_decode"] = run_long_decode(result_root)
        save_json(result_root / "bench/tq3_long_agent_fixed.json", summary["long_decode"])

        summary["server_cache_agent_loop"] = run_server_loop(result_root)
        save_json(result_root / "api/server_cache_agent_loop_fixed.json", summary["server_cache_agent_loop"])
    finally:
        subprocess.run("pkill -f 'scripts/server.py.*18345' || true", shell=True)
        subprocess.run("pkill -f 'test_dflash.*--daemon' || true", shell=True)
        if stopped:
            sudo(f"systemctl start {LIVE_SERVICE}")
        summary["restore_status"] = verify_live_service()
        save_json(result_root / "summary/fix_comparison_summary.json", summary)
        write_report(result_root, summary)
        print(json.dumps({"result_root": str(result_root), "summary": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
'''


def run_remote_validation(timestamp: str) -> dict[str, Any]:
    remote_script = "/tmp/qwen36_lucebox_fix_remote_validate.py"
    scp_text_to_remote(REMOTE_VALIDATOR, "/tmp/qwen36_lucebox_fix_remote_validate.py", remote_script)
    raw = run_remote(
        "PY={venv}; if ! test -x \"$PY\"; then PY=python3; fi; "
        "QWEN36_FIX_TS={ts} \"$PY\" {script}".format(
            venv=shlex.quote(f"{REMOTE_DFLASH}/.venv/bin/python"),
            ts=shlex.quote(timestamp),
            script=shlex.quote(remote_script),
        ),
        timeout=14400,
    )
    return json.loads(raw.strip().splitlines()[-1])


def fetch_results(remote_result_root: str, local_output_root: Path) -> None:
    remote_parent = str(Path(remote_result_root).parent)
    remote_name = Path(remote_result_root).name
    jump_tgz = f"/tmp/{remote_name}.tgz"
    run_remote(
        f"cd {shlex.quote(remote_parent)} && tar -czf /tmp/{shlex.quote(remote_name)}.tgz {shlex.quote(remote_name)}",
        timeout=1200,
    )
    run_jump(
        "sshpass -p {password} scp -o StrictHostKeyChecking=no {user}@{host}:/tmp/{name}.tgz {jump_tgz}".format(
            password=shlex.quote(REMOTE_PASSWORD),
            user=REMOTE_USER,
            host=REMOTE_HOST,
            name=shlex.quote(remote_name),
            jump_tgz=shlex.quote(jump_tgz),
        ),
        capture=False,
        timeout=1200,
    )
    with tempfile.NamedTemporaryFile(suffix=".tgz", delete=False) as handle:
        local_tgz = Path(handle.name)
    try:
        scp_from_jump(jump_tgz, local_tgz)
        local_output_root.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(local_tgz, "r:gz") as tar:
            tar.extractall(local_output_root.parent)
        extracted = local_output_root.parent / remote_name
        if extracted != local_output_root:
            if local_output_root.exists():
                raise RuntimeError(f"local output already exists: {local_output_root}")
            extracted.rename(local_output_root)
    finally:
        local_tgz.unlink(missing_ok=True)


def save_local_patch(output_root: Path) -> None:
    output_root.joinpath("patches").mkdir(parents=True, exist_ok=True)
    diff = subprocess.run(
        ["git", "diff", "--"] + PATCHED_FILES,
        cwd=LOCAL_LUCEBOX,
        text=True,
        capture_output=True,
        check=False,
    )
    (output_root / "patches/lucebox_fix.diff").write_text(diff.stdout, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-sync", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_root = Path("/Users/luo/Documents/github/CodexGame/output/qwen36-lucebox-main-fix-long-agent-pflash-4090") / timestamp
    output_root.mkdir(parents=True, exist_ok=True)
    save_local_patch(output_root)

    if not args.skip_sync:
        sync_sources()
    if not args.skip_build:
        build_remote()

    result = run_remote_validation(timestamp)
    fetch_results(result["result_root"], output_root)
    save_local_patch(output_root)

    print(output_root)
    print(output_root / "summary/final_report.md")


if __name__ == "__main__":
    main()
