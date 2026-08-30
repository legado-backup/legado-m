# spec.md — AI-LLM-Testing

## Intent

ai_tests 目前依赖确定性规则（RuleAnalyzer 4 条规则）判定用例，manual 用例需人工翻看 ai-prompt.md + 截图才能给出结论；UiExecutor 的 8 类动作是硬编码 capture-replay，元素找不到时依赖滚动查找。本特性用**本地 Qwen3VL-8B** 提供两类 AI 能力：

1. **AI 判定器**：读取 manual 用例的 ai-prompt + 8 类证据（含截图图像），调用 VL 模型进行语义判定，回填 `report.json` 的 `cases[].ai_verdict`，替代人工复核。
2. **GUI Agent 执行器**：视觉驱动屏幕操作——截图 + 目标 → VL 输出动作 JSON（tap/swipe/input/verify）→ 执行 → 循环，定位采用"VL 语义 + uiautomator 精确 bounds"混合方案，用于执行器自愈/智能搜索。

两者共享**自动启动的 llama-server 独立进程**（脱离 LM Studio 手动启动），并通过经验层沉淀已验证的定位与判定样本。

## Scope

**范围内**（全部在 ai_tests/ 内，新增为主）：

- `config_ai.py`：模型/服务器路径、端口、推理参数（源自用户现有 `.bat`）
- `lib/llm_server.py`：LlmServerManager——自动拉起/健康探测/优雅启停 llama-server 子进程
- `lib/llm_client.py`：OpenAI 兼容客户端（支持图像消息）+ 重试 + 结构化 JSON 输出解析
- `lib/ai_verifier.py`：判定器——manual 用例批量判定（含截图）→ ai_verdict 回填
- `lib/ai_agent.py`：GUI Agent——截图→VL→动作 JSON→UiExecutor/坐标执行→循环，含混合定位
- `lib/ai_experience.py`：经验层——已验证元素位置/判定样本 JSON 持久化，跨运行复用
- `run_e2e.py` / `scripts/` 接入开关（`--ai-verify`、执行器 heal 增强）
- 单元测试 + OpenSpec 文档 + updateLog

**范围外**：

- ❌ 不修改 Legado 源码（app/ 下）
- ❌ 不引入远程云模型 / 不依赖 LM Studio
- ❌ 不做完整自主测试规划（TestCase 流程仍由 case.md 驱动；执行器只做步骤内/治愈级自主）

## Approach

### Selected Approach

本地 llama-server 子进程托管 + OpenAI 兼容 API + 双产品（判定器/执行器）+ 混合定位 + 经验层。判定器先打通 manual 判定闭环（复用现有 V4 预留位），执行器作为能力层供现有执行流程的 heal/搜索增强调用。

### Alternatives Considered

| 方案 | 否决原因 |
|------|---------|
| 继续依赖 LM Studio 手动启动 | 用户明确要求脱离；手动加载不可自动化、与用户其它模型占用冲突 |
| 纯 VL 坐标点击（VLM 输出 box 直接 tap） | 实测坐标偏差 ~1.27x/0.84y（内部分辨率缩放失真），超出边界值不可信，点击命中率不可接受 |
| 引入 UI-TARS / 专用 GUI-Agent 模型 | 本地无此模型需重新获取，体积大；Qwen3VL 已具备 grounding + 生态成熟，满足需求 |
| 判定器只用文本 ai-prompt（不加截图） | 丢失视觉证据；截图是 manual 用例最丰富的信息，VL 多模态必须用上 |

### Drawbacks

- 8B 本地模型的语义/定位精度有限：复杂长链动作或罕见界面下可能误判，需 confidence 阈值与 manual 兜底
- 常驻/按需拉起 GPU 显存（~6GB），与用户其它模型（35B）并发时需端口+显存协调
- Grounding 坐标需校准映射表，校准样本需在真实用例中积累（经验层承担）

### Prior Art

- 现有 `rule_analyzer.py` V4 预留（LLM 语义判定）、`ai_prompt_template.j2`、report.json `ai_verdict` 字段
- 用户参考脚本 `E:\llama\start\Qwen3.6-35B-A3B-IMG-Q4_K_P.bat`（llama-server 参数基线）
- Qwen3-VL grounding/GUI-Agent 生态

## Requirements

- R1 **服务器自动托管**：`LlmServerManager` 端口探测（在线则复用）→ 不在线则子进程拉起 → 健康等待 → 进程退出时自动停止；端口/路径/参数配置化
- R2 **配置化**：新增 `config_ai.py`，含 LLAMA_SERVER 路径、模型 GGUF 与 mmproj 路径、端口、上下文、温度等参数；参考 .bat 参数
- R3 **判定器**：消费 manual 用例（ai_prompt + evidence + 截图）→ 结构化判定 `{verdict: pass/fail/manual, confidence, reason, evidence_refs}` → 回填 `report.json` `cases[].ai_verdict` + 更新 manual_cases.md；提供 `--ai-verify` 独立命令与 run_e2e 集成
- R4 **执行器**：`GuiAgent` 循环（观察→决策→动作→再观察），动作 JSON 支持 tap/swipe/input_text/back/wait/verify；**混合定位**：优先 uiautomator 文本/类名精确 bounds，取不到时用 VL 坐标 + 校准系数；提供 heal 接口与现有 UiExecutor 并存
- R5 **经验层**：已验证元素定位/判定样本 JSON 持久化（`ai_tests/experience/`），运行前加载、验证后回写，跨运行复用
- R6 **优雅降级**：模型/服务器不可用时判定器回退规则-only（现状），执行器回退滚动查找，均不阻断流程
- R7 **测试**：每个模块单元测试（mock 无 GPU 可跑）+ 真机/模拟器端到端验证（F-P0-6 manual 用例判定 + 执行器 heal 演示）
- R8 **图像归一化（截图防爆）**：VLM 输入统一降采样：截图 > `AI_IMAGE_MAX_DIM`（默认 640）时先等比缩小再送模型，控制视觉 token 与推理耗时；GUI Navigator 点击仍用**设备原生屏幕坐标**（uiautomator bounds 与分辨率无关），VL 返回的 box 坐标按已知缩放系数逆向映射回设备坐标（系数确定，映射精确）

## Scenarios

### 正常流程
1. 用户跑 `run_e2e.py --ai-verify`：完成 8 证据收集 → RuleAnalyzer 判定 → 出现 manual 用例 → AiVerifier 自动拉起服务器 → 逐用例发送 ai_prompt+截图 → 回填 ai_verdict → 生成报告（含 AI 判定汇总）
2. 执行器 heal：某步骤 UiExecutor 定位失败 → GuiAgent 截图+失败目标 → VL 定位 → 修正选择器/坐标重试 → 成功或超限报告

### 异常流程
- llama-server 启动失败/显存不足 → 降级 rules-only，报告中标注 `ai_unavailable: cause`
- VL 判定 confidence 过低 → 保持 manual，reason 附 AI 观察
- 单步循环超限（max_iterations）→ 判定该步失败，附已执行动作轨迹

### 边界用例
- 空证据/空截图 → 判定器不调用模型，直接 manual
- port 被占用（用户 LM Studio 或其它进程）→ 探测到非本进程服务时仍复用（OpenAI 兼容即可）或换端口
- 双击/长按类动作暂不支持 → 执行器动作集受限并记录