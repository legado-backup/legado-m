---
name: legado-skill-auditor
description: Legado Skill 全面审查与优化器。对 legado-source-creator skill 进行8维度深度审查（文档完整性、代码-文档一致性、脚本验证、Legado源码匹配、basic-memory双向同步、新用户视角、设计文档状态、文件债务清理），采用 L1/L2/L3 三层分层审查（42检查点，合并后约30模块），输出3部分结构化审查报告并执行精准修复。
---

# Legado Skill 全面审查与优化器

> 对 `legado-source-creator` skill 进行全方位、无死角的深度审查与优化，确保 skill 能让 AI 更快捷、更方便、更准确地生成书源和订阅源。

## 触发条件

| 触发词 | 示例 |
|--------|------|
| 审查skill | "审查legado-source-creator" / "审查skill" / "skill审查" |
| 优化skill | "优化legado-source-creator" / "优化skill" / "skill优化" |
| 全面审查 | "全面审查" / "深度审查" / "无死角审查" |
| skill质量 | "skill质量检查" / "skill健康度" / "skill诊断" |
| 审计skill | "审计skill" / "skill审计" |

---

## 审查范围

```
legado-source-creator/
├── SKILL.md                    ← A.文档完整性 + B.代码-文档一致性 + F.新用户视角
├── AI_README.md                ← A.文档完整性 + B.代码-文档一致性
├── references/                 ← A.文档完整性（死链/薄文件/数量不一致/缺失文档）
│   ├── _INDEX.md               ← A3 子文档数量一致性
│   ├── troubleshooting/_index.md ← A3 子文档数量一致性
│   ├── js-extensions/_index.md   ← A3 子文档数量一致性
│   ├── js-patterns/_index.md     ← A3 子文档数量一致性
│   ├── special-scenarios/_index.md ← A3 子文档数量一致性
│   └── source-analysis/_index.md  ← A3 子文档数量一致性
├── scripts/                    ← C.脚本验证（语法/参数/导入）+ H2 临时脚本检测
├── tools/                      ← B.代码-文档一致性 + C.脚本验证 + D.Legado源码匹配 + H.文件债务
│   ├── legado-jvm/             ← B1 Kotlin源码清单 + B5 版本锁 + D2 JVM组件
│   │   ├── src/main/kotlin/    ← Kotlin源文件逐一审查
│   │   └── build.gradle.kts    ← B5 版本锁一致性
│   ├── legado-jvm/build/libs/legado-jvm.jar ← C4 JAR文件验证
│   ├── rhino-1.8.1.jar         ← Rhino测试引擎
│   ├── html_fetcher.py         ← HTML获取回退链
│   ├── cookie_manager.py       ← Cookie管理
│   ├── degradation_chain.py    ← 降级链
│   ├── smart_http_client.py    ← 智能HTTP客户端
│   ├── knowledge_matcher.py    ← 知识匹配
│   └── user_action_minimizer.py ← 用户操作最小化
├── templates/                  ← S1 模板文件验证
├── references/cms-samples/     ← S2 CMS样本验证
└── output/                     ← S5 输出目录验证

AGENTS.md (项目根目录)           ← A2 跨文件一致性
legado-workflow-auditor/SKILL.md ← S3 跨skill一致性
basic-memory (project=legado)   ← E.basic-memory双向同步
docs/specs/                     ← G.设计文档状态
```

---

## 8维度37子项 + 5补充检查 审查框架（L1/L2/L3 三层分层）

> **审查顺序**：A→B→C→D→E→F→G→H→S，每维度输出子报告，最终汇总。
> 编号：A1-A4, B1-B5, C1-C4, D1-D4, E1-E4, F1-F3, G1-G3, H1-H10 = 37主项 + S1-S5 = 42总检查点。
>
> **分层审查**：42 项检查点按执行深度分为 L1/L2/L3 三层，合并 4 组相关项后约 30 个逻辑检查模块。
> - **L1 快速检查（10项）**：最高频、最快速的检查（文件债务、死链接、语法验证等），5 分钟内完成
> - **L2 核心检查（15项）**：代码一致性、文档一致性、跨文件一致性等，20 分钟内完成
> - **L3 深度检查（17项）**：memory 一致性、源码验证、债务深度检测等，含 4 个合并模块

### L1/L2/L3 三层检查清单

#### L1 快速检查（10项）— 5 分钟内完成

| 序号 | 检查点 | 维度 | 说明 |
|------|--------|------|------|
| L1-1 | A1 | A | 文件引用断链检查 |
| L1-2 | A3 | A | 子文档数量一致性 |
| L1-3 | C1 | C | Python脚本语法验证 |
| L1-4 | C4 | C | JAR文件验证（存在性+可启动性） |
| L1-5 | H7 | H | 废弃文件引用清理 |
| L1-6 | S1 | S | 模板文件验证 |
| L1-7 | S2 | S | CMS样本验证 |
| L1-8 | S5 | S | 输出目录验证 |
| L1-9 | E3 | E | 重复笔记检测 |
| L1-10 | E4 | E | L3目录结构 vs SKILL.md描述 |

#### L2 核心检查（15项）— 20 分钟内完成

| 序号 | 检查点 | 维度 | 说明 |
|------|--------|------|------|
| L2-1 | A2 | A | 跨文件一致性（SKILL.md vs AI_README.md vs AGENTS.md） |
| L2-2 | B2 | B | Python客户端 vs SKILL.md API描述 |
| L2-3 | B3 | B | 可信度评估逻辑一致性（Kotlin vs Python vs SKILL.md） |
| L2-4 | B4 | B | ES5/ES6模式一致性 |
| L2-5 | B5 | B | build.gradle.kts 版本锁一致性 |
| L2-6 | C2 | C | 脚本参数与SKILL.md描述是否一致 |
| L2-7 | C3 | C | 脚本导入路径是否正确 |
| L2-8 | D2 | D | 所有JVM仿真器组件行为 vs Legado源码 |
| L2-9 | F1 | F | SKILL.md可读性（新agent视角） |
| L2-10 | F2 | F | 缺失信息检测 |
| L2-11 | F3 | F | 模糊描述检测 |
| L2-12 | S3 | S | 跨skill一致性 |
| L2-13 | S4 | S | html_fetcher.py 回退链验证 |
| L2-14 | G1 | G | spec.md需求项 vs 实际完成状态 |
| L2-15 | G3 | G | tasks.md任务状态 vs 实际完成情况 |

#### L3 深度检查（17项）— 含 4 个合并模块

| 序号 | 检查点 | 维度 | 说明 | 所属合并模块 |
|------|--------|------|------|------------|
| L3-1 | H1 | H | 旧版源码文件检测 | 文件债务快速扫描 |
| L3-2 | H2 | H | 旧版/临时测试脚本检测 | 文件债务快速扫描 |
| L3-3 | H3 | H | 功能已被替代的旧文件检测 | 文件债务快速扫描 |
| L3-4 | H4 | H | 构建产物和缓存文件检测 | 文件债务快速扫描 |
| L3-5 | H5 | H | 过时 JAR 文件检测 | 文件债务快速扫描 |
| L3-6 | H6 | H | 过时文档/分析文件检测 | 文件债务快速扫描 |
| L3-7 | H8 | H | 代码逻辑过时检测（代码债务） | 代码一致性统一检查 |
| L3-8 | B1 | B | 所有Kotlin源文件 vs SKILL.md | 代码一致性统一检查 |
| L3-9 | D1 | D | MockJsExtensions函数签名 vs Legado | 代码一致性统一检查 |
| L3-10 | H9 | H | 文档内容过时检测（文档内容债务） | 文档一致性统一检查 |
| L3-11 | A4 | A | 内容过薄检查 | 文档一致性统一检查 |
| L3-12 | D3 | D | RssSource字段定义 vs Legado | 文档一致性统一检查 |
| L3-13 | D4 | D | BookSource字段定义 vs Legado | 文档一致性统一检查 |
| L3-14 | H10 | H | basic-memory 记忆内容过时检测 | memory 一致性检查 |
| L3-15 | E1 | E | SKILL.md陷阱速查表 vs basic-memory | memory 一致性检查 |
| L3-16 | E2 | E | references/关键经验 vs basic-memory | memory 一致性检查 |
| L3-17 | G2 | G | design.md架构决策 vs 实际实现 | — |

