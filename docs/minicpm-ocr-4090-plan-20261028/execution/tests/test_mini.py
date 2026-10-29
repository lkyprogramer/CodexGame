import json
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import Mock, patch
import types
import unittest

from PIL import Image

from ocrbench.mini import MiniAdapter, _visible_text


PROMPTS = {
    "default": {"prompt": "Text Recognition:", "output_format": "text"},
    "element_prompts": {
        "table": {"prompt": "Table Recognition:", "output_format": "html"},
        "display_formula": {"prompt": "Formula Recognition:", "output_format": "latex"},
        "inline_formula": {"prompt": "Inline Formula Recognition:", "output_format": "latex"},
        "seal": {"prompt": "Seal Recognition:", "output_format": "text"},
        "chart": {"prompt": "Chart to Table:", "output_format": "html"},
    },
    "markdown_assembly": {"ignore_labels": ["header", "footer"]},
}


# Raw formula strings captured from four syntax failures and one prose-formatting change.
MIXED_FORMULA_FIXTURES = [('PAPER-026-p014',
  'inline_formula',
  '\\( x_{1}+x_{2}=\\frac{8m}{5} \\) ,  \\( x_{1}x_{2}=\\frac{4m^{2}-16}{5} \\)'),
 ('R0-STRUCT-chem-q2-cd',
  'display_formula',
  'C. 氢气燃烧热为 285.5 kJ/mol，则分解水热方程式为 '
  '\\(2\\mathrm{H_{2}O(g)}=2\\mathrm{H_{2}(g)}+\\mathrm{O_{2}(g)}\\quad \\Delta \\mathrm{H}=+571\\ '
  '\\mathrm{kJ/mol}\\)\n'
  'D. 已知 \\(2\\mathrm{C(s)}+\\mathrm{O_{2}(g)}=2\\mathrm{CO(g)}\\ \\Delta '
  '\\mathrm{H}=-221\\mathrm{kJ\\cdot mol^{-1}}\\)，则石墨的燃烧热为 \\(-110.5\\ \\mathrm{kJ\\cdot '
  'mol^{-1}}\\)'),
 ('R0-STRUCT-math-q2',
  'display_formula',
  '2.(5分)若直线 \\(l\\) 与直线 \\(2x-2\\sqrt{3}y+5=0\\) 垂直，则 \\(l\\) 的倾斜角为\n'
  'A. \\(\\frac{\\pi}{3}\\)         B. \\(\\frac{2\\pi}{3}\\)         C. '
  '\\(\\frac{\\pi}{6}\\)         D. \\(\\frac{5\\pi}{6}\\)'),
 ('R0-STRUCT-physics-q1',
  'display_formula',
  '碳-14 同位素依赖进口的难题。其生产过程的核反应方程为： \\(^{14}_{7}\\mathrm{N} + _{0}^{1}\\mathrm{n} \\rightarrow '
  '^{14}_{6}\\mathrm{C} + \\mathrm{X}\\)，其中的 \\(\\mathrm{X}\\) 为（）\n'
  'A. \\(^{1}_{1}\\mathrm{H}\\)\u3000\u3000\u3000B. \\(^{0}_{-1}\\mathrm{e}\\)\u3000\u3000\u3000C. '
  '\\(^{1}_{0}\\mathrm{n}\\)\u3000\u3000\u3000D. \\(^{4}_{2}\\mathrm{He}\\)'),
 ('R0-STRUCT-physics-q3-graph-options',
  'display_formula',
  '\\[\n'
  '\\begin{array}{l} v / m \\cdot s^{-1} \\\\ 4 \\\\ 0 \\\\ -4 \\\\ 8 \\quad 52 \\quad 60 \\quad '
  '148 \\quad 156 \\quad 200 \\quad 208 \\\\ t / s \\end{array}\n'
  '\\]\n'
  '\n'
  'A. 0, 0  \n'
  'B. 0, 2m/s  \n'
  'C. 416m, 0  \n'
  'D. 416m, 2m/s')]


def sdk_outer_pair_postprocess(raw, fmt, label):
    """Reproduce the pinned SDK's blind outer-pair stripping for latex output."""
    content = raw.strip()
    if fmt == "latex":
        for left, right in (("$$", "$$"), ("$", "$"), (r"\(", r"\)"), (r"\[", r"\]")):
            if content.startswith(left) and content.endswith(right):
                content = content[len(left):len(content) - len(right)].strip()
    return content


