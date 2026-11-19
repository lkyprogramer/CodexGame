# 预注册用例清单模板

状态：TEMPLATE_NOT_RUN。填写case ID和真实输入hash后冻结。下表是覆盖要求，不是已运行结果。原有同身份原件可复用，但需指向raw/hash。

| Case | 范围 | 输入/动作 | 必须断言 | 最小执行层 |
|---|---|---|---|---|
| D1-C01 | planner | 同hash/同3gram异后缀 | token exact-match；不错误证明来源 | CPU |
| D1-C02 | planner | 重复相似函数、邻近anchor | B1/B2同集合；不越界 | CPU |
| D1-C03 | planner | 替换/插入/删除/多token编辑 | proven source恢复只在合法位置 | CPU |
| D1-C04 | planner | reset/restore/source generation变更 | 索引失效，旧候选不能提交 | CPU |
| D1-C05 | planner | accepted大于committed、EOS/预算 | 索引只吸收真实提交历史 | CPU |
| D1-G01 | skip | 连续copy后fallback | MTP hidden/KV/position追平，实际省工作 | 获准GPU |
| D1-G02 | skip | cancel/窗口内EOS/remaining不足 | commit/state/next turn一致 | 获准GPU |
| H2-C01 | asset | wrong hash/shape/remap/dtype | fail-closed或baselinefallback | CPU |
| H2-C02 | candidates | ties/重复/空/越界/NaN | bounded deterministic处理，不漏错误 | CPU |
| H2-G01 | numeric | 固定真实hidden选中行 | 原head selected-row数值oracle | 获准GPU |
| H2-G02 | acceptance | 代码/中日韩/工具holdout | recall/接受变化/完整Target输出 | 获准GPU |
| S-G01 | state | 拒绝首/中/末、cancel、terminal | KV/GDN/conv/hidden/MTP/ledger | 获准GPU |
| S-G02 | continuation | save/restore/短追加 | identity/prefix/next-token/reuse正确 | 获准服务 |
| M0-M01 | 维护 | remaining<W后追加 | bounded input rows，末output未消费 | 独立维护合同 |
| M0-M02 | 维护 | EOS窗内＋remaining组合 | 无不可见尾state；fallback reason可见 | 独立维护合同 |
| O-G01 | 观测 | on/off同身份输入 | 不变Graph/同步语义；CI资格 | 获准GPU |
| P-E01 | 正式 | 冻结N任务×6pair | 全任务质量/wall/失败/CI/资源 | 独立正式预算 |

真实任务清单字段：`case_id/group/split/source_hash/prompt_tokens/context_band/cache_mode/max_new/sampler/oracle_ref/weight`。不要保存未经许可的原代码内容。用例清单冻结后如需修订，废止原spec并新建合同，不能在相同experiment_id覆盖。
