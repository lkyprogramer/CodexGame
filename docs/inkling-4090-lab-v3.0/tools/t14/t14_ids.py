import json, sys, urllib.request
base, out = sys.argv[1], sys.argv[2]; res = []
for s, path in (("a", sys.argv[3]), ("b", sys.argv[4])):
    for i, p in enumerate(json.load(open(path))):
        req = urllib.request.Request(base + "/tokenize", data=json.dumps({"messages": [{"role": "user", "content": p}]}).encode(), headers={"Content-Type": "application/json"})
        res.append({"set": s, "case": i, "ids": json.load(urllib.request.urlopen(req))["tokens"]})
json.dump(res, open(out, "w")); print(len(res))
