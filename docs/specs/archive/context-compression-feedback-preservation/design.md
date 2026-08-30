# Design: 上下文压缩用户反馈保全 + 主线任务完成质量审查（含 openspec 设计偏差审查）+ 打包功能差距修复

## Technical Approach

### Part A: 用户反馈持久化层

在 project_memory.md 新增"用户反馈与决策记录"小节，作为用户反馈的持久化存储。

**结构设计**：

```markdown
## 用户反馈与决策记录（保留最近 7 天，超期归档）

### 2026-07-09

- `[21:00] 决策 | 修复范围询问 | 用户选"全部修复" | P0-P3 全部修复，禁止只修部分`
- `[21:05] 批评 | 文件夹卡片样式 | "丑爆了，学习书架布局" | 必须复用书架封面卡片视觉，禁止纯色大色块`
- `[21:10] 纠正 | 方案选择 | 用户否决方案A，要求方案B | 禁止再使用方案A，后续必须用方案B`
- `[21:15] AskUserQuestion响应 | 检查点1 | 用户选"需调整"，Other:"深度分析主线任务完成质量" | spec 扩展为三部分`
```

**反馈类型分类**：

| 类型 | 触发条件 | 持久化优先级 |
|------|---------|-------------|
| 决策 | 用户明确选择/指示 | P0（最高） |
| 纠正 | 用户否定AI的提议/行为 | P0 |
| 批评 | 用户表达不满 | P1 |
| AskUserQuestion响应 | 用户通过AskUserQuestion选择 | P0 |
| 确认 | 用户确认AI的理解正确 | P2 |

### Part A: 压缩恢复四件套

**现有三件套**：
1. AGENTS.md（强制规则）
2. project_memory.md（项目约束）
3. TaskList（任务状态）

**扩展为四件套**：
1. AGENTS.md（强制规则）
2. **project_memory.md（含"用户反馈与决策记录"小节）** ← 重点读取
3. TaskList（任务状态）
4. basic-memory（若有当前任务历史决策）

**恢复后强制输出**：

```
## 已加载的用户反馈清单（最近 7 天）

### 2026-07-09
- [21:00] 决策：用户选"全部修复" → P0-P3 全部修复
- [21:05] 批评：文件夹卡片丑爆了 → 必须学习书架布局
- [21:10] 纠正：否决方案A → 必须用方案B
- [21:15] 检查点1：用户选"需调整" → spec 扩展为三部分

以上反馈将在本次会话中严格遵守。
```

### Part A: AskUserQuestion 响应处理流程

```
用户通过 AskUserQuestion 给出响应
  ↓
AI 复述用户选择（"收到您选择：XXX"）
  ↓
若用户选"需调整" + Other 输入 → 原文复述意见
  ↓
写入 project_memory.md "用户反馈与决策记录" 小节
  ↓
（可选）写入 basic-memory（若是关键决策）
  ↓
继续执行后续工作
```

### Part A: 反馈记录归档机制

**归档触发**：每周首次压缩恢复时
**归档路径**：`c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\archived_feedback\YYYYMM.md`
**归档规则**：
- 筛选 project_memory.md 中超过 7 天的反馈
- 按月份追加到归档文件
- 从 project_memory.md 删除已归档的反馈
- project_memory.md 只保留最近 7 天

### Part B: 主线任务完成质量三层深度审查

```
┌─────────────────────────────────────────────────┐
│ B0: openspec 设计偏差审查（第一层，最核心）       │
│  - 从历史文档提取用户提问反馈（F1-F10）          │
│  - 对照 yesterday-changes-deep-audit R5         │
│  - 对照 p0-bugfix-round1 Out of Scope          │
│  - 列出 7 项缺失（G1-G7）+ 5 项偏差（D1-D5）    │
│  - 输出《openspec 设计偏差审查报告》             │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ B1: 代码实施审查（第二层）                       │
│  - 读取 p0-bugfix-round1/design.md              │
│  - 逐项 Grep/Read 源码（C-01/V-01/F-01/M-01/M-02）│
│  - git status 确认 18 文件提交                   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ B2: 交付质量审查（第三层）                       │
│  - 读取 E2E 测试结果（pass_rate）                │
│  - Read updateLog.md 确认更新                    │
│  - 确认真机 L2 验证                              │
│  - 输出《主线任务完成质量审查报告》              │
└─────────────────────────────────────────────────┘
                      ↓
              失败项进入 Part C 修复
```

