import concurrent.futures
import hashlib
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from PIL import Image

from ocrbench.core import _decode_page, load_manifest, run_pages
from test_client import Server, normal_response


def simple_adapter(image, context):
    return {"ordered_blocks": [], "text": "text", "raw_text": "text", "markdown": "text",
            "status": "PASS", "errors": [], "requests": []}


def region_task_adapter(image, context):
    result = simple_adapter(image, context)
    result.update(observed_region_task=context.options.get("region_task"), worker_pid=os.getpid())
    context.options["region_task"] = "adapter-local-mutation"
    return result


def hanging_adapter(image, context):
    if context.page_id == "page0":
        held_slot = context.slots.acquire(time.monotonic() + 2)
        time.sleep(3)
        held_slot[1].close()
    else:
        import fcntl
        held = [context.slots.acquire(time.monotonic() + 0.2) for _ in range(4)]
        for _, stream in held:
            fcntl.flock(stream, fcntl.LOCK_UN)
            stream.close()
    return simple_adapter(image, context)


def parallel_adapter(image, context):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(lambda i: context.call([image], "OCR", 100, f"r{i}"), range(4)))
    result = simple_adapter(image, context)
    result["requests"] = [r["request_id"] for r in responses]
    return result


def slow_artifact_adapter(image, context):
    import ocrbench.core as core
    original = core.atomic_json
    def delayed(path, value):
        if path.name == "result.json":
            time.sleep(0.2)
        return original(path, value)
    core.atomic_json = delayed
    result = simple_adapter(image, context)
    result["adapter_finished_monotonic"] = time.monotonic()
    return result


_cached_calls = 0


def cached_adapter(image, context):
    global _cached_calls
    _cached_calls += 1
    result = simple_adapter(image, context)
    result.update(cached_calls=_cached_calls, worker_pid=os.getpid())
    if context.page_id.startswith("WARMUP"):
        time.sleep(0.15)
    return result


def failed_warmup_adapter(image, context):
    result = simple_adapter(image, context)
    result["status"] = "FAIL" if context.page_id.startswith("WARMUP") else "PASS"
    return result


def recovery_adapter(image, context):
    if context.page_id == "page0":
        time.sleep(3)
    return cached_adapter(image, context)


def failed_recovery_warmup_adapter(image, context):
    if context.page_id.startswith("WARMUP-W0-G1"):
        result = simple_adapter(image, context)
        result["status"] = "FAIL"
        return result
    return recovery_adapter(image, context)


def endurance_adapter(image, context):
    if not context.page_id.startswith("WARMUP"):
        time.sleep(0.01 if context.page_id == "first" else 0.12)
    result = simple_adapter(image, context)
    result["worker_pid"] = os.getpid()
    return result


def endurance_hanging_adapter(image, context):
    if not context.page_id.startswith("WARMUP"):
        time.sleep(2)
    return simple_adapter(image, context)


