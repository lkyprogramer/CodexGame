# 六个长检索失败的根因诊断（2026-10-28）

**已定位直接失败机制：原无 thinking 请求在长表中选错邻行，或取对行后提前输出 EOS。** 六个 gold、请求和评分均无误；模板/tokenizer 没有丢失后缀，服务层没有截断连字符。关闭 MTP 后六项仍以相同正文失败；原措辞在冷读、长前缀复用时均失败，而明确完整字符串格式或启用 low thinking 的控制可以通过原来的严格 gold。

这些证据支持“当前量化模型在原提示与无 thinking 模式下的精确检索/完整字符串复制行为失败”，没有发现服务协议、缓存恢复或 MTP 接受错误。**尚未用独立参考实现分离模型参数、量化误差与共用数值内核，因此不把它扩大为基础模型能力不足或所有引擎内核正确的结论。** 原六项仍为 FAIL；P6 正确性门和 DEQUANT_SIDE 的未执行状态不变。

生产未改、未部署，未修改引擎或服务实现。13 个保护文件 hash 不变，生产服务 inactive/dead/enabled；8 个实验 PID 已退出，18089 可重新绑定，GPU 1 MiB / 43°C。见 [FINAL_PROTECTION.json](../workspace/combination/retrieval-rootcause-20261028/FINAL_PROTECTION.json)。

## 请求、gold 和输出核对

独立解析请求正文中的 `config-entry id=…; immutable_value=…;`，再从最后一条实际用户消息提取查询 ID；不使用生成器的映射表来替代正文核对。68K 表有1476条唯一记录，100K 表有2172条。六个 gold 都是对应 ID 的唯一原始字符串，七位数字、连字符、六位后缀均在实际输入中。

| 原请求 | 查询 ID / gold | 原正文 | 实际对应记录 | 直接错误 |
|---|---|---|---|---|
| 69632-prime | R000738 / `6763216-000738` | `1751936` | R000736 / `1751936-000736` | 偏前2行，且丢后缀 |
| 69632-restore | R000147 / `1046570-000147` | `1046570` | 查询行正确 | 丢后缀 |
| 69632-sampled | R001328 / `1747969-001328` | `1747969` | 查询行正确 | 丢后缀 |
| 102400-prime | R001086 / `2390975-001086` | `6395887` | R001087 / `6395887-001087` | 偏后1行，且丢后缀 |
| 102400-restore | R000217 / `3027054-000217` | `3027054` | 查询行正确 | 丢后缀 |
| 102400-sampled | R001954 / `5344683-001954` | `5344683` | 查询行正确 | 丢后缀 |

原请求没有自定义 stop、logit_bias 或输出 schema；max_tokens=64。六次都是8个生成 token、finish_reason=stop，未触及长度上限，也没有取消。prime/restore 保持 temperature=0；sampled 保持 temperature=1、top-p=.95、top-k=20、seed=20261027。

核对原始 SSE 与留存正文一致；本轮复测继续使用 P6 留存的实际历史 body，18 个原请求执行记录的 hash 均匹配相应原 body（含 side 与后续 warm 控制）。原 P3 FAILURE、corpus 和响应没有覆盖；P6 原归档182文件逐一复核不变。见 [original-case-audit.json](../workspace/combination/retrieval-rootcause-20261028/original-case-audit.json)、[PRIOR_EVIDENCE_CHECK.json](../workspace/combination/retrieval-rootcause-20261028/PRIOR_EVIDENCE_CHECK.json)。

## 代码与真实 token 链路

复用 P6 的 v0.2.7 隔离树和二进制 `58ffaf7f…269f22`，原生源码与六文件 #1536/PT 移植均未改变。以下源码快照保存在本轮 [source-evidence](../workspace/combination/retrieval-rootcause-20261028/source-evidence)：

- `serve/frontend.py:610` 起将 `reasoning_effort=none` 和 `enable_thinking=false` 处理为关闭 thinking；本轮六个渲染 kwargs 均只有 `enable_thinking=false`。PT 默认不会在这里注入，原历史也没有需要保留的 reasoning。
- `tools/strata_tokenizer.py` 与真实 GGUF tokenizer：六份完整 prompt 编码再解码逐字一致，完整 gold 均在渲染与解码文本中。连字符 token 为 **12**，停止 token 为 **248044/248046**，没有碰撞。完整 gold 本身不含停止 token。见各阶段 `rendering-audit.json` 与六份 `.rendered.txt`。
- `serve/server.py:4054` 的停止集合来自 `<|im_end|>`、`<|endoftext|>`；`5461` 起只在实际读到停止 token 时置 stop。`2311` 起直接读取原生 `T id`，`5756` 起的现有 `STRATA_DEBUG` 能记录 raw ids；本轮只启用此观测开关，原生源码中没有读取它的分支。
- `src/program/generate.cpp:16719` 起输出 verifier 计算路径的 token，再检查 EOS。不是由 HTTP parser 根据数字或连字符猜测结束。

