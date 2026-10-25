#!/usr/bin/env python3
"""Supervised, resumable B29 measurements. Uses only the existing HTTP API.

Run on 29, from a private directory. No engine/configuration/model mutation.
Raw bodies are private artifacts, never included in public summaries.
"""
import argparse
import concurrent.futures
import copy
import csv
import datetime as dt
import fcntl
import gzip
import hashlib
import http.client
import http.server
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import statistics
import subprocess
import threading
import time
import traceback
import urllib.parse

MODEL = "openclaw/Qwen3.8-27B-WORK"
LENGTHS = [256, 1024, 4096, 8192, 16384, 32768, 65536, 98304,
           131072, 163840, 196608, 229376, 245760, 253952]
WORKLOADS = ["copy_patch", "free_java", "chinese_analysis", "tool_json"]
TRACKS = ["production_sampling_29", "research_greedy"]
LOG_PATH = Path("/home/hhtele/ninfer-4090/logs/ninfer-request.jsonl")
MODEL_PATH = Path("/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer")
MODEL_SHA = "eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e"
IMAGE = "sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3"
BINARY_SHA = "447e37e36deed07e3359609ca41ad248ddf490c4b628c9fd487e0572be3f3c98"
MISSING = {
    "token_ids": "B29 HTTP/schema20 does not expose emitted token IDs",
    "token_itl_seconds": "SSE chunks may contain multiple tokens; chunk gaps are not token ITL",
    "reasoning_tokens": "B29 does not expose a reliable split; proxy zero is not evidence",
    "round_wall_seconds": "schema20 has counters, not per-round wall spans",
    "allocator_high_water_bytes": "B29 does not expose an allocator high-water metric",
    "internal_hidden_state": "not observable through production binary HTTP API",
}

class CalibrationUnavailable(Exception):
    pass


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        f.write(encode(value) + b"\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def command(argv, timeout=60):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"command failed {argv[0]} ({p.returncode}): {p.stderr[:400]}")
    return p.stdout.strip()


def simple_http(path, body=None, port=18030, timeout=60):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        c.request("GET" if body is None else "POST", path,
                  body=None if body is None else encode(body),
                  headers={"Content-Type": "application/json"})
        r = c.getresponse()
        raw = r.read()
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status} {path}: {raw[:300]!r}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode()
    finally:
        c.close()


def count_body(chat):
    """Equivalent for simple corpus; complex-history equivalence is checked on GPU."""
    out = {"model": chat["model"], "max_tokens": chat.get("max_tokens", 512),
           "preserve_thinking": chat.get("preserve_thinking", True), "messages": []}
    systems = []
    for m in chat["messages"]:
        role = m["role"]
        if role in ("system", "developer"):
            if not isinstance(m.get("content"), str):
                raise ValueError("non-text system is not supported by count projection")
            systems.append(m["content"])
        elif role == "tool":
            out["messages"].append({"role": "user", "content": [{
                "type": "tool_result", "tool_use_id": m["tool_call_id"],
                "content": m.get("content", "")}]})
        elif role == "assistant":
            blocks = []
            if m.get("reasoning_content"):
                blocks.append({"type": "thinking", "thinking": m["reasoning_content"]})
            if m.get("content"):
                if not isinstance(m["content"], str):
                    raise ValueError("non-text assistant is not supported by count projection")
                blocks.append({"type": "text", "text": m["content"]})
            for tool in m.get("tool_calls", []):
                fn = tool["function"]
                args = fn.get("arguments", "{}")
                blocks.append({"type": "tool_use", "id": tool["id"], "name": fn["name"],
                               "input": json.loads(args) if isinstance(args, str) else args})
            out["messages"].append({"role": "assistant", "content": blocks or ""})
        else:
            out["messages"].append({"role": role, "content": m.get("content", "")})
    if systems:
        out["system"] = "\n\n".join(systems)
    if chat.get("tools"):
        out["tools"] = []
        for tool in chat["tools"]:
            fn = tool["function"]
            t = {"name": fn["name"], "input_schema": fn.get("parameters", {})}
            if "description" in fn:
                t["description"] = fn["description"]
            out["tools"].append(t)
        out["tool_choice"] = {"type": "auto"}
    opts = chat.get("chat_template_kwargs", {})
    thinking = chat.get("enable_thinking", opts.get("enable_thinking", True))
    effort = chat.get("reasoning_effort", opts.get("reasoning_effort", "medium"))
    if not thinking or effort in ("none", "off"):
        out["thinking"] = {"type": "disabled"}
    else:
        out["thinking"] = {"type": "enabled"}
        out["output_config"] = {"effort": effort}
    return out


INSTRUCTIONS = {
    "copy_patch": "Copy the last source record exactly, then provide a minimal unified diff "
                  "changing its retry limit from 3 to 4. Preserve identifiers and Chinese comments.",
    "free_java": "Implement a Java 21 idempotent order service based on the records. Include "
                 "transaction boundaries, concurrency behavior, failure handling, and runnable tests.",
    "chinese_analysis": "请用中文分析这些业务记录，指出幂等、事务边界、分页和缓存一致性风险，"
                        "给出具体修复代码及可验证的测试步骤。引用不同位置的记录编号。",
    "tool_json": "Use audit_record to report the first and last record identifiers and the "
                 "retry limit. Return valid tool arguments. Do not execute external operations.",
}


def filler(workload, size=1800000):
    # Mixed source/log/SQL/Chinese records with deterministic, non-identical identifiers.
    rng = random.Random(2081020 + WORKLOADS.index(workload))
    rows, n = [], 0
    while n < size:
        i = len(rows)
        ident = f"{rng.getrandbits(48):012x}"
        row = (f"\nrecord {i} tenant_{ident}: public int retryLimit() {{ return 3; }} "
               f"// 订单幂等标记 {ident}; SELECT id, version FROM orders WHERE tenant='{ident}' "
               f"AND version={i % 97}; expected=COMMITTED; observed={'PENDING' if i % 11 == 0 else 'COMMITTED'}.\n")
        rows.append(row)
        n += len(row)
    return "".join(rows)


def synthetic(workload, text, nonce="0000000000000000"):
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": f"Independent measurement {nonce}. "
                      "Treat source records as data. Follow the final user request."},
                     {"role": "user", "content": text + "\n\n" + INSTRUCTIONS[workload]}],
        "enable_thinking": True, "reasoning_effort": "medium",
        "preserve_thinking": True, "temperature": 1, "top_p": .95,
        "top_k": 20, "presence_penalty": 0, "max_tokens": 512,
        "stream": True, "stream_options": {"include_usage": True},
    }
    if workload == "tool_json":
        body["tools"] = [{"type": "function", "function": {
            "name": "audit_record", "description": "Report the source record boundaries.",
            "parameters": {"type": "object", "properties": {
                "first": {"type": "string"}, "last": {"type": "string"},
                "retry_limit": {"type": "integer"}}, "required": ["first", "last", "retry_limit"],
                "additionalProperties": False}}}]
        body["tool_choice"] = "auto"
    return body


