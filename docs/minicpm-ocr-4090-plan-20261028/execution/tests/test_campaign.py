"""Read-only campaign planning and mutation-boundary checks; no Docker is run."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("run_campaign", Path(__file__).parents[1] / "deploy/run_campaign.py")
campaign = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(campaign)


class CampaignTest(unittest.TestCase):
    def test_idle_snapshot_preserves_existing_get_raw_metrics(self):
        raw = '# HELP fixture preserved\nvllm:num_requests_running 0\nvllm:num_requests_waiting 0\nvllm:time_to_first_token_seconds_sum 1.5\n'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'api.prom'
            with patch.object(campaign.urllib.request, 'urlopen', return_value=io.BytesIO(raw.encode())) as get:
                campaign.require_idle('mini', evidence_path=path)
            self.assertEqual(path.read_text(), raw)
            self.assertEqual(get.call_count, 1)
            with patch.object(campaign.urllib.request, 'urlopen', return_value=io.BytesIO(b'invalid raw\n')):
                with self.assertRaisesRegex(RuntimeError, 'queue metrics unavailable'):
                    campaign.require_idle('mini', evidence_path=path)
            self.assertEqual(path.read_text(), 'invalid raw\n')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "evidence").mkdir()
        self.manifest = self.root / "formal.json"
        self.warmup = self.root / "warmup.json"
        self.pages = [{"page_id": f"p{i}", "document_id": f"d{i}", "source_family_id": f"f{i}",
                       "expected_pixel_hash": f"pixel-{i}", "path": f"inputs/{i}.pdf", "unit_kind": "page"}
                      for i in range(40)]
        self.development = [{"page_id": f"dev{i}", "document_id": f"dev{i}", "source_family_id": f"dev{i}",
                             "path": f"inputs/dev{i}.pdf", "split": "development"} for i in range(4)]
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps({"pages": self.pages}))
        self.warmup.write_text(json.dumps({"pages": self.development}))

    def plan(self):
        return campaign.build_plan(self.root, self.manifest, self.warmup, "test")

    def test_fixed_balanced_order_and_same_denominator(self):
        plan = self.plan()
        self.assertEqual(len(plan["trials"]), 12)
        self.assertEqual(plan["pair_order"].count(["mini", "ovis"]), 3)
        self.assertEqual(plan["pair_order"].count(["ovis", "mini"]), 3)
        self.assertEqual(len({trial["trial_id"] for trial in plan["trials"]}), 12)
        self.assertEqual(plan["fixed_denominator_per_trial"], 40)
        self.assertEqual(plan["page_admission"], 1)
        self.assertEqual(plan["region_limit"], 4)

    def test_trial_uses_the_declared_profile_for_standard_and_acceleration(self):
        plan = self.plan()
        for profile in ("C0-S0", "M1-DSPARK-S0"):
            plan["profile"] = profile
            args = campaign.trial_command(self.root, plan, plan["trials"][0], self.root / "results/profile", {})
            self.assertIn("profile=" + json.dumps(profile), args)
            self.assertEqual(sum(value.startswith("profile=") for value in args), 1)

    def mixed_inputs(self):
        tasks = ["text"] * 70 + ["name"] * 20 + ["formula"] * 6 + ["seal"] * 2 + ["table"] * 2
        self.pages = [{"page_id": f"crop-{index}", "document_id": "shared-source",
                       "source_family_id": "shared-family", "expected_pixel_hash": f"formal-rgb-{index}",
                       "path": f"inputs/crop-{index}.png", "kind": "image", "unit_kind": "crop", "task": task}
                      for index, task in enumerate(tasks)]
        self.development = [{"page_id": f"warm-crop-{index}", "document_id": "shared-source",
                             "source_family_id": "shared-family", "expected_pixel_hash": f"warm-rgb-{index}",
                             "path": f"inputs/warm-{index}.png", "kind": "image", "unit_kind": "crop",
                             "task": task, "split": "development"}
                            for index, task in enumerate(["text", "text", "text", "name"])]
        self.save()

    def test_mixed100_accepts_shared_families_with_disjoint_crop_pixels(self):
        self.mixed_inputs()
        plan = campaign.build_plan(self.root, self.manifest, self.warmup, "r0", workload="mixed100", timing_scope="R0")
        self.assertEqual(plan["fixed_denominator_per_trial"], 100)
        self.assertEqual(plan["task_counts"], {"text": 70, "name": 20, "formula": 6, "seal": 2, "table": 2})
        self.assertEqual(plan["warmup_family_overlap"], ["shared-family"])
        self.assertIn("not holdout quality", plan["reference_scope"])
        self.assertEqual(set(campaign.REGION_TASKS), {"text", "name", "seal", "formula", "display_formula",
                                                    "inline_formula", "table", "chart"})

    def test_mixed100_rejects_pixel_overlap_missing_task_and_wrong_scope(self):
        self.mixed_inputs()
        self.development[0]["expected_pixel_hash"] = self.pages[0]["expected_pixel_hash"]
        self.save()
        with self.assertRaisesRegex(ValueError, "R0 warmup RGB"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "r0", workload="mixed100", timing_scope="R0")
        self.development[0]["expected_pixel_hash"] = "warm-rgb-0"
        self.pages[0]["task"] = "invented-task"
        self.save()
        with self.assertRaisesRegex(ValueError, "public region task"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "r0", workload="mixed100", timing_scope="R0")
        self.pages[0]["task"] = "name"
        self.save()
        with self.assertRaisesRegex(ValueError, "fixed task counts"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "r0", workload="mixed100", timing_scope="R0")
        with self.assertRaisesRegex(ValueError, "mixed100 requires R0"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "r0", workload="mixed100", timing_scope="P0")

    def test_pair_counts_and_capacity_limits_are_frozen_into_cli(self):
        for pairs in [1, 3, 6]:
            with self.subTest(pairs=pairs):
                plan = campaign.build_plan(self.root, self.manifest, self.warmup, f"scan{pairs}",
                                            pairs=pairs, page_admission=4, region_limit=2)
                self.assertEqual(len(plan["trials"]), pairs * 2)
                args = campaign.trial_command(self.root, plan, plan["trials"][0], self.root / "results/scan", {})
                self.assertEqual(args[args.index("--page-admission") + 1], "4")
                self.assertEqual(args[args.index("--region-limit") + 1], "2")
                if pairs == 3:
                    self.assertEqual(plan["pair_order"], [["mini", "ovis"], ["ovis", "mini"], ["mini", "ovis"]])
                if pairs == 1:
                    self.assertEqual(plan["statistics_scope"], "SCAN_ONLY_NO_MAIN_SPEED_INFERENCE")
        with self.assertRaisesRegex(ValueError, "concurrency limit"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "invalid", region_limit=8)

    def test_plan_only_cli_accepts_mixed100_r0_and_scan_configuration(self):
        self.mixed_inputs()
        output = io.StringIO()
        with patch.object(campaign.subprocess, "run") as run, contextlib.redirect_stdout(output):
            result = campaign.main(["--root", str(self.root), "--manifest", str(self.manifest),
                                    "--warmup-manifest", str(self.warmup), "--workload", "mixed100",
                                    "--timing-scope", "R0", "--pairs", "3", "--page-admission", "4",
                                    "--region-limit", "1", "--plan-only"])
        self.assertEqual(result, 0)
        run.assert_not_called()
        plan = json.loads(output.getvalue())
        self.assertEqual(plan["pair_count"], 3)
        self.assertEqual(plan["fixed_denominator_per_trial"], 100)
        self.assertEqual((plan["page_admission"], plan["region_limit"]), (4, 1))

    def test_complete49_requires_all_three_entire_original_pdfs(self):
        self.pages = [{"page_id": f"{document}-p{index + 1:03d}", "document_id": document,
                       "source_family_id": f"family-{document}", "expected_pixel_hash": f"{document}-{index}",
                       "path": f"inputs/{document}.pdf", "kind": "pdf", "page_index": index, "unit_kind": "page"}
                      for document, count in [("PDF-001", 15), ("PDF-002", 26), ("PDF-003", 8)]
                      for index in range(count)]
        self.save()
        plan = campaign.build_plan(self.root, self.manifest, self.warmup, "whole", workload="complete49")
        self.assertEqual(plan["fixed_denominator_per_trial"], 49)
        self.assertEqual(plan["formal_document_count"], 3)
        self.assertEqual(plan["timing_scope"], "D0")
        self.pages[1]["page_index"] = 0
        self.save()
        with self.assertRaisesRegex(ValueError, "every original page exactly once"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "whole", workload="complete49")
        self.pages[1]["page_index"] = 1
        self.pages[1]["kind"] = "image"
        self.save()
        with self.assertRaisesRegex(ValueError, "original PDF inputs"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "whole", workload="complete49")

    def test_p0_uses_prepared_images_for_both_formal_and_warmup(self):
        for row in self.pages + self.development:
            row["kind"] = "image"
            row["path"] = row["path"].replace(".pdf", ".png")
        self.save()
        plan = campaign.build_plan(self.root, self.manifest, self.warmup, "p0", timing_scope="P0")
        args = campaign.trial_command(self.root, plan, plan["trials"][0], self.root / "results/p0", {})
        self.assertEqual(plan["fixed_denominator_per_trial"], 40)
        self.assertEqual(args[args.index("--timing-scope") + 1], "P0")
        self.pages[0]["kind"] = "pdf"
        self.save()
        with self.assertRaisesRegex(ValueError, "never PDFs"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "p0", timing_scope="P0")
        self.pages[0]["kind"] = "image"
        self.development[0]["kind"] = "pdf"
        self.save()
        with self.assertRaisesRegex(ValueError, "never PDFs"):
            campaign.build_plan(self.root, self.manifest, self.warmup, "p0", timing_scope="P0")

    def test_plan_only_does_not_invoke_subprocess_or_write_files(self):
        before = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        with patch.object(campaign.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()):
            result = campaign.main(["--root", str(self.root), "--manifest", str(self.manifest),
                                    "--warmup-manifest", str(self.warmup)])
        self.assertEqual(result, 0)
        run.assert_not_called()
        self.assertEqual(before, sorted(p.relative_to(self.root) for p in self.root.rglob("*")))

    def test_stable_document_grouping_preserves_every_selected_page(self):
        self.pages[39]["document_id"] = "d0"
        self.save()
        grouped = campaign.grouped_manifest(self.root, self.manifest)["pages"]
        self.assertEqual([row["page_id"] for row in grouped[:2]], ["p0", "p39"])
        self.assertEqual({row["page_id"] for row in grouped}, {row["page_id"] for row in self.pages})
        self.assertEqual({row["expected_pixel_hash"] for row in grouped}, {row["expected_pixel_hash"] for row in self.pages})
        self.assertTrue(all(row["path"].startswith("/work/inputs/") for row in grouped))
        self.assertEqual(self.plan()["execution_page_order"][:2], ["p0", "p39"])

    def test_rejects_duplicate_pixels_and_family_overlap(self):
        self.pages[1]["expected_pixel_hash"] = self.pages[0]["expected_pixel_hash"]
        self.save()
        with self.assertRaisesRegex(ValueError, "unique"):
            self.plan()
        self.pages[1]["expected_pixel_hash"] = "pixel-1"
        self.pages[1]["source_family_id"] = "dev0"
        self.save()
        with self.assertRaisesRegex(ValueError, "disjoint"):
            self.plan()

    def test_active_job_is_a_read_only_block(self):
        (self.root / "evidence/install-mini-r3-job.json").write_text('{"status":"PASS"}')
        (self.root / "evidence/ovis-quality-v2-job.json").write_text('{"status":"RUNNING"}')
        with patch.object(campaign, "inspect") as inspect, patch.object(campaign, "command") as command:
            with self.assertRaisesRegex(RuntimeError, "RUNNING"):
                campaign.guard(self.root)
        inspect.assert_not_called()
        command.assert_not_called()

    def test_active_compiler_blocks_before_any_mutation(self):
        (self.root / "evidence/install-mini-r3-job.json").write_text('{"status":"PASS"}')
        with patch.object(campaign, "inspect", return_value={"State": {"Running": True}}), \
                patch.object(campaign, "command", return_value="PID COMMAND\n1234 ninja\n") as command:
            with self.assertRaisesRegex(RuntimeError, "compilation"):
                campaign.guard(self.root)
        self.assertEqual(command.call_args.args[0], ["docker", "top", "ocr29-build-20261028", "-eo", "pid,comm"])

    def test_active_endurance_or_standard_entry_blocks_even_with_idle_api_queue(self):
        (self.root / "evidence/install-mini-r3-job.json").write_text('{"status":"PASS"}')
        plan = self.plan()
        for entry in ["run_endurance.py", "run_standard_validation.py"]:
            with self.subTest(entry=entry):
                def info(container):
                    return {"State": {"Running": container == campaign.CONTAINERS["ovis"]},
                            "Mounts": [{"Destination": "/work", "Source": str(self.root.resolve())}]}

                top = f"PID COMMAND\n2345 /work/releases/ovis/bin/python /work/deploy/{entry} --adapter ovis --tag active\n"
                with patch.object(campaign, "inspect", side_effect=info), \
                        patch.object(campaign, "command", return_value=top) as command, \
                        patch.object(campaign, "metrics", return_value={"running": 0.0, "waiting": 0.0}), \
                        patch.object(campaign, "external_load") as load:
                    row = campaign.run_trial(self.root, plan, plan["trials"][0], self.root / entry, 5, 900)
                self.assertEqual(row["status"], "FAIL")
                self.assertIn("execution/probe process is active", row["error"])
                self.assertEqual(command.call_args_list[0].args[0],
                                 ["docker", "top", campaign.CONTAINERS["ovis"], "-eo", "pid,args"])
                self.assertEqual(command.call_count, 1)
                self.assertFalse(any(call.args[0][:2] in [["docker", "stop"], ["docker", "start"]]
                                     for call in command.call_args_list))
                load.assert_not_called()

    def test_preflight_failure_never_stops_a_running_container(self):
        plan = self.plan()
        with patch.object(campaign, "guard", side_effect=RuntimeError("active job")), \
                patch.object(campaign, "inspect") as inspect, patch.object(campaign, "command") as command:
            row = campaign.run_trial(self.root, plan, plan["trials"][0], self.root / "trial", 5, 900)
        self.assertEqual(row["status"], "FAIL")
        self.assertIn("active job", row["error"])
        inspect.assert_not_called()
        command.assert_not_called()
        self.assertTrue((self.root / "trial/trial.json").exists())

    def test_manifest_drift_fails_before_any_container_mutation(self):
        for drift in ["formal", "warmup", "execution", "warmup-execution"]:
            with self.subTest(drift=drift):
                self.save()
                plan = self.plan()
                execution = self.root / Path(plan["manifest_mount"]).relative_to("/work")
                execution.parent.mkdir(parents=True, exist_ok=True)
                campaign.write_json(execution, campaign.grouped_manifest(self.root, self.manifest))
                execution_warmup = self.root / Path(plan["warmup_mount"]).relative_to("/work")
                campaign.write_json(execution_warmup, campaign.grouped_manifest(self.root, self.warmup))
                target = {"formal": self.manifest, "warmup": self.warmup, "execution": execution,
                          "warmup-execution": execution_warmup}[drift]
                target.write_text(target.read_text() + "\n")
                with patch.object(campaign, "guard"), patch.object(campaign, "inspect") as inspect, \
                        patch.object(campaign, "command") as command:
                    row = campaign.run_trial(self.root, plan, plan["trials"][0], self.root / f"trial-{drift}", 5, 900)
                self.assertEqual(row["status"], "FAIL")
                self.assertIn("manifest changed after freeze", row["error"])
                inspect.assert_not_called()
                command.assert_not_called()

    def test_executor_time_source_or_manifest_drift_fails_and_retains_artifacts(self):
        for drift in ["none", "source", "formal", "warmup", "execution", "warmup-execution"]:
            with self.subTest(drift=drift):
                self.save()
                plan = campaign.build_plan(self.root, self.manifest, self.warmup, f"post-{drift}")
                execution = self.root / Path(plan["manifest_mount"]).relative_to("/work")
                execution.parent.mkdir(parents=True, exist_ok=True)
                campaign.write_json(execution, campaign.grouped_manifest(self.root, self.manifest))
                execution_warmup = self.root / Path(plan["warmup_mount"]).relative_to("/work")
                campaign.write_json(execution_warmup, campaign.grouped_manifest(self.root, self.warmup))
                source = self.root / "adapter.py"
                source.write_text("version = 1\n")
                plan["source_hashes"] = {str(source): campaign.sha(source)}
                changed = {"source": source, "formal": self.manifest, "warmup": self.warmup,
                           "execution": execution, "warmup-execution": execution_warmup}.get(drift)
                trial = plan["trials"][0]
                out = self.root / "results" / trial["trial_id"]
                running = {container: False for container in campaign.CONTAINERS.values()}

                def inspect(container):
                    return {"State": {"Running": running[container], "Pid": 1234,
                                      "StartedAt": "2026-10-29T00:00:00Z"}}

                def command(args, **_):
                    if args[:2] == ["docker", "start"]:
                        running[args[2]] = True
                    elif args[:2] == ["docker", "stop"]:
                        running[args[-1]] = False
                    elif "--out" in args and "capture_runtime_policy.py" in args[1]:
                        Path(args[args.index("--out") + 1]).write_text('{"cpuset":"0-7","policy":{}}')
                    else:
                        self.fail(f"unexpected command: {args}")
                    return ""

                def executor(args, **_):
                    if args[:2] == ["docker", "exec"]:
                        (out / "warmup").mkdir(parents=True)
                        campaign.write_json(out / "summary.json", {"run_status": "COMPLETED", "planned_pages": 40,
                                            "terminal_pages": 40, "timing_scope": "D0", "primary_performance_eligible": True})
                        campaign.write_json(out / "warmup/summary.json", {"status": "PASS"})
                        (out / "retained-model-artifact.txt").write_text("retained original output\n")
                        if changed is not None:
                            changed.write_text(changed.read_text() + "\n")
                    elif args[:2] != ["docker", "logs"]:
                        self.fail(f"unexpected subprocess: {args}")
                    return SimpleNamespace(returncode=0)

                sampler = Mock(returncode=0)
                with patch.object(campaign, "guard"), patch.object(campaign, "external_load", return_value={}), \
                        patch.object(campaign, "inspect", side_effect=inspect), patch.object(campaign, "command", side_effect=command), \
                        patch.object(campaign, "wait_ready"), patch.object(campaign, "require_idle") as idle, \
                        patch.object(campaign.time, "sleep"), patch.object(campaign.subprocess, "Popen", return_value=sampler), \
                        patch.object(campaign.subprocess, "run", side_effect=executor):
                    row = campaign.run_trial(self.root, plan, trial, self.root / f"post-trial-{drift}", 5, 900)
                self.assertEqual(row["status"], "PASS" if drift == "none" else "FAIL", row)
                self.assertEqual(row["executor_exit_code"], 0)
                self.assertEqual([call.kwargs['evidence_path'].name for call in idle.call_args_list
                                  if 'evidence_path' in call.kwargs],
                                 ['api-before-warmup.prom', 'api-after-idle.prom'])
                self.assertTrue((out / "retained-model-artifact.txt").is_file())
                self.assertEqual(row["changed_execution_sources"], [str(source)] if drift == "source" else [])
                self.assertEqual(row["changed_manifests"], [str(changed)] if drift not in {"none", "source"} else [])

    def test_real_producer_host_and_container_absolute_paths_map_both_manifests(self):
        import hashlib
        from PIL import Image
        from ocrbench.core import _decode_page, load_manifest

        spec = importlib.util.spec_from_file_location("prepare_perf_inputs", Path(__file__).parents[1] / "prepare_perf_inputs.py")
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)
        source = self.root / "source"
        source.mkdir()
        formal, development = [], []
        for index in range(44):
            image = Image.new("RGB", (4, 4), (index, 255 - index, 20))
            path = source / f"{index}.png"
            image.save(path)
            row = {"page_id": f"source-{index}", "document_id": f"doc-{index}",
                   "source_family_id": f"family-{index}", "kind": "image", "path": str(path),
                   "expected_pixel_hash": hashlib.sha256(image.tobytes()).hexdigest(), "unit_kind": "page"}
            (formal if index < 40 else development).append(row)
        # Exercise the actual producer, including its absolute target.resolve() output.
        formal = producer.materialize(formal, self.root / "p0-formal40", None, True)
        development = producer.materialize(development, self.root / "p0-dev4", "development", True)
        for origin in ["host", "container"]:
            with self.subTest(origin=origin):
                if origin == "container":
                    formal = [dict(row, path=campaign.mounted(self.root, Path(row["path"]))) for row in formal]
                    development = [dict(row, path=campaign.mounted(self.root, Path(row["path"]))) for row in development]
                self.manifest.write_text(json.dumps({"pages": formal}))
                self.warmup.write_text(json.dumps({"pages": development}))
                plan = campaign.build_plan(self.root, self.manifest, self.warmup, origin, timing_scope="P0")
                args = campaign.trial_command(self.root, plan, plan["trials"][0], self.root / "results" / origin, {})
                self.assertEqual(args[args.index("--manifest") + 1], f"/work/evidence/campaign-{origin}/formal-manifest.json")
                self.assertEqual(args[args.index("--warmup-manifest") + 1], f"/work/evidence/campaign-{origin}/warmup-manifest.json")
                for manifest in [self.manifest, self.warmup]:
                    prepared = campaign.grouped_manifest(self.root, manifest)
                    self.assertTrue(all(row["path"].startswith("/work/") for row in prepared["pages"]))
                    # Resolve the same mount back on the host and run the real consumer's
                    # file validation/decode. No Docker or virtual /work tree is created.
                    host_view = {"pages": [dict(row, path=str(self.root / Path(row["path"]).relative_to("/work")))
                                           for row in prepared["pages"]]}
                    local_manifest = self.root / f"consumer-{origin}-{manifest.name}"
                    local_manifest.write_text(json.dumps(host_view))
                    for row in load_manifest(local_manifest):
                        image, _ = _decode_page(row)
                        self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(), row["expected_pixel_hash"])

    def test_executor_command_has_common_scope_and_cpu_layout_environment(self):
        plan = self.plan()
        args = campaign.trial_command(self.root, plan, plan["trials"][0], self.root / "results/trial", {"max_model_len": 16384})
        self.assertEqual(args[args.index("--page-admission") + 1], "1")
        self.assertEqual(args[args.index("--region-limit") + 1], "4")
        self.assertEqual(args[args.index("--timing-scope") + 1], "D0")
        self.assertIn("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True", args)
        self.assertIn("/opt/minicpm-ocr/.venv-sdk-cpu/bin/python", args)
        self.assertIn("--warmup-manifest", args)
        self.assertIn("--layout-model-dir", args)
        self.assertIn("build_interference=false", args)

    def test_failed_trial_keeps_all_twelve_planned_trials_and_final_failure(self):
        (self.root / "deploy").mkdir()
        for name in ["serve.sh", "capture_runtime_policy.py", "sample_resources.py"]:
            (self.root / "deploy" / name).write_text("fixture\n")
        with patch.object(campaign, "guard"), patch.object(campaign, "run_trial", return_value={"status": "FAIL"}) as trial:
            result = campaign.main(["--root", str(self.root), "--manifest", str(self.manifest),
                                    "--warmup-manifest", str(self.warmup), "--name", "failed", "--execute"])
        self.assertEqual(result, 1)
        self.assertEqual(trial.call_count, 12)
        state = json.loads((self.root / "evidence/campaign-failed/state.json").read_text())
        self.assertEqual(state["status"], "FAIL")
        self.assertEqual(len(state["trials"]), 12)
        self.assertEqual([call.args[2]["candidate"] for call in trial.call_args_list],
                         [candidate for pair in campaign.PAIR_ORDER for candidate in pair])


if __name__ == "__main__":
    unittest.main()
