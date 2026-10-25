import copy
import hashlib
import json
import unittest

from slim_protocol_recovery import CASE, prove_completion, recovery_class


def fixture():
    body = {"model": "frozen", "stream": False, "max_tokens": 128, "enable_thinking": False,
            "messages": [{"role": "system", "content": "system"}, {"role": "user", "content": "question"}]}
    sha = hashlib.sha256(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    row = {"id": CASE, "group": "protocol", "http_status": 200, "response_request_id": None,
           "failures": ["MISSING_REQUEST_DONE", "FOREIGN_REQUEST_CONTAMINATION"],
           "foreign_requests_during_interval": 1, "request_sha256": sha, "raw_sha256": "raw"}
    request = {"model": "frozen", "protocol": "openai_chat_completions", "stream": False,
               "enable_thinking": False, "requested_output_tokens": 128, "message_count": 2,
               "tool_count": 0, "has_tool_history": False, "x_request_id": "internal", "request_id": 328}
    start = {"event": "request_start", "schema_version": 20, "server_instance_id": "one",
             "timestamp_unix_ms": 2001, "request": request}
    done = {**start, "event": "request_done", "timestamp_unix_ms": 2300,
            "result": {"prompt_tokens": 93, "completion_tokens": 128,
                       "prefix_cache_hit_tokens": 89, "finish_reason": "output_limit"},
            "timings_seconds": {"prefill": .038, "decode": .217, "ttft": .04}}
    response = {"object": "chat.completion", "model": "frozen", "choices": [{"finish_reason": "length"}],
                "usage": {"prompt_tokens": 93, "completion_tokens": 128, "total_tokens": 221},
                "timings": {"prompt_n": 93, "predicted_n": 128, "cache_n": 89,
                            "prompt_ms": 38, "predicted_ms": 217, "ttft_ms": 40}}
    text = json.dumps(response)
    raw = {"http_status": 200, "error": None, "response_request_id": None,
           "intentional_disconnect": False, "lines": [], "server_events": [], "observation_errors": [],
           "request_sha256": sha, "headers": {"Content-Length": str(len(text.encode()))}, "body": text,
           "start_utc": "1970-01-01T00:00:02+00:00", "elapsed_s": .4}
    return row, body, raw, [start, done]


def encoded(events):
    return b"".join(json.dumps(e).encode() + b"\n" for e in events)


class ProtocolRecoveryTest(unittest.TestCase):
    def test_complete_proof_retains_original_gaps_and_metrics(self):
        row, body, raw, events = fixture()
        before = copy.deepcopy((row, body, raw))
        proof = prove_completion(row, body, raw, encoded(events))
        self.assertFalse(proof["performance_sample_eligible"])
        self.assertFalse(proof["request_resent"])
        self.assertEqual(before, (row, body, raw))

    def test_ambiguous_or_incomplete_request_window_rejected(self):
        row, body, raw, events = fixture()
        for changed in [[events[0]], [events[0], events[0], events[1]],
                        [events[0], {**events[1], "event": "request_error"}],
                        [events[0], {**events[1], "server_instance_id": "other"}]]:
            with self.subTest(events=changed), self.assertRaises(RuntimeError):
                prove_completion(row, body, raw, encoded(changed))

    def test_transport_truncation_usage_timing_and_status_rejected(self):
        row, body, raw, events = fixture()
        mutations = [{"error": "timeout"}, {"http_status": 500},
                     {"headers": {"Content-Length": "1"}}, {"body": "{"}]
        for field in ["usage", "timings"]:
            response = json.loads(raw["body"])
            response[field]["completion_tokens" if field == "usage" else "predicted_ms"] += 1
            text = json.dumps(response)
            mutations.append({"body": text, "headers": {"Content-Length": str(len(text.encode()))}})
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises((RuntimeError, ValueError)):
                prove_completion(row, body, {**raw, **mutation}, encoded(events))

    def test_completed_33_state_records_short_circuit_without_http(self):
        class Parent:
            def request(self, *args, **kwargs):
                raise AssertionError("completed requests must never reach HTTP")
        cls = recovery_class(None, Parent, {})
        runner = cls.__new__(cls)
        runner.results = {"state-" + str(i): {"id": i} for i in range(32)}
        runner.results[CASE] = {"id": CASE, "failures": ["MISSING_REQUEST_DONE"]}
        for ident, row in runner.results.items():
            self.assertIs(runner.request(ident, {"stream": False}, port=18343), row)
        with self.assertRaisesRegex(RuntimeError, "unplanned"):
            runner.request("new", {"stream": False}, port=18343)


if __name__ == "__main__":
    unittest.main()
