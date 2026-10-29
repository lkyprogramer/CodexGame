# v0.2.7 Ada MMVQ差量资格核查（2026-10-28）

**完成：NO_BENEFIT_SCREEN；停止在关闭态资格检查。** 本轮限定的8个新版表差量已命中。将其MMVQ及全部quant/interleave支持成本都乐观删除、保持其他工作耗时不变，本次profiled完整请求中的条件空间为 **2.764% / 2.003%**，低于预登记4%请求门参考。首末输出观测区间对应 **3.084% / 3.240%**。未开启`STRATA_MMVQ_IL_89=1`，未进入单shape候选、parity或配对性能测试。

该结论仅限本次差量与两个样本的条件模型。profiler扰动明显，两次生成轨迹也不同；不能将这些比例当作未插桩环境的严格上界、实际加速或全部Ada表无收益的证明。原六项FAIL、P6正确性门和评分保持。生产未改、服务保持停机，未部署。

## 固定身份与原始输入

通过用户指定的`jssh 29`访问。实际`~/.zshrc`中的函数为`ssh -J jump "$@"`，本轮沿用该跳板路径；没有使用直连29。

复用P6隔离树`5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`、原生SHA256`58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`和六文件#1536/PT移植。完整模型、EXACT6、KVRES20480、int8 KV、spec4、线程布局、CPUSHARE4096、AUTOMAX16384、131072上下文及4096预留均保持。实际引擎环境确认IL89=0、SIDE=0；未编译或改动Strata原生实现。

输入直接取P3冻结`performance-corpus.json`，每个请求在新引擎上运行。没有缩短body、修改采样参数或放宽长度约束：

| 请求 | 原body SHA256 | 实际prompt/reused/read | 输出 |
|---|---|---|---|
| `think-4096` | `239048ab86191d053dc1d3717d40daefa292fb6c2fb34133aacd6103fdf79303` | 4095 / 0 / 4095 | 2048 |
| `think-102400` | `70bca1817c37adeacd59038f25b6a5d622efa3163497ee54b0719cddb3f9c563` | 102400 / 0 / 102400 | 2048 |

temperature1、top_p.95、top_k20、seed20261027、xhigh不变。两题各profile一次、无nsys控制一次，共4请求/8192输出token，均满足原2048长度要求。`performance completion`仅表示性能样本完成，不是任务质量PASS。请求内部的续算段包含在完整响应范围，未用最后一段引擎日志替代总耗时。见[cases.json](../workspace/combination/ada-delta-20261028/cases.json)、[预登记](../workspace/combination/ada-delta-20261028/PREREGISTRATION.json)。

## 实际差量与源码核对

从当前权重清单的776个2D张量得到43种shape，逐T1…8共344个单元。base→新版表改变17个单元，涉及100个tensor×T。其中9个新版rows与旧IL89已测候选相同，8个不同，**这8个全部退回plain(rows=0)**：

| dtype | n_in→n_out | T |
|---|---|---|
| Q4_K | 6144→2560 | 3、4 |
| Q5_K | 2560→10240 | 4 |
| Q5_K head | 2560→248320 | 4 |
| Q5_K | 6144→2560 | 3、4 |
| Q6_K | 2560→6144 | 4 |
| IQ4_XS | 6144→2560 | 4 |

“新差量”指不同于旧IL89候选的表组合，不表示新的数学kernel：旧IL0已经测试过全局plain。Q3_K单列新增没有当前权重覆盖；Ada T5…8没有新表。完整base/new/old rows、张量清单及分类见[INVENTORY.json](../workspace/combination/ada-delta-20261028/INVENTORY.json)。

另外只读比较生产旧源码与固定v0.2.7源码，确认共同IL、多列、quant/interleave、Q4/Q5/Q6/IQ4_XS plain核函数体，以及原Il*.apply函数体保持相同。IL函数体SHA256为`9271d38aca7b999948bfa922856cf14d5dc8ee96167c39a7abe4b3501619cafc`，multi为`75a6fd0250b1214ced1162b36df86ddf563c3579394e388d84de8187b388940d`。

新增PF分支默认0，sm80 PF表不用于sm89；保存的运行env与启动白名单未启PF，实际trace没有PF kernel。旧结果仍只是历史先验：新增host分支和二进制布局不能仅靠函数体相同排除性能变化。源码快照见[source-evidence](../workspace/combination/ada-delta-20261028/source-evidence)。

## 采集与成本

29已有Nsight Systems2023.3.3，CUDA/NVTX及graph-node trace。只给客户端增加请求范围、首输出和逐输出事件标记，沿用原SSE分类，role/progress不算输出。短/长分别2027/2009个输出事件标记，不能当成token数；实际completion_tokens均2048。

分析以PROCESSES绑定实际engine PID，kernel模板和grid反查dtype/T/n_out/rows，n_in无法直接恢复时保留所有匹配张量的超集。两份trace均OBSERVED，实际rows与base不符为0，剩余未知MMVQ为0。不能从缺失关联推导无命中：本轮候选关联到graph launch，未重建逐节点依赖关系。

