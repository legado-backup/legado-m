# spec.md — Legado AI 自动化测试基础设施（V3）

> **状态**：🔄 设计中（V3，基于用户深度反馈再次重构） | **创建日期**：2026-07-07 | **优先级**：P0

---

## 一、Intent（意图）

### 1.1 核心问题（V2 沿用 + V3 补充）

当前 OpenSpec 工作流（[docs/project-rules/openspec-workflow.md](../../project-rules/openspec-workflow.md)）的"步骤 5（开发实施）→ 步骤 6（用户审核）"之间**缺少自动化端到端验证环节**。`network-perf-stability` 等大型优化任务（22 项优化 + 25 项功能借鉴）由 AI agent 实施后，仅完成"编译通过+单元测试"，**真机端到端验证完全依赖用户人工**：

| 痛点 | 当前流程 | 用户工作量 |
|------|---------|-----------|
| APK 安装 | 用户手动 `adb install` 或拖拽到模拟器 | 每包 1-2 分钟 |
| 测试用例执行 | 用户对照 `docs/tests/*.md` 逐步操作 UI | 每用例 3-10 分钟 |
| 日志收集 | 用户手动 `adb logcat` 并打包到 `temp/tmp/` | 每轮 5-10 分钟 |
| 异常分析 | 用户把日志丢给 AI agent，AI 才被动分析 | 每问题 5-30 分钟 |
| 结果判定 | 用户凭经验判断"功能是否正常" | 主观、易漏 |
| **V3 痛点：源码影响未知** | 改 A.java 不知道 B.java 也要复测 | 漏测关联页面 |
| **V3 痛点：用例不持续** | 用例写完就完，无生命周期管理 | 用例库不增长 |
| **V3 痛点：AI 不会越来越准** | 失败案例未沉淀为规则 | 同样问题重复犯 |
| **总计** | **每轮回归 14 用例** | **约 2-4 小时** |

### 1.2 意图（V3 升级）

构建一套 **永久影响 AI 代码开发工作流的基础设施**，让"AI 完成代码实施 → 源码影响分析 → AI 自动跑双轨测试 → 反馈沉淀 → 输出结构化报告 → 用户秒级决策"成为 OpenSpec 工作流的强制子流程（步骤 5.5），并且**让 AI 越来越顺手、越来越自动，持续降低用户测试依赖**。

**关键特征（V3 升级）**：
- **不是一次性工具**，是工作流基础设施
- **不依赖 LLM API**，测试脚本独立可运行（无 API key 也能跑）
- **AI agent 友好**，输出结构化证据 + manual 提示词，让 Trae CN 中的 AI agent 能直接接入分析
- **流程固化到子规范**，让后续每个 AI agent 做 /openspec 时强制执行
- **可被 AI 持续更新**，AI 后续新增测试脚本到 `ai_tests/cases/` 即可纳入
- **V3 新增：源码驱动**：基于源码做影响范围分析 + 深度定制测试脚本，让非多模态环境也能精准自动化
- **V3 新增：双轨用例**：MD 用例（可读性）+ Python 用例（精准性），按场景选择
- **V3 新增：反馈闭环**：失败案例沉淀规则库、提示词库、陷阱库，下一轮更准
- **V3 新增：持续降低用户依赖**：从 70% 自动 → 80% → 90% → 持续提升

### 1.3 成功标准（SMART，V3 更新）

| 维度 | 标准 | 验证方式 |
|------|------|---------|
| **Specific** | 覆盖 `docs/tests/` 全部 14 份测试用例的可执行化 + 子规范文档完整 + 源码影响分析可用 | 用例解析覆盖率 100% + 规范文档审计 + M8 验证 |
| **Measurable** | 单轮回归耗时 ≤ 30 分钟（vs 当前 2-4 小时） + 用户介入次数持续降低 | 计时验证 + 趋势统计 |
| **Achievable** | 不修改 app/ 源码、不引入 JVM/Node 重型依赖、不依赖 LLM API | 依赖清单审计 |
| **Relevant** | 与现有 OpenSpec 工作流嵌入为步骤 5.5，被 AGENTS.md 强制规则引用 | 集成测试 + 流程注入验证 |
| **Time-bound** | 第一版 1-2 周内可用，覆盖 P0 测试用例先行；M8/M9 在 V3 第一版同步交付 | 阶段交付 |
| **V3 新增：持续改进** | 每轮 manual 用例占比持续降低（首轮 < 20% → 三轮后 < 10%） | 回归历史趋势 |

### 1.4 非目标（Anti-Goals，V3 扩展）

- ❌ **不取代单元测试**：本系统是端到端层，不重复 `./gradlew test`
- ❌ **不修改 app/ 源码**：测试系统与被测 App 解耦（M8/M9 是只读分析源码）
- ❌ **不依赖多模态大模型**：所有判定基于文本证据
- ❌ **不依赖 LLM API**：测试脚本本身不调任何 LLM API
- ❌ **不取代人工最终验收**：作为步骤 6 的"自动执行+预判"，用户仍需确认
- ❌ **不集成 CI/CD**：第一版纯本地 CLI，CI/CD 留 V4
- ❌ **不做截图视觉识别**：截图仅作为人工复核证据
- ❌ **不为不可能的场景做错误处理**：遵循极简工程主义
- ❌ **V3 新增：不修改固化层**：M1-M7 模块代码 AI 不应修改（除非通过 OpenSpec 流程）
- ❌ **V3 新增：不自动修复 Bug**：仅识别问题、定位根因，修复由 AI agent 走 OpenSpec 流程
- ❌ **V3 新增：不做性能基准对比**：当前需求是"功能可用性验证"，性能基准留 V4

---

## 二、Scope（范围）

### 2.1 In Scope（本次实现）

#### 2.1.1 代码模块（`ai_tests/`，V3：9 大模块）

