"""Minimal vLLM client with actual multimodal token budgeting and raw evidence."""
from __future__ import annotations

import base64
import http.client
import json
import mimetypes
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit


class HTTPFailure(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        import os
        os.fsync(stream.fileno())
    temporary.replace(path)


class VLLMClient:
    """HTTP timeout covers send and complete body read, within the page deadline.

    /tokenize must use the server's full multimodal chat preprocessing. A token
    count is subsequently checked against completion usage. An unknown endpoint
    is a failure rather than a fallback to text-only estimates.
    """

    def __init__(self, base_url: str, model: str, api_key: str = "local-only",
                 context_limit: int = 16384, seed: int = 20261028):
        parsed = urlsplit(base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url must be an HTTP(S) URL")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.context_limit = context_limit
        self.seed = seed
        self._url = parsed

    def _post(self, endpoint: str, payload: dict, deadline: float,
              evidence: Path) -> dict:
        atomic_json(evidence.with_suffix(".request.json"), payload)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("request deadline elapsed before dispatch")
        cls = http.client.HTTPSConnection if self._url.scheme == "https" else http.client.HTTPConnection
        connection = cls(self._url.hostname, self._url.port, timeout=remaining)
        prefix = self._url.path.rstrip("/")
        if endpoint == "tokenize":
            prefix = prefix[:-3] if prefix.endswith("/v1") else prefix
            route = prefix + "/tokenize"
        else:
            route = prefix + "/chat/completions"
        started = time.monotonic()
        status = None
        raw = bytearray()
        expired = threading.Event()
        live_socket = []

        def abort_at_deadline():
            expired.set()
            # Closing a socket from another thread alone does not reliably wake
            # blocked recv on Linux; shutdown does. Retain the socket even when
            # http.client has detached it for a Connection: close response.
            for sock in live_socket:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()

        timer = threading.Timer(remaining, abort_at_deadline)
        timer.daemon = True
        timer.start()
        try:
            connection.connect()
            live_socket.append(connection.sock)
            if expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError("HTTP connect exceeded request deadline")
            connection.sock.settimeout(max(0.001, deadline - time.monotonic()))
            connection.request("POST", route, body=json.dumps(payload).encode(), headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + self.api_key,
            })
            connection.sock.settimeout(max(0.001, deadline - time.monotonic()))
            response = connection.getresponse()
            if expired.is_set():
                raise TimeoutError("HTTP headers exceeded request deadline")
            status = response.status
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("HTTP response exceeded request deadline")
                # read1 performs at most one underlying read; a trickling response
                # therefore cannot reset an unlimited per-read timeout.
                raw_stream = getattr(getattr(response, "fp", None), "raw", None)
                sock = connection.sock or getattr(raw_stream, "_sock", None)
                if hasattr(sock, "settimeout"):
                    sock.settimeout(remaining)
                chunk = response.read1(65536)
                if not chunk:
                    break
                raw.extend(chunk)
            body = raw.decode("utf-8")
            if expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError("HTTP response exceeded request deadline")
            atomic_json(evidence.with_suffix(".response.json"), {
                "http_status": status, "body": body,
                "wall_seconds": time.monotonic() - started,
            })
            if not 200 <= status < 300:
                raise HTTPFailure(status, body)
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError("HTTP response must be an object")
            return value
        except (socket.timeout, TimeoutError) as error:
            atomic_json(evidence.with_suffix(".response.json"), {
                "http_status": status, "partial_body": raw.decode("utf-8", "replace"),
                "error": str(error), "wall_seconds": time.monotonic() - started,
            })
            raise TimeoutError("HTTP request deadline exceeded") from error
        except Exception as error:
            if not evidence.with_suffix(".response.json").exists():
                atomic_json(evidence.with_suffix(".response.json"), {
                    "http_status": status, "error": str(error),
                    "wall_seconds": time.monotonic() - started,
                })
            if expired.is_set():
                raise TimeoutError("HTTP request deadline exceeded") from error
            raise
        finally:
            timer.cancel()
            connection.close()

    def complete(self, image_paths: list[Path], prompt: str, task_limit: int,
                 deadline: float, evidence_dir: Path, request_id: str) -> dict:
        if not image_paths or not all(Path(path).is_file() for path in image_paths):
            raise ValueError("one or more local image files are required")
        if not isinstance(prompt, str) or not prompt or not 1 <= task_limit <= 8192:
            raise ValueError("invalid task prompt or output limit")
        content = []
        for path in image_paths:
            path = Path(path)
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            content.append({"type": "image_url", "image_url": {
                "url": f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii"),
            }})
        content.append({"type": "text", "text": prompt})
        shared = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "chat_template_kwargs": {"enable_thinking": False},
        }
        base = {"content": "", "finish_reason": None, "usage": None,
                "request_id": request_id, "status": "FAIL", "error": None,
                "attempts": [], "input_tokens": None, "effective_max_tokens": None}
        evidence_dir.mkdir(parents=True, exist_ok=True)
        # One transient retry total per logical call, including tokenization.
        retries_left = 1
        tokenized = None
        attempt = 0
        while True:
            attempt += 1
            phase = "tokenize" if tokenized is None else "completion"
            evidence = evidence_dir / f"{attempt:02d}-{phase}"
            try:
                if tokenized is None:
                    tokenized = self._post("tokenize", shared, deadline, evidence)
                    count = tokenized.get("count")
                    tokens = tokenized.get("tokens")
                    if (type(count) is not int or count <= 0 or not isinstance(tokens, list)
                            or count != len(tokens) or not all(type(x) is int for x in tokens)
                            or tokenized.get("max_model_len") != self.context_limit):
                        raise ValueError("UNVERIFIED_MULTIMODAL_TOKEN_COUNT_OR_CONTEXT")
                    base["input_tokens"] = count
                    budget = min(task_limit, 8192, self.context_limit - count - 512)
                    base["effective_max_tokens"] = budget
                    base["attempts"].append({"phase": phase, "attempt": attempt, "status": "PASS"})
                    if budget <= 0:
                        base.update(status="FAIL_BUDGET", error="No output budget after actual multimodal input and safety margin")
                        break
                    continue
                payload = dict(shared, temperature=0.0, top_p=1.0, top_k=-1,
                               repetition_penalty=1.0, seed=self.seed,
                               max_tokens=base["effective_max_tokens"], stream=False)
                response = self._post("completion", payload, deadline, evidence)
                choice = response["choices"][0]
                usage = response.get("usage")
                base.update(content=choice["message"].get("content") or "",
                            finish_reason=choice.get("finish_reason"), usage=usage,
                            server_request_id=response.get("id"))
                if not isinstance(base["content"], str):
                    raise ValueError("NON_TEXT_COMPLETION")
                if not isinstance(usage, dict) or usage.get("prompt_tokens") != base["input_tokens"]:
                    raise ValueError("TOKENIZE_COMPLETION_PROMPT_COUNT_MISMATCH")
                if base["finish_reason"] == "length":
                    base.update(status="FAIL", error="TRUNCATED_OUTPUT")
                elif base["finish_reason"] != "stop":
                    base.update(status="FAIL", error="UNEXPECTED_FINISH_REASON")
                else:
                    base["status"] = "PASS"
                base["attempts"].append({"phase": phase, "attempt": attempt, "status": base["status"]})
                break
            except Exception as error:
                base["attempts"].append({"phase": phase, "attempt": attempt, "status": "FAIL", "error": str(error)})
                transient = (isinstance(error, HTTPFailure) and error.status in {408, 429, 500, 502, 503, 504}) or isinstance(error, (ConnectionError, OSError))
                # A timeout consumes the original envelope; no new deadline.
                if transient and not isinstance(error, TimeoutError) and retries_left and deadline > time.monotonic():
                    retries_left -= 1
                    continue
                base["error"] = str(error)
                break
        atomic_json(evidence_dir / "result.json", base)
        return base
