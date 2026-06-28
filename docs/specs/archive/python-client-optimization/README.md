# Python 客户端优化设计

> **状态**：🔄 设计中
> **创建日期**：2026-06-21
> **关联文档**：[simulation-fidelity-95](../simulation-fidelity-95/)（JAR 仿真服务端设计）

---

## 功能概述

Python 客户端是 legado-source-creator Skill 的测试校验层，负责在 AI 生成/优化书源和订阅源后，快速完成测试校验。客户端与 JAR 仿真服务端协作，减少对开源阅读源码的依赖。

### 核心能力

1. **预校验**：在 JAR 测试前，用 Python 快速校验源规则语法和字段完整性（source_validator + rule_precheck）
2. **调试执行**：通过 JAR 仿真服务端执行端到端调试（debug_runner → RuleEngineClient → JAR）
3. **错误诊断**：JAR 失败时，自动诊断错误类型并生成修复建议（error_diagnoser + auto_fixer）
4. **经验管理**：测试前检索历史经验，测试后沉淀新经验（experience_manager + conflict_resolver）
5. **用户交互**：需要用户介入时（登录/验证码/CF破盾），生成标准化交互请求（user_interaction + obstacle_resolver）

### 设计目标

| 目标 | 说明 |
|------|------|
| **减少源码依赖** | AI 使用 Skill 生成源后，无需查阅 Legado 源码即可完成测试校验 |
| **快速反馈** | 预校验 < 3 秒，JAR 调试 < 30 秒，全流程 < 2 分钟 |
| **准确诊断** | JAR 失败时能准确区分源规则问题还是仿真端问题 |
| **自动化率 > 70%** | 70% 的网站生成可用源无需手动操作；30% 需用户协助时提供 AI 指引 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent/Scope/Requirements/Scenarios |
| [design.md](./design.md) | 技术设计：双客户端架构/预校验模块/工作流调整 |
| [tasks.md](./tasks.md) | 任务清单：实施步骤和验收标准 |

---

## 现有架构

### 双客户端架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    legado-source-creator Skill                   │
│                                                                  │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │  tools/ (14个.py)   │    │  scripts/legado_client/ (包)     │ │
│  │  独立辅助工具模块    │    │  结构化核心调试流程              │ │
│  │                     │    │                                  │ │
│  │  • auto_fixer       │    │  client/                         │ │
│  │  • cookie_manager   │    │    • debug_runner (核心入口)     │ │
│  │  • crypto_analyzer  │    │    • rule_engine_client (JAR通信) │ │
│  │  • degradation_chain│    │    • batch_runner (批量测试)     │ │
│  │  • error_translator │    │    • webview_handler (Selenium)  │ │
│  │  • fetch_html       │    │    • user_interaction           │ │
│  │  • html_fetcher     │    │  analyzer/                       │ │
│  │  • interactive_guide│    │    • confidence_evaluator       │ │
│  │  • jvm_helpers      │    │    • error_diagnoser            │ │
│  │  • knowledge_matcher│    │    • parse_strategy             │ │
│  │  • obstacle_resolver│    │    • source_navigation          │ │
│  │  • smart_http_client│    │  experience/                     │ │
│  │  • user_action_min  │    │    • experience_manager         │ │
│  │  • workflow_timer   │    │    • conflict_resolver          │ │
│  └─────────────────────┘    │  utils/                          │ │
│                             │    • config / file_utils / logger│ │
│                             └──────────────────────────────────┘ │
│                                          │                       │
│                                    RuleEngineClient               │
│                                          │                       │
│                              ┌───────────┴───────────┐           │
│                              │  JAR 仿真服务端        │           │
│                              │  (legado-jvm fatJar)  │           │
│                              └───────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### 职责边界

| 层级 | 职责 | 归属 |
|------|------|------|
| **预校验层** | 源规则语法检查、字段完整性校验 | Python（新增 source_validator + rule_precheck） |
| **调试执行层** | 端到端调试（search→detail→toc→content） | JAR 仿真服务端（通过 RuleEngineClient 调用） |
| **错误诊断层** | 错误类型识别、修复建议生成 | Python（error_diagnoser + auto_fixer） |
| **经验管理层** | 历史经验检索、新经验沉淀 | Python（experience_manager + basic-memory） |
| **用户交互层** | 登录/验证码/CF破盾引导 | Python（user_interaction + obstacle_resolver） |

---

## 与 simulation-fidelity-95 的关系

| 方面 | simulation-fidelity-95 | python-client-optimization |
|------|----------------------|---------------------------|
| **关注点** | JAR 仿真服务端与真机的行为对齐 | Python 客户端的测试校验流程优化 |
| **设计目标** | 100% 测试校验准确性 | 自动化率 > 70%，快速反馈 |
| **依赖关系** | JAR 是被调用方 | Python 客户端是调用方 |
| **协作方式** | JAR 提供核心规则引擎执行 | Python 负责预校验+诊断+经验+交互 |

两者互补：JAR 保证"执行结果与真机一致"，Python 客户端保证"测试流程高效自动化"。
