# 深度分析报告：memory-mechanism-redesign 改造适配评估

> 创建时间：2026-07-27
> 视角：设计文档现状评估 + 内部一致性审查 + 全局规范适配方案 + 项目记忆迁移路径
> 用户问题：深入分析当前设计文档，当前应该如何改造适配？哪些会要动？尤其是全局规范和项目记忆？怎么动？

---

## 一、设计文档现状评估

### 1.1 文档完整度评估

| 文档 | 完整度 | 关键内容 | 评估 |
|------|--------|---------|------|
| README.md | ✅ 完整 | 功能概述+核心能力+文档索引+状态 | 摘要清晰，但核心能力描述与 AD-11 不一致 |
| spec.md | ✅ 完整 | Intent/Scope/Approach/Alternatives/Drawbacks/Requirements/Scenarios | Approach 部分与 AD-11 严重不一致（见 §二） |
| design.md | ✅ 完整 | 15 个 ADR + 数据流 + 文件变更 + 风险评估 | ADR 完整，但前半部分架构图/数据流未同步 AD-11 |
| tasks.md | ✅ 完整 | 17 章节任务清单 + AOAdapt 日志 | 含已被 AD-11 替代的章节（4/10）未清理 |
| overall-planning.md | ✅ 完整 | 整体规划+可行性分析+规范审查+行业实践 | 质量最高，与 AD-11 一致 |
| industry-best-practices.md | ✅ 完整 | Claude Code/Cursor/Cline 三大工具对比 | 建议 AD-16~AD-20 未纳入 design.md |

### 1.2 设计成熟度总评

| 维度 | 评分 | 说明 |
|------|------|------|
| 痛点识别 | ⭐⭐⭐⭐⭐ | 三大痛点（路径/并发/状态）+ 时间戳错乱 诊断精准 |
| 方案决策 | ⭐⭐⭐⭐ | AD-11 完全分离方案已选定，但文档内部一致性未跟上 |
| 规范适配 | ⭐⭐⭐⭐ | 10 个文件清单完整，但"怎么动"细节需补强 |
| 行业对标 | ⭐⭐⭐⭐⭐ | 三大工具研究深入，AD-16~AD-20 建议合理 |
| 可实施性 | ⭐⭐⭐ | 缺关键假设验证（C盘 Read/Write 实际可用性）+ 文档自相矛盾 |

---

## 二、设计文档内部不一致问题（🔴 必须先修订）

### 2.1 核心矛盾：双轨制 vs AD-11 完全分离

**矛盾根源**：AD-11（2026-07-26 追加）已选定"完全分离"方案，取代 AD-01/AD-03/AD-10 的双轨制。但设计文档前半部分未同步修订。

| 文档 | 位置 | 当前内容（双轨制遗留） | 应改为（AD-11 一致） |
|------|------|---------------------|-------------------|
| README.md | 核心能力 §1 | "双轨制存储架构：官方位置（轻量索引）+ 项目目录（重量主记忆）" | "AI 独立记忆系统：项目目录为主，官方位置不干预" |
| spec.md | Approach §Selected | "双轨制存储 + 对话级 ID 隔离... 官方位置保留为索引" | "AI 独立记忆系统（AD-11）+ 对话级 ID 隔离... 官方位置不读不写" |
| spec.md | Alternatives 表 | 方案B（完全迁移）否决理由"丢失系统自动注入能力" | 方案B 已选定（AD-11），否决理由应改为"双轨制维护成本高" |
| design.md | §1 整体架构 mermaid 图 | 双轨制架构图（官方位置+项目目录并列） | 改为 AD-11 独立记忆架构图（官方位置标为"不干预"） |
| design.md | §3 双轨制数据分工表 | 官方位置仍承担"索引/指针"角色 | 官方位置标为"AI 不读写"，所有数据移至项目目录 |
| design.md | Data Flow 读取流程 | "2. 官方位置 project_memory.md(轻量索引,Grep读取)" | 删除官方位置读取步骤，改为"2. 项目目录 ai_memory_main.md(Edit/Write 可编辑)" |
| design.md | File Changes 修改文件表 | "project_memory.md 瘦身为轻量索引" | 删除该行（AD-11 不动官方位置） |
| tasks.md | §4 官方位置瘦身 | 4.1-4.4 全部任务 | 标记为"取消（AD-11 替代）" |
| tasks.md | §10 与官方不冲突保证 | 10.1-10.6 | 已标注"被 AD-11 替代"，但应移至"已取消任务"附录 |

