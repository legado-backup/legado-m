# design.md — AI-LLM-Testing

## Technical Approach

```
┌──────────────────────── ai_tests/ ─────────────────────────┐
│  config_ai.py         模型/服务器/端口/参数（参考 .bat）     │
│  lib/llm_server.py    LlmServerManager（自动托管）          │
│  lib/llm_client.py    OpenAI兼容客户端（含图+JSON解析）      │
│  lib/ai_verifier.py   判定器 → 回填 ai_verdict              │
│  lib/ai_agent.py      GUI Agent 执行器（混合定位）           │
│  lib/ai_experience.py 经验层（JSON 持久化）                 │
│  run_e2e.py/scripts    --ai-verify / heal 增强接入          │
└──────────────────────────────┬─────────────────────────────┘
                               │ OpenAI 兼容 /v1/chat/completions
                    ┌──────────▼──────────┐
                    │ llama-server.exe    │
                    │ 127.0.0.1:1235      │
                    │ Qwen3VL Q4_K_M + mmproj f16
                    └─────────────────────┘
```

### 判定器数据流

```
report.json (manual 用例)
  → AiVerifier.verify_case(tc, ai_prompt, evidence, screenshots)
  → prompt = ai_prompt + 截图(多张, base64) + 结构化指令(要求 JSON)
  → LlmClient.chat_with_images()
  → 解析 {verdict, confidence, reason, evidence_refs}
  → 回填 report.json cases[].ai_verdict
  → 更新 manual_cases.md（AI 已判定的用例标注 verdict）
```

### 执行器数据流（单步）

```
[目标/失败信息] → GuiAgent.step()
  1. screenshot + ui_xml 快照
  2. 混合定位 resolve(target):
     a. 先 UiExecutor._get_element(text/类名) → 精确 bounds → 直接点击
     b. 取不到 → VL 视觉定位（含校准系数 scale 映射）→ 坐标点击
  3. 动作执行（tap/swipe/input/back/wait）
  4. 再观察（screenshot+ui_xml）→ 验证目标是否达成
  5. 未达成 → 循环至 max_iterations
  6. 成功经验回写 ai_experience.json
```

## Architecture Decisions

### AD-01: llama-server 独立子进程自动托管
- **Context**: 现有依赖 LM Studio 手动加载，不可自动化；用户已有 `E:\llama\llama-server.exe` 与 `.bat` 参数基线
- **Concern**: 自动拉起/健康探测/进程生命周期
- **Decision**: `LlmServerManager`：`subprocess.Popen` 拉起；`/health` 轮询（12s 内就绪，实测）；探测端口已有 OpenAI 兼容服务则复用；进程 `terminate()` 优雅停止；`--reasoning off` 关闭思考链加速
- **Goal**: 一行命令即可获得模型服务，无手动步骤
- **Tradeoff**: 显存占用（~6GB）；与本机其它 llama-server 并发时需端口协调
- **Status**: Accepted

### AD-02: 混合定位（VL 语义 + uiautomator 精确 bounds）
- **Context**: 实测 Qwen3VL grounding 坐标有系统偏差（~1.27x/0.84y，疑似内部分辨率缩放），box 可能超出图像边界
- **Concern**: 点击命中率即测试可信度
- **Decision**: 优先 uiautomator 文本/类名解析精确 bounds（确定性 100%）；仅当其不可用时才回退 VL 坐标，并用 `scale_x=img_w/box_span` 校准系数映射
- **Goal**: 点击 100% 可复现，VL 仅兜底视觉语义
- **Tradeoff**: uiautomator 取不到时（纯图像元素）命中率依赖校准质量
- **Status**: Accepted

### AD-03: 统一 OpenAI 兼容 API 契约
- **Context**: llama-server 原生暴露 `/v1/chat/completions`；判定器与执行器都走多模态消息
- **Decision**: `LlmClient` 单入口，`messages=[{text}, {image_url base64}]`，`max_tokens/temperature` 可配，输出要求 JSON 结构（`response_format` 或指令式），异常重试 2 次+超时
- **Goal**: 一个客户端服务两个产品，将来可平滑切换任意 OpenAI 兼容后端
- **Tradeoff**: 绑定 llama-server/OpenAI 协议，不支持其它协议后端（当前无需）
- **Status**: Accepted

### AD-04: 判定器接入 manual 出口（不动既有规则链）
- **Context**: RuleAnalyzer 4 条规则 + 置信度强制是确定性门禁，已稳定
- **Decision**: 判定器**只在 verdict=manual 时介入**（含 confidence<70 强转 manual），不改变 pass/fail/warning 的规则判定；LLM 判定结果写入 ai_verdict（附置信度），不覆盖规则 verdict
- **Goal**: 保持确定性优先，AI 只处理人工复核层，风险可控
- **Tradeoff**: 规则误判的 pass/fail 不会由 AI 纠正（符合"确定性优先"定位，后续可加 AI 复核开关）
- **Status**: Accepted

