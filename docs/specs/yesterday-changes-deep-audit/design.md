# Design: 昨日改动深度审查

## Technical Approach（技术方案）

### 审查架构

采用"三路并行审查 + 主线交叉验证"架构：

```
                    ┌─ Agent-A: 书源订阅源布局审查（20+ 文件）
                    │
主线（本 AI）──────├─ Agent-B: 视频播放器审查（10+ 文件）
                    │
                    └─ Agent-C: 横向链路审查（配置/菜单/DB Migration）
                              │
                              ▼
                    主线汇总 + 交叉验证
                              │
                              ▼
                    结构化 Bug 报告（带置信度）
```

### 审查维度（每个 Agent 必须覆盖）

| 维度 | 检查点 | 适用模块 |
|------|--------|---------|
| **D12 首页布局架构对比**（核心，用户二次反馈） | RssFragment/ExploreFragment 是否参考书架 style1（Tab+ViewPager）/ style2（单RV混排+点击进入）深度设计 | 首页 |
| **D11 书架架构对比**（核心） | 以书架 BaseBooksAdapter 共享基类 + Fragment 级重建 + RecycledViewPool 隔离 + 浏览/管理分离为基准，对比书源订阅源布局的差距 | 书源订阅源 |
| D1 配置闭环 | PreferKey → AppConfig → 读取点 → 生效 | 全部 |
| D2 菜单闭环 | menu XML → onCompatOptionsItemSelected → 实际处理 | 书源订阅源 |
| D3 数据流闭环 | DAO Flow → map → collect → adapter.setItems | 书源订阅源 |
| D4 状态机一致性 | currentType/currentGroup/inSubDirectory/isShowingFolder 状态转换 | 书源订阅源 |
| D5 多视图一致性 | 列表/紧凑/网格三视图 adapter 与 LayoutManager 匹配 | 书源订阅源 |
| D6 生命周期 | onPrepared/onPause/onResume/onDestroy 资源释放与状态保持 | 视频 |
| D7 空安全 | `!!` / `?.` / 可空字段访问 | 全部 |
| D8 边界值 | 负数/0/超范围/空集合/空字符串 | 全部 |
| D9 配置耦合 | 跨模块共享配置项的语义一致性 | 全部 |
| D10 资源泄漏 | player/release/coroutine job 是否正确释放 | 视频 |
| **D13 阻塞点与依赖关系**（元审查新增） | BP-1~BP-5 阻塞点分析 + Bug 9 修复与首页布局重构依赖 + currentFilter 语义统一 | 全部 |
| **D14 Agent 职责边界**（元审查新增） | Agent-A/B/C/D 分工边界 + 文件重叠处理 + Bug 9 主审归属 | 全部 |

#### D12 首页布局架构对比基准（用户检查点1二次反馈核心）

**书架 style1/style2 两种 Fragment 架构（正确基准）**：

| 样式 | 配置项 | Fragment | 架构 | 分组展示方式 |
|------|--------|---------|------|------------|
| **style1（标签）** | bookGroupStyle=0 | BookshelfFragment1 | Tab + ViewPager | 每个分组一个 Tab，ViewPager 滑动切换，每个 Tab 对应独立 BooksFragment |
| **style2（文件夹）** | bookGroupStyle=1 | BookshelfFragment2 | 单 RV 混排 | 根目录：分组文件夹+书籍混排（getItems=bookGroups+books）；点击文件夹进入子目录；返回键回根目录 |

**MainActivity 切换机制（A7，正确基准）**：
- `getFragmentId`: `if (AppConfig.bookGroupStyle == 1) idBookshelf2 else idBookshelf1`
- 切换 bookGroupStyle 时 Fragment 重建

**首页（RssFragment/ExploreFragment）现状（C1-C3，缺失）**：