### 2.2 次要矛盾：时间戳工具规范

**矛盾**：AD-07 强制"PowerShell Get-Date"，但 Trae IDE 默认终端是 gitbash（本次对话实测 `Get-Date: command not found`）。

| 文档 | 位置 | 当前内容 | 问题 | 建议 |
|------|------|---------|------|------|
| design.md AD-07 | Decision §3 | "强制使用 PowerShell `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`" | gitbash 终端不可用 | 改为"强制使用 `date '+%Y-%m-%d %H:%M:%S'`（gitbash）或 `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`（PowerShell），24H制" |
| overall-planning.md §9.1 问题3 | 优化方向 | "强制 PowerShell Get-Date" | 同上 | 同上 |

### 2.3 文档修订建议（必须先做）

**优先级 P0**（不修订则无法作为实施依据）：
1. 修订 spec.md Approach 部分 → 与 AD-11 一致
2. 修订 design.md §1/§3 架构图+数据分工表 → 与 AD-11 一致
3. 修订 design.md Data Flow → 删除官方位置读取步骤
4. 修订 design.md AD-07 → 时间戳工具兼容 gitbash
5. 修订 tasks.md §4/§10 → 标记为已取消

**优先级 P1**（影响实施效率）：
6. 修订 README.md 核心能力描述 → 与 AD-11 一致
7. 纳入 AD-16~AD-20 到 design.md → 行业最佳实践落地

---

## 三、全局规范改造清单（10 个文件，怎么动）

### 3.1 直接适配（3 个文件，含项目记忆路径引用）

#### 文件1：context-recovery.md（🔴 改动最大）

**当前问题**：
- 第5行明确指向 C盘 `~/.trae-cn/memory/projects/{key}/project_memory.md`
- 与 AD-11 "AI 不读不写 C 盘官方位置" 严重冲突
- 未提及 conv_id 机制
- 未禁 mcp_Time

**具体改动**：

| 行号 | 当前内容 | 改为 |
|------|---------|------|
| 第5行 | `2.项目记忆: {memory目录}/projects/{项目key}/project_memory.md(重点读取"当前任务状态"字段+用户反馈)` | `2.项目记忆: {项目根目录}/.trae/memory/projects/{项目key}/ai_memory_main.md(权威源,重点读取"当前任务状态"字段) + 当前对话 conv_memory_{conv_id}.md(详细状态)` |
| 第34行 | `用户反馈持久化(强制): AskUserQuestion响应/批评/纠正/决策后立即写入项目记忆` | 追加: `写入位置: {项目根目录}/.trae/memory/projects/{项目key}/{YYYYMMDD}/conv_memory_{conv_id}.md(按时间倒序)` |
| 第36行 | `保留: 最近7天,超期归档到archived_feedback/YYYYMM.md` | `保留: 最近7天,超期归档到 {项目根目录}/.trae/memory/projects/{key}/archived/feedback/YYYYMM.md` |
| 末尾追加 | - | `[memory-mechanism-redesign 补充 - 2026-07-27]`<br>`若项目启用 AI 独立记忆系统（.trae/memory/ 存在），则：`<br>`1. 五件套第2项改为读项目目录 ai_memory_main.md`<br>`2. 反馈写入 conv_memory_{conv_id}.md（对话级隔离）`<br>`3. 时间戳强制 date '+%Y-%m-%d %H:%M:%S'（gitbash）或 PowerShell Get-Date（24H制），禁 mcp_Time`<br>`4. conv_id 格式: conv-{YYYYMMDDHHmmss}-{6位hex}` |

#### 文件2：core-spec.md（🟡 追加条款）

**当前问题**：
- 未提及 conv_id 机制
- 第6行"写入项目记忆"未明确路径

**具体改动**：

