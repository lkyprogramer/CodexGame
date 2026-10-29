# 同 token、同量化权重的独立 logits 对照（2026-10-28）

**两个prime的错位数字和提前EOS均在独立llama.cpp模型图中复现。** 完整69616/102392-token输入、同一份量化GGUF，两边16/16个长输入位置的argmax一致，分别为 `1751936`＋EOS、`6395887`＋EOS；短复制资格另8/8一致。参考保留FP16 KV，未使用Strata服务、Verifier、MTP或专家缓存路径。

这更支持“当前量化模型＋长表＋原none提示”的条件相关失败，削弱Strata独有实现或int8 KV为必要成因的解释。**仍未分离基础模型与量化，也未证明所有数值内核正确。** 原六项保持FAIL，评分不变；生产未改、未部署，DEQUANT_SIDE仍未运行。

## 对照身份与独立性

Strata复用P6隔离树：v0.2.7 `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`，原生二进制SHA256 `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`，六文件 #1536/PT 移植及完整配置不变。使用现有 `STRATA_DUMP_FIRST_LOGITS` 观测入口；未改原生代码、采样、EOS处理或ISA门控。`GEN 1` 在每个冻结前缀上只求下一token，不经过HTTP。

参考使用29上已有的 llama.cpp 分支 `/home/hhtele/buun-llama-cpp-87b37ea`，HEAD `87b37eac9be678c8fcbef59506e6d16b6c4ba04c`。核实 `src/models/qwen4exp.cpp` 实现了实际GGUF架构的HC、GDN、QSA及PLE，支持该文件使用的Q2_0 group-64；不是替换为Qwen3.6或只重用Strata Verifier。新编译的 [reference_logits.cpp](../tools/v027/reference_logits.cpp) 直接链接该目录已有的libllama/ggml，以独立模型图执行完整读入。

参考库运行时标记为 `87b37ea-dirty`，当前唯一tracked脏文件是 `tools/server/server-schema.cpp`。本轮没有重建这些库，不能声明它们是从当前干净源码新构建的产物；以实际库SHA256冻结身份。自己的C++客户端编译命令、源码、二进制及全部库hash见 [reference-build](../workspace/combination/reference-logits-20261028/reference-build)，模型图/loader/context/header/CMakeCache快照及源码状态另存 `reference-source/`、`reference-source-state.json`。运行中从自己的 `/proc/PID/maps` 核实5个实际加载的llama/ggml库hash及两个GGUF映射，见 `reference-long-ngl18-v1/loaded-library-map.json`。

两边读取同一对原始GGUF分片，不下载、不转换、不重新量化权重：

| 分片 | 字节数 | SHA256 |
|---|---:|---|
| 00001-of-00002 | 47039860096 | `219ea929900dfa9ef091f3aa473fdba6874b65fcb36526d7d851ac9e95856d15` |
| 00002-of-00002 | 28800138432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |

这些是P6全内容hash，本轮核对当前size/mtime不变，没有再做75GB全文件hash。实际架构 `qwen4exp`，48层、512专家/top10、词表248320；清单有1224张量，包含多种量化类型，文件名IQ3_XXS不代表所有张量均为该格式。Strata pack的 `conversions.json` 为 `tensors=[]`；144个gate/up/down专家张量的GGUF绝对偏移和类型逐一匹配native加载记录。见 [WEIGHT_IDENTITY.json](../workspace/combination/reference-logits-20261028/WEIGHT_IDENTITY.json) 与 `TENSORS.json`。

同源权重不代表中间计算逐bit相同。Strata保留int8 KV、resident20480、原专家缓存/MTP/profile及EXACT6；参考为FP16 K/V，18层GPU offload、其余CPU，batch/ubatch512、16线程，关闭MTP与MoE cache，PLE按需读取。参考没有Strata的专家缓存转换、服务前端或采样器。两条实现仍有GGML量化算法的共同来源，不能据此排除共享算法缺陷。布局、分块和KV格式不同，读入耗时不用于比较性能。

## 固定输入与采集位置

从P7已经核对的原始请求重新渲染，冻结实际int32 token IDs，不让参考重新应用模板、分词、加BOS或改提示。请求hash与P7 raw trace一致。每项保存输入文件hash、int32字节SHA256及消费端FNV；参考打印实际读入ID的FNV，native逐次GEN记录相应前缀FNV。

