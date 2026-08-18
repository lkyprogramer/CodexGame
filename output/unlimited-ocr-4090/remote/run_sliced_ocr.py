#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

import torch
from PIL import Image

from run_ocr import collect_text, image_info, load_model, run_image, run_with_oom_retry, write_return


TEXT_EXTS = {".txt", ".md", ".mmd", ".json"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["gundam", "base"], default="base")
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--slice-height", type=int, default=1800)
    parser.add_argument("--slice-overlap", type=int, default=120)
    return parser.parse_args()


def slice_image(image_path: Path, tmp_root: Path, slice_height: int, overlap: int) -> list[Path]:
    if slice_height <= overlap:
        raise ValueError("slice-height must be greater than slice-overlap")
    out_dir = tmp_root / f"{image_path.stem}_slices"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with Image.open(image_path) as image:
        width, height = image.size
        y = 0
        index = 1
        while y < height:
            bottom = min(y + slice_height, height)
            out_path = out_dir / f"slice_{index:03d}_{y}_{bottom}.png"
            image.crop((0, y, width, bottom)).save(out_path)
            paths.append(out_path)
            if bottom == height:
                break
            y = bottom - overlap
            index += 1
    return paths


def read_result_text(out_dir: Path) -> str:
    result_path = out_dir / "result.md"
    if result_path.exists():
        return clean_text(result_path.read_text(encoding="utf-8", errors="replace"))
    parts: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_EXTS:
            parts.append(clean_text(path.read_text(encoding="utf-8", errors="replace")))
    return "\n".join(part for part in parts if part)


def clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("![](") and stripped.endswith(")"):
            continue
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


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
        "slice_height": args.slice_height,
        "slice_overlap": args.slice_overlap,
        "input_size_bytes": input_path.stat().st_size if input_path.exists() else None,
        "input_image": image_info(input_path),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }

    try:
        tokenizer, model = load_model(args.model)
        tmp_root = Path(tempfile.mkdtemp(prefix="unlimited_ocr_slices_", dir="/work/tmp"))
        slice_paths = slice_image(input_path, tmp_root, args.slice_height, args.slice_overlap)
        merged_parts: list[str] = []
        slice_meta = []
        oom_retry = False
        used_max_length = args.max_length

        for index, slice_path in enumerate(slice_paths, start=1):
            slice_dir = out_dir / f"slice_{index:03d}"
            slice_dir.mkdir(parents=True, exist_ok=True)
            value, used_max_length, slice_oom_retry = run_with_oom_retry(
                lambda limit: run_image(model, tokenizer, slice_path, slice_dir, args.mode, limit),
                used_max_length,
            )
            oom_retry = oom_retry or slice_oom_retry
            write_return(slice_dir, value)
            chars, text_paths = collect_text(slice_dir)
            text = read_result_text(slice_dir)
            if text:
                merged_parts.append(text)
            slice_meta.append(
                {
                    "index": index,
                    "slice": str(slice_path),
                    "output": str(slice_dir),
                    "chars": chars,
                    "text_paths": text_paths,
                }
            )

        merged_text = "\n\n".join(merged_parts)
        (out_dir / "result.md").write_text(merged_text, encoding="utf-8")
        meta.update(
            {
                "ok": True,
                "run_mode": f"sliced-{args.mode}",
                "used_max_length": used_max_length,
                "oom_retry_8192": oom_retry,
                "slice_count": len(slice_paths),
                "slices": slice_meta,
                "output_chars": len(merged_text),
                "text_paths": [str(out_dir / "result.md")],
            }
        )
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
