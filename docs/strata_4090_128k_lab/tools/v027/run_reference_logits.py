"""Same-ID/GGUF reference comparison; original P3 judgments stay FAIL."""
from __future__ import annotations
import argparse
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import struct
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "tools/combination"))
import run_baseline as baseline
from boundary_memory import MemorySampler
from lab.core import available_mib, dump, gpu_inventory, gpu_lock, hash_obj, load_config, sha256
from lab.runner import make_run_config, validate_gpu_ownership, wait_released

PRIOR = ROOT / "workspace/combination/v027-20261028"
P7 = ROOT / "workspace/combination/retrieval-rootcause-20261028"
TASK = ROOT / "workspace/combination/reference-logits-20261028"
REF = Path("/home/hhtele/buun-llama-cpp-87b37ea")
WIDTH = 248320


def read_ids(path):
    return [int(x) for x in Path(path).read_text().replace(",", " ").split()]


def fnv_ids(ids):
    value = 1469598103934665603
    for byte in struct.pack("<" + "i" * len(ids), *ids):
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f"{value:016x}"


def ids_record(path, ids):
    path.write_text(",".join(map(str, ids)) + "\n")
    return {"path": str(path), "count": len(ids), "fnv64": fnv_ids(ids),
            "int32_sha256": hashlib.sha256(struct.pack("<" + "i" * len(ids), *ids)).hexdigest(),
            "file_sha256": sha256(path)}


def prepare():
    os.environ.update(STRATA_PRESERVE_THINKING="0", STRATA_REPLY_REUSE="1")
    c = load_config(PRIOR / "config.json")
    baseline.source_receipt(Path(c["deployed_repo"]), PRIOR)
    from lab.tokenizer import StrataCounter
    counter = StrataCounter(c["deployed_repo"], c["gguf"], c["template"])
    cases = []
    for name, source, gold in [("literal", "control-literal-copy", "6763216-000738"),
                               ("prime-69632", "original-69632-prime", "6763216-000738"),
                               ("prime-102400", "original-102400-prime", "2390975-001086")]:
        body = json.loads((P7 / "trace-v2" / (source + ".request.json")).read_text())
        raw = json.loads((P7 / "trace-v2" / (source + ".raw-tokens.json")).read_text())
        if hash_obj(body) != raw["body_sha256"]:
            raise RuntimeError("SOURCE_BODY_DRIFT")
        messages, tools, kwargs = counter.frontend.openai_to_messages(copy.deepcopy(body))
        rendered = counter.template.render(messages, tools=tools, **kwargs)
        tokens = counter.tokenizer.encode(rendered, parse_special=True)
        if len(tokens) != counter(body):
            raise RuntimeError("RENDER_TOKEN_COUNT_MISMATCH")
        prefix = raw["raw_ids"][:7]
        observed = counter.tokenizer.decode(prefix)
        if len(prefix) != 7 or len(observed) != 7 or not observed.isdigit():
            raise RuntimeError("OBSERVED_PREFIX_IS_NOT_SEVEN_DIGITS")
        (TASK / "input" / (name + ".rendered.txt")).write_text(rendered)
        cases.append({"name": name, "source_request_sha256": hash_obj(body), "gold": gold,
                      "observed_prefix": observed,
                      "tokens": ids_record(TASK / "input" / (name + ".ids"), tokens),
                      "prefix": ids_record(TASK / "input" / (name + ".prefix.ids"), prefix),
                      "gold_digit_ids": counter.tokenizer.encode(gold.split("-")[0]),
                      "tracked_ids": [12, 248044, 248046], "original_status": "CONTROL" if name == "literal" else "FAIL_UNCHANGED"})
    dump(TASK / "inputs.json", cases)
    protected = baseline.combo.assert_protected(c, json.loads((P7 / "FINAL_PROTECTION.json").read_text())["file_sha256"])
    dump(TASK / "production-before.json", {"service": baseline.combo.assert_service_inactive(), "file_sha256": protected})
    dump(TASK / "PREREGISTRATION.json", {"purpose": "independent same-token/source-GGUF logits on two failing prime requests",
         "native": "unchanged P6 binary and existing STRATA_DUMP_FIRST_LOGITS; GEN max_new=1 at each frozen prefix",
         "reference": "llama.cpp 87b37ea graph via existing libraries; direct token IDs; no tokenizer/sampler/MTP/MoE cache",
         "steps": "prompt last-position logits, then seven teacher-forced observed digit IDs; full 248320-way rows",
         "qualification": "short literal copy with the same seven-digit prefix; structural/input/finite checks first",
         "reference_kv": "F16; native int8 retained; cache formats and arithmetic are not asserted bitwise equivalent",
         "limits": {"max_context": 131072, "safety_tokens": 4096, "temperature_abort_c": 85,
                    "min_available_mib": 4096, "reference_qualification_timeout_s": 600, "reference_long_timeout_s": 7200},
         "original_six_status": "FAIL_UNCHANGED", "scoring_changed": False, "production_writes": False, "deployment": False})
    return cases


