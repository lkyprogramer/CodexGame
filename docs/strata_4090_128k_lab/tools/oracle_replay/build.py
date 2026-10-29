"""Apply the preregistered diagnostic and compile its isolated engine (no GPU run)."""
from datetime import datetime, timezone
import json
import subprocess
import sys

import prepare
import make_patch

from lab.core import dump, sha256


def build():
    task, tree = prepare.TASK, prepare.TREE
    if (task / "BUILD_COMPLETE.json").exists():
        raise RuntimeError("BUILD_ALREADY_COMPLETE: recover the existing receipt")
    patch = task / "replay.patch"
    if not patch.exists():
        dump(task / "PATCH.json", make_patch.apply(tree, patch))
    record = json.loads((task / "PATCH.json").read_text())
    if sha256(tree / make_patch.RELATIVE) != record["patched_sha256"]:
        raise RuntimeError("PATCHED_SOURCE_DRIFT")
    commands = json.loads((task / "build-commands.json").read_text())
    results = []
    for index, cmd in enumerate(commands):
        with (task / f"build-{index}.log").open("w") as out:
            result = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT)
        results.append({"command": cmd, "returncode": result.returncode})
        dump(task / "build-results.json", results)
        if result.returncode:
            raise RuntimeError(f"BUILD_FAILED: build-{index}.log")
    receipt = {"completed_utc": datetime.now(timezone.utc).isoformat(),
               "exe_sha256": sha256(tree / "build-lab/strata"),
               "source_sha256": sha256(tree / make_patch.RELATIVE),
               "patch": record, "gpu_requests": 0}
    dump(task / "BUILD_COMPLETE.json", receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    build()
