import copy
import json
from pathlib import Path
import unittest

from tools.frontier.contracts import DEPENDENCIES_SCHEMA, REQUESTS_SCHEMA, WINDOWS_SCHEMA
from tools.frontier.warm_plan import validate_warm_plan


ROOT = Path(__file__).resolve().parents[1]


def plan_fixture():
    plan = json.loads((ROOT / "frontier/templates/PREREGISTRATION.json").read_text())
    plan.update({
        "template_only": False, "planning_only": True, "campaign_id": "offline-fixture",
        "frozen_at_utc": "2026-10-30T00:00:00Z", "execution_instruction_reference": "authorization.json",
        "baseline_identity_path": "IDENTITY.json", "reference_evidence": {
            "authorization.json": {"status": "AVAILABLE", "scope": "p00_readonly_cpu", "sha256": "a" * 64},
            "IDENTITY.json": {"status": "AVAILABLE", "sha256": "b" * 64},
        },
    })
    engine = plan["matrix"][0]
    engine.update({"sampling_seed": 42, "template_tokenizer_identity": {
        "template_sha256": "c" * 64, "tokenizer_sha256": "d" * 64,
    }})
    for index, request in enumerate(engine["requests"]):
        request.update({"body_or_recipe_sha256": "e" * 64, "history_status": "RUNTIME_PENDING",
                        "prompt_tokens_upper_bound": 103000 + index * 6000})
        if index:
            request.update({"append_user_message_sha256": "f" * 64,
                            "append_user_message_source_reference": f"pi-session.json#user-{index}"})
    return plan


class WarmPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "frontier/config/policy.json").read_text())

    def test_frozen_recipes_with_unknown_history_are_offline_only(self):
        plan = plan_fixture()
        before = copy.deepcopy(plan)
        result = validate_warm_plan(plan, self.policy)
        self.assertEqual(result["status"], "PLAN_VALID_PENDING_GPU_HANDOFF")
        self.assertEqual(result["execution_result"], "NOT_RUN")
        self.assertFalse(result["live_ready"])
        self.assertFalse(result["authorization_verified"])
        self.assertEqual(result["p05_status"], "BLOCKED_EVIDENCE")
        self.assertEqual(plan, before)

    def test_preparation_requires_available_authorization_and_handoff(self):
        plan = plan_fixture()
        plan["planning_only"] = False
        plan["reference_evidence"]["authorization.json"]["scope"] = "p01_diagnostic"
        with self.assertRaisesRegex(ValueError, "gpu_handoff_reference"):
            validate_warm_plan(plan, self.policy)
        plan["gpu_handoff_reference"] = "handoff.json"
        plan["reference_evidence"]["handoff.json"] = {"status": "AVAILABLE", "sha256": "f" * 64}
        result = validate_warm_plan(plan, self.policy)
        self.assertEqual(result["status"], "READY_FOR_P01_PREPARATION")
        self.assertFalse(result["live_ready"])
        plan["reference_evidence"]["handoff.json"]["status"] = "NOT_READ"
        with self.assertRaisesRegex(ValueError, "unavailable reference"):
            validate_warm_plan(plan, self.policy)

    def test_budget_and_matrix_rejections(self):
        changes = [
            lambda p: p.update(max_engine_starts=2),
            lambda p: p["matrix"].append(copy.deepcopy(p["matrix"][0])),
            lambda p: p["matrix"][0]["requests"].pop(),
            lambda p: p.update(wall_budget_seconds=3601),
            lambda p: p.update(cleanup_reserve_seconds=119),
            lambda p: p.update(wall_budget_seconds=1800),
            lambda p: p["matrix"][0]["requests"][1].update(request_deadline_seconds=601),
            lambda p: p["matrix"][0]["requests"][1].update(max_output_tokens=2049),
            lambda p: p["matrix"][0]["requests"][1].update(target_output_tokens=128),
            lambda p: p["matrix"][0]["requests"][1].update(prompt_tokens_upper_bound=124929),
            lambda p: p["matrix"][0]["requests"][1].update(prompt_tokens_upper_bound=True),
            lambda p: p["matrix"][0]["requests"][1].update(engine_label="other"),
            lambda p: p["matrix"][0]["requests"][1].update(request_label="prime"),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                plan = plan_fixture()
                change(plan)
                with self.assertRaises(ValueError):
                    validate_warm_plan(plan, self.policy)

    def test_no_profiles_fake_history_or_reintroduced_read_gate(self):
        changes = [
            lambda p: p.update(env={"STRATA_VERIFY_PROFILE": "0"}),
            lambda p: p["matrix"][0].update(env={"STRATA_STAGE_PIN": "0"}),
            lambda p: p.update(profiles=["nsight"]),
            lambda p: p["matrix"][0]["requests"][1].update(profiler="nsight"),
            lambda p: p["matrix"][0]["requests"][1].update(env={"STRATA_ROUTE_RESIDENT": "0"}),
            lambda p: p.update(retry_or_replace_failed_sample=True),
            lambda p: p["matrix"][0].update(append_new_read_includes_pt0_history_reread=False),
            lambda p: p["matrix"][0]["requests"][1].update(new_read_policy="target_3k"),
            lambda p: p["matrix"][0]["requests"][1].update(new_read_target_tokens=3072),
            lambda p: p["matrix"][0]["requests"][1].update(new_read_allowed_range_tokens=[4000, 5000]),
            lambda p: p["matrix"][0]["requests"][1].update(append_padding_allowed=True),
            lambda p: p["matrix"][0]["requests"][1].update(append_user_message_sha256=None),
            lambda p: p["matrix"][0]["requests"][1].update(append_user_message_source_reference=None),
            lambda p: p["matrix"][0]["requests"][1].update(append_user_tokens_upper_bound=True),
            lambda p: p["matrix"][0]["requests"][1].update(rendered_token_ids_sha256="f" * 64),
            lambda p: p["matrix"][0]["requests"][1].update(actual_completion_tokens=2048),
            lambda p: p["matrix"][0]["requests"][1].update(history_status="FIXED"),
            lambda p: p["reference_evidence"]["authorization.json"].update(scope="p01_diagnostic"),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                plan = plan_fixture()
                change(plan)
                with self.assertRaises(ValueError):
                    validate_warm_plan(plan, self.policy)

    def test_policy_cannot_weaken_hard_limits(self):
        policy = copy.deepcopy(self.policy)
        policy["limits"]["diagnostic_output_tokens"] = 128
        with self.assertRaisesRegex(ValueError, "frozen limit mismatch"):
            validate_warm_plan(plan_fixture(), policy)

    def test_real_short_followups_need_no_token_padding_or_read_target(self):
        plan = plan_fixture()
        requests = plan["matrix"][0]["requests"]
        for index in (1, 2):
            request = requests[index]
            self.assertIsNone(request["new_read_target_tokens"])
            self.assertIsNone(request["new_read_allowed_range_tokens"])
            request["prompt_tokens_upper_bound"] = requests[index - 1]["prompt_tokens_upper_bound"] + 2048 + 256 + 64
        self.assertEqual(validate_warm_plan(plan, self.policy)["execution_result"], "NOT_RUN")
        requests[2]["prompt_tokens_upper_bound"] -= 1
        with self.assertRaisesRegex(ValueError, "64-token template/BPE margin"):
            validate_warm_plan(plan, self.policy)

    def test_policy_cannot_restore_superseded_3k_target(self):
        for field, value in (("append_new_read_target_tokens", 3072), ("append_new_read_policy", "target_3k")):
            with self.subTest(field=field):
                policy = copy.deepcopy(self.policy)
                policy["diagnostic"][field] = value
                with self.assertRaises(ValueError):
                    validate_warm_plan(plan_fixture(), policy)

    def test_result_schemas_preserve_missing_and_failure_fields(self):
        for schema in (REQUESTS_SCHEMA, WINDOWS_SCHEMA, DEPENDENCIES_SCHEMA):
            self.assertEqual(schema["type"], "object")
            self.assertIn("missing_reasons", schema["required"])
            json.dumps(schema)
        self.assertIn("FAILED", REQUESTS_SCHEMA["properties"]["execution_status"]["enum"])
        self.assertIn("null", REQUESTS_SCHEMA["properties"]["completion_tokens"]["type"])
        self.assertIn("UNKNOWN", DEPENDENCIES_SCHEMA["properties"]["edges"]["items"]["properties"]["verified"]["enum"])


if __name__ == "__main__":
    unittest.main()