六个原失败请求的 raw 文本均为 **七位数字＋`<|im_end|>`**，末尾 ID=248046，raw token数与usage均为8；raw在EOS前的内容与SSE正文完全相同。也就是说，**目标解码路径选中了EOS，服务正常结束，没有生成后再被丢弃的连字符/后缀。** 完整值可以在同一链路输出为14个可见字符＋EOS、共15个token。

## 最小对照及结果

三个完成阶段共27请求。所有控制仍使用原完整字符串 gold 和同一 exact 评分器，没有前缀匹配、类型转换或补齐后缀。改过输入的控制单独标记，不能替代原请求的失败判定。

| 对照 | 保持项 / 唯一目的 | 观察结果 |
|---|---|---|
| 原六项＋两个side，开启 raw trace | 原body/gold/采样；另固定共同专家缓存预算 | 六项同错，两个side正确；raw均证实原生EOS |
| 直接复制literal，63 token输入 | 直接把gold写入指令；只验证复制与输出链路 | 完整 `6763216-000738`，15 token，PASS；不能当检索能力通过 |
| 短表、原问题，1298 token输入 | 保留25条被查询记录及邻行，原最终问题和gold不变 | 完整 `6763216-000738`，PASS；仅说明上下文缩短后的控制通过 |
| 原68K表＋明确完整字符串要求 | 不提供答案，只追加“包括连字符和六位后缀” | 原先warm控制PASS；另补cold控制，避免缓存混杂 |
| 原68K/100K表＋low thinking，冷读 | 同一查询及gold；为thinking留1536输出上限、512 reasoning预算 | 两档均PASS；总输出121/114 token，未达到thinking预算；reused均0 |
| MTP关闭、suffix draft关闭 | 同权重、body、gold、KV、共同缓存；实际目标解码T=1 | 六项正文与开启组逐字相同，全部FAIL；9请求drafts_offered总和为0 |
| 明确完整格式，68K/100K冷读 | 原完整表、none、max64；只追加格式要求 | 两档均PASS，reused=0，生成均15 token |
| 随后恢复原措辞、复用长前缀 | 原body/gold/none/max64 | 仍分别为 `1751936` / `6395887`；reused65536/98304 |

冷格式控制的实际prompt为69649/102425 token，cold原请求为69616/102392；差额为追加格式要求。cold格式控制全量读入时已能成功，原问题在warm路径又失败，排除了“格式控制只是因为命中前缀缓存才碰巧正确”的解释。thinking控制也均为冷读，正文分别是原完整 gold；它们是本模型/量化/引擎组合在这些长度上能够正确取值的具体见证，不是正式质量非劣证明。

### MTP与容量控制

原生native IQ路径要求 `--spec>=2`（`generate.cpp:4347`），不能直接用spec0或删资格检查来伪造关闭组。源码 `9255`、`16426` 支持保留verifier窗口能力但不加载MTP；同时关闭suffix draft后，目标每轮单token解码。本轮由单独冻结的 `config-no-mtp.json` 去掉MTP，未修改通用PR包装器中冻结MTP的护栏。实际引擎argv无 `--mtp`，suffix=0，所有请求offered/accepted drafts均0。

为避免MTP移除后自动扩大专家缓存，两臂共用 `--expert-cache 6000` 的字节预算，实测均为 **8053 slots**、同一profile排序；KV保持int8/resident20480。这是诊断公共设置，区别于P6的auto/10272 slots。原六项在8053和P6的10272槽下正文相同；不能把本轮耗时当作当前生产配置的性能对比。

首次误把expert-cache参数当成实际槽数，10272的请求值最终得到10386槽，被启动校验拦在发请求前。源码 `generate.cpp:7003` 起表明，混合格式会按最大槽字节预算、profile实际blob尺寸及可用显存重新计算容量。因此改用两臂都能完整容纳的较小公共预算，并核对实际槽数相等。首次失败目录 `trace/`、原驱动及预登记修订保留。另一次no-MTP启动前被通用PR护栏拒绝，随后使用独立诊断输入配置，未削弱护栏。见 `PREREGISTRATION-AMENDMENT-1/2.json`。

## 归因与尚未证明的边界

| 层次 | 本轮可支持的判断 |
|---|---|
| 请求/gold/评分 | 正确、完整、绑定同一行；不是错误gold或评分截取造成的FAIL |
| 模板/tokenizer/HTTP/SSE/stop处理 | 输入逐字往返正确；可输出完整值；原生实际EOS后结束。未发现这些层截断后缀 |
| #1536/PT与会话恢复 | 原none渲染不受PT默认影响；两个prime在reused0时已失败，故恢复不是必要成因；warm原措辞仍失败 |
| MTP接受/lookup | 完全无草稿时六项同错，故不是这些错误的必要成因 |
| 专家缓存容量 | 两个已验证容量下六项同错；MTP对照实际槽数相等，未用自动扩容混入结论 |
| thinking/提示配置与输出行为 | 原none提示在长表上误取邻行并早停；更明确格式或low thinking能得到严格正确值。属于条件相关的检索/格式遵循失败 |
| 模型参数、低比特量化、共用数值内核 | 尚未独立拆分。没有同token、同权重的独立参考推理结果，不能认定基础模型固有缺陷，也不能证明所有数值内核无误 |

