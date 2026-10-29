# 给执行AI的入口指令

你在用户授权的本机环境内，以本包固定最新Strata为基础实施可验证性能优化。先读本文件、AGENTS.md、REPORT.md和VALIDATION.md，再做P00。不要先合并性能PR，不要从头重跑已完成P0，也不要把研究文档中的拟新增接口当成已经存在的命令。

## 任务状态

用户最后已知机器：RTX4090 24GB；Silver4216 16C/32T、无VBMI/AMX；2×32GB DDR4、历史约36GB/s；Flash-Next GSQ-RCO IQ3_XXS（偶奇层实际格式不同）。生产已是A0+EXACT6、performance+C6 off；perf已安装。所有事实需只读复核，不因旧入口写服务停止而擅自启动/停止生产。原始证据在history/reports。

先读config/directions.json，各O方向对应plans；6项F前置优先。原生引擎源码操作在workspace的隔离树，不在生产树。当前包的CLI `prepare --pr`只支持注册PR；原创O方向不能乱造PR编号，通过P00建立独立worktree和实验卡，完成后使用有build receipt的cfg --tree或新增经测试的任务注册接口。

## 步骤1：离线自检

```bash
python3 -B -m lab.cli verify
python3 -B -m lab.cli selftest
python3 -B -m lab.cli list
python3 -B -m lab.cli validate-plan --plan plans/park_restore.example.json
```

## 步骤2：一次性本地配置与盘点

以下是需要本机真实路径的模板；所有占位填全后才执行。`init`拒绝覆盖既有配置。配置文件不保存密钥，原服务API密钥不输出。

```bash
python3 -B -m lab.cli --config config/local.json init \
  --deployed-repo /ABSOLUTE/PRODUCTION/Strata \
  --deployed-config /ABSOLUTE/PRODUCTION/strata-model.json \
  --gguf /ABSOLUTE/MODEL/first-shard.gguf \
  --template /ABSOLUTE/PACK/tokenizer/chat_template.jinja \
  --python /ABSOLUTE/strata-venv/bin/python
python3 -B -m lab.cli --config config/local.json doctor
python3 -B -m lab.cli --config config/local.json assets
python3 -B -m lab.cli --config config/local.json bootstrap
```

核对local.json：workspace必须与生产分离；实验port18089；max_context131072；安全余量4096；初始cache0仅用于基础资格，真实缓存任务再小预算分级；冻结EXACT6及已有生产env。填MTP等asset_files；设置可信Java镜像后才java_enabled。PATH使用满足构建条件的cmake/ninja/nvcc。不要通过降低余量让任务通过。

`maintenance_confirmed=false`是默认，防止未知环境自动跑GPU。若用户本会话已经授权维护窗口/独占实验，核验服务归属与资源后记录并设true，不重复请求同一权限；若没有，需要在具体实验准备好后说明要停止哪个自己有权控制的服务及原因。此研究zip本身没有操作用户机器。

## 步骤3：P00后才做候选

```bash
python3 -B -m lab.cli --config config/local.json build
python3 -B -m lab.cli --config config/local.json prepare --pr 2253
python3 -B -m lab.cli --config config/local.json qualify --pr 2253
```

`prepare`下载固定donor并创建TASK.md，**只检查patch可应用，不自动apply**。读plans/P02和真实diff，添加失败测试、语义移植、默认关闭flag、off/on activation、commit和review证据，生成READY。cache为0时qualify2253会拒绝，这是正确行为。

```bash
python3 -B -m lab.cli --config config/local.json build --pr 2253
python3 -B -m lab.cli --config config/local.json run --pr 2253 --suite smoke
# 只有对应实施、P00资格、维护资源门满足时才追加--execute。
```

cfg只支持STRATA环境变量；MALLOC对照需先实施P00受控接口。没有`scenario park-restore`命令，当前只有validate-plan离线检查。不要把dry-run或离线校验说成运行过引擎。

## 步骤4：结果处理

使用严格smoke stats查缺项/身份/基础质量；真实任务用P00适配器和独立quality_gate（正式性能适配器仍需实现）。准确接口见HARNESS_UPGRADE。每阶段更新templates中的任务卡、decision和证据引用；只测有明确剩余风险的分支。无收益或不适用立即记录并停止，不“优化到测出显著”。

最终P12形成可审阅候选、组合/留出验证与回滚方案。生产改动遵守既有授权；不要把本包的默认保护解释成必须反复向用户确认每一步。遇到新阻塞讲清具体事实与下一项可执行动作。
