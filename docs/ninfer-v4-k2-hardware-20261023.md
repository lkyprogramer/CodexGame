# K2-T01最小实机筛选：数值与Graph通过，未出现稳定收益

**结论：保持原512线程分派，结束本轮CTA实验，不追加补测，不进入有赢家后的整轮验证。** 8个数值场景和Graph验证均通过；128/256相对512的四组计时都未达到冻结的“配对中位收益≥10%，且至少4/5批胜出”门槛，结果全部为`NO_SIGNAL`。这只说明本轮指标未形成稳定收益，不能证明128/256纯kernel绝无潜力。

本轮通过`ssh 29`执行一次冻结窗口，未修改源码或工具。GPU为RTX4090。完整控制窗口约1.568327秒，正常完成后即清理，无需等待第7分钟；清理发生在窗口起点后1.370438秒，远低于420秒清理期限和600秒硬限。模型请求、HTTP、重试和旧任务重跑均为0。原GPU服务保持停止。

## 数值、Graph与预算

| 项目 | 实际结果 |
|---|---|
| 数值 | 8场景PASS，22次direct Op，0失败 |
| 主要形状 | BF16、D128/H48，T1/T4各普通、near-zero、饱和gate，共6场景 |
| 回退 | 非对齐T1走原generic256；对齐T5走原warp512，均PASS |
| 数值条件 | 既有FP64 oracle阈值、旧新BF16逐字节比较、输出guard及输入保持均通过 |
| Graph | 6次capture，每图1个真实Gated norm节点；12次正确性replay全部PASS |
| Graph几何 | T1的128/256/512对应12/6/3 CTA；T4对应48/24/12 CTA，函数指针和block/grid核对通过 |
| 计时 | 6配置各10次warmup及5批×64次replay；30批后数值/guard均0失败 |
| 总replay | 12 correctness＋60 warmup＋1920 timing＝1992，达到并未超出冻结额度 |
| 账本 | 56项预留全部COMPLETED，对应56条outcome，无未知结果或未决预留 |
| 模型 / HTTP | 0 / 0 |

所有判断来自实际ledger、outcomes和native summary，并经独立只读复核；没有把控制器退出码0单独当作数值或性能PASS。[原始数值与Graph结果](../output/ninfer-v4-k2-hardware-20261023/remote/hardware-r1/observed/native-outcomes.jsonl)、[实际账本](../output/ninfer-v4-k2-hardware-20261023/remote/hardware-r1/observed/budget-ledger.json)。

## 128/256对512的计时结果

按同T、同batch配对计算`1 - candidate_us / corresponding_512_us`，再取5批中位数。正数表示本轮该指标更快，负数表示更慢；没有用“各自中位数之比”替换冻结计算方法。

| 形状 | 候选线程 | 配对中位收益 | 胜出批次 | 冻结判定 |
|---|---:|---:|---:|---|
| T1 | 128 | +1.20% | 3/5 | NO_SIGNAL |
| T1 | 256 | +5.76% | 3/5 | NO_SIGNAL |
| T4 | 128 | −3.43% | 2/5 | NO_SIGNAL |
| T4 | 256 | +4.98% | 3/5 | NO_SIGNAL |

计时口径是**主机连续提交64次单节点Graph replay的CUDA event跨度除以64**，含逐次截止检查，并可能包含GPU等待主机投递的间隔，不是纯kernel latency。各配置观测约2.08–5.66μs，单批配对收益跨正负且波动大。因此不能把上表小幅正值当作稳定加速，也不能把T4/128的负值外推为已证明的整轮回退。

[逐批配对CSV](../output/ninfer-v4-k2-hardware-20261023/timing-batches.csv)保留全部20组配对；[机器汇总](../output/ninfer-v4-k2-hardware-20261023/final-summary.json)含30批原数据范围、四组中位收益及门槛。完整round和Chat收益仍为null，未运行模型，未取得K4或生产资格。没有胜者，本轮不增加路由或扩形状继续追成绩。

## 冻结身份与清理

| 身份 | 值 |
|---|---|
| 工程分支 | `codex/k2-gated-rmsnorm-20261023` |
| 源树 | `13223b2b2989d0cf580715b197b276d74acffc86` |
| 冻结SHA | `37a398b62655482f0f34ea42970d2eb4796f3f8d70c5cb7731b99af2c29cdd0e` |
| 窗口 | `prepared-window-r1-37a398b62655482f` |
| 实际原始归档SHA | `d6f31831d6731b25ea9fe3ad51db59018c52c66aaa48c3e2fc391c49a234a9a7` |

执行前核验6个冻结输入和全0账本、无历史runtime，确认原服务exited/PID0、GPU空闲，再执行既有controller的`--run --authorize-new-gpu-run --freeze-sha`。新授权另存[授权记录](../output/ninfer-v4-k2-hardware-20261023/remote/hardware-r1/authorization.json)，未覆盖旧准备回执。当前`prepared-window-r1`已消耗：runtime存在，账本为COMPLETED，禁止重启或复用为新窗口。

结束后核验候选退出码0、PID0，controller与guardian均退出，GPU无计算进程，原服务仍STOPPED。原容器ID、镜像、启动参数SHA、cache dev/inode及C0原serve SHA保持一致；源树不变且无未暂存源码变化。6个冻结输入执行后哈希仍一致。[清理回执](../output/ninfer-v4-k2-hardware-20261023/remote/hardware-r1/observed/runtime/cleanup.json)、[独立结束回读](../output/ninfer-v4-k2-hardware-20261023/remote/hardware-r1/postflight.json)。没有自动恢复原服务。

## 证据与限制

原始runtime、ledger、outcomes、summary、空stdout/stderr及候选身份共20个导出文件，长度和SHA全部校验，本机持久目录与29均保留。native部分durable文件由容器root以0600创建，通过已停止且所有权核验通过的原候选`docker cp`读取相同字节；没有改权限、改属主或重新生成原始结果。空stdout/stderr是此次成功执行的实际输出，结构化证据完整，不能据此登记日志缺失。[导出来源](../output/ninfer-v4-k2-hardware-20261023/remote/hardware-r1/export-receipt.json)、[归档回执](../output/ninfer-v4-k2-hardware-20261023/hardware-r1-delivery.json)。

离线复核命令：

```sh
python3 output/ninfer-v4-k2-hardware-20261023/analyze.py
```

此命令只读已完成窗口，不发GPU/模型/HTTP请求。[校验结果](../output/ninfer-v4-k2-hardware-20261023/validation.json)和[独立复核](../output/ninfer-v4-k2-hardware-20261023/review.json)均通过。

本轮无新增失败或附件缺口。历史失败、18处G1差异、C1附件缺口、旧Baseline限制及先前CPU19项未保存原始stdout的披露均保留。C0继续关闭。产品默认分派、采样/context及Pi medium/32768未改，未提交、推送或部署。`p95=null`、`optimization_qualification=false`，追加测量预算0。
