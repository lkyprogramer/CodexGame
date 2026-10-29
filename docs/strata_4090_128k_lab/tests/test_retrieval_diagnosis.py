import importlib.util
from pathlib import Path
import unittest

from lab.core import hash_obj

PATH = Path(__file__).resolve().parents[1] / "tools/v027/diagnose_retrieval.py"
spec = importlib.util.spec_from_file_location("retrieval_diagnosis_tested", PATH)
diagnosis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnosis)


class RetrievalDiagnosisTests(unittest.TestCase):
    def fixture(self):
        body = {"messages": [{"role": "system", "content": "exact"}, {"role": "user", "content":
            "Read ledger.\nconfig-entry id=R000001; immutable_value=1234567-000001;\n"
            "config-entry id=R000002; immutable_value=7654321-000002;\n"
            "Return only the immutable_value of R000002."}], "max_tokens": 64,
            "chat_template_kwargs": {"enable_thinking": False}, "reasoning_effort": "none"}
        case = {"id": "original", "body": body, "expected": "7654321-000002", "actual_request_sha256": hash_obj(body)}
        response = {"text": "1234567", "finish_reason": "stop", "usage": {"completion_tokens": 8}}
        return case, body, response

    def test_gold_verified_against_literal_record_and_wrong_row_reported(self):
        case, body, response = self.fixture()
        row = diagnosis.inspect_case(case, body, response)
        self.assertTrue(row["gold_unique_and_present"])
        self.assertEqual(row["actual_prefix_matches"][0]["row_delta"], -1)

    def test_changed_body_and_wrong_gold_are_rejected(self):
        case, body, response = self.fixture()
        case["expected"] = "1234567-000001"
        with self.assertRaisesRegex(ValueError, "GOLD_NOT_UNIQUE"):
            diagnosis.inspect_case(case, body, response)
        case, body, response = self.fixture()
        body["max_tokens"] = 128
        with self.assertRaisesRegex(ValueError, "FROZEN_BODY_CHANGED"):
            diagnosis.inspect_case(case, body, response)

    def test_controls_leave_original_body_gold_and_score_contract_unchanged(self):
        case, body, _ = self.fixture()
        old = hash_obj(body)
        variants = diagnosis.controls(case)
        self.assertEqual(hash_obj(body), old)
        self.assertEqual(case["expected"], "7654321-000002")
        self.assertEqual(variants["short-same-question"]["messages"][-1]["content"].splitlines()[-1],
                         body["messages"][-1]["content"].splitlines()[-1])
        self.assertEqual(variants["long-explicit-format"]["max_tokens"], 64)


if __name__ == "__main__":
    unittest.main()
