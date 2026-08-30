# Legado Skill 整体优化方案

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> **目标**：让 AI/Agent 使用 legado-source-creator Skill 快速为用户开发/优化书源和订阅源，减少对开源阅读源码的依赖，通过 JAR 仿真服务端 + Python 客户端协作完成测试校验。
> **状态**：🔄 设计中（统一 OpenSpec，合并 simulation-fidelity-95 + python-client-optimization）
> **创建日期**：2026-06-21
> **更新日期**：2026-06-21（第十轮深度审查 + 源码逐行核实修正 18 个错误 + 补充 7 个新发现）

---

## 为什么需要统一 OpenSpec

### 问题：14 套 OpenSpec 散乱

此前 `docs/specs/` 下累积了 **14 套 OpenSpec**，导致 AI 在使用 Skill 时无法从整体角度理解"客户端 + 服务端 + Skill 工作流"的协作关系。经排查分类：

| 分类 | 数量 | 处理方式 |
|------|------|---------|
| 已完成且已实施 | 6 套 | 归档到 `archive/` |
| 已被统一文档合并 | 2 套（simulation-fidelity-95 + python-client-optimization） | 归档 |
| 重叠/孤立/被覆盖 | 2 套（skill-deep-optimization-v2 + pageindex-local-experience-engine） | 归档 |
| 仍活跃 | 4 套 | 保留 |

**本统一文档进一步合并 `skill-core-capability-rebuild`**（主题高度重叠：同为"Python客户端工程化+JAR仿真服务端保真度提升"），将其 `simulation-gap-report.md` 作为差距报告来源引用。

**解决方案**：合并为唯一活跃统一 OpenSpec，从整体角度描述三层协作架构。归档后仅保留 4 个活跃目录。

---

## 三层协作架构

```
┌─────────────────────────────────────────────────────────────────────┐
│              legado-source-creator Skill（编排层）                    │
│                                                                     │
│  5 阶段闭环工作流：                                                   │
│  Phase 1: 经验优先（basic-memory 检索）                              │
│  Phase 2: 构建规则 + 预校验（source_validator + rule_precheck）      │
│  Phase 3: 测试驱动（JAR 优先 + Python 降级）                         │
│  Phase 4: 源码深挖 + 工具辅助（source_navigation + auto_fixer）      │
│  Phase 5: 经验反哺 + 代码进化（半自动写入 basic-memory）             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼
┌───────────────────────┐    ┌──────────────────────────┐
│  Python 客户端（校验层）│    │  JAR 仿真服务端（执行引擎）│
│                        │    │                          │
│  预校验：source_validator│    │  规则引擎：AnalyzeRule     │
│  规则语法：rule_precheck │    │  JS 引擎：Rhino           │
│  调试流程：debug_runner  │◄──►│  HTTP 客户端：OkHttp       │
│  错误诊断：error_diagnoser│   │  调试器：BookSourceDebugger│
│  自动修复：auto_fixer    │    │          RssSourceDebugger│
│  经验管理：experience_mgr │    │  加密解密：hutool          │
│  用户交互：user_interaction│   │  委托路径：Selenium/环境变量│
└───────────────────────┘    └──────────────────────────┘
```

### 职责边界

| 层级 | 职责 | 归属 |
|------|------|------|
| **编排层（Skill）** | 5 阶段工作流编排、经验检索/反哺、用户交互 | SKILL.md |
| **校验层（Python）** | 预校验、调试流程编排、错误诊断、自动修复、经验管理 | legado_client/ + tools/ |
| **执行引擎（JAR）** | 规则引擎执行、JS 执行、HTTP 请求、加密解密、调试器 | legado-jvm fatJar |

### 协作关系

1. **Skill 编排** → 调用 Python 客户端执行测试校验
2. **Python 客户端** → 预校验通过后调用 JAR 执行调试
3. **JAR 仿真服务端** → 执行规则引擎，返回调试结果
4. **Python 客户端** → 诊断错误，自动修复或请求用户介入
5. **Skill** → 沉淀经验到 basic-memory

