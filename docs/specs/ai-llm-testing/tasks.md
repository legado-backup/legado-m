# tasks.md — AI-LLM-Testing

> 状态：待实施（已确认）｜开始：2026-08-12

## 1. 基建层（llama-server 托管 + 客户端）

- [x] 1.1 新增 `config_ai.py`（LLAMA_SERVER 路径、MODEL/MMPROJ、PORT=1235、参数对齐用户 .bat）
- [x] 1.2 `lib/llm_server.py`：LlmServerManager（探测复用 / Popen 拉起 / 健康轮询 / 优雅停止 / LlmUnavailableError）
- [x] 1.3 `lib/llm_client.py`：LlmClient（含图消息 / JSON 解析 / 重试 2 次 / 超时）
- [x] 1.4 单测：test_llm_server.py（mock 端口/子进程）、test_llm_client.py（mock 响应）
- [x] 1.5 验证：真实拉起 Qwen3VL，跑通 vision+grounding 最小调用
- [x] 1.6 图像归一化：LlmClient 统一降采样（AI_IMAGE_MAX_DIM）+ 坐标逆向映射工具函数（已知系数精确还原设备坐标）

## 2. AI 判定器

- [x] 2.1 `lib/ai_verifier.py`：AiVerifier（manual 用例 → 组装 ai_prompt+截图 → 结构化判定 → 回填 report.json ai_verdict + 更新 manual_cases.md）
- [x] 2.2 `scripts/ai_verify.py`：独立命令入口（--report 参数）
- [x] 2.3 `run_e2e.py` 接入 `--ai-verify` 开关（manual 用例判定后汇总）
- [x] 2.4 单测：test_ai_verifier.py（mock LlmClient）
- [x] 2.5 验证：跑一次含 manual 用例的 e2e（F-P0-6），确认 ai_verdict 回填

## 3. GUI Agent 执行器

- [x] 3.1 `lib/ai_agent.py`：GuiAgent（观察→决策→动作→验证循环；动作 JSON：tap/swipe/input_text/back/wait/verify）
- [x] 3.2 混合定位 resolve()：uiautomator 优先 → VL 坐标回退（含 scale 校准）
- [x] 3.3 heal 接入：UiExecutor 定位失败时调 GuiAgent 视觉修正（或提供同构接口）
- [x] 3.4 单测：test_ai_agent.py（mock UiExecutor/LlmClient）
- [ ] 3.5 验证：真机演示（书源管理页元素找不到→AI 视觉定位→点击成功）

## 4. 经验层

- [x] 4.1 `lib/ai_experience.py`：AiExperience（load/save/签名失效控制，`ai_tests/experience/ai_experience.json`）
- [x] 4.2 执行器成功经验回写；判定样本记录
- [x] 4.3 单测：test_ai_experience.py

## 5. 收尾

- [x] 5.1 单元测试全绿（`ai_tests/venv/Scripts/python.exe -m pytest` 或现有 test runner）
- [ ] 5.2 文档同步：README / docs/INDEX.md / ai_memory_main
- [ ] 5.3 updateLog.md 追加版本条目
- [ ] 5.4 用户确认（强制检查 2）

## AOAdapt 日志

- 2026-08-12：test_evidence_collector 修复 3 处（包名断言 io.legado.app→io.legado；logcat FATAL 时间戳硬编码改为 datetime.now+1min，消除日期敏感 flaky）；test_run_e2e 修复 3 处过时 V3 降级测试（--diff 不在 handle_v3 范围由 main()5.5 处理；--update-source-map 已实现返回 0，mock SourceImpactAnalyzer）

