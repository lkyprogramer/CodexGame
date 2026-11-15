# Strata / RTX 4090：5060 Ti 配置对照后的剩余优化方向

资料截点：2026-11-02（北京时间）。本报告为文档级证据审计与研究设计，不包含本机新测速。

## 1. 结论：有新问题值得研究，没有新的已合格提速方案

5060 Ti 的“95–106 tok/s”不构成恢复旧 Kernel 探索的理由。它提供的是一组尚未建立因果关系的变量：Q4 KV、不同 KV 驻留长度、HC_Q8、草稿词表、耦合采样、固定 PCIe 分工，以及未知的 CPU、请求和计时条件。

最值得保留的三类新问题是：

1. **HC_Q8 能否通过减少常驻权重读取和显存占用改善完整请求？** 这是与已失败 P24 不同的机制，但有数值/质量代价；优先级是“可低维护审查”，不是“可以直接开启”。
2. **真实工作负载的草稿成本，能否通过适配词表、目标不变的耦合提案或复制长窗口下降？** 先用已有原件证明任务覆盖和开销；不能以接受率代替净收益。
3. **如果接受另立质量合同，k8v4 是否比 q4_0 更合适？** 先试验设计后授权，先单变量后组合；保留 INT8 为原合同基线。

F05 行窗 scratch 等 Prefill 方向仍可作为“改变目标合同后的条件研究”。DFlash2 的 served 实现与额外显存成本仍是前置阻塞。原 F02、P24、F03、PCIe 扫描、线程/SIMD 扫描等关闭结论不变。[S02–S06、S11–S15]

## 2. 必须先修正的基线

### 2.1 不再把当前主线统称 IQ3_S

用户仓库的环境记录明确将 10-08 IQ3_S 记录标为过时；10-23 之后的主线是 **GSQ-RCO IQ3_XXS 混合包**。包内实际 GU 分布为 IQ2_XXS 9 层、IQ2_XS 10 层、IQ2_S 10 层、IQ3_XXS 6 层、IQ3_S 13 层；down 为 IQ4_NL 18 层、Q2_0 30 层。包名不等于所有矩阵都使用同一种格式。[S01、S04]

5060 Ti Gist 的 pack、两个 GGUF 分片、tokenizer、vision model 路径也全部为 IQ3_XXS。因此“对方用更低精度权重”不是本次可成立的主要解释；仍需权重、pack、MTP、tokenizer 的哈希才能证明资产相同。[S07]

若用户机器今天确实已经换回 IQ3_S，应建立新基线，不把本包 IQ3_XXS 历史成绩套上去。本次没有访问目标机确认。

### 2.2 版本和状态也要分层

| 对象 | 可核查身份 | 使用边界 |
|---|---|---|
| 历史生产 A0 | v0.2.3，`5c8dd322528cc84f68f461ad54a506b9da8fa8d4` 加部署补丁 | 保护对象，不随本报告升级 |
| 研究基线 B / P6 | v0.2.7 / engine 0.1.52，`5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d` 加六文件 Python port | 旧冻结合同的比较基线 |
| 本次官方源码 | v0.2.9 对应 main `c62d5e3a15b40ea51c96aae9e8d36928965f53ab` | 源码 donor，不自动替换 P6 |
| v0.2.9 发布引擎 | tag message 记引擎/SYCL 包由 `99866a47a2b8a21b131aad162a584ee9da92f8f0` 构建 | 发布标签 SHA 不等于每个资产的构建 SHA |
| 5060 Ti Gist | description `029`、exe 路径、CUDA 13.1 路径 | 这些不能证明具体二进制、编译开关与实际加载库 |

研究基线 B 的报告二进制 SHA256 是 `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`。本次只读取报告，未重新 hash 用户机器的文件。[S03、S04、S08]

仓库最新 NEXT_ACTIONS 记载：2026-10-31 已采纳 Astra 收口意见；随后用户另行要求恢复生产，12:50:44 北京时间回执为 active/running/enabled。**这是最后一次历史回执，不是本次实时状态；不能沿用更早 inactive/dead 作为 GPU 空闲凭证。**[S02、S06]