class Context:
    def __init__(self, output_dir, *, options=None, length=False):
        self.output_dir = output_dir
        self.page_id = "page-001"
        self.options = options or {}
        self.calls = []
        self.events = []
        self.length = length
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0

    def emit(self, name, **fields):
        self.events.append((name, fields))

    def remaining_seconds(self):
        return 10

    def call(self, image_paths, prompt, task_limit, task_name):
        with self.lock:
            self.active += 1
            self.peak = max(self.active, self.peak)
            index = len(self.calls)
            self.calls.append((image_paths, prompt, task_limit, task_name))
        time.sleep(0.005)
        with self.lock:
            self.active -= 1
        content = "<table><tr><td>A</td><td>B</td></tr></table>" if prompt in {"Table Recognition:", "Chart to Table:"} else task_name
        return {"content": content, "finish_reason": "length" if self.length else "stop",
                "usage": {"prompt_tokens": 20}, "request_id": f"req-{index}",
                "status": "PASS", "error": None}


class Detector:
    labels = ["header", "text", "table", "display_formula", "image", "footer", "seal", "chart"]

    def __init__(self, config):
        self.config = config
        self.starts = 0

    def validate_config(self, config):
        assert config["device"] == "cpu"
        assert config["skip_vlm_labels"] == []

    def start(self):
        self.starts += 1

    def describe(self):
        return {"device": "cpu"}

    def detect(self, images):
        return [[{"label": label, "bbox": [0, i * 10, 100, i * 10 + 10],
                  "class_id": i, "score": 0.9} for i, label in enumerate(self.labels)]]

    def crop(self, image, detections):
        return [{**d, "image": image.crop(d["bbox"]), "polygon": [], "skip_vlm": False}
                for d in detections]


class MiniTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root / "page.png"
        Image.new("RGB", (100, 100), "white").save(self.image)

    def tearDown(self):
        self.temp.cleanup()

    def adapter(self, detector=Detector, postprocessor=None):
        return MiniAdapter("/fake/layout", detector_factory=detector, prompt_map=PROMPTS,
                           postprocessor=postprocessor or (lambda raw, fmt, label: raw))

    def formula_result(self, raw, label):
        context = Context(self.root / "formula", options={"region_task": label})
        context.call = lambda *args: {"content": raw, "finish_reason": "stop", "usage": None,
                                     "request_id": "formula", "status": "PASS", "error": None}
        process = Mock(side_effect=sdk_outer_pair_postprocess)
        result = self.adapter(postprocessor=process).process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        return result, process

    def test_observed_mixed_math_documents_preserve_raw_boundaries(self):
        self.assertNotEqual(
            sdk_outer_pair_postprocess(MIXED_FORMULA_FIXTURES[0][2], "latex", "inline_formula"),
            MIXED_FORMULA_FIXTURES[0][2],
        )
        for name, label, raw in MIXED_FORMULA_FIXTURES:
            with self.subTest(fixture=name):
                result, process = self.formula_result(raw, label)
                block = result["ordered_blocks"][0]
                self.assertEqual(block["raw_content"], raw)
                self.assertEqual(block["raw_text"], raw)
                self.assertEqual(block["content"], raw.strip())
                self.assertEqual(block["text"], raw.strip())
                self.assertEqual(block["formula_latex"], raw.strip())
                self.assertEqual(result["markdown"], raw.strip())
                self.assertEqual(block["formula_representation"], "mixed_math_document")
                self.assertEqual(result["adapter_version"], "mini-adapter-v2")
                process.assert_not_called()

    def test_mixed_math_delimiter_styles_and_labels_remain_verbatim(self):
        for raw in (r"$x$ $y$", r"$$x$$, $$y$$", r"\[x\] \[y\]",
                    r"中文标签：\(x\)", r"\(x\)，中文标签", r"price \$5 and $x$",
                    r"$x+\$1$ and $y$", r"\{label\} $x$", r"\\ $x$"):
            for label in ("inline_formula", "display_formula"):
                with self.subTest(raw=raw, label=label):
                    result, process = self.formula_result("  " + raw + "  ", label)
                    self.assertEqual(result["markdown"], raw)
                    self.assertEqual(result["ordered_blocks"][0]["formula_representation"], "mixed_math_document")
                    process.assert_not_called()

    def test_single_latex_and_escaped_dollars_keep_sdk_processing_and_wrapper(self):
        for raw in (r"x^{2}+1", r"\( x^{2}+1 \)", r"\[ x^{2}+1 \]",
                    "$x^{2}+1$", "$$x^{2}+1$$", r"x+\$1", r"\$5 and \$6",
                    r"$x+\$1$", r"\text{if \{ $x$ \} then},y",
                    r"\text{if \\ $x$},y"):
            for label in ("inline_formula", "display_formula"):
                with self.subTest(raw=raw, label=label):
                    result, process = self.formula_result(raw, label)
                    expected = sdk_outer_pair_postprocess(raw, "latex", label)
                    block = result["ordered_blocks"][0]
                    self.assertEqual(block["raw_content"], raw)
                    self.assertEqual(block["content"], expected)
                    self.assertEqual(block["formula_latex"], expected)
                    self.assertEqual(block["formula_representation"], "single_latex")
                    self.assertEqual(result["markdown"], f"${expected}$" if label == "inline_formula" else f"$$\n{expected}\n$$")
                    process.assert_called_once_with(raw, "latex", label)

    def test_adjacent_inline_spans_preserve_each_boundary(self):
        # Real SDK display processing collapses this to "xy". Expected output
        # is the original pair of complete inline spans, with no display wrapper.
        for label in ("inline_formula", "display_formula"):
            with self.subTest(label=label):
                result, process = self.formula_result("$x$$y$", label)
                block = result["ordered_blocks"][0]
                self.assertEqual(block["formula_representation"], "mixed_math_document")
                self.assertEqual(block["content"], "$x$$y$")
                self.assertEqual(result["markdown"], "$x$$y$")
                process.assert_not_called()

    def test_tex_argument_math_is_part_of_single_expression(self):
        raw = r"\text{if $x>0$}, x^2"
        result, process = self.formula_result(raw, "display_formula")
        block = result["ordered_blocks"][0]
        self.assertEqual(block["formula_representation"], "single_latex")
        # Independently fixed expected value: verified against the real SDK.
        self.assertEqual(block["content"], r"\text{if $x>0$}, x^2")
        self.assertEqual(result["markdown"], "$$\n" + raw + "\n$$")
        process.assert_called_once_with(raw, "latex", "display_formula")

    def test_complete_export_preserves_auxiliary_labels_and_assets(self):
        context = Context(self.root / "out")
        result = self.adapter().process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["ordered_blocks"]), 8)
        self.assertIn("mini:0:header", result["text"])
        self.assertIn("mini:5:footer", result["text"])
        self.assertIn("mini:4:image", result["markdown"])
        self.assertIn("![image](crops/block-0004.png)", result["markdown"])
        self.assertEqual(result["ordered_blocks"][2]["text"], "A\tB")
        self.assertEqual(result["ordered_blocks"][2]["table_html"], "<table><tr><td>A</td><td>B</td></tr></table>")
        self.assertNotIn("<table>", result["raw_text"])
        self.assertIn("A\tB", result["raw_text"])
        self.assertNotIn("mini:3:display_formula", result["raw_text"])
        self.assertEqual(result["ordered_blocks"][3]["formula_latex"], "mini:3:display_formula")
        self.assertEqual(result["text_serialization"], "visible-text-v1")
        for block in result["ordered_blocks"]:
            self.assertTrue((context.output_dir / block["image_reference"]).is_file())
        self.assertLessEqual(context.peak, 4)
        self.assertGreater(context.peak, 1)
        self.assertEqual({call[2] for call in context.calls}, {1024, 2048, 4096, 8192} - {1024})
        layout = json.loads((context.output_dir / "layout.json").read_text())
        self.assertEqual(layout["image_size"], [100, 100])

    def test_length_is_failure_and_raw_content_retained(self):
        context = Context(self.root / "out", length=True)
        result = self.adapter().process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("mini:0:header", result["raw_text"])
        self.assertIn("TRUNCATED_FINISH_REASON_LENGTH", result["errors"][0])

    def test_layout_failure_is_observable_without_region_requests(self):
        class Broken(Detector):
            def detect(self, images):
                raise RuntimeError("Paddle prediction failed")

        context = Context(self.root / "out")
        result = self.adapter(Broken).process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("Paddle prediction failed", result["errors"][0])
        self.assertEqual(context.calls, [])

    def test_gt_region_path_does_not_initialize_or_call_layout(self):
        def must_not_start(config):
            raise AssertionError("layout must be bypassed for correct region track")

        context = Context(self.root / "out", options={"region_task": "formula"})
        result = self.adapter(must_not_start).process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(context.calls[0][1:3], ("Formula Recognition:", 2048))
        self.assertEqual(len(result["ordered_blocks"]), 1)
        self.assertEqual(result["ordered_blocks"][0]["bbox"], [0, 0, 100, 100])

    def test_cached_layout_is_reused_and_raw_processed_are_separate(self):
        made = []
        def factory(config):
            detector = Detector(config)
            made.append(detector)
            return detector

        adapter = self.adapter(factory, lambda raw, fmt, label: raw if label in {"table", "chart"} else raw + "-processed")
        result = adapter.process_page(self.image, Context(self.root / "out1"))
        adapter.process_page(self.image, Context(self.root / "out2"))
        self.assertEqual(len(made), 1)
        self.assertEqual(made[0].starts, 1)
        first = result["ordered_blocks"][0]
        self.assertEqual(first["content"], first["raw_content"] + "-processed")
        self.assertNotIn("-processed", result["raw_text"])

    def test_invalid_predicted_bbox_fails_before_sending_image(self):
        class BadBox(Detector):
            def detect(self, images):
                return [[{"label": "text", "bbox": [-1, 0, 10, 10], "score": 1, "class_id": 0}]]

        context = Context(self.root / "out")
        result = self.adapter(BadBox).process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("Invalid layout crop bbox", result["errors"][0])
        self.assertEqual(context.calls, [])

    def test_raw_otsl_is_decoded_without_processed_cleanup(self):
        context = Context(self.root / "out", options={"region_task": "table"})
        native_call = context.call
        raw_otsl = "<fcel> raw  cell <ecel><nl>"
        def call(*args):
            response = native_call(*args)
            response["content"] = raw_otsl
            return response
        context.call = call
        converter = types.ModuleType("minicpmvocr.postprocess.otsl")
        converter.convert_otsl_to_html = lambda raw: "<table><tr><td> raw  cell </td><td></td></tr></table>"
        adapter = self.adapter(postprocessor=lambda raw, fmt, label: "<table><tr><td>clean</td></tr></table>")
        with patch.dict("sys.modules", {"minicpmvocr.postprocess.otsl": converter}):
            result = adapter.process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["raw_text"], " raw  cell \t")
        self.assertEqual(result["text"], "clean")
        self.assertEqual(result["ordered_blocks"][0]["raw_content"], raw_otsl)

    def test_cell_whitespace_and_empty_columns_are_preserved(self):
        html = "<table>\n<tr><td> A </td><td></td></tr><tr><td>B<br>C</td><td> </td></tr></table>"
        self.assertEqual(_visible_text(html, "table"), " A \t\nB\nC\t ")

    def test_invalid_table_output_and_budget_failure_are_not_pass(self):
        context = Context(self.root / "out", options={"region_task": "table"})
        native_call = context.call
        def call(*args):
            response = native_call(*args)
            response["content"] = "<table><tr><td>broken"
            return response
        context.call = call
        result = self.adapter().process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("INVALID_OR_UNSUPPORTED_TABLE_HTML", result["errors"][0])
        context = Context(self.root / "budget", options={"region_task": "text"})
        context.call = lambda *args: {"content": "", "finish_reason": None, "usage": None,
                                     "request_id": "budget", "status": "FAIL_BUDGET", "error": "overflow"}
        result = self.adapter().process_page(self.image, context)
        self.assertEqual(result["status"], "FAIL_BUDGET")

    def test_folded_sdk_crop_has_one_call_and_original_region_mapping(self):
        class Folded(Detector):
            def detect(self, images):
                return [[{"label": "text", "bbox": bbox, "score": .9, "class_id": 0}
                         for bbox in ([0, 0, 50, 10], [50, 0, 100, 10])]]
            def crop(self, image, detections):
                return [{**detections[0], "image": image.crop((0, 0, 100, 10))},
                        {**detections[1], "image": None, "group_id": 0}]
        context = Context(self.root / "out")
        result = self.adapter(Folded).process_page(self.image, context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(context.calls), 1)
        self.assertEqual(result["ordered_blocks"][0]["regions"], [[0, 0, 50, 10], [50, 0, 100, 10]])
        self.assertEqual(result["ordered_blocks"][0]["bbox"], [0, 0, 50, 10])


if __name__ == "__main__":
    unittest.main()
