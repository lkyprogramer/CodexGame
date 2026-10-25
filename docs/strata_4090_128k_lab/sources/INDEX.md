# 来源与源码锁

检索日：2026-10-23。以下都是一手仓库资料。性能为作者/社区报告，不是本包在4090上的测量。

## 基线

- Release: https://github.com/Niko1221/Strata/releases/tag/v0.2.3（基线即此 tag；v0.2.3.1 为 Control-only 热修：https://github.com/Niko1221/Strata/releases/tag/v0.2.3.1）
- 上一版: https://github.com/Niko1221/Strata/releases/tag/v0.2.2
- 固定开发树: https://github.com/Niko1221/Strata/tree/5c8dd322528cc84f68f461ad54a506b9da8fa8d4
- Compare: https://github.com/Niko1221/Strata/compare/v0.2.2...5c8dd322528cc84f68f461ad54a506b9da8fa8d4
- 发布列表: https://api.github.com/repos/Niko1221/Strata/releases

## 相关 Issue

- [#1842](https://github.com/Niko1221/Strata/issues/1842)：RTX 4090 + Qwen3.8-Flash-Next IQ3_S，0.1.41 的 128K decode 慢约 18%，`STRATA_MMVQ_IL=0` 全部找回（2026-10-13 按“超过三天”统一关闭，无修复记录）。对应配置对照 CFG-IL0。

## 非 PR 外部资料

- [JustAResearcher/gpu-unlock-ada](https://github.com/JustAResearcher/gpu-unlock-ada)：v1.1.1，检索时 main `4e7fefcc4923f9e083d5324dc75a7d2f906af77f`；4090 配对证据在 `docs/evidence/rtx4090-pr1-matched/`。对应 CFG-UNLOCK。
- [Zagitta/gpu-unlock#15](https://github.com/Zagitta/gpu-unlock/issues/15)：3080 上 Strata 解锁前后的 A/B（prefill 32K/128K +12～13%，decode 无变化）。

## PR身份

| PR | 固定head | 参考fork | 检索状态 |
|---|---|---|---|
| [#3453](https://github.com/Niko1221/Strata/pull/3453) | `17dd3a912da9f5e015608a2727f3b4aea1f945a8` | rodi4eg/Strata | open / merged=false |
| [#1536](https://github.com/Niko1221/Strata/pull/1536) | `1de969b6b68bc73b35381178e01fc0428daceeed` | zsariboga/Strata | open / merged=false |
| [#3517](https://github.com/Niko1221/Strata/pull/3517) | `70781f4b55dab6483453bf292b377083e6df727c` | chaog992/Strata | open / merged=false |
| [#3307](https://github.com/Niko1221/Strata/pull/3307) | `41bff1d3d02f238cc5f7bda21d787ab19bbc42cd` | gopinath87607/Strata | open / merged=false |
| [#2964](https://github.com/Niko1221/Strata/pull/2964) | `f8184f25c169f6459b2e2a1524731055f54c5d90` | sergqwer/Strata-pr | open / merged=false |
| [#3281](https://github.com/Niko1221/Strata/pull/3281) | `cf14700f5da34901908f5d12fa0f3437bcc44708` | c3c/Strata | open / merged=false |
| [#3584](https://github.com/Niko1221/Strata/pull/3584) | `7d882bed7a204cf896844a81e9a9add69b35835d` | justindressler/Strata | open / merged=false |
| [#3711](https://github.com/Niko1221/Strata/pull/3711) | `36b01d3723e1204a6cc30f84e404cbbf5adfbac8` | yoggsaron010-lang/Strata | open / merged=false |
| [#2822](https://github.com/Niko1221/Strata/pull/2822) | `ee75d94e05360872e59d9533f3f1199e02f85c3b` | Zcg2021/Strata | open / merged=false |
| [#3322](https://github.com/Niko1221/Strata/pull/3322) | `4335151ce0033b951e93b3818b2d7c73b0c24019` | j-luwierski/Strata | open / merged=false |
| [#2253](https://github.com/Niko1221/Strata/pull/2253) | `3ee9597a55815384e6732b78f5c788506b804227` | alanthinker/Strata | open / merged=false / 与main冲突（2026-10-23 新增） |

## 已核对的集成接口

| 文件 | 用于本包 |
|---|---|
| serve/server.py | `python -m serve.server --engine strata --config ... --port ...`；固定max_tokens；OpenAI兼容HTTP |
| serve/frontend.py | ChatTemplate、openai_to_messages、literal_tags、mark/unmark_think_literals |
| tools/strata_tokenizer.py | Tokenizer.from_gguf、encode(parse_special=True, plain=spans) |
| tools/strata_bench.py | usage/timings字段名、TTFT语义；本包不采用其SSE chunk代替token的fallback |
| serve/runconfig.py | args/user_args、fit_max_tokens、配置重启语义 |

- https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/serve/server.py
- https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/serve/frontend.py
- https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/tools/strata_tokenizer.py
- https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/tools/strata_bench.py
- https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/serve/runconfig.py

## 本地用户资料

用户此前上传的 Pasted text(20261008-035514).txt 用于修正硬件/模型/内存假设。只在文档摘要中引用历史事实，不打包用户原文件，也不以它替代当前doctor。

## 在线访问受限时

本次制作环境没有对目标主机的访问权限，容器网络也不能直接clone。研究通过GitHub连接器读取固定ref和PR元数据。包内prepare脚本在用户机器用Git按完整SHA取得源码，缺失就停止，不用缓存片段猜实现。分支后续更新不改变本包锁定head。