## 3. 5060 Ti 为什么“看起来追平”？

### 3.1 原始证据只到配置，不到性能

Gist 固定 revision 为 `7886e445ac61d2ae6ff03fc3c6e8f8927f22d7f4`，只有 `gistfile1.txt`，1776 字节，没有评论、日志附件或 benchmark 结果。没有 CPU、内存通道、引擎 hash、prompt/output token 数、采样参数和冷暖顺序。`--max-context 131072` 是容量上限，不证明测试时已经填入 100K；`vision.max_tokens=1024` 是视觉配置，不能充当生成长度。[S07]

故以下数字均保留为用户转述的作者宣称，不提升为已验证同条件结果：95–106 tok/s、约 100K、0.2 秒缓存重读、Basalt Prefill +35%、Strata Decode +15%。

### 3.2 比较表：差异是研究变量，不是因果结论

| 变量 | 社区配置 | 我们的冻结研究基线 | 含义 |
|---|---|---|---|
| 权重包 | IQ3_XXS 路径，无哈希 | IQ3_XXS 混合包，有报告哈希 | 同名仍需资产验证 |
| KV | q4_0 | int8 | 改数值、占用和搬运，必须独立质量分支 |
| GPU 主 KV cells | 32768 | 20480 | 不能脱离每 cell 字节数比较 |
| MTP | spec4 / min-p0.5 | spec4 / min-p0.5 | 实际 verify T、tokens/round 不一定相同 |
| 草稿词表 | cyrillic 文件 | 冻结默认文件 | 必须查真实语言覆盖与 hash，不能盲抄 |
| COUPLED | 1 | 未登记开启 | 可能提高接受率，也可能不提速 |
| HC_Q8 | 1 | 未登记开启 | 与 P24 的 HC 临时缓冲复用不同 |
| Expert cache | 请求 5363 slots | auto；P6/P01B 历史实际 10272，P3 10290 | slot 大小、profile、热度和分派比个数更重要 |
| PCIe 分工 | 固定 0.19 | 自动；以实际启动/请求记录为准 | 不照抄；既有固定比例/Balance 无稳定净益 |
| 自适应 | every1 / swaps160 / decay0.97 | 按冻结原件 | 影响窗口成本、warm-up 和 CPU/GPU 舍入 |
| Vision | 开启 | 实验需按冻结合同 | 资源不同不能悄悄消掉 |
| 硬件/库 | 用户称 5060 Ti +61GB RAM；CPU未知 | 4090 / Xeon4216 /2×32GB DDR4，CUDA12.3 | 这是异构 CPU+RAM+GPU 系统，不是 GPU 峰值对比 |

### 3.3 三个分母不能混用

- **Native Decode tok/s**：真实 committed tokens 除以引擎完整 Decode 区间。
- **完整请求有效 tok/s**：输出 tokens 除以 HTTP 请求完成墙钟；包含前处理、Prefill、状态保存等。
- **任务表现**：真实 Pi/Java 任务成功率、预算内完成时间；多思考、更早 EOS、失败快都可能扭曲 tok/s。

用户给出的 P01B 短样本 142.8 / 122.5 tok/s 可作为口径说明，但本次未取得 REQUESTS.jsonl 原件，不能独立复算这些 native rates。报告中 append_2 为 774 token / 8.4737 秒，算术上完整请求约 **91.34 tok/s**。这并不与 122.5 的 native Decode 数字矛盾，二者分母不同。旧 75.1 tok/s 又属于更早模型、版本与流量，不作为今天统一分母。[S01、S05]

P01B 本身是脱敏真实 session 的 HTTP 诊断投影、`tool_choice=none`，不是完整 Pi 执行 Java 工具链的任务验收；其 TTFT 是首 thinking 事件，不是首可见答案。[S05]

0.2 秒 warm re-read 可能只消费少量新 token 或恢复已缓存状态。没有 read/reused/restore 明细，不能把它写成“100K 冷读只要 0.2 秒”。

