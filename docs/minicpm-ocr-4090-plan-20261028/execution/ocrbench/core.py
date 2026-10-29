"""Bounded page admission with killable persistent adapter workers."""
from __future__ import annotations

import fcntl
import hashlib
import importlib
import json
import math
import multiprocessing
import os
import re
import signal
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Callable

from .client import VLLMClient, atomic_json


_REGION_TASKS = frozenset({"text", "name", "seal", "formula", "display_formula",
                           "inline_formula", "table", "chart"})


def _safe_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", value):
        raise ValueError("IDs must be path-safe ASCII identifiers of at most 160 characters")
    return value


def _case_metadata(case: dict) -> dict:
    metadata = {"source_family_id": case.get("source_family_id"), "scene_tags": case.get("scene_tags", []),
                "unit_kind": case.get("unit_kind", "page"), "split": case.get("split")}
    for key in ("GT_status", "render_QA_required", "source_id", "origin_kind", "task", "original_bbox"):
        if key in case:
            metadata[key] = case[key]
    return metadata


def _sum_complete(records: list[dict], key: str):
    values = [record.get(key) for record in records]
    return sum(values) if all(type(value) is int for value in values) else None


class EventJournal:
    """Append one complete JSON line, safe across threads and page processes."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def emit(self, event: str, **fields) -> None:
        record = dict(fields, event=event, monotonic_timestamp=time.monotonic(), wall_timestamp=time.time())
        line = json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.write(line)
            stream.flush()
            fcntl.flock(stream, fcntl.LOCK_UN)


class RegionSlots:
    """Four kernel-owned locks. Killing a worker automatically releases its slots.

    A multiprocessing semaphore can remain acquired after SIGKILL. Independent
    flock file descriptors avoid that leak for the real page-timeout boundary.
    """

    def __init__(self, directory: Path, limit: int = 4):
        self.directory = directory
        self.limit = limit

    def acquire(self, deadline: float):
        while time.monotonic() < deadline:
            for index in range(self.limit):
                stream = (self.directory / f"region-{index}.lock").open("a")
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return index, stream
                except BlockingIOError:
                    stream.close()
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        raise TimeoutError("region deadline exceeded waiting for a global slot")


class PageContext:
    def __init__(self, *, page_id: str, document_id: str, output_dir: Path,
                 deadline: float, client: VLLMClient, journal: EventJournal,
                 slots: RegionSlots, model_dir: Path, layout_model_dir: Path | None = None,
                 options: dict | None = None, region_timeout: float = 120):
        self.page_id = page_id
        self.document_id = document_id
        self.output_dir = output_dir
        self.deadline = deadline
        self.client = client
        self.journal = journal
        self.slots = slots
        self.model_dir = model_dir
        self.layout_model_dir = layout_model_dir
        self.options = options or {}
        self.region_timeout = region_timeout
        self.requests: list[dict] = []
        self._records_lock = threading.Lock()

    def emit(self, event: str, **fields) -> None:
        fields.pop("page_id", None)
        fields.pop("document_id", None)
        self.journal.emit(event, page_id=self.page_id, document_id=self.document_id, **fields)

    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def call(self, image_paths: list[Path], prompt: str, task_limit: int, task_name: str) -> dict:
        if self.remaining_seconds() <= 0:
            raise TimeoutError("page deadline elapsed")
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        deadline = min(self.deadline, started + self.region_timeout)
        self.emit("region_queued", request_id=request_id, task_name=task_name)
        stream = None
        slot = None
        try:
            slot, stream = self.slots.acquire(deadline)
            self.emit("region_start", request_id=request_id, task_name=task_name, slot=slot)
            response = self.client.complete(
                [Path(path) for path in image_paths], prompt, task_limit, deadline,
                self.output_dir / "requests" / request_id, request_id,
            )
            if time.monotonic() >= deadline and response["status"] == "PASS":
                response.update(status="FAIL", error="REGION_DEADLINE_DURING_EVIDENCE_WRITE")
        except Exception as error:
            response = {"content": "", "finish_reason": None, "usage": None,
                        "request_id": request_id, "status": "FAIL", "error": str(error)}
        finally:
            self.emit("region_end", request_id=request_id, task_name=task_name, slot=slot)
            if stream is not None:
                fcntl.flock(stream, fcntl.LOCK_UN)
                stream.close()
        response.update(task_name=task_name, wall_seconds=time.monotonic() - started,
                        prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
        with self._records_lock:
            self.requests.append(response)
            atomic_json(self.output_dir / "request-records.json", self.requests)
        return response


def _decode_page(case: dict):
    from PIL import Image, ImageOps
    source = Path(case["path"])
    if case["kind"] == "pdf":
        import fitz
        with fitz.open(source) as document:
            if not document.is_pdf:
                raise ValueError("PDF input is not a PDF document")
            page = document.load_page(case["page_index"])
            matrix = fitz.Matrix(300 / 72, 300 / 72)
            bounds = (page.rect * matrix).irect
            pixels = max(1, bounds.width) * max(1, bounds.height)
            # Check before MuPDF allocates the raster, using Pillow's existing
            # error threshold. page.rect already includes crop and rotation.
            if Image.MAX_IMAGE_PIXELS is not None and pixels > 2 * Image.MAX_IMAGE_PIXELS:
                raise Image.DecompressionBombError(
                    f"Image size ({pixels} pixels) exceeds limit of {2 * Image.MAX_IMAGE_PIXELS} "
                    "pixels, could be decompression bomb DOS attack.")
            pixmap = page.get_pixmap(matrix=matrix,
                                     colorspace=fitz.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        transform = {"pdf_page_index": case["page_index"], "dpi": 300, "exif_orientation": None}
    else:
        with Image.open(source) as original:
            orientation = original.getexif().get(274)
            image = ImageOps.exif_transpose(original).convert("RGB")
        transform = {"dpi": None, "exif_orientation": orientation, "exif_normalized": True}
    return image, transform


def render_page(case: dict, destination: Path, context: PageContext, timing_scope: str) -> dict:
    """Render only this admitted page, never materialize a future online page."""
    source = Path(case["path"])
    if case["kind"] == "pdf" and timing_scope != "D0":
        raise ValueError("PDF inputs require D0; P0 must point to ready common page pixels")
    context.emit("raster_start" if timing_scope == "D0" else "pixel_load_start",
                 page_index=case.get("page_index"), dpi=300 if case["kind"] == "pdf" else None)
    image, transform = _decode_page(case)
    pixel_hash = hashlib.sha256(image.tobytes()).hexdigest()
    if case.get("expected_pixel_hash") and pixel_hash != case["expected_pixel_hash"]:
        raise ValueError("INPUT_PIXEL_HASH_MISMATCH")
    image.save(destination, format="PNG")
    with source.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    metadata = {"input_pixel_hash": pixel_hash, "width": image.width, "height": image.height,
                "color_mode": "RGB", "orientation_transform": transform,
                "source_sha256": source_hash}
    context.emit("raster_end" if timing_scope == "D0" else "pixel_load_end", **metadata)
    return metadata


def _adapter_worker(connection, config: dict, adapter_override: Callable | None) -> None:
    # Each worker owns its child processes and is terminated as a group on a
    # deadline. Its adapter/module cache survives ordinary pages within a run.
    initialized = time.monotonic()
    os.setsid()
    adapter = adapter_override
    if adapter is None:
        adapter = importlib.import_module("ocrbench." + config["adapter"]).process_page
    client = VLLMClient(config["base_url"], config["model"], config.get("api_key", "local-only"))
    journal = EventJournal(Path(config["out"]) / "events.jsonl")
    warmup_journal = EventJournal(Path(config["out"]) / "warmup" / "events.jsonl")
    slots = RegionSlots(Path(config["out"]) / "locks", config["region_limit"])
    connection.send({"worker_ready": True, "initialize_wall_seconds": time.monotonic() - initialized})
    while True:
        message = connection.recv()
        if message is None:
            return
        case, admitted, deadline, phase = message
        phase_root = Path(config["out"]) / "warmup" if phase == "warmup" else Path(config["out"])
        output = phase_root / "pages" / case["page_id"]
        output.mkdir(parents=True, exist_ok=False)
        context = PageContext(
            page_id=case["page_id"], document_id=case["document_id"], output_dir=output,
            deadline=deadline, client=client, journal=warmup_journal if phase == "warmup" else journal, slots=slots,
            model_dir=Path(config["model_dir"]),
            layout_model_dir=Path(config["layout_model_dir"]) if config.get("layout_model_dir") else None,
            options=dict(config.get("options") or {}), region_timeout=config["region_timeout"],
        )
        result = {"page_id": case["page_id"], "document_id": case["document_id"],
                  "status": "FAIL", "errors": [], "ordered_blocks": [], "text": "", "raw_text": "", "markdown": ""}
        try:
            if config["timing_scope"] == "R0" and "task" in case:
                task = case["task"]
                if not isinstance(task, str) or task not in _REGION_TASKS:
                    raise ValueError("INVALID_R0_REGION_TASK")
                context.options["region_task"] = task
            metadata = render_page(case, output / "input.png", context, config["timing_scope"])
            if context.remaining_seconds() <= 0:
                raise TimeoutError("page expired during rasterization")
            parsed = adapter(output / "input.png", context)
            if (not isinstance(parsed, dict) or parsed.get("status") not in {"PASS", "FAIL", "FAIL_BUDGET", "UNSUPPORTED"}
                    or not isinstance(parsed.get("text"), str) or not isinstance(parsed.get("raw_text"), str)
                    or not isinstance(parsed.get("markdown"), str)
                    or not isinstance(parsed.get("ordered_blocks"), list) or not isinstance(parsed.get("errors"), list)):
                raise ValueError("INVALID_ADAPTER_RESULT")
            result.update(parsed)
            # Adapter cannot overwrite admitted identity or input evidence.
            result.update(page_id=case["page_id"], document_id=case["document_id"], **metadata)
            if any(record["status"] != "PASS" for record in context.requests):
                result["status"] = "FAIL_BUDGET" if any(r["status"] == "FAIL_BUDGET" for r in context.requests) else "FAIL"
                result["errors"].append("ONE_OR_MORE_MODEL_CALLS_FAILED")
            if context.remaining_seconds() <= 0:
                raise TimeoutError("page expired before artifacts were complete")
        except Exception as error:
            result["status"] = "FAIL"
            result["errors"].append(str(error))
            atomic_json(output / "exception.json", {"error": str(error), "traceback": traceback.format_exc()})
        result.update(request_records=context.requests, timing_scope=config["timing_scope"],
                      **_case_metadata(case),
                      admitted_monotonic=admitted, execution_phase=phase)
        atomic_json(output / "result.json", result)
        for filename, text in (("text.txt", result["text"]), ("raw-text.txt", result["raw_text"]),
                               ("markdown.md", result["markdown"])):
            temporary = output / (filename + ".tmp")
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(output / filename)
        if context.remaining_seconds() <= 0:
            result["status"] = "FAIL"
            result["errors"].append("PAGE_DEADLINE_DURING_ARTIFACT_WRITE")
            atomic_json(output / "result.json", result)
        context.emit("artifacts_complete", status=result["status"])
        # Capture after all required IR/text/assets are on disk. The timing
        # record is measurement instrumentation, rather than predicted content.
        complete = time.monotonic()
        timing = {"admitted_monotonic": admitted, "complete_monotonic": complete,
                  "latency_seconds": complete - admitted,
                  "latency_scope": "admission_to_required_artifacts_complete"}
        atomic_json(output / "timing.json", timing)
        context.emit("page_terminal", status=result["status"], **timing)
        usage = [record.get("usage") for record in context.requests]
        usage_complete = all(isinstance(value, dict) and type(value.get("prompt_tokens")) is int
                             and type(value.get("completion_tokens")) is int for value in usage)
        connection.send({"page_id": case["page_id"], "document_id": case["document_id"], "status": result["status"], **timing,
                         "execution_phase": phase, "logical_request_count": len(context.requests),
                         "model_call_count": sum(attempt.get("phase") == "completion" for record in context.requests for attempt in record.get("attempts", [])),
                         "tokenize_http_attempt_count": sum(attempt.get("phase") == "tokenize" for record in context.requests for attempt in record.get("attempts", [])),
                         "prompt_tokens": sum(value["prompt_tokens"] for value in usage) if usage_complete else None,
                         "completion_tokens": sum(value["completion_tokens"] for value in usage) if usage_complete else None})


def load_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pages = data if isinstance(data, list) else data["pages"]
    if not isinstance(pages, list) or not pages:
        raise ValueError("manifest pages must be a nonempty list")
    seen = set()
    clean = []
    for page in pages:
        # Whitelist only inference metadata. GT, reference text and annotations
        # never cross into the worker/adapter, even if supplied in the manifest.
        entry = {key: page[key] for key in (
            "page_id", "document_id", "source_family_id", "kind", "page_index",
            "expected_pixel_hash", "scene_tags", "split", "unit_kind", "path",
            "GT_status", "render_QA_required", "source_id", "origin_kind", "task", "original_bbox",
        ) if key in page}
        entry["page_id"] = _safe_id(entry["page_id"])
        entry["document_id"] = _safe_id(entry["document_id"])
        if entry["page_id"] in seen:
            raise ValueError("duplicate page_id")
        seen.add(entry["page_id"])
        if entry.get("kind") not in {"pdf", "image"}:
            raise ValueError("input kind must be pdf or image")
        source = Path(entry["path"])
        if not source.is_absolute():
            source = path.parent / source
        if not source.is_file():
            raise ValueError(f"missing input for {entry['page_id']}")
        entry["path"] = str(source.resolve())
        if entry["kind"] == "pdf" and (type(entry.get("page_index")) is not int or entry["page_index"] < 0):
            raise ValueError("PDF requires nonnegative zero-based page_index")
        clean.append(entry)
    return clean


def run_pages(pages: list[dict], config: dict, adapter_override: Callable | None = None,
              warmup_pages: list[dict] | None = None) -> dict:
    admission = config.get("page_admission", 1)
    if admission not in {1, 2, 4} or config.get("region_limit", 4) not in {1, 2, 4}:
        raise ValueError("page admission and global region limit must be 1, 2 or 4")
    if not pages:
        raise ValueError("at least one timed input is required")
    warmup_enabled = warmup_pages is not None
    if warmup_enabled and (not warmup_pages or any(p.get("split") != "development" for p in warmup_pages)):
        raise ValueError("warmup must contain only explicitly marked development inputs")
    endurance = config.get("execution_mode") == "E0"
    admission_window = config.get("admission_window_seconds")
    minimum_completed = config.get("minimum_completed_pages", 300)
    if admission_window is not None and not endurance:
        raise ValueError("an admission time window requires explicit E0 mode")
    if endurance:
        if (config.get("timing_scope", "D0") != "P0" or not warmup_enabled or len(warmup_pages) != 4
                or admission != 4 or config.get("region_limit", 4) != 4):
            raise ValueError("E0 requires P0, four development warmup inputs, page admission four and region limit four")
        if type(admission_window) not in (int, float) or not math.isfinite(admission_window) or admission_window <= 0:
            raise ValueError("E0 admission window must be finite and positive")
        if type(minimum_completed) is not int or minimum_completed <= 0:
            raise ValueError("E0 minimum completed pages must be a positive integer")
    pages = [dict(page) for page in pages]
    warmup_pages = [dict(page) for page in warmup_pages or []]
    documents = {}
    seen_documents = set()
    last_document = None
    for case in pages:
        document_id = case["document_id"]
        if document_id != last_document:
            if document_id in seen_documents:
                raise ValueError("manifest must keep each document's pages contiguous")
            seen_documents.add(document_id)
            last_document = document_id
        documents.setdefault(document_id, []).append(case)
    output = Path(config["out"])
    output.mkdir(parents=True, exist_ok=False)
    (output / "locks").mkdir()
    (output / "pages").mkdir()
    (output / "warmup" / "pages").mkdir(parents=True)
    config = dict(config, page_admission=admission, out=str(output.resolve()),
                  region_limit=config.get("region_limit", 4),
                  page_timeout=config.get("page_timeout", 300),
                  document_timeout=config.get("document_timeout", 1800),
                  region_timeout=config.get("region_timeout", 120),
                  timing_scope=config.get("timing_scope", "D0"))
    if config["timing_scope"] not in {"D0", "P0", "R0"}:
        raise ValueError("unsupported timing scope")
    timing_mode = "warm_adapter" if warmup_enabled else "cold_adapter"
    preparation = {
        "input_preparation": (
            "offline RGB audit discarded; timed D0 rerenders" if warmup_enabled and config["timing_scope"] == "D0" else
            "offline RGB audit discarded; timed prepared image decode and parse" if warmup_enabled else
            "no executor offline RGB audit; timed D0 renders admitted sources" if config["timing_scope"] == "D0" else
            "no executor offline RGB audit; timed prepared image decode and parse"
        ),
        "storage_cache_state": "preaccessed/uncontrolled, not cold" if warmup_enabled else
                               "uncontrolled; no executor preaudit; not verified cold",
    }
    safe_config = {key: value for key, value in config.items() if key != "api_key"}
    safe_config.update(preparation)
    safe_config["timing_mode"] = timing_mode
    safe_config["warmup_enabled"] = warmup_enabled
    atomic_json(output / "effective-config.json", safe_config)
    journal = EventJournal(output / "events.jsonl")
    warm_journal = EventJournal(output / "warmup" / "events.jsonl")
    job_started = time.monotonic()
    journal.emit("run_start", planned_pages=len(pages), timing_mode=timing_mode)
    preflight_seconds = 0.0
    abort_reason = None
    formal_duplicates = []

    # Pixel isolation is an explicitly offline admission check. It may rasterize
    # original PDFs once and discard pixels. D0 still re-renders each current
    # admitted page online and verifies this frozen pixel hash.
    if warmup_enabled:
        audit_started = time.monotonic()
        journal.emit("pixel_isolation_preflight_start")
        audit = []
        warm_keys = set()
        formal_keys = {}
        cache = {}
        try:
            for phase, inputs in (("warmup", warmup_pages), ("formal", pages)):
                for case in inputs:
                    key = (case["path"], case["kind"], case.get("page_index"))
                    if key not in cache:
                        image, _ = _decode_page(case)
                        cache[key] = (image.width, image.height, hashlib.sha256(image.tobytes()).hexdigest())
                        image.close()
                    width, height, pixel_hash = cache[key]
                    if case.get("expected_pixel_hash") and case["expected_pixel_hash"] != pixel_hash:
                        raise ValueError("INPUT_PIXEL_HASH_MISMATCH_DURING_PREFLIGHT")
                    case["expected_pixel_hash"] = pixel_hash
                    pixel_key = (width, height, pixel_hash)
                    audit.append({"phase": phase, "page_id": case["page_id"], "width": width,
                                  "height": height, "input_pixel_hash": pixel_hash})
                    if phase == "warmup":
                        warm_keys.add(pixel_key)
                    elif pixel_key in warm_keys:
                        raise ValueError("WARMUP_FORMAL_RGB_PIXEL_OVERLAP")
                    elif pixel_key in formal_keys:
                        formal_duplicates.append({"page_id": case["page_id"], "same_pixels_as": formal_keys[pixel_key]})
                    else:
                        formal_keys[pixel_key] = case["page_id"]
        except Exception as error:
            abort_reason = str(error)
        preflight_seconds = time.monotonic() - audit_started
        atomic_json(output / "pixel-isolation.json", {"status": "FAIL" if abort_reason else "PASS",
                    "error": abort_reason, "wall_seconds": preflight_seconds, "pages": audit,
                    "formal_duplicate_pixels": formal_duplicates,
                    "scope": "offline_preflight_not_in_formal_latency"})
        journal.emit("pixel_isolation_preflight_end", status="FAIL" if abort_reason else "PASS",
                     error=abort_reason, wall_seconds=preflight_seconds)
    atomic_json(output / "input-manifest.json", {"pages": pages})
    atomic_json(output / "warmup" / "input-manifest.json", {"pages": warmup_pages})
    mp = multiprocessing.get_context("spawn")
    workers = []
    document_starts: dict[str, float] = {}
    results = []
    warm_results = []
    initialization = []
    next_page = 0
    formal_started = None
    formal_ended = None
    first_warmup = None
    last_warmup = None
    document_results = []
    warm_document_results = []
    document_order = list(documents)
    current_document_index = 0
    worker_count = min(admission, len(pages))
    admission_deadline = None
    admission_closed = False
    admission_closed_at = None
    admission_stop_reason = None
    admitted_documents = {}
    endurance_recovery_errors = []

    def close_admission(reason, closed_at):
        nonlocal admission_closed, admission_closed_at, admission_stop_reason
        admission_closed = True
        admission_closed_at = closed_at
        admission_stop_reason = reason
        journal.emit("endurance_admission_closed", reason=reason, submitted_pages=next_page,
                     candidate_pool_pages=len(pages), closed_monotonic=closed_at)

    def warmups_for(index, generation):
        if not warmup_enabled:
            return []
        chosen = warmup_pages[index::worker_count] or [warmup_pages[index % len(warmup_pages)]]
        return [dict(case,
                     page_id=f"WARMUP-W{index}-G{generation}-{sequence}-{case['page_id']}",
                     document_id=f"WARMUP-W{index}-G{generation}-{case['document_id']}")
                for sequence, case in enumerate(chosen)]

    def launch(index, generation=0):
        parent, child = mp.Pipe()
        process = mp.Process(target=_adapter_worker, args=(child, config, adapter_override))
        launched = time.monotonic()
        process.start()
        child.close()
        warmups = warmups_for(index, generation)
        warm_documents = {}
        for case in warmups:
            warm_documents.setdefault(case["document_id"], []).append(case)
        return {"process": process, "connection": parent, "case": None, "ready": False,
                "index": index, "generation": generation, "launched": launched,
                "initialize_deadline": launched + config.get("worker_init_timeout", 60),
                "pending_warmups": list(warmups), "warmup_documents": warm_documents,
                "assembled_warmup_documents": set()}

    def terminate(worker):
        process = worker["process"]
        if process.is_alive():
            try:
                if os.getpgid(process.pid) == process.pid:
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass
        process.join(timeout=2)
        worker["connection"].close()

    def retire(worker):
        terminate(worker)
        worker.update(disabled=True, case=None, pending_warmups=[])

    def fail_endurance_recovery(worker, reason):
        endurance_recovery_errors.append({"worker_index": worker["index"], "generation": worker["generation"],
                                          "reason": reason})
        if not admission_closed:
            close_admission(reason, time.monotonic())
        retire(worker)

    def recover_failure(worker, reason):
        case = worker["case"]
        phase = worker["phase"]
        events = warm_journal if phase == "warmup" else journal
        terminate(worker)
        active_requests = {}
        if events.path.exists():
            with events.path.open() as stream:
                fcntl.flock(stream, fcntl.LOCK_SH)
                for line in stream:
                    event = json.loads(line)
                    if event.get("page_id") == case["page_id"]:
                        if event["event"] == "region_start":
                            active_requests[event["request_id"]] = event
                        elif event["event"] == "region_end":
                            active_requests.pop(event["request_id"], None)
                fcntl.flock(stream, fcntl.LOCK_UN)
        for request_id, event in active_requests.items():
            events.emit("region_end", page_id=case["page_id"], document_id=case["document_id"],
                        request_id=request_id, task_name=event.get("task_name"),
                        slot=event.get("slot"), aborted=True, error=reason)
        failed = {"page_id": case["page_id"], "document_id": case["document_id"],
                  "status": "FAIL", "errors": [reason], "text": "", "raw_text": "",
                  "ordered_blocks": [], "timing_scope": config["timing_scope"],
                  "execution_phase": phase, **_case_metadata(case),
                  "model_call_count": None, "logical_request_count": None,
                  "tokenize_http_attempt_count": None,
                  "latency_seconds": time.monotonic() - worker["admitted"],
                  "partial_artifacts_preserved": True}
        phase_root = output / "warmup" if phase == "warmup" else output
        page_dir = phase_root / "pages" / case["page_id"]
        page_dir.mkdir(exist_ok=True)
        atomic_json(page_dir / "result.json", failed)
        events.emit("page_terminal", page_id=case["page_id"], document_id=case["document_id"],
                    status="FAIL", error=reason, latency_seconds=failed["latency_seconds"])
        return failed

    def assemble(document_id, cases, phase, admitted):
        events = warm_journal if phase == "warmup" else journal
        events.emit("document_assembly_start", document_id=document_id)
        deadline = admitted + config["document_timeout"]
        try:
            from .document import assemble_document
            result = assemble_document(document_id, cases, output / "warmup" if phase == "warmup" else output, deadline)
            if not isinstance(result, dict) or result.get("status") not in {"PASS", "FAIL"}:
                raise ValueError("INVALID_DOCUMENT_ASSEMBLY_RESULT")
        except Exception as error:
            result = {"status": "FAIL", "errors": [str(error)]}
        complete = time.monotonic()
        if complete > deadline:
            result.update(status="FAIL", errors=result.get("errors", []) + ["DOCUMENT_DEADLINE_DURING_ASSEMBLY"])
        result.update(document_id=document_id, execution_phase=phase, admitted_monotonic=admitted,
                      complete_monotonic=complete, latency_seconds=complete - admitted)
        events.emit("document_terminal", **result)
        target = (output / "warmup" if phase == "warmup" else output) / "documents" / document_id
        atomic_json(target / "terminal.json", result)
        return result

    pool_started = time.monotonic()
    try:
        if not abort_reason:
            workers = [launch(index) for index in range(worker_count)]
        while not abort_reason and ((next_page < len(pages) and not admission_closed)
                                    or any(w["case"] is not None for w in workers)
                                    or formal_started is None):
            if endurance and formal_started is not None and not admission_closed and time.monotonic() >= admission_deadline:
                close_admission("ADMISSION_WINDOW_ELAPSED", time.monotonic())
            for index, worker in enumerate(workers):
                if worker.get("disabled"):
                    continue
                if endurance and formal_started is not None:
                    if not admission_closed and time.monotonic() >= admission_deadline:
                        close_admission("ADMISSION_WINDOW_ELAPSED", time.monotonic())
                    if admission_closed and worker["generation"] > 0 and worker["case"] is None:
                        retire(worker)
                        continue
                process = worker["process"]
                if not worker["ready"]:
                    if worker["connection"].poll():
                        try:
                            ready = worker["connection"].recv()
                            if not ready.get("worker_ready"):
                                raise ValueError("invalid worker readiness message")
                            worker["ready"] = True
                            initialization.append(dict(ready, worker_index=index, generation=worker["generation"],
                                                       launch_to_ready_seconds=time.monotonic() - worker["launched"]))
                        except (EOFError, ValueError):
                            if endurance and formal_started is not None:
                                fail_endurance_recovery(worker, "RECOVERY_WORKER_INITIALIZATION_FAILED")
                                continue
                            abort_reason = "WORKER_INITIALIZATION_FAILED"
                            break
                    elif not process.is_alive() or time.monotonic() >= worker["initialize_deadline"]:
                        if endurance and formal_started is not None:
                            fail_endurance_recovery(worker, "RECOVERY_WORKER_INITIALIZATION_FAILED")
                            continue
                        abort_reason = "WORKER_INITIALIZATION_FAILED"
                        break
                    else:
                        continue
                case = worker["case"]
                if case is not None:
                    completed = worker["connection"].poll()
                    if completed:
                        try:
                            record = worker["connection"].recv()
                            record.update(worker_index=index, generation=worker["generation"])
                            if worker["phase"] == "warmup":
                                warm_results.append(record)
                                last_warmup = time.monotonic()
                                if record["status"] != "PASS":
                                    if endurance and formal_started is not None:
                                        fail_endurance_recovery(worker, "RECOVERY_WARMUP_FAILED")
                                        continue
                                    abort_reason = "WARMUP_FAILED"
                                    break
                            else:
                                results.append(record)
                            worker["case"] = None
                        except EOFError:
                            completed = False
                    if not completed and (not process.is_alive() or time.monotonic() >= worker["deadline"]):
                        reason = "PAGE_OR_DOCUMENT_DEADLINE" if process.is_alive() else "WORKER_EXITED"
                        failed = recover_failure(worker, reason)
                        if worker["phase"] == "warmup":
                            warm_results.append(failed)
                            last_warmup = time.monotonic()
                            if endurance and formal_started is not None:
                                fail_endurance_recovery(worker, "RECOVERY_WARMUP_FAILED")
                                continue
                            abort_reason = "WARMUP_FAILED"
                            break
                        results.append(failed)
                        if endurance and (admission_closed or time.monotonic() >= admission_deadline):
                            if not admission_closed:
                                close_admission("ADMISSION_WINDOW_ELAPSED", time.monotonic())
                            retire(worker)
                            continue
                        workers[index] = launch(index, worker["generation"] + 1)
                        continue
                if worker["case"] is None and worker["pending_warmups"]:
                    if endurance and formal_started is not None and worker["generation"] > 0:
                        if not admission_closed and time.monotonic() >= admission_deadline:
                            close_admission("ADMISSION_WINDOW_ELAPSED", time.monotonic())
                        if admission_closed:
                            retire(worker)
                            continue
                    case = worker["pending_warmups"].pop(0)
                    admitted = time.monotonic()
                    if first_warmup is None:
                        first_warmup = admitted
                    deadline = admitted + config["page_timeout"]
                    warm_journal.emit("page_admitted", page_id=case["page_id"], document_id=case["document_id"],
                                      worker_index=index, generation=worker["generation"], deadline_monotonic=deadline)
                    worker.update(case=case, admitted=admitted, deadline=deadline, phase="warmup")
                    worker["connection"].send((case, admitted, deadline, "warmup"))
                    continue
                if worker["case"] is None:
                    for document_id, cases in worker["warmup_documents"].items():
                        if document_id in worker["assembled_warmup_documents"]:
                            continue
                        records = [record for record in warm_results if record.get("document_id") == document_id]
                        if len(records) == len(cases):
                            admitted = min(record.get("admitted_monotonic", time.monotonic()) for record in records)
                            assembled = assemble(document_id, cases, "warmup", admitted)
                            warm_document_results.append(assembled)
                            worker["assembled_warmup_documents"].add(document_id)
                            if assembled["status"] != "PASS":
                                if endurance and formal_started is not None:
                                    fail_endurance_recovery(worker, "RECOVERY_WARMUP_DOCUMENT_FAILED")
                                    break
                                abort_reason = "WARMUP_DOCUMENT_FAILED"
                                break
                    if abort_reason:
                        break
                    if worker.get("disabled"):
                        continue
                if worker["case"] is None and formal_started is not None and next_page < len(pages) and not admission_closed:
                    case = pages[next_page]
                    if case["document_id"] != document_order[current_document_index]:
                        continue
                    admitted = time.monotonic()
                    if endurance and admitted >= admission_deadline:
                        close_admission("ADMISSION_WINDOW_ELAPSED", admitted)
                        continue
                    next_page += 1
                    if endurance:
                        admitted_documents.setdefault(case["document_id"], []).append(case)
                        if next_page == len(pages):
                            close_admission("CANDIDATE_POOL_EXHAUSTED", admitted)
                    doc_start = document_starts.setdefault(case["document_id"], admitted)
                    deadline = min(admitted + config["page_timeout"], doc_start + config["document_timeout"])
                    journal.emit("page_admitted", page_id=case["page_id"], document_id=case["document_id"],
                                 deadline_monotonic=deadline, admission_limit=admission,
                                 worker_index=index, generation=worker["generation"])
                    if deadline <= admitted:
                        failed = {"page_id": case["page_id"], "document_id": case["document_id"],
                                  "status": "FAIL", "errors": ["DOCUMENT_DEADLINE"], "text": "", "raw_text": "",
                                  **_case_metadata(case), "execution_phase": "formal",
                                  "model_call_count": 0, "logical_request_count": 0,
                                  "tokenize_http_attempt_count": 0,
                                  "ordered_blocks": [], "latency_seconds": 0, "timing_scope": config["timing_scope"]}
                        page_dir = output / "pages" / case["page_id"]
                        page_dir.mkdir()
                        atomic_json(page_dir / "result.json", failed)
                        journal.emit("page_terminal", page_id=case["page_id"], document_id=case["document_id"], status="FAIL", error="DOCUMENT_DEADLINE")
                        results.append(failed)
                    else:
                        worker.update(case=case, admitted=admitted, deadline=deadline, phase="formal")
                        worker["connection"].send((case, admitted, deadline, "formal"))
            if formal_started is None and not abort_reason and all(
                    w["ready"] and not w["pending_warmups"] and w["case"] is None for w in workers):
                formal_started = time.monotonic() if warmup_enabled else pool_started
                if endurance:
                    admission_deadline = formal_started + admission_window
                journal.emit("timed_workload_start", timing_mode=timing_mode,
                             batch_start_monotonic=formal_started, warmed_workers=len(workers) if warmup_enabled else 0)
            if formal_started is not None and not abort_reason and current_document_index < len(document_order):
                document_id = document_order[current_document_index]
                cases = (admitted_documents.get(document_id, []) if endurance and admission_closed
                         else documents[document_id])
                terminal_ids = {record["page_id"] for record in results}
                if cases and all(case["page_id"] in terminal_ids for case in cases):
                    document_results.append(assemble(document_id, cases, "formal", document_starts[document_id]))
                    current_document_index += 1
            time.sleep(0.005)
        formal_ended = time.monotonic()
    finally:
        for worker in workers:
            terminate(worker)
    wall = formal_ended - formal_started if formal_started is not None else None
    initial_warm = [record for record in warm_results if record.get("generation", 0) == 0]
    recovery_warm = [record for record in warm_results if record.get("generation", 0) > 0]
    initial_warm_wall = ((formal_started if formal_started is not None else formal_ended) - first_warmup
                         if warmup_enabled and first_warmup is not None else None)
    warm_summary = {"enabled": warmup_enabled,
                    "status": "FAIL" if (abort_reason or endurance_recovery_errors) and warmup_enabled else "PASS" if warmup_enabled else "NOT_RUN",
                    "worker_count": worker_count, "completed_warmup_inputs": len(warm_results),
                    "initial_warmup_wall_seconds": initial_warm_wall,
                    "total_warmup_worker_seconds": sum(record["latency_seconds"] for record in warm_results),
                    "recovery_warmup_worker_seconds": sum(record["latency_seconds"] for record in recovery_warm),
                    "initialization": initialization, "results": warm_results,
                    "documents": warm_document_results,
                    "formal_workload_started": formal_started is not None,
                    "cost_note": "warmup requests/artifacts/events are separate; recovery warmup after a formal failure remains in formal batch wall"}
    atomic_json(output / "warmup" / "summary.json", warm_summary)
    drained = len(results) == next_page and len(document_results) == len(admitted_documents)
    window_completed = admission_stop_reason == "ADMISSION_WINDOW_ELAPSED"
    minimum_met = len(results) >= minimum_completed
    complete = (not abort_reason and window_completed and drained and minimum_met if endurance else
                not abort_reason and len(results) == len(pages) and len(document_results) == len(documents))
    documents_pass = (drained if endurance else complete) and all(result["status"] == "PASS" for result in document_results)
    performance_eligible = complete and warmup_enabled and not formal_duplicates and not endurance
    ineligible_reason = abort_reason or ("ENDURANCE_REPEATED_WORKLOAD" if endurance else
                                         "FORMAL_RGB_DUPLICATES" if formal_duplicates else
                                         "COLD_ADAPTER_NO_SAME_WORKER_WARMUP" if not warmup_enabled else
                                         "INCOMPLETE_FIXED_WORKLOAD" if not complete else None)
    summary = {"run_status": "COMPLETED" if complete else abort_reason or ("INSUFFICIENT" if endurance and (not window_completed or not minimum_met) else "INCOMPLETE"),
               **preparation,
               "planned_pages": len(pages), "submitted_pages": next_page, "terminal_pages": len(results),
               "pass_pages": sum(record["status"] == "PASS" for record in results),
               "batch_wall_seconds": wall, "timing_scope": config["timing_scope"], "timing_mode": timing_mode,
               "offline_pixel_preflight_seconds": preflight_seconds,
               "completed_units_per_second": sum(record["status"] == "PASS" for record in results) / wall if wall else None,
               "documents": document_results, "pass_documents": sum(record["status"] == "PASS" for record in document_results),
               "all_document_artifacts_pass": documents_pass,
               "primary_performance_eligible": performance_eligible,
               "recovery_warmup_model_call_count": _sum_complete(recovery_warm, "model_call_count"),
               "model_call_count_including_recovery_warmup": _sum_complete(results + recovery_warm, "model_call_count"),
               "performance_ineligibility_reason": ineligible_reason,
               "quality_status": "UNSCORED", "good_page_per_second": None, "results": results,
               "job_wall_seconds_including_preflight_cold_warmup_shutdown": time.monotonic() - job_started}
    if endurance:
        failed = (any(record["status"] != "PASS" for record in results) or not documents_pass
                  or bool(abort_reason) or bool(endurance_recovery_errors))
        summary.update(execution_mode="E0", candidate_pool_pages=len(pages), not_admitted_pages=len(pages) - next_page,
                       admission_window_seconds=admission_window, admission_closed_monotonic=admission_closed_at,
                       admission_stop_reason=admission_stop_reason,
                       admission_elapsed_seconds=admission_closed_at - formal_started if admission_closed_at is not None else None,
                       drain_seconds=formal_ended - admission_closed_at if admission_closed_at is not None else None,
                       minimum_completed_pages=minimum_completed, minimum_completed_pages_met=minimum_met,
                       admitted_workload_drained=drained,
                       endurance_recovery_errors=endurance_recovery_errors,
                       endurance_status="FAIL" if failed else "PASS" if complete else "INSUFFICIENT",
                       independent_quality_sample_count_note="repeated source pixels do not add independent quality samples")
        atomic_json(output / "not-admitted.json", {
            "status": "NOT_ADMITTED", "reason": admission_stop_reason or abort_reason,
            "pages": [{key: case[key] for key in ("page_id", "document_id", "source_id", "expected_pixel_hash") if key in case}
                      for case in pages[next_page:]],
        })
    journal.emit("run_terminal", **{key: value for key, value in summary.items() if key != "results"})
    predictions = []
    for case in pages[:next_page] if endurance else pages:
        directory = output / "pages" / case["page_id"]
        if not (directory / "result.json").is_file():
            continue
        prediction = json.loads((directory / "result.json").read_text(encoding="utf-8"))
        document = next((record for record in document_results if record["document_id"] == case["document_id"]), None)
        prediction["document_status"] = document["status"] if document else "NOT_RUN"
        if (directory / "timing.json").is_file() and not prediction.get("partial_artifacts_preserved"):
            prediction.update(json.loads((directory / "timing.json").read_text(encoding="utf-8")))
        predictions.append(prediction)
    atomic_json(output / "predictions.json", {"pages": predictions})
    atomic_json(output / "summary.json", summary)
    return summary
