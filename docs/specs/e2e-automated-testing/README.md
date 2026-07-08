# Legado AI 自动化测试基础设施（AI Tests Infrastructure）

> **状态**：🔄 设计中（第三版 V3，基于用户深度反馈再次重构）
> **创建日期**：2026-07-07
> **V2 调整日期**：2026-07-07
> **V3 调整日期**：2026-07-07
> **优先级**：P0（永久影响 AI 代码开发工作流，是 OpenSpec 强制子流程）
> **核心原则**：固化流程、固化脚本、固化证据；让 AI 越来越顺手、越来越自动，持续降低用户测试依赖

---

## 一、功能概述

### 1.1 V2→V3 核心理念升级

| 维度 | V2（已采纳） | V3（再次升级） |
|------|------------|---------------|
| **核心理念** | "AI 开发工作流永久基础设施" | **"AI 越来越顺手、持续降低用户测试依赖"** |
| **测试用例机制** | 仅 MD 单轨 | **双轨制：MD 用例 + Python 源码生成用例** |
| **源码利用** | 不读源码 | **基于源码做深度定制脚本 + 影响范围分析** |
| **影响范围分析** | 无 | **git diff → 受影响 Activity → 自动选复测用例** |
| **用例覆盖策略** | 14 份存量用例 | **三波覆盖（存量→核心模块→Bug 反向补充）** |
| **流程验证** | 仅端到端跑通 | **三阶段（单元+端到端+流程注入验证）** |
| **反馈闭环** | 无 | **失败 → 沉淀规则库 → 提示词调优 → 下一轮更准** |
| **代码模块数** | 7 个（M1-M7） | **9 个（M1-M9，新增 M8 源码影响分析、M9 源码→测试生成器）** |
| **任务规模** | 17 阶段 128 子任务 | **22 阶段 165 子任务** |

### 1.2 V3 核心命题

**"流程你规划你用，你或其他 AI 用起来越来越顺手，并且能越来越自动化测试，解决用户自己测试的痛点。"**

V3 在 V2 基础上回答四个根本问题：

1. **如何持续构建测试用例？** → 双轨制 + 三波覆盖 + 用例生命周期管理
2. **改动了哪些源码？影响哪些前端页面？** → M8 源码影响分析器 + source_map.json
3. **非多模态如何精准自动化？** → M9 源码→测试生成器，元素 ID 来自源码
4. **如何让 AI 越来越懂？** → 固化层 vs 持续迭代层分类 + 反馈闭环

### 1.3 核心问题（V2 沿用）

当前 OpenSpec 工作流（[docs/project-rules/openspec-workflow.md](../../project-rules/openspec-workflow.md)）的"步骤 5（开发实施）→ 步骤 6（用户审核）"之间**缺少自动化端到端验证环节**：

```
现状：
  步骤 5: 编译通过 + 单元测试 → 步骤 6: 用户审核（基于 AI 描述）
                                    ↓
                          用户必须手动装 APK 到手机/模拟器
                          按 docs/tests/*.md 逐用例操作 UI
                          adb logcat 收集日志 → 丢给 AI 分析
                          每轮回归 2-4 小时
```

```
目标（V3）：
  步骤 5: 编译通过 + 单元测试
    ↓ 新增 ↓
  步骤 5.5: AI 自动端到端测试（本系统）
    ├── 5.5.1 git diff → 源码影响分析 → 自动选受影响用例（V3 新增）
    ├── 5.5.2 自动发现最新 APK + 启动 MEmu + 安装
    ├── 5.5.3 自动跑双轨用例（MD 通用 + Python 精准）
    ├── 5.5.4 自动收集 8 类证据
    ├── 5.5.5 规则判定 pass/warning/fail/manual
    ├── 5.5.6 manual 用例由 AI agent 对话介入分析
    ├── 5.5.7 输出 Markdown + JSON + manual 三件套报告
    └── 5.5.8 失败案例 → 沉淀规则库 + 调优提示词（V3 新增反馈闭环）
    ↓
  步骤 6: 用户审核（基于自动测试报告，秒级决策）
```

