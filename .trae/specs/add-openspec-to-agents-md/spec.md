# 将 OpenSpec 工作流程写入 AGENTS.md 主规范 Spec

## Why
当前 OpenSpec 工作流程仅作为子规范文档（docs/project-rules/openspec-workflow.md）存在，AI Agent 容易忽略。需要将其作为 🔴 强制执行规则直接写入 AGENTS.md 主规范，确保所有新增功能、优化功能必须先生成 OpenSpec 文档并经用户审核通过后才能开始实施。

## What Changes
- 在 AGENTS.md 中新增「🔴🔴 AI Agent 强制执行规则：OpenSpec 工作流程」章节，与现有的「复杂任务处理流程」和「书源自测交付流程」同级
- 该章节包含：强制触发条件、四文档要求、强制检查点、文档状态流转
- 在 AGENTS.md 的反模式警告中补充 OpenSpec 相关条目
- 保留 docs/project-rules/openspec-workflow.md 作为详细展开文档，AGENTS.md 中放精简版+链接

## Impact
- Affected specs: AGENTS.md 主规范
- Affected code: 无代码变更，仅文档变更

## ADDED Requirements

### Requirement: OpenSpec 强制工作流程
AI Agent 在执行任何新增功能、优化功能、Bug 修复、重构任务时，**必须**先生成 OpenSpec 四文档（README.md、spec.md、design.md、tasks.md），经用户审核通过后才能开始实施代码。

#### Scenario: 新功能开发
- **WHEN** 用户请求新增功能
- **THEN** AI Agent 必须先执行需求分析，生成 OpenSpec 四文档到 `docs/specs/{功能名称}/`，更新 docs/INDEX.md，然后停下来等待用户审核确认

#### Scenario: 功能优化
- **WHEN** 用户请求优化现有功能
- **THEN** AI Agent 必须先分析影响范围，生成 OpenSpec 四文档，等待用户确认后才能修改代码

#### Scenario: Bug 修复
- **WHEN** 用户报告 Bug 需要修复
- **THEN** AI Agent 必须先定位 Bug 根因，生成 OpenSpec 四文档（可精简），等待用户确认后才能修复

#### Scenario: 用户审核通过
- **WHEN** 用户审核 OpenSpec 文档并确认
- **THEN** AI Agent 按照 tasks.md 顺序执行，每完成一个任务标记 ✅

#### Scenario: 用户审核未通过
- **WHEN** 用户审核后提出修改意见
- **THEN** AI Agent 修改 OpenSpec 文档后重新提交审核，不得直接开始编码

### Requirement: 强制检查点
AI Agent 在以下节点必须停下来等待用户确认，不得跳过：
1. **检查点 1**：OpenSpec 四文档生成后 → 等待用户审查设计方案
2. **检查点 2**：核心实施完成后 → 等待用户审核实施结果
3. **检查点 3**：所有任务完成后 → 等待用户最终验收

### Requirement: 文档同步
任务完成后，AI Agent 必须对照代码变更同步更新 docs/project-flow/ 下对应文档，确保文档与代码一致。

## MODIFIED Requirements
无

## REMOVED Requirements
无
