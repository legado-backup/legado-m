# Spec: Skill 三件套使用者体验优化方案

---

## Intent（意图）

从使用者（AI agent / 人类用户）角度系统性优化三个 legado skill 的上手成本、执行效率、可靠性，解决上下文膨胀、流程过度设计、功能边界模糊、工具选择困难、basic-memory 单点故障、协作链路理想化等系统性痛点。

**核心原则**：
- **使用者优先**：优化以使用者体验为准，非技术完整性
- **简化优于完整**：宁可少做，不可做乱
- **已实现为准**：只描述已实现功能，移除"设计中"内容
- **独立可用**：每个 skill 应能独立工作，不强依赖外部服务

---

## Scope（范围）

### 涉及的三个 skill

| Skill | SKILL.md 行数 | 核心问题 |
|-------|-------------|---------|
| legado-source-creator | 514 行 | 上下文膨胀、流程过度设计、功能边界模糊 |
| legado-workflow-auditor | 153 行 | 功能单薄、完全依赖 basic-memory、无独立价值 |
| legado-skill-auditor | 1257 行 | 审查框架过于复杂、只审查 source-creator、修复能力名不副实 |

### 不涉及的范围

- JAR 仿真服务端保真度提升（由 `legado-skill-optimization` 负责）
- Python 客户端工程化（由 `legado-skill-optimization` 负责）
- 新功能开发（本方案只优化现有功能的使用体验）
- references/ 知识库内容更新（由 `legado-skill-auditor` 审查时处理）

---

## Approach（方法）

### 方法 1：精简文档结构

将 SKILL.md 从"全量知识库"转变为"决策入口"，详细内容下沉到 references/。

**原则**：
- SKILL.md 只保留：触发条件、核心流程、关键决策点、快速参考表
- 详细解释、完整列表、代码示例全部下沉到 references/
- AI agent 按需读取 references/，而非一次性加载

### 方法 2：分级工作流

为不同复杂度的场景提供不同级别的工作流。

**原则**：
- 快速路径：简单场景（普通 CMS / 静态 HTML）2 步完成
- 标准路径：中等复杂度场景走精简 5 阶段
- 完整路径：复杂场景（CF/登录/加密）走完整 5 阶段
- AI 根据网站特征自动选择路径

### 方法 3：统一降级策略

三个 skill 采用统一的 basic-memory 降级路径。

**原则**：
- 检测不可用 → 明确告知功能边界 → 提供替代方案 → 标记待验证
- 降级时每个 skill 都能独立工作
- 降级状态在输出中明确标注

### 方法 4：功能边界明确化

移除所有"实现状态：设计中/部分实现"标记。

**原则**：
- 只描述已实现的功能
- 未实现的功能不写入 SKILL.md
- 如需记录未实现功能，放入单独的"路线图"文档

---

## Requirements（需求）

### REQ-1：SKILL.md 精简（方向 1）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-1.1 | source-creator SKILL.md ≤ 300 行 | 行数统计 ≤ 300 |
| REQ-1.2 | skill-auditor SKILL.md ≤ 500 行 | 行数统计 ≤ 500 |
| REQ-1.3 | workflow-auditor SKILL.md ≤ 120 行 | 行数统计 ≤ 120 |
| REQ-1.4 | SKILL.md 中无"实现状态：设计中"标记 | Grep 搜索结果为 0 |
| REQ-1.5 | SKILL.md 中无"实现状态：部分实现"标记 | Grep 搜索结果为 0 |
| REQ-1.6 | 详细内容下沉到 references/，SKILL.md 只保留决策入口 | 结构审查通过 |

### REQ-2：分级工作流（方向 2）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-2.1 | source-creator 支持快速路径（简单场景 2 步） | 文档中有快速路径描述 |
| REQ-2.2 | 快速路径触发条件明确（CMS/静态HTML/无JS） | 有明确的判断标准 |
| REQ-2.3 | 快速路径跳过 Phase 1/4/5，只执行分析+测试 | 流程描述清晰 |
| REQ-2.4 | AI 能根据网站特征自动选择路径 | 决策树清晰 |

### REQ-3：统一降级策略（方向 3）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-3.1 | 三个 skill 采用统一的 basic-memory 降级路径格式 | 格式一致 |
| REQ-3.2 | 降级路径包含：检测→告知→替代→标记 四步 | 四步完整 |
| REQ-3.3 | 降级时每个 skill 能独立工作（不崩溃） | 功能可用 |
| REQ-3.4 | 降级状态在输出中明确标注 | 标注存在 |

### REQ-4：功能边界明确化（方向 4）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-4.1 | 移除 source-creator 中所有"设计中"功能描述 | Grep 为 0 |
| REQ-4.2 | 移除 source-creator 中所有"部分实现"功能描述 | Grep 为 0 |
| REQ-4.3 | 未实现功能记录到单独的路线图文档（如有必要） | 路线图文档存在或确认不需要 |
| REQ-4.4 | 辅助工具列表只保留已实现且可用的工具 | 工具列表与代码一致 |

