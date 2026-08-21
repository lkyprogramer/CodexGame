#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.util import dump_json, utc_now


def command_output(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
        return {
            "available": True,
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "command": command, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture benchmark host and toolchain environment")
    parser.add_argument("--output", required=True)
    parser.add_argument("--server-command", default="", help="Exact llama.cpp/server launch command to record")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    payload = {
        "captured_at": utc_now(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "server_command": args.server_command,
        "server_command_argv": shlex.split(args.server_command) if args.server_command else [],
        "notes": args.notes,
        "tools": {
            "nvidia_smi": command_output([
                "nvidia-smi",
                "--query-gpu=name,uuid,driver_version,memory.total,power.limit,temperature.gpu",
                "--format=csv,noheader",
            ]),
            "java": command_output(["java", "-version"]),
            "javac": command_output(["javac", "-version"]),
            "git": command_output(["git", "--version"]),
            "python": command_output([sys.executable, "--version"]),
        },
    }
    dump_json(args.output, payload)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