### AD-05: 经验层 JSON 持久化 + 显式导入导出
- **Context**: 定位/判定结果应在跨运行间复用，避免每次重新花 token 与时间
- **Decision**: `ai_tests/experience/ai_experience.json`：`{elements: {screen: {desc: coords/bounds}}, verdicts: [{hash, verdict, confidence}]}`；运行前 `load()`，验证成功 `save()`；文件冲突时以新样本覆盖旧（记录版本）
- **Goal**: 逐步自进化：已验证元素下次直接命中，判定样本可做 few-shot
- **Tradeoff**: 经验可能过期（UI 改版）；用 screen+desc 签名做失效控制
- **Status**: Accepted

### AD-06: VLM 输入降采样归一化（截图防爆）
- **Context**: 用户指出——模拟器若以高分屏启动，截图超大（1080x2400+），base64 体积大、视觉 token 多、推理变慢，甚至超出模型上下文（-c 8192）；实测 800x1280 单图已占 ~1000+ token
- **Decision**: 发送前统一等比降采样：`AI_IMAGE_MAX_DIM=640`（最长边），在 LlmClient 统一处理（PIL 缩放 + JPEG 压缩），**所有**发往 VL 的图像都走此管道；坐标映射：VL 返回 box 在降采样图坐标系，逆映射回设备坐标 `device = vl * (device_dim / feed_dim)`，系数是**已知确定值**，与模型内部失真无关
- **Goal**: 单图视觉 token 恒定可控（<~700），推理快，多图/长文本不爆上下文
- **Tradeoff**: 小图上精细元素（小开关/小图标）语义识别能力略降；GUI 点击锚点仍以 uiautomator bounds 为准，VL 仅兜底，故可接受
- **Status**: Accepted

## Data Flow

1. **配置**: `config_ai.py` 提供 LLAMA_SERVER 路径、MODEL/MMPROJ 路径、PORT=1235、CTX=8192、-ngl -1、temp 等（对齐用户 .bat：flash-attn on、cache q4_0、enable_thinking false、reasoning off）
2. **启动**: `LlmServerManager.ensure_online()` → 探测 `/health` → 未在线则 Popen → 轮询健康（超时 60s）→ 失败抛 `LlmUnavailableError`（调用方降级）
3. **判定**: `run_e2e --ai-verify` → 遍历 report.json manual 用例 → 每用例组装 prompt+截图 → `ai_verdict` 回填 → 汇总报告
4. **执行**: `GuiAgent.step(target, action_hint)` 供 UiExecutor heal 与新增 AI 步骤调用 → 混合定位 → 执行 → 验证 → 经验回写

## File Changes

### 新增
| 文件 | 职责 |
|------|------|
| `ai_tests/config_ai.py` | 模型/服务器/端口/推理参数 + `AI_IMAGE_MAX_DIM=640` 等图像归一化常量 |
| `ai_tests/lib/llm_server.py` | `LlmServerManager` + `LlmUnavailableError` |
| `ai_tests/lib/llm_client.py` | `LlmClient`（chat_with_images / **图像降采样归一化** / 结构化 JSON / 重试） |
| `ai_tests/lib/ai_verifier.py` | `AiVerifier`（判定+回填） |
| `ai_tests/lib/ai_agent.py` | `GuiAgent`（循环+混合定位+动作执行） |
| `ai_tests/lib/ai_experience.py` | `AiExperience`（load/save/签名） |
| `ai_tests/tests/test_llm_server.py` | 单测（mock 子进程/端口） |
| `ai_tests/tests/test_llm_client.py` | 单测（mock 响应/重试） |
| `ai_tests/tests/test_ai_verifier.py` | 单测（mock LlmClient） |
| `ai_tests/tests/test_ai_agent.py` | 单测（mock UiExecutor） |
| `ai_tests/tests/test_ai_experience.py` | 单测 |
| `ai_tests/scripts/ai_verify.py` | 独立命令入口（跑判定器） |

### 修改
| 文件 | 变更 |
|------|------|
| `ai_tests/run_e2e.py` | 新增 `--ai-verify` 开关，manual 后接判定器 |
| `ai_tests/lib/rule_analyzer.py` | （可选）`_check_expect_match` 注释升级路径引用；不动逻辑 |
| `ai_tests/README.md` | 新增 AI 能力文档段 |
| `app/src/main/assets/updateLog.md` | 版本条目（编译前） |