class Guard:
    def __init__(self, c, folder, proc, exe, timeout):
        self.c, self.folder, self.proc, self.exe = c, folder, proc, str(Path(exe).resolve())
        self.deadline = time.monotonic() + timeout
        self.stop = threading.Event()
        self.reason = None
        self.samples = []
        self.thread = threading.Thread(target=self.loop, daemon=True)

    def terminate(self):
        if self.proc.poll() is None:
            with contextlib.suppress(ProcessLookupError): os.killpg(self.proc.pid, signal.SIGTERM)

    def loop(self):
        try:
            while not self.stop.wait(1):
                if self.proc.poll() is not None: break
                gpu = gpu_inventory("0")
                mem = available_mib()
                self.samples.append({"ts": time.time(), "gpu": gpu, "mem_available_mib": mem})
                if gpu["compute_processes"]:
                    try:
                        validate_gpu_ownership(gpu["compute_processes"], self.proc.pid, self.exe)
                    except FileNotFoundError:
                        # NVML may still list the exited owner after /proc has disappeared.
                        # Recheck for other PIDs; wait_released verifies eventual GPU release.
                        if self.proc.poll() is not None:
                            fresh = gpu_inventory("0")["compute_processes"]
                            if all(int(row.split(',', 1)[0]) == self.proc.pid for row in fresh):
                                break
                        raise
                if mem < 4096: raise RuntimeError("RAM_GUARD")
                if float(gpu["temperature_c"]) >= 85: raise RuntimeError("THERMAL_GUARD")
                if time.monotonic() > self.deadline: raise RuntimeError("WALL_TIMEOUT")
        except BaseException as error:
            self.reason = str(error)
            self.terminate()

    def __enter__(self):
        dump(self.folder / "owned-process.json", {"pid": self.proc.pid, "exe": self.exe, "started": time.time()})
        self.thread.start()
        return self

    def finish(self):
        # End ownership sampling while the engine is still alive, before QUIT
        # removes /proc entries. In-flight samples must finish before shutdown.
        self.stop.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError("GUARD_MONITOR_NOT_STOPPED")
        if self.reason:
            raise RuntimeError("RESOURCE_GUARD: " + self.reason)
        dump(self.folder / "guard-finished.json", {"monitor_stopped_before_quit": True})

    def __exit__(self, *_):
        self.stop.set()
        self.terminate()
        try: self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError): os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait(timeout=15)
        self.thread.join(timeout=5)
        dump(self.folder / "telemetry.json", {"abort_reason": self.reason, "samples": self.samples})


def choose(suite):
    cases = json.loads((TASK / "inputs.json").read_text())
    selected = [c for c in cases if (c["name"] == "literal") == (suite == "qualify")]
    for case in selected:
        for field in ("tokens", "prefix"):
            record = case[field]
            ids = read_ids(record["path"])
            if sha256(Path(record["path"])) != record["file_sha256"] or fnv_ids(ids) != record["fnv64"]:
                raise RuntimeError("FROZEN_ID_DRIFT")
    return selected


def clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("STRATA_", "GGML_", "LLAMA_"))}
    env.update(CUDA_VISIBLE_DEVICES="0", OMP_NUM_THREADS="16", OPENBLAS_NUM_THREADS="16")
    return env


def run_reference(c, folder, cases, ngl):
    manifest = folder / "cases.txt"
    manifest.write_text("".join(f'{x["name"]} {x["tokens"]["path"]} {x["prefix"]["path"]} {folder / (x["name"] + ".f32")}\n' for x in cases))
    exe = TASK / "reference-build/reference_logits"
    cmd = [str(exe), "--model", c["gguf"], "--cases", str(manifest), "--backend-path", str(REF / "build/bin"),
           "--ngl", str(ngl), "--max-context", "131072", "--batch", "512", "--threads", "16"]
    dump(folder / "command.json", cmd)
    env = clean_env()
    env["GGML_BACKEND_PATH"] = str(REF / "build/bin")
    with (folder / "stdout.log").open("w") as out, (folder / "stderr.log").open("w") as err:
        proc = subprocess.Popen(cmd, env=env, stdout=out, stderr=err, start_new_session=True)
        with Guard(c, folder, proc, exe, 600 if len(cases) == 1 else 7200) as guard, \
             MemorySampler(folder, lambda: [proc.pid]) as memory:
            memory.stage = "reference-load-prefill-logits"
            rc = proc.wait()
            if rc or guard.reason: raise RuntimeError(f"REFERENCE_EXIT={rc}: {guard.reason}")
    stdout = (folder / "stdout.log").read_text()
    for case in cases:
        record = case["tokens"]
        if f'input_fnv={record["fnv64"]} prefix_fnv={case["prefix"]["fnv64"]}' not in stdout:
            raise RuntimeError("REFERENCE_CONSUMED_ID_HASH_MISMATCH")
        if (folder / (case["name"] + ".f32")).stat().st_size != (case["prefix"]["count"] + 1) * WIDTH * 4:
            raise RuntimeError("REFERENCE_LOGITS_SHAPE_MISMATCH")


