"""MiniCPM page adapter against the locked SDK's CPU layout contract.

The SDK is imported lazily in CPU workers; importing this module never loads a
model. Requests go through PageContext, which owns global dispatch and deadlines.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import threading
from typing import Any, Callable

from PIL import Image


SDK_REVISION = "62d5e649c32be2271f2c8c66ec8307f3d7373903"
ADAPTER_VERSION = "mini-adapter-v2"
IMAGE_LABELS = {"image", "header_image", "footer_image"}
_ADAPTERS: dict[str, "MiniAdapter"] = {}


def _is_mixed_math_document(content: str) -> bool:
    """Recognize complete math spans without parsing or rewriting their LaTeX."""
    closing = {r"\(": r"\)", r"\[": r"\]", "$": "$", "$$": "$$"}
    start = None
    expected = None
    spans = []
    group_depth = 0
    index = 0
    while index < len(content):
        char = content[index]
        token = char
        if char == "\\":
            token = content[index:index + 2]
            if token not in {r"\(", r"\)", r"\[", r"\]"}:
                # Includes escaped braces, dollars and paired backslashes.
                index += 2
                continue
        elif char == "{":
            group_depth += 1
        elif char == "}":
            group_depth = max(0, group_depth - 1)
        elif char == "$" and expected != "$" and content.startswith("$$", index):
            token = "$$"
        if group_depth == 0:
            if start is None:
                if token in closing:
                    start, expected = index, closing[token]
            elif token == expected:
                spans.append((start, index + len(token)))
                start, expected = None, None
        index += len(token)
    if not spans:
        return False
    outside = []
    end = 0
    for begin, finish in spans:
        outside.append(content[end:begin])
        end = finish
    outside.append(content[end:])
    return len(spans) > 1 or bool("".join(outside).strip())


class _VisibleHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.cell_depth = 0
        self.stack: list[str] = []
        self.invalid = False
        self.table_count = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() == "table":
            self.table_count += 1
            if self.stack:
                self.invalid = True
        if tag.lower() in {"table", "tr", "td", "th"}:
            self.stack.append(tag.lower())
        if tag.lower() == "img":
            self.invalid = True
        if tag.lower() in {"td", "th"}:
            self.cell_depth += 1
        elif tag.lower() == "br" and self.cell_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.cell_depth:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"table", "tr", "td", "th"}:
            if not self.stack or self.stack[-1] != tag.lower():
                self.invalid = True
            else:
                self.stack.pop()
        if tag.lower() in {"td", "th"}:
            self.parts.append("\t")
            self.cell_depth -= 1
        elif tag.lower() == "tr":
            if self.parts and self.parts[-1] == "\t":
                self.parts.pop()
            self.parts.append("\n")


def _visible_text(content: str, label: str) -> str:
    if label not in {"table", "chart"} or "<table" not in content.lower():
        return content
    parser = _VisibleHTML()
    parser.feed(content)
    parser.close()
    if parser.parts and parser.parts[-1] == "\n":
        parser.parts.pop()
    return "".join(parser.parts)


def _raw_visible_text(content: str, label: str) -> str:
    """Decode table syntax only; never run SDK cleanup on the raw channel."""
    if label in {"table", "chart"} and any(
        token in content for token in ("<fcel>", "<ecel>", "<nl>")
    ):
        from minicpmvocr.postprocess.otsl import convert_otsl_to_html

        content = convert_otsl_to_html(content)
    return _visible_text(content, label)


def _validate_table_html(content: str) -> None:
    parser = _VisibleHTML()
    parser.feed(content)
    parser.close()
    if parser.invalid or parser.stack or parser.table_count != 1 or not re.fullmatch(
        r"\s*<table\b.*</table>\s*", content, flags=re.I | re.S
    ):
        raise ValueError("INVALID_OR_UNSUPPORTED_TABLE_HTML")


class MiniAdapter:
    def __init__(
        self,
        layout_model_dir: str | Path,
        *,
        detector_factory: Callable[[dict], Any] | None = None,
        prompt_map: dict | None = None,
        postprocessor: Callable[[str, str, str], str] | None = None,
    ) -> None:
        self.layout_model_dir = str(layout_model_dir)
        self._detector_factory = detector_factory
        self._prompt_map = deepcopy(prompt_map) if prompt_map is not None else None
        self._postprocessor = postprocessor
        self._detector = None
        self._initialization_lock = threading.Lock()
        self._layout_lock = threading.Lock()

    def _initialize(self, context: Any, *, need_layout: bool) -> None:
        with self._initialization_lock:
            if self._prompt_map is None:
                from minicpmvocr.prompts import DEFAULT_PROMPT_MAP

                self._prompt_map = deepcopy(DEFAULT_PROMPT_MAP)
                self._prompt_map["markdown_assembly"]["ignore_labels"] = []
            if self._postprocessor is None:
                from minicpmvocr.postprocess.markdown import postprocess_content

                def sdk_postprocess(raw: str, output_format: str, label: str) -> str:
                    content = postprocess_content(raw, output_format, label=label)
                    if label in {"table", "chart"} and any(
                        token in content for token in ("<fcel>", "<ecel>", "<nl>")
                    ):
                        from minicpmvocr.postprocess.otsl import convert_otsl_to_html

                        content = convert_otsl_to_html(content)
                    return content

                self._postprocessor = sdk_postprocess
            if need_layout and self._detector is None:
                if not self.layout_model_dir:
                    raise ValueError("layout_model_dir is required for Mini full-page parsing")
                factory = self._detector_factory
                if factory is None:
                    from minicpmvocr.layouts import create_layout_detector

                    factory = create_layout_detector
                context.emit("layout_initialization_start", model_dir=self.layout_model_dir)
                config = {
                    "provider": "ppdoclayout3_paddlex",
                    "model_name": "PP-DocLayoutV3",
                    "model_dir": self.layout_model_dir,
                    "device": "cpu",
                    "threshold": 0.3,
                    "nms": True,
                    "skip_vlm_labels": [],
                    "use_ocr_for_image_block": True,
                    "use_chart_recognition": True,
                    "use_seal_recognition": True,
                }
                detector = factory(config)
                detector.validate_config(config)
                detector.start()
                self._detector = detector
                context.emit("layout_initialization_end", details=detector.describe())

    def process_page(self, image_path: Path, context: Any) -> dict:
        output_dir = Path(context.output_dir)
        crop_dir = output_dir / "crops"
        crop_dir.mkdir(parents=True, exist_ok=True)
        options = getattr(context, "options", {}) or {}
        region_task = options.get("region_task")
        try:
            self._initialize(context, need_layout=not bool(region_task))
            with Image.open(image_path) as opened:
                image = opened.convert("RGB")
            with image:
                width, height = image.size
                context.emit("layout_start", provider="GT_CROP_BYPASS" if region_task else "ppdoclayout3_paddlex")
                if region_task:
                    labels = {
                        "text": "text", "handwriting": "text", "image_text": "image",
                        "formula": "display_formula", "display_formula": "display_formula",
                        "inline_formula": "inline_formula", "table": "table",
                        "seal": "seal", "name": "text", "chart": "chart",
                    }
                    if region_task not in labels:
                        raise ValueError(f"Unknown Mini region_task: {region_task}")
                    blocks = [{"label": labels[region_task], "bbox": [0, 0, width, height],
                               "class_id": None, "score": None, "polygon": [],
                               "image": image.copy(), "skip_vlm": False}]
                    detections = []
                else:
                    # Paddle predictors are not shared concurrently between pages.
                    with self._layout_lock:
                        batches = self._detector.detect([image])
                        if len(batches) != 1:
                            raise ValueError("CPU layout returned an invalid page batch")
                        detections = batches[0]
                        blocks = self._detector.crop(image, detections)
                context.emit("layout_end", detection_count=len(detections), crop_count=len(blocks))
                (output_dir / "layout.json").write_text(
                    json.dumps({"provider": "GT_CROP_BYPASS" if region_task else "ppdoclayout3_paddlex",
                                "sdk_revision": SDK_REVISION, "image_size": [width, height],
                                "detections": detections}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                recipes = []
                # The pinned SDK folds cross-column regions into a leader's
                # crop. None is that explicit contract, not a missing image.
                folded_by_leader: dict[int, list[list[int]]] = {}
                leaders: set[int] = set()
                last_leader = None
                for index, block in enumerate(blocks):
                    if block.get("image") is not None:
                        leaders.add(index)
                        last_leader = index
                    else:
                        group_id = block.get("group_id")
                        leader = group_id if group_id in leaders else last_leader
                        if leader is None:
                            raise ValueError(f"Folded layout region has no leader at block {index}")
                        folded_by_leader.setdefault(leader, []).append(list(block["bbox"]))
                for index, block in enumerate(blocks):
                    if context.remaining_seconds() <= 0:
                        raise TimeoutError("Page deadline expired during CPU crop preparation")
                    bbox = block["bbox"]
                    if len(bbox) != 4 or not (0 <= bbox[0] < bbox[2] <= width and 0 <= bbox[1] < bbox[3] <= height):
                        raise ValueError(f"Invalid layout crop bbox at block {index}: {bbox}")
                    if block.get("skip_vlm"):
                        raise ValueError(f"Unexpected skipped VLM label: {block['label']}")
                    pixels = block.get("image")
                    if pixels is None:
                        continue
                    block["regions"] = [list(bbox)] + folded_by_leader.get(index, [])
                    crop = pixels if isinstance(pixels, Image.Image) else Image.fromarray(pixels)
                    crop_path = crop_dir / f"block-{index:04d}.png"
                    with crop:
                        crop.convert("RGB").save(crop_path)
                    label = str(block["label"])
                    default = self._prompt_map["default"]
                    recipe = {**default, **self._prompt_map.get("element_prompts", {}).get(label, {})}
                    # Common task ceilings override short native label ceilings.
                    if label in {"table", "chart"}:
                        limit = 8192
                    elif label == "display_formula":
                        limit = 2048
                    elif label == "inline_formula":
                        limit = 1024
                    elif label == "seal" or region_task == "name":
                        limit = 2048
                    else:
                        limit = 4096
                    recipes.append((index, block, crop_path, recipe, limit))
            def recognize(entry: tuple) -> dict:
                index, block, crop_path, recipe, limit = entry
                label = str(block["label"])
                item = {
                    "block_id": f"{context.page_id}:block-{index:04d}", "order": index,
                    "block_type": label, "label": label, "bbox": list(block["bbox"]),
                    "bbox_units": "input_pixels", "polygon": block.get("polygon", []),
                    "regions": block["regions"],
                    "crop_geometry": "sdk_polygon_mask_or_merged_regions",
                    "layout_class_id": block.get("class_id"), "layout_score": block.get("score"),
                    "image_reference": str(crop_path.relative_to(output_dir)),
                    "raw_text": "", "text": "", "raw_content": "", "content": "",
                    "table_html": None, "formula_latex": None, "visible_image_text": None,
                    "style_marks": "UNAVAILABLE", "status": "FAIL", "errors": [],
                    "request_ids": [], "prompt": recipe["prompt"], "task_limit": limit,
                }
                try:
                    response = context.call([crop_path], recipe["prompt"], limit, f"mini:{index}:{label}")
                    raw = response.get("content", "")
                    if not isinstance(raw, str):
                        raise ValueError("Mini response content is not text")
                    item.update(raw_content=raw, raw_text=_raw_visible_text(raw, label), finish_reason=response.get("finish_reason"),
                                usage=response.get("usage"), request_ids=[response["request_id"]])
                    item["status"] = response["status"]
                    if response.get("error"):
                        item["errors"].append(str(response["error"]))
                    if response.get("finish_reason") == "length":
                        item["status"] = "FAIL"
                        item["errors"].append("TRUNCATED_FINISH_REASON_LENGTH")
                    is_formula = label in {"display_formula", "inline_formula"}
                    mixed_math = is_formula and _is_mixed_math_document(raw)
                    # The SDK strips matching ends even across separate math
                    # spans; preserve these documents before that lossy cleanup.
                    content = raw.strip() if mixed_math else self._postprocessor(
                        raw, recipe.get("output_format", "text"), label
                    )
                    item["content"] = content
                    item["text"] = _visible_text(content, label)
                    if label in {"table", "chart"}:
                        item["table_html"] = content
                        _validate_table_html(content)
                    if is_formula:
                        item["formula_latex"] = content
                        item["formula_representation"] = "mixed_math_document" if mixed_math else "single_latex"
                    if label in IMAGE_LABELS:
                        item["visible_image_text"] = content
                except Exception as exc:
                    item["status"] = "FAIL"
                    item["errors"].append(f"{type(exc).__name__}: {exc}")
                return item

            with ThreadPoolExecutor(max_workers=4, thread_name_prefix="mini-region") as pool:
                results = list(pool.map(recognize, recipes))
            errors = [f"{b['block_id']}: {e}" for b in results for e in b["errors"]]
            status = "PASS" if all(b["status"] == "PASS" for b in results) else (
                "FAIL_BUDGET" if any(b["status"] == "FAIL_BUDGET" for b in results) else "FAIL"
            )
            markdown = []
            for block in results:
                content, label = block["content"], block["label"]
                if label in IMAGE_LABELS:
                    markdown.append(f"![{escape(label)}]({block['image_reference']})\n\n{content}")
                elif block.get("formula_representation") == "mixed_math_document":
                    markdown.append(content)
                elif label == "display_formula":
                    markdown.append(f"$$\n{content}\n$$")
                elif label == "inline_formula":
                    markdown.append(f"${content}$")
                elif label == "doc_title":
                    markdown.append(f"# {content}")
                elif label == "paragraph_title":
                    markdown.append(f"## {content}")
                else:
                    markdown.append(content)
            return {"adapter": "mini", "adapter_version": ADAPTER_VERSION,
                    "sdk_revision": SDK_REVISION, "status": status,
                    "page_id": context.page_id, "ordered_blocks": results,
                    "text": "\n".join(b["text"] for b in results if b["label"] not in {"display_formula", "inline_formula"}),
                    "raw_text": "\n".join(b["raw_text"] for b in results if b["label"] not in {"display_formula", "inline_formula"}),
                    "text_serialization": "visible-text-v1",
                    "markdown": "\n\n".join(markdown), "errors": errors,
                    "requests": [r for b in results for r in b["request_ids"]],
                    "image_size": [width, height], "layout_empty": not bool(results),
                    "processing_policy": "SDK postprocess_content except mixed math documents preserved verbatim; conditional OTSL conversion; raw preserved; no cross-block dedup",
                    "cross_page_links": "UNSUPPORTED"}
        except Exception as exc:
            return {"adapter": "mini", "adapter_version": ADAPTER_VERSION,
                    "page_id": context.page_id, "status": "FAIL",
                    "ordered_blocks": [], "text": "", "raw_text": "", "markdown": "",
                    "errors": [f"{type(exc).__name__}: {exc}"], "requests": []}


def process_page(image_path: Path, context: Any) -> dict:
    model_dir = str(getattr(context, "layout_model_dir", "") or
                    (getattr(context, "options", {}) or {}).get("layout_model_dir", "") or
                    os.environ.get("MINICPM_LAYOUT_MODEL_DIR", ""))
    if model_dir not in _ADAPTERS:
        _ADAPTERS[model_dir] = MiniAdapter(model_dir)
    return _ADAPTERS[model_dir].process_page(Path(image_path), context)
