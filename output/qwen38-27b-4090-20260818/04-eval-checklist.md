# 执行清单

给下一轮在 `192.168.10.29` 上跑方案用。细节和门槛见 [01-deployment-and-eval-plan.md](01-deployment-and-eval-plan.md)。

## 安全

- [ ] 只占用 `19343`
- [ ] 测试窗口停 `openclaw-qwen36-mtp4-128k.service`，结束必须恢复
- [ ] 不改 NGINX、不改生产 ExecStart，除非 S1–S4 全过且有人明确要求切灰度
- [ ] 3.8 与 3.6 不要同时占卡

## S0

- [ ] SSH 到 4090，确认 GPU / 磁盘 / 模型 SHA256
- [ ] `llama-server --help` 含 `--reasoning-budget`、`--spec-type`、`--chat-template-kwargs`
- [ ] 缺 flag 则升 llama.cpp 后再测，不要用旧 binary 假装测了预算切断
- [ ] 记录 driver、温度、生产单元状态

## S1 `work-balanced`

- [ ] `/v1/models` 200
- [ ] `reasoning_effort=banana` 走 kwargs → 4xx
- [ ] medium 简单问答：正文非空，`finish_reason=stop`
- [ ] 预算切断后不重做全文
- [ ] `response_format` JSON schema 通过
- [ ] 一轮工具 + 回灌
- [ ] 请求级 thinking off：`OK`

## S2 32K q8 矩阵

- [ ] `base_nospec`
- [ ] `mtp_n2_p0`（主候选）
- [ ] `mtp_n2_p075`
- [ ] `mtp_n3_p0`
- [ ] `mtp_n4_p0`（负对照）
- [ ] 每 lane：256/1024/2048 ×3 + 硬编码 + JSON + junk
- [ ] 按任务通过 / junk / acceptance 选 n 和 p-min，不要只看 2048 tok/s

## S3

- [ ] xhigh / low / medium / medium+4k / medium+16k / medium+32k / off
- [ ] 同一套硬任务
- [ ] 记录 reasoning_tokens、time_to_first_tool、task_pass

## S4 工作题（每题 2 次）

- [ ] JSON schema
- [ ] 5 轮工具
- [ ] 可应用 patch + 本地编译/单测
- [ ] 隐藏回归（45s→5s）
- [ ] 安全拒绝（不能只用 contains `git status`）
- [ ] 禁 fence / 恰好 N 字段
- [ ] 多约束实现 + 隐藏单测
- [ ] 可选：game-runtime 只读诊断
- [ ] 恢复 3.6 后跑同一题集

## S5 / S6 / S7

- [ ] 8K/32K/56K 交叉三事实，不是纯 marker
- [ ] 32K q8 vs f16
- [ ] cold / exact warm / incremental / similar；thinking 开关不得串 cache
- [ ] 峰值 < 22000 MiB @ 64K
- [ ] 生产恢复：18343 200，28343 鉴权，无 19343 残留

## 结论

只能写三选一，并引用 S1–S4 数字：

- `灰度 work-balanced`
- `仅旁路继续调`
- `不上，保留 3.6`
