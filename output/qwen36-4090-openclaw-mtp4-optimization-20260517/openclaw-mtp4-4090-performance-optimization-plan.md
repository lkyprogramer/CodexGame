# OpenClaw Qwen3.6 27B MTP4 4090 推理性能优化方案

日期：2026-05-17  
目标机器：RTX 4090，通过 GCP 跳板访问 `100.107.189.100`  
当前服务：`openclaw-qwen36-mtp4-128k.service`  
目标：在不升级 CUDA、不破坏现有 128k MTP4 稳定服务的前提下，继续压榨 OpenClaw 基础模型推理性能，并保留质量评分与可回滚路径。

## 1. 直接结论

当前 4090 上的 MTP4 128k 服务已经吃到了主要确定性收益：

```text
-ngl 99
-fa on
-ctk q4_0
-ctv q4_0
--spec-type mtp
--spec-draft-n-max 4
--cache-prompt
-c 131072
-np 1
CUDA graphs enabled at build time
```

继续提升性能的重点不应是盲目堆现有参数，而应集中在五个方向：

1. 旁路构建并测试新版 llama.cpp MTP：重点验证 `ngram-mod,draft-mtp` 链式 speculative。
2. 优化 OpenClaw prompt 结构，让 prompt cache 能稳定命中长前缀。
3. 对 MTP 参数做小矩阵 sweep：`--spec-draft-n-max=3/4/5/6`。
4. 增加 32k/64k 低延迟 profile，与现有 128k 长上下文 profile 分离。
5. 小心测试 `--cache-ram`、`--ctx-checkpoints`、`-b/-ub`，但不把它们当第一收益来源。

不建议继续把 256k 作为当前可用主线。之前实测 `-c 262144 -np 1` 在约 53k prompt processing 处 CUDA OOM，即使降低 `-b/-ub` 和 cache 参数仍失败。

## 2. 当前运行态证据

### 2.1 访问路径

当前本机不能直接 SSH 4090，需要：

```bash
gcloud compute ssh \
  --zone "us-central1-a" \
  "instance-20260222-145427" \
  --project "project-d4e4f88c-f262-47af-b5b" \
  --tunnel-through-iap
```

从 GCP 跳板访问 4090：

```bash
sshpass -p hhtele ssh hhtele@100.107.189.100
```

### 2.2 服务状态

核查结果：

```text
openclaw-qwen36-mtp4-128k.service: active
openclaw-qwen36-mtp4-128k.service: enabled
```

本机后端接口：

```text
http://127.0.0.1:18343/v1/models
HTTP 200
model: openclaw/Qwen3.6-27B-MTP-Q4XL
n_ctx: 131072
n_ctx_train: 262144
n_params: 27,320,697,856
```

### 2.3 GPU / 系统状态

核查结果：

```text
GPU: NVIDIA GeForce RTX 4090
Driver: 545.23.08
VRAM total: 24564 MiB
VRAM used: 22058 MiB
VRAM free: 2159 MiB
Power limit: 450 W
Persistence Mode: Enabled
Idle performance state: P8
```

CPU / RAM：

```text
CPU: Intel Xeon Silver 4216, 16C/32T
RAM total: 62 GiB
RAM available: 49 GiB
Swap: 976 MiB, currently full
```

判断：

- GPU 显存余量只有约 2.1GB，不能随意增加 GPU 侧开销。
- RAM 余量充足，`--cache-ram` 可以谨慎上调测试，但 swap 已满，不建议直接放开到无限制。
- GPU idle 时处于 P8 深度降频，长输出平均速度影响不大，但短请求 TTFT 可能受冷唤醒影响。

## 3. 当前启动配置

当前脚本：

```bash
/opt/llama.cpp/run-openclaw-qwen36-mtp4-128k.sh
```

内容等价于：

```bash
/home/hhtele/llama.cpp-mtp-unsloth-20260513/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --spec-type mtp \
  --spec-draft-n-max 4 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-reuse 256 \
  --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --host 0.0.0.0 \
  --port 18343
```

