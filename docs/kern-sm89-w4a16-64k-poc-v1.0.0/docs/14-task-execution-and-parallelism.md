# AI任务执行与并行

任务详细文件位于tasks/，机器可读DAG是configs/tasks.json。T00开始，每个任务以“独立可验证成果”为单位，不以修改行数划分。

CPU并行组：环境锁/权重header/协议测试/Java夹具/文档检查可以分工。GPU依赖组：oracle→packing/GEMM→GDN/Attention→全模型→性能与Agent，必须在同一时间只有一个owner。

每个独立开发任务在独立git worktree；共同改provider生成器时由一个integrator合入。不得多个AI同时改一个文件、同时写同一个artifact cache。所有编译输出按arch+toolchain+source+shape key隔离。

`python3 scripts/next_task.py`给出尚未完成、依赖已满足的任务。实际状态记录在`work/task-status.json`，初始任务清单不可直接改成全PASS。状态必须绑定证据文件。

每个任务结束：小范围单测→源diff审阅→相关GPU回归（如涉及）→提交→记录commit/命令/退出码。reviewer不能仅看“主AI说测试通过”。模型挂了或进程超时，先保留原始日志、停止当前候选、恢复NInfer，再做系统化debug。

本包不提供远程SSH凭据、不替用户自动创建外部AI任务。它是交给已有执行AI的工作合同。执行器能力不足时用BLOCKED说明缺的是哪项工具/权限，不伪造通过。

## 路径约定（避免两个work目录互不相见）

`KIT_ROOT`是解压目录；`POC_ROOT`默认`/data/kern-sm89-poc`；Kern源码是`POC_ROOT/source/kern`。任务里的`tools/`、`crates/`、`tests/sm89/`、`examples/`相对Kern源码；本包的`configs/`、`scripts/`、`poc_tools/`相对KIT_ROOT。

AI在T01建立一个共享工作目录`POC_ROOT/work`，将`KIT_ROOT/work`与`KERN_SOURCE/work`链接到它（只在目标不存在时创建，不覆盖目录）。这样任务命令从Kern源码运行时的`work/poc.local.json`与本包next_task看到的是同一份。`configs/qualification.local.json`永远位于KIT_ROOT；其中全部argv路径由T22写为已存在的绝对路径。记录每条命令cwd，不依赖执行器猜测。
