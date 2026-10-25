#!/usr/bin/env python3
"""Versioned overlay for independently proven invalid frozen tool arguments."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import sys

ERROR = {"code": None, "message": "function tool_call arguments must be a JSON object string",
         "param": "messages", "type": "invalid_request_error"}


def invalid_arguments(body):
    invalid = []
    for mi, message in enumerate(body.get("messages", [])):
        if message.get("role") != "assistant":
            continue
        for ti, tool in enumerate(message.get("tool_calls", [])):
            if tool.get("type") != "function":
                continue
            args = tool.get("function", {}).get("arguments")
            reason = None
            if not isinstance(args, str):
                reason = "NON_STRING_ARGUMENTS"
            else:
                try:
                    parsed = json.loads(args)
                    if not isinstance(parsed, dict):
                        reason = "NON_OBJECT_ARGUMENTS"
                except (ValueError, RecursionError):
                    reason = "INVALID_JSON_ARGUMENTS"
            if reason:
                invalid.append({"message_index": mi, "tool_index": ti, "reason": reason})
    return invalid


def validate_fixture(base, prior, root, row, body):
    proof = invalid_arguments(body)
    if not proof or body.get("max_tokens") != 32768:
        raise RuntimeError("no independent malformed frozen tool argument proof")
    if not base.intact(root, row) or row.get("request_sha256") != base.sha(base.encode(body)):
        raise RuntimeError("fixture rejection evidence integrity mismatch")
    with gzip.open(Path(root) / "requests" / row["id"] / "raw.json.gz", "rb") as stream:
        raw = json.load(stream)
    if (row.get("group") != "pi_teacher_forced" or row.get("requested_output_tokens") != 32768
            or row.get("http_status") != 400 or row.get("response_request_id") is not None
            or row.get("foreign_requests_during_interval") != 0
            or not set(row.get("failures", [])) <= prior.EXPECTED_OLD_GAPS
            or raw.get("request_sha256") != row["request_sha256"]
            or raw.get("http_status") != 400 or raw.get("error") is not None
            or raw.get("response_request_id") is not None or raw.get("intentional_disconnect") is not False
            or raw.get("lines") != [] or raw.get("server_events") != []
            or raw.get("observation_errors") != []):
        raise RuntimeError("not a complete unadmitted invalid-fixture rejection")
    if json.loads(raw["body"]) != {"error": ERROR}:
        raise RuntimeError("unexpected HTTP400 error; invalid fixture not qualified")
    length = next((v for k, v in raw.get("headers", {}).items() if k.lower() == "content-length"), None)
    if length is None or int(length) != len(raw["body"].encode()):
        raise RuntimeError("fixture rejection response completeness not established")
    return {"outcome": "INVALID_FROZEN_TOOL_ARGUMENTS", "static_proof": proof,
            "original_failures_retained": row["failures"], "record_sha256": base.sha(base.encode(row)),
            "request_sha256": row["request_sha256"], "raw_sha256": row["raw_sha256"],
            "requested_output_tokens": 32768, "performance_sample_eligible": False,
            "model_quality_status": "NOT_APPLICABLE_INVALID_FROZEN_FIXTURE", "request_resent": False}


def recovery_class(base, prior, old_receipt, receipt):
    parent = prior.recovery_class(base, old_receipt)
    allowed = {**old_receipt["existing_rejections"], **receipt["existing_rejections"]}

    class FixtureRecoveryRunner(parent):
        def collect_pi(self, priority):
            for case in self.manifest["pi_cases"]:
                ident = "pi-"+case["id"]
                if (ident in self.manifest["priority_ids"]) != priority or ident in self.resolutions:
                    continue
                body = base.pi_body(self.root / "pi-private", case, self.manifest["pi_seed"])
                malformed = bool(invalid_arguments(body))
                old = self.results.get(ident)
                if old is not None:
                    projected = old.get("extra", {}).get("projected_count")
                    if old.get("failures") or old.get("http_status") != 200:
                        if allowed.get(ident) != base.sha(base.encode(old)):
                            raise RuntimeError("existing rejected Pi row not explicitly authorized")
                        if malformed:
                            self.fixture_overlay(ident, validate_fixture(base, prior, self.root, old, body))
                        else:
                            self.capacity_overlay(ident, prior.validate_rejection(base, self.root, old, body, projected))
                    elif malformed:
                        raise RuntimeError("malformed fixture unexpectedly admitted; no recovery qualification")
                    row = old
                else:
                    projected, projection_error = None, None
                    try:
                        projected = self.count(body, ident)
                    except (ValueError, KeyError, RuntimeError) as exc:
                        projection_error = type(exc).__name__+": "+str(exc)[:200]
                    oversized = type(projected) is int and projected > prior.CAPACITY
                    row = self.request(ident, body, group="pi_teacher_forced", timeout=2400, port=18343,
                        expected_status=400 if malformed or oversized else 200,
                        extra={"source_sha256": case["source_sha256"], "entry_id": case["entry_id"],
                               "qualification": self.manifest["pi_qualification"], "block": 0,
                               "historical_budget_provenance": case["budget_provenance"],
                               "mandatory_truncation": case["mandatory_truncation"],
                               "projected_count": projected, "count_projection_error": projection_error,
                               "cache_condition": "OBSERVED_SEQUENCE_WITH_GAPS_NOT_ASSUMED_APPEND"})
                    if malformed:
                        self.fixture_overlay(ident, validate_fixture(base, prior, self.root, row, body))
                    elif oversized:
                        self.capacity_overlay(ident, prior.validate_rejection(base, self.root, row, body, projected))
                    elif row.get("http_status") != 200:
                        raise RuntimeError("unexpected Pi HTTP status; no automatic retry")
                self.resolve(ident, self.root, row)
                self.report()

        def capacity_overlay(self, ident, outcome):
            # New outcomes belong to v3; never rewrite the prior capacity overlay.
            self.fixture_overlay(ident, outcome)

        def fixture_overlay(self, ident, outcome):
            path = self.root / "fixture-rejections-v3.json"
            overlay = json.loads(path.read_text()) if path.exists() else {
                "schema_version": 1, "manifest_sha256": self.status["manifest_sha256"],
                "recovery_receipt_sha256": receipt["receipt_sha256"], "outcomes": {}}
            if (overlay["manifest_sha256"] != self.status["manifest_sha256"]
                    or overlay["recovery_receipt_sha256"] != receipt["receipt_sha256"]):
                raise RuntimeError("fixture overlay belongs to another recovery")
            overlay["outcomes"][ident] = outcome
            base.atomic(path, overlay)

        def report(self):
            result = super().report()
            path = self.root / "fixture-rejections-v3.json"
            if path.exists():
                result["fixture_rejections"] = json.loads(path.read_text())
                base.atomic(self.root / "reference-report.json", result)
            return result
    return FixtureRecoveryRunner


def load_recovery(bundle, root, receipt_path):
    import hashlib
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("schema_version") != 1 or receipt.get("lane_drained") is not True:
        raise RuntimeError("unsupported or undrained fixture recovery receipt")
    if receipt["wrapper_sha256"] != digest(__file__) or receipt["manifest_sha256"] != digest(root / "manifest.json"):
        raise RuntimeError("fixture wrapper/manifest identity mismatch")
    for key in ["prior_wrapper", "prior_receipt", "drain"]:
        if digest(receipt[key]["path"]) != receipt[key]["sha256"]:
            raise RuntimeError("fixture recovery dependency changed: "+key)
    if not isinstance(receipt["existing_rejections"], dict) or not receipt["existing_rejections"]:
        raise RuntimeError("explicit invalid fixture row identities required")
    spec = importlib.util.spec_from_file_location("frozen_capacity_recovery_v2", receipt["prior_wrapper"]["path"])
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    base, old_receipt = prior.load_recovery(bundle, root, receipt["prior_receipt"]["path"])
    receipt["receipt_sha256"] = digest(receipt_path)
    return base, prior, old_receipt, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-bundle")
    parser.add_argument("--recovery-receipt")
    parser.add_argument("--root", required=True)
    parser.add_argument("--stage", choices=["remaining"], required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    bundle = Path(args.frozen_bundle).resolve() if args.frozen_bundle else root.parent / "slim-bin-v1"
    receipt = Path(args.recovery_receipt) if args.recovery_receipt else root / "recovery-fixture-v3/receipt.json"
    base, prior, old_receipt, receipt = load_recovery(bundle, root, receipt)
    base.SlimRunner = recovery_class(base, prior, old_receipt, receipt)
    sys.argv = [str(base.__file__), "--root", args.root, "--stage", args.stage]
    base.main()


if __name__ == "__main__":
    main()