> **合并模块说明**：L3 深度检查中的 17 项被组织为 4 个合并模块 + 1 个独立项。
> - **文件债务快速扫描**（L3-1~L3-6）：H1+H2+H3+H4+H5+H6，一次性扫描所有文件债务
> - **代码一致性统一检查**（L3-7~L3-9）：H8+B1+D1，代码逻辑+文档描述+源码签名统一验证
> - **文档一致性统一检查**（L3-10~L3-13）：H9+A4+D3+D4，文档内容+薄文件+字段定义统一验证
> - **memory 一致性检查**（L3-14~L3-16）：H10+E1+E2，basic-memory 笔记双向同步+过时检测
>
> 合并后逻辑检查模块数：42 - 12（合并减少）= 30 个。

---

### 维度 A：文档完整性审查

**目标**：确保所有文档内容充实、引用有效、跨文件一致、无死链、无薄文件、数量对齐。

> **🔴 L3 合并模块**：A4 参与"文档一致性统一检查"（L3-10~L3-13：H9+A4+D3+D4），与 H9（文档内容过时）和 D3/D4（字段定义）统一执行。

#### A1. 文件引用断链检查

**检查方法**：
1. 读取 SKILL.md 和 AI_README.md 中所有 `[text](path)` 格式的链接
2. 提取每个链接的相对路径
3. 用 Glob 工具验证路径对应的文件是否存在
4. 对 `references/` 下所有 `_index.md` 中的链接执行同样检查
5. 对 AGENTS.md 中引用 skill 文件的链接执行同样检查
6. **自动化脚本**：`python scripts/check_dead_links.py`（自动检测 .trae/skills/ 下所有 .md 文件的内部死链，输出 JSON）

**通过标准**：0 个死链

**常见问题**：
- `../entity-fields.md` 引用不存在的文件（应改为 `../booksource-schema.md`）
- `_index.md` 中引用的子文档路径拼写错误
- SKILL.md 中引用的脚本路径与实际路径不一致
- AGENTS.md 中引用的 references/ 路径与实际目录结构不匹配

#### A2. 跨文件一致性（SKILL.md vs AI_README.md vs AGENTS.md）

**检查方法**：
1. 提取 SKILL.md 中的关键描述（MVP 覆盖率、函数列表、脚本参数、目录结构、可信度规则）
2. 提取 AI_README.md 中的对应描述
3. 提取 AGENTS.md 中对 legado-source-creator 的描述（skill 名称、功能描述、参考文档路径、触发条件）
4. 三方交叉对比，标记不一致项

**通过标准**：SKILL.md / AI_README.md / AGENTS.md 三方描述完全一致

**关键对比项**：
| 对比项 | SKILL.md | AI_README.md | AGENTS.md |
|--------|----------|-------------|-----------|
| MVP 覆盖率数字 | ? | ? | ? |
| 函数列表 | ? | ? | — |
| 脚本参数描述 | ? | ? | — |
| 目录结构 | ? | ? | ? |
| 可信度规则 | ? | ? | — |
| 触发条件 | ? | — | ? |
| 参考文档路径 | ? | ? | ? |

**常见问题**：
- SKILL.md 写 "55-65%" 但 AI_README.md 写 "55-60%"
- AGENTS.md 引用的参考文档路径与 SKILL.md 不一致
- AI_README.md 的脚本列表缺少 SKILL.md 中新增的脚本

#### A3. 子文档数量一致性（_index.md 列出数 vs SKILL.md 声称数 vs 实际文件数）

**检查方法**：
1. 读取 `references/_INDEX.md`，统计每个子目录声明的文档数量
2. 读取 SKILL.md 中对每个子目录的声称数量（如"11子文档"、"6子文档"）
3. 用 Glob 统计每个子目录下实际的 `.md` 文件数量（排除 `_index.md` 自身）
4. 三方数量对比，标记不一致

**通过标准**：_index.md 列出数 = SKILL.md 声称数 = 实际文件数

**检查清单**：
| 子目录 | _index.md 列出数 | SKILL.md 声称数 | 实际文件数 | 一致？ |
|--------|-----------------|----------------|-----------|--------|
| troubleshooting/ | ? | 6 | ? | ? |
| js-extensions/ | ? | 11 | ? | ? |
| js-patterns/ | ? | 11 | ? | ? |
| special-scenarios/ | ? | 13 | ? | ? |
| source-analysis/ | ? | 6 | ? | ? |

#### A4. 内容过薄检查

**检查方法**：
1. 读取 `references/` 下所有 `.md` 文件（排除 `_index.md`）
2. 统计行数，标记 < 30 行的文件为"薄文件"
3. 检查薄文件是否只有标题和空壳，无实质内容（无代码示例、无修复方案、无使用说明）
4. 对 `templates/` 下的文件检查是否有占位符说明

**通过标准**：0 个薄文件（< 30 行且无实质内容）

---

### 维度 B：代码-文档一致性审查

**目标**：确保 Kotlin/Python 代码实现与 SKILL.md/AI_README.md 描述完全一致，版本锁正确。

> **🔴 L3 合并模块**：B1 参与"代码一致性统一检查"（L3-7~L3-9：H8+B1+D1），与 H8（代码逻辑过时）和 D1（Mock签名验证）统一执行。

#### B1. 所有Kotlin源文件 vs SKILL.md（命令列表、函数列表、参数签名、ES5模式）

**检查方法**：
1. 读取 `tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/` 下**所有** Kotlin 源文件
2. 逐一对比每个文件的关键实现与 SKILL.md 描述

**Kotlin 源文件清单**（必须全部检查）：

| 文件 | 检查重点 | 对比 SKILL.md 章节 |
|------|---------|-------------------|
| `RuleEngineServer.kt` | 支持的命令列表、assessConfidence/assessAnalyzeConfidence 返回值、ES6检测逻辑、webview→unverifiable | API速查表 + 可信度标注规则 |
| `MinimalMockJsExtensions.kt` | @JsFunction 函数名列表、参数签名、返回值类型 | MockJsExtensions 函数列表 |
| `AnalyzeRule.kt` | ES5模式(VERSION_1_7)、规则前缀处理、getElements返回值 | 规则语法 + AnalyzeRule描述 |
| `AnalyzeByJSoup.kt` | CSS选择器行为、自定义索引语法 | 规则语法 |
| `AnalyzeByXPath.kt` | XPath解析行为 | 规则语法 |
| `RuleAnalyzer.kt` | &&/\|\|/%% 组合逻辑解析 | 规则语法 |

**通过标准**：
- 6 个 Kotlin 文件全部检查，无遗漏
- 命令列表与 SKILL.md API 表完全匹配
- 可信度返回值全部为英文（high/medium/low/unverifiable）
- ES6 检测逻辑存在且正确
- webview 返回 "unverifiable"
- 所有 JS 上下文使用 VERSION_1_7
- 无注释与代码矛盾

**常见问题**：
- `assessConfidence` 返回中文（"高"/"中"/"低"）
- `cx.languageVersion = Context.VERSION_ES6`（应为 VERSION_1_7）
- webview 规则返回 "low"（应为 "unverifiable"）
- 只检查了 RuleEngineServer.kt，遗漏了 AnalyzeRule.kt 中的 ES5 模式

#### B2. Python客户端 vs SKILL.md API描述

**检查方法**：
1. 读取 `tools/rule_engine_client.py`
2. 提取 `RuleEngineClient` 类的所有公开方法
3. 对比 SKILL.md 中的 API 速查表
4. 验证方法签名（参数名、参数数量）与文档描述一致
5. 验证 JAR 路径回退逻辑（legado-jvm.jar 主路径 + 备用路径）与 SKILL.md 描述一致

**通过标准**：Python 客户端方法与 SKILL.md API 表完全匹配

#### B3. 可信度评估逻辑一致性（Kotlin assessConfidence vs Python assess_confidence vs SKILL.md）

**检查方法**：
1. 读取 `RuleEngineServer.kt` 中的 `assessConfidence()`
2. 读取 `tools/jvm_helpers.py` 中的 `assess_confidence()`
3. 逐条件对比两个函数的逻辑分支：
   - webview/webjs → unverifiable
   - ES6 语法（let/const/=>/模板字符串）→ low
   - ajax + Cookie/Header → low
   - ajax 无 Cookie → medium
   - 纯逻辑 → high
4. 对比 SKILL.md 可信度标注规则表
5. 验证三方逻辑完全一致

**通过标准**：Kotlin / Python / SKILL.md 三方可信度评估逻辑完全一致

#### B4. ES5/ES6模式一致性（代码中的Rhino语言版本 vs SKILL.md陷阱#1）

