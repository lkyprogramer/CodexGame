# Qwen3.5-27B-UD-Q4_K_XL 单人压测摘要

## 结论

- 当前线上配置改为 `--chat-template-kwargs '{"enable_thinking": true}' + --reasoning-format none` 后，单人压测 `18/18` 全部成功。
- 第一轮成功率是 `33.3%`，第二轮提升到 `100.0%`。
- 这证明此前的 `500 Failed to parse input at pos ...` 主要不是模型推理失败，而是 `llama-server` 在 reasoning 输出拆分阶段出错。
- 当前配置适合单人 `Precise coding tasks`，前提是客户端接受 thinking 内容直接出现在 `message.content` 中，而不是单独依赖 `message.reasoning_content`。

## 当前服务

- 入口：`http://100.107.189.100:18343/v1`
- 模型：`unsloth/Qwen3.5-27B-UD-Q4_K_XL`
- 脚本：`/opt/llama.cpp/run-qwen.sh`
- service：`/etc/systemd/system/llama-qwen.service`

## 关键结果

- `smoke_java_bugfix`：`500 -> 200`
- `context_small`：`500 -> 200`
- `context_large`：`500 -> 200`
- `cache_round_1/2/3`：`500 -> 200`
- `soak_round_1/2/3/4`：`500 -> 200`

长上下文结果：

- `context_small`：`5230` prompt tokens，`21.64s`
- `context_medium`：`19728` prompt tokens，`41.16s`
- `context_large`：`64929` prompt tokens，`100.34s`

cache 结果：

- `cache_round_1` prompt_ms：`8338 ms`
- `cache_round_2` prompt_ms：`304 ms`
- `cache_round_3` prompt_ms：`318 ms`

GPU 结果：

- 平均显存占用：`22680.03 MiB`
- 峰值显存占用：`22752 MiB`
- 平均 GPU 利用率：`59.89%`

## 当前 trade-off

收益：

- thinking 仍然存在
- 真实 coding prompt 稳定性显著提升
- 长上下文、cache、soak 全部恢复可用

代价：

- 不再单独返回 `message.reasoning_content`
- thinking 与 answer 合并在 `message.content` 中

## 工件

- 详细报告：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/single_user_bench_detailed_report.md`
- 原始 CSV：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/single_user_bench_results.csv`
- 原始 JSON：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/single_user_bench_results.json`
- GPU 采样：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/gpu_samples.csv`
- VM 采样：`/Users/luo/Documents/github/CodexGame/output/qwen-single-user-bench-reasoning-none/vmstat.log`