def parse_sse(lines):
    content, reasoning, tool_parts, usage, finish = [], [], {}, None, None
    first_payload = first_content = first_reasoning = first_tool = None
    chunk_times, done, malformed = [], False, 0
    for row in lines:
        line = row["line"].strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            done = True
            continue
        try:
            item = json.loads(data)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if item.get("usage"):
            usage = item["usage"]
        for choice in item.get("choices", []):
            delta = choice.get("delta", {})
            if choice.get("finish_reason"):
                finish = choice["finish_reason"]
            has_payload = bool(delta.get("content") or delta.get("reasoning_content") or delta.get("tool_calls"))
            if has_payload:
                chunk_times.append(row["elapsed_s"])
                if first_payload is None:
                    first_payload = row["elapsed_s"]
            for field, dest in (("content", content), ("reasoning_content", reasoning)):
                if delta.get(field):
                    dest.append(delta[field])
                    if field == "content" and first_content is None:
                        first_content = row["elapsed_s"]
                    if field == "reasoning_content" and first_reasoning is None:
                        first_reasoning = row["elapsed_s"]
            for tool in delta.get("tool_calls", []):
                if first_tool is None:
                    first_tool = row["elapsed_s"]
                acc = tool_parts.setdefault(tool.get("index", 0), {"id": "", "name": "", "arguments": ""})
                acc["id"] += tool.get("id", "")
                for k in ("name", "arguments"):
                    acc[k] += tool.get("function", {}).get(k, "")
    tools, tool_valid = [], True
    for tool in tool_parts.values():
        try:
            json.loads(tool["arguments"])
        except (json.JSONDecodeError, TypeError):
            tool_valid = False
        tools.append({"id": tool["id"], "type": "function", "function": {
            "name": tool["name"], "arguments": tool["arguments"]}})
    assistant = {"role": "assistant", "content": "".join(content)}
    if reasoning:
        assistant["reasoning_content"] = "".join(reasoning)
    if tools:
        assistant["tool_calls"] = tools
    return {
        "usage": usage, "finish_reason": finish, "sse_done": done, "malformed_data_events": malformed,
        "first_payload_s": first_payload, "first_content_s": first_content,
        "first_reasoning_s": first_reasoning, "first_tool_s": first_tool,
        "chunk_times_s": chunk_times, "tool_json_valid": tool_valid,
        "tool_count": len(tools), "content_chars": len(assistant["content"]),
        "reasoning_chars": len(assistant.get("reasoning_content", "")),
        "assistant": assistant,
    }


