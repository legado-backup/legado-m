# design.md — legado-source-creator Skill 改进

> **状态**：🔄 设计中 | **创建日期**：2026-06-03

---

## 1. Technical Approach（技术方法）

### 1.1 三阶段流水线

```
Phase 1: 源码验证（9组并行） → Phase 2: 文档改进（13项） → Phase 3: SKILL.md 流程优化（4项）
```

**Phase 1 核心方法**：
- 使用 Grep/Read 工具读取 Legado 源码中对应的 .kt 文件
- 定位方法/字段的定义和签名
- 记录验证结论到 `references/source-analysis/` 对应文档
- 验证不通过的内容不写入正式文档

**Phase 2 核心方法**：
- 基于验证结果，使用 SearchReplace 更新现有文档
- 使用 Write 创建新文档
- 所有新增内容附带源码依据（文件名+行号）

**Phase 3 核心方法**：
- 更新 SKILL.md 工作流程
- 更新 AI_README.md 导航

### 1.2 验证方法分类

| 验证类型 | 源码确认方法 | 测试验证方法 | 工具 |
|----------|-------------|-------------|------|
| 方法存在性 | Grep 方法名在 JsExtensions.kt 中 | 用 Rhino JAR 调用方法验证返回值 | Grep + Read + RunCommand |
| 字段存在性 | Grep 字段名在实体类中 | 用 Python 脚本构造对象验证字段 | Grep + Read + RunCommand |
| 语法解析逻辑 | 读取 AnalyzeRule.kt / RuleAnalyzer.kt | 用 Python 模拟解析或用 Rhino JAR 执行规则 | Read + RunCommand |
| 选择器兼容性 | 读取 AnalyzeByJSoup.kt + jsoup 文档 | 用 Python + jsoup 库测试选择器 | Read + WebSearch + RunCommand |
| Rhino 陷阱 | 读取 RhinoScriptEngine.kt | 用 Rhino JAR 编写测试脚本验证 | Read + RunCommand |

**验证铁律**：源码确认 + 测试验证，缺一不可。只有两者都通过的经验才能写入正式文档。

### 1.3 文档组织原则