| 编号 | 缺失 | 书架怎么做（正确） | 首页怎么做（缺失） |
|------|------|------------------|------------------|
| C1 | 缺 style1 设计 | BookshelfFragment1 Tab+ViewPager，每组一 Tab | RssFragment 无 Tab+ViewPager，只有文件夹/列表二选一 |
| C2 | 缺 style2 设计 | BookshelfFragment2 单RV混排，点击进入+返回 | RssFragment 文件夹视图只显示文件夹列表，点击切换到列表+searchView筛选，无混排无进入逻辑 |
| C3 | 缺样式切换机制 | MainActivity 按 bookGroupStyle 切换 Fragment | MainActivity 无 sourceGroupStyle 切换 Fragment 机制，RssFragment 只有一个 |

**双维度下拉菜单设计建议（C4，用户三次反馈核心设计）**：

书源/订阅源的布局配置对话框应比书架更复杂，支持**双维度独立选择**：

| 维度 | 下拉菜单选项 | 对应字段 | 说明 |
|------|------------|---------|------|
| **归类维度** | 按分组 / 按类型 | 按分组=BookSource.group / RssSource.group；按类型=BookSource.bookSourceType / RssSource.type | BookSourceType: default(0 文本)/audio(1 音频)/image(2 图片)/file(3 文件)/video(4 视频) |
| **样式维度** | 标签 / 文件夹 | 标签=style1（Tab+ViewPager）；文件夹=style2（单RV混排+点击进入） | 参考书架 bookGroupStyle |

4 种组合矩阵：

| 归类维度 \ 样式维度 | 标签（style1） | 文件夹（style2） |
|-------------------|---------------|----------------|
| 按分组 | style1，每个分组一个 Tab | style2，分组文件夹+源混排 |
| 按类型 | style1，每个类型一个 Tab（文本/音频/图片/文件/视频） | style2，类型文件夹+源混排 |

**与书架的差异**：书架只有 bookGroupStyle（0=标签/1=文件夹）一个维度，且只按 group 字段归类。书源/订阅源需要双维度独立选择，且增加"按类型"归类选项。

**当前 SourceFolderAdapter.showConfigDialog 的问题**：sourceGroupStyle（0=列表/1=按分组/2=按类型）把"归类维度"和"视图模式"混在一个配置项里，不是双维度独立选择，需重新设计。

**搜索框设计建议（C5，用户四次反馈核心设计）**：

首页搜索框应默认带当前归类信息传递给后端查询，**不回填搜索框**：

| 当前归类 | 搜索时后端查询条件 | 搜索框显示 |
|---------|------------------|-----------|
| 按类型=文本 | type=0 + name=用户输入 | 只显示用户输入的关键词 |
| 按类型=音频 | type=1 + name=用户输入 | 只显示用户输入的关键词 |
| 按分组=小说 | group=小说 + name=用户输入 | 只显示用户输入的关键词 |
| 全部（无归类） | name=用户输入 | 只显示用户输入的关键词 |

**设计要点**：
- 归类信息作为独立的筛选条件（currentFilter 状态）传递给后端，与搜索关键词分离
- 搜索框只接收用户输入的名称关键词，不显示 `group:xxx` 或 `type:xxx` 前缀
- DAO 层需新增组合查询方法（如 `flowByTypeAndName(type, name)` / `flowByGroupAndName(group, name)`）

**当前 RssFragment/ExploreFragment 的问题（Bug 9）**：
- `onFolderClick` 把 `group:$group` 回填到 searchView（`searchView.setQuery("group:$group", true)`）
- 搜索框被归类前缀污染，用户搜索名称时需先清空前缀
- 归类信息与搜索关键词混为一谈，是错误设计

**DAO 组合查询方法发现（C5.1，元审查发现 AM-5）**：

审查 DAO 层发现，**组合查询方法已存在但未被搜索框使用**：

