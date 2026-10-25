# 来源锁定与证据边界

核查日期：2026-10-19。最新 HyperQwen 分支查询返回 `30dba4f11b577e1f7699ec0b2947d6fe9d5ea997`（提交时间 2026-10-19 06:37:15 UTC，最新提交是双 5070 Ti 文档；并非宣称本次采用了双卡优化）。用户 `b0-scanner` 和上游 `tensorninja` 查询仍分别为 `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`、`5b99996bc7c1fe6ff27f271a205eb605302ec8bb`。tqLLM 继续使用 V2 已审阅的 `4d27324a124f92b7b7dcc554e6406ab6dc645b49`，没有悄悄更新 donor。

| 身份 | 固定值 | 本次含义 |
|---|---|---|
| 共同祖先 B | `44a2c6c3392c9d51e76a895ed97bf1867530d252` | 原 P0—P6 合入起点 |
| 用户 O | `e0b05f7cb46adae2787be2ccbe605e1b0c9b3923` | 当前可见远程分支，不等于部署镜像 |
| 上游 U | `5b99996bc7c1fe6ff27f271a205eb605302ec8bb` | 原上游整合目标仍有效 |
| HyperQwen H | `30dba4f11b577e1f7699ec0b2947d6fe9d5ea997` | 新算法参考，不是 merge parent |
| P6 合格集成提交 | 尚未提供 | 执行 H0 时从真实 gate 读取，禁止填 U 代替 |
| 产品实现/GPU资格 | NOT_RUN | 本次仅交付研究、架构与执行文档 |

[用户分支查询](https://api.github.com/repos/lkyprogramer/ninfer-4090/git/ref/heads/b0-scanner) · [上游分支查询](https://api.github.com/repos/tensorninja/ninfer-4090/git/ref/heads/tensorninja) · [HyperQwen 固定提交](https://github.com/syv-ai/HyperQwen/commit/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997)

本次使用 GitHub 连接器获取固定 SHA 的关键文件/补丁与分支元数据；Web 搜索用于公开项目当前信息交叉检查。容器直接克隆因 DNS 失败，**没有完整 clone、完整补丁应用或 vLLM/NInfer CUDA 编译**。源码出现的测试通过/速度是作者报告，不能转换成本次实测。

## 新核查的一级来源

| ID | 文件及固定链接 | 阅读范围 | 能支持的结论 |
|---|---|---|---|
| HQ01 | [docs/optimizations.md](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/docs/optimizations.md) | 1–230 | 项目报告：Lookup 专项吞吐、40K 词表覆盖、已有优化及不获益实验；不是本机实测 |
| HQ02 | [patches/dflash2-lookup-drafting.patch](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/patches/dflash2-lookup-drafting.patch) | 1–270;350–710;820–1045 | 实际补丁：trained block、verify block、head/tail fusion、point-mass、双 graph、Sticky 单请求限制 |
| HQ03 | [patches/dflash2-ngram-chains.patch](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/patches/dflash2-ngram-chains.patch) | 1–240 | 实际补丁：chain 首次拒绝退出、正常步刷新证据、greedy/single-request gating |
| HQ04 | [docs/long-context.md](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/docs/long-context.md) | 1–210 | 作者测量：112K MTP/KVarN 对照、Split-KV 4090 A/B、vLLM 页几何；部分输出截断，只采用可见内容 |
| HQ05 | [docs/spec-decode-scratch-token-units.md](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/docs/spec-decode-scratch-token-units.md) | 1–240 | token 行与 sequence 行的容量区别、零吞吐结果、独立 oracle 和编译缓存污染 |
| HQ06 | [prepare/build_draft_vocab.py](https://github.com/syv-ai/HyperQwen/blob/30dba4f11b577e1f7699ec0b2947d6fe9d5ea997/prepare/build_draft_vocab.py) | 1–220 | CJK 稀缺说明、byte-BPE 分类、语料统计、原子发布；存在不同历史覆盖率口径 |
| NI01 | [src/core/gdn_replay_records.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/core/gdn_replay_records.h) | 全文 | ReplaySSM conv/key/value/gate 的实际维度及非 owning 存储 |
| NI02 | [src/targets/qwen3_8/export/ninfer/targets/qwen3_8/runtime.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/export/ninfer/targets/qwen3_8/runtime.h) | 1–240 | TextPhase、GraphExecutionProfile、Program 和 continuation 所有权 |
| NI03 | [src/targets/qwen3_8/impl/runtime/speculative_target_impl.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/speculative_target_impl.h) | 全文 | target_verify_accept：record→target verify→accept→selected hidden→scatter |
| NI04 | [src/targets/qwen3_8/impl/runtime/mtp_impl.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/mtp_impl.h) | 1–235 | mtp_decode_batch_body 绑定 verify、MTP alignment、下一轮 proposal；bridge 支持无 proposal 对齐 |
| NI05 | [src/targets/qwen3_8/impl/runtime/instantiate.h](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/instantiate.h) | 全文 | 实际编译入口及 graph/speculative/decode/mtp 实现文件 |
| NI06 | [src/targets/qwen3_8/CMakeLists.txt](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/CMakeLists.txt) | 全文 | family runtime 按 Variant 实例化，不应增加未实例化的泛型 .cpp |

## 继承来源

原 NInfer 提交/差异明细见 [V2 sources](../previous-v2/data/sources.json.md)；原 tqLLM tensor/检索/Graph 取证见 [tqLLM sources](../previous-v2/data/tqllm/sources.json.md)。这些为继承证据，未对全部文件逐一重抓。附件中的网页速度和论文数据只作待核查输入；本计划不依赖未重验的论文性能数字。

## 输入完整性

V2 ZIP SHA256：`f68e47aab95c34622b95971b25de5b36f0b31a85b63ba40f250c6c6c6cf5cd11`。
HyperQwen 附件 SHA256：`d91f620cd21c0de717dae6fdc0f8d60298243a971cb722ecff6bd09c3667703f`。
保留原文本于 [附件](../inputs/hyperqwen-analysis.md)，包括原文中已过时的 E8 描述和网页渲染残留；纠正项只写在单独审计，不篡改原文。

## 2026-10-20 现场补充与来源状态

上述SHA、来源访问范围和2026-10-19研究是历史锁，不因本次审查升级为部署事实。现场B29是image e753…、binary447e…、E8/schema20；远端无.git目录和PINNED_COMMIT不证明镜像构建来源。完整指纹、BO/B6状态和复现前置见 [baseline执行合同](../plans/05-baseline-29-execution.md)。P6资格commit仍null，不能填U/O代替；当前只跑B29 baseline，不变更这些来源锁。
