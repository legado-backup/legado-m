# spec.md - 全局规范重组

## Intent

解决 spec-system-optimization 任务的"虚假完成"问题：创建了 core-spec.md（V2.1，583行/27.9KB）但未验证系统注入机制，导致该文件因太大被系统省略，V2.1 规范从未生效。

同时解决用户反馈的三个核心问题：
1. AGENTS.md 通用内容应迁移到全局规范（不应放在项目主规范中）
2. AskUserQuestion 规则跨项目失效（AI在其他项目不主动使用AskUserQuestion）
3. 违禁词规避规范不够明确，又遇到问题

## Scope

### 做什么
- S1：确认系统注入机制（✅ 已完成）
- S2：重组全局规范（多文件拆分策略，参考 rule-1782963384927.md 模式）
- S3：迁移 AGENTS.md 通用内容到独立全局文件
- S4：AGENTS.md 瘦身（只保留项目特定内容）
- S5：强化违禁词规避规范（明确范围+处理方式+正向反例）
- S6：子代理验证策略（不需要新对话）

### 不做什么
- 不修改项目特定的 AGENTS.md 内容（视频播放器/书源/ai_tests等）
- 不修改 Skill 文件
- 不修改 ai_tests 文件

### 影响模块
- `~/.trae-cn/user_rules/` 目录（全局规范）
- `f:\myself\github\WeAgentChat\temp\legado\AGENTS.md`（项目主规范）

## Approach

### Selected Approach：多文件拆分策略

**核心原则**：每个规则独立成文件，参考 rule-1782963384927.md 的模式（核心原则+正向示例+反例+禁止行为+检查清单），文件控制在 ≤3KB，确保被系统注入。

**系统注入机制研究发现**：
1. 系统自动注入 `~/.trae-cn/user_rules/` 目录的 .md 文件
2. 注入顺序 = 修改时间从旧到新
3. 大小限制约 10-15KB（被注入10.5KB，被省略30.2KB）
4. 子代理与主代理规则加载完全相同（可通过子代理验证）

**文件结构（11个文件）**：

| 文件 | 操作 | 大小目标 | 内容 |
|------|------|---------|------|
| user_rules.md | 保留 | 2.3KB | 基础规则 |
| danger-ops.md | 保留 | 1.3KB | 危险操作规则 |
| rule-1782963384927.md | 保留 | 9.2KB | AskUserQuestion规范 |
| core-spec.md | 备份后删除重建 | ≤2KB | 仅索引 |
| context-recovery.md | 新建 | ≤3KB | 上下文压缩恢复 |
| output-safety.md | 新建 | ≤3KB | 输出安全/违禁词（强化版） |
| coding-philosophy.md | 新建 | ≤3KB | 编码哲学 |
| openspec-workflow.md | 新建（从AGENTS.md迁移） | ≤3KB | OpenSpec工作流 |
| complex-task.md | 新建（从AGENTS.md迁移） | ≤3KB | 复杂任务处理 |
| concurrent-editing.md | 新建（从AGENTS.md迁移） | ≤3KB | 并发文件修改 |
| budget-management.md | 新建（从AGENTS.md迁移） | ≤3KB | 输出预算管理 |

**文件内容设计原则**：
1. 参考 rule-1782963384927.md 的结构（核心原则+必须执行场景+错误做法vs正确做法+禁止行为+检查清单）
2. **去掉元信息**（版本号、变更记录、铁证、"最后更新"等）——这些对AI加载无帮助，反而让AI懵逼
3. 精简无冗余，只保留规则和示例
4. 每个文件 ≤3KB

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| 整合策略（spec-system-optimization 的做法） | core-spec.md 583行/27.9KB 被系统省略，V2.1 规范从未生效 |
| 双轨保障（系统注入+文件驱动） | 系统确实注入文件，不需要双轨；只需解决大小限制问题 |
| 精简 core-spec.md 到 ≤200行 | 仍然是大文件策略；用户反馈应拆分多个小文件 |
| 保守精简（不创建新文件） | 无法迁移 AGENTS.md 通用内容；无法解决 AskUserQuestion 跨项目失效 |

### Drawbacks

1. 文件数量增加（11个文件），管理复杂度增加
2. 系统注入限制确切阈值未知，可能部分文件仍被省略（通过子代理验证调整）
3. 需要维护文件间引用关系（core-spec.md 作为索引）
4. 最新修改的文件最可能被省略（注入顺序=修改时间从旧到新）

## Requirements

### R1：系统注入机制确认（✅ 已完成）
- 系统确实注入 `~/.trae-cn/user_rules/` 目录的 .md 文件
- 注入顺序 = 修改时间从旧到新
- 大小限制约 10-15KB
- 子代理与主代理规则加载完全相同

### R2：多文件拆分
- 每个规则独立成文件
- 每个文件 ≤3KB
- 参考 rule-1782963384927.md 的结构
- 去掉元信息（版本号、变更记录、铁证等）

### R3：AGENTS.md 通用内容迁移
- V2.1 硬约束 → complex-task.md
- 复杂任务五阶段 → complex-task.md
- 输出预算管理 → budget-management.md
- OpenSpec 工作流 → openspec-workflow.md
- 并发文件修改 → concurrent-editing.md

### R4：AGENTS.md 瘦身
- 只保留项目特定内容
- 通用内容用引用指向全局文件

### R5：违禁词规范强化
- 明确违禁词范围（成人/违法/政治敏感/暴力/视频网站等）
- 明确处理方式（代号替代/路径模式化/技术分析优先）
- 提供正向和反例
- 强化"不能因违禁词中断对话"
- **思考过程也不能有违禁词**（2026-07-13铁证）

### R6：子代理验证
- 每创建一批文件后，启动子代理验证注入状态
- 根据验证结果调整文件大小和数量

## Scenarios

### 场景1：正常流程
1. 备份 core-spec.md → .zip
2. 删除 core-spec.md（释放27.9KB空间）
3. 创建拆分文件（context-recovery/output-safety/coding-philosophy）
4. 启动子代理验证注入状态
5. 迁移 AGENTS.md 通用内容到独立文件
6. AGENTS.md 瘦身
7. 子代理最终验证

### 场景2：文件被省略
- 子代理验证发现某文件被省略
- 精简该文件内容（去掉冗余示例/说明）
- 重新验证

### 场景3：违禁词触发
- AI 输出或思考过程触发违禁词
- 按 output-safety.md 规范处理
- 不中断对话，自动恢复
- 后续输出加强过滤

### 场景4：注入顺序问题
- 新创建的文件修改时间最新，排在注入顺序最后
- 可能被省略
- 解决方案：控制总大小在限制内，确保所有文件被注入