**B0: openspec 设计偏差审查执行细节**：

| 审查项 | 执行方法 | 输出 |
|--------|---------|------|
| 用户提问反馈提取 | 重新分析 364KB 历史文档，提取用户在 AskUserQuestion 检查点和批评中的反馈 | 10 项反馈清单（F1-F10） |
| yesterday-changes-deep-audit 对照 | Read spec.md R5 章节，确认是否捕获"首页参考书架 style1/style2" | R5 捕获状态 |
| p0-bugfix-round1 Out of Scope 对照 | Read spec.md Out of Scope，逐项与用户诉求比对 | 7 项缺失（G1-G7） |
| 偏差确认 | 对照用户设想 vs openspec 设计 | 5 项偏差（D1-D5），D1 F-08 降级为致命 |
| 处理建议 | 为每个缺失/偏差提出归属 spec 建议 | 处理建议表 |

**B1 审查表执行细节**：

| 审查项 | 执行命令 | 通过标准 |
|--------|---------|---------|
| C-01 sourceSort 拆分 | `Grep "bookSourceSort"` + `Grep "rssSort"` | PreferKey/AppConfig/BookSourceActivity/RssSourceActivity/SourceFolderAdapter 5 处全部修改 |
| V-01 视频换集静音 | `Read VideoPlayer.kt:155-170` | `setNeedMute(isMuted)` 而非 `if (muteOnStart) setNeedMute(true)` |
| F-01 搜索框解耦 | `Grep "currentGroup"` | RssFragment.kt + ExploreFragment.kt 都有 currentGroup 字段，onFolderClick 不回填 searchView |
| M-01/M-02 compact/grid 选择 | `Grep "BookSourceSelection"` + `Grep "RssSourceSelection"` | 接口定义存在 + 3 adapter（Compact/Grid/普通）全部实现 |
| 代码提交 | `git status` | 工作区干净，18 文件已 commit |

**B2 审查表执行细节**：

| 审查项 | 执行命令 | 通过标准 |
|--------|---------|---------|
| E2E 测试 | 读取 `report_20260709_131708/summary.txt` | pass_rate > 50%（当前 10%） |
| updateLog.md | `Read updateLog.md:1-20` | 顶部有 2026/07/09 条目 |
| 真机 L2 验证 | 确认是否有 L2 验证记录 | UI dump + Python 解析 XML 确认功能生效 |

### Part C: 打包功能与设计差距三层修复

```
┌─────────────────────────────────────────────────┐
│ C1: openspec 偏差修复（第一层）                  │
│  - 基于 B0 报告，明确 7 项缺失归属               │
│  - F-08 不能继续 Out of Scope 悬空               │
│  - 沉淀 openspec 偏差审查规范到 project_memory   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ C2: 代码/测试修复（第二层）                      │
│  - UI dump 确认"书源管理"真实入口 → 修复用例     │
│  - git commit 18 文件                            │
│  - 更新 updateLog.md                             │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│ C3: E2E 重跑 + 真机 L2 验证（第三层）            │
│  - venv Python 重跑 F-P0-6                       │
│  - UI dump + Python 解析 XML 确认功能生效        │
└─────────────────────────────────────────────────┘
                      ↓
          输出《打包功能与设计差距修复报告》
```

**C1: openspec 偏差修复执行细节**：

