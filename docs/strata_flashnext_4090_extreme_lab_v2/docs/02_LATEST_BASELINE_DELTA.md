# 最新源码基线与迁移

| 身份 | 固定值 |
|---|---|
| 上游 | Niko1221/Strata |
| 最终执行main | `4b9e05a2a806a3fe24f7b2560d98626c37dade35`，2026-10-25 12:56:36 UTC |
| 最新发布 | [v0.2.6](https://github.com/Niko1221/Strata/releases/tag/v0.2.6)，2026-10-25 13:45:25 UTC |
| 发布tag对象 / peeled commit | `ff91dd77a13857ccc2f1bd67edc9a8ecd4ecdfa4` → `4b9e05a2a806a3fe24f7b2560d98626c37dade35` |
| 发布版本区别 | Qwen引擎包仍0.1.50；Control/DeepSeek与CMake project为0.1.51 |
| 本轮深入审计源码 | `41cf05a06a25dd29103b7b27a2279a3f60c21876`；固定源码链接保留此SHA |
| 前一发布 | v0.2.5 / `fa663fabc5c2c568d6035b3ae853b38e1762865a` |
| 历史生产 | `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` + EXACT6 + host tuning |

## 0. 最终刷新增量

研究中途发布了v0.2.6。本包最终执行source lock已跟到4b9e05a；不是将41cf继续称为最新。完整树差分55文件，src/core、src/kernels/cpu、src/kernels/cuda、src/prefill及相关include无变化。Qwen generate.cpp仅修正spec-split“非bit-exact”的注释；CMake project版本变化。serve增加空messages返回400，并取消单token输出的虚假decode tok/s。PR3871的CPU bench文件未变，仍需测量修复。逐文件/关键blob证据见[刷新审计](../sources/FRESHNESS_DELTA.md)。

固定41cf的源码引用仍准确描述相关实现；后续部署和build必须使用4b9锁并重新资格验证服务接口与版本回执，不能只核version字符串。v0.2.6的DeepSeek大RAM提速不外推给Flash-Next。来源：[发布说明](https://github.com/Niko1221/Strata/releases/tag/v0.2.6)、[完整比较](https://github.com/Niko1221/Strata/compare/41cf05a06a25dd29103b7b27a2279a3f60c21876...4b9e05a2a806a3fe24f7b2560d98626c37dade35)。

## 1. 必须区分Qwen与DeepSeek

本地完整git diff显示，旧A0到深审41cf快照的`src/kernels/cuda/`、`src/prefill/`与CPU `pool.cpp`没有变动；重要FlashNext变化集中在IQ/TQ CPU路径、`adapt_async_default`及`generate.cpp`。大量新增文件属于DeepSeek。发布文中的DeepSeek少专家、SSD与CPU重叠、AMD WMMA等收益不能算作本机FlashNext的现成收益。

## 2. Async tier的新默认与当前配置

最新版本新增自评估策略：warmup/测量/试用窗口决定是否保留异步tier，允许小幅退化阈值。它有明确资格检查；**当前生产STRATA_ADAPT_OVERLAP=1本身就是排除条件之一**，所以不能声称升级会自动为本机开启新async收益。

迁移A/B必须固定effective mode、相同EXACT6和host设置。先保留当前overlap；单独比较blocking/async/overlap时，作为不同配置实验，不能混进源码升级效果。需要记录选择原因、phase、actual async/overlap状态，不能仅看用户传了什么参数。

来源：[include/strata/core/adapt_async_default.hpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/include/strata/core/adapt_async_default.hpp)、[src/program/generate.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/program/generate.cpp)。

## 3. ISA门控不允许强开

最新IQ512路径仍依赖`cpu_avx512_ok()`，整个编译单元还可能启用VBMI/VPOPCNTDQ。4216有AVX512-VNNI并不满足全部要求；AVX-VNNI与AVX512-VNNI也不是同一CPUID位。新增4216路径必须隔离编译单元并检查生成指令，不能删CPUID条件。

来源：[src/kernels/cpu/expert_layout.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/expert_layout.cpp)、[src/kernels/cpu/native_expert.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/native_expert.cpp)、[CMakeLists.txt](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/CMakeLists.txt)。

## 4. 迁移步骤

1. 读取最后已知生产状态并与本机inventory比对。只复核，不重装perf或重复host调优。
2. 新建最新源码隔离树；固定GGML依赖、compiler、CMakeCache；记录dirty diff。
3. 建立`latest_base`与`legacy_production`双臂；相同资产/配置/host/profile，唯一变量是源码及必要ABI兼容。
4. 校验tokenizer与接口；短质量、工具、Java、8/32/64K与接近上限场景。
5. 最新版发生质量/性能退化：生产留历史基线，研究可在latest修问题；不带病替换生产。
6. 最新版资格通过后，所有新改造都以`latest_base`为对照。最终候选再与历史生产做一次端到端对照。

当前main是研究锁，不是永久“latest”。未来执行若要跟新提交，建立新baseline并重做必要资格检查；不能静默移动此锁后复用旧结果。
