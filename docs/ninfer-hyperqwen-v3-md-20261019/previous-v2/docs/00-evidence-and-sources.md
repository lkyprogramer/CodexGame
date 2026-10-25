> V3 继承资料：P0—P6 的任务目标和上游合入顺序继续有效。命令依赖须先按根目录 `support/REHYDRATE.md` 恢复。

# 00｜证据、来源和结论边界

## 审计口径

审计时点为 **2026-10-15**。GitHub连接读取两个仓库的分支、commit、比较结果和重点源码；后续执行全部使用固定SHA。不是只读README作对比，也没有把别人的性能数值当成本机测试。

当前容器不能直接克隆GitHub。已恢复三个完整tokenizer.h、逐字节核对Git blob SHA并运行真实git merge-file；其它重点冲突为source/commit diff语义分析。整仓三方merge、完整上游net file/line总量和全部冲突index由P0在用户主机补齐。因此“16个共享修改路径”不等于“16个已实测冲突”。

定制侧43个文件和11个提交有完整路径/数量账本；34个上游独有提交已逐项归组。上游大compare的部分additions/deletions被预算裁切为0，不参与总量计算，不能声称上游只改了少量代码。

## 三类陈述

**源码事实：** 下列Sxx链接定位到固定SHA文件/commit，支持字段、接口、变化和作者测量描述。**分析与设计：** 单编码器、分阶段merge、scope分离等是本报告的建议，不冒称已经实现。**实际实验：** 仅本包CPU工具自测和单header三方合并；所有NInfer/GPU/生产门禁状态PENDING。

历史生产source-audit只证明其记录日期的配置。当前镜像可能不同，P0重新核对。32个CPU自测通过也不能证明目标C++可编译、真实4090可部署或速度会提高。

## 固定源索引

正文的`[Sxx]`指向下面同号条目；`[Uxx]`指向`data/upstream-commits.json`中的提交。多条编号表示跨文件/提交的联合依据。路径较长时浏览器汇总版可直接点击。

### S01｜固定分支、共同祖先和定制 diff

**类型：** GitHub branch/compare API。**支持：** 11/34分叉、B/O/U身份、fork43文件numstat。分支查询是2026-10-15时点读数；报告和执行使用SHA锁定。