| 缺失项 | 处理建议 |
|--------|---------|
| G1 RssSourceActivity 移除文件夹视图 | 修订 p0-bugfix-round1 或新建 spec（属 P1） |
| G2 文件夹卡片样式参考书架 | 新建 spec 或并入 G1 spec |
| G3 F-08 首页 style1/style2 | 🔴 新建专门 spec（P2 架构重构），明确不能悬空 |
| G4 双维度下拉菜单 | 并入 F-08 spec 或新建 spec |
| G5 编译前更新 updateLog.md | 沉淀为 project_memory 规范（已存在，强化执行） |
| G6 venv 强制使用 | 沉淀为 project_memory 规范（已存在，强化执行） |
| G7 L2 真机功能验证 | 沉淀为 project_memory 规范（已存在，强化执行） |

**C2: 代码/测试修复流程**：

```
1. F-P0-6 用例 UI 入口修复：
   ├─ ADB UI dump 获取首页 XML
   ├─ Python 解析 XML 查找"书源"相关元素
   ├─ 确认真实入口路径（可能是"书源"而非"书源管理"）
   └─ 更新 docs/tests/F-P0-6-source-manage.md 用例路径
  ↓
2. P0 代码提交：
   ├─ git add 18 文件
   └─ git commit -m "fix: P0 修复（C-01 sourceSort拆分 + V-01 视频换集静音 + F-01 搜索框解耦 + M-01/M-02 compact/grid选择）"
  ↓
3. updateLog.md 更新：
   └─ 在 ## cronet版本: 之后追加：
      **2026/07/09**
      - 修复书源/订阅源排序串扰（sourceSort 拆分为 bookSourceSort + rssSort）
      - 修复视频换集强制静音（换集保持用户静音状态）
      - 修复 RSS/发现搜索框回填 Bug（引入 currentGroup 解耦）
      - 修复 compact/grid 视图选择模式（3 adapter 统一 Selection 接口）
```

**C3: E2E 重跑 + L2 验证流程**：

```
1. E2E 重跑：
   └─ ai_tests\venv\Scripts\python.exe ai_tests\run_e2e.py --apk auto --tc F-P0-6
  ↓
2. 真机 L2 验证：
   ├─ UI dump 确认书源管理入口可达
   ├─ Python 解析 XML 确认交互元素状态
   └─ 验证 P0 修复功能生效（排序/静音/搜索框/选择模式）
  ↓
输出《打包功能与设计差距修复报告》
```

## Architecture Decisions

### AD-01: 持久化存储选择 project_memory.md 而非独立文件（Part A）

- **Context**: 用户反馈需要持久化存储，可选方案：project_memory.md 新增小节 / 独立文件 / basic-memory
- **Concern**: 压缩恢复时需要快速读取用户反馈，且与现有恢复流程集成
- **Decision**: 在 project_memory.md 新增"用户反馈与决策记录"小节
- **Goal**: 压缩恢复时读取 project_memory.md 即可同时获取规范和用户反馈，无需多读文件
- **Tradeoff**: project_memory.md 会膨胀，但通过定期归档缓解
- **Status**: Accepted

### AD-02: 压缩恢复从三件套扩展为四件套（Part A）

- **Context**: 现有三件套（AGENTS.md + project_memory.md + TaskList）不包含用户反馈的专门读取
- **Concern**: project_memory.md 已包含用户反馈小节，但恢复时可能未重点关注该小节
- **Decision**: 明确四件套中 project_memory.md 的"用户反馈与决策记录"小节为必读项，恢复后必须输出反馈清单
- **Goal**: 确保 AI 恢复时明确知晓用户最近的反馈，不会无视
- **Tradeoff**: 恢复流程增加一步"输出反馈清单"，耗时略增
- **Status**: Accepted

### AD-03: AskUserQuestion 响应必须复述 + 持久化（Part A）

- **Context**: 用户通过 AskUserQuestion 给出的响应只存在于对话上下文，压缩后丢失
- **Concern**: AI 可能在压缩后忘记用户的选择，重复提问或做出相反行为
- **Decision**: 用户响应后 AI 必须复述确认 + 写入 project_memory.md
- **Goal**: 双重保障——复述让用户确认 AI 理解正确，持久化让压缩后不丢失
- **Tradeoff**: 复述增加一轮交互，但避免压缩后错误执行的成本远高于此
- **Status**: Accepted

