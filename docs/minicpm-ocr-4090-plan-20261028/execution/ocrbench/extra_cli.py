"""O1 PRED cross-page tasks from immutable, pixel-verified Stage1 artifacts.

Stage2 timing is reported separately. This command neither recreates Stage1 nor
claims recursive reconstruction without a versioned Markdown renderer.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

from .client import VLLMClient, atomic_json
from .core import EventJournal, PageContext, RegionSlots, load_manifest
from .ovis import process_crosspage_pair, table_text


def _sha(value: str | bytes) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", value):
        raise ValueError("pair_id must be path-safe ASCII, at most 160 characters")
    return value


def load_stage1(run_dir: Path, manifest_path: Path | None = None) -> tuple[dict, dict]:
    """Read identity/order metadata; page pixels are opened only after pair admission."""
    cases = load_manifest(manifest_path or run_dir / "input-manifest.json")
    by_id = {case["page_id"]: case for case in cases}
    predictions = _read(run_dir / "predictions.json")
    records = predictions["pages"] if isinstance(predictions, dict) else predictions
    if not isinstance(records, list):
        raise ValueError("Stage1 predictions must contain a pages array")
    predicted = {}
    for record in records:
        page_id = record["page_id"]
        if page_id in predicted or page_id not in by_id:
            raise ValueError("Stage1 prediction identity is duplicated or absent from the input manifest")
        if record["document_id"] != by_id[page_id]["document_id"]:
            raise ValueError("Stage1 document identity differs from the input manifest")
        predicted[page_id] = record
    if set(predicted) != set(by_id):
        raise ValueError("Stage1 predictions and input manifest must have the same page denominator")
    return by_id, predicted


def select_pairs(cases: dict[str, dict], manifest: Path | None = None) -> list[dict]:
    """Select original adjacent pages, never lexicographic filenames or cross-document pairs."""
    if manifest is not None:
        loaded = _read(manifest)
        pairs = loaded["pairs"] if isinstance(loaded, dict) else loaded
        if not isinstance(pairs, list):
            raise ValueError("pairs manifest must contain a pairs array")
    else:
        documents: dict[str, list[dict]] = {}
        for case in cases.values():
            if type(case.get("page_index")) is int:
                documents.setdefault(case["document_id"], []).append(case)
        pairs = []
        for document_id in sorted(documents):
            pages = sorted(documents[document_id], key=lambda item: item["page_index"])
            if len({page["page_index"] for page in pages}) != len(pages):
                raise ValueError("ambiguous duplicate original page_index within a document")
            for left, right in zip(pages, pages[1:]):
                if right["page_index"] == left["page_index"] + 1:
                    pair_id = f"pair-{len(pairs) + 1:05d}"
                    pairs.append({"pair_id": pair_id, "page_ids": [left["page_id"], right["page_id"]]})
    selected, seen = [], set()
    for index, supplied in enumerate(pairs):
        pair_id = _safe_id(supplied.get("pair_id", f"pair-{index + 1:05d}"))
        if pair_id in seen:
            raise ValueError("duplicate pair_id")
        seen.add(pair_id)
        if supplied.get("track", "PRED") != "PRED":
            raise ValueError("this command supports PRED only; ORACLE must have a separate diagnostic runner")
        page_ids = supplied["page_ids"]
        if (not isinstance(page_ids, list) or len(page_ids) < 2
                or any(not isinstance(v, str) or v not in cases for v in page_ids)
                or len(set(page_ids)) != len(page_ids)):
            raise ValueError("pair page_ids must identify at least two distinct admitted pages")
        entries = [cases[page_id] for page_id in page_ids]
        document_id = entries[0]["document_id"]
        if any(entry["document_id"] != document_id for entry in entries):
            raise ValueError("cross-document page pairs are forbidden")
        indices = [entry.get("page_index") for entry in entries]
        if any(type(value) is not int or value < 0 for value in indices):
            raise ValueError("cross-page tasks require original zero-based page_index values")
        if any(right != left + 1 for left, right in zip(indices, indices[1:])):
            raise ValueError("page_ids must follow adjacent original page order")
        selected.append({"pair_id": pair_id, "document_id": document_id, "page_ids": page_ids,
                         "page_indices": indices, "track": "PRED",
                         "task": supplied.get("task", "X01" if len(page_ids) == 2 else "X02")})
    return selected


def _page_assets(run_dir: Path, case: dict, prediction: dict) -> tuple[Path, dict, dict]:
    from PIL import Image

    directory = run_dir / "pages" / case["page_id"]
    stored_path, image_path = directory / "result.json", directory / "input.png"
    stored = _read(stored_path)
    if any(prediction.get(key) != value for key, value in stored.items()):
        raise ValueError("STAGE1_PREDICTION_RESULT_MISMATCH")
    if stored.get("page_id") != case["page_id"] or stored.get("document_id") != case["document_id"]:
        raise ValueError("STAGE1_PAGE_IDENTITY_MISMATCH")
    if stored.get("status") != "PASS" or stored.get("finish_reason") != "stop":
        raise ValueError("INVALID_STAGE1_PREDECESSOR")
    if (stored.get("mode") != "structured" or stored.get("region_task") is not None
            or not str(stored.get("adapter_version", "")).startswith("ovis-adapter-")
            or stored.get("timing_scope") not in {"D0", "P0"}
            or stored.get("unit_kind", "page") != "page"):
        raise ValueError("OVIS_STRUCTURED_FULL_PAGE_STAGE1_REQUIRED")
    if any(record.get("status") != "PASS" or record.get("finish_reason") != "stop"
           for record in stored.get("request_records", [])):
        raise ValueError("INVALID_STAGE1_MODEL_CALL")
    # Full source identity is checked as well as the page pixels that Stage2 actually consumes.
    source_hash = _file_sha(Path(case["path"]))
    if source_hash != stored.get("source_sha256"):
        raise ValueError("STAGE1_ORIGINAL_SOURCE_HASH_MISMATCH")
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
    pixel_hash = _sha(rgb.tobytes())
    if (pixel_hash != stored.get("input_pixel_hash")
            or [rgb.width, rgb.height] != [stored.get("width"), stored.get("height")]):
        raise ValueError("STAGE1_INPUT_PIXEL_HASH_MISMATCH")
    blocks = stored.get("ordered_blocks")
    if (not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks)
            or not isinstance(stored.get("markdown"), str)):
        raise ValueError("STAGE1_STRUCTURED_BLOCKS_REQUIRED")
    if stored["markdown"] != "\n\n".join(block["content"] for block in blocks):
        raise ValueError("STAGE1_MARKDOWN_BLOCK_MAPPING_MISMATCH")
    audit = {"page_id": case["page_id"], "document_id": case["document_id"],
             "original_page_index": case["page_index"], "source_path": case["path"],
             "source_sha256": source_hash, "stage1_result_sha256": _file_sha(stored_path),
             "input_image": str(image_path), "input_image_sha256": _file_sha(image_path),
             "input_pixel_hash": pixel_hash, "width": rgb.width, "height": rgb.height}
    return image_path, stored, audit


def _fragments(pages: list[dict]) -> list[dict]:
    fragments = []
    for page in pages:
        table_index = 0
        for index, block in enumerate(page["ordered_blocks"]):
            if block["block_type"] == "table":
                html = block["table_html"]
                fragments.append({
                    "fragment_id": [page["page_id"], table_index], "original_block_index": index,
                    "original_span": {"unit": "markdown_unicode_codepoints",
                                      "start": sum(len(b["content"]) + 2 for b in page["ordered_blocks"][:index]),
                                      "end": sum(len(b["content"]) + 2 for b in page["ordered_blocks"][:index]) + len(block["content"])},
                    "original_html_sha256": _sha(html),
                    "original_visible_text_sha256": _sha(table_text(html)),
                    "original_fragment_ancestry": [[page["page_id"], table_index]],
                })
                table_index += 1
    return fragments


def _audit_writeback(pages: list[dict], result: dict, fragments: list[dict]) -> dict:
    non_tables = [{"page_id": page["page_id"], "blocks": [
        {"block_index": index, "content_sha256": _sha(block["content"])}
        for index, block in enumerate(page["ordered_blocks"]) if block["block_type"] != "table"
    ]} for page in pages]
    if result.get("original_pages") != pages:
        raise ValueError("ORIGINAL_PAGE_ARTIFACT_MUTATED")
    if not result.get("writeback_applied"):
        rewritten = result.get("rewritten_markdown")
        if rewritten is not None and rewritten != [page["markdown"] for page in pages]:
            raise ValueError("UNEXPECTED_WRITEBACK_WITHOUT_BINDING")
        return {"status": "NOT_APPLIED", "original_fragments": fragments,
                "unselected_fragments": fragments, "non_table_content": non_tables,
                "originals_preserved": True}
    if len(pages) != 2 or len(fragments) != 2 or [f["fragment_id"] for f in fragments] != [
        [pages[0]["page_id"], 0], [pages[1]["page_id"], 0]
    ]:
        raise ValueError("UNSUPPORTED_TABLE_BINDING_WRITEBACK")
    expected_operands = [fragment["fragment_id"] for fragment in fragments]
    if result.get("merged_fragment_ancestry") != expected_operands:
        raise ValueError("MERGED_FRAGMENT_ANCESTRY_MISMATCH")
    prediction = json.loads(result["raw_output"])[0]
    expected = []
    for page_index, page in enumerate(pages):
        parts = []
        for block in page["ordered_blocks"]:
            if block["block_type"] != "table":
                parts.append(block["content"])
            elif page_index == 0:
                parts.append(prediction["html"])
        expected.append("\n\n".join(parts))
    if result.get("rewritten_markdown") != expected:
        raise ValueError("UNSELECTED_CONTENT_CHANGED_DURING_WRITEBACK")
    return {"status": "PASS", "original_fragments": fragments,
            "selected_operand_fragment_ids": expected_operands, "unselected_fragments": [],
            "non_table_content": non_tables, "non_table_content_preserved": True,
            "originals_preserved": True}


def _export_pages(stage1_run: Path, folder: Path, pages: list[dict], rewritten: list[str]) -> list[dict]:
    exports = []
    for page, markdown in zip(pages, rewritten, strict=True):
        source_folder = stage1_run / "pages" / page["page_id"]
        destination = folder / "rewritten" / page["page_id"]
        destination.mkdir(parents=True)
        resources = []
        seen = set()
        for block in page["ordered_blocks"]:
            for image in [block, *block.get("embedded_images", [])]:
                reference = image.get("image_reference")
                if reference is None:
                    continue
                relative = Path(reference)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("INVALID_STAGE1_RESOURCE_REFERENCE")
                source = source_folder / relative
                # Restrict source reads to this Stage1 page, including symbolic links.
                if not source.resolve().is_relative_to(source_folder.resolve()):
                    raise ValueError("STAGE1_RESOURCE_OUTSIDE_PAGE")
                digest = _file_sha(source)
                if image.get("crop_file_sha256") is not None and digest != image["crop_file_sha256"]:
                    raise ValueError("STAGE1_RESOURCE_HASH_MISMATCH")
                if reference in seen:
                    continue
                seen.add(reference)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                resources.append({"relative_path": str(relative), "sha256": _file_sha(target),
                                  "source_path": str(source)})
        path = destination / "document.md"
        temporary = destination / "document.md.tmp"
        temporary.write_text(markdown, encoding="utf-8")
        temporary.replace(path)
        exports.append({"page_id": page["page_id"], "markdown_reference": str(path.relative_to(folder)),
                        "markdown_sha256": _file_sha(path), "resources": resources})
    return exports


def run_pairs(stage1_run: Path, output: Path, config: dict, *, pairs_manifest: Path | None = None,
              manifest_path: Path | None = None, client: Any = None) -> dict:
    cases, predictions = load_stage1(stage1_run, manifest_path)
    pairs = select_pairs(cases, pairs_manifest)
    profile = config.get("profile", "O1-16K-PRED")
    if profile not in {"O1-16K-PRED", "O1-LOWPIX-16K-PRED"}:
        raise ValueError("unsupported O1 PRED profile")
    policy_evidence = None
    policy_content = None
    if config.get("service_policy_evidence") is not None:
        policy_path = Path(config["service_policy_evidence"]).resolve()
        policy_bytes = policy_path.read_bytes()
        policy_content = json.loads(policy_bytes)
        if not isinstance(policy_content, dict):
            raise ValueError("service policy evidence must be a JSON object")
        policy_evidence = {"source_path": str(policy_path), "sha256": _sha(policy_bytes),
                           "bytes": len(policy_bytes),
                           "snapshot_path": str((output / "service-policy-evidence.json").resolve()),
                           "verification": "POLICY_JSON_SNAPSHOT_ONLY_NOT_LIVE_RUNTIME_PROOF"}
    config = dict(config, profile=profile, service_policy_evidence=policy_evidence)
    output.mkdir(parents=True, exist_ok=False)
    (output / "locks").mkdir()
    (output / "pairs").mkdir()
    journal = EventJournal(output / "events.jsonl")
    slots = RegionSlots(output / "locks", 4)
    client = client or VLLMClient(config["base_url"], config["model"], config.get("api_key", "local-only"))
    if policy_evidence is not None:
        atomic_json(output / "service-policy-evidence.json", {**policy_evidence, "content": policy_content})
    atomic_json(output / "effective-config.json", {key: value for key, value in config.items() if key != "api_key"})
    atomic_json(output / "pairs-manifest.json", {"pairs": pairs, "profile": profile, "stage1_run": str(stage1_run.resolve()),
                                              "stage1_predictions_sha256": _file_sha(stage1_run / "predictions.json")})
    results, document_starts = [], {}
    started = time.monotonic()
    for pair in pairs:
        admitted = time.monotonic()
        doc_start = document_starts.setdefault(pair["document_id"], admitted)
        deadline = min(admitted + config.get("pair_timeout", 300),
                       doc_start + config.get("document_timeout", 1800))
        folder = output / "pairs" / pair["pair_id"]
        folder.mkdir()
        context = PageContext(
            page_id=pair["pair_id"], document_id=pair["document_id"], output_dir=folder,
            deadline=deadline, client=client, journal=journal, slots=slots,
            model_dir=Path(config["model_dir"]), region_timeout=config.get("region_timeout", 120),
        )
        context.emit("pair_admitted", page_ids=pair["page_ids"], page_indices=pair["page_indices"], profile=profile)
        result = {**pair, "profile": profile, "service_policy_evidence": policy_evidence,
                  "status": "FAIL", "errors": [], "requests": [], "writeback_applied": False,
                  "separate_stage2_export_only": True, "original_stage1_writeback": False,
                  "stage1_predecessors": [{
                      "page_id": page_id, "status": predictions[page_id].get("status"),
                      "finish_reason": predictions[page_id].get("finish_reason"),
                      "errors": predictions[page_id].get("errors", []),
                      "model_call_statuses": [{key: record.get(key) for key in
                                               ("request_id", "status", "finish_reason", "error")}
                                              for record in predictions[page_id].get("request_records", [])],
                      "result_path": str(stage1_run / "pages" / page_id / "result.json"),
                  } for page_id in pair["page_ids"]]}
        try:
            if context.remaining_seconds() <= 0:
                raise TimeoutError("DOCUMENT_DEADLINE_BEFORE_PAIR_ADMISSION")
            loaded = [_page_assets(stage1_run, cases[page_id], predictions[page_id]) for page_id in pair["page_ids"]]
            images, pages, assets = map(list, zip(*loaded))
            fragments = _fragments(pages)
            result.update(source_assets=assets, original_table_fragments=fragments)
            if len(pages) > 2:
                result.update(status="UNSUPPORTED", original_pages=copy.deepcopy(pages),
                              recursive_3plus_support="UNSUPPORTED_REQUIRES_VERSIONED_MARKDOWN_RENDERER")
                result["errors"].append("RECURSIVE_3PLUS_REQUIRES_VERSIONED_MARKDOWN_RENDERER")
            else:
                result.update(process_crosspage_pair(images, pages, context))
            result["writeback_audit"] = _audit_writeback(pages, result, fragments)
            if any(record.get("status") != "PASS" for record in context.requests):
                result["status"] = "FAIL_BUDGET" if any(
                    record.get("status") == "FAIL_BUDGET" for record in context.requests
                ) else "FAIL"
                result["errors"].append("ONE_OR_MORE_MODEL_CALLS_FAILED")
            if result["status"] == "PASS" and "rewritten_markdown" in result:
                result["exported_pages"] = _export_pages(stage1_run, folder, pages, result["rewritten_markdown"])
            if context.remaining_seconds() <= 0:
                raise TimeoutError("PAIR_DEADLINE_BEFORE_ARTIFACTS_COMPLETE")
        except Exception as error:
            result["status"] = "FAIL_BUDGET" if any(
                record.get("status") == "FAIL_BUDGET" for record in context.requests
            ) else "FAIL"
            result["errors"].append(f"{type(error).__name__}: {error}")
        result.update(request_records=context.requests, admitted_monotonic=admitted,
                      timing_scope="O1_STAGE2_FROM_FROZEN_STAGE1", quality_status="UNSCORED")
        atomic_json(folder / "result.json", result)
        if context.remaining_seconds() <= 0:
            result["status"] = "FAIL"
            result["errors"].append("PAIR_DEADLINE_DURING_ARTIFACT_WRITE")
            atomic_json(folder / "result.json", result)
        complete = time.monotonic()
        timing = {"latency_seconds": complete - admitted, "complete_monotonic": complete}
        atomic_json(folder / "timing.json", timing)
        context.emit("pair_terminal", status=result["status"], profile=profile, **timing)
        results.append({"pair_id": pair["pair_id"], "profile": profile, "status": result["status"], **timing})
    summary = {"profile": profile, "service_policy_evidence": policy_evidence,
               "submitted_pairs": len(pairs), "terminal_pairs": len(results),
               "pass_pairs": sum(item["status"] == "PASS" for item in results),
               "unsupported_pairs": sum(item["status"] == "UNSUPPORTED" for item in results),
               "batch_wall_seconds": time.monotonic() - started, "results": results,
               "timing_scope": "O1_STAGE2_FROM_FROZEN_STAGE1", "quality_status": "UNSCORED",
               "combined_stage1_stage2_end_to_end_measured": False,
               "selection_status": "SELECTED" if pairs else "GAP_NO_ADJACENT_ORIGINAL_PAGES"}
    atomic_json(output / "summary.json", summary)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1-run", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="Same full original Stage1 input manifest; default: RUN/input-manifest.json")
    parser.add_argument("--pairs", type=Path, help='JSON {"pairs":[{"pair_id":"x","page_ids":["p1","p2"]}]}')
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=["O1-16K-PRED", "O1-LOWPIX-16K-PRED"], default="O1-16K-PRED")
    parser.add_argument("--service-policy-evidence", type=Path,
                        help="Read-only JSON policy snapshot; its bytes/hash/content are recorded, not applied")
    parser.add_argument("--pair-timeout", type=float, default=300)
    parser.add_argument("--document-timeout", type=float, default=1800)
    parser.add_argument("--region-timeout", type=float, default=120)
    args = parser.parse_args(argv)
    if any(value <= 0 for value in (args.pair_timeout, args.document_timeout, args.region_timeout)):
        parser.error("timeouts must be positive")
    config = {"base_url": args.base_url, "model": args.model, "model_dir": str(args.model_dir.resolve()),
              "api_key": os.environ.get("OCR_API_KEY", "local-only"),
              "pair_timeout": args.pair_timeout, "document_timeout": args.document_timeout,
              "region_timeout": args.region_timeout, "max_model_len": 16384,
              "requested_service_max_images": 2, "profile": args.profile,
              "service_policy_evidence": str(args.service_policy_evidence.resolve()) if args.service_policy_evidence else None}
    summary = run_pairs(args.stage1_run.resolve(), args.out.resolve(), config,
                        pairs_manifest=args.pairs, manifest_path=args.manifest)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, ensure_ascii=False))
    return 0 if summary["submitted_pairs"] > 0 and summary["pass_pairs"] == summary["submitted_pairs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
