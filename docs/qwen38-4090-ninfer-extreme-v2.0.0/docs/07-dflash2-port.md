# 第二条路线：DFlash2 的受控移植与制品预算

## 1. donor事实已明确

固定`Neroued/ninfer@b88c0f6...`作只读donor。上游支持Qwen3.8-27B K1..15、eager/graph、Text/Vision和Device/Host状态；旧44a的35B DFlash骨架不是同一个模型。此任务必须backport**行为合同和必要实现**，而不是merge整个master。[S01/S02]

## 2. 模型合同（不可猜）

| 项 | DFlash2 |
|---|---|
| layers / H / MLP |5 /5120 /17408 |
| attention |32Q /8KV /128head，非因果对称SWA |
| target taps |零起始blocks [5,19,33,47,61]的完整residual |
| feature fc |[5120,25600]，拼接顺序锁定 |
| dynamic conv |attention/MLP各2side、2tap、group16、320group |
| selector |top16，rank256，实际前驱条件q |
| vocabulary |physical248320、有效IDs0..248076、mask248070 |
| local context |五层×2048×8×128×(BF16 K+FP16 V)=**40MiB** |
| width |K proposals，W=K+1；推荐K7/W8 |

target仍使用24Q/4KV/d256和原长上下文，**draft2048窗口不是削减target窗口**。query block自身非因果可互见，context按绝对位置对称窗口规则；别复制target causal mask。所有norm遵循draft plain RMSNorm，不能套target offset norm。[S01]

## 3. 制品与精度决策

上游suffix是完整66个`dflash2/`对象：feature/attention/MLP矩阵为W8G32_F16S；norm、dynamic conv、selector BF16。19.03GiB减16.96GiB只是文件差，**不是运行时新增显存的精确数**——但按inventory逐项累加恰好也是2.074GiB=2124MiB常驻（`22 §3.1`），因为权重1:1常驻。DFlash2启动可不materialize MTP（省430MiB）；draft使用target embedding/head；另外有40MiB环、workspace、pending、graph。[S02]

**显存账（2026-09-09，CPU可算，T08 loader plan实测确认）**：现网free 1509MiB；DFlash2 W8常驻净增 +2124−430+40 = **+1734MiB**，工作区另估50–150MiB。

| 容量 | 释放 | 加DFlash2 W8后余量 | 判定 |
|---|---|---|---|
| 262144 | 0 | −225…−325MiB | **不成立**（零余量都差） |
| **200192**（用户决策） | ≈1597MiB（rk4v4-e8 ≈26.4KB/token） | **≈1.2GiB** | 满足≥512MiB硬门与≥1GiB偏好 |

因此本线的目标profile是**rk4v4-e8 @200192 + DFlash2 W8**。draft主体W4 variant（companion≈1.22GiB，余量≈550MiB压线且改变q/AL）不再是主线路径，仅当T08 loader plan实测余量<512MiB才开。rk8v4与DFlash2争同一块显存，200192下不能同时要（`22 §3.3`）。

首选导出新不可变组合artifact：原1124对象内容hash不变，追加经过binder校验的完整66对象。重定位offset可以改变文件hash，但不能改主模型payload/quant words。新loader接受旧完整base作MTP、接受完整新suffix作DFlash2、拒绝部分suffix/错head/错shape。绝不直接将HF浮动main覆盖生产文件。

## 4. 实现顺序

0. **T07先行（收益门）**：在44a现有kernel/op测试框架上建立W7/W8的合法decode attention路径（专用编译或可证明的generic route），测184K下每轮verify的额外耗时与分配峰值。DFlash2的实质收益只能来自K=7的宽度（§9）；W8路径成本若吞掉预期AL收益，本线降级为可行性研究，T09/T10不启动。
1. inventory+loader兼容测试；不调用新kernel也能检查完整对象。同时输出resident plan，与§3显存账对照。
2. donor矩阵布局/量化单算子对照，dynamicconv每个tap/side分解测试。
3. target feature捕获（block输出在norm之前）与context fc/每层KV写入。
4. K3/W4先验证状态及q算法，在已存在small-T范围隔离问题；K7/W8接T07路径。
5. eager的full proposal head诊断；optimized shortlist是独立候选（必须全局token映射）。
6. positive-temperature actualq和拒绝/残差（复用`speculative_round.cuh`现有exact rejection sampling，新增Sparse16 q）；之后才cudaGraph。
7. pending features在checkpoint前catch-up；**Device/Host恢复是新功能**（§8）、tool边界、cancel/stop_partial。
8. 最后才wide16和suffix混合。

## 5. 需要特别保留的三种frontier

Target consumed frontier、DFlash materialized frontier、Frontend committed frontier不能隐式用同一个整数替代。每轮verify产生pending features，只为实际提交的N行保留；checkpoint前materialize到同一frontier。ring外旧字节可保留但不可见。变更W会改变非因果draft输出，不能拿W8的q验证W16的候选。[S01]

## 6. 资源表（由执行AI填写实测证据，不是假定常量）

`artifact inventory`列每component磁盘bytes；`allocation plan`列选择profile真正residentbytes；`stage peak`分别列load、cold prefill、W4/8/16 verify、checkpoint copy、graph capture。输出artifact/state schema、dtype、offset、align和owner；整个host侧禁止一次性解压全主模型。

## 7. 本机机会实验和正式门不能混合

先用已有Lucebox q8/vLLM DFlash2做20轨迹估算是可行的，但target量化/内核/缓存不同，AL只能指导投资。正式门必须是**同一NInfer target**的MTP与DFlash2：matchingmedium/seed策略、分桶round/ms、原Java、heldout、196K cap探针（总≤200192）、同样cache命中态。只看AL大了不够；selectedhead/draft精度/width字段必须入结果。

## 8. 会话持久化是新功能，不是移植

44a对DFlash后端的session save/restore显式抛错（`session_snapshot_impl.h:342/534`；`docs/serving.md:130` "The DFlash backend is not supported"）；进程内L1/L2 image已为ring预留`dflash_local / dflash_checkpoint_local`（`continuation_image.h:683-711`），但持久化路径未做。现网85%的prompt token靠前缀复用（报告10），热命中TTFT 1.1s对全重算21s（报告12）。DFlash2 profile若没有等价恢复，每次会话切换/重启退回全重算，`task_wall_ratio>1.02`直接`NO_MEASURABLE_PRODUCT_GAIN`。

T10硬断言：解除DFlash throw；L1/L2 continuation image含40MiB ring + pending features + 绝对frontier；A→B→A会话切换后`reused_prompt_tokens`与MTP profile相同；Host image增大（每image +40MiB，含turn checkpoint再翻倍）计入L2 8GiB预算（可存image数约少10%）。

## 9. 有界估算（推断，公式可查，`22 §4.1`）

- 每轮固定开销：draft权重读2.07GiB≈2.2–2.4ms（4090实效~900GB/s），MTP 0.42GiB≈0.5ms → 净**+≈2ms/轮**。
- 现网轮时：184K≈29ms、4K≈23ms → 打平需committed/轮 +7%/+9%。
- 同K换drafter：模型卡AL增益+8.8–20.1% → 净0–12%，接近噪声。收益只能来自**K=7的宽度**。
- 4-bit KV下W4→W8的verify读字节几乎不变（184K×26.4KB≈4.9GB/轮），额外代价主要在draft与head计算 → W8在长上下文更划算。
- 停止点：T07测得W8路径184K每轮额外耗时`Δ_w8`；若`(AL_dflash2_K7/AL_mtp_K3 − 1)`的下界不足以覆盖`(2ms+Δ_w8)/29ms`，DFlash2链不进入T09。