def run_native(c, folder, cases, save_session=False):
    cfg = make_run_config(c, Path(c["deployed_repo"]), "cfg", {}, folder)
    env = clean_env()
    env.update(cfg["env"])
    env["STRATA_DUMP_FIRST_LOGITS"] = str(folder / "first")
    cmd = [cfg["exe"], "--serve", *cfg["args"]]
    dump(folder / "command.json", cmd)
    lines = queue.Queue()
    with (folder / "stderr.log").open("w") as err, (folder / "stdout.log").open("w") as out:
        proc = subprocess.Popen(cmd, cwd=cfg["cwd"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=err, text=True, bufsize=1, start_new_session=True)
        def pump():
            for line in proc.stdout:
                out.write(line); out.flush(); lines.put(line.strip())
            lines.put(None)
        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        def until(prefix):
            while True:
                try: line = lines.get(timeout=10)
                except queue.Empty:
                    if proc.poll() is not None: raise RuntimeError("NATIVE_ENDED_WITHOUT_TERMINAL_LINE")
                    continue
                if line is None or line.startswith(("ERR", "SERR ")): raise RuntimeError("NATIVE_PROTOCOL: " + str(line))
                if line.startswith(prefix): return line
        with Guard(c, folder, proc, cfg["exe"], 1800) as guard, MemorySampler(folder, lambda: [proc.pid]) as memory:
            memory.stage = "native-load-prefill-logits"
            ready = until("READY ")
            if "131072" not in ready: raise RuntimeError("NATIVE_CONTEXT_DRIFT")
            index = 0
            records = []
            for case in cases:
                tokens = read_ids(case["tokens"]["path"])
                prefix = read_ids(case["prefix"]["path"])
                with (folder / (case["name"] + ".f32")).open("wb") as output:
                    for step in range(len(prefix) + 1):
                        current = tokens + prefix[:step]
                        proc.stdin.write("GEN 1 " + ",".join(map(str, current)) + "\n")
                        proc.stdin.flush()
                        token = int(until("T ").split()[1])
                        done = until("DONE")
                        data = Path(str(folder / "first") + "." + str(index)).read_bytes()
                        if len(data) != WIDTH * 4: raise RuntimeError("NATIVE_LOGITS_SHAPE_MISMATCH")
                        output.write(data); output.flush()
                        records.append({"case": case["name"], "step": step, "input_count": len(current),
                                        "input_fnv": fnv_ids(current), "emitted": token, "done": done, "dump_index": index})
                        dump(folder / "requests.json", records)
                        index += 1
                print("NATIVE_COMPLETE", case["name"], flush=True)
            if save_session:
                session_path = folder / "session.bin"
                proc.stdin.write("SAVE " + str(session_path) + "\n"); proc.stdin.flush()
                saved = until("SAVED ").split()
                if len(saved) != 4 or int(saved[2]) != session_path.stat().st_size:
                    raise RuntimeError("SAVED_FILE_SHAPE_MISMATCH")
                dump(folder / "SAVED.json", {"live_tokens": int(saved[1]), "bytes": int(saved[2]),
                     "path": str(session_path), "save_ms": float(saved[3])})
            guard.finish()
            proc.stdin.write("QUIT\n"); proc.stdin.flush()
            proc.wait(timeout=60)
            if proc.returncode or guard.reason: raise RuntimeError(f"NATIVE_EXIT={proc.returncode}: {guard.reason}")
        thread.join(timeout=5)


def run(mode, suite, name, ngl):
    c = load_config(PRIOR / "config.json")
    before = json.loads((TASK / "production-before.json").read_text())
    baseline.combo.assert_service_inactive()
    baseline.combo.assert_protected(c, before["file_sha256"])
    baseline.source_receipt(Path(c["deployed_repo"]), PRIOR)
    folder = TASK / name
    folder.mkdir(exist_ok=False)
    cases = choose(suite)
    dump(folder / "plan.json", {"mode": mode, "suite": suite, "cases": cases, "ngl": ngl})
    try:
        with gpu_lock(c["gpu_lock_workspace"]):
            dump(folder / "cooldown.json", baseline.combo.wait_cool(c))
            if mode == "reference": run_reference(c, folder, cases, ngl)
            else: run_native(c, folder, cases)
            wait_released(c)
        dump(folder / "COMPLETION.json", {"state": "COMPLETE", "original_six_status": "FAIL_UNCHANGED"})
    except BaseException as error:
        dump(folder / "FAILURE.json", {"error": str(error), "partial_files_preserved": True})
        raise
    finally:
        dump(folder / "production-after.json", {"service": baseline.combo.assert_service_inactive(),
             "file_sha256": baseline.combo.assert_protected(c, before["file_sha256"]), "gpu": gpu_inventory("0")})
    return {"state": "COMPLETE", "folder": str(folder)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["prepare", "reference", "native"], required=True)
    parser.add_argument("--suite", choices=["qualify", "long"], default="qualify")
    parser.add_argument("--name")
    parser.add_argument("--ngl", type=int, default=18)
    args = parser.parse_args()
    if args.mode == "prepare": print(json.dumps(prepare()), flush=True)
    else:
        if not args.name: parser.error("--name is required for a run")
        print(json.dumps(run(args.mode, args.suite, args.name, args.ngl)), flush=True)
