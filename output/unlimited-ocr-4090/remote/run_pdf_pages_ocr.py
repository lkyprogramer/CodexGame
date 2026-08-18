#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import fitz
import torch

from run_ocr import collect_text, load_model, run_image, run_with_oom_retry, write_return


TEXT_EXTS = {".txt", ".md", ".mmd", ".json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["gundam", "base"], default="base")
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--dpi", type=int, default=150)
    return parser.parse_args()


def clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("![](") and stripped.endswith(")"):
            continue
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def read_text(out_dir: Path) -> str:
    result_path = out_dir / "result.md"
    if result_path.exists():
        return clean_text(result_path.read_text(encoding="utf-8", errors="replace"))
    parts: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_EXTS:
            parts.append(clean_text(path.read_text(encoding="utf-8", errors="replace")))
    return "\n".join(part for part in parts if part)


def render_page(page: fitz.Page, out_dir: Path, page_number: int, dpi: int) -> Path:
    out_path = out_dir / f"page_{page_number:04d}.png"
    scale = dpi / 72
    page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(str(out_path))
    return out_path


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "run_meta.json"
    started = time.perf_counter()
    meta = {
        "group": args.group,
        "input": str(input_path),
        "output": str(out_dir),
        "mode_arg": args.mode,
        "max_length_arg": args.max_length,
        "dpi": args.dpi,
        "input_size_bytes": input_path.stat().st_size if input_path.exists() else None,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }

    try:
        tokenizer, model = load_model(args.model)
        tmp_root = Path(tempfile.mkdtemp(prefix="unlimited_ocr_pdf_", dir="/work/tmp"))
        image_dir = tmp_root / input_path.stem
        image_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(str(input_path))
        meta["page_count"] = doc.page_count
        pages = []
        merged_parts: list[str] = []
        used_max_length = args.max_length
        oom_retry = False

        for index, page in enumerate(doc, start=1):
            page_started = time.perf_counter()
            page_out = out_dir / f"page_{index:04d}"
            page_out.mkdir(parents=True, exist_ok=True)
            image_path = render_page(page, image_dir, index, args.dpi)
            value, used_max_length, page_oom_retry = run_with_oom_retry(
                lambda limit: run_image(model, tokenizer, image_path, page_out, args.mode, limit),
                used_max_length,
            )
            oom_retry = oom_retry or page_oom_retry
            write_return(page_out, value)
            chars, text_paths = collect_text(page_out)
            text = read_text(page_out)
            if text:
                merged_parts.append(f"## Page {index}\n\n{text}")
            pages.append(
                {
                    "page": index,
                    "image": str(image_path),
                    "output": str(page_out),
                    "chars": chars,
                    "elapsed_s": time.perf_counter() - page_started,
                    "text_paths": text_paths,
                }
            )
            meta.update(
                {
                    "ok": True,
                    "run_mode": f"pdf-pages-{args.mode}",
                    "used_max_length": used_max_length,
                    "oom_retry_8192": oom_retry,
                    "pages": pages,
                    "output_chars": sum(page["chars"] for page in pages),
                }
            )
            meta["elapsed_s"] = time.perf_counter() - started
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        doc.close()
        merged_text = "\n\n".join(merged_parts)
        (out_dir / "result.md").write_text(merged_text, encoding="utf-8")
        meta.update({"text_paths": [str(out_dir / "result.md")], "output_chars": len(merged_text)})
    except (OSError, RuntimeError, ValueError) as exc:
        meta.update({"ok": False, "error": repr(exc)})
        raise
    finally:
        meta["elapsed_s"] = time.perf_counter() - started
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
