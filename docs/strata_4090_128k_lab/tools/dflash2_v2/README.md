# DF01 D1 v2 · CPU分类适配源码

适用合同：[默认exact-match v2](../../plans/DF01_D1_EXACT_MATCH_V2.md)。这些文件是D1Q的源码副本；实际执行目录及原件见[D1Q回执](../../reports/DF01-D1Q-V2-ADAPTER-20261102.md)。

- `qualification_v2.hpp`：复用未修改的v1比较器。仅完整drafter置信度绝对差为诊断；原行/token门保留，两侧概率有限值/范围和夹具词表域保持硬失败。诊断JSON单独记录legacy判定、全部概率/差值和硬门；单夹具记录始终`D1_v2_qualified=false`。
- `adapter_controls.cpp`：CPU分类正负例，覆盖置信度与后续硬失败并存、边界值、shape、行、token、NaN/Inf/越界及记录覆盖保护。
- `replay_saved.cpp`：只读取已保存的行/token/概率、原参考与夹具词表；不加载模型或CUDA。
- `prepare_cpu.py`：在新实验目录复制原D1N比较器和程序，修改独立副本，执行CPU检查，编译/链接但不运行GPU程序，并生成准备阶段封存。
- `complete_cpu.py`：提取原target/selector检查表达式做CPU负例，生成只含D1的命令描述，复核身份并生成最终封存。
- `run_d1_v2.py`：D1S监督器副本，绑定D1Q的`FINAL_FREEZE.json`与`COMMANDS_V2.json`；保留原非零退出停止、资源、身份、进程清理及停机边界，校验四份v2记录。仅在单独GPU授权的新目录执行。
- `bind_d1_v2.py`：D1S的CPU绑定正负例与新授权快照。复制到新run时，两个文件分别命名`supervisor.py`与`bind_cpu.py`。本次实绩见[D1S报告](../../reports/DF01-D1S-V2-QUALIFICATION-20261102.md)。

`prepare_cpu.py`和`complete_cpu.py`必须复制到新的`workspace/dflash2/<run>/`后执行。相邻D0B/D1L/D1N/D1P目录属于冻结依赖；不得直接在本源码目录执行。原GPU程序、runner、gold和FAIL保持原位。

D1Q的`COMMANDS_V2.json`只有命令描述。全部`execute=false`，D1Q当时GPU预算和生成预算均为0。`FINAL_FREEZE.json`是D1Q最终身份清单；准备阶段`FREEZE.json`与包含旧D2命令的`COMMANDS.json`仅作历史来源。后续D1S使用独立`AUTHORIZATION.json`记录用户新增的2程序/16夹具/六生成/60分钟授权，不修改这两份冻结文件或其argv/env。

CPU检查不证明GPU实现正确。实际target采样、提交状态、EOS、独立selector、机制/资源及真实生成仍待独立授权。后续监督器必须绑定最终清单和D1命令；任何程序非零退出仍立即停止。不得直接忽略旧v1的exit1，不得将单夹具诊断记录作为D1通过。
