# Tasks：技术文档全面审查与一致性修复

## 组1：AGENTS.md（已完成）

- [x] 1.1 OpenSpec 路径 `.trae/specs/{change-id}/` → `docs/specs/{功能名称}/`
- [x] 1.2 Skill 核心描述：6大目录/10脚本/MVP1-4 → 10大目录/16脚本/legado-jvm.jar
- [x] 1.3 参考文档 6→10 目录（添加 site-features/rule-construction-guide/known-fix-patterns/cms-samples）
- [x] 1.4 获取流程中 deep-verify.py → verify-source.py
- [x] 1.5 验证/固化/辅助脚本列表更新
- [x] 1.6 JVM 仿真器描述：MVP1-4/55-90% → legado-jvm.jar/85-90%
- [x] 1.7 三件套概览表更新
- [x] 1.8 快速入口 specs 链接更新
- [x] 1.9 Skill 三件套调用链路图 ASCII → mermaid

## 组2：docs/INDEX.md（已完成）

- [x] 2.1 "6 大参考目录、10 个验证脚本" → "10 大参考目录、16 个验证脚本"
- [x] 2.2 参考文档索引表 6→10 目录
- [x] 2.3 JVM 工具表：删除 3 个 MVP JAR，改为 `tools/legado-jvm/build/libs/legado-jvm.jar`
- [x] 2.4 `tools/rule_engine_client.py` → `scripts/legado_client/client/rule_engine_client.py`
- [x] 2.5 `tools/ajax-diff-analysis.md` → `references/source-analysis/ajax-diff-analysis.md`
- [x] 2.6 验证脚本表：删除 deep-verify.py/classify-and-fix.py，添加 verify-source.py/debug-source.py 等
- [x] 2.7 specs 部分：6 个归档链接移至 archive/，新增 7 个活跃 specs

## 组3：docs/project-flow/ 文档（已完成）

- [x] 3.1 quick-reference.md：实体数 28→21
- [x] 3.2 skill-architecture.md：陷阱数 54→79
- [x] 3.3 skill-architecture.md：参考目录 6→10
- [x] 3.4 skill-architecture.md：验证脚本 5→16
- [x] 3.5 skill-architecture.md：JVM MVP1-3→legado-jvm.jar
- [x] 3.6 skill-architecture.md：rhino-1.7.15→1.8.1
- [x] 3.7 skill-architecture.md：rule_engine_client.py 路径修正
- [x] 3.8 skill-architecture.md：附录目录结构更新（添加 test-data/output/legado_client/等）
- [x] 3.9 skill-architecture.md：ASCII 图表→mermaid（金字塔+5阶段）
- [x] 3.10 project-flow/INDEX.md：扩展关键词索引（50→130 条目，覆盖全部 33 个文档）

## 组4：docs/01-项目概述.md（无需修复）

- [x] 4.1 文件已重写为完整内容，无 BookSourceType/FindModel 等错误

## 组5：docs/04-网络请求.md（已完成）

- [x] 5.1 headerMapF: (() -> Map<String, String>)? → Map<String, String>?
- [x] 5.2 speakSpeed: Float → Int?
- [x] 5.3 baseUrl: String? → String = ""
- [x] 5.4 infoMap: MutableMap<String, Any>? → MutableMap<String, String>?

## 组6：docs/project-rules/（已完成）

- [x] 6.1 testing_rules.md：androidTest 描述修正
- [x] 6.2 architecture_rules.md：EventBus 常量 42→38
- [x] 6.3 exception_rules.md：WebDavException 注释
- [x] 6.4 openspec-workflow.md：路径+映射表修复

## 组7：Skill 文档（已完成）

- [x] 7.1 SKILL.md (source-creator)：classify-and-fix.py → verify-source.py
- [x] 7.2 SKILL.md (skill-auditor)：更新旧版目录结构引用（mvp1-build/等→tools/legado-jvm/）
- [x] 7.3 AI_README.md：classify-and-fix.py → debug-source.py
- [x] 7.4 references/site-features/high-frequency-issues.md：classify-and-fix.py → debug-source.py
- [x] 7.5 references/basic-memory-usage.md：deep-verify → verify-source
- [x] 7.6 scripts/generate-js-doc.py：deep-verify → verify-source

## 组8：mermaid 图表重构（已完成）

- [x] 8.1 AGENTS.md：Skill 三件套调用链路图
- [x] 8.2 skill-architecture.md：Skill 金字塔架构图
- [x] 8.3 skill-architecture.md：5 阶段工作流图

## 组9：编码修复（已完成）

- [x] 9.1 skill-architecture.md：360 处 U+FFFD 乱码修复 + UTF-8 编码转换
- [x] 9.2 rule-engine-algorithms.md：AnalyzeByRegex 描述修复（"非独立解析器"）

## 组10：03-规则引擎.md（已处理）

- [x] 10.1 文件已被文档整合移除，内容迁移至 rule-engine-algorithms.md
- [x] 10.2 AnalyzeByRegex 描述已在 rule-engine-algorithms.md 中修复

## 验证（全部通过）

- [x] V1 Grep 验证 AGENTS.md 无 "6 大参考目录" / "MVP1-4" / "deep-verify" / "classify-and-fix" 残留
- [x] V2 Grep 验证 docs/INDEX.md 无 MVP JAR 路径残留
- [x] V3 Grep 验证 skill-architecture.md 数字统计正确
- [x] V4 Grep 验证 04-网络请求.md 类型描述正确
- [x] V5 Grep 验证活跃文件（.trae/skills/ + docs/非specs/）无 deep-verify/classify-and-fix 残留
- [x] V6 Grep 验证全项目 .md 文件无 U+FFFD 损坏（rhino-js-traps.md 中的 4 处为有意示例）
- [x] V7 Grep 验证全项目 .py 文件无 deep-verify/classify-and-fix 残留