构建信息：

```text
llama.cpp commit: ebe4fca
CMAKE_BUILD_TYPE: Release
GGML_CUDA: ON
GGML_CUDA_FA: ON
GGML_CUDA_GRAPHS: ON
CMAKE_CUDA_ARCHITECTURES: 89
```

## 4. 关键发现

### 4.1 `--cache-reuse` 当前实际上不可用

日志显示：

```text
cache_reuse is not supported by this context, it will be disabled
prompt cache is enabled, size limit: 2048 MiB
```

含义：

- `--cache-prompt` 仍然有效，之前 128k exact prompt warm 请求已实测约 76x 到 86x 加速。
- 但 `--cache-reuse 256` 这类 KV shifting partial reuse 在当前 MTP / hybrid context 下被禁用。
- 因此真实 OpenClaw 性能提升不能只靠 `--cache-reuse` 参数，必须从 prompt 结构上保证大块稳定前缀可复用。

### 4.2 128k 是当前稳定主线

已验证最强通过点：

```text
-c 131072 -np 1
prompt_tokens: 130406
cold latency: 105.84s
warm latency: 1.23s
cache_n: 130402 / 130406
prompt cache speedup: 85.89x
```

128k 最近失败点：

```text
prompt_tokens: 131866
n_ctx: 131072
result: HTTP 400 exceed_context_size_error
```

### 4.3 256k 不是当前可用能力

已验证失败形态：

```text
-c 262144 -np 1
约 240k / 255k prompt
prompt processing 阶段 CUDA OOM abort
约 53248 processed tokens 附近失败
```

即使用：

```text
-b 512 -ub 128 --ctx-checkpoints 4 --cache-ram 2048
```

仍然失败。

判断：

- 256k 失败不是普通输入超限，而是当前 MTP + CUDA FA + 24GB 4090 显存路径不可承受。
- 后续若继续攻关 256k，应作为单独底层实验，不应进入 OpenClaw 默认路由。

## 5. 优化方向一：新版 llama.cpp MTP / 链式 speculative

### 5.1 背景

当前服务使用的二进制支持：

```text
--spec-type none,draft,eagle3,mtp,ngram-simple,ngram-map-k,ngram-map-k4v,ngram-mod,ngram-cache
```

但 Unsloth 最新说明已出现参数变化：

```text
--spec-type mtp -> --spec-type draft-mtp
```

并给出链式 speculative 示例：

```text
--spec-type ngram-mod,draft-mtp --spec-draft-n-max 4
```

### 5.2 为什么值得测

OpenClaw / coding agent 场景有大量重复 token：

- 文件路径
- 函数名
- JSON schema
- patch 上下文
- 已读源码片段
- 工具调用结构
- 错误日志中的重复行

MTP 擅长预测后续 token；ngram speculative 擅长从上下文中复制已出现 token。两者链式组合，理论上比单独 MTP 更适合代码编辑和长上下文定位任务。

### 5.3 执行方式

不替换当前稳定服务。新建旁路目录：

```text
/home/hhtele/llama.cpp-mtp-latest-YYYYMMDD
```

使用当前系统 CUDA / driver 编译，不升级 CUDA：

```bash
cmake -B build \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA=ON \
  -DGGML_CUDA_GRAPHS=ON \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j
```

先用非生产端口启动：

```bash
./build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL-newmtp \
  -ngl 99 \
  -c 32768 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --spec-type ngram-mod,draft-mtp \
  --spec-draft-n-max 4 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --host 127.0.0.1 \
  --port 19343
```

如果新版参数仍是 `mtp` 而不是 `draft-mtp`，以 `llama-server --help` 为准。

### 5.4 验证指标

每组至少记录：

```text
prompt eval tok/s
decode tok/s
TTFT
total latency
draft acceptance rate
accepted/generated
think leak count
JSON/tool parse success
patch fence leak
人工质量分
```

### 5.5 风险

