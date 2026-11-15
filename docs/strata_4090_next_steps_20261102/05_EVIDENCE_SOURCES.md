# 证据来源索引与证明边界

资料截点：2026-11-02（北京时间）。本索引与 [01_RESEARCH_SUMMARY.md](01_RESEARCH_SUMMARY.md) 的 S01–S21 一一对应。它记录本次读到的报告、源码和作者材料，不是本机重新测速报告。

## 证据使用规则

- **源码事实**：说明固定版本确有某机制、默认值或门控；不单独证明该机制在目标负载的完成路径上，也不证明净提速。
- **源码计算**：按维度、dtype 和生命周期计算的字节数；必须与实际分配、峰值、驻留和可兑换的 expert slots 区分。
- **历史本机报告**：CodexGame 内固定提交的现场结论。本次没有取得被忽略的 workspace 原件，因此不能声称独立复算了原始样本、统计或 hash。
- **作者/社区自报**：一手作者记录，不等于独立复现；必须保留硬件、量化、请求形状、采样与版本限制。
- **PR 状态**：按本次读取时的 open/closed、merged 字段与 head/base SHA 记录。PR 正文可更新，评论定位不是不可变快照；当前主线源码优先于过时正文。
- **未取得**：保持 UNKNOWN / BLOCKED_EVIDENCE。不得把报告提到的原件路径伪装成可访问文件，不得自动重跑补齐。

所有“当前”默认均指下表固定源码，而非用户目标机的实时配置。研究主线 P6、历史生产 A0 与当前 upstream donor 不可互相冒充。

## 固定身份总表

