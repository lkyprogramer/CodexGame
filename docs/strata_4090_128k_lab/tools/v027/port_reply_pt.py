"""Port the frozen, additive #1536/PT Python patch onto the v0.2.7 tag.

Native sources are never patched. Every insertion needs a unique upstream
anchor; the resulting diff and file hashes are recorded for review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TAG = "5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d"
FILES = {"serve/frontend.py", "serve/server.py", "tools/strata_tokenizer.py",
         "serve/test_server.py", "serve/test_prompt_encoder.py", "serve/test_frontend.py"}


def sections(patch):
    result = {}
    for section in patch.split("diff --git ")[1:]:
        first, *lines = section.splitlines(keepends=True)
        name = first.split()[1][2:]
        if name not in FILES:
            raise ValueError("Unexpected patch path: " + name)
        if any(line.startswith("-") and not line.startswith("---") for line in lines):
            raise ValueError("Expected the frozen additive patch")
        result[name] = lines
    if result.keys() != FILES:
        raise ValueError("Incomplete frozen patch")
    return result


def insert_hunks(text, lines):
    # The server's neighboring constants changed upstream. Preserve the entire
    # insertion, locating it by the longest unique preceding context suffix.
    context = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("@@"):
            context = []
        elif line.startswith(" "):
            context.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added = []
            while index < len(lines) and lines[index].startswith("+"):
                added.append(lines[index][1:])
                index += 1
            insertion = "".join(added)
            for size in range(len(context), 0, -1):
                anchor = "".join(context[-size:])
                if text.count(anchor) == 1:
                    text = text.replace(anchor, anchor + insertion, 1)
                    break
            else:
                raise ValueError("No unique preceding anchor for " + insertion[:80])
            context = []
            continue
        index += 1
    return text


def run(tree, patch, out):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tree, text=True)
    if git("rev-parse", "HEAD").strip() != TAG or git("diff", "--name-only"):
        raise ValueError("Start from the clean frozen v0.2.7 tag")
    parts = sections(patch.read_text())
    for name in sorted(FILES):
        path = tree / name
        if name == "serve/server.py":
            path.write_text(insert_hunks(path.read_text(), parts[name]))
        elif name == "serve/test_frontend.py":
            added = "".join(line[1:] for line in parts[name]
                            if line.startswith("+") and not line.startswith("+++"))
            anchor = "class EmptyAssistantHistory(unittest.TestCase):\n"
            text = path.read_text()
            if text.count(anchor) != 1:
                raise ValueError("Frontend test anchor changed")
            path.write_text(text.replace(anchor, added + "\n\n" + anchor))
        else:
            subprocess.run(["git", "apply", "--check", "--include=" + name, str(patch)], cwd=tree, check=True)
            subprocess.run(["git", "apply", "--include=" + name, str(patch)], cwd=tree, check=True)
    if set(git("diff", "--name-only").splitlines()) != FILES:
        raise ValueError("Unexpected port write set")
    subprocess.run(["git", "diff", "--check"], cwd=tree, check=True)
    (out / "reply-pt-v027.patch").write_text(git("diff", "--", *sorted(FILES)))
    receipt = {"tag_commit": TAG, "native_changes": False,
               "original_patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
               "files": {name: hashlib.sha256((tree / name).read_bytes()).hexdigest() for name in sorted(FILES)}}
    (out / "reply-pt-port.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.tree, args.patch.resolve(), args.out)), flush=True)