- **SKILL.md**：只放流程和规则，不超过 700 行
- **references/rule-syntax.md**：语法规则集中文档
- **references/js-extensions/**：JS 扩展方法按类别拆分
- **references/special-scenarios/**：特殊场景按功能拆分
- **references/source-analysis/**：源码验证结果

---

## 2. Architecture Decisions（架构决策）

### AD1: 新增内容放入 references/ 而非 SKILL.md

**决策**：所有新增的技术细节放入 references/ 子文档，SKILL.md 只放流程指引和必读文档清单。

**理由**：
- SKILL.md 当前 560 行，精炼高效
- 阅读Skill 的 SKILL.md 4600 行过于冗长，是反面教材
- AI 可以按需读取 references/ 子文档，不会遗漏

### AD2: 源码验证结果独立存档

**决策**：每项验证结果写入 `references/source-analysis/` 独立文档，而非直接修改正式文档。

**理由**：
- 验证过程本身是有价值的知识（为什么某个方法存在/不存在）
- 独立存档便于后续复查和自进化
- 正式文档只包含验证通过的结论

### AD3: 以 lyc 魔改版源码为准

**决策**：所有功能验证以 lyc 魔改版源码（`gitee.com/lyc486/legado`）为准。阅读Skill 中提到的功能，只要在 lyc 魔改版中存在且测试通过，就采纳。

**理由**：
- 我们的项目就是 lyc 魔改版，不是原版 Legado
- lyc 魔改版可能包含原版没有的功能（如 `source.put/get` 键值对、`book.putVariable` 等）
- 阅读Skill 混合了原版和魔改版功能描述，我们以自己的源码为唯一权威

### AD4: 按优先级分批实施

**决策**：15 个改进项按优先级分三批实施。

**批次**：
- **P0（最高优先级）**：改进项 1（Default 语法）、改进项 2（全局对象 API）、改进项 12（新 Rhino 陷阱）
- **P1（高优先级）**：改进项 3-7（变量系统、搜索技巧、详情/目录/正文技巧、编码指南、动态加载）
- **P2（中优先级）**：改进项 8-15（登录 API、HTML 检查清单、nextContentUrl、正则分类、JS 方法补充、高级模式库、SKILL.md 优化）

---

## 3. Data Flow（数据流）

### 3.1 源码确认 + 测试验证数据流

```
阅读Skill 经验声明
    ↓
lyc 魔改版源码 (.kt 文件)
    ↓ Grep/Read
源码确认结论（存在/不存在/签名不同）
    ↓ 存在的进入下一步
编写测试方法（Python 脚本 / Rhino JAR）
    ↓ RunCommand
测试结果（通过/不通过）
    ↓ 通过的进入下一步
references/source-analysis/{topic}.md（验证结论+测试结果）
    ↓ 验证通过
references/{对应子文档}.md（正式文档更新）
```

### 3.2 文档改进数据流

```
验证通过的结论
    ↓
分类归入对应 references/ 子文档
    ├── rule-syntax.md ← Default 语法 + 正则分类 + 变量系统 + nextContentUrl
    ├── js-extensions/global-objects.md ← 全局对象 API（新建）
    ├── js-extensions/{各子文档}.md ← JS 方法补充
    ├── special-scenarios/search-advanced.md ← 搜索技巧（新建）
    ├── special-scenarios/content-advanced.md ← 正文技巧（新建）
    ├── special-scenarios/toc-advanced.md ← 目录技巧（新建）
    ├── special-scenarios/encoding-guide.md ← 编码指南（新建）
    ├── special-scenarios/advanced-patterns.md ← 高级模式库（新建）
    ├── troubleshooting/diagnosis-flow.md ← 诊断流程（新建）
    └── html-analysis-checklist.md ← HTML 检查清单（新建）
```

### 3.3 SKILL.md 流程优化数据流

```
SKILL.md 当前流程
    ↓ 增加3个子步骤
步骤1"分析目标网站"中增加：
    - 1.0 必读参考文档（按任务类型索引）
    - 1.1 编码检测（curl -sI / meta 标签）
    - 1.2 获取原始 HTML（curl，不信任浏览器 DOM）
```

---

## 4. File Changes（文件变更）

### 4.1 新建文件

| 文件路径 | 内容 | 改进项 |
|----------|------|--------|
| `references/js-extensions/global-objects.md` | book/chapter/source/cookie/cache 完整 API | R2 |
| `references/special-scenarios/search-advanced.md` | 搜索高级技巧 6 种模式 | R4 |
| `references/special-scenarios/content-advanced.md` | 正文高级技巧 | R5 |
| `references/special-scenarios/toc-advanced.md` | 目录高级技巧 | R5 |
| `references/special-scenarios/encoding-guide.md` | 编码处理完整指南 | R6 |
| `references/special-scenarios/advanced-patterns.md` | 高级功能模式库 | R14 |
| `references/html-analysis-checklist.md` | HTML 分析检查清单 | R9 |
| `references/troubleshooting/diagnosis-flow.md` | 问题诊断流程 | - |
| `references/source-analysis/default-syntax.md` | Default 语法验证结果 | Phase 1 |
| `references/source-analysis/selector-compatibility.md` | 选择器兼容性验证 | Phase 1 |
| `references/source-analysis/variable-system.md` | 变量系统验证 | Phase 1 |
| `references/source-analysis/regex-modes.md` | 正则模式验证 | Phase 1 |
| `references/source-analysis/webview-mechanism.md` | WebView 机制验证 | Phase 1 |
| `references/source-analysis/rhino-const-trap.md` | Rhino const 陷阱验证 | Phase 1 |
| `references/source-analysis/global-objects-api.md` | 全局对象 API 验证 | Phase 1 |
| `references/source-analysis/encoding-network-api.md` | 编码/网络方法验证 | Phase 1 |
| `references/source-analysis/login-crypto-font-api.md` | 登录/加密/字体方法验证 | Phase 1 |

### 4.2 修改文件

| 文件路径 | 修改内容 | 改进项 |
|----------|---------|--------|
| `references/rule-syntax.md` | 新增 Default 语法章节 + 正则分类 + 变量系统 + nextContentUrl | R1/R3/R10/R11 |
| `references/js-extensions/webview.md` | 补充四种 webView 启用方式 + webJs 返回值限制 | R7 |
| `references/special-scenarios/login.md` | 补充 loginCheckJs API + 登录头管理 | R8 |
| `references/js-extensions/crypto-encoding.md` | 补充非对称加密/签名/strToBytes/bytesToStr | R13 |
| `references/js-extensions/network.md` | 补充 ajaxAll/ajaxTestAll/head/webViewGetOverrideUrl | R13 |
| `references/js-extensions/font-anti-crawl.md` | 补充 queryTTF/replaceFont | R13 |
| `references/js-extensions/utils.md` | 补充 s2t/t2s/encodeURI/timeFormat 等 | R13 |
| `SKILL.md` | 流程优化：必读参考文档 + 编码检测前置 + 强制获取原始 HTML | R15 |
| `AI_README.md` | 更新导航索引 | - |
| `AGENTS.md` | 陷阱清单新增 4 条 | R12 |

### 4.3 删除文件

无删除。之前的 `temp/skill-comparison-design-doc.md` 是临时分析文档，不在正式变更范围内。