| DAO 方法 | 文件:行号 | 功能 | 当前使用情况 |
|---------|---------|------|------------|
| `flowByTypeSearch(type, searchKey)` | BookSourceDao.kt:105-115 | 按类型+名称组合查询 | ❌ 未被 ExploreFragment 搜索框使用 |
| `flowByTypeSearch(type, searchKey)` | RssSourceDao.kt:71-80 | 按类型+名称组合查询 | ❌ 未被 RssFragment 搜索框使用 |
| `flowGroupSearchExact(group, searchKey)` | BookSourceDao.kt:117-130 | 按分组+名称组合查询 | ❌ 未被 ExploreFragment 搜索框使用 |
| `flowGroupSearchExact(group, searchKey)` | RssSourceDao.kt:82-94 | 按分组+名称组合查询 | ❌ 未被 RssFragment 搜索框使用 |

**Bug 9 根因深化**：不仅搜索框回填了归类信息，而且当用户输入名称关键词后，`upRssFlowJob` 的 `searchKey` 不再以 `group:` 开头，会走 `flowEnabled(searchKey)` 分支——**归类信息完全丢失**，用户在"小说"文件夹内搜索名称，实际搜索了全部源。修复应直接使用已有的 `flowGroupSearchExact` / `flowByTypeSearch` 方法。

**数据模型一致性设计建议（C6，元审查发现 BP-1/AM-1）**：

RssSource.type 与 BookSource.bookSourceType 语义不一致：

| 字段 | 所属实体 | 注解 | 类型定义 | 类型数量 |
|------|---------|------|---------|---------|
| `bookSourceType` | BookSource | @BookSourceType.Type | 0=文本/1=音频/2=图片/3=文件/4=视频 | 5种 |
| `type` | RssSource | 无注解 | 0=网页/1=图片/2=视频 | 3种 |

**影响**：双维度下拉菜单"按类型"归类在订阅源上只有3种类型，书源有5种。下拉菜单选项需根据源类型动态调整，或统一 RssSource.type 语义。

**配置项迁移设计建议（C7，元审查发现 BP-3）**：

双维度下拉菜单重新设计后，现有 sourceGroupStyle 迁移逻辑：

| 现有 sourceGroupStyle | 现有含义 | 迁移后归类维度 | 迁移后样式维度 |
|----------------------|---------|--------------|--------------|
| 0（列表） | 列表视图 | 无（不归类） | 列表（无Tab/无文件夹） |
| 1（按分组） | 分组文件夹 | 按分组 | 文件夹（style2） |
| 2（按类型） | 类型文件夹 | 按类型 | 文件夹（style2） |

**注意**：现有 sourceGroupStyle=1/2 隐含了"文件夹"样式，但没有"标签"样式的选项。迁移后需让用户能选择"标签"样式。

**类型文件夹数据模型设计建议（C8，元审查发现 AM-2）**：

"按类型+文件夹"组合中类型文件夹的数据模型未定义：

| 方案 | 说明 | 优缺点 |
|------|------|--------|
| 方案A：动态生成 | 根据数据库中实际存在的类型动态生成文件夹（如只有文本和视频源，只显示2个文件夹） | 优点：自适应；缺点：文件夹顺序不稳定 |
| 方案B：预定义 | 预定义所有类型文件夹（文本/音频/图片/文件/视频），空文件夹不显示或显示"0个源" | 优点：稳定；缺点：可能有空文件夹 |
| 方案C：参考BookGroup | 像 BookGroup 的 IdAudio(-3)/IdVideo(-6) 特殊分组ID，定义类型文件夹的虚拟ID | 优点：与书架一致；缺点：BookSource/RssSource 无"类型分组"实体表 |

**推荐方案C**：参考 BookGroup 特殊分组ID机制，定义类型文件夹的虚拟ID，无需新建实体表。

#### D13 阻塞点与依赖关系分析（元审查新增维度）

**BP-1: RssSource.type 语义不一致（阻塞双维度下拉菜单设计）**
- 阻塞点：订阅源"按类型"归类只有3种类型，书源有5种，下拉菜单选项需动态调整
- 修复方向：统一 RssSource.type 语义为 BookSourceType，或明确区分两者的类型定义