| 用例 | 完整输入token | int32 token序列SHA256 | 原gold | 冻结的实际七位前缀 |
|---|---:|---|---|---|
| literal短复制控制 | 63 | `2ac2dcc79f247d3df0b024a7976f16ddd51188ef0714d37772bac028a55e1910` | `6763216-000738` | `6763216` |
| 69632-prime | 69616 | `1ed7173ce27f28bdd2f1cc71e882ab6244008a687e1fda68c5c568d4709bab95` | `6763216-000738` | `1751936` |
| 102400-prime | 102392 | `5befd14dd87a5aa37371b9d61ced69e0a0aa3e1f0b745039a29363387b2f65a6` | `2390975-001086` | `6395887` |

每边每项8行完整FP32 logits：step0为prompt最后位置；step1～7依次强制追加实际Strata七位数字，再求下一token。每行248320值，每份文件7946240字节。重点比较首个错位数字，以及七位数字之后的EOS248046、另一停止token248044、连字符12。

这是条件logits对照；若参考在任一位置argmax不同，后续行仍条件于原Strata前缀，不能串成参考自由生成答案。原HTTP请求的gold、评分和六项FAIL均保留，诊断退出码0只表示采集完成。

## 已完成结果

63-token资格控制的8个argmax全部一致，为 `6763216-` 的8个字符；这8行没有继续生成后缀，完整复制通过复用P7证据。数字后连字符均排名1：参考相对EOS高9.9542 logit，Strata高9.8476。两边可以正常选择连字符，不存在token映射或dump形状错误。

68K的8行argmax全部相同，依次为 `1751936`、EOS248046。独立参考重现偏前两行的错误数字和提前结束。首数字及末尾的具体排名：

| 位置/实现 | 错误首位排名/概率 | 正确首位排名/概率 | 错误−正确logit | EOS排名/概率 | 连字符排名/概率 | EOS−连字符logit |
|---|---|---|---:|---|---|---:|
| 68K首位1对6/参考 | 1 / 22.3022% | 8 / 6.0661% | +1.3020 | — | — | — |
| 68K首位1对6/Strata | 1 / 31.6681% | 9 / 3.4125% | +2.2279 | — | — | — |
| 68K七位后/参考 | — | — | — | 1 / 99.7590% | 2 / 0.2123% | +6.1524 |
| 68K七位后/Strata | — | — | — | 1 / 99.4666% | 2 / 0.4727% | +5.3491 |
| 100K首位6对2/参考 | 1 / 35.4439% | 6 / 4.9232% | +1.9740 | — | — | — |
| 100K首位6对2/Strata | 1 / 47.6935% | 3 / 10.6806% | +1.4964 | — | — | — |
| 100K七位后/参考 | — | — | — | 1 / 97.3698% | 2 / 2.5988% | +3.6235 |
| 100K七位后/Strata | — | — | — | 1 / 93.5645% | 2 / 6.4006% | +2.6823 |

概率是完整248320-way logits的稳定softmax，用于描述排序；不改temperature或原评分。另一EOS248044在68K七位后排名参考47/Strata27，100K为26/25，均不是最终选择。

100K的8行argmax也全部相同，独立参考重现偏后一行的 `6395887` 和提前结束。两项的每一步参考argmax均等于所强制的下一数字，最后均等于EOS；因此这两条条件轨迹也自洽地构成各自的greedy失败路径。没有用teacher forcing掩盖任何分叉，也没有重跑原六题把结果改成PASS。

完整top20、跟踪ID排名/概率、两实现全词表差值、去常量偏移RMSE、KL见 [qualification-analysis.json](../workspace/combination/reference-logits-20261028/qualification-analysis.json)、[long-analysis.json](../workspace/combination/reference-logits-20261028/long-analysis.json)。68K八行centered RMSE为0.1587～0.3011，100K为0.1485～0.2360；最大单项绝对差分别1.5143、1.8970。两项KL(reference||native)最大分别0.0480、0.1358。logits并非逐bit相同，top1一致只覆盖这些输入和位置，不等于所有token的数值正确性。

## 归因边界与下一步

68K/100K的错误首位在参考中均排名1，正确首位仅第8/第6；EOS相对连字符有6.15/3.62的优势。即使参考没有Strata服务层、MTP、专家缓存路径，并改用FP16 KV，仍出现相同失误。因此Strata独有实现或int8 KV不是这两个错误模式的必要条件。结合P7的原提示/明确格式/low thinking对照，现有证据更支持当前量化模型在长表与none提示组合下的检索和格式遵循失败。

仍不能拆开基础模型、该量化权重和共享数值算法。没有运行未量化或更高精度的同源checkpoint，也没有逐层张量parity。参考库不是本轮干净重建，KV精度、执行后端与prefill分块均不同；这些是数值差异的候选来源，不能把差值直接判成某个Strata kernel错误。

