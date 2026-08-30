# AI-LLM-Testing — 本地视觉大模型接入 ai_tests

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> **目标**：将本地 Qwen3VL-8B（GGUF，llama-server 直启，脱离 LM Studio）接入 ai_tests，提供两类能力：**AI 判定器**（manual 用例自动判定并回填 `ai_verdict`）+ **GUI Agent 执行器**（视觉驱动元素定位与屏幕操作），并沉淀跨运行经验。
>
> **状态**：待实施（文档已确认）
> **创建**：2026-08-12

## 文档导航

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope / Approach / Alternatives / Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / ADR / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 核心结论（探针已验证）

| 项 | 结论 |
|----|------|
| 模型 | `G:\AI\models\HauhauCS\Qwen3VL-8B-Uncensored-HauhauCS-Balanced\`（Q4_K_M 4.7GB + mmproj f16 1.1GB） |
| 启动 | `E:\llama\llama-server.exe` 独立子进程，12s 健康，OpenAI 兼容 API，端口 1235（避让 LM Studio 1234） |
| 视觉 | ✅ 能准确描述界面状态（书源列表/开关状态等） |
| 定位 | ✅ 支持 `<box>[[x1,y1,x2,y2]]</box>`，但坐标有系统偏差（~1.27x/0.84y），**不可直接点击**，须混合 uiautomator 精确定位 |
| 弃用 | locateanything-3b-imatrix 纯文本无视觉，不适用 |

## 接入点（现有 V4 预留位）

- `rule_analyzer.py` manual 出口生成 `reports/manual_cases/{tc}_ai-prompt.md`，report.json 预留 `cases[].ai_verdict`
- `ai_prompt_template.j2` 判定器模板已存在未启用
- `config.py` CRASH_PATTERNS 注明"升级路径:接入 LLM 语义分析(V4)"