### 1.4 核心能力（V3：九大模块 + 四大规范）

#### 1.4.1 九大代码模块（`ai_tests/lib/`）

| 模块 | 职责 | V3 状态 |
|------|------|---------|
| **M1 模拟器控制** | 启停 MEmu、ADB 连接 | V2 沿用 |
| **M2 APK 部署** | 自动发现+安装+启动+等待首屏 | V2 沿用 |
| **M3 用例解析器** | MD → 结构化步骤 JSON + 双轨调度 | V3 扩展双轨 |
| **M4 UI 执行器** | uiautomator2 操作 UI | V2 沿用 |
| **M5 证据收集器** | 收集 8 类证据 | V2 沿用 |
| **M6 规则分析器** | 规则判定 + 生成 manual 提示词 | V2 沿用 |
| **M7 报告生成器** | Markdown + JSON + manual 三件套 | V2 沿用 |
| **M8 源码影响分析器** ⭐ V3 新增 | git diff → source_map.json 反向追踪 → 自动选复测用例 | V3 新增 |
| **M9 源码→测试生成器** ⭐ V3 新增 | 基于 Activity 源码生成 Python 测试骨架 | V3 新增 |

#### 1.4.2 四大规范文档（固化到 `docs/project-rules/`）

| 规范 | 路径 | 强制内容 |
|------|------|---------|
| **AI 自动测试工作流** | `docs/project-rules/ai_e2e_testing_workflow.md` | OpenSpec 步骤 5.5 的强制流程、AI agent 协作接口、源码影响分析触发 |
| **测试用例设计指南** | `docs/project-rules/test-case-design-guide.md` | 教 AI 设计可自动化测试用例（MD 模板+步骤语义化+预期类型+双轨制） |
| **修改 OpenSpec 工作流** | `docs/project-rules/openspec-workflow.md`（修改） | 在步骤 5/6 之间嵌入步骤 5.5（含 5.5.1 源码影响分析、5.5.8 反馈闭环） |
| **修改 AGENTS.md** | `AGENTS.md`（修改） | 添加"AI 自动测试"强制规则条目，引用三大子规范 |

### 1.5 双轨制测试用例机制（V3 新增）

**核心痛点**：单一 MD 用例对所有场景一视同仁，复杂交互无法精准化。但纯 Python 又难以人工审阅。

**方案**：MD 用例 + Python 用例双轨，按场景选择

| 轨道 | 适用场景 | 元素定位来源 | 执行优先级 |
|------|---------|-------------|-----------|
| **A 轨：MD 用例** | 流程性、可读性高、简单断言 | 通用正则解析（text/描述） | 同 TC-ID 时降级 |
| **B 轨：Python 用例** | 复杂交互、性能敏感、精准断言 | 源码生成的 resource-id | 同 TC-ID 时优先 |

**B 轨 Python 用例生成流程**：
```
1. AI 通过 OpenSpec 实施新功能 → 改动 Activity 源码
2. M9 自动扫描改动 Activity：
   - setContentView / Compose setContent
   - findViewById / viewBinding 引用
   - R.id.xxx resource-id
   - onClickListener 跳转目标
3. 生成 Python 骨架到 ai_tests/cases/{module}/auto_{tc_id}.py
4. AI 补全业务逻辑（步骤、断言、证据收集）
5. 纳入存量用例库
```

### 1.6 三波用例覆盖策略（V3 新增）

**当前现状**：`docs/tests/` 14 份 P0/P1 用例，但开源阅读有 50+ 功能模块未覆盖。

**三波覆盖规划**：

| 波次 | 范围 | 用例量 | 完成周期 | 触发节奏 |
|------|------|--------|---------|---------|
| **第一波** | 现有 14 份存量用例 | 14 | MVP-4 阶段 | 测试系统本身验证 |
| **第二波** | 核心模块优先级矩阵 | ~80 | 持续 3 个月 | 每 sprint 覆盖一个模块 |
| **第三波** | Bug history 反向补充 | ~50 | 持续 6 个月 | 每个修复过的 bug 都补一个用例 |

