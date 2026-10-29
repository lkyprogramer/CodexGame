# 执行实现独立评审

2026-10-29，按用户要求派发 Astra max 只读评审。评审不访问29、不读取模型私有识别全文、不修改文件；由实现owner修复，reviewer独立复验。

本轮1项P1、2项P2均关闭：

| 问题 | 修复与验证 |
|---|---|
| 活跃E0队列暂空时可能被campaign误停 | guard识别endurance/standard入口；独立新增回归通过 |
| 最后一轮执行中源码/清单漂移仍可能PASS | 轮末重新核源码与四清单，变化记录并FAIL，产物保留；六分支回归通过 |
| E0关窗后恢复预热失败打断其他已接纳页排空 | 停止后续恢复预热，退役失败worker且继续其他正式页；原复现4提交/4终态/排空true，原失败仍FAIL |

reviewer首轮独立47项测试PASS，修复后5项新增回归PASS。稳定code：core f0d18534aa6d86b5c92597970c55d79bf1af91060ad359eb7e8b7cbbc89f6847；campaign b853bbfc45348324b0ae153584eaef662daf0ce563ac2ebd9953210c6a205ca9；endurance入口384a6fbff8bfb21572d7f2cd025f3fa6d682c998d55b90067797511c37c6ba75。

reviewer指出的README旧30页、页面执行器未实现、初始空闲状态与E0说明已经同步。真实60分钟GPU验收尚未执行，不能以本地review与测试代替。最终硬件结果另见execution-report.md。

## 串行主控补充评审

Astra max独立复现两项P2，均已由原作者修复并由reviewer用原始复现再次关闭：四张已知含文字开发页出现空/纯空白canonical text时不放行；campaign任意cleanup_error均让序列STOPPED，普通模型失败仍继续预定轮次。原复现分别从空块true变false、从9步全启动变为仅第1组后STOPPED。独立运行campaign19、standard12、endurance entry4用例通过；未访问29或读取候选文字。

稳定SHA：sequence dd4e8248f142fff6c084f763c172883472399130bd8eb513826fa833d88a8003；standard c63fef217468df78bcf0827426dc2d7d5e8566bd94e9368ba15b97a3261241af。当前Mini标准控制器已按前版加载，补充门禁将对既有实际dev产物单独readback，保持活跃批次不热替换。

增量只读复核又确认PDF输入前置guard与API指标接线：正常300DPI、旋转/crop的RGB与原渲染相同；巨大PDF与PNG伪装PDF在get_pixmap前拒绝，Pillow阈值等号与None语义保留。reviewer实际4个PDF fixture、1个metrics用例及原两项复现通过，未运行GPU。最新core f2b707796feabd80c7f5a446a8f519b29a426b7859da7a68a6c3f1eac67d3e89；campaign15dfc934d8ff8136283aca8b9f4fa7cde7efd3a3851861154bbbf5e6416a77c1；sequence b0b7e46d8c2473803d7eff91f77c2229d1d579cb716f0dc592ddea13adec4919。

G7薄执行器另经Astra max只读复核，私有13项tests和真实run_trial的模拟I/O 18轮接线均通过（standard/DSpark各9，R0六轮/P0十二轮）。未运行Docker或GPU。runner稳定SHA fc4aa5517f11e81dd2d1a942ad5fdefef3a4e5896114d5efb46d67f6ec02f0c2；前三个spec总counter为生效门，per-position仅诊断。

## Docker top PID列修复

2026-10-29，root在29真实前置guard发现 `docker top <container> -eo args` 返回 `Couldn't find PID field in ps output`。Docker解析要求输出含PID列；原guard异常阻断了后续步骤，当时Mini仍运行且空闲，没有因此执行stop，正式66 trials尚未启动。

修复仅涉及 `execution/deploy/run_campaign.py` 及 `tests/test_campaign.py`：候选进程检查使用 `-eo pid,args`；构建检查使用 `-eo pid,comm`，从每行PID后的comm取得进程名，继续拒绝nvcc、ptxas、cicc、ninja和cmake。测试fixture改成真实 `PID COMMAND` 列，不增加缺PID兜底。稳定SHA：campaign `cc6c87a80671a6f7ecadcf092c90d1cdf9f70bcbfe50fc8b4c942167f395dd1a`；tests `31cc9a9f15500d96f1879ac20312968a3c520c7ecbf331fd796c9ed18708039e`。

验证证据分开记录：root此前以正确PYTHONPATH实际执行campaign全21项测试PASS，记录为 `/private/tmp/ocr-campaign-profile-final-20261029.log`（0.438秒）；该日志是profile修复后的全套证据，不冒充本次PID补丁后的全套复跑。本次PID补丁由实现owner运行4项定向测试PASS（0.012秒），覆盖含PID参数、活动endurance/standard控制器即使API队列空闲仍拒绝、ninja编译拒绝、活跃job拒绝和原raw metrics保留；语法检查PASS。定向检查不等于真实Docker验收。本次修复owner未访问29；远端部署、完整SHA核对与实机guard readback由root另行执行和记录。

### PID修复后的root实测补证

2026-10-29，root在PID补丁后以 `PYTHONPATH=execution` 实际执行campaign全21项测试PASS（0.450秒）；这是补丁后的新证据，与上述profile阶段21项PASS（0.438秒）及实现owner4项定向PASS（0.012秒）分别保留。root随后在29实际核对 `docker top ... -eo pid,args` 与新guard均PASS。v8 tar SHA256 `e7d228530e62fe8f006c5bd4eea1f55c3de25ae3ce2ecadd87ad271faa8fa8cd` 已实际部署，并确认core完整SHA `f2b707796feabd80c7f5a446a8f519b29a426b7859da7a68a6c3f1eac67d3e89`。该实测由root执行，本附录整理未访问29。正式66 trials、E0和DSpark尚未执行，不将guard通过视为GPU性能验收。
