from pathlib import Path
p = Path("/home/hhtele/ninfer-4090/launch/production-18343.sh")
t = p.read_text()
t = t.replace("ninfer-request-${STAMP}.jsonl", "ninfer-request.jsonl-${STAMP}")
p.write_text(t)
print([ln for ln in t.splitlines() if "DEST=" in ln])
