import json
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image

from ocrbench.client import VLLMClient


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append((self.path, data))
        status, body = self.server.respond(self.path, data)
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except BrokenPipeError:
            # The timeout test deliberately closes its socket before reply.
            pass


def normal_response(path, _):
    if path == "/tokenize":
        return 200, {"count": 1000, "tokens": [1] * 1000, "max_model_len": 16384}
    return 200, {"id": "fake", "choices": [{"message": {"content": "abc"}, "finish_reason": "stop"}],
                 "usage": {"prompt_tokens": 1000, "completion_tokens": 3}}


class Server:
    def __init__(self, respond=normal_response, handler=Handler):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.server.requests = []
        self.server.respond = respond

    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root / "image.png"
        Image.new("RGB", (30, 30), "white").save(self.image)

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, server):
        return VLLMClient(server.url, "model").complete(
            [self.image], "recognize", 4096, time.monotonic() + 5, self.root / "evidence", "id")

    def test_actual_multimodal_budget_and_raw_evidence(self):
        with Server() as server:
            result = self.invoke(server)
            self.assertEqual(result["status"], "PASS")
            paths = [p for p, _ in server.server.requests]
            self.assertEqual(paths, ["/tokenize", "/v1/chat/completions"])
            token_payload = server.server.requests[0][1]
            complete_payload = server.server.requests[1][1]
            self.assertEqual(token_payload["messages"], complete_payload["messages"])
            self.assertEqual(complete_payload["max_tokens"], 4096)
            self.assertEqual(complete_payload["temperature"], 0)
            self.assertNotIn("no_repeat_ngram_size", complete_payload)
        self.assertTrue((self.root / "evidence" / "01-tokenize.request.json").is_file())
        self.assertTrue((self.root / "evidence" / "02-completion.response.json").is_file())

    def test_budget_overflow_never_calls_generation(self):
        def respond(path, data):
            return 200, {"count": 16000, "tokens": [1] * 16000, "max_model_len": 16384}
        with Server(respond) as server:
            result = self.invoke(server)
            self.assertEqual(result["status"], "FAIL_BUDGET")
            self.assertEqual(len(server.server.requests), 1)
            self.assertEqual(result["attempts"], [{"phase": "tokenize", "attempt": 1, "status": "PASS"}])

    def test_count_mismatch_and_unsupported_endpoint_fail_closed(self):
        for response in [(404, {"error": "missing"}),
                         (200, {"count": 10, "tokens": [1], "max_model_len": 16384})]:
            with self.subTest(response=response), Server(lambda p, d: response) as server:
                result = self.invoke(server)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(len(server.server.requests), 1)

    def test_transient_retry_is_bounded_and_usage_is_cross_checked(self):
        counts = {"completion": 0}
        def respond(path, data):
            if path != "/tokenize":
                counts["completion"] += 1
                if counts["completion"] <= 2:
                    return 503, {"error": "busy"}
            return normal_response(path, data)
        with Server(respond) as server:
            result = self.invoke(server)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(counts["completion"], 2)
            self.assertEqual(sum(attempt["phase"] == "completion" for attempt in result["attempts"]), 2)
        def mismatch(path, data):
            status, value = normal_response(path, data)
            if path != "/tokenize":
                value["usage"]["prompt_tokens"] = 999
            return status, value
        with Server(mismatch) as server:
            self.assertIn("COUNT_MISMATCH", self.invoke(server)["error"])

    def test_length_is_failure_with_raw_content_retained(self):
        def respond(path, data):
            status, value = normal_response(path, data)
            if path != "/tokenize":
                value["choices"][0]["finish_reason"] = "length"
            return status, value
        with Server(respond) as server:
            result = self.invoke(server)
            self.assertEqual(result["content"], "abc")
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["error"], "TRUNCATED_OUTPUT")

    def test_actual_input_reduces_budget_and_timeout_has_no_retry(self):
        def large_input(path, data):
            if path == "/tokenize":
                return 200, {"count": 15500, "tokens": [1] * 15500, "max_model_len": 16384}
            status, value = normal_response(path, data)
            value["usage"]["prompt_tokens"] = 15500
            return status, value
        with Server(large_input) as server:
            result = self.invoke(server)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(server.server.requests[-1][1]["max_tokens"], 372)

        def slow(path, data):
            time.sleep(0.5)
            return normal_response(path, data)
        with Server(slow) as server:
            started = time.monotonic()
            result = VLLMClient(server.url, "model").complete(
                [self.image], "recognize", 100, started + 0.1, self.root / "timeout", "id")
            self.assertLess(time.monotonic() - started, 0.4)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(len(server.server.requests), 1)

    def test_absolute_deadline_interrupts_trickling_http_headers(self):
        class SlowHeaderHandler(Handler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                try:
                    self.wfile.write(b"HTTP/1.1 200 OK\r\n")
                    for byte in b"Content-Length: 2\r\n\r\n{}":
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(0.025)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        with Server(handler=SlowHeaderHandler) as server:
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                VLLMClient(server.url, "model")._post(
                    "tokenize", {"x": 1}, started + 0.1, self.root / "slow-header")
            self.assertLess(time.monotonic() - started, 0.3)


if __name__ == "__main__":
    unittest.main()
