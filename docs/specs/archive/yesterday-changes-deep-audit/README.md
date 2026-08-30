# 昨日改动深度审查（2026-07-08 全量改动）

> **状态**：✅ 审查完成（29 项 bug + 7 阻塞点 + 1 需求偏差，用户检查点2 已确认）
> **创建日期**：2026-07-09
> **审查范围**：2026-07-08 全量改动（168+ 文件，25768 行新增），重点两大改动
> **审查报告**：[audit-report.md](./audit-report.md)

---

## 功能概述

对 2026-07-08 的全量改动进行深度自我审查，发现并定位 bug。本次审查**只读不改**——发现的 bug 将在用户确认后通过独立 OpenSpec 流程修复。

## 审查背景

用户反馈：
1. 昨天改动过程中"来回横跳，来回改"，存在混乱
2. 明确告知"肯定有 bug，而且不少"，要求 AI 自我反省发现
3. 重点关注两大改动：书源订阅源布局调整 + 内置视频播放器功能性能提升
4. **检查点1反馈（核心）**："书源订阅源布局，让你好好学习书架布局模式，但是你只学到了表象，没有抓住核心，你没有看到书架布局的所有类型以及布局条件影响的对象是谁，现在搞得书源订阅源布局有 bug 还徒有其表"
5. **检查点1二次反馈（核心）**："书架的对象是根据图书的什么信息进行归类的？还有就是书架布局里面的分组样式里面选择标签后当前书架变成什么样，选择文件夹后变成什么样？还有就是昨天为什么大量的去改了订阅源栏目设置里面的二级页面呢？我要的是订阅源栏目首页根据书架布局深度分析设计"

## 审查范围（按优先级）

| 优先级 | 改动模块 | 涉及 spec | 核心文件数 |
|--------|---------|-----------|-----------|
| 🔴 P0 | **首页布局架构对比**（核心维度，用户二次反馈） | - | 6（首页+书架 style1/style2） |
| 🔴 P0 | **书架布局核心机制对比**（核心维度） | - | 8（书架基准源码） |
| 🔴 P0 | 书源/订阅源**管理页**布局重做 | source-layout-redesign + folder-view-welcome-refactor | 20+ |
| 🔴 P0 | 视频播放器（静音+倍速+m3u8缓存） | video-mute-highspeed + video-m3u8-cache | 10+ |
| 🟡 P1 | 数据库 Migration（RssSource defaultValue） | - | 3 |
| 🟡 P1 | 任务清单状态一致性 | 4 个 spec 的 tasks.md | 4 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 审查意图、范围、方法、R4 书架对比 + R5 首页布局要求（R5.6双维度下拉菜单 + R5.7搜索框 + R5.8-R5.12元审查）、S1-S22 审查场景 |
| [design.md](./design.md) | 审查技术方案、ADR、D11 书架架构对比（A1-A6+B1-B6）+ D12 首页布局对比（C1-C8）+ D13 阻塞点分析 + D14 Agent职责边界、文件清单 |
| [tasks.md](./tasks.md) | 审查任务清单（3.1.0书架基准 + 3.1.2 Bug 1-9 + 3.4 Agent-D首页布局 + 3.5阻塞点分析 + 3.6 Agent职责边界）|

## 核心发现：需求理解偏差（检查点1二次反馈，最重要）

### 偏差总结

| 维度 | 昨天实际改的（错误） | 用户要的（正确） |
|------|-------------------|----------------|
| **对象** | RssSourceActivity（订阅源**管理页**，二级页面） | RssFragment（订阅源**首页**，一级页面） |
| **对象** | BookSourceActivity（书源**管理页**，二级页面） | ExploreFragment（发现页**首页**，一级页面） |
| **设计依据** | 只加了 compact/grid adapter 切换 | 应参考书架 style1（Tab+ViewPager）/ style2（单RV混排）深度设计 |

**结论**：昨天的改动**改错了对象**——改了管理页（二级页面），但用户要的是首页（一级页面）参考书架 style1/style2 深度设计。

### 书架分组归类依据（用户问题1答案）