**BP-2: Bug 9 修复与首页布局重构的依赖关系**
- 阻塞点：Bug 9 的"正确设计"依赖 currentFilter 状态，currentFilter 在 style1/style2 下语义不同，但 style1/style2 不存在
- 修复方向：先在现有 RssFragment 架构内修复 Bug 9（使用已有 DAO 组合查询方法），等首页布局重构后再适配 style1/style2

**BP-3: 配置项迁移（阻塞双维度下拉菜单实施）**
- 阻塞点：现有 sourceGroupStyle 值如何迁移到双维度配置
- 修复方向：按 C7 迁移表执行

**BP-4: Agent-A 与 Agent-D 职责重叠**
- 阻塞点：两者都审查 RssFragment/ExploreFragment
- 修复方向：Agent-A 只审查菜单处理（D2），Agent-D 只审查布局架构（D12），Bug 9 归 Agent-D（因搜索框属于首页布局功能）

**BP-5: Bug 9 主审 Agent 归属**
- 阻塞点：Bug 9 跨 Agent-A D3 数据流和 Agent-D D12 首页布局
- 修复方向：Bug 9 归 Agent-D 主审（首页布局+搜索框），Agent-A 辅助验证 DAO 数据流

#### D14 Agent 职责边界与协作（元审查新增维度）

| Agent | 主审范围 | 禁止越界 | 文件重叠处理 |
|-------|---------|---------|------------|
| Agent-A | 书架基准源码（3.1.0）+ 书源订阅源管理页（3.1.1）+ Bug 1-8（3.1.2） | 不审查 RssFragment/ExploreFragment 的布局架构（归 Agent-D） | BookshelfFragment1/2.kt 只读共享基类部分（A2），style1/style2 架构归 Agent-D |
| Agent-B | 视频播放器（3.2） | 不审查非视频文件 | 无重叠 |
| Agent-C | 横向链路（3.3） | 不审查 UI 布局 | DAO 方法 SQL 正确性归 Agent-C，DAO 方法使用情况归 Agent-D |
| Agent-D | 首页布局架构对比（3.4）+ Bug 9（3.4.3.7）+ 数据模型/配置迁移/DAO使用（3.4.3.8-3.4.3.11） | 不审查管理页（归 Agent-A） | RssFragment/ExploreFragment 的菜单处理归 Agent-A，布局架构归 Agent-D |

#### D11 书架架构对比基准（A1-A6 核心机制 + B1-B6 差距）

**书架布局核心机制（A1-A6，正确基准）**：

| 编号 | 机制 | 书架实现 | 影响对象 |
|------|------|---------|---------|
| A1 | 配置项语义 | bookshelfLayout（0-6，数值=Grid列数）/ showBookname（0-2）/ bookGroupStyle（0-1）/ bookshelfSort（0-5） | BooksFragment.adapter 选择 + ItemDecoration 列数 + showBookname 显示 |
| A2 | **BaseBooksAdapter\<VB\> 共享基类** | 统一 DiffUtil/payload/notification/CallBack/selection，三 adapter（List/List2/Grid）继承 | 选择/批量操作/拖拽/校验刷新 等跨 adapter 共享能力 |
| A3 | style1 vs style2 | style1（Tab+ViewPager，每组一 Fragment）/ style2（单 RV 混排+getItemViewType） | Fragment 隔离 vs 单 RV 混排 |
| A4 | Fragment 级重建 + RecycledViewPool 隔离 | postEvent(EventBus.RECREATE) 重建 Fragment + booksListRecycledViewPool/booksGridRecycledViewPool 独立 | 布局切换时状态恢复 + ViewHolder 类型隔离 |
| A5 | 浏览/管理分离哲学 | BooksFragment（浏览，只读）+ BookshelfManageActivity（管理，选择/批量/拖拽） | 职责清晰，浏览界面不承担管理功能 |
| A6 | 配置对话框统一管理 | BaseBookshelfFragment.configBookshelf 统一管理 9 项配置 + 边界校验 + RecycledViewPool 清理 | 菜单与对话框配置一致 |

