# 命令与实际能力

入口 `./run.sh` 使用 `LAB_PYTHON`，否则使用 `python3`。建议 Python 3.10+，生产 Python 环境已有 Strata 的 `regex`、`jinja2` 等依赖。不要全局升级依赖或驱动。`--config PATH` 是全局选项，必须放在子命令之前。

| 命令 | 是否写入生产 | 行为 |
|---|---|---|
| `init` | 否 | 首次写local.json；拒绝覆盖 |
| `selftest` | 否 | 测试包内CPU/HTTP/可信Java oracle；无GPU |
| `doctor` | 否 | 读取部署配置、硬件、Git身份，写私有inventory |
| `bootstrap` | 否 | 在独立workspace克隆；锁定base worktree |
| `assets` | 否 | 首次完整计算模型/pack/profile/template哈希；大模型需顺序读盘 |
| `qualify --pr N` | 否 | 输出适用性阻断与机制探针需求 |
| `prepare --pr N` | 否 | 固定PR head、导出diff、生成TASK；不应用补丁 |
| `ai --pr N --execute` | 否，任务约束 | 调用用户配置的外部AI argv；需已有认证，不自动申请密钥 |
| `build [--pr N]` | 否 | 编译实验tree；不启动GPU服务 |
| `corpus --suite full` | 否 | 本地实际tokenizer计数，生成冻结题集 |
| `noise --suite smoke --execute` | 否 | 最新base三次同配置对照，测本机运行噪声 |
| `run --pr N --suite smoke --execute` | 否 | base/off/on，每轮独立引擎，默认5轮 |
| `auto --pr N --suite smoke --execute` | 否 | prepare→qualify→外部AI→单测重跑→编译→资产/题集→A/B→统计 |
| `scenario --pr N --name java-agent --execute` | 否 | 8个受限Java多轮工具任务 |
| `scenario --pr N --name reply-chain --execute` | 否 | 将模型真实回答逐轮放回历史，检测BPE前缀复用 |
| `scenario --pr N --name preemption --execute` | 否 | 两个重叠HTTP客户端，单原生引擎协作式调度 |
| `stats --results DIR` | 否 | 重算JSON/CSV/Markdown统计 |
| `verify` | 否 | 验证包内固定文件SHA256，非数字签名 |

## 首次必须填写

`deployed_repo`、`deployed_config`、GGUF首分片、chat_template、Strata Python路径。无源码部署须先由AI建立与实际版本相符的只读源码参照，不能把安装目录冒充Git仓库。GGUF多分片会共同哈希。

`ggml_dir`：若现网有与冻结main要求一致的llama.cpp依赖，可指向它；不一致时必须在实验工作区按固定源码文档建立依赖，并记录commit。不得向生产的依赖目录写入。当前包不保证自动解决所有操作系统/工具链的依赖问题，失败会留日志并停止。

`agent_command`：是argv数组，不是shell字符串。包装器自行读取 `{task_file}` 并将工作目录限定为 `{worktree}`。包不绑定特定商业AI CLI，不包含模型/API，也不承诺某个CLI版本的参数。正在本机IDE/Codex会话中执行的AI可直接读TASK，无需再嵌套调用AI。

`maintenance_confirmed=true`：只有用户安排了GPU独占维护窗口后才能设置。它不是“授权停止生产”的开关；检测到其他GPU计算进程仍然拒绝运行。

## 一次只变一个因素

配置、模型、KV、MTP、CPU workers、CUDA工具链是共同变量。上下文固定131072，显式输出上限，缓存预算默认0。为测试特定PR开启小预算缓存时，先单独建立这个前提配置的稳定base结果，再对三态使用同一预算；不得把“cache 0→开启”的收益归入PR。

#3322需要执行AI开发专用drafter切换适配器，详情见专项文档。通用runner故意冻结`--mtp`，不假装一个环境变量就能完成MTP与DFlash2的对照。

## 退出状态

0：命令完成，不等于性能/质量通过。检查JSON中的state/decision。
2：阻断、输入错误、缺少review、硬件/内存不符、编译或实验失败。原始日志保留。

在没有本机配置时，`list`、`selftest`、`verify`仍可用；`run/auto`不加`--execute`只显示计划，但仍需有效local.json。
