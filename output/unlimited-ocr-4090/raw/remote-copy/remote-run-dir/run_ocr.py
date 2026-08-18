#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import fitz
import torch
from PIL import Image
from transformers import AutoModel, AutoTokenizer


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TEXT_EXTS = {".txt", ".md", ".mmd", ".json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["auto", "gundam", "base"], default="auto")
    parser.add_argument("--max-length", type=int, default=32768)
    parser.add_argument("--min-chars", type=int, default=50)
    return parser.parse_args()


def pdf_to_images(pdf_path: Path, tmp_root: Path, dpi: int = 300) -> list[str]:
    doc = fitz.open(str(pdf_path))
    out_dir = tmp_root / f"{pdf_path.stem}_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    paths: list[str] = []
    for i, page in enumerate(doc):
        out = out_dir / f"page_{i + 1:04d}.png"
        page.get_pixmap(matrix=mat).save(str(out))
        paths.append(str(out))
    doc.close()
    return paths


def image_info(path: Path) -> dict[str, Any]:
    try:
        with Image.open(path) as img:
            return {"width": img.width, "height": img.height, "mode": img.mode}
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def collect_text(out_dir: Path) -> tuple[int, list[str]]:
    paths: list[str] = []
    chars = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        paths.append(str(path))
        chars += len(text.strip())
    return chars, paths


def load_model(model_path: str) -> tuple[Any, Any]:
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )
    model = AutoModel.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
        use_safetensors=True,
        torch_dtype=torch.bfloat16,
    )
    return tokenizer, model.eval().cuda()


def run_image(
    model: Any,
    tokenizer: Any,
    image_path: Path,
    out_dir: Path,
    mode: str,
    max_length: int,
) -> Any:
    if mode == "gundam":
        return model.infer(
            tokenizer,
            prompt="<image>document parsing.",
            image_file=str(image_path),
            output_path=str(out_dir),
            base_size=1024,
            image_size=640,
            crop_mode=True,
            max_length=max_length,
            no_repeat_ngram_size=35,
            ngram_window=128,
            save_results=True,
        )
    return model.infer(
        tokenizer,
        prompt="<image>document parsing.",
        image_file=str(image_path),
        output_path=str(out_dir),
        base_size=1024,
        image_size=1024,
        crop_mode=False,
        max_length=max_length,
        no_repeat_ngram_size=35,
        ngram_window=128,
        save_results=True,
    )


def run_pdf(
    model: Any,
    tokenizer: Any,
    pdf_path: Path,
    out_dir: Path,
    tmp_root: Path,
    max_length: int,
) -> Any:
    return model.infer_multi(
        tokenizer,
        prompt="<image>Multi page parsing.",
        image_files=pdf_to_images(pdf_path, tmp_root),
        output_path=str(out_dir),
        image_size=1024,
        max_length=max_length,
        no_repeat_ngram_size=35,
        ngram_window=1024,
        save_results=True,
    )


def run_with_oom_retry(fn: Any, max_length: int) -> tuple[Any, int, bool]:
    try:
        return fn(max_length), max_length, False
    except RuntimeError as exc:
        if "out of memory" not in str(exc).lower() or max_length <= 8192:
            raise
        torch.cuda.empty_cache()
        return fn(8192), 8192, True


def write_return(out_dir: Path, value: Any) -> None:
    if value is None:
        return
    try:
        (out_dir / "raw_return.txt").write_text(str(value), encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "run_meta.json"
    started = time.perf_counter()

    meta: dict[str, Any] = {
        "group": args.group,
        "input": str(input_path),
        "output": str(out_dir),
        "mode_arg": args.mode,
        "max_length_arg": args.max_length,
        "input_size_bytes": input_path.stat().st_size if input_path.exists() else None,
        "input_image": image_info(input_path) if input_path.suffix.lower() in IMAGE_EXTS else None,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }

    try:
        tokenizer, model = load_model(args.model)
        suffix = input_path.suffix.lower()
        tmp_root = Path(tempfile.mkdtemp(prefix="unlimited_ocr_", dir="/work/tmp"))
        if suffix == ".pdf":
            run_mode = "pdf-base"
            value, used_max_length, oom_retry = run_with_oom_retry(
                lambda limit: run_pdf(model, tokenizer, input_path, out_dir, tmp_root, limit),
                args.max_length,
            )
            write_return(out_dir, value)
            fallback = False
        elif suffix in IMAGE_EXTS:
            run_mode = "gundam" if args.mode == "auto" else args.mode
            value, used_max_length, oom_retry = run_with_oom_retry(
                lambda limit: run_image(model, tokenizer, input_path, out_dir, run_mode, limit),
                args.max_length,
            )
            write_return(out_dir, value)
            chars, _ = collect_text(out_dir)
            fallback = False
            if args.mode == "auto" and run_mode == "gundam" and chars < args.min_chars:
                fallback = True
                fallback_dir = out_dir / "fallback_base"
                fallback_dir.mkdir(parents=True, exist_ok=True)
                value, used_max_length, second_oom_retry = run_with_oom_retry(
                    lambda limit: run_image(model, tokenizer, input_path, fallback_dir, "base", limit),
                    used_max_length,
                )
                oom_retry = oom_retry or second_oom_retry
                write_return(fallback_dir, value)
        else:
            raise ValueError(f"unsupported input suffix: {suffix}")

        chars, text_paths = collect_text(out_dir)
        meta.update(
            {
                "ok": True,
                "run_mode": run_mode,
                "fallback_base": fallback,
                "used_max_length": used_max_length,
                "oom_retry_8192": oom_retry,
                "output_chars": chars,
                "text_paths": text_paths,
            }
        )
    except Exception as exc:  # noqa: BLE001
        meta.update({"ok": False, "error": repr(exc)})
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
    finally:
        meta["elapsed_s"] = time.perf_counter() - started
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(meta, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
