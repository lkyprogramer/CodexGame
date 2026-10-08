# 18 · Artifact 资源与 prepare-detail 身份

## 18.1 三层身份必须分开

A0=固定纯源44a2c6c/schema19；A20=A0+真实观测overlay/schema20；C=A20+B0+B1+必要计数。报告对比应说明A0或A20，不能将两个名称交替使用。评审宣称三核心前端源相等，执行者仍需核对现场文件和构建上下文与镜像关联。

短image ID `9c2dec8b9ff0`只作报告线索；保存Docker inspect的完整Id、RepoDigests（若有）、构建source/overlayhash。tag可变，不能据tag认定同一二进制。

## 18.2 资源提取原则

优先从实际`.ninfer`目录表读取六个frontend资源对象，按本基线`resources.cpp`绑定名称获取，不猜header/offset，不加载全部权重到GPU。可用原仓已有读制品工具或编写最小只读提取器；输出文件bytes必须与目录对象一致。

资源文件：tokenizer.json、tokenizer_config.json、chat_template.jinja、generation_config.json、preprocessor_config.json、video_preprocessor_config.json。提取完用`tools/resource_fingerprint.py`计算fullSHA256和aggregateSHA；记录对象名、offset/length、sourceartifactidentity。只需约13MB资源，不必新下载17GB模型。

报告中的SHA前缀保存在[data/resources-reported.json](../data/resources-reported.json)，仅用于提示明显错资源；不能匹配前缀就当完整identity验证完成。旧转换器official_resources.py与现网前三项不同，不可按该清单把正确生产资源拒绝。

## 18.3 HF 作为替代来源

R1说生产资源逐字节匹配HF短revision1d4bf0f。只有执行者解析该完整revision并把六文件fullSHA与artifact提取结果比对后，才可替代artifact资源用于oracle。无artifact验证时标`HF_RESOURCE_ONLY`，不能升格为G0生产资源PASS。不访问浮动main。

## 18.4 模板与采样不变

评审现场为ReasoningEffort模板，preserve_thinking为true，并有服务端显式保留；旧转换器清单模板却是ThinkingToggle。主差分以真实ReasoningEffort组合，另用原测试fixture验证ThinkingToggle兼容。不要用减少历史reasoning来获得更小渲染文本。

## 18.5 Overlay 安全整合

先冻结diff再应用到新工作树。对每个changedfile记录功能：观测计数、timer移动、JSONLschema、统计传递。若发现改变tokenizer/processor/template输出的修改，停止“A20与A0等价”假设，先为overlay单独差分。

未提供原overlaybytes，所以本包不附伪造patch。执行者生成的overlay.patch、source_inventory.json、image_identity.json置于新证据目录，不改写本包原始review证据。机器路径/用户名可以保留本地，但对外报告脱敏。

## 18.6 构建输入冻结

四个CPUbuild lane共享资源aggregateSHA、源基线、compiler/runtime、commonunicode实现；不同优化diff单独hash。输入request保序序列化、渲染文本也hash；不能同一request文件但模板不同还配对。HTTP还固定modelID/weightswindow/kv/MTP/sampling、代理和客户端形态。
