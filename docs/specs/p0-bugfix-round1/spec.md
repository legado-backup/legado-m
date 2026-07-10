# Spec: P0 核心 Bug 修复

## Intent

修复 2026-07-08 改动中发现的 4 项 P0 核心 bug（M-01/M-02 + F-01 + V-01 + C-01），恢复核心功能可用性。修复后须通过 E2E 自动化测试验证。

## Scope

### In Scope

- M-01：BookSource compact/grid adapter 添加 selection 机制 + Activity 用 currentAdapter()
- M-02：RssSource compact/grid adapter 添加 selection 机制 + Activity 用 currentAdapter()
- F-01：RssFragment/ExploreFragment 引入 currentFilter 解耦 searchView，启用 DAO 组合查询
- V-01：VideoPlayer onPrepared 用 isMuted 而非 muteOnStart
- C-01：sourceSort 拆分为 bookSourceSort + rssSort
- 附带修复：C-04（注释不一致）、F-11（空判不一致）、C-05（启用死代码）
- G1（补录，代码已实施）：订阅源管理移除文件夹视图，回归列表/紧凑/网格三视图模式；配置对话框自动隐藏分组样式选项
- G2（补录，代码已实施）：优化书源文件夹卡片样式，对齐书架 grid 布局风格，移除 CardView 包裹，分组名叠加在封面底部（渐变遮罩背景）

### Out of Scope

- M-10 基类提取（P2 架构重构）
- F-08 首页 style1/style2 设计（P2 架构重构）
- F-02/F-03/F-05/F-06 阻塞点决策（P1）
- V-02/V-03/V-04 视频其余 bug（P3）
- M-06~M-09 管理页其余 bug（P3）

## Approach

### M-01/M-02：简化方案（先修 bug，P2 再重构）

给 compact/grid adapter 添加 selection 机制（与 list adapter 相同的 selected 集合 + selectAll + revertSelection + selection + dragSelectCallback），Activity 用 currentAdapter() 动态获取当前显示的 adapter。

**Alternatives Considered**:
- 方案A：提取 BaseSourceAdapter 基类（M-10）—— 工作量大，P2 再做
- 方案B（选用）：给 compact/grid adapter 直接添加 selection 机制 —— 工作量适中，P0 先保证功能可用

**Drawbacks**：compact/grid adapter 的 selection 逻辑与 list adapter 重复，P2 的 M-10 会重构覆盖。

### F-01：引入 currentFilter 解耦 searchView

RssFragment/ExploreFragment 添加 currentGroup: String? 字段，onFolderClick 设置 currentGroup 不回填 searchView，upRssFlowJob 用 currentGroup + searchKey 组合查询（启用 DAO 已有的 flowGroupSearchExact）。

**Alternatives Considered**:
- 方案A：等 style1/style2 重构后统一 currentFilter（Long groupId）—— 依赖 P2，P0 不能立即修复
- 方案B（选用）：现有 RssFragment 用 String currentGroup 修复 —— 不依赖 style1/style2，P0 可立即修复

**Drawbacks**：currentGroup 是 String 类型，P2 的 style1/style2 重构会改为 Long groupId，需返工。但 P0 优先保证功能可用。

### V-01：onPrepared 用 isMuted

VideoPlayer.kt onPrepared 改为 `setNeedMute(isMuted)`，跟随用户当前静音状态。initView 中 isMuted 初始化保持 `isMuted = VideoPlay.muteOnStart`（仅首次播放应用 muteOnStart）。

### C-01：拆分 sourceSort

sourceSort 改为 bookSourceSort（书源专用），启用已有的 rssSort/rssSortAscending（订阅源专用）。

## Requirements

### R1: M-01/M-02 选择模式恢复

- R1.1 compact/grid adapter 必须有 selected 集合和 selection 属性
- R1.2 compact/grid adapter 必须实现 selectAll/revertSelection/setSelection
- R1.3 compact/grid adapter 必须有 dragSelectCallback 和 checkSelectedInterval
- R1.4 Activity 内所有 `adapter.selection`/`adapter.selectAll()` 必须改为 `currentAdapter().xxx`
- R1.5 compact 模式下 cb 复选框必须正确显示选中状态
- R1.6 grid 模式下必须用 foreground 高亮显示选中状态

### R2: F-01 搜索框解耦

- R2.1 RssFragment/ExploreFragment 必须有 currentGroup 字段
- R2.2 onFolderClick 必须设置 currentGroup，不回填 searchView
- R2.3 upRssFlowJob 必须用 currentGroup + searchKey 组合查询
- R2.4 用户输入名称后归类信息必须保留（走 flowGroupSearchExact）
- R2.5 搜索框文本必须只是用户输入的名称，无 "group:" 前缀
- R2.6 菜单 menu_group_text 快捷筛选也必须设置 currentGroup，不回填 searchView

### R3: V-01 视频静音

- R3.1 onPrepared 必须用 `setNeedMute(isMuted)` 而非 `if (muteOnStart) setNeedMute(true)`
- R3.2 首次播放仍应用 muteOnStart（initView 中 isMuted = muteOnStart）
- R3.3 换集后静音状态必须保持用户上一次手动设置
- R3.4 静音图标状态必须与实际静音一致

### R4: C-01 sourceSort 拆分

- R4.1 PreferKey/AppConfig 必须有 bookSourceSort（书源专用）和 rssSort（订阅源专用）
- R4.2 BookSourceActivity 菜单和 sortSources 必须用 bookSourceSort
- R4.3 RssSourceActivity 菜单和 sortSources 必须用 rssSort
- R4.4 书源排序状态变更不得影响订阅源，反之亦然
- R4.5 配置对话框 sourceSort 必须按 Activity 类型区分（bookSourceSort/rssSort）

### R5: 编译与测试

- R5.1 `./gradlew assembleRelease` 编译通过
- R5.2 E2E 测试无 FATAL EXCEPTION
- R5.3 4 项 P0 bug 场景验证通过

## Scenarios

### S1: M-01 compact 选择模式（BookSource）

1. 打开书源管理页
2. 切换到紧凑布局
3. 长按选择一个源
4. 点击"全选"
5. 验证：所有源被选中，cb 复选框显示选中状态
6. 点击"删除"
7. 验证：选中的源被删除

### S2: M-02 grid 选择模式（RssSource）

1. 打开订阅源管理页
2. 切换到网格布局
3. 长按选择一个源
4. 滑动多选
5. 验证：滑动范围内的源被选中，foreground 高亮
6. 点击"禁用"
7. 验证：选中的源被禁用

### S3: F-01 搜索框解耦（RssFragment）

1. 打开订阅源首页
2. 切换到文件夹视图
3. 点击"小说"分组
4. 验证：列表显示小说分组的源，搜索框为空
5. 在搜索框输入"起点"
6. 验证：列表显示小说分组中名称含"起点"的源（走 flowGroupSearchExact）
7. 清空搜索框
8. 验证：列表恢复显示小说分组的全部源

### S4: V-01 视频换集静音

1. 打开视频播放器
2. 播放视频（首次应用 muteOnStart，静音）
3. 点击静音按钮取消静音
4. 验证：视频有声音，图标显示非静音
5. 切换下一集
6. 验证：新集有声音（保持用户取消静音的状态），图标显示非静音

### S5: C-01 sourceSort 独立

1. 打开书源管理页，菜单选"按名称排序"
2. 退出，打开订阅源管理页
3. 验证：订阅源排序不受书源影响（保持订阅源自己的排序）
4. 在订阅源菜单选"按 URL 排序"
5. 退出，打开书源管理页
6. 验证：书源排序保持"按名称"（不受订阅源影响）