**检查方法**：
1. 在**所有** Kotlin 源码中搜索 `Context.VERSION_ES6` 和 `Context.VERSION_1_8` 和 `Context.VERSION_1_7`
2. 确认所有 JS 执行上下文均使用 `Context.VERSION_1_7`（包括 RuleEngineServer.kt 和 AnalyzeRule.kt）
3. 验证 SKILL.md 中 ES5 only 陷阱（陷阱#1）的描述与代码行为一致
4. 验证 AI_README.md 中对 ES5 限制的描述与代码一致
5. 检查是否有注释与代码矛盾（如注释写"ES5兼容"但代码用 VERSION_ES6）

**通过标准**：
- 0 处使用 VERSION_ES6 或 VERSION_1_8
- 所有 JS 上下文（RuleEngineServer + AnalyzeRule）均为 VERSION_1_7
- SKILL.md/AI_README.md 的 ES5 描述与代码一致
- 无注释与代码矛盾

#### B5. build.gradle.kts 版本锁一致性

**检查方法**：
1. 读取 `tools/legado-jvm/build.gradle.kts`
2. 提取依赖版本号
3. 对比 AGENTS.md 中的版本锁约束：

| 依赖 | AGENTS.md 要求 | build.gradle.kts 实际 | 一致？ |
|------|---------------|---------------------|--------|
| jsoup | 1.16.2（锁定，jsoup#2017破坏性变更） | ? | ? |
| rhino | 1.8.1（锁定，Android 6以下缺Arrays.setAll） | ? | ? |
| hutool | 5.8.22（锁定，书源加解密依赖） | ? | ? |

4. 验证 fatJar 任务配置正确（非 build 任务）
5. 验证 Kotlin/JVM 版本兼容
6. **自动化脚本**：`python scripts/check_version_lock.py`（自动对比 build.gradle.kts 与 AGENTS.md 版本锁定，输出 JSON）

**通过标准**：build.gradle.kts 中三个依赖版本与 AGENTS.md 版本锁 100% 一致，fatJar 配置正确

**常见问题**：
- jsoup 升级到 1.17+ 导致 CSS 选择器行为变化
- rhino 升级导致 ES6 语法意外支持
- hutool 升级导致加解密结果不一致
- 使用 `build` 而非 `fatJar` 生成不含依赖的 JAR

---

### 维度 C：脚本与JAR验证审查

**目标**：确保所有 Python 脚本语法正确、参数一致、导入路径有效，JAR 文件可用。

#### C1. Python脚本语法验证

**检查方法**：
1. 对 `scripts/` 和 `tools/` 下所有 `.py` 文件执行 `python -m py_compile {file}`
2. 记录所有语法错误和导入错误

**通过标准**：0 个语法错误

#### C2. 脚本参数与SKILL.md描述是否一致

**检查方法**：
1. 读取每个脚本的 `argparse` 定义
2. 对比 SKILL.md 中描述的参数（如 `--jvm`、`--jar-path`、`--algo`、`--url` 等）
3. 验证 SKILL.md 中声明的参数在实际脚本中存在
4. 验证脚本的默认值与 SKILL.md 描述一致

**通过标准**：SKILL.md 声明的参数 100% 在脚本中存在，默认值一致

#### C3. 脚本导入路径是否正确

**检查方法**：
1. 读取每个脚本的 `import` 语句
2. 验证相对导入（如 `from tools.jvm_helpers import ...`）的路径在 skill 目录结构中有效
3. 验证第三方依赖是否在 requirements.txt 或注释中声明
4. 验证 `scripts/` 下的脚本对 `tools/` 的导入路径是否正确（需考虑 Python 路径设置）
5. 验证脚本间协作：`verify-*.py` 是否正确使用 `jvm_helpers.py` 的 `add_jvm_args()` 和 `init_jvm_client()`

**通过标准**：所有导入路径有效，第三方依赖有声明，脚本间接口调用正确

#### C4. JAR文件验证（存在性、可启动性、源码同步性）

**检查方法**：
1. 验证 JAR 文件存在：
   - `tools/legado-jvm/build/libs/legado-jvm.jar`
2. 验证 JAR 文件大小 > 0（非空文件）
3. 验证 JAR 可启动（JDK 17+ 环境下）：
   ```bash
   java -jar tools/legado-jvm/build/libs/legado-jvm.jar --test
   ```
   或通过 Python 客户端 ping 测试：
   ```python
   from scripts.legado_client.client.rule_engine_client import RuleEngineClient
   with RuleEngineClient() as client:
       assert client.ping() == True
   ```
4. 验证 JAR 与源码同步（非过期）：
   - 对比 JAR 构建时间 vs Kotlin 源码修改时间
   - 如果源码比 JAR 更新，标记为"需重建"

**通过标准**：
- legado-jvm.jar 文件存在且非空
- JAR 可启动并响应 ping
- JAR 构建时间 >= Kotlin 源码最新修改时间

**常见问题**：
- 修改了 Kotlin 源码但忘记重建 JAR（JAR 过期）
- JAR 文件为 0 字节（构建失败但未察觉）
- JDK 版本不兼容导致 JAR 无法启动

---

### 维度 D：Legado 源码匹配审查

**目标**：确保 skill 中的 MockJsExtensions、AnalyzeRule、字段定义等与 Legado 实际源码一致。

> **🔴 L3 合并模块**：
> - D1 参与"代码一致性统一检查"（L3-7~L3-9：H8+B1+D1）
> - D3+D4 参与"文档一致性统一检查"（L3-10~L3-13：H9+A4+D3+D4）

#### D1. MockJsExtensions函数签名 vs Legado JsExtensions.kt

**检查方法**：
1. 读取 Legado 源码 `app/src/main/java/io/legado/app/help/JsExtensions.kt`
2. 提取所有公开函数的签名（函数名 + 参数类型 + 返回类型）
3. 对比 `MinimalMockJsExtensions.kt` 中的实现
4. 标记：签名不匹配 / 缺失函数 / 返回值类型不一致
5. 对比 SKILL.md 中声明的 MockJsExtensions 函数列表

**通过标准**：
- Mock 中实现的函数签名与 Legado 源码 100% 一致
- 缺失函数在 SKILL.md 中有明确标注（"未实现"）

**关键检查项**：
- `ajax(urlOrStrResponse)` 的参数类型（Legado 支持 String 和 StrResponse）
- `getElements(rule)` 的返回类型（Legado 返回 List<*>，非 JSON 字符串）
- `decryptStr()` vs `decrypt()` 的区分（文本 vs 二进制）
- `webView()` 的参数列表（4 个参数 vs 3 个参数版本）
- `createSymmetricCrypto()` 的参数和返回值

#### D2. 所有JVM仿真器组件行为 vs Legado源码

**检查方法**：
1. 读取 Legado 源码中的对应文件
2. 逐一对比 JVM 仿真器的每个组件

**JVM 仿真器组件清单**（必须全部检查）：

| JVM 仿真器组件 | Legado 源码 | 检查重点 |
|-----------|------------|---------|
| `AnalyzeRule.kt` | `app/.../analyzeRule/AnalyzeRule.kt` | 自定义索引语法、规则前缀处理、getElements返回值 |
| `RuleAnalyzer.kt` | `app/.../analyzeRule/RuleAnalyzer.kt` | &&/\|\|/%% 组合逻辑、规则拆分 |
| `AnalyzeByJSoup.kt` | `app/.../analyzeRule/AnalyzeByJSoup.kt` | CSS选择器行为、索引语法 |
| `AnalyzeByXPath.kt` | `app/.../analyzeRule/AnalyzeByXPath.kt` | XPath解析行为 |

3. 对比 SKILL.md 中对规则语法的描述

**通过标准**：4 个 JVM 仿真器组件的核心行为与 Legado 源码一致

**常见问题**：
- RuleAnalyzer 的 && 逻辑与 Legado 不一致（顺序、空值处理）
- AnalyzeByJSoup 的索引语法（`tag.div.0` vs `tag.div!0`）计算方式不同
- 只检查了 AnalyzeRule.kt，遗漏了 RuleAnalyzer.kt

#### D3. RssSource字段定义 vs Legado RssSource.kt

**检查方法**：
1. 读取 Legado 源码 `app/src/main/java/io/legado/app/data/entities/RssSource.kt`
2. 对比 `references/source-analysis/rss-source-entity.md`
3. 对比 `references/booksource-schema.md` 中的 RssSource 部分
4. 验证字段名、字段类型、默认值是否一致
5. 特别注意扁平字段（ruleArticles/ruleTitle/ruleLink 等）vs BookSource 的嵌套规则组

**通过标准**：文档中的 RssSource 字段定义与 Legado 源码 100% 一致

#### D4. BookSource字段定义 vs Legado BookSource.kt

