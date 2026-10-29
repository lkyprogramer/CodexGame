"""Operational image/API probe; synthetic input never supplies quality evidence.

Run only against an otherwise idle, exclusively controlled candidate service.
Every HTTP payload/response and metrics snapshot is retained under a new out.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request

from ocrbench.client import HTTPFailure, VLLMClient, atomic_json


def parse_metrics(raw: str) -> dict:
    wanted = {"vllm:num_requests_running", "vllm:num_requests_waiting", "vllm:request_success_total"}
    values: dict[str, list[dict]] = {name: [] for name in wanted}
    pattern = re.compile(r'^([A-Za-z_:][A-Za-z0-9_:]*)(?:\{(.*)\})?\s+([^\s]+)(?:\s+\S+)?$')
    labels_pattern = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("(?:[^"\\]|\\.)*")')
    for line in raw.splitlines():
        matched = pattern.fullmatch(line.strip())
        if matched is None or matched[1] not in wanted:
            continue
        value = float(matched[3])
        if not math.isfinite(value) or value < 0:
            raise ValueError("Invalid runtime metric value")
        labels = {name: json.loads(encoded) for name, encoded in labels_pattern.findall(matched[2] or "")}
        values[matched[1]].append({"value": value, "labels": labels})
    running = values["vllm:num_requests_running"]
    waiting = values["vllm:num_requests_waiting"]
    aborts = [item for item in values["vllm:request_success_total"] if item["labels"].get("finished_reason") == "abort"]
    return {
        "running": sum(item["value"] for item in running) if running else None,
        "waiting": sum(item["value"] for item in waiting) if waiting else None,
        "aborts": sum(item["value"] for item in aborts) if aborts else None,
        "samples": values,
    }


def _get(url: str, destination: Path, api_key: str) -> tuple[int | None, str, str | None]:
    started = time.monotonic()
    status, raw, error = None, b"", None
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + api_key})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw, error = exc.code, exc.read(), str(exc)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    text = raw.decode("utf-8", "replace")
    destination.write_text(text, encoding="utf-8")
    atomic_json(destination.with_name(destination.name + ".http.json"), {
        "url": url, "http_status": status, "error": error,
        "wall_seconds": time.monotonic() - started,
    })
    return status, text, error


class Metrics:
    def __init__(self, root_url: str, out: Path, api_key: str):
        self.url = root_url + "/metrics"
        self.out, self.api_key, self.index = out, api_key, 0
        self.out.mkdir()

    def snapshot(self, phase: str) -> dict:
        self.index += 1
        status, text, error = _get(self.url, self.out / f"{self.index:04d}-{phase}.prom", self.api_key)
        result = {"phase": phase, "monotonic_timestamp": time.monotonic(), "http_status": status}
        try:
            if status != 200:
                raise ValueError(error or "Metrics endpoint unavailable")
            result.update(parse_metrics(text))
        except Exception as exc:
            result.update(running=None, waiting=None, aborts=None, error=str(exc))
        return result


def cancellation_probe(client: VLLMClient, payload: dict, metrics: Metrics, out: Path,
                       disconnect_after: float, drain_timeout: float) -> dict:
    """Observe an active request, disconnect, and require abort-counter evidence."""
    samples = [metrics.snapshot("before-disconnect-test")]
    baseline = samples[0]
    result = {"status": "UNAVAILABLE", "queue_drain_status": "UNAVAILABLE",
              "exclusive_candidate_service_required": True, "samples": samples,
              "disconnect_after_seconds": disconnect_after, "request_result": {},
              "abort_counter_source": "vllm:request_success_total{finished_reason=abort}",
              "claim": "No model quality or throughput result"}
    if baseline["running"] is None or baseline["waiting"] is None:
        result["reason"] = "No reliable running/waiting metrics"
        return result
    if baseline["running"] != 0 or baseline["waiting"] != 0:
        result["status"] = "FAIL"
        result["reason"] = "Candidate service was not idle; cancellation attribution invalid"
        return result
    finished = threading.Event()
    started = time.monotonic()
    deadline = started + disconnect_after

    def request():
        try:
            value = client._post("completion", payload, deadline, out / "disconnect-generation")
            result["request_result"] = {"status": "COMPLETED_BEFORE_DISCONNECT", "response": value}
        except TimeoutError as exc:
            result["request_result"] = {"status": "CLIENT_TIMEOUT", "error": str(exc)}
        except Exception as exc:
            result["request_result"] = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        finally:
            result["client_wall_seconds"] = time.monotonic() - started
            finished.set()

    thread = threading.Thread(target=request, name="runtime-disconnect-probe", daemon=True)
    thread.start()
    observed_active = False
    while not finished.is_set():
        sample = metrics.snapshot("while-request-active")
        samples.append(sample)
        observed_active |= (sample["monotonic_timestamp"] < deadline and
                            (sample["running"] or 0) + (sample["waiting"] or 0) > 0)
        finished.wait(0.05)
    thread.join(timeout=1)
    result["observed_active_before_disconnect"] = observed_active
    if result["request_result"].get("status") != "CLIENT_TIMEOUT":
        result["reason"] = "No timeout of an active request; cancellation was not exercised"
        return result
    end = time.monotonic() + drain_timeout
    idle_streak, saw_abort_delta = 0, False
    while time.monotonic() < end:
        sample = metrics.snapshot("after-client-disconnect")
        samples.append(sample)
        if sample["running"] == 0 and sample["waiting"] == 0:
            idle_streak += 1
        else:
            idle_streak = 0
        if baseline["aborts"] is not None and sample["aborts"] is not None:
            saw_abort_delta |= sample["aborts"] > baseline["aborts"]
        if idle_streak >= 3 and saw_abort_delta:
            break
        time.sleep(min(0.2, max(0, end - time.monotonic())))
    result["queue_drain_status"] = "PASS" if idle_streak >= 3 else "FAIL"
    result["abort_counter_increased"] = saw_abort_delta
    if idle_streak < 3:
        result.update(status="FAIL", reason="Running/waiting did not remain zero within drain timeout")
    elif not observed_active:
        result["reason"] = "Request activity was not observed; queue drain does not prove abort"
    elif baseline["aborts"] is None or not saw_abort_delta:
        result["reason"] = "Queue drained, but no reliable abort counter increase; natural completion is possible"
    else:
        result.update(status="PASS", reason="Active request timed out; abort counter grew and queue stayed idle")
    return result


def _shared_payload(image: Path, prompt: str, model: str) -> dict:
    mime = mimetypes.guess_type(image.name)[0] or "image/png"
    return {"model": model, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(image.read_bytes()).decode("ascii")}},
        {"type": "text", "text": prompt},
    ]}], "chat_template_kwargs": {"enable_thinking": False}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Candidate OpenAI URL ending in /v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--image", type=Path, help="Local development image; not GT or a quality test")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--disconnect-after", type=float, default=0.5)
    parser.add_argument("--drain-timeout", type=float, default=15)
    args = parser.parse_args(argv)
    if not args.base_url.rstrip("/").endswith("/v1"):
        parser.error("base-url must end in /v1")
    if min(args.timeout, args.disconnect_after, args.drain_timeout) <= 0:
        parser.error("timeouts must be positive")
    args.out.mkdir(parents=True, exist_ok=False)
    api_key = os.environ.get("OCR_API_KEY", "local-only")
    client = VLLMClient(args.base_url, args.model, api_key)
    root_url = args.base_url.rstrip("/")[:-3]
    report = {"kind": "OPERATIONAL_PROBE_NOT_QUALITY_BENCHMARK", "model": args.model,
              "base_url": args.base_url, "context_expected": 16384, "checks": {},
              "neutral_sampling": {"temperature": 0.0, "top_p": 1.0, "top_k": -1,
                                   "repetition_penalty": 1.0, "seed": 20261028,
                                   "chat_template_kwargs": {"enable_thinking": False}},
              "effective_server_config_claim": "Request fields observed; engine launch flags must be checked separately"}
    image = args.image
    if image is None:
        from PIL import Image, ImageDraw
        image = args.out / "synthetic-api-probe.png"
        canvas = Image.new("RGB", (1024, 256), "white")
        ImageDraw.Draw(canvas).text((30, 30), "OCR runtime probe 20261028\nPage 1: 12345 + 67890 = 80235\nSynthetic input; not a quality sample.", fill="black")
        canvas.save(image)
    if not image.is_file():
        parser.error("image does not exist")
    report["input"] = {"path": str(image.resolve()), "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                       "synthetic": args.image is None, "quality_evidence": False}
    prompt_file = args.prompt_file
    if prompt_file is None and (args.model_dir / "prompts" / "plain_ocr.txt").is_file():
        prompt_file = args.model_dir / "prompts" / "plain_ocr.txt"
    prompt = prompt_file.read_text(encoding="utf-8") if prompt_file else "Text Recognition:"
    report["prompt"] = {"source": str(prompt_file) if prompt_file else "Mini native Text Recognition task",
                        "sha256": hashlib.sha256(prompt.encode()).hexdigest()}
    status, raw, error = _get(args.base_url.rstrip("/") + "/models", args.out / "models.raw.json", api_key)
    try:
        ids = [entry["id"] for entry in json.loads(raw)["data"]]
        report["checks"]["model_listing"] = {"status": "PASS" if status == 200 and args.model in ids else "FAIL", "ids": ids}
    except Exception:
        report["checks"]["model_listing"] = {"status": "FAIL", "http_status": status, "error": error}
    normal = client.complete([image], prompt, 4096, time.monotonic() + args.timeout, args.out / "normal", "probe-normal")
    report["checks"]["image_tokenize_completion_usage"] = normal
    length = client.complete([image], prompt, 1, time.monotonic() + args.timeout, args.out / "forced-length", "probe-length")
    report["checks"]["forced_length"] = {"status": "PASS" if length.get("finish_reason") == "length" and length["status"] == "FAIL" else "UNAVAILABLE",
                                          "reason": "Expected truncation retained as failure" if length.get("finish_reason") == "length" else "One-token output did not reproduce length finish",
                                          "response": length}
    shared = _shared_payload(image, prompt, args.model)
    neutral = report["neutral_sampling"]
    for name, overrides, expected in (
        ("unknown_model", {"model": "ocr-probe-intentionally-missing-model", "max_tokens": 1}, {400, 404}),
        ("context_overflow", {"max_tokens": 16385}, {400, 422}),
    ):
        try:
            response = client._post("completion", dict(shared, **neutral, stream=False, **overrides), time.monotonic() + args.timeout, args.out / name)
            report["checks"][name] = {"status": "FAIL", "reason": "Invalid request was accepted", "response": response}
        except HTTPFailure as exc:
            report["checks"][name] = {"status": "PASS" if exc.status in expected else "FAIL", "http_status": exc.status, "reason": str(exc)}
        except Exception as exc:
            report["checks"][name] = {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}
    if normal["status"] == "PASS":
        budget = min(8192, 16384 - normal["input_tokens"] - 512)
        payload = dict(shared, **neutral, max_tokens=budget, stream=False)
        report["checks"]["disconnect_abort_and_drain"] = cancellation_probe(
            client, payload, Metrics(root_url, args.out / "metrics", api_key), args.out,
            args.disconnect_after, args.drain_timeout,
        )
    else:
        report["checks"]["disconnect_abort_and_drain"] = {"status": "UNAVAILABLE", "reason": "Valid image/token budget prerequisite failed"}
    statuses = [check["status"] for check in report["checks"].values()]
    report["status"] = "FAIL" if "FAIL" in statuses else "PASS" if all(s == "PASS" for s in statuses) else "UNAVAILABLE"
    atomic_json(args.out / "probe-result.json", report)
    print(json.dumps({"status": report["status"], "out": str(args.out), "checks": {k: v["status"] for k, v in report["checks"].items()}}))
    return 0 if report["status"] == "PASS" else 1 if report["status"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
