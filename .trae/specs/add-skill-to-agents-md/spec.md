# AGENTS.md 瘦身 + Skill 引入 + 文档体系关联 Spec

## Why
当前 AGENTS.md 存在三个严重问题：
1. **太长**（509 行），每次对话都加载到上下文，浪费 Token。其中 42.8% 是 REFERENCE 类内容（任务导航 159 行、Wiki 索引 44 行），应完全外移
2. **缺失核心 Skill 说明**：`legado-source-creator` 是项目核心工具（54 条陷阱检查、5 阶段闭环工作流、6 大参考目录、5 个验证脚本），主规范完全没提及
3. **已有文档未引用**：`docs/` 顶层 15 个编号文档、`docs/project-flow/` 下 5 个文件、`docs/specs/` 下 6 个文件均未被引用，形成信息孤岛

## What Changes
- **瘦身 AGENTS.md**：从 509 行精简到 ~180 行，只保留 CONSTRAINT 类内容（强制规则 + 代码约束摘要 + 版本锁定 + 快速入口链接）
- **新增 Skill 章节**：在 AGENTS.md 中新增精简的 skill 引用（定位+触发条件+5阶段概要+文档/脚本索引链接），详细内容指向 skill 文档
- **外移 REFERENCE/FUNCTIONAL 内容**：任务导航表移到 `docs/project-flow/task-navigation.md`，Wiki 索引合并到 `docs/INDEX.md`
- **关联已有文档**：在 AGENTS.md 快速入口中引用 `docs/INDEX.md` 作为统一文档入口

## Impact
- Affected specs: AGENTS.md 主规范（大幅重构）
- Affected code: 无代码变更，仅文档变更
- 新建文件: `docs/project-flow/task-navigation.md`

## ADDED Requirements

### Requirement: AGENTS.md 精简到 ~180 行
AGENTS.md 只保留以下内容：
1. 项目描述（2-3 行）
2. 三个强制规则章节（复杂任务处理流程 + 书源自测交付流程 + OpenSpec 工作流程）— 不可删减
3. 代码约束摘要（Code Style 最关键 6 条 + Landmines 最致命 6 条 + 指向子文档链接）
4. 项目核心 Skill 引用（legado-source-creator 定位+触发+5阶段概要+文档/脚本索引链接）
5. 版本锁定速查（3 个不可升级依赖）
6. 快速入口链接区（指向 docs/INDEX.md、task-navigation.md、quick-reference.md 等）

### Requirement: 任务导航表外移
AGENTS.md 中的 14 个任务导航表（159 行）移到 `docs/project-flow/task-navigation.md`，AGENTS.md 仅保留一行链接。

### Requirement: Wiki 索引外移
AGENTS.md 中的「模块 Wiki 索引」（44 行）合并到 `docs/INDEX.md`，AGENTS.md 仅保留一行链接。

### Requirement: Skill 引用章节
AGENTS.md 中新增精简的 skill 引用章节，包含：
1. Skill 定位与触发条件（3-5 行）
2. 5 阶段闭环工作流概要（5 行流程图）
3. 参考文档索引链接（指向 skill 的 _INDEX.md）
4. 验证脚本索引链接（指向 skill 的 scripts/）
5. 与「书源自测交付流程」的关联说明（2 行）

### Requirement: 统一文档入口
`docs/INDEX.md` 作为项目所有文档的统一入口，覆盖 project-rules、project-flow、specs、skill 四类文档。

## MODIFIED Requirements
无

## REMOVED Requirements
无