## 4. 一个容易算错的显存账：Q4 不等于多出 0.7 GiB 专家缓存

按当前模型 12 个 QSA 层与官方 cell 字节数计算，**仅主 K/V 数据，不含索引、MTP、GDN、Graph、scratch 和对齐**：[S01、S10、S11]

| 格式 | bytes / cell / QSA层 | 全 131072 cells 逻辑主KV | 固定 20480 resident 的主KV |
|---|---:|---:|---:|
| int8 | 1056 | 1.546875 GiB | 247.5 MiB |
| k8v4 | 816 | 1.1953125 GiB | 191.25 MiB |
| q4_0 | 576 | 0.84375 GiB | 135 MiB |

社区配置 q4_0 × resident32768 的主 KV 约 **216 MiB**；我们 int8 × resident20480 约 **247.5 MiB**，这两种配置在这一个 GPU 项上仅差 **31.5 MiB**。Q4 可以让更多 cells 用近似的 GPU 预算驻留，并减少主存副本和每次 KV 搬运，但不能把全逻辑 KV 的 0.703125 GiB 差额全算作 GPU 专家缓存收益。

这是尺寸估算，不是整卡实测。实际 resident映射、MTP ring、index、snapshot、多份副本、分配粒度和状态生命周期都要分开登记。

相对而言，HC_Q8 可能释放更明显的常驻权重预算：按 48 层、每层 4 个 320×10240 down/up 矩阵，BF16 1200 MiB → Q8_0 637.5 MiB，再计 4 个 6.25 MiB scratch，理论差量约 **537.5 MiB**。这是源码维度下的机制估算，不是已测整卡释放量，也不保证 auto cache 能全部接收或提高命中率。[S12]

## 5. 候选优先级：排序的是进一步审查价值，不是预期提升百分比

| 优先级/编号 | 方向 | 推荐状态 | 主要门槛 |
|---|---|---|---|
| 先决 N0 | 恢复既有原件、统一身份和分母 | 文档级可做；缺件就 BLOCKED，不重跑凑齐 | workspace 原件、当前资产身份、正式 warm 探针资格 |
| Q1 | HC_Q8 的权重/常驻显存双重影响 | **质量分支首要候选**，未授权运行 | 单变量、核查 P6 是否含实现/需迁移；长链质量与实际释放量 |
| T1 | 语料匹配的 MTP 词表；单独 COUPLED | 低维护、条件候选 | 中英/Java token 覆盖、完整 draft+verify 成本；不扫 spec |
| Q2 | INT8 → k8v4 → q4_0 | **另合同选择项**；优先研究 k8v4 的取舍而非默认 Q4 | 长文/代码/工具质量、主存及驻留账；不得同时改resident |
| T2 | #4928 长 Lookup | 仅实际 copy/edit 占比足够才准入 | 与旧 #4040 的新差量、实际长匹配覆盖、Graph开销 |
| T3 | DFlash2 served / accepted-prefix /资源共享 | 等服务路径与预算证据；不是立即切换 | 当前 main served回退MTP；新增draft可能挤掉expert cache |
| P1 | F05 group scratch行窗；F06/F07 | 只作独立 Prefill合同的条件研究 | 不改Dm/规约，证明真正冷读/长追加占比与暴露成本 |
| 保留关闭 | F02、P24、F03、旧CPU/PCIe/线程扫描 | **不重开** | 需要独立新机制，不是换参数或换名字 |

Q1 与 T1 并不获得原冻结合同的自动资格。用户批准“出文档”不代表批准降精度、停生产或消耗 GPU。

## 6. 综合之前引擎研究后，哪些建议应更新？

