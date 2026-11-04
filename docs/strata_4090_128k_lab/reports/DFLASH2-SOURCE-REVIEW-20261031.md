# DFlash2 / DSpark 第一方来源核查（2026-10-31）

2026-11-03 补记。下文的 CLI 限制适用于当时核查的版本。v0.2.10 单卡服务支持和 29 的实际准备状态见 [发布版评估](DFLASH2-V0210-READINESS-20261103.md)。

本报告只核查源码、模型仓库元数据和原作者公开测量。**本次无 GPU、无 SSH、无模型权重下载、无服务启动、无配置变更、无新本机测量。** 外部测量均为作者报告，不是本机验收。本报告不授权实验，也不替代主测试方案。

## 结论

- **已证实：** A0、P6 和用户指定主线快照的 DFlash2 是单卡 CLI 路径；`--serve`、`--batch`、layer split 会拒用并回退 MTP。Control 层也主动回退。不能把启动选项存在当成 HTTP 服务真正使用 DFlash2。[A0源码](https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/src/program/generate.cpp#L5474-L5517)、[P6源码](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/program/generate.cpp#L6220-L6260)、[指定主线源码](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/program/generate.cpp#L6301-L6343)。
- **已证实：** 官方 DFlash2 资产与 Strata 固定下载 revision 一致，原始 BF16 safetensors 和 Strata Q8 pack 是不同产物。官方 SGLang/GB300 的正收益、消费卡的正负结果，都不能推出本机 4090 收益。[Strata资产常量](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/strata_control/drafting.py#L84-L101)、[官方模型卡](https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2/blob/a22a1744e85c17364dcc54a6a420af7135d4c7f6/README.md)。
- **需纠正：** Strata 的 `--dspark` 是独立 DeepSeek-V4.1 引擎入口；社区 Qwen DSpark 依赖 SGLang 适配，不是 Strata Qwen drafter 的现成开关。[构建目标](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/CMakeLists.txt#L906-L920)、[DeepSeek参数解析](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/dsv41/ds4_main.cpp#L1332-L1343)。
- **UNKNOWN：** DFlash2 + Strata 概率拒绝采样模式的端到端正确性。源码存在 MTP q 路径与 DFlash2 proposal 来源需要核实的交互，见后文。不能用官方算法的 lossless 声明替代特定实现验证。

## 固定身份及证据边界

| 用途 | 固定身份 | 核查状态 |
|---|---|---|
| A0 | `5c8dd322528cc84f68f461ad54a506b9da8fa8d4`，用户指定 v0.2.3 | 已读取 generate / drafting / packer；release页SHA匹配 |
| P6 | `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`，用户指定 v0.2.7 | 已读取同组文件；release页SHA匹配 |
| 用户提及主线快照 | `c62d5e3a15b40ea51c96aae9e8d36928965f53ab` | 从 GitHub commit 页嵌入元数据解析完整 SHA；不以最新 main 替换 |
| 官方 DFlash2 | `incoai/Qwen3.8-Flash-Next-DFlash2@a22a1744e85c17364dcc54a6a420af7135d4c7f6` | HF API 当前 sha 与 Strata常量一致 |
| 社区 DSpark | `shadowpa0327/Qwen3.8-Flash-Next-DSpark@3f74bdfa4a1b9deaaa56cc7c1377440ec5095fad` | HF API读取后，README/config 均按该 SHA 获取 |

直接身份入口：[A0 release](https://github.com/Niko1221/Strata/releases/tag/v0.2.3)、[P6 release](https://github.com/Niko1221/Strata/releases/tag/v0.2.7)、[指定主线commit](https://github.com/Niko1221/Strata/commit/c62d5e3a15b40ea51c96aae9e8d36928965f53ab)、[DFlash2 API元数据](https://huggingface.co/api/models/incoai/Qwen3.8-Flash-Next-DFlash2?blobs=true)、[DSpark API元数据](https://huggingface.co/api/models/shadowpa0327/Qwen3.8-Flash-Next-DSpark?blobs=true)。API查询和PR状态会变化；产物内容使用上述 immutable revision。

## DFlash2 的真实合同

**已证实：服务限制。** 三个快照的 `generate.cpp` 检查 `multi_gpu || o.batch > 0 || o.serve`；还要求 MTP fallback、native target pack 和 drafter pack。P6的 `ENGINE_SERVES_DFLASH2 = False` 使 `decide()` 返回 MTP，即使用户选了 dflash2；成功加载后 CLI 仍保留 MTP fallback。是否启用必须检查实际成功回执与轮次数，不能仅看命令行。[P6 generate](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/program/generate.cpp#L6220-L6262)、[P6 Control](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/strata_control/drafting.py#L141-L176)。

**已证实：资产。** 固定 revision 的 `config.json` 为 1,236 bytes，`model.safetensors` 为 1,206,140,008 bytes，后者 SHA256 为 `d6723f2a359eaf33ec0c95f22ae8edda896774020c552296a85e1913b4d3186f`；模型卡标 Apache-2.0、base model 为 Qwen/Qwen3.8-Flash-Next。仓库没有随附 tokenizer 资产，因此不能按 drafter 名称推断任意 target/tokenizer 兼容。[固定模型文件](https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2/tree/a22a1744e85c17364dcc54a6a420af7135d4c7f6)、[Strata校验常量](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/strata_control/drafting.py#L84-L101)。

**已证实：转换支持。** `tools/dflash2_pack.py` 默认将矩阵转为 `q8_0`，小张量使用 f32/bf16，支持 `--bf16`；引擎产物名为 `qwen3.8-flash-next-dflash2.q8.pack`，不是下载仓库自带 GGUF。这里的 Q8 支持指 drafter pack，不保证任意量化 target 的接受率或质量。[固定packer](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/tools/dflash2_pack.py)。

**已证实：几何与特征。** 官方配置为 5 层 sliding attention，32 Q heads / 8 KV heads / head_dim 128 / hidden 2560，window 2048；target层为 `[5,15,25,35,45]`，vocab 248320，mask token 248077。Strata实现的 block 为 anchor + 7 masks，ring 2064，K/V为float；prefill只取最后最多2047行target taps，以2048行容量请求捕获。256K位置上限不表示 drafter保存256K全量KV。[官方config](https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2/blob/a22a1744e85c17364dcc54a6a420af7135d4c7f6/config.json)、[native几何](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/include/strata/core/dflash2.hpp#L1-L38)、[末prompt捕获](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/program/generate.cpp#L17454-L17457)。

### 显存账：确定项与估计项

| 项目 | 可核实的结果 | 限制 |
|---|---|---|
| DFlash2 FP32 K/V ring | `5 × 2 × 2064 × 8 × 128 × 4 = 84,541,440 bytes = 80.625 MiB` | 根据源码 float ring 分配精确计算；不是全部buffer |
| target features形状估算 | `2048 × 5 × 2560 × 4 = 100 MiB` | 形状上限计算，不证明同时驻留/峰值/分配生命周期 |
| Q8 pack | Control写约0.76 GB；社区记录760,353,792 bytes（约725.13 MiB） | 文件大小与GPU常驻字节可能不同；不可把760MB写成760MiB |
| draft head及其它scratch | 源码提示约0.2 GiB head、buffers+ring约0.25 GiB | 取决于native head格式、draft_vocab子集与graph工作区 |
| 总计1.0–1.2GiB | 可作为源码预算级估计 | 不是4090测量；CLI还保留MTP，不能当替换后净增量 |

来源：[ring实际分配](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/dflash2.cpp#L227-L241)、[head子集分配](https://github.com/Niko1221/Strata/blob/c62d5e3a15b40ea51c96aae9e8d36928965f53ab/src/core/dflash2.cpp#L310-L329)、[预算提示](https://github.com/Niko1221/Strata/blob/5c8dd322528cc84f68f461ad54a506b9da8fa8d4/src/program/generate.cpp#L5511-L5514)、[社区文件/VRAM记录](https://github.com/Niko1221/Strata/issues/3965)。源码日志自身存在 GB/GiB近似混用，规划应记录 bytes，并区分文件、常驻、加载峰值和专家槽净损失。

### 采样正确性：UNKNOWN，不将算法声明当实现证明

官方卡声明 greedy等价、sampling保持target分布；其参考环境是patched SGLang，不是 Strata native。[官方声明与参考启动](https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2/blob/a22a1744e85c17364dcc54a6a420af7135d4c7f6/README.md)。

P6静态证据如下：

1. `STRATA_SPEC_COUPLED` 和 `STRATA_SPEC_PROB` 都默认 off；PROB同时启用coupled基础设施。单独COUPLED不会分配q列表，PROB才分配。[环境默认](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/include/strata/core/coupled_draft.hpp#L51-L80)、[q分配](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/core/mtp.cpp#L609-L614)。
2. `mtp.prob()` 为 `coupled_active_ && h_q_ != nullptr`；非greedy、temperature>0且不低于spec_min_temp时，`set_draft_sampling`可激活coupled_active_。[定义](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/include/strata/core/mtp.hpp#L133-L137)、[激活条件](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/core/mtp.cpp#L646-L651)。
3. DFlash2的下一轮proposal来自`df2.draft`，该分支直接返回，不由`mtp.draft`生成；同时gated proposal条件明确将`spec_uses_df2`作为不可用条件。[proposal来源](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/program/generate.cpp#L18163-L18201)、[gate条件](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/program/generate.cpp#L18064-L18071)。
4. 后续`else if (use_mtp && mtp.prob() && !from_sfx && T_mtp > 1 && o.spec_corrupt <= 0)`仍调用`ver.set_spec_q(mtp.spec_q(), T_mtp - 1)`，未显式排除DFlash2。[调用位置](https://github.com/Niko1221/Strata/blob/5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d/src/program/generate.cpp#L18294-L18297)。

**基于证据的推断：** 开启PROB且使用DFlash2、非零温度时，存在验证使用的q不对应实际proposal的风险；尚未沿全部初始化/生命周期证明触发，所以不定为已复现bug。默认off也不代表用户生产配置off。必须先冻结真实环境并证明q来源/拒绝残差/状态回滚合同，再安排生产采样性能筛查。普通exact-match路径仍需数值、处理器和状态一致性验证；greedy速度或几个同seed输出不能证明采样分布等价。

## 公开性能：仅来源报告

### 官方 GB300 / SGLang

以下数字已与固定模型卡逐项一致。条件：单GB300 TP1、FP8 target、SGLang；QSA限制verify block4（两种方法同为3个draft）；temperature1/top-p0.95/top-k20、xhigh、输出上限4096含reasoning；并发1、128 samples。指标为总output tokens / end-to-end wall time，不能改称Strata纯decode。[完整原始条件与表格](https://huggingface.co/incoai/Qwen3.8-Flash-Next-DFlash2/blob/a22a1744e85c17364dcc54a6a420af7135d4c7f6/README.md#evaluation)。

| 任务 | MTP tok/s | DFlash2 tok/s | 相对MTP增幅（本报告算术复核） |
|---|---:|---:|---:|
| GSM8K | 326.0 | 368.2 | 12.94% |
| MATH-500 | 325.9 | 383.6 | 17.70% |
| HumanEval | 296.9 | 363.8 | 22.53% |
| MBPP | 304.7 | 378.3 | 24.15% |
| MT-Bench | 285.1 | 343.8 | 20.59% |

这是数据中心卡/官方FP8/参考运行时的证据，不是4090+IQ3_XXS+CPU专家卸载+128K预测。

### 消费卡与旧独立PR

**已证实（作者报告）：** #3965 的4060Ti16GB、IQ3_S、greedy：1024输出41.61→40.22 tok/s（−3.3%）；16K prompt+16K output为47.64→42.85（−10.1%）；专家槽3594→3027。每个测试仅一对，两边后续文本分歧，无完整质量对照。[原始报告](https://github.com/Niko1221/Strata/issues/3965)。

**已证实（作者评论）：** 同issue的5080 NVFP4，单卡CLI，cap5为82.16→87.43（+6.4%），同session结尾MTP82.18；但此前同MTP跨session100.79→82.16约−18.5%。不能用跨session单次pair给drafter排名。评论将漂移解释为adaptive expert placement导致文本变化；这是作者解释，本次未独立验证因果。[Hazelhof评论](https://github.com/Niko1221/Strata/issues/3965)。

**纠正：** PR #3322 当前是closed、未merge；页面最后head为`4335151ce0033b951e93b3818b2d7c73b0c24019`，是j-luwierski的独立分支，不是当前main服务能力。作者4070TiSUPER/NVFP4短代码+29.05%，256K+14.84% decode，但后者仅一次96-token greedy，整请求1012.19→1019.47s（慢0.72%）；这些不是128K本机结果。PR关闭本身不能证明其每项实现都未被其它提交吸收。[PR状态/测量](https://github.com/Niko1221/Strata/pull/3322)、[固定分支head](https://github.com/j-luwierski/Strata/tree/4335151ce0033b951e93b3818b2d7c73b0c24019)。

## DSpark：配置成本与测量版本不能混为一项

**已证实：** 固定社区revision配置为5层full attention、8KV heads×128、BF16、hidden2560，target taps `[1,12,23,34,45]`、mask248070、vocab248320，与DFlash2的层位和mask不同；不能互换权重。模型卡为664.6M参数，embedding/LM head由target共享。[固定config](https://huggingface.co/shadowpa0327/Qwen3.8-Flash-Next-DSpark/blob/3f74bdfa4a1b9deaaa56cc7c1377440ec5095fad/config.json)、[固定模型卡](https://huggingface.co/shadowpa0327/Qwen3.8-Flash-Next-DSpark/blob/3f74bdfa4a1b9deaaa56cc7c1377440ec5095fad/README.md)。

**成本推算：** 若单序列、131072 tokens、全量BF16 KV，`5×2×131072×8×128×2 = 2.5 GiB`；资产文件1,329,146,274 bytes≈1.238GiB。两者约3.738GiB仅是权重文件+KV几何估算，不含scratch、graph、feature capture、并发和加载峰值，也未扣除被替换的MTP分配，因此**不等于净增量**。[固定config](https://huggingface.co/shadowpa0327/Qwen3.8-Flash-Next-DSpark/blob/3f74bdfa4a1b9deaaa56cc7c1377440ec5095fad/config.json)、[资产元数据](https://huggingface.co/api/models/shadowpa0327/Qwen3.8-Flash-Next-DSpark?blobs=true)。

**已证实：测量口径。** 下表是step1600、greedy、H100 TP2、patched SGLang0.5.21、block7的accepted length，**包括bonus token**；对照是MTP7steps，不能当成MTP4 A/B。step1800是当前上传，速度则来自step1200。[固定卡Results/Verification](https://huggingface.co/shadowpa0327/Qwen3.8-Flash-Next-DSpark/blob/3f74bdfa4a1b9deaaa56cc7c1377440ec5095fad/README.md#results)。

| context | DSpark step1600 | MTP7 |
|---|---:|---:|
| 0–8K | 5.64 | 5.07 |
| 32–64K | 3.41 | 3.76 |
| 64–96K | 3.95 | 4.69 |
| 96–128K | 3.16 | 4.07 |

**关键服务限制：** 卡片明确step1800未served；stock SGLang0.5.21需仓库aux-capture addon，只允许block3，而表中block7依赖未随仓库发布的QSA补丁。上传资产+stock addon的端到端服务验证尚待完成。故当前表不能作为可直接复现实验或Strata候选已ready的证据。[固定卡Serving与Verification status](https://huggingface.co/shadowpa0327/Qwen3.8-Flash-Next-DSpark/blob/3f74bdfa4a1b9deaaa56cc7c1377440ec5095fad/README.md)。

**许可证：** HF元数据为`other`；卡片说明权重受nvidia/Qwen3.8-Flash-Next-NVFP4许可约束，训练数据Open-SWE-Traces为CC-BY-4.0。不能把DFlash2的Apache-2.0套用到该社区权重。[固定卡License](https://huggingface.co/shadowpa0327/Qwen3.8-Flash-Next-DSpark/blob/3f74bdfa4a1b9deaaa56cc7c1377440ec5095fad/README.md#license)。

## 未决项与下一项最佳验证

- **高置信度：** 固定源码的CLI/serve限制、Control回退、固定模型配置、文件身份和显存公式。
- **中置信度：** 公开性能表已核对原作者文本，但无原始日志重算/独立复现；PR/issue状态只是本次查询快照。
- **UNKNOWN：** 4090真实净显存、专家槽减少及端到端收益；DFlash2+PROB采样合同；本机已有同名GGUF是否Flash-Next兼容；社区DSpark当前权重在可取得的补丁版本上是否可完整服务。
- 下一步仅建议：先离线审计实际target/drafter metadata、tokenizer与feature合同，并封闭采样q路径疑点，再由主测试方案确定是否申请实验。当前来源证据不支持自动启用、下载、移植旧PR或部署。

## 本次执行和限制

执行了只读git状态检查、本地历史文档阅读、HTTPS获取固定源码/README/config/资产元数据、公式与百分比算术复核；仅新增本报告。GitHub REST API返回rate limit后改读公开HTML/raw源码；未用API失败推断对象不存在。未执行pnpm检查（无应用代码变更），未执行任何推理/benchmark/SSH。历史本地文档只作定位线索，结论回到上述第一方来源。
