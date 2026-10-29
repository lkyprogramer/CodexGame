"""OvisOCR3 task adapter. All inference goes through the shared budgeted context.

Input coordinates always refer to the exact admitted image, never an annotation.
No model import or network request occurs when this module is imported.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


CATEGORIES = frozenset(
    "abstract algorithm aside_text chart content display_formula doc_title "
    "figure_title footer footer_image footnote formula_number header header_image "
    "image inline_formula number paragraph_title reference_content seal table text "
    "vertical_text vision_footnote".split()
)
VISUAL_CATEGORIES = frozenset({"image", "header_image", "footer_image", "chart"})
PROMPT_HASHES = {
    "document_structured.txt": "1b6139ec72888e087c8af75f2e2dfb78b425e15ae1c1529940b96137613d1db1",
    "plain_ocr.txt": "e037cf0013a757e19eae6d4d701f3b90848449fbebe44d1f8fa7d8ca4a5af9a7",
    "document_markdown.txt": "dbf31d5899a86047ce0cd4d0d12cdc5616df1bea5d9a600b823098442c32997c",
    "figure_captioning.txt": "944bb410dbe17aa1cbe65f6acb14585053473e8a988b120f98c95d97a7e844de",
    "formula_recognition.txt": "b07b4c70a7585ddc2b4db33a1fff19bcacb1faf57b6db8ae2ebdb1035eeeb5b4",
    "chart_parsing.txt": "bb933216bdad5a81a3eca59e770bdb7d4b936ab85f97a2af6de5dd0890371f38",
    "crosspage_table.txt": "b5f38187df651d83bb46b6756d1b9386d04120cb6b299cfd1e93f9e0dec564d1",
}


class OvisOutputError(ValueError):
    """A response cannot satisfy the declared task output contract."""


def _sha(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _load_prompt(context: Any, filename: str) -> tuple[str, str]:
    data = (Path(context.model_dir) / "prompts" / filename).read_bytes()
    digest = _sha(data)
    if digest != PROMPT_HASHES[filename]:
        raise OvisOutputError(f"PROMPT_HASH_MISMATCH:{filename}:{digest}")
    return data.decode("utf-8"), digest


def parse_structured(raw: str) -> list[dict[str, Any]]:
    """Validate the original response, without extracting JSON from wrappers."""
    try:
        blocks = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OvisOutputError(f"INVALID_JSON:{exc.msg}") from exc
    if not isinstance(blocks, list):
        raise OvisOutputError("STRUCTURED_OUTPUT_NOT_ARRAY")
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or set(block) != {"bbox", "category", "content"}:
            raise OvisOutputError(f"INVALID_BLOCK_FIELDS:{index}")
        bbox = block["bbox"]
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(type(v) is not int or not 0 <= v < 1000 for v in bbox)
            or bbox[0] >= bbox[2]
            or bbox[1] >= bbox[3]
        ):
            raise OvisOutputError(f"INVALID_BBOX:{index}")
        if (not isinstance(block["category"], str) or block["category"] not in CATEGORIES
                or not isinstance(block["content"], str)):
            raise OvisOutputError(f"INVALID_BLOCK_TYPE:{index}")
    return blocks


def _normalized_image(attrs: list[tuple[str, str | None]]) -> tuple[str, list[int]]:
    if len(attrs) != 1 or attrs[0][0] != "src" or not isinstance(attrs[0][1], str):
        raise OvisOutputError("INVALID_IMAGE_ATTRIBUTES")
    reference = attrs[0][1]
    match = re.fullmatch(r"images/bbox_(\d+)_(\d+)_(\d+)_(\d+)\.jpg", reference)
    if match is None:
        raise OvisOutputError("INVALID_NORMALIZED_IMAGE_REFERENCE")
    bbox = list(map(int, match.groups()))
    if any(not 0 <= value < 1000 for value in bbox) or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise OvisOutputError("INVALID_IMAGE_BBOX")
    return reference, bbox


class _ImageTags(HTMLParser):
    """Locate only normalized image references. Parsing never loads HTML assets."""

    def __init__(self, content: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = content
        self.line_offsets = [0]
        for match in re.finditer("\n", content):
            self.line_offsets.append(match.end())
        self.image_slots: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            reference, bbox = _normalized_image(attrs)
            line, column = self.getpos()
            start = self.line_offsets[line - 1] + column
            end = start + len(self.get_starttag_text())
            self.image_slots.append({"image_reference": reference, "bbox_normalized": bbox,
                                     "source_span": {"start": start, "end": end,
                                                     "unit": "original_content_unicode_codepoints"}})

    def validate_image_count(self) -> None:
        if len(self.image_slots) != len(re.findall(r"<img\b", self.source, re.I)):
            raise OvisOutputError("MALFORMED_IMAGE_TAG")


class _TableText(_ImageTags):
    def __init__(self, content: str, embedded_texts: list[str] | None = None) -> None:
        super().__init__(content)
        self.embedded_texts = embedded_texts
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.cell: list[str] | None = None
        self.stack: list[str] = []
        self.table_count = 0
        self.invalid = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.table_count += 1
            if self.stack:
                self.invalid = True
        elif tag == "tr" and (not self.stack or self.stack[-1] != "table"):
            self.invalid = True
        elif tag in {"td", "th"} and (not self.stack or self.stack[-1] != "tr"):
            self.invalid = True
        if tag in {"table", "tr", "td", "th"}:
            self.stack.append(tag)
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append("\n")
        if tag == "img":
            if self.cell is None:
                self.invalid = True
            super().handle_starttag(tag, attrs)
            slot = self.image_slots[-1]
            slot["cell_ordinal"] = {"row": len(self.rows), "column": len(self.row)}
            if self.embedded_texts is not None and self.cell is not None:
                if len(self.image_slots) > len(self.embedded_texts):
                    raise OvisOutputError("EMBEDDED_IMAGE_TEXT_COUNT_MISMATCH")
                text = self.embedded_texts[len(self.image_slots) - 1]
                if text:
                    self.cell.append("\n" + text + "\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"table", "tr", "td", "th"}:
            if not self.stack or self.stack[-1] != tag:
                self.invalid = True
            else:
                self.stack.pop()
            if tag in {"td", "th"}:
                if self.cell is None:
                    self.invalid = True
                else:
                    self.row.append("".join(self.cell))
                    self.cell = None
            elif tag == "tr":
                self.rows.append(self.row)

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)


def _parse_table(content: str, embedded_texts: list[str] | None = None) -> _TableText:
    parser = _TableText(content, embedded_texts)
    parser.feed(content)
    parser.close()
    parser.validate_image_count()
    if parser.invalid or parser.stack or parser.table_count != 1:
        raise OvisOutputError("INVALID_OR_UNSUPPORTED_TABLE_HTML")
    if not re.fullmatch(r"\s*<table\b.*</table>\s*", content, flags=re.I | re.S):
        raise OvisOutputError("TABLE_CONTENT_OUTSIDE_TABLE")
    if embedded_texts is not None and len(embedded_texts) != len(parser.image_slots):
        raise OvisOutputError("EMBEDDED_IMAGE_TEXT_COUNT_MISMATCH")
    return parser


def table_text(content: str, embedded_texts: list[str] | None = None) -> str:
    """Visible cell text; optional raw OCR text is inserted at each predicted image slot."""
    parser = _parse_table(content, embedded_texts)
    return "\n".join("\t".join(row) for row in parser.rows)


def parse_chart(raw: str) -> dict[str, Any]:
    try:
        chart = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OvisOutputError(f"INVALID_CHART_JSON:{exc.msg}") from exc
    if not isinstance(chart, dict) or set(chart) != {"title", "source", "x_title", "y_title", "values"}:
        raise OvisOutputError("INVALID_CHART_FIELDS")
    if any(not isinstance(chart[key], str) for key in ("title", "source", "x_title")):
        raise OvisOutputError("INVALID_CHART_METADATA")
    y_title = chart["y_title"]
    if not isinstance(y_title, str) and not (
        isinstance(y_title, list) and len(y_title) == 2 and all(isinstance(v, str) for v in y_title)
    ):
        raise OvisOutputError("INVALID_CHART_Y_TITLE")
    values = chart["values"]
    if not isinstance(values, dict) or not values:
        raise OvisOutputError("EMPTY_CHART_VALUES")
    def strings_only(value: Any) -> bool:
        if isinstance(value, dict):
            return all(strings_only(v) for v in value.values())
        if isinstance(value, list):
            return all(strings_only(v) for v in value)
        return isinstance(value, str)
    if not strings_only(values):
        raise OvisOutputError("CHART_SCALAR_NOT_STRING")
    return chart


def _pixel_bbox(bbox: list[int], width: int, height: int) -> list[int]:
    return [
        math.floor(bbox[0] * width / 1000), math.floor(bbox[1] * height / 1000),
        math.ceil(bbox[2] * width / 1000), math.ceil(bbox[3] * height / 1000),
    ]


def _formula_markdown(content: str, category: str) -> str:
    stripped = content.strip()
    if ((stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) >= 4)
            or (stripped.startswith("$") and stripped.endswith("$") and len(stripped) >= 2)):
        return content
    if category == "display_formula":
        if stripped.startswith(r"\[") and stripped.endswith(r"\]"):
            content = stripped[2:-2].strip()
        return "$$\n" + content + "\n$$"
    if stripped.startswith(r"\(") and stripped.endswith(r"\)"):
        content = stripped[2:-2].strip()
    return "$" + content + "$"


def _check_response(response: dict[str, Any]) -> None:
    if response.get("status") != "PASS":
        raise OvisOutputError(str(response.get("error") or response.get("status") or "CALL_FAILED"))
    if response.get("finish_reason") == "length":
        raise OvisOutputError("TRUNCATED_OUTPUT")
    if not isinstance(response.get("content"), str):
        raise OvisOutputError("NON_TEXT_RESPONSE")


def _recognize_image(image: Any, context: Any, slot: dict, name: str) -> tuple[dict, dict]:
    """Export a predicted region and send its lossless pixels through the common budget gate."""
    bbox = _pixel_bbox(slot["bbox_normalized"], image.width, image.height)
    reference = slot["image_reference"]
    destination = Path(context.output_dir) / reference
    destination.parent.mkdir(parents=True, exist_ok=True)
    inference_crop = Path(context.output_dir) / "crops" / f"{name}.png"
    inference_crop.parent.mkdir(parents=True, exist_ok=True)
    with image.crop(tuple(bbox)) as crop:
        if not crop.width or not crop.height:
            raise OvisOutputError("EMPTY_IMAGE_CROP")
        crop.save(destination, format="JPEG", quality=95, subsampling=0)
        crop.save(inference_crop, format="PNG")
        pixel_hash = _sha(crop.tobytes())
    resource_hash = _sha(destination.read_bytes())
    inference_hash = _sha(inference_crop.read_bytes())
    prompt, digest = _load_prompt(context, "plain_ocr.txt")
    response = context.call([inference_crop], prompt, 4096, f"ovis:image_text:{name}")
    record = {
        **slot, "bbox": bbox, "bbox_units": "input_pixels", "page_id": context.page_id,
        "crop_file_sha256": resource_hash,
        "inference_crop_reference": str(inference_crop.relative_to(context.output_dir)),
        "inference_crop_file_sha256": inference_hash,
        "inference_crop_rgb_sha256": pixel_hash,
        "crop_transform": {"origin_xy": bbox[:2], "scale_xy": [1, 1]},
        "supplement_prompt_sha256": digest, "visible_image_text": response.get("content", ""),
        "request_ids": [response.get("request_id")], "status": response.get("status", "FAIL"),
        "finish_reason": response.get("finish_reason"), "error": response.get("error"),
    }
    if record["finish_reason"] == "length":
        record.update(status="FAIL", error="TRUNCATED_OUTPUT")
    return record, response


def _enhance_embedded_images(content: str, image: Any, context: Any, result: dict,
                             block: dict, name: str, *, table: bool) -> tuple[str, str]:
    """Append escaped raw image OCR without changing source tags, cells, or raw model output."""
    if table:
        block.update(raw_table_html=content, raw_table_html_sha256=_sha(content))
        parser = _parse_table(content)
    else:
        parser = _ImageTags(content)
        parser.feed(content)
        parser.close()
        parser.validate_image_count()
    records = block["embedded_images"] = []
    for index, slot in enumerate(parser.image_slots):
        record, response = _recognize_image(image, context, slot, f"{name}-{index:04d}")
        records.append(record)
        result["requests"].extend(record["request_ids"])
        block["request_ids"].extend(record["request_ids"])
        try:
            _check_response(response)
        except OvisOutputError:
            block["status"] = record["status"] if record["status"] != "PASS" else "FAIL"
            raise
    product = content
    visible = content
    for index in range(len(records) - 1, -1, -1):
        record = records[index]
        text = record["visible_image_text"]
        start, end = record["source_span"]["start"], record["source_span"]["end"]
        addition = (f'<br/><span data-ocr-supplement="{name}-{index:04d}">'
                    + escape(text).replace("\n", "<br/>") + "</span><br/>") if text else ""
        product = product[:end] + addition + product[end:]
        visible = visible[:start] + ("\n" + text + "\n" if text else "") + visible[end:]
    block["supplement_policy"] = "predicted-image-ocr-v2-raw-preserved"
    if table:
        visible = table_text(content, [record["visible_image_text"] for record in records])
        block.update(raw_table_html=content, table_html=product,
                     raw_table_html_sha256=_sha(content), product_table_html_sha256=_sha(product))
        # Product markup and faithful raw supplementation must serialize the same visible cells.
        if table_text(product) != visible:
            raise OvisOutputError("EMBEDDED_IMAGE_TEXT_SERIALIZATION_MISMATCH")
    return product, visible


def process_page(image_path: Path, context: Any) -> dict[str, Any]:
    """Run one independent task on the currently admitted page or correct crop."""
    from PIL import Image

    options = context.options
    region_task = options.get("region_task")
    mode = options.get("ovis_mode", "structured")
    tasks = {
        "text": ("plain_ocr.txt", 4096), "seal": ("plain_ocr.txt", 2048),
        "name": ("plain_ocr.txt", 2048), "handwriting": ("plain_ocr.txt", 4096),
        "image_text": ("plain_ocr.txt", 4096),
        "formula": ("formula_recognition.txt", 2048),
        "display_formula": ("formula_recognition.txt", 2048),
        "inline_formula": ("formula_recognition.txt", 1024),
        "table": ("document_markdown.txt", 8192), "chart": ("chart_parsing.txt", 8192),
    }
    modes = {
        "structured": ("document_structured.txt", 8192),
        "plain": ("plain_ocr.txt", 8192), "markdown": ("document_markdown.txt", 8192),
        "figure": ("figure_captioning.txt", 8192),
    }
    result: dict[str, Any] = {
        "status": "FAIL", "errors": [], "requests": [], "ordered_blocks": [],
        "text": "", "raw_text": "", "markdown": "", "mode": mode, "region_task": region_task,
        "adapter_version": "ovis-adapter-v2", "visual_supplement": region_task == "table" or mode in {"structured", "markdown"},
        "text_serialization": "visible-text-v2-embedded-images",
        "raw_product_policy": "raw_output/raw_content/raw_table_html unchanged; product content/table_html appends escaped raw predicted-image OCR",
        "text_serialization_formula_policy": "exclude formula blocks from page text/raw_text; retain block raw_content, formula_latex and markdown",
    }
    try:
        if region_task is not None:
            if region_task not in tasks:
                raise OvisOutputError(f"UNSUPPORTED_REGION_TASK:{region_task}")
            filename, limit = tasks[region_task]
        else:
            if mode not in modes:
                raise OvisOutputError(f"UNSUPPORTED_MODE:{mode}")
            filename, limit = modes[mode]
        prompt, digest = _load_prompt(context, filename)
        result["prompt_sha256"] = digest
        context.emit("layout_start", source="ovis_native_structure", task=region_task or mode)
        response = context.call([image_path], prompt, limit, f"ovis:{region_task or mode}")
        result["requests"].append(response.get("request_id"))
        result["raw_output"] = response.get("content", "")
        result["finish_reason"] = response.get("finish_reason")
        _check_response(response)
        raw = response["content"]
        if region_task is not None or mode in {"plain", "markdown"}:
            result.update(status="PASS", text=raw, raw_text=raw, markdown=raw)
            region_block = None
            if region_task is not None:
                with Image.open(image_path) as opened:
                    width, height = opened.size
                category = {
                    "formula": "display_formula", "display_formula": "display_formula",
                    "inline_formula": "inline_formula", "table": "table", "chart": "chart", "seal": "seal",
                }.get(region_task, "text")
                region_block = {
                    "block_id": f"{context.page_id}:b0000", "block_type": category,
                    "bbox": [0, 0, width, height], "bbox_units": "input_pixels",
                    "raw_content": raw, "content": raw, "raw_text": raw, "text": raw,
                    "status": "PASS", "request_ids": [response.get("request_id")],
                    "style_marks": "UNAVAILABLE",
                }
                result["image_size"] = [width, height]
                result["ordered_blocks"] = [region_block]
            if region_task == "table":
                with Image.open(image_path) as opened, opened.convert("RGB") as image:
                    product, visible = _enhance_embedded_images(raw, image, context, result,
                                                               region_block, "region-table", table=True)
                region_block.update(content=product, text=visible, raw_text=visible)
                result.update(text=visible, raw_text=visible, table_html=product, raw_table_html=raw)
            elif region_task == "chart":
                result["chart_data"] = parse_chart(raw)
                region_block["chart_data"] = result["chart_data"]
            elif region_task in {"formula", "display_formula", "inline_formula"}:
                result["formula_latex"] = raw
                region_block["formula_latex"] = raw
                region_block["content"] = _formula_markdown(raw, region_block["block_type"])
                result["text"] = result["raw_text"] = ""
            if region_block is not None:
                result["ordered_blocks"] = [region_block]
                result["markdown"] = region_block["content"]
            elif mode == "markdown":
                markdown_block = {
                    "block_id": f"{context.page_id}:native-markdown", "block_type": "content",
                    "bbox": None, "bbox_source": "UNAVAILABLE_NATIVE_MARKDOWN",
                    "raw_content": raw, "content": raw, "raw_text": raw, "text": raw,
                    "status": "PASS", "request_ids": [response.get("request_id")],
                    "style_marks": "UNAVAILABLE",
                }
                result["ordered_blocks"] = [markdown_block]
                with Image.open(image_path) as opened, opened.convert("RGB") as image:
                    product, visible = _enhance_embedded_images(raw, image, context, result,
                                                               markdown_block, "native-markdown", table=False)
                markdown_block.update(content=product, text=visible, raw_text=visible)
                result.update(markdown=product, text=visible, raw_text=visible)
            return result
        native_blocks = parse_structured(raw)
        with Image.open(image_path) as opened:
            image = opened.convert("RGB")
        width, height = image.size
        result["image_size"] = [width, height]
        for index, native in enumerate(native_blocks):
            category, content, bbox = native["category"], native["content"], native["bbox"]
            block: dict[str, Any] = {
                "block_id": f"{context.page_id}:b{index:04d}", "block_type": category,
                "bbox": _pixel_bbox(bbox, width, height), "bbox_normalized": bbox,
                "raw_content": content, "content": content, "raw_text": content,
                "text": content, "status": "PASS", "request_ids": [response.get("request_id")],
                "style_marks": "UNAVAILABLE",
            }
            result["ordered_blocks"].append(block)
            if category == "table":
                product, visible = _enhance_embedded_images(content, image, context, result,
                                                           block, f"table-{index:04d}", table=True)
                block.update(content=product, text=visible, raw_text=visible)
            elif category in {"display_formula", "inline_formula"}:
                block["formula_latex"] = content
                block["content"] = _formula_markdown(content, category)
            elif category in VISUAL_CATEGORIES:
                if mode == "figure":
                    # Captions are descriptions, not faithful OCR text.
                    block["caption_output"] = content
                    block["derived_content"] = True
                    block["derived_output_fields"] = ["caption_output", "caption", "mermaid"]
                    block["text"] = block["raw_text"] = ""
                    caption_match = re.fullmatch(
                        r"\s*<caption>(.*?)</caption>\s*(?:<mermaid>(.*?)</mermaid>)?\s*", content, re.S,
                    )
                    if caption_match is None:
                        raise OvisOutputError(f"INVALID_FIGURE_CAPTION:{index}")
                    if len(caption_match.group(1).split()) > 100:
                        raise OvisOutputError(f"FIGURE_CAPTION_WORD_LIMIT:{index}")
                    block["caption"] = caption_match.group(1)
                    block["mermaid"] = caption_match.group(2)
                    block["caption_factuality"] = "UNSCORED"
                    block["mermaid_syntax"] = "UNAVAILABLE"
                    continue
                expected = f"images/bbox_{'_'.join(map(str, bbox))}.jpg"
                tag = re.fullmatch(r'\s*<img\s+src=[\"\']([^\"\']+)[\"\']\s*/?>\s*', content)
                if tag is None or tag.group(1) != expected:
                    raise OvisOutputError(f"INVALID_IMAGE_REFERENCE:{index}")
                record, extra = _recognize_image(image, context, {
                    "image_reference": expected, "bbox_normalized": bbox,
                }, f"visual-{index:04d}")
                block.update({key: value for key, value in record.items()
                              if key not in {"request_ids", "status", "error"}})
                result["requests"].extend(record["request_ids"])
                block["request_ids"].extend(record["request_ids"])
                block["raw_text"] = block["text"] = block["visible_image_text"]
                block["content"] = f'<img src="{expected}" />\n{block["text"]}'
                try:
                    _check_response(extra)
                except OvisOutputError:
                    block["status"] = extra.get("status", "FAIL")
                    if block["status"] == "PASS":
                        block["status"] = "FAIL"
                    raise
        ordinary_blocks = [block for block in result["ordered_blocks"]
                           if block["block_type"] not in {"display_formula", "inline_formula"}]
        result["text"] = "\n".join(block["text"] for block in ordinary_blocks)
        result["raw_text"] = "\n".join(block["raw_text"] for block in ordinary_blocks)
        result["markdown"] = "\n\n".join(block["content"] for block in result["ordered_blocks"])
        result["status"] = "PASS"
    except (OvisOutputError, OSError, UnicodeError) as exc:
        result["status"] = "FAIL_BUDGET" if any(
            response.get("status") == "FAIL_BUDGET" for response in context.requests
        ) else "FAIL"
        result["errors"].append(str(exc))
        # Keep all successfully parsed blocks, but never call a partial page complete.
        ordinary_blocks = [block for block in result["ordered_blocks"]
                           if block["block_type"] not in {"display_formula", "inline_formula"}]
        result["text"] = "\n".join(block["text"] for block in ordinary_blocks)
        result["raw_text"] = "\n".join(block["raw_text"] for block in ordinary_blocks)
        result["markdown"] = "\n\n".join(block["content"] for block in result["ordered_blocks"])
    return result


def process_crosspage_pair(
    image_paths: list[Path], pages: list[dict[str, Any]], context: Any,
) -> dict[str, Any]:
    """O1 pair task with conservative single-table writeback and original retention.

    This is not a recursive document renderer. The caller must retain this result
    and use an explicit rendering stage before any subsequent 3+ page merge.
    """
    result: dict[str, Any] = {
        "status": "FAIL", "errors": [], "requests": [], "writeback_applied": False,
        "original_pages": copy.deepcopy(pages), "adapter_version": "ovis-crosspage-pair-v2",
        "recursive_3plus_support": "UNSUPPORTED_REQUIRES_VERSIONED_MARKDOWN_RENDERER",
    }
    try:
        if len(image_paths) != 2 or len(pages) != 2:
            raise OvisOutputError("CROSSPAGE_REQUIRES_TWO_PAGES")
        if any(page.get("status") != "PASS" or page.get("finish_reason") == "length" for page in pages):
            raise OvisOutputError("INVALID_STAGE1_PREDECESSOR")
        prompt, digest = _load_prompt(context, "crosspage_table.txt")
        prior = "\n\n".join(
            f'<INPUT_PAGE index="{index + 1}">\n{page["markdown"]}\n</INPUT_PAGE>'
            for index, page in enumerate(pages)
        )
        response = context.call(image_paths, prompt.removesuffix("\n") + "\n\nInput Markdown:\n\n" + prior,
                                8192, "ovis:crosspage_pair")
        result["requests"].append(response.get("request_id"))
        result["prompt_sha256"] = digest
        result["raw_output"] = response.get("content", "")
        _check_response(response)
        prediction = json.loads(response["content"])
        if not isinstance(prediction, list) or len(prediction) != 1:
            raise OvisOutputError("MULTIPLE_MERGES_UNSUPPORTED")
        merge = prediction[0]
        if not isinstance(merge, dict) or set(merge) != {"source_pages", "html"}:
            raise OvisOutputError("INVALID_CROSSPAGE_FIELDS")
        if merge["source_pages"] == [] and merge["html"] == "No cross-page table exists between these pages.":
            result.update(status="PASS", crosspage_exists=False, rewritten_markdown=[p["markdown"] for p in pages])
            return result
        if merge["source_pages"] != [1, 2] or any(type(v) is not int for v in merge["source_pages"]):
            raise OvisOutputError("INVALID_SOURCE_PAGES")
        operand_has_images = any(
            block.get("embedded_images") or re.search(r"<img\b", block.get("table_html", ""), re.I)
            for page in pages for block in page["ordered_blocks"] if block["block_type"] == "table"
        )
        if not isinstance(merge["html"], str):
            raise OvisOutputError("INVALID_CROSSPAGE_HTML_TYPE")
        if operand_has_images or re.search(r"<img\b", merge["html"], re.I):
            result.update(status="UNSUPPORTED", crosspage_exists=True,
                          unsupported_feature="crosspage_image_source_mapping")
            result["errors"].append("CROSSPAGE_IMAGE_SOURCE_MAPPING_UNSUPPORTED_KEEP_ORIGINALS")
            return result
        table_text(merge["html"])
        table_indices = [
            [index for index, block in enumerate(page["ordered_blocks"]) if block["block_type"] == "table"]
            for page in pages
        ]
        if any(len(indices) != 1 for indices in table_indices):
            result.update(status="UNSUPPORTED", crosspage_exists=True)
            result["errors"].append("MULTI_TABLE_OR_MISSING_TABLE_BINDING_WRITEBACK_DISABLED")
            return result
        rewritten = copy.deepcopy(pages)
        operands = []
        for page_index, indices in enumerate(table_indices):
            block = pages[page_index]["ordered_blocks"][indices[0]]
            original_html = block["table_html"]
            operands.append({
                "fragment_id": [pages[page_index]["page_id"], 0],
                "original_html_sha256": _sha(original_html),
                "original_visible_text_sha256": _sha(table_text(original_html)),
                "original_block_index": indices[0],
            })
        first = rewritten[0]["ordered_blocks"][table_indices[0][0]]
        first.update(content=merge["html"], table_html=merge["html"], text=table_text(merge["html"]))
        del rewritten[1]["ordered_blocks"][table_indices[1][0]]
        # Only the selected table blocks are modified. Preserve every other original block.
        for page in rewritten:
            page["markdown"] = "\n\n".join(block["content"] for block in page["ordered_blocks"])
        result.update(
            status="PASS", crosspage_exists=True, writeback_applied=True,
            rewritten_markdown=[page["markdown"] for page in rewritten],
            operand_fragments=operands, merged_fragment_ancestry=[item["fragment_id"] for item in operands],
        )
    except (OvisOutputError, json.JSONDecodeError, OSError, UnicodeError, KeyError, TypeError) as exc:
        result["errors"].append(str(exc))
        if any(response.get("status") == "FAIL_BUDGET" for response in context.requests):
            result["status"] = "FAIL_BUDGET"
    return result
