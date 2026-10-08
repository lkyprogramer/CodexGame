# 09 风险、决策与停止规则

| ID | 决策 | 原因 | 对应验证 |
|---|---|---|---|
| D01 | 原权重冻结；LSP是近似实验 | 不把原生CED训练结果外推到现有Qwen | P3/P4质量 |
| D02 | 从48/16开始 | 先检验最小有意义late-state可学习性 | P4/P6 |
| D03 | 先Teacher注入，不先训练 | 分离runtime缺state和学习失败 | P1 |
| D04 | 预测pre-conv QKV，不仅post-conv K/V | 未来decode需要卷积history | P2/P4 |
| D05 | 新StateOnly大T，不扩短Replay窗口 | 长T成本和数值路径不同 | P2 |
| D06 | 正常tail至少1token | 正确产生最后hidden/首token；不保证治愈prefix误差 | P4 |
| D07 | MTP单列阶段，增加final-hidden head | 原MTP prefix不可凭空形成 | P5 |
| D08 | 来源字段随lane/image/checkpoint持久化 | 防止approx污染native cache | P5 |
| D09 | v1只cold LSP，不在native warm suffix任意混用 | 缩小状态组合与误差面 | P4/P5 |
| D10 | Predictor分时离线训练，标签有上限 | 24GB GPU / 600GB SSD约束 | P0/P3 |
| D11 | 主机/电源/模型/codec不混改 | 保证收益可归因 | 全阶段 |
| D12 | 默认关闭，不自动生产启用 | 质量证据可能仅够个人opt-in | P8 |

## 风险清单与应对

**R1 可学习性不足。** h_split单token无法可靠恢复深层上下文状态是现实可能。先分层head误差与连续state验证；允许一个有界causal trunk扩展方案（仅P3第二修复轮，≤3token因果上下文，参数预算不变），不能无限加模型直到等于被跳过层的成本。仍失败则NO-GO。

**R2 递推误差随长度累积。** 用非零Teacher窗口与from-zero free-running对照；扩大tail并不保证修复。64K通过、200K失败只代表资格化范围变小，不能宣称200K通过。

**R3 MTP成本吞掉收益。** 比较CED no-spec与同mode基线、CED MTP3与native MTP3。MTP final-hidden成本必须计入。P4通过但P5不通过，交付no-spec实验结果，不替换现有MTP3生产默认。

**R4 训练标签超过存储。** 滚动样本、分层导出、token限额，禁止不受控dump。100万全标签约267.5GiB只是张量，不含多版本副本。

**R5 显存不足。** per-head streaming，复用scratch，优化附加buffer；不得缩小原262144窗口并隐瞒。

**R6 原生缓存收益高，CED对真实Agent无益。** P0取输入改写/uncached分布，P6报告冷热各占比及端到端总时间；只有cold单测快而总任务不快，结论就是局部收益。

**R7 默认INT8 prefill与BF16 Teacher混用。** 导出自实际profile，记录每个标签的precision边界。一个模型名字不是同一数值模型证明。

**R8 质量统计不足。** 小样本通过仅private opt-in；报告区间与失败，不写“基本无损”替代数据。

**R9 异常造成错误状态复用。** poison测试、provenance、事务回退。原生回退必须清洁重算，不能在approx state上续跑后更名。

**R10 文档与代码漂移。** 固定commit、resolved symbol map、生成task manifest。上游更新在独立diff审查后才引入，禁止工作中途自动pull。

## 停止时交付什么

输出当前最高通过Phase、已通过split、失败fixture与根因、资源/性能/质量曲线、可复现命令和原生恢复验证。停止不意味着删除证据或宣布工程全部完成。

只有没有训练数据或硬件授权时使用BLOCKED；实际实验否定该参数组合时使用FAIL/NO-GO。不要把“不想继续花时间”包装成理论不可能，也不要把可运行包装成有效。
