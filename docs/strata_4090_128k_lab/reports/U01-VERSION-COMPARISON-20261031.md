# U01 · v0.2.3与无HC v0.2.7限额对比

结论：**执行INCOMPLETE，版本比较INSUFFICIENT；不建议据本轮进入完整升级验收或切换生产。** 预登记3组/12请求，实际在第一组A臂完成2次请求后，因本地token计数与服务端usage不符触发基础设施停止条件。剩余10请求NOT_RUN，B臂v0.2.7未启动；没有重试、替补或追加生成请求。

这次失败来自本轮执行器遗漏计数进程的PT0环境，不能归因于v0.2.3或v0.2.7。原v0.2.3两题评分均通过，但没有有效版本配对，不能据此比较两版性能或成功率。原生产已自动恢复，13项保护文件SHA全部匹配。

## 合同与实际执行

用户授权使用jssh 29，临时停生产，最多半天、3组配对、12请求，冻结配置/评分、不启其他优化，失败保留、不补样本，结束恢复原生产。[本轮合同](../plans/U01_VERSION_COMPARISON.md)与远端PREREGISTRATION在停生产前冻结。固定顺序A→B、B→A、A→B，每臂独立进程/引擎，依次执行schema-boolean和seed43原编码末轮；不另发送生成探针。

A为P3隔离树，二进制SHA256 `819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d`，与生产一致；B为无HC P6，SHA256 `58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22`。两臂归一化runtime除exe/cwd/log/临时key外完全相同。P6原生tag及六文件reply/PT port、两版二进制、原资产metadata/路径集合、共享harness和原受限Docker评分镜像均已核对。

维护监督器于2026-10-31 **16:23:35北京时间**启动，原服务停止并释放GPU后，计算以hhtele身份运行。实际只启动1个实验引擎，发送2个HTTP生成请求。外层维护上限10800秒、恢复预留300秒，没有耗尽时间预算。

## 原始结果：只描述A臂，不能做版本比较

| 第一组A：v0.2.3 | 实际输入token | 输出token | 完整请求wall | 原评分 |
|---|---:|---:|---:|---|
| schema-boolean | 324 | 30 | 1.7050s | PASS，schema与值严格匹配，未执行工具 |
| seed43-final-original | 4408 | 25846 | 193.8404s | PASS，受限Docker累计8项全部通过 |

两个body均与原冻结hash完全一致。编码保留原16条历史、seed43、xhigh、temperature1/top_p0.95/top_k20和32768输出上限；没有修改生成代码或评分。8/8表示单个末轮产物的8项检查，不表示新八轮任务完成率。

这说明旧生产版本也能通过此前两个正向样本，与“单次新版通过不能证明版本改善”的判断相符；它不能估计间歇失败率。没有B臂数据，不能给出新版更好、更差或相同的结论。耗时保留原聚合计时设置，只有单臂观察，不是正式性能结果。

## 中止原因与CPU核对

执行器对每次请求保存原SSE、响应、评分、usage及资源后，调用原usage验收。编码评分完成后报`USAGE_DRIFT`：

| 计数条件 | 同一编码请求的prompt token |
|---|---:|
| 本轮worker的本地计数，PT环境缺失 | 44108 |
| 实际服务端，PT=0 | 4408 |
| CPU离线重渲染，显式PT=0 | **4408** |
| CPU离线重渲染，显式PT=1 | 44108 |

源码中的frontend根据进程环境注入preserve_thinking默认值。本轮服务环境正确为PT0，但创建本地StrataCounter的worker没有继承该默认值，因而计算了原历史thinking；这是本次适配遗漏。布尔题本地316/服务324，相差8，在原32-token容差内，不能用它证明含历史thinking的计数正确。

本轮执行源码和失败目录原样保留，执行器SHA256为`9b8b308fc873594d99eb576151d7ff91078924afeb940ca51031caa0ca2b8bac`，与预登记一致。没有事后修改原run的计数、验收或状态。COUNTER_DIAGNOSIS仅在已执行请求上做CPU重渲染，GPU不可见，不产生新HTTP生成。

本地公开执行器随后增加最小修正：在创建计数器前，从实际server.cfg同步STRATA_REPLY_REUSE与STRATA_PRESERVE_THINKING两个默认值。修正后的脚本未在本轮GPU执行，也未覆盖远端已执行脚本；不能将修复写成原run通过。重新发任何请求都应属于新合同，当前不执行。

## 资源、恢复与保护

实验护栏113样本，无abort；最高74°C，MemAvailable最低10944MiB，没有触发85°C/4096MiB门。该短窗口不证明长期稳定性。

监督器在实验退出、GPU释放后自动启动原openclaw-qwen38-next.service。**16:29:12北京时间**恢复为active/running/enabled，NRestarts0，health loaded=true、status=ok，模型openclaw/Qwen3.8-next、max_context131072；13项生产保护SHA与停机前完全相同。维护监督器从启动到恢复约336秒。

**16:30:59北京时间**再次只读确认：上述生产状态和health保持，GPU23598MiB/43°C，唯一compute为生产v0.2.3 native PID2417347；实验18089无监听。未替换生产二进制、修改配置/权重/systemd或升级引擎，Pi默认模型保持next。

## 验证与交付边界

- 执行前：既有tests.test_v027_baseline五项本地PASS；新执行器及监督脚本远端Python语法检查PASS。没有把这些检查当完整新执行器验收。
- 执行后：同一请求CPU三种PT条件重渲染完成，PT0与服务usage精确相等；本地修正版仅语法/文档检查，无GPU重跑。
- 本地原件`workspace/combination/version-compare-20261031/raw/`：38项文件、11320294bytes逐长度/SHA核对PASS；压缩包SHA256为`298168507bac43bec6f1b657a5ebb2cd8ae9ec978ecfb5a15cb5d16744f8a2e3`。另保存执行源码、预登记、原请求/SSE/响应、评分、环境、内存/护栏、CPU诊断和生产恢复回执；临时私有runtime不导出。
- 本地包与链接检查另记该workspace的PACKAGE_CHECKS.json。无游戏runtime/protocol改动，不运行无关pnpm全仓检查。历史报告和所有失败保持，原始证据只保留本地，不自动提交或push。

## 是否继续升级验收

**本轮没有足够依据进入完整升级验收，更不能直接切生产。** 原两个正向结果在旧版这次也出现，尚未建立版本优势；本次还缺全部B臂与后续配对。执行失败不构成新版无益或存在回归的证据。

当前到此停止，保留2次实际请求和10次NOT_RUN。只有用户后续明确要求新的限额版本对比时，才使用已修正适配重新登记；不能在本轮补样本。Astra/frontier零候选、F02暂缓、F03关闭、六项历史FAIL和P05 BLOCKED_EVIDENCE均不改变；生产保持原v0.2.3运行。
