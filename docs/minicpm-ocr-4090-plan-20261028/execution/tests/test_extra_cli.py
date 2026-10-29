"""Real file/context integration with a fake model; no GPU/quality claim."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from ocrbench import extra_cli as extra


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, images, prompt, limit, deadline, evidence, request_id):
        self.calls.append({"images": images, "prompt": prompt, "limit": limit})
        answer = self.responses.pop(0)
        return {"request_id": request_id, "content": answer.get("content", ""),
                "finish_reason": answer.get("finish_reason", "stop"),
                "status": answer.get("status", "PASS"), "usage": {}, "error": answer.get("error")}


class ExtraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage1 = self.root / "stage1"
        self.stage1.mkdir()
        self.config = {"base_url": "http://localhost:1/v1", "model": "ovisocr3", "model_dir": str(self.root)}
        self.prompt_patch = patch("ocrbench.ovis._load_prompt", return_value=("official prompt", "fixed-hash"))
        self.prompt_patch.start()
        self.addCleanup(self.prompt_patch.stop)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def make_stage1(self, counts=(1, 1), docs=None, indices=None):
        cases, predictions = [], []
        docs = docs or ["doc"] * len(counts)
        indices = indices or list(range(len(counts)))
        for index, table_count in enumerate(counts):
            page_id = f"p{index}"
            original = self.root / f"original-{index}.png"
            image = Image.new("RGB", (20, 30), (index, 100, 200))
            image.save(original)
            folder = self.stage1 / "pages" / page_id
            folder.mkdir(parents=True)
            image.save(folder / "input.png")
            case = {"page_id": page_id, "document_id": docs[index], "page_index": indices[index],
                    "path": str(original), "kind": "image"}
            blocks = [{"block_type": "text", "content": f"Body-{index}", "text": f"Body-{index}"}]
            for number in range(table_count):
                html = f"<table><tr><td>{index}-{number}</td></tr></table>"
                blocks.append({"block_type": "table", "content": html, "table_html": html})
            result = {"page_id": page_id, "document_id": docs[index], "status": "PASS", "finish_reason": "stop",
                      "request_records": [{"status": "PASS", "finish_reason": "stop"}],
                      "adapter_version": "ovis-adapter-v1", "mode": "structured", "region_task": None,
                      "timing_scope": "D0", "unit_kind": "page", "width": 20, "height": 30,
                      "source_sha256": extra._file_sha(original), "input_pixel_hash": extra._sha(image.tobytes()),
                      "ordered_blocks": blocks, "markdown": "\n\n".join(b["content"] for b in blocks)}
            self.write(folder / "result.json", result)
            cases.append(case)
            predictions.append(result)
        self.write(self.stage1 / "input-manifest.json", {"pages": cases})
        self.write(self.stage1 / "predictions.json", {"pages": predictions})
        return cases, predictions

    def result(self, pair="pair-00001"):
        return extra._read(self.root / "out" / "pairs" / pair / "result.json")

    def positive(self):
        return {"content": json.dumps([{"source_pages": [1, 2],
                                        "html": "<table><tr><td>merged</td></tr></table>"}])}

    def add_embedded_image(self, predictions):
        reference = "images/bbox_100_200_500_800.jpg"
        source = self.stage1 / "pages/p0" / reference
        source.parent.mkdir()
        Image.new("RGB", (8, 10), "green").save(source)
        raw_html = f'<table><tr><td><img src="{reference}" /></td></tr></table>'
        product = raw_html.replace("</td>", '<br/><span data-ocr-supplement="image">图中文字</span><br/></td>')
        table = predictions[0]["ordered_blocks"][1]
        table.update(content=product, table_html=product, raw_content=raw_html, raw_table_html=raw_html,
                     embedded_images=[{"image_reference": reference, "crop_file_sha256": extra._file_sha(source),
                                       "bbox_normalized": [100, 200, 500, 800], "visible_image_text": "图中文字"}])
        predictions[0]["adapter_version"] = "ovis-adapter-v2"
        predictions[0]["markdown"] = "\n\n".join(b["content"] for b in predictions[0]["ordered_blocks"])
        self.write(self.stage1 / "pages/p0/result.json", predictions[0])
        self.write(self.stage1 / "predictions.json", {"pages": predictions})
        return reference, source

    def test_actual_entry_uses_two_verified_stage1_images_and_audits_body(self):
        self.make_stage1()
        original_hash = extra._file_sha(self.stage1 / "predictions.json")
        client = Client([self.positive()])
        summary = extra.run_pairs(self.stage1, self.root / "out", self.config, client=client)
        self.assertEqual(summary["pass_pairs"], 1)
        self.assertEqual(summary["profile"], "O1-16K-PRED")
        result = self.result()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["profile"], "O1-16K-PRED")
        self.assertIsNone(result["service_policy_evidence"])
        self.assertEqual(result["writeback_audit"]["selected_operand_fragment_ids"], [["p0", 0], ["p1", 0]])
        self.assertTrue(result["writeback_audit"]["non_table_content_preserved"])
        self.assertEqual(len(client.calls[0]["images"]), 2)
        self.assertEqual(client.calls[0]["images"][0], self.stage1 / "pages/p0/input.png")
        self.assertEqual(client.calls[0]["limit"], 8192)
        self.assertEqual(extra._file_sha(self.stage1 / "predictions.json"), original_hash)
        self.assertFalse(summary["combined_stage1_stage2_end_to_end_measured"])
        self.assertTrue((self.root / "out/pairs/pair-00001/request-records.json").is_file())
        self.assertEqual((self.root / "out/pairs/pair-00001/rewritten/p1/document.md").read_text(), "Body-1")

    def test_auto_pairs_follow_document_and_original_adjacent_order(self):
        cases, _ = self.make_stage1((1, 1, 1, 1, 1), docs=["A", "A", "A", "B", "B"], indices=[0, 2, 3, 0, 1])
        pairs = extra.select_pairs({case["page_id"]: case for case in reversed(cases)})
        self.assertEqual([pair["page_ids"] for pair in pairs], [["p1", "p2"], ["p3", "p4"]])

    def test_lowpixel_cli_preserves_profile_and_readonly_service_policy_evidence(self):
        self.make_stage1()
        policy = {"max_pixels": 4147200, "max_model_len": 16384, "max_images": 2}
        policy_path = self.root / "service-policy.json"
        self.write(policy_path, policy)
        before = policy_path.read_bytes()
        with patch.object(extra, "VLLMClient", return_value=Client([self.positive()])), patch("builtins.print"):
            code = extra.main([
                "--stage1-run", str(self.stage1), "--out", str(self.root / "out"),
                "--base-url", "http://localhost:1/v1", "--model", "ovisocr3", "--model-dir", str(self.root),
                "--profile", "O1-LOWPIX-16K-PRED", "--service-policy-evidence", str(policy_path),
            ])
        self.assertEqual(code, 0)
        self.assertEqual(policy_path.read_bytes(), before)
        summary = extra._read(self.root / "out/summary.json")
        config = extra._read(self.root / "out/effective-config.json")
        result = self.result()
        for document in (summary, config, result, summary["results"][0]):
            self.assertEqual(document["profile"], "O1-LOWPIX-16K-PRED")
        metadata = summary["service_policy_evidence"]
        self.assertEqual(metadata["sha256"], extra._sha(before))
        self.assertEqual(metadata["source_path"], str(policy_path.resolve()))
        self.assertEqual(metadata["bytes"], len(before))
        snapshot = extra._read(Path(metadata["snapshot_path"]))
        self.assertEqual(snapshot["content"], policy)
        self.assertEqual(result["service_policy_evidence"], metadata)

    def test_explicit_cross_document_nonadjacent_and_reverse_pairs_rejected(self):
        cases, _ = self.make_stage1((1, 1, 1), docs=["A", "A", "B"], indices=[0, 2, 1])
        by_id = {case["page_id"]: case for case in cases}
        for ids in [["p0", "p2"], ["p0", "p1"], ["p1", "p0"]]:
            self.write(self.root / "pairs.json", {"pairs": [{"page_ids": ids}]})
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                extra.select_pairs(by_id, self.root / "pairs.json")

    def test_multi_table_refusal_keeps_side_table_and_every_original_hash(self):
        self.make_stage1((2, 1))
        before = extra._file_sha(self.stage1 / "pages/p0/result.json")
        summary = extra.run_pairs(self.stage1, self.root / "out", self.config, client=Client([self.positive()]))
        result = self.result()
        self.assertEqual(summary["unsupported_pairs"], 1)
        self.assertFalse(result["writeback_applied"])
        self.assertEqual(len(result["writeback_audit"]["unselected_fragments"]), 3)
        self.assertEqual(result["original_pages"][0]["ordered_blocks"][2]["table_html"],
                         "<table><tr><td>0-1</td></tr></table>")
        self.assertEqual(extra._file_sha(self.stage1 / "pages/p0/result.json"), before)

    def test_budget_failure_is_preserved_at_pair_and_request_level(self):
        self.make_stage1()
        client = Client([{"status": "FAIL_BUDGET", "error": "INPUT_PLUS_MARGIN_EXCEEDS_16K"}])
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=client)
        result = self.result()
        self.assertEqual(result["status"], "FAIL_BUDGET")
        self.assertEqual(result["request_records"][0]["status"], "FAIL_BUDGET")
        self.assertFalse(result["writeback_applied"])

    def test_three_page_chain_reports_unsupported_without_pseudo_recursive_calls(self):
        self.make_stage1((1, 1, 1))
        self.write(self.root / "pairs.json", {"pairs": [{"pair_id": "chain", "page_ids": ["p0", "p1", "p2"]}]})
        client = Client([])
        summary = extra.run_pairs(self.stage1, self.root / "out", self.config,
                                  pairs_manifest=self.root / "pairs.json", client=client)
        result = self.result("chain")
        self.assertEqual(summary["unsupported_pairs"], 1)
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertEqual(len(result["original_table_fragments"]), 3)
        self.assertEqual(client.calls, [])

    def test_stage1_truncated_model_call_prevents_any_stage2_inference(self):
        _, predictions = self.make_stage1()
        predictions[0]["request_records"][0]["finish_reason"] = "length"
        self.write(self.stage1 / "pages/p0/result.json", predictions[0])
        self.write(self.stage1 / "predictions.json", {"pages": predictions})
        client = Client([])
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=client)
        self.assertEqual(self.result()["status"], "FAIL")
        self.assertIn("INVALID_STAGE1_MODEL_CALL", self.result()["errors"][0])
        self.assertEqual(self.result()["stage1_predecessors"][0]["model_call_statuses"][0]["finish_reason"], "length")
        self.assertEqual(client.calls, [])

    def test_prediction_and_input_pixels_cannot_silently_drift(self):
        self.make_stage1()
        Image.new("RGB", (20, 30), "red").save(self.stage1 / "pages/p0/input.png")
        client = Client([])
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=client)
        self.assertIn("STAGE1_INPUT_PIXEL_HASH_MISMATCH", self.result()["errors"][0])
        self.assertEqual(client.calls, [])

    def test_full_predictions_denominator_must_match_manifest(self):
        _, predictions = self.make_stage1()
        self.write(self.stage1 / "predictions.json", {"pages": predictions[:1]})
        with self.assertRaisesRegex(ValueError, "same page denominator"):
            extra.load_stage1(self.stage1)

    def test_writeback_audit_rejects_unselected_body_mutation(self):
        _, pages = self.make_stage1()
        fragments = extra._fragments(pages)
        result = {"original_pages": copy.deepcopy(pages), "writeback_applied": True,
                  "merged_fragment_ancestry": [["p0", 0], ["p1", 0]],
                  "raw_output": self.positive()["content"],
                  "rewritten_markdown": ["changed body", "Body-1"]}
        with self.assertRaisesRegex(ValueError, "UNSELECTED_CONTENT_CHANGED"):
            extra._audit_writeback(pages, result, fragments)

    def test_exported_markdown_keeps_page_local_image_resource(self):
        _, predictions = self.make_stage1()
        source = self.stage1 / "pages/p0/images/diagram.jpg"
        source.parent.mkdir()
        Image.new("RGB", (4, 4), "green").save(source)
        visual = {"block_type": "image", "content": '<img src="images/diagram.jpg" />',
                  "image_reference": "images/diagram.jpg"}
        predictions[0]["ordered_blocks"].append(visual)
        predictions[0]["markdown"] += "\n\n" + visual["content"]
        self.write(self.stage1 / "pages/p0/result.json", predictions[0])
        self.write(self.stage1 / "predictions.json", {"pages": predictions})
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=Client([self.positive()]))
        result = self.result()
        self.assertEqual(result["status"], "PASS")
        exported = self.root / "out/pairs/pair-00001/rewritten/p0/images/diagram.jpg"
        self.assertEqual(extra._file_sha(source), extra._file_sha(exported))
        self.assertTrue(result["exported_pages"][0]["resources"])

    def test_no_merge_exports_v2_embedded_table_images_with_stage1_hash(self):
        _, predictions = self.make_stage1()
        reference, source = self.add_embedded_image(predictions)
        negative = {"content": json.dumps([{"source_pages": [],
                                            "html": "No cross-page table exists between these pages."}])}
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=Client([negative]))
        result = self.result()
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["writeback_applied"])
        exported = self.root / "out/pairs/pair-00001/rewritten/p0" / reference
        self.assertTrue(exported.is_file())
        self.assertEqual(extra._file_sha(source), extra._file_sha(exported))
        self.assertEqual(result["exported_pages"][0]["resources"][0]["relative_path"], reference)

    def test_generated_merge_image_without_source_mapping_is_not_success(self):
        self.make_stage1()
        answer = {"content": json.dumps([{"source_pages": [1, 2], "html":
                  '<table><tr><td><img src="images/bbox_100_200_500_800.jpg" /></td></tr></table>'}])}
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=Client([answer]))
        result = self.result()
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertFalse(result["writeback_applied"])
        self.assertNotIn("exported_pages", result)
        self.assertEqual(result["original_pages"][0]["ordered_blocks"][1]["table_html"],
                         "<table><tr><td>0-0</td></tr></table>")

    def test_embedded_image_operand_cannot_be_written_back_without_source_mapping(self):
        _, predictions = self.make_stage1()
        _, source = self.add_embedded_image(predictions)
        before = extra._file_sha(source)
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=Client([self.positive()]))
        result = self.result()
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertFalse(result["writeback_applied"])
        self.assertEqual(result["unsupported_feature"], "crosspage_image_source_mapping")
        self.assertEqual(extra._file_sha(source), before)
        self.assertNotIn("exported_pages", result)

    def test_tampered_stage1_embedded_resource_cannot_be_exported_as_success(self):
        _, predictions = self.make_stage1()
        _, source = self.add_embedded_image(predictions)
        source.write_bytes(b"changed")
        negative = {"content": json.dumps([{"source_pages": [],
                                            "html": "No cross-page table exists between these pages."}])}
        extra.run_pairs(self.stage1, self.root / "out", self.config, client=Client([negative]))
        result = self.result()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("STAGE1_RESOURCE_HASH_MISMATCH", result["errors"][-1])


if __name__ == "__main__":
    unittest.main()