### AD-04: 反馈记录定期归档（保留 7 天）（Part A）

- **Context**: 用户反馈持续追加会导致 project_memory.md 膨胀
- **Concern**: 文件过大影响压缩恢复时的读取速度
- **Decision**: 保留最近 7 天，超期归档到 archived_feedback/YYYYMM.md
- **Goal**: 平衡反馈保留时长与文件大小
- **Tradeoff**: 7 天前的反馈不再在恢复时直接加载，但可按需查阅归档
- **Status**: Accepted

### AD-05: 主线任务审查不能信任 TaskList 标记（Part B1+B2）

- **Context**: TaskList #11 标记 completed，但 E2E 实测 pass_rate=10%
- **Concern**: TaskList 的 completed 标记可能虚标，直接信任会导致"千差万里"
- **Decision**: 必须对照 design.md 逐项审查源码 + E2E 结果 + git 状态
- **Goal**: 发现"标记完成但实测失败"项，不放过任何虚标
- **Tradeoff**: 审查耗时，但比交付残次品的成本低得多
- **Status**: Accepted

### AD-06: 差距修复必须用 venv Python（Part C3）

- **Context**: project_memory.md P0-17 要求 E2E 测试必须用 venv Python
- **Concern**: 用公共 Python 会污染用户环境
- **Decision**: 严格使用 `ai_tests\venv\Scripts\python.exe`
- **Goal**: 遵守已有规范，不重复犯错
- **Tradeoff**: 无（venv 已配置好，无额外成本）
- **Status**: Accepted

### AD-07: updateLog.md 必须在交付前更新（Part C2）

- **Context**: project_memory.md 环境常量要求"updateLog.md 编译前更新，不是交付阶段"
- **Concern**: 当前 updateLog.md 未更新，用户安装 APK 后不知道改了什么
- **Decision**: 在 Part C2 修复时同步更新 updateLog.md
- **Goal**: 用户可感知变更内容
- **Tradeoff**: 无
- **Status**: Accepted

### AD-08: openspec 生成前必须对照用户提问反馈清单（Part B0 + C1，新增）

- **Context**: p0-bugfix-round1 spec 把 F-08 首页 style1/style2（用户核心诉求）列为 Out of Scope，导致"千差万里"
- **Concern**: 生成 openspec 时若不对照用户提问反馈，可能把用户核心诉求降级或遗漏
- **Decision**: 生成新 openspec 前，必须执行"用户提问反馈清单对照"，确认每项用户反馈都有归属（本 spec 实现 / 其他 spec 实现 / 明确推迟并告知用户）
- **Goal**: 防止用户核心诉求被悄悄降级为 Out of Scope
- **Tradeoff**: 增加 openspec 生成流程一步，但避免"千差万里"的成本远高于此
- **Status**: Accepted

### AD-09: openspec 偏差审查三层结构（Part B0，新增）

- **Context**: 用户第二次"需调整"反馈要求审查 openspec 设计本身是否捕获用户所有反馈
- **Concern**: 仅审查代码实施（B1）无法发现"设计就错了"的问题
- **Decision**: Part B 扩展为三层：B0 openspec 设计偏差审查 + B1 代码实施审查 + B2 交付质量审查
- **Goal**: 从设计源头发现"千差万里"的根因（F-08 被降级）
- **Tradeoff**: 三层审查耗时，但能定位根因而非表象
- **Status**: Accepted

### AD-10: F-08 等架构重构不在本 spec 实现，只明确归属（Part C1，新增）

- **Context**: F-08 首页 style1/style2 是 P2 架构重构，本 spec 是审查+修复+反馈保全
- **Concern**: 在本 spec 直接实现 F-08 会超出范围，导致 spec 膨胀
- **Decision**: 本 spec 只明确 F-08 等的归属 spec 和实施计划，实际实现由专门 spec 承接
- **Goal**: 控制本 spec 范围，同时不让用户核心诉求悬空
- **Tradeoff**: 用户需等待专门 spec 实施 F-08，但本 spec 会明确计划
- **Status**: Accepted