def endurance_failed_recovery_adapter(image, context):
    result = simple_adapter(image, context)
    if context.page_id.startswith("WARMUP-W0-G1"):
        time.sleep(context.options.get("recovery_warmup_delay", 0))
        result.update(status="FAIL", errors=["replacement warmup failed"])
    elif context.page_id == "page0":
        time.sleep(0.02)
        os._exit(17)
    elif not context.page_id.startswith("WARMUP"):
        time.sleep(context.options.get("formal_delay", 0.8))
    return result


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root / "source.png"
        self.pixel_bytes = Image.new("RGB", (30, 30), "white")
        self.pixel_bytes.save(self.image)
        self.pages = [{"page_id": f"page{i}", "document_id": "doc", "path": str(self.image), "kind": "image"} for i in range(2)]
        self.config = {"adapter": "ovis", "out": str(self.root / "run"), "base_url": "http://127.0.0.1:1/v1",
                       "model": "fake", "model_dir": str(self.root), "page_timeout": 5, "document_timeout": 10}
        self.warmup_image = self.root / "warmup.png"
        Image.new("RGB", (30, 30), "blue").save(self.warmup_image)
        self.warmup = [{"page_id": "dev", "document_id": "devdoc", "path": str(self.warmup_image),
                        "kind": "image", "split": "development"}]

    def tearDown(self):
        self.temp.cleanup()

    def events(self):
        return [json.loads(line) for line in (self.root / "run" / "events.jsonl").read_text().splitlines()]

    def test_serial_page_admission_covers_raster_and_artifacts(self):
        result = run_pages(self.pages, self.config, simple_adapter)
        self.assertEqual(result["pass_pages"], 2)
        events = self.events()
        terminal0 = next(i for i, e in enumerate(events) if e["event"] == "page_terminal" and e["page_id"] == "page0")
        admitted1 = next(i for i, e in enumerate(events) if e["event"] == "page_admitted" and e["page_id"] == "page1")
        self.assertLess(terminal0, admitted1)
        page_result = json.loads((self.root / "run/pages/page0/result.json").read_text())
        self.assertEqual(page_result["input_pixel_hash"], hashlib.sha256(self.pixel_bytes.tobytes()).hexdigest())
        self.assertIsNone(result["good_page_per_second"])
        with self.assertRaises(FileExistsError):
            run_pages(self.pages, self.config, simple_adapter)

    def test_cpu_deadline_kills_worker_before_next_admission_and_releases_locks(self):
        self.config["page_timeout"] = 0.5
        self.pages[0].update(source_family_id="family", scene_tags=["handwriting"], unit_kind="crop", split="heldout")
        result = run_pages(self.pages, self.config, hanging_adapter)
        self.assertEqual(result["pass_pages"], 1)
        self.assertLess(result["batch_wall_seconds"], 2)
        events = self.events()
        terminal = next(e for e in events if e["event"] == "page_terminal" and e["page_id"] == "page0")
        admitted = next(e for e in events if e["event"] == "page_admitted" and e["page_id"] == "page1")
        self.assertLess(terminal["monotonic_timestamp"], admitted["monotonic_timestamp"])
        failed = json.loads((self.root / "run/pages/page0/result.json").read_text())
        self.assertEqual([failed[key] for key in ("source_family_id", "scene_tags", "unit_kind", "split")],
                         ["family", ["handwriting"], "crop", "heldout"])

    def test_global_region_four_across_two_page_workers(self):
        def respond(path, data):
            time.sleep(0.03)
            return normal_response(path, data)
        with Server(respond) as server:
            self.config.update(base_url=server.url, page_admission=2)
            result = run_pages(self.pages, self.config, parallel_adapter)
        self.assertEqual(result["pass_pages"], 2)
        active = set()
        peak = 0
        for event in self.events():
            if event["event"] == "region_start":
                active.add(event["request_id"])
                peak = max(peak, len(active))
            elif event["event"] == "region_end":
                active.discard(event["request_id"])
        self.assertEqual(peak, 4)
        self.assertEqual(active, set())

    def test_manifest_strips_ground_truth_and_resolves_relative_paths(self):
        manifest = self.root / "manifest.json"
        page = dict(self.pages[0], path="source.png", text="secret GT", gt={"answer": "secret"})
        manifest.write_text(json.dumps({"pages": [page]}))
        loaded = load_manifest(manifest)
        self.assertEqual(loaded[0]["path"], str(self.image.resolve()))
        self.assertNotIn("gt", loaded[0])
        self.assertNotIn("text", loaded[0])
        page["page_id"] = "../bad"
        manifest.write_text(json.dumps({"pages": [page]}))
        with self.assertRaises(ValueError):
            load_manifest(manifest)

    def test_mixed_r0_tasks_use_same_worker_without_cross_page_option_leak(self):
        self.config.update(timing_scope="R0", options={"region_task": "seal"})
        pages = [dict(self.pages[0], task="text"), dict(self.pages[1], task="formula"),
                 dict(self.pages[0], page_id="page2")]
        manifest = self.root / "mixed.json"
        manifest.write_text(json.dumps({"pages": [dict(page, gt="not inference metadata") for page in pages]}))
        loaded = load_manifest(manifest)
        self.assertTrue(all("gt" not in page for page in loaded))
        summary = run_pages(loaded, self.config, region_task_adapter)
        predictions = json.loads((self.root / "run/predictions.json").read_text())["pages"]
        self.assertEqual(summary["pass_pages"], 3)
        self.assertEqual([page["observed_region_task"] for page in predictions], ["text", "formula", "seal"])
        self.assertEqual(len({page["worker_pid"] for page in predictions}), 1)
        self.assertEqual(self.config["options"], {"region_task": "seal"})

    def test_case_task_does_not_route_d0_or_p0(self):
        for scope in ("D0", "P0"):
            with self.subTest(scope=scope):
                config = dict(self.config, timing_scope=scope, out=str(self.root / scope),
                              options={"region_task": "text"})
                summary = run_pages([dict(self.pages[0], task="not-a-region-task")], config, region_task_adapter)
                page = json.loads((self.root / scope / "pages/page0/result.json").read_text())
                self.assertEqual(summary["pass_pages"], 1)
                self.assertEqual(page["observed_region_task"], "text")

    def test_invalid_r0_task_fails_before_adapter_without_poisoning_next_page(self):
        self.config.update(timing_scope="R0", options={"region_task": "text"})
        pages = [dict(self.pages[0], task="not-a-region-task"), self.pages[1]]
        summary = run_pages(pages, self.config, region_task_adapter)
        predictions = json.loads((self.root / "run/predictions.json").read_text())["pages"]
        self.assertEqual(summary["pass_pages"], 1)
        self.assertEqual(predictions[0]["errors"], ["INVALID_R0_REGION_TASK"])
        self.assertNotIn("observed_region_task", predictions[0])
        self.assertEqual(predictions[1]["observed_region_task"], "text")

    def test_pixel_mismatch_fails_without_adapter_output(self):
        self.pages[0]["expected_pixel_hash"] = "0" * 64
        result = run_pages(self.pages[:1], self.config, simple_adapter)
        self.assertEqual(result["pass_pages"], 0)
        page = json.loads((self.root / "run/pages/page0/result.json").read_text())
        self.assertIn("INPUT_PIXEL_HASH_MISMATCH", page["errors"])

    def test_actual_two_page_pdf_renders_only_admitted_page_at_300dpi(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF unavailable")
        pdf = self.root / "two-pages.pdf"
        with fitz.open() as document:
            for text in ("first", "second"):
                page = document.new_page(width=72, height=144)
                page.insert_text((5, 20), text)
            document.save(pdf)
        pages = [dict(self.pages[i], path=str(pdf), kind="pdf", page_index=i) for i in range(2)]
        result = run_pages(pages, self.config, simple_adapter)
        self.assertEqual(result["pass_pages"], 2)
        first = json.loads((self.root / "run/pages/page0/result.json").read_text())
        self.assertEqual((first["width"], first["height"]), (300, 600))
        events = self.events()
        end0 = next(e["monotonic_timestamp"] for e in events if e["event"] == "page_terminal" and e["page_id"] == "page0")
        raster1 = next(e["monotonic_timestamp"] for e in events if e["event"] == "raster_start" and e["page_id"] == "page1")
        self.assertLess(end0, raster1)

    def test_huge_pdf_rejected_before_pixmap_allocation(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF unavailable")
        pdf = self.root / "huge-canvas.pdf"
        with fitz.open() as document:
            page = document.new_page(width=14400, height=14000)
            page.set_rotation(90)
            document.save(pdf)
        case = dict(self.pages[0], path=str(pdf), kind="pdf", page_index=0)
        with patch.object(fitz.Page, "get_pixmap", side_effect=AssertionError("Raster allocation attempted")) as render:
            with self.assertRaises(Image.DecompressionBombError):
                _decode_page(case)
            render.assert_not_called()

    def test_png_disguised_as_pdf_rejected_before_rasterization(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF unavailable")
        disguised = self.root / "png-disguised.pdf"
        self.pixel_bytes.save(disguised, format="PNG")
        with fitz.open(disguised) as document:
            self.assertFalse(document.is_pdf)
        case = dict(self.pages[0], path=str(disguised), kind="pdf", page_index=0)
        with patch.object(fitz.Page, "get_pixmap", side_effect=AssertionError("Raster allocation attempted")) as render:
            with self.assertRaisesRegex(ValueError, "not a PDF document"):
                _decode_page(case)
            render.assert_not_called()

    def test_pdf_pixel_limit_boundary_and_disabled_limit_preserve_rotated_rgb(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("PyMuPDF unavailable")
        pdf = self.root / "rotated-crop.pdf"
        with fitz.open() as document:
            page = document.new_page(width=80, height=160)
            page.insert_text((10, 30), "rotated")
            page.set_cropbox(fitz.Rect(4, 8, 76, 152))
            page.set_rotation(90)
            document.save(pdf)
        case = dict(self.pages[0], path=str(pdf), kind="pdf", page_index=0)
        with fitz.open(pdf) as document:
            pixmap = document[0].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72),
                                          colorspace=fitz.csRGB, alpha=False)
        pixels = pixmap.width * pixmap.height
        with patch.object(Image, "MAX_IMAGE_PIXELS", pixels // 2 - 1), \
                patch.object(fitz.Page, "get_pixmap", side_effect=AssertionError("Raster allocation attempted")) as render:
            with self.assertRaises(Image.DecompressionBombError):
                _decode_page(case)
            render.assert_not_called()
        for limit in (pixels // 2, None):
            with self.subTest(limit=limit), patch.object(Image, "MAX_IMAGE_PIXELS", limit):
                image, transform = _decode_page(case)
                with image:
                    self.assertEqual(image.size, (600, 300))
                    self.assertEqual(image.mode, "RGB")
                    self.assertEqual(image.tobytes(), pixmap.samples)
                self.assertEqual(transform["dpi"], 300)

    def test_final_latency_includes_artifact_io(self):
        summary = run_pages(self.pages[:1], self.config, slow_artifact_adapter)
        prediction = json.loads((self.root / "run/predictions.json").read_text())["pages"][0]
        self.assertGreaterEqual(prediction["complete_monotonic"] - prediction["adapter_finished_monotonic"], 0.2)
        self.assertEqual(summary["results"][0]["latency_seconds"], prediction["latency_seconds"])

    def test_document_deadline_fallback_preserves_source_metadata(self):
        self.config.update(document_timeout=0.01)
        self.pages[1].update(source_family_id="family2", scene_tags=["name"], unit_kind="crop", split="test")
        summary = run_pages(self.pages, self.config, hanging_adapter)
        failed = json.loads((self.root / "run/pages/page1/result.json").read_text())
        self.assertEqual(failed["errors"], ["DOCUMENT_DEADLINE"])
        self.assertEqual([failed[key] for key in ("source_family_id", "scene_tags", "unit_kind", "split")],
                         ["family2", ["name"], "crop", "test"])
        self.assertEqual(summary["terminal_pages"], 2)

    def test_warmup_primes_every_worker_excluded_from_formal_wall_and_results(self):
        self.config["page_admission"] = 2
        distinct = self.root / "distinct-formal.png"
        Image.new("RGB", (30, 30), "red").save(distinct)
        self.pages[1]["path"] = str(distinct)
        summary = run_pages(self.pages, self.config, cached_adapter, self.warmup)
        self.assertTrue(summary["primary_performance_eligible"])
        self.assertEqual(summary["timing_mode"], "warm_adapter")
        self.assertEqual(summary["input_preparation"], "offline RGB audit discarded; timed D0 rerenders")
        self.assertEqual(summary["storage_cache_state"], "preaccessed/uncontrolled, not cold")
        effective = json.loads((self.root / "run/effective-config.json").read_text())
        self.assertEqual(effective["input_preparation"], summary["input_preparation"])
        self.assertEqual(effective["storage_cache_state"], summary["storage_cache_state"])
        self.assertEqual(summary["submitted_pages"], 2)
        self.assertEqual(summary["pass_pages"], 2)
        warm_summary = json.loads((self.root / "run/warmup/summary.json").read_text())
        self.assertEqual({r["worker_index"] for r in warm_summary["results"]}, {0, 1})
        self.assertEqual(warm_summary["completed_warmup_inputs"], 2)
        predictions = json.loads((self.root / "run/predictions.json").read_text())["pages"]
        self.assertTrue(all(p["cached_calls"] >= 2 for p in predictions))
        self.assertTrue(all(p["execution_phase"] == "formal" for p in predictions))
        self.assertGreater(summary["job_wall_seconds_including_preflight_cold_warmup_shutdown"] - summary["batch_wall_seconds"], 0.15)
        formal_start = next(e["monotonic_timestamp"] for e in self.events() if e["event"] == "timed_workload_start")
        warm_events = [json.loads(line) for line in (self.root / "run/warmup/events.jsonl").read_text().splitlines()]
        self.assertTrue(all(e["monotonic_timestamp"] < formal_start for e in warm_events))

    def test_warmup_pixel_overlap_and_non_development_inputs_are_rejected(self):
        duplicate = self.root / "duplicate.png"
        duplicate.write_bytes(self.image.read_bytes())
        overlapping = [dict(self.warmup[0], path=str(duplicate))]
        summary = run_pages(self.pages, self.config, cached_adapter, overlapping)
        self.assertEqual(summary["run_status"], "WARMUP_FORMAL_RGB_PIXEL_OVERLAP")
        self.assertEqual(summary["submitted_pages"], 0)
        self.assertIsNone(summary["batch_wall_seconds"])
        self.assertFalse(summary["primary_performance_eligible"])
        self.config["out"] = str(self.root / "not-development")
        with self.assertRaises(ValueError):
            run_pages(self.pages, self.config, cached_adapter, [dict(self.warmup[0], split="heldout")])

    def test_failed_warmup_does_not_admit_formal_inputs(self):
        summary = run_pages(self.pages, self.config, failed_warmup_adapter, self.warmup)
        self.assertEqual(summary["run_status"], "WARMUP_FAILED")
        self.assertEqual(summary["submitted_pages"], 0)
        self.assertFalse(summary["primary_performance_eligible"])
        self.assertFalse(any(e["event"] == "page_admitted" for e in self.events()))

    def test_without_warmup_is_explicitly_cold_diagnostic(self):
        summary = run_pages(self.pages, self.config, simple_adapter)
        self.assertEqual(summary["timing_mode"], "cold_adapter")
        self.assertFalse(summary["primary_performance_eligible"])
        self.assertEqual(summary["input_preparation"], "no executor offline RGB audit; timed D0 renders admitted sources")
        self.assertIn("not verified cold", summary["storage_cache_state"])

    def test_four_workers_all_warm_and_duplicate_formal_pixels_stay_diagnostic(self):
        self.config["page_admission"] = 4
        pages = [dict(self.pages[0], page_id=f"page{i}") for i in range(4)]
        summary = run_pages(pages, self.config, cached_adapter, self.warmup)
        warm = json.loads((self.root / "run/warmup/summary.json").read_text())
        self.assertEqual({r["worker_index"] for r in warm["results"]}, {0, 1, 2, 3})
        self.assertEqual(summary["pass_pages"], 4)
        self.assertEqual(summary["submitted_pages"], 4)
        self.assertFalse(summary["primary_performance_eligible"])
        self.assertEqual(summary["performance_ineligibility_reason"], "FORMAL_RGB_DUPLICATES")

    def test_document_assembly_completes_before_next_document_admission(self):
        self.pages.append(dict(self.pages[0], page_id="page2", document_id="doc2"))
        self.config["page_admission"] = 2
        summary = run_pages(self.pages, self.config, simple_adapter)
        self.assertEqual(summary["pass_documents"], 2)
        events = self.events()
        document_end = next(e["monotonic_timestamp"] for e in events if e["event"] == "document_terminal" and e["document_id"] == "doc")
        next_admitted = next(e["monotonic_timestamp"] for e in events if e["event"] == "page_admitted" and e["page_id"] == "page2")
        self.assertLess(document_end, next_admitted)
        for name in ("document.md", "document.txt", "document.raw.txt", "document.json"):
            self.assertTrue((self.root / "run/documents/doc" / name).is_file())

    def test_replacement_worker_warms_again_and_cost_stays_in_formal_wall(self):
        self.config["page_timeout"] = 0.5
        distinct = self.root / "distinct.png"
        Image.new("RGB", (30, 30), "red").save(distinct)
        self.pages[1]["path"] = str(distinct)
        summary = run_pages(self.pages, self.config, recovery_adapter, self.warmup)
        self.assertEqual(summary["terminal_pages"], 2)
        self.assertEqual(summary["pass_pages"], 1)
        self.assertTrue(summary["primary_performance_eligible"])
        self.assertFalse(summary["all_document_artifacts_pass"])
        self.assertGreater(summary["batch_wall_seconds"], 0.65)
        warm = json.loads((self.root / "run/warmup/summary.json").read_text())
        self.assertEqual({r["generation"] for r in warm["results"]}, {0, 1})
        self.assertGreaterEqual(warm["recovery_warmup_worker_seconds"], 0.15)
        predictions = json.loads((self.root / "run/predictions.json").read_text())["pages"]
        self.assertEqual(predictions[1]["cached_calls"], 2)

    def test_failed_recovery_warmup_does_not_continue_unwarmed(self):
        self.config["page_timeout"] = 0.5
        summary = run_pages(self.pages, self.config, failed_recovery_warmup_adapter, self.warmup)
        self.assertEqual(summary["run_status"], "WARMUP_FAILED")
        self.assertEqual(summary["submitted_pages"], 1)
        self.assertEqual(summary["terminal_pages"], 1)
        self.assertFalse(summary["primary_performance_eligible"])

    def endurance_config(self, *, window=0.05, minimum=1):
        self.config.update(execution_mode="E0", timing_scope="P0", page_admission=4, region_limit=4,
                           admission_window_seconds=window, minimum_completed_pages=minimum)
        return [dict(self.warmup[0], page_id=f"dev{i}", document_id=f"devdoc{i}") for i in range(4)]

    def test_endurance_closes_admission_then_drains_partial_document(self):
        warmup = self.endurance_config()
        pages = [dict(self.pages[0], page_id=f"page{i}", source_id=f"original-{i % 2}") for i in range(12)]
        pages += [dict(self.pages[0], page_id="later-doc", document_id="doc2")]
        summary = run_pages(pages, self.config, endurance_adapter, warmup)
        self.assertEqual(summary["run_status"], "COMPLETED")
        self.assertEqual(summary["endurance_status"], "PASS")
        self.assertEqual(summary["submitted_pages"], 4)
        self.assertEqual(summary["terminal_pages"], 4)
        self.assertEqual(summary["candidate_pool_pages"], 13)
        self.assertEqual(summary["not_admitted_pages"], 9)
        self.assertTrue(summary["admitted_workload_drained"])
        self.assertFalse(summary["primary_performance_eligible"])
        self.assertEqual(summary["performance_ineligibility_reason"], "ENDURANCE_REPEATED_WORKLOAD")
        self.assertEqual(summary["admission_stop_reason"], "ADMISSION_WINDOW_ELAPSED")
        self.assertGreaterEqual(summary["admission_elapsed_seconds"], 0.05)
        self.assertGreater(summary["drain_seconds"], 0.03)
        self.assertEqual(summary["pass_documents"], 1)
        self.assertEqual(summary["documents"][0]["selected_unit_count"], 4)
        self.assertEqual(summary["documents"][0]["scope"], "selected_input_units")
        unsubmitted = json.loads((self.root / "run/not-admitted.json").read_text())
        self.assertEqual(unsubmitted["status"], "NOT_ADMITTED")
        self.assertEqual(len(unsubmitted["pages"]), 9)
        predictions = json.loads((self.root / "run/predictions.json").read_text())["pages"]
        self.assertEqual(len(predictions), 4)
        self.assertEqual({page["source_id"] for page in predictions}, {"original-0", "original-1"})
        warm = json.loads((self.root / "run/warmup/summary.json").read_text())
        warm_pids = {json.loads(path.read_text())["worker_pid"] for path in (self.root / "run/warmup/pages").glob("*/result.json")}
        self.assertEqual({page["worker_pid"] for page in predictions}, warm_pids)
        self.assertEqual(len(warm["initialization"]), 4)

    def test_endurance_pool_exhaustion_does_not_claim_full_window(self):
        warmup = self.endurance_config(window=2)
        summary = run_pages(self.pages, self.config, endurance_adapter, warmup)
        self.assertEqual(summary["run_status"], "INSUFFICIENT")
        self.assertEqual(summary["endurance_status"], "INSUFFICIENT")
        self.assertEqual(summary["admission_stop_reason"], "CANDIDATE_POOL_EXHAUSTED")
        self.assertEqual(summary["submitted_pages"], 2)
        self.assertEqual(summary["not_admitted_pages"], 0)
        self.assertTrue(summary["admitted_workload_drained"])
        self.assertLess(summary["admission_elapsed_seconds"], 2)

    def test_endurance_assembles_completed_document_and_next_admitted_prefix(self):
        warmup = self.endurance_config(window=0.08)
        pages = [dict(self.pages[0], page_id="first")]
        pages += [dict(self.pages[0], page_id=f"next{i}", document_id="doc2") for i in range(10)]
        summary = run_pages(pages, self.config, endurance_adapter, warmup)
        self.assertEqual(summary["endurance_status"], "PASS")
        self.assertEqual(summary["submitted_pages"], 5)
        self.assertEqual([(doc["document_id"], doc["selected_unit_count"]) for doc in summary["documents"]],
                         [("doc", 1), ("doc2", 4)])

    def test_endurance_drain_retains_existing_deadlines_and_cleans_workers(self):
        import multiprocessing
        warmup = self.endurance_config()
        self.config["page_timeout"] = 0.25
        pages = [dict(self.pages[0], page_id=f"page{i}") for i in range(12)]
        started = time.monotonic()
        summary = run_pages(pages, self.config, endurance_hanging_adapter, warmup)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(summary["submitted_pages"], 4)
        self.assertEqual(summary["terminal_pages"], 4)
        self.assertEqual(summary["endurance_status"], "FAIL")
        self.assertTrue(all(record["errors"] == ["PAGE_OR_DOCUMENT_DEADLINE"] for record in summary["results"]))
        self.assertEqual(multiprocessing.active_children(), [])

    def test_endurance_recovery_after_close_does_not_cancel_admitted_formal_pages(self):
        warmup = self.endurance_config()
        self.config.update(page_timeout=3, options={})
        pages = [dict(self.pages[0], page_id=f"page{i}") for i in range(12)]
        summary = run_pages(pages, self.config, endurance_failed_recovery_adapter, warmup)
        self.assertEqual(summary["submitted_pages"], 4)
        self.assertEqual(summary["terminal_pages"], 4)
        self.assertEqual(summary["pass_pages"], 3)
        self.assertTrue(summary["admitted_workload_drained"])
        self.assertEqual(summary["endurance_status"], "FAIL")
        warm_events = [json.loads(line) for line in (self.root / "run/warmup/events.jsonl").read_text().splitlines()]
        self.assertFalse(any(event["event"] == "page_admitted" and "-G1-" in event["page_id"]
                             and event["monotonic_timestamp"] > summary["admission_closed_monotonic"]
                             for event in warm_events))
        terminals = [event for event in self.events() if event["event"] == "page_terminal"]
        self.assertEqual({event["page_id"] for event in terminals}, {f"page{i}" for i in range(4)})

    def test_endurance_inflight_recovery_failure_after_close_keeps_draining(self):
        warmup = self.endurance_config(window=0.5)
        self.config.update(page_timeout=3, options={"recovery_warmup_delay": 0.7, "formal_delay": 1.4})
        pages = [dict(self.pages[0], page_id=f"page{i}") for i in range(12)]
        summary = run_pages(pages, self.config, endurance_failed_recovery_adapter, warmup)
        self.assertEqual(summary["admission_stop_reason"], "ADMISSION_WINDOW_ELAPSED")
        self.assertEqual(summary["terminal_pages"], summary["submitted_pages"])
        self.assertEqual(summary["pass_pages"], 3)
        self.assertTrue(summary["admitted_workload_drained"])
        self.assertEqual(summary["endurance_status"], "FAIL")
        self.assertEqual(summary["endurance_recovery_errors"][0]["reason"], "RECOVERY_WARMUP_FAILED")
        warm_events = [json.loads(line) for line in (self.root / "run/warmup/events.jsonl").read_text().splitlines()]
        recovery = [event for event in warm_events if "-G1-" in event.get("page_id", "")]
        admitted = next(event for event in recovery if event["event"] == "page_admitted")
        failed = next(event for event in recovery if event["event"] == "page_terminal")
        self.assertLess(admitted["monotonic_timestamp"], summary["admission_closed_monotonic"])
        self.assertGreater(failed["monotonic_timestamp"], summary["admission_closed_monotonic"])

    def test_endurance_early_recovery_failure_closes_admission_but_drains_formal_pages(self):
        warmup = self.endurance_config(window=3)
        self.config.update(page_timeout=3, options={})
        pages = [dict(self.pages[0], page_id=f"page{i}") for i in range(12)]
        summary = run_pages(pages, self.config, endurance_failed_recovery_adapter, warmup)
        self.assertEqual(summary["admission_stop_reason"], "RECOVERY_WARMUP_FAILED")
        self.assertLess(summary["admission_elapsed_seconds"], 3)
        self.assertEqual(summary["submitted_pages"], 4)
        self.assertEqual(summary["terminal_pages"], 4)
        self.assertTrue(summary["admitted_workload_drained"])
        self.assertEqual(summary["endurance_status"], "FAIL")
        warm = json.loads((self.root / "run/warmup/summary.json").read_text())
        self.assertEqual(warm["status"], "FAIL")

    def test_endurance_minimum_count_is_not_satisfied_by_unadmitted_pool(self):
        from unittest.mock import patch
        import ocrbench.core as core
        warmup = self.endurance_config(minimum=300)
        pages = [dict(self.pages[0], page_id=f"page{i}") for i in range(320)]
        with patch.object(core, "_decode_page", wraps=core._decode_page) as decode:
            summary = run_pages(pages, self.config, endurance_adapter, warmup)
        # Parent preflight decodes each distinct source once; online worker
        # decoding remains real and lives in separate spawned processes.
        self.assertEqual(decode.call_count, 2)
        self.assertEqual(summary["run_status"], "INSUFFICIENT")
        self.assertEqual(summary["endurance_status"], "INSUFFICIENT")
        self.assertEqual(summary["terminal_pages"], 4)
        self.assertFalse(summary["minimum_completed_pages_met"])

    def test_endurance_window_cannot_change_fixed_mode_or_skip_required_warmup(self):
        self.config["admission_window_seconds"] = 1
        with self.assertRaisesRegex(ValueError, "explicit E0"):
            run_pages(self.pages, self.config, simple_adapter)
        self.config.update(execution_mode="E0", timing_scope="P0", page_admission=4, region_limit=4)
        with self.assertRaisesRegex(ValueError, "four development"):
            run_pages(self.pages, self.config, simple_adapter, self.warmup)

    def test_endurance_pool_repeats_sources_with_unique_operational_ids(self):
        import importlib.util
        path = Path(__file__).parents[1] / "deploy/run_endurance.py"
        spec = importlib.util.spec_from_file_location("endurance_entry", path)
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        source = [dict(self.pages[0], source_id="frozen-source", expected_pixel_hash="frozen-pixels", source_family_id="family"),
                  dict(self.pages[1], document_id="other"),
                  dict(self.pages[0], page_id="page2")]
        pool = entry.build_pool(source, 2)
        self.assertEqual(len(pool), 6)
        self.assertEqual(len({case["page_id"] for case in pool}), 6)
        self.assertEqual(len({case["document_id"] for case in pool}), 4)
        self.assertEqual([case["original_page_id"] for case in pool], ["page0", "page2", "page1"] * 2)
        self.assertTrue(all(case["path"] == str(self.image) for case in pool))
        self.assertEqual(pool[0]["source_id"], "frozen-source")
        self.assertEqual(pool[0]["source_family_id"], "family")
        self.assertEqual(pool[0]["expected_pixel_hash"], "frozen-pixels")
        self.assertEqual(pool[1]["source_id"], "page2")


if __name__ == "__main__":
    unittest.main()