- 新版 MTP 参数可能变化。
- MTP 格式问题可能回归，必须确认不会再次出现 `<think>` 泄漏。
- 不能直接替换 systemd 生产服务，必须先旁路端口验证。

## 6. 优化方向二：OpenClaw prompt cache 结构优化

### 6.1 原则

真实收益最大的不是继续调 `--cache-reuse`，而是让请求拥有稳定长前缀。

推荐结构：

```text
稳定前缀：
1. system policy
2. OpenClaw agent role
3. output contract
4. tool schema
5. repo summary
6. stable long context files

变化尾部：
1. user current task
2. latest diff
3. latest logs
4. current error
5. step-local observations
```

### 6.2 禁止事项

不要把这些放在长前缀中：

```text
timestamp
random id
每轮变化的 trace id
动态 token budget
每轮更新的日志摘要
非稳定排序的文件列表
```

### 6.3 测试方式

构造真实 OpenClaw trace：

```text
case A: 完全相同 prompt 重复
case B: 固定 100k repo context，只替换尾部 500 tokens task
case C: 固定 100k repo context，只替换尾部 3k logs
case D: 文件顺序扰动，用于验证 cache miss 惩罚
```

判断标准：

```text
case B/C warm latency 显著低于 cold
cache_n 或日志 cache state 显示稳定前缀被复用
输出质量不低于 cold
```

### 6.4 建议改造点

在 OpenClaw 调用层增加 prompt canonicalization：

```text
1. 文件列表固定排序
2. tool schema 固定排序
3. repo summary 固定版本
4. volatile context 统一追加到尾部
5. 同一 repo session 尽量复用同一个 prefix builder
```

## 7. 优化方向三：MTP 参数 sweep

当前默认：

```text
--spec-draft-n-max 4
```

短输出日志显示：

```text
draft acceptance rate = 1.00000
4 accepted / 4 generated
decode speed about 135 tok/s for very short output
```

但短输出不代表长代码任务。建议矩阵：

```text
--spec-draft-n-max: 3 / 4 / 5 / 6
--spec-draft-p-min: 0.60 / 0.75 / 0.90
```

测试任务：

```text
1. 512-token concise answer
2. 2048-token code review
3. 4096-token patch generation
4. 8192-token long implementation explanation
5. JSON/tool-call constrained output
```

评分：

```text
performance: tok/s, TTFT, latency
quality: correctness, format, patch usability, instruction adherence
stability: crash/OOM/HTTP error/think leak
```

预期：

- 如果 acceptance rate 仍高，`n-max=5/6` 可能提升长输出。
- 如果 acceptance 降低，`n-max=4` 仍可能是最优折中。
- 不应只看速度，必须把格式和人工质量分纳入结论。

## 8. 优化方向四：32k / 64k 低延迟 profile

当前 128k 服务适合长上下文，但不一定适合所有请求。建议建立可切换 profile：

### 8.1 32k profile

```bash
llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL-32K \
  -ngl 99 \
  -c 32768 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --spec-type mtp \
  --spec-draft-n-max 4 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 1024 \
  --host 0.0.0.0 \
  --port 18343
```

### 8.2 64k profile

```bash
llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL-64K \
  -ngl 99 \
  -c 65536 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --spec-type mtp \
  --spec-draft-n-max 4 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 1536 \
  --host 0.0.0.0 \
  --port 18343
```

### 8.3 使用方式

不要和 128k 服务同时常驻同一张 4090。建议做成三个 systemd template 或三个脚本：

```text
openclaw-qwen36-mtp4-32k.service
openclaw-qwen36-mtp4-64k.service
openclaw-qwen36-mtp4-128k.service
```

一次只启动一个。

### 8.4 预期收益

主要收益：

- 显存余量更大
- 冷启动更稳
- 低上下文任务 prompt processing 更轻
- OOM 风险降低

非预期收益：

- 不应期待 decode tok/s 翻倍，因为模型计算仍是 27B。

