# OpenSpec 工作流优化 Spec

## Why

当前 OpenSpec 工作流（`docs/project-rules/openspec-workflow.md`）存在以下问题：
1. **文档体系过重**：所有场景一律要求完整四文档，Bug 修复和一行改动也需要 README.md + spec.md + design.md + tasks.md，流程摩擦大
2. **spec.md 缺少权衡思考**：只有 Approach（选了什么方案），没有 Alternatives（否决了什么方案）和 Drawbacks（方案有什么缺点），导致 AI Agent 盲目实施
3. **design.md 决策记录无结构**：Architecture Decisions 是自由文本，缺乏 ADR 的 Y-Statement 结构化模板，决策不可追溯、不可废弃
4. **tasks.md 只记录结果**：缺少实施过程中的 Action-Observation-Adapt 日志，失败原因和调整策略无法沉淀
5. **检查点粒度粗**：检查点2（用户审核实施结果）是阶段级审查，无法在单个任务级别接受/拒绝变更
6. **与内置 /spec 命令割裂**：OpenSpec 用 `docs/specs/` 目录，内置 /spec 用 `.trae/specs/` 目录，两套体系并存导致混乱

## What Changes

- **引入三级文档规模**：根据任务复杂度选择 Full（四文档）/ Standard（三文档）/ Minimal（两文档），替代当前"一律四文档"
- **spec.md 增加 RFC 要素**：新增 Alternatives Considered、Drawbacks、Prior Art 三个必填章节
- **design.md 引入 ADR 模板**：Architecture Decisions 改用 Y-Statement 结构化模板，支持废弃链
- **tasks.md 增加 AOAdapt 日志**：每个任务可记录 Action/Observation/Adapt，沉淀实施过程知识
- **检查点2 细化**：支持任务级别的 Diff 审查模式（可选），用户可接受/拒绝单个任务变更
- **统一文档目录**：将 OpenSpec 文档目录从 `docs/specs/` 迁移到 `.trae/specs/`，与内置 /spec 命令统一

## Impact

- Affected specs: `docs/project-rules/openspec-workflow.md`（重写）、AGENTS.md 中 OpenSpec 章节（同步更新）
- Affected code: 无代码变更
- Affected docs: 现有 `docs/specs/` 下的功能文档需迁移到 `.trae/specs/`

## ADDED Requirements

### Requirement: 三级文档规模

AI Agent 根据任务复杂度自动选择文档规模，无需用户手动指定：

| 级别 | 适用场景 | 必须文档 | 可选文档 |
|------|---------|---------|---------|
| **Full** | 新功能、架构重构、跨模块变更 | README.md + spec.md + design.md + tasks.md | checklist.md |
| **Standard** | 功能优化、Bug 修复（涉及多文件） | spec.md + design.md + tasks.md | checklist.md |
| **Minimal** | 单文件修复、配置调整、文档更新 | spec.md + tasks.md | - |

#### Scenario: 新功能开发 → Full 级别
- **WHEN** 用户请求新增功能或跨模块变更
- **THEN** AI Agent 生成 Full 级别四文档，包含完整的 Intent/Scope/Alternatives/Drawbacks

#### Scenario: Bug 修复涉及多文件 → Standard 级别
- **WHEN** 用户报告 Bug 且修复涉及 2+ 文件
- **THEN** AI Agent 生成 Standard 级别三文档，spec.md 可精简但必须包含 Intent 和 Scope

#### Scenario: 单文件修复 → Minimal 级别
- **WHEN** 用户请求修复单文件 Bug 或调整配置
- **THEN** AI Agent 生成 Minimal 级别两文档，spec.md 仅需 Intent + Scope + Requirements

#### Scenario: AI Agent 误判级别
- **WHEN** AI Agent 选择 Minimal 级别但实施中发现涉及多文件
- **THEN** AI Agent 必须升级到 Standard 级别，补充 design.md，并通知用户

### Requirement: spec.md 增加 RFC 要素

spec.md 的 Approach 章节扩展为以下结构：

```markdown
## Approach
### Selected Approach
[选定的技术方案及理由]

### Alternatives Considered
| 方案 | 否决理由 |
|------|---------|
| 方案A | [为什么不用] |
| 方案B | [为什么不用] |

### Drawbacks
[选定方案的已知缺点和接受理由]

### Prior Art
[类似工作的参考，避免重复造轮子]
```

#### Scenario: AI Agent 编写 spec.md
- **WHEN** AI Agent 生成 spec.md
- **THEN** Approach 章节必须包含 Selected Approach、Alternatives Considered、Drawbacks 三个子章节

#### Scenario: 无替代方案
- **WHEN** 确实只有一个可行方案
- **THEN** Alternatives Considered 写"无可行替代方案"并说明原因，不得省略该章节

