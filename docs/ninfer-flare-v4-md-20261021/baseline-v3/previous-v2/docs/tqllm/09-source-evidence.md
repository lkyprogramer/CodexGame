> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 固定源码与证据边界

基准日期2026-10-15。以下是源码读取结果，不是本次运行结果；行号锚点用于导航，最终以固定提交的函数/符号为准。Git blob SHA来自GitHub接口，未对未下载的整文件声称本地重算。

## T01

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/README.md#L10-L195>

GGUF/TQ weight formats; 65K draft vocabulary; author-reported 3090 speed and retrieval results, not a NInfer A/B.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`ef194ddaf92c100c8a6af6dec0cf78e3d9cdcbb7`。

## T02

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/docs/ARCHITECTURE.md#L1-L56>

Engine, format registries, unified attention arithmetic, memory fit and graph invariants.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`9cd0ea00b11d698af4e740fd16d1c7cf4aa6c6bc`。

## T03

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/src/qwen35.cpp#L2932-L3105>

DFlash2 metadata, all-layer KV projection, full-vs-ring allocation, retrieval sets ring=0; draft head rows mapping.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`6451d86b623ebdbf2d82a274431dc0eb9ea26a7d`。

## T04

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/src/qwen35.cpp#L3194-L3280>

Target feature projection and per-layer draft K/V injection; batch path refuses ring<=0.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`6451d86b623ebdbf2d82a274431dc0eb9ea26a7d`。

## T05

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/src/qwen35.cpp#L3422-L3505>

Single draft graph gated on ring>0 and !subset; physical block B and retrieval per layer.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`6451d86b623ebdbf2d82a274431dc0eb9ea26a7d`。

## T06

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/kernels/qwen35.cu#L975-L1100>

RCHUNK16, last4096 remote chunks, deterministic per-head top-k, virtual-position RoPE gather.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`f50a84932d1ced84ce07871b146b8ad290fabab6`。

## T07

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/kernels/dflash.cu#L80-L180>

Dynamic two-tap grouped convolution, deterministic top16 and conditioned lattice score.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`edac1ff8808ba5555660eb38fcd873878200a2b6`。

## T08

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/README.md#L200-L365>

Static mtp-from threshold, lookup, effective verify maximum8, memory fit can change context/codec, sampling and performance restrictions.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`ef194ddaf92c100c8a6af6dec0cf78e3d9cdcbb7`。

## T09

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/tests/dflash_exact.cpp#L1-L72>

Plain/tree/linear token equality test reads at most12000 source characters; context argument does not establish long actual prompt coverage.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`f1e0a0394408330c6ce04d86c4be5511a92cde9c`。

## T10

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/tests/dflash_retrieve.cu#L1-L165>

pos6000 planted-chunk and RoPE tests; no coverage of retrieval candidate truncation beyond65K.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`83f51785b102f22453bb4132f5207e26dcae021e`。

## T11

来源：<https://github.com/turbo-tan/tqllm/blob/4d27324a124f92b7b7dcc554e6406ab6dc645b49/NOTICE>

Apache2.0 project, third-party MIT/public-domain notices; file-specific attribution needed.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`036b04a04cdcc1233b01bca71b9a5e4356975b39`。

## N01

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8_27b/impl/config.h#L10-L112>

27B has16 full-attention layers, KV4x256, MTPmax5, DFlash unsupported; configured1M ceiling not4090 capacity evidence.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`12fc566958ed12eb604f6b0487fe5bdc5b33af29`。

## N02

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8_27b/impl/variant.h#L16-L48>

Already has131072-row optimized draft head and closed compile-time target leaves.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`be35018217346c6bff76f9a1c80fdbf97ab1c454`。

## N03

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_6_35b_a3b/impl/config.h#L60-L120>

35B DFlash supported, different geometry/features; cannot flip27B flag to reuse checkpoint.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`bb13a6e538b062a7d402fefa0dda4997c1cf7079`。

## N04

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/dflash_context.h>

Existing local/full DFlash state and feature buffers, not arbitrary27B DFlash2.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`9482c0e7e210040985f374e21ca5b4dde0d9e81f`。

## N05

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/schedule.h#L28-L160>

TargetVerifyFrameView, target_verify_accept, replay_records, no speculation in decision pass.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`509e6f9e30148b7671a78c5f331f317ca6191e66`。

## N06

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/include/ninfer/types.h#L50-L74>

Startup SpeculativeOptions supports None/Mtp/DFlash; request-level auto policy not existing.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`94b16bab36abc759baad1c1332418c512a3968fc`。

## N07

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/ops/launcher/gqa_attention_decode.cu#L1-L155>

Small-T1..6 and split envelope policy exist; not a generic add-FlashAttention problem.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`bdfbe705521e2f1f77224cbc8195408ae0f11ce9`。

## N08

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/src/targets/qwen3_8/impl/runtime/program.h#L1-L180>

Owned lane/request plans, GDN replay, retained states and bounded entitlement.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`129dd6cc87fe9e61984f16e909b39fe7fcefcab2`。

## N09

来源：<https://github.com/tensorninja/ninfer-4090/blob/5b99996bc7c1fe6ff27f271a205eb605302ec8bb/LICENSE#L1-L35>

NInfer is Apache2.0; does not automatically license external checkpoints.

证据级别：`SOURCE_READ_NOT_EXECUTED`；blob：`261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`。

## R01

来源：<https://aclanthology.org/2026.acl-long.83/>

Publisher abstract: LongSpec constant-sized draftKV, position indices, attention aggregation. No27B256K reproduction here.

证据级别：`PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED`。

## R02

来源：<https://aclanthology.org/2026.findings-acl.2153/>

Publisher abstract: SpecExtend target-guided draft-context retrieval, including16K evaluation; not direct draftKV reconstruction.

证据级别：`PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED`。

## R03

来源：<https://proceedings.mlr.press/v306/lee26d.html>

Publisher search entry: Dustin sparse verification, numerical/accuracy tradeoffs. Page open unavailable here; not an exactness authority or release dependency.

证据级别：`PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED`。

## R04

来源：<https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2>

Model catalog existence corroborated by original DFlash project and model search. Full immutable checkpoint/tensor manifest NOT downloaded; asset gate mandatory.

证据级别：`PRIMARY_ABSTRACT_OR_CATALOG_NOT_REPRODUCED`。

## 输入分析及旧包

原始分析按字节保留在 `../../data/tqllm/user-analysis-original.txt`。原包内容保留与改动清单见 `../../evidence/tqllm/original-package-integrity.json`；更新不是把原实施任务标为完成。相关引用在正文采用T/N/R编号，均对应本页。
