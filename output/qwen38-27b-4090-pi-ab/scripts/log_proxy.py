#!/usr/bin/env python3
"""HTTP reverse proxy: 127.0.0.1:18444 -> 127.0.0.1:18343 (ssh tunnel).

Logs tools/system hashes and usage.timings without storing full prompts.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LISTEN = ("127.0.0.1", 18444)
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/pi-proxy.jsonl")
UPSTREAM = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:18343"


def sha(obj) -> str | None:
    if obj is None:
        return None
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("proxy " + (fmt % args) + "\n")

    def _forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        url = UPSTREAM + self.path
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
        headers["Host"] = "127.0.0.1:18343"
        req = urllib.request.Request(url, data=body or None, headers=headers, method=self.command)
        t0 = time.time()
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "method": self.command,
            "path": self.path,
        }
        if body and "chat/completions" in self.path:
            try:
                payload = json.loads(body.decode())
            except Exception:
                payload = {}
            msgs = payload.get("messages") or []
            rec.update(
                {
                    "n_messages": len(msgs),
                    "n_tools": len(payload.get("tools") or []),
                    "tool_choice": payload.get("tool_choice"),
                    "model": payload.get("model"),
                    "max_tokens": payload.get("max_tokens"),
                    "temperature": payload.get("temperature"),
                    "has_template_kwargs": bool(payload.get("chat_template_kwargs")),
                    "sha_tools": sha(payload.get("tools")),
                    "sha_system": sha(next((m.get("content") for m in msgs if m.get("role") == "system"), None)),
                    "roles": [m.get("role") for m in msgs],
                }
            )
        try:
            with urllib.request.urlopen(req, timeout=1800) as resp:
                data = resp.read()
                status = resp.status
                out_headers = dict(resp.headers)
        except urllib.error.HTTPError as e:
            data = e.read()
            status = e.code
            out_headers = dict(e.headers)
        except Exception as e:
            rec["error"] = str(e)
            rec["wall_s"] = round(time.time() - t0, 3)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            with OUT.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.send_error(502, str(e))
            return
        rec["http"] = status
        rec["wall_s"] = round(time.time() - t0, 3)
        text = data.decode("utf-8", errors="replace")
        parsed = None
        try:
            parsed = json.loads(text)
        except Exception:
            # Pi uses SSE streaming; take the last JSON payload.
            for line in reversed(text.splitlines()):
                line = line.strip()
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line.startswith("{") and "usage" in line:
                    try:
                        parsed = json.loads(line)
                        rec["stream"] = True
                        break
                    except Exception:
                        continue
        try:
            if not parsed:
                raise ValueError("no json")
            usage = parsed.get("usage") or {}
            timings = usage.get("timings") or parsed.get("timings") or {}
            rec["prompt_tokens"] = usage.get("prompt_tokens")
            rec["completion_tokens"] = usage.get("completion_tokens")
            rec["cache_hit"] = timings.get("cache_hit")
            rec["cached_prefix_tokens"] = timings.get("cached_prefix_tokens")
            rec["prefilled_tokens"] = timings.get("prefilled_tokens")
            rec["effective_prompt_tokens"] = timings.get("effective_prompt_tokens")
            rec["agent_turn_cache_hit"] = timings.get("agent_turn_cache_hit")
            rec["prefill_ms"] = timings.get("prefill_ms")
            rec["decode_ms"] = timings.get("decode_ms")
            ch = (parsed.get("choices") or [{}])[0]
            rec["finish"] = ch.get("finish_reason")
            rec["n_tool_calls"] = len((ch.get("message") or {}).get("tool_calls") or [])
        except Exception:
            rec["parse"] = "non-json"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.send_response(status)
        for k, v in out_headers.items():
            if k.lower() in ("transfer-encoding", "connection"):
                continue
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = _forward
    do_POST = _forward
    do_PUT = _forward
    do_DELETE = _forward
    do_OPTIONS = _forward


def main() -> None:
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    httpd = http.server.ThreadingHTTPServer(LISTEN, Handler)
    print(f"proxy {LISTEN[0]}:{LISTEN[1]} -> {UPSTREAM} log={OUT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
