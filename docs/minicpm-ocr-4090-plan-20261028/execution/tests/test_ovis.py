"""Adapter contract tests; no OCR, GPU, or model quality claim."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from ocrbench import ovis


def response(content, *, status="PASS", finish_reason="stop"):
    return {"content": content, "status": status, "finish_reason": finish_reason,
            "usage": {}, "request_id": "request", "error": None}


class Context:
    def __init__(self, directory, responses, **options):
        self.model_dir = directory
        self.output_dir = directory
        self.options = options
        self.page_id = "page-01"
        self.requests = []
        self.pending = list(responses)
        self.calls = []
        self.events = []

    def emit(self, event, **fields):
        self.events.append((event, fields))

    def call(self, paths, prompt, limit, task):
        self.calls.append((paths, prompt, limit, task))
        result = self.pending.pop(0)
        result["request_id"] = f"request-{len(self.calls)}"
        self.requests.append(result)
        return result


def block(category, content, bbox=None):
    return {"category": category, "content": content, "bbox": bbox or [0, 0, 999, 999]}


class OvisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "input.png"
        Image.new("RGB", (100, 200), "white").save(self.image)
        self.prompt_patch = patch.object(ovis, "_load_prompt", return_value=("fixed official prompt", "hash"))
        self.prompt_patch.start()
        self.addCleanup(self.prompt_patch.stop)

    def test_complete_structured_page_and_predicted_visual_crop(self):
        structured = [
            block("header", "Header"), block("text", "Body"),
            block("table", "<table><tr><td>A</td><td>B</td></tr></table>"),
            block("display_formula", "$$x^2$$"),
            block("image", '<img src="images/bbox_100_200_500_800.jpg" />', [100, 200, 500, 800]),
            block("footer", "Page 1"),
        ]
        context = Context(self.root, [response(json.dumps(structured)), response("Figure labels")])
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["text"], "Header\nBody\nA\tB\nFigure labels\nPage 1")
        self.assertEqual(result["ordered_blocks"][3]["formula_latex"], "$$x^2$$")
        self.assertEqual(result["raw_output"], json.dumps(structured))
        visual = result["ordered_blocks"][4]
        self.assertEqual(visual["bbox"], [10, 40, 50, 160])
        with Image.open(context.calls[1][0][0]) as crop:
            self.assertEqual(crop.size, (40, 120))
            self.assertEqual(ovis._sha(crop.convert("RGB").tobytes()), visual["inference_crop_rgb_sha256"])
        self.assertTrue((self.root / visual["image_reference"]).is_file())
        self.assertEqual(len(result["requests"]), 2)

    def test_schema_failure_does_not_salvage_text(self):
        context = Context(self.root, [response('```json\n[]\n```')])
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["text"], "")
        self.assertIn("INVALID_JSON", result["errors"][0])

    def test_schema_rejects_bad_coordinates_and_unhashable_category(self):
        for invalid in [block([], "x"), block("text", "x", [0, 0, 1000, 3]),
                        block("text", "x", [False, 0, 5, 3]), block("text", "x", [4, 0, 2, 3])]:
            with self.subTest(invalid=invalid), self.assertRaises(ovis.OvisOutputError):
                ovis.parse_structured(json.dumps([invalid]))

    def test_length_and_budget_are_terminal_failures(self):
        for answer, expected in [(response("[]", finish_reason="length"), "FAIL"),
                                 (response("", status="FAIL_BUDGET"), "FAIL_BUDGET")]:
            with self.subTest(expected=expected):
                result = ovis.process_page(self.image, Context(self.root, [answer]))
                self.assertEqual(result["status"], expected)

    def test_failed_supplement_preserves_partial_raw_and_fails_page(self):
        structured = [block("image", '<img src="images/bbox_0_0_999_999.jpg" />')]
        context = Context(self.root, [response(json.dumps(structured)), response("partial", finish_reason="length")])
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["ordered_blocks"][0]["raw_text"], "partial")
        self.assertEqual(result["ordered_blocks"][0]["status"], "FAIL")

    def test_wrong_image_reference_is_not_fetched(self):
        structured = [block("image", '<img src="https://invalid.example/private.png" />')]
        context = Context(self.root, [response(json.dumps(structured))])
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(context.calls), 1)

    def test_figure_caption_is_not_ocr_text(self):
        structured = [block("image", "<caption>A chart.</caption><mermaid>graph TD;A-->B;</mermaid>")]
        context = Context(self.root, [response(json.dumps(structured))], ovis_mode="figure")
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["text"], "")
        self.assertIn("caption_output", result["ordered_blocks"][0])

    def test_region_task_uses_own_limit(self):
        context = Context(self.root, [response("name")], region_task="seal")
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(context.calls[0][2], 2048)

    def test_r0_table_adapter_output_is_consumed_by_real_structural_scorer(self):
        from ocrbench.scoring import structural_scores, prediction_digest
        html = "<table><tr><td>A</td><td>B</td></tr></table>"
        prediction = ovis.process_page(self.image, Context(self.root, [response(html)], region_task="table"))
        gt = {"acceptance_rule_id": "page-good-v1", "applicability": {"table": True}, "structure_GT": {"table": [{"id": "table-1", "html": html}]},
              "assessment": {"kind": "human_verified_correspondence", "prediction_sha256": prediction_digest(prediction),
                             "matches": {"table-1": 0}}}
        metrics = structural_scores(prediction, gt)["table"]
        self.assertEqual(prediction["ordered_blocks"][0]["bbox"], [0, 0, 100, 200])
        self.assertEqual(metrics["TEDS"], 1.0)
        self.assertEqual(metrics["cell_CER"], 0.0)
        self.assertTrue(metrics["passes"])

    def test_r0_formula_adapter_retains_block_for_scorer_and_excludes_page_cer(self):
        from ocrbench.scoring import structural_scores, prediction_digest
        latex = "x^2"
        prediction = ovis.process_page(self.image, Context(self.root, [response(latex)], region_task="formula"))
        gt = {"acceptance_rule_id": "page-good-v1", "applicability": {"formula": True}, "structure_GT": {"formula": [{"id": "formula-1", "latex": latex}]},
              "assessment": {"kind": "human_verified_correspondence", "prediction_sha256": prediction_digest(prediction),
                             "matches": {"formula-1": 0}}}
        metrics = structural_scores(prediction, gt)["formula"]
        self.assertEqual(prediction["raw_text"], "")
        self.assertEqual(prediction["ordered_blocks"][0]["raw_content"], latex)
        self.assertEqual(metrics["latex_EM"], [True])
        self.assertEqual(metrics["status"], "UNAVAILABLE")  # Rendering is an independent gate.
        self.assertEqual(prediction["markdown"], "$$\nx^2\n$$")

    def test_every_mode_has_markdown_serializable_for_document_export(self):
        from ocrbench.client import atomic_json
        cases = [
            ({"ovis_mode": "plain"}, "Plain OCR", "Plain OCR"),
            ({"ovis_mode": "markdown"}, "# Title", "# Title"),
            ({"region_task": "formula"}, "$$x^2$$", "$$x^2$$"),
            ({"region_task": "inline_formula"}, "x^2", "$x^2$"),
            ({}, json.dumps([block("display_formula", "x^2"), block("text", "Body")]), "$$\nx^2\n$$\n\nBody"),
            ({"ovis_mode": "figure"}, json.dumps([block("image", "<caption>A diagram.</caption>")]),
             "<caption>A diagram.</caption>"),
        ]
        for index, (options, raw, expected) in enumerate(cases):
            with self.subTest(options=options):
                result = ovis.process_page(self.image, Context(self.root, [response(raw)], **options))
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["raw_output"], raw)
                path = self.root / f"mode-{index}.json"
                atomic_json(path, result)
                stored = json.loads(path.read_text())
                markdown_path = self.root / f"mode-{index}.md"
                markdown_path.write_text(stored["markdown"], encoding="utf-8")
                self.assertEqual(markdown_path.read_text(), expected)
                if options.get("ovis_mode") == "figure":
                    self.assertEqual(stored["raw_text"], "")
                    self.assertTrue(stored["ordered_blocks"][0]["derived_content"])

    def test_prompt_bytes_must_match_lock(self):
        self.prompt_patch.stop()
        prompts = self.root / "prompts"
        prompts.mkdir()
        (prompts / "plain_ocr.txt").write_text("changed prompt")
        with self.assertRaisesRegex(ovis.OvisOutputError, "PROMPT_HASH_MISMATCH"):
            ovis._load_prompt(Context(self.root, []), "plain_ocr.txt")

    def test_invalid_table_and_embedded_image_explicitly_fail(self):
        for html in ["<table><tr><td>incomplete", '<table><tr><td><img src="x"></td></tr></table>',
                     "<table><td>cell without row</td></table>"]:
            with self.subTest(html=html), self.assertRaises(ovis.OvisOutputError):
                ovis.table_text(html)

    def test_table_serialization_retains_cell_whitespace_and_empty_last_cell(self):
        self.assertEqual(ovis.table_text("<table><tr><td> A </td><td></td></tr><tr><td>B<br>C</td><td> D </td></tr></table>"),
                         " A \t\nB\nC\t D ")

    def test_real_four_image_table_shape_exports_and_reads_each_predicted_crop(self):
        references = ["220_106_400_180", "550_103_682_249", "226_318_396_426", "567_309_696_466"]
        html = ('<table border="1"><tr><td>A</td><td><img src="images/bbox_' + references[0] + '.jpg" /></td>'
                '<td>B</td><td><img src="images/bbox_' + references[1] + '.jpg" /></td></tr>'
                '<tr><td>C</td><td><img src="images/bbox_' + references[2] + '.jpg" /></td>'
                '<td>D</td><td><img src="images/bbox_' + references[3] + '.jpg" /></td></tr></table>')
        raw = json.dumps([block("table", html, [100, 50, 800, 900])])
        additions = ["图一 <x>&", "图二", "图三", "图四"]
        context = Context(self.root, [response(raw)] + [response(text) for text in additions])
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["adapter_version"], "ovis-adapter-v2")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["ordered_blocks"]), 1)
        table = result["ordered_blocks"][0]
        self.assertEqual(table["raw_content"], html)
        self.assertEqual(table["raw_table_html"], html)
        self.assertEqual(result["raw_output"], raw)
        self.assertEqual(len(context.calls), 5)
        self.assertEqual(len(result["requests"]), 5)
        self.assertEqual(len(table["request_ids"]), 5)
        self.assertEqual(len(table["embedded_images"]), 4)
        self.assertEqual(table["embedded_images"][0]["bbox"], [22, 21, 40, 36])
        self.assertEqual([entry["cell_ordinal"] for entry in table["embedded_images"]],
                         [{"row": 0, "column": 1}, {"row": 0, "column": 3},
                          {"row": 1, "column": 1}, {"row": 1, "column": 3}])
        for index, embedded in enumerate(table["embedded_images"]):
            self.assertTrue((self.root / embedded["image_reference"]).is_file())
            crop_path = self.root / embedded["inference_crop_reference"]
            self.assertEqual(context.calls[index + 1][0], [crop_path])
            self.assertEqual(context.calls[index + 1][2], 4096)
            with Image.open(crop_path) as crop:
                self.assertEqual(ovis._sha(crop.tobytes()), embedded["inference_crop_rgb_sha256"])
            self.assertIn(additions[index], result["raw_text"])
        self.assertIn("&lt;x&gt;&amp;", table["table_html"])
        self.assertNotIn("<x>", table["table_html"])
        self.assertEqual(table["table_html"].count("<tr>"), 2)
        self.assertEqual(table["table_html"].count("<td>"), 8)
        self.assertEqual(table["table_html"].count("<img "), 4)
        self.assertEqual(ovis.table_text(table["table_html"]), result["raw_text"])

    def test_embedded_table_invalid_reference_or_bbox_rejected_before_extra_calls(self):
        references = ["https://invalid.example/external.jpg", "../images/bbox_1_1_20_20.jpg",
                      "images/bbox_1_1_1000_20.jpg", "images/bbox_20_1_10_20.jpg"]
        for reference in references:
            with self.subTest(reference=reference):
                html = ('<table><tr><td><img src="images/bbox_1_1_20_20.jpg" /></td>'
                        f'<td><img src="{reference}" /></td></tr></table>')
                context = Context(self.root, [response(json.dumps([block("table", html)]))])
                result = ovis.process_page(self.image, context)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(len(context.calls), 1)
                self.assertEqual(result["ordered_blocks"][0]["raw_table_html"], html)

    def test_embedded_table_failed_supplement_is_never_page_pass(self):
        html = '<table><tr><td><img src="images/bbox_1_1_200_200.jpg" /></td></tr></table>'
        for extra in [response("partial", finish_reason="length"), response("", status="FAIL_BUDGET")]:
            with self.subTest(extra=extra):
                context = Context(self.root, [response(json.dumps([block("table", html)])), extra])
                result = ovis.process_page(self.image, context)
                self.assertNotEqual(result["status"], "PASS")
                table = result["ordered_blocks"][0]
                self.assertEqual(table["raw_table_html"], html)
                self.assertNotEqual(table["status"], "PASS")
                self.assertNotEqual(table["embedded_images"][0]["status"], "PASS")
                self.assertEqual(len(result["requests"]), 2)

    def test_embedded_table_missing_written_asset_fails_before_extra_call(self):
        html = '<table><tr><td><img src="images/bbox_1_1_200_200.jpg" /></td></tr></table>'
        context = Context(self.root, [response(json.dumps([block("table", html)]))])
        with patch.object(Image.Image, "save", return_value=None):
            result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(context.calls), 1)

    def test_native_markdown_reuses_image_export_and_supplement_without_changing_raw(self):
        raw = ('# 图示\n\n<img src="images/bbox_10_20_300_400.jpg" />\n\n'
               '<table><tr><td><img src="images/bbox_500_200_800_600.jpg" /></td></tr></table>')
        context = Context(self.root, [response(raw), response("图上文字"), response("表内文字")], ovis_mode="markdown")
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["raw_output"], raw)
        content = result["ordered_blocks"][0]
        self.assertIsNone(content["bbox"])
        self.assertEqual(content["raw_content"], raw)
        self.assertEqual(len(content["embedded_images"]), 2)
        self.assertEqual(len(context.calls), 3)
        self.assertIn("图上文字", result["raw_text"])
        self.assertIn("表内文字", result["raw_text"])
        self.assertIn('<img src="images/bbox_10_20_300_400.jpg" />', result["markdown"])

    def test_native_markdown_invalid_image_and_failed_supplement_do_not_pass(self):
        raw = '<img src="images/bbox_10_20_300_400.jpg" />'
        context = Context(self.root, [response(raw), response("partial", finish_reason="length")], ovis_mode="markdown")
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["requests"]), 2)
        self.assertEqual(result["ordered_blocks"][0]["embedded_images"][0]["status"], "FAIL")
        context = Context(self.root, [response('<img src="https://invalid.example/a.jpg" />')], ovis_mode="markdown")
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(context.calls), 1)

    def test_r0_table_embedded_image_uses_crop_coordinates_and_keeps_single_ir_block(self):
        html = '<table><tr><td><img src="images/bbox_100_200_500_800.jpg" /></td></tr></table>'
        context = Context(self.root, [response(html), response("crop字")], region_task="table")
        result = ovis.process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["raw_table_html"], html)
        self.assertEqual(len(result["ordered_blocks"]), 1)
        self.assertEqual(result["ordered_blocks"][0]["embedded_images"][0]["bbox"], [10, 40, 50, 160])
        self.assertIn("crop字", result["raw_text"])

    def test_chart_requires_string_values_and_complete_schema(self):
        value = {"title": "Chart", "source": "None", "x_title": "Year", "y_title": ["A", "B"],
                 "values": {"series": {"2026": "3.5"}}}
        self.assertEqual(ovis.parse_chart(json.dumps(value)), value)
        value["values"]["series"]["2026"] = 3.5
        with self.assertRaisesRegex(ovis.OvisOutputError, "CHART_SCALAR_NOT_STRING"):
            ovis.parse_chart(json.dumps(value))

    def pages(self, table_counts=(1, 1)):
        pages = []
        for page_id, count in enumerate(table_counts, 1):
            blocks = [{"block_type": "text", "content": f"Paragraph {page_id}", "text": f"Paragraph {page_id}"}]
            for index in range(count):
                html = f"<table><tr><td>{page_id}-{index}</td></tr></table>"
                blocks.append({"block_type": "table", "content": html, "table_html": html, "text": f"{page_id}-{index}"})
            pages.append({"page_id": f"p{page_id}", "status": "PASS", "finish_reason": "stop",
                          "ordered_blocks": blocks, "markdown": "\n\n".join(b["content"] for b in blocks)})
        return pages

    def test_single_table_crosspage_binding_preserves_originals_and_body(self):
        pages = self.pages()
        before = copy.deepcopy(pages)
        merged = "<table><tr><td>1-0</td></tr><tr><td>2-0</td></tr></table>"
        context = Context(self.root, [response(json.dumps([{"source_pages": [1, 2], "html": merged}]))])
        result = ovis.process_crosspage_pair([self.image, self.image], pages, context)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["writeback_applied"])
        self.assertEqual(pages, before)
        self.assertEqual(result["rewritten_markdown"], ["Paragraph 1\n\n" + merged, "Paragraph 2"])
        self.assertEqual(result["merged_fragment_ancestry"], [["p1", 0], ["p2", 0]])
        self.assertIn('<INPUT_PAGE index="1">', context.calls[0][1])
        self.assertEqual(len(context.calls[0][0]), 2)

    def test_multi_table_merge_does_not_overwrite_side_table(self):
        pages = self.pages((2, 1))
        context = Context(self.root, [response(json.dumps([{"source_pages": [1, 2],
                                                         "html": "<table><tr><td>merged</td></tr></table>"}]))])
        result = ovis.process_crosspage_pair([self.image, self.image], pages, context)
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertFalse(result["writeback_applied"])
        self.assertEqual(result["original_pages"], pages)

    def test_crosspage_prior_truncation_prevents_inference(self):
        pages = self.pages()
        pages[0]["finish_reason"] = "length"
        context = Context(self.root, [])
        result = ovis.process_crosspage_pair([self.image, self.image], pages, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(context.calls, [])


if __name__ == "__main__":
    unittest.main()
