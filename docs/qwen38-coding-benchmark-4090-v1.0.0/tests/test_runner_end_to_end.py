from __future__ import annotations

import difflib
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from qcb.catalog import load_task
from qcb.config import EndpointConfig, InferenceConfig, ModelConfig, RunConfig
from qcb.runner import run_task


class ResponseServer:
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.requests: list[dict[str, Any]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                outer.requests.append(payload)
                index = len(outer.requests) - 1
                response = outer.responses[min(index, len(outer.responses) - 1)]
                body = json.dumps(response).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"

    def __enter__(self) -> "ResponseServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def assistant(message: dict[str, Any], *, reasoning: int | None = None) -> dict[str, Any]:
    usage: dict[str, Any] = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    if reasoning is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning}
    return {"choices": [{"message": message}], "usage": usage, "timings": {"predicted_per_second": 12.5}}


class RunnerEndToEndTest(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def config(self, source: Path, base_url: str) -> RunConfig:
        return RunConfig(
            model=ModelConfig(id="fake-model", file="", sha256="", quantization="Q4_K_M"),
            endpoint=EndpointConfig(base_url=base_url, model="fake", timeout_seconds=5),
            inference=InferenceConfig(
                lane="normalized",
                temperature=0.0,
                top_p=1.0,
                top_k=0,
                min_p=0.0,
                seed=42,
                max_tokens=1024,
                context_size=32768,
                reasoning_effort="medium",
                mtp_enabled=False,
                tool_mode=True,
                max_tool_calls=8,
                max_retries=0,
                system_prompt_file="config/system-prompt.txt",
                extra_body={},
            ),
            source_path=source,
        )

    def test_patch_task_runs_tool_loop_and_hidden_verifier(self) -> None:
        task = load_task(self.root, "SF001")
        baseline = (task.workspace_dir / "src" / "RateLimiter.java").read_text(encoding="utf-8").splitlines(keepends=True)
        reference = (task.task_dir / "reference" / "src" / "RateLimiter.java").read_text(encoding="utf-8").splitlines(keepends=True)
        patch = "".join(difflib.unified_diff(baseline, reference, fromfile="a/src/RateLimiter.java", tofile="b/src/RateLimiter.java"))
        responses = [
            assistant({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "apply_patch", "arguments": json.dumps({"patch": patch})},
                }],
            }),
            assistant({"role": "assistant", "content": "Implemented and checked."}, reasoning=7),
        ]
        with tempfile.TemporaryDirectory() as temp, ResponseServer(responses) as server:
            source = Path(temp) / "config.toml"
            source.write_text("fake", encoding="utf-8")
            record = run_task(self.root, task, self.config(source, server.base_url), "smoke", Path(temp) / "results")
        self.assertTrue(record["verification"]["passed"], record["verification"])
        self.assertEqual(record["agent"]["tool_calls"], 1)
        self.assertEqual(record["agent"]["invalid_tool_calls"], 0)
        self.assertEqual(record["usage"]["reasoning_tokens"], 7)
        tool_names = {tool["function"]["name"] for tool in server.requests[0]["tools"]}
        self.assertIn("apply_patch", tool_names)

    def test_review_task_receives_read_only_tools_and_is_scored(self) -> None:
        task = load_task(self.root, "CR001")
        answer = (task.task_dir / "reference" / "answer.json").read_text(encoding="utf-8")
        responses = [
            assistant({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": json.dumps({"path": "src/JwtVerifier.java"})},
                }],
            }),
            assistant({"role": "assistant", "content": answer}),
        ]
        with tempfile.TemporaryDirectory() as temp, ResponseServer(responses) as server:
            source = Path(temp) / "config.toml"
            source.write_text("fake", encoding="utf-8")
            record = run_task(self.root, task, self.config(source, server.base_url), "smoke", Path(temp) / "results")
        self.assertTrue(record["verification"]["passed"], record["verification"])
        tool_names = {tool["function"]["name"] for tool in server.requests[0]["tools"]}
        self.assertEqual(tool_names, {"list_files", "read_file", "search"})
        self.assertEqual(record["agent"]["tool_calls"], 1)


if __name__ == "__main__":
    unittest.main()