| 对象 | 本次固定身份 | 说明 |
|---|---|---|
| CodexGame，4090-report | b4fb53ff88df2cea58149483533cef7159fb9120 | [提交](https://github.com/lkyprogramer/CodexGame/commit/b4fb53ff88df2cea58149483533cef7159fb9120)；本机报告与实验合同来源 |
| Strata main / v0.2.9 tag target | c62d5e3a15b40ea51c96aae9e8d36928965f53ab | [提交](https://github.com/Niko1221/Strata/commit/c62d5e3a15b40ea51c96aae9e8d36928965f53ab)；源码 donor |
| Strata v0.2.9 引擎/SYCL 发布包 | 99866a47a2b8a21b131aad162a584ee9da92f8f0 | 来自 tag message，不能仅以 tag target 认定二进制构建 SHA；见 S08 |
| Basalt | a04edb960cf3b7e5df2db2d70169ca615bcfbf21 | [提交](https://github.com/jesdga95/basalt/commit/a04edb960cf3b7e5df2db2d70169ca615bcfbf21) |
| tandem.cpp | b03b0014674576b685d9641f01da1bbccf2d5afc | [提交](https://github.com/ewhacc/tandem.cpp/commit/b03b0014674576b685d9641f01da1bbccf2d5afc)；README 文件 blob 为 02fc9c2abf7d50768234567e12de7237059b8584 |
| Infernix | 09d6dd21a3dccfab858f0450deb0ec172583578a | [提交](https://github.com/Wallawalla47/Infernix/commit/09d6dd21a3dccfab858f0450deb0ec172583578a)；根 CMakeLists.txt 文件 blob 为 1b51313ed99ce2934d394455d116c90689000ca0 |
| FreeToken | ee43b2a11345d056ba349d22ee073c6828b1364b | [提交](https://github.com/FlashML-org/FreeToken/commit/ee43b2a11345d056ba349d22ee073c6828b1364b)；文档与依赖说明补查，未做性能复现 |
| 5060 Ti Gist | history revision 7886e445ac61d2ae6ff03fc3c6e8f8927f22d7f4 | 不是 raw URL 中的 110b434… 标识；见 S07 |

文件 blob SHA 只标识文件内容，不能当作 repository commit，也不能放入 commit URL 冒充提交。

## S01 — 本机环境、模型与历史基线纠正

**来源**

- [02_ENVIRONMENT.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/docs/02_ENVIRONMENT.md)
- [实验主目录](https://github.com/lkyprogramer/CodexGame/tree/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab)

**读到什么**

历史环境为 RTX 4090、Xeon Silver 4216、2×32GB DDR4、CUDA 12.3、SM89，单会话 Pi/Java 目标。10-08 的 IQ3_S / 75.1 tok/s / 8004 slots 等旧记录已被标为过时；10-23 后实验主线为 GSQ-RCO IQ3_XXS 混合包。GU 和 down 的真实 dtype 按层混合，不能由包名推断所有矩阵格式。

**证明边界**

这是固定提交里的环境记录，不是本次实时硬件、服务或资产检查。不能证明用户今天未换回 IQ3_S，也不能证明对方同名 pack 与本机字节相同。原始 shell、PCIe、RAM 通道和二进制检查未在本次目标机执行。

## S02 — NEXT_ACTIONS 与最新收口

**来源**

- [plans/NEXT_ACTIONS.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/plans/NEXT_ACTIONS.md)
- [FRONTIER-CLOSURE-ASTRA-20261031.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/FRONTIER-CLOSURE-ASTRA-20261031.md)
- [ASTRA_REASSESSMENT_20261031.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/reports/ASTRA_REASSESSMENT_20261031.md)
- [frontier/docs/03_CANDIDATE_DECISION.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/docs/03_CANDIDATE_DECISION.md)

**读到什么**

2026-10-31 采纳 Astra 收口，现冻结合同为 NO_QUALIFIED_CANDIDATE；撤回“优先 F02”，取消拟追加四小时审计，不转另一方向续测。F02 保持 DEFERRED_NEW_EVIDENCE，六 FAIL 和 P05 BLOCKED_EVIDENCE 保留。新机制需有当前真实暖态命中、可闭合依赖、成本账及独立授权。

**证明边界**

关闭是对现有证据和合同的资格判断，不是数学证明“全局无优化空间”。NEXT_ACTIONS 中较早的停机段落已被顶部生产恢复说明及 S06 覆盖，不能择取旧 inactive 状态作为 GPU 空闲凭证。

## S03 — 关闭台账与 64 方向映射

**来源**

- [01_EVIDENCE_AND_CLOSURES.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/docs/01_EVIDENCE_AND_CLOSURES.md)
- [V2_64_DIRECTION_CROSSWALK.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/history/V2_64_DIRECTION_CROSSWALK.md)
- [P2-NP3-TRACE-20261026.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/P2-NP3-TRACE-20261026.md)
- [P2-NPRES-PCIEFRAC-20261026.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/P2-NPRES-PCIEFRAC-20261026.md)

**读到什么**

POOL、VNNI、gather、PCIe 分工、lag/async、spec、lookup、trim/MMAP、KVGROW、HC 等已有结果与限制。台账区分“实际运行无益”“关闭态审计未准入”“未测”，并纠正 NP3 固定同步开销等旧归因。

**证明边界**

不能把 P10/P11 关闭态上界审计写成开关开启后的实测退化；不能写 spec6 已测；不能把旧 profiled 条件成本当当前严格全局上界。旧 v2 研究计划受后来的关闭台账约束，不是重新遍历 64 个方向的许可。

## S04 — Snapshot、P6、P00 与 P9 身份

**来源**

- [frontier/docs/00_SNAPSHOT.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/docs/00_SNAPSHOT.md)
- [P6-V027-BASELINE-20261028.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/P6-V027-BASELINE-20261028.md)
- [P00-EVIDENCE-20261030.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/P00-EVIDENCE-20261030.md)
- [P9-HIGHER-PRECISION-LOGITS-20261028.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/P9-HIGHER-PRECISION-LOGITS-20261028.md)

**读到什么**

生产 A0 为 v0.2.3 / 5c8dd322… 加部署补丁；研究 B/P6 为 v0.2.7 / engine 0.1.52 / 5e8a4cca… 加六文件 Python port。P6 报告 binary SHA256 为 58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22。冻结 INT8 KV、resident20480、spec4/min-p0.5、总会话缓存6144MiB/4slots、PT0，以及 EXACT6、关闭键和 presence-sensitive profiling 规则。

P9 记录 GSQ-RCO 发布 revision ed59f92082b1e93c0e96d60a8b11aab089b52f09 与分片 SHA256；IQ3_S 是独立参考图诊断，不是已切换生产模型。16/16 长输入 argmax 相同，原错误和提前 EOS 保留。

**证明边界**

本次读到的是 hash 清单与报告，不是重新取得模型、pack、tokenizer、MTP 和 binary 后逐件 hash。更高精度小样本没改变错误，不证明所有量化影响被排除，也不修复原六 FAIL。

## S05 — P01B 与计时分母

**来源**

- [P01B-PI-WARM-DIAGNOSTIC-20261031.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md)
- [忽略规则](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/.gitignore)

**读到什么**

单引擎三请求执行 COMPLETE、资格 INSUFFICIENT，无重试；输出941/576/774。append_2 read291/reused89207、完整 wall8.4737秒。774/8.4737≈91.34 tok/s 是从报告数字作的请求级算术，不是 native decode 复算。TTFT 为首 thinking 事件。HTTP 投影使用 tool_choice=none，不是完整 Java 工具链验收。

窄 verify返回→commit进入 host gap 占 native decode 0.1340% /0.1224%，只否定该窄方向的4%机会。

**证明边界**

workspace/frontier/p01b-20261031 在仓库读取返回404；REQUESTS.jsonl、原始 token IDs、SQLite、assets.json 未取得。本次不能独立复核原始计时与完整性，也不由 wall−TTFT 反推 native decode。142.8/122.5 tok/s 在总结中只保留为用户提供的短样本口径，未宣称本次从原件重算。GPU内部、CPU dtype×nt、其他依赖仍 UNKNOWN。

## S06 — 生产恢复历史回执

**来源**

- [PRODUCTION-RESTORE-20261031.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/PRODUCTION-RESTORE-20261031.md)

**读到什么**

文档收口后用户另行要求恢复既有服务；报告记2026-10-31北京时间12:49 loaded=true，12:50:44 active/running/enabled，NRestarts0，未修改既有配置或追加GPU实验。

**证明边界**

这是最后一次带时间历史回执，不是2026-11-02实时状态。既不能声称“现在一定在运行”，也不能用更早停机回执认定可占用GPU。新硬件阶段仍需独立授权。

## S07 — 5060 Ti Gist

**来源**

- [Gist](https://gist.github.com/thisisspartan/ced4de87227f6da197c095cbd429ad6c)
- [官方 API 与 history](https://api.github.com/gists/ced4de87227f6da197c095cbd429ad6c)
- [固定 history revision 定位](https://api.github.com/gists/ced4de87227f6da197c095cbd429ad6c/7886e445ac61d2ae6ff03fc3c6e8f8927f22d7f4)
- [实际读取的 raw 文件](https://gist.githubusercontent.com/thisisspartan/ced4de87227f6da197c095cbd429ad6c/raw/110b434ea5c818350b59a9ec83bd80dcf6a9ba4b/gistfile1.txt)

**读到什么**

API/history 与 raw 已读取；固定 revision 单独端点未另行重取。只有 gistfile1.txt，1776字节，无评论或 benchmark附件。路径均为IQ3_XXS；q4_0、resident32768、HC_Q8=1、COUPLED=1、cyrillic draft vocab、5363 slots、PCIe0.19等是配置事实。description 029、exe/CUDA路径不是二进制身份。

**证明边界**

95–106 tok/s、约100K、0.2秒重读、Basalt Prefill+35%、Strata Decode+15%仍是用户转述的作者宣称，Gist没有对应原始性能证据。max-context131072只证明容量配置，不证明实测填充100K。vision.max_tokens不是输出长度。CPU、内存通道、资产hash、请求与计时合同未知。

## S08 — 官方版本、tag 与发布资产

**来源**

- [Strata c62d5提交](https://github.com/Niko1221/Strata/commit/c62d5e3a15b40ea51c96aae9e8d36928965f53ab)
- [v0.2.9 release](https://github.com/Niko1221/Strata/releases/tag/v0.2.9)
- [annotated tag对象 d94bac6…](https://api.github.com/repos/Niko1221/Strata/git/tags/d94bac6aa33065f5e6a65cca111846627599e318)
- [发布引擎构建提交99866a47…](https://github.com/Niko1221/Strata/commit/99866a47a2b8a21b131aad162a584ee9da92f8f0)

**读到什么**

main和tag target为c62d5；release发布于2026-10-31。tag message区分引擎/SYCL包与App/Terminal/Control等构建来源：引擎来自99866a47，后者来自c62d5。v0.2.9不是“所有资产由同一SHA构建”的保证。

**证明边界**

源码审计没有下载并验证用户安装的实际包、二进制、CUDA库或编译开关；本报告也不授权升级P6。PR文档或release说明与源码门控冲突时，以固定源码的可执行门控为当前实现证据。

## S09 — P24 HC 与 F03 Snapshot 的关闭证据

**来源**

- [P24-HC-PAIRED-PERFORMANCE-20261029.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/P24-HC-PAIRED-PERFORMANCE-20261029.md)
- [F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/reports/F03-SNAPSHOT-LIFECYCLE-AUDIT-20261031.md)

**读到什么**

P24六对正式报告：TTFT比0.991756、CI[0.981959,1.000352]；完整wall比1.009464；完整decode比1.044275、CI[1.020868,1.068783]。确实减少buffer/carve、借槽与搬运，但没变成净收益。

F03两份合法parked image合计4.2993GiB；没有证明可删除owner。唯一去零填原型完整CPU成本三对慢6.08%–7.74%，不保留候选。

**证明边界**

P24是HC临时激活/暂存复用，不是S12的HC权重量化；负结果不等同覆盖后者，但也不为后者授权。P24原始统计未独立复算。F03没有GPU测试，不能称GPU回归；park串行时间是观测成本，不是可安全删掉的时间。

## S10 — KV cell字节数与显存计算

**来源**

- [strata_control/vram_fit.py](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/strata_control/vram_fit.py#L36-L41)
- [ModelGeometry](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/include/strata/core/geometry.hpp)

**读到什么**

KV_BYTES明确fp16=2112、int8=1056、q4_0=576、k8v4=816，单位是每token每attention-layer。此前口头出现的819为笔误，已纠正。

总结的主KV账用12个主干QSA层；vram_fit完整session估算用13层及经验factor，不应把两者混成同一分母。131072逻辑cells与20480/32768驻留cells分开计算；q4_0×32768对int8×20480的这一个GPU数据项仅差31.5MiB。

**证明边界**

以上是源码尺寸计算，不含MTP、index、GDN、Graph、scratch、snapshot、分配粒度及生命周期。不能把全逻辑KV差额全部兑换成GPU专家缓存，也不能将经验session估算当实测整卡峰值。

## S11 — Q4 / K8V4 精度、性能与长上下文

**来源**

- [2026-09-27-kv-q4官方实验](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/bench/results/2026-09-27-kv-q4/README.md)
- [DETAILS中的KV说明](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/docs/DETAILS.md#L210-L218)
- [K8V4 PR120](https://github.com/Niko1221/Strata/pull/120)
- [119K/198K作者实验](https://github.com/Niko1221/Strata/pull/120#issuecomment-5893652119)
- [维护者确认手工整合](https://github.com/Niko1221/Strata/pull/120#issuecomment-5895474702)
- [当前KV streaming接口](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/include/strata/kernels/kv_stream.hpp)；[parity测试源码](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/kernels/kv_stream_parity.cpp)

**读到什么**

INT8默认；Q4/K8V4可选。官方Q2_0 teacher-forced比较显示q4 docs PPL在1K/8K约+8%/+12%，KL为int8的2.6–4.2倍；needle含128K/262K成功案例。K8V4是K-int8/V-rotated-Q4；社区3090 CoderIQ1_M有119K/198K性能和needle记录。

PR120 API closed/merged=false不等于功能不可用：维护者明确手工整合，当前源码已有。其早期正文“不支持streaming”不能覆盖当前实现。

**证明边界**

needle通过不等于长链Agent质量等价，低bit不属于原无损合同。未找到同GSQ-RCO IQ3_XXS、4090+4216、>100K完整Agent的严格质量/性能对照；不把Q2_0或3090数字外推为收益百分比。

## S12 — HC_Q8 源码、默认、显存与质量

**来源**

- [native_dense.cpp默认](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/native_dense.cpp#L45-L90)
- [量化、分配与scratch](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/native_dense.cpp#L426-L478)
- [HC维度](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/kernels/cuda/gr.cu#L20-L23)
- [A4000 IQ3_XXS质量实验](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/docs/AMD_HIP.md#L679-L700)
- [不再保留整套BF16副本的提交](https://github.com/Niko1221/Strata/commit/b60aab1ba27ccf87c9177190fd83a25f83a4b874)
- [另一个HC_REQ8实现](https://github.com/Niko1221/Strata/commit/2f44bf51dd22cf6b1b91f85ab1a72c3069a0d30d)

**读到什么**

native IQ*的CUDA分支HC_Q8默认off；gfx1151/gfx12有默认on。UD setup另有设置，不能外推到本机native包。已有Q8_0时读原字节；BF16 pack则在load时量化层内down/up，inject及该pack的final mixer保留BF16。Prefill需要时反量化到复用scratch。

按48层×4矩阵×320×10240：BF161200MiB→Q8_0(34bytes/32weights)637.5MiB；4个6.25MiB scratch合25MiB，原始字节净差537.5MiB。HC_REQ8的675MiB采用FP32 scale，是另一实现。

A4000 IQ3_XXS 4995位置的teacher-forced实验为top1同95.4%、KL .0251；Agent文本KL .0779。官方也报告纯CPU/GPU BF16舍入差KL .0228作为量级参考。

**证明边界**

537.5MiB是计算而非实测；cudaMalloc粒度、资产来源、自动cache规划可能改变实际收益。该开关改变数值，不是P24的buffer复用，也不能用短teacher-forced数据承诺128K Agent质量。AMD速度结果不证明SM89收益。

## S13 — 草稿词表、COUPLED 与采样语义

**来源**

- [DETAILS词表/MTP](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/docs/DETAILS.md#L315-L331)
- [coupled_draft.hpp](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/include/strata/core/coupled_draft.hpp#L1-L17)
- [已有coupled计时比较](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/docs/DETAILS.md#L1446-L1447)
- [draft_vocab.py](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/tools/draft_vocab.py)

**读到什么**

词表限制draft proposal，不限制target最终输出词表。默认包含全部CJK；en省约110MiB但CJK几乎无draft。纯COUPLED默认off，令draft使用target采样链与同一Philox随机数，target仍exact-match其自身sample。固定target数值/历史/采样器时，proposal只决定每轮接受数，不改变target选择。

3060 IQ3_XXS的12对数据接受率上升而decode42.8对43.3 tok/s在噪声内；另一10对温度比较中coupled持平或更慢。提高接受率不是充分收益证据。

**证明边界**

自然执行时batch形状、CPU/GPU舍入、adaptive等可能改变target数值，理论target-fixed不等于整机字节一致。GUMBEL会同时改target采样器；SPEC_PROB是另一拒绝采样路径，不能与纯COUPLED混称。无>100K本机接受率、完整draft+verify耗时及任务质量证明。

## S14 — DFlash2 当前服务门、Ada反例与未合并服务PR

**来源**

- [drafting.py服务门](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/strata_control/drafting.py#L141-L183)
- [DFlash2接口](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/include/strata/core/dflash2.hpp)
- [工具/研究说明](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/tools/dflash2/README.md)
- [4060Ti社区报告issue3965](https://github.com/Niko1221/Strata/issues/3965)
- [服务/多slot PR4937](https://github.com/Niko1221/Strata/pull/4937)

**读到什么**

固定main的ENGINE_SERVES_DFLASH2=False；Control请求DFlash2会回退MTP且不下载不可服务的pack。单卡one-shot CLI可用不等于Agent serve可用。

4060Ti16GB+i5-12400F+96GB、IQ3_S社区单pair：16K prompt+16K output，MTP47.64、DFlash42.85 tok/s；MTP约1049MiB继续保留，DFlash另增约1026MiB，expert slots3594→3027。这是风险实例，不是4090预测。

PR4937本次状态open/unmerged、非draft；base为c62d5，head为761fe6c00fd3a40a1dbc6af0b1fd420d0d5c53af。作者正文记录42864fcc在gfx1201测试，含c=2/c=4 batched co-draft、prefill lending和serve改造。当前47文件、+6356/-517，不是一个无维护开关。

**证明边界**

PR正文测试revision与当前head不同，不能自动认定head全部验证；作者未运行CUDA/SYCL/Apple硬件及物理多GPU。其并发结果不证明4090单会话>100K收益。Open PR没有解除main的False门，额外显存和保留MTP风险仍须纳入完整账。未在本次运行任何草稿实验。

## S15 — STRATA_LOOKUP PR4928

**来源**

- [PR4928](https://github.com/Niko1221/Strata/pull/4928)

**读到什么**

本次为open/unmerged、非draft；base c62d5，head fbe58ddd7a6a75e0d3c072aadcc5127eb7f15b45。默认off，CUDA需wide-window构建；面向single-slot长复制9–16窗口，利用SuffixDrafter，MTP分块回放与收益校准。

作者的P40复制场景有正例，5090无净增益，vision情形可退化。Pascal batch2+长窗口故障被门控禁用，未根因闭合；未测HIP/SYCL。

**证明边界**

不能把P40百分比写成4090预期收益，也不能只凭copy benchmark证明Pi/Java自然负载覆盖。旧#4040约0.8%可加速覆盖的本机反证仍需解释；PR状态与作者验证是截点记录，不代表已合并主线。

## S16 — Strata 已有Q8输入共享与accepted-only MTP

**来源**

- [verify输入量化共享](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/verify.cpp#L1490-L1517)
- [routed/shared额外QDEDUP](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/verify.cpp#L2152-L2165)
- [MTP capture_round](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/mtp.cpp#L1330-L1357)
- [MTP默认T=a+1](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/mtp.cpp#L1624-L1628)

**读到什么**

Verifier已经一次quant_in供多个projection复用xq/xil；另有默认off的STRATA_VERIFY_QDEDUP用于特定native、非shared-fork路径。MTP默认只catch-up接受的a+1行，而不是所有被拒行；catch-up与首draft处于同一capture round。

**证明边界**

这些对应tandem优化的主要功能意图，不是声明两个引擎逐行同构。不能把已存在结构再列为“待移植新收益”；QDEDUP可审资格，但没有本机净益证明。当前main的存在也不自动证明P6二进制拥有完全相同版本，需逐提交核对。

## S17 — Prefetch、retained weights、cache与默认值

**来源**

- [Prefill stream-ahead默认](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/prefill/prefill.cpp#L174-L191)
- [PR789](https://github.com/Niko1221/Strata/pull/789)；[整合提交6f21c9d…](https://github.com/Niko1221/Strata/commit/6f21c9d912e389f147df1035e09c0d906981937c)
- [RAM预算内保留借出expert权重与refill](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/expert_source.cpp#L3615-L3692)
- [cache尺寸与同层替换](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/include/strata/core/expert_cache.hpp#L96-L170)
- [adaptive async条件自测默认](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/include/strata/core/adapt_async_default.hpp#L1-L70)
- [CUDA默认与route-tail区别](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/docs/DETAILS.md#L1002-L1004)
- [nv_defaults.cpp](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/nv_defaults.cpp)

**读到什么**

STREAM_AHEAD默认true；已有staging ring、expert cache尾槽借用、RAM预算内保留副本、后续refill。PR789虽API未merge，功能实际已整合。当前cache替换API是same-layer，profile-sized槽不把专家移去另一层槽。

适用CUDA serve的adapt-async已经条件自测，不是普遍off；CPU-bound旧Xeon有退化反证。ROUTE_TAIL_SKIP=7在适用CUDA路径默认，语义是跳过低rank未缓存专家并改变输出，不是cache优化。nv_defaults有SM86/SM60/SM121特定栈，不能当SM89默认。

**证明边界**

“已有retained weights”仅指上面精确定义，不能外推任何形式的跨请求/跨层缓存都已实现。跨层动态配额是另一类需要尺寸、地址稳定性及重整成本的代码项目，未证明当前缺口与收益。已有arena/lend之外的临时显存不能因“看似空闲”永久占用，须覆盖下一轮Prefill/KV/Graph生命周期。默认存在不等于P6已开启或应强制覆盖冻结参数。

## S18 — tandem.cpp 与 Infernix

**来源**

- [tandem固定README](https://github.com/ewhacc/tandem.cpp/blob/b03b0014674576b685d9641f01da1bbccf2d5afc/README.md)
- [tandem.patch](https://github.com/ewhacc/tandem.cpp/blob/b03b0014674576b685d9641f01da1bbccf2d5afc/tandem.patch)
- [tandem BASE_COMMIT](https://github.com/ewhacc/tandem.cpp/blob/b03b0014674576b685d9641f01da1bbccf2d5afc/BASE_COMMIT)
- [Infernix固定CMakeLists.txt](https://github.com/Wallawalla47/Infernix/blob/09d6dd21a3dccfab858f0450deb0ec172583578a/CMakeLists.txt#L3-L26)
- [Infernix固定README](https://github.com/Wallawalla47/Infernix/blob/09d6dd21a3dccfab858f0450deb0ec172583578a/README.md)
- [Infernix Flash-Next设计记录](https://github.com/Wallawalla47/Infernix/blob/09d6dd21a3dccfab858f0450deb0ec172583578a/docs/maintainer/qwen3_8-flash-next-design.md)
- [Infernix prefix-cache设计](https://github.com/Wallawalla47/Infernix/blob/09d6dd21a3dccfab858f0450deb0ec172583578a/docs/maintainer/hybrid-prefix-cache-spec.md)

**读到什么**

tandem是llama.cpp f5222f25c上的patch set，包含Q8 activation缓存与MTP defer。README的4090+i5-12400F+64GB DDR4 GSM8K结果比本机硬件更接近，但仍是不同CPU、权重、请求与短负载；其Strata exact-mode主动关闭ROUTE_TAIL_SKIP，比较合同应保留。

Infernix当前根CMake硬限SM120a且CUDA>=13.4；因此不能直接在SM89/4090换引擎。README主要5090+7950X+DDR5、不同草稿/并发证据。设计记录同时含实现、计划、失败和撤回，需逐项核对；其prefill staging / PLE预取概念不能当Strata从未实现。

**证明边界**

不把第三方整引擎收益归因于单一待移植机制。tandem的两个主要概念已有S16对应结构；Infernix的DFlash资源策略不同，不能忽略MTP保留、expert cache和并发。未建立一个已经证明必要、可低维护移植且128K单会话净益明确的新Infernix差量。

补查已将固定commit文件与blob匹配：tandem README为02fc9c2…，Infernix CMake为1b51313…；这些不是commit SHA。

## S19 — Basalt 的Ada参考范围

**来源**

- [CMake SM120门](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/CMakeLists.txt#L40-L45)
- [FP4目标单独SM120a](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/CMakeLists.txt#L1307-L1310)
- [Prefill run.cpp](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/src/prefill/run.cpp#L29-L69)
- [IQ fused prefill](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/src/prefill/moe_fused_iq.cu#L131-L150)
- [原生NVFP4 prefill](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/src/prefill/fp4/moe_fp4.cu#L51)
- [ahead.cpp](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/src/prefill/ahead.cpp#L14-L19)
- [GDN chunked](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/src/prefill/gdn_chunked.cu#L1-L8)
- [精度路径说明](https://github.com/jesdga95/basalt/blob/a04edb960cf3b7e5df2db2d70169ca615bcfbf21/docs/precision/index.md#L79-L86)

**读到什么**

当前build拒绝非SM120，FP4子目标用SM120a。IQ fused路径可看到>=SM800守卫、cp.async与INT8 MMA，故非FP4部分有Ada代码参考价值；NVFP4 Tensor Core指令本身不能照搬。run.cpp当前是chunk外层、layer内层，不是整prompt layer-major。

**证明边界**

一个内核有SM800守卫不等于完整项目支持4090；修改CMake也不证明正确或更快。需要与Strata已有融合、stream、cache逐函数比出新差量并证明完成路径暴露成本。Gist没有给出Basalt+35%的原件，不能作为移植收益承诺。

## S20 — F05/F06/F07 与性能、数值、质量合同

**来源**

- [F05_MOE_GROUP_SCRATCH.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/candidates/F05_MOE_GROUP_SCRATCH.md)
- [F06_STABLE_INTEGER_GROUPING.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/candidates/F06_STABLE_INTEGER_GROUPING.md)
- [F07_MMQ_POOL_EPOCH.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/candidates/F07_MMQ_POOL_EPOCH.md)
- [06_BENCHMARK_PROTOCOL.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/docs/06_BENCHMARK_PROTOCOL.md)
- [05_NUMERICS_AND_QUALITY.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/docs/05_NUMERICS_AND_QUALITY.md)
- [F10_TARGET_FIXED_DRAFT.md](https://github.com/lkyprogramer/CodexGame/blob/b4fb53ff88df2cea58149483533cef7159fb9120/docs/strata_4090_128k_lab/frontier/candidates/F10_TARGET_FIXED_DRAFT.md)

**读到什么**

F05只研究GU/H/Xq/Hq行窗，保留全Dm与K10原combine；T16384×K10×N2560×FP32的Dm单项1.5625GiB是必须保留的尺寸，不是节省。F06已有mapped/fused grouping前提；F07已有CachingPool，不能假定每次cudaMalloc。

frontier主性能门m=max(4%,2×A/A噪声)，主时间比CI上界<=1−m，非目标<=1.02。旧通用5%、P3与P24各有自己的合同，不追溯混用。P05稳定自然warm fixed2048原件资格不足，连A/A也不能自动起跑。

质量合同保留六FAIL；相对2pp非劣使用指定Clopper–Pearson上下界公式，30对全一致不足；按该公式，全一致至少183个独立任务对。多seed/轮/token不是独立任务。

**证明边界**

候选文档是有条件设计，不是准入或实测收益。冷Prefill/长追加合同不能在warm Decode失败后临时替换主指标。旧E0/E1分类、统计通过或性能研究不解除六FAIL；HC_Q8/KV低bit应另立质量合同，不混入原无损收益表。

## S21 — FreeToken 的机制参照与64GB内存前置门

**来源**

- [README](https://github.com/FlashML-org/FreeToken/blob/ee43b2a11345d056ba349d22ee073c6828b1364b/README.md#L18-L24)
- [models.md](https://github.com/FlashML-org/FreeToken/blob/ee43b2a11345d056ba349d22ee073c6828b1364b/docs/models.md#L162)
- [pyproject.toml](https://github.com/FlashML-org/FreeToken/blob/ee43b2a11345d056ba349d22ee073c6828b1364b/pyproject.toml)
- [install.md](https://github.com/FlashML-org/FreeToken/blob/ee43b2a11345d056ba349d22ee073c6828b1364b/docs/install.md)
- [quickstart.md](https://github.com/FlashML-org/FreeToken/blob/ee43b2a11345d056ba349d22ee073c6828b1364b/docs/quickstart.md)

**读到什么**

README定位通用异构MoE serving，声称支持RTX30/40/50；依赖显示Python/PyTorch/Triton/CUDA技术栈。README列semantic-anchor recurrent+KV checkpoint、elastic KV/expert VRAM、全层双buffer Prefill与带宽自适应CPU/GPU分工，能作为机制参照。

models.md明确Flash-Next的47.7GiB PLE n-gram table常驻host pinned RAM。对64GB目标机，这是必须先闭合的容量前置门：不能只看24GB VRAM，还要容纳专家、其他权重、状态、运行时与OS；当前未证明能在保留安全余量时容纳。47.7GiB单项本身并非数学上超过64GB，因此本报告不把它简化成“绝对不可能运行”。

**证明边界**

本次读README/install/models/quickstart/pyproject，未审完相应cache/scheduler实现，也未测迁移收益。未找到Flash-Next+4090+>100K单会话的同条件benchmark；“支持RTX40”不证明该模型/量化/容量组合可用，更不证明可直接替换Strata或将宣传机制变为新的低维护补丁。先核内存布局、资产格式和Strata现有等价机制，不能因为项目名称新就解除旧关闭结论。

## 本次未取得的原件与开放问题

| 缺口 | 当前证据状态 | 不允许的替代 |
|---|---|---|
| P00完整IDENTITY/资产表、实际pack/MTP/tokenizer/binary | 仅报告与hash清单；目标文件未重新hash | 把路径相同、模型名相同或tag相同当字节相同 |
| P01B REQUESTS.jsonl / ANALYSIS / token manifests / SQLite等 | workspace被忽略；读取目录404 | 用wall−TTFT凑native rate，重跑后冒充原run |
| P24 PREREGISTRATION / ANALYSIS与逐pair原件 | 取得报告，未独立复算 | 事后剔除慢样本、改变CI或失败替补 |
| F03 owner/lifecycle ledger及CPU原始样本 | 取得报告 | 将RSS或park时间直接解释为泄漏/可删量 |
| 5060Ti作者benchmark、CPU/RAM/实际context、冷暖顺序 | Gist仅配置 | 把max-context当输入长度，把作者转述当复现 |
| 当前本机生产状态与当下资产 | 仅2026-10-31历史回执 | 自动停服务、占GPU或宣称当前可用 |
| 当前稳定warm fixed2048与完整任务质量合同 | P05 BLOCKED_EVIDENCE、六FAIL保留 | 自动A/A、缩短到自然EOS样本后称过门 |
| >100K同硬件HC_Q8/KV/coupled/DFlash净益与质量 | 未找到同条件公开证据 | 借AMD/5090/3090/短needle百分比填空 |
| FreeToken在64GB上完整模型/状态容量与同条件表现 | 文档只有47.7GiB pinned PLE前提，完整账未闭合 | 把RTX40支持列表或单项内存大小当可运行/不可运行的完整证明 |

优先动作是找回并验真既有原件、明确新合同与身份，不是以缺证据为由默认重跑。来源索引本身不产生实现、实验、生产变更或质量取舍的授权。