排除项逐kernel保留原因：精确模板证明是Ada表不支持的type8/20/42/21，或明确T1、T5…8/无变化单元。初版分析将这些项留在unknown；`short-analysis-v1.json`完整保留，最终采用有源码依据排除的v2结果。QSA采用实际block_scores/topk/attention符号集合归类，未因名称不含`qsa_`就记零。

| 区间 | 4K短请求 | 100K长请求 |
|---|---:|---:|
| trace完整请求 | 25.015秒 | 49.428秒 |
| 首末输出观测区间 | 21.971秒 | 21.034秒 |
| 该观测区间的新差量MMVQ并集 | 273.586ms | 322.759ms |
| 全部quant/interleave支持成本超集并集 | 404.042ms | 358.732ms |
| 新差量＋支持成本并集 | 677.627ms | 681.491ms |
| 条件空间/首末输出区间 | 3.084% | 3.240% |
| 完整请求的新差量＋支持成本并集 | 691.519ms | 990.245ms |
| 条件空间/完整请求 | 2.764% | 2.003% |

所有比例使用区间并集，不把重叠kernel累计时间直接当墙钟收益。支持成本故意包含全部quant/interleave，未声称这些工作都由差量shape独占或能被删掉。首末输出区间不含首token计算及最终响应尾部，亦不等于完整verify窗口集合。

同时保留全部17个表变化的账：其MMVQ加全支持成本，在短/长首末输出区间分别1088.268/987.250ms，约4.953%/4.694%。这不能算成8个新差量的空间，也不能用本轮结论证明全表开启无收益。QSA超集在decode区间约499.754/1057.941ms，GPU wait约2010.323/2317.068ms；这些分类互相关系未构成因果关键路径，不据此启动另一优化。

## 测量限制与停止决定

| HTTP观测 | profile短 | control短 | profile长 | control长 |
|---|---:|---:|---:|---:|
| 完整请求秒 | 25.012 | 18.632 | 49.425 | 43.712 |
| 聚合decode毫秒 | 21873.7 | 15243.2 | 20922.7 | 15901.5 |
| 实际专家槽数 | 10264 | 10272 | 10264 | 10272 |

两组均全程IL89=0。输出长度相同，但生成内容、草稿接受数和轨迹不同；单次控制不能因果量化profiler开销，也不是off/on收益。采集时的槽位差异不来自开启候选。短trace回传与长profile部分时段重叠，增加了观测环境限制；控制仍只作诊断，不能当正式性能配对。

跨运行把profiled完整候选成本除以control完整请求时间，仅作敏感性诊断，为3.711%/2.265%；它不能建立同token、未插桩上界。尤其短样本profiled候选成本除以control的decode时间会超过4%，所以**不能推广为正常长输出decode严格不足4%**。本轮停止是预登记两请求条件模型下的有限筛查决定，不是实际无收益证明。

按既定范围不重跑9个旧候选，也不继续开启新表。单shape微测、开启路径parity、固定token logits、真实请求配对及任务质量采用验证均NOT_RUN；原六项FAIL未豁免。详见[SUMMARY](../workspace/combination/ada-delta-20261028/SUMMARY.json)、[DECISION](../workspace/combination/ada-delta-20261028/DECISION.json)。

## 验证与交付

- 新增[trace_ada.py](../tools/v027/trace_ada.py)、[ada_inventory.py](../tools/v027/ada_inventory.py)、[analyze_ada.py](../tools/v027/analyze_ada.py)及三个定向测试模块。本机与29最终各16项通过；覆盖冻结表解析、SSE标记恢复、区间并集、缺trace/关联、rows不符传播及非候选排除。
- 根仓库`pnpm typecheck/lint/test/test:integration/build`本轮全部exit0。未重跑P6服务402项、全量native parity或lab selftest。独立评审只读检查源码和实际short SQLite，未发现material finding；reviewer未SSH、运行模型或执行测试。
- 四阶段257个资源样本，无abort；峰值71°C/23784MiB，最低MemAvailable7361MiB。12个driver/server/engine PID均退出，两次profiler结束；GPU1MiB/43°C且无计算进程，18089可绑定。
- 13个生产保护hash与P6原生/六文件port不变，P6/P7/P8/P9/P10共922个旧raw文件hash不变，4份临时key已脱敏。权重size/mtime仍匹配P9全内容hash身份。见[FINAL_PROTECTION](../workspace/combination/ada-delta-20261028/FINAL_PROTECTION.json)。

原始证据在29`/home/hhtele/strata-lab-4090/workspace/combination/ada-delta-20261028`及本地同名[raw目录](../workspace/combination/ada-delta-20261028)。保留请求、SSE、响应、env/argv、SQLite/nsys-rep、源码快照、初版/最终分析及双端校验回执。实验包MANIFEST为224文件。没有提交、推送、改生产或部署，未修改范围外已有内容。

复算（输出必须新建）：

```bash
python3 -B -m unittest tests.test_ada_trace tests.test_ada_inventory tests.test_ada_analysis -v
python3 -B tools/v027/analyze_ada.py \
  --trace workspace/combination/ada-delta-20261028/short-profile-v1-trace.sqlite \
  --inventory workspace/combination/ada-delta-20261028/INVENTORY.json \
  --run-folder workspace/combination/ada-delta-20261028/short-profile-v1 \
  --output workspace/combination/ada-delta-20261028/analysis-new.json
```