**核心模块优先级矩阵（第二波）**：

| 优先级 | 模块 | 用例数 | 关联源码根 |
|--------|------|--------|-----------|
| P0 | 调试工具 | 5 | DebugActivity.kt |
| P0 | 书架 | 8 | BookshelfActivity.kt |
| P0 | 书源管理 | 10 | BookSourceActivity.kt |
| P0 | 阅读 | 12 | ReadBookActivity.kt |
| P1 | 搜索 | 6 | SearchActivity.kt |
| P1 | 订阅源 | 8 | RssSourceActivity.kt |
| P1 | 设置 | 8 | SettingsActivity.kt |
| P2 | 备份/恢复 | 6 | BackupActivity.kt |
| P2 | 导入/导出 | 6 | ImportActivity.kt |
| P3 | 其他 | 20+ | 各类 Activity |

### 1.7 8 种非多模态验证手段（V2 沿用）

由于用户当前 AI 大模型**非多模态**，无法识别截图视觉内容。系统通过 8 类**文本可读证据**实现自动判定：

| # | 验证手段 | 实现命令 | 判定能力 | 适用场景 |
|---|---------|---------|---------|---------|
| 1 | **logcat 日志** | `adb logcat -v threadtime *:W` | FATAL/ANR/Exception/CRASH 关键字 | 崩溃/异常/ANR |
| 2 | **UI XML 层级** | `uiautomator2.dump_hierarchy()` | 元素是否存在/文本内容 | 页面跳转/按钮显示/输入内容 |
| 3 | **截图（人工证据）** | `uiautomator2.screenshot()` | 不参与自动判定 | 用户复核证据 |
| 4 | **Activity 栈** | `adb shell dumpsys activity top` | 当前 Activity/Fragment 名称 | 页面跳转验证 |
| 5 | **数据库状态** | `adb shell run-at io.legado.app sqlite3 ...` | 书源/书架/RSS 数据 | 数据写入验证 |
| 6 | **SharedPreferences** | `adb shell run-at cat /data/data/.../shared_prefs/*.xml` | 配置项值 | 配置变更验证 |
| 7 | **App Web 接口** | `curl http://localhost:8080/...` | Web 端备份/书架 API | F-P0-3 Web 备份等功能 |
| 8 | **进程/内存状态** | `adb shell dumpsys meminfo io.legado.app` | App 是否存活/内存占用 | 内存泄漏检测/进程存活 |

### 1.8 测试前置资源策略（V2 沿用）

每个测试用例必须明确前置资源归属：

| 资源类型 | 归属 | 示例 | 提供方式 |
|---------|------|------|---------|
| **AI 自备资源** | AI 自动准备 | HTTP 探测站点（httpbin.org）、ping 目标（baidu.com）、测试字符串、URL | 测试脚本内置常量 |
| **用户必供资源** | 用户提供 | 真实书源 JSON、订阅源 JSON、登录态 Cookie | `ai_tests/cases/{module}/preconditions/` 目录 |
| **共享资源** | 一次性配置 | MEmu 实例 0、Python venv、ADB 路径 | `ai_tests/config.py` |

### 1.9 固化层 vs 持续迭代层（V3 新增）

**核心原则**：明确哪些是 AI 不应修改的基础设施，哪些是 AI 不断改进的能力。

#### 🔒 固化层（基础设施，AI 不应修改）

