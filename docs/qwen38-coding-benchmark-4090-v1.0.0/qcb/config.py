from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


@dataclass(frozen=True)
class ModelConfig:
    id: str
    file: str
    sha256: str
    family: str = "Qwen3.8-27B"
    quantization: str = "unknown"
    template_id: str = "embedded"
    notes: str = ""


@dataclass(frozen=True)
class EndpointConfig:
    base_url: str
    model: str
    api_key: str = "not-needed"
    timeout_seconds: float = 900.0


@dataclass(frozen=True)
class InferenceConfig:
    lane: str
    temperature: float
    top_p: float
    top_k: int
    min_p: float
    seed: int
    max_tokens: int
    context_size: int
    reasoning_effort: str
    mtp_enabled: bool
    tool_mode: bool
    max_tool_calls: int
    max_retries: int
    system_prompt_file: str
    extra_body: dict[str, Any]


@dataclass(frozen=True)
class RunConfig:
    model: ModelConfig
    endpoint: EndpointConfig
    inference: InferenceConfig
    source_path: Path


def _require(section: dict[str, Any], key: str, kind: type) -> Any:
    value = section.get(key)
    if not isinstance(value, kind):
        raise ValueError(f"Missing or invalid config value: {key}")
    return value


def load_config(path: str | Path) -> RunConfig:
    source = Path(path).resolve()
    with source.open("rb") as handle:
        data = tomllib.load(handle)

    m = data.get("model", {})
    e = data.get("endpoint", {})
    i = data.get("inference", {})

    model = ModelConfig(
        id=_require(m, "id", str),
        file=str(m.get("file", "")),
        sha256=str(m.get("sha256", "")),
        family=str(m.get("family", "Qwen3.8-27B")),
        quantization=str(m.get("quantization", "unknown")),
        template_id=str(m.get("template_id", "embedded")),
        notes=str(m.get("notes", "")),
    )
    endpoint = EndpointConfig(
        base_url=_require(e, "base_url", str).rstrip("/"),
        model=_require(e, "model", str),
        api_key=str(e.get("api_key", "not-needed")),
        timeout_seconds=float(e.get("timeout_seconds", 900)),
    )
    inference = InferenceConfig(
        lane=str(i.get("lane", "normalized")),
        temperature=float(i.get("temperature", 0.0)),
        top_p=float(i.get("top_p", 1.0)),
        top_k=int(i.get("top_k", 0)),
        min_p=float(i.get("min_p", 0.0)),
        seed=int(i.get("seed", 42)),
        max_tokens=int(i.get("max_tokens", 8192)),
        context_size=int(i.get("context_size", 32768)),
        reasoning_effort=str(i.get("reasoning_effort", "medium")),
        mtp_enabled=bool(i.get("mtp_enabled", False)),
        tool_mode=bool(i.get("tool_mode", True)),
        max_tool_calls=int(i.get("max_tool_calls", 40)),
        max_retries=int(i.get("max_retries", 1)),
        system_prompt_file=str(i.get("system_prompt_file", "config/system-prompt.txt")),
        extra_body=dict(i.get("extra_body", {})),
    )
    if inference.lane not in {"normalized", "optimized"}:
        raise ValueError("inference.lane must be 'normalized' or 'optimized'")
    if not 0.0 <= inference.top_p <= 1.0:
        raise ValueError("top_p must be between 0 and 1")
    if not 0.0 <= inference.min_p <= 1.0:
        raise ValueError("min_p must be between 0 and 1")
    if inference.temperature < 0.0:
        raise ValueError("temperature must be non-negative")
    if inference.top_k < 0:
        raise ValueError("top_k must be non-negative")
    if inference.max_tokens <= 0 or inference.context_size <= 0:
        raise ValueError("max_tokens and context_size must be positive")
    if inference.max_tool_calls < 0 or inference.max_retries < 0:
        raise ValueError("max_tool_calls and max_retries must be non-negative")
    if endpoint.timeout_seconds <= 0:
        raise ValueError("endpoint.timeout_seconds must be positive")
    if inference.lane == "normalized" and inference.mtp_enabled:
        raise ValueError("Normalized lane requires mtp_enabled=false")
    if not inference.tool_mode:
        raise ValueError("Standard QCB suites require tool_mode=true; use build_context_bundle.py for nonstandard inline diagnostics")
    reserved = {
        "model", "messages", "tools", "tool_choice", "temperature", "top_p",
        "top_k", "min_p", "max_tokens", "seed", "stream", "reasoning_effort",
    }
    conflicts = sorted(reserved & set(inference.extra_body))
    if conflicts:
        raise ValueError(f"extra_body cannot override controlled request fields: {conflicts}")
    return RunConfig(model=model, endpoint=endpoint, inference=inference, source_path=source)
