# 00 · 冻结身份与事实分层

## 四个来源层次

| 标记 | 含义 | 本包如何使用 |
|---|---|---|
| R | 固定仓库提交中的报告/源码 | 可核查历史证据；报告中的原件路径不代表原件已读取 |
| U | 用户本次提供的信息 | 当前任务背景；“Astra xhigh仅建议一次诊断”属于此层 |
| S | 外部固定源码/官方文档 | 证明机制存在和限制；不证明本机更快 |
| H | 本包推断或设计政策 | 必须通过未来实验；没有填造实测数据 |

证据仓库固定 `lkyprogramer/CodexGame@3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0`。本包取读了核心报告、规范和指定实验工具；没有获取所有 workspace 原件。故可审计报告一致性，不能声称独立重新计算 P24 的全部原始统计。

## 机器与运行配置

| 项 | 冻结事实/后续核查 |
|---|---|
| GPU | RTX4090，24GB，sm89；不是5090、SM90或SM120 |
| CPU | Xeon Silver4216，16C/32T，旧记录pool15 workers；有AVX512-VNNI不等于支持VBMI/VPOPCNTDQ |
| 内存 | 2×32GB DDR4，OS约62GiB；旧只读带宽约36GB/s属于历史测量，不是当前硬上界 |
| 工具链 | Debian12、CUDA12.3、gcc12.2；P6用已有CMake4.4.3构建成功 |
| 模型 | Flash-Next GSQ-RCO IQ3_XXS包；内部GU存在IQ2_XXS/IQ2_XS/IQ3_XXS/IQ3_S/IQ2_S等，不能以包名猜实际分派 |
| 结构 | 48层：36 GDN+12 QSA；每层512专家、top10；现有tail-skip等基线行为原样冻结 |
| Context | 总131072；输入包含template/tools/history，另留4096安全余量 |
| KV | int8、resident20480；全部QSA主K/V理论约1.55GiB，不含index、状态、draft、scratch |
| 草稿 | MTP spec4，spec-min-p0.5；该阈值不是请求的min_p |
| 服务 | reply reuse=1、preserve thinking=0、CPUSHARE4096、AUTOMAX16384、EXACT6、overlap |
| 会话 | cache6144MiB、slots4；不能直接相乘当物理占用；不为跑分改成cache0 |
| 请求 | Pi典型xhigh、temperature1/top_p.95/top_k20；主用单会话无并发 |

来源：[环境记录](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/docs/02_ENVIRONMENT.md)、[P5格式/ISA实测](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P5-GU-VNNI-PROBE-20261027.md)、[P6基线](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P6-V027-BASELINE-20261028.md)。

## 版本身份

| 名称 | SHA/身份 | 角色 |
|---|---|---|
| 生产 A0 | `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` +本地补丁 | v0.2.3；保护对象 |
| 本轮研究 B | `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d` +P6六文件Python port | v0.2.7/engine0.1.52；原生无HC |
| P24 HC | 报告binary `9a6b441d…00bb` | 已拒绝的候选，不作B |
| 当前main | `870aedd9e1ebe1c91f94da93b59af17729f6c5c0` | 只作源码donor |

P6 reported binary SHA256为 `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`。完整toolchain flags、GGML逐文件清单、六文件port和资产hash要从原件恢复；包内不编造缺失值。

## 状态不能倒写

U：截至10月30日用户只读复核生产inactive/dead，GPU1MiB、13项保护文件未变。R：P24结束也如此。原作者未连接29。整合时于2026-10-30 11:47北京时间只读核对：服务inactive/dead/enabled、GPU1MiB且无计算进程、18089未接受连接、13保护文件与P24一致；P6原二进制SHA匹配。见 [现场回执](../sources/HOST29_READONLY_20261030.json)。这没有验证完整源码/port/模型大文件，也不完成P00。 实验执行时需重新核查，不能把这些历史状态直接当GPU空闲租约。

P3正式组合未通过；KVRES历史确实部署过不等于正式组合门通过。P6未升级生产。六项长检索仍FAIL；P8/P9支持问题与当前模型/提示条件有关，未分离基础模型和量化影响。详情见[关闭台账](01_EVIDENCE_AND_CLOSURES.md)。

## P6默认值与构建合同必须逐项一致

除EXACT6的原始六开关回执外，P6固定 `STRATA_DEFAULTS=026`；`STRATA_MMVQ_IL_89`、`STRATA_PROMPT_ATTN_IMMA`、`STRATA_KVA`、`STRATA_ROUTE_PRIOR`、`STRATA_DEQUANT_SIDE`、`STRATA_PLE_AUTO_RAM`均为字符串`0`。构建保留`STRATA_MMQ_KQUANTS=OFF`、`STRATA_Q6K_EXPERTS=OFF`、Release、sm89、CUDA12.3。source patch、build flags、runtime env分别记录。相同SHA不保证这些默认分派一致。

研究B的`expert-cache auto`历史实际10272 slots，P3为10290；不调参数凑槽位。启动复查完整实际env/argv及分派，冲突即BLOCKED_EVIDENCE。`STRATA_VERIFY_PROFILE`键必须删除，并核实际PID environ不存在；设0仍会开启。正式性能的其他presence-sensitive timing/dump变量按源码逐个删除，不能把全部STRATA变量粗暴清空。

EXACT6逐项为 `STRATA_SIDE_MIXER=2`、`STRATA_ATTN_DAILY=1`、`STRATA_GR_UP75=1`、`STRATA_GU_SWIGLU=1`、`STRATA_QSA_ROWS=1`、`STRATA_B6_MMVQ_ROWS=1`。以实际PID environ回执验证，不能只看启动脚本。七项试验中的`STRATA_CPU_IQ_ALL_EXACT1`已被drop-one剔除，不得重新带入。来源：[P0-T6](https://github.com/lkyprogramer/CodexGame/blob/3cd82436ed7fe71daf79cfbe03f7fc05d5601fb0/docs/strata_4090_128k_lab/reports/P0-T6-CFG-20261025.md)。

## P00新增冻结证据

2026-10-30已完成P6六port/HEAD/二进制/3574依赖/16资产全hash核对，准备真实Pi 103183token输入。P00状态EVIDENCE_LOCKED，P01未运行；最新准备与pending项以实验主目录reports/P00-EVIDENCE-20261030.md及workspace/frontier/p00-20261030/PHASE_GATE.json为准。