### 设计目标

| 目标 | 说明 |
|------|------|
| **减少源码依赖** | AI 使用 Skill 生成源后，无需查阅 Legado 源码即可完成测试校验 |
| **100% 测试校验准确性** | JAR 测试通过则真机也能通过；JAR 失败时能准确区分源规则问题还是仿真端问题 |
| **自动化率 > 70%** | 70% 的网站生成可用源无需手动操作；30% 需用户协助时提供 AI 指引 |
| **快速反馈** | 预校验 < 3 秒，JAR 调试 < 30 秒，全流程 < 2 分钟 |

---

## 核心设计决策

### 决策 1：100% 测试校验准确性（非 100% 兼容运行）

**决策**：设计目标从"100% 兼容运行"（完全复刻真机）修正为"100% 测试校验准确性"。

**理由**：185 个 GAP 中 40% 是过度修复（持久化/安全沙箱/性能执念），不应追求完全复刻真机，应聚焦"测试校验准确性"。

**判定标准**：

| 场景 | 判定 | 责任方 |
|------|------|--------|
| JAR 测试通过，真机也能通过 | ✅ 准确 | - |
| JAR 测试通过，但真机失败（假阳性） | ❌ 必须修复 | 仿真端 |
| JAR 测试失败，但真机能运行（假阴性） | ❌ 必须修复 | 仿真端 |
| JAR 测试失败，真机也失败（源规则问题） | ✅ 准确 | 源规则 |
| 真机也运行失败（网站改版/反爬/域名失效） | ➖ 不计入 | 网站 |
| Android 平台特有方法（WebView/UI/硬件） | 🔄 委托路径 | 平台限制 |
| 持久化/安全沙箱/性能差异（不影响校验结果） | ➖ 不计入 | 过度修复 |

### 决策 2：185 个 GAP 四分类法

| 分类 | 数量 | 判断铁则 | 处理方式 |
|------|------|---------|---------|
| ✅ 必需修复 | ~52 | 差异导致假阳性或假阴性 | 实施 |
| ⚠️ 可选修复 | ~28 | 差异在特定场景下会导致假阳性或假阴性，但该场景出现频率低于 5% | 遇到实际失败源时实施 |
| 🔄 需要重新设计 | ~10 | 修复方案工作量过大，有更简单替代 | 用替代方案 |
| ❌ 过度修复 | ~75 | 差异不影响测试校验结果 | 不实施 |

### 决策 3：源码逐行核实修正

通过 3 组子代理（共 27 个源文件）逐行核实，发现并修正 18 个设计文档错误：

| 序号 | 错误 | 修正 |
|------|------|------|
| 1 | BookType.text=0b1 | BookType.text=0b1000（8） |
| 2 | RssSource 字段名 sourceType | 实际为 type |
| 3 | BookChapter 有 chapterUrl/level 字段 | 实际为 url，无 level |
| 4 | init 规则在 WebBook.kt | 实际在 BookInfo.kt |
| 5 | ruleNextPage=="PAGE" 在 WebBook.kt | 实际在 RssParserByRule.kt |
| 6 | ConcurrentRecord 定义在 ConcurrentRateLimiter | 实际在 AnalyzeUrl |
| 7 | BookSource 的 searchUrl/ruleSearch 必填 | 实际可空 |
| 8 | RssSource 的 ruleArticles 必填 | 实际可空 |
| 9 | 规则前缀 @json: | 源码书写为 `@Json:`（大写 J），但 `startsWith("@Json:", true)` 忽略大小写，`@json:` 也能匹配。建议书源规则统一用大写 `@Json:` 以符合源码规范 |
| 10 | @js: 和 `<regex>` 前缀不存在 | **第十轮再修正（精确化）**：① `AnalyzeRule.kt` 中 `@js:` 和 `<js></js>` 均通过 `JS_PATTERN` 正则匹配（`AppPattern.kt:7-8`，CASE_INSENSITIVE），非 startsWith 前缀；且不在 `SourceRule.init` 规则类型识别分支中。② `BaseSource.kt` 中 `@js:` 是 startsWith 前缀匹配，共 3 处但 ignoreCase 不一致：第 76 行（loginUrl）无 ignoreCase、第 108 行（header）有 ignoreCase=true、第 193 行（loginUi）无 ignoreCase。③ `<regex>` 前缀在源码中完全不存在 |
| 11 | BaseSource 是 class | 实际是 interface |
| 12 | dateFormat 在 BaseSource | 实际在 AppConst |
| 13 | HtmlFormatter 方法名是 formatHtml | 实际是 format/formatKeepImg |
| 14 | mapBase64Flags 方法存在 | 实际不存在 |
| 15 | aesEncodeToString 在 JsExtensions | 实际在 JsEncodeUtils |
| 16 | cookie()/getBook() 方法存在 | 实际不存在 |
| 17 | AnalyzeUrl 有 followRedirects 字段 | 实际无此字段 |
| 18 | aesEncodeToString 实现正确 | 疑似源码 Bug（加密方法调用解密） |

