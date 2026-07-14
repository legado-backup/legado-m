# design.md - 全局规范重组

## Technical Approach

### 系统注入机制研究发现

通过对比 system-reminder 中 `<user_rules>` 标签内容与 user_rules/ 目录文件：

1. **系统自动注入** `~/.trae-cn/user_rules/` 目录的 .md 文件
2. **注入顺序** = 修改时间从旧到新（rule-1782963384927.md 7/11 → danger-ops.md 7/12 18:34 → user_rules.md 7/12 19:24 → core-spec.md 7/12 19:24）
3. **大小限制** 约 10-15KB（被注入10.5KB，被省略30.2KB，`[user rules omitted due to size limit]`）
4. **子代理与主代理规则加载完全相同**（通过子代理验证确认）

### 多文件拆分策略

**核心原则**：每个规则独立成文件，参考 rule-1782963384927.md 的模式，文件控制在 ≤3KB。

**文件内容设计模板**（参考 rule-1782963384927.md）：
1. 核心原则（1-2句）
2. 必须执行的场景（表格/列表）
3. 错误做法 vs 正确做法（反例 vs 正例）
4. 禁止行为（列表）
5. 检查清单（可选）

**去掉的元信息**：
- 版本号（V2.1等）
- 变更记录表
- "最后更新"日期
- "铁证"（给用户看的历史教训，对AI无帮助）
- "为什么需要这条规则"的解释（AI只需知道怎么做）

## Architecture Decisions

### AD-01：多文件拆分策略（取代整合策略）
- **Context**: spec-system-optimization 将8个碎片文件整合到 core-spec.md（583行/27.9KB），但被系统省略
- **Concern**: core-spec.md 太大被系统省略，V2.1 规范从未生效
- **Decision**: 采用多文件拆分策略，每个规则独立成文件
- **Goal**: 确保所有规范文件被系统注入
- **Tradeoff**: 文件数量增加，管理复杂度增加
- **Status**: Accepted

### AD-02：删除 core-spec.md 重建为索引
- **Context**: core-spec.md 27.9KB 被系统省略
- **Concern**: 大文件无法被系统注入
- **Decision**: 备份后删除 core-spec.md，重建为 ≤2KB 的索引文件
- **Goal**: core-spec.md 作为索引文件，指向其他详细规范文件
- **Tradeoff**: 需要维护文件间引用关系
- **Status**: Accepted

### AD-03：文件内容去掉元信息
- **Context**: 用户反馈版本号、变更记录等元信息对AI加载无帮助
- **Concern**: 元信息占用空间，可能让AI懵逼
- **Decision**: 去掉版本号、变更记录、铁证等元信息
- **Goal**: 文件只保留规则内容和示例
- **Tradeoff**: 无法追溯变更历史（备份文件保留历史）
- **Status**: Accepted

### AD-04：子代理验证策略
- **Context**: 用户说新对话测试不现实
- **Concern**: 需要验证拆分后文件是否被注入
- **Decision**: 通过子代理验证注入状态（子代理与主代理规则加载相同）
- **Goal**: 不需要新对话即可验证
- **Tradeoff**: 子代理验证需要额外启动子代理
- **Status**: Accepted

### AD-05：违禁词规范强化
- **Context**: 用户反馈违禁词又遇到问题
- **Concern**: 违禁词规范不够明确，思考过程也会触发违禁词
- **Decision**: 在 output-safety.md 中明确违禁词范围和处理方式，包含思考过程约束
- **Goal**: AI 能正确处理违禁词，不中断对话
- **Tradeoff**: 需要更多篇幅描述违禁词规范
- **Status**: Accepted

### AD-06：AGENTS.md 通用内容迁移
- **Context**: AGENTS.md 包含大量通用内容（V2.1硬约束/复杂任务/输出预算/OpenSpec/并发修改）
- **Concern**: 通用内容应在全局规范中，不应在项目规范中
- **Decision**: 将通用内容迁移到独立全局文件
- **Goal**: AGENTS.md 只保留项目特定内容
- **Tradeoff**: 需要维护全局文件与 AGENTS.md 的引用关系
- **Status**: Accepted

## Data Flow

### 规则加载数据流
```
系统启动对话/子代理
  ↓
系统读取 ~/.trae-cn/user_rules/ 目录的 .md 文件
  ↓
按修改时间从旧到新排序
  ↓
依次注入到 <user_rules> 标签
  ↓
累计大小达到限制（约10-15KB）后，剩余文件省略
  ↓
显示 [user rules omitted due to size limit]
  ↓
AI 根据注入的规则执行
```

### 文件拆分数据流
```
1. 备份 core-spec.md → core-spec-backup-20260713.zip
2. 删除 core-spec.md（释放27.9KB空间）
3. 创建拆分文件：
   - context-recovery.md（上下文压缩恢复）
   - output-safety.md（输出安全/违禁词，强化版）
   - coding-philosophy.md（编码哲学）
4. 启动子代理验证注入状态
5. 根据验证结果调整文件大小
6. 迁移 AGENTS.md 通用内容到独立文件：
   - openspec-workflow.md
   - complex-task.md
   - concurrent-editing.md
   - budget-management.md
7. 重建 core-spec.md（≤2KB，仅索引）
8. AGENTS.md 瘦身
9. 子代理最终验证
```

## File Changes

### 全局规范文件变更（~/.trae-cn/user_rules/）

| 文件 | 操作 | 大小目标 | 内容来源 |
|------|------|---------|---------|
| user_rules.md | 保留 | 2.3KB | 基础规则（不变） |
| danger-ops.md | 保留 | 1.3KB | 危险操作规则（不变） |
| rule-1782963384927.md | 保留 | 9.2KB | AskUserQuestion规范（不变） |
| core-spec.md | 备份后删除重建 | ≤2KB | 仅索引（指向其他文件） |
| context-recovery.md | 新建 | ≤3KB | 从 core-spec.md §1 拆分 |
| output-safety.md | 新建 | ≤3KB | 从 core-spec.md §2 拆分+强化违禁词 |
| coding-philosophy.md | 新建 | ≤3KB | 从 core-spec.md §4 拆分 |
| openspec-workflow.md | 新建 | ≤3KB | 从 AGENTS.md 迁移 |
| complex-task.md | 新建 | ≤3KB | 从 AGENTS.md 迁移 |
| concurrent-editing.md | 新建 | ≤3KB | 从 AGENTS.md 迁移 |
| budget-management.md | 新建 | ≤3KB | 从 AGENTS.md 迁移 |

### 项目文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| AGENTS.md | 瘦身 | 删除通用内容（L92-181, L283-357, L493-505），保留项目特定内容 |
| docs/INDEX.md | 更新 | 更新 spec 状态 |

### AGENTS.md 迁移内容清单

| AGENTS.md 行段 | 迁移目标 | 内容 |
|---------------|---------|------|
| L92-181 | complex-task.md + budget-management.md | V2.1硬约束 + 复杂任务五阶段 + 输出预算管理 |
| L283-357 | openspec-workflow.md + context-recovery.md | OpenSpec工作流 + 上下文压缩恢复 |
| L493-505 | concurrent-editing.md | 并发文件修改规范 |
