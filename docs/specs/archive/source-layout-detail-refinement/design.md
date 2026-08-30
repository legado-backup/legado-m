# Design: 书源/订阅源布局细节优化 + 视频播放细节优化

## Technical Approach

### D1: 标签+分组两模式（首页 RssFragment/ExploreFragment）

> **实施对象调整**（用户明确）：D1 对象是**首页**（RssFragment/ExploreFragment），非管理页（BookSourceActivity/RssSourceActivity）。管理页保持现有列表/文件夹视图不变。

**参考实现**：
- 书架 BookshelfFragment1（标签模式）：TabLayout + ViewPager，标签平铺顶部，每个标签对应一个 BooksFragment
- 书架 BookshelfFragment2（分组模式）：单 RecyclerView 混排，分组作为卡片，点击进入文件夹

**实际采用方案**（用户选方案B）：
- **方案A**（未采用）：TabLayout + ViewPager + 多 Fragment，复刻 BookshelfFragment1 架构，工作量大
- **方案B**（采用）：TabLayout + 单 RecyclerView，点击标签切换 currentGroup 刷新数据，复用现有 upRssFlowJob/upExploreData 逻辑，不支持左右滑动

**双维度正交设计**：

| 维度 | 配置项 | 值 | 含义 |
|------|--------|-----|------|
| 归类维度 | `sourceGroupStyle` | 0=列表/1=按类型/2=按分组 | 数据如何归类 |
| 样式维度 | `sourceGroupMode` | 0=标签/1=分组 | 归类后如何展示 |

**三模式架构**：
- 列表模式（sourceGroupStyle==0）：纯列表，无 Tab，无文件夹
- 标签模式（sourceGroupStyle!=0 && sourceGroupMode==0）：TabLayout 可见 + 列表，点击 Tab 设置 currentGroup 刷新数据
- 分组模式（sourceGroupStyle!=0 && sourceGroupMode==1）：文件夹视图（现有 folderAdapter 逻辑）

**Tab.tag 存 currentGroup**：避免 position 映射不稳定（groups 动态变化时 position→group 映射会错位），onTabSelected 时直接取 `tab.tag as? String`。

**关键文件**：
- `fragment_rss.xml` / `fragment_explore.xml`：新增 TabLayout（id=tab_layout, visibility=gone, tabMode=scrollable）
- `RssFragment.kt` / `ExploreFragment.kt`：新增 isTagMode/applyView/initTabLayout/upTabLayout，统一视图应用逻辑
- `dialog_source_folder_config.xml`：新增"展示模式"Spinner（sp_group_mode）
- `SourceFolderAdapter.kt`：showConfigDialog 新增 sourceGroupMode 初始化和保存
- `AppConfig.kt` / `PreferKey.kt`：新增 sourceGroupMode 配置项
- `arrays.xml` / `strings.xml`：新增展示模式数组和字符串

### D2: 修复按类型分组一级页面不生效 + 源类型+源分组两维度

**Bug 根因分析**（用户反馈"一级页面类型分类从来都没成功过"）：

当前 BookSourceActivity.kt 按类型分组逻辑：
1. `applyConfigChange()` line 436：sourceGroupStyle == 1 时显示文件夹视图
2. `upFolderView()` line 448-455：创建类型文件夹列表（全部/文本/音频/图片/文件/视频）
3. `onFolderClick()` line 908-918：点击类型文件夹设置 currentType
4. `upBookSource()` line 485-488：currentType >= 0 时查询 flowByType(currentType)

**待排查的 bug 点**（实施时需源码核实）：
- `flowByType()` DAO 方法是否正确查询 bookSourceType 字段
- bookSourceType 值映射是否正确（0=文本/1=音频/2=图片/3=文件/4=视频）
- 文件夹视图是否正确显示（upFolderView 是否被调用）
- 点击文件夹后 isShowingFolder 是否正确切换为 false

**数据基础**：
- BookSource 有 `bookSourceType: Int` 字段（line 42，待确认值含义）
- BookSource 有 `group: String` 字段（源分组信息）
- RssSource 有 `group: String` 字段（需确认是否有 type 字段）

**实现方案**：

1. **先修复 bug**：排查并修复按类型分组一级页面不生效的问题
2. **再支持两维度组合**：将"按类型/按分组"互斥单选改为可组合的两维度

