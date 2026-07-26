# 行业最佳实践对比分析（知名 AI 工具记忆机制研究）

> 用户要求："去网上看看 openclaw 等知名 ai 工具是怎么搞的"
> 已研究：Claude Code / Cursor / Cline 三大知名 AI 编码助手的记忆机制
> 创建时间：2026-07-26

---

## 一、Claude Code 的记忆机制（最成熟，重点借鉴）

### 1.1 五层记忆架构

```
短期记忆（会话内对话，内存，进程退出即丢）
工作记忆（当前任务状态，子Agent任务/文件变更追踪）
长期记忆三层结构：
  ├─ 记忆目录：~/.claude/projects/<project>/memory/
  ├─ MEMORY.md 索引文件（最多200行，始终加载到提示）
  └─ 独立主题文件（按需加载，用Claude Sonnet扫描选最相关5个）
```

### 1.2 四类记忆分类（语义分型，非时间堆叠）

| 类型 | 用途 | 隐私级别 | 共享策略 |
|------|------|---------|---------|
| **user** | 角色与背景（担任角色/专业领域/沟通偏好） | 私有 | 不共享 |
| **feedback** | 纠错与确认（做错了什么+被确认可行的用法） | 私有 | 不共享 |
| **project** | 进行中目标（目标/deadline/incidents/决策） | 团队可见 | 可共享 |
| **reference** | 外部系统信息（Grafana URL/Linear标识） | 团队可见 | 可共享 |

### 1.3 关键设计原则（核心洞察）

#### 原则1：只记"上下文无法派生的认知"
- **筛子**：一条信息是否"无法从当前上下文派生"
- 凡是能通过读代码、看文件、调工具重新得到的事实，**不写进记忆**
- 这类信息随时可重建，写下来只会占用预算，还要承担过期风险
- 值得留存的：丢失之后需要人重新告知、或跨多次会话才能积累的认知

#### 原则2："记忆只是提示"而非事实
- 系统提示明确要求模型把记忆当成**线索**而非**事实**
- 落到具体动作前会先去核对真实代码
- 这种"记忆只是提示"的姿态，显著降低凭记忆产生幻觉的概率

#### 原则3：相对日期必须转成绝对日期
- "下周三"在写下的当天清晰，三周后再读就失去锚点
- 落成 `2026-06-24` 这样的形式，记忆才能在任意时刻被正确解读

### 1.4 CLAUDE.md 分层加载机制

| 层级 | 位置 | 归属 | 加载时机 |
|------|------|------|---------|
| 企业级 | `/Library/Application Support/ClaudeCode/CLAUDE.md` | 组织策略 | 启动时 |
| 用户级 | `~/.claude/CLAUDE.md` | 跟人走，所有项目生效 | 启动时 |
| 项目级 | `./CLAUDE.md` 或 `./.claude/CLAUDE.md` | 提交进Git，团队共享 | 启动时 |
| 项目本地 | `./CLAUDE.local.md` | 个人差异，进.gitignore | 启动时追加 |
| 子目录级 | `子目录/CLAUDE.md` | 模块专属指令 | 按需（访问相关文件时） |

**加载机制**：从当前目录**递归向上**查找，沿途所有 CLAUDE.md 都被加载（叠加而非覆盖）

### 1.5 import 语法（模块化记忆）

```markdown
# Instructions
See @README for overview and @package.json for commands.
```
- 支持相对/绝对/`~/`路径
- 递归引入最多4层
- 首次使用需批准

### 1.6 条件规则（.claude/rules/*.md）

```yaml
---
paths:
  - "src/**/*.ts"
---
# TypeScript Rules
- Use strict null checks
- Prefer interfaces over types
```
- 用 YAML frontmatter 声明适用范围
- 只在 Claude 操作匹配文件时加载

### 1.7 Auto Dream（自动整理）

- **触发**：距离上次清理超过24小时且有5个以上新会话
- **动作**：后台自动合并冲突记忆、删除无效笔记
- **约束**：MEMORY.md 索引严格压缩在200行以内

### 1.8 四级压缩体系

| 级别 | 名称 | 触发条件 | 策略 |
|------|------|---------|------|
| 1 | Snip（轻量裁剪） | 上下文略满 | 裁剪最旧内容 |
| 2 | Microcompact（工具结果缓存） | 工具结果重复 | 缓存替换 |
| 3 | Auto Compact（全量对话摘要） | 上下文将满 | 全量摘要 |
| 4 | Reactive Compact（响应式压缩） | 413错误 | 紧急压缩 |

