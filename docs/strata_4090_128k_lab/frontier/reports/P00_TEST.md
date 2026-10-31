# P00独立验证

独立Validator在实验主目录实际执行：

```bash
python3 -B -m unittest discover -s tests -p 'test_frontier_*.py' -v
python3 -B -m unittest discover -s frontier/tests -p 'test*.py' -v
python3 -B frontier/tools/validate.py --root frontier
```

结果分别为19 tests PASS、9 tests PASS、PACKAGE_VALID。身份和计划重算为IDENTITY_LOCKED与PLAN_VALID_PENDING_GPU_HANDOFF，live_ready=false。

Validator核授权/身份文件SHA，prime和两个recipe的canonical JSON SHA（sort_keys=True,separators=(',',':'),ensure_ascii=False），真实user message及来源hash，103183token CPU记录/token SHA，以及六项原FAIL request文件SHA，全部一致。文件SHA按原始bytes计算，不能与canonical对象SHA混淆。

本地初次从仓库根执行定向测试时，warm_plan测试因tools模块导入路径失败；保留该失败，改为正确实验主目录执行后通过。P00原说明中的tools/validate.py路径歧义也改成frontier/tools/validate.py。没有删除用例、弱化断言或增加mock取得通过。

Validator未SSH、未重新hash远端资产或运行tokenizer；只核采集原件一致性。模型生成代码没有执行，所有测试均是工具自身的合成反例。游戏业务未改，pnpm全仓套件未运行。

实际warm read/reused、append完整history hash和active PID/env均NOT_RUN；P05和六FAIL保持原状态。最终manifest与保护检查由主代理收尾，见实验主目录reports/P00-EVIDENCE-20261030.md和workspace/frontier/p00-20261030原件。
