# V2 支撑材料：`data/sources.json`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: data/sources.json -->
<!-- payload-sha256: 3326b9022d4dd9d900082c3df88c0fd434cd4bdbe9f1ea27d7c6f250cda70132 -->
<!-- payload-bytes: 12453 -->

<!-- payload-begin -->
````json
[
  {
    "id": "S01",
    "title": "固定分支、共同祖先和定制 diff",
    "urls": [
      "https://api.github.com/repos/lkyprogramer/ninfer-4090/branches/b0-scanner",
      "https://api.github.com/repos/tensorninja/ninfer-4090/branches/tensorninja",
      "https://api.github.com/repos/tensorninja/ninfer-4090/compare/lkyprogramer:e0b05f7cb46adae2787be2ccbe605e1b0c9b3923...5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "https://github.com/lkyprogramer/ninfer-4090/compare/44a2c6c3392c9d51e76a895ed97bf1867530d252...e0b05f7cb46adae2787be2ccbe605e1b0c9b3923"
    ],
    "supports": "11/34分叉、B/O/U身份、fork43文件numstat。分支查询是2026-10-15时点读数；报告和执行使用SHA锁定。",
    "evidence_kind": "GitHub branch/compare API"
  },
  {
    "id": "S02",
    "title": "历史生产审计",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/evidence/b0/t00/source-audit.md"
    ],
    "supports": "2026-09-28记录的prepare-detail镜像、base+timing overlay、非Git生产目录、当时模型/资源。不是当前生产测量。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S03",
    "title": "O/B/U完整tokenizer头文件",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.h",
      "https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/tokenizer.h",
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/tokenizer.h"
    ],
    "supports": "B0 work/restarts、上游segmented/token_id、2处单头文件merge冲突的输入。附带blob SHA验证和本地实验。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S04",
    "title": "B0 scanner与restart实现",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/tokenizer.cpp",
      "https://github.com/lkyprogramer/ninfer-4090/commit/6b4286de451411b19d75051376b0ede6d461c936",
      "https://github.com/lkyprogramer/ninfer-4090/commit/1d05441bafdb89a254f9e592de53d19c1de4e765"
    ],
    "supports": "首字节索引、added token顺序、request-local counters、只记录selected-token-end的restart。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S05",
    "title": "B1边界校验与memo",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/commit/a5128f058c13c32affa6e40e80dfa1774ca16482",
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/processor.cpp"
    ],
    "supports": "一次主编码、restart局部重编码、memo与旧exact-prefix校验，迁移到新边界结构时的冲突。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S06",
    "title": "上游SegmentedEncoding",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/commit/94cdb5a975e514935ed4be214ee7f776a8683635",
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/tokenizer.cpp"
    ],
    "supports": "SegmentedEncoding/PrefixRelation、显式切点LCP、借用生命周期，与B0重叠的优化边界。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S07",
    "title": "最终processor契约",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/processor.h",
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/processor.cpp"
    ],
    "supports": "PromptBoundary、ProcessedDecisionState、preprocessing_digest、替换占位符后的边界调整。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S08",
    "title": "新旧chat模板结构",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/chat_template.h",
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/targets/qwen3_8/impl/frontend/chat_template.h",
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/frontend/chat_template.cpp"
    ],
    "supports": "旧stable_prefix/checkpoint_hints与新boundaries(kind/publish)、cache_breakpoint和render选项的差异。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S09",
    "title": "fork计时、size与schema20补丁",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/commit/f3b231db68542f01568216711d4fda485fa62799",
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/request_log.h"
    ],
    "supports": "6项prepare_detail、PromptSummary.frontend、raw body size、UTF8字节语义、Vision tokenizer=-1。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S10",
    "title": "新旧GenerationService",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/src/serve/generation_service.h",
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/serve/generation_service.h"
    ],
    "supports": "timing定制与tool begin/arguments/end/progress、Decision handle/lifetime接口重叠。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S11",
    "title": "自定义测试注册和G1驱动",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/CMakeLists.txt",
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/g1_diff_main.cpp"
    ],
    "supports": "真实target、standalone G1、53/74cases、toggle参数、seed与资源要求；文件存在不意味着cases已取得。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S12",
    "title": "midrise codec与决策自有列",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/commit/772b88117867862d9669f4d970929242872bfabe"
    ],
    "supports": "旧E8删除、新midrise编解码、state版本变化；上游4090测得+2.3%prefill及BF16/压缩决策偏差，非本机结果。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S13",
    "title": "异步导出与准入",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/commit/4d3366e5b9a959627a6db1f0eb36932be0482def"
    ],
    "supports": "异步export、fence与lane选择、重叠执行和资源生命周期。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S14",
    "title": "三协议流式工具调用",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/commit/f4089901fa17b83ecbb21bd2bde17bf614c3bf03"
    ],
    "supports": "增量tool parser、typed parameters、Complete/Incomplete、discarded bytes、上游schema20。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S15",
    "title": "决策runtime与OpenAI wire接入",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/commit/ab221dc13cc856fb006df928d16390ba7de73723",
      "https://github.com/tensorninja/ninfer-4090/commit/ab7ada97c4a28b9b26bad0c0cdacb282fe8ca2fc"
    ],
    "supports": "共享27B生成与决策、LoRA/pointerhead、prefill-only branches、两个协议的结构/usage差异。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S16",
    "title": "最终图像决策与缓存版本",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/commit/5b99996bc7c1fe6ff27f271a205eb605302ec8bb",
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/docs/continuation-cache.md",
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/docs/serving.md"
    ],
    "supports": "图像detail/preprocessing身份/MRoPE、snapshot6/targetimage5/decision-alias2、schema24及未训练图像adapter资格限制。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S17",
    "title": "最终产品与所有权契约",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/AGENTS.md"
    ],
    "supports": "sm89、27B/35B构建、NVFP4执行限制、唯一.ninfer、共享Qwen family与单GPUbounded concurrency。仓库指令作为产品说明，不覆盖用户本次目标。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S18",
    "title": "无权重Dockerfile",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/Dockerfile.sm89-nobake"
    ],
    "supports": "CUDA13.2 base、27B-only、无dashboard/无baked model、ENTRYPOINT、编译产物路径。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S19",
    "title": "两个上游里程碑文件对比",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/compare/44a2c6c3392c9d51e76a895ed97bf1867530d252...f4089901fa17b83ecbb21bd2bde17bf614c3bf03",
      "https://github.com/tensorninja/ninfer-4090/compare/f4089901fa17b83ecbb21bd2bde17bf614c3bf03...5b99996bc7c1fe6ff27f271a205eb605302ec8bb"
    ],
    "supports": "两个17commit片段的文件级结构变化。后段API大量stats变0是响应预算现象，不按0求和；完整net量由P0本地生成。",
    "evidence_kind": "GitHub compare API"
  },
  {
    "id": "S20",
    "title": "全部34上游与11fork提交目录",
    "urls": [
      "../data/upstream-commits.json",
      "../data/fork-commits.json"
    ],
    "supports": "每项包含完整SHA、时点、功能、目标phase与原始primary commit URL。标题有归纳，不都逐字复制原commit message。",
    "evidence_kind": "包内从GitHub提交记录整理的索引"
  },
  {
    "id": "S21",
    "title": "Legacy oracle生产DTO依赖",
    "urls": [
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.h",
      "https://github.com/lkyprogramer/ninfer-4090/blob/e0b05f7cb46adae2787be2ccbe605e1b0c9b3923/tests/targets/qwen3_8/reference/legacy_encode_rendered_chat.cpp"
    ],
    "supports": "旧oracle包含生产processor.h并使用已被上游替换的字段，说明无文本冲突也可能编译失败。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S22",
    "title": "最终请求日志schema",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/serve/request_log.h"
    ],
    "supports": "kRequestLogSchemaVersion=24；不能退回fork20，也不抢占后续上游schema号。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S23",
    "title": "真实27B prefix/MTP/vision测试",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/tests/targets/qwen3_8_27b/test_engine_prefix_real.cpp"
    ],
    "supports": "实际环境变量NINFER_QWEN3_8_27B_WEIGHTS、缺权重77；context4096；GDN chunk/INT8浮点可影响argmax，不能强求所有路径逐token一致。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S24",
    "title": "Web构建契约",
    "urls": [
      "https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/apps/web/package.json"
    ],
    "supports": "packageManager=bun@1.3.5、bun test、tsc/Vite build；实际浏览器执行不等于unit test。",
    "evidence_kind": "源码 / commit diff"
  },
  {
    "id": "S25",
    "title": "最终helper验证与单文件合并证据",
    "urls": [
      "../evidence/header-merge/result.json",
      "../evidence/header-merge/tokenizer.h.diff3.txt",
      "../evidence/tool-tests-green.txt"
    ],
    "supports": "本包本地实验范围：header merge2处冲突；32个CPU工具自测（含本地synthetic仓库真merge），不包括NInfer或GPU资格。",
    "evidence_kind": "本地可复跑证据"
  }
]
````
<!-- payload-end -->
