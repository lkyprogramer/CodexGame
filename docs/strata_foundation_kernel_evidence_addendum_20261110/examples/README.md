# 合成示例的使用边界

这里不是你的模型输出、GPU计数器或产品验收数据。

- [numerical_complete_fixture.json](numerical_complete_fixture.json)：2个请求、2个stock arm、1个candidate的缩小JSON合同。stock/candidate允许不同的预注册scorer身份。每个token/概率/ID均为人工值；emitted只是教学数组，不是经过认证的真实收据。
- [kernel_evidence_example.json](kernel_evidence_example.json)：只展示证据附件的分层与UNKNOWN，不具备产物/运行绑定资格；不声称覆盖04章完整schema。
- [tests/test_addendum.py](../tests/test_addendum.py)：由阳例逐项破坏，测试缺request、缺/重复/重排位置、单stock、重复run、wrong text/path/scorer、缺forced输出、非有限与有限非法摘要、tie与格式舍入、交付文件/链接/hash验证。

`tools/contract_examples.py`只验证以上缩小JSON。其成功状态为INPUT_ADMISSIBLE_FIXTURE_ONLY，不解析实际Strata TSV/meta，不认证process/receipt，不检查graph、真实模型、KV状态或性能，不发controller Decision。

合成score_format_tolerance固定为1e-9，是这份人工例的数值边界；**不是给真实Strata评分输出设置的容忍阈值**。真实ε需按锁定输出格式在实验前另行登记。包内JSON parser拒绝重复key和NaN/Infinity文字。

`tools/probe_upstream_force_check.py`是另一个范围极小的离线检查：要求输入已存在且SHA256精确匹配的上游force_check.py，从AST仅取ceil8/binom_tail_ge/check三函数；不import整个上游module，不执行Engine/main/gen/score、不下载源码。100次bootstrap只服务全零mismatch的人工反例，与原6对正式收益bootstrap无关。它不修改上游文件，也不是通用安全执行沙箱。

若源文件不存在或hash不同，probe以BLOCKED退出，不能绕过白名单。新源码需要重新审阅和显式更新版本，不能把旧反例结果自动外推。

完整生产guard、counter importer、memory oracle和controller adapter都仍为PLANNED。它们的测试要求在08章，不在这份toy helper中假装已实现。
