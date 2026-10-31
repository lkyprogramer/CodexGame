# 本包的执行约束

先读 START_HERE_AI.md、sources/LOCK.json、config/policy.json、当前 Phase 和候选合同。

本包是用户要求的后续探索计划，不覆盖原仓库保护规则。已授权的离线代码与文档工作可继续；不要把本包文件中的布尔值当用户授权。目标机有其他任务、服务状态变化或 GPU 交接不明确时，停止启动新负载，保留恢复点。

1. 生产和回滚树只读；实验只用 18089，不改 systemd、NGINX、生产启动脚本、驱动、CUDA 12.3、内核/GRUB/initramfs，不自动恢复生产，不执行 updater。
2. 总 context≤131072；完整渲染输入+输出预算+4096≤131072。85°C 停止；实际 MemAvailable≥4096MiB；任何 arm 不启 STRATA_STAGE_PIN、STRATA_ROUTE_RESIDENT。
3. 六项原长检索 FAIL 保留；不改 gold、prompt、预算或评分使其变 PASS。基础模型与量化影响仍未拆开。
4. P24 HC、P5 VNNI、P12 gather、已筛查 Ada/DEQUANT_SIDE、NP3 pool 等不重跑；重开须有独立机制差量、当前关键路径证据和新编号，不能换名字续测。
5. 当前只允许计划先推进一次限额暖态 decode 资格诊断。资格不是性能 PASS。无资格就结束；不自动遍历 atlas。
6. 所有配置、权重、模板、源码、二进制、实际分派、计数与请求身份可追溯。native 数值 oracle 复用匹配分派的方法；跨 fresh engine 不逐 bit 不能当候选正确性证据。
7. 同一 GPU 的任务串行；开发并行须文件/接口不冲突。每 Task 最小验证，每 Phase 独立 review/test，证据有效则复用。
8. 模型生成代码只在原受限 Docker 评分器执行。没有 Java 镜像就是 NOT_RUN，不能宿主执行。
9. 不把 SSH、sudo、Bearer、Pi apiKey 写入文档、日志、git 或归档。
10. 工具的 exit 0 不等于部署许可。最终状态必须区分 BLOCKED、INSUFFICIENT、NO_GAIN、RESEARCH_RESULT_ONLY、READY_FOR_HUMAN_REVIEW。
