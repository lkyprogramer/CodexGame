import json, sys, urllib.request
kind, base, pfile = sys.argv[1:4]
def post(path, body):
    r = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=120).read())
raw = json.load(open(pfile))
items = raw if isinstance(raw, list) else raw.get("prompts", raw)
out = []
for it in items[:16]:
    msgs = it["messages"] if isinstance(it, dict) and "messages" in it else [{"role": "user", "content": it if isinstance(it, str) else it.get("prompt") or it.get("content")}]
    try:
        if kind == "astral":
            ids = post("/tokenize", {"messages": msgs})["tokens"]
            text = None
        else:
            text = post("/apply-template", {"messages": msgs})["prompt"]
            ids = post("/tokenize", {"content": text, "add_special": False, "parse_special": True})["tokens"]
        out.append({"ids": ids, "text": text})
    except Exception as e:
        out.append({"error": repr(e)})
print(json.dumps(out, ensure_ascii=False))
