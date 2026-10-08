"""Production-shaped synthetic agent session for the review harness (not production data).

Shape targets taken from the slowest schema-20 record: ~890 KB rendered, 769 messages,
12 tools, and a last real user query ~20 agent turns before the end.

Usage: python3 gen_prodshape.py [MESSAGES=769] [TURNS_SINCE_USER=20] [TOOL_SCALE=1.0] > out.jsonl
Needs raw/{zh_docs,en_docs,cpp_code,json_logs}.txt (any UTF-8 corpora of ~512 KiB each; the
review used Chinese markdown docs, the NInfer README/docs, NInfer C++ sources and JSONL logs).
A user message is also inserted every 60 agent turns, so the effective value is capped by the
distance to the last such insertion (about 20 turns for 769 messages).
The review used TOOL_SCALE=0.78, which renders to ~903 KB.
"""
import json
import random
import sys

rng = random.Random(20260925)
raw = {k: open(f"raw/{k}.txt", encoding="utf-8", errors="ignore").read()
       for k in ("zh_docs", "en_docs", "cpp_code", "json_logs")}


def snippet(kind, n):
    text = raw[kind]
    start = rng.randrange(0, max(1, len(text) - n))
    return text[start:start + n]


target_messages = int(sys.argv[1]) if len(sys.argv) > 1 else 769
turns_since_user = int(sys.argv[2]) if len(sys.argv) > 2 else 20
tool_scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
user_every = 60

# Solve for agent turns P: 1 system + users + 2P == target_messages.
P = (target_messages - 1) // 2
while True:
    users = {t for t in range(0, P, user_every)} | {P - turns_since_user}
    if 1 + len(users) + 2 * P <= target_messages:
        break
    P -= 1

tools = []
for i in range(12):
    tools.append({"type": "function", "function": {
        "name": f"tool_{i}", "description": snippet("en_docs", 300),
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "file path"},
            "query": {"type": "string", "description": "search query"}},
            "required": ["path"]}}})

messages = [{"role": "system", "content": snippet("en_docs", 12000) + "\n" + snippet("zh_docs", 6000)}]
ends = []
for t in range(P + 3):
    if t in users:
        messages.append({"role": "user", "content": snippet("zh_docs", rng.randint(80, 600))})
    args = json.dumps({"path": f"src/module{t}/File{t}.java", "query": snippet("en_docs", 40)},
                      ensure_ascii=False)
    messages.append({"role": "assistant", "content": snippet("zh_docs", rng.randint(0, 200)),
                     "reasoning_content": snippet(rng.choice(["en_docs", "zh_docs"]),
                                                  rng.randint(300, 1400)),
                     "tool_calls": [{"id": f"call_{t}", "type": "function",
                                     "function": {"name": f"tool_{t % 12}", "arguments": args}}]})
    kind = rng.choice(["cpp_code", "cpp_code", "json_logs", "zh_docs", "en_docs"])
    messages.append({"role": "tool", "tool_call_id": f"call_{t}",
                     "content": snippet(kind, int(rng.randint(200, 1500) * tool_scale))})
    ends.append(len(messages))

for k in range(4):
    msgs = messages[:ends[P - 1 + k]]
    print(json.dumps({"case_id": f"prodshape-turn-{k:02d}", "request": {
        "messages": msgs, "tools": tools, "reasoning_effort": "medium",
        "preserve_thinking": True}}, ensure_ascii=False))