下一项最小验证若需分离量化与基础模型，应先确认**同一模型revision、同一GSQ-RCO处理、相同tokenizer和架构的更高精度权重**可用，再在同一参考图上只跑两个原prime的首位和七位后logits，比较排名是否改变。若更高精度通过而当前GGUF失败，才进一步分层定位量化影响；若两者同错，再归入该模型/原提示组合的能力问题。不能用另一个模型、另一个微调或截短上下文来替代这个对照。该权重变更实验本轮未执行。

本轮到此停止，不扩展逐层排查；当前没有某个Strata独有算子导致这两条错误的差分证据。若后续出现参考严格成功而Strata失败的相同权重样本，先对齐FP16 KV与prefill分块，再只抓首个分叉位置的层输出，避免把精度或分块差异直接当kernel缺陷。该控制本轮未执行。

当前不修改EOS处理、提示默认值或ISA门控；原六FAIL、P6正确性门FAIL及DEQUANT_SIDE未运行状态不变。不建立升级采用、性能改善或任务质量非劣结论。

## 验证与复现

新工具为 [run_reference_logits.py](../tools/v027/run_reference_logits.py)、C++客户端、[analyze_reference_logits.py](../tools/v027/analyze_reference_logits.py)，测试 [test_reference_logits.py](../tests/test_reference_logits.py)。工具测试本机与29各5项通过，覆盖截断/非有限logits、并列排名、稳定softmax/KL、输入hash漂移、native emitted/argmax及原失败锚点。

首次资格分析把短复制控制末位也假定为EOS，被锚点校验拒绝；控制实际正确选择连字符。分析工具已区分control的连字符与原prime的EOS，并补对应回归检查，没有重跑模型或更改失败锚点。见 `analysis-correction.json`。未使用NumPy依赖或安装新框架。

根仓库 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` 本轮全部exit0，日志在本轮raw的 `local-verification/`，保留既有Phaser chunk提示。未重跑P6的402项服务测试、全量native parity或lab selftest；原生及六文件port身份按冻结hash复核。

实验包根复现入口如下。每次必须使用新输出名，已有目录拒绝覆盖；保持单GPU串行和原131072总预算/4096预留。reference仅链接本轮已冻结的29库，其他版本不能当本次复现。

```bash
REF_PY=/home/hhtele/strata-0.1.43.1/.venv/bin/python
REF_TASK=workspace/combination/reference-logits-20261028
$REF_PY -B tools/v027/run_reference_logits.py --mode native --suite qualify --name native-qualify-new
$REF_PY -B tools/v027/run_reference_logits.py --mode reference --suite qualify --name reference-qualify-new --ngl 18
# 先用analyze_reference_logits.py核对短资格；通过后才运行long。
$REF_PY -B tools/v027/run_reference_logits.py --mode native --suite long --name native-long-new
$REF_PY -B tools/v027/run_reference_logits.py --mode reference --suite long --name reference-long-new --ngl 18
$REF_PY -B tools/v027/analyze_reference_logits.py --task "$REF_TASK" \
  --reference "$REF_TASK/reference-long-new" --native "$REF_TASK/native-long-new" \
  --case prime-69632 --case prime-102400 --output "$REF_TASK/comparison-new.json"
```

## 资源、保护和归档

四个阶段均完成、退出码0，合计1161个资源样本，无abort；峰值72°C/23640MiB，最低MemAvailable10443MiB。四个拥有的PID均退出，GPU1MiB/50°C、无计算进程，18089可绑定。生产保持inactive/dead/enabled，13个保护文件hash不变。native/六文件port、参考客户端/库/源码快照均核对未变，模型size/mtime未变。见 [FINAL_PROTECTION.json](../workspace/combination/reference-logits-20261028/FINAL_PROTECTION.json)。没有启动生产、写入生产、修改systemd、安装依赖或部署。

旧P6原182个raw文件、P7原373个raw文件及P3冻结输入逐一核对不变，见 [PRIOR_EVIDENCE_CHECK.json](../workspace/combination/reference-logits-20261028/PRIOR_EVIDENCE_CHECK.json)。本轮raw双端完整性回执见 `RAW_MANIFEST.json` 与 `REMOTE_RAW_INTEGRITY.json`；包MANIFEST覆盖211个交付文件。未提交、推送或创建PR，范围外已有工作区修改保持原样。

raw目录：29 `/home/hhtele/strata-lab-4090/workspace/combination/reference-logits-20261028`；本地 [workspace/combination/reference-logits-20261028](../workspace/combination/reference-logits-20261028)。只归档本轮证据、源码/库身份与自己的小型参考客户端，不复制模型或既有大型库。