| 范围项 | 内容 | 边界 |
|--------|------|------|
| **S1 模拟器控制** | 启停 MEmu 实例 0、等待就绪、ADB 连接验证 | 仅支持 MEmu，不兼容雷电/夜神 |
| **S2 APK 部署** | 自动从 `app\build\outputs\apk\app\debug\` 发现最新 APK + 安装 + 启动 + 等待首屏 | 不处理签名冲突（用户负责重装） |
| **S3 用例解析（V3 双轨）** | 解析 `docs/tests/*.md` 与 `ai_tests/cases/*/case.md` 为结构化步骤 JSON + 调度 B 轨 Python 用例 | 仅支持已规范的格式 |
| **S4 UI 执行器** | 通过 `uiautomator2` 执行点击/输入/等待/滑动/返回 | 不支持复杂手势、不依赖图像识别 |
| **S5 证据收集器** | 收集 8 类证据（logcat/UI XML/截图/Activity/DB/Prefs/Web API/进程） | 仅收集可文本化的证据 |
| **S6 规则分析器** | 规则匹配判定 pass/warning/fail/manual + 生成 manual 提示词 | 不调 LLM API |
| **S7 报告生成** | Markdown 人读 + JSON 机器可读 + manual 提示词清单 | 不做实时仪表盘、不发飞书 |
| **S8 一键编排** | `python ai_tests/run_e2e.py --apk <auto|path> --tc <all|P0|F-P0-1|TC-XXX>` | 默认 `--apk auto` 自动发现 |
| **S9 源码影响分析器（M8，V3 新增）** ⭐ | git diff → source_map.json 反向追踪 → 输出 affected_modules + 自动选复测 TC-ID | 仅静态分析，不修改源码 |
| **S10 源码→测试生成器（M9，V3 新增）** ⭐ | 基于 Activity 源码生成 Python 测试骨架（resource-id/text/跳转链） | 生成骨架，业务逻辑由 AI 补全 |
| **S11 双轨用例调度（V3 新增）** | 同 TC-ID 时 Python 优先于 MD；MD 与 Python 不可重复 | 调度规则在 M3 中实现 |
| **S12 三波用例覆盖（V3 新增）** | 第一波 14 份存量 → 第二波核心模块矩阵 → 第三波 Bug 反向补充 | 第二/三波持续迭代 |

#### 2.1.2 规范文档（`docs/project-rules/`，V3：5 份）

| 范围项 | 内容 |
|--------|------|
| **S13 AI 自动测试工作流子规范** | 新建 `ai_e2e_testing_workflow.md`，定义 OpenSpec 步骤 5.5 强制流程（含 5.5.1 源码影响分析、5.5.8 反馈闭环） |
| **S14 测试用例设计指南子规范（V3 双轨）** | 新建 `test-case-design-guide.md`，教 AI 写可自动化用例（MD 模板+步骤语义化+预期类型+双轨制+源码溯源字段） |
| **S15 修改 OpenSpec 工作流** | 在 `openspec-workflow.md` 步骤 5/6 之间嵌入步骤 5.5（V3 含 5.5.1/5.5.8） |
| **S16 修改 AGENTS.md** | 添加"AI 自动测试"强制规则条目，引用 S13/S14 子规范 + 固化层保护规则 |
| **S17 AI 协作指南** | 新建 `ai_tests/docs/ai_collaboration_guide.md`，告诉 AI agent 如何读取报告、处理 manual 用例、执行反馈闭环 |
| **S18 V3 新增：源码影响分析指南** | 新建 `ai_tests/docs/source_impact_guide.md`，教 AI 维护 source_map.json + 解读 affected_modules |
| **S19 V3 新增：源码→测试生成指南** | 新建 `ai_tests/docs/source_test_guide.md`，教 AI 用 M9 生成 B 轨 Python 用例 |
| **S20 V3 新增：已知问题与陷阱库** | 新建 `ai_tests/docs/known_issues.md`，沉淀失败案例 + 陷阱清单（持续迭代） |
| **S21 V3 新增：回归历史** | 新建 `ai_tests/docs/regression_history.md`，记录每轮回归趋势（持续迭代） |

### 2.2 Out of Scope（本次不做，V3 调整）

| 排除项 | 原因 | 后续阶段 |
|--------|------|---------|
| 多模拟器并行测试 | 单实例已满足当前用例量 | V4 |
| CI/CD 集成（GitHub Actions） | 第一版纯本地 CLI | V4 |
| 飞书群通知 | lark-* skill 可复用，本系统输出 JSON 即可对接 | V4 |
| iOS 测试 | 项目是 Android App | 永不 |
| 性能基准对比 | 当前需求是"功能可用性验证" | V4 |
| 自动修复 Bug | 仅识别问题，修复走 OpenSpec 流程 | V4 |
| Monkey 随机测试 | 与"按用例执行"目标冲突 | 永不 |
| 视觉回归测试（截图 diff） | 用户非多模态 | 永不 |
| LLM API 直接调用 | 用户环境是 Trae CN 对话，无 API key | 永不 |
| **V3 新增：动态源码插桩** | 仅静态分析源码，不做字节码插桩 | V4 |
| **V3 新增：跨仓库依赖分析** | 仅分析本仓库 app/ 源码，不分析第三方库 | V4 |

### 2.3 影响范围（V3 更新）

| 文件/模块 | 变更类型 | 说明 |
|-----------|---------|------|
| `ai_tests/` | **新增目录** | 全部测试系统代码（项目根目录） |
| `ai_tests/venv/` | **新增** | Python 虚拟环境（gitignore） |
| `ai_tests/cases/` | **新增** | 测试用例（MD + V3 自动生成 Python + 前置资源） |
| `ai_tests/reports/` | **新增** | 测试报告（gitignore） |
| `ai_tests/lib/source_map.json` | **V3 新增** | 源码→UI 映射表（M8 输入，AI 持续维护） |
| `ai_tests/docs/known_issues.md` | **V3 新增** | 陷阱库（持续迭代） |
| `ai_tests/docs/regression_history.md` | **V3 新增** | 回归历史（持续迭代） |
| `docs/tests/` | **不修改** | 仅读取作为输入（存量 14 份） |
| `app/src/main/` | **只读分析** | V3 新增：M8/M9 只读分析源码，不修改 |
| `app/build/outputs/apk/app/debug/` | **只读** | 自动发现 APK |
| `docs/INDEX.md` | **修改** | 添加 spec 索引 |
| `docs/project-flow/quick-reference.md` | **修改** | 添加测试命令速查 |
| `docs/project-rules/openspec-workflow.md` | **修改** | 嵌入步骤 5.5（V3 含 5.5.1/5.5.8） |
| `docs/project-rules/ai_e2e_testing_workflow.md` | **新增** | 强制流程子规范 |
| `docs/project-rules/test-case-design-guide.md` | **新增** | 测试用例设计指南（V3 含双轨制） |
| `AGENTS.md` | **修改** | 添加"AI 自动测试"强制规则 + V3 固化层保护 |
| `.gitignore` | **修改** | 添加 `ai_tests/venv/`、`ai_tests/reports/`、`ai_tests/__pycache__/`、`ai_tests/cases/*/preconditions/` |
| `assets/updateLog.md` | **不修改** | 测试系统非用户可感知功能 |
| `.trae/skills/` | **不修改** | 不与现有 skill 冲突 |
| MEmu 实例 | **不新增** | 复用已有实例 0 |
| **AndroidManifest.xml** | **只读** | V3 新增：M9 Activity 跳转链解析 |

---

## 三、Approach（方案）

### 3.1 Selected Approach（选定方案 V3）

**Python + uiautomator2 + memuc/adb + 8 类证据规则判定 + AI agent 对话介入 manual 用例 + V3 源码驱动双轨用例 + 反馈闭环**

#### 3.1.1 技术栈选型（V3 调整）

| 层 | 选型 | 理由 |
|----|------|------|
| 编排语言 | Python 3.12（venv 隔离） | 项目已有 Python 脚本生态，团队熟悉 |
| 模拟器控制 | `memuc.exe` 优先 + `adb.exe` 兜底 | memuc 提供高级 API，避免手写 ADB 流程 |
| UI 自动化 | `uiautomator2`（openatx） | 纯 Python、元素定位、MEmu x86_64 兼容 |
| 日志收集 | `adb logcat` 子进程管道 | 不依赖第三方日志库 |
| 证据收集 | ADB shell + uiautomator2 + curl | 8 类证据，全部可文本化 |
| **判定方式** | **纯规则匹配 + manual 提示词** | **不调 LLM API**，让 AI agent 对话介入 |
| 报告格式 | Markdown + JSON + manual 提示词清单 | 人读 + 机器读 + AI 协作引导 |
| **V3 新增：源码解析** | **tree-sitter-java（可选）+ 正则兜底** | M9 解析 Activity 源码提取 resource-id |
| **V3 新增：源码影响分析** | **git diff + 静态调用图分析** | M8 反向追踪受影响 Activity |

#### 3.1.2 系统架构（V3 三层 + 源码驱动层）

```
┌─────────────────────────────────────────────────────────────────┐
│  OpenSpec 工作流（步骤 5.5 强制嵌入，V3 含 8 子步骤）              │
│  ↓ AI agent 触发 ↓                                               │
│  python ai_tests/run_e2e.py --apk auto --tc all                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: 编排层（run_e2e.py）                                    │
│  - 解析参数 (--apk auto|path, --tc, --report-dir, --no-rules)    │
│  - 串联 M1→M2→M3→M4+M5→M6→M7                                    │
│  - V3 新增：M8 源码影响分析 → 自动选复测用例                       │
│  - V3 新增：M9 源码→测试生成器（按需触发）                        │
│  - 失败不阻断，最终汇总报告                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: 用例与执行层                                            │
│  - M3 用例解析器：MD → 步骤 JSON（正则+状态机）+ V3 双轨调度      │
│  - M4 UI 执行器：uiautomator2 操作 + 截图 + XML + Activity       │
│  - M5 证据收集器：8 类证据收集 + 时间切片                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: 基础设施层                                              │
│  - M1 模拟器控制：memuc.exe start/stop/isvmrunning               │
│  - M2 APK 部署：自动发现 + installapp + startapp                 │
│  - M6 规则分析器：8 类证据规则匹配 + manual 提示词生成             │
│  - M7 报告生成器：Markdown + JSON + manual 清单                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  V3 新增：Layer 0 - 源码驱动层                                    │
│  - M8 源码影响分析器：git diff → source_map.json → affected       │
│  - M9 源码→测试生成器：Activity 源码 → Python 测试骨架            │
│  - 输入：app/src/main/ + AndroidManifest.xml（只读）              │
│  - 输出：source_map.json + auto_*.py + affected_modules           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  输出：reports/{run_id}/                                          │
│  ├── report.md          # 人读报告                                │
│  ├── report.json        # 机器可读（AI agent 接入，含 affected）   │
│  ├── manual_cases.md    # manual 用例清单 + AI 分析提示词           │
│  ├── summary.txt        # 一行摘要                                  │
│  ├── affected_modules.json # V3 新增：源码影响分析结果              │
│  └── cases/{tc_id}/     # 每用例证据目录                           │
│      ├── step-XX-*.png|xml     # 截图+UI XML                       │
│      ├── log-slice.txt          # 日志切片                          │
│      ├── activity-stack.txt     # Activity 栈                      │
│      ├── db-state.json         # 数据库状态                         │
│      ├── prefs-state.json      # SharedPreferences                 │
│      ├── web-api-resp.json     # Web API 响应                       │
│      ├── meminfo.txt           # 内存状态                           │
│      └── ai-prompt.md          # AI agent 分析提示词（manual 时）   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  AI agent（Trae CN 对话）介入                                     │
│  - 读取 report.json + manual_cases.md + affected_modules.json     │
│  - 对每个 manual 用例：读取 ai-prompt.md + 证据目录                │
│  - 通过对话能力判定 pass/fail，回填到最终报告                       │
│  - V3 新增：执行反馈闭环 → 沉淀规则库/陷阱库 → 调优提示词          │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.1.3 关键设计点（V3 更新）

1. **APK 自动发现**：默认 `--apk auto`，扫描 `app\build\outputs\apk\app\debug\*.apk`，按 mtime 取最新
2. **8 类证据收集**：每用例结束收集 8 类证据，全部文本化存储
3. **规则判定 + manual 提示词**：
   - 规则匹配 → pass/warning/fail（高置信度）
   - 规则无法判定 → manual + 生成 AI 分析提示词
4. **AI agent 协作接口**：`report.json` + `manual_cases.md` + `ai-prompt.md` 三件套，让 Trae CN 中的 AI agent 能直接接入
5. **测试用例设计规范**：子规范定义 MD 模板，AI 设计用例时遵守，确保可被 M3 解析
6. **目录在项目根 `ai_tests/`**：方便 AI 持续更新测试脚本，与 `app/`、`docs/`、`.trae/` 同级
7. **V3 新增：源码影响分析**：步骤 5.5.1 触发 `git diff → source_map.json → affected_modules`，自动选复测用例
8. **V3 新增：双轨用例调度**：同 TC-ID 时 Python（B 轨）优先于 MD（A 轨）
9. **V3 新增：反馈闭环**：步骤 5.5.8 触发失败案例沉淀规则库/陷阱库/提示词调优
10. **V3 新增：固化层保护**：lib/ 下基础设施代码 AI 不应修改，除非通过 OpenSpec 流程

### 3.2 Alternatives Considered（替代方案）

#### 3.2.1 测试框架替代方案（V2 沿用）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| Appium + Python | Appium Server + Python | 需 JVM/Node Server，违反极简原则 |
| Maestro (YAML) | YAML 描述流程 | 需 Node CLI，与 Python 生态脱节 |
| Espresso (Java) | Android 原生白盒 | 需在 app/ 源码内写测试，违反"不修改源码" |
| UIAutomator (Java) | Android 原生黑盒 | 需 Java 测试工程，与 Python 生态脱节 |
| Monkey + ADB | `adb shell monkey` 随机事件 | 随机事件无法精准对应用例 |
| Firebase Test Lab | Google 云测试 | 涉及外部服务依赖与隐私 |
| Airtest (NetEase) | 图像识别+UI | 图像识别依赖多模态，违反约束 |
| Detox (Wix) | React Native 灰盒 | 仅 React Native |
| Calabash | Cucumber BDD | 已停止维护 |
| 裸 ADB Shell + Python | `adb shell input tap` | 元素定位脆弱（坐标硬编码） |
| **选定：uiautomator2 + Python** | openatx 维护 | 纯 Python、元素定位、MEmu 兼容 |

#### 3.2.2 AI 判定方式替代方案（V2 沿用）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| A. 测试脚本直调 LLM API | 测试脚本内置 OpenAI/Anthropic SDK | 用户明确：无 API key |
| **B. 测试脚本输出证据，AI agent 对话介入** | 测试脚本只做规则判定+证据收集，manual 由 AI 对话分析 | **被采纳** |
| C. 纯规则判定，无 AI 介入 | 仅关键字匹配 | 准确率不足 |
| D. 调用本地 Ollama/llama.cpp | 本地大模型 | 用户环境无本地模型 |

#### 3.2.3 V3 新增：源码影响分析替代方案

| 方案 | 描述 | 优势 | 劣势 | 否决理由 |
|------|------|------|------|---------|
| **A. 静态调用图分析** | Python 扫 import / 调用关系，构建调用图 | 无外部依赖、纯 Python | 仅静态分析，无法覆盖反射/动态加载 | **被采纳**（覆盖 80%+ 场景） |
| B. JVM 字节码分析 | 解析 .class 文件，构建精确调用图 | 准确性高 | 需引入 javalang/asm 库，违反极简 | 重型依赖 |
| C. IDE 集成分析（如 IntelliJ IDEA 依赖分析） | 复用 IDE 能力 | 准确性最高 | 需启动 IDE，非 CLI 友好 | 与自动化流程冲突 |
| D. LLM 分析源码 | 让 LLM 看源码，输出影响范围 | 灵活 | LLM 不稳定、有 API 依赖 | 违反"不依赖 LLM API" |
| E. 不做影响分析 | 全量回归所有用例 | 最简 | 浪费时间、漏测关联页面 | V2 已被否决 |

#### 3.2.4 V3 新增：源码→测试生成器替代方案

| 方案 | 描述 | 优势 | 劣势 | 否决理由 |
|------|------|------|------|---------|
| **A. 正则 + 简单状态机解析 Kotlin/Java 源码** | 正则提取 `setContentView`/`findViewById`/`R.id.xxx` | 零外部依赖 | 仅覆盖 70% 模式 | **被采纳**（覆盖核心场景） |
| B. tree-sitter-java AST 解析 | 精确 AST 提取 | 准确性高 | 需引入 tree-sitter 库 | 可选增强，作为 B 选项 |
| C. Kotlin Compiler 嵌入分析 | 复用 Kotlin 编译器 | 最准确 | 重型依赖、JVM 需求 | 违反极简 |
| D. LLM 生成测试代码 | 让 LLM 看源码生成测试 | 灵活、可读性高 | LLM 不稳定、有 API 依赖 | 违反"不依赖 LLM API" |

#### 3.2.5 V3 新增：双轨用例调度替代方案

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 仅 MD 单轨 | V2 方案 | 复杂交互无法精准化 |
| 仅 Python 单轨 | 全部用 Python | 可读性差，人工审阅困难 |
| **MD + Python 双轨** | MD 优先可读，Python 优先精准 | **被采纳** |
| MD + Java 双轨 | Java 替代 Python | 与 Python 生态脱节 |

#### 3.2.6 验证手段替代方案（V2 沿用）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 仅 logcat 日志 | 只看崩溃日志 | 无法判定 UI 状态、配置变更、数据库写入 |
| logcat + UI XML | V1 方案 | 覆盖率约 60% |
| logcat + 截图视觉识别 | 多模态识别 | 用户非多模态，违反约束 |
| **8 类证据全收集** | 日志/UI XML/截图/Activity/DB/Prefs/Web API/进程 | **被采纳**，覆盖率 90%+ |

#### 3.2.7 目录结构替代方案（V2 沿用）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| `tools/e2e-testing/` | V1 方案 | 用户要求建在项目根 `ai_tests/` |
| `docs/specs/e2e-testing/scripts/` | 与 spec 文档同级 | 测试脚本是代码，不是文档 |
| `scripts/e2e/` | 与现有 `scripts/` 平级 | 现有 `scripts/` 是书源验证脚本，混杂会混乱 |
| **`ai_tests/`（项目根）** | 与 `app/`、`docs/`、`.trae/` 同级 | **被采纳** |

### 3.3 Drawbacks（选定方案的已知缺点，V3 扩展）

| 缺点 | 影响 | 接受理由 | 缓解措施 |
|------|------|---------|---------|
| **D1 首次 init 设备** | 第一次需推送 atx-agent + uiautomator2-test.apk（~5MB），需 30s | 一次性成本 | 提供 `init_device.py` 一键脚本，失败重试 3 次 |
| **D2 manual 用例需 AI 介入** | 规则无法判定的用例（预估首轮 20%，V3 持续降低至 < 10%） | 比人工 2-4 小时成本低 | 生成结构化 `ai-prompt.md` + V3 反馈闭环 |
| **D3 MEmu 渲染可能不稳定** | 模拟器 vs 真机有差异 | 项目当前以"功能可用"为标准 | 不做像素级比对，只做 8 类文本证据判定 |
| **D4 uiautomator2 偶尔卡死** | atx-agent 与设备通信可能 hang | 已知问题 | 每步操作超时 30s，超时重启 atx-agent |
| **D5 用例解析规则依赖 MD 格式** | 现有 `docs/tests/*.md` 格式需稳定 | 子规范 S14 定义模板 | 解析器宽容，不符合时标记 `parse_warning` |
| **D6 不支持复杂手势** | 双指/拖拽/长按组合不支持 | 现有 14 份用例未涉及 | 后续 V4 通过 `d.swipe_ext` 扩展 |
| **D7 8 类证据收集耗时** | 每用例收集 8 类证据比 V1 仅 2 类慢约 30s | 总耗时仍 ≤ 30 分钟 | 并行收集（DB/Prefs/Web API 可并发） |
| **D8 模拟器是 x86_64** | 部分 ARM-only App 不兼容 | Legado 是 Kotlin/Java | V1 已实测可启动 |
| **D9 AI agent 介入需手动触发** | manual 用例需 AI agent 主动读取报告 | OpenSpec 工作流已强制 AI 在步骤 5.5 触发 | 子规范 S13 明确 AI agent 接入流程 |
| **D10 子规范学习成本** | AI 需学习 S13/S14 子规范 | 一次性学习，AGENTS.md 强制引用 | 子规范简洁（< 500 行），有示例 |
| **V3 D11 源码影响分析覆盖率约 80%** | 静态调用图无法覆盖反射/动态加载 | 80% 已能覆盖 Legado 主流场景 | source_map.json 手动补充反射场景；V4 字节码分析 |
| **V3 D12 源码→测试生成仅 70% 模式** | 正则解析无法覆盖 Compose 复杂模式 | 70% 已能覆盖传统 View 体系 | tree-sitter-java 可选增强；AI 补全剩余 30% |
| **V3 D13 source_map.json 需持续维护** | 每新增 Activity 需更新映射表 | AI 自动追加 + 人工审核 | M8 提供 `--update-source-map` 子命令 |
| **V3 D14 反馈闭环可能引入误判** | 自动扩展规则库可能引入误报 | 比人工扩展规则成本低 | 规则库扩展需 AI agent 审核后才入库 |
| **V3 D15 双轨用例可能产生冲突** | 同 TC-ID 的 MD 与 Python 行为不一致 | 罕见（Python 通常基于 MD 增强） | M3 调度时记录 `track_source` 字段，冲突时人工审核 |
| **V3 D16 流程注入验证成本高** | 需让另一个 AI agent 实际跑一遍 | 一次性成本 | 阶段 C 验证后流程稳定，后续无需重复 |

### 3.4 Prior Art（参考工作，V3 扩展）

| 参考 | 链接 | 借鉴点 |
|------|------|--------|
| **openatx/uiautomator2** | https://github.com/openatx/uiautomator2 | API 设计、init 流程、dump_hierarchy |
| **openatx/atx-agent** | https://github.com/openatx/atx-agent | 设备端 agent 通信协议 |
| **Maestro** | https://ma.mobile.dev/ | YAML 流程描述简洁性 |
| **Appium Python Client** | https://github.com/appium/python-client | API 风格参考 |
| **Airtest** | https://airtest.netease.com/ | 截图+报告归档模式 |
| **Logcat Analyzer (社区)** | https://github.com/marcingrzejszczyk/logcat-analyzer | 日志关键字过滤规则 |
| **adbutils** | https://github.com/openatx/adbutils | Python ADB 封装 |
| **ATX Agent 文档（MEmu 适配）** | https://github.com/openatx/atx-agent | MEmu x86_64 兼容性参考 |
| **Trae CN AI agent 协作模式** | 项目内既有 skill 协作（legado-skill-auditor 等） | AI agent 接入接口设计参考 |
| **V3 新增：tree-sitter-java** | https://tree-sitter.github.io/tree-sitter/ | M9 AST 解析参考（可选增强） |
| **V3 新增：Android calls graph 静态分析** | 社区多个开源项目 | M8 调用图构建思路 |
| **V3 新增：Gradle dependency analysis** | Android Gradle Plugin 源码 | M8 依赖分析参考 |
| **V3 新增：JetBrains IntelliJ bytecode analysis** | 开源社区 | V4 字节码分析参考 |
| **V3 新增：pytest + conftest** | https://docs.pytest.org/ | M9 测试骨架生成参考 |

### 3.5 设计哲学（V3 更新）

> **极简工程主义 + 流程固化优先 + 源码驱动 + 持续反馈**

- ✅ 复用 `memuc.exe`（不重写 ADB 流程）
- ✅ 复用 Python 3.12（不引入新运行时）
- ✅ 复用 `docs/tests/` 测试用例（不重写存量）
- ✅ 复用 Trae CN AI agent 对话能力（不引入 LLM API）
- ✅ 复用 ADB shell 8 类证据收集能力（不引入新工具）
- ✅ V3 新增：复用源码做影响分析（不引入字节码工具）
- ✅ V3 新增：复用源码生成精准测试（不依赖多模态）
- ✅ V3 新增：复用失败案例沉淀规则（不引入额外学习成本）
- ❌ 不引入 Appium Server、Maestro CLI、Node.js、Java 测试工程
- ❌ 不调任何 LLM API
- ❌ 不依赖多模态识别
- ❌ 不为"未来可能的需求"过度设计（CI/CD、多设备并行留 V4）
- ❌ V3 新增：不修改固化层基础设施代码（除非通过 OpenSpec 流程）

---

## 四、Requirements（需求）

### 4.1 功能性需求（FR）

#### FR-1 模拟器控制（M1）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-1.1 | 启动指定 MEmu 实例 | P0 | `start_memu(0)` 30s 内返回 Running |
| FR-1.2 | 关闭指定 MEmu 实例 | P0 | `stop_memu(0)` 15s 内返回 Stopped |
| FR-1.3 | 查询实例运行状态 | P0 | `is_running(0)` 返回 bool |
| FR-1.4 | 等待 ADB 就绪 | P0 | `wait_for_adb(0, timeout=60)` 返回设备 serial |
| FR-1.5 | 启动失败重试 | P0 | 失败重试 3 次，每次间隔 5s（指数退避） |
| FR-1.6 | 多实例管理（预留） | P2 | API 支持 `instance_id` 参数 |

#### FR-2 APK 部署（M2）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-2.1 | **自动发现最新 APK** | P0 | `discover_apk()` 扫描 `app\build\outputs\apk\app\debug\*.apk`，按 mtime 取最新 |
| FR-2.2 | APK 路径校验 | P0 | 文件存在 + `.apk` 后缀 + 大小 > 1MB |
| FR-2.3 | 安装/覆盖安装 | P0 | `install_apk(apk_path)` 返回 SUCCESS，-r -d 兼容降级 |
| FR-2.4 | 卸载 App | P1 | `uninstall_app(pkg)` 清理残留 |
| FR-2.5 | 启动 App | P0 | `start_app(pkg, activity)` 10s 内首屏渲染 |
| FR-2.6 | 等待 App 首屏 | P0 | `wait_for_app(pkg, timeout=30)` 抓 logcat `Displayed io.legado.app` |
| FR-2.7 | 清理 App 数据 | P1 | `clear_data(pkg)` 调 `pm clear` |

#### FR-3 用例解析（M3，V3 双轨扩展）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-3.1 | 解析单文件 | P0 | 输出 `{tc_id, title, steps, expects, preconditions}` |
| FR-3.2 | 批量解析 `docs/tests/` | P0 | 14 份文件全解析，无 fatal 错误 |
| FR-3.3 | 解析"测试步骤"段 | P0 | 识别"1. xxx 2. xxx" 编号 |
| FR-3.4 | 解析"预期结果"段 | P0 | 识别"- ✅ xxx" 列表项 |
| FR-3.5 | 解析"前置资源"段 | P0 | 识别 AI 自备 vs 用户必供 |
| FR-3.6 | 容错：格式不规范时降级 | P1 | 标记 `parse_warning`，不阻断 |
| FR-3.7 | 步骤语义化为原子动作 | P0 | "点击 XX 按钮"→ `{action: click, target: {text: "XX"}}` |
| FR-3.8 | 预期类型识别 | P0 | display/rule_match/db_state/prefs_state/activity_state/web_api/process_state |
| **FR-3.9 V3 新增** | **双轨调度：同 TC-ID 时 Python 优先** | P0 | 检测 `ai_tests/cases/{module}/auto_{tc_id}.py` 存在时优先执行 |
| **FR-3.10 V3 新增** | **解析"关联源码"字段** | P0 | MD 头部 `**关联源码**：xxx.kt` 字段 |
| **FR-3.11 V3 新增** | **解析"关联 Activity"字段** | P0 | MD 头部 `**关联 Activity**：XxxActivity` 字段 |

#### FR-4 UI 执行（M4）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-4.1 | 点击（resource-id/text/xpath/description） | P0 | 四种定位都支持 |
| FR-4.2 | 输入文本 | P0 | clear + input |
| FR-4.3 | 等待元素出现 | P0 | `wait_exists(locator, timeout=10)` |
| FR-4.4 | 滑动 | P0 | 上下左右四方向 |
| FR-4.5 | 返回键 | P0 | `press_back()` |
| FR-4.6 | 截图 | P0 | 每步执行后自动截图 |
| FR-4.7 | dump UI XML | P0 | 每步执行后自动 dump |
| FR-4.8 | 超时保护 | P0 | 单步 30s 超时 |
| FR-4.9 | atx-agent 卡死自愈 | P1 | 3 次失败重启 atx-agent |

#### FR-5 证据收集（M5）— 8 类

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-5.1 | 启动 logcat 子进程 | P0 | 持续抓取 `*:W` 到文件 |
| FR-5.2 | 按用例时间切片 logcat | P0 | 每用例独立日志文件 |
| FR-5.3 | 提取 logcat 异常 | P0 | 6 类关键字提取（FATAL/ANR/CRASH/OOM/ClassNotFound/Other） |
| FR-5.4 | 收集 UI XML | P0 | 每步 dump_hierarchy |
| FR-5.5 | 收集截图 | P0 | 每步 screenshot |
| FR-5.6 | 收集 Activity 栈 | P1 | `dumpsys activity top` 输出到 activity-stack.txt |
| FR-5.7 | 收集数据库状态 | P1 | `run-at io.legado.app sqlite3` 查关键表 |
| FR-5.8 | 收集 SharedPreferences | P1 | `cat shared_prefs/*.xml` |
| FR-5.9 | 收集 App Web 接口响应 | P2 | `curl http://localhost:8080/...` |
| FR-5.10 | 收集进程/内存状态 | P1 | `dumpsys meminfo io.legado.app` |
| FR-5.11 | 全量证据归档 | P0 | 每用例独立目录 |

#### FR-6 规则分析器（M6）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-6.1 | 规则匹配判定 | P0 | 输出 `{verdict, confidence, evidence}` |
| FR-6.2 | 4 种 verdict | P0 | pass/warning/fail/manual |
| FR-6.3 | 规则 1：FATAL/CRASH/ANR → fail | P0 | confidence=95 |
| FR-6.4 | 规则 2：Exception/Error 但非 Fatal → warning | P0 | confidence=80 |
| FR-6.5 | 规则 3：无异常 + 步骤全过 + 预期匹配 → pass | P0 | confidence=85 |
| FR-6.6 | 规则 4：证据不足 → manual | P0 | confidence=50 |
| FR-6.7 | 置信度 < 70 → 强制 manual | P0 | - |
| FR-6.8 | 生成 manual 提示词 | P0 | 输出 `ai-prompt.md` |
| FR-6.9 | 不调任何 LLM API | P0 | 纯规则 + 结构化输出 |
| **FR-6.10 V3 新增** | **规则库可扩展** | P0 | `CRASH_PATTERNS` 字典可被 AI 持续追加 |
| **FR-6.11 V3 新增** | **触发反馈闭环** | P1 | manual/fail 时输出 `feedback_signal` 字段 |

#### FR-7 报告生成（M7，V3 扩展）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-7.1 | Markdown 人读报告 | P0 | 含执行摘要+每用例详情+证据链接 |
| FR-7.2 | JSON 机器报告 | P0 | `{run_id, apk, summary, cases: [...]}` |
| FR-7.3 | manual 用例清单 | P0 | `manual_cases.md` 含所有 manual 用例+提示词路径 |
| FR-7.4 | 一行摘要 | P1 | `summary.txt` 供 CI 消费 |
| FR-7.5 | 证据目录归档 | P0 | 截图/XML/日志/Activity/DB/Prefs 按 TC-ID 归档 |
| FR-7.6 | 失败用例高亮 | P0 | 失败用例置顶，红色标记 |
| FR-7.7 | 执行耗时统计 | P1 | 每用例耗时 + 总耗时 |
| **FR-7.8 V3 新增** | **affected_modules.json 输出** | P0 | 含受影响 Activity 清单 + 复测 TC-ID 列表 |
| **FR-7.9 V3 新增** | **feedback_signal 字段** | P1 | manual/fail 用例附带反馈闭环触发信号 |
| **FR-7.10 V3 新增** | **track_source 字段** | P1 | 标记用例来源（A 轨 MD / B 轨 Python） |

#### FR-8 编排（run_e2e.py，V3 扩展）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-8.1 | `--apk <auto\|path>` 默认 auto | P0 | 自动从 build 目录发现 |
| FR-8.2 | `--tc <all\|P0\|F-P0-1\|TC-XXX>` 用例筛选 | P0 | 4 种粒度 |
| FR-8.3 | `--report-dir <path>` | P0 | 默认 `reports/{timestamp}` |
| FR-8.4 | `--no-rules` 跳过规则判定 | P2 | 仅收集证据 |
| FR-8.5 | `--keep-device` 不重启模拟器 | P1 | 复用已运行实例 |
| FR-8.6 | `--init-device` 重新初始化 uiautomator2 | P1 | - |
| FR-8.7 | 失败不阻断 | P0 | 单用例失败继续后续 |
| FR-8.8 | 退出码反映结果 | P0 | 全过=0，部分失败=1，致命错误=2 |
| **FR-8.9 V3 新增** | **`--diff <git_ref>` 触发源码影响分析** | P0 | 默认 `HEAD~1`，输出 affected_modules |
| **FR-8.10 V3 新增** | **`--gen-test <activity>` 触发 M9** | P1 | 基于 Activity 源码生成 Python 测试骨架 |
| **FR-8.11 V3 新增** | **`--update-source-map` 触发 source_map 重建** | P1 | 扫描 app/src/main/ 重建映射表 |
| **FR-8.12 V3 新增** | **`--feedback` 触发反馈闭环** | P1 | 失败案例沉淀到规则库/陷阱库 |

#### FR-9 源码影响分析（M8，V3 新增）⭐

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-9.1 | 解析 git diff 输出 | P0 | 输出本次改动文件清单（含 `.kt`/`.java`） |
| FR-9.2 | 加载 source_map.json | P0 | 解析源码→UI 映射表 |
| FR-9.3 | 反向追踪受影响 Activity | P0 | 改动文件 → 调用方 → Activity/Fragment |
| FR-9.4 | 输出 affected_modules | P0 | 受影响 Activity 清单 + 关联 TC-ID 列表 |
| FR-9.5 | source_map.json 首次构建 | P0 | 扫描 app/src/main/ 静态分析构建 |
| FR-9.6 | source_map.json 持续维护 | P1 | 新增 Activity 时追加映射 |
| FR-9.7 | 反射/动态加载场景标记 | P2 | 标记 `unknown_binding` 字段供 AI 审核 |
| FR-9.8 | 输出复测建议 | P0 | report.json 含 `suggested_retest_tc_ids` 字段 |

#### FR-10 源码→测试生成器（M9，V3 新增）⭐

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-10.1 | 解析 Activity 源码 | P0 | 提取 `setContentView`/`findViewById`/`R.id.xxx` |
| FR-10.2 | 解析 onClickListener 跳转 | P0 | 提取 `startActivity`/`Intent` 目标 |
| FR-10.3 | 解析 AndroidManifest.xml | P0 | Activity 注册与跳转链 |
| FR-10.4 | 生成 Python 测试骨架 | P0 | 输出到 `ai_tests/cases/{module}/auto_{tc_id}.py` |
| FR-10.5 | 骨架含元素定位代码 | P0 | 自动填入 resource-id（来自源码） |
| FR-10.6 | 骨架含跳转断言 | P1 | 自动生成 Activity 跳转断言 |
| FR-10.7 | tree-sitter-java 可选增强 | P2 | 提供更精确 AST 解析（可选） |
| FR-10.8 | 骨架含 TODO 标记 | P0 | AI 补全业务逻辑的占位符 |

#### FR-11 双轨用例调度（V3 新增）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-11.1 | 检测同 TC-ID 的 Python 用例 | P0 | 扫描 `ai_tests/cases/*/auto_{tc_id}.py` |
| FR-11.2 | 同 TC-ID 时 Python 优先 | P0 | 同 TC-ID 优先执行 B 轨 |
| FR-11.3 | MD 与 Python 不可重复同 TC-ID | P0 | 两个 MD 同 TC-ID 时报错 |
| FR-11.4 | track_source 字段标记 | P1 | 报告中标记用例来源 |
| FR-11.5 | 双轨结果一致性检查 | P2 | 同 TC-ID 双轨都执行时对比结果（可选） |

#### FR-12 反馈闭环（V3 新增）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-12.1 | 失败案例提取根因 | P0 | 从证据中提取异常类型/关键字 |
| FR-12.2 | 规则库扩展建议 | P0 | 输出 `rule_suggestion`（待 AI 审核） |
| FR-12.3 | 提示词调优建议 | P1 | 输出 `prompt_suggestion` |
| FR-12.4 | 陷阱库沉淀建议 | P0 | 输出 `known_issue_suggestion` |
| FR-12.5 | 回归历史记录 | P1 | 写入 `regression_history.md` |
| FR-12.6 | 趋势统计 | P2 | manual 用例占比趋势 |
| FR-12.7 | 规则库扩展需 AI 审核 | P0 | 建议不直接入库，由 AI agent 审核后才入库 |

#### FR-13 三波用例覆盖（V3 新增）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-13.1 | 第一波：现有 14 份存量用例 | P0 | MVP-4 阶段验证 |
| FR-13.2 | 第二波：核心模块优先级矩阵 | P1 | 持续 3 个月，每 sprint 覆盖一模块 |
| FR-13.3 | 第三波：Bug history 反向补充 | P2 | 持续 6 个月 |
| FR-13.4 | 用例生命周期管理 | P1 | 草案→审核→已纳入→回归中→失效/废弃 |
| FR-13.5 | 用例溯源字段 | P0 | 每个 MD 含"关联源码"和"关联 Activity"字段 |
| FR-13.6 | 模块优先级矩阵维护 | P1 | `ai_tests/docs/module_matrix.md` |

#### FR-14 流程注入验证（V3 新增）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-14.1 | 阶段 A 单元层验证 | P0 | 每模块独立 mock 数据测试 |
| FR-14.2 | 阶段 B 端到端验证 | P0 | 14 用例全跑通（≤ 30 分钟） |
| FR-14.3 | 阶段 C 流程注入验证 | P0 | 让另一个 AI agent 按 V3 流程跑 /openspec |
| FR-14.4 | 阶段 C 验证清单 | P0 | 7 项检查（5.5.1/5.5.2-7/5.5.8） |
| FR-14.5 | 流程审计报告输出 | P0 | pass/fail，每项打分 |

### 4.2 规范文档需求（FR-15 ~ FR-19，V3 扩展）

#### FR-15 AI 自动测试工作流子规范（S13）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-15.1 | 定义 OpenSpec 步骤 5.5 强制流程 | P0 | 8 个子步骤（5.5.1~5.5.8） |
| FR-15.2 | 定义 AI agent 接入接口 | P0 | 读取 report.json + manual_cases.md 的流程 |
| FR-15.3 | 定义 manual 用例处理流程 | P0 | AI agent 介入分析 + 回填报告 |
| FR-15.4 | 引用 AGENTS.md 强制规则 | P0 | 子规范被 AGENTS.md 引用 |
| FR-15.5 V3 | 定义 5.5.1 源码影响分析触发流程 | P0 | git diff → M8 → affected_modules |
| FR-15.6 V3 | 定义 5.5.8 反馈闭环触发流程 | P0 | 失败案例 → 规则库/陷阱库/提示词 |

#### FR-16 测试用例设计指南子规范（S14，V3 双轨）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-16.1 | 定义测试用例 MD 模板 | P0 | 含 TC-ID/标题/前置资源/步骤/预期 |
| FR-16.2 | 定义步骤语义化关键词 | P0 | 6 类原子动作关键词 |
| FR-16.3 | 定义预期类型枚举 | P0 | 8 种预期类型 |
| FR-16.4 | 定义前置资源分类 | P0 | AI 自备 vs 用户必供 |
| FR-16.5 | 提供 3 个完整示例 | P0 | 正常用例+边界+异常 |
| FR-16.6 V3 | 定义"关联源码"和"关联 Activity"字段 | P0 | MD 头部强制字段 |
| FR-16.7 V3 | 定义 B 轨 Python 用例模板 | P1 | `auto_{tc_id}.py` 模板 |
| FR-16.8 V3 | 定义双轨用例选择指南 | P1 | 何时用 MD，何时用 Python |

#### FR-17 修改 OpenSpec 工作流（S15）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-17.1 | 在步骤 5/6 之间嵌入步骤 5.5 | P0 | 修改 `openspec-workflow.md` |
| FR-17.2 | 更新工作流图 | P0 | 含步骤 5.5（8 子步骤） |
| FR-17.3 | 更新检查点说明 | P1 | 检查点 2 引用步骤 5.5 报告 |
| FR-17.4 V3 | 含 5.5.1 源码影响分析与 5.5.8 反馈闭环 | P0 | 8 子步骤全部纳入 |

#### FR-18 修改 AGENTS.md（S16，V3 固化层保护）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-18.1 | 添加"AI 自动测试"强制规则 | P0 | 在强制规则区添加条目 |
| FR-18.2 | 引用 S13/S14 子规范 | P0 | 链接到子规范路径 |
| FR-18.3 | 添加反模式说明 | P1 | "❌ 跳过步骤 5.5 直接审核"等 |
| FR-18.4 V3 | 添加固化层保护规则 | P0 | "❌ AI 修改 lib/ 下基础设施代码" |

#### FR-19 AI 协作指南（S17）

| ID | 需求 | 优先级 | 验收标准 |
|----|------|--------|---------|
| FR-19.1 | 定义 AI agent 接入流程 | P0 | OpenSpec 步骤 5.5 触发 → 执行 run_e2e.py → 读取 report.json |
| FR-19.2 | 定义 manual 用例处理流程 | P0 | 读取 ai-prompt.md → 读取证据目录 → 对话判定 → 回填 ai_verdict |
| FR-19.3 | 定义失败用例处理流程 | P0 | 读取证据 → 分析根因 → 触发修复 |
| FR-19.4 V3 | 定义反馈闭环执行流程 | P0 | 失败案例 → 规则库扩展建议 → 提示词调优 → 陷阱库沉淀 |

### 4.3 非功能性需求（NFR，V3 扩展）

| ID | 维度 | 需求 | 验收标准 |
|----|------|------|---------|
| NFR-1 | 性能 | 单轮 14 用例 ≤ 30 分钟 | 计时验证 |
| NFR-2 | 可靠性 | 单步失败不阻断全流程 | 模拟失败测试 |
| NFR-3 | 可复用 | 同一 APK 二次运行结果一致 | 重复运行验证 |
| NFR-4 | 可维护 | 新增测试用例无需改代码 | 仅改 MD 文件即可纳入 |
| NFR-5 | 可观测 | 每步操作有日志 | stdout + 文件日志 |
| NFR-6 | 跨平台 | Windows 11 主，可移植 Linux | 不依赖 Windows 特定 API |
| NFR-7 | 安全 | 不上传 APK/日志到外部服务 | 仅本地处理 |
| NFR-8 | 资源 | 测试期间 CPU/内存不爆 | 监控验证 |
| NFR-9 | 文档 | README + 子规范 + 故障排查 | 文档完整 |
| NFR-10 | 兼容 | 与现有 OpenSpec/AGENTS.md 规则一致 | 审计通过 |
| NFR-11 | 零 LLM API 依赖 | 测试脚本不调任何 LLM | 代码审计无 LLM SDK |
| NFR-12 | AI agent 友好 | 输出结构化 JSON + manual 提示词 | AI agent 能直接接入 |
| **NFR-13 V3** | **源码影响分析覆盖率** | 静态调用图覆盖 ≥ 80% Activity | M8 验证 |
| **NFR-14 V3** | **源码→测试生成模式覆盖率** | 正则解析覆盖 ≥ 70% View 体系 | M9 验证 |
| **NFR-15 V3** | **持续降低用户依赖** | 三轮回归后 manual 占比 < 10% | 趋势统计 |
| **NFR-16 V3** | **固化层稳定性** | lib/ 下代码不随用例变化而修改 | 代码审计 |
| **NFR-17 V3** | **反馈闭环审核率** | 规则库扩展建议 100% AI 审核后才入库 | 流程审计 |
| **NFR-18 V3** | **流程注入验证通过** | 阶段 C 7 项检查全 pass | 审计报告 |

---

## 五、Scenarios（场景）

### 5.1 主场景：OpenSpec 步骤 5.5 触发全量回归（V3 升级）

**触发**：AI agent 完成 `network-perf-stability` 任务实施，进入步骤 5.5

```
AI agent:
  1. 完成代码实施 + 单元测试
  2. 触发步骤 5.5：
     python ai_tests/run_e2e.py --apk auto --tc all --diff HEAD~1
