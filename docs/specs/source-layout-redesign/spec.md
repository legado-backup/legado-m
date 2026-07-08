# Spec: 书源/订阅源布局设置重做

## Intent

用户反馈书源分组"两种视图下都不生效"、订阅源"分组生效但类型不生效"，并要求学习书架的视图模式（列表/紧凑列表/网格多列）和排序功能，统一重做书源/订阅源的布局设置。

**核心诉求**：
1. 修复书源分组菜单为空的 Bug
2. 修复订阅源类型筛选缺失的问题
3. 书源/订阅源视图模式从 2 种扩展到 5 种（对齐书架）
4. 订阅源新增排序功能（对齐书源已有排序）
5. 新增按类型筛选（网页/图片/视频等）
6. 统一配置对话框入口

## Scope

### In Scope

- **书源管理（BookSourceActivity）**：修复 `groupMenuLifecycleOwner` 导致分组菜单为空；扩展视图模式；新增类型筛选
- **订阅源管理（RssSourceActivity）**：扩展视图模式；新增排序功能；新增类型筛选
- **DAO 层**：BookSourceDao / RssSourceDao 新增按 type 查询的 Flow 方法
- **配置层**：AppConfig 新增 `rssSort`（订阅源排序）配置项；视图模式值域扩展
- **UI 层**：统一配置对话框（参考书架 `DialogBookshelfConfigBinding`）；菜单新增类型筛选项
- **Adapter 层**：列表 Adapter 支持多视图布局（列表/紧凑/网格）

### Out of Scope

- 书源/订阅源编辑页的改动（仅改管理列表页）
- 书架本身的视图模式改动（书架是学习对象，不改）
- 文件夹视图的卡片样式改动（仅改列表视图的布局模式）
- 前端 web 管理页的同步（后续独立任务）

## Approach

### 方案：扩展式重做（保留现有语义 + 新增模式）

**视图模式值域设计**（向后兼容）：

| 值 | 含义 | 状态 |
|----|------|------|
| 0 | 列表 | 保留（旧用户默认） |
| 1 | 文件夹 | 保留 |
| 2 | 紧凑列表 | 新增 |
| 3 | 网格2列 | 新增 |
| 4 | 网格3列 | 新增 |

**关键设计决策**：
- `isFolderViewMode` 判断保持 `== 1` 不变（向后兼容）
- 视图模式 0/2/3/4 都走"列表视图"分支，仅在 LayoutManager 和 item layout 上区分
- 文件夹视图（1）保持独立的 `applyFolderView()` 路径
- 排序和类型筛选在列表视图和文件夹视图下都生效

**Bug 修复策略**：
- 书源分组：移除 `groupMenuLifecycleOwner`，改为 `lifecycleScope` 直接 collect（对齐订阅源的 `initGroupFlow`）
- 订阅源类型：新增 `flowByType` DAO 方法 + 菜单项 + `upSourceFlow` 分支

### Alternatives Considered

**Alt 1：完全学习书架的值域（0=列表/1=紧凑/>=2=网格）**
- 优点：与书架完全一致，学习成本低
- 缺点：破坏现有 `sourceViewMode` 语义（旧 1=文件夹 → 新 1=紧凑），需要数据迁移，风险高
- **否决**：向后兼容风险太大

**Alt 2：文件夹视图也支持网格多列**
- 优点：文件夹卡片可以按多列排列
- 缺点：文件夹视图已有 `calculateSpanCount` 动态计算列数，再叠加网格模式会导致逻辑混乱
- **否决**：文件夹视图保持独立的列数计算逻辑

**Alt 3：类型筛选用 Tab 而非菜单**
- 优点：切换更便捷
- 缺点：占用屏幕空间，与现有 SearchView 冲突
- **否决**：用菜单项（SubMenu），与分组筛选保持一致的交互模式

### Drawbacks

1. 视图模式值域不是连续的（0/2/3/4 是列表类，1 是文件夹类），语义不够直观
2. 订阅源排序功能新增后，与书源排序的枚举值不完全一致（订阅源无 Weight/Respond）
3. 类型筛选作为 SubMenu 嵌套在分组菜单中，层级较深（分组菜单 → 类型子菜单）

## Requirements

### REQ-1: 书源分组 Bug 修复
- 移除 `groupMenuLifecycleOwner`，`initLiveDataGroup` 改为 `lifecycleScope` 直接 collect
- 分组菜单在 Activity 创建后立即加载数据，打开菜单时分组项已就绪

### REQ-2: 订阅源类型筛选
- RssSourceDao 新增 `flowByType(type: Int): Flow<List<RssSource>>` 方法
- 菜单新增类型筛选 SubMenu（全部/网页/图片/视频）
- `upSourceFlow` 新增 `type:` 前缀分支

### REQ-3: 书源类型筛选
- BookSourceDao 新增 `flowByType(type: Int): Flow<List<BookSourcePart>>` 方法
- 菜单新增类型筛选 SubMenu（全部/文本/音频/图片/文件/视频）
- `upBookSource` 新增 `type:` 前缀分支

### REQ-4: 视图模式扩展
- AppConfig `sourceViewMode` / `rssViewMode` 值域扩展为 0-4
- `applyListView()` 根据视图模式选择 LayoutManager 和 item layout
- 新增紧凑列表和网格布局的 item layout

### REQ-5: 订阅源排序
- 新增 `RssSourceSort` 枚举（Default/Name/Url/Update/Enable）
- AppConfig 新增 `rssSort` 配置项
- `upSourceFlow` 中根据排序方式排序数据
- 菜单新增排序 SubMenu

### REQ-6: 统一配置对话框
- 新建 `dialog_source_config.xml`，参考 `dialog_bookshelf_config.xml`
- 包含：视图模式 RadioGroup + 排序 RadioGroup + 间距 SeekBar
- 替换现有 `DialogSourceFolderConfigBinding`

## Scenarios

### Scenario 1: 书源分组菜单正常显示
1. 用户进入书源管理页
2. 点击三点菜单 → 分组
3. **预期**：分组子菜单立即显示所有分组名称（不为空）
4. 点击某个分组 → 列表筛选为该分组的源

### Scenario 2: 订阅源按类型筛选
1. 用户进入订阅源管理页
2. 点击三点菜单 → 类型
3. 选择"视频"
4. **预期**：列表仅显示 type=2 的订阅源

### Scenario 3: 切换网格视图
1. 用户在书源管理页点击三点菜单 → 布局设置
2. 选择"网格3列"
3. **预期**：列表变为 3 列网格布局，每行 3 个源卡片

### Scenario 4: 订阅源排序
1. 用户在订阅源管理页点击三点菜单 → 排序
2. 选择"按名称"
3. **预期**：列表按源名称字母排序

### Scenario 5: 文件夹视图下类型筛选
1. 用户在文件夹视图下点击三点菜单 → 类型 → "图片"
2. 点击某个文件夹进入分组列表
3. **预期**：分组列表中仅显示该分组下 type=1 的源
