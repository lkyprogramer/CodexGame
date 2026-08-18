# 最终结论

**决策：仅旁路继续调，不上 28343，保留现网 Qwen3.6。**

不是“3.8 不能干活”，而是 **还不能替换现网默认入口**。

## 已落地

- 08-17 的灰度推荐（MTP n=4、KV q4、全局关思考、评测 temp=0）作废。
- 在 4090 上按社区/官方配方跑完 S0–S7。
- 工作配置验证为：

```text
UD-Q4_K_XL
llama.cpp 4df29be + --jinja
--spec-default --spec-type draft-mtp --spec-draft-n-max 2
KV / draft KV = q8_0
-c 65536 -np 1
reasoning_effort=medium via chat_template_kwargs
--reasoning-budget 16384 + 反重做文案
thinking 采样 1.0 / 0.95 / 20
```

- 峰值约 **20.6GB / 83–85°C**，低于 22GB 门禁。
- systemd 旁路单元已写入并保持 **disabled**。现网 3.6 已恢复，鉴权行为未变。

## 门禁对照

| 门禁 | 结果 |
|---|---|
| S1 协议 100% | **8/8 通过** |
| S2 无 junk，n=2 快于 no-spec | 通过。n=2 p=0 ≈ 59 tok/s（1.51x）。n=4 未 junk 但无收益 |
| S2 accept ≥ 0.70 | **未达**（n=2 p=0 中位 0.57；p=0.75 才 0.79 但更慢） |
| S3 medium 不弱于 xhigh | 通过，短编码题全过 |
| S4 每题至少 1 次通过 | 通过（含人工判定的安全拒绝） |
| S4 自动通过率 ≥ 75% | 原始 12/16=75%；安全误判修正后 14/16=87.5% |
| S4 安全 100% 自动 | 自动失败，**人工通过**（3.6 同一规则也失败） |
| 相对 3.6 不在 patch+隐藏回归上双输 | 通过，两边都指出 45s→5s |
| 64K 交叉事实 | 8K/32K/47K 全过 |
| 空正文 = 0 | **未达**：2 次思考吃光 `max_tokens=2048` |

卡灰度的两项：acceptance 纸面门槛、以及 **思考请求必须把 max_tokens 拉到 ≥ 20480**。后者不改，OpenClaw 会间歇拿到空 `content`。

## 和 08-17 的关键差异（已用本轮数据验证）

1. **不要 n=4。** 本轮 n=2 与 n=3 速度持平，n=4 更慢、accept 更差。
2. **不要全局关思考。** S1 medium 1.2s 给出正确答案；关思考只作为短 JSON 快路径。
3. **不要用 temp=0 当工作采样。** 本轮按官方 thinking/instruct 档跑。
4. **不要用 marker 代替推理。** 交叉三事实在 47K q8 上仍对。
5. **客户端预算是第一生产风险**，不是量化也不是 MTP。

## 若要真正换成默认入口，还差

1. OpenClaw / 调用方：思考请求 `max_tokens >= 20480`，并解析 `reasoning_content` 兜底。
2. `reasoning_effort` 必须走 `chat_template_kwargs`（S1 sentinel 已证明非法值会 4xx/5xx，不会静默）。
3. 再跑一轮 8–12 题、`max_tokens=20480`、至少 3 次重复，空正文必须为 0。
4. 明确灰度流量从哪条路由切，单卡一次只能活一个模型。

在此之前：现网继续 3.6；需要试 3.8 时按 S7 手动切换旁路单元。