| 位置 | 当前内容 | 改为 |
|------|---------|------|
| 第6行 | `3.写入项目记忆` | `3.写入项目记忆(若项目启用 AI 独立记忆系统,写入 .trae/memory/projects/{key}/conv_memory_{conv_id}.md)` |
| 末尾追加 | - | `[memory-mechanism-redesign 补充 - 2026-07-27]`<br>`对话级 conv_id 隔离机制:`<br>`- 格式: conv-{YYYYMMDDHHmmss}-{6位hex}`<br>`- 生成时机: 对话开始时(压缩恢复读取后,无对话ID则生成新ID)`<br>`- 同一对话保持一致: 依赖对话历史上下文`<br>`- 多任务并发: 每个对话只 Edit 自己的 conv_memory 文件`<br>`详细设计: docs/specs/memory-mechanism-redesign/design.md AD-02/AD-14` |

#### 文件3：user_rules.md（🟡 明确路径+工具）

**当前问题**：
- 第8行"记录到项目记忆中"未明确路径
- 第8行"24H制"未禁 mcp_Time
- 未强制具体时间获取命令

**具体改动**：

| 行号 | 当前内容 | 改为 |
|------|---------|------|
| 第8行 | `8.所有交互强制必须使用AskUserQuestion工具询问用户，用户回复必须第一时间记录到项目记忆中（记录时时间已经要获取当前系统时间，并且是24H制，禁止使用12H制），禁止自以为是认为任务结束主动终止对话！！！` | `8.所有交互强制必须使用AskUserQuestion工具询问用户，用户回复必须第一时间记录到项目记忆中（项目目录 .trae/memory/projects/{key}/conv_memory_{conv_id}.md，若未启用则 C盘 ~/.trae-cn/memory/）。记录时时间必须获取当前系统时间，强制 24H制（命令: date '+%Y-%m-%d %H:%M:%S' 或 PowerShell Get-Date -Format 'yyyy-MM-dd HH:mm:ss'），禁止 12H制，禁止 mcp_Time（时区处理有问题）。禁止自以为是认为任务结束主动终止对话！！！` |

### 3.2 间接适配（3 个文件，追加补充条款）

#### 文件4：concurrent-editing.md

**追加内容**（末尾）：
```
[memory-mechanism-redesign 补充 - 2026-07-27]
对话级记忆文件隔离:
- 若项目启用 AI 独立记忆系统，每个对话只 Edit 自己的 conv_memory_{conv_id}.md 文件
- 跨对话状态共享通过 ai_memory_main.md 的"活跃对话索引"协调
- ai_memory_main.md 的写入需串行化（同一时刻只允许一个对话更新索引行）
- conv_memory 文件不需要串行化（对话级隔离，天然无冲突）
```

#### 文件5：budget-management.md

**追加内容**（末尾）：
```
[memory-mechanism-redesign 补充 - 2026-07-27]
记忆文件缓存与归档:
- 若项目启用 AI 独立记忆系统，缓存写入 {项目根目录}/.trae/memory/cache/
- 归档触发: ai_memory_main.md > 50KB 或 反馈 > 7天 或 对话完成
- 归档位置: .trae/memory/projects/{key}/archived/{type}_{YYYYMMDD}_{seq}.md
- 永不归档: Hard Constraints + 当前任务状态 + 活跃对话索引
```

#### 文件6：danger-ops.md

**追加内容**（末尾）：
```
[memory-mechanism-redesign 补充 - 2026-07-27]
记忆文件操作边界:
- 创建项目目录 .trae/memory/ 不算危险操作（在工作区内，无需 AskUserQuestion 确认）
- 删除 .trae/memory/ 整个目录算危险操作（需备份 + AskUserQuestion 确认）
- 迁移 C盘 project_memory.md 到项目目录前必须 .bak 备份
- 清理 conv_memory 文件需先归档到 archived/，禁止直接删除
```

### 3.3 无需适配（4 个文件，确认即可）

| 文件 | 确认理由 |
|------|---------|
| coding-philosophy.md | 编码哲学，与记忆机制无关 |
| complex-task.md | 五阶段流水线，与记忆机制无关 |
| openspec-workflow.md | OpenSpec 工作流，与记忆机制无关 |
| output-safety.md | 输出安全，与记忆机制无关 |

### 3.4 项目级规范适配（3 个文件 + AGENTS.md）

