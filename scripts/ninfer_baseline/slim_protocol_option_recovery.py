#!/usr/bin/env python3
"""Preserve protocol-option rejections; do not rewrite frozen requests."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ERROR = {"code": "chat_template_option_not_supported",
         "message": "chat_template_kwargs.enable_thinking is not supported",
         "param": "chat_template_kwargs", "type": "invalid_request_error"}
CASES = {"protocol-responses-False", "protocol-responses-True"}


def validate_rejection(base, root, row, body):
    if (row["id"] not in CASES or row.get("group") != "protocol"
            or body.get("model") != "openclaw/Qwen3.8-27B-WORK"
            or body.get("input") != "用中文回答1+1等于几？"
            or body.get("max_output_tokens") != 128 or type(body.get("stream")) is not bool
            or row["id"] != "protocol-responses-" + str(body["stream"])
            or body.get("chat_template_kwargs") != {"enable_thinking": False}
            or set(body) != {"model", "input", "max_output_tokens", "stream", "chat_template_kwargs"}
            or row.get("http_status") != 400 or not row.get("response_request_id")
            or row.get("foreign_requests_during_interval") != 0
            or not set(row.get("failures", [])) <= {"HTTP_STATUS", "MISSING_REQUEST_DONE"}
            or not base.intact(root, row) or row["request_sha256"] != base.sha(base.encode(body))):
        raise RuntimeError("not an intact frozen protocol-option rejection")
    with gzip.open(Path(root)/"requests"/row["id"]/"raw.json.gz", "rb") as stream:
        raw = json.load(stream)
    if (raw.get("request_sha256") != row["request_sha256"] or raw.get("http_status") != 400
            or raw.get("response_request_id") != row["response_request_id"]
            or raw.get("error") is not None or raw.get("intentional_disconnect") is not False
            or raw.get("lines") != [] or raw.get("server_events") != []
            or raw.get("observation_errors") != [] or json.loads(raw["body"]) != {"error": ERROR}):
        raise RuntimeError("not a complete unadmitted specified protocol HTTP400")
    length = next((v for k,v in raw["headers"].items() if k.lower()=="content-length"), None)
    if length is None or int(length) != len(raw["body"].encode()):
        raise RuntimeError("incomplete protocol rejection body")
    return {"outcome": "FROZEN_PROTOCOL_OPTION_REJECTED", "original_failures_retained": row["failures"],
            "performance_sample_eligible": False, "successful_responses_protocol_coverage": False,
            "model_quality_status": "NOT_APPLICABLE_PRE_ADMISSION_PROTOCOL_REJECTION",
            "requested_output_tokens": 128, "request_resent": False,
            "record_sha256": base.sha(base.encode(row)), "request_sha256": row["request_sha256"],
            "raw_sha256": row["raw_sha256"], "server_error": ERROR}


def recovery_class(base, parent, receipt):
    class ProtocolOptionRecoveryRunner(parent):
        def __init__(self, root, stage):
            super().__init__(root, stage)
            for ident, proof in receipt["validated_existing_rejections"].items():
                self.option_overlay(ident, proof)

        def option_overlay(self, ident, proof):
            path = self.root/"protocol-option-rejections-v5.json"
            overlay = json.loads(path.read_text()) if path.exists() else {
                "manifest_sha256": self.status["manifest_sha256"],
                "recovery_receipt_sha256": receipt["receipt_sha256"], "outcomes": {}}
            if (overlay["manifest_sha256"] != self.status["manifest_sha256"]
                    or overlay["recovery_receipt_sha256"] != receipt["receipt_sha256"]):
                raise RuntimeError("protocol rejection overlay identity mismatch")
            if ident in overlay["outcomes"] and overlay["outcomes"][ident] != proof:
                raise RuntimeError("protocol rejection proof changed")
            overlay["outcomes"][ident] = proof
            base.atomic(path, overlay)

        def request(self, case_id, body, **kwargs):
            if case_id in self.results:
                if case_id in CASES:
                    self.option_overlay(case_id, validate_rejection(base, self.root, self.results[case_id], body))
                return self.results[case_id]
            if case_id in CASES:
                if kwargs.get("group") != "protocol" or kwargs.get("path") != "/v1/responses":
                    raise RuntimeError("unexpected protocol recovery call")
                kwargs["expected_status"] = 400
                row = super().request(case_id, body, **kwargs)
                self.option_overlay(case_id, validate_rejection(base, self.root, row, body))
                return row
            return super().request(case_id, body, **kwargs)

        def report(self):
            result = super().report()
            path = self.root/"protocol-option-rejections-v5.json"
            if path.exists():
                result["protocol_option_rejections"] = json.loads(path.read_text())
                base.atomic(self.root/"reference-report.json", result)
            return result
    return ProtocolOptionRecoveryRunner


def load_recovery(bundle, root, path):
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    path = Path(path); receipt = json.loads(path.read_text())
    if (receipt.get("schema_version") != 1 or receipt.get("lane_drained") is not True
            or receipt["wrapper_sha256"] != digest(__file__)
            or receipt["manifest_sha256"] != digest(root/"manifest.json")):
        raise RuntimeError("protocol option recovery identity mismatch")
    for key in ["prior_wrapper", "prior_receipt", "drain"]:
        if digest(receipt[key]["path"]) != receipt[key]["sha256"]:
            raise RuntimeError("protocol option dependency changed: "+key)
    spec = importlib.util.spec_from_file_location("frozen_protocol_recovery_v4", receipt["prior_wrapper"]["path"])
    prior = importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    base, parent, old = prior.load_recovery(bundle, root, receipt["prior_receipt"]["path"])
    parent = prior.recovery_class(base, parent, old)
    row = json.loads((root/"requests/protocol-responses-False/record.json").read_text())
    if base.sha(base.encode(row)) != receipt["existing_record_sha256"]:
        raise RuntimeError("original protocol rejection row changed")
    body = json.loads((root/"requests/protocol-responses-False/request.json").read_text())
    receipt["validated_existing_rejections"] = {row["id"]:validate_rejection(base, root, row, body)}
    for ident in sorted(CASES - {row["id"]}):
        directory = root/"requests"/ident
        if (directory/"record.json").exists():
            existing = json.loads((directory/"record.json").read_text())
            request = json.loads((directory/"request.json").read_text())
            receipt["validated_existing_rejections"][ident] = validate_rejection(base, root, existing, request)
    drain = json.loads(Path(receipt["drain"]["path"]).read_text())
    rows = (root/"records.jsonl").read_bytes().splitlines(keepends=True)
    if base.sha(b"".join(rows[:drain["record_count"]])) != drain["records_sha256"]:
        raise RuntimeError("pre-v5 record prefix changed")
    receipt["receipt_sha256"] = digest(path)
    return base, parent, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--stage", choices=["remaining"], required=True)
    args = parser.parse_args();root = Path(args.root).resolve()
    base, parent, receipt = load_recovery(root.parent/"slim-bin-v1", root, root/"recovery-protocol-option-v5/receipt.json")
    base.SlimRunner = recovery_class(base, parent, receipt)
    sys.argv = [str(base.__file__), "--root", args.root, "--stage", args.stage]
    base.main()


if __name__ == "__main__":
    main()
