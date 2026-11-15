"""CPU-only toy contract tests. These are NOT product integration tests."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from contract_examples import guard_fixed_text_fixture  # noqa: E402
from validate_addendum import check_local_links, check_manifest, read_json_strict, validate  # noqa: E402
from probe_upstream_force_check import load_audited_check  # noqa: E402


def fixture():
    return json.loads((ROOT / "examples/numerical_complete_fixture.json").read_text())


class NumericalInputTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def assertReason(self, reason):
        self.assertIn(reason, guard_fixed_text_fixture(self.data)["reasons"])

    def test_complete_is_only_fixture_admissible(self):
        result = guard_fixed_text_fixture(self.data)
        self.assertEqual(result["status"], "INPUT_ADMISSIBLE_FIXTURE_ONLY")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["engine_starts"], 0)

    def test_declared_candidate_build_may_differ(self):
        self.assertNotEqual(self.data["expected"]["scorer_by_role"]["stock"],
                            self.data["expected"]["scorer_by_role"]["candidate"])
        self.assertEqual(guard_fixed_text_fixture(self.data)["reasons"], [])

    def test_live_claim_rejected(self):
        self.data["provenance"] = "LIVE_MEASURED"
        self.assertReason("NOT_A_SYNTHETIC_FIXTURE")

    def test_missing_request(self):
        self.data["arms"][-1]["requests"].pop()
        self.assertReason("INPUT_SET_MISMATCH")

    def test_extra_request(self):
        self.data["arms"][-1]["requests"].append({"id": "extra", "rows": [], "emitted": []})
        self.assertReason("INPUT_SET_MISMATCH")

    def test_duplicate_request(self):
        self.data["arms"][-1]["requests"].append(copy.deepcopy(self.data["arms"][-1]["requests"][0]))
        self.assertReason("DUPLICATE_REQUEST_ID")

    def test_short_coverage(self):
        self.data["arms"][-1]["requests"][0]["rows"].pop()
        self.assertReason("POSITION_COVERAGE_MISMATCH")

    def test_duplicate_position_does_not_replace_missing(self):
        rows = self.data["arms"][-1]["requests"][0]["rows"]
        rows[-1] = copy.deepcopy(rows[0])
        self.assertReason("DUPLICATE_POSITION")
        self.assertReason("POSITION_COVERAGE_MISMATCH")

    def test_out_of_range_position(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["pos"] = 999
        self.assertReason("POSITION_COVERAGE_MISMATCH")

    def test_reordered_stock_positions_rejected(self):
        self.data["arms"][0]["requests"][0]["rows"].reverse()
        self.assertReason("POSITION_ORDER_MISMATCH")

    def test_target_mismatch(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["target"] = 999
        self.assertReason("TARGET_MISMATCH")

    def test_forced_emission_mismatch(self):
        self.data["arms"][-1]["requests"][0]["emitted"].pop()
        self.assertReason("FORCED_OUTPUT_MISMATCH")

    def test_missing_emitted_receipt_rejected(self):
        del self.data["arms"][-1]["requests"][0]["emitted"]
        self.assertReason("FORCED_OUTPUT_UNPROVEN")

    def test_float_emitted_tokens_rejected(self):
        self.data["arms"][-1]["requests"][0]["emitted"] = [7.0, 8.0]
        self.assertReason("INVALID_EMITTED_TOKENS")

    def test_one_stock_arm(self):
        self.data["arms"].pop(0)
        self.assertReason("INSUFFICIENT_STOCK_ARMS")

    def test_duplicate_stock_identity(self):
        self.data["arms"][1]["run_id"] = self.data["arms"][0]["run_id"]
        self.assertReason("DUPLICATE_RUN_ID")

    def test_changed_text_contract(self):
        self.data["expected"]["contract"] = "decoder-generated-text/v1"
        self.assertReason("UNSUPPORTED_TEXT_CONTRACT")

    def test_wrong_set_digest(self):
        self.data["arms"][-1]["set_digest"] = "other"
        self.assertReason("SET_DIGEST_MISMATCH")

    def test_wrong_scorer_digest(self):
        self.data["arms"][-1]["scorer_digest"] = "undeclared-build"
        self.assertReason("SCORER_IDENTITY_MISMATCH")

    def test_prompt_cannot_masquerade_as_decode(self):
        self.data["arms"][-1]["path"] = "prompt"
        self.assertReason("WRONG_SCORER_PATH")

    def test_nan_rejected(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["logp"] = float("nan")
        self.assertReason("NONFINITE_SCORE")

    def test_inf_rejected(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["top2_margin"] = float("inf")
        self.assertReason("NONFINITE_SCORE")

    def test_huge_integer_score_rejected_without_crashing(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["logp"] = 10 ** 400
        self.assertReason("NONFINITE_SCORE")

    def test_missing_top2_rejected(self):
        del self.data["arms"][-1]["requests"][0]["rows"][0]["top2_margin"]
        self.assertReason("NONFINITE_SCORE")

    def test_positive_logp_rejected(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["logp"] = 0.1
        self.assertReason("INVALID_SCORE_DOMAIN")

    def test_reversed_top2_rejected(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["top2_logp"] = -0.01
        self.assertReason("SCORE_ORDER_MISMATCH")

    def test_same_top2_token_rejected(self):
        row = self.data["arms"][-1]["requests"][0]["rows"][0]
        row["top2_id"] = row["argmax"]
        self.assertReason("TOP2_ID_DUPLICATE")

    def test_same_token_different_logp_rejected(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["logp"] = -0.2
        self.assertReason("INCONSISTENT_TOKEN_LOGP")

    def test_fabricated_margin_rejected(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["top2_margin"] = 0.9
        self.assertReason("MARGIN_MISMATCH")

    def test_legal_tie_allowed(self):
        row = self.data["arms"][-1]["requests"][0]["rows"][0]
        row["top2_logp"] = row["argmax_logp"]
        row["top2_margin"] = 0.0
        self.assertEqual(guard_fixed_text_fixture(self.data)["reasons"], [])

    def test_declared_format_rounding_allowed(self):
        row = self.data["arms"][-1]["requests"][0]["rows"][0]
        row["logp"] += 1e-10
        self.assertEqual(guard_fixed_text_fixture(self.data)["reasons"], [])

    def test_incomplete_collector(self):
        self.data["arms"][-1]["complete"] = False
        self.assertReason("INCOMPLETE_COLLECTOR")

    def test_empty_expected_rejected(self):
        self.data["expected"]["requests"] = []
        self.assertReason("INVALID_EXPECTED_SET")

    def test_duplicate_expected_rejected(self):
        self.data["expected"]["requests"].append(copy.deepcopy(self.data["expected"]["requests"][0]))
        self.assertReason("INVALID_EXPECTED_SET")

    def test_empty_continuation_rejected(self):
        self.data["expected"]["requests"][0]["continuation"] = []
        self.assertReason("INVALID_EXPECTED_SET")

    def test_boolean_position_is_not_integer(self):
        self.data["arms"][-1]["requests"][0]["rows"][0]["pos"] = True
        self.assertReason("INVALID_ROW")

    def test_candidate_required(self):
        self.data["arms"].pop()
        self.assertReason("INVALID_ARM_ROLES")


class PackageChecksTests(unittest.TestCase):
    def test_good_local_link_and_external_not_fetched(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "target.md").write_text("# Target\n")
            path = root / "readme.md"
            path.write_text("[ok](target.md) [web](https://example.invalid/page)\n")
            self.assertEqual(check_local_links(root, path), [])

    def test_missing_local_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            path = root / "readme.md"
            path.write_text("[bad](missing.md)\n")
            self.assertTrue(check_local_links(root, path))

    def test_reference_style_link_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            path = root / "readme.md"
            path.write_text("[bad][target]\n\n[target]: missing.md\n")
            self.assertTrue(check_local_links(root, path))

    def test_link_escape_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            path = root / "readme.md"
            path.write_text("[bad](../outside.md)\n")
            self.assertTrue(check_local_links(root, path))

    def test_json_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "bad.json"
            path.write_text('{"value": NaN}')
            with self.assertRaises(ValueError):
                read_json_strict(path)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "bad.json"
            path.write_text('{"id": 1, "id": 2}')
            with self.assertRaises(ValueError):
                read_json_strict(path)

    def test_json_float_overflow_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "bad.json"
            path.write_text('{"value": 1e999}')
            with self.assertRaises(ValueError):
                read_json_strict(path)

    def assertBadBudget(self, budget):
        def corrupt_in_memory(path):
            data = read_json_strict(path)
            if path.name == "LOCK.json":
                data["live_budget"] = budget
            return data
        with mock.patch("validate_addendum.read_json_strict", side_effect=corrupt_in_memory):
            result = validate(ROOT)
        self.assertTrue(any("live budget" in error for error in result["errors"]))

    def test_empty_budget_is_not_known_zero(self):
        self.assertBadBudget({})

    def test_boolean_budget_is_not_known_integer_zero(self):
        self.assertBadBudget({k: False for k in ("engine_starts", "generation_requests", "gpu_runs", "production_changes")})

    def test_manifest_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "a.md").write_text("hello\n")
            (root / "MANIFEST.sha256").write_text("0" * 64 + "  a.md\n")
            self.assertTrue(check_manifest(root))

    def test_manifest_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "MANIFEST.sha256").write_text("0" * 64 + "  absent.md\n")
            self.assertTrue(check_manifest(root))

    def test_manifest_unlisted_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "extra.md").write_text("extra\n")
            (root / "MANIFEST.sha256").write_text("")
            self.assertTrue(check_manifest(root))

    def test_probe_refuses_unlocked_source(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "untrusted.py"
            path.write_text("raise RuntimeError('must not execute')\n")
            with self.assertRaisesRegex(ValueError, "SOURCE_HASH_MISMATCH"):
                load_audited_check(path)


if __name__ == "__main__":
    unittest.main()