### REQ-5：简化工具选择（方向 5）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-5.1 | source-creator 测试脚本推荐从 7 个简化为 2 个核心脚本 | 核心脚本 ≤ 2 |
| REQ-5.2 | 2 个核心脚本为：debug-source.py（端到端）+ verify-source.py（完整性） | 明确指定 |
| REQ-5.3 | 其他脚本标记为"高级/可选"，不在主流程推荐 | 分级清晰 |
| REQ-5.4 | skill-auditor 42 检查点分级为：核心 10 项 + 标准 15 项 + 深度 17 项 | 分级明确 |
| REQ-5.5 | 默认执行核心 10 项，用户可显式要求标准/深度 | 默认行为明确 |

### REQ-6：扩展 skill-auditor 审查范围（方向 6）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-6.1 | skill-auditor 审查范围扩展到三个 skill | 审查范围包含三个 |
| REQ-6.2 | 新增 workflow-auditor 审查维度（功能完整性/独立性/降级能力） | 维度存在 |
| REQ-6.3 | 新增 skill-auditor 自身审查维度（框架复杂度/执行成本/修复有效性） | 维度存在 |

### REQ-7：增强 workflow-auditor 独立价值（方向 7）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-7.1 | workflow-auditor 增加实际验证能力（执行 verify-source.py） | 验证步骤存在 |
| REQ-7.2 | workflow-auditor 减少 basic-memory 依赖（8 项中至少 3 项不依赖） | 依赖项 ≤ 5 |
| REQ-7.3 | workflow-auditor 审计报告增加错误原因分析 | 报告格式包含 |
| REQ-7.4 | workflow-auditor 审计报告增加修复建议 | 报告格式包含 |

### REQ-8：统一触发词和上下文传递（方向 8）

| ID | 需求 | 验证标准 |
|----|------|---------|
| REQ-8.1 | 简化触发词表，消除歧义 | 无歧义触发词 |
| REQ-8.2 | 提供上下文传递标准模板 | 模板存在 |
| REQ-8.3 | 上下文传递模板包含必填字段和可选字段 | 字段分级明确 |
| REQ-8.4 | 三个 skill 的触发词在 AGENTS.md 中统一管理 | AGENTS.md 一致 |

---

## Scenarios（场景）

### 场景 1：AI agent 创建简单 CMS 书源（快速路径）

**前提**：用户要求将一个 WordPress 网站做成书源

**当前流程**（5 阶段，过度设计）：
1. Phase 1：搜索 basic-memory（无命中）
2. Phase 2：查阅 references/ + 构建规则 + 预校验
3. Phase 3：运行测试脚本
4. Phase 4：（跳过，测试通过）
5. Phase 5：经验反哺

**优化后流程**（快速路径，2 步）：
1. 检测到 WordPress CMS → 直接使用 cms-samples 选择器 → 构建规则 → 运行 verify-source.py
2. 输出 JSON + 标注可信度

**验证**：WordPress 网站从输入到输出 ≤ 2 步

### 场景 2：basic-memory 不可用时创建书源

**前提**：basic-memory MCP 服务不可用

**当前行为**：
- source-creator Phase 1 降级到 Grep references/（效率低）
- workflow-auditor 8 项检查中 7 项失效
- skill-auditor E 维度完全跳过

**优化后行为**：
- source-creator Phase 1 跳过经验搜索，直接进入 Phase 2（标注"无经验参考"）
- workflow-auditor 切换到降级模式（检查 output 目录 + 执行 verify-source.py）
- skill-auditor E 维度跳过，标注"需 basic-memory 验证"
- 所有 skill 输出中标注"basic-memory 降级模式"

**验证**：basic-memory 不可用时，三个 skill 都能独立工作

### 场景 3：AI agent 执行 skill-auditor 审查

**前提**：用户要求"审查 skill"

**当前行为**：
- AI 读取 1257 行 SKILL.md（上下文消耗严重）
- 尝试执行 42 个检查点（经常只执行部分）
- 审查范围只覆盖 source-creator

**优化后行为**：
- AI 读取 ≤ 500 行 SKILL.md
- 默认执行核心 10 项检查（5 分钟完成）
- 用户可显式要求"标准审查"（15 项）或"深度审查"（17 项）
- 审查范围覆盖三个 skill

**验证**：核心审查 ≤ 5 分钟完成，覆盖三个 skill

### 场景 4：三个 skill 协作（简化上下文传递）

**前提**：source-creator 任务完成后调用 workflow-auditor

**当前行为**：
- 需要传递 source_name/source_type/task_type/phases_completed/execution_logs
- AI 经常遗漏字段，导致审计失败

**优化后行为**：
- 上下文传递模板：必填 source_name + source_type，可选 phases_completed
- workflow-auditor 自动从 output/ 目录推断缺失信息
- 降级时标注数据来源

**验证**：上下文传递字段从 5 个简化为 2 个必填 + 1 个可选

### 场景 5：用户触发词歧义

**前提**：用户说"审计一下"

**当前行为**：
- AI 需要判断"审计"是指 workflow-auditor（任务执行）还是 skill-auditor（skill 本身）
- 优先级表复杂，AI 容易混淆

**优化后行为**：
- "审计"默认指 workflow-auditor（任务执行证据）
- "审查 skill"明确指 skill-auditor
- 触发词表简化为 3 个核心词 + 2 个限定词

**验证**：触发词表从 12 个简化为 5 个
