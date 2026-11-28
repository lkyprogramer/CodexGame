#!/usr/bin/env python3
"""T43 Phase 0: target directory for llama.cpp's DFlash2 converter without the 18 GB native shard.

  t43_shim.py <A1.gguf> <native dir> <out dir>
The converter (conversion/qwen.py, DFlashModel) reads the target's config / tokenizer and, for an
Inkling2 target, one tensor: model.llm.embed_norm.weight. A1 stores that norm unquantized (F32), so it
is copied from A1's GGUF; every other file is a symlink to the native directory. The index is replaced
by one that maps only that tensor to a small safetensors file.
"""
import json, os, sys
from pathlib import Path
import numpy as np
from gguf import GGUFReader
from safetensors.numpy import save_file

a1, native, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
for f in native.iterdir():
    if f.name in ("model.safetensors.index.json",) or f.suffix == ".safetensors":
        continue
    dst = out / f.name
    if not dst.exists():
        os.symlink(f.resolve(), dst)
r = GGUFReader(a1)
cand = [t for t in r.tensors if "norm" in t.name and t.n_elements == 2304 and "blk." not in t.name]
names = [(t.name, t.tensor_type.name) for t in cand]
print("candidates", names)
t = [t for t in cand if t.name in ("token_embd_norm.weight", "embd_norm.weight", "token_embd_norm")]
if len(t) != 1:
    sys.exit("embed norm tensor not identified among %s" % names)
t = t[0]
if t.tensor_type.name != "F32":
    sys.exit("embed norm is %s, not F32" % t.tensor_type.name)
w = np.array(t.data, dtype=np.float32).reshape(-1)
save_file({"model.llm.embed_norm.weight": w}, str(out / "model-shim.safetensors"))
json.dump({"metadata": {}, "weight_map": {"model.llm.embed_norm.weight": "model-shim.safetensors"}},
          open(out / "model.safetensors.index.json", "w"))
print("embed_norm from", t.name, "mean", float(w.mean()), "std", float(w.std()))
