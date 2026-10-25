# PR实验决策报告

状态：PENDING_GPU / ADOPT_CANDIDATE / NO_BENEFIT / NOT_APPLICABLE / BLOCKED / REGRESSION

## 身份与环境

日期、base SHA、PR head、candidate SHA、binary SHA、编译器/ggml SHA、驱动、CPU、GPU、RAM、模型及分片哈希、KV/MTP/专家缓存/采样、context=131072、题集哈希。

## 机制证据

实际路径命中、节省的计算/拷贝/重读；避免仅打印enabled=1而未执行代码。

## 对照

| 指标 | A0原版 | A1关闭 | B开启 | 配对数量 | CI | 原始日志 |
|---|---:|---:|---:|---:|---|---|

分开报告冷读、热追加、状态恢复和Java工具循环。定长输出未达目标则速度行不可比较。

## 失败与未执行项

包括base固有失败、候选新失败、GPU/后端未测、所有超时/OOM/NaN、Java编译失败、内存门触发。失败不得从分母移除。

## 质量与资源

工具授权、上下文恢复、Java断言、实际Pi留出集、RSS/VRAM/pinned峰值、swap及每turn增长、重启/取消。

## 成本与最终判断

端到端净收益是否抵消新状态与维护成本；收益是否只是更短输出/不同路由/另换模型。

## 回退

关闭参数、对应已验证二进制、隔离配置路径；不自动更改生产。