## 9. 优化方向五：cache / batch 参数小矩阵

### 9.1 cache-ram

当前：

```text
--cache-ram 2048
```

建议测试：

```text
2048
4096
6144
```

不建议直接：

```text
8192
-1
```

原因：

- 当前 RAM 余量足够，但 swap 已满。
- cache-ram 是主存上限，不是显存上限，但过大可能让系统内存回收和 page cache 行为变差。

### 9.2 ctx-checkpoints

建议测试：

```text
--ctx-checkpoints 8
--ctx-checkpoints 16
--ctx-checkpoints 32
```

观察：

```text
cache update time
cache memory size
warm latency
exact repeat hit rate
tail-change partial benefit
```

### 9.3 batch / ubatch

当前默认：

```text
n_batch = 2048
n_ubatch = 512
```

建议只在 128k profile 下小心测试：

```text
-b 1024 -ub 256
-b 2048 -ub 512
-b 4096 -ub 512
-b 4096 -ub 1024
```

停止条件：

```text
CUDA OOM
server abort
VRAM free < 512 MiB
prompt eval tok/s 没有收益
质量或格式异常
```

## 10. GPU / 系统层优化

### 10.1 已确认

```text
Persistence Mode: Enabled
Current Power Limit: 450 W
Max Power Limit: 500 W
Idle P-state: P8
```

### 10.2 可测试项

#### Keep-warm heartbeat

对短请求 TTFT，可以测试每 20 到 30 秒发送极小请求：

```text
Reply with OK only.
```

目的：

- 避免 GPU 长时间停留在 P8 深度降频。
- 保持服务路径热态。

风险：

- 增加功耗。
- 可能污染 prompt cache。
- 对长输出平均 tok/s 可能没有明显提升。

#### Power limit 500W

4090 当前 power limit 为 450W，最大 500W。可以做一次受控测试：

```bash
sudo nvidia-smi -pl 500
```

前提：

- 确认 PSU 和散热可承受。
- 测试结束恢复：

```bash
sudo nvidia-smi -pl 450
```

判断：

- 如果长输出过程中没有触发功耗限制，收益会很小。
- 只应在极限吞吐测试中短时使用。

## 11. 不建议优先投入的方向

### 11.1 vLLM / SGLang

外部资料对 Qwen MTP 会推荐 vLLM / SGLang，但当前约束是：

```text
不能升级 CUDA
单卡 24GB
目标是当前 4090 上稳定服务
```

因此 vLLM / SGLang 暂不作为主线。

### 11.2 多并发

用户目标是单并发上下文极限。并且 MTP 路线对 `-np > 1` 仍有限制和不确定性。继续测 `-np 2/4` 不符合当前目标。

### 11.3 直接上 256k

当前实测不可用。除非满足至少一个前提：

```text
1. 换更小 MTP GGUF 量化，例如 Q3
2. 新版 llama.cpp 修复 256k 内存路径
3. 接受明显质量下降或 CPU/offload 性能下降
```

否则不建议进入 OpenClaw 默认路线。

### 11.4 Q5 质量 lane

Q5 可能提升质量，但会进一步压缩显存。当前 128k 已只剩约 2.1GB free，Q5 不适合作为性能优化方向。

## 12. 下一轮测试矩阵

### 12.1 Baseline

当前服务：

```text
commit: ebe4fca
spec: mtp
n-max: 4
context: 128k
cache-ram: 2048
```

### 12.2 Candidate A：新版 draft-mtp

```text
new llama.cpp
--spec-type draft-mtp
--spec-draft-n-max 4
```

### 12.3 Candidate B：ngram + draft-mtp

```text
new llama.cpp
--spec-type ngram-mod,draft-mtp
--spec-draft-n-max 4
```

### 12.4 Candidate C：MTP n-max sweep

```text
current llama.cpp or new llama.cpp
n-max: 3 / 4 / 5 / 6
```

### 12.5 Context 档位

```text
32k
64k
128k
```

### 12.6 测试任务

