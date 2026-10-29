# 机器、模型与已完成工作

## 1. 证据优先级

本次目标机没有连接。以下是附件**最后已知状态**，执行时用只读inventory复核。七份10月25日报告比10月23日入口说明更新；`DEPLOY-A0-EXACT6-20261025.md`覆盖“生产停着/perf没装”的旧状态。历史原文在`../history/`；不改写它们的结论。

| 项目 | 最后已知值 |
|---|---|
| CPU | Intel Xeon Silver4216，16C/32T；AVX512-VNNI，有AVX2，无VBMI；不能假定有AVX-VNNI或AMX |
| RAM | 2×32GB DDR4；STREAM类读测约36GB/s，4～8线程接近饱和 |
| GPU | RTX4090 24GB、sm89；驱动610.57.04 |
| OS | Debian12，kernel6.1.0-17-amd64，glibc2.36，gcc12.2 |
| CUDA/构建 | CUDA12.3；既有成功构建使用venv内cmake4.4.3/Ninja |
| 模型 | Qwen3.8-Flash-Next GSQ-RCO IQ3_XXS，两份GGUF |
| CPU专家实际格式 | 偶层IQ2_XS GU + IQ4_NL down；奇层IQ2_XXS GU + Q2_0 down；执行时重新导出tensor清单 |
| 当前引擎 | v0.2.3 / A0 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` + EXACT6 |
| 当前二进制SHA256 | `819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d` |
| 运行 | spec4，spec-min-p0.5，KVint8，总ctx131072，vram reserve974MiB，expert-cache auto，prefill auto |
| 会话缓存 | 6144MiB、4 slots；这是会话缓存槽，不可直接视为4路并行decode |
| 基础env | STRATA_ADAPT_OVERLAP=1；STRATA_PREFILL_CPU_SHARE_MAX=3072；两项timing |
| EXACT6 | SIDE_MIXER=2、ATTN_DAILY=1、GR_UP75=1、GU_SWIGLU=1、QSA_ROWS=1、B6_MMVQ_ROWS=1（均带STRATA_前缀） |
| host设置 | performance governor；C6关闭；POLL/C1/C1E未改；perf已安装、paranoid=1 |
| 最后部署 | `/home/hhtele/strata-0.2.3`，模型名`openclaw/Qwen3.8-next` |

`spec-min-p=0.5`是推测控制参数，**不是**采样请求里的`min_p`。不得据此套用其他框架关于sampling min-p的限制。

## 2. 已做过的尝试

| 尝试 | 附件报告结果 | 后续处理 |
|---|---|---|
| 旧生产→A0 | MIG-PASS，390请求、5轮 | 不重新执行旧迁移 |
| EXACT6 | 受控窗口约-5.3%；greedy decode约+4～5% | 保留公共基线；在最新源码重新资格验证 |
| performance+C6 off | 18对短请求中位+2.2%，接近组噪声 | 已上线；不是新成果，也不单独归因C6 |
| Ada table / IL0 / IL89 | 无窗口级有效收益 | 默认搁置，除非新profile显示形状显著变化 |
| POOL8 | CPU阶段约+21%、窗口约+5.8% | 不再简单“把16线程改8线程” |
| Q2_0 128位路径 | 微基准变快，真实服务无收益 | 先修bench入口不一致 |
| LOOKUP2 | 当前生成语料无收益 | 只在copy/edit独立语料重新研究 |
| learned profile | 稳态无收益 | 冷启动另立实验，不泛化结论 |
| MTPQ4 head | 窗口约-1.5%，采样不稳定 | 边缘候选，不加入默认 |
| THP | 匿名内存43.0GiB中36.7GiB已是大页 | 不再包装成“打开THP大幅加速” |
| PR2964 | PCIe share低且与ADAPT_OVERLAP冲突 | 现配置不直接适用；与VBMI无关 |
| PR2253 park/restore | 未完成机制复现与A/B | 下一主线之一 |
| NP-3 pool同步 | 有瓶颈证据，尚无实际优化结果 | 下一主线之一 |

## 3. 尚未具备的证据

附件缺原始`workspace/results`、window-trace、nsys数据、实际local.json，以及历史mig_analyze/cfg_analyze/mkdecode脚本；因此不能在本轮重算历史CI或声称复现实机结果。原MANIFEST也未覆盖后加的七份报告。本包只保存它们及独立哈希作为历史记录。

EXACT6既有质量测试与七开关组合并非完全同一候选；旧JSON评分还存在bool与int混同问题。后续不抹去旧结果，但必须用修复后的评分器重新验证实际候选。

## 4. 必须重新只读确认的内容

- SSD型号、当前空闲空间、PCIe实际协商宽度/代际/传输速率（4216平台是PCIe3.0；不假定4090总以PCIe4运行）。
- 当前服务PID/二进制/实际args/env，以及生产是否从附件时间以来发生变化。
- pack、GGUF、MTP、template、profile、tokenizer哈希和大小；源模型和实际部署pack分别记录。
- KV是否全部GPU驻留、RAM热区/冷区、memlock、swap、cgroup约束、OCR或其他共存负载。
- 正常Pi负载的thinking、采样、工具schema、输入输出分布；旧greedy题集不能代表这些。

CPU官方规格：[Intel Silver4216](https://www.intel.com/content/www/us/en/products/sku/193394/intel-xeon-silver-4216-processor-22m-cache-2-10-ghz/specifications.html)。其六通道能力不等于本机实际装满六通道；软件不能把两条DIMM变成六条。