- [来源 1](https://api.github.com/repos/lkyprogramer/ninfer-4090/branches/b0-scanner)
- [来源 2](https://api.github.com/repos/tensorninja/ninfer-4090/branches/tensorninja)
- [来源 3](https://api.github.com/repos/tensorninja/ninfer-4090/compare/lkyprogramer:e0b05f7cb46adae2787be2ccbe605e1b0c9b3923...5b99996bc7c1fe6ff27f271a205eb605302ec8bb)
- [来源 4](https://github.com/lkyprogramer/ninfer-4090/compare/44a2c6c3392c9d51e76a895ed97bf1867530d252...e0b05f7cb46adae2787be2ccbe605e1b0c9b3923)

### S02｜历史生产审计

**类型：** 源码 / commit diff。**支持：** 2026-09-28记录的prepare-detail镜像、base+timing overlay、非Git生产目录、当时模型/资源。不是当前生产测量。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/source-audit.md)

### S03｜O/B/U完整tokenizer头文件

**类型：** 源码 / commit diff。**支持：** B0 work/restarts、上游segmented/token_id、2处单头文件merge冲突的输入。附带blob SHA验证和本地实验。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.h)
- [来源 2](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/tokenizer.h)
- [来源 3](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/tokenizer.h)

### S04｜B0 scanner与restart实现

**类型：** 源码 / commit diff。**支持：** 首字节索引、added token顺序、request-local counters、只记录selected-token-end的restart。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.cpp)
- [来源 2](https://github.com/lkyprogramer/ninfer-4090/commit/6b4286de451411b19d75051376b0ede6d461c936)
- [来源 3](https://github.com/lkyprogramer/ninfer-4090/commit/1d05441bafdb89a254f9e592de53d19c1de4e765)

### S05｜B1边界校验与memo

**类型：** 源码 / commit diff。**支持：** 一次主编码、restart局部重编码、memo与旧exact-prefix校验，迁移到新边界结构时的冲突。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/commit/a5128f058c13c32affa6e40e80dfa1774ca16482)
- [来源 2](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/processor.cpp)

### S06｜上游SegmentedEncoding

**类型：** 源码 / commit diff。**支持：** SegmentedEncoding/PrefixRelation、显式切点LCP、借用生命周期，与B0重叠的优化边界。

- [来源 1](https://github.com/tensorninja/ninfer-4090/commit/94cdb5a975e514935ed4be214ee7f776a8683635)
- [来源 2](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/tokenizer.cpp)

### S07｜最终processor契约

**类型：** 源码 / commit diff。**支持：** PromptBoundary、ProcessedDecisionState、preprocessing_digest、替换占位符后的边界调整。

- [来源 1](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/processor.h)
- [来源 2](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/processor.cpp)

### S08｜新旧chat模板结构

**类型：** 源码 / commit diff。**支持：** 旧stable_prefix/checkpoint_hints与新boundaries(kind/publish)、cache_breakpoint和render选项的差异。

- [来源 1](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/chat_template.h)
- [来源 2](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/chat_template.h)
- [来源 3](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/chat_template.cpp)

### S09｜fork计时、size与schema20补丁

**类型：** 源码 / commit diff。**支持：** 6项prepare_detail、PromptSummary.frontend、raw body size、UTF8字节语义、Vision tokenizer=-1。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/commit/f3b231db68542f01568216711d4fda485fa62799)
- [来源 2](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request_log.h)

### S10｜新旧GenerationService

**类型：** 源码 / commit diff。**支持：** timing定制与tool begin/arguments/end/progress、Decision handle/lifetime接口重叠。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/generation_service.h)
- [来源 2](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/serve/generation_service.h)

### S11｜自定义测试注册和G1驱动

**类型：** 源码 / commit diff。**支持：** 真实target、standalone G1、53/74cases、toggle参数、seed与资源要求；文件存在不意味着cases已取得。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/CMakeLists.txt)
- [来源 2](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/g1_diff_main.cpp)

### S12｜midrise codec与决策自有列

**类型：** 源码 / commit diff。**支持：** 旧E8删除、新midrise编解码、state版本变化；上游4090测得+2.3%prefill及BF16/压缩决策偏差，非本机结果。