---

## 二、Cursor 的记忆机制（Rules + Memories 双轨制）

### 2.1 Rules（显式系统级指令）

- **位置**：`.cursor/rules/*.mdc` 文件
- **格式**：Markdown with metadata（YAML头 + 正文）
- **字段**：
  - Description：Agent判断何时使用
  - Globs：自动应用文件范围（如 `*.tsx`）
  - Content：规则正文

### 2.2 四种触发类型

| 类型 | 描述 | 适用场景 |
|------|------|---------|
| **Always** | 始终应用在模型上下文开头 | 全局通用规范 |
| **Auto** | 涉及匹配文件时自动加入 | 特定文件类型规则 |
| **Manual** | 明确@引用时应用 | 按需规则 |
| **Agent request** | AI自行决定是否包含 | 需要Description供AI判断 |

### 2.3 Memories（AI自动记忆，Cursor 1.0）

- **存储**：每项目每用户
- **机制**：伴随模型观察聊天，建议保存潜在记忆
- **审批**：开发者批准或拒绝
- **本质**：自动生成的规则，在设置中管理

---

## 三、Cline 的记忆机制（Memory Bank 三层架构）

### 3.1 三层架构

```
内存银行（Memory Bank）——持久化知识存储
    ↕
上下文管理器（Context Manager）——动态窗口调控
    ↕
智能压缩引擎（Compression）——信息密度优化
```

### 3.2 Memory Bank 六类核心文件

| 文件 | 职责 | 更新频率 |
|------|------|---------|
| `projectbrief.md` | 项目总览（目标/范围/约束） | 偶尔调整 |
| `productContext.md` | 产品背景（用户需求/痛点/价值） | 需求变化时 |
| `activeContext.md` | 当前焦点（任务/决策/下一步） | **最高** |
| `systemPatterns.md` | 架构设计（模块/模式/接口） | 架构变更时 |
| `techContext.md` | 技术栈（语言/框架/依赖/版本） | 技术选型变化时 |
| `progress.md` | 进度追踪（已完成/未完成/问题） | 每迭代后 |

### 3.3 工作机制

- **规则驱动**：`.clinerules` 中声明"每次任务开始必须读取memory-bank下所有文件"
- **流程**：读→验证→执行→更新
- **版本控制**：文件受Git管理，可diff/回滚
- **new_task工具**：上下文>50%时自动创建新任务，传递结构化上下文

### 3.4 智能压缩策略

- 语义提炼（保留核心概念，去除冗余）
- 结构化转换（长文本→表格/列表）
- 代码精简（保留逻辑，去除注释/格式）
- 引用替换（用引用代替完整内容，按需加载）

---

## 四、对比分析：我们的设计 vs 行业最佳实践

### 4.1 维度对比表

| 维度 | 我们的设计(AD-11) | Claude Code | Cursor | Cline |
|------|------------------|-------------|--------|-------|
| 存储位置 | 项目目录.trae/memory/ | ~/.claude/projects/ | 项目内+全局 | 项目内memory-bank/ |
| 主索引文件 | ai_memory_main.md | MEMORY.md(200行) | Rules文件 | activeContext.md |
| 对话级文件 | conv_memory_{conv_id}.md | 主题文件(4类) | 无 | 无 |
| 记忆分类 | Hard Constraints/反馈/任务状态 | user/feedback/project/reference | 无明确分类 | 6类核心文件 |
| 加载机制 | AI主动读 | 前200行始终加载+按需加载 | 始终加载 | 任务前读取所有 |
| 压缩机制 | 归档(7天/50KB/对话级) | Auto Dream+4级压缩 | 无 | 智能压缩引擎 |
| 条件触发 | 无 | YAML前置元数据+paths | Globs匹配 | 无 |
| 版本控制 | 未明确 | CLAUDE.md进Git | .cursor/rules进Git | memory-bank进Git |

### 4.2 我们的设计差距（8项）

