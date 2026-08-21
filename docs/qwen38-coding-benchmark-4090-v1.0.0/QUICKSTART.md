# QCB-4090 快速执行手册

## 1. 解压后先验证基准包

```bash
python3 scripts/check_manifest.py
python3 scripts/verify_release.py
```

`verify_release.py` 会检查：Python 编译、单元/端到端测试、48 题目录与泄漏边界、48 个参考实现、48 个故障基线以及合成报告管线。缺少 Python 3.11、Git 或 JDK 17+ 时会失败。

## 2. 启动 CLI

执行器可直接运行，不要求安装第三方依赖：

```bash
python3 -m qcb.cli --help
```

需要 `qcb` 短命令时再做可选安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --no-deps -e .
qcb --help
```

在完全离线且虚拟环境没有 setuptools 的机器上，直接使用 `python3 -m qcb.cli` 或 `python3 scripts/*.py`，无需执行安装步骤。执行器本身只使用 Python 标准库；题目不访问网络，也不下载 Maven、Gradle 或 pip 依赖。

## 3. 冻结环境和模型

```bash
python3 scripts/collect_environment.py \
  --server-command './llama-server ...完整参数...' \
  --output environment/original-q4km.json

python3 scripts/hash_model.py /models/model.gguf
cp config/normalized.example.toml config/original-q4km.toml
```

必须替换：

- GGUF 的真实绝对路径；
- 64 位 SHA-256；
- Config ID、Quant、Template ID；
- Endpoint 地址与模型名；
- 实际 Context、reasoning、MTP 元数据。

执行器只在 Suite 开始时校验一次大模型哈希，避免每题重复读取几十 GB。

## 4. 检查本地端点

端点必须实现：

```text
POST http://127.0.0.1:8080/v1/chat/completions
```

标准 Suite 要求可用的 OpenAI-compatible tool calling：

- Patch/Agent：`list_files`、`read_file`、`search`、`apply_patch`、`run_tests`；
- Code Review：只暴露 `list_files`、`read_file`、`search`。

`tool_mode=false` 不属于标准榜。只想做全文单轮诊断时，可用 `scripts/build_context_bundle.py` 生成可见文件拼接，并单独报告。

不同 llama.cpp 版本可能不接受 `reasoning_effort`，或不返回 reasoning/timings/MTP 字段。不要伪造 0；框架会保存为 `N/A`，差异写入环境报告。

## 5. 生成模型轮换顺序

```bash
python3 scripts/latin_square_order.py \
  original sharp grug fable salience cold-fusion
```

每个 block 对相同题目和 Seed 轮换模型顺序。不要先把 A 全跑完再跑 B。

## 6. 分阶段执行

```bash
# Gate：12 题 × 1 Seed
qcb run \
  --config config/original-q4km.toml \
  --suite smoke \
  --seeds 42 \
  --output results/original

# Main：32 题 × 3 Seeds
qcb run \
  --config config/original-q4km.toml \
  --suite core \
  --seeds 11,29,47 \
  --output results/original

# Final：27 题 × 5 Seeds
qcb run \
  --config config/original-q4km.toml \
  --suite finalists \
  --seeds 11,29,47,71,97 \
  --output results/original
```

结果文件已存在时，执行器默认拒绝继续，防止重复样本：

```bash
# 仅补齐缺失 task/seed
qcb run ... --resume

# 明确删除并重跑该结果文件
qcb run ... --overwrite
```

禁止为模型失败选择性使用 `--overwrite`。正式重跑只能依据预先声明的 infrastructure-error 规则。

## 7. 先审计结果，再生成报告与比较

每个结果文件在进入统计前必须通过完整性与配置一致性审计：

```bash
python3 scripts/audit_results.py \
  --results results/original/original-normalized-core.jsonl \
  --check-artifacts \
  --json reports/original-core-audit.json

# 等价 CLI
qcb audit \
  --results results/original/original-normalized-core.jsonl \
  --check-artifacts
```

审计会拒绝：缺失或重复的 `(task, seed)`、混合模型/Lane/Suite、混合配置或受控推理参数、模型哈希不匹配，以及缺失的运行 artifact。只有审计通过的数据才能进入以下报告流程。

```bash
python3 scripts/generate_report.py \
  --results results/original/original-normalized-core.jsonl \
  --output reports/original-core.md \
  --json reports/original-core.json

python3 scripts/compare_models.py \
  --model-a results/original/original-normalized-core.jsonl \
  --model-b results/grug/grug-normalized-core.jsonl \
  --output reports/original-vs-grug.md \
  --json reports/original-vs-grug.json

python3 scripts/generate_leaderboard.py \
  --input results/original/original-normalized-core.jsonl \
  --input results/grug/grug-normalized-core.jsonl \
  --input results/fable/fable-normalized-core.jsonl \
  --output reports/leaderboard.md \
  --json reports/leaderboard.json
```

两模型比较要求 Lane、Suite 和全部 `(task, seed)` 完整配对；缺失或重复会直接报错。排行榜先执行质量门槛，再比较效率，并输出 Pairwise Bootstrap、McNemar 与 Holm 修正。

## 8. 第一轮推荐矩阵

```text
Original Q4_K_M / official template
Original Q4_K_M / Sharp template
Grug v1.1 Q4_K_M
Fable-Distill Q4_K_M
Salience R5 Q4_K_M
Cold Fusion Q4_K_M
```

先做同量化档、同工具、同 Context 的 Normalized 横评。Pearson coding-aware IQ4_XS、Q5_K_M、Ridge 和 MTP 属于第二轮量化/部署实验，不能混入权重能力结论。

## 9. 最终交付

归档以下内容：

```text
benchmark ZIP + SHA-256
每个模型 TOML
环境 JSON
Latin-square block
完整 server 启动命令和日志
JSONL + artifacts
单模型报告
Pairwise 报告
排行榜
人工补丁复盘
私有 Java 回放报告
```
