# 13｜固定来源与审阅边界

所有SOURCE条目固定完整commit，不引用浮动HEAD的API当实施依据。Git blob SHA见`../source-lock.json`；本包未附完整原仓，也未完成原仓构建。

## S00｜提交元数据
[44a2c6c完整提交](https://github.com/tensorninja/ninfer-4090/commit/44a2c6c3392c9d51e76a895ed97bf1867530d252)：board energy归因，request log schema18→19。

## 固定源码
### S01｜encode_rendered_chat：整段编码后逐边界重新编码前缀
[src/targets/qwen3_8/impl/frontend/processor.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/processor.cpp#L530-L615)  
Git blob: `3ee949d441ab0c8ce537f672a9afd73f070cfb13`。行号是审阅导航；以该commit完整文件为准。

### S02｜旧版只有 encode/decode，无 encode_with_boundaries
[src/targets/qwen3_8/impl/frontend/tokenizer.h](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/tokenizer.h#L1-L65)  
Git blob: `e90338a3d5d7bfad98aec62269616dcf8a000f39`。行号是审阅导航；以该commit完整文件为准。

### S03｜added token 配置限制、按 ID 排序
[src/targets/qwen3_8/impl/frontend/tokenizer.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/tokenizer.cpp#L160-L303)  
Git blob: `1f4e15f4a0b3539045ee27cfe480dfcb40f06d56`。行号是审阅导航；以该commit完整文件为准。

### S04｜NFC、Qwen 分词、字符串 BPE 全候选扫描
[src/targets/qwen3_8/impl/frontend/tokenizer.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/tokenizer.cpp#L418-L601)  
Git blob: `1f4e15f4a0b3539045ee27cfe480dfcb40f06d56`。行号是审阅导航；以该commit完整文件为准。

### S05｜added token 最早位置匹配、相同位置保留较早 ID
[src/targets/qwen3_8/impl/frontend/tokenizer.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/tokenizer.cpp#L636-L674)  
Git blob: `1f4e15f4a0b3539045ee27cfe480dfcb40f06d56`。行号是审阅导航；以该commit完整文件为准。

### S06｜StablePrefix/StableTurn/Rolling hints 随工具历史生成
[src/targets/qwen3_8/impl/frontend/chat_template.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/chat_template.cpp#L305-L497)  
Git blob: `9795c6f4ca0ed9f43ebd9e01aeaa30883ebfa2c8`。行号是审阅导航；以该commit完整文件为准。

### S07｜prepare/count_tokens/prepare_tokens 三条路径
[src/targets/qwen3_8/impl/frontend/frontend.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/frontend.cpp#L848-L990)  
Git blob: `47ca07a8b285f7df6a47896f984699f179e9813e`。行号是审阅导航；以该commit完整文件为准。

### S08｜本提交的 PromptIdentity 和 PrepareStats
[src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/export/ninfer/targets/qwen3_8/prepared_prompt.h#L40-L110)  
Git blob: `f355971c481c2752546ac5efee11bb3fa51aafb9`。行号是审阅导航；以该commit完整文件为准。

### S09｜Frontend 持有 shared_ptr<const Impl>；工厂签名
[src/targets/qwen3_8/export/ninfer/targets/qwen3_8/frontend.h](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/export/ninfer/targets/qwen3_8/frontend.h#L112-L153)  
Git blob: `c2d8ddd4c73c1197e40602be707ae1ad00a3e3be`。行号是审阅导航；以该commit完整文件为准。

### S10｜真实 CTest target 与 SKIP_RETURN_CODE 77
[tests/CMakeLists.txt](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/tests/CMakeLists.txt#L1-L220)  
Git blob: `7c3644b1605d8d3e5ad32b4417c48761e352046e`。行号是审阅导航；以该commit完整文件为准。

### S11｜FrontendTestAccess、两种模板 fixture、合成 tokenizer resources
[tests/targets/qwen3_8/test_frontend.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/tests/targets/qwen3_8/test_frontend.cpp#L1-L148)  
Git blob: `e5b00db7ea8db2ca7bf39dcc8f3d7cd4c06f8660`。行号是审阅导航；以该commit完整文件为准。

### S12｜C++20、CUDA>=12.8、sm_89、BUILD_TESTING
[CMakeLists.txt](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/CMakeLists.txt#L1-L135)  
Git blob: `c61d22f2e8c67415d5ca001570e917d3ada4ea46`。行号是审阅导航；以该commit完整文件为准。

### S13｜frontend 源文件进入 ninfer_engine
[src/targets/qwen3_8/CMakeLists.txt](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/CMakeLists.txt#L1-L19)  
Git blob: `453d5c27ac86ad44275c69acccebad6390e724ab`。行号是审阅导航；以该commit完整文件为准。

### S14｜原仓治理规则、产品目标及所有权边界
[AGENTS.md](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/AGENTS.md#L1-L230)  
Git blob: `9fe1fa110b946faabeb6980f153f4918f6329bb6`。行号是审阅导航；以该commit完整文件为准。

### S15｜六份嵌入 frontend 资源的绑定/提取
[src/targets/qwen3_8/impl/frontend/resources.cpp](https://github.com/tensorninja/ninfer-4090/blob/44a2c6c3392c9d51e76a895ed97bf1867530d252/src/targets/qwen3_8/impl/frontend/resources.cpp#L1-L47)  
Git blob: `7a6f936b9a9e5ec854dbef60b0146c250442bb1a`。行号是审阅导航；以该commit完整文件为准。

## 用户证据
用户在本对话提供2026-09-18、9-19/20及9-22/23诊断汇总；最新摘要结构化保存在data目录。未获得原始request JSONL、请求正文、prepare-detail补丁或本次主机访问。

## 资料构建限制
GitHub连接器读取了固定源文件及commit元数据。本会话容器不能直接解析GitHub域名，未成功clone完整仓库；因此验证只覆盖文档包与附带辅助工具，不是源代码编译。
