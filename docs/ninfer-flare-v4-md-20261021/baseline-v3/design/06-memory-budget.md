# 24GB显存/64GB主机：逐项预算与停止条件

GPU为用户的单RTX4090，生产driver/CUDA/功耗/显存余量在H0重新读取；旧审计不是当前环境。显存24GB和日志中的GiB不可混用。保留P6已经合格的Target/context/KV capacity/concurrency，不因新资源默默压缩。

## 必填账本

`target weights + base KV pool + FP32 GDN persistent state + MTP resources + proposal head delta + chain frames + ReplaySSM records + attention partials + alignment scratch + graph pool + draft weights/ring + feature buffers + staging/index + export/transient + measured headroom`。

host另记：进程RSS、archive常驻、host checkpoint ring、L2 cache、pinned memory、双buffer transfer、文件page cache。L2预算是上限还是预分配由实际源码/运行统计确认，不能把64GB全部再次分配给archive。

分开给出planned、cuda allocated/reserved、NVML used、峰值和测量时刻；一个buffer只记一次，共享workspace按max lifetime冲突记，跨层持久化按全层记。

## 可推导但尚未测量的宽度增量

依据NI01及V2 N01的27B几何，每lane每verify-column的ReplaySSM raw payload：

`48 × (10240×2 + 128×16×2 + 128×48×2 + 2×48×4)`
`= 1,787,904 bytes ≈1.705 MiB`。

这不是复制整个FP32 GDN state；conv/key/value为BF16记录，g/beta为FP32。W6→W16理论增加约17.05MiB/lane；4lane约68.20MiB。record_capacity、对齐及实际layout还需实测，不把这数当总增量。

完整Target logits按 `output_rows×physical_columns×4B` 计，W16×4lane约60.625MiB（使用248320 padded rows）；W6×4lane约22.734MiB。若实现流式消除某buffer，必须以代码生命周期和实测证明节省，不能预先扣除。

Lookup token mirror满262144为1MiB/lane（uint32）；CPU索引额外预算32MiB/lane。更多graph不能只计逻辑Tensor，capture自身私有pool也有成本。候选mask为短不等于大图不占内存。

## 停止/回退

启动profile不能满足与P6相同context和安全headroom则拒绝该profile；仅当前短请求能跑不是完整262K资格。H4可不发布W16；H6可只在另行明确的短上下文实验profile进行研究，但不得把它当262K主力替换。未释放旧proposal head之前不能把新head节约的钱再花一次。

运行时不在OOM后重试更低KV精度，不清空他人的缓存，不更改功耗/driver。单卡对照串行A/B/A，旧镜像/参数/独立缓存目录保留。主机容量缺项、草稿资产未知、NVML未取样，都记录UNKNOWN/BLOCKED，不用0补齐。

## 29现场单位与当前范围

2026-10-20观察为24564MiB GPU、67,064,762,368bytes host RAM（约62.46GiB）；以每run实际可用/分配/峰值为准，不能把“64GB host”理解成可额外分配64GiB archive。B29已有L1/L2、RSS、page cache与pinned需要共同计账。当前baseline不增加draft/graph/head资源；P6合格资源账本尚未提供，不能继承为已通过。先按 [baseline合同](../plans/05-baseline-29-execution.md)测同配置14档与容量边界，不因余量不足静默改E8、context或并发。