**关键文件**：
- `BookSourceActivity.kt`：修复 bug + 分组逻辑支持两维度组合
- `RssSourceActivity.kt`：同上
- `BookSourceDao` / `RssSourceDao`：确认 flowByType 方法正确性 + 可能新增两维度组合查询

### D3: 订阅源二级设置还原列表

**当前问题**：订阅源点击文件夹后进入二级页面，可能延续了文件夹/布局概念。

**实现方案**：订阅源首屏使用布局概念（标签/文件夹），但点击进入二级页面后还原为默认列表展示。

**关键文件**：
- `RssSourceActivity.kt`：onFolderClick 进入二级页面时强制使用列表视图

### D4: 搜索框参考书架

**参考实现**：
- BookshelfFragment1/2 都实现了 SearchView.OnQueryTextListener
- F2 修复已用 currentGroup 解耦搜索框与分组筛选（RssFragment.kt:82）

**实现方案**：确保书源/订阅源搜索框不回填 type:/group: 到搜索框，与标签/分组模式配合。

**关键文件**：
- `BookSourceActivity.kt`：搜索框逻辑
- `RssSourceActivity.kt`：搜索框逻辑

### D5: 视频缓存下拉选择

**当前实现**：
- `SettingsDialog.kt:69-82`：已有缓存容量选择（50/100/200/500 MB 单选对话框）
- `VideoPlay.videoCacheSize`：默认 100MB，可配置
- `ExoPlayerHelper.kt:126`：从 videoCacheSize 读取，范围保护 50-500MB

**用户反馈**：用户说"滚动下拉选择"且"想调整怎么办"——当前是单选对话框（setSingleChoiceItems），用户想要 Spinner 下拉。

**实现方案**：
1. 将 SettingsDialog 中的单选对话框改为 Spinner 下拉选择
2. 评估是否需要在全局设置（OtherConfigFragment）增加视频缓存设置入口，让用户更容易找到

**关键文件**：
- `SettingsDialog.kt`：tvVideoCacheSize 点击逻辑改为 Spinner
- `dialog_video_settings.xml`：缓存大小项改为 Spinner 布局
- 可选：`pref_config_other.xml` 新增全局视频缓存设置入口

### D6: 视频倍速保留 15x 不动

**用户决策**：方案C——保留 15x 不动，不处理音频失真问题。

**无需代码修改**。本项仅记录用户决策，倍速列表保持现状（0.5f~15.0f）。

## Architecture Decisions

### ADR-1: D1 标签模式实现方式

**Context**：书源/订阅源需要标签模式（Tab 平铺展示分组标签）

**Decision**：在现有 Activity 中切换 UI（Tab 模式 vs 文件夹模式），不新建 Fragment

**Rationale**：
- 书源/订阅源管理是 Activity 不是 Fragment（与书架不同）
- 在 Activity 中切换 UI 更简单，避免 Fragment 嵌套复杂性
- 标签模式用 TabLayout + ViewPager 展示不同分组的源列表

### ADR-2: D2 两维度组合实现方式

**Context**：分组类型需要源类型+源分组两维度组合

**Decision**：将现有"按类型/按分组"互斥单选改为两维度独立选择

**Rationale**：
- 当前 source_group_style_new 是三选一（列表/按类型/按分组）
- 改为两维度独立选择：源类型（全部/文本/图片/视频）× 源分组（全部/各分组）
- 两维度可组合筛选，更灵活

### ADR-3: D5 缓存设置入口位置

**Context**：用户找不到视频缓存设置入口

**Decision**：保留视频播放界面设置对话框中的入口，同时新增全局设置入口

**Rationale**：
- 视频播放界面设置对话框已有入口（SettingsDialog.kt），但用户找不到
- 新增全局设置入口（OtherConfigFragment / pref_config_other.xml）让用户更容易发现
- 两处入口同步同一个配置项（VideoPlay.videoCacheSize）

### ADR-4: D6 倍速方案

**Context**：15x 倍速音频失真（ExoPlayer 限制）

**Decision**：方案C——保留 15x 不动，不处理音频失真

**Rationale**：
- 用户检查点1明确选方案C
- 用户接受音频失真，不需要限制倍速
- 无需代码修改

## Data Flow

### D1 标签+分组两模式数据流

```
用户打开配置对话框 → 选择展示模式（标签/分组）
→ 保存 sourceGroupMode 到 AppConfig
→ Activity 根据 sourceGroupMode 切换 UI
  → 标签模式：TabLayout + ViewPager（每个标签对应一个分组的源列表）
  → 分组模式：文件夹卡片（点击进入源列表）
```