**检查方法**：
1. 读取 Legado 源码 `app/src/main/java/io/legado/app/data/entities/BookSource.kt`
2. 对比 `references/booksource-schema.md`
3. 验证字段名、字段类型、默认值是否一致
4. 特别注意嵌套规则组（ruleSearch/ruleBookInfo/ruleToc/ruleContent）的字段
5. 验证 SKILL.md 中对 BookSource 结构的描述与源码一致

**通过标准**：文档中的 BookSource 字段定义与 Legado 源码 100% 一致

**扩展检查**（可选但推荐）：
- Rhino 限制描述 vs Legado RhinoClassShutter.kt
- Cookie 同步机制描述 vs Legado CookieStore.kt + BackstageWebView.kt

---

### 维度 E：basic-memory 双向同步审查

**目标**：确保 basic-memory 中的记忆与 skill 文档双向一致，无重复、无遗漏、无冲突。

#### E1. SKILL.md陷阱速查表 vs basic-memory trap笔记

**检查方法**：
1. 读取 SKILL.md 陷阱速查表，提取所有陷阱编号和描述
2. 对每个陷阱搜索 basic-memory：
   ```
   mcp_basic-memory_search_notes(query="陷阱: {陷阱关键词}", search_type="hybrid", project="legado", tags=["trap"])
   ```
3. 验证每条陷阱在 basic-memory 中有对应的 trap 笔记
4. 验证 basic-memory 中的 trap 笔记有 `source_doc` 元数据指向 references/ 下的文档
5. 反向检查：basic-memory 中的 trap 笔记是否在 SKILL.md 陷阱速查表中有对应条目

**通过标准**：SKILL.md 每条陷阱 ↔ basic-memory trap 笔记，双向无遗漏

#### E2. references/关键经验 vs basic-memory experience/pattern笔记

**检查方法**：
1. 读取 `references/` 下各子目录的 `_index.md`，提取关键经验条目
2. 对每个关键经验搜索 basic-memory：
   ```
   mcp_basic-memory_search_notes(query="{经验关键词}", search_type="hybrid", project="legado", tags=["experience","pattern"])
   ```
3. 验证 references/ 中的关键经验在 basic-memory 中有对应的 experience/pattern 笔记
4. 验证 basic-memory 中的 experience/pattern 笔记有 `source_doc` 元数据
5. 反向检查：basic-memory 中有但 references/ 中没有的笔记（可能是孤立笔记或需补写到 references/）

**通过标准**：references/ 关键经验 ↔ basic-memory experience/pattern 笔记，双向无遗漏

#### E3. 重复笔记检测

**检查方法**：
1. 执行 `mcp_basic-memory_search_notes(query="经验", search_type="hybrid", project="legado", page_size=50)`
2. 执行 `mcp_basic-memory_search_notes(query="陷阱", search_type="hybrid", project="legado", page_size=50)`
3. 执行 `mcp_basic-memory_search_notes(query="模式", search_type="hybrid", project="legado", page_size=50)`
4. 对比相似标题的笔记，标记内容重复的条目
5. 验证重复笔记是否需要合并

**通过标准**：0 个内容重复的笔记

#### E4. L3目录结构 vs SKILL.md描述

**检查方法**：
1. 执行 `mcp_basic-memory_list_directory(dir_name="/", project="legado", depth=3)`
2. 对比 SKILL.md 中定义的 L3 目录结构：
   ```
   legado/
   ├── traps/           # 陷阱索引
   ├── patterns/        # 成功模式
   ├── experiences/     # 网站特征→经验
   ├── verifications/   # 源码验证结论
   ├── execution-logs/  # Phase 执行证据
   ├── test-reports/    # 测试报告
   └── cases/           # 实战案例
   ```
3. 标记：多余的目录 / 缺失的目录 / 目录层级不一致
4. 检查笔记的 note_type 和 directory 是否与 SKILL.md 的笔记类型体系一致

**通过标准**：basic-memory 目录结构与 SKILL.md 定义一致，笔记类型合规

---

### 维度 F：新用户视角审查

**目标**：从全新使用者角度审查 skill，发现信息缺失、决策困惑、模糊描述。

#### F1. SKILL.md可读性（新agent能否理解每个Phase的输入/输出/决策点）

**检查方法**：
1. 模拟全新 agent，仅读取 SKILL.md，尝试理解完整工作流
2. 验证：能否仅凭 SKILL.md 完成一次书源创建？
3. 验证：每个 Phase 的输入/输出/触发条件是否清晰？
4. 验证：关键决策点是否有明确的判断标准？
5. 验证：Phase 切换条件是否清晰？

**通过标准**：仅凭 SKILL.md 能理解完整工作流，无歧义决策点

**常见问题**：
- "JVM 仿真器有哪些能力？" 已在 SKILL.md API 速查表中说明
- "JVM 不可用时如何降级？" 描述不够具体
- "可信度评估是自动还是手动？" 未说明
- "Phase 3 测试失败的标准是什么？" 未定义

#### F2. 缺失信息（新agent会问什么问题但文档没回答）

**检查方法**：
1. 检查是否有概念首次出现但未定义的情况（如"自定义索引语法"首次出现时无解释）
2. 检查错误信息是否有对应的排查路径
3. 检查 SKILL.md 中"详见 xxx"指向的文档是否确实回答了问题
4. 列出新 agent 最可能问的 10 个问题，检查文档是否有答案

**通过标准**：无信息缺失，所有概念首次出现时有定义或有效链接

**新 agent 常见疑问**：
- "什么是 AnalyzeRule？"
- "JVM 仿真器（legado-jvm.jar）有哪些能力？怎么启动？"
- "怎么启动 JVM 仿真器？"
- "verify-source.py 和 debug-source.py 有什么区别？"
- "可信度 high/medium/low 分别意味着什么？"
- "如何处理 CF 反爬？"
- "订阅源的 ruleContent 为什么是扁平的？"

#### F3. 模糊描述（"详见xxx"但xxx没有具体说明）

**检查方法**：
1. 搜索 SKILL.md 中所有"详见"、"参见"、"参考"等指向性描述
2. 对每个指向，读取目标文档，验证目标文档是否有足够的具体说明
3. 标记"详见xxx但xxx没有具体说明"的情况
4. 检查是否有循环引用（A 详见 B，B 详见 A）

**通过标准**：0 个模糊描述，所有"详见"指向的文档有足够具体说明

**常见问题**：
- SKILL.md 写"详见 references/troubleshooting/"但 troubleshooting/_index.md 只有标题列表无详细说明
- "详见 js-patterns/common-traps.md"但该文件只有 7 行空壳
- "使用 templates/auto-video-player.html"但未说明如何替换占位符

---

### 维度 G：设计文档状态审查

**目标**：确保 `docs/specs/` 下的设计文档与实际实现状态一致。

#### G1. spec.md需求项 vs 实际完成状态

**检查方法**：
1. 读取 `docs/specs/skill-architecture-optimization/spec.md`
2. 提取所有需求项（Requirements / Scenarios）
3. 对比实际 skill 目录结构和功能
4. 标记：spec 中描述但未实现的功能 / 已实现但 spec 未描述的功能

**通过标准**：spec.md 与实际实现 100% 一致

#### G2. design.md架构决策 vs 实际实现

**检查方法**：
1. 读取 `docs/specs/skill-architecture-optimization/design.md`
2. 检查每个架构决策（AD）的状态标记
3. 验证 AD 状态与实际代码一致（如"JVM仿真器可选未实施"但实际已实施）
4. 验证 design.md 中的文件变更清单与实际文件一致

**通过标准**：所有 AD 状态标记与实际代码一致

#### G3. tasks.md任务状态 vs 实际完成情况

**检查方法**：
1. 读取 `docs/specs/skill-architecture-optimization/tasks.md`
2. 检查每个任务的完成标记（`✅ YYYY-MM-DD`）
3. 验证已标记完成的任务确实在代码中实现
4. 验证未标记完成的任务是否确实未实现
5. 标记：已完成但未标记 / 未完成但已标记

**通过标准**：tasks.md 完成状态与实际代码一致

---

### 维度 H：全面债务清理审查

**目标**：识别并清理 skill 中的文件债务、代码债务、文档内容债务、记忆内容债务，防止 skill 膨胀和腐化。

