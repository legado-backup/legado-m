# Skill 三件套使用者体验优化方案

> **目标**：从使用者（AI agent / 人类用户）角度优化三个 skill 的上手成本、执行效率、可靠性，降低上下文消耗，消除功能歧义。
> **状态**：🔄 设计中
> **创建日期**：2026-06-21
> **视角**：使用者体验（区别于 legado-skill-optimization 的技术实现视角）

---

## 为什么需要本方案

### 问题：三个 skill 从使用者角度存在系统性痛点

现有 `legado-skill-optimization` 聚焦**技术实现**（JAR 仿真保真度、Python 客户端工程化、三层架构），但忽略了**使用者体验**：

| 痛点类别 | 具体表现 | 影响 |
|---------|---------|------|
| **上下文膨胀** | 三个 SKILL.md 合计 1924 行（source-creator 514 + workflow-auditor 153 + skill-auditor 1257） | AI agent 读取后上下文消耗严重，复杂任务时遗漏关键步骤 |
| **流程过度设计** | source-creator 5 阶段对简单 CMS 网站是过度设计 | 简单场景执行效率低，AI 花大量时间在流程管理 |
| **功能边界模糊** | 大量"实现状态：设计中/部分实现"标记 | 使用者无法判断 skill 实际能力边界 |
| **工具选择困难** | 11 个辅助工具 + 7 个测试脚本 + 42 个审查检查点 | 使用者不知道何时该用哪个 |
| **basic-memory 单点故障** | 三个 skill 都强依赖 basic-memory | 不可用时整个体系降级，降级路径各自为政 |
| **协作链路理想化** | "skill-auditor → source-creator → workflow-auditor" | 实际使用中用户不会按此顺序，协作经常失败 |
| **职责重叠** | skill-auditor E 维度与 workflow-auditor 都检查 basic-memory | 使用者困惑该用哪个 |
| **审查范围不全** | skill-auditor 只审查 source-creator | 三个 skill 中有两个不在审查范围内 |

### 与现有文档的关系

| 文档 | 视角 | 聚焦点 |
|------|------|--------|
| `legado-skill-optimization` | 技术实现 | JAR 保真度、Python 客户端、三层架构 |
| **本方案** | **使用者体验** | **上下文消耗、流程简化、功能边界、工具选择、协作可靠性** |

两者互补：技术实现是"能力"，使用者体验是"可用性"。

---

## 核心优化方向（8 个）

| # | 方向 | 目标 | 受益 skill |
|---|------|------|-----------|
| 1 | 精简 SKILL.md | source-creator 514→300行，skill-auditor 1257→500行 | 全部 |
| 2 | 简化工作流，支持快速路径 | 简单场景 2 步完成（分析→输出） | source-creator |
| 3 | 统一 basic-memory 降级策略 | 三 skill 采用统一降级路径 + 功能边界说明 | 全部 |
| 4 | 消除"实现状态"歧义 | 移除"设计中"描述，只描述已实现功能 | source-creator |
| 5 | 简化工具选择 | 7 个测试脚本→2 个核心脚本，42 检查点→分级执行 | source-creator, skill-auditor |
| 6 | 扩展 skill-auditor 审查范围 | 审查三个 skill 而非只审查 source-creator | skill-auditor |
| 7 | 增强 workflow-auditor 独立价值 | 增加实际验证能力，减少 basic-memory 依赖 | workflow-auditor |
| 8 | 统一触发词和上下文传递 | 简化触发词表，提供上下文传递模板 | 全部 |

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 需求规格：Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术设计：8 个优化方向的具体方案 |
| [tasks.md](./tasks.md) | 任务清单：按优先级分级 |

---

## 预期收益

| 指标 | 当前 | 优化后 |
|------|------|--------|
| SKILL.md 总行数 | 1924 行 | ~800 行 |
| 简单场景执行步骤 | 5 阶段 | 2 步（快速路径） |
| "实现状态"歧义标记 | 15+ 处 | 0 处 |
| basic-memory 不可用时可用率 | ~30% | ~80% |
| 工具选择决策点 | 18 个（11工具+7脚本） | 4 个（2脚本+2工具） |
| 审查检查点执行完整率 | ~40%（AI 经常只执行部分） | ~90%（分级执行） |