class Runner:
    def __init__(self, root, smoke=False):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.smoke = smoke
        self.stop = threading.Event()
        self.resource_error = None
        self.status_lock = threading.Lock()
        self.status = {"state": "PREPARING", "started_utc": utc(), "pid": os.getpid(),
                       "completed_requests": 0, "current_case": None}
        self.resource_enabled = True
        self.resource_process = None
        self.monitor = None
        self.results = {}
        records = self.root / "records.jsonl"
        if records.exists():
            data = records.read_bytes()
            lines = data.splitlines(keepends=True)
            valid = []
            for index, line in enumerate(lines):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    if index != len(lines)-1 or line.endswith(b"\n"):
                        raise RuntimeError("corrupt durable records before trailing partial line")
                    (self.root / f"records-partial-tail-{time.time_ns()}.bin").write_bytes(line)
                    break
                if row["id"] in self.results:
                    raise RuntimeError("duplicate durable request ID")
                self.results[row["id"]] = row
                valid.append(line.rstrip(b"\n")+b"\n")
            if b"".join(valid) != data:
                recovered = records.with_suffix(".recovered")
                recovered.write_bytes(b"".join(valid))
                os.replace(recovered, records)
        # A crash between record.json fsync and the append must not repeat that request.
        for record_path in sorted((self.root / "requests").glob("*/record.json")):
            row = json.loads(record_path.read_text())
            if row["id"] not in self.results:
                raw_path = record_path.parent / "raw.json.gz"
                if not raw_path.exists() or sha(raw_path.read_bytes()) != row["raw_sha256"]:
                    raise RuntimeError("orphan record has missing/corrupt raw artifact")
                with records.open("a") as f:
                    f.write(json.dumps(row, ensure_ascii=False)+"\n")
                    f.flush()
                    os.fsync(f.fileno())
                self.results[row["id"]] = row
        self.status["completed_requests"] = len(self.results)
        self.events_lock = threading.Lock()
        self.expected = json.loads((self.root / "expected-baseline.json").read_text())

    def update(self, **values):
        with self.status_lock:
            self.status.update(values)
            self.status["heartbeat_utc"] = utc()
            self.status["resource_monitor_error"] = self.resource_error
            atomic(self.root / "status.json", self.status)

    def resource_loop(self):
        fields = "timestamp,uuid,memory.used,memory.total,utilization.gpu,utilization.memory,temperature.gpu,power.draw,power.limit,clocks.current.sm,clocks.current.memory,pstate"
        args = ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits", "-lms", "200"]
        while not self.stop.is_set():
            if not self.resource_enabled:
                self.stop.wait(.1)
                continue
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.resource_process = p
            expected_stop = False
            try:
                with (self.root / "gpu.csv").open("a") as out:
                    for line in p.stdout:
                        if self.stop.is_set() or not self.resource_enabled:
                            expected_stop = True
                            break
                        out.write(f"{time.time():.6f},{line}")
                        out.flush()
            except Exception as exc:
                self.resource_error = type(exc).__name__
            finally:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
                self.resource_process = None
                if not self.stop.is_set() and not expected_stop:
                    self.resource_error = "nvidia-smi exited"
            if self.resource_error:
                return

    def heartbeat_loop(self):
        while not self.stop.wait(15):
            try:
                self.update(free_disk_bytes=shutil.disk_usage(self.root).free)
                with (self.root / "host.jsonl").open("a") as f:
                    f.write(json.dumps({"utc": utc(), "loadavg": os.getloadavg(),
                                        "meminfo": Path("/proc/meminfo").read_text()}) + "\n")
            except Exception as exc:
                self.resource_error = f"heartbeat: {type(exc).__name__}"

    def start_monitor(self):
        self.monitor = threading.Thread(target=self.resource_loop, daemon=True)
        self.monitor.start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    def fingerprint(self, name, full=False):
        raw = command(["docker", "inspect", "ninfer-4090-prod", "--format",
                       '{"image_id":{{json .Image}},"path":{{json .Path}},"args":{{json .Args}},'
                       '"mounts":{{json .Mounts}},"started_at":{{json .State.StartedAt}}}'])
        image = json.loads(raw)
        if image["image_id"] != IMAGE or image["args"] != self.expected["image"]["args"]:
            raise RuntimeError("DEPLOYMENT_DRIFT: image or argv changed")
        model_stat = MODEL_PATH.stat()
        fp = {"utc": utc(), "image": image, "kernel": command(["uname", "-a"]),
              "gpu": command(["nvidia-smi", "--query-gpu=uuid,name,driver_version,memory.total,power.limit",
                              "--format=csv"]),
              "model_stat": {"size": model_stat.st_size, "mtime_ns": model_stat.st_mtime_ns,
                             "ctime_ns": model_stat.st_ctime_ns},
              "launch_proxy_hash": command(["sha256sum",
                  "/home/hhtele/ninfer-4090/launch/production-18343.sh",
                  "/home/hhtele/ninfer-4090/launch/openai_compat_proxy.py"])}
        expected_hashes = self.expected["sha256"]
        for line in fp["launch_proxy_hash"].splitlines():
            digest, file = line.split(None, 1)
            if expected_hashes[file.strip()] != digest:
                raise RuntimeError("DEPLOYMENT_DRIFT: launch or proxy changed")
        if self.expected["gpu_uuid"] not in fp["gpu"]:
            raise RuntimeError("DEPLOYMENT_DRIFT: GPU UUID changed")
        fp["binary_hash"] = command(["docker", "exec", "ninfer-4090-prod", "sha256sum",
                                      "/usr/local/bin/ninfer-serve"])
        if fp["binary_hash"].split()[0] != BINARY_SHA:
            raise RuntimeError("DEPLOYMENT_DRIFT: binary changed")
        anchor_path = self.root / "fingerprint-anchor.json"
        if anchor_path.exists():
            anchor = json.loads(anchor_path.read_text())
            if anchor["model_stat"] != fp["model_stat"] or anchor["gpu"] != fp["gpu"]:
                raise RuntimeError("DEPLOYMENT_DRIFT: model file stat or GPU configuration changed")
        else:
            atomic(anchor_path, fp)
        if full:
            fp["model_hash"] = command(["sha256sum", str(MODEL_PATH)], timeout=240)
            if fp["model_hash"].split()[0] != MODEL_SHA:
                raise RuntimeError("DEPLOYMENT_DRIFT: model changed")
            fp["cuda_runtime_packages"] = command([
                "docker", "exec", "ninfer-4090-prod", "dpkg-query", "-W",
                "cuda-cudart-13-2", "libcublas-13-2", "libcudnn9-cuda-13", "cuda-compat-13-2"])
            fp["docker_diff"] = command(["docker", "diff", "ninfer-4090-prod"])
        atomic(self.root / "fingerprints" / f"{name}.json", fp)
        return fp

    def idle(self, timeout=60):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            slots = simple_http("/slots")
            if all(not x.get("is_processing") for x in slots):
                return slots
            time.sleep(2)
        raise RuntimeError("GPU_NOT_IDLE: no new request dispatched")

    def count(self, body, name):
        projection = count_body(body)
        response = simple_http("/v1/messages/count_tokens", projection, timeout=180)
        n = response["input_tokens"]
        if not isinstance(n, int) or n < 1:
            raise RuntimeError("invalid tokenizer count")
        path = self.root / "calibration" / f"{name}.json"
        atomic(path, {"projection": projection, "response": response,
                      "chat_sha256": sha(encode(body)), "utc": utc()})
        return n

    def align_final_count(self, body, target, name):
        """Calibrate the actual nonce-bearing wire, not only its base fixture."""
        n = self.count(body, name+"-initial")
        if n == target:
            return body, n
        content = body["messages"][1]["content"]
        separator = "\n\n"
        source, instruction = content.rsplit(separator, 1)
        candidates = [(n, source)]
        # Nonce difference is tiny; bound a local character search around the base.
        extended = source + filler("copy_patch", 1024)[:512]
        low, high = max(0, len(source)-512), len(source)+512
        for step in range(12):
            size = (low+high)//2
            body["messages"][1]["content"] = extended[:size]+separator+instruction
            n = self.count(body, name+f"-adjust-{step}")
            candidates.append((n, extended[:size]))
            if n == target:
                return body, n
            if n < target:
                low = size+1
            else:
                high = size-1
            if low > high:
                break
        # Token counts are not continuous (or strictly monotone) in characters.
        # A tokenizer merge may jump over the target. Try small delimited tails
        # around the closest under-target prefix; always verify the actual wire.
        below = [(tokens, text) for tokens, text in candidates if tokens < target]
        if below:
            tokens, text = max(below, key=lambda candidate: candidate[0])
            padding = max(1, target-tokens)
            for trim in range(9):
                prefix = text[:max(0, len(text)-trim)]
                for index, tail in enumerate((" x", " a", " 0", "\nx", "\n0", " .", ";", " ", "\n")):
                    body["messages"][1]["content"] = prefix + tail*padding + separator + instruction
                    n = self.count(body, name+f"-tail-{trim}-{index}")
                    if n == target:
                        return body, n
        raise RuntimeError(f"FINAL_TOKEN_BUCKET_MISMATCH target={target}, counted={n}")

    def calibrate(self, workload, target):
        path = self.root / "corpus" / f"{workload}-{target}.json"
        exact_path = path.with_name(f"{workload}-{target}-exact-v2.json")
        if exact_path.exists():
            path = exact_path
        meta_path = path.with_suffix(".meta.json")
        if path.exists() and meta_path.exists():
            body = json.loads(path.read_text())
            meta = json.loads(meta_path.read_text())
            if sha(encode(body)) != meta["sha256"]:
                raise RuntimeError("corpus hash mismatch")
            if meta["counted_prompt_tokens"] != target:
                # Preserve earlier approximate fixtures referenced by old records.
                body, counted = self.align_final_count(body, target, f"{workload}-{target}-exact-v2")
                meta = {**meta, "counted_prompt_tokens": counted, "exact": True,
                        "sha256": sha(encode(body)), "previous_fixture": str(path.relative_to(self.root))}
                atomic(exact_path, body)
                atomic(exact_path.with_suffix(".meta.json"), meta)
            return body, meta
        self.update(state="CALIBRATING", current_case=f"{workload}-{target}")
        text = filler(workload)
        minimum = self.count(synthetic(workload, ""), f"{workload}-{target}-minimum")
        if minimum > target:
            atomic(self.root / "unrepresentable" / f"{workload}-{target}.json", {
                "status": "UNREPRESENTABLE", "workload": workload, "target_prompt_tokens": target,
                "minimum_prompt_tokens": minimum, "reason": "fixed template/tools/instruction exceed target"})
            raise CalibrationUnavailable(f"{workload} minimum {minimum} exceeds {target}")
        low, high, best, history = 0, min(len(text), target * 6), None, []
        for step in range(24):
            size = (low + high) // 2
            body = synthetic(workload, text[:size])
            n = self.count(body, f"{workload}-{target}-{step}")
            history.append({"chars": size, "tokens": n})
            if best is None or abs(n-target) < abs(best[0]-target):
                best = (n, body)
            if n == target or low >= high:
                break
            if n < target:
                low = size + 1
            else:
                high = size - 1
        if abs(best[0]-target) > 2:
            raise RuntimeError(f"token calibration cannot reach {target}: {best[0]}")
        body = best[1]
        body, counted = self.align_final_count(body, target, f"{workload}-{target}-exact")
        meta = {"target": target, "counted_prompt_tokens": counted, "sha256": sha(encode(body)),
                "iterations": history, "exact": True,
                "count_qualification": "PENDING_CHAT_REQUEST_DONE_EQUALITY"}
        atomic(path, body)
        atomic(meta_path, meta)
        return body, meta

    def log_events(self, offset, request_id, wait=3):
        end = time.monotonic() + wait
        events, foreign = [], 0
        while True:
            events, foreign = [], 0
            with LOG_PATH.open() as f:
                f.seek(offset)
                for line in f:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rid = item.get("request", {}).get("x_request_id")
                    if rid == request_id and request_id:
                        events.append(item)
                    elif item.get("event") == "request_start":
                        foreign += 1
            if any(e["event"] in ("request_done", "request_error") for e in events) or time.monotonic() >= end:
                return events, foreign
            time.sleep(.1)

    def request(self, case_id, body, *, group, cache=None, expected_count=None,
                target=None, port=18030, path="/v1/chat/completions", timeout=1800,
                concurrent=False, disconnect_after=None, expected_status=200, extra=None, relay=None):
        if case_id in self.results:
            return self.results[case_id]
        if self.stop.is_set() or (self.root / "STOP").exists():
            raise RuntimeError("STOP_REQUESTED")
        if shutil.disk_usage(self.root).free < 5 * 1024**3:
            raise RuntimeError("LOW_DISK")
        if not concurrent:
            self.idle()
        self.update(state="RUNNING", current_case=case_id, request_deadline_utc=(
            dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=timeout)).isoformat())
        directory = self.root / "requests" / case_id
        if directory.exists():
            # A request may have reached the model even without a durable record.
            raise RuntimeError(f"UNKNOWN_REQUEST_OUTCOME: preserve and reconcile {case_id}; no retry")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload = encode(body)
        atomic(directory / "request.json", body)
        before = simple_http("/metrics")
        offset = LOG_PATH.stat().st_size
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        socket_ref = [None]
        response = None
        # A wall-clock deadline also interrupts slow trickles, not just socket inactivity.
        def abort():
            sock = socket_ref[0] or conn.sock
            if sock:
                try:
                    sock.shutdown(2)
                except OSError:
                    pass
            conn.close()
        deadline_expired = threading.Event()
        def wall_timeout():
            deadline_expired.set()
            abort()
        timer = threading.Timer(timeout, wall_timeout)
        timer.daemon = True
        timer.start()
        started = time.monotonic()
        start_utc = utc()
        lines, headers, raw, error, status, rid, intentional_disconnect = [], {}, b"", None, None, None, False
        cancelled = threading.Event()
        cancel_timer = None
        if disconnect_after is not None:
            def cancel():
                cancelled.set()
                abort()
            cancel_timer = threading.Timer(disconnect_after, cancel)
            cancel_timer.daemon = True
            cancel_timer.start()
        try:
            conn.request("POST", path, body=payload, headers={"Content-Type": "application/json",
                         "X-Request-Id": case_id})
            socket_ref[0] = conn.sock
            response = conn.getresponse()
            headers = dict(response.getheaders())
            rid = response.getheader("X-Request-Id")
            status = response.status
            if relay:
                relay.start_response(status, headers)
            if body.get("stream") and status == 200:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    lines.append({"elapsed_s": time.monotonic()-started,
                                  "line": line.decode("utf-8", "replace")})
                    if relay:
                        relay.write_chunk(line)
            else:
                raw = response.read()
                if relay:
                    relay.write_chunk(raw)
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:300]
        finally:
            if cancel_timer:
                cancel_timer.cancel()
            intentional_disconnect = cancelled.is_set()
            conn.close()
            if response is not None and hasattr(response, "close"):
                response.close()
            timer.cancel()
        elapsed = time.monotonic()-started
        if deadline_expired.is_set():
            error = "DEADLINE_EXCEEDED"
        parsed = parse_sse(lines)
        raw_document = {"request_sha256": sha(payload), "request_bytes": len(payload),
                        "start_utc": start_utc, "elapsed_s": elapsed, "headers": headers,
                        "http_status": status, "response_request_id": rid, "error": error,
                        "lines": lines, "body": raw.decode("utf-8", "replace"),
                        "metrics_before": before, "intentional_disconnect": intentional_disconnect,
                        "parsed": parsed}
        # Persist client evidence before any fallible post-request observation.
        atomic(directory / "client-raw.json", raw_document)
        recovery_error = None
        if intentional_disconnect or error:
            try:
                self.idle(timeout=90)
            except Exception as exc:
                recovery_error = str(exc)
        observation_errors = []
        try:
            events, foreign = self.log_events(offset, rid)
        except Exception as exc:
            events, foreign = [], 0
            observation_errors.append("log: "+str(exc))
        done = next((e for e in reversed(events) if e["event"] == "request_done"), None)
        raw_document["server_events"] = events
        raw_document["observation_errors"] = observation_errors
        try:
            raw_document["metrics_after"] = simple_http("/metrics")
        except Exception as exc:
            raw_document["metrics_after_error"] = str(exc)
        with gzip.open(directory / "raw.json.gz", "wb") as f:
            f.write(encode(raw_document))
        # Persist the compressed artifact before publishing its durable record.
        with (directory / "raw.json.gz").open("rb") as durable_raw:
            os.fsync(durable_raw.fileno())
        result = done.get("result", {}) if done else {}
        timing = done.get("timings_seconds", {}) if done else {}
        p = result.get("prompt_tokens")
        o = result.get("completion_tokens")
        hits = result.get("prefix_cache_hit_tokens")
        failures = []
        if status != expected_status:
            failures.append("HTTP_STATUS")
        if error and not intentional_disconnect:
            failures.append("TRANSPORT_ERROR")
        if recovery_error:
            failures.append("LANE_NOT_RELEASED")
        if expected_status == 200 and not intentional_disconnect and not done:
            failures.append("MISSING_REQUEST_DONE")
        if done and done.get("schema_version") != 20:
            failures.append("LOG_SCHEMA_DRIFT")
        if expected_count is not None and p != expected_count:
            failures.append("COUNT_PROJECTION_MISMATCH")
        if target is not None and group == "core" and p != target:
            failures.append("WRONG_CONTEXT_BUCKET")
        if cache == "request_cold" and (hits != 0 or result.get("computed_prefill_tokens") != p):
            failures.append("COLD_CONDITION_NOT_MET")
        if cache == "warm_prefix" and (hits is None or hits <= 0):
            failures.append("WARM_CONDITION_NOT_MET")
        if foreign and not concurrent:
            failures.append("FOREIGN_REQUEST_CONTAMINATION")
        if self.resource_error:
            failures.append("RESOURCE_MONITOR_FAILED")
        chat_stream = path == "/v1/chat/completions" and body.get("stream")
        if expected_status == 200 and chat_stream and not intentional_disconnect:
            if not parsed["sse_done"] or not parsed["finish_reason"] or parsed["malformed_data_events"]:
                failures.append("INVALID_CHAT_STREAM")
        if disconnect_after is not None and not intentional_disconnect:
            failures.append("DISCONNECT_NOT_EXERCISED")
        req_o = body.get("max_tokens")
        effective = min(req_o, 262144-p+1) if req_o is not None and p is not None and p <= 262144 else None
        row = {
            "schema_version": 1,
            "id": case_id, "group": group, "cache": cache, "target_prompt_tokens": target,
            "start_utc": start_utc, "completed_utc": utc(), "elapsed_s": elapsed,
            "status": "RECORDED" if not failures else "RECORDED_WITH_GAPS",
            "failures": failures, "request_sha256": sha(payload),
            "raw_sha256": sha((directory / "raw.json.gz").read_bytes()),
            "response_request_id": rid, "server_instance_id": done.get("server_instance_id") if done else None,
            "http_status": status, "prompt_tokens": p, "completion_tokens": o,
            "requested_output_tokens": req_o, "effective_output_cap_by_source_contract": effective,
            "result": result, "timings_seconds": timing,
            "prepare_detail": done.get("prepare_detail") if done else None,
            "speculative": done.get("speculative") if done else None,
            "continuation_cache": done.get("continuation_cache") if done else None,
            "decode_tokens_per_s": (o-1)/timing["decode"] if o and o > 1 and timing.get("decode", 0) > 0 else None,
            "decode_rate_definition": "(completion_tokens-1)/server_decode_seconds; raw retained",
            "first_payload_s": parsed["first_payload_s"], "first_content_s": parsed["first_content_s"],
            "first_reasoning_s": parsed["first_reasoning_s"], "first_tool_s": parsed["first_tool_s"],
            "content_chars": parsed["content_chars"], "reasoning_chars": parsed["reasoning_chars"],
            "finish_reason": parsed["finish_reason"], "tool_json_valid": parsed["tool_json_valid"],
            "sse_done": parsed["sse_done"], "malformed_data_events": parsed["malformed_data_events"],
            "quality_status": "NOT_JUDGED_PERFORMANCE_OBSERVATION_ONLY",
            "behavior_outcomes": {
                "incomplete_tool_json": not parsed["tool_json_valid"],
                "reasoning_only": parsed["reasoning_chars"] > 0 and parsed["content_chars"] == 0
                                  and parsed["tool_count"] == 0,
                "output_budget_exhausted": result.get("finish_reason") in ("output_limit", "context_capacity")},
            "unavailable_metrics": {k: {"value": None, "reason": v} for k, v in MISSING.items()},
            "foreign_requests_during_interval": foreign, "extra": extra or {},
        }
        atomic(directory / "record.json", row)
        # Only the main process writes this file; queued requests serialize the append.
        with self.events_lock:
            with (self.root / "records.jsonl").open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            self.results[case_id] = row
        self.update(state="BETWEEN_REQUESTS", current_case=None, completed_requests=len(self.results),
                    last_completed_case=case_id, request_deadline_utc=None)
        if any(f in failures for f in ("TRANSPORT_ERROR", "LOG_SCHEMA_DRIFT", "FOREIGN_REQUEST_CONTAMINATION",
                                       "RESOURCE_MONITOR_FAILED", "MISSING_REQUEST_DONE", "LANE_NOT_RELEASED")):
            raise RuntimeError(f"measurement stopped: {','.join(failures)}")
        return row

    def assistant(self, case_id):
        with gzip.open(self.root / "requests" / case_id / "raw.json.gz", "rb") as f:
            return json.load(f)["parsed"]["assistant"]

    def core(self):
        # 5 independent temporal blocks. A/A pairs remain separate observations.
        # O512 p95 bucket = fixed equal mix of 4 workloads, 25 each = 100 requests.
        blocks = 1 if self.smoke else 5
        lengths = [256, 1024] if self.smoke else LENGTHS
        workloads = ["copy_patch", "tool_json"] if self.smoke else WORKLOADS
        for block in range(blocks):
            self.fingerprint(f"core-block-{block}")
            for w in range(3):
                body = synthetic("chinese_analysis", "Warmup only.", f"warmup-{block}-{w}")
                body["max_tokens"] = 32
                self.request(f"warmup-{block}-{w}", body, group="warmup")
            combinations = [(p, o, workload, track) for p in lengths
                            for o in ([128] if self.smoke else [128, 512, 2048])
                            for workload in workloads for track in TRACKS]
            random.Random(20261020+block).shuffle(combinations)
            for p, o, workload, track in combinations:
                repeats = 1 if self.smoke else (7 if p == 256 and o == 512 else 5 if o == 512 else 4)
                original, meta = None, None
                for rep in range(repeats):
                    prefix = f"core-b{block}-r{rep}-P{p}-O{o}-{workload}-{track}"
                    cold_id, warm_id = prefix+"-cold", prefix+"-warm"
                    if cold_id in self.results and warm_id in self.results:
                        continue
                    if cold_id in self.results:
                        cold = self.results[cold_id]
                        body = json.loads((self.root / "requests" / cold_id / "request.json").read_text())
                        if sha(encode(body)) != cold["request_sha256"]:
                            raise RuntimeError("saved cold request hash mismatch")
                        if cold["failures"] or cold["prompt_tokens"] != p:
                            raise RuntimeError("cannot resume warm pair from unqualified cold record")
                        counted, extra = p, cold["extra"]
                    else:
                        if original is None:
                            try:
                                original, meta = self.calibrate(workload, p)
                            except CalibrationUnavailable:
                                break
                        body = copy.deepcopy(original)
                        nonce = f"{int(sha(prefix.encode())[:16],16) % 10**16:016d}"
                        body["messages"][0]["content"] = body["messages"][0]["content"].replace(
                            "0000000000000000", nonce)
                        body["max_tokens"] = o
                        body["seed"] = 20261020 + block*100 + rep
                        if track == "research_greedy":
                            body["temperature"] = 0
                        body, counted = self.align_final_count(body, p, prefix)
                        extra = {"block": block, "repetition": rep, "track": track, "workload": workload,
                                 "sample_role": "BASELINE_REPEAT" if rep < 4 else "P95_EXTRA",
                                 "calibrated_base_tokens": meta["counted_prompt_tokens"],
                                 "p95_bucket": f"P{p}-O512-{track}-equal{3 if p == 256 else 4}workload"
                                               if o == 512 else None}
                    cold = self.request(prefix+"-cold", body, group="core", cache="request_cold",
                                        expected_count=counted, target=p, extra=extra)
                    # On resume a previously completed cold does not establish current warm state.
                    if warm_id not in self.results:
                        if self.status.get("last_completed_case") != prefix+"-cold":
                            self.request(prefix+"-resume-prime-"+str(int(time.time())), body,
                                         group="resume_priming", expected_count=counted)
                    self.request(warm_id, body, group="core", cache="warm_prefix",
                                 expected_count=counted, target=p, extra=extra)
                    if "COUNT_PROJECTION_MISMATCH" in cold["failures"]:
                        raise RuntimeError("count projection mismatch: corpus cannot be qualified")
            self.summarize()

    def pi(self):
        manifest = json.loads((self.root / "pi-private" / "manifest.json").read_text())
        # Teacher-forced sequence: each request uses frozen historical assistant/tool messages.
        for block in range(1 if self.smoke else 5):
            self.fingerprint(f"pi-block-{block}")
            selected = manifest["cases"][:1] if self.smoke else manifest["cases"]
            for row in selected:
                raw = (self.root / "pi-private" / row["payload_file"]).read_bytes()
                if sha(raw) != row["payload_sha256"]:
                    raise RuntimeError("Pi frozen payload hash mismatch")
                body = json.loads(raw)
                body["stream"] = True
                body["stream_options"] = {"include_usage": True}
                body["seed"] = 20261020 + block
                counted = None
                projection_error = None
                try:
                    counted = self.count(body, f"pi-{block}-{row['id']}")
                except (ValueError, KeyError, RuntimeError) as exc:
                    projection_error = type(exc).__name__ + ": " + str(exc)[:200]
                measured = self.request(f"pi-b{block}-{row['id']}", body, group="pi_teacher_forced",
                             expected_count=None, timeout=2400, port=18343, extra={
                                 "source_sha256": row["source_sha256"], "entry_id": row["entry_id"],
                                 "qualification": manifest["qualification"], "block": block,
                                 "historical_budget_provenance": row["budget_provenance"],
                                 "mandatory_truncation": row["mandatory_truncation"],
                                 "projected_count": counted, "count_projection_error": projection_error,
                                 "cache_condition": "OBSERVED_SEQUENCE_WITH_GAPS_NOT_ASSUMED_APPEND"})
                atomic(self.root / "pi-calibration" / f"b{block}-{row['id']}.json", {
                    "projected_prompt_tokens": counted, "actual_prompt_tokens": measured["prompt_tokens"],
                    "projection_error": projection_error,
                    "status": "MATCH" if counted == measured["prompt_tokens"] and counted is not None
                              else "PROJECTION_NOT_EQUIVALENT_USE_ACTUAL_CHAT_COUNT",
                    "exact_frontend_equivalence_gate": counted is not None and counted == measured["prompt_tokens"]})
            self.summarize()

    def stability(self):
        for p in [1024, 32768, 131072, 253952]:
            body, _ = self.calibrate("copy_patch", p)
            body = copy.deepcopy(body)
            body["temperature"] = 0
            body["seed"] = 20261020
            body["max_tokens"] = 512
            self.request(f"aa-P{p}-prime", body, group="aa_priming")
            for pair in range(10):
                for member in ["A", "A2"]:
                    self.request(f"aa-P{p}-pair{pair}-{member}", body, group="frozen_wire_AA",
                                 cache="warm_prefix", target=p,
                                 extra={"pair": pair, "member": member, "same_wire_same_seed": True})

    def observer_overhead(self):
        body, _ = self.calibrate("free_java", 32768)
        body = copy.deepcopy(body)
        body.update(temperature=0, seed=20261020, max_tokens=512)
        self.request("observer-prime", body, group="observer_priming")
        for pair in range(10):
            order = [False, True] if pair % 2 == 0 else [True, False]
            for enabled in order:
                self.resource_enabled = enabled
                deadline = time.monotonic()+10
                while bool(self.resource_process) != enabled:
                    if time.monotonic() > deadline:
                        raise RuntimeError("GPU observer did not enter requested state")
                    time.sleep(.1)
                self.request(f"observer-pair{pair}-{'on' if enabled else 'off'}", body,
                             group="observer_overhead", cache="warm_prefix",
                             extra={"pair": pair, "gpu_sampler_enabled": enabled, "cadence_ms": 200,
                                    "scope": "incremental_GPU_sampler_only; production_log_and_HTTP_collector_always_on"})
        self.resource_enabled = True

    def service_cold(self):
        for p in [1024, 32768, 131072, 253952]:
            case_id = f"service-cold-P{p}"
            if case_id in self.results:
                continue
            body, _ = self.calibrate("copy_patch", p)
            body = copy.deepcopy(body)
            body["max_tokens"] = 128
            self.idle()
            self.update(state="RESTARTING_SAME_BASELINE", current_case=case_id, request_deadline_utc=None)
            started = time.monotonic()
            restart = command([
                "/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh",
                "systemctl", "restart", "openclaw-qwen38-ninfer.service"], timeout=360)
            deadline = time.monotonic()+360
            while True:
                try:
                    simple_http("/health", timeout=5)
                    simple_http("/v1/models", port=18343, timeout=5)
                    break
                except Exception:
                    if time.monotonic() > deadline:
                        raise RuntimeError("service failed to become ready after same-config restart")
                    time.sleep(3)
            self.fingerprint(f"service-cold-P{p}")
            atomic(self.root / "startup" / f"P{p}.json", {
                "ready_seconds": time.monotonic()-started, "restart_stdout": restart,
                "os_page_cache": "HOT_OR_UNKNOWN_NOT_DROPPED", "configuration_changed": False})
            self.request(case_id, body, group="S0_service_cold", cache="request_cold",
                         expected_count=p, target=p, extra={"post_restart_first_generation": True})
            self.request(case_id+"-warm", body, group="S7_process_cache_scope", cache="warm_prefix",
                         expected_count=p, target=p,
                         extra={"cache_scope": "new_process_L1_L2_not_cross_restart_persistence"})

    def capacity_boundaries(self):
        for p in [255, 256, 257, 511, 512, 513, 1023, 1024, 1025, 4095, 4096, 4097,
                  262017, 262018, 262144, 262145]:
            body, _ = self.calibrate("free_java", p)
            body = copy.deepcopy(body)
            body["max_tokens"] = 128
            body["temperature"] = 0
            body["seed"] = 20261020
            self.request(f"boundary-P{p}-O128", body, group="capacity_boundary",
                         expected_count=p if p <= 262144 else None, target=p,
                         expected_status=200 if p <= 262144 else 400,
                         extra={"context_capacity": 262144, "expected_effective_output_cap":
                                min(128, 262144-p+1) if p <= 262144 else 0,
                                "contract": "P>C rejects; otherwise O_eff=min(O,C-P+1); last sample has no KV write"})

    def supplemental(self):
        # Long decode and state transitions use the unchanged production configuration.
        for p in [1024, 32768, 131072, 229376]:
            for track in TRACKS:
                body, _ = self.calibrate("free_java", p)
                body = copy.deepcopy(body)
                body["max_tokens"] = 8192
                body["temperature"] = 0 if track == "research_greedy" else 1
                for rep in range(3):
                    body["seed"] = 20261020+rep
                    self.request(f"long-output-P{p}-{track}-r{rep}", body,
                                 group="long_output_8192", target=p)
        for p in [8192, 32768, 131072, 196608, 245760]:
            base, _ = self.calibrate("tool_json", p)
            base = copy.deepcopy(base)
            base["max_tokens"] = 512
            base["temperature"] = 0
            for size in [128, 1024]:
                name = f"state-P{p}-append{size}"
                self.request(name+"-base", base, group="S3_append", target=p)
                assistant = self.assistant(name+"-base")
                appended = copy.deepcopy(base)
                appended["messages"].append(assistant)
                for t in assistant.get("tool_calls", []):
                    appended["messages"].append({"role": "tool", "tool_call_id": t["id"],
                                                  "content": json.dumps({"ok": True, "value": "fixture"})})
                appended["messages"].append({"role": "user", "content":
                    ("Additional fixture constraint. " * size)[:size] + " Report the retry limit."})
                self.request(name+"-append", appended, group="S3_append", target=p,
                             extra={"append_characters": size, "actual_increment_tokens": "derive from server P"})
                changed = copy.deepcopy(appended)
                changed["messages"][-1]["content"] = "Correction: report retry limit 4."
                self.request(name+"-branch-B", changed, group="S4_S5_branch")
                self.request(name+"-branch-A", appended, group="S4_S5_branch")
                changed_system = copy.deepcopy(appended)
                changed_system["messages"][0]["content"] = "Updated system: report only verified records."
                self.request(name+"-system-change", changed_system, group="S4_system")
        # L2 is observational: pressure does not by itself prove a particular cache source.
        for p in [32768, 131072, 253952]:
            base, _ = self.calibrate("copy_patch", p)
            base = copy.deepcopy(base)
            base["max_tokens"] = 128
            self.request(f"l2-P{p}-A", base, group="S6_L2")
            for w in ["free_java", "chinese_analysis", "tool_json"]:
                pressure, _ = self.calibrate(w, p)
                pressure = copy.deepcopy(pressure)
                pressure["max_tokens"] = 128
                self.request(f"l2-P{p}-pressure-{w}", pressure, group="S6_L2")
            self.request(f"l2-P{p}-return-A", base, group="S6_L2",
                         extra={"required_cache_source": "l2", "source_must_be_observed": True})
        self.protocols_and_queue()
        atomic(self.root / "applicability.json", {
            "S0_service_cold": "EXECUTED_BY_SERVICE_COLD_STAGE_CHECK_RECORDS",
            "S7_restart": "L1/L2_NONPERSISTENCE_ONLY; no L3 in B29",
            "S8_aux_identity_late_DMA": "NOT_APPLICABLE_B29: requires candidate hooks not in this binary",
            "active_C2_C3_C4": "NOT_APPLICABLE_B29: active C1 frozen; no candidate configuration authorized",
            "historical_ladder_exact_wire": "BLOCKED: original full wire unavailable; Pi derived corpus is separate",
            "round_fault_injection": "UNAVAILABLE: no production fault-injection hook; no engine changes authorized",
            "old_snapshot_wrong_identity": "UNAVAILABLE: slot persistence disabled in B29",
            "closed_loop_20x3": "PENDING_LOCAL_ISOLATED_PI_RUNNER",
            "p95": "Only predeclared O512 equal-workload buckets with >=100 eligible requests",
            "full_performance_qualification": "BLOCKED if required observable metrics/state conditions are absent",
        })

    def protocols_and_queue(self):
        base = synthetic("chinese_analysis", "1+1等于几？")
        base["max_tokens"] = 128
        base["enable_thinking"] = False
        base.pop("reasoning_effort")
        for stream in [False, True]:
            for port in [18030, 18343]:
                body = copy.deepcopy(base)
                body["stream"] = stream
                self.request(f"protocol-chat-{port}-{stream}", body, group="protocol", port=port)
            anthropic = count_body(base)
            anthropic["stream"] = stream
            self.request(f"protocol-messages-{stream}", anthropic, group="protocol",
                         path="/v1/messages", extra={"sse_parser": "raw protocol-specific frames retained"})
            responses = {"model": MODEL, "input": "用中文回答1+1等于几？", "max_output_tokens": 128,
                         "stream": stream, "chat_template_kwargs": {"enable_thinking": False}}
            self.request(f"protocol-responses-{stream}", responses, group="protocol",
                         path="/v1/responses", extra={"sse_parser": "raw protocol-specific frames retained"})
        for clients in [2, 4]:
            self.idle()
            with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as pool:
                futures = []
                for i in range(clients):
                    body = synthetic("free_java", f"Queue client {i}: implement a bounded retry loop.")
                    body["max_tokens"] = 512
                    futures.append(pool.submit(self.request, f"queue-{clients}-{i}", body,
                                               group="C1_queue", concurrent=True))
                for f in futures:
                    f.result()
        body = synthetic("free_java", "Write a long implementation and tests.")
        body["max_tokens"] = 8192
        self.request("cancel-disconnect", body, group="disconnect", disconnect_after=2)
        self.request("cancel-next-request", base, group="disconnect_recovery")
        named = synthetic("tool_json", "Call audit_record.")
        named["tool_choice"] = {"type": "function", "function": {"name": "audit_record"}}
        self.request("unsupported-named-tool", named, group="negative_contract", expected_status=400)

    def bridge(self):
        runner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def setup(self):
                super().setup()
                self.connection.settimeout(60)
            def log_message(self, format, *args):
                pass
            def start_response(self, status, headers):
                self.send_response(status)
                for key, value in headers.items():
                    if key.lower() in ("content-type", "x-request-id"):
                        self.send_header(key, value)
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                self.headers_sent = True
            def write_chunk(self, chunk):
                self.wfile.write(chunk)
                self.wfile.flush()
            def do_GET(self):
                if self.path == "/health":
                    value = {"status": "ok", "collector": True}
                elif self.path == "/v1/models":
                    value = simple_http("/v1/models", port=18343)
                else:
                    self.send_error(404)
                    return
                data = encode(value)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def do_POST(self):
                self.headers_sent = False
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 16*1024*1024:
                    self.send_error(413)
                    return
                try:
                    body = json.loads(self.rfile.read(length))
                    case_id = "closed-loop-"+str(time.time_ns())
                    runner.request(case_id, body, group="closed_loop_request", port=18343,
                                   timeout=2400, relay=self,
                                   extra={"local_case_header": self.headers.get("X-Baseline-Case")})
                    runner.update(state="BRIDGE_WAITING", current_case=None)
                except Exception as exc:
                    runner.update(state="NEEDS_ATTENTION", error=type(exc).__name__+": "+str(exc))
                    runner.stop.set()
                    if not self.headers_sent:
                        self.send_error(502, "Collector failed; inspect private evidence")
                finally:
                    self.close_connection = True
                    runner.summarize()
        self.update(state="BRIDGE_WAITING", current_case=None)
        server = http.server.HTTPServer(("127.0.0.1", 18090), Handler)
        server.timeout = 2
        try:
            while not self.stop.is_set():
                server.handle_request()
        finally:
            server.server_close()
        if self.status["state"] == "NEEDS_ATTENTION":
            raise RuntimeError(self.status.get("error", "collector bridge failed"))

    def summarize(self):
        rows = list(self.results.values())
        groups = {}
        for r in rows:
            g = groups.setdefault(r["group"], {"recorded": 0, "with_gaps": 0, "elapsed_s": 0})
            g["recorded"] += 1
            g["with_gaps"] += bool(r["failures"])
            g["elapsed_s"] += r["elapsed_s"]
        buckets = {}
        for r in rows:
            name = r["extra"].get("p95_bucket")
            if name:
                key = name+"-"+r["cache"]
                buckets.setdefault(key, []).append(r)
        out = {}
        for name, values in buckets.items():
            valid = [x for x in values if not x["failures"]]
            elapsed = sorted(x["elapsed_s"] for x in valid)
            out[name] = {"recorded_n": len(values), "eligible_n": len(valid),
                         "status": "ESTIMABLE" if len(valid) >= 100 else "INCONCLUSIVE",
                         "median_s": statistics.median(elapsed) if elapsed else None,
                         "p95_s": elapsed[math.ceil(.95*len(elapsed))-1] if len(elapsed) >= 100 else None,
                         "actual_prompt_tokens": sorted(set(x["prompt_tokens"] for x in values
                                                             if x["prompt_tokens"] is not None)),
                         "bootstrap_ci": None, "bootstrap_status": "PENDING_FINAL_CLUSTER_BOOTSTRAP"}
        atomic(self.root / "summary.json", {
            "updated_utc": utc(), "run_state": self.status["state"], "requests": len(rows),
            "groups": groups, "p95_buckets": out, "optimization_changes": False,
            "qualification": "MEASUREMENTS_ONLY_PENDING_COMPLETENESS_AND_METRIC_GATES",
            "unavailable_metrics": MISSING,
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--stage", choices=["smoke", "all", "core", "pi", "supplemental", "bridge"], default="all")
    parser.add_argument("--skip-full-hash", action="store_true", help="Only for bounded collector smoke")
    args = parser.parse_args()
    os.umask(0o077)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_root = next((p for p in root.resolve().parents if p.name == "ninfer-baseline-20261020"),
                     root.parent)
    with (lock_root / "baseline-gpu.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = Runner(root, smoke=args.stage == "smoke")
        runner.start_monitor()
        def signal_handler(signum, frame):
            runner.stop.set()
            runner.update(state="STOPPING", signal=signum)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        try:
            runner.idle()
            runner.fingerprint("startup-"+str(int(time.time())), full=not args.skip_full_hash)
            if args.stage == "bridge":
                runner.bridge()
            if args.stage in ("all", "core", "smoke"):
                if args.stage == "all":
                    runner.service_cold()
                    runner.observer_overhead()
                    runner.stability()
                runner.core()
            if args.stage in ("all", "pi"):
                runner.pi()
            if args.stage in ("all", "supplemental"):
                runner.capacity_boundaries()
                runner.supplemental()
            runner.fingerprint("end-"+str(int(time.time())))
            if args.stage == "all":
                runner.update(state="ANALYZING", current_case=None, request_deadline_utc=None)
                analysis_output = command([
                    "python3", str(Path(__file__).with_name("analyze.py")),
                    "--root", str(root), "--output", str(root / "analysis"), "--verify-raw"], timeout=2400)
                (root / "analysis-command.log").write_text(analysis_output+"\n")
            runner.update(state="MEASUREMENT_STAGES_FINISHED", current_case=None, finished_utc=utc())
        except BaseException as exc:
            runner.update(state="NEEDS_ATTENTION", error=type(exc).__name__+": "+str(exc),
                          finished_utc=utc())
            (root / "failure.txt").write_text(traceback.format_exc())
            raise
        finally:
            runner.summarize()
            runner.stop.set()


if __name__ == "__main__":
    main()
