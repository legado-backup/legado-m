"""ai_tests/config_ai.py — 本地视觉大模型（Qwen3VL-8B）配置

AI-LLM-Testing 基建：llama-server 自动托管 + LlmClient 参数。
参数对齐用户参考脚本 E:\\llama\\start\\Qwen3.6-35B-A3B-IMG-Q4_K_P.bat。

🔒 固化层：模型路径/端口为本地环境相关，换机器需修改；其余推理参数不随意升级。
"""
from pathlib import Path

# === llama-server 可执行文件（用户本机） ===
LLAMA_SERVER_PATH = r"E:\llama\llama-server.exe"
LLAMA_WORKDIR = r"E:\llama"

# === Qwen3VL-8B 模型（HauhauCS Uncensored Balanced） ===
AI_MODEL_DIR = Path(r"G:\AI\models\HauhauCS\Qwen3VL-8B-Uncensored-HauhauCS-Balanced")
AI_MODEL_GGUF = AI_MODEL_DIR / "Qwen3VL-8B-Uncensored-HauhauCS-Balanced-Q4_K_M.gguf"
AI_MODEL_MMPROJ = AI_MODEL_DIR / "Qwen3VL-8B-Uncensored-HauhauCS-Balanced-mmproj-f16.gguf"

# === 服务端口（避让 LM Studio 1234） ===
AI_HOST = "127.0.0.1"
AI_PORT = 1235
AI_BASE_URL = f"http://{AI_HOST}:{AI_PORT}"
AI_MODEL_ID = "qwen3vl"  # /v1/models 展示名由 llama-server 决定；客户端仅需合法字符串

# === 服务器托管 ===
AI_HEALTH_TIMEOUT = 90      # 等待健康秒数（实测 ~12s 就绪）
AI_START_TIMEOUT = 120      # 子进程启动窗口
AI_CTX = 8192               # 上下文（单图归一化后 ~700 token，留足多图+长证据）
AI_TEMP = 0                 # 判定/定位用确定性输出

# === 图像归一化（R8/AD-06：截图防爆） ===
AI_IMAGE_MAX_DIM = 640      # 发往 VL 的最长边阈值，超则等比缩小
AI_IMAGE_JPEG_QUALITY = 85  # JPEG 压缩质量

# === LlmClient 调用 ===
AI_REQUEST_TIMEOUT = 300    # 单次请求超时（秒）
AI_MAX_RETRIES = 2          # 失败重试次数
AI_MAX_TOKENS = 1500        # 单次生成上限

# === llama-server 启动参数（对齐用户 .bat，扣除 LLM 无关项） ===
AI_LLAMA_ARGS = [
    "-ngl", "-1",
    "-c", str(AI_CTX),
    "-t", "12",
    "-b", "2048", "-ub", "2048",
    "--no-warmup",
    "--no-mmap",
    "--temp", str(AI_TEMP),
    "--cache-type-k", "q4_0", "--cache-type-v", "q4_0",
    "--flash-attn", "on",
    "--chat-template-kwargs", '{"enable_thinking":false}',
    "--reasoning", "off",
]