旧P3在A0上已有KVRES0与20480均同错的独立证据。本轮复用该事实，没有再改KV格式或驻留方式；它不替代v0.2.7的KV逐bit参考验收。当前证据不支持把问题归因于v0.2.7新增回归，也不支持修改内核或放宽EOS处理来“修复”评分。

**原六个测试保持FAIL。** 控制通过没有使原题变成PASS，没有改生产提示或开启thinking默认值，也没有进入DEQUANT_SIDE实验、升级采用或性能门。

若必须进一步分离权重/量化与共用数值实现，下一项最小验证应是一条独立目标logits对照：固定69632-prime的完整token输入，以及实际生成的七位数字前缀；比较首个错位数字、数字后EOS与连字符12的排序。参考实现需真正支持该模型和相同权重/token，不能把本轮同一引擎的T=1路径当独立oracle。本轮未运行此项，也未下载/安装其他模型或推理框架。

## 验证、资源与归档

- 新诊断工具 `tools/v027/diagnose_retrieval.py`，新增 `tests.test_retrieval_diagnosis` 本机/29各3项通过；覆盖gold与字面记录绑定、冻结body不可改、控制不改原请求/gold。最终29日志为 `unit-tests-final-29.log`。
- 27份原始SSE重解析、raw token数与usage、预算检查全部一致；18个原请求记录的body hash与完整gold、9个修改控制的完整gold均复核通过。无MTP九请求的draft计数均0。见 [LOCAL_INTEGRITY_CHECK.json](../workspace/combination/retrieval-rootcause-20261028/LOCAL_INTEGRITY_CHECK.json)。
- 三个完成阶段分别13/9/5请求，退出码均0只表示诊断编排完成，原答案失败仍完整保留；evidence final audit均PASS。未重跑原服务层402项，复用源hash未变化的P6通过证据；未运行全量native parity/lab selftest。
- 本轮根仓库 `pnpm typecheck`、`lint`、`test`、`test:integration`、`build` 全部exit0，日志在本轮raw的 `local-verification/`；保留既有Phaser chunk提示。
- 三个完成阶段共361个1秒级样本，无abort；最高75°C/19976MiB，最低MemAvailable6192MiB。初次预检失败阶段另存遥测，不混入该表。没有建立持续热稳态、频率或性能改善结论。
- 生产13个保护hash、旧P3输入、P6原182文件不变；4份临时key移除，实验服务/引擎退出，GPU及18089释放。没有提交、推送或部署。

raw目录：29 `/home/hhtele/strata-lab-4090/workspace/combination/retrieval-rootcause-20261028`，本地 [workspace/combination/retrieval-rootcause-20261028](../workspace/combination/retrieval-rootcause-20261028)。保留每阶段command/源码hash、v1/v2/v3诊断源码、原始请求/SSE/响应/raw ids、渲染文本、native源码快照、实际PID内存与保护回执。构建/模型复用P6冻结身份，没有重新编译引擎。

复现入口在实验包根；每次使用新输出名，不能覆盖本轮目录：

```bash
LAB_PYTHON=/home/hhtele/strata-0.1.43.1/.venv/bin/python
DIAG_TASK=/home/hhtele/strata-lab-4090/workspace/combination/retrieval-rootcause-20261028
V027_TASK=/home/hhtele/strata-lab-4090/workspace/combination/v027-20261028
P3_TASK=/home/hhtele/strata-lab-4090/workspace/combination/kvres-20261027
$LAB_PYTHON -B tools/v027/diagnose_retrieval.py --config "$DIAG_TASK/config.json" \
  --prior "$V027_TASK" --old "$P3_TASK" --phase trace --name trace-new
$LAB_PYTHON -B tools/v027/diagnose_retrieval.py --config "$DIAG_TASK/config-no-mtp.json" \
  --prior "$V027_TASK" --old "$P3_TASK" --phase no-mtp --name no-mtp-new
$LAB_PYTHON -B tools/v027/diagnose_retrieval.py --config "$DIAG_TASK/config.json" \
  --prior "$V027_TASK" --old "$P3_TASK" --phase format-cold --name format-cold-new
```

no-mtp阶段会核对本轮已冻结 `trace-v2/activation.json` 中的实际槽数；不是自动创建一轮新的统计配对。未把任何诊断控制当正式请求性能、任务完成率或质量非劣门。

双端归档 **373个证据文件**逐一SHA256校验通过，见 [REMOTE_RAW_INTEGRITY.json](../workspace/combination/retrieval-rootcause-20261028/REMOTE_RAW_INTEGRITY.json) 与 `RAW_MANIFEST.json`；包MANIFEST为206文件。既有其他工作区修改保留，范围内文档、新工具及链接检查通过。