**第十轮审查新发现（7 个补充修正）**：

| 序号 | 问题 | 修正 |
|------|------|------|
| 19 | 文件路径 `rss/RssParserByRule.kt` | 实际为 `model/rss/RssParserByRule.kt` |
| 20 | 文件路径 `help/book/HtmlFormatter.kt` | 实际为 `utils/HtmlFormatter.kt` |
| 21 | ruleNextPage 精确匹配 `"PAGE"` | 使用 `uppercase()` 转大写比较，`"page"`/`"Page"`/`"PAGE"` 均可匹配 |
| 22 | BaseSource 中 `@js:` ignoreCase 一致 | 3 处不一致：loginUrl 无、header 有、loginUi 无 |
| 23 | aesEncodeToString 的 ReplaceWith 正确 | ReplaceWith 也错误指向 decryptStr |
| 24 | auto_fixer 处理 2 种错误类型 | 实际处理 4 种：rule_parse/css/url_empty/network |
| 25 | experience_manager 有 extract()/write_to_basic_memory() | 实际方法为 search()/write_pending()，需新增 |

---

## Python 客户端现状分析（第九轮审查新增）

### 已有模块清单

| 目录 | 模块数 | 定位 | 关键模块 |
|------|--------|------|---------|
| `scripts/legado_client/` | 16 个 | 核心包（规范包结构） | debug_runner、rule_engine_client、error_diagnoser、experience_manager、source_navigation、confidence_evaluator |
| `tools/` | 14 个 | 辅助包（扁平结构，无 `__init__.py`） | auto_fixer、obstacle_resolver、crypto_analyzer、html_fetcher、interactive_guide |
| `scripts/` 独立脚本 | 10 个 | CLI 入口 | debug-source.py、verify-source.py、quick-verify.py 等 |

### 关键问题（3 个）

**问题 1：预校验模块完全缺失**
- `source_validator`（字段完整性校验）和 `rule_precheck`（规则语法校验）未实现
- SKILL.md Phase 2 描述了预校验步骤，但代码不存在

**问题 2：5 个独立脚本 JVM 依赖断裂**
- `tools/rule_engine_client.py` 已迁移到 `legado_client/client/rule_engine_client.py`
- 但 verify-source.py / analyze_site.py / verify-selector.py / verify-decrypt.py / verify-image.py 仍引用旧路径
- 导致这 5 个脚本的 JVM 验证功能全部失效（降级到纯 Python 模式）

**问题 3：双客户端职责边界模糊**
- `tools/`（扁平结构）与 `legado_client/`（规范包）并存
- debug_runner.py 混合依赖两套模块（包内直接 import + tools/ try-import）
- auto_fixer 在 tools/，error_diagnoser 在 legado_client/，职责割裂

