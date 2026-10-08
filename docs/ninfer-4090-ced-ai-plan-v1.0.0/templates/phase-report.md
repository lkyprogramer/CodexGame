# Phase 统一验收报告

> 本文件是待填写模板；不是已经完成的测试结果。无证据字段保留“未执行”，不要填猜测值。

## 结论

Phase：未执行。集成提交：未执行。Gate：NOT_RUN。资格范围：none。Production quality proven：false。

## 实物与身份

填写source/binary/base/Predictor/config SHA、运行环境、实际时间、执行命令、完整required-check清单。若不需要Predictor，说明原因而非留一个虚构SHA。

## 统一测试结果

| 检查ID | 实际用例数 | 通过 | 失败 | SKIP | 原始证据 |
|---|---:|---:|---:|---:|---|
| 未执行 | 0 | 0 | 0 | 0 | 尚无 |

## 数值与状态

Teacher injection、StateOnly/math误差、learned误差分别报告。列出conv/frontier/MTP/provenance检查和第一分歧。

## 质量与性能

列出同一配置A/B/C对照、真实输入长度、sampling、MTP、cold/warm、TTFT全部开销、decode、Agent成功率/耗时、失败/超时和置信区间。没有测的项目明确未测。

## 资源与生产恢复

峰值GPU、余量、RAM、磁盘、数据量；生产原active/enabled、恢复后health/model、保护文件diff、实验进程清理结果。

## 根因、修复与范围

记录失败根因、最多两轮修复、重新执行的测试、仍未解决的限制。不要只给“优化了一下”。

## Gate判定与下一动作

明确哪个阈值支持PASS/FAIL，统计证据不足时说明private_opt_in或INCONCLUSIVE。指出下一允许Phase/Task或NO-GO。