| 文件 | 改动内容 |
|------|---------|
| docs/project-rules/logging-during-refactoring.md | 追加: 反馈日志写入 conv_memory_{conv_id}.md |
| docs/project-rules/version-delivery-sync.md | 追加: 版本交付同步检查包含 ai_memory_main.md 状态 |
| docs/project-rules/spec-sedimentation-mechanism.md | 追加: 错误沉淀写入 conv_memory + ai_memory_main 归档触发 |
| AGENTS.md | 项目记忆章节同步: AD-11 独立记忆系统 + AD-14 任务级 + AD-15 防错乱 + 路径配置 |

### 3.5 全局规范改造原则

1. **追加补充，不删除原条款**：保留原条款，末尾追加 `[memory-mechanism-redesign 补充]` 段落
2. **条件触发语句**：使用"若项目启用 AI 独立记忆系统（.trae/memory/ 存在），则..."避免影响其他项目
3. **跨项目影响**：全局规范影响所有项目，其他项目未启用新机制时仍走原路径（C盘）
4. **标注来源**：`[memory-mechanism-redesign 补充 - 2026-07-27]`
5. **实施时机**：纳入阶段4 规范适配，与项目目录创建同步

---

## 四、项目记忆迁移方案（C盘 → 项目目录）

### 4.1 当前 C盘 状态盘点

```
C:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\
├── project_memory.md                          # 主记忆（需迁移）
├── project_memory.md.bak_202607211911         # 历史备份 ×8（保留，不迁移）
├── project_memory.md.bak_202607261038
├── 20260618/ ~ 20260726/                      # 日期目录 ×22（系统自动持久化，不干预）
│   ├── session_memory_*.jsonl                 # 系统维护
│   └── topics.md                              # 系统维护
└── archived_feedback/                         # 历史归档（保留，可选迁移）
    ├── 202607.md
    └── README.md
```

### 4.2 迁移目标结构

```
f:\myself\github\WeAgentChat\temp\legado\.trae\memory\projects\-f-myself-github-WeAgentChat-temp-legado\
├── ai_memory_main.md                          # 主记忆（Hard Constraints + 当前任务状态 + 活跃对话索引）
├── 20260727/                                  # 今日对话目录
│   └── conv_memory_{conv_id}.md               # 对话级独立记忆（本次对话）
└── archived/
    ├── feedback/
    │   └── legacy_20260727.md                 # 旧反馈归档（从 C盘 project_memory.md 拆分）
    ├── main_history/
    └── conv/
```

### 4.3 关键假设验证（🔴 必须先做）

**假设1：C盘 Read 可用** → ✅ 已验证（本次对话 Read C盘 user_rules 成功）

**假设2：C盘 Write/Edit 受限** → ⚠️ 需验证
- AD-01 声称"Edit/Write 工具因工作区限制无法直接编辑"
- 但 user_profile.md updated_at=2026-07-24，说明 C盘文件最近被更新过
- C盘有8个 .bak 备份，说明 project_memory.md 被频繁修改
- **矛盾**：要么 AD-01 假设不准确，要么之前的修改用的是 PowerShell 间接写入
- **验证方法**：尝试 Edit C盘 project_memory.md 的某一行，看是否报错

**假设3：项目目录 Edit/Write 可用** → ✅ 大概率可用（工作区内）
- 但 .trae/memory/ 目录尚不存在，需先创建

### 4.4 迁移步骤（7步）

| 步骤 | 操作 | 工具 | 验证 |
|------|------|------|------|
| 1 | 创建项目目录 .trae/memory/projects/{key}/ | RunCommand `mkdir -p` | LS 确认目录存在 |
| 2 | 创建子目录 archived/feedback/, archived/main_history/, archived/conv/ | RunCommand `mkdir -p` | LS 确认 |
| 3 | 读取 C盘 project_memory.md | Read（若受限则 Grep 分段） | 确认内容完整 |
| 4 | 拆分内容：Hard Constraints → ai_memory_main.md；用户反馈 → archived/feedback/legacy_20260727.md | Write | 对比原文件行数 |
| 5 | 写入 ai_memory_main.md 骨架（Hard Constraints + 当前任务状态 + 活跃对话索引） | Write | Read 确认 |
| 6 | 创建今日对话目录 20260727/ + conv_memory_{conv_id}.md | Write | Read 确认 |
| 7 | 备份 C盘 project_memory.md 到 .bak（若 Edit 可用则原位标记 deprecated） | RunCommand `cp` | LS 确认 .bak 存在 |

