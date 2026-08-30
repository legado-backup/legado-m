# Legado Skill 统一优化重设计

## 项目概述
Legado书源/订阅源智能创建器（legado-source-creator）的全面审计与优化重设计。基于对现有Skill的设计文档、落地实现、组件能力与测试体系的深度审计，输出对齐现有Skill架构的新版统一OpenSpec优化设计文档。

## 核心目标
1. JAR仿真端+Python客户端与真机合法书源/订阅源高兼容（保真度95%+）
2. 日常开发调试无需频繁查阅源码（经验知识库可检索率>90%）
3. 全流程自动化率>70%（70%网站生成可用源无需手动操作）
4. 端到端测试校验准确性100%（JAR通过则真机通过）

## 四层架构
- 经验知识库（SKILL.md + references/ + basic-memory）= 决策大脑
- Python客户端（测试脚本 + 工具集）= 操作执行层
- JAR仿真服务端（legado-jvm规则引擎）= 核心能力底座
- Legado官方源码 = 最终兜底保障

## 文档索引
| 文档 | 内容 |
|------|------|
| README.md（本文件） | 项目概述、核心目标、架构、状态 |
| spec.md | 需求规格：Intent/Scope/Approach/Requirements/Scenarios |
| design.md | 技术设计：架构决策/数据流/文件变更/差距清单/修复计划 |
| tasks.md | 任务清单：分阶段落地实施Roadmap与验收标准 |

## 当前状态
- 阶段：**已归档** → 合并至 [legado-skill-v2-rebuild](../legado-skill-v2-rebuild/)
- 归档原因：经源码逐行核实审查，本方案存在以下关键错误：
  1. JsExtensionsStub 方法统计错误（本方案称 95/11/23，实际为 86/38/8）
  2. P0 级差距声称"全部完成"但未逐行源码核实
  3. 未识别 7 个高风险 Bug（v2-rebuild 识别并逐行核实）
  4. v2-rebuild 已全面覆盖本方案内容并修正了源码核实发现的错误
- 前置核查：已完成（4项全量核查）
- 核心发现：legado-skill-optimization 268项任务仅完成5.6%；JVM 132方法中**86完整/38降级/8不可用**（修正后）；Python客户端15个import路径问题；SKILL.md引用11个不存在文件

## 合规声明
所有开发与测试遵守著作权法律法规，仅使用合法授权的内容源。测试样本选取合法合规、真机可正常运行的真实书源/订阅源。

## 历史合并说明
本统一文档合并了以下历史OpenSpec的未完成项：
- legado-skill-optimization（统一OpenSpec，268项，5.6%完成率）
- skill-usability-optimization（可用性优化，71项，0%完成率）
- legado-skill-v2-rebuild（V2重建，85项，0%完成率）
- skill-core-capability-rebuild（核心能力重建，160项，100%已完成）
- jvm-webview-and-test-fix（WebView+测试修复，52项，100%已完成）
- source-repair-loop-optimization（源修复闭环，212项，86.8%已完成）
