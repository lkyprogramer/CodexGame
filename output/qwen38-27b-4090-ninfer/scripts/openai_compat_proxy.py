#!/usr/bin/env python3
"""llama.cpp-shaped OpenAI shim in front of ninfer-serve.

- Listen 0.0.0.0:18343, upstream 127.0.0.1:18030.
- Public model id matches WORK: openclaw/Qwen3.8-27B-WORK.
- Lift chat_template_kwargs.enable_thinking / reasoning_effort (ninfer 400s those keys).
- Default reasoning_effort=medium when thinking is on and the client omitted it
  (ninfer would otherwise render xhigh).
- GET /v1/models returns both OpenAI `data` and llama.cpp `models`.
"""
from __future__ import annotations

import json
import os
import socket
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

PUBLIC_MODEL = os.environ.get("NINFER_PUBLIC_MODEL", "openclaw/Qwen3.8-27B-WORK")
UPSTREAM_HOST = os.environ.get("NINFER_UPSTREAM_HOST", "127.0.0.1")
UPSTREAM_PORT = int(os.environ.get("NINFER_UPSTREAM_PORT", "18030"))
BIND_HOST = os.environ.get("NINFER_BIND_HOST", "0.0.0.0")
BIND_PORT = int(os.environ.get("NINFER_BIND_PORT", "18343"))
CONTEXT_WINDOW = int(os.environ.get("NINFER_CONTEXT_WINDOW", "262144"))
ALIASES = {
    PUBLIC_MODEL,
    "qwen3.8-27b",
    "qwen3.8-27B",
    "Qwen3.8-27B-WORK",
    "openclaw/Qwen3.8-27B",
}

HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def inject_openai_usage(obj: dict[str, Any], cache_n: int | None = None) -> int:
    """Fill OpenAI usage.prompt_tokens_details.cached_tokens from timings.cache_n.

    Returns the latest known cache hit count so stream chunks can carry it forward.
    """
    timings = obj.get("timings")
    if isinstance(timings, dict) and timings.get("cache_n") is not None:
        cache_n = _as_int(timings.get("cache_n"), cache_n or 0)
    usage = obj.get("usage")
    if not isinstance(usage, dict):
        return cache_n or 0
    cached = cache_n if cache_n is not None else 0
    details = usage.get("prompt_tokens_details")
    if not isinstance(details, dict):
        details = {}
    if details.get("cached_tokens") is None:
        details["cached_tokens"] = cached
    details.setdefault("cache_write_tokens", 0)
    usage["prompt_tokens_details"] = details
    ctd = usage.get("completion_tokens_details")
    if not isinstance(ctd, dict):
        ctd = {}
    ctd.setdefault("reasoning_tokens", 0)
    usage["completion_tokens_details"] = ctd
    obj["usage"] = usage
    return _as_int(details.get("cached_tokens"), cached)


def inject_openai_usage_json(raw: bytes) -> bytes:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw
    if isinstance(obj, dict):
        inject_openai_usage(obj)
        return json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return raw