### 4.5 迁移风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| C盘 Read 受限导致读取不全 | 迁移数据丢失 | Grep 分段读取 + 行数对比 |
| 拆分逻辑错误 | Hard Constraints 与反馈混淆 | 人工确认拆分结果 |
| 迁移后 C盘仍被系统注入 | AI 行为不一致 | 以项目目录为权威源，C盘作背景参考 |
| 项目目录未纳入 .gitignore | 敏感反馈泄露 Git | 检查 .gitignore 配置（AD-20 需权衡） |
| 迁移期对话启动 | 并发写入冲突 | 迁移在对话启动时完成，无并发 |

---

## 五、行业最佳实践借鉴建议（AD-16~AD-20）

### 5.1 优先级评估

| ADR | 标题 | 借鉴来源 | 推荐优先级 | 实施成本 | 建议 |
|-----|------|---------|-----------|---------|------|
| AD-16 | "记忆只是提示"原则 | Claude Code | P0 必做 | 极低（1行声明） | ✅ 强烈推荐，降低幻觉 |
| AD-17 | "只记无法派生认知"原则 | Claude Code | P0 必做 | 低（写入前筛检） | ✅ 强烈推荐，避免冗余 |
| AD-18 | 4类记忆分类 | Claude Code | P1 推荐 | 中（重构 ai_memory_main.md 结构） | 🟡 建议采纳，但可延后 |
| AD-19 | 索引文件200行限制 | Claude Code | P1 推荐 | 低（追加归档触发） | ✅ 推荐，控制上下文占用 |
| AD-20 | 版本控制集成 | Cline/Claude Code | P2 可选 | 中（.gitignore 配置） | ⚠️ 需权衡（敏感反馈泄露风险） |

### 5.2 既有 ADR 修订建议

| ADR | 追加条款 | 来源 | 建议 |
|-----|---------|------|------|
| AD-07 时间戳规范 | 相对日期必须转绝对日期 | Claude Code | ✅ 推荐（"下周三"→"2026-08-03"） |
| AD-08 归档机制 | 定期整理机制（Auto Dream） | Claude Code | 🟡 建议简化版（每次对话启动检查） |
| AD-14 任务级记忆 | 压缩前状态传递 | Cline new_task | ✅ 推荐（压缩前主动写 conv_memory） |

### 5.3 不建议借鉴

1. ❌ Claude Code 投机执行（Copy-on-Write 过于复杂）
2. ❌ Claude Code 20项 Shell 安全检查（本项目非 Shell 密集型）
3. ❌ Cline 语义嵌入算法（实现成本过高）
4. ❌ Cursor BugBot（与记忆机制无关）

---

## 六、推荐实施顺序（分阶段）

### 6.1 阶段划分

| 阶段 | 目标 | 关键任务 | 依赖 | 预估工作量 |
|------|------|---------|------|-----------|
| **阶段0：设计文档修订** | 解决内部不一致 | 修订 spec/design/tasks/README 与 AD-11 一致 | 无 | 小 |
| **阶段1：关键假设验证** | 验证 C盘 Edit/Write 实际可用性 | 尝试 Edit C盘 project_memory.md | 阶段0 | 小 |
| **阶段2：目录结构搭建** | 创建 .trae/memory/ 骨架 | mkdir + LS 确认 | 阶段1 | 小 |
| **阶段3：旧记忆迁移** | C盘 → 项目目录 | 7步迁移流程 | 阶段2 | 中 |
| **阶段4：全局规范适配** | 10个文件改造 | 3直接+3间接+4确认+AGENTS.md | 阶段3 | 中 |
| **阶段5：机制实现** | conv_id + 时间戳 + 归档 | 生成函数+模板+触发逻辑 | 阶段4 | 中 |
| **阶段6：验证与回滚** | 4项验证+3步回滚 | V1-V4 验证 + R1-R3 回滚 | 阶段5 | 中 |
| **阶段7：深度集成** | OpenSpec/AskUserQuestion 集成 | 5项集成任务 | 阶段6 | 中 |
| **阶段8：行业实践落地** | AD-16~AD-20 | 纳入 design.md + 实施 | 阶段7 | 可选 |

