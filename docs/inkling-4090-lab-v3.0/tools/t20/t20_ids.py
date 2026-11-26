#!/usr/bin/env python3
"""T20: chat-template token ids from Astral's /tokenize (V2: equal to llama.cpp's).

  t20_ids.py <astral url> <out ids.json> b <t14 ids.json>          set-b prompts (copied from T14)
  t20_ids.py <astral url> <out ids.json> d <doc spec>...            long documents; a spec is
      path[+path...]; the first 24000 characters become one user message
"""
import json
import sys
import urllib.request

base, out, kind = sys.argv[1:4]


def tokenize(text):
    req = urllib.request.Request(base + "/tokenize", data=json.dumps({"messages": [{"role": "user", "content": text}]}).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["tokens"]


res = []
if kind == "b":
    res = [{"case": len(res), "ids": e["ids"]} for e in json.load(open(sys.argv[4])) if e["set"] == "b"]
    res = [{"case": i, "ids": e["ids"]} for i, e in enumerate(res)]
elif kind == "d":
    for i, spec in enumerate(sys.argv[4:]):
        text = "\n\n".join(open(p, encoding="utf-8").read() for p in spec.split("+"))[:24000]
        res.append({"case": i, "src": spec.split("/")[-1], "ids": tokenize("Read the following document and list its main points.\n\n" + text)})
else:
    sys.exit("kind must be b or d")
json.dump(res, open(out, "w"))
print(len(res), [len(e["ids"]) for e in res])