| 来源 | 仍有价值的借鉴 | 本次必须收回/限制的外推 |
|---|---|---|
| FreeToken | 通用异构MoE执行、语义锚点检查点、KV/expert弹性显存的设计参照 | 官方支持Flash-Next和RTX40，但文档要求其47.7 GiB PLE表固定host pinned RAM；64GB机器需先过资源门。未见本组合100K同条件测速，不能直接判它比Strata快 |
| tandem.cpp | 用同硬件、同target/route、同草稿的精确对照方法 | Strata 已有 QKV 输入 Q8复用、accepted-only MTP catch-up；不能把概念再移植一遍当新候选。共享/路由额外Q8去重已有opt-in开关，仍须成本准入 |
| Infernix | DFlash2完整成本、验证前缀和资源账；跨层同存储类cache作为独立机制审查 | 当前SM120a，不能直接在4090换引擎；此前5090 Agent结果也不是同草稿策略对照 |
| Basalt | IQ fused prefill、ring/stream重叠、按机器实测CPU/GPU分工 | 当前CMake拒绝非SM120；原生NVFP4 Tensor Core不能照搬。当前run.cpp是chunk外层/layer内层，不能宣传为整prompt layer-major |
| #4928 | 长匹配才扩窗、MTP分块回放、预捕获、收益校准 | P40+23%不是4090预计收益；RTX5090无净益、有vision可负收益；#4040在本机旧负载覆盖仅约0.8%不能忽略 |
| adaptive tail /临时显存复用 | 只研究既有arena/lend/refill之外可证明的独立差量 | 不能把“prefill看似闲置4.3GB”直接当decode可永久占用；要覆盖下一轮prefill、KV/Graph/allocator生命周期及额外搬运 |

Strata 当前 `Verifier` 的输入量化共享和 `MtpDrafter` 的 accepted-only catch-up 已在主线；此前把两者泛化列为新增移植方向，证据不足，应从优先列表撤下。[S16]

FreeToken不是SM120专用引擎；其“语义锚点”思路与Pi历史渲染导致的大重读有关，值得保留为会话层设计参照。但本次只核实官方功能声明，未完成与Strata快照/渲染路径的实现差量审计，不能据此重开F03或声称可省掉全部park成本。[S21]

Basalt 的非FP4 IQ内核可作为 Ada 移植参考，但当前 Strata 已有大量融合、异步和cache机制；只有逐函数对照确认差量且进入完成路径，才是项目，不是看到 `cp.async` 就有收益。[S19]

## 7. 不再重复的负结果

| 方向 | 本机历史结果/资格结论 |
|---|---|
| P24 HC临时缓冲复用 | TTFT仅改善0.824%，CI跨0；完整Decode耗时+4.428%；真实释放/少搬运并未变成净收益 |
| F03 snapshot去零填 | CPU完整成本三对慢6.08%–7.74%；没有证明可安全删除的快照owner |
| F12 verify→commit窄host gap | P01B仅约0.1340% /0.1224%；不是4%级机会 |
| F02单格式GU布局 | 旧profile最大TG21条件成本约2.22% /2.13%，新load/layout机制未证；不是当前严格全局上界 |
| P5 / P12 | VNNI未过完整专家门；gather完整专家耗时+33.04%；不扩格式/nt续接 |
| 固定PCIe / PCIE_BALANCE | CPU少算未必更快，GPU等待抵消；原研究未形成稳定净益 |
| spec3/5、SPECCOST、lookup2 | 旧工作负载无足够净收益；不能由5060的spec4重新启动全参数搜索 |

完整边界见 [S03] 的关闭台账。旧profile百分比不是当前严格收益上限；反过来，“还没证明全局无空间”也不是继续花GPU的理由。

## 8. 实际建议

**现在完成的工作：**本包统一事实、候选卡、协议与有界计划；不发起新硬件试验。

**下一次若只批准一件事：**优先明确是否愿意开展 Q1 的独立质量—性能研究；若不接受任何数值变化，维持原冻结合同收口，仅接收可证明的新机制证据。若批准 Q1，先离线核对源代码/资产和原件，不直接起服务。

**不要期待必然把“75”变成“106”。** 75是旧基线，106不是同口径证据；正确目标是固定任务成功前提下，完整请求/任务时间的可重复净下降。

所有来源、固定提交和证据缺口见 [05_EVIDENCE_SOURCES.md](05_EVIDENCE_SOURCES.md)；候选细节见 [02_CANDIDATE_DESIGNS.md](02_CANDIDATE_DESIGNS.md)。
