#!/usr/bin/env python3
"""Read-only hardware inventory. This does not qualify GPU performance."""
import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import subprocess

GPU_QUERY = "name,memory.total,memory.free,driver_version,pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,pcie.link.width.max"
COMMANDS = {"uname": ["uname", "-a"], "lscpu": ["lscpu"],
            "nvidia_smi": ["nvidia-smi", "--query-gpu=" + GPU_QUERY, "--format=csv,noheader,nounits"],
            "nvcc": ["nvcc", "--version"],
            "lsblk": ["lsblk", "-b", "-o", "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS"],
            "df": ["df", "-h", "-P"]}
GPU_KEYS = ["name", "memory_total_mib", "memory_free_mib", "driver_version",
            "pcie_gen_current", "pcie_gen_max", "pcie_width_current", "pcie_width_max"]


def run_command(command, timeout=5):
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout, check=False)
        return {"command": command, "ok": result.returncode == 0, "exit_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr,
                "error": None if result.returncode == 0 else "nonzero exit"}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": command, "ok": False, "exit_code": None,
                "stdout": None, "stderr": None, "error": type(error).__name__ + ": " + str(error)}


def collect():
    probes = {key: run_command(command) for key, command in COMMANDS.items()}
    try:
        probes["meminfo"] = {"ok": True, "path": "/proc/meminfo",
                             "stdout": Path("/proc/meminfo").read_text(encoding="utf-8")}
    except OSError as error:
        probes["meminfo"] = {"ok": False, "path": "/proc/meminfo", "stdout": None, "error": str(error)}
    gpus = []
    if probes["nvidia_smi"]["ok"]:
        try:
            for row in csv.reader(io.StringIO(probes["nvidia_smi"]["stdout"]), skipinitialspace=True):
                if len(row) != len(GPU_KEYS):
                    raise ValueError("unexpected nvidia-smi CSV field count")
                gpu = dict(zip(GPU_KEYS, (value.strip() for value in row)))
                for key in GPU_KEYS:
                    if key not in ("name", "driver_version"):
                        gpu[key] = int(gpu[key]) if gpu[key].isdigit() else None
                    elif gpu[key] in ("", "N/A", "[Not Supported]"):
                        gpu[key] = None
                gpu["unavailable_fields"] = [key for key in GPU_KEYS if gpu[key] is None]
                gpus.append(gpu)
            if not gpus:
                raise ValueError("nvidia-smi returned no GPU rows")
        except (ValueError, csv.Error) as error:
            probes["nvidia_smi"]["ok"] = False
            probes["nvidia_smi"]["error"] = str(error)
            gpus = []
    match = "UNKNOWN"
    if gpus and all(gpu["name"] is not None for gpu in gpus):
        name = gpus[0]["name"]
        match = "MATCH" if len(gpus) == 1 and re.search(r"\bRTX\s+4090\b", name) and "Laptop" not in name else "MISMATCH"
    return {"evidence_kind": "hardware_inventory", "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "machine_match": match, "match_scope": "one desktop RTX 4090 model only",
            "performance_qualification": "NOT_RUN", "probes": probes, "gpus": gpus}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        Path(args.output).write_text(json.dumps(collect(), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except OSError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

