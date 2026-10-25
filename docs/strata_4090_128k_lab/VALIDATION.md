# 交付验证记录

验证日期：2026-10-23。本记录区分**本包已经执行的验证**和**必须在用户4090执行的验收**。

## 已实际执行并通过

| 项目 | 结果 | 证据 |
|---|---|---|
| Python 单元/集成测试 | **31 tests，0 failure，0 error** | `evidence/final_tests.txt` |
| 8套可信Java参考实现 | 全部 `javac --release 8` 编译成功，断言输出 `ALL_OK` | `evidence/java_reference_checks.json` |
| 真实本地HTTP/SSE | 启动loopback测试服务，验证片段重组/usage/timings/结束语义 | `tests/test_integration.py` |
| 上下文预算 | 131072总上限、输出余量、错误计数拒绝 | `tests/test_core.py` |
| 题集结构 | full=82、smoke=21；长输入/根检查点/编辑链结构 | `tests/test_corpus.py` |
| Git工作区隔离 | 临时真实Git仓库克隆/worktree，生产参照保持不变 | `tests/test_workspace.py` |
| 资产身份 | 模型文件变化被检测并拒绝继续 | `tests/test_workspace.py` |
| 统计拒绝路径 | 失败配对、请求hash不同、定长输出不足、未评分项不计有效收益 | `tests/test_additional.py`、`tests/test_integration.py` |
| 子进程超时 | 终止本命令拥有的进程组，保留已产生日志 | `tests/test_processes.py` |
| 脚本语法 | `compileall`、`bash -n run.sh`、CLI help/list通过 | `evidence/cli_help.txt` |
| 数据与PR锁 | 所有JSON解析、10个head为40位SHA、文档/PR一一对应 | `evidence/local_validation_summary.json` |

Java参考程序是本包作者编写的可信测试代码，只用于验证断言本身，不是模型产物。模型产生的Java在目标环境仍必须使用离线受限容器评分。

结构化题集测试使用假的token counter来验证生成器逻辑，**没有冒充实际Qwen tokenizer计数**。目标机运行`corpus`时会使用固定Strata代码和用户自己的GGUF/tokenizer；每个arm启动后还会核对服务端实际usage。

## 明确未执行

- RTX4090上的CUDA编译、kernel parity、性能/温度/VRAM测量。
- 10个PR在固定main上的最终移植、冲突解决及完整代码评审。
- 目标模型128K真实Prefill、MTP、KV恢复、长时Pi工作流。
- Docker内模型生成Java评分的目标机集成（本地验证只编译可信参考代码）。
- 原生Windows GPU进程生命周期；WSL2目标环境的PID审计。
- DFlash2专用服务配置适配器，须由执行AI按PR10任务开发并验证。

所以本包不存在“4090已提速X%”的本机结论，也没有已替换生产配置。PR历史收益在专项文档中有来源与限定条件，不写入本机测量结果。

## 红绿测试历史

`evidence/`内保留早期失败与后续通过记录。早期`*_red.txt`及stage日志是开发历史，**不是当前失败状态**；当前最终结论以`final_tests.txt`和最终Java检查JSON为准。开发时发现Java断言字符串转义和超时日志保留问题，已修正后重跑整个测试集。

## 包完整性

`MANIFEST.sha256`覆盖交付的固定文件，不覆盖用户后续生成的local.json和workspace；它是完整性校验，不是作者数字签名。执行：

```bash
./run.sh verify
./run.sh selftest
```

ZIP另附同名`.sha256`便于核对下载字节。执行AI修改本包脚本前应另复制一份，保留原始包及哈希，不要抹去原始验证记录。