### D5 视频缓存下拉选择数据流

```
用户打开视频设置 → Spinner 下拉选择缓存大小
→ 保存到 VideoPlay.videoCacheSize
→ 重启 App 后 ExoPlayerHelper 读取新值初始化 SimpleCache
```

## File Changes

### 新增文件
- 无（复用现有文件结构）

### 修改文件

| 文件 | 变更内容 | 涉及需求 |
|------|---------|---------|
| `dialog_source_folder_config.xml` | 新增"展示模式"Spinner（标签/分组） | D1 |
| `BookSourceActivity.kt` | 根据 sourceGroupMode 切换 UI + 两维度分组逻辑 | D1/D2/D4 |
| `RssSourceActivity.kt` | 同上 + 二级设置还原列表 | D1/D2/D3/D4 |
| `AppConfig.kt` | 新增 sourceGroupMode 配置项 | D1 |
| `PreferKey.kt` | 新增 sourceGroupMode key | D1 |
| `arrays.xml` | 新增展示模式数组 + 源类型数组 | D1/D2 |
| `strings.xml` | 新增字符串资源 | D1/D2 |
| `SettingsDialog.kt` | 缓存大小改为 Spinner 下拉 | D5 |
| `dialog_video_settings.xml` | 缓存大小项改为 Spinner 布局 | D5 |
| `pref_config_other.xml` | 可选：新增全局视频缓存设置入口 | D5 |
| `app/src/main/assets/updateLog.md` | 编译前更新变更日志 | 全部 |

## 待确认项（已全部核实）

1. **D2 bookSourceType 值含义** ✅：BookSource 0=文本/1=音频/2=图片/3=文件/4=视频；RssSource 0=网页/1=图片/2=视频
2. **D2 flowByType DAO 方法正确性** ✅：BookSourceDao `where bookSourceType = :type`；RssSourceDao `where type = :type`，SQL 均正确
3. **D2 RssSource 是否有 type 字段** ✅：RssSource.kt line 107 `var type: Int = 0`，数据基础具备
4. **D3 订阅源二级设置** ✅：订阅源首屏用文件夹视图，点击文件夹后用列表视图（onFolderClick 切换 isShowingFolder=false + applyListView）

## D2 Bug 排查结论（Phase 2 已完成排查）

### 书源（BookSourceActivity）—— 代码逻辑正确，需真机验证

静态分析结论：代码逻辑完全正确，未发现 Bug。
- `applyConfigChange()` line 430：sourceGroupStyle 1/2 时显示文件夹视图 ✅
- `upFolderView()` line 448-455：创建类型文件夹列表 ✅
- `onFolderClick()` line 906-933：设置 currentType + 切换列表视图 ✅
- `upBookSource()` line 485-488：currentType >= 0 时查询 flowByType ✅
- BookSourcePart 视图包含 bookSourceType 字段 ✅
- 可能原因：从未正确编译/部署，需真机验证

### 订阅源（RssSourceActivity）—— 三重根因，完全无文件夹视图实现

**根因1**：SourceFolderAdapter.kt line 85 `if (!isBookSource) llGroupStyle.visibility = View.GONE` —— 订阅源隐藏分组样式选项，用户无法选择"按类型/按分组"

**根因2**：SourceFolderAdapter.kt line 96-105 订阅源强制 `sourceGroupStyle=0` —— 即使绕过 UI，配置也被强制重置为列表平铺

**根因3**：RssSourceActivity 完全没有文件夹视图实现：
- 无 `folderAdapter` 字段
- 无 `applyFolderView()` / `upFolderView()` / `onFolderClick()` 方法
- 无 `isShowingFolder` 运行时状态变量
- 未实现 `SourceFolderAdapter.CallBack` 接口
- class 声明（line 64-67）只有 `PopupMenu.OnMenuItemClickListener, SelectActionBar.CallBack, RssSourceAdapter.CallBack`

**修复方案**：
1. SourceFolderAdapter: 移除 line 85（隐藏 llGroupStyle）+ 移除 line 96-105（强制 sourceGroupStyle=0）
2. RssSourceActivity: 参照 BookSourceActivity 新增 folderAdapter + applyFolderView + upFolderView + onFolderClick + isShowingFolder + 实现 SourceFolderAdapter.CallBack
3. RssSourceActivity onFolderClick 中切换到列表视图（满足 D3：二级页面用列表）
