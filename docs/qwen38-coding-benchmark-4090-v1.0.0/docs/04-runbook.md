# 04 · 标准运行手册

## A. 冻结环境

```bash
python3 scripts/collect_environment.py \
  --server-command './llama-server ...完整参数...' \
  --output environment.json
python3 scripts/hash_model.py /models/model.gguf
```

保存 server commit、构建选项、启动命令、Template 文件与 SHA-256。任何影响行为或显存的变更都创建新的 Config ID，不能覆盖旧卡。

## B. 验证基准包

```bash
python3 scripts/check_manifest.py
python3 scripts/verify_release.py
qcb validate
```

`verify_release.py` 是发布级自检；它会执行单元/端到端测试、目录与泄漏检查、参考实现和故障基线。故障基线以独立临时工作区运行，超时会终止整个进程组，避免遗留 Java 子进程污染后续样本。

## C. 启动并预热模型

1. 使用冻结的 server command 启动一个 Config；
2. 用非正式题执行固定次数 warm-up；
3. 记录稳定后的 GPU 时钟、温度、显存、prompt/decode 速度；
4. 清空 warm-up 对话，不共享 KV；
5. 按 Latin-square block 开始正式题。

Warm-up 不得包含正式题参考答案或隐藏测试。

## D. 标准工具边界

### Patch / Agent

- `list_files`
- `read_file`
- `search`
- `apply_patch`
- `run_tests`（只运行任务声明的公开测试命令）

### Code Review

只提供 `list_files`、`read_file`、`search`。审查题不能修改工作区，也不能运行任意 shell。

所有路径都限制在临时 workspace。`hidden_tests/` 与 `reference/` 从未复制到 workspace。工具参数错误与公开测试失败分开记录：后者是有效调用的失败结果，不是格式错误。

## E. 分阶段运行

```bash
qcb run --config config/model-a.toml --suite smoke --seeds 42 --output results/model-a
qcb run --config config/model-a.toml --suite core --seeds 11,29,47 --output results/model-a
qcb run --config config/model-a.toml --suite finalists --seeds 11,29,47,71,97 --output results/model-a
```

单题诊断：

```bash
qcb run --config config/model-a.toml --suite core --task AT001 --seeds 42 --output diagnostics/model-a
```

诊断运行不得选择性合并进正式结果。

## F. 中断与恢复

结果文件存在时默认报错：

```bash
# 只跳过已经存在的 (task, seed)
qcb run ... --resume

# 删除结果文件并从头运行
qcb run ... --overwrite
```

`--resume` 会检查既有记录中的 model ID、Lane 和 Suite。禁止把不同配置写入同一个 JSONL。`--overwrite` 只适用于明确废弃整轮结果，不能用于把模型失败“洗掉”。

## G. 故障分类

| 情况 | Outcome/处理 | 是否允许重跑 |
|---|---|---|
| Endpoint 连接失败、服务崩溃 | `endpoint_error` / infrastructure | 按预声明规则统一重跑 |
| 无最终 diff/JSON | `invalid_output` | 否 |
| Diff 不能应用 | `patch_failed` | 否 |
| 超工具预算 | `tool_budget_exhausted` | 否 |
| 隐藏验证失败 | 正常模型失败 | 否 |
| 模型补丁导致测试死锁 | 正常模型失败并保留超时日志 | 否 |
| OOM | 部署可运行性失败；记录 load/prefill/decode 阶段 | 仅统一配置修正后新建 Config |

Endpoint 请求重试次数写入每条记录。模型输出错误不能使用 endpoint retry。

## H. 结果与 Artifact 审计

报告前先运行机器审计：

```bash
python3 scripts/audit_results.py \
  --results results/<model>/<model>-normalized-core.jsonl \
  --check-artifacts \
  --json reports/<model>-normalized-core-audit.json
```

该步骤验证 Suite×Seed 完整性、重复记录、配置/推理参数混杂、模型哈希状态和 artifact 完整性。随后每个 block 至少随机抽查：

- 模型没有看到 hidden/reference；
- Review 请求中没有写工具；
- Tool trace 路径没有逃出 workspace；
- `final.patch` 与最终工作区一致；
- Verifier 输出与 JSONL 一致；
- 公开测试失败没有被计作 invalid tool call；
- reasoning/timing 缺失时为 `null/N/A`；
- GGUF、Config、Prompt、Task metadata 哈希可追溯。

## I. 报告顺序

1. 每模型报告；
2. 相同 Lane/Suite 的完整配对比较；
3. 多模型质量门槛排行榜；
4. 失败根因和补丁人工审查；
5. Optimized 消融；
6. 私有 Java 回放；
7. 最终部署建议。
