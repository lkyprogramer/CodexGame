# P02 — 会话缓存准入、回收与淘汰策略

**Goal：**避免长主会话切换短子任务时发生可避免的cache拒绝/重复prefill。对应O39/O40；O61的host/allocator owner归P09、在本计划只做准入依赖；E轨道优先。这里的潜力是减少恢复尾延迟，不是直接提高持续decode tokens/s。

## 源码与donor

- [conversation_cache.hpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/core/conversation_cache.hpp)：make_room、evict_oldest、guard/unguard、borrow、pinned与reuse。
- [conversation_memory.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_memory.cpp)：MemAvailable/cgroup/limit读取。
- [generate.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/program/generate.cpp)：约9516–9665 parking预算、physical RAM admission、post-capture检查。
- [conversation_cache_test.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_cache_test.cpp)、[conversation_memory_test.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/conversation_memory_test.cpp)。
- [PR2253](https://github.com/Niko1221/Strata/pull/2253)和[PR4031](https://github.com/Niko1221/Strata/pull/4031)，固定head见sources。均未合并，不直接merge分支。

## P02-01 机制复现与资源边界

先运行P00的cache小预算场景：A长会话→B短子任务→A，接着A→B→C→A；再测试超过4slot的短任务burst、相同前缀但不同后缀、pin/guard、取消。每轮记录snapshot估算/实际bytes、cache bytes/slot、RSS/heap/pinned、MemAvailable/cgroup剩余、park/refuse/evict/restore/read/reuse事件。

通过提高隔离实验的`--conversation-cache-min-free-mib`可触发拒绝，不能降低主机安全余量强行压到OOM；不启动无关内存hog。先证明发生了“free后glibc保留heap，cache逐空仍拒绝”或者有不必要淘汰。若latest无此模式，O39标NOT_APPLICABLE而不是假造场景收益。

## P02-02 准入纯逻辑与guarded donor修正

拟新增/语义移植`admit_ram`、`evictable_bytes`，将available/release钩子注入以CPU单测。**PR2253仅排除pinned的旧evictable_bytes不能照搬：latest evict_oldest也排除guarded donor。** 计量与可驱逐选择必须使用同一predicate。held/incoming reuse/pinned/guarded容量不双计、不漏计；加法/减法做overflow检查。

算法合同：先读取真实available；需要时做一次有界release并重读；只有理论可释放的合法条目足以填补缺口时才尝试逐出。每次逐出/trim后重读实际available，不能假设释放对象就等量归还OS。上限由可逐出数界定。读取失败保守拒绝；只有pinned/guarded或空cache时不会空转。

**拟新增feature开关**`STRATA_LAB_RAM_ADMISSION`，默认0，启动打印off/on及算法版本；不是现主线上游参数。off必须保留旧行为和数值。

## P02-03 glibc回收与post-capture门

glibc才调用`malloc_trim(0)`；其它allocator无此假设。避免每token/每小alloc执行；只在准入压力事件并限次。记录trim耗时和实际RSS/available变化。PR作者37–482ms只是其环境报告，不作本机数字。

capture前估算可能与最终实际allocation不同。单独处理post-capture available floor：不足时释放新snapshot、保持原active/borrowed donor可恢复、恢复所有权和cache计数，不留下半成品。不能降低floor消除错误，也不能让guard失效导致捐赠源被逐出。

## P02-04 测试先于移植

拟扩展现有纯CPU测试，先添加会在latest失败的准入行为用例，再实现：

| 测试组 | 必须结果 |
|---|---|
| available边界 | floor、floor−1、need恰等、need+1、UINT64边界 |
| cache保护 | pinned-only、guarded-only、两者混合、held donor、不合法serial |
| allocator行为 | 全量/半量/零回收、外部available下降、首次trim可直接满足 |
| 无望请求 | 缺口超过合法evictable，不清空可用cache |
| 异常回滚 | capture分段失败、post-capture floor失败、取消、restore失败 |
| 身份与状态 | A/B prefix冲突、模板/模型/精度变化禁止错复用 |

本包cmake_args包含`-DSTRATA_BUILD_CONVERSATION_TESTS=ON`，否则纯CPU conversation目标默认不生成。现有目标可先运行：

```bash
cmake --build build-lab --target conversation_cache_test conversation_memory_test conversation_snapshot_test conversation_validation_test --parallel 4
ctest --test-dir build-lab --output-on-failure -R '^(conversation_cache_test|conversation_memory_test|conversation_snapshot_test|conversation_validation_test)$'
```

其中snapshot/validation依赖CUDA构建与实际运行条件；不能在无GPU环境标通过。新增purelogic测试可独立在CPU跑，实际state测试必须在4090执行。

## P02-05 PR4031按slot与bytes的策略拆分

PR4031的smallest-slot victim与empty-cache learnt ceiling是两个处理变量，且作者实现有默认行为变化。不可只看“flag off”说明就认定off等价。拟拆成：A=现有LRU，B=仅slot压力时选低价值/小snapshot，C=仅有时效的压力容量学习，D=B+C。先与O39单独比较，再做2×2消融；不是把2253/4031全部叠上。

防止压力恢复后预算/slot永久缩小；显式有效期、重新探测与配置上限，日志显示effective budget，不能偷偷从6144MiB/4slot缩成另一规格。逐出决策应考虑预期复用与重prefill成本，小snapshot不总低价值。

## P02-06 实机验收与停止

工具中的`validate-plan`只是离线格式检查；先按P00实现adapter。使用冻结cache_state标签，同一事件序列比较base/off/on；记录重prefill读token、恢复TTFT、任务restricted wall、cache命中、trim停顿、RAMfloor、swap。目标是使原失败恢复成功且时间区间满足正式政策；普通decode不得有>3%区间上界退化。

没有真实restore、只是同请求命中active prefix：INSUFFICIENT。trim停顿抵消避免prefill，或策略赶走长主会话：NO_GAIN。任何状态污染/OOM/guard破坏：REJECTED并回到关闭开关的独立构建。原生产与host设置保持原样。