书架根据 **Book.group 字段（Long 类型）** 归类，对应 BookGroup.groupId。
- [Book.kt:79](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/Book.kt#L79): `var group: Long = 0`
- [BookGroup.kt:17](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/entities/BookGroup.kt#L17): `val groupId: Long`（主键）
- 特殊分组 ID：IdAll(-1)、IdLocal(-2)、IdAudio(-3)、IdVideo(-6)、IdError(-11) 等

### 书架分组样式两种形态（用户问题2答案）

| bookGroupStyle | 样式 | Fragment | 书架变成什么样 |
|---------------|------|----------|--------------|
| **0（标签）** | style1 | BookshelfFragment1 | **Tab + ViewPager**：每个分组一个 Tab，顶部 TabLayout 横向滚动，ViewPager 滑动切换，每个 Tab 对应独立 BooksFragment |
| **1（文件夹）** | style2 | BookshelfFragment2 | **单 RV 混排**：根目录分组文件夹+书籍混排（getItems=bookGroups+books），点击文件夹进入子目录，返回键回根目录 |

### 首页现状（C1-C3 缺失）

| 编号 | 缺失 | 说明 |
|------|------|------|
| C1 | 缺 style1 设计 | RssFragment/ExploreFragment 无 Tab+ViewPager，只有文件夹/列表二选一切换 |
| C2 | 缺 style2 设计 | RssFragment 文件夹视图只显示文件夹列表，点击切换到列表+searchView筛选，无书架 style2 的混排+点击进入+返回逻辑 |
| C3 | 缺样式切换机制 | MainActivity 无 sourceGroupStyle 切换 Fragment 机制，RssFragment 只有一个 |

### 双维度下拉菜单设计建议（C4，用户三次反馈核心设计）

书源/订阅源的布局配置对话框应比书架更复杂，支持**双维度独立选择**：

| 维度 | 下拉菜单选项 | 对应字段 |
|------|------------|---------|
| **归类维度** | 按分组 / 按类型 | 按分组=BookSource.group；按类型=BookSource.bookSourceType（[BookSourceType](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/BookSourceType.kt): 文本/音频/图片/文件/视频） |
| **样式维度** | 标签 / 文件夹 | 标签=style1（Tab+ViewPager）；文件夹=style2（单RV混排+点击进入） |

4 种组合矩阵：

| 归类维度 \ 样式维度 | 标签（style1） | 文件夹（style2） |
|-------------------|---------------|----------------|
| 按分组 | 每个分组一个 Tab | 分组文件夹+源混排 |
| 按类型 | 每个类型一个 Tab（文本/音频/图片/文件/视频） | 类型文件夹+源混排 |

**与书架的差异**：书架只有 bookGroupStyle（0=标签/1=文件夹）一个维度，且只按 group 字段归类。书源/订阅源需要双维度独立选择，且增加"按类型"归类选项。

**当前问题**：SourceFolderAdapter.showConfigDialog 的 sourceGroupStyle（0=列表/1=按分组/2=按类型）把"归类维度"和"视图模式"混在一个配置项里，不是双维度独立选择，需重新设计。

### 搜索框设计建议（C5，用户四次反馈核心设计）

首页搜索框应默认带当前归类信息传递给后端查询，**不回填搜索框**：

| 当前归类 | 搜索时后端查询条件 | 搜索框显示 |
|---------|------------------|-----------|
| 按类型=文本 | type=0 + name=用户输入 | 只显示用户输入的关键词 |
| 按分组=小说 | group=小说 + name=用户输入 | 只显示用户输入的关键词 |
| 全部（无归类） | name=用户输入 | 只显示用户输入的关键词 |

**当前 Bug 9**：[RssFragment.kt:276-285](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt#L276-L285) 的 `onFolderClick` 把 `group:$group` 回填到 searchView，搜索框被归类前缀污染，用户搜索名称时需先清空前缀。ExploreFragment 同构问题。

### Bug 9 根因深化（元审查发现）

不仅搜索框回填了归类信息，而且当用户输入名称关键词后，`upRssFlowJob` 的 `searchKey` 不再以 `group:` 开头，会走 `flowEnabled(searchKey)` 分支——**归类信息完全丢失**，用户在"小说"文件夹内搜索名称，实际搜索了全部源。

**DAO 层已有组合查询方法但未被使用**：

| DAO 方法 | 功能 | 当前使用情况 |
|---------|------|------------|
| `flowByTypeSearch(type, searchKey)` | 按类型+名称组合查询 | ❌ 未被搜索框使用 |
| `flowGroupSearchExact(group, searchKey)` | 按分组+名称组合查询 | ❌ 未被搜索框使用 |

修复应直接使用已有 DAO 方法，而非回填搜索框。

## 核心发现：元审查（检查点1五次反馈，设计文档合理性审查）

### 阻塞点（5项）

| 编号 | 阻塞点 | 影响 | 修复方向 |
|------|--------|------|---------|
| BP-1 | RssSource.type（3种）与 BookSource.bookSourceType（5种）语义不一致 | 双维度下拉菜单"按类型"选项需动态调整 | 统一 RssSource.type 语义或明确区分 |
| BP-2 | Bug 9 修复依赖 currentFilter，但 style1/style2 不存在 | Bug 9 修复顺序与首页布局重构有依赖 | 先在现有架构内修复，等重构后再适配 |
| BP-3 | 双维度下拉菜单的 sourceGroupStyle 迁移逻辑未定义 | 用户升级可能丢失配置 | 按 C7 迁移表执行 |
| BP-4 | Agent-A 与 Agent-D 都审查 RssFragment/ExploreFragment | 职责重叠 | Agent-A 审菜单，Agent-D 审布局 |
| BP-5 | Bug 9 主审 Agent 归属不明 | 可能漏审或重复审 | Bug 9 归 Agent-D 主审 |

### 模糊地带（5项）

| 编号 | 模糊地带 | 说明 |
|------|---------|------|
| AM-1 | RssSource.type 语义 | 0=网页/1=图片/2=视频（3种）vs BookSourceType 0=文本/1=音频/2=图片/3=文件/4=视频（5种） |
| AM-2 | 类型文件夹数据模型 | "按类型+文件夹"中类型文件夹是动态生成/预定义/参考BookGroup？推荐方案C（参考BookGroup特殊ID） |
| AM-3 | style1/style2 与 MainActivity 切换 | 是否需要像书架一样在 MainActivity 切换 Fragment？还是只在 RssFragment 内部切换？ |
| AM-4 | currentFilter 语义 | style1（当前Tab）/style2（当前文件夹）/现有RssFragment（group参数）三种情况未统一 |
| AM-5 | DAO 组合查询方法未使用 | flowByTypeSearch/flowGroupSearchExact 已存在但搜索框未调用 |

### 设计不合理（3项）

| 编号 | 不合理 | 修复 |
|------|--------|------|
| UR-1 | 缺少"数据模型一致性"审查维度 | 新增 R5.8 + C6 |
| UR-2 | 缺少"配置项迁移"审查维度 | 新增 R5.9 + C7 |
| UR-3 | Agent-D 3.4.1 与 Agent-A 3.1.0 书架源码审查重叠 | D14 Agent职责边界明确分工 |

## 核心发现：书架对比研究（检查点1反馈后深入研究）

### 根因总结

书源订阅源布局重构**只复制了书架的"配置项命名"和"多 adapter 切换"形式**，但**没有复制 `BaseBooksAdapter<VB>` 共享基类的关键架构**，导致 compact/grid 模式下选择/拖拽/批量操作/校验刷新全部断裂——这正是用户所说的"徒有其表"。

### 书架布局核心机制（A1-A6，正确基准）

| 编号 | 机制 | 说明 |
|------|------|------|
| A1 | 配置项语义 | bookshelfLayout（0-6=Grid列数）/ showBookname（0-2）/ bookGroupStyle（0-1）/ bookshelfSort（0-5） |
| A2 | **BaseBooksAdapter\<VB\> 共享基类** | 统一 DiffUtil/payload/notification/CallBack/selection，三 adapter 继承 |
| A3 | style1 vs style2 | style1（Tab+ViewPager）/ style2（单 RV 混排+getItemViewType） |
| A4 | Fragment 级重建 + RecycledViewPool 隔离 | EventBus.RECREATE 重建 + list/grid 独立 pool |
| A5 | 浏览/管理分离哲学 | BooksFragment（浏览）+ BookshelfManageActivity（管理）分离 |
| A6 | 配置对话框统一管理 | BaseBookshelfFragment.configBookshelf 统一 9 项配置 |

### 书源订阅源布局差距（B1-B6，徒有其表）

| 编号 | 差距 | 导致的 Bug |
|------|------|-----------|
| B1 | **缺共享基类** | Bug 1/3/5（选择/批量/校验断裂） |
| B2 | 无 Fragment 重建 | 状态丢失 |
| B3 | ItemTouchHelper 错位绑定 | Bug 2/4/8（拖拽断裂） |
| B4 | 选择模式只作用 list | Bug 1/3（选择失效） |
| B5 | 无 RecycledViewPool 隔离 | ViewHolder 类型冲突 |
| B6 | 配置对话框与菜单不同步 | Bug 7（排序冲突） |

## 初步发现概览（待深度审查验证）

> 以下为审查计划阶段已初步发现的疑似 bug，将在深度审查阶段验证确认。

### 书架对比新发现 Bug（8 项，检查点1反馈后深入研究）

| 编号 | 严重度 | 摘要 | 对应差距 |
|------|--------|------|---------|
| Bug 1 | 🔴 高 | BookSource compact/grid 选择模式与批量操作完全失效 | B1/B4 |
| Bug 2 | 🟡 中 | BookSource ItemTouchHelper 错位绑定 + isCanDrag 条件不一致 | B3 |
| Bug 3 | 🔴 高 | RssSource compact/grid 选择模式失效 | B1/B4 |
| Bug 4 | 🟡 中 | RssSource DragSelectTouchHelper 失效 | B3 |
| Bug 5 | 🟡 中 | 校验进度刷新在 compact/grid 模式下无效 | B1 |
| Bug 6 | 🟡 中 | 文件夹视图与列表视图互斥，无源计数 | B5 |
| Bug 7 | 🟡 中 | 排序状态在配置对话框与菜单间不同步 | B6 |
| Bug 8 | 🟢 低 | 文件夹视图 ItemTouchHelper 残留 | B3 |
| Bug 9 | 🔴 高 | 搜索框回填归类信息（onFolderClick 把 `group:$group` 回填 searchView，污染用户输入） | C5 |

### 书源订阅源布局（7 项，初步发现）

| 编号 | 严重度 | 摘要 |
|------|--------|------|
| L-01 | 🔴 高 | BookSource 与 RssSource 共享 `AppConfig.sourceSort`，语义不同导致互相干扰 |
| L-02 | 🔴 高 | `onFolderClick` 中 `all_groups` 与 `no_group` 都映射到 `null`，"未分组"显示全部源 |
| L-03 | 🟡 中 | `RssSourceActivity.upSourceFlow` 缺少 `flowWithLifecycleAndDatabaseChange`，数据库变化不刷新 |
| L-04 | 🟡 中 | `sourceLayout` 边界值（>6 或负数）导致布局与 adapter 类型不匹配 |
| L-05 | 🟡 中 | `itemTouchCallback.isCanDrag` 在 collect 中缺少 `layout==0` 检查，网格视图可能误允许拖拽 |
| L-06 | 🟢 低 | `upBookSource` 的 `delay(500)` 与 `upSourceFlow` 的 `delay(100)` 不一致 |
| L-07 | 🔴 高 | 4 个 spec 的 tasks.md 状态与实际完成严重不一致（video-m3u8-cache 全未勾选） |

### 视频播放器（8 项）

| 编号 | 严重度 | 摘要 |
|------|--------|------|
| V-01 | 🔴 高 | `cachePlay` 已 `@Deprecated` 恒返回 false，video-m3u8-cache spec 的 4 处 setUp 实际是空操作 |
| V-02 | 🔴 高 | `SettingsDialog` 缺少 `cb_cache_play` 开关，与 video-m3u8-cache tasks.md 2.1-2.5 严重不一致 |
| V-03 | 🟡 中 | `onPrepared` 中 `muteOnStart=false` 时不显式 `setNeedMute(false)`，player 复用可能残留静音 |
| V-04 | 🔴 高 | 换集 `onPrepared` 重新静音，覆盖用户手动取消静音的状态（体验 bug） |
| V-05 | 🟡 中 | `ChoiceSpeedDialog.onStop` 中 `onItemClickListener!!` 可能 NPE |
| V-06 | 🟡 中 | 15X 倍速实用性：ExoPlayer 音频重采样上限通常 8-10X，15X 音频失真/静音 |
| V-07 | 🟡 中 | `VideoPlay.startPlay` 中 `source==null` 提前 return 导致 `isLoading` 泄漏 |
| V-08 | 🟢 低 | `setVideoSpeed` 中 `mDanmakuContext!!` 潜在 NPE（虽有前置 mDanmakuView 检查） |

---

## 状态标记说明

- 🔄 审查中：审查计划已生成，待用户确认后进入深度审查
- ✅ 审查完成：深度审查完成，bug 报告已交付
