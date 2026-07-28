# Spec: 项目记忆机制改造

> ⚠️ **重大修订说明（2026-07-27 22:51）**：用户决策废弃 conv_id 机制（原因：闭环漏洞——三对话并发压缩恢复场景无法判断当前 conv_id；AI 无状态无法可靠生成/沿用 conv_id）。简化方案：所有对话共享 ai_memory_main.md，多任务并发时 AskUserQuestion 询问用户当前窗口处理哪个任务。本文档保留原 conv_id 设计作为历史记录，但实施以简化方案为准。详见 [tasks.md](./tasks.md)。

## Intent（意图）

> 🔧 **简化方案（2026-07-27 22:51）**：用户决策废弃 conv_id 机制，痛点3 改为"多任务并发时用 AskUserQuestion 询问用户当前窗口处理哪个任务"。

解决当前 TRAE IDE 项目记忆机制的三大核心痛点：
1. **路径权限受限**：官方位置在 C 盘 `~/.trae-cn/memory/`，AI 的 Read/Edit/Write 工具因工作区限制无法直接访问（铁证：2026-07-27 实测 Read C盘 project_memory.md 报错 "File path is not within allowed workspace"，但 Read C盘 user_rules/*.md 成功——说明 memory 目录被特别禁止）
2. **多任务并发冲突**：多个对话窗口共享 `project_memory.md`，写入时互相覆盖（铁证：用户 2026-07-26 反馈"防止多任务并发的时候出现冲突"）
3. **多任务并发时当前任务识别**：AI 无状态，压缩恢复后若多个任务活跃，无法可靠判断当前窗口处理哪个任务；简化方案：用 AskUserQuestion 询问用户当前窗口处理哪个任务（废弃 conv_id 机制）

## Scope（范围）

> 🔧 **简化方案（2026-07-27 22:51）**：废弃 conv_id 机制，不做对话级 ID 生成/持久化/恢复；所有对话共享 ai_memory_main.md，靠 Edit 串行化 + old_string 匹配保证安全。

### 做什么
- 建立 AI 独立记忆系统：项目目录 `.trae/memory/` 作为 AI 完全自主管理的记忆（AD-11）
- 设计多任务并发处理机制：压缩恢复后若多个活跃任务，用 AskUserQuestion 询问用户当前窗口处理哪个（废弃 conv_id）
- 适配全局规范（6个文件追加补充）+ 项目级规范（AGENTS.md 更新）
- 设计迁移方案与兼容策略
- 纳入行业最佳实践（AD-16~AD-20）

### 不做什么
- 不修改 TRAE IDE 系统行为（仅改造 AI 使用记忆的方式）
- 不迁移 user_profile.md（全局记忆保留官方位置，跨项目共享）
- 不干预 C盘 session_memory_*.jsonl（系统自动持久化，AI 不读不写）
- 不破坏现有归档机制（archived_feedback/ 保留）
- **不实现 conv_id 机制**（用户 2026-07-27 22:51 决策废弃，原因：闭环漏洞）

## Approach（技术方案）

> 🔧 **简化方案（2026-07-27 22:51）**：本章节原"对话 ID 机制"设计已废弃（AD-02/AD-04 Deprecated）。简化方案核心：1) AI 独立记忆系统（AD-11）；2) 所有对话共享 ai_memory_main.md；3) 多任务并发时 AskUserQuestion 询问用户。下方保留原 conv_id 设计作为历史记录。

### Selected Approach: AI 独立记忆系统（AD-11）+ 多任务 AskUserQuestion 确认（简化版）

**核心思路**：
1. **完全分离原则**（AD-11）：
   - 官方记忆（C盘 `~/.trae-cn/memory/`）：TRAE IDE 系统维护，AI 不读不写不干预
   - AI 记忆（项目目录 `.trae/memory/`）：AI 完全自主管理
   - 两个系统独立运行，不试图同步、不试图替换

2. **AI 记忆存储结构**（路径简化，去掉冗余 project key）：
   ```
   .trae/memory/                              # AI 独立记忆根目录（项目目录下，Edit/Write 可用）
   ├── ai_memory_main.md                      # AI 主记忆（Hard Constraints + 当前任务状态 + 活跃对话索引）
   ├── {YYYYMMDD}/                            # 按日期组织的对话目录
   │   └── conv_memory_{conv_id}.md           # 对话级独立记忆
   └── archived/                              # 归档目录
       ├── feedback/YYYYMM.md                 # 反馈归档
       ├── main_history_{YYYYMMDD}.md         # 主记忆历史归档
       └── conv_{conv_id}.md                  # 对话归档
   ```
   
   **路径简化理由**：项目目录本身就是项目边界，不需要再用 `{项目key}` 区分。原设计 `{项目根目录}/.trae/memory/projects/{项目key}/` 中 `{项目key}` 是冗余的（用户 2026-07-27 反馈）。

3. **对话 ID 机制**（完整设计，解决一致性核心痛点）：
   - **格式**：`conv-{YYYYMMDDHHmmss}-{6位hex}`（如 `conv-20260727222000-a3b4c5`）
   - **生成时机**：对话第一次用户消息时（AI 检测到 ai_memory_main.md 无活跃对话，或活跃对话均已完成）
   - **生成方法**：`date '+%Y%m%d%H%M%S'` + `printf '%06x' $RANDOM`（gitbash 兼容）
   - **持久化机制（3处，确保可靠，不依赖对话历史）**：
     - **P1 主持久化**：`ai_memory_main.md` 的"当前活跃对话索引"字段（支持多任务并发，列表形式）
     - **P2 文件系统持久化**：`conv_memory_{conv_id}.md` 文件名（文件存在即表示对话存在）
     - **P3 自描述持久化**：`conv_memory_{conv_id}.md` 文件内首行"对话元信息"包含 conv_id
   - **AI 每次调用获取 conv_id 的流程**：
     ```
     步骤1: Read .trae/memory/ai_memory_main.md
     步骤2: 检查"当前活跃对话索引"字段
     步骤3:
       - 若有1个活跃对话 → 沿用该 conv_id
       - 若有多个活跃对话 → 对比用户消息与各"任务摘要"，匹配度最高的即为当前对话
       - 若无活跃对话 → 生成新 conv_id，追加到索引
     步骤4: 操作对应的 conv_memory_{conv_id}.md
     ```
   - **压缩恢复时获取 conv_id**（不依赖对话历史，从文件恢复）：
     ```
     步骤1: Read .trae/memory/ai_memory_main.md（P1 权威源）
     步骤2: 提取"当前活跃对话索引"
     步骤3:
       - 若有1个活跃对话 → 该 conv_id 即为当前对话
       - 若有多个活跃对话 → 询问用户确认当前对话
       - 若无活跃对话 → 可能是新对话或异常，AskUserQuestion 确认
     步骤4: Read conv_memory_{conv_id}.md（P2 详细状态）
     步骤5: 对比用户最新消息与"当前任务状态"：
       - 若匹配 → 续接，沿用 conv_id
       - 若不匹配 → AskUserQuestion 确认（旧消息 or 新任务）
     ```
   - **多任务并发**：
     - "当前活跃对话索引"支持多个（列表形式），每个对话追加自己的条目
     - 写入策略：用 Edit 在索引末尾追加新条目（不覆盖已有内容）
     - 冲突规避：基于时间戳+随机hex，conv_id 几乎不会冲突
   - **对话结束**：
     - 将该对话在"当前活跃对话索引"中的状态改为"已完成"
     - 归档 conv_memory_{conv_id}.md 到 archived/conv/

### Alternatives Considered（替代方案）

| 方案 | 描述 | 否决理由 |
|------|------|---------|
| 方案A：双轨制存储 | 官方位置保留为索引 + 项目目录主记忆 | 维护成本高，需同步两份数据；用户已否定（AD-11 替代 AD-01/AD-03/AD-10） |
| 方案C：保持官方位置 + PowerShell 增强 | 用 RunCommand + PowerShell 间接编辑 C 盘文件 | 操作繁琐，仍有并发冲突，未解决核心痛点；且 C盘 memory 目录 Read 都受限，PowerShell 写入可靠性存疑 |
| 方案D：仅添加对话 ID（不改路径） | 保持 C 盘位置，仅引入对话 ID 机制 | 未解决 Edit/Write 工具权限问题（铁证：Read C盘 project_memory.md 报错） |
| 方案E：双轨制 + 实时同步 | 双轨制基础上增加双向同步 | 复杂度过高，同步逻辑易出错，收益不明确 |

### Drawbacks（已知缺点）

1. **丢失系统自动注入能力**：TRAE IDE 系统注入的 memory context（C盘）与项目目录主记忆不同步
   - 接受理由：用户明确表态"官方记官方的，我们自己记录我们的就好"（AD-11）；AI 主动读取项目目录 ai_memory_main.md 作为 P1 权威源补偿

2. **对话 ID 依赖文件持久化**：conv_id 不再依赖对话历史，但依赖 ai_memory_main.md 文件存在
   - 接受理由：ai_memory_main.md 在项目目录内，Edit/Write 可用；文件损坏风险通过 .bak 备份缓解

3. **多任务并发时索引写入冲突**：多个对话同时追加"当前活跃对话索引"可能冲突
   - 接受理由：Edit 工具基于 old_string 匹配，并发时可能失败重试；冲突概率低（时间戳+随机hex）；最坏情况是索引丢失，conv_memory 文件仍存在可恢复

4. **迁移期数据同步**：从旧机制迁移到新机制需一次性同步
   - 接受理由：迁移完成后正常运行，一次性成本可接受；C盘 project_memory.md 用 Grep 分段读取（Read 受限）

### Prior Art（参考）
- TRAE IDE 官方文档：https://docs.trae.cn/ide_memories
- 现有规范：`~/.trae-cn/user_rules/context-recovery.md`、`core-spec.md`
- 行业最佳实践：Claude Code（5层架构+4类分类+Auto Dream）/ Cursor（Rules+Memories双轨制）/ Cline（Memory Bank三层架构）
- 详细对比：[industry-best-practices.md](./industry-best-practices.md)

## Requirements（需求）

### 功能性需求
- **R1 路径建立**：项目目录下创建 `.trae/memory/` 主记忆目录（简化路径，无 project key 层级）
- **R2 对话 ID 生成**：AI 在对话开始时生成唯一对话 ID（格式 `conv-{YYYYMMDDHHmmss}-{6位hex}`），通过 `date '+%Y%m%d%H%M%S'` + `printf '%06x' $RANDOM` 生成
- **R3 对话 ID 持久化**：conv_id 持久化到3处（ai_memory_main.md 索引 + conv_memory 文件名 + conv_memory 文件内元信息），不依赖对话历史
- **R4 对话级独立文件**：每个对话独立 `conv_memory_{conv_id}.md` 文件，路径 `.trae/memory/{YYYYMMDD}/conv_memory_{conv_id}.md`
- **R5 压缩恢复流程更新**：五件套并行读取新增"项目目录 ai_memory_main.md"读取，conv_id 从该文件获取
- **R6 用户反馈持久化**：写入对话级文件 `conv_memory_{conv_id}.md`，按时间倒序
- **R7 旧记忆迁移**：迁移时用 Grep 分段读取 C盘 project_memory.md（Read 受限），内容拆分到 ai_memory_main.md + archived/feedback/legacy_{YYYYMMDD}.md
- **R8 多任务并发支持**：ai_memory_main.md 的"当前活跃对话索引"支持多个对话（列表形式）

### 非功能性需求
- **NR1 兼容性**：不破坏现有 archived_feedback/ 归档机制（C盘保留）
- **NR2 最小破坏**：user_profile.md 保留官方位置（跨项目共享）
- **NR3 可回滚**：迁移失败可回滚到官方单轨（删除 .trae/memory/ 即可，C盘未受影响）
- **NR4 工具友好**：所有记忆文件用 Edit/Write 直接可编辑（在工作区内）
- **NR5 时间戳准确**：强制 `date '+%Y-%m-%d %H:%M:%S'`（gitbash）或 `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`（PowerShell），24H制，禁 mcp_Time（AD-07）

## Scenarios（场景）

### 场景1：新对话启动
- AI 读取 `.trae/memory/ai_memory_main.md` → 检查"当前活跃对话索引"
- 若无活跃对话 → 生成新 conv_id（`date '+%Y%m%d%H%M%S'` + `printf '%06x' $RANDOM`）
- 创建 `.trae/memory/{YYYYMMDD}/conv_memory_{conv_id}.md`
- 追加新条目到 ai_memory_main.md 的"当前活跃对话索引"
- 输出反馈清单（三重验证）

### 场景2：多任务并发
- 对话A 和对话B 同时启动
- 各自生成独立 conv_id（基于时间戳+随机hex，几乎不冲突）
- 各自只 Edit 自己的 conv_memory 文件
- ai_memory_main.md 的"当前活跃对话索引"追加各自的条目（不互相覆盖）
- AI 通过对比用户消息与各"任务摘要"识别当前对话

### 场景3：压缩恢复
- AI Read `.trae/memory/ai_memory_main.md`（P1 权威源）→ 获取"当前活跃对话索引"
- 若有1个活跃对话 → 该 conv_id 即为当前对话
- 若有多个活跃对话 → 询问用户确认当前对话
- Read 对应的 `conv_memory_{conv_id}.md`（P2 详细状态）
- 对比用户最新消息 → 判断续接或新对话
- 续接：沿用 conv_id，继续任务
- 新对话：生成新 conv_id，追加到索引

### 场景4：用户反馈持久化
- AskUserQuestion 响应后
- 获取当前时间（`date '+%Y-%m-%d %H:%M:%S'`，24H制）
- 写入对话级 `conv_memory_{conv_id}.md`（按时间倒序）
- 更新 ai_memory_main.md 的"当前活跃对话索引"中该对话的"最后更新"时间

### 场景5：对话完成归档
- 对话完成 → conv_memory 文件移至 `archived/conv_{conv_id}.md`
- ai_memory_main.md 的"当前活跃对话索引"中该对话状态改为"已完成"
- 保留索引记录30天后清理（或手动清理）

### 场景6：AI 每次调用获取 conv_id
- AI 每次被调用时（无状态），通过以下流程获取 conv_id：
- Read `.trae/memory/ai_memory_main.md` → 检查"当前活跃对话索引"
- 若有1个活跃对话 → 沿用该 conv_id
- 若有多个活跃对话 → 对比用户消息与各"任务摘要"，匹配度最高的即为当前对话
- 若无活跃对话 → 生成新 conv_id，追加到索引
- 此流程不依赖对话历史，仅依赖文件持久化
