# U01R1 · 修复PT0计数后的独立版本对比

> 已完成：6引擎/3组/12请求，无重试或替补；编码两版3/3，工具A3/3、B2/3。计数修复验证通过，当前不建议升级或继续完整验收；原生产17:39恢复，13保护SHA匹配。见[实际报告](../reports/U01R1-VERSION-COMPARISON-20261031.md)。本轮到此停止。

2026-10-31，用户在U01提前中止后明确要求修复问题并重新测试。本轮独立run_id为version-compare-20261031-r1，不覆盖[U01原合同](U01_VERSION_COMPARISON.md)、原2请求、10个NOT_RUN或失败结论。

沿用原授权的半天上限、3组配对、12个生成请求、最多6个实验引擎；固定A→B、B→A、A→B。A为生产同SHA的v0.2.3隔离树，B为无HC差量的P6 v0.2.7及六文件reply/PT port。请求body、seed、采样、输出预算、配置、原受限Docker评分器、资源护栏与生产恢复规则全部沿用U01；不开其他优化，不追加生成探针、重试或替补。

## 本轮前置修复与证据

执行器在创建CPU计数器前统一从实际runtime同步STRATA_REPLY_REUSE与STRATA_PRESERVE_THINKING，prepare与worker复用同一个make_counter。预检按版本使用独立CPU进程，避免Python导入缓存混用frontend。

本地tests.test_version_compare三项及原tests.test_v027_baseline五项PASS。覆盖父进程PT1被runtime PT0覆盖、两个默认值均取自runtime、已关闭campaign拒绝重放。

两版CPU预检均为：布尔请求316 token，编码原请求4408 token；编码显式preserve_thinking=false为4408，true为44108。编码PT0计数与U01服务端实际usage精确相等；布尔历史服务usage324，与316相差8，仍沿用原32-token容差，不放宽门槛。CPU正/负控制不发送HTTP生成。

PREREGISTRATION在停生产前冻结两版源码/二进制、配置、共享harness、评分镜像、原请求hash和CPU预检结果。worker在生成前再次校验计数等于预检，实际usage继续走原门。旧执行器9b8b308f…的失败证据保留，不重标PASS。

## 执行与决策边界

普通答案失败保留并继续另一配对臂；基础设施或资源错误中止，剩余NOT_RUN。比较逐组两题成功、反向回归、完整请求耗时与资源；只有重复出现优势且无重要回归，才建议另行完整升级验收。三组是相同两个冻结case/seed的重复，不是独立任务质量样本，不建立正式非劣或性能PASS，不自动升级生产。

监督器临时停止既有生产，计算/评分以hhtele运行，结束或中止后恢复原v0.2.3服务并核对health及13保护SHA。实验仅18089，生产配置、缓存6144MiB/4slots、PT0和原六FAIL不改。外层维护最多10800秒并保留300秒恢复，不以预算为凑满理由。

原件目录workspace/combination/version-compare-20261031-r1。最终结果另建报告，当前合同不授权超出12请求或补样本。