```text
1. short-control: 20-token answer
2. medium-code-review: 2k output
3. patch-generation: 4k output
4. long-agent-report: 8k output
5. long-context-retrieval: 64k / 120k prompt exact marker
6. openclaw-json-tool: strict JSON/tool-call output
7. prompt-cache-real-trace: stable repo prefix + variable tail
```

### 12.7 输出指标

每个 case 输出：

```text
config
prompt_tokens
completion_tokens
TTFT
total_latency
prompt_eval_tok_s
decode_tok_s
draft_acceptance_rate
accepted/generated
cache_state
cache_hit_or_cache_n
VRAM peak
HTTP status
think_leak_count
format_error_count
manual_quality_score
conclusion
```

### 12.8 人工评分标准

```text
5: 完全满足 OpenClaw 使用要求，格式稳定，质量好，可作为默认
4: 可用，有小瑕疵，但不影响主流程
3: 部分可用，需要路由限制或后处理
2: 偶发失败或质量明显不稳定
1: 不可用，崩溃、严重格式错误或质量不可接受
```

评分维度：

```text
1. 指令遵循
2. 代码/patch 可用性
3. JSON/tool 格式稳定性
4. 长上下文定位准确性
5. think 标签泄漏
6. 输出冗余度
7. 性能收益
8. 稳定性
```

## 13. 推荐执行顺序

### Phase 1：只读与 baseline 固化

目标：

```text
记录当前服务参数、版本、GPU 状态、baseline 性能。
```

验证：

```text
/v1/models
short streaming TTFT
512/2048/4096 output
128k prompt cache exact repeat
```

### Phase 2：新版 llama.cpp 旁路构建

目标：

```text
在不替换当前 systemd 服务的情况下，构建新 MTP binary。
```

验证：

```text
llama-server --help
确认支持 draft-mtp 或当前实际参数名
19343 旁路端口启动
短 prompt 无 think 泄漏
```

### Phase 3：链式 speculative 对比

目标：

```text
比较 mtp / draft-mtp / ngram-mod,draft-mtp。
```

验证：

```text
性能 + 质量 + 格式三维评分
```

### Phase 4：OpenClaw prompt cache trace

目标：

```text
验证真实 OpenClaw 稳定前缀是否能产生 warm latency 收益。
```

验证：

```text
fixed repo prefix + changing tail
cache state
warm speedup
质量不下降
```

### Phase 5：profile 固化

目标：

```text
根据测试结果保留 1 到 2 个服务 profile。
```

候选：

```text
openclaw-qwen36-mtp4-64k-lowlatency.service
openclaw-qwen36-mtp4-128k-longctx.service
```

## 14. 回滚与安全边界

任何新实验都不得直接覆盖：

```text
/opt/llama.cpp/run-openclaw-qwen36-mtp4-128k.sh
/etc/systemd/system/openclaw-qwen36-mtp4-128k.service
/home/hhtele/llama.cpp-mtp-unsloth-20260513
```

实验端口使用：

```text
19343
29343
```

保留当前稳定入口：

```text
18343 backend
28343 nginx auth proxy
```

若实验失败，停止实验服务即可：

```bash
sudo systemctl stop <experiment-service>
```

当前稳定服务恢复：

```bash
sudo systemctl restart openclaw-qwen36-mtp4-128k.service
```

## 15. 资料来源

- llama.cpp speculative decoding documentation: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/speculative.md
- llama.cpp multi-gpu / memory related documentation: https://github.com/ggml-org/llama.cpp/blob/master/docs/multi-gpu.md
- Unsloth Qwen3.6-27B-MTP-GGUF: https://huggingface.co/unsloth/Qwen3.6-27B-MTP-GGUF
- Unsloth README update mentioning `mtp` to `draft-mtp` and `ngram-mod,draft-mtp`: https://huggingface.co/unsloth/Qwen3.6-27B-MTP-GGUF/commit/296162df313e8eebe1e15a00d60b3f8f33962e18

