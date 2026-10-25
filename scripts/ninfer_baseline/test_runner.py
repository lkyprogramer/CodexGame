import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("baseline_runner", Path(__file__).with_name("runner.py"))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class CollectorTests(unittest.TestCase):
    def test_count_projection_preserves_tool_schema_and_missing_description(self):
        body = runner.synthetic("tool_json", "fixture")
        del body["tools"][0]["function"]["description"]
        projected = runner.count_body(body)
        self.assertNotIn("description", projected["tools"][0])
        self.assertEqual(projected["tools"][0]["input_schema"],
                         body["tools"][0]["function"]["parameters"])
        self.assertEqual(projected["output_config"], {"effort": "medium"})

    def test_count_projection_preserves_history_and_off(self):
        body = runner.synthetic("copy_patch", "fixture")
        body["enable_thinking"] = False
        body["messages"].extend([
            {"role": "assistant", "reasoning_content": "reason", "content": None,
             "tool_calls": [{"id": "t1", "type": "function", "function": {
                 "name": "read", "arguments": '{"path":"Main.java"}'}}]},
            {"role": "tool", "tool_call_id": "t1", "content": "class Main {}"},
        ])
        p = runner.count_body(body)
        self.assertEqual(p["thinking"], {"type": "disabled"})
        self.assertNotIn("output_config", p)
        self.assertEqual(p["messages"][1]["content"][1]["input"], {"path": "Main.java"})
        self.assertEqual(p["messages"][2]["content"][0]["tool_use_id"], "t1")

    def test_sse_chunk_is_not_token_and_reasoning_only_is_visible(self):
        lines = [
            {"elapsed_s": .1, "line": 'data: {"choices":[{"delta":{"role":"assistant"}}]}'},
            {"elapsed_s": .2, "line": 'data: {"choices":[{"delta":{"reasoning_content":"several tokens"}}]}'},
            {"elapsed_s": .3, "line": 'data: {"choices":[{"delta":{},"finish_reason":"length"}]}'},
            {"elapsed_s": .4, "line": "data: [DONE]"},
        ]
        p = runner.parse_sse(lines)
        self.assertEqual(p["first_payload_s"], .2)
        self.assertIsNone(p["first_content_s"])
        self.assertEqual(p["chunk_times_s"], [.2])
        self.assertTrue(p["sse_done"])
        self.assertEqual(p["finish_reason"], "length")

    def test_malformed_and_incomplete_tool_stream_are_retained(self):
        lines = [
            {"elapsed_s": .1, "line": "data: {broken"},
            {"elapsed_s": .2, "line": json.dumps({"dummy": "not SSE"})},
            {"elapsed_s": .3, "line": 'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"t","function":{"name":"read","arguments":"{"}}]}}]}'},
        ]
        p = runner.parse_sse(lines)
        self.assertEqual(p["malformed_data_events"], 1)
        self.assertFalse(p["sse_done"])
        self.assertFalse(p["tool_json_valid"])
        self.assertEqual(p["tool_count"], 1)

    def test_atomic_json_replaces_complete_record(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "status.json"
            runner.atomic(p, {"state": "A"})
            runner.atomic(p, {"state": "B", "n": 7})
            self.assertEqual(json.loads(p.read_text()), {"state": "B", "n": 7})
            self.assertFalse(p.with_suffix(".json.tmp").exists())

    def make_runner(self, root):
        (root / "expected-baseline.json").write_text("{}")
        return runner.Runner(root)

    def test_resume_detects_duplicate_durable_id(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "records.jsonl").write_text('{"id":"same"}\n{"id":"same"}\n')
            with self.assertRaisesRegex(RuntimeError, "duplicate"):
                self.make_runner(root)

    def test_partial_tail_and_complete_orphan_record_recover(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "records.jsonl").write_bytes(b'{"id":"first"}\n{"id":"partial')
            orphan = root / "requests/second"
            orphan.mkdir(parents=True)
            (orphan / "raw.json.gz").write_bytes(b"frozen raw")
            (orphan / "record.json").write_text(json.dumps({
                "id": "second", "raw_sha256": runner.sha(b"frozen raw")}))
            r = self.make_runner(root)
            self.assertEqual(set(r.results), {"first", "second"})
            self.assertEqual(len(list(root.glob("records-partial-tail-*"))), 1)
            self.assertEqual(len((root / "records.jsonl").read_text().splitlines()), 2)

    def test_connection_close_slow_stream_obeys_wall_deadline(self):
        class Slow(runner.http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("X-Request-Id", "slow")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    for _ in range(40):
                        self.wfile.write(b'data: {"choices":[{"delta":{"content":"x"}}]}\n\n')
                        self.wfile.flush()
                        time.sleep(.05)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        server = runner.http.server.HTTPServer(("127.0.0.1", 0), Slow)
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                log = root / "server.jsonl"
                log.write_text("")
                r = self.make_runner(root)
                r.idle = lambda **kw: []
                r.log_events = lambda *a: ([], 0)
                started = time.monotonic()
                with patch.object(runner, "LOG_PATH", log), \
                     patch.object(runner, "simple_http", return_value="metrics"):
                    with self.assertRaisesRegex(RuntimeError, "TRANSPORT_ERROR"):
                        r.request("slow", runner.synthetic("copy_patch", "fixture"), group="test",
                                  port=server.server_port, timeout=.2)
                self.assertLess(time.monotonic()-started, 1)
                raw = json.loads((root / "requests/slow/client-raw.json").read_text())
                self.assertEqual(raw["error"], "DEADLINE_EXCEEDED")
                self.assertTrue(raw["lines"])
        finally:
            server.server_close()
            thread.join(timeout=3)

    def test_final_wire_alignment_rechecks_after_nonce(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.make_runner(Path(d))
            body = runner.synthetic("copy_patch", "x" * 100)
            # A deterministic fake tokenizer tests correction around final wire.
            r.count = lambda b, name: len(b["messages"][1]["content"].rsplit("\n\n", 1)[0]) + 17
            aligned, count = r.align_final_count(body, 123, "test")
            self.assertEqual(count, 123)
            self.assertEqual(r.count(aligned, ""), 123)

    def test_final_wire_alignment_handles_token_count_jump(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.make_runner(Path(d))
            body = runner.synthetic("free_java", "x" * 100)
            instruction = body["messages"][1]["content"].rsplit("\n\n", 1)[1]
            def count(b, name):
                source = b["messages"][1]["content"].rsplit("\n\n", 1)[0]
                # Prefix truncation skips odd counts; a delimited suffix can fill the gap.
                return 17 + (len(source) // 2) * 2 + int(source.endswith(" x"))
            r.count = count
            aligned, n = r.align_final_count(body, 122, "jump")
            self.assertEqual(n, 122)
            self.assertEqual(count(aligned, ""), 122)
            self.assertEqual(aligned["messages"][1]["content"].rsplit("\n\n", 1)[1], instruction)

    def test_unknown_attempt_is_never_dispatched_again(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = self.make_runner(root)
            pending = root / "requests/unknown"
            pending.mkdir(parents=True)
            (pending / "request.json").write_text('{"original":true}')
            r.idle = lambda **kw: []
            with patch.object(runner, "simple_http") as http:
                with self.assertRaisesRegex(RuntimeError, "UNKNOWN_REQUEST_OUTCOME"):
                    r.request("unknown", runner.synthetic("free_java", "fixture"), group="test")
                http.assert_not_called()
            self.assertEqual((pending / "request.json").read_text(), '{"original":true}')

    def test_core_resume_skips_finished_pairs_and_reuses_original_cold_wire(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = self.make_runner(root)
            r.smoke = True
            r.fingerprint = lambda *args: None
            r.summarize = lambda: None
            r.calibrate = lambda *args: self.fail("completed or partial pairs must not rebuild corpus")
            r.align_final_count = lambda *args: self.fail("frozen cold wire must not be recalibrated")
            for p in (256, 1024):
                for workload in ("copy_patch", "tool_json"):
                    for track in runner.TRACKS:
                        prefix = f"core-b0-r0-P{p}-O128-{workload}-{track}"
                        for cache in ("cold", "warm"):
                            r.results[prefix+"-"+cache] = {"failures": []}
            prefix = "core-b0-r0-P1024-O128-copy_patch-research_greedy"
            del r.results[prefix+"-warm"]
            body = runner.synthetic("copy_patch", "frozen historical request")
            body.update(max_tokens=128, temperature=0, seed=20261020)
            cold = {"request_sha256": runner.sha(runner.encode(body)), "failures": [],
                    "prompt_tokens": 1024, "extra": {"original": True}}
            r.results[prefix+"-cold"] = cold
            runner.atomic(root/"requests"/(prefix+"-cold")/"request.json", body)
            sent = []
            def request(case, wire, **kw):
                if case in r.results:
                    return r.results[case]
                sent.append((case, copy.deepcopy(wire), kw))
                r.results[case] = {"failures": []}
                r.status["last_completed_case"] = case
                return r.results[case]
            r.request = request
            r.core()
            pair_sends = [(case, wire, kw) for case, wire, kw in sent if case.startswith(prefix)]
            self.assertEqual(len(pair_sends), 2)
            self.assertIn("-resume-prime-", pair_sends[0][0])
            self.assertEqual(pair_sends[1][0], prefix+"-warm")
            self.assertTrue(all(wire == body for _, wire, _ in pair_sends))
            self.assertEqual(pair_sends[1][2]["extra"], {"original": True})

    def test_approximate_cached_fixture_is_preserved_with_exact_revision(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = self.make_runner(root)
            path = root/"corpus/free_java-122.json"
            body = runner.synthetic("free_java", "x" * 100)
            runner.atomic(path, body)
            runner.atomic(path.with_suffix(".meta.json"), {
                "counted_prompt_tokens": 121, "sha256": runner.sha(runner.encode(body)), "exact": False})
            original = path.read_bytes()
            r.count = lambda b, name: len(b["messages"][1]["content"].rsplit("\n\n", 1)[0]) + 17
            aligned, meta = r.calibrate("free_java", 122)
            self.assertEqual(meta["counted_prompt_tokens"], 122)
            self.assertEqual(r.count(aligned, ""), 122)
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(path.with_name("free_java-122-exact-v2.json").exists())
            r.count = lambda *args: self.fail("reuse exact frozen revision without counting again")
            self.assertEqual(r.calibrate("free_java", 122)[0], aligned)

    def test_raw_survives_post_request_log_failure(self):
        class Response:
            status = 200
            def getheaders(self): return [("X-Request-Id", "r1")]
            def getheader(self, name): return "r1"
            def read(self): return b'{"choices":[]}'
        class Connection:
            sock = None
            def __init__(self, *args, **kwargs): pass
            def request(self, *args, **kwargs): pass
            def getresponse(self): return Response()
            def close(self): pass
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            log = root / "server.jsonl"
            log.write_text("")
            r = self.make_runner(root)
            r.idle = lambda **kw: []
            r.log_events = lambda *a: (_ for _ in ()).throw(OSError("log unavailable"))
            body = runner.synthetic("copy_patch", "fixture")
            body["stream"] = False
            with patch.object(runner, "LOG_PATH", log), \
                 patch.object(runner, "simple_http", return_value="metrics"), \
                 patch.object(runner.http.client, "HTTPConnection", Connection):
                with self.assertRaisesRegex(RuntimeError, "MISSING_REQUEST_DONE"):
                    r.request("test", body, group="test")
            self.assertTrue((root / "requests/test/client-raw.json").exists())
            self.assertTrue((root / "requests/test/raw.json.gz").exists())
            record = json.loads((root / "requests/test/record.json").read_text())
            self.assertIn("MISSING_REQUEST_DONE", record["failures"])
            self.assertEqual(record["status"], "RECORDED_WITH_GAPS")


if __name__ == "__main__":
    unittest.main()
