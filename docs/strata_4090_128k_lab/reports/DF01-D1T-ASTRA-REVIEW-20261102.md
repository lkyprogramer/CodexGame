# DF01/D1T n2300 独立终审

日期：2026-11-02。审查档位：Astra / xhigh。结论：**最终根因未定位；没有具备证据的单点修复，支持停止当前候选。** D1 保持未通过，D2 未开始。原 FAIL、冻结参考和 token 硬门保持。

本次能够确认的是：n2300 第 4 项 token 分歧可以由进入 head／selector 之前的 drafter 行差异复现；同一尾部合同下，两个候选的总分排序翻转。尚未确认产生行差异的首个错误算子，也不能判断 CPU 参考或 GPU 实现哪一侧需要修正。不能把“数值差异”“近邻排名翻转”或“普通舍入”直接写成最终原因。

本代理只读审查源码、冻结清单、历史负结果和主代理本轮产物；没有运行尾部、完整模型、CUDA 程序或生成，没有派发其他代理。唯一写入是本文件。

## 已观察证据

已直接读取本轮 `../TAIL_RESULT.json`、`../check_tail.py`，并与 D1O 原尾部脚本逐行比较。新脚本只调整 n2300／seed4 输入、D1S 原观察路径、目录层级和本轮截止时间；没有改变尾部计算。它复用 D1N 原 Q8 pack、夹具 head／词表、D1L 真除量化及原 native integer GEMM。

主代理唯一一次数值重放完成于 `2026-11-02T13:18:49.008559+00:00`，耗时 `3.0952010238543153` 秒。其回执显示：CPU 尾部程序 1、保存行输入 2、selector 行 14、完整 backbone 前向 0、GPU 程序 0、生成 0、服务变更 0。运行环境为 Torch `2.5.1+cpu`，`torch.version.cuda=null`，`CUDA_VISIBLE_DEVICES=''`。

| 检查 | 已观察结果 |
| --- | --- |
| 冻结 CPU 行重放 | 7 个 token 精确一致，7 个概率逐 bit 一致 |
| 保存 GPU 行经 CPU 尾部重放 | 7/7 token 与原 GPU 输出相同 |
| 同 GPU 行的尾部概率最大误差 | `6.705522537231445e-7` |
| 第 4 项 GPU 原概率 | `0.22695942223072052` |
| 第 4 项 GPU 行 CPU 重放概率 | `0.2269587516784668` |
| 冻结 CPU 第 4 项概率 | `0.33877629041671753` |

尾部程序核对的 7 项 SHA256 全部匹配冻结身份；夹具尾部 rows／tokens／probabilities 与独立 reference 文件逐 byte 一致。关键输入身份：

- D1N `reference-n2300.bin`：`e17b4007ba1d280e57413812465f70ad3aced52e8d1d3108374d58642c2180ca`。
- D1S `drafter-n2300-seed4.bin.v2-observed.bin`：`604f0cf9bc8c5231b5db56fe6a0112e68c1bbf00d9a41977cedf2ee4355514d5`。
- 原 Q8 pack：`c7d83c0cdfeadc7c692a1587795adb0181cfd94dacd96ac1a91f71ea7ecc62ed`。

## 第 4 项的具体分叉

以下均为本轮 CPU 尾部重放值，不冒称保存了 GPU 中间分数。token index `3` 使用最终 rows 的零基行 `4`。两边前驱都是 `174243`；`212522` 和 `209087` 在两套 top-16 中同时存在，对应 head 行号分别为 `213` 和 `209`，候选序号分别为 `0` 和 `3`。

| 输入行来源 | token | unary | pairwise | total score |
| --- | ---: | ---: | ---: | ---: |
| 冻结 CPU 行 | 212522 | 22.7847518921 | -1.5253752470 | 21.2593765259 |
| 冻结 CPU 行 | 209087 | 19.9990215302 | 0.9545275569 | 20.9535484314 |
| 保存 GPU 行 | 212522 | 22.3655433655 | -1.5749654770 | 20.7905769348 |
| 保存 GPU 行 | 209087 | 19.9087772369 | 0.8896739483 | 20.7984504700 |

冻结 CPU 行使 `212522` 领先 `0.3058280944824219`；GPU 行使 `209087` 领先 `0.00787353515625`。这不是精确同值规则触发，不是其中一个赢家未进入 top-16，也不是此前 token 已分叉造成的前驱差异。第 5 项随后使用不同前驱，因此后续概率差不能全部解释为该行自身的孤立误差。

rows 零基行 4 的 cosine 为 `0.9993771043304526`，norm ratio 为 `1.0014121922215227`，最大元素绝对差为 `0.5171394348144531`。高 cosine 与 norm 门通过并不保证两个候选的相对分数不变；此处只解释已观察失败如何传递，不改变任何门限。

## 实际合同复核

已读 D1N `freeze_reference.py`、D0B `dflash2_ref_q8.py`／`make_q8_fixtures.py`、D1L `cpu_reference.py`／`native_ops.cpp`、D1R `reference_ops.py`，以及 D1Q 实际 `drafter_qualification.cpp`／`qualification_v2.hpp`。

