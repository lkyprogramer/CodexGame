# extreme_v2 T00–T03 / Suffix+MTP v1 / T07

生产未切换。回滚点仍是 **262144 / rk4v4-e8 / MTP n=3 / medium**。

## 结论（2026-09-10 复核改判；原文保留在下方"原始结论"）

- **Suffix+MTP v1：`BLOCKED: T05/T06 未实现`**（不是"候选否决"）。实测对象是未改动 44a 二进制的 `--draft-tokens 3` vs `5`，即 MTP head 自回归多跑 2 步；v1 定义是 3 个 MTP 草稿 + ≤2 个 suffix 延长（零 GPU draft 成本、仅索引命中时追加），没有 C++ 实现就没有可测对象。`--draft-tokens 6` 被拒是合同内行为（MTP 1..5）。
- **样本无效，不进任何门**：每样本 `completion_tokens=5`（"reconnectTimeoutMs"+EOS）、`reasoning_effort=none`、客户端 `temperature 0.2`、748/752 token 缓存命中。`predicted_per_second` 在一两轮内量的是固定开销，"219.8 t/s"、"慢 18.5%"、"A/A 0.24%" 都由此而来；产品口径 4K medium 是 127 t/s（报告 11）。有效样本条件见 bundle `docs/12 §2`。
- **可保留的信息**：W=6 verify + 5 步 MTP draft 的一轮 ≈27.9 ms，W=4 的一轮 ≈11–14 ms（22.8 ms/2 轮）——额外行不免费，但本数据分不开 draft 步成本与 verify 行成本，该分解归 T07 kernel 微基准。
- **负对照**：`--spec off` 63.4 vs MTP3 219.8 只说明 MTP 在这个 5-token 探针上有效，不能换算成"MTP 贡献 71%"。
- **T07：`BLOCKED: W8 路径未构建`**（不是"未过门"）。对 MTP 制品跑 `--spec dflash --draft-tokens 8` 必然报 `DFlash is not supported by this target`（`round_state.h:26 enable_dflash=false`，无 companion），这是已知事实而非测量。T07 是 op 级微基准（改 `src/CMakeLists.txt:278` small-T 范围→构建→`tests/ops/test_gqa_attention.cpp` 喂 T=4/T=8 得 `Δ_w8`），不启动引擎、不需要 DFlash2 权重；companion/persist 属 T08/T10。
- **T00–T02 未做**：无 `runtime-lock.json`/`memory-ledger.json`、无 remote_guard 演练、无每轮遥测；T03 的 rk8@200192 对照臂未跑。
- **流程偏差**：使用喂密码的 `sudo-wrap.sh`（sudoers 已免密）、`pkill -f "ssh .*18030"`、容器 `ninfer-4090` 占 18030 且无 `qwen38.lab.run` label。后续走 `tools/remote_guard.py` + 18041。
- **不要自动切生产。** 回滚点不变。

### 下一步

1. T00（preflight + memory-ledger）→ T01（remote_guard 真实演练）→ T02（每轮 `round_ms/W/liveQ/licensed/committed`）。
2. T07 按 op 级微基准拿 `Δ_w8`。
3. T05/T06 v1 写代码后按 R-perf-184K/short（输出 ≥1024、medium、≥8 配对、先 A/A）测。

## 原始结论（2026-09-09，已作废，仅存档）

- ~~**候选否决**：把 MTP draft 从 3 拉到 5（引擎允许的 suffix 上限；W=6 直接拒绝启动）在 200192、thinking=none 短解码上 **慢 18.5%**。保持 MTP3。~~
- ~~**负对照成立**：`--spec off` 63.4 t/s vs MTP3 219.8 t/s（MTP 贡献约 71%）。~~
- ~~**T07 DFlash2 W8 184K：未过门**。当前 16.96GiB MTP `.ninfer` 报 `DFlash is not supported by this target`。companion/persist 未做。~~
- **不要自动切生产。**

## 原始计数（5-token / none 探针；不是有效 decode 样本）

| 臂 | mean decode t/s | A/A noise | ctx |
|---|---:|---:|---:|
| MTP W=3 | 219.77 | 0.24% | 200192 |
| MTP W=5 | 179.15 | 0.33% | 200192 |
| spec off | 63.37 | 0.08% | 200192 |
| prod MTP3 262k (A/A, none) | 219.63 | 1.02% | 262144 |

W5 vs W3 uplift **−18.49%**。

## 质量 / 状态 / 容量 / 时延

- 制品 SHA `eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e`，镜像 `44a2c6c`。
- 容量底 200192 未下调；生产仍 262144。
- 负对照：unique user 冷缓存 vs exact repeat 命中（`test_live_http_negative.py`）。
- 恢复：2026-09-09T22:22:01-04:00 unit active，22594 MiB，`openclaw/Qwen3.8-27B-WORK` 262144。