| # | 差距 | 影响 | 改进方向 |
|---|------|------|---------|
| G1 | 缺少"记忆只是提示"原则 | 可能凭记忆产生幻觉 | 规范中加入"记忆是线索，行动前核对真实代码" |
| G2 | 缺少"只记上下文无法派生的认知"原则 | 记忆冗余+过期风险 | 写入前筛检"是否能通过读代码重新得到" |
| G3 | 记忆分类不够语义化 | 检索效率低 | 考虑采用user/feedback/project/reference四类 |
| G4 | 缺少索引文件行数限制 | 主记忆无限增长 | 参考MEMORY.md 200行限制 |
| G5 | 缺少Auto Dream自动整理 | 冲突记忆累积 | 设计定期整理机制 |
| G6 | 缺少条件触发机制 | 所有规范始终应用 | 参考Cursor的Always/Auto/Manual/Agent request |
| G7 | 缺少相对日期转绝对日期规范 | 时间锚点丢失 | 加入"相对日期必须转绝对日期" |
| G8 | 缺少版本控制集成 | 记忆不可追溯 | 明确.trae/memory/纳入Git管理 |

---

## 五、可借鉴的10个关键设计点

### 5.1 必须借鉴（P0，核心改进）

#### 借鉴1：Claude Code的"记忆只是提示"原则
- **原文**：系统提示明确要求模型把记忆当成线索而非事实，落到具体动作前会先去核对真实代码
- **我们的应用**：在 ai_memory_main.md 顶部声明"本记忆为线索，行动前必须核对真实代码/文件"
- **价值**：降低幻觉概率

#### 借鉴2：Claude Code的"只记上下文无法派生的认知"原则
- **原文**：能通过读代码、看文件、调工具重新得到的事实，不写进记忆
- **我们的应用**：在写入前筛检"是否能通过读代码重新得到"，能则不写
- **价值**：避免记忆冗余和过期风险

#### 借鉴3：Claude Code的4类记忆分类
- **原文**：user/feedback/project/reference 四类语义分类
- **我们的应用**：考虑将 ai_memory_main.md 的内容按四类组织
- **价值**：语义化分类提升检索效率

### 5.2 推荐借鉴（P1，重要改进）

#### 借鉴4：Claude Code的MEMORY.md索引+主题文件分离
- **原文**：索引文件(200行)始终加载 + 主题文件按需加载
- **我们的应用**：ai_memory_main.md 限制行数 + 主题文件按需加载
- **价值**：控制上下文占用

#### 借鉴5：Claude Code的Auto Dream自动整理
- **原文**：后台自动合并冲突记忆、删除无效笔记
- **我们的应用**：设计定期整理机制（每次对话启动时检查）
- **价值**：保持记忆整洁

#### 借鉴6：Cursor的四种触发类型
- **原文**：Always/Auto/Manual/Agent request
- **我们的应用**：规范文件标注触发类型
- **价值**：避免无关规范占用上下文

### 5.3 可选借鉴（P2，优化增强）

#### 借鉴7：Claude Code的相对日期转绝对日期
- **原文**："下周三"→`2026-06-24`
- **我们的应用**：时间戳规范追加"相对日期必须转绝对日期"
- **价值**：避免时间锚点丢失

#### 借鉴8：Cline的6类核心文件体系
- **原文**：projectbrief/productContext/activeContext/systemPatterns/techContext/progress
- **我们的应用**：考虑按此结构组织 ai_memory_main.md
- **价值**：结构化知识存储

#### 借鉴9：Cline的new_task工具
- **原文**：上下文>50%时自动创建新任务，传递结构化上下文
- **我们的应用**：设计压缩前的状态传递机制
- **价值**：压缩恢复不丢失关键状态

#### 借鉴10：版本控制集成
- **原文**：记忆文件进Git，可diff/回滚
- **我们的应用**：明确.trae/memory/纳入Git管理（除敏感信息）
- **价值**：可追溯、可回滚

---

## 六、对当前设计的改进建议

### 6.1 新增 ADR 决策建议

#### 建议 AD-16: "记忆只是提示"原则（借鉴Claude Code）
- **Context**: 研究Claude Code发现"记忆只是提示"原则能降低幻觉
- **Decision**: ai_memory_main.md 顶部声明"本记忆为线索，行动前必须核对真实代码/文件"
- **Goal**: 降低凭记忆产生幻觉的概率

#### 建议 AD-17: "只记上下文无法派生的认知"原则（借鉴Claude Code）
- **Context**: 研究Claude Code发现"只记无法派生的认知"能避免冗余
- **Decision**: 写入前筛检"是否能通过读代码重新得到"，能则不写
- **Goal**: 避免记忆冗余和过期风险

#### 建议 AD-18: 4类记忆分类（借鉴Claude Code）
- **Context**: Claude Code的user/feedback/project/reference分类更语义化
- **Decision**: ai_memory_main.md 内容按四类组织（user/feedback/project/reference）
- **Goal**: 语义化分类提升检索效率

