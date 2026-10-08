# 本包工具手册

| 命令 | 已实现功能 | 不代表什么 |
|---|---|---|
| `bash scripts/self_check.sh` | CPU单测、语法、文档/任务检查 | 不是GPU测试 |
| `bash scripts/preflight.sh` | 只读采集机器/工具/服务信息 | 不改驱动，不加载模型 |
| `python3 -m poc_tools.cli weights DIR --out FILE` | safetensors头与大小审计 | 不证明全部device布局 |
| `... lock-model DIR --out FILE` | 流式SHA锁定模型文件 | 不生成Marlin权重 |
| `... memory --weight-gib X` | 明确KV/state/workspace估算 | 不是真实显存峰值 |
| `... lint MANIFEST` | PoC SM89禁用特性/资源粗检 | 不能替代Kern verifier或SASS |
| `python3 -m poc_tools.build_prompts ...` | 使用本地tokenizer生成精确长度token数组 | 不假定服务已接受长度 |
| `python3 -m poc_tools.http_probe ...` | SSE/usage/TTFT/trace采集 | SSE帧数不是token数 |
| `python3 -m poc_tools.numeric_check ...` | 同名NPZ数组差异 | 不替用户生成GPUoracle |
| `python3 -m poc_tools.java_runner ...` | Pi真实工具循环+独立测试验证 | 不是全能力benchmark |
| `python3 scripts/guard_gpu.py ...` | 显式维护租约、正常恢复 | 不能处理断电/SIGKILL |
| `bash scripts/run_qualification.sh` | 执行T22生成的本机资格计划 | 不是自动完成GPU引擎开发 |
| `... cli report evidence.json` | fail-closed证据裁决 | 不是防恶意伪造的硬件证明 |

`configs/qualification.example.json`只是展示argv编排的探索例子，故意不能当完整资格套件。正式文件由AI在实现GPU exporter、cache/lifecycle adapter和candidate launcher之后生成；脚本缺该文件时BLOCKED，不擅自创建假的结果。

依赖：CPU基础工具用Python标准库；NPZ比较需要numpy；精确token生成需要tokenizers；Java夹具需要javac/java；Pi测试需要本机Pi。requirements-tools.txt应安装在隔离venv。不要修改用户全局Python/Node环境。


## 工具依赖安装（非GPU开发环境）

```bash
# 推荐离线：联网机先用目标Python/架构下载requirements-tools.txt中的wheels。
WHEELHOUSE=/data/offline/wheelhouse bash scripts/setup_tools.sh
# 或明确允许联网：ALLOW_NETWORK=1 bash scripts/setup_tools.sh
source .venv/bin/activate
bash scripts/self_check.sh
```

setup_tools只创建本包.venv，不安装驱动、不停止生产。未提供wheelhouse且未授权联网时退出78。它不负责安装Rust/CUDA/vLLM，这些属于T01的独立环境锁。