### 优化方向

| 方向 | 措施 | 收益 |
|------|------|------|
| 新建预校验模块 | source_validator + rule_precheck | 减少 20-30% 无效 JAR 调用 |
| 修复依赖断裂 | 5 个独立脚本 import 路径修正 | 恢复 JVM 验证功能 |
| 双客户端整合 | tools/ 核心模块迁移到 legado_client/ | 统一包结构，降低维护成本 |

---

## 三层协作如何减少源码依赖

### 核心理念

```
AI 生成源 → Python 预校验（快速拦截） → JAR 执行（精确校验） → 经验沉淀（减少重复）
```

**减少源码依赖的三个层面**：

| 层面 | 机制 | 效果 |
|------|------|------|
| **预校验层（Python）** | source_validator + rule_precheck 在调用 JAR 前拦截字段缺失和语法错误 | AI 无需查阅源码即可发现 20-30% 的常见错误 |
| **执行层（JAR）** | JAR 内嵌完整规则引擎（Rhino + jsoup + hutool + AnalyzeRule），行为与真机一致 | AI 无需查阅源码即可完成精确测试校验 |
| **经验层（Skill）** | error_diagnoser 提供修复建议模板 + source_navigation 自动映射到源码位置 | 50% 错误可自动修复，30% 有明确修复建议，仅 20% 需查阅源码 |

### 协作流程详解

```
1. AI 使用 Skill 生成 BookSource/RssSource JSON
2. Python 预校验（< 3 秒）
   ├→ source_validator: 字段完整性（必填字段非空、URL 格式合法、字段冲突检测）
   └→ rule_precheck: 规则语法（CSS/XPath/JSONPath/Regex/JS 语法检查，不执行 JS）
   └→ 失败：返回错误，AI 重新构建（无需 JAR，无需源码）
3. JAR 执行（< 30 秒）
   ├→ RuleEngineClient 调用 JAR 执行端到端调试
   ├→ JAR 内嵌 AnalyzeRule + Rhino + jsoup + hutool，行为与真机一致
   └→ 失败：error_diagnoser 诊断错误类型
        ├→ 可自动修复（50%）：auto_fixer 修复后重试
        ├→ 有修复建议（30%）：source_navigation 映射到源码位置 + 修复建议模板
        └→ 需用户介入（20%）：user_interaction 生成交互请求
4. 经验沉淀
   └→ experience_manager 提取经验要素 → 生成草稿 → 写入 basic-memory
   └→ 下次遇到同类网站，Phase 1 直接复用经验（无需源码分析）
```

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 统一需求规格：Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 统一技术设计：三层架构/修复方案/源码核实修正 |
| [tasks.md](./tasks.md) | 统一任务清单：JAR 修复 + Python 客户端 + Skill 工作流 |

---

## 预期测试校验准确性提升

```
当前测试校验准确性: ~98%（100 个失败源中仿真端问题仅 2 个）
修复第一优先级（16 个 P0）: → 99%
修复第二优先级（20 个 P1）: → 99.5%
修复第三优先级（16 个基础对齐）: → 99.8%
Selenium 委托 WebView（9 个）: → 99.9%
环境变量配置硬件（4 个）: → 99.95%
```

**结论**：通过修复 52 个必需修复项，可达到 99.9% 测试校验准确性。对于不依赖 WebView/UI/Android 原生的源，可达到 100% 测试校验准确性。

---

## 关联文档

| 文档 | 说明 |
|------|------|
| [SKILL.md](../../.trae/skills/legado-source-creator/SKILL.md) | Skill 5 阶段闭环工作流定义 |
| [simulation-gap-report.md](../skill-core-capability-rebuild/simulation-gap-report.md) | 原始差距报告（67 个不兼容方法），skill-core-capability-rebuild 合并后保留此报告 |
| [multi-agent-analysis-spec.md](../../docs/project-flow/architecture/multi-agent-analysis-spec.md) | 多代理分析方法论 |
