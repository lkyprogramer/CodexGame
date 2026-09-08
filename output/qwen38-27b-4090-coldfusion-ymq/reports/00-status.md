# Cold-Fusion YMQ-M 4090 最大窗口试验

模型：[zerodigest/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-YMQ-GGUF](https://huggingface.co/zerodigest/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-YMQ-GGUF) 的 **YMQ-M**（14.6GB）。

- 权重：`/data/models/qwen/qwen38-coldfusion-ymq/`
- 脚本：`/home/hhtele/qwen38-coldfusion-ymq/scripts/run_ladder_nohup.sh`
- 二进制：现网 `llama.cpp-qwen38-20260817`（不换）
- 阶梯：C0 200192 MTP n=2 → C1 245760 → C2 **262144**；C2 失败则 C3 关 MTP
- KV：双侧 q4；无 mmproj；`ctx-checkpoints 4`
- 针：28k/64k，满窗再加 128k/200k/240k；decode 256 tok；工具一条
- EXIT trap restore WORK 18343

下载完自动开阶梯（`wait_and_ladder.sh`）。
