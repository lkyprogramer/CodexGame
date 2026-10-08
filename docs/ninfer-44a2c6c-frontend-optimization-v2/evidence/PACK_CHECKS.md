# 文档包本次验证范围 · 2026-09-25

## 实际完成

本包辅助工具单元测试 **72 项通过**；包含词法模型、输入生成/校准、防止hash篡改、独立结果比较、严格日志聚合、原型资产审计、配对统计、固定Git源检查及文档DAG/linkchecker。原始red/green/final输出在本目录，最新为 `helper-tests-final.txt`。这些不是 NInfer 产品 CTest。

有限added-token词法模型以seed20260925检查 **20,000 个输入、383,654 个byte cuts**，scanner选择与同请求prefix分解均通过。模型没有真实NFC/BPE或Qwen资源，scope明确为`FINITE_LEXICAL_REFERENCE_MODEL_ONLY`，不能替代G1。

8组配方、32条合成请求重复生成bytes相同，内嵌request SHA256一致；结果在`generated-data-check.json`。所有token数仍UNMEASURED，HTTP未提交。88个active对抗case与test-matrix一一对应；26个旧B2case只在deferred。

保留review资产逐文件哈希核对、28 session/4 raw行解析完毕；20条直接legacy、8条间接参照、12条超262K。附件没有真实1690日志、资源、overlay或原始raw语料，本次没有声称补齐。

Python工具AST解析、shell `bash -n`、JSON语法、schema定义、Markdown本地链接、任务依赖、生成输入与来源manifest均作为文档自检项目；最终执行`tools/self_check.sh`和MANIFEST校验。最终ZIP的CRC与文件内容SHA在打包后另行核验。

## 明确没有执行

没有改动用户仓库或现网；没有编译真实NInfer C++/CUDA；没有在节点29重跑CPU基准；没有读取实际artifact六资源；没有HTTP/4090/vision GPU/生产发布或回滚。`templates/gate-report.json`的G0–G7全部NOT_RUN。

审查结果支持更改设计优先级，但实测101.56→0.443秒仍属于用户提供的CPU原型记录，不是本包作者的现网成绩。产品实现必须按任务卡新生成证据。
