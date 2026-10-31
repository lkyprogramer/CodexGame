# P01B · 验证回执

结果：单引擎三请求执行COMPLETE；最小host采集有效，资格INSUFFICIENT。父目录完整报告 `reports/P01B-PI-WARM-DIAGNOSTIC-20261031.md`。

root在实验根目录执行：

```bash
python3 -B -m unittest discover -s tests -p 'test_frontier_*.py' -v
python3 -B -m unittest discover -s tests -p 'test_frontier_p01b_*.py' -v
```

首条49项PASS；采集门由64改为完整2048窗口并补时钟/CPU成本门后，第二条17项PASS，未改变的原32项不重复运行。独立Reviewer另行执行17+7项PASS，不将其测试算为root GPU复现。

29号机实际完成独立tree的CUDA12.3/sm89 Release构建，mandatory flags保持；最终二进制hash见CAPTURE_BUILD。g++ -std=c++17 -O3 observer probe：CPU单调时钟包络、完整IDs/窗口、token及窗口溢出均PASS，状态188464bytes，合成净平均145.28473ns/window，小于5000ns门。CPU成本不是GPU off/on对照。

唯一实际命令：

```bash
function jssh() { ssh -J jump "$@"; }
jssh -o BatchMode=yes -o ConnectTimeout=10 29 'cd /home/hhtele/strata-lab-4090
exec /home/hhtele/strata-0.1.43.1/.venv/bin/python -B tools/frontier/p01b_run.py --execute --plan workspace/frontier/p01b-20261031/input/DIAGNOSTIC_PLAN.json --identity workspace/frontier/p01b-20261031/input/IDENTITY.json --out workspace/frontier/p01b-20261031/run'
```

实际1引擎、3HTTP尝试，178.1738秒，无重试；941/576/774输出均自然EOS。939完整窗口/2291原始IDs闭合。原始包92项、13112270bytes，本地逐SHA/长度PASS；独立原件审阅与冻结分析器重算也PASS。

未运行：额外GPU校准/对照/profiler、候选实现、P04数值oracle、P05固定2048正式性能、P06质量验收、部署和无关pnpm全仓检查。GPU内部依赖、CPU expert dtype/nt及任务完成/park拆分仍UNKNOWN；六FAIL不变。