**书源订阅源布局差距（B1-B6，徒有其表）**：

| 编号 | 差距 | 书架怎么做（正确） | 书源订阅源怎么做（错误） | 导致的 Bug |
|------|------|------------------|----------------------|-----------|
| B1 | **缺共享基类** | BaseBooksAdapter\<VB\> 统一 selection/notification/CallBack | 三 adapter 各自独立，无共享基类 | Bug 1/3/5（选择/批量/校验断裂） |
| B2 | 无 Fragment 重建 | EventBus.RECREATE 重建 Fragment | applyListView 直接替换 layoutManager+adapter | Bug 10（状态丢失） |
| B3 | ItemTouchHelper 错位绑定 | BooksFragment 按 bookshelfLayout 绑定当前 adapter | itemTouchCallback by lazy 永远绑 list adapter | Bug 2/4/8（拖拽断裂） |
| B4 | 选择模式只作用 list | BaseBooksAdapter 统一 selection | selectAll/revertSelection 硬编码 adapter.selection | Bug 1/3（选择失效） |
| B5 | 无 RecycledViewPool 隔离 | list/grid 独立 pool | 共用同一 pool | ViewHolder 类型冲突 |
| B6 | 配置对话框与菜单不同步 | configBookshelf 统一管理 | 菜单强制 sourceSort=0，对话框设 sourceSort=1 | Bug 7（排序冲突） |

### 审查产出格式（每个 bug）

```
### BUG-XX: [标题]
- 严重度: 🔴高 / 🟡中 / 🟢低
- 置信度: 高(代码证据确凿) / 中(逻辑推断) / 低(需真机验证)
- 文件: path/to/file.kt:LXX-LYY
- 根因: [为什么会产生这个 bug]
- 影响: [用户可感知的现象]
- 修复方向: [建议的修复思路，不实际修复]
```

## Architecture Decisions（架构决策）

### AD-01: 审查与修复分离

- **Context**: 用户要求自我反省发现 bug，但 OpenSpec 流程要求修复也需四文档
- **Concern**: 审查与修复混在一个 OpenSpec 会导致文档臃肿、检查点混乱
- **Decision**: 本 OpenSpec 只做审查（只读不改），bug 修复另开独立 OpenSpec
- **Goal**: 审查专注发现问题，修复专注解决问题，职责清晰
- **Tradeoff**: 用户需两次确认（审查报告 + 修复方案），流程稍长
- **Status**: Accepted

### AD-02: 多 Agent 并行而非串行

- **Context**: 168+ 文件改动，单 Agent 上下文超限
- **Concern**: 串行审查耗时长，且单 Agent 容易因上下文压缩丢失发现
- **Decision**: 按模块拆分为 3 个并行 Agent（书源订阅源/视频/横向链路）
- **Goal**: 最大化审查覆盖面，降低单 Agent 上下文压力
- **Tradeoff**: 跨模块耦合 bug 可能漏报，需主线专门检查
- **Status**: Accepted

### AD-03: 不依赖 E2E 测试发现 bug

- **Context**: 昨天 E2E 测试基础设施刚建立，未验证可靠
- **Concern**: E2E 测试只能发现运行期崩溃，无法发现逻辑/体验/配置耦合 bug
- **Decision**: 以静态源码审查为主，E2E 仅作辅助验证手段
- **Goal**: 发现编译通过但逻辑错误的 bug
- **Tradeoff**: 运行期才暴露的 bug（ANR/内存泄漏）可能漏报
- **Status**: Accepted

### AD-04: tasks.md 不作为审查依据

- **Context**: 初步发现 video-m3u8-cache/tasks.md 全部 [ ] 未勾选但 AOAdapt 说完成
- **Concern**: tasks.md 状态与实际代码脱节，作为审查依据会误导
- **Decision**: 以源码实际状态为唯一审查依据，tasks.md 仅作为"不一致问题"的审查对象
- **Goal**: 避免被错误的任务状态误导
- **Tradeoff**: 无法快速定位"应做未做"的任务，需全量审查源码
- **Status**: Accepted