> **核心理念**：不是标记"已废弃"，而是直接删除或修复！即使没有标记废弃，也要主动核实是否适配最新版本。
>
> **三类债务**：
> - **文件债务**（H1-H7）：废弃文件、重复文件、缓存文件 → 直接删除
> - **代码/文档/记忆内容债务**（H8-H10）：内容没标记废弃但已过时 → 修复或更新
>
> **🔴 L3 合并模块**：维度 H 中的检查项参与 4 个 L3 合并模块：
> - **文件债务快速扫描**（L3-1~L3-6）：H1+H2+H3+H4+H5+H6 → 一次性扫描所有文件债务，详见各检查项
> - **代码一致性统一检查**（L3-7~L3-9）：H8+B1+D1 → 代码逻辑过时+Kotlin源码对比+Mock签名验证统一执行
> - **文档一致性统一检查**（L3-10~L3-13）：H9+A4+D3+D4 → 文档内容过时+薄文件+RssSource/BookSource字段统一验证
> - **memory 一致性检查**（L3-14~L3-16）：H10+E1+E2 → basic-memory笔记过时+双向同步统一验证

#### H1. 旧版源码文件检测（根目录 vs legado-jvm/src/ 下的重复源码）

**检查方法**：
1. 读取 `tools/` 根目录下的 `.kt` 文件
2. 读取 `tools/legado-jvm/src/main/kotlin/` 下对应的 `.kt` 文件
3. 对比内容是否重复（或根目录版本是否为旧版）
4. 如果 `legado-jvm/src/` 下有最新版本，则 `tools/` 根目录下的同名文件为废弃文件

**已知废弃文件**（基于历史审查）：
| 废弃文件 | 原因 | 最新版本位置 |
|---------|------|------------|
| `tools/MinimalMockJsExtensions.kt` | AI_README.md 标注"旧版源码" | `tools/legado-jvm/src/.../MinimalMockJsExtensions.kt` |
| `tools/RuleEngineServer.kt` | AI_README.md 标注"旧版源码" | `tools/legado-jvm/src/.../RuleEngineServer.kt` |

**通过标准**：0 个根目录下的旧版 Kotlin 源码文件

**修复动作**：直接删除废弃文件，并更新 AI_README.md / SKILL.md 中的引用

#### H2. 旧版/临时测试脚本检测

**检查方法**：
1. 读取 `tools/` 和 `scripts/` 下所有 `.py` 文件
2. 识别临时测试脚本的特征：
   - 文件名含 `test_` 前缀但不在正式测试目录中
   - 文件名含 `_old` / `_backup` / `_tmp` / `_v1` 等后缀
   - 文件内容含 `# 临时` / `# TODO: 删除` / `# 测试用` 等标记
   - 文件功能已被其他脚本完全覆盖
3. 对比 SKILL.md 中声明的脚本列表，识别未在文档中声明的脚本
4. **自动化脚本**：`python scripts/check_file_debt.py`（自动扫描临时文件，输出 JSON）

**已知可疑文件**（基于历史审查）：
| 可疑文件 | 判断依据 | 处置建议 |
|---------|---------|---------|
| `tools/test_mvp3.py` | 临时测试脚本，仅测试 MVP3 decrypt/encrypt | 删除（功能已被 verify-source.py 覆盖） |

**通过标准**：0 个临时测试脚本，所有脚本在 SKILL.md 中有声明

#### H3. 功能已被替代的旧文件检测

**检查方法**：
1. 识别功能重叠的文件对（旧版 vs 新版）
2. 验证旧版是否仍被任何脚本或文档引用
3. 如果旧版无引用且新版功能完全覆盖旧版，则标记为废弃
4. **自动化脚本**：`python scripts/check_file_debt.py`（自动扫描临时文件，输出 JSON）

**已知功能重叠文件**（基于历史审查）：
| 旧文件 | 新文件（替代者） | 旧文件是否仍被引用 |
|--------|---------------|-----------------|
| `tools/fetch_html.py` | `tools/html_fetcher.py` | html_fetcher.py 内部调用 fetch_html.py（Playwright 回退） |

**特殊处理**：如果旧文件仍被新文件引用，不能直接删除，需先重构引用关系

**通过标准**：0 个无引用的废弃文件；有引用的旧文件有明确的迁移计划

#### H4. 构建产物和缓存文件检测

