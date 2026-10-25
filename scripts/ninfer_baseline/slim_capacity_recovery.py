#!/usr/bin/env python3
"""Versioned capacity-rejection overlay; the original collector bundle stays frozen."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import sys

CAPACITY = 262144
ERROR = {"code": "context_length_exceeded", "message": "prepared prompt exceeds Engine context capacity",
         "param": "messages", "type": "invalid_request_error"}
EXPECTED_OLD_GAPS = {"HTTP_STATUS", "MISSING_REQUEST_DONE", "INVALID_CHAT_STREAM"}


def validate_rejection(base, root, row, body, projected):
    """Accept only the complete, unadmitted response, never infer from missing SSE."""
    if type(projected) is not int or projected <= CAPACITY or body.get("max_tokens") != 32768:
        raise RuntimeError("capacity overlay requires unchanged oversized frozen Pi request")
    if not base.intact(root, row) or row.get("request_sha256") != base.sha(base.encode(body)):
        raise RuntimeError("capacity evidence integrity mismatch")
    calibration = json.loads((Path(root) / "calibration" / (row["id"]+".json")).read_text())
    if (calibration.get("chat_sha256") != row["request_sha256"]
            or calibration.get("response", {}).get("input_tokens") != projected):
        raise RuntimeError("capacity tokenizer evidence mismatch")
    with gzip.open(Path(root) / "requests" / row["id"] / "raw.json.gz", "rb") as stream:
        raw = json.load(stream)
    if (row.get("group") != "pi_teacher_forced" or row.get("requested_output_tokens") != 32768
            or row.get("http_status") != 400 or row.get("response_request_id") is not None
            or row.get("extra", {}).get("projected_count") != projected
            or row.get("extra", {}).get("count_projection_error") is not None
            or row.get("foreign_requests_during_interval") != 0
            or not set(row.get("failures", [])) <= EXPECTED_OLD_GAPS
            or raw.get("request_sha256") != row["request_sha256"]
            or raw.get("http_status") != 400 or raw.get("error") is not None
            or raw.get("response_request_id") is not None or raw.get("intentional_disconnect") is not False
            or raw.get("lines") != [] or raw.get("server_events") != []
            or raw.get("observation_errors") != []):
        raise RuntimeError("not a complete unadmitted capacity rejection")
    if json.loads(raw["body"]) != {"error": ERROR}:
        raise RuntimeError("unexpected HTTP400 error; no recovery qualification")
    length = next((v for k, v in raw.get("headers", {}).items() if k.lower() == "content-length"), None)
    if length is None or int(length) != len(raw["body"].encode("utf-8")):
        raise RuntimeError("capacity response body completeness not established")
    return {"outcome": "EXPECTED_PRE_ADMISSION_CONTEXT_CAPACITY_REJECTION", "projected_prompt_tokens": projected,
            "context_capacity": CAPACITY, "requested_output_tokens": 32768,
            "original_failures_retained": row["failures"], "record_sha256": base.sha(base.encode(row)),
            "request_sha256": row["request_sha256"], "raw_sha256": row["raw_sha256"],
            "performance_sample_eligible": False, "request_resent": False}


def recovery_class(base, receipt):
    class CapacityRecoveryRunner(base.SlimRunner):
        def collect_pi(self, priority):
            for case in self.manifest["pi_cases"]:
                ident = "pi-"+case["id"]
                if (ident in self.manifest["priority_ids"]) != priority or ident in self.resolutions:
                    continue
                body = base.pi_body(self.root / "pi-private", case, self.manifest["pi_seed"])
                old = self.results.get(ident)
                if old is not None:
                    projected = old.get("extra", {}).get("projected_count")
                    if old.get("failures") or old.get("http_status") != 200:
                        if receipt["existing_rejections"].get(ident) != base.sha(base.encode(old)):
                            raise RuntimeError("existing rejected Pi row not explicitly authorized")
                        outcome = validate_rejection(base, self.root, old, body, projected)
                        self.capacity_overlay(ident, outcome)
                    row = old
                else:
                    projected, projection_error = None, None
                    try:
                        projected = self.count(body, ident)
                    except (ValueError, KeyError, RuntimeError) as exc:
                        projection_error = type(exc).__name__+": "+str(exc)[:200]
                    oversized = type(projected) is int and projected > CAPACITY
                    row = self.request(ident, body, group="pi_teacher_forced", timeout=2400, port=18343,
                        expected_status=400 if oversized else 200,
                        extra={"source_sha256": case["source_sha256"], "entry_id": case["entry_id"],
                               "qualification": self.manifest["pi_qualification"], "block": 0,
                               "historical_budget_provenance": case["budget_provenance"],
                               "mandatory_truncation": case["mandatory_truncation"],
                               "projected_count": projected, "count_projection_error": projection_error,
                               "cache_condition": "OBSERVED_SEQUENCE_WITH_GAPS_NOT_ASSUMED_APPEND"})
                    if oversized:
                        self.capacity_overlay(ident, validate_rejection(base, self.root, row, body, projected))
                    elif row.get("http_status") != 200:
                        raise RuntimeError("unexpected Pi HTTP status; no automatic retry")
                self.resolve(ident, self.root, row)
                self.report()

        def capacity_overlay(self, ident, outcome):
            path = self.root / "capacity-outcomes.json"
            overlay = json.loads(path.read_text()) if path.exists() else {
                "schema_version": 1, "manifest_sha256": self.status["manifest_sha256"],
                "recovery_receipt_sha256": receipt["receipt_sha256"], "outcomes": {}}
            if (overlay["manifest_sha256"] != self.status["manifest_sha256"]
                    or overlay["recovery_receipt_sha256"] != receipt["receipt_sha256"]):
                raise RuntimeError("capacity overlay belongs to another recovery")
            overlay["outcomes"][ident] = outcome
            base.atomic(path, overlay)

        def report(self):
            result = super().report()
            path = self.root / "capacity-outcomes.json"
            if path.exists():
                result["capacity_outcomes"] = json.loads(path.read_text())
                result["capacity_outcomes_note"] = "Outcome overlay only; original gaps/raw retained; not throughput samples"
                base.atomic(self.root / "reference-report.json", result)
            return result
    return CapacityRecoveryRunner


def load_recovery(bundle, root, receipt_path):
    import hashlib
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("schema_version") != 1 or receipt.get("lane_drained") is not True:
        raise RuntimeError("unsupported or undrained recovery receipt")
    if receipt["wrapper_sha256"] != digest(__file__) or receipt["manifest_sha256"] != digest(root / "manifest.json"):
        raise RuntimeError("recovery wrapper/manifest identity mismatch")
    if set(receipt["bundle_sha256"]) != {"runner.py", "slim_runner.py", "slim_plan.py", "guardian.py"}:
        raise RuntimeError("incomplete frozen bundle identity")
    for name, expected in receipt["bundle_sha256"].items():
        if digest(bundle / name) != expected:
            raise RuntimeError("frozen bundle changed: "+name)
    if digest(receipt["drain"]["path"]) != receipt["drain"]["sha256"]:
        raise RuntimeError("drain receipt changed")
    if not isinstance(receipt["existing_rejections"], dict) or not receipt["existing_rejections"]:
        raise RuntimeError("explicit existing rejection identities required")
    receipt["receipt_sha256"] = digest(receipt_path)
    sys.path.insert(0, str(bundle))
    spec = importlib.util.spec_from_file_location("frozen_slim_capacity_base", bundle / "slim_runner.py")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    return base, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-bundle")
    parser.add_argument("--recovery-receipt")
    parser.add_argument("--root", required=True)
    parser.add_argument("--stage", choices=["remaining"], required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    bundle = Path(args.frozen_bundle).resolve() if args.frozen_bundle else Path(__file__).resolve().parent.parent / "slim-bin-v1"
    receipt_path = Path(args.recovery_receipt) if args.recovery_receipt else root / "recovery-capacity-v2/receipt.json"
    base, receipt = load_recovery(bundle, root, receipt_path)
    base.SlimRunner = recovery_class(base, receipt)
    sys.argv = [str(base.__file__), "--root", args.root, "--stage", args.stage]
    base.main()


if __name__ == "__main__":
    main()
