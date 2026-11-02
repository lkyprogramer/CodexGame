# U01R1 · 修复计数后的v0.2.3 / 无HC v0.2.7对比

结论：**计数问题已修复，新一轮执行COMPLETE；不建议继续完整升级验收或切换生产。** 按固定顺序完成3组配对、6个实验引擎、12个生成请求，无重试、无替补、无追加生成探针。v0.2.3为6/6通过，v0.2.7为5/6通过：两版编码均3/3通过，v0.2.7仍有一次工具布尔类型错误。编码请求耗时两组变慢、一组变快，没有稳定升级优势。

原v0.2.3生产已恢复，health loaded=true、服务active/running/enabled，13项保护SHA全部匹配。当前维持原生产。这里是两个固定case/seed的三次重复筛查，不是总体质量、正式非劣或版本性能统计证明。

## 修复与预检

[U01上一轮](U01-VERSION-COMPARISON-20261031.md)的2请求、10个NOT_RUN、原执行源码及USAGE_DRIFT终态保留。本轮按用户随后“修复问题并重新测试”的授权建立独立run_id：version-compare-20261031-r1，不把旧A臂样本并入新配对。

修复位置为tools/v027/compare_versions.py：make_counter在创建CPU计数器前，从实际runtime同步STRATA_REPLY_REUSE与STRATA_PRESERVE_THINKING，prepare与worker共用此入口。预检按版本启动独立CPU进程，避免导入缓存混用frontend；worker在生成前再次核对预检计数。

- tests.test_version_compare三项及原tests.test_v027_baseline五项本地PASS，覆盖父进程PT1被runtime PT0覆盖、两项默认值取自runtime、已关闭campaign拒绝重放。
- 两版CPU预检相同：工具316 token；编码默认PT0与显式false均4408，显式true为44108，复现并排除上一轮的缺省环境错误。预检没有HTTP生成或GPU负载。
- 实际6个编码请求均为本地4408 / 服务usage4408，无USAGE_DRIFT；6个工具请求为本地316 / 服务324，相差8，沿用原32-token容差，没有放宽门槛。

本轮实际执行器SHA256为`0fcf6263f0499e9634a9511b5105f9bd11606810637a3c1d2d88463ab65fc3f9`，与预登记及归档执行源码一致。

## 冻结条件与实际数量

[本轮合同](../plans/U01R1_VERSION_COMPARISON.md)沿用U01的冻结输入、配置、评分和半天上限。A为与生产二进制SHA一致的v0.2.3隔离树；B为P6 v0.2.7原生及六文件reply/PT port，**没有HC scratch复用补丁**。原模型计算、权重、模板和EXACT6保持，不启其他优化。

归一化runtime除exe/cwd/log/临时key外完全一致；PT0、reply reuse、6144MiB/4slots、KV int8/resident20480、CPUSHARE4096、AUTOMAX16384、spec4及保守026设置保持。实际自动expert slots A为10290、B为10272，保留版本自然容量差异，没有调预算凑齐。沿用原聚合计时，不增加profiler或observer，因此本轮不作为正式无插桩性能试验。

顺序为A→B、B→A、A→B；每臂fresh engine，先schema-boolean，再原seed43编码末轮。两个body hash分别为`4dfe4679ae9b2d0ad8b23bbdf1a34859ac78381bea3f71e9306460ecdfb5f846`、`a9b8e7231a860ea2dff1f39b545c5baf66443f278f2786d5c880decd582541c7`，全部12项匹配。编码保留原16条消息及采样，不改变输出预算或评分；8/8仅指末轮产物的8项累计检查，未新跑完整八轮链。

原受限Docker镜像sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad保持；工具只检查schema和值，不执行。模型代码仅在既有受限容器评分，未在宿主执行。

## 正确性

| 请求 | v0.2.3三组 | v0.2.7三组 |
|---|---|---|
| 布尔工具参数 | PASS / PASS / PASS | **FAIL** / PASS / PASS |
| 编码末轮8项累计检查 | 8/8 / 8/8 / 8/8 | 8/8 / 8/8 / 8/8 |

第一组B返回`configure`参数`{"retries":0,"enabled":"False"}`，enabled是字符串，原要求为布尔false；原严格评分为tool name/arguments mismatch。该结果作为普通答案失败保留，后续按预登记继续，无重试或代码修补。

这说明先前新版单次通过的两个样本没有形成稳定新增能力：旧版本轮也全部通过，新版仍出现既有类型错误。三次重复不足以估计总体失败率，不能据此断言新版总体质量更差；同样不能据一次成功宣称问题已修复或正式质量非劣。

## 编码请求耗时：全部三对保留

| 组 | A wall秒 | A输出token | B wall秒 | B输出token | B/A耗时比 |
|---|---:|---:|---:|---:|---:|
| 1 | 124.077 | 16681 | 192.561 | 25785 | 1.551945 |
| 2 | 189.752 | 25976 | 157.123 | 20482 | 0.828044 |
| 3 | 192.914 | 25839 | 195.893 | 25797 | 1.015442 |

三对完整请求wall比的描述性几何均值为1.092769，即本次B用时约多9.28%；两版wall中位数分别189.752/192.561秒。没有剔除任何一组，不计算选择性子集的采用统计。

输入和评分固定，但生成长度/轨迹不同，因此这不是同token吞吐对照，不能说v0.2.7引擎吞吐下降9.28%。这里没有置信区间、显著性或稳定warm性能结论。工具题包含失败结果，耗时不用于宣称有效任务收益。

## 资源与生产恢复

维护监督器2026-10-31 **17:10:26北京时间**启动，**17:39:28**恢复原生产，窗口约29分02秒，未超半天。945个护栏样本无abort，最高75°C/23722MiB，MemAvailable最低10800MiB。实际6个唯一实验native PID、启动顺序、12份attempt及评分记录全部核对，未启动第7个引擎。

恢复回执为active/running/enabled、NRestarts0，health loaded=true、status=ok，模型openclaw/Qwen3.8-next、max_context131072；13项生产保护SHA全部匹配。

**17:40:23北京时间**最终只读核对：生产MainPID2443578，唯一GPU compute为生产v0.2.3 native PID2443599，GPU23598MiB/45°C；实验18089可bind，models含正确模型，NGINX未认证请求401。冻结harness最终SHA匹配，没有残留本轮实验native。生产配置、模型、Pi设置、驱动/CUDA/systemd均未修改，未升级部署。

## 归档与停止点

原件在workspace/combination/version-compare-20261031-r1/raw/，178项文件、62763641bytes，下载后逐长度/SHA核验PASS。压缩包SHA256为`59cf41cfc22174976a197e43c854bb776458be0512a2da8937da6265cf3ce376`。归档包含预登记、CPU预检、实际执行源码、请求/SSE/响应、原评分、身份/环境/护栏及恢复回执，不含临时私有runtime。

本地analyze.py独立重算全部三对描述性统计，核对6个唯一native、实际顺序、两版binary hash、12项请求hash和计数；输出ANALYSIS.json。包、链接和diff检查另记PACKAGE_CHECKS.json。无游戏代码变更，不运行无关pnpm全仓检查。

**到此结束，不建议因这两个正向样本继续投入完整升级验收，当前继续使用v0.2.3。** 本次计数适配问题已经在两版真实请求中验证修复；版本升级没有展示稳定质量或耗时优势。该有限筛查不证明v0.2.7在所有任务上无收益，也不重开HC/F02等已关闭方向。原六FAIL、P05 BLOCKED_EVIDENCE和所有历史失败保留；本轮没有自动追加实验、提交或push。
