"""Prove MiniCPM image processor overrides via real /tokenize; no generation.

Run in the candidate container's Python environment, against its idle service.
PASS establishes differential preprocessing, not OCR quality or generation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ocrbench.client import VLLMClient, atomic_json
from probe_runtime import _shared_payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def software_identity() -> dict:
    result = {}
    files = {
        "vllm": "vllm/model_executor/models/minicpmv4_6.py",
        "transformers": "transformers/models/minicpmv4_6/processing_minicpmv4_6.py",
        "torch": None,
    }
    for name, relative in files.items():
        try:
            distribution = importlib.metadata.distribution(name)
            record = {"version": distribution.version}
            direct_url = distribution.read_text("direct_url.json")
            if direct_url:
                # Keep source identity only; do not retain repository credentials.
                record["vcs_info"] = json.loads(direct_url).get("vcs_info")
            if relative:
                # Editable metadata lives in site-packages while its package
                # can live in a checkout. Resolve only the top-level spec;
                # finding a dotted submodule would execute package imports.
                spec = importlib.util.find_spec(name)
                origin = spec.origin if spec is not None else None
                source = (Path(origin).resolve().parent / Path(relative).relative_to(name)
                          if origin else None)
                record["package_spec_origin"] = origin
                record["processor_source"] = str(source) if source else None
                record["processor_source_sha256"] = sha256(source) if source and source.is_file() else None
            result[name] = record
        except importlib.metadata.PackageNotFoundError:
            result[name] = {"status": "UNAVAILABLE"}
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18499/v1")
    parser.add_argument("--model", default="minicpm-ocr")
    parser.add_argument("--model-dir", type=Path, default=Path("/models/MiniCPM-OCR-1.0"))
    parser.add_argument("--image", type=Path, required=True,
                        help="One large development image; small images cannot prove slicing")
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New evidence directory")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    # Fail before touching the output if inputs are absent or malformed.
    image_hash = sha256(args.image)
    lock = json.loads(args.source_lock.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "UNVERIFIED", "claim": "Differential multimodal tokenization only; no generation or quality claim",
        "image": {"path": str(args.image.resolve()), "sha256": image_hash},
        "base_url": args.base_url, "model": args.model, "prompt": "Text Recognition:",
        "expected_server_kwargs": {"downsample_mode": "4x", "max_slice_nums": 9},
        "source_lock_sha256": sha256(args.source_lock),
        "expected_sources": {key: lock.get(key) for key in ("vllm", "transformers")},
        "software": software_identity(), "variants": {}, "checks": {},
        "model_metadata_sha256": {
            name: sha256(args.model_dir / name) if (args.model_dir / name).is_file() else None
            for name in ("config.json", "preprocessor_config.json", "processor_config.json", "tokenizer_config.json")
        },
    }
    client = VLLMClient(args.base_url, args.model)
    variants = {
        "server_default": None,
        "explicit_4x_slice9": {"downsample_mode": "4x", "max_slice_nums": 9},
        "explicit_16x_slice9": {"downsample_mode": "16x", "max_slice_nums": 9},
        "explicit_4x_slice1": {"downsample_mode": "4x", "max_slice_nums": 1},
    }
    token_sequences = {}
    try:
        for name, kwargs in variants.items():
            payload = _shared_payload(args.image, report["prompt"], args.model)
            if kwargs is not None:
                payload["mm_processor_kwargs"] = kwargs
            started = time.monotonic()
            response = client._post("tokenize", payload, started + args.timeout, args.out / name)
            count, tokens = response.get("count"), response.get("tokens")
            if (type(count) is not int or count <= 0 or not isinstance(tokens, list)
                    or len(tokens) != count or any(type(token) is not int for token in tokens)
                    or response.get("max_model_len") != 16384):
                raise ValueError(f"{name}: inconsistent tokens/count or max_model_len is not 16384")
            token_sequences[name] = tokens
            report["variants"][name] = {
                "request_mm_processor_kwargs": kwargs, "prompt_token_count": count,
                "max_model_len": response["max_model_len"], "wall_seconds": time.monotonic() - started,
                "request_sha256": sha256(args.out / (name + ".request.json")),
                "token_ids_sha256": hashlib.sha256(json.dumps(tokens).encode()).hexdigest(),
            }
        counts = {key: value["prompt_token_count"] for key, value in report["variants"].items()}
        report["checks"] = {
            "server_default_matches_explicit_4x_slice9": token_sequences["server_default"] == token_sequences["explicit_4x_slice9"],
            "4x_has_more_tokens_than_16x_same_slices": counts["explicit_4x_slice9"] > counts["explicit_16x_slice9"],
            "slice9_has_more_tokens_than_slice1_same_4x": counts["explicit_4x_slice9"] > counts["explicit_4x_slice1"],
        }
        report["status"] = "PASS" if all(report["checks"].values()) else "UNVERIFIED"
        if report["status"] != "PASS":
            report["reason"] = "Override effect/default not proven; inspect raw requests/responses and image size. No full420 admission."
    except Exception as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
    atomic_json(args.out / "report.json", report)
    print(json.dumps({"status": report["status"], "checks": report["checks"],
                      "counts": {key: value["prompt_token_count"] for key, value in report["variants"].items()},
                      "report": str(args.out / "report.json")}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
