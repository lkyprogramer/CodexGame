# Speedy：同会话后缀碰撞回放有价值，默认近似不可进入主线

固定来源：[Speedy v0.4.12 `7d500de`](https://github.com/DevDock-AI/Speedy/tree/7d500de0067f8fb31a9da1fbef16a303f790dacc)，[release](https://github.com/DevDock-AI/Speedy/releases/tag/v0.4.12)，[patch ledger](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/SPEEDY.md#L1-L26)。当前复制底座 Strata v0.2.7.1（`46c152a1`）；仓库元数据非 fork，未得到跨仓两 HEAD 的 GitHub merge-base。独立代码是 [非商业授权](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/LICENSE)，Strata 沿用的 MIT 部分另计，不能假设可整库复制到生产。
目标基线未绑定；历史 Flash-Next GSQ-RCO IQ3_XXS 两分片、Xeon Silver 4216 / Gen3 ×16，不是这里的 3080 实验，也不把 donor 的模型/量化/默认当用户当前实参。

## 唯一明确的新差异：两张同会话后缀索引

[v0.4.11/#21](https://github.com/DevDock-AI/Speedy/pull/21)，[Speedy `suffix_drafter.cpp`](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/src/spec/suffix_drafter.cpp#L19-L120) vs [现行 Strata 文件](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/spec/suffix_drafter.cpp#L18-L95)。

| 环节 | Strata 当前 | Speedy 补充 |
|---|---|---|
| 插入 | 3-gram 哈希同行会话 history，最多 4 个近期候选位置 | 默认再配一张 8-gram 表，旧的 3-gram 近期窗口规则不变 |
| 查询 | 查看短键桶候选，按真实 token 回望取得最长匹配 | 两张表的候选都做真实 token 匹配；长键先查，等长保留最先找到的匹配 |
| 解决什么 | 一般重复可找；大量新位置具有同一末尾 3 tokens，会挤掉更早的长引用位置 | 当旧位置的 8-token 尾仍能定位，才真正新增候选；并不创造新的重复文本 |
| 成本 | 每 token 插入、主存的旧表、reset 扫表 | 同容量二表、更多哈希与记录 used slots，reset 只清用过的槽；没有额外 VRAM，但 RAM 与 host 时间必须实测 |

[Speedy fixture](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/src/spec/suffix_drafter_test.cpp#L162-L211) 人为制造旧源被短键挤掉。它支持机制可用，不证明感知得到的性能，也不证明生产 sampled/EOS/cache/rollback/MTP 都对等。发布者“greedy 不变”是对应实现的宣称；本轮不能先搬后验证。
现行 [Strata DraftPolicy](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/spec/draft_policy.cpp#L577-L630) 已看匹配/代价，MTP+lookup chaining 也已存在。必须把“恢复候选”与“被 policy 使用、获得更多有效提交”分开，不重写窗口控制。

## C01：只做离线反事实，设清不立项的终点

1. 拿绑定后的同会话固定 token 路径，不用跨用户数据、不改现有采样/模型/量化/KV/模板。若实际合同 lookup 关闭，不能无授权线上开；反事实结果只用来判断是否有讨论价值。
2. 固定轮次上下文，A=现行 3-gram，B=同容量定义增 8-gram；无碰撞已有候选的结果和桶“曾存在后来消失”要能重现。按实际 session 或任务分类，不按某条复写挑最好数字。
3. 需要四个可区分的量：`eligible_steps`、`evicted_old_source_recovered`、沿固定已提交 token 的 `oracle_accept_prefix`、`would_choose_after_current_policy`。实际 engine 后续可能不同，不能把 oracle 填进 runtime acceptance。
4. 计长表查找/插入/hash probes、reset wall、peak host bytes/RSS；用同机实际已采的 width×pos 验证定价，包括更多行触发额外 expert rows、rollback、cache/host read；没有实价时只能报告暂缺。
5. 分 copy-heavy edit/文档原样引用、真实多轮 coding/tool 和 non-copy prose；记录 context bucket 与 tool turn，分别加权。copy-only 胜利不能冒充长期生产均值。

**停**：旧位置被挤出且实际可恢复的频次低；命中后策略不会挑；最乐观的端到端上界达不到 **至少 4% 且超过 2× A/A 噪声**；收益被额外 CPU/RAM/非复写尾延迟吃掉。过上界也仅获得后续独立候选设计资格；本交付没有在线方案。未来变更还须按主合同验 greedy token、固定种子、EOS/取消/restore/tool parsing，不能引入跨会话或跨租户 corpus。

### 离线记录的最小结构

| 字段组 | 例项 | 用来排除什么 |
|---|---|---|
| 样本 | run/turn 匿名 ID，task tier，context bucket，hash 过的输入身份 | 相同复写请求、一个长 tool 结果在总样本权重过高 |
| 旧漏失 | 候选桶当前位置数、历史确曾落桶、是否被后来位置移除、真实最长匹配位 | 把首次出现、哈希撞键或普通无匹配误当 4-way eviction |
| 策略 | old/new oracle 可提交个数、策略实际/反事实窗口 `T`、是否替代 MTP 提案 | 恢复候选并不是净多提交；不能把被替换 MTP 的贡献也加一次 |
| 开销 | host ns、RAM peak、空跑 A/A、按运行路径桶的 verify/rollback 时间 | 只报告 acceptance 上升而实际 wall 变差 |

等价候选 replay 与 token 质量检查分别归档，不用一个成功的 synthetic fixture 代表二者。若本机 trace 缺“原候选所在位置”和“后续匹配完整长度”，报告 telemetry 缺口，而不是视为全部被长表找回。

### 一个反例就能结束的情形

如果长文把同一 trigram 写了很多次，但会话今后只引用较新的位置，则现有 4-way 足够。
如果长表找回旧上下文、但当前保守的长窗成本知道该位置很慢，不挑该候选，也没可回收时间。
如果只在输入几乎原样抄写的校准任务盈利、真实多轮 coding 不盈利，标记局部现象，不把生产权重改成复写。

## 将旧基准拆回旧路径和硬件

[基准协议和原读数](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/docs/BENCHMARKS.md#L6-L104)：RTX 3080 10GB LHR/可选 unlock、PCIe Gen4 ×16、Threadripper PRO 5975WX、128GB 八通道 DDR4、Debian/CUDA 13.4。60/120/200K 档是 55/111/185K 实际 tokens；prefill 来自 engine log，decode 是有效提交；warm +924 tokens 通常 99.2% reuse。ABBA 的 prefill noise 约 ±0.5%，decode ±4–8%。不能把它拿来当本机 A/A。

| 旧候选 | 原读数与反例 | 当前上游状态 |
|---|---|---|
| #4039 小 group scratch、HC region | IQ3_S 在 131K preset，auto chunk 4864→7680，PP +22/+24%，decode 无确定改变；UD-IQ4_XS auto chunk 3584→5632 | [已具备 opt-in 和适用性检查](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/prefill/prefill.cpp#L2131-L2174)，all-MMQ 才合条件；不是新路径，不重开 workspace/HC |
| #4283 routed prompt stream | UD-IQ4_XS +8–10.5% PP，叠加 #4039 约 +41–44%；IQ3_S 在 #4039 上无新增，Q2_0 略负/噪声 | [当前 issuer 路径已有](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/prefill/prefill.cpp#L4530-L4556)，冲突与支持性以实际分支日志为准 |
| #5862 rewind-keep | 旧双 3090 / 双 3080 的 edited-reply cache 场景，非每次续聊 | [当前有相应配置与行为](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/docs/DETAILS.md#L760-L778)，不能拿 PR 未合推断机制缺失 |

不是同一实际 chunk 大小的旧对照，就别把数字叫“kernel 本身更快”。文档注明 raw logs 由维护者保留，没有把全部同实验原 trace/manifest 交给我们。仓库内继承的旧 4090 社区目录，也不能替代 Speedy v0.4.12 与当前 Strata 的同机 A/B。

## 严格区分近似、服务端行为和网络延迟

- [Speedy defaults](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/src/program/speedy_defaults.hpp#L19-L36) 默认 `STRATA_VERIFY_DEFER_CPU=1`，权重 `<0.1` 的 CPU 专家贡献在下一层 mixer 之后才补到 residual；[实现](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/src/core/verify.cpp#L1507-L1545) 很清楚：l+1 attention/GDN 输入已不同，晚补不能逆转这一点。`STRATA_DEFER_HITS_FUSE` 的 bitwise 只是相对已经延迟的路径。
- [上游 PR2690](https://github.com/Niko1221/Strata/pull/2690)：低 context RTX2080Ti +15.4% 时 teacher-forced KL 0.098（placement floor 0.030、tail skip 0.064），较早 RTX3080 +15.8% / KL 0.088。不是 4090 通用值，也不通过 exact。现有 Strata 自身 [route tail skip](https://github.com/Niko1221/Strata/blob/58ee3227720629ff2e41d640165ebe89c880dfef/engine/src/core/expert_source.cpp#L4930-L5027) 是另一近似；基线实参写进 manifest、不自动改变，不能借该近似证明再引入新近似合理。
- v0.4.12 的 [commit](https://github.com/DevDock-AI/Speedy/commit/7d500de0067f8fb31a9da1fbef16a303f790dacc) 是引用式 `</think>` 识别、TCP_NODELAY、glibc arena 可选上限。[TCP 单测](https://github.com/DevDock-AI/Speedy/blob/7d500de0067f8fb31a9da1fbef16a303f790dacc/serve/test_tcp_nodelay.py) 检查 getsockopt，不是网络或 GPU 性能对照。只有服务端 flush 到客户端 first-byte 出现尖峰或 RSS 有 malloc attribution，才独立诊断；不进 C01。
- reasoning effort floor、工具调用强制/修复、丢长上下文老 thinking、default sampling 改变输入或生成行为，不是纯性能开关。切换它们会让“提速但任务变了”无法归因。

接入闸门看运行时实参而不是 release 默认。旧 Strata 用户曾针对 CPU gap、HC 与工作区判无充分收益，Speedy 的低显存壁垒和台阶变化不能自动重置这些结论；只收集新现场 path，有理由再单独提案。

相关数据契约见 [05_DATA_MODEL_AND_MEASUREMENT.md](05_DATA_MODEL_AND_MEASUREMENT.md)，统一停止条件见 [18_CANDIDATES_AND_STOP_RULES.md](18_CANDIDATES_AND_STOP_RULES.md)。