GPU 侧使用 D1C 保存的源码副本审查，并通过只读 `ssh -J jump 29` 对当前 base 源文件执行 `sha256sum`；以下 5 份文件与本地副本一致。前三份及 Q8_1 helper 也逐项对照 D1Q `FINAL_FREEZE.json` 中的原身份。

| GPU 源文件 | SHA256 |
| --- | --- |
| `src/core/dflash2.cpp` | `5e851a122875450baff7ff558afa18534611579a65b066b137c6225cb38063eb` |
| `src/kernels/cuda/dflash2.cu` | `30d2615421f92d9b4de52212ae5088740cadbb9c3d9576ae35dc65d6c21c3d34` |
| `src/kernels/cuda/native_mmvq.cu` | `adf77ee9264ffc331e96a7b8afb440273415f0019e3cb7a5ba1aa0da9dde55fb` |
| `include/strata/kernels/q8_1_finite.hpp` | `6789c75d692ef1cf21a07d8d602e5cf35ad40657b715f8d510cf7ddad1162598` |
| `include/strata/core/dflash2.hpp` | `ab6a17d1318b80ff8b6c6e6f404199c1a8e533d788a54e31ff8c00e0b686b23f` |

关键合同及定位：

- `src/core/dflash2.cpp:422` 起，两条尾部路径均读取最终归一化 `fn_` 的 rows 1..7。head 使用 `native_quantize_q8_1`；hidden projection 使用 `df2_quant_rows`。D1N 两条激活量化格式与此对应，不能互换。
- `q8_1_finite.hpp:24` 与 `native_mmvq.cu:156`：head 先由 FP32 `amax / 127` 得到 scale，`roundf(x / d)` 取整并限制到 int8，再保存 FP16 scale。夹具 head 的 34-byte Q8_0 block 解码一致。本夹具绑定类型 `8`，不是原 Python 文档字符串所描述的真实 target Q6_K head。
- `dflash2.cu:341`：planar Q8 使用一次 `127.0f / amax`、RN-even、FP32 scale；D1L 已保留真除修复。`:279` 起的 GEMM 为 int8 点积、FP16 权重 scale × FP32 激活 scale、FMA、32-lane XOR 归约；D1N 使用的 `native_ops.cpp:4` 保持同一拆分顺序。
- `dflash2.cu:515`：top-16 以分数降序、同值时 head 行号升序，再映射词表。D1N stable argsort 后再映射词表相符。`:591` 起 selector 使用前一个选中 token 的 predecessor codebook，分数为 `unary + successor · (predecessor * hp)`，同值取候选首项；D1N 对应 `argmax`。概率是在这 16 项总分上的 softmax，未错误当作完整词表分布。
- GPU 夹具 `context(n-1)` 后 `draft(last,1,n-1)` 得到 anchor position `s=n`；CPU `set_context(n)` 后 `draft(n)` 相符。n2300 的 context 下界 `lo=253`，读入位置 253..2299；2064 槽 ring 保留 236..2299，所需位置没有被新写入覆盖。GPU context mask `j > s + row - window` 与 CPU 当前窗口定义相符。此为源码索引检查，不是新增 GPU 状态验收。
- D1Q v2 只把完整 drafter 概率差分类为诊断。它仍调用原行／token 比较逻辑，独立 selector、target sampling、commit、EOS 未被绕过。n2300 token 失败仍需停止。

以上未发现能够解释本次分歧的具体 selector、head、量化布局或位置合同缺陷。CPU head 矩阵乘法和 selector 归约仍未承诺与 GPU 每个中间值逐 bit 相等；本轮同输入输出级交叉检查支持排除尾部作为此 token 分歧的必要来源，不替代尚未运行的三组独立 GPU selector 硬门。

## 修复资格与停止意见

已知 CPU/GPU 算术差量仍存在于 RMS 归约、RoPE 频率／角度精度和分块 attention 次序。D1O 原报告与审查已保留统一候选 n2048 通过、n32 回归失败的结果。本轮没有重跑或采用该组合。源码存在算术差量，不足以指定其中一个为 n2300 的首个错误算子。

现存 n2300 原件只有最终 rows／tokens／probabilities，没有逐层 GPU 同输入输出或 head／projection／selector 中间快照。当前证据链止于“前向行差异 → 同一尾部下分数排序翻转”。不能据此归因到某个 RMS、RoPE、attention 算子，不能确认普通舍入是全部原因，也不能认定 GPU 侧必然错误。

**无可证明且可在本轮收口的单点修复；建议立即停止候选。** 不消耗剩余时间做计算顺序组合，不按 context 拼参考，不修改原 gold 或 FAIL，不追加 GPU，也不以置信度诊断豁免 token 硬失败。D1 仍未通过；独立 selector、target sampling、真实提交状态、EOS 和六次生成仍未运行，不作性能、最终 target 正确性或生产采用结论。

本代理验证限于上述只读源码／SHA 检查及对主代理执行产物的复核；没有重复数值前向、编译或运行比较器，没有运行应用 `pnpm` 检查，没有服务启停或生产恢复。
