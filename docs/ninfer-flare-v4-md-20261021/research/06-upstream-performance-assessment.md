# 完整上游合并：按源码与当前P4评估

结论：上游确有推理性能价值，应保留已吸收的核心改动与后续上游性能实验；完整合并可作为可选对照。当前剩余U28—U34尚未找到纯文本Chat直接提速证据，因此不把完整U34列为kernel/Lookup开工前置，也不因当前没有收益证据就永久删除完整合并候选。

## 固定比较对象与实际检查

P4树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`；上游U27`29d13e3d99491ed82e7be4edc801d92a59643cea`；U34`5b99996bc7c1fe6ff27f271a205eb605302ec8bb`。本轮读取本地已保留Git对象及完整U27→U34 patch，没有构建/运行新候选。所有139个变更文件已列全，7提交/18123新增、1021删除行；检查共享执行器、generation service、frontend/processor、prefill、program、cache identity及snapshot路径，21份固定对象源码按SHA保存为见证。

[原始diff](../../../output/ninfer-v4-performance-scope-20261023/remaining-upstream-U28-U34.patch) · [提交清单](../../../output/ninfer-v4-performance-scope-20261023/remaining-upstream-log.txt) · [机器审计与源码SHA](../../../output/ninfer-v4-performance-scope-20261023/upstream-source-audit.json)。这证明静态范围与可达性，不证明性能或构建成功。

## 已吸收U01—U27不能再算未来合并收益

| 上游组 | 当前用途及收益可能 | 当前处理 |
|---|---|---|
| U01—U03、U17、U27 | 协议/工具/UTF8正确性与实际增量交付；不是GPU算子提速 | P1/P3/P4证据复用，当前只要求Chat |
| U04/U05/U09 | 重复循环边界与故障清理，可能减少异常成本 | 已有合同保留；不借性能优化改变采样/输出政策 |
| U06/U07/U08 | cache alias/breakpoint与共享payload，可能减少重复prefill、拷贝/存储 | 已在P1，实测cache证据复用；净收益仍要用新选中对照 |
| U10 | 单次segmented编码与前端工作减少 | 已在P1并保留G1差异，不能当未实现项重做 |
| U11/U12 | 异步导出/准入与测量驱动，可能减少阻塞、提供归因 | 已在P2/P3，共用现有请求/job观测 |
| U13—U16 | Q4/Q5 small-T与Attention/GDN投影路由 | P3数值/Graph已有最小证据；实际端到端收益仍未资格 |
| U18—U20 | 部分为decisions，midrise KV影响真实内存/精度/容量 | P4已构建且必要数值/Graph/cache通过；不为已集成功能再列新开发 |
| U21—U27其它部分 | 35B构建、LoRA夹具、dashboard、mixed bench、文档 | 保留既有资料，不变成纯Chat性能必做 |

“上游合并没有帮助”过于笼统。当前不是从旧B29重新做所有合并；已有P4实现是研究起点，完整上游的新增价值必须扣除已吸收部分。

## 剩余U28—U34逐项判断

| 提交 | 主要内容 | 纯文本Chat直接提速证据 | 当前选择 |
|---|---|---|---|
| U28 897652a3 | TypeSafe answer shapes文档 | 无执行改动 | 参考，不独立实施 |
| U29 ed8e548b | /systemone改/typesafe路径 | 路由功能，无推理计算减少 | 不作为性能任务 |
| U30 9570a58d | SystemOne playground | UI | 不验收UI |
| U31 13aabb7b | 结构化请求预设 | UI/预设 | 不列待办 |
| U32 4e570b79 | 作者说明 | 无直接性能代码依据 | 不为历史完整性开任务 |
| U33 ab7ada97 | OpenAI Decisions、双协议、模型列表 | 新业务与请求分派 | 共享依赖按diff选择，非Chat收益证明 |
| U34 5b99996b | 图像决策、预处理身份/位置和状态格式 | 媒体正确性为主；纯文本热路径尚无直接提速证据 | 可随必要耦合合入，但先验证格式/cache，不独立验收图像 |

关键可达性：`Frontend::prepare`只有`has_media`时调用`convert_processed`。该helper把token_ids的assign改成move，但P4纯文本else本来已经move，因此不能把该copy节省算文本收益。`concurrent_executor`新增host lease/取消与释放主要在decision路径；`program_impl`与`text_prefill`新增rope_delta/可空Vision配合媒体状态，不等于纯文本更快。U27→U34的`src/ops`、`include/ninfer/ops`、`src/core/gdn_*`无改动；不能据此排除所有CPU间接效应，但不能宣称新增GPU kernel收益。

`prefix_identity`、continuation及snapshot增加preprocessing_digest/rope信息并提升版本，可能影响缓存可恢复性和冷启动；它们是完整合并的成本与正确性依赖，不是纯文本缓存命中率提高的证据。不能直接替换现有缓存目录或绕过版本拒绝。

## 保留两个上游候选入口

`upstream_selective_candidate`与`upstream_full_candidate`共用UP-T01和一次K4资格，不是先后两阶段。默认选对当前瓶颈有用且依赖可分离的最小改动。出现下列实际依据可选完整合并：共享text性能修复需要不可合理拆分的API/状态变更；拆分风险/维护成本明显高于完整候选；或者明确要验证完整上游是否有可测的CPU/缓存间接收益。把理由、文件/调用点、成本和停止条件写入回执。

完整候选应从干净P4隔离分支重新生成、构建与评审，保留18差异/全部本地修复。已中断P5导入本机未评审、远端9冲突且没有构建，不能复用为“完整上游已就绪”。[停止回执](../../../output/ninfer-v4-performance-scope-20261023/P5-scope-stop.json)与[原补丁](../../../output/ninfer-v4-performance-scope-20261023/abandoned-P5-unreviewed.patch)保留。

预计选择性0.5–2工程日；完整U34约2–5工程日，pilot20–45分钟、≤32wire/24模型请求/26含warmup模型提交。当前只修订文档，尚未授权重新合并或测试GPU。完整候选若没有净收益、增加缓存失效成本或回归，保留P4/选择性版本，不为完成合并扩大纯Chat需求。
