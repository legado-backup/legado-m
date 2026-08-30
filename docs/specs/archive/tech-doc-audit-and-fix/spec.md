# Spec：技术文档全面审查与一致性修复

## Intent

项目中大量技术文档与实际代码/结构不一致，包括过时数字统计、失效链接、错误类型描述、缺失索引等。AI Agent 按文档执行时会直接报错或遗漏关键参考。需要全面审查并修复，确保文档与项目真实情况一致。

## Scope

### In Scope

- AGENTS.md：过时数字和引用修复
- docs/INDEX.md：失效链接和过时信息修复
- docs/project-flow/：skill-architecture.md、quick-reference.md、INDEX.md 过时内容修复
- docs/01-项目概述.md：BookSourceType 错误描述、不存在类名修复
- docs/04-网络请求.md：AnalyzeUrl 参数类型错误修复
- docs/project-rules/：testing_rules.md、architecture_rules.md、exception_rules.md、openspec-workflow.md 不一致修复
- .trae/skills/ SKILL.md：过时脚本引用修复
- 所有文档中的 ASCII 图表 → mermaid-cn 重构

### Out of Scope

- docs/specs/ 下的 OpenSpec 设计文档（已排除）
- 代码修改（仅修改文档）
- 新增功能设计文档

## Approach

### Alternatives Considered

1. **逐文件手动修复**：准确但效率低，容易遗漏
2. **批量子代理并行修复**：效率高但之前超时严重，且难以控制修改质量
3. **先审查出清单，按清单逐文件精准修复**（Selected）：审查与修复分离，清单经用户审核后再执行

### Selected Approach

基于已完成的深度审查结果，生成精确的修改清单（每个文件的具体 old→new），经用户审核后逐文件执行。

### Drawbacks

- 修改清单较长（约 40+ 项），逐文件修复耗时
- 部分历史文档（01-15）的类名/方法名描述可能需要较大幅度重写

## Requirements

### R1：数字统计一致性

| 文档 | 过时值 | 正确值 | 依据 |
|------|--------|--------|------|
| AGENTS.md | "6 大参考目录" | "10 大参考目录" | references/ 下实际 10 个子目录 |
| AGENTS.md | "10 个验证脚本" | "16 个验证脚本" | scripts/ 下实际 16 个 .py |
| AGENTS.md | "MVP1-4" | "legado-jvm.jar" | 实际只有 1 个统一 JAR |
| AGENTS.md | "覆盖率 55-90%" | "覆盖率 85-90%" | SKILL.md 记载 |
| docs/INDEX.md | "6 大参考目录、10 个验证脚本" | "10 大参考目录、16 个验证脚本" | 同上 |
| docs/INDEX.md | 3 个 MVP JAR | 1 个 legado-jvm.jar | 实际文件结构 |
| skill-architecture.md | "54 条陷阱" | "79 条陷阱" | SKILL.md 陷阱编号 1-79 |
| skill-architecture.md | "6 大参考目录" | "10 大参考目录" | 同上 |
| skill-architecture.md | "5 个验证脚本" | "16 个验证脚本" | 同上 |
| skill-architecture.md | "MVP1-3 三个 JAR" | "1 个 legado-jvm.jar" | 同上 |
| skill-architecture.md | "rhino-1.7.15.jar" | "rhino-1.8.1.jar" | 实际文件 |
| quick-reference.md | "实体数 28" | "21" | 实际 21 个 @Entity |

### R2：失效链接修复

| 文档 | 失效链接 | 正确链接 |
|------|---------|---------|
| docs/INDEX.md | specs/skill-improvement/ | specs/archive/skill-improvement/ |
| docs/INDEX.md | specs/skill-architecture-optimization/ | specs/archive/skill-architecture-optimization/ |
| docs/INDEX.md | specs/skill-html-fetch-enhancement/ | specs/archive/skill-html-fetch-enhancement/ |
| docs/INDEX.md | specs/test-infra-upgrade/ | specs/archive/test-infra-upgrade/ |
| docs/INDEX.md | specs/skill-trio-optimization/ | specs/archive/skill-trio-optimization/ |
| docs/INDEX.md | specs/skill-deep-optimization-v2/ | specs/archive/skill-deep-optimization-v2/ |
| docs/INDEX.md | tools/legado-rule-engine-mvp1.jar | tools/legado-jvm/build/libs/legado-jvm.jar |
| docs/INDEX.md | tools/legado-rule-engine-mvp2.jar | （删除） |
| docs/INDEX.md | tools/legado-rule-engine-mvp3.jar | （删除） |
| docs/INDEX.md | tools/rule_engine_client.py | scripts/legado_client/client/rule_engine_client.py |
| docs/INDEX.md | tools/ajax-diff-analysis.md | references/source-analysis/ajax-diff-analysis.md |