- [来源 1](https://github.com/tensorninja/ninfer-4090/commit/772b88117867862d9669f4d970929242872bfabe)

### S13｜异步导出与准入

**类型：** 源码 / commit diff。**支持：** 异步export、fence与lane选择、重叠执行和资源生命周期。

- [来源 1](https://github.com/tensorninja/ninfer-4090/commit/4d3366e5b9a959627a6db1f0eb36932be0482def)

### S14｜三协议流式工具调用

**类型：** 源码 / commit diff。**支持：** 增量tool parser、typed parameters、Complete/Incomplete、discarded bytes、上游schema20。

- [来源 1](https://github.com/tensorninja/ninfer-4090/commit/f4089901fa17b83ecbb21bd2bde17bf614c3bf03)

### S15｜决策runtime与OpenAI wire接入

**类型：** 源码 / commit diff。**支持：** 共享27B生成与决策、LoRA/pointerhead、prefill-only branches、两个协议的结构/usage差异。

- [来源 1](https://github.com/tensorninja/ninfer-4090/commit/ab221dc13cc856fb006df928d16390ba7de73723)
- [来源 2](https://github.com/tensorninja/ninfer-4090/commit/ab7ada97c4a28b9b26bad0c0cdacb282fe8ca2fc)

### S16｜最终图像决策与缓存版本

**类型：** 源码 / commit diff。**支持：** 图像detail/preprocessing身份/MRoPE、snapshot6/targetimage5/decision-alias2、schema24及未训练图像adapter资格限制。

- [来源 1](https://github.com/tensorninja/ninfer-4090/commit/5b99996bc7c1fe6ff27f271a205eb605302ec8bb)
- [来源 2](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/docs/continuation-cache.md)
- [来源 3](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/docs/serving.md)

### S17｜最终产品与所有权契约

**类型：** 源码 / commit diff。**支持：** sm89、27B/35B构建、NVFP4执行限制、唯一.ninfer、共享Qwen family与单GPUbounded concurrency。仓库指令作为产品说明，不覆盖用户本次目标。

- [来源 1](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/AGENTS.md)

### S18｜无权重Dockerfile

**类型：** 源码 / commit diff。**支持：** CUDA13.2 base、27B-only、无dashboard/无baked model、ENTRYPOINT、编译产物路径。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/Dockerfile.sm89-nobake)

### S19｜两个上游里程碑文件对比

**类型：** GitHub compare API。**支持：** 两个17commit片段的文件级结构变化。后段API大量stats变0是响应预算现象，不按0求和；完整net量由P0本地生成。

- [来源 1](https://github.com/tensorninja/ninfer-4090/compare/44a2c6c3392c9d51e76a895ed97bf1867530d252...f4089901fa17b83ecbb21bd2bde17bf614c3bf03)
- [来源 2](https://github.com/tensorninja/ninfer-4090/compare/f4089901fa17b83ecbb21bd2bde17bf614c3bf03...5b99996bc7c1fe6ff27f271a205eb605302ec8bb)

### S20｜全部34上游与11fork提交目录

**类型：** 包内从GitHub提交记录整理的索引。**支持：** 每项包含完整SHA、时点、功能、目标phase与原始primary commit URL。标题有归纳，不都逐字复制原commit message。

- [来源 1](../data/upstream-commits.json.md)
- [来源 2](../data/fork-commits.json.md)

### S21｜Legacy oracle生产DTO依赖

**类型：** 源码 / commit diff。**支持：** 旧oracle包含生产processor.h并使用已被上游替换的字段，说明无文本冲突也可能编译失败。

- [来源 1](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.h)
- [来源 2](https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp)

### S22｜最终请求日志schema

**类型：** 源码 / commit diff。**支持：** kRequestLogSchemaVersion=24；不能退回fork20，也不抢占后续上游schema号。

- [来源 1](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/serve/request_log.h)

### S23｜真实27B prefix/MTP/vision测试

**类型：** 源码 / commit diff。**支持：** 实际环境变量NINFER_QWEN3_8_27B_WEIGHTS、缺权重77；context4096；GDN chunk/INT8浮点可影响argmax，不能强求所有路径逐token一致。

- [来源 1](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/tests/targets/qwen3_8_27b/test_engine_prefix_real.cpp)

### S24｜Web构建契约

**类型：** 源码 / commit diff。**支持：** packageManager=bun@1.3.5、bun test、tsc/Vite build；实际浏览器执行不等于unit test。

- [来源 1](https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/apps/web/package.json)

### S25｜最终helper验证与单文件合并证据

**类型：** 本地可复跑证据。**支持：** 本包本地实验范围：header merge2处冲突；32个CPU工具自测（含本地synthetic仓库真merge），不包括NInfer或GPU资格。

- [来源 1](../evidence/header-merge/result.json.md)
- [来源 2](../evidence/header-merge/tokenizer.h.diff3.txt.md)
- [来源 3](../evidence/tool-tests-green.txt.md)

## 文件快照与许可边界

仅附带3份必要的tokenizer.h用于可核验合并实验；代码版权仍归原仓库作者，来源、提交和Git blob SHA在result.json。没有把整个仓库、模型权重、私有生产流量或凭据装入本包。辅助脚本为本次审计新写，标准库运行，不需要API key。

## 尚未完成的验证（不得转述为已完成）

整仓clone/merge、C++/CUDA build、原G1真实资源回放、所有4090/模型/长context实验、当前PROD身份、生产canary、实际回滚都未在本次环境执行。P0—P6的模板留PENDING，后续Agent用真实raw evidence替换。
