# 项目记忆机制改造（memory-mechanism-redesign）

> 状态标记：✅ 实施完成（2026-07-27 废弃 conv_id，采用简化方案，阶段A→F 全部完成）
> ⚠️ **重大修订**：废弃 conv_id 机制，所有对话共享 ai_memory_main.md，多任务并发时 AskUserQuestion 确认

## 功能概述

对当前 TRAE IDE 项目记忆机制进行整体改造，解决三大核心痛点：
1. **路径权限问题**：官方位置在 C 盘 `~/.trae-cn/memory/`，AI 的 Read/Edit/Write 工具无法直接访问（铁证：2026-07-27 实测 Read C盘 project_memory.md 报错 "File path is not within allowed workspace"）
2. **多任务并发冲突**：多个对话窗口共享同一个 `project_memory.md`，写入时互相覆盖（无对话级隔离）
3. **AI 无法获取 session_id**：无法直接感知当前对话的唯一标识，导致压缩恢复时难以区分新旧对话；且 conv_id 如何在对话中保持一致、压缩恢复后如何获取，是核心设计挑战

## 核心能力

### 1. AI 独立记忆系统（AD-11 完全分离）
- **官方记忆（C盘）**：TRAE IDE 系统维护，AI 不读不写不干预，系统注入作背景参考（P3）
- **AI 独立记忆（项目目录 `.trae/memory/`）**：AI 完全自主管理，Edit/Write 可用（P1 权威源）
- 两个系统独立运行，不试图同步、不试图替换

### 2. 多任务并发处理（简化版，废弃 conv_id）
- **废弃 conv_id 机制**（用户 2026-07-27 22:51 决策）：不再生成/持久化/恢复 conv_id
- **所有对话共享 `ai_memory_main.md`**：靠 Edit 串行化 + old_string 精确匹配避免覆盖
- **多任务并发处理流程**：
  ```
  对话开始/压缩恢复时：
    AI Read ai_memory_main.md → 检查"当前活跃任务列表"
    ├─ 无活跃任务 → 询问用户当前任务
    ├─ 有1个活跃任务 → 假设是当前任务，沿用（告知可纠正）
    └─ 有多个活跃任务 → AskUserQuestion 让用户选择当前窗口处理哪个任务
  ```
- **不依赖对话历史**：仅依赖文件持久化，AI 无状态也能可靠恢复

### 3. 存储结构（简化版，去掉冗余层级和 conv_memory）
```
.trae/memory/                              # AI 独立记忆根目录（项目目录下）
├── ai_memory_main.md                      # AI 主记忆（Hard Constraints + 当前任务状态 + 活跃任务列表 + 用户反馈）
└── archived/                              # 归档目录
    ├── feedback/YYYYMM.md                 # 反馈归档（超7天）
    └── main_history_{YYYYMMDD}.md         # 主记忆历史归档（超50KB）
```
**路径简化理由**：项目目录本身就是项目边界，不需要再用 `{项目key}` 区分；废弃 conv_id 后无对话级文件，去掉 `{YYYYMMDD}/conv_memory_{conv_id}.md` 层级。

### 4. 现有规范合理性审查
- 路径硬编码风险评估（已确认 C盘 memory 目录 Read 受限）
- 五件套并行读取流程优化（改为读项目目录 ai_memory_main.md）
- 用户反馈持久化机制改进（写入 ai_memory_main.md，Edit 串行化）
- 时间戳规范（禁 mcp_Time + 强制 date/PowerShell 24H制）

### 5. 行业最佳实践借鉴（AD-16~AD-20）
- AD-16 "记忆只是提示"原则（借鉴 Claude Code，降低幻觉）
- AD-17 "只记上下文无法派生的认知"原则（避免冗余）
- AD-18 4类记忆分类（user/feedback/project/reference）
- AD-19 索引文件200行限制（控制上下文占用）
- AD-20 版本控制集成（.gitignore 排除敏感内容）

## 官方机制优缺点速览

| 维度 | 优点 | 缺点 |
|------|------|------|
| 路径 | 标准化统一 | C 盘硬编码，AI Read/Edit/Write 受限（铁证） |
| 注入 | 系统自动注入 memory context | 仅识别官方位置，AI 独立记忆不被注入 |
| 共享 | 全局记忆跨项目共享（user_profile.md） | 项目记忆不跨电脑 |
| 归档 | 已有 archived_feedback/ | project_memory.md 持续增长 |
| 并发 | - | 无对话级隔离，多窗口互相覆盖 |
| 标识 | - | AI 无法直接获取 session_id |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求范围、技术方案（AD-11 独立记忆系统 + 简化方案废弃 conv_id + 替代方案 + 缺点） |
| [design.md](./design.md) | 技术架构（AD-11）+ 20 个 ADR 决策 + 数据流 + 文件变更（AD-02/04 标记废弃） |
| [tasks.md](./tasks.md) | 实施任务清单（一次性完成，废弃 conv_id 简化方案，阶段A→F 连续执行） |
| [overall-planning.md](./overall-planning.md) | 整体规划与可行性分析 |
| [industry-best-practices.md](./industry-best-practices.md) | 行业最佳实践对比（Claude Code/Cursor/Cline） |
| [analysis-report.md](./analysis-report.md) | 深度分析报告（文档评估 + 不一致分析 + 改造清单 + 迁移方案） |

## 状态

- ✅ 实施完成（2026-07-27 阶段A→F 全部完成）
- ✅ 设计完成（2026-07-27 修订，简化方案：废弃 conv_id + 路径简化 + 多任务 AskUserQuestion 确认）
- ✅ 验证完成（V1 Edit/Write 可用 + V2 压缩恢复流程 + V3 归档触发条件已设计）

## 关键设计决策摘要

| ADR | 标题 | 状态 |
|-----|------|------|
| AD-11 | AI 独立记忆系统（完全分离） | Accepted（替代 AD-01/03/10） |
| AD-02 | ~~对话 ID 完整机制（3处持久化）~~ | **Deprecated（2026-07-27 22:51 废弃）** |
| AD-04 | ~~对话级独立文件隔离~~ | **Deprecated（2026-07-27 22:51 废弃）** |
| AD-07 | 时间戳规范（兼容 gitbash） | Accepted（2026-07-27 修订） |
| AD-09 | 全局规范适配（6个文件追加补充） | Accepted |
| AD-14 | 任务级记忆记录机制 | Accepted（简化：写入 ai_memory_main.md） |
| AD-15 | 压缩恢复防错乱机制 | Accepted（简化：多任务 AskUserQuestion 确认） |
| AD-16 | "记忆只是提示"原则 | Accepted（新增） |
| AD-17 | "只记无法派生认知"原则 | Accepted（新增） |
| AD-18 | 4类记忆分类 | Accepted（新增，可延后） |
| AD-19 | 索引文件200行限制 | Accepted（新增） |
| AD-20 | 版本控制集成 | Accepted（.trae/memory/ 纳入 Git） |