### AD-05: 书架架构对比作为核心审查维度（用户检查点1反馈）

- **Context**: 用户在检查点1反馈"只学到了表象，没有抓住核心，你没有看到书架布局的所有类型以及布局条件影响的对象是谁，现在搞得书源订阅源布局有 bug 还徒有其表"
- **Concern**: 初步审查计划只从"配置项/菜单/数据流"等通用维度审查，未以书架布局核心架构为基准对比，会漏掉"徒有其表"的根本性架构 bug
- **Decision**: 新增 D11 书架架构对比维度作为核心，建立 A1-A6 书架核心机制基准 + B1-B6 差距清单，逐项定位 Bug 1-8
- **Goal**: 抓住书架布局的"共享基类 + Fragment 重建 + RecycledViewPool 隔离 + 浏览/管理分离"核心，对比书源订阅源布局的架构性缺陷
- **Tradeoff**: 审查工作量增加（需先深入研究书架源码），但能发现根因性 bug 而非表面 bug
- **Status**: Accepted

## Data Flow（审查数据流）

```
1. 主线读取 4 个 spec 的 tasks.md + AOAdapt 日志 → 建立预期完成清单
2. 主线读取核心源码（BookSourceActivity/RssSourceActivity/VideoPlayer/VideoPlay/...）→ 初步发现 15 个疑似 bug
3. 主线生成审查计划四文档 → 🛑检查点1：用户确认（用户反馈"徒有其表"）
3.5 主线启动书架对比研究 Agent → 深入研究书架布局核心机制（A1-A6）+ 对比差距（B1-B6）→ 发现 Bug 1-8
4. 主线更新四文档纳入 D11 书架架构对比维度 → 🛑检查点1（重新确认）
5. 启动 3 个并行审查 Agent：
   - Agent-A 输入: 书架核心源码 + 书源订阅源相关 20+ 文件路径 + D1-D5/D9/D11 维度（含 Bug 1-8 验证）
   - Agent-B 输入: 视频相关 10+ 文件路径 + D6-D8/D10 维度
   - Agent-C 输入: 横向链路（AppConfig/PreferKey/menu/DatabaseMigrations）+ D1/D9 维度
6. 各 Agent 输出: 该模块的 bug 清单（按 BUG-XX 格式）
7. 主线汇总: 合并去重 + 交叉验证 + 补充跨模块耦合 bug
8. 主线元审查四文档合理性 → 发现 5 阻塞点 + 3 设计不合理 + 5 模糊地带 → 更新四文档纳入 R5.8-R5.12 + S20-S22 + C6-C8 + D13-D14 + 3.5-3.6
9. 主线生成完整 bug 报告 → 🛑检查点2：用户确认
10. 用户确认后: 对 bug 开独立 OpenSpec 修复
```

## File Changes（审查文件清单）

> 本审查不修改任何文件，以下为审查对象清单。

### 书架布局核心源码审查清单（Agent-A 基准，D11 维度）

> 此清单为书架布局的"正确基准"源码，Agent-A 审查书源订阅源布局时必须以此对比。

