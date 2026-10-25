# 固定 C1/W4/K3 随机 MTP＋精确 q：CPU/BO 可行性完成

**隔离候选已实现并构建，12个新增CPU合同一次执行全部通过，两路评审发现的P1/P2均已修复。当前结论仅为CPU/构建层面的可行性完成，没有GPU、模型请求或实测收益。** 4–6小时是预留检查点，不是声称已经消耗的工时；本轮无需等待满时长或扩大改造即可完成这一层交付。

## 可构建补丁与身份

- 连接：`jssh 29`（实际`ssh -J jump 29`）。远端根`/home/hhtele/ninfer-v4-sampled-q-20261024`，分支`codex/sampled-q-w4-20261024`。
- 基点raw树`a5ba33de12d75ab1e16a153020e4068094ee1757`；候选树`f557ab41f68105a629344c2acb5adb6f9a38c783`。HEAD仍为`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，没有创建commit或push，源树身份包含实际暂存补丁。
- 28个变更文件：构建边界、Op producer/verifier、共享MTP运行时及定向CPU测试。未合入W6/Lookup/correction/T1024的新默认分派；旧源码中的既有实现与所有历史资料保持。
- 冻结源码和两个server二进制位于远端`frozen-r2/`。本机保存完整源码副本、压缩源包、补丁、原失败和构建/CPU日志；未将本机紧凑证据称为完整二进制备份。

[源码补丁](../output/ninfer-v4-sampled-q-20261024/evidence/sampled-q-r2.patch) · [CPU交付回执](../output/ninfer-v4-sampled-q-20261024/evidence/CPU-DELIVERY-RECEIPT.json) · [本机源树](../output/ninfer-v4-sampled-q-20261024/source/CMakeLists.txt)。

## 实际实现

1. `NINFER_SAMPLED_MTP_Q`默认OFF；显式候选构建ON时限定C1/K3、optimized proposal head、纯文本、fresh FullReset、cache off且禁用snapshot。W4由K3执行链确定。默认产品选项、Target采样参数、模型/codec/context和Pi medium/32768不变。
2. 在现有Q4 proposal投影后，从最多12项归一化条件q中抽取全局token ID，保存完整支持集与FP32概率；沿用20项物理容量，不裁剪完整Target支持集。prefill、后续AR和跨轮current/next包均已接线。
3. 接受使用`min(1,p(d)/q(d))`，拒绝在完整已处理Target支持集上使用`normalize(max(p-q,0))`；全接受bonus沿用原Target合同。small和248320词multiblock均编译进实际Op，原Target排序、过滤和归一化源码保持。
4. proposal RNG使用独立purpose6；q包绑定epoch/frontier/extent。首token在prefill已经计数，因此首包不重复叠加anchor；后续包叠加本轮licensed前缀与之前的草稿。新verifier不修改counts，仅在正式许可提交时更新已提交部分，取消/终态使q包失效。
5. 复用原arena/Graph、GDN raw状态和许可链。现有持久化只存draft IDs，候选明确拒绝缓存导入/导出和session snapshot，没有改缓存ABI，也没有把cache off当生产恢复资格。

这改变草稿生成策略；Target参数和目标分布合同保持。相同seed的greedy与sampled文本不要求一致。实际GPU浮点、条件前缀与分布是否满足合同仍未验证。

## 已执行验证与修复

| 项目 | 结果 |
|---|---|
| 默认BO，采样候选宏OFF | PASS，`ninfer-serve`及CPU目标 |
| 候选BO，采样候选宏ON | PASS，`ninfer-serve`及CPU目标 |
| 实际消费TU | `variant.cpp`、`round_state.cpp`和CPU目标的宏开关与各自构建一致 |
| 新CPU合同 | 12/12 PASS，实际执行12次；没有重跑旧矩阵 |
| Spec评审 | R1发现1个P1；R2定向复核关闭，开放0 |
| Standards评审 | R1发现1个P2；R2定向复核关闭，开放0 |
| GPU/模型/HTTP | 0/0/0，未加载模型 |

BO使用固定镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，sm89/CUDA13.2；runc、network none、NVIDIA_VISIBLE_DEVICES=void，并断言无`/dev/nvidia0`和`/dev/nvidiactl`。复用原对象和依赖前对未改源文件做内容相等检查，不重建模型或重新转换权重。

12项覆盖默认/候选准入、稀疏全局ID、无效q、p=q、delta退化、Target支持集外残差、独立FP64有限分布参考、RNG位置推进、真实许可/32768预算及epoch/frontier失效。CPU直接调用生产host/device数学helper和运行时合同；不能代替CUDA sampler、实际RNG或状态证明。

**本轮保留的失败与修复：**

- P1：下一轮proposal位置原本少加1，首次拒绝后可能复用刚被拒绝草稿的随机数，破坏实际条件q。R2首草稿偏移改1、后续AR改2；真实CUDA采样点与CPU共用位置helper。case9覆盖拒绝深度0/1/2和全接受3＋bonus，评审复核关闭。
- P2：CPU目标漏声明CUDA头依赖，R1 BO实际失败于`cuda_runtime.h`缺失。R2显式链接`CUDA::cudart`后构建通过。原r1源包、日志和非零退出码保留。

[BO默认](../output/ninfer-v4-sampled-q-20261024/evidence/BO-default-r2.json) · [BO候选](../output/ninfer-v4-sampled-q-20261024/evidence/BO-candidate-r2.json) · [CPU原件](../output/ninfer-v4-sampled-q-20261024/evidence/CPU-contract-r1.jsonl) · [消费TU](../output/ninfer-v4-sampled-q-20261024/evidence/consuming-TU-r2.json) · [两路评审](../output/ninfer-v4-sampled-q-20261024/evidence/INTEGRATION-REVIEW.md)。

## 最小实机提案与剩余准备

当前只冻结CPU/源码/二进制交付，**没有冻结可执行GPU窗口**。原H3入口已消费，不得启动；本轮未另建控制器。继续复用其owner、HTTP终态、deadline和K2 CUDA审计，只适配新profile。

旧H3仅注入token IDs的oracle缺少真实q，旧native的持久化导出也被候选有意拒绝。因此GPU前还需将现有诊断改为完整真实q包及canonical状态观察，固定新夹具和空账本，枚举全部startup/Graph/kernel/传输上限。预计CPU准备1–2小时；这部分尚未实施，不把旧驱动的已通过结果冒充新路线资格。

| 后续新增项目 | 建议上限（尚非执行授权） |
|---|---:|
| 新Op分布/残差＋direct/Graph | 4场景、8 direct Op、4 capture、8 replay（含warmup） |
| native条件q/许可/取消及状态 | 4请求、≤12 decode/verify |
| 正式Chat配对 | 4种新任务各greedy/sampled一次＝8 Chat |
| HTTP warmup / wire | 2 / 12（10模型HTTP＋2health） |
| 总模型提交 | ≤14（native4＋Chat8＋warmup2） |
| 窗口 | 预计10–20分钟，硬20分钟，第17分钟清理候选 |

独立Op的4/8 capture/replay不是全窗口总计，模型startup和decode Graph仍需最终枚举；全窗口GPU资源预算因此保持未冻结。正式Chat关闭profiler；native用于归因与状态，性能结论看完整decode/token和请求wall，而非只看接受率。四个新非重复Java/中文/工具/低接受控制夹具只作筛选，不产生p95或质量等价保证。结果整理预计0.5–1小时；接受率增加但整轮无净收益就停止该配置，不自动加样本。

[机器预算提案](../output/ninfer-v4-sampled-q-20261024/GPU-PILOT-PROPOSAL.json)。

## 保持的限制

原GPU服务最终读回STOPPED/PID0，原镜像未变，GPU无计算进程。没有部署、采样参数调整、Pi预算缩减或旧任务重跑。18处G1差异、C1附件缺口、Baseline缺口与所有历史失败保持。完整采样分布、Graph/FP32状态、缓存恢复、性能采用和生产发布继续独立；`optimization_qualification=false`、`p95=null`。
