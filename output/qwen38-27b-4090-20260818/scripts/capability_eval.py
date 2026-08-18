#!/usr/bin/env python3
"""Full capability eval for production Qwen3.8-27B-WORK on :18343."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

BASE = os.environ.get("QWEN38_BASE", "http://127.0.0.1:18343")
MODEL = os.environ.get("QWEN38_MODEL", "openclaw/Qwen3.8-27B-WORK")
ROOT = Path(os.environ.get("CAP_ROOT", "/home/hhtele/qwen38-27b-4090-20260818/capability"))
THINK = {"enable_thinking": True, "reasoning_effort": "medium", "preserve_thinking": False}
LOW = {"enable_thinking": True, "reasoning_effort": "low", "preserve_thinking": False}
XHIGH = {"enable_thinking": True, "reasoning_effort": "xhigh", "preserve_thinking": False}
OFF = {"enable_thinking": False, "reasoning_effort": "low", "preserve_thinking": False}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"error_text": body}
        return exc.code, parsed


def chat(
    messages: list[dict[str, Any]],
    *,
    max_tokens: int = 8192,
    kwargs: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: Any = None,
    temperature: float = 1.0,
    top_p: float = 0.95,
    timeout: int = 900,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": 20,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": kwargs or THINK,
    }
    if tools is not None:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice if tool_choice is not None else "auto"
    if extra:
        payload.update(extra)
    t0 = time.perf_counter()
    status, body = post_json(f"{BASE}/v1/chat/completions", payload, timeout)
    elapsed = time.perf_counter() - t0
    msg = ((body.get("choices") or [{}])[0].get("message") or {})
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    usage = body.get("usage") or {}
    return {
        "http": status,
        "elapsed": elapsed,
        "content": content,
        "reasoning": reasoning,
        "empty": status == 200 and not str(content).strip() and not msg.get("tool_calls"),
        "finish": ((body.get("choices") or [{}])[0].get("finish_reason")),
        "completion": usage.get("completion_tokens"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "tool_calls": msg.get("tool_calls") or [],
        "raw": body,
        "request": {k: v for k, v in payload.items() if k != "messages"} | {"n_messages": len(messages)},
    }


def parse_json(text: str) -> Any:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json|python|javascript|ts|js)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}|\[.*\]", raw, flags=re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None


def extract_code(text: str) -> str:
    raw = text or ""
    blocks = re.findall(r"```(?:python|py|javascript|js)?\s*([\s\S]*?)```", raw)
    if blocks:
        return max(blocks, key=len).strip()
    parsed = parse_json(raw)
    if isinstance(parsed, dict) and isinstance(parsed.get("code"), str):
        return parsed["code"]
    return raw.strip()


def save_case(suite: str, case_id: str, rec: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    row = {
        "id": case_id,
        "suite": suite,
        "pass": extra.get("pass"),
        "detail": extra.get("detail"),
        "empty": rec.get("empty"),
        "elapsed": rec.get("elapsed"),
        "completion": rec.get("completion"),
        "prompt_tokens": rec.get("prompt_tokens"),
        "finish": rec.get("finish"),
        "http": rec.get("http"),
        "content_len": len(rec.get("content") or ""),
        "reason_len": len(rec.get("reasoning") or ""),
    }
    out = ROOT / "raw" / suite / case_id
    write_json(out / "result.json", {**row, "content": rec.get("content"), "reasoning_head": (rec.get("reasoning") or "")[:1500], **extra})
    return row


def finish_suite(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for r in rows if r.get("pass"))
    summary = {"suite": name, "passed": passed, "total": len(rows), "rate": passed / len(rows) if rows else 0, "rows": rows, "finished": now()}
    write_json(ROOT / "results" / f"{name}.json", summary)
    print(f"SUITE {name} {passed}/{len(rows)}", flush=True)
    return summary


# ---------------------------------------------------------------------------
# T4 instruction following
# ---------------------------------------------------------------------------

def run_t4() -> dict[str, Any]:
    rows = []
    cases: list[dict[str, Any]] = []

    # 50 IFEval-style programmatic constraints
    for i in range(1, 11):
        n = 3 + (i % 4)
        cases.append({
            "id": f"ifeval_bullets_{i}",
            "prompt": f"List exactly {n} benefits of using a write-ahead log. Use a numbered list 1..{n}. No intro, no outro.",
            "check": lambda text, n=n: len(re.findall(r"^\s*\d+[\.\)]", text, re.M)) == n,
        })
    for i in range(1, 9):
        word = ["banana", "kangaroo", "isotope", "velvet"][i % 4]
        cases.append({
            "id": f"ifeval_forbid_{i}",
            "prompt": f"Explain two-phase commit in at most 60 words. Do not use the word '{word}'.",
            "check": lambda text, word=word: word.lower() not in text.lower() and 1 <= len(text.split()) <= 80,
        })
    for i in range(1, 9):
        cases.append({
            "id": f"ifeval_lang_{i}",
            "prompt": "用简体中文回答：什么是幻读？不超过三句话。整段回答必须是中文，不要英文单词。",
            "check": lambda text: bool(re.search(r"[\u4e00-\u9fff]", text)) and len(re.findall(r"[A-Za-z]{4,}", text)) <= 1,
        })
    for i in range(1, 9):
        cases.append({
            "id": f"ifeval_json_{i}",
            "prompt": 'Return JSON only with exactly keys "ok" (boolean true) and "n" (integer). n must be ' + str(i) + ". No markdown.",
            "check": lambda text, i=i: (lambda p: isinstance(p, dict) and set(p.keys()) == {"ok", "n"} and p.get("ok") is True and p.get("n") == i)(parse_json(text)),
        })
    for i in range(1, 8):
        cases.append({
            "id": f"ifeval_wrap_{i}",
            "prompt": f"Wrap the word READY in double square brackets like [[READY]]. Then stop. Attempt {i}.",
            "check": lambda text: "[[READY]]" in text and text.count("[") <= 4,
        })
    for i in range(1, 8):
        cases.append({
            "id": f"ifeval_end_{i}",
            "prompt": "Write one sentence about TCP. End the entire reply with the exact token END-OF-ANSWER.",
            "check": lambda text: text.rstrip().endswith("END-OF-ANSWER"),
        })

    # 20 harder custom
    hard = [
        ("hard_title_20", "先用不超过20个汉字给出结论，换行后再写证据。结论行不得包含标点以外的英文。问题：InnoDB RR 会不会彻底避免幻读？",
         lambda t: bool(re.match(r"^[\u4e00-\u9fff]{1,20}", t.splitlines()[0] if t else "")) and len(t.splitlines()[0]) <= 24),
        ("hard_url", "Give one official Postgres docs URL about isolation levels. The reply must contain https://www.postgresql.org/ and nothing else except one sentence.",
         lambda t: "https://www.postgresql.org/" in t and t.count("http") == 1),
        ("hard_no_cmd", "Describe how to rotate WAL files. Do not include any shell command, slash-starting path, or the tokens rm, sudo, chmod.",
         lambda t: not re.search(r"\b(rm|sudo|chmod)\b|/`|/` ", t) and "/" not in t.split()[0] if t else False),
        ("hard_schema", 'Return JSON only matching {"svc":string,"port":number,"tags":[string,string]}. svc=api port=8080 tags=["a","b"]. No extra keys.',
         lambda t: (lambda p: isinstance(p, dict) and set(p)=={"svc","port","tags"} and p["port"]==8080 and p["tags"]==["a","b"])(parse_json(t))),
        ("hard_sort_unique", "Output the unique sorted integers from 3,1,3,2,2 as a comma-separated list with no spaces.",
         lambda t: re.sub(r"\s", "", t) == "1,2,3" or "1,2,3" in re.sub(r"\s", "", t)),
        ("hard_zh_then_en", "第一行只用中文写“通过”。第二行只用英文写 PASSED。不要第三行。",
         lambda t: [x.strip() for x in t.strip().splitlines() if x.strip()][:2] == ["通过", "PASSED"]),
        ("hard_count_words", "Reply with exactly six English words about indexes.",
         lambda t: len(re.findall(r"[A-Za-z]+", t)) == 6),
        ("hard_quoted", 'Put the entire answer inside double quotes. Answer: isolation.',
         lambda t: t.strip().startswith('"') and t.strip().endswith('"') and "isolation" in t.lower()),
        ("hard_no_digit", "Explain checksums without using any digit 0-9.",
         lambda t: not re.search(r"\d", t)),
        ("hard_csv_header", "Output a 2-line CSV. Header must be name,role. Second line must be alice,dba. Nothing else.",
         lambda t: [x.strip() for x in t.strip().splitlines() if x.strip()][:2] == ["name,role", "alice,dba"]),
        ("hard_repeat_3", "Write the token PING exactly three times separated by single spaces and nothing else.",
         lambda t: t.strip() == "PING PING PING"),
        ("hard_lower", "Answer in all lowercase: Why use connection pooling? One sentence.",
         lambda t: t == t.lower() and "?" not in t or t == t.lower()),
        ("hard_bullet_dash", "Give exactly two items about WAL, each line starting with '- '.",
         lambda t: sum(1 for line in t.splitlines() if line.startswith("- ")) == 2),
        ("hard_no_markdown", "Explain MVCC in 2 sentences. Do not use *, `, # or [].",
         lambda t: not any(ch in t for ch in "*`#[]")),
        ("hard_first_last", "Start with BEGIN and end with STOP. Between them write one English word: READY.",
         lambda t: t.strip().startswith("BEGIN") and t.strip().endswith("STOP") and "READY" in t),
        ("hard_json_array", "Return a JSON array of three integers: 2,3,5. No object wrapper.",
         lambda t: parse_json(t) == [2, 3, 5]),
        ("hard_exclude_because", "State one risk of SELECT FOR UPDATE. Do not use the word because.",
         lambda t: "because" not in t.lower()),
        ("hard_two_langs", "Line1 English: Isolation matters. Line2 中文：隔离级别重要。Only those two lines.",
         lambda t: [x.strip() for x in t.strip().splitlines() if x.strip()][:2] == ["Isolation matters.", "隔离级别重要。"]),
        ("hard_hex", "Output the hex of ASCII A as 0x41 only.",
         lambda t: "0x41" in t and len(t.strip()) <= 8),
        ("hard_no_i", "Describe locks without using the letter i or I.",
         lambda t: "i" not in t.lower()),
    ]
    for cid, prompt, check in hard:
        cases.append({"id": cid, "prompt": prompt, "check": check})

    for case in cases:
        rec = chat([{"role": "user", "content": case["prompt"]}], max_tokens=512, kwargs=THINK)
        try:
            ok = bool(case["check"](rec.get("content") or "")) and not rec.get("empty")
            detail = "ok" if ok else (rec.get("content") or "")[:120]
        except Exception as exc:
            ok, detail = False, repr(exc)
        rows.append(save_case("t4", case["id"], rec, {"pass": ok, "detail": detail}))
    return finish_suite("t4", rows)


# ---------------------------------------------------------------------------
# T6 tools
# ---------------------------------------------------------------------------

TOOLS = [
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "list_dir", "description": "List a directory",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "run_check", "description": "Run a named read-only check",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "lookup_metric", "description": "Lookup a metric",
        "parameters": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
    }},
]


def _fn(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    fn = call.get("function") or {}
    name = fn.get("name") or ""
    try:
        args = json.loads(fn.get("arguments") or "{}")
    except Exception:
        args = {}
    return name, args if isinstance(args, dict) else {}


def run_t6() -> dict[str, Any]:
    rows = []
    singles = [
        ("read_config", "Call read_file on apps/game-runtime/src/runtime/config.ts now.", "read_file", "config.ts"),
        ("read_actions", "Use the read_file tool for packages/protocol/src/actions.ts", "read_file", "actions.ts"),
        ("list_runtime", "List directory apps/game-runtime/src/runtime with list_dir.", "list_dir", "runtime"),
        ("metric_tick", "Lookup metric tick_ms via lookup_metric.", "lookup_metric", "tick"),
        ("check_health", "Run the health check using run_check name=health.", "run_check", "health"),
        ("read_sim", "Read packages/simulation/src/simulation.ts with the tool.", "read_file", "simulation.ts"),
        ("list_protocol", "list_dir packages/protocol/src", "list_dir", "protocol"),
        ("metric_sched", "lookup_metric key=scheduler_ms", "lookup_metric", "scheduler"),
        ("check_lint", "run_check name=lint", "run_check", "lint"),
        ("read_store", "read_file path=apps/game-runtime/src/runtime/contentStore.ts", "read_file", "contentStore"),
    ]
    for cid, prompt, expect_name, needle in singles:
        rec = chat([{"role": "user", "content": prompt}], max_tokens=1024, kwargs=THINK, tools=TOOLS)
        names = [_fn(c)[0] for c in rec.get("tool_calls") or []]
        blob = json.dumps(rec.get("tool_calls") or [])
        ok = expect_name in names and needle.lower() in blob.lower()
        rows.append(save_case("t6", f"single_{cid}", rec, {"pass": ok, "detail": names}))

    # sequential implied
    rec = chat([{"role": "user", "content": "First list_dir apps/game-runtime then read_file its package.json. You may call tools now."}],
               max_tokens=1024, kwargs=THINK, tools=TOOLS)
    names = [_fn(c)[0] for c in rec.get("tool_calls") or []]
    ok = "list_dir" in names or "read_file" in names
    rows.append(save_case("t6", "seq_list_then_read", rec, {"pass": ok, "detail": names}))

    for i, prompt in enumerate([
        "Call both list_dir on packages/protocol and lookup_metric key=tick_ms in this turn.",
        "In one response call read_file on README.md and run_check name=typecheck.",
        "Invoke list_dir apps and list_dir packages together.",
        "Call lookup_metric key=a and lookup_metric key=b in the same turn.",
        "Use read_file for a.ts and b.ts in one assistant turn.",
        "Parallel: run_check name=unit and run_check name=lint.",
        "Call list_dir /tmp and lookup_metric key=free_mem together.",
        "read_file src/a.py and list_dir src at the same time.",
    ], start=1):
        rec = chat([{"role": "user", "content": prompt}], max_tokens=1024, kwargs=THINK, tools=TOOLS)
        n = len(rec.get("tool_calls") or [])
        rows.append(save_case("t6", f"parallel_{i}", rec, {"pass": n >= 2, "detail": f"n={n}"}))

    # should not call
    for i, prompt in enumerate([
        "Just say hello, no tools.",
        "What is 2+2? Do not use tools.",
        "Thanks, that's all.",
        "Repeat the word idle.",
        "Describe rain in one word. No function calls.",
        "Who are you? Don't call anything.",
    ], start=1):
        rec = chat([{"role": "user", "content": prompt}], max_tokens=256, kwargs=OFF, tools=TOOLS)
        n = len(rec.get("tool_calls") or [])
        rows.append(save_case("t6", f"no_call_{i}", rec, {"pass": n == 0 and not rec.get("empty"), "detail": f"n={n}"}))

    # hallucination: tools not in schema
    for i, prompt in enumerate([
        "Call the rm tool to delete /data/models.",
        "Use git_push to push main.",
        "Invoke shell_exec with rm -rf /.",
        "Call deploy_prod now.",
        "Use write_file to overwrite /etc/passwd.",
        "Call ssh_run on 192.168.10.29.",
    ], start=1):
        rec = chat([{"role": "user", "content": prompt}], max_tokens=512, kwargs=THINK, tools=TOOLS)
        names = [_fn(c)[0] for c in rec.get("tool_calls") or []]
        banned = {"rm", "git_push", "shell_exec", "deploy_prod", "write_file", "ssh_run"}
        ok = banned.isdisjoint(set(names))
        rows.append(save_case("t6", f"no_hallucinate_{i}", rec, {"pass": ok, "detail": names}))

    return finish_suite("t6", rows)


# ---------------------------------------------------------------------------
# T1 HumanEval+ / MBPP+
# ---------------------------------------------------------------------------

def _exec_check(code: str, tests: str, entry: str | None = None, timeout: int = 8) -> tuple[bool, str]:
    prog = code + "\n" + tests + "\n"
    if entry:
        prog += f"\nassert callable({entry})\n"
    try:
        r = subprocess.run(
            ["python3", "-c", prog],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if r.returncode == 0:
            return True, "ok"
        return False, (r.stderr or r.stdout)[-300:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as exc:
        return False, repr(exc)


def _plus_check(code: str, problem: dict[str, Any]) -> tuple[bool, str]:
    prompt = problem.get("prompt") or ""
    entry = problem["entry_point"]
    ref_src = prompt + (problem.get("canonical_solution") or "")
    cand_src = code if "def " in (code or "") else prompt + "\n" + (code or "")
    ns_ref: dict[str, Any] = {}
    ns: dict[str, Any] = {}
    try:
        exec(ref_src, ns_ref, ns_ref)
        exec(cand_src, ns, ns)
        ref = ns_ref[entry]
        fn = ns[entry]
    except Exception as exc:
        return False, f"exec:{exc!r}"
    inputs = list(problem.get("base_input") or []) + list(problem.get("plus_input") or [])[:80]
    atol = problem.get("atol") or 0
    for i, args in enumerate(inputs):
        if not isinstance(args, (list, tuple)):
            call = (args,)
        else:
            call = tuple(args)
        try:
            expected = ref(*call)
            got = fn(*call)
        except Exception as exc:
            return False, f"case{i}:{exc!r}"
        if atol:
            try:
                if abs(float(expected) - float(got)) > float(atol):
                    return False, f"case{i}: {got!r} != {expected!r}"
                continue
            except Exception:
                pass
        if expected != got:
            return False, f"case{i}: {got!r} != {expected!r}"
    extra = problem.get("test") or problem.get("assertion") or ""
    if extra:
        ok, detail = _exec_check(cand_src, extra, entry)
        if not ok:
            return False, detail
    return True, f"ok n={len(inputs)}"


def run_t1() -> dict[str, Any]:
    from evalplus.data import get_human_eval_plus, get_mbpp_plus

    rows = []
    he = get_human_eval_plus()
    mb = get_mbpp_plus()
    he_ids = [f"HumanEval/{i}" for i in range(0, 164, 4)]
    mb_ids = list(mb.keys())[::4][:40]

    def one(tag: str, pid: str, problem: dict[str, Any], prompt: str) -> None:
        rec = chat(
            [{"role": "system", "content": "Complete the function. Return only Python code."},
             {"role": "user", "content": prompt}],
            max_tokens=2048, kwargs=THINK,
        )
        code = extract_code(rec.get("content") or "")
        ok, detail = _plus_check(code, problem)
        row = save_case("t1", f"{tag}_{pid.replace('/', '_')}_p1", rec, {"pass": bool(ok) and not rec.get("empty"), "detail": detail, "attempt": 1})
        if not row["pass"]:
            rec2 = chat(
                [{"role": "system", "content": "Complete the function. Return only Python code."},
                 {"role": "user", "content": prompt + "\nThe previous attempt failed hidden tests. Try again."}],
                max_tokens=2048, kwargs=THINK,
            )
            ok2, d2 = _plus_check(extract_code(rec2.get("content") or ""), problem)
            row2 = save_case("t1", f"{tag}_{pid.replace('/', '_')}_p2", rec2, {"pass": bool(ok2) and not rec2.get("empty"), "detail": d2, "attempt": 2})
            rows.append({**row, "pass@2": row2["pass"]})
            rows.append(row2)
        else:
            rows.append({**row, "pass@2": True})

    for pid in he_ids:
        one("he", pid, he[pid], he[pid]["prompt"])
    for pid in mb_ids:
        p = mb[pid]
        one("mb", str(pid), p, p.get("prompt") or "")
    return finish_suite("t1", rows)


# ---------------------------------------------------------------------------
# T2 original contest problems (40)
# ---------------------------------------------------------------------------

def t2_problems() -> list[dict[str, Any]]:
    items = []

    def add(pid: str, prompt: str, tests: str, fn: str) -> None:
        items.append({"id": pid, "prompt": prompt, "tests": tests, "fn": fn})

    add("two_sum_sorted",
        "Write two_sum_sorted(nums, target) -> list[int]. nums is sorted ascending. Return 1-based indices of two numbers that add to target. Exactly one solution. O(n).",
        "assert two_sum_sorted([2,7,11,15],9)==[1,2]\nassert two_sum_sorted([2,3,4],6)==[1,3]\nassert two_sum_sorted([-1,0],-1)==[1,2]\n",
        "two_sum_sorted")
    add("longest_unique",
        "longest_unique(s) return length of longest substring without repeating characters.",
        "assert longest_unique('abcabcbb')==3\nassert longest_unique('bbbbb')==1\nassert longest_unique('pwwkew')==3\nassert longest_unique('')==0\n",
        "longest_unique")
    add("valid_paren",
        "valid_paren(s) True iff brackets ()[]{} are valid.",
        "assert valid_paren('()')\nassert valid_paren('()[]{}')\nassert not valid_paren('(]')\nassert not valid_paren('([)]')\nassert valid_paren('{[]}')\n",
        "valid_paren")
    add("merge_intervals",
        "merge_intervals(intervals) merge overlapping [s,e] intervals, return sorted merged.",
        "assert merge_intervals([[1,3],[2,6],[8,10],[15,18]])==[[1,6],[8,10],[15,18]]\nassert merge_intervals([[1,4],[4,5]])==[[1,5]]\n",
        "merge_intervals")
    add("rotate_k",
        "rotate_k(nums, k) rotate list right by k in-place and also return it.",
        "a=[1,2,3,4,5,6,7]; rotate_k(a,3); assert a==[5,6,7,1,2,3,4]\n",
        "rotate_k")
    add("product_except",
        "product_except_self(nums) return array where ans[i] is product of all except nums[i]. O(n) no div.",
        "assert product_except_self([1,2,3,4])==[24,12,8,6]\nassert product_except_self([-1,1,0,-3,3])[2]==0\n",
        "product_except_self")
    add("max_subarray",
        "max_subarray(nums) kadane maximum subarray sum.",
        "assert max_subarray([-2,1,-3,4,-1,2,1,-5,4])==6\nassert max_subarray([1])==1\nassert max_subarray([5,4,-1,7,8])==23\n",
        "max_subarray")
    add("climb",
        "climb_stairs(n) number of ways to climb n stairs 1 or 2.",
        "assert climb_stairs(2)==2\nassert climb_stairs(3)==3\nassert climb_stairs(5)==8\n",
        "climb_stairs")
    add("coin_change",
        "coin_change(coins, amount) fewest coins or -1.",
        "assert coin_change([1,2,5],11)==3\nassert coin_change([2],3)==-1\nassert coin_change([1],0)==0\n",
        "coin_change")
    add("lis",
        "lis_length(nums) longest increasing subsequence length O(n log n) or O(n^2).",
        "assert lis_length([10,9,2,5,3,7,101,18])==4\nassert lis_length([0,1,0,3,2,3])==4\n",
        "lis_length")
    add("unique_paths",
        "unique_paths(m,n) robot top-left to bottom-right only right/down.",
        "assert unique_paths(3,7)==28\nassert unique_paths(3,2)==3\n",
        "unique_paths")
    add("edit_distance",
        "edit_distance(a,b) levenshtein.",
        "assert edit_distance('horse','ros')==3\nassert edit_distance('intention','execution')==5\nassert edit_distance('','a')==1\n",
        "edit_distance")
    add("word_break",
        "word_break(s, wordDict) True if s can be segmented.",
        "assert word_break('leetcode',['leet','code'])\nassert word_break('applepenapple',['apple','pen'])\nassert not word_break('catsandog',['cats','dog','sand','and','cat'])\n",
        "word_break")
    add("can_jump",
        "can_jump(nums) True if can reach last index from 0, nums[i] is max jump.",
        "assert can_jump([2,3,1,1,4])\nassert not can_jump([3,2,1,0,4])\nassert can_jump([0])\n",
        "can_jump")
    add("trap_rain",
        "trap_rain(height) trapped rain water.",
        "assert trap_rain([0,1,0,2,1,0,1,3,2,1,2,1])==6\nassert trap_rain([4,2,0,3,2,5])==9\n",
        "trap_rain")
    add("daily_temp",
        "daily_temperatures(t) wait days until warmer, 0 if none.",
        "assert daily_temperatures([73,74,75,71,69,72,76,73])==[1,1,4,2,1,1,0,0]\n",
        "daily_temperatures")
    add("next_greater",
        "next_greater_elements(nums) circular next greater, -1 if none.",
        "assert next_greater_elements([1,2,1])==[2,-1,2]\n",
        "next_greater_elements")
    add("min_window",
        "min_window(s,t) smallest window of s covering all chars of t, or ''.",
        "w=min_window('ADOBECODEBANC','ABC'); assert w=='BANC'\nassert min_window('a','a')=='a'\nassert min_window('a','aa')==''\n",
        "min_window")
    add("group_anagrams_n",
        "group_anagrams_count(strs) return number of anagram groups.",
        "assert group_anagrams_count(['eat','tea','tan','ate','nat','bat'])==3\n",
        "group_anagrams_count")
    add("top_k_freq",
        "top_k_frequent(nums,k) k most frequent numbers, any order.",
        "r=set(top_k_frequent([1,1,1,2,2,3],2)); assert r=={1,2}\n",
        "top_k_frequent")
    add("kth_largest",
        "find_kth_largest(nums,k) kth largest.",
        "assert find_kth_largest([3,2,1,5,6,4],2)==5\nassert find_kth_largest([3,2,3,1,2,4,5,5,6],4)==4\n",
        "find_kth_largest")
    add("median_two",
        "find_median_sorted(a,b) median of two sorted arrays.",
        "assert abs(find_median_sorted([1,3],[2])-2)<1e-6\nassert abs(find_median_sorted([1,2],[3,4])-2.5)<1e-6\n",
        "find_median_sorted")
    add("reverse_k_group_len",
        "Just implement reverse_words(s) reverse word order, strip extra spaces.",
        "assert reverse_words('  hello world  ')=='world hello'\nassert reverse_words('a good   example')=='example good a'\n",
        "reverse_words")
    add("is_anagram",
        "is_anagram(s,t).",
        "assert is_anagram('anagram','nagaram')\nassert not is_anagram('rat','car')\n",
        "is_anagram")
    add("first_uniq",
        "first_uniq_char(s) index of first unique char or -1.",
        "assert first_uniq_char('leetcode')==0\nassert first_uniq_char('loveleetcode')==2\nassert first_uniq_char('aabb')==-1\n",
        "first_uniq_char")
    add("my_atoi",
        "my_atoi(s) implement atoi with 32-bit clamp.",
        "assert my_atoi('42')==42\nassert my_atoi('   -42')==-42\nassert my_atoi('4193 with words')==4193\n",
        "my_atoi")
    add("spiral",
        "spiral_order(matrix) return spiral list.",
        "assert spiral_order([[1,2,3],[4,5,6],[7,8,9]])==[1,2,3,6,9,8,7,4,5]\n",
        "spiral_order")
    add("set_zeroes_count",
        "zero_matrix_inplace(m) set row/col zero if any zero. return m.",
        "m=[[1,1,1],[1,0,1],[1,1,1]]; zero_matrix_inplace(m); assert m==[[1,0,1],[0,0,0],[1,0,1]]\n",
        "zero_matrix_inplace")
    add("search_rotated",
        "search_rotated(nums,target) index or -1, rotated sorted unique.",
        "assert search_rotated([4,5,6,7,0,1,2],0)==4\nassert search_rotated([4,5,6,7,0,1,2],3)==-1\n",
        "search_rotated")
    add("find_min_rot",
        "find_min_rotated(nums) min in rotated sorted unique.",
        "assert find_min_rotated([3,4,5,1,2])==1\nassert find_min_rotated([4,5,6,7,0,1,2])==0\n",
        "find_min_rotated")
    add("oranges",
        "oranges_rotting(grid) minutes to rot all, -1 if impossible. 2=rotten 1=fresh 0=empty. 4-dir.",
        "assert oranges_rotting([[2,1,1],[1,1,0],[0,1,1]])==4\nassert oranges_rotting([[2,1,1],[0,1,1],[1,0,1]])==-1\n",
        "oranges_rotting")
    add("num_islands",
        "num_islands(grid) of '1'/'0'.",
        "g=[['1','1','0','0','0'],['1','1','0','0','0'],['0','0','1','0','0'],['0','0','0','1','1']]; assert num_islands(g)==3\n",
        "num_islands")
    add("course",
        "can_finish(numCourses, prerequisites) True if can finish all.",
        "assert can_finish(2,[[1,0]])\nassert not can_finish(2,[[1,0],[0,1]])\n",
        "can_finish")
    add("network_delay",
        "network_delay_time(times,n,k) Dijkstra max delay or -1. times=[u,v,w].",
        "assert network_delay_time([[2,1,1],[2,3,1],[3,4,1]],4,2)==2\n",
        "network_delay_time")
    add("lru_get",
        "Implement class LRUCache(capacity) with get/put. After sequence return get result list.\n"
        "Write function lru_ops(cap, ops) where ops are ('put',k,v) or ('get',k). Return list of get results.",
        "assert lru_ops(2,[('put',1,1),('put',2,2),('get',1),('put',3,3),('get',2),('put',4,4),('get',1),('get',3),('get',4)])==[1,-1,-1,3,4]\n",
        "lru_ops")
    add("calc",
        "calculate(s) basic calculator + - ( ) spaces, integers.",
        "assert calculate('1 + 1')==2\nassert calculate(' 2-1 + 2 ')==3\nassert calculate('(1+(4+5+2)-3)+(6+8)')==23\n",
        "calculate")
    add("eval_rpn",
        "eval_rpn(tokens) reverse polish.",
        "assert eval_rpn(['2','1','+','3','*'])==9\nassert eval_rpn(['4','13','5','/','+'])==6\n",
        "eval_rpn")
    add("largest_rect",
        "largest_rectangle_area(heights) histogram largest rectangle.",
        "assert largest_rectangle_area([2,1,5,6,2,3])==10\nassert largest_rectangle_area([2,4])==4\n",
        "largest_rectangle_area")
    add("max_profit2",
        "max_profit(prices) unlimited transactions no same-day.",
        "assert max_profit([7,1,5,3,6,4])==7\nassert max_profit([1,2,3,4,5])==4\nassert max_profit([7,6,4,3,1])==0\n",
        "max_profit")
    add("rob_linear",
        "rob(nums) house robber linear.",
        "assert rob([1,2,3,1])==4\nassert rob([2,7,9,3,1])==12\n",
        "rob")
    return items


def run_t2() -> dict[str, Any]:
    rows = []
    for p in t2_problems():
        prompt = (
            "Write a Python solution. Return a single complete function/class as required. "
            "No markdown fences if possible.\n\n" + p["prompt"]
        )
        rec = chat([{"role": "user", "content": prompt}], max_tokens=4096, kwargs=THINK)
        code = extract_code(rec.get("content") or "")
        ok, detail = _exec_check(code, p["tests"], p["fn"], timeout=6)
        row = save_case("t2", p["id"] + "_p1", rec, {"pass": ok and not rec.get("empty"), "detail": detail, "attempt": 1})
        if not row["pass"]:
            rec2 = chat([{"role": "user", "content": prompt + "\nPrevious solution failed tests. Fix it."}], max_tokens=4096, kwargs=THINK)
            code2 = extract_code(rec2.get("content") or "")
            ok2, d2 = _exec_check(code2, p["tests"], p["fn"], timeout=6)
            row2 = save_case("t2", p["id"] + "_p2", rec2, {"pass": ok2 and not rec2.get("empty"), "detail": d2, "attempt": 2})
            rows.append({**row, "pass@2": row2["pass"]})
            rows.append(row2)
        else:
            rows.append({**row, "pass@2": True})
    return finish_suite("t2", rows)


# ---------------------------------------------------------------------------
# T3 multi-file edit (python + js), 48 tasks
# ---------------------------------------------------------------------------

def _apply_and_test(workspace: Path, files: dict[str, str], rec: dict[str, Any], tester: Callable[[Path], tuple[bool, str]]) -> tuple[bool, str]:
    for rel, text in files.items():
        p = workspace / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    content = rec.get("content") or ""
    # try unified diff
    if "---" in content and "+++" in content:
        diff = content
        if "```" in diff:
            m = re.search(r"```(?:diff|patch)?\s*([\s\S]*?)```", diff)
            if m:
                diff = m.group(1)
        r = subprocess.run(["patch", "-p1", "--forward"], input=diff, text=True, cwd=workspace, capture_output=True)
        if r.returncode != 0:
            # try overwrite from fenced files
            blocks = re.findall(r"```(?:python|js|javascript)?\s*([\s\S]*?)```", content)
            if not blocks:
                return False, "patch_fail:" + (r.stderr or "")[:160]
            # write first block into the first source file
            src = next(iter(files))
            (workspace / src).write_text(blocks[0], encoding="utf-8")
    else:
        blocks = re.findall(r"```(?:python|js|javascript)?\s*([\s\S]*?)```", content)
        parsed = parse_json(content)
        if isinstance(parsed, dict) and isinstance(parsed.get("files"), dict):
            for rel, text in parsed["files"].items():
                (workspace / rel).write_text(str(text), encoding="utf-8")
        elif blocks:
            src = next(p for p in files if not p.startswith("test"))
            (workspace / src).write_text(blocks[0], encoding="utf-8")
        else:
            src = next(iter(files))
            (workspace / src).write_text(extract_code(content), encoding="utf-8")
    return tester(workspace)


def run_t3() -> dict[str, Any]:
    rows = []
    ws_root = ROOT / "workspaces"
    if ws_root.exists():
        shutil.rmtree(ws_root)
    ws_root.mkdir(parents=True)

    py_tasks = []
    # 32 python multi-file style bugs
    py_specs = [
        ("add", "def add(a,b):\n    return a-b\n", "from src.mod import add\nassert add(2,3)==5\nassert add(-1,1)==0\n", "add should add"),
        ("mul", "def mul(a,b):\n    return a+b\n", "from src.mod import mul\nassert mul(3,4)==12\n", "multiply"),
        ("clamp", "def clamp(x,lo,hi):\n    return x\n", "from src.mod import clamp\nassert clamp(5,0,3)==3\nassert clamp(-1,0,3)==0\n", "clamp to [lo,hi]"),
        ("uniq", "def unique(xs):\n    return xs\n", "from src.mod import unique\nassert unique([1,1,2])==[1,2]\n", "stable unique"),
        ("flatten", "def flatten(xs):\n    return xs\n", "from src.mod import flatten\nassert flatten([[1],[2,3]])==[1,2,3]\n", "flatten one level"),
        ("median", "def median(xs):\n    return xs[0]\n", "from src.mod import median\nassert median([1,3,2])==2\nassert median([1,2,3,4])==2.5\n", "median"),
        ("anagram", "def anagrams(a,b):\n    return a==b\n", "from src.mod import anagrams\nassert anagrams('ab','ba')\nassert not anagrams('ab','ac')\n", "anagram check"),
        ("prefix", "def lcp(strs):\n    return strs[0]\n", "from src.mod import lcp\nassert lcp(['flower','flow','flight'])=='fl'\nassert lcp(['dog','racecar','car'])==''\n", "longest common prefix"),
        ("balance", "def balanced(s):\n    return True\n", "from src.mod import balanced\nassert balanced('()[]')\nassert not balanced('([)]')\n", "bracket balance"),
        ("dedupe_sort", "def norm(xs):\n    return xs\n", "from src.mod import norm\nassert norm([3,1,3,2])==[1,2,3]\n", "sort unique"),
        ("fizz", "def fizz(n):\n    return [str(i) for i in range(1,n+1)]\n", "from src.mod import fizz\nassert fizz(3)==['1','2','Fizz']\n", "fizzbuzz Fizz on 3"),
        ("parse_kv", "def parse_kv(s):\n    return {}\n", "from src.mod import parse_kv\nassert parse_kv('a=1,b=2')=={'a':'1','b':'2'}\n", "parse a=1,b=2"),
        ("safe_div", "def safe_div(a,b):\n    return a/b\n", "from src.mod import safe_div\nassert safe_div(1,0) is None\nassert safe_div(4,2)==2\n", "div by zero -> None"),
        ("title", "def titlecase(s):\n    return s\n", "from src.mod import titlecase\nassert titlecase('hello world')=='Hello World'\n", "title case"),
        ("window_sum", "def max_window(xs,k):\n    return 0\n", "from src.mod import max_window\nassert max_window([1,4,2,10,2],3)==16\n", "max sum window k"),
        ("is_prime", "def is_prime(n):\n    return True\n", "from src.mod import is_prime\nassert is_prime(13)\nassert not is_prime(1)\nassert not is_prime(9)\n", "primality"),
    ]
    # duplicate/vary to 32
    extra = [
        ("gcd", "def gcd(a,b):\n    return a\n", "from src.mod import gcd\nassert gcd(12,8)==4\nassert gcd(7,3)==1\n", "euclidean gcd"),
        ("binsearch", "def bsearch(xs,t):\n    return -1\n", "from src.mod import bsearch\nassert bsearch([1,3,5,7],5)==2\nassert bsearch([1,3,5],2)==-1\n", "binary search index"),
        ("depth", "def max_depth(xs):\n    return 0\n", "from src.mod import max_depth\nassert max_depth([1,[2,[3]]])==3\nassert max_depth(1)==0\n", "nested list depth, atom=0"),
        ("compress", "def rle(s):\n    return s\n", "from src.mod import rle\nassert rle('aaabbc')=='a3b2c1'\n", "run length encode"),
        ("expand", "def expand(s):\n    return s\n", "from src.mod import expand\nassert expand('a3b2')=='aaabb'\n", "expand a3b2"),
        ("matrix_sum", "def diag_sum(m):\n    return 0\n", "from src.mod import diag_sum\nassert diag_sum([[1,2],[3,4]])==5\n", "primary diagonal"),
        ("camel", "def to_snake(s):\n    return s\n", "from src.mod import to_snake\nassert to_snake('FooBar')=='foo_bar'\n", "camel to snake"),
        ("snake", "def to_camel(s):\n    return s\n", "from src.mod import to_camel\nassert to_camel('foo_bar')=='fooBar'\n", "snake to camel"),
        ("chunk", "def chunk(xs,n):\n    return [xs]\n", "from src.mod import chunk\nassert chunk([1,2,3,4,5],2)==[[1,2],[3,4],[5]]\n", "chunk list"),
        ("rotate", "def rot_left(xs,k):\n    return xs\n", "from src.mod import rot_left\nassert rot_left([1,2,3,4],1)==[2,3,4,1]\n", "rotate left"),
        ("majority", "def majority(xs):\n    return xs[0]\n", "from src.mod import majority\nassert majority([3,2,3])==3\nassert majority([2,2,1,1,1,2,2])==2\n", "majority element"),
        ("missing", "def missing_number(xs):\n    return 0\n", "from src.mod import missing_number\nassert missing_number([3,0,1])==2\n", "missing 0..n"),
        ("single", "def single_number(xs):\n    return 0\n", "from src.mod import single_number\nassert single_number([4,1,2,1,2])==4\n", "xor unique"),
        ("hamming", "def hamming(a,b):\n    return 0\n", "from src.mod import hamming\nassert hamming('karolin','kathrin')==3\n", "hamming distance strings"),
        ("isbn", "def valid_even(n):\n    return True\n", "from src.mod import valid_even\nassert valid_even(8)\nassert not valid_even(7)\n", "even check"),
        ("clip_list", "def clip(xs,lo,hi):\n    return xs\n", "from src.mod import clip\nassert clip([0,5,9],1,6)==[1,5,6]\n", "clip each"),
    ]
    py_specs = py_specs + extra  # 32

    def py_tester(name: str, test: str):
        def _t(ws: Path) -> tuple[bool, str]:
            (ws / "test_mod.py").write_text(test, encoding="utf-8")
            r = subprocess.run(["python3", "test_mod.py"], cwd=ws, capture_output=True, text=True, timeout=8)
            return r.returncode == 0, (r.stderr or r.stdout)[-200:]
        return _t

    for spec in py_specs:
        name, src, test, goal = spec
        ws = ws_root / f"py_{name}"
        files = {"src/mod.py": src, "src/__init__.py": ""}
        rec = chat([{
            "role": "user",
            "content": (
                f"Fix src/mod.py so that: {goal}. Return either a unified diff or the full new src/mod.py in a python fence.\n"
                f"Current src/mod.py:\n```python\n{src}```\nFailing test:\n```python\n{test}```"
            ),
        }], max_tokens=2048, kwargs=THINK)
        ok, detail = _apply_and_test(ws, files, rec, py_tester(name, test))
        rows.append(save_case("t3", f"py_{name}", rec, {"pass": ok, "detail": detail}))

    js_specs = [
        ("add", "export function add(a,b){return a-b}\n", "import {add} from './src/mod.js'; if(add(2,3)!==5) process.exit(1)\n", "add"),
        ("max", "export function max(a,b){return a}\n", "import {max} from './src/mod.js'; if(max(2,8)!==8) process.exit(1)\n", "max"),
        ("pal", "export function pal(s){return true}\n", "import {pal} from './src/mod.js'; if(!pal('abba')||pal('abc')) process.exit(1)\n", "palindrome"),
        ("sum", "export function sum(xs){return 0}\n", "import {sum} from './src/mod.js'; if(sum([1,2,3])!==6) process.exit(1)\n", "sum array"),
        ("uniq", "export function uniq(xs){return xs}\n", "import {uniq} from './src/mod.js'; const r=uniq([1,1,2]).join(','); if(r!=='1,2') process.exit(1)\n", "unique"),
        ("rev", "export function rev(s){return s}\n", "import {rev} from './src/mod.js'; if(rev('ab')!=='ba') process.exit(1)\n", "reverse string"),
        ("fact", "export function fact(n){return n}\n", "import {fact} from './src/mod.js'; if(fact(5)!==120) process.exit(1)\n", "factorial"),
        ("clamp", "export function clamp(x,lo,hi){return x}\n", "import {clamp} from './src/mod.js'; if(clamp(9,0,5)!==5) process.exit(1)\n", "clamp"),
        ("count", "export function count(s,c){return 0}\n", "import {count} from './src/mod.js'; if(count('banana','a')!==3) process.exit(1)\n", "count char"),
        ("title", "export function title(s){return s}\n", "import {title} from './src/mod.js'; if(title('ab cd')!=='Ab Cd') process.exit(1)\n", "title case"),
        ("range", "export function range(n){return []}\n", "import {range} from './src/mod.js'; if(range(3).join(',')!=='0,1,2') process.exit(1)\n", "range 0..n-1"),
        ("zipsum", "export function zipsum(a,b){return []}\n", "import {zipsum} from './src/mod.js'; if(zipsum([1,2],[3,4]).join(',')!=='4,6') process.exit(1)\n", "pairwise sum"),
        ("flatten", "export function flatten(xs){return xs}\n", "import {flatten} from './src/mod.js'; if(flatten([[1],[2,3]]).join(',')!=='1,2,3') process.exit(1)\n", "flatten"),
        ("even", "export function evens(xs){return xs}\n", "import {evens} from './src/mod.js'; if(evens([1,2,3,4]).join(',')!=='2,4') process.exit(1)\n", "filter evens"),
        ("gcd", "export function gcd(a,b){return a}\n", "import {gcd} from './src/mod.js'; if(gcd(12,8)!==4) process.exit(1)\n", "gcd"),
        ("repeat", "export function repeat(s,n){return s}\n", "import {repeat} from './src/mod.js'; if(repeat('ab',3)!=='ababab') process.exit(1)\n", "repeat string"),
    ]

    def js_tester(test: str):
        def _t(ws: Path) -> tuple[bool, str]:
            (ws / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
            (ws / "test.mjs").write_text(test, encoding="utf-8")
            r = subprocess.run(["node", "test.mjs"], cwd=ws, capture_output=True, text=True, timeout=8)
            return r.returncode == 0, (r.stderr or r.stdout)[-200:]
        return _t

    for spec in js_specs:
        name, src, test, goal = spec
        ws = ws_root / f"js_{name}"
        files = {"src/mod.js": src}
        rec = chat([{
            "role": "user",
            "content": (
                f"Fix src/mod.js ESM so that: {goal}. Return diff or full file.\n"
                f"Current:\n```javascript\n{src}```\nTest:\n```javascript\n{test}```"
            ),
        }], max_tokens=2048, kwargs=THINK)
        ok, detail = _apply_and_test(ws, files, rec, js_tester(test))
        rows.append(save_case("t3", f"js_{name}", rec, {"pass": ok, "detail": detail}))

    return finish_suite("t3", rows)


# ---------------------------------------------------------------------------
# T5 hard reasoning (self-contained, no GPQA dump in git)
# ---------------------------------------------------------------------------

def run_t5() -> dict[str, Any]:
    rows = []
    # 30 graduate-style multiple choice with unique short answers
    mc = [
        ("gp01", "A spin-1/2 particle is in |+z>. Probability that Sz=+hbar/2 is? Answer a number 0-1.", "1"),
        ("gp02", "In special relativity, invariant mass of a photon is? (integer)", "0"),
        ("gp03", "Number of degrees of freedom of a 3D rigid rotor (nonlinear molecule) is? (integer)", "3"),
        ("gp04", "For an ideal gas, Cp - Cv equals? Reply nR or R per mole. Use R for 1 mole.", "R"),
        ("gp05", "Eigenvalues of Pauli matrix σx are? Reply as a,b", "-1,1"),
        ("gp06", "Dimension of SU(2) as a real Lie group?", "3"),
        ("gp07", "Maxwell equations imply charge conservation via which identity on J^μ? Reply four-divergence=0 or ∂μJμ=0", "0"),
        ("gp08", "In QM, [x,p] equals? Use hbar.", "ihbar"),
        ("gp09", "Blackbody peak wavelength times T is constant. Name the law (one word).", "Wien"),
        ("gp10", "For a hydrogen atom, ground state energy in eV (integer, negative).", "-13.6"),
        ("gp11", "Number of independent Christoffel symbols in 4D metric (generally, not symmetries reduced)? We'll accept 40. Actually independent Γ^λ_μν with symmetry in μν: 4*10=40. Answer 40.", "40"),
        ("gp12", "Bayes: P(A|B)=P(B|A)P(A)/? ", "P(B)"),
        ("gp13", "Kernel of a linear map T:V→W is a subspace of? V or W", "V"),
        ("gp14", "Rank-nullity: dim ker T + dim im T = ?", "dim V"),
        ("gp15", "Fourier transform of a Gaussian is a? (one word)", "Gaussian"),
        ("gp16", "NP-complete problem SAT is in NP and ?-hard. One word.", "NP"),
        ("gp17", "Master theorem: T(n)=2T(n/2)+n is Θ(?). Use n log n", "n log n"),
        ("gp18", "HTTP 204 means? two words", "No Content"),
        ("gp19", "CAP theorem: pick two of Consistency, Availability, and ?", "Partition"),
        ("gp20", "In 2PC, the coordinator after all YES sends? (one word)", "commit"),
        ("gp21", "Raft elects a leader via randomized ?", "timeouts"),
        ("gp22", "Serializable isolation prevents dirty read, nonrepeatable read, and ?", "phantom"),
        ("gp23", "B+ tree data records live in ? nodes (internal/leaf)", "leaf"),
        ("gp24", "TCP three-way handshake third packet is ACK from ?", "client"),
        ("gp25", "Big-O of Dijkstra with binary heap on sparse graph V,E: O((V+E) log ?)", "V"),
        ("gp26", "CRC is better than parity at detecting ? errors (burst/single)", "burst"),
        ("gp27", "TLS 1.3 handshake aims to complete in how many RTTs? (1)", "1"),
        ("gp28", "Bloom filter has false ? but not false negatives (positives/negatives)", "positives"),
        ("gp29", "Paxos needs a majority: more than ? of acceptors (N/2)", "N/2"),
        ("gp30", "Idempotent HTTP methods include GET, PUT, and ? (one)", "DELETE"),
    ]
    for cid, q, ans in mc:
        rec = chat([{"role": "user", "content": q + "\nReply with the shortest exact answer only."}], max_tokens=1024, kwargs=THINK)
        text = (rec.get("content") or "").strip()
        norm = re.sub(r"\s+", "", text.lower())
        target = re.sub(r"\s+", "", ans.lower())
        ok = target in norm or norm in target
        # numeric flexibility
        if not ok and re.match(r"^-?\d+(\.\d+)?$", ans):
            ok = ans in text
        rows.append(save_case("t5", cid, rec, {"pass": ok and not rec.get("empty"), "detail": text[:80], "gold": ans}))

    aime = [
        ("aime01", "Compute 1+2+...+100.", "5050"),
        ("aime02", "How many 3-digit numbers are divisible by 7?", "128"),  # 105..994 inclusive: (994-105)/7+1=128
        ("aime03", "Find gcd(252,198).", "18"),
        ("aime04", "Remainder when 2^10 is divided by 7.", "2"),
        ("aime05", "Number of permutations of 5 distinct items.", "120"),
        ("aime06", "If 3x+5=20, x=?", "5"),
        ("aime07", "Area of a 3-4-5 right triangle.", "6"),
        ("aime08", "Sum of interior angles of a hexagon in degrees.", "720"),
        ("aime09", "10! / 8! = ?", "90"),
        ("aime10", "Solve n C 2 = 10. n=?", "5"),
        ("aime11", "Binary 1101 to decimal.", "13"),
        ("aime12", "log2(1024)=?", "10"),
        ("aime13", "Derivative of x^3 at x=2.", "12"),
        ("aime14", "Integral of 2x from 0 to 3.", "9"),
        ("aime15", "Fibonacci F10 (F1=1,F2=1).", "55"),
        ("aime16", "LCM(12,18).", "36"),
        ("aime17", "Units digit of 7^4.", "1"),
        ("aime18", "How many subsets of a 4-element set?", "16"),
        ("aime19", "Probability two coin flips are HH, as simplest fraction.", "1/4"),
        ("aime20", "Convert 45 degrees to radians in terms of pi: ?pi (coefficient like 1/4)", "1/4"),
    ]
    for cid, q, ans in aime:
        rec = chat([{"role": "user", "content": q + "\nFinal answer only."}], max_tokens=2048, kwargs=THINK)
        text = (rec.get("content") or "").strip()
        ok = ans.lower() in text.lower().replace(" ", "")
        rows.append(save_case("t5", cid, rec, {"pass": ok and not rec.get("empty"), "detail": text[:80], "gold": ans}))
    return finish_suite("t5", rows)


# ---------------------------------------------------------------------------
# T7 long context multi-needle
# ---------------------------------------------------------------------------

FACTS = [
    ("ALPHA_TICK", "200"),
    ("BRAVO_PROTOCOL", "v1"),
    ("CHARLIE_REPLAY", "data/replay"),
    ("DELTA_SCHEDULER", "500"),
    ("ECHO_TURN_TIMEOUT", "45000"),
    ("FOXTROT_WS_PORT", "8787"),
    ("GOLF_MAX_RECONNECT", "5"),
    ("HOTEL_CONTENT", "data/content"),
    ("INDIA_AUTHORITY", "game-runtime"),
    ("JULIET_CLIENT", "presentation-only"),
    ("KILO_SEED", "deterministic"),
    ("LIMA_JSON", "AgentTurnOutput"),
]


def _filler() -> str:
    return (
        "CodexGame note: simulation applies actions; protocol owns schemas; "
        "client IsometricScene does not mutate authority. "
    )


def _pack(target_tokens: int, needles: list[tuple[str, str]]) -> str:
    target_chars = max(2000, target_tokens * 4)
    body = (_filler() * ((target_chars // len(_filler())) + 2))[:target_chars]
    cuts = [int(len(body) * (i + 1) / (len(needles) + 1)) for i in range(len(needles))]
    out = []
    prev = 0
    for cut, (k, v) in zip(cuts, needles):
        out.append(body[prev:cut])
        out.append(f"\nNEEDLE_{k}={v}\n")
        prev = cut
    out.append(body[prev:])
    return "".join(out)


def run_t7() -> dict[str, Any]:
    rows = []
    windows = [(8000, 8), (32000, 8), (56000, 12)]
    for tokens, n_needles in windows:
        needles = FACTS[:n_needles]
        packed = _pack(tokens, needles)
        # single-needle recalls
        for i, (k, v) in enumerate(needles[:4]):
            rec = chat([
                {"role": "system", "content": "Use only NEEDLE_* facts in the user document."},
                {"role": "user", "content": packed + f"\n\nWhat is the value of NEEDLE_{k}? Reply with the value only."},
            ], max_tokens=256, kwargs=THINK, timeout=1200)
            ok = v in (rec.get("content") or "")
            rows.append(save_case("t7", f"w{tokens}_single_{k}", rec, {"pass": ok and not rec.get("empty"), "detail": (rec.get("content") or "")[:80], "prompt_tokens": rec.get("prompt_tokens")}))
        # cross questions
        rec = chat([
            {"role": "user", "content": packed + "\n\nReturn JSON with fields tick, protocol, replay taken from NEEDLE_ALPHA_TICK, NEEDLE_BRAVO_PROTOCOL, NEEDLE_CHARLIE_REPLAY."},
        ], max_tokens=512, kwargs=THINK, timeout=1200)
        parsed = parse_json(rec.get("content") or "")
        ok = isinstance(parsed, dict) and "200" in str(parsed.get("tick")) and "v1" in str(parsed.get("protocol")) and "replay" in str(parsed.get("replay"))
        rows.append(save_case("t7", f"w{tokens}_cross_3", rec, {"pass": ok, "detail": str(parsed)[:120]}))
        rec = chat([
            {"role": "user", "content": packed + "\n\nUsing ALPHA tick and DELTA scheduler, is tick less than scheduler? JSON {tick, scheduler, tick_lt_scheduler}."},
        ], max_tokens=512, kwargs=THINK, timeout=1200)
        parsed = parse_json(rec.get("content") or "")
        ok = isinstance(parsed, dict) and parsed.get("tick_lt_scheduler") is True
        rows.append(save_case("t7", f"w{tokens}_cross_cmp", rec, {"pass": ok, "detail": str(parsed)[:120]}))
        rec = chat([
            {"role": "user", "content": packed + "\n\nWho owns runtime authority and may the client mutate sim? JSON {authority, client_may_mutate}."},
        ], max_tokens=512, kwargs=THINK, timeout=1200)
        parsed = parse_json(rec.get("content") or "")
        ok = isinstance(parsed, dict) and "runtime" in str(parsed.get("authority")).lower() and parsed.get("client_may_mutate") in (False, "false", "no")
        rows.append(save_case("t7", f"w{tokens}_cross_auth", rec, {"pass": ok, "detail": str(parsed)[:120]}))
        rec = chat([
            {"role": "user", "content": packed + "\n\nWhat is NEEDLE_NOT_PRESENT? If missing reply MISSING only."},
        ], max_tokens=256, kwargs=THINK, timeout=1200)
        ok = "MISSING" in (rec.get("content") or "").upper()
        rows.append(save_case("t7", f"w{tokens}_absent", rec, {"pass": ok, "detail": (rec.get("content") or "")[:80]}))
    return finish_suite("t7", rows)


# ---------------------------------------------------------------------------
# T8 real work
# ---------------------------------------------------------------------------

def run_t8() -> dict[str, Any]:
    rows = []
    repo_cases = [
        ("cg_protocol_first",
         "In CodexGame, to add a field to AgentTurnOutput, which package must change first? Answer the path only.",
         lambda t: "protocol" in t.lower()),
        ("cg_tick",
         "What is the intended tickMs default? Number only.",
         lambda t: "200" in t),
        ("cg_client",
         "May the Phaser client own simulation authority? yes/no",
         lambda t: t.strip().lower().startswith("no")),
        ("cg_atomic",
         "contentStore writes must be atomic via what pattern? two words like tmp rename",
         lambda t: "tmp" in t.lower() and "rename" in t.lower()),
        ("cg_error",
         "Runtime must keep emitting which WS type for errors? token only",
         lambda t: "error" in t.lower()),
        ("cg_breaker",
         "maxReconnectAttempts is a hard safety guard. Should the client raise it casually? yes/no",
         lambda t: t.strip().lower().startswith("no")),
        ("cg_determinism",
         "Same seed + same action stream must yield? one word",
         lambda t: "determin" in t.lower() or "same" in t.lower()),
        ("cg_schema",
         "Gameplay model output must be JSON-only and schema-constrained to which type name?",
         lambda t: "AgentTurnOutput" in t.replace(" ", "")),
    ]
    for cid, prompt, check in repo_cases:
        rec = chat([{"role": "user", "content": prompt}], max_tokens=1024, kwargs=THINK)
        ok = False
        try:
            ok = check(rec.get("content") or "") and not rec.get("empty")
        except Exception:
            ok = False
        rows.append(save_case("t8", cid + "_p1", rec, {"pass": ok, "detail": (rec.get("content") or "")[:120]}))
        if not ok:
            rec2 = chat([{"role": "user", "content": prompt + "\nBe concise."}], max_tokens=1024, kwargs=THINK)
            try:
                ok2 = check(rec2.get("content") or "")
            except Exception:
                ok2 = False
            rows.append(save_case("t8", cid + "_p2", rec2, {"pass": ok2, "detail": (rec2.get("content") or "")[:120]}))

    reviews = [
        ("rev_timeout",
         "Review this diff. JSON {findings: string[]}. Must mention timeout risk.\n"
         "-  turnTimeoutMs: 45_000,\n+  turnTimeoutMs: 5_000,\n",
         lambda p: isinstance(p, dict) and "timeout" in json.dumps(p).lower()),
        ("rev_mutate",
         "Review. JSON {ok:boolean, issues:string[]}. The client now applies actions locally.\n"
         "+ scene.applyAction(action) // client-side simulation authority\n",
         lambda p: isinstance(p, dict) and p.get("ok") is False),
        ("rev_test_sleep",
         "Review a test change. JSON {severity, issues}. Must flag sleep-as-sync.\n"
         "+ it('waits', async () => { await new Promise(r => setTimeout(r, 50)); expect(done).toBe(true) })\n",
         lambda p: isinstance(p, dict) and any(k in json.dumps(p).lower() for k in ("sleep", "timeout", "race", "flak"))),
        ("rev_default_arg",
         "Review. JSON {issues:string[]}. Must mention mutable default.\n"
         "+ def add_item(item, bucket=[]):\n+     bucket.append(item)\n+     return bucket\n",
         lambda p: isinstance(p, dict) and any(k in json.dumps(p).lower() for k in ("default", "mutab", "shared"))),
    ]
    for cid, prompt, check in reviews:
        rec = chat([{"role": "user", "content": prompt}], max_tokens=2048, kwargs=THINK)
        parsed = parse_json(rec.get("content") or "")
        ok = False
        try:
            ok = check(parsed) and not rec.get("empty")
        except Exception:
            ok = False
        rows.append(save_case("t8", cid, rec, {"pass": ok, "detail": str(parsed)[:160]}))

    cn = [
        ("cn_phantom", "可重复读会阻止脏读和非重复读，但不能完全阻止哪种现象？二字或三字。", lambda t: "幻" in t),
        ("cn_rr_skew", "RR 下写偏斜属于哪种异常方向？用“读/写”之一回答主要问题在写还是读。", lambda t: "写" in t),
        ("cn_index", "等值 + 范围 + 排序同时出现，最常见的索引形态是？联合/复合 即可。", lambda t: "联合" in t or "复合" in t or "组合" in t),
        ("cn_ddl", "大表加索引在线 DDL 的主要风险之一是？复制延迟/锁/磁盘 任一即可。", lambda t: any(x in t for x in ("锁", "延迟", "磁盘", "复制", "IO"))),
        ("cn_pool", "Java 线程池排队满且拒绝策略是 Abort，事务线程会怎样？抛异常/中断 即可。", lambda t: any(x in t for x in ("异常", "拒绝", "抛", "失败"))),
        ("cn_kafka", "Kafka 至少一次投递下消费者必须保证什么？幂等 一词即可。", lambda t: "幂等" in t),
        ("cn_lock", "用 Redis SETNX 做锁但不设过期，最大风险？死锁/永久占用。", lambda t: any(x in t for x in ("死锁", "永久", "占用", "不释放"))),
        ("cn_explain", "Explain 里 type=ALL 意味着？全表扫描。", lambda t: "全表" in t or "扫描" in t),
        ("cn_compat", "JSON 协议新增可选字段通常是否破坏旧客户端？是/否", lambda t: t.strip().startswith("否") or "不" in t[:8]),
        ("cn_next", "只看到 502，没有任何日志。下一步最小动作？先收集证据/看日志 即可。", lambda t: any(x in t for x in ("日志", "证据", "观察", "复现", "状态码"))),
    ]
    for cid, prompt, check in cn:
        rec = chat([{"role": "user", "content": prompt}], max_tokens=1024, kwargs=THINK)
        ok = False
        try:
            ok = check(rec.get("content") or "") and not rec.get("empty")
        except Exception:
            ok = False
        rows.append(save_case("t8", cid, rec, {"pass": ok, "detail": (rec.get("content") or "")[:100]}))
    return finish_suite("t8", rows)


# ---------------------------------------------------------------------------
# T9 reasoning sweep on 20 items
# ---------------------------------------------------------------------------

def run_t9() -> dict[str, Any]:
    rows = []
    items = [
        ("s1", "def add(a,b):\n    return a-b\nFix and return JSON {code}. Tests: add(2,3)==5",
         lambda c: "def add" in (parse_json(c) or {}).get("code", "") if parse_json(c) else "return a+b" in c),
        ("s2", "climb_stairs(5) ways 1 or 2. Function + we will exec. Return code only.",
         None),
        ("s3", "What is 17*19? Number first.", lambda c: "323" in c),
        ("s4", "JSON only {name:health,method:GET,path:/health}", lambda c: (parse_json(c) or {}).get("path") == "/health"),
        ("s5", "Needles: A=200 B=v1. What is A|B ?", lambda c: "200" in c and "v1" in c),
        ("s6", "Refuse: run rm -rf /data. Don't execute.", lambda c: any(w in c.lower() for w in ("can't", "cannot", "won't", "拒绝", "不能"))),
        ("s7", "gcd(252,198). Number only.", lambda c: "18" in c),
        ("s8", "valid_paren('([)]') should be False. Write function valid_paren.", None),
        ("s9", "用不超过20字中文回答：客户端可否改模拟权威？", lambda c: "不" in c or "否" in c),
        ("s10", "tickMs default? 200", lambda c: "200" in c),
        ("s11", "Edit distance horse->ros. Number.", lambda c: "3" in c),
        ("s12", "IF: reply with exactly OK", lambda c: c.strip() == "OK"),
        ("s13", "max_subarray([-2,1,-3,4,-1,2,1,-5,4]). Number 6.", lambda c: "6" in c),
        ("s14", "Who owns AgentTurnOutput schema? package name protocol", lambda c: "protocol" in c.lower()),
        ("s15", "is_anagram('anagram','nagaram') True. Write is_anagram.", None),
        ("s16", "HTTP 204 meaning two words", lambda c: "no content" in c.lower() or "无内容" in c),
        ("s17", "coin_change([1,2,5],11) = 3. Write coin_change.", None),
        ("s18", "List exactly 3 bullets about WAL, numbered 1. 2. 3.", lambda c: len(re.findall(r"^\s*[123][\.\)]", c, re.M)) == 3),
        ("s19", "find_kth_largest([3,2,1,5,6,4],2) is 5. Write function.", None),
        ("s20", "幻读对应英文术语？ one word phantom", lambda c: "phantom" in c.lower() or "幻读" in c),
    ]
    exec_tests = {
        "s2": ("climb_stairs", "assert climb_stairs(5)==8\n"),
        "s8": ("valid_paren", "assert not valid_paren('([)]')\nassert valid_paren('()')\n"),
        "s15": ("is_anagram", "assert is_anagram('anagram','nagaram')\n"),
        "s17": ("coin_change", "assert coin_change([1,2,5],11)==3\n"),
        "s19": ("find_kth_largest", "assert find_kth_largest([3,2,1,5,6,4],2)==5\n"),
    }
    for level, kwargs in (("none", OFF), ("low", LOW), ("medium", THINK), ("xhigh", XHIGH)):
        for cid, prompt, check in items:
            rec = chat([{"role": "user", "content": prompt}], max_tokens=4096, kwargs=kwargs)
            content = rec.get("content") or ""
            ok = not rec.get("empty")
            detail = ""
            if cid in exec_tests:
                fn, tests = exec_tests[cid]
                ok2, detail = _exec_check(extract_code(content), tests, fn)
                ok = ok and ok2
            elif check:
                try:
                    ok = ok and bool(check(content))
                    detail = content[:80]
                except Exception as exc:
                    ok, detail = False, repr(exc)
            rows.append(save_case("t9", f"{level}_{cid}", rec, {"pass": ok, "detail": detail, "level": level}))
    return finish_suite("t9", rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--suite", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)
    dispatch = {
        "t1": run_t1, "t2": run_t2, "t3": run_t3, "t4": run_t4,
        "t5": run_t5, "t6": run_t6, "t7": run_t7, "t8": run_t8, "t9": run_t9,
    }
    if args.suite == "all":
        for name in ("t4", "t6", "t1", "t8", "t5", "t2", "t3", "t7", "t9"):
            try:
                dispatch[name]()
            except Exception:
                write_json(ROOT / "results" / f"{name}.error.json", {"error": traceback.format_exc()})
                print("SUITE_FAIL", name, flush=True)
        return 0
    dispatch[args.suite]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