| 文件 | 说明 |
|------|------|
| `ai_tests/lib/memu_controller.py` | M1 模拟器控制 |
| `ai_tests/lib/apk_deployer.py` | M2 APK 部署 |
| `ai_tests/lib/case_parser.py` | M3 用例解析器 |
| `ai_tests/lib/ui_executor.py` | M4 UI 执行器 |
| `ai_tests/lib/evidence_collector.py` | M5 证据收集器 |
| `ai_tests/lib/rule_analyzer.py` | M6 规则分析器 |
| `ai_tests/lib/report_generator.py` | M7 报告生成器 |
| `ai_tests/lib/source_impact_analyzer.py` | M8 源码影响分析器（V3 新增） |
| `ai_tests/lib/source_test_generator.py` | M9 源码→测试生成器（V3 新增） |
| `ai_tests/run_e2e.py` | 编排入口 |
| `ai_tests/config.py` 中的路径常量、超时 | 基础配置 |
| `docs/project-rules/ai_e2e_testing_workflow.md` | 工作流子规范 |
| `docs/project-rules/test-case-design-guide.md` | 用例设计指南 |
| `AGENTS.md` 中的强制规则 | 规范 |

#### 🔄 持续迭代层（AI 不断改进）

| 文件 | 迭代节奏 | 谁迭代 |
|------|---------|-------|
| `ai_tests/cases/*/case.md` | 每功能迭代 | AI 生成 + 用户审核 |
| `ai_tests/cases/*/auto_*.py` | 每源码改动 | AI 基于 M9 生成 |
| `ai_tests/lib/source_map.json` | 每新增 Activity | AI 维护 |
| `ai_tests/config.py` 中的 `CRASH_PATTERNS` | 每轮测试后 | 基于失败案例扩展 |
| `ai_tests/config.py` 中的 `DB_QUERIES` | 每新增模块 | 基于源码 Dao 扩展 |
| `ai_tests/templates/ai_prompt_template.j2` | 每轮 manual 用例后 | 基于经验调优 |
| `ai_tests/cases/{module}/preconditions/` | 每模块 | 用户必供 |
| `ai_tests/docs/known_issues.md` | 每发现新陷阱 | AI 沉淀 |
| `ai_tests/docs/regression_history.md` | 每轮回归 | AI 记录趋势 |

### 1.10 反馈闭环机制（V3 新增）

**核心命题**：让 AI 越来越顺手、越来越自动。

```
       ┌─────────────────────────────────────────────┐
       ↓                                             │
   测试执行 → 失败案例 → 根因分析                       │
                ↓                                     │
       ┌────────┴────────┐                           │
       ↓                 ↓                           │
   规则库扩展         提示词调优                       │
   (CRASH_PATTERNS)  (ai_prompt)                     │
       ↓                 ↓                           │
       └────────┬────────┘                           │
                ↓                                     │
   known_issues.md 沉淀（陷阱库）                      │
                ↓                                     │
   下一轮测试更准 → 越来越少 manual → 越来越少用户介入  │
                ↓                                     │
       ┌────────┴────────┐                           │
       ↓                 ↓                           │
   用例库扩展         三波覆盖推进                     │
   (Bug 反向补充)    (第二波/第三波)                   │
       ↓                 ↓                           │
       └────────┬────────┘                           │
                └──────────────────────────────────→┘
                  （持续循环）
```

### 1.11 三阶段流程验证（V3 新增）

**V2 痛点**：流程规划完毕后，怎么证明流程能跑通？光跑通 14 用例不等于流程跑通。

**V3 方案**：三阶段验证

| 阶段 | 内容 | V 状态 |
|------|------|--------|
| **A 单元层验证** | 每模块独立验证（mock 数据） | V2 已有 |
| **B 端到端验证** | 14 用例全跑通（≤ 30 分钟） | V2 已有 |
| **C 流程注入验证** ⭐ | 让另一个 AI agent 按 V3 流程做一次 /openspec，验证步骤 5.5 能被正确执行 | **V3 新增** |

**阶段 C 验证清单**：
- [ ] AI agent 能正确执行步骤 5.5.1（git diff → 源码影响分析）
- [ ] AI agent 能正确执行步骤 5.5.2-5.5.7（自动装机+测试+报告）
- [ ] AI agent 能正确生成 manual 用例 + ai-prompt.md
- [ ] AI agent 能被另一个 AI 读取并判定 manual 用例
- [ ] AI agent 能正确触发复测（基于 affected_modules）
- [ ] AI agent 能正确执行步骤 5.5.8（反馈闭环：沉淀规则、调优提示词）
- [ ] 输出：流程审计报告（pass/fail，每项打分）