### R3：错误类型描述修复

| 文档 | 错误描述 | 正确描述 |
|------|---------|---------|
| 04-网络请求.md | headerMapF: (() -> Map<String, String>)? | headerMapF: Map<String, String>? |
| 04-网络请求.md | speakSpeed: Float | speakSpeed: Int? |
| 04-网络请求.md | baseUrl: String? | baseUrl: String = "" |
| 04-网络请求.md | infoMap: MutableMap<String, Any>? | infoMap: MutableMap<String, String>? |

### R4：错误类名/概念修复

| 文档 | 错误 | 正确 |
|------|------|------|
| 01-项目概述.md | BookSourceType 是"位标志" | BookSourceType 是简单枚举(0-4)，位标志是 BookType |
| 01-项目概述.md | FindModel.kt | WebBook.exploreBook() / ExploreShowViewModel |
| 01-项目概述.md | BookInfoModel.kt | WebBook.getBookInfo() / BookInfo.kt |
| 01-项目概述.md | BookChapterModel.kt | WebBook.getChapterList() / BookChapterList.kt |
| 01-项目概述.md | ImageRule.kt | ImageProvider / BookHelp.saveImages() |
| 03-规则引擎.md | AnalyzeByRegex 独立解析器 | 正则处理内嵌在 AnalyzeRule 中，非独立类 |

### R5：规范文档不一致修复

| 文档 | 不一致 | 修复 |
|------|--------|------|
| testing_rules.md | 声称"没有 androidTest" | 改为列出 6 个 androidTest 文件 |
| architecture_rules.md | EventBus 常量"42 个" | 改为"38 个" |
| exception_rules.md | WebDavException 继承描述矛盾 | 添加注释说明例外 |
| openspec-workflow.md | 路径 .trae/specs/ | 改为 docs/specs/ |
| openspec-workflow.md | 映射表引用 Grafana 内容 | 替换为 Legado 项目内容 |

### R6：缺失索引补充

| 文档 | 缺失内容 |
|------|---------|
| docs/INDEX.md | 缺少 7 个活跃 specs 目录 |
| docs/INDEX.md | 缺少 4 个参考目录（site-features, rule-construction-guide, known-fix-patterns, cms-samples） |
| project-flow/INDEX.md | 仅覆盖 8/33 个文档的关键词索引 |

### R7：不存在脚本引用清理

| 文档 | 不存在脚本 | 替换为 |
|------|-----------|--------|
| AGENTS.md | deep-verify.py | verify-source.py |
| AGENTS.md | classify-and-fix.py | debug-source.py |
| docs/INDEX.md | deep-verify.py | verify-source.py |
| docs/INDEX.md | classify-and-fix.py | debug-source.py |

### R8：ASCII 图表 → mermaid 重构

| 文档 | 图表类型 | 当前格式 |
|------|---------|---------|
| AGENTS.md | Skill 三件套调用链路图 | ASCII 方框图 |
| 01-项目概述.md | 分层架构图 | mermaid（已有） |
| 01-项目概述.md | 模块依赖图 | mermaid（已有） |
| 01-项目概述.md | 服务启动依赖图 | mermaid（已有） |
| 02-数据库设计.md | ER 图 | mermaid（已有） |
| skill-architecture.md | Skill 金字塔架构 | ASCII |
| skill-architecture.md | 5 阶段工作流 | ASCII |

## Scenarios

### S1：AI Agent 按文档执行脚本

- **Before**：Agent 引用 `deep-verify.py` → 文件不存在 → 报错
- **After**：Agent 引用 `verify-source.py` → 文件存在 → 正常执行

### S2：AI Agent 查阅参考文档

- **Before**：Agent 只看到 6 大参考目录，遗漏 known-fix-patterns 等 4 个目录
- **After**：Agent 看到 10 大参考目录，完整覆盖

### S3：AI Agent 读取 AnalyzeUrl 参数

- **Before**：Agent 按 headerMapF 函数类型编写代码 → 编译错误
- **After**：Agent 按 Map 类型编写代码 → 正确

### S4：AI Agent 查找 specs 文档

- **Before**：INDEX.md 指向已归档路径 → 404
- **After**：INDEX.md 正确指向 archive/ 或活跃目录 → 可访问
