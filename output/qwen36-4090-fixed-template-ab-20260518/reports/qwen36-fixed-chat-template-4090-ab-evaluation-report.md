# Qwen3.6 27B Fixed Chat Template A/B 评估报告

日期：2026-05-18  
机器：RTX 4090，直连 `192.168.10.29`  
模型：`/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf`  
测试 binary：`/home/hhtele/llama.cpp-master-pr22673-20260517/build/bin/llama-server`  
生产服务：测试前临时停止，测试完成后已恢复 `openclaw-qwen36-mtp4-128k.service`

## 1. 结论

`froggeric/Qwen-Fixed-Chat-Templates` 对当前 4090 推理优化的价值是“提示模板稳定性 / Agent 多轮格式稳定性 / prompt cache 可预测性”，不是底层 decode speed 的直接优化。

在本次 128k、单并发、MTP n=4、q4_0 KV、prompt cache 开启的 A/B 中：

1. `fixed_v19 + <|think_off|>` 可以作为候选默认模板继续灰度验证。
   - 平均 decode：`74.95 tok/s`，略高于嵌入模板 `73.26 tok/s`。
   - 平均 MTP 接受率：`75.68%`，略高于嵌入模板 `74.22%`。
   - 格式分 / 质量分：与嵌入模板一致，均为 `4.89 / 4.78`。
   - 128k 长前缀 warm cache 命中正常：`cache_n=65617`，冷 `44.93s` -> warm `0.64s`，约 `70.22x`。

2. `fixed_v19 + <|think_on|>` 不适合作为 OpenClaw 默认模式。
   - 虽然平均 decode 最高：`81.09 tok/s`，但严格格式任务大量失败。
   - 平均格式分 / 质量分只有 `2.22 / 2.22`。
   - `OK only`、JSON、patch、long marker 等场景出现空输出或非目标输出。
   - 只能作为少数“允许模型显式思考且不要求严格输出格式”的人工分析模式候选。

3. 当前嵌入模板本身已经能稳定命中 exact prompt cache。
   - 嵌入模板 65k prompt tokens：冷 `44.84s`，warm `0.58s`，`cache_n=65613`，约 `76.65x`。
   - 固定模板没有在“完全相同 prompt 重复请求”上超过嵌入模板；它的潜在收益更可能出现在真实 Agent 多轮历史、tool loop、历史 think 保留/剥离一致性场景。

4. 不建议立刻替换生产 systemd 服务。
   - 本次结果支持新增一个固定模板灰度服务或下一轮真实 OpenClaw agent loop 测试。
   - 若要替换生产，需要先跑真实工具调用、多轮文件编辑、失败重试、JSON schema 输出和长会话回归。

## 2. 外部依据

Hugging Face 页面当前标注为 v19，并说明 llama.cpp / koboldcpp 的接入方式是：

```bash
--jinja --chat-template-file chat_template.jinja
```

页面说明 v19 的主要变化包括移除 empty think poisoning、保留历史 thinking 以保证 prefix KV cache、修复 minijinja 兼容、支持 developer role、支持 `<|think_off|>` / `<|think_on|>` 控制。参考：

- https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates

## 3. 测试配置

共同参数：

```bash
/home/hhtele/llama.cpp-master-pr22673-20260517/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --spec-type draft-mtp \
  --spec-draft-p-min 0.75 \
  --spec-draft-n-max 4 \
  --host 127.0.0.1 \
  --port 19343
```

三条 lane：

| Lane | 模板 | 额外参数 | 用途 |
|---|---:|---|---|
| `embedded_template_mtp4_ctx128` | GGUF / llama.cpp 内置模板 | 无 | 当前基线 |
| `fixed_v19_think_off_mtp4_ctx128` | fixed v19 | `--jinja --chat-template-file ...` + `<|think_off|>` | 候选默认 |
| `fixed_v19_think_on_mtp4_ctx128` | fixed v19 | `--jinja --chat-template-file ...` + `<|think_on|>` | 深度推理对照 |

## 4. 总体结果

| Lane | 请求成功 | 平均 decode tok/s | 平均响应 tok/s | MTP 接受率 | 格式分 | 质量分 | 65k warm speedup | 峰值显存 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| embedded | 9/9 | 73.26 | 40.46 | 74.22% | 4.89 | 4.78 | 76.65x | 21808 MiB |
| fixed v19 think_off | 9/9 | 74.95 | 42.80 | 75.68% | 4.89 | 4.78 | 70.22x | 21812 MiB |
| fixed v19 think_on | 9/9 | 81.09 | 58.47 | 73.71% | 2.22 | 2.22 | 43.62x | 21812 MiB |

解释：

- `think_off` 的性能差异很小，但没有质量退化，显存增量只有约 `4 MiB`。
- `think_on` 看起来更快，主要是因为多个严格任务返回空内容或不完整内容，不能视为有效吞吐提升。
- 三条 lane 的 128k 服务峰值显存基本一致，模板文件本身不构成显存压力。

## 5. 分项结果

### 5.1 fixed v19 think_off

