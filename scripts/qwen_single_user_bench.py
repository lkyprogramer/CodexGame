#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CODE_BLOCK = """
// File: UserService.java
package com.example.user;

import java.util.*;
import java.time.*;

public class UserService {
    private final UserRepository userRepository;
    private final AuditRepository auditRepository;

    public UserService(UserRepository userRepository, AuditRepository auditRepository) {
        this.userRepository = userRepository;
        this.auditRepository = auditRepository;
    }

    public UserDTO updateUserProfile(Long userId, UpdateUserProfileCommand command) {
        User user = userRepository.findById(userId);
        if (user == null) {
            throw new IllegalArgumentException("user not found");
        }
        if (command.getDisplayName() != null) {
            user.setDisplayName(command.getDisplayName().trim());
        }
        if (command.getEmail() != null) {
            user.setEmail(command.getEmail().trim().toLowerCase(Locale.ROOT));
        }
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);
        auditRepository.save(new AuditLog("USER_PROFILE_UPDATED", userId, Instant.now()));
        return new UserDTO(user.getId(), user.getDisplayName(), user.getEmail());
    }
}

// File: UserRepository.java
package com.example.user;

public interface UserRepository {
    User findById(Long id);
    void save(User user);
}

// File: UserController.java
package com.example.user;

public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    public UserDTO update(UpdateUserProfileCommand command) {
        return userService.updateUserProfile(command.getUserId(), command);
    }
}
""".strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def send_chat_request(base_url: str, api_key: str, payload: dict[str, Any], timeout_seconds: int) -> tuple[int, dict[str, Any], float]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers=build_headers(api_key),
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return resp.status, json.loads(raw.decode("utf-8")), elapsed_ms
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {"raw_error": raw.decode("utf-8", errors="replace")}
        return exc.code, payload, elapsed_ms
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return 0, {"exception": repr(exc)}, elapsed_ms


def get_models(base_url: str, api_key: str, timeout_seconds: int) -> dict[str, Any]:
    req = urllib.request.Request(f"{base_url.rstrip('/')}/models", headers=build_headers(api_key), method="GET")
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_repeated_context(title: str, approx_chars: int) -> str:
    parts: list[str] = [f"# Context Bundle: {title}\n"]
    while sum(len(p) for p in parts) < approx_chars:
        parts.append("\n## Module Snippet\n")
        parts.append(CODE_BLOCK)
        parts.append("\n")
    return "".join(parts)


def build_messages(prefix: str | None, task: str) -> list[dict[str, str]]:
    content = task
    if prefix:
        content = (
            "You are reviewing a coding task. Use the supplied project context carefully.\n\n"
            f"{prefix}\n\n"
            "Task:\n"
            f"{task}"
        )
    return [{"role": "user", "content": content}]


@dataclass
class Case:
    case_id: str
    family: str
    description: str
    max_tokens: int
    messages: list[dict[str, str]]
    sleep_after_seconds: int = 0


def build_cases() -> list[Case]:
    small_prefix = build_repeated_context("small", 24_000)
    medium_prefix = build_repeated_context("medium", 96_000)
    large_prefix = build_repeated_context("large", 320_000)

    shared_cache_prefix = build_repeated_context("cache-shared", 96_000)

    return [
        Case(
            case_id="smoke_math",
            family="smoke",
            description="Simple arithmetic sanity check.",
            max_tokens=256,
            messages=build_messages(None, "What is 2+2?"),
        ),
        Case(
            case_id="smoke_python_lru",
            family="smoke",
            description="Small coding task for Python.",
            max_tokens=768,
            messages=build_messages(
                None,
                "Write a compact but production-usable Python LRU cache implementation with a short explanation.",
            ),
        ),
        Case(
            case_id="smoke_java_bugfix",
            family="smoke",
            description="Small coding task for Java backend debugging.",
            max_tokens=1024,
            messages=build_messages(
                None,
                "Given a Java service that sometimes throws NullPointerException after loading an optional nested config, explain the likely root cause and give the smallest safe fix.",
            ),
        ),
        Case(
            case_id="boundary_max_tokens_8",
            family="boundary",
            description="Reasoning mode minimum token budget check.",
            max_tokens=8,
            messages=build_messages(None, "What is 2+2?"),
        ),
        Case(
            case_id="boundary_max_tokens_64",
            family="boundary",
            description="Reasoning mode small token budget check.",
            max_tokens=64,
            messages=build_messages(None, "What is 2+2?"),
        ),
        Case(
            case_id="boundary_max_tokens_128",
            family="boundary",
            description="Reasoning mode moderate token budget check.",
            max_tokens=128,
            messages=build_messages(None, "What is 2+2?"),
        ),
        Case(
            case_id="boundary_max_tokens_256",
            family="boundary",
            description="Reasoning mode safe token budget check.",
            max_tokens=256,
            messages=build_messages(None, "What is 2+2?"),
        ),
        Case(
            case_id="context_small",
            family="context",
            description="Small code context, intended to stay in low-thousands prompt tokens.",
            max_tokens=768,
            messages=build_messages(
                small_prefix,
                "Review the provided Java snippets and identify the top 3 correctness risks, then propose the smallest patch plan.",
            ),
        ),
        Case(
            case_id="context_medium",
            family="context",
            description="Medium code context, intended to simulate multi-file review.",
            max_tokens=1024,
            messages=build_messages(
                medium_prefix,
                "You are doing a precise backend code review. Find the most likely transaction and data consistency bug, explain why, and give a minimal fix plan.",
            ),
        ),
        Case(
            case_id="context_large",
            family="context",
            description="Large code context, intended to stress long-context single-user usage.",
            max_tokens=1024,
            messages=build_messages(
                large_prefix,
                "From the provided project context, identify the highest-risk bug that could cause data corruption in a production coding workflow. Explain root cause, affected flow, and the smallest safe fix.",
            ),
        ),
        Case(
            case_id="cache_round_1",
            family="cache",
            description="Shared-prefix coding request, first round.",
            max_tokens=768,
            messages=build_messages(
                shared_cache_prefix,
                "Using the shared context, find the most likely bug in the update flow and suggest a minimal code patch.",
            ),
        ),
        Case(
            case_id="cache_round_2",
            family="cache",
            description="Shared-prefix coding request, second round with same prefix.",
            max_tokens=768,
            messages=build_messages(
                shared_cache_prefix,
                "Using the same shared context, identify the most likely validation bug and suggest a minimal code patch.",
            ),
        ),
        Case(
            case_id="cache_round_3",
            family="cache",
            description="Shared-prefix coding request, third round with same prefix.",
            max_tokens=768,
            messages=build_messages(
                shared_cache_prefix,
                "Using the same shared context, identify the most likely audit log bug and suggest a minimal code patch.",
            ),
        ),
        Case(
            case_id="soak_round_1",
            family="soak",
            description="Start of sequential single-user soak test.",
            max_tokens=768,
            messages=build_messages(
                medium_prefix,
                "Explain one backend bug in the context and give a precise minimal patch outline.",
            ),
            sleep_after_seconds=5,
        ),
        Case(
            case_id="soak_round_2",
            family="soak",
            description="Sequential single-user soak test round 2.",
            max_tokens=768,
            messages=build_messages(
                medium_prefix,
                "Explain one API contract bug in the context and give a precise minimal patch outline.",
            ),
            sleep_after_seconds=5,
        ),
        Case(
            case_id="soak_round_3",
            family="soak",
            description="Sequential single-user soak test round 3.",
            max_tokens=768,
            messages=build_messages(
                medium_prefix,
                "Explain one state management bug in the context and give a precise minimal patch outline.",
            ),
            sleep_after_seconds=5,
        ),
        Case(
            case_id="soak_round_4",
            family="soak",
            description="Sequential single-user soak test round 4.",
            max_tokens=768,
            messages=build_messages(
                medium_prefix,
                "Explain one error handling bug in the context and give a precise minimal patch outline.",
            ),
            sleep_after_seconds=5,
        ),
        Case(
            case_id="soak_round_5",
            family="soak",
            description="Sequential single-user soak test round 5.",
            max_tokens=768,
            messages=build_messages(
                medium_prefix,
                "Explain one data validation bug in the context and give a precise minimal patch outline.",
            ),
        ),
    ]


def extract_result(case: Case, http_status: int, response: dict[str, Any], elapsed_ms: float) -> dict[str, Any]:
    success = http_status == 200 and "choices" in response
    message: dict[str, Any] = {}
    reasoning = ""
    content = ""
    finish_reason = ""
    usage = response.get("usage") or {}
    timings = response.get("timings") or {}
    error_message = ""

    if success:
        choice0 = response["choices"][0]
        message = choice0.get("message") or {}
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        finish_reason = choice0.get("finish_reason") or ""
    else:
        error = response.get("error")
        if isinstance(error, dict):
            error_message = error.get("message") or json.dumps(error, ensure_ascii=False)
        else:
            error_message = response.get("raw_error") or response.get("exception") or json.dumps(response, ensure_ascii=False)

    return {
        "timestamp_utc": utc_now(),
        "case_id": case.case_id,
        "family": case.family,
        "description": case.description,
        "http_status": http_status,
        "success": success,
        "max_tokens": case.max_tokens,
        "prompt_chars": len(case.messages[0]["content"]),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "finish_reason": finish_reason,
        "elapsed_ms": round(elapsed_ms, 3),
        "prompt_ms": timings.get("prompt_ms"),
        "predicted_ms": timings.get("predicted_ms"),
        "predicted_per_second": timings.get("predicted_per_second"),
        "reasoning_content_length": len(reasoning),
        "content_length": len(content),
        "reasoning_preview": reasoning[:240].replace("\n", "\\n"),
        "content_preview": content[:240].replace("\n", "\\n"),
        "error_message": error_message,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="Example: http://127.0.0.1:18343/v1")
    parser.add_argument("--api-key", default="sk-no-key-required")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "single_user_bench_results.csv"
    json_path = out_dir / "single_user_bench_results.json"
    meta_path = out_dir / "single_user_bench_meta.json"

    meta = {
        "generated_at_utc": utc_now(),
        "base_url": args.base_url,
        "model": args.model,
        "timeout_seconds": args.timeout_seconds,
    }

    try:
        meta["models_response"] = get_models(args.base_url, args.api_key, args.timeout_seconds)
    except Exception as exc:
        meta["models_error"] = repr(exc)

    rows: list[dict[str, Any]] = []
    for case in build_cases():
        payload = {
            "model": args.model,
            "messages": case.messages,
            "max_tokens": case.max_tokens,
        }
        status, response, elapsed_ms = send_chat_request(args.base_url, args.api_key, payload, args.timeout_seconds)
        row = extract_result(case, status, response, elapsed_ms)
        rows.append(row)
        print(
            f"[{case.case_id}] status={row['http_status']} success={row['success']} "
            f"prompt_tokens={row['prompt_tokens']} total_ms={row['elapsed_ms']}",
            flush=True,
        )
        if case.sleep_after_seconds > 0:
            time.sleep(case.sleep_after_seconds)

    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Wrote CSV: {csv_path}")
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote META: {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