#### 建议 AD-19: 索引文件行数限制（借鉴Claude Code）
- **Context**: MEMORY.md 200行限制控制上下文占用
- **Decision**: ai_memory_main.md 限制200行，超出移至主题文件
- **Goal**: 控制上下文占用

#### 建议 AD-20: 版本控制集成（借鉴Cline/Claude Code）
- **Context**: 记忆文件进Git可追溯
- **Decision**: .trae/memory/ 纳入Git管理（除CLAUDE.local.md类敏感信息）
- **Goal**: 可追溯、可回滚

### 6.2 既有 ADR 的修订建议

#### AD-07（时间戳规范）追加条款
- 借鉴Claude Code：**相对日期必须转成绝对日期**
- "下周三"→`2026-06-24`

#### AD-08（归档机制）追加条款
- 借鉴Claude Code Auto Dream：**定期整理机制**
- 每次对话启动时检查并合并冲突记忆、删除无效笔记

#### AD-14（任务级记忆）追加条款
- 借鉴Cline的new_task：**压缩前状态传递**
- 上下文>50%时主动传递结构化上下文到 conv_memory

---

## 七、研究结论与下一步建议

### 7.1 研究结论

1. **Claude Code 最成熟**：5层架构+4类分类+Auto Dream+4级压缩，设计最完整
2. **Cursor 最简洁**：Rules+Memories双轨制，.mdc格式清晰
3. **Cline 最结构化**：6类核心文件+三层架构，适合团队协作
4. **我们的设计有特色**：对话级 conv_memory 文件隔离多任务并发，是独特优势
5. **但存在8项差距**：缺少"记忆只是提示"原则、只记无法派生认知、4类分类等

### 7.2 下一步建议

1. **立即采纳**：借鉴1-3（P0核心改进）
2. **分阶段采纳**：借鉴4-6（P1重要改进）
3. **可选采纳**：借鉴7-10（P2优化增强）
4. **新增5个ADR**：AD-16至AD-20
5. **修订3个既有ADR**：AD-07/AD-08/AD-14 追加条款

### 7.3 不建议借鉴的设计

1. **不借鉴Claude Code的投机执行**：Copy-on-Write覆盖文件系统过于复杂
2. **不借鉴Claude Code的20项Shell安全检查**：本项目非Shell密集型
3. **不借鉴Cursor的BugBot**：与记忆机制无关
4. **不借鉴Cline的语义嵌入算法**：实现成本过高，收益不明确

---

## 八、引用来源

- [Claude Code 新功能上线：Auto Memory](https://cloud.tencent.cn/developer/article/2701676)
- [Claude Code 源码曝光：1884个文件拆完之后](https://cloud.tencent.com/developer/article/2698419)
- [Claude Code 的记忆机制](http://m.toutiao.com/group/7657858249076638248/)
- [Claude Code的记忆&上下文机制](https://blog.csdn.net/iting_0924/article/details/161368239)
- [深入 Claude Code 的 CLAUDE.md](https://juejin.cn/post/7661303393304313866)
- [Cursor 1.0 Introduces BugBot and Memories](https://www.aitechsuite.com/ai-news/ai-coding-gets-smarter-cursor-10-introduces-bugbot-and-memories)
- [关于Cursor的一些基础问题](https://blog.csdn.net/qq_39965059/article/details/150555859)
- [Cursor 1.0正式推出：全面解析](https://blog.csdn.net/linshantang/article/details/148471116)
- [学会使用Cursor的三大神器Rules、Memories、Commands](https://devpress.csdn.net/v1/article/detail/154458734)
- [Cline Memory Bank 使用](https://icode.best/i/169491424652455)
- [Cline智能内存管理：突破AI编码助手上下文局限](https://blog.gitcode.com/5109b4a75ae4871adfbd7927bec121a1.html)
- [Cline's new_task Tool Eliminates Context Window Limitations](https://cline.bot/blog/unlocking-persistent-memory-how-clines-new_task-tool-eliminates-context-window-limitations)
- [突破上下文壁垒：Cline智能编码助手的记忆管理革新](https://blog.gitcode.com/23c67d05d6a2a853a1b33df6bc4a48c2.html)
- [突破AI编码助手局限：Cline智能内存管理技术全解析](https://blog.csdn.net/gitblog_01178/article/details/151814999)