### 1.12 已探测的环境基线（V2 沿用）

| 资源 | 路径 | 状态 |
|------|------|------|
| 逍遥模拟器 | `D:\Program Files\Microvirt\MEmu` | ✅ v9.5.3 |
| 命令行管理工具 | `D:\Program Files\Microvirt\MEmu\memuc.exe` | ✅ |
| ADB | `D:\Program Files\Microvirt\MEmu\adb.exe` | ✅ |
| MEmu 实例 0 | Android 9 / API 28 / MI 9 / 720x1280 / x86_64 | ✅ 已实测可启动 |
| ADB 端口 | 127.0.0.1:21503 | ✅ memuc 自动连接 |
| Python | `D:\Program Files\Python312\python.exe` 3.12.10 | ✅ |
| **APK 打包目录** | `app\build\outputs\apk\app\debug\` | ✅ 当前包：`legado_app_3.26.070715.apk` |
| 测试用例源 | `docs/tests/*.md` 14 份 | ✅ 已规范 |
| 历史日志样本 | `temp/tmp/logs_extracted/logs/*.txt` | ✅ 训练规则匹配 |
| **源码根** | `app/src/main/java/io/legado/app/` | ✅ M8/M9 输入 |

### 1.13 预期收益（V3 更新）

| 维度 | 当前 | V3 自动化后 | 提升 |
|------|------|------------|------|
| 单轮回归耗时 | 2-4 小时 | ≤ 30 分钟 | -85% |
| 用户介入次数 | 70+ 次 | 仅 manual 用例（< 20%）→ 持续降低 | -80% → 持续优化 |
| 异常检出率 | 主观判断 | 8 种证据客观扫描 | +200% |
| 报告可追溯性 | 无 | 截图+日志+XML+Activity+DB+Prefs 全保留 | 全新能力 |
| 可复用性 | 每次从头 | 一键复用 | 全新能力 |
| AI agent 协作 | 无 | JSON 报告机器可读 + manual 提示词引导 | 全新能力 |
| OpenSpec 工作流 | 缺自动验证 | 步骤 5.5 强制嵌入（8 子步骤） | 流程升级 |
| 测试用例设计 | 无规范 | 双轨制 + 子规范教 AI 写可自动化用例 | 规范化 |
| **源码影响分析** | 无 | git diff → 受影响 Activity → 自动复测 | V3 全新能力 |
| **源码→脚本生成** | 无 | 基于 Activity 源码生成 Python 测试骨架 | V3 全新能力 |
| **反馈闭环** | 无 | 失败 → 沉淀规则 → 调优提示词 → 下一轮更准 | V3 全新能力 |
| **持续降低用户依赖** | 100% 人工 | 70% 自动 → 80% → 90% → 持续提升 | V3 核心价值 |

---

## 二、文档索引

### 2.1 OpenSpec 四文档（V3）

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent / Scope（V3 含 S14-S17 新范围项）/ Approach（含 Alternatives + Drawbacks + Prior Art）/ Requirements（V3 含 FR-13/14/15）/ Scenarios |
| [design.md](./design.md) | Technical Approach（三层架构 + 8 类证据 + V3 双轨用例 + M8/M9）/ Architecture Decisions（V3 含 15 条 ADR）/ Data Flow / File Changes |
| [tasks.md](./tasks.md) | V3：22 阶段 165 子任务（含 M8/M9、双轨用例、流程注入验证、反馈闭环）+ AOAdapt 日志 |

### 2.2 关联资源（V2 沿用）

| 资源 | 路径 | 用途 |
|------|------|------|
| 测试用例源 | [docs/tests/](../../tests/) | M3 用例解析器的输入（存量 14 份） |
| 历史日志样本 | [temp/tmp/logs_extracted/](../../../temp/tmp/logs_extracted/) | 规则匹配关键字验证语料 |
| OpenSpec 工作流 | [docs/project-rules/openspec-workflow.md](../../project-rules/openspec-workflow.md) | **修改目标**：嵌入步骤 5.5（V3 含 5.5.1 源码影响分析、5.5.8 反馈闭环） |
| AGENTS.md | [AGENTS.md](../../../AGENTS.md) | **修改目标**：添加强制规则 |
| 优化任务上下文 | [specs/network-perf-stability/](../network-perf-stability/) | 被测对象源 spec |
| 网络层模块 | [docs/project-flow/architecture/network-layer.md](../../project-flow/architecture/network-layer.md) | 被测模块结构 |
| UI 模块 | [docs/project-flow/architecture/android-ui.md](../../project-flow/architecture/android-ui.md) | UI 操作页面定位参考 |
| 构建指南 | [docs/project-flow/build-apk-guide.md](../../project-flow/build-apk-guide.md) | APK 产出路径 |
| Legado Web 服务 | [docs/project-flow/modules/web-service.md](../../project-flow/modules/web-service.md) | F-P0-3 等 Web 端功能验证参考 |
| **源码根** | `app/src/main/java/io/legado/app/` | **V3 新增**：M8/M9 输入 |
| **AndroidManifest** | `app/src/main/AndroidManifest.xml` | **V3 新增**：M9 Activity 跳转链解析 |

### 2.3 V3 新增子规范文档（实施时生成）

| 规范 | 路径 | 状态 |
|------|------|------|
| AI 自动测试工作流 | `docs/project-rules/ai_e2e_testing_workflow.md` | 待生成 |
| 测试用例设计指南（含双轨制） | `docs/project-rules/test-case-design-guide.md` | 待生成 |
| AI 协作指南 | `ai_tests/docs/ai_collaboration_guide.md` | 待生成 |
| **源码影响分析指南** ⭐ V3 | `ai_tests/docs/source_impact_guide.md` | 待生成 |
| **源码→测试生成指南** ⭐ V3 | `ai_tests/docs/source_test_guide.md` | 待生成 |
| **已知问题与陷阱库** ⭐ V3 | `ai_tests/docs/known_issues.md` | 待生成 |
| **回归历史** ⭐ V3 | `ai_tests/docs/regression_history.md` | 待生成 |

---

## 三、状态标记

- 🔄 设计中（V3）：四文档已重构，等待用户审查（强制检查点 1）
- ⏳ 后续状态：✅ 设计完成 → 🔄 开发中 → ✅ 已完成

---

## 四、V3 调整记录

### 4.1 2026-07-07 V3 调整（基于用户深度反馈再次重构）

**用户反馈核心**（V2 审核意见）：

> "现在整个流程既然整理下来了，那你如何去构建持续迭代的测试用例呢？并且基于现在的源码呀，源码是你的根，你优化的功能也有源码呀，你，作为ai，你通过openspec现在设计了一个新功能，功能有改动了，影响了哪些源码？源码动了之后可能会对哪些前端页面造成影响，需要进行复测，并且这个复测的手段是可以基于源码去做一些深度定制脚本的呀，毕竟没有多模态，你只能基于源码的xml去自动模拟触发模拟器内apk的流程性东西呀，还有就是现在存量的全量的测试用例你打算怎么搞？？并且现在这个流程规划完毕之后，你打算如何验证？并且后续持续迭代这个流程呢？哪些是固化的，哪些是需要持续迭代的呀，让你越来越懂，越来越降低用户测试的依赖性呀"

**6 项 V3 关键调整**：

1. ❌ V2 仅 MD 单轨用例 → ✅ V3 双轨制（MD + Python 源码生成）
2. ❌ V2 不读源码 → ✅ V3 M8 源码影响分析 + M9 源码→测试生成器
3. ❌ V2 无影响范围分析 → ✅ V3 git diff → source_map.json → 自动选复测用例
4. ❌ V2 仅 14 份存量用例 → ✅ V3 三波覆盖（存量→核心模块→Bug 反向补充）
5. ❌ V2 仅端到端验证 → ✅ V3 三阶段（单元+端到端+流程注入验证）
6. ❌ V2 无反馈闭环 → ✅ V3 失败 → 沉淀规则库 → 调优提示词 → 下一轮更准

### 4.2 V3 保留项（V2 合理部分）

- ✅ V2 全部 8 项调整（V1→V2 的修正全部保留）
- ✅ 9 模块中 M1-M7 全部保留，V3 仅扩展 M8/M9
- ✅ 8 类非多模态验证手段
- ✅ 三层架构（编排/执行/基础设施）
- ✅ 失败不阻断 + 证据归档
- ✅ Markdown + JSON + manual 三件套报告
- ✅ 子规范 + OpenSpec 工作流 + AGENTS.md 修改

### 4.3 V2 被升级的关键设计

| V2 设计 | V3 升级理由 |
|---------|-----------|
| 单一 MD 用例 | 复杂交互无法精准化 → 双轨制 |
| 不读源码 | 错失非多模态环境下的精准化机会 → M8/M9 利用源码 |
| 仅 14 份存量用例 | 50+ 功能模块未覆盖 → 三波覆盖策略 |
| 仅端到端验证 | 流程本身未被验证 → 三阶段含流程注入验证 |
| 无反馈闭环 | AI 不会越来越准 → 反馈闭环机制 |

---

## 五、关键约束与原则（V3 更新）

### 5.1 V3 六大设计原则

1. **流程固化优先**：能写到子规范的，不写到代码注释；能写到代码注释的，不依赖 AI 临场判断
2. **AI agent 友好**：测试脚本输出结构化 JSON + manual 提示词，让 Trae CN 中的 AI agent 能直接接入分析
3. **零 LLM API 依赖**：测试脚本本身不调任何 LLM，纯规则判定 + 结构化证据输出
4. **极简工程**：能复用现有能力就不新增代码；必须新增的代码，要朴素、可读、健壮
5. **可观测可追溯**：每步操作有日志，每用例有独立证据目录，失败可复盘
6. **V3 新增：源码驱动**：基于源码做深度定制脚本 + 影响范围分析，让非多模态环境也能精准自动化
7. **V3 新增：持续反馈**：每轮失败案例沉淀为规则/陷阱/提示词调优，下一轮更准

### 5.2 强制约束

- **不修改 app/ 源码**：测试系统是黑盒（但 M8/M9 是只读分析源码）
- **不依赖多模态**：所有判定基于文本证据
- **不依赖 LLM API**：测试脚本独立可运行，无 API key 也能跑
- **不破坏现有 OpenSpec 流程**：作为子环节嵌入，不取代人工审查
- **失败不阻断**：单用例失败继续后续，最终汇总
- **子规范强制**：所有规范文档必须被 AGENTS.md 引用，AI 必须遵守
- **V3 新增：双轨用例 TC-ID 唯一**：同 TC-ID 时 Python 优先，但同 TC-ID 不允许两个 MD 用例
- **V3 新增：固化层不随意修改**：AI 不应修改 lib/ 下的基础设施代码，除非通过 OpenSpec 流程

### 5.3 依赖锁定（V3 更新）

| 依赖 | 版本 | 锁定理由 |
|------|------|---------|
| Python | 3.12.10 | 已安装 |
| uiautomator2 | ≥ 3.2.0 | openatx 主流维护 |
| memuc.exe | 9.5.3（随 MEmu） | 逍遥官方工具 |
| adb.exe | 随 MEmu | 不引入 Android SDK |
| Jinja2 | ≥ 3.1.0 | 报告模板渲染 |
| loguru | ≥ 0.7.0 | 日志库 |
| pydantic | ≥ 2.0 | 数据模型校验 |
| **tree-sitter-java** ⭐ V3 | ≥ 0.20 | M9 源码 AST 解析（可选） |
| **无 LLM SDK** | - | 测试脚本不调 LLM API |
| **无新增 JVM/Node** | - | 极简原则 |