### 6.2 关键路径

```
阶段0（设计文档修订）→ 阶段1（假设验证）→ 阶段2（目录创建）→ 阶段3（迁移）→ 阶段4（规范适配）
                                                                                    ↓
                                                              阶段7（集成）← 阶段6（验证）← 阶段5（机制）
```

### 6.3 阶段0 详细任务（设计文档修订，建议立即执行）

| # | 任务 | 文件 | 改动内容 |
|---|------|------|---------|
| 0.1 | 修订 spec.md Approach | spec.md | 双轨制 → AD-11 独立记忆系统 |
| 0.2 | 修订 spec.md Alternatives | spec.md | 方案B 从"否决"改为"选定" |
| 0.3 | 修订 design.md §1 架构图 | design.md | 双轨制图 → AD-11 独立记忆图 |
| 0.4 | 修订 design.md §3 数据分工表 | design.md | 官方位置标为"不干预" |
| 0.5 | 修订 design.md Data Flow | design.md | 删除官方位置读取步骤 |
| 0.6 | 修订 design.md File Changes | design.md | 删除"project_memory.md 瘦身" |
| 0.7 | 修订 design.md AD-07 | design.md | 时间戳工具兼容 gitbash |
| 0.8 | 修订 tasks.md §4 | tasks.md | 标记为"取消（AD-11 替代）" |
| 0.9 | 修订 tasks.md §10 | tasks.md | 移至"已取消任务"附录 |
| 0.10 | 修订 README.md 核心能力 | README.md | 双轨制 → AD-11 独立记忆 |
| 0.11 | 纳入 AD-16~AD-20 | design.md | 新增 5 个 ADR（P0/P1） |

---

## 七、关键决策点（需用户确认）

### 7.1 决策1：是否先修订设计文档自身？

**背景**：设计文档存在严重的内部不一致（双轨制 vs AD-11），不修订则无法作为可靠实施依据。

**选项**：
- A. 先修订设计文档（推荐）：解决内部不一致，确保实施有可靠依据
- B. 跳过修订直接实施：风险是实施过程中遇到矛盾时需反复决策
- C. 边实施边修订：风险是实施方向可能与最终修订不一致

### 7.2 决策2：C盘 Edit/Write 实际可用性？

**背景**：AD-01 声称"Edit/Write 受限"，但 user_profile.md 最近被更新过，C盘有8个 .bak 备份。这个假设是整个方案的基础。

**验证方法**：
- 尝试 Edit C盘 project_memory.md 的某一行
- 若成功 → AD-01 假设不准确，可简化方案（不必完全分离）
- 若失败 → AD-01 假设准确，AD-11 完全分离方案正确

### 7.3 决策3：是否纳入 AD-16~AD-20 行业最佳实践？

**背景**：industry-best-practices.md 建议5个新 ADR，但会增加复杂度。

**选项**：
- A. 全部纳入（推荐 P0+P1）：AD-16/AD-17 必做，AD-18/AD-19 推荐
- B. 仅纳入 P0：AD-16/AD-17（"记忆只是提示" + "只记无法派生认知"）
- C. 暂不纳入：先完成核心改造，后续迭代

### 7.4 决策4：全局规范适配方式？

**背景**：全局规范跨项目共享，其他项目可能未启用新机制。

**选项**：
- A. 条件触发语句（推荐）：使用"若项目启用 AI 独立记忆系统，则..."，不影响其他项目
- B. 直接替换：所有项目强制使用新机制，风险高
- C. 项目级覆盖：全局规范不动，在项目 AGENTS.md 中覆盖

### 7.5 决策5：是否立即进入实施？

**背景**：用户之前说"不要实施要整体规划"，现已完成整体规划+深度分析。

**选项**：
- A. 继续完善设计（阶段0 修订）：先解决文档内部不一致
- B. 立即进入实施（阶段1 开始）：跳过修订，边实施边修订
- C. 仅做关键假设验证（阶段1）：验证 C盘 Edit/Write 后再决策

---

## 八、总结

### 8.1 核心发现