**检查方法**：
1. 扫描 `__pycache__/` 目录
2. 扫描 `.pyc` 文件
3. 扫描构建临时文件（如 `nul`、`.class`、`.gradle/`）
4. 扫描空文件（0 字节）
5. **自动化脚本**：`python scripts/check_file_debt.py`（自动扫描 __pycache__/nul/*.tmp/*.bak/*.swp/*.pyc，输出 JSON）

**已知需清理文件**（基于历史审查）：
| 文件 | 类型 | 处置 |
|------|------|------|
| `tools/__pycache__/` | Python 缓存 | 删除整个目录 |
| `scripts/__pycache__/` | Python 缓存 | 删除整个目录 |
| `tools/legado-jvm/nul` | Windows 空文件（误创建） | 删除 |

**通过标准**：0 个 `__pycache__/` 目录，0 个空文件，0 个构建临时文件

#### H5. 过时 JAR 文件检测

**检查方法**：
1. 检查 `tools/` 下是否有不再需要的独立 JAR 文件
2. 验证每个 JAR 文件是否仍被脚本引用
3. 验证 JAR 版本是否与当前 MVP 版本对应
4. **自动化脚本**：`python scripts/check_file_debt.py`（自动扫描临时文件，输出 JSON）

**已知可疑文件**（基于历史审查）：
| 文件 | 用途 | 判断 |
|------|------|------|
| `tools/rhino-1.7.15.jar` | SKILL.md 标注"旧版，兼容性测试用" | 评估是否仍需保留 |
| `tools/rhino-1.8.1.jar` | SKILL.md 标注"Legado使用的版本，快速测试JS片段" | 评估是否仍需保留 |

**评估标准**：
- 如果 `legado-jvm.jar` 已内置 Rhino，则独立 Rhino JAR 可能不再需要
- 如果 SKILL.md 中有使用独立 Rhino JAR 的说明，则保留

**通过标准**：每个 JAR 文件都有明确的保留理由，无冗余 JAR

#### H6. 过时文档/分析文件检测

**检查方法**：
1. 读取 `tools/` 下的 `.md` 文件（非代码文件）
2. 判断是否为临时分析文档（如差异分析、调试记录）
3. 验证其内容是否已被正式 references/ 文档覆盖
4. 如果已被覆盖，标记为废弃
5. **自动化脚本**：`python scripts/check_file_debt.py`（自动扫描临时文件，输出 JSON）

**已知可疑文件**（基于历史审查）：
| 文件 | 内容 | 判断 |
|------|------|------|
| `tools/ajax-diff-analysis.md` | MockJsExtensions ajax() 差异分析 | 如果内容已合并到 references/js-extensions/ 或 source-analysis/，则可删除 |

**通过标准**：0 个临时分析文档残留在 tools/ 目录中

#### H7. SKILL.md/AI_README.md 中对废弃文件的引用清理

**检查方法**：
1. 删除废弃文件后，搜索 SKILL.md 和 AI_README.md 中对这些文件的引用
2. 清理引用（删除行或更新为最新版本路径）
3. 更新目录结构描述

**通过标准**：SKILL.md / AI_README.md 中无对已删除文件的引用

#### H8. 代码逻辑过时检测（代码债务）

**目标**：代码虽然没有标记废弃，但逻辑可能已不适配最新 Legado 版本或最新 SKILL.md 规则。

**检查方法**：
1. **硬编码值过时检测**：
   - 搜索 Python/Kotlin 代码中的硬编码版本号、端口号、JAR 文件名
   - 验证这些值是否与最新版本一致
   - 例如：`legado-rule-engine-mvp*.jar` 是否仍被代码引用但实际已不需要（应统一为 legado-jvm.jar）

2. **代码逻辑与最新 Legado 行为不一致**：
   - 读取 `MinimalMockJsExtensions.kt` 中每个函数的实现
   - 对比 Legado 最新源码 `JsExtensions.kt` 中对应函数的最新行为
   - 标记：参数变更 / 返回值变更 / 行为变更 / 新增参数未实现
   - 即使函数签名一致，内部行为可能已不同

3. **代码逻辑与最新 SKILL.md 规则不一致**：
   - 读取 `jvm_helpers.py` 中 `assess_confidence()` 的逻辑分支
   - 对比 SKILL.md 中最新的可信度标注规则
   - 标记：SKILL.md 新增了规则但代码未实现 / 代码有逻辑但 SKILL.md 未描述

4. **代码中的 URL/路径有效性**：
   - 搜索 `html_fetcher.py` 中的 Wayback Machine URL、Google Cache URL
   - 验证这些 URL 是否仍然可达
   - 搜索代码中的文件路径引用，验证路径是否仍然有效

5. **代码注释与实际行为矛盾**：
   - 搜索注释中描述的行为
   - 验证代码实际行为是否与注释一致
   - 例如：注释写"ES5兼容"但代码用 VERSION_ES6

**通过标准**：
- 0 个硬编码值与最新版本不一致
- Mock 函数行为与 Legado 最新源码一致
- 代码逻辑与 SKILL.md 最新规则一致
- 代码中引用的 URL/路径仍然有效
- 0 个注释与代码矛盾

**常见问题**：
- `assessConfidence` 新增了 ES6 检测但 `assessAnalyzeConfidence` 没有
- SKILL.md 新增了可信度规则但 Python 端未同步
- `html_fetcher.py` 中 Wayback Machine URL 格式已变更
- `rule_engine_client.py` 中 JAR 回退链缺少最新版本

#### H9. 文档内容过时检测（文档内容债务）

**目标**：文档虽然没有标记废弃，但内容可能已与最新 Legado 源码或最新 SKILL.md 不一致。

**检查方法**：
1. **references/ 文档内容与最新 Legado 源码不一致**：
   - 读取 `references/js-extensions/` 下的函数文档
   - 对比 Legado 最新源码中对应函数的参数和行为
   - 标记：文档描述的参数与源码不一致 / 文档缺少新增参数 / 文档描述的行为与源码不一致
   - 特别注意 `@Deprecated` 标注的函数：Legado 源码中已标注废弃但文档仍推荐使用

2. **文档中的代码示例过时**：
   - 读取 `references/js-patterns/` 和 `references/special-scenarios/` 下的代码示例
   - 验证示例中的 JS 代码是否符合 ES5 only 限制（无 let/const/=>/模板字符串）
   - 验证示例中调用的 JsExtensions 函数是否仍然存在
   - 验证示例中的 CSS 选择器语法是否与 jsoup 1.16.2 兼容

3. **SKILL.md 陷阱描述与最新 Legado 行为不一致**：
   - 读取 SKILL.md 陷阱速查表
   - 对比 Legado 最新源码验证每条陷阱是否仍然成立
   - 标记：陷阱已在新版 Legado 中修复 / 陷阱描述不准确 / 缺少新发现的陷阱

4. **字段定义文档与最新 Legado 实体不一致**：
   - 读取 `references/booksource-schema.md` 和 `references/source-analysis/rss-source-entity.md`
   - 对比 Legado 最新源码中的 `BookSource.kt` 和 `RssSource.kt`
   - 标记：新增字段未记录 / 字段类型变更 / 默认值变更

**通过标准**：
- references/ 文档内容与 Legado 最新源码一致
- 代码示例符合 ES5 only 限制
- 陷阱描述与 Legado 最新行为一致
- 字段定义与 Legado 最新实体一致

**常见问题**：
- 文档中的 `ajax()` 示例使用了 ES6 语法
- 文档中推荐的 `decrypt()` 方法已被 `decryptStr()` 替代
- 新版 Legado 新增了字段但文档未更新
- 陷阱描述基于旧版 Rhino 行为，新版已不同

#### H10. basic-memory 记忆内容过时检测（记忆内容债务）

**目标**：basic-memory 中的笔记虽然存在，但内容可能已与最新 references/ 文档或最新 Legado 源码不一致。

**检查方法**：
1. **笔记内容与最新 references/ 文档不一致**：
   - 读取 basic-memory 中的 trap/experience/pattern 笔记
   - 读取对应的 references/ 文档
   - 对比内容：笔记摘要是否与文档最新内容一致
   - 标记：笔记描述的行为与文档不一致 / 笔记缺少文档中的新增内容

2. **笔记中的结论与最新源码分析不一致**：
   - 读取 basic-memory 中的 verification 笔记
   - 对比 Legado 最新源码
   - 标记：验证结论已过时（如"Rhino 不支持 let"但新版可能支持）

3. **笔记中的代码示例过时**：
   - 读取 basic-memory 笔记中的代码示例
   - 验证示例是否符合 ES5 only 限制
   - 验证示例中调用的函数是否仍然存在

4. **source_doc 指向的文档已更新但笔记未更新**：
   - 读取笔记的 `source_doc` 元数据
   - 读取 source_doc 指向的文档
   - 对比文档修改时间 vs 笔记修改时间
   - 如果文档比笔记更新，标记为"需同步"

5. **孤立笔记检测**（有笔记但无对应文档）：
   - 搜索 basic-memory 中没有 `source_doc` 的笔记
   - 搜索 basic-memory 中 `source_doc` 指向不存在的文档的笔记
   - 标记：需补写 references/ 文档 / 需删除孤立笔记

**通过标准**：
- 笔记内容与最新 references/ 文档一致
- 验证结论与最新源码分析一致
- 笔记中的代码示例有效
- source_doc 指向的文档比笔记更新时已标记"需同步"
- 0 个孤立笔记

---

### 补充检查模块 S

> 以下检查项不属于主维度，但对 skill 质量有重要影响。

#### S1. 模板文件验证

**检查方法**：
1. 读取 `templates/` 下所有文件
2. 验证 HTML 模板是有效 HTML（有 `<html>`/`<head>`/`<body>` 结构）
3. 验证模板有版本标记（如 `V1.20260606.1`）
4. 验证模板中的占位符（`${videoUrl}` 等）在 SKILL.md 中有使用说明
5. 验证 SKILL.md 引用的模板名称与实际文件名一致

**通过标准**：模板文件有效、有版本标记、占位符有说明

#### S2. CMS样本验证

**检查方法**：
1. 读取 `references/cms-samples/` 目录结构
2. 验证每个 CMS 类型目录下有 `selectors.json` 和 HTML 样本文件
3. 验证 `selectors.json` 结构正确（有 primary 和 fallbacks 字段）
4. 验证 SKILL.md 中对 CMS 样本的引用与实际目录一致

**通过标准**：CMS 样本结构正确，SKILL.md 引用一致

#### S3. 跨skill一致性（legado-workflow-auditor 对 legado-source-creator 的描述）

**检查方法**：
1. 读取 `legado-workflow-auditor/SKILL.md`
2. 检查其中对 legado-source-creator 的描述是否与实际一致
3. 检查审计流程中的检查项是否与 legado-source-creator 的 Phase 完成标志匹配
4. 检查降级路径是否与 legado-source-creator 的降级逻辑一致

**通过标准**：legado-workflow-auditor 对 legado-source-creator 的描述准确

#### S4. html_fetcher.py 回退链验证

**检查方法**：
1. 读取 `tools/html_fetcher.py`
2. 验证回退链顺序与 SKILL.md 描述一致（curl → Wayback → CMS样本 → Google Cache → Playwright）
3. 验证 FetchResult 输出格式与 SKILL.md 描述一致
4. 验证 `--cms-type` 参数与 `references/cms-samples/` 中的目录名匹配

**通过标准**：回退链顺序、输出格式、参数与 SKILL.md 一致

#### S5. 输出目录验证

**检查方法**：
1. 验证 `output/book/` 和 `output/rss/` 目录存在
2. 验证已有输出文件是有效 JSON 数组格式（`[...]`）
3. 验证 SKILL.md 中对输出格式的描述与实际一致

**通过标准**：输出目录存在，已有文件格式正确

---

## 审查执行流程（L1/L2/L3 三层分层）

> **分层执行策略**：按 L1→L2→L3 顺序执行，L1 快速发现问题后可直接进入修复，无需等待全量审查。

### Phase 0：L1 快速检查（10项，5分钟内完成）

```
L1 快速检查（可单代理执行）：
  → A1: 死链检测（Glob 验证所有 .md 文件中的链接）
  → A3: 子文档数量一致性（_index.md vs SKILL.md vs 实际文件数）
  → C1: Python 脚本语法验证（py_compile）
  → C4: JAR 文件验证（存在性+大小+ping 测试）
  → H7: 废弃文件引用清理（搜索已删除文件的引用）
  → S1: 模板文件验证
  → S2: CMS 样本验证
  → S5: 输出目录验证
  → E3: 重复笔记检测（basic-memory 搜索）
  → E4: L3 目录结构 vs SKILL.md 描述
```

**L1 通过标准**：0 个 P0 问题，可进入 L2；有 P0 问题则先修复再继续。

### Phase 1：L2 核心检查 + 并行扫描（3 个子代理）

```
子代理A：L2 文档+用户视角（A2 + F1-F3 + S3）
  → A2: 跨文件一致性（SKILL.md vs AI_README.md vs AGENTS.md）
  → F1-F3: 新用户视角审查
  → S3: 跨 skill 一致性

子代理B：L2 代码+脚本（B2-B5 + C2-C3 + S4）
  → B2-B5: Python 客户端/可信度/ES5模式/版本锁一致性
  → C2-C3: 脚本参数/导入路径验证
  → S4: html_fetcher.py 回退链验证

子代理C：L2 源码+设计文档（D2 + G1 + G3）
  → D2: JVM仿真器组件行为 vs Legado 源码
  → G1: spec.md 需求项 vs 实际完成状态
  → G3: tasks.md 任务状态 vs 实际完成情况
```

**L2 通过标准**：0 个 P0/P1 问题，可进入 L3；有 P1 问题则记录但继续 L3。

### Phase 2：L3 深度检查（17项，含 4 个合并模块）

```
L3-1~L3-6 文件债务快速扫描（合并模块）：
  → H1+H2+H3+H4+H5+H6: 一次性扫描所有文件债务
  → 旧版源码/临时脚本/功能重叠/缓存文件/过时JAR/过时文档

L3-7~L3-9 代码一致性统一检查（合并模块）：
  → H8+B1+D1: 代码逻辑过时+Kotlin源码对比+Mock签名验证
  → 统一读取 Kotlin 源码，一次性对比 SKILL.md + Legado 源码

L3-10~L3-13 文档一致性统一检查（合并模块）：
  → H9+A4+D3+D4: 文档内容过时+薄文件+RssSource/BookSource字段定义
  → 统一读取 references/ 文档，一次性对比 Legado 源码

L3-14~L3-16 memory 一致性检查（合并模块）：
  → H10+E1+E2: basic-memory笔记过时+双向同步
  → 统一查询 basic-memory，一次性对比 references/ 文档

L3-17 独立检查：
  → G2: design.md 架构决策 vs 实际实现
```

### Phase 3：交叉验证 + 问题分级

1. 汇总 3 个子代理的发现
2. 交叉验证：子代理A 发现的文档问题是否与子代理B 的代码问题相关？
3. 识别根因：一个代码 bug 可能导致多个文档问题
4. 特别关注：A2 跨文件一致性问题是否与 G1/G2/G3 设计文档问题同源
5. 特别关注：B5 版本锁问题是否与 D1/D2 源码匹配问题同源

### Phase 3：问题分级

| 级别 | 定义 | 示例 |
|------|------|------|
| **P0 极严重** | 导致生成错误书源/订阅源 | ES6 模式假阴性、可信度逻辑错误、字段定义错误、版本锁错误 |
| **P1 高严重度** | 导致用户困惑或功能不可用 | 函数签名不匹配、死链、返回值语言不统一、跨文件不一致、JAR过期、废弃文件导致引用混乱 |
| **P2 中严重度** | 影响体验但不阻塞核心流程 | 薄文件、函数列表不完整、数量不一致、设计文档状态过时、临时脚本残留 |
| **P3 低严重度** | 优化建议 | 文档措辞改进、示例补充、模板占位符说明、缓存文件清理 |

### Phase 4：精准修复 + 回归验证

1. 按 P0→P1→P2→P3 顺序修复
2. 每个修复必须验证：
   - 修复后代码是否语法正确？（Python: `py_compile`，Kotlin: `gradlew.bat fatJar`）
   - 修复后文档引用是否有效？（Glob 验证）
   - 修复后是否引入新问题？（交叉检查）
   - 修复后 A2 跨文件一致性是否保持？（SKILL.md / AI_README.md / AGENTS.md 同步更新）
3. 修复后更新相关文档

**回归验证步骤**（修复完成后必须执行）：

| 修复类型 | 回归验证 |
|---------|---------|
| Kotlin 源码修改 | `gradlew.bat fatJar` → 复制 JAR → 启动 JAR → ping 测试 → ES5/ES6 验证 |
| Python 脚本修改 | `python -m py_compile {file}` → 运行 `--help` 验证参数 |
| SKILL.md 修改 | A2 跨文件一致性复查（AI_README.md / AGENTS.md 同步） |
| AI_README.md 修改 | A2 跨文件一致性复查（SKILL.md 同步） |
| references/ 修改 | A1 死链复查 + A3 数量一致性复查 |
| basic-memory 修改 | E1/E2 双向同步复查 |
| **文件删除（H维度）** | **H7 引用清理复查 + A1 死链复查 + C3 导入路径复查 + C4 JAR引用复查** |

### Phase 5：输出审查报告

---

## 审查报告格式（3 部分）

> **格式简化**：从原 5 部分（总览+详细问题+修复验证+健康度评分+建议行动）简化为 3 部分，提升 AI 生成效率。

```markdown
# Legado Skill 审查报告

**审查日期**：{YYYY-MM-DD}
**审查范围**：legado-source-creator + AGENTS.md + basic-memory(project=legado) + docs/specs/
**审查层级**：L1 快速检查 / L2 核心检查 / L3 深度检查（含合并模块）

---

## 第 1 部分：问题清单

### 总览

| 维度 | 问题数 | P0 | P1 | P2 | P3 | 状态 |
|------|--------|----|----|----|----|------|
| A. 文档完整性 | N | N | N | N | N | ✅/⚠️/❌ |
| B. 代码-文档一致性 | N | N | N | N | N | ✅/⚠️/❌ |
| C. 脚本与JAR验证 | N | N | N | N | N | ✅/⚠️/❌ |
| D. Legado源码匹配 | N | N | N | N | N | ✅/⚠️/❌ |
| E. basic-memory双向同步 | N | N | N | N | N | ✅/⚠️/❌ |
| F. 新用户视角 | N | N | N | N | N | ✅/⚠️/❌ |
| G. 设计文档状态 | N | N | N | N | N | ✅/⚠️/❌ |
| H. 文件债务清理 | N | N | N | N | N | ✅/⚠️/❌ |
| S. 补充检查 | N | N | N | N | N | ✅/⚠️/❌ |
| **合计** | **N** | **N** | **N** | **N** | **N** | — |

### 详细问题清单

（按 L1→L2→L3 分层列出，格式：`[LX-N] 检查点: 问题描述 | 严重度: P0/P1/P2/P3`）

---

## 第 2 部分：修复验证

| 修复项 | 验证方法 | 验证结果 |
|--------|---------|---------|
| ES5模式修复 | Python 测试脚本 | ES6 let→low, ES5 var→high ✅ |
| 死链修复 | Glob 验证文件存在 | booksource-schema.md 存在 ✅ |
| 跨文件一致性 | 三方对比 | SKILL.md/AI_README.md/AGENTS.md 一致 ✅ |
| JAR重建 | fatJar + ping测试 | legado-jvm.jar可启动 ✅ |
| 版本锁 | build.gradle.kts对比 | jsoup 1.16.2/rhino 1.8.1/hutool 5.8.22 ✅ |
| 文件债务清理 | H7 引用清理复查 | 废弃文件已删除，引用已清理 ✅ |
| memory 一致性 | E1/E2 双向同步复查 | 笔记与文档一致 ✅ |

---

## 第 3 部分：健康度评分

### 维度评分

| 维度 | 评分 | 说明 |
|------|------|------|
| A. 文档完整性 | X/10 | |
| B. 代码-文档一致性 | X/10 | |
| C. 脚本与JAR验证 | X/10 | |
| D. Legado源码匹配 | X/10 | |
| E. basic-memory双向同步 | X/10 | |
| F. 新用户视角 | X/10 | |
| G. 设计文档状态 | X/10 | |
| H. 文件债务清理 | X/10 | |
| S. 补充检查 | X/10 | |
| **综合** | **X/10** | |

### 建议与后续行动

1. {P0/P1 问题的后续跟进}
2. {需要 Legado 源码更新的项}
3. {需要 basic-memory 补写的项}
4. {需要 AGENTS.md 同步更新的项}
5. {需要 JAR 重建的项}
6. {需要删除的废弃文件清单及删除前确认}
```

---

## 历史审查经验

> 以下是从 7 轮审查中提炼的常见问题模式，审查时优先检查。

### 高频问题 Top 25

| 排名 | 问题 | 维度 | 出现频率 |
|------|------|------|---------|
| 1 | ES5/ES6 模式配置错误 | B4 | 每次审查必查 |
| 2 | 可信度评估逻辑不一致（Kotlin vs Python vs SKILL.md） | B3 | 每次审查必查 |
| 3 | 旧版源码文件残留（根目录 .kt vs legado-jvm/src/） | H1 | 每次审查必查 |
| 4 | 代码逻辑与最新 Legado 行为不一致（未标记废弃但已过时） | H8 | 每次审查必查 |
| 5 | 文档内容与最新 Legado 源码不一致（未标记废弃但已过时） | H9 | 每次审查必查 |
| 6 | basic-memory 笔记内容过时（有笔记但内容已不准确） | H10 | 每次审查必查 |
| 7 | 引用死链（_index.md 引用不存在的文件） | A1 | 高频 |
| 8 | 薄文件（文档只有标题无内容） | A4 | 高频 |
| 9 | 跨文件不一致（SKILL.md vs AI_README.md vs AGENTS.md） | A2 | 高频 |
| 10 | 子文档数量不一致（_index.md vs SKILL.md vs 实际） | A3 | 高频 |
| 11 | MockJsExtensions 函数列表不完整 | B1 | 高频 |
| 12 | basic-memory 笔记缺少 source_doc 元数据 | E1/E2 | 高频 |
| 13 | Kotlin源码只检查了RuleEngineServer.kt，遗漏其他文件 | B1 | 高频 |
| 14 | JAR文件过期（源码已更新但JAR未重建） | C4 | 高频 |
| 15 | 临时测试脚本残留（test_mvp3.py等） | H2 | 高频 |
| 16 | __pycache__/ 缓存文件残留 | H4 | 高频 |
| 17 | 文档中的代码示例使用了 ES6 语法 | H9 | 高频 |
| 18 | build.gradle.kts版本锁与AGENTS.md不一致 | B5 | 中频 |
| 19 | 模糊描述（"详见xxx"但xxx无具体说明） | F3 | 中频 |
| 20 | 设计文档状态标记过时 | G2/G3 | 中频 |
| 21 | JVM仿真器只检查AnalyzeRule.kt，遗漏RuleAnalyzer等 | D2 | 中频 |
| 22 | BookSource字段定义未验证 | D4 | 低频但严重 |
| 23 | 功能重叠文件（fetch_html.py vs html_fetcher.py） | H3 | 中频 |
| 24 | 过时JAR文件（rhino-1.7.15.jar等） | H5 | 低频 |
| 25 | source_doc 指向的文档已更新但笔记未更新 | H10 | 中频 |

### 42项审查检查清单（L1/L2/L3 三层分层）

> **分层说明**：42 项检查点按 L1(10)/L2(15)/L3(17) 三层组织，L3 含 4 个合并模块（合并后约 30 个逻辑检查模块）。

#### L1 快速检查（10项）— 5 分钟内完成

- [ ] L1-1 / A1: 所有文档引用链接有效（SKILL.md + AI_README.md + _index.md + AGENTS.md）
- [ ] L1-2 / A3: _index.md 列出数 = SKILL.md 声称数 = 实际文件数
- [ ] L1-3 / C1: Python 脚本语法正确
- [ ] L1-4 / C4: legado-jvm.jar存在且非空，可启动，JAR与源码同步
- [ ] L1-5 / H7: SKILL.md/AI_README.md 中无对已删除文件的引用
- [ ] L1-6 / S1: 模板文件有效、有版本标记、占位符有说明
- [ ] L1-7 / S2: CMS样本结构正确、SKILL.md引用一致
- [ ] L1-8 / S5: 输出目录存在，已有文件格式正确
- [ ] L1-9 / E3: 无重复笔记
- [ ] L1-10 / E4: basic-memory 目录结构与 SKILL.md 定义一致

#### L2 核心检查（15项）— 20 分钟内完成

- [ ] L2-1 / A2: SKILL.md / AI_README.md / AGENTS.md 三方描述一致
- [ ] L2-2 / B2: Python 客户端方法与 SKILL.md API 表匹配
- [ ] L2-3 / B3: Kotlin assessConfidence vs Python assess_confidence vs SKILL.md 三方一致
- [ ] L2-4 / B4: 所有 JS 上下文使用 VERSION_1_7，无注释与代码矛盾
- [ ] L2-5 / B5: build.gradle.kts 版本锁与 AGENTS.md 一致（jsoup 1.16.2 / rhino 1.8.1 / hutool 5.8.22）
- [ ] L2-6 / C2: 脚本参数与 SKILL.md 一致
- [ ] L2-7 / C3: 导入路径有效，脚本间接口调用正确
- [ ] L2-8 / D2: 所有4个JVM仿真器组件（AnalyzeRule/RuleAnalyzer/AnalyzeByJSoup/AnalyzeByXPath）与 Legado 一致
- [ ] L2-9 / F1: 新 agent 能理解每个 Phase 的输入/输出/决策点
- [ ] L2-10 / F2: 无信息缺失，概念首次出现有定义
- [ ] L2-11 / F3: 无模糊描述，"详见xxx"指向的文档有具体说明
- [ ] L2-12 / S3: legado-workflow-auditor 对 legado-source-creator 的描述准确
- [ ] L2-13 / S4: html_fetcher.py 回退链与 SKILL.md 一致
- [ ] L2-14 / G1: spec.md 与实际实现一致
- [ ] L2-15 / G3: tasks.md 完成状态与实际代码一致

#### L3 深度检查（17项）— 含 4 个合并模块

**合并模块 1：文件债务快速扫描（L3-1~L3-6）**
- [ ] L3-1 / H1: 无旧版源码文件残留（根目录 .kt vs legado-jvm/src/）
- [ ] L3-2 / H2: 无临时测试脚本残留（test_*.py 等）
- [ ] L3-3 / H3: 无功能重叠的废弃文件（fetch_html.py 等），有引用的旧文件有迁移计划
- [ ] L3-4 / H4: 无 __pycache__/、空文件、构建临时文件
- [ ] L3-5 / H5: 每个JAR文件有明确保留理由，无冗余JAR
- [ ] L3-6 / H6: 无临时分析文档残留在 tools/ 目录

**合并模块 2：代码一致性统一检查（L3-7~L3-9）**
- [ ] L3-7 / H8: 代码逻辑与最新 Legado 行为一致，无硬编码过时值，无注释与代码矛盾
- [ ] L3-8 / B1: 所有6个Kotlin源文件与SKILL.md一致（命令/函数/可信度/ES5模式）
- [ ] L3-9 / D1: Mock 函数签名与 Legado JsExtensions.kt 匹配

**合并模块 3：文档一致性统一检查（L3-10~L3-13）**
- [ ] L3-10 / H9: 文档内容与最新 Legado 源码一致，代码示例有效，陷阱描述准确
- [ ] L3-11 / A4: 无薄文件（< 30 行且无实质内容）
- [ ] L3-12 / D3: RssSource 字段定义与 Legado RssSource.kt 匹配
- [ ] L3-13 / D4: BookSource 字段定义与 Legado BookSource.kt 匹配

**合并模块 4：memory 一致性检查（L3-14~L3-16）**
- [ ] L3-14 / H10: basic-memory 笔记内容与最新文档一致，无过时结论，无孤立笔记
- [ ] L3-15 / E1: SKILL.md 陷阱速查表 ↔ basic-memory trap 笔记双向无遗漏
- [ ] L3-16 / E2: references/ 关键经验 ↔ basic-memory experience/pattern 笔记双向无遗漏

**独立检查**
- [ ] L3-17 / G2: design.md AD 状态与实际代码一致

---

## 降级路径

| 不可用项 | 降级方案 |
|---------|---------|
| Legado 源码不可访问 | 跳过维度 D，标记为"需源码验证"，使用 references/source-analysis/ 中的已有结论 |
| basic-memory MCP 不可用 | 1.检测不可用(调用search_notes异常) 2.Grep references/替代 3.标记"需 basic-memory 验证" |
| JDK 不可用 | 跳过 C4 JAR 启动验证和 B5 构建验证，仅做静态代码审查 |
| Python 不可用 | 跳过 C1 脚本语法验证，仅做静态代码审查 |
| Gradle 不可用 | 跳过 B5 构建验证，仅检查 build.gradle.kts 文件内容 |

---

## 与 legado-workflow-auditor 的关系

| 维度 | legado-workflow-auditor | legado-skill-auditor |
|------|------------------------|---------------------|
| 审查对象 | 单次书源/订阅源创建任务的执行证据 | skill 本身的质量和一致性 |
| 触发时机 | 每次创建源任务完成后 | 定期或用户主动触发 |
| 审查范围 | Phase 1/3/5 执行证据 | 8维度37子项+5补充=42检查点（L1/L2/L3三层，合并后~30模块） |
| 输出 | 审计报告（通过/失败） | 审查报告 + 修复 + 回归验证 + 健康度评分 |
| 修复能力 | 无（仅报告） | 有（精准修复 + 回归验证） |

**建议使用顺序**：先用 `legado-skill-auditor` 确保 skill 健康，再用 `legado-source-creator` 创建源，最后用 `legado-workflow-auditor` 审计执行证据。