### Requirement: design.md 引入 ADR 模板

design.md 的 Architecture Decisions 改用 Y-Statement 结构化模板：

```markdown
## Architecture Decisions

### AD-01: [决策标题]
- **Context**: [决策背景和约束]
- **Concern**: [面临的问题]
- **Decision**: [做出的决策]
- **Goal**: [期望达到的目标]
- **Tradeoff**: [接受的权衡]
- **Status**: Proposed / Accepted / Deprecated
- **Superseded-by**: AD-XX（如适用）
```

#### Scenario: 新增架构决策
- **WHEN** AI Agent 在设计阶段做出架构决策
- **THEN** 必须用 AD-XX 编号和 Y-Statement 模板记录

#### Scenario: 废弃已有决策
- **WHEN** 新决策替代旧决策
- **THEN** 旧决策 Status 改为 Deprecated，Superseded-by 指向新决策编号；新决策记录完整 Y-Statement

#### Scenario: Minimal 级别无 design.md
- **WHEN** 任务为 Minimal 级别（无 design.md）
- **THEN** 架构决策记录在 spec.md 的 Approach.Selected Approach 中

### Requirement: tasks.md 增加 AOAdapt 日志

tasks.md 的任务格式扩展，支持可选的 Action-Observation-Adapt 日志：

```markdown
- [ ] 2.1 实现 XXX
  - Action: [执行了什么操作]
  - Observation: [观察到了什么结果]
  - Adapt: [基于观察做了什么调整]
```

#### Scenario: 任务顺利完成
- **WHEN** 任务按预期完成，无需调整
- **THEN** AOAdapt 日志可省略，直接标记完成

#### Scenario: 任务实施中发现问题
- **WHEN** 任务实施过程中发现需要调整方案
- **THEN** 必须记录 AOAdapt 日志，说明观察到的偏差和调整策略

#### Scenario: 任务失败需回退
- **WHEN** 任务实施失败，需要回退到之前状态
- **THEN** 记录 AOAdapt 日志（Observation 记录失败原因），标记任务为 ❌ 并说明回退计划

### Requirement: 统一文档目录到 .trae/specs/

将 OpenSpec 文档目录统一到 `.trae/specs/`，与内置 /spec 命令使用同一目录：

| 变更 | 旧路径 | 新路径 |
|------|--------|--------|
| 功能文档目录 | `docs/specs/{功能名称}/` | `.trae/specs/{change-id}/` |
| INDEX.md | `docs/INDEX.md` | 保持不变（INDEX.md 仍作为全局文档索引） |

#### Scenario: AI Agent 生成 OpenSpec 文档
- **WHEN** AI Agent 需要生成 OpenSpec 文档
- **THEN** 文档放在 `.trae/specs/{change-id}/` 目录下

#### Scenario: 现有 docs/specs/ 下的文档
- **WHEN** 已有功能文档在 `docs/specs/` 下
- **THEN** 保持原位不迁移（历史文档不动），新文档统一使用 `.trae/specs/`

### Requirement: 检查点2 支持任务级审查

检查点2（用户审核实施结果）增加可选的细粒度审查模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **阶段审查**（默认） | 每个阶段完成后审查 | Full/Standard 级别 |
| **任务审查**（可选） | 每个任务完成后展示 Diff | 涉及核心模块变更 |

#### Scenario: 默认阶段审查
- **WHEN** AI Agent 完成一个阶段的所有任务
- **THEN** 汇报阶段完成情况，等待用户审核

#### Scenario: 用户请求任务级审查
- **WHEN** 用户要求对每个任务进行审查
- **THEN** AI Agent 每完成一个任务后展示变更 Diff，等待用户确认

## MODIFIED Requirements

### Requirement: 强制检查点（原版优化）

原版三个检查点保留，但增加灵活性：

| 检查点 | 时机 | 行为 | 可跳过条件 |
|--------|------|------|-----------|
| **检查点 1** | 文档生成后 | 停下来等待用户审查设计方案 | **不可跳过** |
| **检查点 2** | 阶段/任务完成后 | 停下来等待用户审核实施结果 | Minimal 级别可合并到检查点3 |
| **检查点 3** | 所有任务完成后 | 停下来等待用户最终验收 | **不可跳过** |

#### Scenario: Minimal 级别的检查点
- **WHEN** 任务为 Minimal 级别
- **THEN** 检查点2 可合并到检查点3，减少交互次数

## REMOVED Requirements

### Requirement: 所有场景一律要求完整四文档
**Reason**: 流程摩擦大，小变更也需要四文档导致 AI Agent 和用户都不愿意走流程
**Migration**: 替换为三级文档规模，根据任务复杂度自动选择
