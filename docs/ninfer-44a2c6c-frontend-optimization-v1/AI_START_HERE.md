# AI 执行入口

将本包放在原仓之外，或原仓 `docs/ai/frontend-tokenization-v1/`。不要覆盖原仓根 AGENTS.md，也不要自动 cherry-pick 最新上游。

## 可直接交给开发 AI 的任务指令

```text
目标：基于 tensorninja/ninfer-4090 的
44a2c6c3392c9d51e76a895ed97bf1867530d252，修复真实 4090 长会话热续写的
CPU tokenize 瓶颈。不修改模型制品、GPU kernel、MTP3、rk4v4-e8、262144 窗口、
采样、模板输出、工具协议或 GPU continuation 规则。

先读当前仓 AGENTS.md，再读本包 README、docs/00、01、02、03、07、08、10。
严格执行 T00–T13；每次开始任务先读任务卡及其依赖产物。

已知源码问题不是单纯“一次 BPE 太慢”：processor.cpp::encode_rendered_chat
会针对每个语义检查点，从文本开头反复 encode 前缀。先完成单请求 one-main-pass
和局部边界验证，再评估并实现安全的跨请求前缀复用。

必须建立指定提交的独立 legacy oracle；保持 token_ids、token_types、三轴 positions、
rope_delta、三个 optional boundary、checkpoint_hints 的顺序/重复/种类、
starts_in_reasoning，以及非法输入的可观察错误契约一致。

不能把 exact token prefix 当作任意追加都稳定；不能用生成结果反向填充前端 cache；
不能在前端使用尚未产生的 GPU append_frontier 作为 fast-path 开关；不能关闭 checkpoints
或 preserve_thinking 换速度；不能把测试 skip 当 pass。

现网 ninfer-4090:prepare-detail/schema20 是本地诊断 overlay，先保存其镜像身份、
源码 diff、配置与日志映射，和纯 44a2c6c 分开审计。未知字段不得猜名、缺失不得当零。

按任务卡执行红→绿→回归→证据记录。共享源文件单写者；CPU fixture 编制可并行，
GPU 回放及容器必须串行。仅在获得停机/切流授权后使用单卡维护窗口。

输出 implementation-report.md、gate-report.json、paired-results.jsonl、
source/overlay/build/artifact 身份、完整失败与跳过记录、回滚说明。
无 GPU 或无真实资源时可以完成 CPU 层和代码提交，但 GPU/生产状态必须保持 NOT_RUN。
```

## 第一次执行

```bash
python3 tools/validate_pack.py
python3 tools/check_source_pin.py --repo /path/to/ninfer-4090
```

第二条 `/path/to/ninfer-4090` 是唯一必须替换的工作仓路径；脚本只读，不 checkout、不 reset、不 fetch。之后按 T00 建隔离 worktree。所有本包提出的新 NInfer 命令行选项、bench target、统计字段，在对应任务实现前都不存在，不能直接用于现网启动。

## 停止条件

发现 oracle 失配：停止开启快速路径，保留失败输入的受控本地证据，先缩小复现。发现 schema20 overlay 改了语义而非纯统计：建立差异分支，不把两者混为同一 baseline。无生产授权：完成可离线完成部分，保留部署 Gate 未执行；不要以此要求重新确认已经明确的设计任务。