| Case | 结果 | decode tok/s | prompt_ms | cache_n | 格式/质量 | 备注 |
|---|---:|---:|---:|---:|---:|---|
| stream TTFT OK | 成功 | N/A | N/A | N/A | 5.0 / 5.0 | TTFT `0.157s` |
| short OK | 成功 | 39.66 | 84.86 | 0 | 5.0 / 5.0 | 输出 `OK` |
| JSON tool | 成功 | 100.09 | 185.48 | 0 | 5.0 / 5.0 | raw minified JSON |
| unified diff | 成功 | 96.64 | 146.75 | 0 | 5.0 / 4.5 | 无 markdown fence |
| 中文 review | 成功 | 68.03 | 191.50 | 0 | 4.5 / 4.5 | 指出 `forEach async` 等待与一致性问题 |
| agent history JSON | 成功 | 70.16 | 237.70 | 0 | 5.0 / 5.0 | 带历史 `<think>` 仍输出合法 JSON |
| long generation 768 | 成功 | 62.65 | 154.27 | 0 | 4.5 / 4.0 | 打满 768 tokens |
| 65k marker cold | 成功 | 81.10 | 44297.60 | 0 | 5.0 / 5.0 | 精确召回 marker |
| 65k marker warm | 成功 | 81.27 | 122.50 | 65617 | 5.0 / 5.0 | prompt cache 命中 |

### 5.2 embedded baseline

基线也很稳，尤其是 exact prompt cache：

- 65k cold：`44.84s`，`prompt_ms=44259.15`，`cache_n=0`
- 65k warm：`0.58s`，`prompt_ms=121.90`，`cache_n=65613`
- 平均质量与 fixed think_off 相同。

这说明 fixed template 不是当前“完全相同 prompt 重复请求”的必要条件；真实价值需要放到多轮 Agent 历史动态变化里继续验证。

### 5.3 fixed v19 think_on

`think_on` 失败特征：

- `short_ok` 输出为空，格式/质量 `1.0 / 1.0`。
- `json_tool` 输出为空或非 JSON，格式/质量 `1.0 / 2.0`。
- `patch_unified_diff` 输出未满足 diff 格式，格式/质量 `1.0 / 2.5`。
- `long_context_marker` 没有返回 marker，格式/质量 `1.0 / 1.0`。
- `agent_history_json` 反而成功，说明它不是彻底不可用，而是对严格格式短任务有明显风险。

结论：`think_on` 不进入默认服务配置。

## 6. 对 OpenClaw 的影响判断

### 有帮助的地方

1. 多轮 Agent loop 的历史渲染更有机会稳定。
   - fixed v19 针对 empty think poisoning、历史 thinking 保留、tool loop retry、developer role 做了专门修复。
   - 这些问题更贴近 OpenClaw 的长期 coding agent 场景，而不是单轮 benchmark。

2. 对严格 JSON / patch 输出没有引入退化。
   - `think_off` 下 JSON、patch、agent history JSON 都通过。

3. 成本低。
   - 只多一个模板文件和启动参数。
   - 本轮显存峰值从 `21808 MiB` 到 `21812 MiB`，差异可忽略。

### 没帮助或边界

1. 不会直接解决底层 decode 极限。
   - decode 主要仍由量化、KV cache、MTP 接受率、上下文长度、CUDA kernel、GPU 功耗/温度决定。

2. 不会修复 TurboQuant PR146 的 `/` 退化。
   - 之前 PR146 no-spec 也异常，属于 binary/model generation path 兼容问题，不是 chat template 层问题。

3. 对 exact prompt cache 的提升不明显。
   - 当前嵌入模板已经能在完全相同 prompt 上获得 `76.65x` warm speedup。

## 7. 推荐配置

下一轮灰度服务可用：

```bash
/home/hhtele/llama.cpp-master-pr22673-20260517/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL-FixedTemplate \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --spec-type draft-mtp \
  --spec-draft-p-min 0.75 \
  --spec-draft-n-max 4 \
  --jinja \
  --chat-template-file /home/hhtele/qwen36-fixed-template-ab-20260518/chat_template.jinja \
  --host 0.0.0.0 \
  --port 18343
```

默认系统提示建议包含：

```text
You are OpenClaw's local coding agent model. Follow exact output format requirements. Do not use markdown fences unless explicitly requested. <|think_off|>
```

不建议把 `<|think_on|>` 放进默认系统提示。

## 8. 下一轮测试建议

若要决定是否替换生产服务，下一轮不再做单轮 synthetic benchmark，而应直接跑 OpenClaw 真实 Agent trace：

1. 20-50 轮连续 coding agent 对话。
   - 每轮包含读取文件、失败命令、修复、复测、总结。
   - 记录 JSON 合法率、工具调用有效率、空输出率、markdown fence 泄漏率。

2. 带失败重试的 tool loop。
   - 第一次工具返回 `Traceback` 或 schema validation error。
   - 观察第二轮是否修正 action，而不是重复错误调用。

3. 长会话 prompt cache。
   - 32k、64k、96k、128k 逐步增长历史。
   - 记录每轮 `cache_n`、`prompt_ms`、显存、TTFT。

4. 与当前生产服务同 prompt 对照。
   - 至少保留 embedded baseline 与 fixed think_off 两个服务轮流跑同一 trace。
   - 以真实任务完成率优先，其次才看 tok/s。

## 9. 原始文件

- 测试脚本：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-fixed-template-ab-20260518/remote/qwen4090_fixed_template_ab_eval.py`
- wrapper：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-fixed-template-ab-20260518/remote/run_fixed_template_ab_eval_wrapper.sh`
- 模板文件：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-fixed-template-ab-20260518/remote/chat_template.jinja`
- 原始结果：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-fixed-template-ab-20260518/raw/remote-copy/results`
- 汇总 JSON：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-fixed-template-ab-20260518/raw/remote-copy/results/summary.json`

## 10. 恢复验证

测试结束后已验证：

- `openclaw-qwen36-mtp4-128k.service`：`active`
- systemd enabled：`enabled`
- 本机后端：`http://127.0.0.1:18343/v1/models` 正常
- NGINX token 入口：`http://192.168.10.29:28343/v1/models` 带 token 正常
- NGINX 无 token：返回 `401`
- 临时 `19343` 测试进程：无残留
- 恢复后 GPU：约 `21866 MiB` 已用，生产服务常驻