## Data Flow

### Part A: 反馈写入流程

```
用户消息（AskUserQuestion响应/批评/纠正/决策）
  ↓
AI 识别反馈类型（决策/纠正/批评/AskUserQuestion响应/确认）
  ↓
AI 格式化反馈记录：[YYYY-MM-DD HH:MM] 类型 | 触发上下文 | 用户原文 | 影响
  ↓
AI Edit project_memory.md，追加到"用户反馈与决策记录"小节
  ↓
（若是关键决策）AI 写入 basic-memory
  ↓
AI 复述用户反馈（确认理解）
  ↓
AI 继续执行工作
```

### Part A: 压缩恢复读取流程

```
上下文压缩触发
  ↓
并行读取四件套：
  ├─ AGENTS.md（强制规则）
  ├─ project_memory.md（含用户反馈与决策记录小节）← 重点
  ├─ TaskList（任务状态）
  └─ basic-memory（若有历史决策）
  ↓
解析 project_memory.md 的"用户反馈与决策记录"小节
  ↓
筛选最近 7 天的反馈
  ↓
输出"已加载的用户反馈清单"
  ↓
AI 声明"以上反馈将在本次会话中严格遵守"
  ↓
继续从 TaskList 当前任务工作
```

### Part A: 归档流程

```
压缩恢复时检测
  ↓
读取 project_memory.md 的"用户反馈与决策记录"小节
  ↓
筛选超过 7 天的反馈
  ↓
若有超期反馈：
  ├─ 追加到 archived_feedback/YYYYMM.md
  └─ 从 project_memory.md 删除已归档项
  ↓
继续恢复流程
```

### Part B: 三层审查流程

```
B0: openspec 设计偏差审查
  ├─ 分析历史文档提取用户提问反馈（F1-F10）
  ├─ Read yesterday-changes-deep-audit/spec.md R5
  ├─ Read p0-bugfix-round1/spec.md Out of Scope
  ├─ 列出 7 项缺失（G1-G7）+ 5 项偏差（D1-D5）
  └─ 输出《openspec 设计偏差审查报告》
  ↓
B1: 代码实施审查
  ├─ Read p0-bugfix-round1/design.md
  ├─ 逐项 Grep/Read 源码（C-01/V-01/F-01/M-01/M-02）
  └─ git status 确认提交
  ↓
B2: 交付质量审查
  ├─ 读取 E2E 结果
  ├─ Read updateLog.md
  ├─ 确认 L2 验证
  └─ 输出《主线任务完成质量审查报告》
  ↓
失败项进入 Part C
```

### Part C: 三层修复流程

```
C1: openspec 偏差修复
  ├─ 基于 B0 报告明确 7 项缺失归属
  ├─ F-08 明确归属专门 spec（不悬空）
  ├─ 沉淀 openspec 偏差审查规范
  └─ G5/G6/G7 强化 project_memory 规范执行
  ↓
C2: 代码/测试修复
  ├─ UI dump 确认真实入口 → 修复 F-P0-6 用例
  ├─ git add + commit 18 文件
  └─ 更新 updateLog.md
  ↓
C3: E2E 重跑 + L2 验证
  ├─ venv Python 重跑 E2E
  └─ UI dump + Python 解析 XML 确认功能生效
  ↓
输出《打包功能与设计差距修复报告》
```

## File Changes

### 1. project_memory.md（新增小节，Part A + C1）

**路径**: `c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\project_memory.md`

**变更**: 
- 在"活跃 Spec 清单"之前新增"用户反馈与决策记录"小节（Part A）
- 新增 P0 规范 18："openspec 生成前必须对照用户提问反馈清单"（Part C1）

```markdown
## 用户反馈与决策记录（保留最近 7 天，超期归档到 archived_feedback/）

### 2026-07-09

- `[HH:MM] 类型 | 触发上下文 | 用户原文/响应 | 影响`
```

