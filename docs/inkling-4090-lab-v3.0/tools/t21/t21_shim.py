#!/usr/bin/env python3
"""T21 draft-precision arm: a stand-in native checkpoint for llama.cpp's --dspark export. The
native directory has mtp.safetensors but not the target shards; the export needs the target's
unembed (for the fold) and embed_norm. Both are taken from the A1 GGUF (output.weight is Q8_0,
dequantized), which is what Astral itself folds with. Writes <out>/ with symlinks to the native
files, model-00001-of-00001.safetensors holding the two tensors, and a two-entry index.
usage: t21_shim.py <native dir> <A1 gguf> <out dir>"""
import json
import os
import sys

import numpy as np
import torch
from gguf import GGUFReader
from gguf.quants import dequantize
from safetensors.torch import save_file

native, a1, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
for f in os.listdir(native):
    if f.startswith("model") and f.endswith((".safetensors", ".json")):
        continue
    d = os.path.join(out, f)
    if not os.path.lexists(d):
        os.symlink(os.path.join(native, f), d)
r = GGUFReader(a1)
t = {x.name: x for x in r.tensors}
want = {"model.llm.unembed.weight": "output.weight", "model.llm.embed_norm.weight": None}
norm = [n for n in t if "norm" in n and not n.startswith("blk.")]
print("non-block norms in A1:", norm)
want["model.llm.embed_norm.weight"] = next(n for n in norm if "embd" in n or "embed" in n)
res = {}
for hf, g in want.items():
    x = t[g]
    a = dequantize(x.data, x.tensor_type).reshape([int(v) for v in reversed(x.shape)]) if x.tensor_type.name not in ("F32", "F16", "BF16") or True else None
    a = np.asarray(a, dtype=np.float32)
    print(hf, "<-", g, x.tensor_type.name, a.shape)
    res[hf] = torch.from_numpy(a.copy()).to(torch.bfloat16)
save_file(res, os.path.join(out, "model-00001-of-00001.safetensors"), metadata={"format": "pt"})
json.dump({"metadata": {}, "weight_map": {k: "model-00001-of-00001.safetensors" for k in res}}, open(os.path.join(out, "model.safetensors.index.json"), "w"))
