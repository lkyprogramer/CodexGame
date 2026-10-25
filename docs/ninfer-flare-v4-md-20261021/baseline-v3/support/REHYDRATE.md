# Markdown-only 支撑材料恢复

本 ZIP 的成员全部为 `.md`。原 V2 的 Python/Bash 工具、JSON/CSV 账本及证据以 Markdown 代码围栏归档在 `previous-v2/`；没有丢掉 P0—P6 执行依赖，也没有把旧脚本测试冒充本次产品测试。

需要执行旧 P0—P6 的命令时，在本地新建一个空目录，运行以下恢复器。它只写指定目录，不执行恢复出的脚本、不访问网络、不碰生产服务。代码围栏中的源码保留原字节；校验失败即停止。`PACK` 指向恢复目录；阅读文档仍以此 Markdown 包为准。旧 `phase_gate.py` 仅用于 P0—P6，不用于已经被取代的旧 P7—P12。

```python
from pathlib import Path
import hashlib, re, sys
source = Path(sys.argv[1]).resolve() / "previous-v2"
target = Path(sys.argv[2]).resolve()
if not source.is_dir(): raise SystemExit("Missing previous-v2")
if target.exists() and any(target.iterdir()): raise SystemExit("Target must be empty")
# Do not restore into the document package or one of its ancestors.
if target == source.parent or target in source.parents or source.parent in target.parents:
    raise SystemExit("Use a separate target directory")
target.mkdir(parents=True, exist_ok=True)
count = 0
for doc in sorted(source.rglob("*.md")):
    text = doc.read_bytes().decode("utf-8")
    m = re.search(r"<!-- payload-path: (.+) -->", text)
    if not m:
        dest = target / doc.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        continue
    rel = Path(m.group(1))
    if rel.is_absolute() or ".." in rel.parts: raise SystemExit("Unsafe payload path")
    size = int(re.search(r"<!-- payload-bytes: (\d+) -->", text).group(1))
    expected = re.search(r"<!-- payload-sha256: ([0-9a-f]{64}) -->", text).group(1)
    body = text.split("<!-- payload-begin -->\n", 1)[1].split("\n", 1)[1]
    raw = body.encode("utf-8")[:size]
    if hashlib.sha256(raw).hexdigest() != expected: raise SystemExit(f"Hash mismatch: {rel}")
    dest = target / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    count += 1
print(f"Recovered {count} exact text payloads; no scripts executed")
```

将代码保存为包外的 `rehydrate.py` 后：

```bash
python3 rehydrate.py /path/to/ninfer-hyperqwen-v3-md-20261019 /path/to/empty-v2-support
export PACK=/path/to/empty-v2-support
python3 "$PACK/scripts/phase_gate.py" --help
```

V3 新提议的 NInfer 源码、测试目标、benchmark driver 均尚未实现，不由恢复器生成。新任务首先实现文档中的接口及测试，再运行所列命令。