1. **设计文档质量高但内部不一致**：15 个 ADR 决策完整，但前半部分未同步 AD-11，需先修订
2. **全局规范适配清单完整**：10 个文件清单准确，"怎么动"已有具体方案
3. **项目记忆迁移路径清晰**：7步迁移流程 + 风险缓解措施完备
4. **关键假设需验证**：C盘 Edit/Write 实际可用性是方案基础，必须先验证
5. **行业最佳实践有价值**：AD-16/AD-17 强烈推荐，AD-18~AD-20 可选

### 8.2 推荐路径

**阶段0（设计文档修订）→ 阶段1（关键假设验证）→ 阶段2-7（按序实施）**

### 8.3 风险提示

1. **最大风险**：C盘 Edit/Write 假设不准确，导致方案过度复杂化
2. **次要风险**：全局规范适配影响其他项目，需用条件触发语句隔离
3. **低风险**：迁移期数据丢失（有 .bak 备份 + 行数对比验证）

---

## 附录A：设计文档与实际现状对照

| 设计文档假设 | 实际现状 | 一致性 |
|-------------|---------|--------|
| C盘 Edit/Write 受限 | user_profile.md 2026-07-24 被更新过 | ⚠️ 需验证 |
| 项目目录 .trae/memory/ 不存在 | 确认不存在（LS 确认） | ✅ 一致 |
| 全局规范 10 个文件 | 确认 10 个文件存在（LS 确认） | ✅ 一致 |
| C盘 project_memory.md 存在 | 确认存在 + 8个 .bak 备份 | ✅ 一致 |
| C盘 session_memory_*.jsonl 存在 | 确认存在（22个日期目录） | ✅ 一致 |
| C盘 archived_feedback/ 存在 | 确认存在（202607.md + README.md） | ✅ 一致 |

## 附录B：AD-07 时间戳工具兼容性测试

| 工具 | 命令 | 可用性 | 24H制 | 准确性 |
|------|------|--------|-------|--------|
| PowerShell | `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'` | ❌ gitbash 不可用 | ✅ | ✅ |
| gitbash date | `date '+%Y-%m-%d %H:%M:%S'` | ✅ | ✅ | ✅ |
| mcp_Time | get_current_time | ✅ | ⚠️ 时区问题 | ❌ 时区处理有误 |

**结论**：AD-07 应改为"强制 `date '+%Y-%m-%d %H:%M:%S'`（gitbash）或 `Get-Date -Format 'yyyy-MM-dd HH:mm:ss'`（PowerShell），禁 mcp_Time"

---

## 附录C：用户反馈记录（2026-07-27 22:20）

### [2026-07-27 22:20] AskUserQuestion 响应 + 批评
- **问题**: 深度分析报告已完成，发现设计文档存在双轨制 vs AD-11 完全分离的内部不一致问题。下一步应如何推进？
- **用户选择**: 执行阶段0：修订设计文档
- **附加意见（批评）**: 
  1. 路径冗余问题：`{项目根目录}/.trae/memory/projects/{项目key}/ai_memory_main.md` 中 `{项目key}` 多余——项目目录本身就是项目边界，不需要再用 key 区分
  2. conv_id 一致性质疑：如何保证 conv_id 对话一开始的生成？如何在整个对话任务中保持一致？如何让 AI 在压缩恢复时仍然知道这个值？
  3. 一次性完成要求：不要分阶段实施的任务设计，要深入分析后一次性完成的任务设计
- **影响**: 
  1. 路径简化：去掉 `{项目key}` 层级，直接用 `.trae/memory/ai_memory_main.md`
  2. conv_id 机制需完整设计：生成时机 + 持久化机制（不依赖对话历史）+ 压缩恢复获取流程
  3. tasks.md 改为一次性任务清单，不分阶段
- **铁证**: Read C盘 project_memory.md 报错 "File path is not within allowed workspace"——验证 AD-01 假设准确，C盘 memory 目录不在工作区内，AI 无法直接 Read/Edit/Write

### [2026-07-27 22:20] 关键发现
- C盘 user_rules/*.md 可以 Read（系统配置允许）
- C盘 memory/projects/.../project_memory.md 不可以 Read（用户数据，禁止 AI 直接访问）
- 这印证了 AD-11 完全分离方案的必要性——AI 必须有自己的独立记忆系统