def rewrite_sse_event(event: bytes, cache_n: int) -> tuple[bytes, int]:
    lines = event.split(b"\n")
    out: list[bytes] = []
    for line in lines:
        payload = line
        prefix = b""
        if line.startswith(b"data:"):
            prefix = b"data:"
            payload = line[5:]
            if payload.startswith(b" "):
                prefix += b" "
                payload = payload[1:]
        stripped = payload.strip()
        if prefix and stripped and stripped != b"[DONE]":
            try:
                obj = json.loads(stripped.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                out.append(line)
                continue
            if isinstance(obj, dict):
                cache_n = inject_openai_usage(obj, cache_n)
                line = prefix + json.dumps(obj, ensure_ascii=False).encode("utf-8")
        out.append(line)
    return b"\n".join(out), cache_n


def rewrite_body(raw: bytes, content_type: str) -> bytes:
    if "json" not in content_type.lower():
        return raw
    try:
        body: Any = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw
    if not isinstance(body, dict):
        return raw
    kwargs = body.get("chat_template_kwargs")
    if isinstance(kwargs, dict):
        if "enable_thinking" in kwargs and kwargs["enable_thinking"] is not None:
            body.setdefault("enable_thinking", kwargs["enable_thinking"])
        if "reasoning_effort" in kwargs and kwargs["reasoning_effort"] is not None:
            body.setdefault("reasoning_effort", kwargs["reasoning_effort"])
        if "preserve_thinking" in kwargs and kwargs["preserve_thinking"] is not None:
            body.setdefault("preserve_thinking", kwargs["preserve_thinking"])
        body.pop("chat_template_kwargs", None)
    thinking = body.get("enable_thinking")
    if thinking is False:
        body["reasoning_effort"] = "none"
    else:
        body.setdefault("reasoning_effort", "medium")
        if thinking is None:
            body["enable_thinking"] = True
    model = body.get("model")
    if isinstance(model, str) and model in ALIASES:
        body["model"] = PUBLIC_MODEL
    opts = body.get("stream_options")
    if isinstance(opts, dict):
        include = opts.get("include_usage")
        body["stream_options"] = {"include_usage": bool(include)} if include is not None else {}
        if not body["stream_options"]:
            body.pop("stream_options", None)
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def llama_models_payload(upstream: dict[str, Any]) -> dict[str, Any]:
    created = 0
    data = upstream.get("data") if isinstance(upstream.get("data"), list) else []
    if data and isinstance(data[0], dict):
        created = int(data[0].get("created") or 0)
        data[0]["id"] = PUBLIC_MODEL
        data[0]["owned_by"] = data[0].get("owned_by") or "ninfer"
        data[0]["aliases"] = [PUBLIC_MODEL]
        meta = data[0].setdefault("meta", {})
        if isinstance(meta, dict):
            meta.setdefault("n_ctx", CONTEXT_WINDOW)
            meta.setdefault("n_ctx_train", CONTEXT_WINDOW)
    else:
        data = [
            {
                "id": PUBLIC_MODEL,
                "object": "model",
                "created": created,
                "owned_by": "ninfer",
                "aliases": [PUBLIC_MODEL],
                "meta": {"n_ctx": CONTEXT_WINDOW, "n_ctx_train": CONTEXT_WINDOW},
            }
        ]
    return {
        "object": "list",
        "data": data,
        "models": [
            {
                "name": PUBLIC_MODEL,
                "model": PUBLIC_MODEL,
                "modified_at": "",
                "size": "",
                "digest": "",
                "type": "model",
                "description": "",
                "tags": [""],
                "capabilities": ["completion"],
                "parameters": "",
                "details": {
                    "parent_model": "",
                    "format": "ninfer",
                    "family": "qwen3",
                    "families": ["qwen3"],
                    "parameter_size": "27B",
                    "quantization_level": "groupwise-int",
                },
            }
        ],
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:
        self._forward()

    def do_POST(self) -> None:
        self._forward()

    def do_PUT(self) -> None:
        self._forward()

    def do_DELETE(self) -> None:
        self._forward()

    def do_OPTIONS(self) -> None:
        self._forward()

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        ctype = self.headers.get("Content-Type") or ""
        if self.command in {"POST", "PUT", "PATCH"} and raw:
            raw = rewrite_body(raw, ctype)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"
        headers["Connection"] = "close"
        if raw:
            headers["Content-Length"] = str(len(raw))
            if ctype:
                headers["Content-Type"] = ctype.split(";")[0] + "; charset=utf-8" if "json" in ctype else ctype
        conn = HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=1800)
        try:
            conn.request(self.command, self.path, body=raw or None, headers=headers)
            resp = conn.getresponse()
            content_type = resp.getheader("Content-Type") or "application/json"
            models_path = self.command == "GET" and self.path.rstrip("/") in {
                "/v1/models",
                "/models",
            }
            if models_path:
                payload = resp.read()
                try:
                    payload = json.dumps(
                        llama_models_payload(json.loads(payload.decode("utf-8"))),
                        ensure_ascii=False,
                    ).encode("utf-8")
                    content_type = "application/json"
                except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    pass
                self.send_response(resp.status, resp.reason)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)
                return
            is_sse = "event-stream" in content_type.lower()
            is_json = "json" in content_type.lower() and not is_sse
            if is_json:
                payload = inject_openai_usage_json(resp.read())
                self.send_response(resp.status, resp.reason)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(payload)
                return
            self.send_response(resp.status, resp.reason)
            skip = HOP | {"content-length"}
            for key, val in resp.getheaders():
                if key.lower() in skip or key.lower() == "content-type":
                    continue
                self.send_header(key, val)
            self.send_header("Content-Type", content_type)
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                pending = b""
                cache_n = 0
                while True:
                    buf = resp.read(8192)
                    if not buf:
                        break
                    if is_sse:
                        pending += buf
                        while b"\n\n" in pending or b"\r\n\r\n" in pending:
                            if b"\r\n\r\n" in pending and (
                                b"\n\n" not in pending
                                or pending.find(b"\r\n\r\n") < pending.find(b"\n\n")
                            ):
                                event, pending = pending.split(b"\r\n\r\n", 1)
                                sep = b"\r\n\r\n"
                            else:
                                event, pending = pending.split(b"\n\n", 1)
                                sep = b"\n\n"
                            rewritten, cache_n = rewrite_sse_event(event, cache_n)
                            out = rewritten + sep
                            self.wfile.write(b"%x\r\n" % len(out) + out + b"\r\n")
                            self.wfile.flush()
                    else:
                        self.wfile.write(b"%x\r\n" % len(buf) + buf + b"\r\n")
                        self.wfile.flush()
                if is_sse and pending:
                    rewritten, cache_n = rewrite_sse_event(pending, cache_n)
                    self.wfile.write(b"%x\r\n" % len(rewritten) + rewritten + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
        except (OSError, HTTPException, TimeoutError, socket.timeout) as exc:
            err = json.dumps(
                {
                    "error": {
                        "message": f"upstream ninfer unavailable: {exc}",
                        "type": "server_error",
                        "code": "upstream_error",
                    }
                }
            ).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)
        finally:
            conn.close()


def main() -> None:
    httpd = ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler)
    httpd.daemon_threads = True
    print(
        f"ninfer-compat proxy {BIND_HOST}:{BIND_PORT} -> {UPSTREAM_HOST}:{UPSTREAM_PORT} "
        f"model={PUBLIC_MODEL}",
        flush=True,
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
