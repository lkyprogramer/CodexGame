import json, subprocess, sys
tk_bin, gguf, tj = sys.argv[1:4]
from tokenizers import Tokenizer
hf = Tokenizer.from_file(tj)
cases = ["The capital of France is", "Hello, world!  Multiple   spaces\n\nand newlines\t tabs",
  "自循环模型在 4090 上的推理速度如何？", "def f(x):\n    return x**2 + 3.14159  # comment",
  "emoji 🚀🔥 and accents: café naïve Ωμέγα", "日本語のテキストと한국어 텍스트", "<|im_start|>user\nhi<|im_end|>",
  "1234567890 0.000001 1e-9 ¥€$", "   leading spaces", "URL https://example.com/a?b=c&d=e"]
res = []
for c in cases:
    out = subprocess.run([tk_bin, "-m", gguf, "-p", c, "--ids", "--log-disable", "--no-bos"], capture_output=True, text=True)
    line = [l for l in out.stdout.strip().splitlines() if l.startswith("[")]
    ll = json.loads(line[-1]) if line else None
    h = hf.encode(c, add_special_tokens=False).ids
    res.append({"text": c, "match": ll == h, "llama": ll, "hf": h, "err": None if line else out.stdout[-400:] + out.stderr[-400:]})
print(json.dumps({"all_match": all(r["match"] for r in res), "n": len(res), "cases": res}, ensure_ascii=False, indent=1))
