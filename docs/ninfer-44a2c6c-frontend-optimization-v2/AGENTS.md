# 本文档包的 AI 工作约束

本文件只管本目录及其执行资料，不替代固定仓库的 `AGENTS.md`。禁止将它复制到仓库根覆盖原有规则。

## 实现范围

产品主线 = B0 + B1 + 必需的 request-local 观测。只能修改 [05 文件映射](docs/05_CODE_CHANGE_MAP_AND_INTERFACES.md) 中与前端和测试直接相关的内容。新增运行时跨请求缓存、共享锁、pin/LRU、后台 shadow、DFlash2、GPU KV 布局、采样和权重转换均不在范围内。

## 不可破坏的合同

保持 earliest-position / smallest-ID；普通分段 NFC/BPE 一字不改；保留 `parse_added_tokens=false`；保留 `special` 标记的旧含义（不是所有 flags 都必须 false）；保留边界的异常类型、名字和顺序；hint 输出保留 kind、顺序和重复；主编码失败优先于边界错误；诊断计数不改变控制流。

先构造失败的结构性/差分测试，再写产品实现。纯性能优化的 correctness 测试在 legacy 下可通过，但新增“扫描量/主编码次数”的测试必须先红，不能为了制造红测试删除旧的合法行为。

## 工程纪律

Tokenizer 构造后只读；桶保存 vector 索引而非内部裸指针，以保持 copy/move 安全。trace、memo、统计都是单调用局部所有权；不复制完整 token 前缀到每个边界；对所有 input size/offset 使用 checked size_t 算术。内存分配失败不等于合法输入语义差分，但不可吞错或产生不完整输出。

旧 oracle 与新扫描器不得共享被优化的 selector/resolver。不能只把候选 B1 作为 B0+B1 的“独立”参照。原始 review harness 是调查辅助，不是完整 oracle。

## 证据纪律

PASS 必须附命令、退出码、输入 hash、资源 hash、二进制/commit 身份和原始文件路径。SKIP、NOT_RUN、CPU 原型 PASS 不能升级成 GPU/HTTP PASS。`stop_token` 仅说明结束原因，不说明 Java 任务或工具参数正确。有限随机差分不是全输入穷尽证明。

## 运维与数据

不默认有 SSH、Docker 或生产写权限。任何维护窗口、重启、抓取真实请求正文、修改端点或内存预算须先有具体授权。CPU-only 基准也会竞争 LLC/内存带宽；优先隔离，必要时限核/降优先级并监测业务，不承诺“对生产零影响”。
