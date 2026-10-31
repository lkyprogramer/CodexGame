# P01B · 自然 EOS 与有界 host 依赖采集

2026-10-31 用户明确授权：使用 jssh 29，先补齐最小采集并验证；满足条件后只启动一个引擎、最多三条真实暖态请求，生产保持停机。本阶段是新批次，不改变 P01 的 INSUFFICIENT 或 P05 的固定输出性能合同。

## 输入与范围

复用 P00 脱敏 Pi prime、两条原追问、模板/tokenizer、采样参数和保守预算。prime 103183 输入 token。每次回传本引擎实际正文/thinking，保持 reply reuse=1/PT0，不填充追问、不执行模型工具调用。

输出上限 2048，接受正常 stop/length，不设非零最短输出。零输出、错误、无暖态复用、计数不符、资源或身份失败立即停止，不补样本。每请求最多600秒，全程3600秒，清理预留120秒；总context不超过131072且保留4096安全余量。唯一矩阵 prime→append_1→append_2。

## 采集前置门

研究树基于原 P6，原生产、回滚树及 P6 基线只读。只在独立 tree 修改 generate.cpp，新增 lab_p01b_trace.hpp。仅插入主线程 host 记录，CUDA 调用、graph、融合、数学与分派语句保持原样；PROFILE/TRACE 原开关不启用。独立源码审阅、隔离构建、29号机CPU时钟与记录/溢出验证必须通过。

每请求静态上限2048窗口、2048个原始 emitted token ID；状态内存不超过512KiB。正常串行每窗至少一个输出，因此可覆盖全部窗口。溢出、缺记录、时序或计数不闭合一律失效。请求后一次导出，不在窗口中分配或写文件。CPU合成 mean 打点净成本门为5000ns/window；这是运行准备门，不能证明真实GPU无扰动。

## 可以证明的边界

记录每窗 begin、verify成功返回、commit进入/返回、draft返回、完整结束六个host时刻，以及context/T/kept/emitted/first/merged和异步分支状态。原始token IDs直接取自native打印T记录的位置，不由解码文本重新分词。

只对原verify/head同步已完成后至commit调用前的host区间建立窄依赖边。first/merged/T1、pipeline、多stage、peer/remote、foresight、pending/aflipped或未完成adapt分支全部排除；adapt线程已启动时记录未知常量，不读取其并发写入的容器。async commit/draft返回不被当作GPU全局完成。

CPU pool内部完成/park、实际expert dtype/nt、GPU细分区间与未知重叠仍为UNKNOWN。所有host gap总量只给本次采集条件下此区间的删光模型；闭合部分另列。没有具体可删机制或资格不足时以INSUFFICIENT结束，不自动重跑或进入P02。六项历史FAIL与P05 BLOCKED_EVIDENCE保持。

## 交付与停止

产物位于 `../../workspace/frontier/p01b-20261031/`：授权/合同、实际源码与build身份、CPU probe、采集门、原始请求/SSE/native trace/资源采样、DEPENDENCIES/WINDOWS/QUALIFICATION与最终资源回读。阶段报告另存根reports。独立review/test核原件后关闭；不部署、不恢复生产。
