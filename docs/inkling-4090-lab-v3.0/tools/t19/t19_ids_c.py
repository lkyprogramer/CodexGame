#!/usr/bin/env python3
"""Chat-template token ids for prompts_set_c.json from Astral's /tokenize (same path V2 proved
equal to llama.cpp's). usage: t19_ids_c.py <astral url> <prompts_set_c.json> <out ids.json>"""
import json
import sys
import urllib.request

base, src, out = sys.argv[1:4]
res = []
for i, p in enumerate(json.load(open(src))):
    req = urllib.request.Request(base + "/tokenize", data=json.dumps({"messages": [{"role": "user", "content": p}]}).encode(),
                                 headers={"Content-Type": "application/json"})
    res.append({"set": "c", "case": i, "ids": json.load(urllib.request.urlopen(req))["tokens"]})
json.dump(res, open(out, "w"))
print(len(res))
