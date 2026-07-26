# 项目记忆机制改造（memory-mechanism-redesign）

> 状态标记：🔄 设计中

## 功能概述

对当前 TRAE IDE 项目记忆机制进行整体改造，解决三大核心痛点：
1. **路径权限问题**：官方位置在 C 盘 `~/.trae-cn/memory/`，导致 AI 的 Edit/Write 工具无法直接编辑（实测报错 "File path is not within allowed workspace"）
2. **多任务并发冲突**：多个对话窗口共享同一个 `project_memory.md`，写入时互相覆盖（无对话级隔离）
3. **AI 无法获取 session_id**：无法直接感知当前对话的唯一标识，导致压缩恢复时难以区分新旧对话

## 核心能力

### 1. 双轨制存储架构
- **官方位置（轻量索引）**：`~/.trae-cn/memory/projects/{key}/project_memory.md` 保留，作为"系统注入索引"
- **项目目录（重量主记忆）**：`.trae/memory/projects/{key}/` 作为主记忆，解决 Edit/Write 权限

### 2. 对话级唯一 ID 机制
- 格式：`conv-{YYYYMMDDHHmmss}-{6位hex}`
- 每个对话独立记忆文件 `conv_memory_{conv_id}.md`，避免并发冲突

### 3. 现有规范合理性审查
- 路径硬编码风险评估
- 五件套并行读取流程优化
- 用户反馈持久化机制改进

## 官方机制优缺点速览

| 维度 | 优点 | 缺点 |
|------|------|------|
| 路径 | 标准化统一 | C 盘硬编码，Edit/Write 受限 |
| 注入 | 系统自动注入 memory context | 仅识别官方位置，迁移后失效 |
| 共享 | 全局记忆跨项目共享 | 项目记忆不跨电脑 |
| 归档 | 已有 archived_feedback/ | project_memory.md 持续增长 |
| 并发 | - | 无对话级隔离，多窗口互相覆盖 |
| 标识 | - | AI 无法直接获取 session_id |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求范围、技术方案（含替代方案+缺点） |
| [design.md](./design.md) | 技术架构、ADR 决策、数据流、文件变更 |
| [tasks.md](./tasks.md) | 实施任务清单（设计阶段完成，等待审核） |

## 状态

- 🔄 设计中（2026-07-26）
- ⏳ 等待用户审查设计方案
