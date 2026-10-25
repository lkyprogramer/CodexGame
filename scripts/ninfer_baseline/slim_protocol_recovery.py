#!/usr/bin/env python3
"""Reconcile one completed proxy response; retain the original row and gaps."""
import argparse
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

CASE = "protocol-chat-18343-False"
GAPS = {"MISSING_REQUEST_DONE", "FOREIGN_REQUEST_CONTAMINATION"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prove_completion(row, body, raw, log_bytes):
    """Post-hoc corroboration only. It never upgrades original performance data."""
    canonical = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    if (row.get("id") != CASE or row.get("group") != "protocol"
            or set(row.get("failures", [])) != GAPS
            or row.get("http_status") != 200 or row.get("response_request_id") is not None
            or row.get("foreign_requests_during_interval") != 1
            or body.get("stream") is not False or body.get("max_tokens") != 128
            or body.get("enable_thinking") is not False
            or raw.get("http_status") != 200 or raw.get("error") is not None
            or raw.get("response_request_id") is not None
            or raw.get("intentional_disconnect") is not False
            or raw.get("lines") != [] or raw.get("server_events") != []
            or raw.get("observation_errors") != []
            or raw.get("request_sha256") != row["request_sha256"]
            or hashlib.sha256(canonical(body)).hexdigest() != row["request_sha256"]):
        raise RuntimeError("not the authorized complete non-stream proxy response")
    length = next((v for k, v in raw["headers"].items() if k.lower() == "content-length"), None)
    if length is None or int(length) != len(raw["body"].encode()):
        raise RuntimeError("incomplete proxy JSON response")
    response = json.loads(raw["body"])
    if (response.get("object") != "chat.completion" or response.get("model") != body["model"]
            or len(response.get("choices", [])) != 1
            or response["choices"][0].get("finish_reason") != "length"):
        raise RuntimeError("unexpected completed proxy response")
    start_ms = dt.datetime.fromisoformat(raw["start_utc"]).timestamp() * 1000
    # schema20 timestamps have millisecond precision; preserve explicit 1ms bounds.
    lower, upper = start_ms - 1, start_ms + raw["elapsed_s"] * 1000 + 1
    if not log_bytes.endswith(b"\n"):
        raise RuntimeError("incomplete frozen server log")
    selected, intervals, offset = [], [], 0
    for line in log_bytes.splitlines(keepends=True):
        event = json.loads(line)
        if lower <= event.get("timestamp_unix_ms", -1) <= upper:
            selected.append(event)
            intervals.append([offset, offset + len(line)])
        offset += len(line)
    requests = [e for e in selected if e.get("event", "").startswith("request_")]
    if [e["event"] for e in requests] != ["request_start", "request_done"]:
        raise RuntimeError("ambiguous or incomplete request interval")
    start, done = requests
    if (start["request"] != done["request"] or start.get("schema_version") != 20
            or done.get("schema_version") != 20 or not start.get("server_instance_id")
            or start["server_instance_id"] != done.get("server_instance_id")
            or start["timestamp_unix_ms"] > done["timestamp_unix_ms"]):
        raise RuntimeError("server request identity mismatch")
    request = done["request"]
    expected = {"model": body["model"], "protocol": "openai_chat_completions",
                "stream": False, "enable_thinking": False, "requested_output_tokens": 128,
                "message_count": len(body["messages"]), "tool_count": len(body.get("tools", [])),
                "has_tool_history": False}
    if any(request.get(k) != v for k, v in expected.items()) or not request.get("x_request_id"):
        raise RuntimeError("server request attributes mismatch")
    usage, timings, result = response["usage"], response["timings"], done["result"]
    p, o = usage["prompt_tokens"], usage["completion_tokens"]
    if (type(p) is not int or type(o) is not int or usage["total_tokens"] != p + o
            or p != result["prompt_tokens"] or o != result["completion_tokens"]
            or timings["prompt_n"] != p or timings["predicted_n"] != o
            or timings["cache_n"] != result["prefix_cache_hit_tokens"]
            or result["finish_reason"] != "output_limit"):
        raise RuntimeError("proxy usage does not match completed engine result")
    for proxy, engine in [("prompt_ms", "prefill"), ("predicted_ms", "decode"), ("ttft_ms", "ttft")]:
        if not math.isclose(timings[proxy] / 1000, done["timings_seconds"][engine], rel_tol=1e-9, abs_tol=1e-9):
            raise RuntimeError("proxy timing does not match completed engine result")
    return {"outcome": "COMPLETED_PROXY_RESPONSE_WITH_ORIGINAL_CORRELATION_GAPS",
            "original_failures_retained": row["failures"], "request_resent": False,
            "performance_sample_eligible": False, "original_metrics_unchanged": True,
            "proof_scope": "post-hoc unique bounded request interval plus matching usage and timings; original header absent",
            "timestamp_tolerance_ms": 1, "interval_ms": [lower, upper],
            "server_log_byte_intervals": intervals,
            "correlated_server_request_id": request["request_id"],
            "correlated_x_request_id": request["x_request_id"],
            "server_instance_id": done["server_instance_id"], "events": selected,
            "record_sha256": hashlib.sha256(canonical(row)).hexdigest(),
            "request_sha256": row["request_sha256"], "raw_sha256": row["raw_sha256"]}


def recovery_class(base, parent, receipt):
    class ProtocolRecoveryRunner(parent):
        def __init__(self, root, stage):
            super().__init__(root, stage)
            rows = (self.root / "records.jsonl").read_bytes().splitlines(keepends=True)
            drain = json.loads(Path(receipt["drain"]["path"]).read_text())
            if hashlib.sha256(b"".join(rows[:drain["record_count"]])).hexdigest() != drain["records_sha256"]:
                raise RuntimeError("pre-repair record prefix changed")
            row = self.results[CASE]
            if base.sha(base.encode(row)) != receipt["existing_record_sha256"] or not base.intact(self.root, row):
                raise RuntimeError("authorized original protocol row changed")
            directory = self.root / "requests" / CASE
            body = json.loads((directory / "request.json").read_text())
            raw = json.loads(gzip.decompress((directory / "raw.json.gz").read_bytes()))
            proof = prove_completion(row, body, raw, Path(receipt["server_log"]["path"]).read_bytes())
            overlay = {"manifest_sha256": self.status["manifest_sha256"],
                       "recovery_receipt_sha256": receipt["receipt_sha256"], "outcomes": {CASE: proof}}
            path = self.root / "protocol-reconciliation-v4.json"
            if path.exists() and json.loads(path.read_text()) != overlay:
                raise RuntimeError("existing protocol reconciliation changed")
            base.atomic(path, overlay)
            # Ledger-only reconciliation; original rows and raw artifacts stay unchanged.
            for ident in self.manifest["state_case_ids"]:
                if ident in self.results and ident not in self.resolutions:
                    self.resolve(ident, self.root, self.results[ident])

        def request(self, case_id, body, **kwargs):
            if case_id in self.results:
                return self.results[case_id]
            # No future missing-header fallback: the sole affected frozen case is complete.
            if kwargs.get("port", 18030) == 18343 and body.get("stream") is False:
                raise RuntimeError("unplanned non-stream proxy request; no fallback or retry")
            return super().request(case_id, body, **kwargs)

        def report(self):
            result = super().report()
            path = self.root / "protocol-reconciliation-v4.json"
            if path.exists():
                result["protocol_reconciliation"] = json.loads(path.read_text())
                base.atomic(self.root / "reference-report.json", result)
            return result
    return ProtocolRecoveryRunner


def load_recovery(bundle, root, path):
    path = Path(path)
    receipt = json.loads(path.read_text())
    if (receipt.get("schema_version") != 1 or receipt.get("lane_drained") is not True
            or digest(__file__) != receipt["wrapper_sha256"]
            or digest(root / "manifest.json") != receipt["manifest_sha256"]):
        raise RuntimeError("protocol recovery identity mismatch")
    for key in ["prior_wrapper", "prior_receipt", "drain", "server_log"]:
        if digest(receipt[key]["path"]) != receipt[key]["sha256"]:
            raise RuntimeError("protocol recovery dependency changed: " + key)
    spec = importlib.util.spec_from_file_location("frozen_fixture_recovery_v3", receipt["prior_wrapper"]["path"])
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    base, capacity, capacity_receipt, fixture_receipt = prior.load_recovery(bundle, root, receipt["prior_receipt"]["path"])
    parent = prior.recovery_class(base, capacity, capacity_receipt, fixture_receipt)
    receipt["receipt_sha256"] = digest(path)
    return base, parent, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--stage", choices=["remaining"], required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    base, parent, receipt = load_recovery(root.parent / "slim-bin-v1", root, root / "recovery-protocol-v4/receipt.json")
    base.SlimRunner = recovery_class(base, parent, receipt)
    sys.argv = [str(base.__file__), "--root", args.root, "--stage", args.stage]
    base.main()


if __name__ == "__main__":
    main()
