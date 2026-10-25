# Q4 FFN 紧凑布局与五级预取：最小实机结果

**数值和Graph最小验证通过；两种候选均未测得提速，不采用，保留原四级路径。** 全部冻结测量已执行完成，不追加GPU，不进入完整decode或Chat验证。控制器收尾另有权限失败，原始失败保留，不能将本轮记成整套工具全PASS。

## 实测结果

2026-10-24 19:56（北京时间）通过jssh 29执行冻结候选。固定Q4 FFN `34816×5120 → 17408×4`，C1/W4、split-K1，三配置交错32组cold-Graph计时。

| 配置 | 中位耗时 | 相对原路径耗时 | 比原路径更快的配对组 |
|---|---:|---:|---:|
| 原四级 | 161.792 μs | — | — |
| 紧凑四级 | 162.736 μs | +0.583% | 8/32 |
| 紧凑五级 | 163.936 μs | +1.325% | 7/32 |

两项均未达到预先规定的中位下降≥10%、绝对节省≥12μs、至少24/32组改善门槛。这是一个短窗口的局部算子结果，不能据此证明稳定退化，也不能换算完整推理/TTFT收益。

4个输入场景的三配置完整输出逐bit相同，均通过原独立FP64/A16标准与guard检查。3个Graph均为一个kernel节点，实际/期望函数、完整参数、544 CTA×256 threads及shared见证通过。12次Graph正确性、18次warmup、96次计时共126次replay完整执行。

三配置实际资源查询仍为REG78、LOCAL0，shared为29696/25600/32000B；occupancy calculator均为3 CTA/SM。**压缩shared没有增加本配置理论驻留CTA，五级预取也没有在此次测量中形成净收益。** 是否受访存延迟、指令调度或其他瓶颈约束，本轮没有足够profiling证据作进一步归因。去掉shared空洞本来就不减少模型权重的global读取字节。

[原始summary](../output/ninfer-v4-q4-compact-t4-hardware-20261024/remote/prepared-window-r1/native-summary.json) · [逐组计时CSV](../output/ninfer-v4-q4-compact-t4-hardware-20261024/timings.csv) · [独立复核](../output/ninfer-v4-q4-compact-t4-hardware-20261024/REVIEW.md)。

## 实际预算与收尾

| 项目 | 实际 / 冻结上限 |
|---|---:|
| 数值场景 | 4 / 4 |
| direct Op | 12 / 12 |
| capture | 3 / 3 |
| replay | 126 / 126 |
| 算法kernel执行 | 138 / 138 |
| helper compute / 模型 / HTTP | 0 / 0 / 0 |
| H2D | 10次、98,386,944B / 40次、128MiB |
| D2H | 13次、4,148,224B / 24次、4MiB |
| D2D | 0 |
| memset | 138次、37,044,092,928B / 144次、36GiB |
| 显式device buffers | 363,596,800B / 384MiB |

310条reservation与310条outcome按持久ID关联，全部COMPLETED，逐项求和等于账本used，无未知/未结束操作。嵌套场景reservation的完成顺序不等于预留顺序；本机首版分析器错误使用物理行序，已改为ID关联后通过，原分析失败另存，没有修改raw或重新执行GPU。

候选进程exit0，账本和summary均COMPLETE；从控制器启动到退出约4.334秒，候选已清理，未触及7分钟清理点或10分钟硬限。19:58独立宿主readback确认候选、wrapper和guardian均退出、GPU无compute进程、lease释放；原`ninfer-4090-prod`保持停止，镜像、启动参数、缓存目录身份不变。

本轮没有重跑CPU合同或任何旧任务，没有模型请求，没有修改默认分派、Target采样、Pi medium/32768、codec或缓存格式。

## 控制器权限缺陷与取证边界

GPU容器创建时未指定`--user`，因此使用root运行；probe按原合同以0600临时文件原子替换账本/summary，形成root所有的终态文件。GPU完成后，宿主hhtele控制器在读取账本时触发`PermissionError`，最终exit1。前轮CPU合同没有覆盖实际容器输出文件所有权，这个工具缺陷在实机中才暴露。

没有重发kernel或重启控制器，也没有chmod/chown原始文件。通过**无GPU、只读挂载的BO容器**将证据导出到stdout，在本机保存；记录原uid/gid/mode与SHA。34个导出文件、7个冻结附件SHA全部匹配。根据candidate exit0、完整耐久账本、逐条outcome和Graph诊断完成独立复核，因此可以报告测量结果，同时保留控制器FAIL。

已消费的冻结源码和工具不覆盖，权限缺陷没有伪装成已修复。未来若复用该控制器，必须先将候选创建改成宿主UID/GID并单独验证文件所有权；不能复用本轮已消费账本。由于性能未形成采用信号，本轮不为这个候选再开GPU窗口。

[原失败栈](../output/ninfer-v4-q4-compact-t4-hardware-20261024/remote/hardware-r1/controller.stderr) · [原权限与导出SHA](../output/ninfer-v4-q4-compact-t4-hardware-20261024/remote/EXPORT-RECEIPT.json) · [最终清理readback](../output/ninfer-v4-q4-compact-t4-hardware-20261024/final-readback.json)。

## 身份与限制

- 隔离分支：`codex/q4-swiglu-compact-t4-20261024`。
- 候选源码树：`ebc4158e3146b87d65ca68427377476045af4646`，运行前后不变。
- 已消费入口：`/home/hhtele/ninfer-v4-q4-compact-t4-20261024/prepared-window-r1`。
- freeze：`55834651b95939debf2c1e29200460f489a9e96dc66d31a5339d9eadfbf4c717`。
- 最终状态：`MEASUREMENT_COMPLETE_NO_ADOPTION_CONTROLLER_READBACK_FAILED`。

没有完整decode/Chat对照，没有窗口内连续时钟/功耗轨迹，没有统计或生产资格结论。CUDA context/Graph内部allocator高水位未知，不能用显式buffer代替。`p95=null`、`optimization_qualification=false`。全部历史失败、18处G1差异、C1缺口及随机MTP结果保留。

[机器汇总与全部计数](../output/ninfer-v4-q4-compact-t4-hardware-20261024/final-summary.json) · [原始归档](../output/ninfer-v4-q4-compact-t4-hardware-20261024/remote-result-r1.tar.gz) · [准备阶段原始报告](ninfer-v4-q4-compact-t4-20261024.md)。
