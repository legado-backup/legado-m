# Spec: 项目记忆机制改造

## Intent（意图）

解决当前 TRAE IDE 项目记忆机制的三大核心痛点：
1. **路径权限受限**：官方位置在 C 盘 `~/.trae-cn/memory/`，AI 的 Edit/Write 工具因工作区限制无法直接编辑，只能用 Grep/LS 读取
2. **多任务并发冲突**：多个对话窗口共享 `project_memory.md`，写入时互相覆盖（铁证：用户 2026-07-26 反馈"防止多任务并发的时候出现冲突"）
3. **AI 无状态感知**：无法直接获取当前对话 session_id，导致压缩恢复时难以区分新旧对话

## Scope（范围）

### 做什么
- 设计双轨制存储架构：官方位置（轻量索引）+ 项目目录（重量主记忆）
- 设计对话级唯一 ID 机制（conv-{YYYYMMDDHHmmss}-{6位hex}）
- 设计独立对话记忆文件 `conv_memory_{conv_id}.md`
- 审查现有规范合理性（路径硬编码/五件套/反馈持久化）
- 设计迁移方案与兼容策略

### 不做什么
- 不实施代码改造（用户明确要求"不要实施要整体规划"）
- 不修改 TRAE IDE 系统行为（仅改造 AI 使用记忆的方式）
- 不迁移 user_profile.md（全局记忆保留官方位置，跨项目共享）
- 不破坏现有归档机制（archived_feedback/ 保留）

## Approach（技术方案）

### Selected Approach: 双轨制存储 + 对话级 ID 隔离

**核心思路**：
1. **官方位置保留为索引**：`~/.trae-cn/memory/projects/{key}/project_memory.md` 瘦身为"系统注入索引"
   - 内容：Hard Constraints + 活跃对话索引（对话ID + 任务摘要 + 启动时间）
   - 作用：保留 TRAE IDE 系统自动注入 memory context 能力
   - 写入策略：仅追加对话索引行（Edit 风险低，PowerShell 间接写入）

2. **项目目录主记忆**：`.trae/memory/projects/{key}/` 作为重量主记忆
   - `project_memory_main.md`：主记忆（替代原 project_memory.md 的详细内容）
   - `{YYYYMMDD}/conv_memory_{conv_id}.md`：对话级独立记忆文件
   - 写入策略：每个对话只 Edit 自己的 conv_memory 文件（避免并发冲突）

3. **对话 ID 机制**：
   - 格式：`conv-{YYYYMMDDHHmmss}-{6位hex}`（如 `conv-20260726102518-d4a5b0`）
   - 生成时机：对话开始时（压缩恢复读取后，无对话ID则生成新ID）
   - 同一对话保持一致：依赖对话历史上下文（AI 能看到自己之前生成的ID）

### Alternatives Considered（替代方案）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 方案B：完全迁移到项目目录 | 放弃 C 盘官方位置，全部记忆放 `.trae/memory/` | 丢失系统自动注入能力，TRAE IDE 不识别项目目录记忆文件 |
| 方案C：保持官方位置 + PowerShell 增强 | 用 RunCommand + PowerShell 间接编辑 C 盘文件 | 操作繁琐，仍有并发冲突，未解决核心痛点 |
| 方案D：仅添加对话 ID（不改路径） | 保持 C 盘位置，仅引入对话 ID 机制 | 未解决 Edit/Write 工具权限问题，写入仍依赖 PowerShell |
| 方案E：双轨制 + 实时同步 | 双轨制基础上增加双向同步 | 复杂度过高，同步逻辑易出错，收益不明确 |

### Drawbacks（已知缺点）

1. **双轨制维护成本**：需维护官方位置索引 + 项目目录主记忆两份数据
   - 接受理由：兼顾系统注入能力和工作区编辑权限的最优解

2. **对话 ID 生成不完美**：AI 无状态，跨多次调用依赖对话历史保持一致
   - 接受理由：同一对话内通过历史保持一致已足够实用；压缩恢复时通过"当前任务状态"字段传递

3. **系统注入可能不一致**：TRAE IDE 注入的 memory context（官方位置）与项目目录主记忆可能不同步
   - 接受理由：主记忆以项目目录为准，系统注入仅作辅助参考；AI 主动读取项目目录

4. **迁移期数据同步**：从旧机制迁移到新机制需一次性同步
   - 接受理由：迁移完成后正常运行，一次性成本可接受

### Prior Art（参考）
- TRAE IDE 官方文档：https://docs.trae.cn/ide_memories
- 现有规范：`~/.trae-cn/user_rules/context-recovery.md`、`core-spec.md`
- 项目记忆目录：`~/.trae-cn/memory/projects/-f-myself-github-WeAgentChat-temp-legado/`

## Requirements（需求）

### 功能性需求
- **R1 路径迁移**：项目目录下创建 `.trae/memory/projects/{key}/` 主记忆目录
- **R2 对话 ID 生成**：AI 在对话开始时生成唯一对话 ID（格式 `conv-{YYYYMMDDHHmmss}-{6位hex}`）
- **R3 对话级独立文件**：每个对话独立 `conv_memory_{conv_id}.md` 文件
- **R4 官方索引同步**：官方位置 project_memory.md 保留为索引（Hard Constraints + 活跃对话索引）
- **R5 压缩恢复流程更新**：五件套并行读取新增"项目目录主记忆"读取
- **R6 用户反馈持久化**：写入对话级文件，按时间倒序
- **R7 旧记忆归档**：迁移时旧 project_memory.md 内容归档到 `archived/legacy_{YYYYMMDD}.md`

### 非功能性需求
- **NR1 兼容性**：不破坏现有 archived_feedback/ 归档机制
- **NR2 最小破坏**：user_profile.md 保留官方位置（跨项目共享）
- **NR3 可回滚**：迁移失败可回滚到官方位置单轨制
- **NR4 工具友好**：所有记忆文件用 Edit/Write 直接可编辑（在工作区内）

## Scenarios（场景）

### 场景1：新对话启动
- AI 读取官方位置索引 → 获取活跃对话列表
- AI 读取"当前任务状态"字段 → 确认是否有进行中对话
- 若为新对话 → 生成新 conv_id → 创建 `conv_memory_{conv_id}.md`
- 更新官方位置索引（追加对话行）

### 场景2：多任务并发
- 对话A 和对话B 同时启动
- 各自生成独立 conv_id（基于时间戳+随机）
- 各自只 Edit 自己的 conv_memory 文件
- 主 project_memory_main.md 通过"活跃对话索引"协调
- 不互相覆盖

### 场景3：压缩恢复
- AI 并行读取五件套（含项目目录主记忆）
- 读取"当前任务状态"字段中的 conv_id
- 读取对应 `conv_memory_{conv_id}.md`
- 对比用户最新消息 → 判断续接或新对话

### 场景4：用户反馈持久化
- AskUserQuestion 响应后
- 写入对话级 `conv_memory_{conv_id}.md`（按时间倒序）
- 同步更新官方位置索引的"活跃对话索引"行

### 场景5：对话完成归档
- 对话完成 → conv_memory 文件移至 `archived/conv_{conv_id}.md`
- 官方位置索引移除对应行
