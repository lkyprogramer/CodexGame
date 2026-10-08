# Full_reset 独立调查模板

## 状态

UNCLASSIFIED_METADATA_ONLY / HYPOTHESIS / CONTROLLED_REPRODUCTION / VERIFIED_CAUSE / CONFIG_CHANGE_APPROVED。

## 证据

匿名实际clientidentity、source/镜像/参数、resolvedTTL、L1状态变化、L2具体rejectionreason、实际serializedsize与主机峰值内存。tool_count和时间gap只作线索。

## 对照

主会话连续 / 插入小客户端 / idle阈值前后 / sessionalias不同形态。每组固定input/resource至少3次，记录reused/computed/TTFT/prefill/publish/evict。

## 改造选择

先比较路由、L1多状态、L2预算/L3、TTL、alias，每次只改一项。所有需重启/配置/客户端变更记录授权和回滚。未测payloadbytes不能声明“16GB必够”。

## 收益

按同一观测窗口报告reset率和prefillsum，不与tokenizer优化合并推导。仍无法解释的reset保留UNKNOWN。
