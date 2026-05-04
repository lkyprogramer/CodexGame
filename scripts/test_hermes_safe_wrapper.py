#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hermes_guardrail_lib import extract_json_payload, load_session_final_content, recover_final_output, save_json
from hermes_safe_wrapper import diff_changed_files, evaluate_attempt, readonly_violation, should_retry


class HermesGuardrailLibTest(unittest.TestCase):
    def test_load_session_final_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "session.json"
            save_json(
                session_path,
                {
                    "messages": [
                        {"role": "user", "content": "hi"},
                        {"role": "assistant", "content": "first"},
                        {"role": "assistant", "content": "final answer"},
                    ]
                },
            )
            self.assertEqual(load_session_final_content(session_path), "final answer")

    def test_extract_json_payload_from_fenced_block(self) -> None:
        payload = extract_json_payload("```json\n{\"status\":\"ok\"}\n```")
        self.assertEqual(json.loads(payload), {"status": "ok"})

    def test_extract_json_payload_from_tail(self) -> None:
        payload = extract_json_payload("Let me provide the result:\n{\"status\":\"ok\",\"count\":2}")
        self.assertEqual(json.loads(payload), {"status": "ok", "count": 2})

    def test_recover_final_output_prefers_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "session.json"
            save_json(
                session_path,
                {
                    "messages": [
                        {"role": "assistant", "content": "```json\n{\"status\":\"ready\"}\n```"}
                    ]
                },
            )
            recovered = recover_final_output(
                mode="json",
                stdout_text="STATUS: noisy",
                stderr_text="",
                session_path=session_path,
            )
            self.assertEqual(recovered.output_source, "session")
            self.assertTrue(recovered.json_parse_success)
            self.assertEqual(json.loads(recovered.final_output), {"status": "ready"})


class HermesSafeWrapperDecisionTest(unittest.TestCase):
    def test_exit_nonzero_with_valid_session_is_soft_success(self) -> None:
        attempt = type(
            "Attempt",
            (),
            {
                "timed_out": False,
                "exit_code": 1,
                "session_path": Path("/tmp/session.json"),
                "recovered": type("Recovered", (), {"output_source": "session"})(),
            },
        )()
        evaluation = evaluate_attempt(
            mode="text",
            attempt=attempt,
            final_output="READY",
            json_parse_success=False,
            validation_success=True,
            readonly_ok=True,
        )
        self.assertTrue(evaluation.success)
        self.assertTrue(evaluation.soft_success)
        self.assertIsNone(evaluation.failure_reason)

    def test_readonly_violation_fails(self) -> None:
        violation, delta = readonly_violation(
            before=[" M tracked.txt"],
            after=[" M tracked.txt", "?? rogue.txt"],
        )
        self.assertTrue(violation)
        self.assertEqual(delta, ["?? rogue.txt"])

    def test_non_transient_failure_does_not_retry(self) -> None:
        self.assertFalse(
            should_retry(
                attempt_number=1,
                max_retries=1,
                failure_reason="contract_failure",
                stderr_text="",
                had_fenced_json=False,
            )
        )

    def test_json_failure_with_fence_retries(self) -> None:
        self.assertTrue(
            should_retry(
                attempt_number=1,
                max_retries=1,
                failure_reason="json_parse_failure",
                stderr_text="",
                had_fenced_json=True,
            )
        )

    def test_changed_files_filters_ephemeral_python_artifacts(self) -> None:
        changed = diff_changed_files(
            before={"app.py": "a", "__pycache__/app.cpython-311.pyc": "x"},
            after={"app.py": "b", "__pycache__/app.cpython-311.pyc": "y"},
        )
        self.assertEqual(changed, ["app.py"])


if __name__ == "__main__":
    unittest.main()
