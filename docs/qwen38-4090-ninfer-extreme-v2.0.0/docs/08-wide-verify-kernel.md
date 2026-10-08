# 宽验证 Attention：T6 → T8 → T16

## 1. 基线是已审阅的代码，不是报告描述

44a small-T compile和dispatcher只到6。[S03/S04] 先在诊断日志记录每个实际width选择的是small-T、prefill/generic还是报错；W8能得到结果不等于走了高效decode。T07先做**正确可运行路径**，T12再做性能，不为了benchmark伪造route_label。

## 2. shape与内存合同

主Attention B=1、Qheads24、KVheads4、group6、d256。页/scale地址来自现有cache view，prefix长到200192（生产基线仍以262144运行，kernel须两者都正确）。Q为W=4/6/8/16，liveQ可小于W，key有效位置依column变化。output与split partial的accumulation dtype锁定，不能把FP16 scratch当FP32读（历史fork已发生过此类错误）。

每个CTA内将一个KV tile尽可能复用到多query rows和对应GQA heads；不许宣称全GPU只读一遍。先计算寄存器、sharedmemory和并行度，再选择Bc/Bq/headsperCTA/splits。SM89 block动态shared上限99KiB需opt-in，不能带入sm103的227KiB。[S14]

## 3. 算法与精度

保留当前packed4 code + scale解码数学。对rk4v4-e8，读取路径是packed4，不把Root decoder优化当lattice读优化。Q旋转域、scale顺序、RNE、在线softmax的m/l更新顺序需要对oracle。不得在本任务添加coset bit、换成另一E8编码或降累加精度。[S05]

将tile的K/V unpack与load overlap；逐row保持独立softmaxmax/sum；归并split时采用现有稳定公式。tail tile只读有效范围；mask非法列完全不写target state。使用64位byte offset，测试超过2GiB地址跨度和非连续page表。

## 4. sweep范围

只搜索小网格：W={4,6,8,16}，Bc={32,64}，splits={4,8,16,32}，headpacking={1,2}；并非所有组合都合法，编译前资源过滤。一次改变一个major lever。先fixture短shape验证，再64K/184K计时；不得用最优microbenchwinner跳过model。

Metrics：总round_ms、attn_ms、DRAMread、L2hit、registers/spill、barrierstall、achievedSMclock、replayGDN/head成本；ncu仅诊断。正常计时关闭profile，并使用相同warmup/热状态。

## 5. 验收与回退

字节级codec解码一致；输出与现有算子按预登记numeric合同验证，所有分支/partial mask正确；全模型greedy和teacher-forcedstate比较。kernel >10%但全round<3%不合入默认；W16若AL/latency曲线不赢W8则不继续扩大。保持small-T旧路径feature flag随时回退。264K以外不扩本轮范围。