### 2. AGENTS.md（更新章节，Part A）

**路径**: `f:\myself\github\WeAgentChat\temp\legado\AGENTS.md`

**变更**: 更新"🔴🔴 强制规则：上下文压缩恢复流程"章节

- 三件套 → 四件套（+用户反馈记录）
- 新增"用户反馈持久化"子小节
- 新增"AskUserQuestion 响应处理"规范
- 恢复后必须输出"已加载的用户反馈清单"

### 3. 归档目录（新建，Part A）

**路径**: `c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\archived_feedback\`

**变更**: 新建目录，存放按月归档的用户反馈

### 4. user_rules.md（补充规范，Part A，可选）

**路径**: 用户级 user_rules

**变更**: 在"用户交互强制规范"补充"用户反馈持久化"小节（跨项目通用）

### 5. F-P0-6 测试用例（修复，Part C2）

**路径**: `f:\myself\github\WeAgentChat\temp\legado\docs\tests\F-P0-6-source-manage.md`

**变更**: 修复 UI 入口路径（基于 UI dump 确认的真实入口）

### 6. updateLog.md（更新，Part C2）

**路径**: `f:\myself\github\WeAgentChat\temp\legado\app\src\main\assets\updateLog.md`

**变更**: 顶部追加 2026/07/09 条目，面向用户描述 P0 修复内容

### 7. P0 修复代码（提交，Part C2）

**路径**: 18 个源码文件

**变更**: `git add` + `git commit`，Conventional Commits 格式

### 8. openspec 设计偏差审查报告（新建，Part B0）

**路径**: `f:\myself\github\WeAgentChat\temp\legado\docs\specs\context-compression-feedback-preservation\openspec-deviation-report.md`

**变更**: 输出 10 项用户反馈 + 7 项缺失 + 5 项偏差 + 处理建议

### 9. 主线任务完成质量审查报告（新建，Part B1+B2）

**路径**: `f:\myself\github\WeAgentChat\temp\legado\docs\specs\context-compression-feedback-preservation\audit-report.md`

**变更**: 输出对照 design.md 逐项审查结果 + 交付质量，列出"标记完成但实测失败"项

### 10. 打包功能与设计差距修复报告（新建，Part C1+C2+C3）

**路径**: `f:\myself\github\WeAgentChat\temp\legado\docs\specs\context-compression-feedback-preservation\fix-report.md`

**变更**: 输出 openspec 偏差修复 + 代码测试修复 + E2E/L2 验证结果

## 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| AI 不遵守持久化规范 | 中 | 反馈仍丢失 | 检查点验证 + 用户监督复述环节 |
| project_memory.md 膨胀 | 低 | 恢复变慢 | 定期归档（7天） |
| 反馈记录格式混乱 | 中 | 解析困难 | 固定格式模板 + AI 遵守 |
| 归档时误删未过期反馈 | 低 | 反馈丢失 | 归档前确认日期筛选逻辑 |
| AI 复述不准确 | 中 | 用户需纠正 | 用户确认复述后才继续 |
| Part B0 审查发现大量偏差 | 高 | 修复工作量大 | 按严重度分级，D1 F-08 优先明确归属 |
| Part B1 审查发现代码未提交 | 高 | 代码丢失风险 | Part C2 立即 git commit |
| F-P0-6 用例修复后仍失败 | 中 | 需进一步排查 | UI dump 确认真实入口，循环修复 |
| git commit 冲突 | 低 | 提交失败 | 提交前 git status 确认，冲突时回退 |
| venv E2E 运行失败 | 低 | 无法验证 | 检查 venv 依赖，回退到 manual 验证 |
| updateLog.md 格式错误 | 低 | 用户困惑 | 遵循已有格式模板 |
| F-08 归属 spec 用户不认可 | 中 | 需重新规划 | C1 输出归属建议表交用户确认 |
| openspec 偏差审查主观性 | 中 | 偏差判断不准 | 以历史文档用户原话为依据，非臆测 |