| 文件 | 审查重点（作为基准） |
|------|---------|
| `app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt` | A6 配置对话框统一管理 + 边界校验 + RecycledViewPool 清理 + EventBus.RECREATE |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/style1/books/BooksFragment.kt` | A1/A2/A4 adapter 按 bookshelfLayout 选择 + GridLayoutManager 列数 + RecycledViewPool 隔离 |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/adapter/BaseBooksAdapter.kt` | A2 共享基类（DiffUtil/payload/notification/CallBack/selection） |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/adapter/BooksAdapterList.kt` | A2 继承 BaseBooksAdapter |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/adapter/BooksAdapterList2.kt` | A2 继承 BaseBooksAdapter |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/adapter/BooksAdapterGrid.kt` | A2 继承 BaseBooksAdapter |
| `app/src/main/java/io/legado/app/ui/main/MainViewModel.kt` | A4 booksListRecycledViewPool/booksGridRecycledViewPool 独立 pool |
| `app/src/main/java/io/legado/app/ui/book/manage/BookshelfManageActivity.kt` | A5 管理界面（选择/批量/拖拽）与浏览分离 |

### 书源订阅源布局审查清单（Agent-A，D1-D5/D9/D11 维度）

| 文件 | 审查重点 |
|------|---------|
| `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt` | D2/D3/D4/D5/D11（对比 BaseBookshelfFragment + BooksFragment） |
| `app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt` | D2/D3/D4/D5/D11（对比 BaseBookshelfFragment + BooksFragment） |
| `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapter.kt` | D5/D11（对比 BaseBooksAdapter 共享基类） |
| `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapterCompact.kt` | D5/D11（是否继承共享基类？是否有 selection？） |
| `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapterGrid.kt` | D5/D11（是否继承共享基类？是否有 selection？） |
| `app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceAdapterCompact.kt` | D5/D11（是否继承共享基类？是否有 selection？） |
| `app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceAdapterGrid.kt` | D5/D11（是否继承共享基类？是否有 selection？） |
| `app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt` | D1/D5/D11（文件夹视图是否实现 ItemTouchHelper.Callback？） |
| `app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt` | D2 |
| `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | D2 |
| `app/src/main/res/menu/book_source.xml` | D2 |
| `app/src/main/res/menu/rss_source.xml` | D2 |
| `app/src/main/res/menu/main_explore.xml` | D2 |
| `app/src/main/res/menu/main_rss.xml` | D2 |
| `app/src/main/res/layout/dialog_source_folder_config.xml` | D1 |
| `app/src/main/res/layout/item_book_source_compact.xml` | D5 |
| `app/src/main/res/layout/item_book_source_grid.xml` | D5 |
| `app/src/main/res/layout/item_rss_source_compact.xml` | D5 |
| `app/src/main/res/layout/item_rss_source_grid.xml` | D5 |
| `app/src/main/res/layout/item_source_folder_grid.xml` | D5 |

### 视频播放器审查清单（Agent-B）

| 文件 | 审查重点 |
|------|---------|
| `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt` | D6/D7/D8 |
| `app/src/main/java/io/legado/app/model/VideoPlay.kt` | D6/D8/D10 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | D7/D8 |
| `app/src/main/java/io/legado/app/ui/video/config/SettingsDialog.kt` | D1 |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | D6/D10 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoPlayerManager.kt` | D6/D10 |
| `app/src/main/java/io/legado/app/help/gsyVideo/ExoVideoManager.kt` | D6/D10 |
| `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt` | D6 |
| `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt` | D6/D10 |
| `app/src/main/res/layout/video_layout_controller_full.xml` | D5 |
| `app/src/main/res/layout/video_layout_controller.xml` | D5 |
| `app/src/main/res/layout/dialog_video_settings.xml` | D1 |

### 横向链路审查清单（Agent-C）

| 文件 | 审查重点 |
|------|---------|
| `app/src/main/java/io/legado/app/constant/PreferKey.kt` | D1 |
| `app/src/main/java/io/legado/app/help/config/AppConfig.kt` | D1/D9 |
| `app/src/main/java/io/legado/app/data/dao/BookSourceDao.kt` | D3 |
| `app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt` | D3 |
| `app/src/main/java/io/legado/app/data/entities/RssSource.kt` | D8 |
| `app/src/main/java/io/legado/app/data/DatabaseMigrations.kt` | D8 |
| `app/src/main/java/io/legado/app/data/AppDatabase.kt` | D8 |
| `app/schemas/io.legado.app.data.AppDatabase/93.json` | D8 |
| `app/src/main/res/values/strings.xml` | D1 |
| `app/src/main/res/values-zh/strings.xml` | D1 |
