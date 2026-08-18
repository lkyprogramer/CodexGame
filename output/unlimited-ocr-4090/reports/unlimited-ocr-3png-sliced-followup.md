# Unlimited-OCR 3.png 与长图切片复测

测试时间：2026-06-30  
测试机器：`192.168.10.29`  
Qwen 状态：测试前已停止 `openclaw-qwen36-mtp4-128k.service`，测试后保持停止。

## Qwen 停服状态

```text
systemctl is-active openclaw-qwen36-mtp4-128k.service => inactive
systemctl is-enabled openclaw-qwen36-mtp4-128k.service => enabled
18343 => not listening
28343 => nginx still listening
qwen/llama/openclaw process => none
gpu memory after tests => 3 MiB
```

## 3.png 对比

| Case | mode | max_length | 结果 | 耗时 | 字符数 | 观察 |
|---|---|---:|---|---:|---:|---|
| `3_base_8192` | `base` | 8192 | 成功 | `19.69s` | 1495 | 仍误判 table，但不长时间卡住 |
| `3_base_16384` | `base` | 16384 | 成功 | `19.64s` | 1495 | 与 8192 基本一致，说明长度不是主要变量 |
| `3_gundam_8192` | `gundam` | 8192 | 成功 | `177.03s` | 17116 | 大量编号和空表格退化，明显放大问题 |

结论：`3.png` 的版面本身容易触发表格误判；`gundam crop` 会进一步放大退化和耗时。后续处理这类 1550x6664 长图应优先使用切片 + `base`，不建议直接用整图 `gundam`。

## 纵向切片

配置：

```text
mode=base
max_length=8192
slice_height=1800
slice_overlap=120
slice_count=4
```

| 图片 | 结果 | 耗时 | 合并字符数 | 本地文本 |
|---|---|---:|---:|---|
| `11.png` | 成功 | `31.19s` | 1055 | `/Users/luo/Documents/tmpnew1/testimg/11.unlimited-ocr-sliced-base-8192.txt` |
| `2.png` | 成功 | `27.24s` | 644 | `/Users/luo/Documents/tmpnew1/testimg/2.unlimited-ocr-sliced-base-8192.txt` |
| `3.png` | 成功 | `28.76s` | 2172 | `/Users/luo/Documents/tmpnew1/testimg/3.unlimited-ocr-sliced-base-8192.txt` |
| `4.png` | 成功 | `18.85s` | 652 | `/Users/luo/Documents/tmpnew1/testimg/4.unlimited-ocr-sliced-base-8192.txt` |

`3.png` 的切片版从原先整图 `gundam` 约 5 分钟不可用，变成 28.76 秒可完成；但第一段仍有 table 输出，说明切片解决了长生成和严重退化，不完全解决版面分类错误。

## 已放入 testimg 的文本

```text
/Users/luo/Documents/tmpnew1/testimg/11.unlimited-ocr-sliced-base-8192.txt
/Users/luo/Documents/tmpnew1/testimg/2.unlimited-ocr-sliced-base-8192.txt
/Users/luo/Documents/tmpnew1/testimg/3.unlimited-ocr-sliced-base-8192.txt
/Users/luo/Documents/tmpnew1/testimg/4.unlimited-ocr-sliced-base-8192.txt
/Users/luo/Documents/tmpnew1/testimg/3.unlimited-ocr-base-8192.txt
/Users/luo/Documents/tmpnew1/testimg/3.unlimited-ocr-base-16384.txt
/Users/luo/Documents/tmpnew1/testimg/3.unlimited-ocr-gundam-8192.txt
```

原始远端结果归档：

```text
/Users/luo/Documents/github/CodexGame/output/unlimited-ocr-4090/raw/followup-remote-copy
```
