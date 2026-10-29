# Astra max 文档审查与修正记录

日期：2026-10-28。审查模型：`gpt-6-astra`，推理档位：`max`，独立新上下文。审查对象为修改前的11份方案/清单；审查期间哈希保持不变，首轮报告确认1项P1、2项P2。三项均接受，下面记录文档修正，不代表部署或模型问题已在运行环境修复。

| Finding | 原问题 | 修正后合同 |
|---|---|---|
| P1-1 | Mini concurrent分支绕过page_workers，整文档CLI预渲染/预布局不满足C0单页接纳 | C0改由待实现的共用页面执行器按页接纳/渲染/布局/区域/终态；SDK配置serial只是页内处理设置。原staged命令改名为N0参考，新增跨页不重叠与全局4区域事件fixture |
| P2-1 | Ovis默认前页末表/后页首表绑定，正确合并HTML仍可覆盖无关表格 | 明确单次边界合并能力；以原页+表索引记录片段/祖先/hash，未参与表格与正文全部对账；无可靠系统绑定不写回，PRED禁用GT绑定；多表/非边界/双续表加入负例 |
| P2-2 | 集合micro/macro/平均结构分不能决定good-page分子 | 增加page-good-v1逐页AND谓词、适用任务/GT/评分器版本、缺GT与缺指标规则；集合门保持独立；零good页不除能耗分母；100页中只有90页good的计数fixture |

修正位置：[调度与Mini配置](deployment-details.md)、[Ovis支持边界](ovis-deployment.md)、[统一调度/片段/逐页计分合同](comparison-plan.md)、[机器合同](comparison-contract.json)、[Mini锁](source-lock.json)、[Ovis锁](ovis-source-lock.json)。已有语料清单和匿名样本不变。

## 事实依据

- Mini固定源码[staged.py调度分支](https://github.com/OpenBMB/MiniCPM-OCR/blob/62d5e649c32be2271f2c8c66ec8307f3d7373903/sdk/minicpmvocr/pipeline/staged.py#L412)的concurrent路径不检查page_workers，并把全部页区域展平到线程队列；只改serial仍不能消除CLI整文件预处理。
- Ovis固定[document_crosspage.py](https://huggingface.co/ATH-MaaS/OvisOCR3/blob/4833d5d2afa6e769ee933f024504d67ace80a24c/document_crosspage.py)明确每页对一次边界合并。源码SHA为`3c5d4ded915fee1e27c4b662b37f11f231f0b5fb9b8a12e60a3586a53272e2ad`，与模型锁相同。
- 仅运行该脚本的纯文本helper，用合成A/B表验证：默认绑定确会替换无关的末表，显式片段绑定可保留它；没有调用模型、浏览器或GPU。本次不修改上游脚本，也不实现通用匹配器。
- 100个等长中文页中，90页零错误、10页各10%错误，集合CER为1%；以本页CER≤1%判定时只有90页good。集合门通过不能把分子写成100。

## 验证范围

窄验证覆盖JSON解析、Markdown/链接、C0/N0与版本锁一致性、三类调度事件fixture、逐页计数/缺GT/零good分母规则，以及上述官方helper复现。检查脚本和原始审查证据保存在`/private/tmp/ocr-astra-max-review-20261028/`；合同fixture只是规则自检，不能当成执行器、评分器或OCR实测通过。

尚未执行：受控页面执行器与评分器实现、容器构建、GPU/SDK真实事件轨迹、模型下载/推理、真实GT标注、跨页端到端/能耗/速度/质量测试。它们仍按主方案保留执行gate。

修正后已由同一`gpt-6-astra / max`完成定向只读复核：三项均为 **RESOLVED（文档合同）**，没有剩余明确finding。复核期间12份文档哈希保持不变；本段状态按复核结论收口更新。两模型执行器/评分器/部署/推理与质量性能仍未实测。

已实际执行并通过：

```bash
python3 /private/tmp/ocr-astra-max-review-20261028/validate_repair.py
```

检查结果：6份JSON、6份Markdown及引用/格式、共同基线和锁、三类页面事件合同例、90/100合格页计数、6个状态/文字规则例、缺GT与零good分母规则、原语料清单不变，全部PASS。Astra另核最终多表禁写回、GT隔离和执行器未实现等断言，全部通过。完整首轮和复核证据分别为临时目录中的`findings.md`、`closure.md`、`validation-result.json`，不把这些合同例当实际运行器验收。
