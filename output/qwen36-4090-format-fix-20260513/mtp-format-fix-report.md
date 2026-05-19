# MTP 格式问题优化报告

## 结论

当前 4090 上的 MTP llama.cpp 分支暂不需要先改源码。上一轮 `<think></think>` 泄漏的直接原因是启动参数同时用了：

```bash
-rea off --reasoning-format none
```

其中 `--reasoning-format none` 明确表示“把 thoughts 原样留在 `message.content`”，因此会绕过 Qwen3 chat parser 对空 `<think></think>` 的消费逻辑。把 `--reasoning-format none` 去掉，只保留 `-rea off`，或者只使用 `--chat-template-kwargs '{"enable_thinking":false}'`，chat endpoint 输出即恢复干净。

## 源码核对

当前 MTP 分支 `/home/hhtele/llama.cpp-mtp-unsloth-20260513` 已经包含 Qwen3 disabled-thinking 的解析逻辑：

- `common/chat.cpp` 中 Qwen3 parser 在 `extract_reasoning && !inputs.enable_thinking` 时会消费空 `<think></think>`。
- `extract_reasoning` 的条件是 `inputs.reasoning_format != COMMON_REASONING_FORMAT_NONE`。
- 因此手动传入 `--reasoning-format none` 会禁用该路径。

旧 `/opt/llama.cpp` 的本地补丁集中在：

- `common/chat.cpp`
- `common/chat.h`
- `common/chat-auto-parser.h`
- `common/chat-diff-analyzer.cpp`
- `tools/server/server-common.cpp`
- `tools/server/server-task.cpp`

旧补丁作用是给更老的 parser 增加 Qwen3 fallback；当前 MTP 分支已经有等价的核心能力，问题不在缺源码补丁，而在启动参数把解析关掉。

## 实测结果

### 格式探测

| Lane | chat JSON 输出 | completion endpoint | 结论 |
| --- | --- | --- | --- |
| `mtp_fmt_rea_off_auto` | 干净，无 `<think>` | 仍输出真实 thinking | 推荐 |
| `mtp_fmt_kwargs_no_think` | 干净，无 `<think>` | 仍输出真实 thinking | 可用 |
| `mtp_fmt_rea_off_kwargs` | 干净，无 `<think>` | 仍输出真实 thinking | 可用但冗余 |

注意：`/completion` endpoint 不适合作为 OpenAI chat 替代，它会输出真实 thinking 过程。

### 完整 6-case 回归

Lane：`mtp_spec4_rea_off_auto_full`

| 指标 | 结果 |
| --- | ---: |
| case_count | 6 |
| ok_count | 6 |
| error_count | 0 |
| avg_tokens_per_sec | 49.63 |
| median_tokens_per_sec | 49.98 |
| avg_elapsed_s | 4.91 |
| long_context_pass | true |

关键输出确认：

- `instruction_following`：返回纯 JSON，无 `<think>`。
- `niah_1200_words`：只返回 `NEEDLE_CODE_4090_MTP_DFLASH`，无额外包裹。

## 推荐启动命令

```bash
cd /home/hhtele/llama.cpp-mtp-unsloth-20260513
./build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias qwen36-mtp-udq4xl \
  -ngl 99 -c 32768 -np 1 -fa on \
  -ctk q4_0 -ctv q4_0 \
  --spec-type mtp --spec-draft-n-max 4 \
  -rea off \
  --temp 0 --top-p 1 \
  --host 0.0.0.0 --port 18704
```

不要再加：

```bash
--reasoning-format none
```

## 如果仍要做源码防呆

可选源码优化是：在 `tools/server/server-common.cpp` 里检测 `enable_thinking=false` 且 Qwen3 template 会生成空 `<think></think>` 时，禁止或覆盖 `--reasoning-format none`。但这会改变 llama.cpp 对 `reasoning-format none` 的官方语义，风险高于收益。

更稳妥的工程策略是：

1. 启动脚本层固定使用 `-rea off`。
2. 测试脚本增加断言：OpenAI chat content 不得以 `<think>` 开头。
3. 报告中明确 `/completion` endpoint 不用于 JSON/exact-match 质量测试。

## 记录位置

- Raw：`output/qwen36-4090-format-fix-20260513/raw/`
- Logs：`output/qwen36-4090-format-fix-20260513/logs/`
- 本报告：`output/qwen36-4090-format-fix-20260513/mtp-format-fix-report.md`

## 恢复状态

- `qwen35-35b-a3b-uncensored.service` 已恢复为 `active`。
- GPU 恢复到约 `21870 MiB used / 2347 MiB free`。
