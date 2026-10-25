> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# NInfer 4090 上游合入方案与 AI 开发计划

**目标分支：`lkyprogramer/ninfer-4090:b0-scanner`。基准日期：2026-10-15。**

本包交付的是源码差异分析、合并设计、可执行开发计划和验收辅助工具，不是已经合并、编译或部署完成的 NInfer 代码。

## 结论

推荐从你的固定提交建立独立集成分支，按 5 个上游里程碑完成合并；每个里程碑恢复定制保留项并通过统一 review 和测试，再进入下一阶段。**保留 B0 单调扫描器、观测能力、差分 oracle 和无权重镜像；把 B1 的边界优化并入上游的分段前缀接口。采用上游新边界/缓存/调度契约，不保留两套生产前端。新 `rk4v4` 必须独立通过长上下文质量和容量验证，不能把 `rk4v4-e8` 静默改名。**

源码全部合入与功能全部生产启用是两件事。最终源码应包含上游全部 34 个独有提交；决策适配器和新增视觉决策能力默认不进入现有 Java 编码流量配置。

## 阅读入口

| 入口 | 内容 |
|---|---|
| [执行摘要](docs/01-executive-report.md) | 分叉事实、关键风险、推荐路线与明确不做的事 |
| [完整差异分析](docs/02-difference-analysis.md) | 11 个定制提交、34 个上游提交、变化分组与收益边界 |
| [逐文件冲突处理](docs/03-conflict-resolution.md) | 16 个双方改动文件；文本冲突之外的语义与运行风险 |
| [合并后架构](docs/04-target-design.md) | 编码器、边界、缓存、异步导出、日志和 KV 的设计决策 |
| [AI 开发总计划](plans/00-master-plan.md) | Phase / Task、并行关系、统一 review 与阶段门禁 |
| [测试与 4090 验收](docs/05-validation.md) | CPU、真实 tokenizer、CUDA、长上下文、HTTP 和业务质量 |
| [部署与回滚](docs/06-deployment.md) | 单卡串行 A/B/A、独立缓存目录、停机窗口与三件套回退 |
| [风险与决策记录](docs/07-risks-and-decisions.md) | 明确取舍、触发条件与备选路线 |
| [命令手册](docs/08-command-runbook.md) | 已核实目标名称与可复跑命令；新测试明确标记为待实现 |
| [AI 启动指令](AI_EXECUTION_PROMPT.md) | 直接交给后续开发 Agent 的入口 |
| [证据与来源](docs/00-evidence-and-sources.md) | 固定 SHA、源码来源、已运行实验与尚未验证事项 |
| `REPORT.html` | 汇总阅读版，可在浏览器打开、搜索和打印 |

## 包内可直接运行的内容

```bash
python3 -m unittest discover -s tests -v
python3 scripts/phase_gate.py --validate-plan
python3 scripts/source_audit.py --repo /path/to/ninfer-4090 \
  --out /path/outside/repository/audit-20261015 --merge-probe
```

最后一个命令要求指定仓库已经包含 `data/source-lock.json` 的三个 Git 对象。获取对象的命令在命令手册中。审计脚本不会联网、push、切换原工作区或重启服务；完整合并实验只在临时本地克隆中进行。

## 已核实和未核实

已核实：共同祖先；11 / 34 个独有提交；定制侧 43 个变化文件（+5,857 / -39）；16 个双方均改动路径；重点实现的源码语义；三个版本 `tokenizer.h` 的 Git blob SHA；该完整头文件三方合并的 2 处冲突；本包辅助工具的 CPU 自测。

**没有完成：两个仓库的完整本地克隆、整仓 `git merge`、NInfer C++/CUDA 编译、真实模型测试、4090 性能实测、你的当前生产镜像核验。** 当前环境不能直接克隆 GitHub，因此使用 GitHub 源码接口取证；整仓差异总量和完整冲突清单由 P0 的审计脚本补齐。16 个共享修改路径不是“16 个已实测 Git 冲突”。

包中所有 `PENDING`、模板空值、未运行矩阵均是真实待执行状态。辅助脚本自测通过不等于 NInfer 验收通过。包内未包含模型权重、私有流量、API key 或任何远端仓库写操作。


---

# v2扩展：tqLLM借鉴与性能融合（P7—P12）

上文保留原包范围和证据边界。本扩展不把原P0—P6标为完成；新增阶段消费真实P6合格提交。

| 新入口 | 用途 |
|---|---|
| [扩展执行摘要](docs/tqllm/00-executive-and-scope.md) | 哪些值得吸收、哪些不照搬，明确设计可行与实测收益不同 |
| [附件逐项核实](docs/tqllm/01-source-and-claim-audit.md) | 修正旧E8、27B缺DFlash2、KV/graph/测试覆盖等15项判断 |
| [源码借鉴与冲突](docs/tqllm/02-adoption-and-conflict-map.md) | 12项能力采用账本及NInfer接入边界 |
| [新增开发总计划](plans/01-tqllm-extension.md) | 32实施task、6统一gate，接在原P6之后 |
| [新AI启动指令](TQLLM_EXECUTION_PROMPT.md) | 可交给后续开发Agent按依赖推进 |
| [核心接口](docs/tqllm/03-speculation-contracts.md) | C01—C05策略、Lookup、验证、提交、观测 |
| [DFlash2设计](docs/tqllm/04-dflash2-design.md) | C06离线companion、特征、算子、ring、graph |
| [全局草稿缓存](docs/tqllm/05-selective-draft-cache.md) | C07/C08状态来源、两级检索、hostarchive与图外刷新 |
| [预算与实验](docs/tqllm/06-memory-and-performance.md) | 所有内存份额、128K/248K实际token与采用门槛 |
| [测试/部署/回滚](docs/tqllm/07-validation-and-deployment.md) | 必测负例、GPU与业务验收、功能档位 |
| [来源证据](docs/tqllm/09-source-evidence.md) | 固定T/U代码及出版页，区分源码/推导/建议 |
| `TQLLM_REPORT.html` | 只读扩展报告，含全部新增task |
| `REPORT.html` | 原报告加扩展的全包汇总 |

扩展只交付设计、开发计划和Python预算/覆盖/成本辅助工具；没有运行模型或CUDA编译，没有生产更改。完整DAG现含67实施task及13gate；验收矩阵由机器清单生成。所有NInfer实施任务仍PENDING。原包逐字节保留/修改说明见evidence/tqllm/original-package-integrity.json。
