# 并行与文件锁表

Phase串行；同Phase只在依赖满足、write-set不交叉时并行。接口先冻结，CPU与CUDA实现可在独立worktree交patch，Integrator唯一修改公共头/CMake/Program最终组合。

| 文件/资源 | 唯一串行Owner | 原因 |
|---|---|---|
| include/ninfer/types.h、serve_options.* | 当前Phase Integrator | enum/CLI/schema跨task消费 |
| src/CMakeLists.txt、tests/CMakeLists.txt、各target实例化入口 | Integrator | 测试目标不能漏注册/ODR重复 |
| program_impl.h、hybrid_impl.h、mtp_impl.h | Runtime Integrator | pending/resolve/align/输出事务 |
| graph_impl.h、variant.cpp、workspace_recipe.h | Graph Integrator | captured pointer与shape闭合 |
| gqa_attention_decode* | Attention owner（H3与H4串行） | dtype/geometry共用实例化 |
| GDN recurrent/replay | State owner（H3与H4串行） | FP32状态与记录一致性 |
| request_log.* | Serving owner，经Integrator合入 | core24与extensions稳定 |
| 数据calibration/test manifest | Data owner | 防评测泄露 |
| RTX4090 | 单GPU test queue owner | 容量/热状态可比性 |
| 生产容器/路由/缓存目录 | Deployment owner | 排空、切换、回滚不可并行 |

worker需要改未拥有文件时提交明确patch request，不自行“顺手修”。phase-base允许UNQUALIFIED；只有gate后才能部署。任何review修复都让旧build/perf证据过期，需重绑定与重测受影响范围。

## baseline-only的共享资源

本轮ROOT唯一拥有29 GPU队列、服务切换、run manifest及runner/monitor；Pi语料worker只维护离线重建工具/冻结输入，产品与方案文档worker不并发修改运行状态。正文、registry及断言镜像由方案Integrator同步维护；本轮不进入优化源码write-set。私有session/凭据不写文档包。

## sampling共同资格文件

H1-T07只读复用并测试既有speculative_accept_greedy_drafts、sampling_device、Target preview/resolve/commit；若确需生产修补仍由H1 Integrator唯一合入，不另造sampler。其测试与H1-T06共享GPU队列，T06在T07后运行；后续W/head/backend变更按共同合同补当前组合证据。当前本轮仍只有文档/采集工具范围，不实际修改这些生产文件。