系统：
  1. 5.5.1 V3：git diff HEAD~1 → M8 源码影响分析 → affected_modules
  2. 自动发现 app\build\outputs\apk\app\debug\legado_app_3.26.070715.apk
  3. 启动 MEmu 实例 0（已运行则跳过）
  4. 等待 ADB 就绪
  5. init uiautomator2（首次推送 atx-agent）
  6. 卸载旧版 + 安装新 APK
  7. 启动 App，等待首屏
  8. 遍历 docs/tests/*.md，解析 14 份用例（V3：含双轨调度）
  9. 5.5.3 V3：双轨调度——同 TC-ID 检测 auto_*.py，存在则优先执行
  10. 逐用例执行：
      a. 启动 logcat 抓取
      b. 按步骤执行 UI 操作（截图+XML+Activity）
      c. 收集 8 类证据
      d. 停止 logcat，切片
      e. 规则判定 pass/warning/fail/manual
      f. 生成用例报告 + manual 提示词（如需）
  11. 汇总 Markdown + JSON + manual_cases.md + affected_modules.json
  12. 5.5.8 V3：反馈闭环——失败案例提取根因 + 规则库扩展建议
  13. 输出 reports/2026-07-07_143000/
AI agent:
  14. 读取 report.json + manual_cases.md + affected_modules.json
  15. V3：检查 affected_modules，确认是否需要复测关联用例
  16. 对每个 manual 用例：读取 ai-prompt.md + 证据目录，对话分析判定
  17. V3：审核反馈闭环建议（规则库扩展/陷阱库沉淀/提示词调优）
  18. 回填最终报告
用户（步骤 6）:
  19. 查看最终报告，秒级决策
```

### 5.2 子集场景：仅跑 P0 用例

```
python ai_tests/run_e2e.py --apk auto --tc P0
→ 仅执行 P0-network-stability.md + F-P0-1~F-P0-4 用例
```

### 5.3 单用例场景：调试模式

```
python ai_tests/run_e2e.py --apk auto --tc TC-F-P0-1-01 --keep-device
→ 不重启模拟器，仅跑单条用例
```

### 5.4 manual 用例 AI agent 介入场景（V2 沿用）

```
系统输出 reports/{run_id}/manual_cases.md：
  ## Manual 用例清单
  
  ### TC-F-P0-1-03：HTTP 请求工具（正常用例）
  - 证据目录：cases/TC-F-P0-1-03/
  - AI 提示词：cases/TC-F-P0-1-03/ai-prompt.md
  - 原因：规则未匹配预期，但无 FATAL

AI agent 介入：
  1. 读取 ai-prompt.md（含预期+证据摘要+分析引导）
  2. 读取证据目录中的 log-slice.txt / activity-stack.txt / db-state.json
  3. 通过对话能力判定：pass（HTTP 200 + 响应体正确 + Activity 仍在 HttpTestScreen）
  4. 回填到 report.json 的 cases[].ai_verdict
```

### 5.5 失败场景：用例失败不阻断（V2 沿用）

```
用例 TC-F-P0-1-03 失败（HTTP 工具崩溃）
系统：
  1. 捕获异常
  2. 收集证据（截图显示崩溃对话框 + logcat 有 FATAL）
  3. 规则判定 fail (confidence=95)
  4. V3：触发反馈闭环——提取根因（NullPointerException @ HttpTestScreen.kt:42）
  5. V3：输出 rule_suggestion（建议将 NullPointerException 加入 CRASH_PATTERNS）
  6. 继续执行 TC-F-P0-1-04
最终报告：12 通过 / 2 失败 / 0 manual，失败用例详情置顶，含反馈闭环建议
```

### 5.6 模拟器异常场景（V2 沿用）

```
MEmu 启动失败（资源不足）
系统：
  1. 重试 3 次，每次间隔 5s（指数退避）
  2. 仍失败 → 标记致命错误（exit code 2）
  3. 输出诊断信息
AI agent: 报告致命错误，请求用户介入
```

### 5.7 APK 自动发现场景（V2 沿用）

```
用户：python ai_tests/run_e2e.py --apk auto --tc all
系统：
  1. 扫描 app\build\outputs\apk\app\debug\*.apk
  2. 按 mtime 取最新：legado_app_3.26.070715.apk
  3. 校验：存在 + .apk + 大小 > 1MB
  4. 继续...
```

### 5.8 前置资源准备场景（V2 沿用）

```
测试用例 TC-F-P0-1-03 需要 HTTP 测试站点：
  - AI 自备资源：https://httpbin.org/get（脚本内置常量）
  - 无需用户准备

测试用例 TC-F-P1-8 需要 RSS 源：
  - 用户必供资源：ai_tests/cases/F-P1-8/preconditions/rss.json
  - 用户放入文件后才能跑该用例
  - 系统检测缺失 → 跳过 + 标记 "缺前置资源"
```

### 5.9 AI agent 接入场景（V2 沿用 + V3 扩展）

```
下游 AI agent（如 legado-workflow-auditor）：
  1. 读取 reports/{run_id}/report.json
  2. 判定 summary.failed == 0 && summary.manual == 0
  3. 若全 pass → 标记任务完成
  4. 若有 failed → 读取失败用例证据，触发修复流程
  5. 若有 manual → 读取 manual_cases.md + ai-prompt.md，对话分析
  6. V3：读取 affected_modules.json → 检查是否漏测关联用例
  7. V3：审核反馈闭环建议（规则库扩展/陷阱库沉淀）→ 入库或拒绝
```

### 5.10 边界场景（V2 沿用 + V3 扩展）

| 场景 | 处理 |
|------|------|
| APK 目录无 APK | 报错"未发现 APK，请先 ./gradlew assembleAppDebug" |
| APK 后缀非 .apk | 报错 |
| MEmu 未安装 | 报错，提示路径 |
| ADB 连接失败 | 重试 3 次，仍失败 exit 2 |
| atx-agent 推送失败 | 重试 3 次，仍失败跳过该用例 |
| 用例解析失败 | 标记 `parse_warning`，跳过 |
| 单步超时（30s） | 标记该步失败，继续下步 |
| logcat 子进程崩溃 | 重启子进程，记录 gap |
| 前置资源缺失 | 跳过用例 + 标记"缺前置资源" |
| 磁盘空间不足（<1GB） | 启动前检查，不足报错 |
| Web 接口未启动（8080 端口） | 跳过该类证据，标记"Web API 不可用" |
| 数据库查询失败（run-at 不可用） | 跳过该类证据，标记"DB 查询失败" |
| **V3：git diff 无改动** | 提示"无源码改动，跳过影响分析"，全量回归 |
| **V3：source_map.json 缺失** | 自动触发首次构建，记录构建耗时 |
| **V3：M9 生成失败** | 标记 `gen_test_failed`，AI 手动补全 |
| **V3：双轨用例 TC-ID 冲突** | 两个 MD 同 TC-ID 时报错，要求重命名 |
| **V3：反馈闭环建议被拒绝** | 记录到 regression_history.md，不阻断流程 |
| **V3：流程注入验证失败** | 阶段 C 检查项 fail 时记录到审计报告 |

### 5.11 V3 新增场景：源码影响分析

```
AI agent 实施 network-perf-stability 任务，改动了 BookSourceDao.kt
触发步骤 5.5.1：
  python ai_tests/run_e2e.py --apk auto --tc all --diff HEAD~1
系统 M8：
  1. git diff HEAD~1 → 改动文件：[BookSourceDao.kt, BookSourceViewModel.kt]
  2. 加载 source_map.json：
     "BookSourceDao.kt" → callers: [BookSourceEditActivity, BookSourceListActivity]
     "BookSourceViewModel.kt" → callers: [BookSourceEditActivity, BookSourceListActivity]
  3. 反向追踪 → affected_activities: [BookSourceEditActivity, BookSourceListActivity]
  4. 查关联 TC-ID：
     BookSourceEditActivity → TC-F-P0-2-01, TC-F-P0-2-02
     BookSourceListActivity → TC-F-P0-2-03
  5. 输出 affected_modules.json：
     {
       "changed_files": ["BookSourceDao.kt", "BookSourceViewModel.kt"],
       "affected_activities": ["BookSourceEditActivity", "BookSourceListActivity"],
       "suggested_retest_tc_ids": ["TC-F-P0-2-01", "TC-F-P0-2-02", "TC-F-P0-2-03"]
     }
AI agent:
  - 确认这些用例已被全量回归覆盖（--tc all）
  - 若 --tc P0，则提示需要补充复测
```

### 5.12 V3 新增场景：双轨用例执行

```
TC-F-P0-1-01 既有 MD 又有 Python：
  - docs/tests/F-P0-1-debug-tools.md（A 轨）
  - ai_tests/cases/F-P0-1/auto_TC-F-P0-1-01.py（B 轨）

系统 M3 调度：
  1. 检测到 auto_TC-F-P0-1-01.py 存在
  2. 优先执行 B 轨（Python），跳过 A 轨（MD）
  3. 报告标记 track_source: "python"
  
若 B 轨执行失败（import 错误等）：
  1. 标记 B 轨失败
  2. 降级执行 A 轨（MD）
  3. 报告标记 track_source: "md (python_failed)"
```

### 5.13 V3 新增场景：源码→测试生成

```
AI agent 新增了 ImportActivity 功能
触发 M9：
  python ai_tests/run_e2e.py --gen-test ImportActivity
系统 M9：
  1. 定位源码：app/src/main/java/io/legado/app/ui/association/ImportActivity.kt
  2. 解析源码：
     - setContentView(R.layout.activity_import)
     - findViewById<Button>(R.id.btn_import)
     - findViewById<EditText>(R.id.et_url)
     - startActivity(Intent(this, BookshelfActivity::class.java))
  3. 解析 AndroidManifest.xml：ImportActivity 已注册
  4. 生成 Python 骨架：
     # ai_tests/cases/F-P2-import/auto_TC-F-P2-XX-01.py
     class TestImportActivity:
         def test_import_flow(self, device):
             device(resourceId="io.legado.app:id/btn_import").click()
             device(resourceId="io.legado.app:id/et_url").set_text("test_url")
             # TODO: 补全业务逻辑
             # TODO: 补全断言
             assert device(activity="BookshelfActivity").exists
  5. AI agent 补全 TODO 部分
  6. 纳入存量用例库
```

### 5.14 V3 新增场景：反馈闭环

```
本轮回归：
  - 14 用例，2 failed，3 manual
  - 失败用例 1：NullPointerException @ HttpTestScreen.kt:42
  - 失败用例 2：OutOfMemoryError @ BookCoverLoader.kt
  - manual 用例：网络延迟导致预期未及时显示

触发反馈闭环（步骤 5.5.8）：
  python ai_tests/run_e2e.py --feedback reports/2026-07-07_143000/
系统：
  1. 提取失败根因：
     - NullPointerException → 已在 CRASH_PATTERNS，无需扩展
     - OutOfMemoryError → 已在 CRASH_PATTERNS，无需扩展
  2. 提取 manual 根因：
     - 网络延迟导致预期未及时显示 → 建议扩展规则：
       "等待时间不足 → 自动延长 timeout 后重试"
  3. 输出建议清单：
     rule_suggestion:
       - 添加规则 5：网络相关 manual → 自动延长 timeout 重试
     prompt_suggestion:
       - ai-prompt.md 加入"网络延迟"判定引导
     known_issue_suggestion:
       - "HTTP 测试可能因网络延迟误判，建议增加 timeout"
  4. AI agent 审核：
     - rule_suggestion 接受 → 加入 CRASH_PATTERNS
     - prompt_suggestion 接受 → 调优模板
     - known_issue_suggestion 接受 → 写入 known_issues.md
  5. 记录到 regression_history.md：
     "第 1 轮：14 用例，2 failed，3 manual（21% manual）"
下一轮预期：
  - manual 占比降低（网络延迟场景自动延长 timeout 后判定）
```

### 5.15 V3 新增场景：流程注入验证

```
阶段 C 验证：
  让另一个 AI agent 按 V3 流程做一次 /openspec：
  1. 设计新功能 spec
  2. 实施 code（仅 mock 改动）
  3. 触发步骤 5.5
  
验证清单：
  [✓] 5.5.1 源码影响分析能正确执行（git diff → affected_modules）
  [✓] 5.5.2 APK 自动发现 + MEmu 启动
  [✓] 5.5.3 双轨用例调度正确（同 TC-ID 时 Python 优先）
  [✓] 5.5.4 8 类证据收集
  [✓] 5.5.5 规则判定
  [✓] 5.5.6 manual 用例 AI agent 介入
  [✓] 5.5.7 三件套报告生成
  [✓] 5.5.8 反馈闭环触发
  
输出审计报告：
  pass: 7/7
  备注反馈：流程可被 AI agent 正确执行
```
