# U01 · v0.2.3与无HC v0.2.7限额对比

> 本轮已结束：执行INCOMPLETE、比较INSUFFICIENT。第一组A两次请求后触发USAGE_DRIFT，剩余10请求NOT_RUN；生产已恢复，13保护SHA不变。见[实际报告](../reports/U01-VERSION-COMPARISON-20261031.md)。下文保留执行合同，不授权重跑。

用户于2026-10-31明确授权使用jssh 29、临时停生产；最多半天、3组配对、12个请求，冻结配置和评分，普通失败保留、不补样本，结束恢复原生产。本轮是独立版本升级筛查，不重开frontier关闭的性能候选，不授权部署v0.2.7。

## 冻结对象

- A：P3隔离树combo-kvres-20261027，源码f615cc8d11c7f705a7c29b2884af415886c21f9c；二进制SHA256为819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d，与原生产一致。
- B：P6隔离树v027-20261028，原生tag 5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d及六文件reply/PT移植；二进制SHA256为58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22，没有HC差量。
- 两臂保留EXACT6、PT0/reply reuse、KV int8/resident20480、6144MiB/4slots、CPUSHARE4096/AUTOMAX16384、spec4、原权重/模板/采样。保守026设置及六个新版优化关闭值在两臂一致；归一化runtime除exe/cwd/log/临时key外必须相同。
- 沿用原配置中的聚合计时，不开启profiler、新采集observer或其他优化；本轮耗时仅作任务回放描述，不代替无插桩正式性能配对。
- 原13项生产保护文件、P6端口补丁、两个二进制、资产metadata与路径集合及共享harness均锁定。资产全内容hash复用已有证据，不重复扫描78GB。

## 工作负载与上限

顺序固定A→B、B→A、A→B。每臂独立进程与引擎，依次执行以下两个请求，最多6引擎/12次生成尝试；健康、props和idle等GET不生成token。

| 请求 | 原始body SHA256 | 评分 |
|---|---|---|
| schema-boolean | 4dfe4679ae9b2d0ad8b23bbdf1a34859ac78381bea3f71e9306460ecdfb5f846 | 原tool schema及值严格匹配，不执行工具 |
| seed43-final-original | a9b8e7231a860ea2dff1f39b545c5baf66443f278f2786d5c880decd582541c7 | 原16条历史的末轮请求，已有受限Docker评分器的8项累计检查 |

三组重复原body及seed，不能当作三项独立任务。编码8/8表示单个末轮产物的8项检查，不代表重新执行完整八轮链。镜像固定sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad，禁止拉取镜像或宿主执行模型代码。

源请求/评分/采样不改；每请求沿用900秒上限，不发送额外生成探针。逐请求在发送前落盘attempt记录，之后保存原SSE、响应、严格评分、usage、墙钟和native内存/GPU护栏记录。无重试、无替补、无可选加样本。

外层维护窗口上限10800秒，其中保留300秒恢复；原始预登记14400秒是半天总上限，外层采用更短限制。资源护栏85°C、MemAvailable4096MiB、总上下文131072并保留4096。普通答案失败继续配对；HTTP/资源/身份/评分器等基础设施失败中止，剩余记NOT_RUN。

## 决策与交还

比较两题的逐组成功、反向回归、完整请求耗时和资源。只有重复出现的优势且没有观察到重要回归，才建议另行开展完整任务链及生产兼容性验收；没有稳定优势则结束。这里不建立成功率统计显著性、2pp非劣、正式性能PASS或生产采用结论。六项历史FAIL保持。

执行器为tools/v027/compare_versions.py；远端原件目录为workspace/combination/version-compare-20261031。PREREGISTRATION在停生产前冻结；独立监督脚本只管理本服务，计算与Docker评分以hhtele身份运行，正常或异常结束后恢复既有v0.2.3服务并核health。只清理本轮有PID/starttime/exe身份的进程，不能清理无关GPU任务。最终必须报告实际请求数、NOT_RUN、所有失败、13保护hash和生产恢复结果。
