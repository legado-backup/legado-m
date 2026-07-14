# 全局规范重组（global-spec-restructure）

> **状态**：🔄 设计中
> **创建日期**：2026-07-13
> **前置任务**：spec-system-optimization（✅ 已完成，但发现系统注入机制问题）

## 功能概述

将 Legado 项目 AGENTS.md 中**跨项目通用**的内容迁移到全局规范（`~/.trae-cn/user_rules/`），解决以下核心问题：

1. **系统注入机制问题**：spec-system-optimization 创建了 core-spec.md V2.1，但系统注入的 user_rules 可能是固定文本配置而非读取文件，导致新规范不生效
2. **AGENTS.md 通用内容冗余**：V2.1硬约束机制/复杂任务处理/输出预算管理/OpenSpec流程/并发文件修改等通用内容被放在项目主规范中，其他项目无法复用
3. **AskUserQuestion 跨项目失效**：用户还原了 rule-1782963384927.md，因为 AI 在其他项目中不遵守 AskUserQuestion 规则，根因是系统注入版本中该规则约束不够强
4. **AI "认为完成但实际很多问题"**：spec-system-optimization 未验证系统注入机制就声称完成，是虚假完成

## 核心能力

- 将通用内容从 AGENTS.md 迁移到全局规范
- 确保全局规范在所有项目中被系统注入并生效
- 强化 AskUserQuestion 跨项目强制规则
- 建立验证机制，确保规范真的被系统注入和遵守

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| spec.md | [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| design.md | [design.md](./design.md) | Technical Approach/Architecture Decisions/Data Flow/File Changes |
| tasks.md | [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 关键决策摘要

| 决策 | 选定方案 | 理由 |
|------|---------|------|
| 系统注入机制 | 待确认（检查点1与用户确认） | 需要搞清楚系统注入的是文件还是固定文本 |
| 通用内容迁移目标 | core-spec.md 扩充 | core-spec.md 已有5章节，新增§6通用流程+§7输出预算 |
| AskUserQuestion 强化 | 整合到系统注入入口 | 确保所有项目都能看到 |
| AGENTS.md 瘦身 | 保留索引+项目特定内容 | 通用内容只保留"详见 core-spec.md §X"引用 |
