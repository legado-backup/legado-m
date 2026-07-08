# 书源/订阅源布局深度重构 — 续接实施计划（Task #59/#60/#61）

> **背景**：前序任务 #53-#58 已完成（配置基础设施/DAO/资源/对话框/适配器/布局），本计划聚焦剩余的 Activity 重构与验证收尾。
> **指导文档**：[source-layout-deep-refactor.md](./source-layout-deep-refactor.md)（已审核通过的总方案）

---

## 一、当前状态核实（Phase 1 探查结论）

### ✅ 已完成（Task #53-#58）

| 任务 | 文件 | 状态 |
|------|------|------|
| #53 配置基础设施 | [AppConfig.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/config/AppConfig.kt) L250-303 + [PreferKey.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/PreferKey.kt) L232-237 | ✅ `sourceGroupStyle`/`sourceLayout`/`sourceSort`/`sourceMargin`/`migrateSourceConfigIfNeeded()` 已就位 |
| #54 DAO 组合查询 | [BookSourceDao.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/dao/BookSourceDao.kt) L114-128 + [RssSourceDao.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt) L80-94 | ✅ `flowByTypeSearch`/`flowGroupSearchExact` 已新增（双 DAO） |
| #55 资源字符串 | strings.xml（values + values-zh）+ arrays.xml | ✅ 12 条字符串 + `source_group_style_new` 数组 |
| #57 配置对话框 | [dialog_source_folder_config.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/dialog_source_folder_config.xml) + [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) L74-114 | ✅ 新签名 `showConfigDialog(context, onConfigChanged: () -> Unit)` 已就位，读取/保存 4 个配置 |
| #58 适配器+布局 | BookSourceAdapterCompact/Grid + RssSourceAdapterCompact/Grid + 4 布局 + bg_source_enabled_dot | ✅ 9 个文件已创建 |

### ❌ 未完成（本计划目标）

| 任务 | 文件 | 缺口 |
|------|------|------|
| #59 BookSourceActivity 重构 | [BookSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt) | 仍是旧代码：L116-117 用 `sourceViewMode`、L344-370 `showFolderConfig` 用旧签名、L399-445 `upBookSource` 处理 `type:`/`group:` 前缀、L802-823 `onFolderClick` 回填搜索框、无状态变量、无网格支持 |
| #60 RssSourceActivity 重构 | [RssSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt) | 同上问题，且无排序变量（需新增） |
| #61 验证收尾 | updateLog.md + 编译 + 真机 | 未开始 |

### 关键事实（探查确认）

- **BookSourceSort 枚举**（[BookSourceSort.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceSort.kt)）：`Default, Name, Url, Weight, Update, Enable, Respond`（7 值）
- **BookSourceActivity 现有排序变量**：`sort: BookSourceSort` + `sortAscending: Boolean`（L108-111），菜单 7 项排序（menu_sort_manual/auto/name/url/time/respondTime/enable）
- **RssSourceActivity 无排序变量**：完全需新增
- **BookSourceType 映射**：0=文本/1=音频/2=图片/3=文件/4=视频（strings: type_text/audio/image/file/video）
- **RssSource.type 映射**：0=网页/1=图片/2=视频（strings: type_web/image/video）
- **sourceSort 配置**：0=手动/1=名称/2=启用/3=类型/4=分组/5=URL（6 值，与 BookSourceSort 不完全对应）
- **BookSourceAdapter.showMenu** L168 检查 `callBack.sort == BookSourceSort.Default` 决定是否显示 menu_top/menu_bottom

---

## 二、提议变更

### 2.1 Task #59：BookSourceActivity 重构

#### 2.1.1 新增状态变量（L114-121 区域替换）

**删除**：
```kotlin
private val isFolderViewMode: Boolean
    get() = AppConfig.sourceViewMode == 1
private var isShowingFolder: Boolean = false
```

**替换为**：
```kotlin
// source-layout-refactor 隐藏字段方案：子目录状态变量
private var currentType: Int = -1        // -1=全部, 0-4=具体类型
private var currentGroup: String? = null // null=根目录, 非空=在某个分组内
private val inSubDirectory: Boolean get() = currentType >= 0 || currentGroup != null
// source-layout-refactor 视图状态：sourceGroupStyle!=0 时根目录显示文件夹
private val isFolderViewMode: Boolean
    get() = AppConfig.sourceGroupStyle != 0
private var isShowingFolder: Boolean = false
```

#### 2.1.2 重构 `upBookSource`（L399-505）

**核心**：用状态变量 `currentType`/`currentGroup` 替代 `type:`/`group:` 前缀解析；新增 `sortSources()` 方法。

```kotlin
private fun upBookSource(searchKey: String? = null) {
    if (isShowingFolder) return
    // 历史兼容：清空 type:/group: 前缀回填（防止旧代码遗留）
    val nameQuery = searchKey?.let {
        when {
            it.startsWith("type:") || it.startsWith("group:") -> ""
            else -> it
        }
    }
    sourceFlowJob?.cancel()
    sourceFlowJob = lifecycleScope.launch {
        val flow = when {
            // 子目录：按类型 + 名称搜索
            currentType >= 0 && !nameQuery.isNullOrEmpty() ->
                appDb.bookSourceDao.flowByTypeSearch(currentType, nameQuery)
            currentType >= 0 ->
                appDb.bookSourceDao.flowByType(currentType)
            // 子目录：按分组 + 名称搜索
            currentGroup != null && !nameQuery.isNullOrEmpty() ->
                appDb.bookSourceDao.flowGroupSearchExact(currentGroup!!, nameQuery)
            currentGroup != null ->
                appDb.bookSourceDao.flowGroupSearch(currentGroup!!)
            // 根目录：特殊筛选（保留 enabled/disabled/need_login 等快捷词）
            !nameQuery.isNullOrEmpty() && nameQuery == getString(R.string.enabled) ->
                appDb.bookSourceDao.flowEnabled()
            !nameQuery.isNullOrEmpty() && nameQuery == getString(R.string.disabled) ->
                appDb.bookSourceDao.flowDisabled()
            !nameQuery.isNullOrEmpty() && nameQuery == getString(R.string.need_login) ->
                appDb.bookSourceDao.flowLogin()
            !nameQuery.isNullOrEmpty() && nameQuery == getString(R.string.no_group) ->
                appDb.bookSourceDao.flowNoGroup()
            !nameQuery.isNullOrEmpty() && nameQuery == getString(R.string.enabled_explore) ->
                appDb.bookSourceDao.flowEnabledExplore()
            !nameQuery.isNullOrEmpty() && nameQuery == getString(R.string.disabled_explore) ->
                appDb.bookSourceDao.flowDisabledExplore()
            // 根目录：名称搜索
            !nameQuery.isNullOrEmpty() -> appDb.bookSourceDao.flowSearch(nameQuery)
            // 根目录：全部
            else -> appDb.bookSourceDao.flowAll()
        }
        flow.map { data ->
            hostMap.clear()
            if (groupSourcesByDomain) {
                data.sortedWith(
                    compareBy<BookSourcePart> { getSourceHost(it.bookSourceUrl) == "#" }
                        .thenBy { getSourceHost(it.bookSourceUrl) }
                        .thenByDescending { it.lastUpdateTime })
            } else {
                sortSources(data)
            }
        }.flowWithLifecycleAndDatabaseChange(
            lifecycle, table = AppDatabase.BOOK_SOURCE_TABLE_NAME
        ).catch {
            AppLog.put("书源界面更新书源出错", it)
        }.flowOn(IO).conflate().collect { data ->
            adapter.setItems(data, adapter.diffItemCallback, !Debug.isChecking)
            itemTouchCallback.isCanDrag = AppConfig.sourceSort == 0 && !groupSourcesByDomain
            delay(500)
        }
    }
}

// source-layout-refactor 排序：sourceSort 配置驱动（6 选项），兼容旧 sort/sortAscending
private fun sortSources(data: List<BookSourcePart>): List<BookSourcePart> {
    // sourceSort!=0 时用新配置排序；sourceSort==0 时回退旧 sort 逻辑（保留 Weight/Update/Respond）
    return if (AppConfig.sourceSort != 0) {
        val sorted = when (AppConfig.sourceSort) {
            1 -> data.sortedWith { o1, o2 -> o1.bookSourceName.cnCompare(o2.bookSourceName) }
            2 -> data.sortedByDescending { it.enabled }
            3 -> data.sortedBy { it.bookSourceType }
            4 -> data.sortedBy { it.bookSourceGroup ?: "" }
            5 -> data.sortedBy { it.bookSourceUrl }
            else -> data
        }
        if (!sortAscending) sorted.reversed() else sorted
    } else {
        // 旧逻辑：保留 BookSourceSort.Default/Weight/Update/Respond 等菜单排序
        if (sortAscending) {
            when (sort) {
                BookSourceSort.Weight -> data.sortedBy { it.weight }
                BookSourceSort.Name -> data.sortedWith { o1, o2 -> o1.bookSourceName.cnCompare(o2.bookSourceName) }
                BookSourceSort.Url -> data.sortedBy { it.bookSourceUrl }
                BookSourceSort.Update -> data.sortedByDescending { it.lastUpdateTime }
                BookSourceSort.Respond -> data.sortedBy { it.respondTime }
                BookSourceSort.Enable -> data.sortedWith { o1, o2 ->
                    var cmp = -o1.enabled.compareTo(o2.enabled)
                    if (cmp == 0) cmp = o1.bookSourceName.cnCompare(o2.bookSourceName)
                    cmp
                }
                else -> data
            }
        } else {
            when (sort) {
                BookSourceSort.Weight -> data.sortedByDescending { it.weight }
                BookSourceSort.Name -> data.sortedWith { o1, o2 -> o2.bookSourceName.cnCompare(o1.bookSourceName) }
                BookSourceSort.Url -> data.sortedByDescending { it.bookSourceUrl }
                BookSourceSort.Update -> data.sortedBy { it.lastUpdateTime }
                BookSourceSort.Respond -> data.sortedByDescending { it.respondTime }
                BookSourceSort.Enable -> data.sortedWith { o1, o2 ->
                    var cmp = o1.enabled.compareTo(o2.enabled)
                    if (cmp == 0) cmp = o1.bookSourceName.cnCompare(o2.bookSourceName)
                    cmp
                }
                else -> data.reversed()
            }
        }
    }
}
```

#### 2.1.3 重构 `onFolderClick`（L802-823）

**核心**：设置状态变量，不触碰搜索框。

```kotlin
override fun onFolderClick(group: String) {
    when (AppConfig.sourceGroupStyle) {
        1 -> { // 按类型
            currentType = when (group) {
                getString(R.string.type_text) -> 0
                getString(R.string.type_audio) -> 1
                getString(R.string.type_image) -> 2
                getString(R.string.type_file) -> 3
                getString(R.string.type_video) -> 4
                else -> -1  // all_groups 或 no_group
            }
            currentGroup = null
        }
        2 -> { // 按分组
            currentType = -1
            currentGroup = when (group) {
                getString(R.string.all_groups) -> null
                getString(R.string.no_group) -> null  // 无分组特殊处理：用 flowNoGroup
                else -> group
            }
        }
        else -> return  // 列表平铺模式无文件夹
    }
    isShowingFolder = false
    applyListView()
    invalidateOptionsMenu()
    upBookSource(searchView.query?.toString())
}
```

**简化说明**：no_group 文件夹点击后 currentGroup=null + currentType=-1，依赖搜索框内容触发 flowNoGroup | 已知上限：no_group 文件夹需搜索框含"未分组"关键字才能筛选 | 升级路径：新增 `currentNoGroup: Boolean` 状态变量

#### 2.1.4 重构 `onCompatOptionsItemSelected` 菜单类型筛选（L274-292）

**核心**：设置 `currentType` 状态变量，不回填搜索框。

```kotlin
R.id.menu_type_all, R.id.menu_type_0, R.id.menu_type_1,
R.id.menu_type_2, R.id.menu_type_3, R.id.menu_type_4 -> {
    item.isChecked = true
    currentType = when (item.itemId) {
        R.id.menu_type_all -> -1
        R.id.menu_type_0 -> 0
        R.id.menu_type_1 -> 1
        R.id.menu_type_2 -> 2
        R.id.menu_type_3 -> 3
        R.id.menu_type_4 -> 4
        else -> -1
    }
    currentGroup = null
    if (isShowingFolder) {
        isShowingFolder = false
        applyListView()
        invalidateOptionsMenu()
    }
    upBookSource(searchView.query?.toString())
}
```

同理，`menu_group_*`（L296-298）和 `menu_enabled_group` 等保留搜索框回填（这些是快捷筛选词，非 type:/group: 前缀，不影响子目录搜索）。

#### 2.1.5 重构 `showFolderConfig`（L344-370）

**核心**：使用新签名 `showConfigDialog(context, onConfigChanged)`，新增 `applyConfigChange()`。

```kotlin
private fun showFolderConfig() {
    SourceFolderAdapter.showConfigDialog(this) {
        applyConfigChange()
    }
}

// source-layout-refactor 配置变更后应用视图
private fun applyConfigChange() {
    // 配置变更后重置子目录状态
    currentType = -1
    currentGroup = null
    when (AppConfig.sourceGroupStyle) {
        0 -> { // 列表平铺：直接显示所有源
            isShowingFolder = false
            applyListView()
            upBookSource(searchView.query?.toString())
        }
        1, 2 -> { // 按类型/按分组：显示文件夹
            isShowingFolder = true
            applyFolderView()
            upFolderView()
        }
    }
    invalidateOptionsMenu()
}
```

#### 2.1.6 重构 `applyListView`/`applyFolderView`（L319-341）

**核心**：支持 `sourceLayout` 网格布局 + 适配器选择。

```kotlin
private fun applyListView() {
    binding.recyclerView.removeItemDecoration(gridSpacingDecoration)
    binding.recyclerView.removeItemDecoration(verticalDivider)
    val layout = AppConfig.sourceLayout
    when (layout) {
        0 -> { // 列表
            binding.recyclerView.addItemDecoration(verticalDivider)
            binding.recyclerView.layoutManager = LinearLayoutManager(this)
            binding.recyclerView.adapter = adapter
        }
        1 -> { // 紧凑列表
            binding.recyclerView.addItemDecoration(verticalDivider)
            binding.recyclerView.layoutManager = LinearLayoutManager(this)
            binding.recyclerView.adapter = adapterCompact
        }
        else -> { // 网格 2-6 列
            gridSpacingDecoration.spacing = AppConfig.sourceMargin.dpToPx()
            binding.recyclerView.addItemDecoration(gridSpacingDecoration)
            binding.recyclerView.layoutManager = GridLayoutManager(this, layout)
            binding.recyclerView.adapter = adapterGrid
        }
    }
    itemTouchCallback.isCanDrag =
        AppConfig.sourceSort == 0 && sort == BookSourceSort.Default
        && layout == 0 && !groupSourcesByDomain
}

private fun applyFolderView() {
    binding.recyclerView.removeItemDecoration(verticalDivider)
    binding.recyclerView.removeItemDecoration(gridSpacingDecoration)
    val marginDp = AppConfig.sourceMargin
    gridSpacingDecoration.spacing = SourceFolderAdapter.spacingPx(this, marginDp)
    binding.recyclerView.addItemDecoration(gridSpacingDecoration)
    val spanCount = SourceFolderAdapter.calculateSpanCount(this, marginDp)
    binding.recyclerView.layoutManager = GridLayoutManager(this, spanCount)
    binding.recyclerView.adapter = folderAdapter
    itemTouchCallback.isCanDrag = false
}
```

**新增适配器懒加载**（L96-97 区域追加）：
```kotlin
private val adapterCompact by lazy { BookSourceAdapterCompact(this, this) }
private val adapterGrid by lazy { BookSourceAdapterGrid(this, this) }
```

#### 2.1.7 新增返回键处理（子目录返回根目录）

在 Activity 中覆写 `onBackPressed` 或工具栏返回逻辑：

```kotlin
override fun onBackPressed() {
    if (inSubDirectory) {
        // 子目录内按返回：回到根目录
        currentType = -1
        currentGroup = null
        if (AppConfig.sourceGroupStyle == 0) {
            applyListView()
        } else {
            isShowingFolder = true
            applyFolderView()
            upFolderView()
        }
        upBookSource(searchView.query?.toString())
        invalidateOptionsMenu()
        return
    }
    super.onBackPressed()
}
```

#### 2.1.8 `upFolderView` 更新（L373-390）

将 `AppConfig.sourceFolderStyle == 1` 改为 `AppConfig.sourceGroupStyle == 1`：

```kotlin
private fun upFolderView() {
    val folderList = mutableListOf<String>()
    if (AppConfig.sourceGroupStyle == 1) {
        // 按类型分组：显示类型文件夹
        folderList.add(getString(R.string.all_groups))
        folderList.add(getString(R.string.type_text))
        folderList.add(getString(R.string.type_audio))
        folderList.add(getString(R.string.type_image))
        folderList.add(getString(R.string.type_file))
        folderList.add(getString(R.string.type_video))
    } else {
        // 按自定义分组
        folderList.add(getString(R.string.all_groups))
        folderList.add(getString(R.string.no_group))
        folderList.addAll(groups)
    }
    folderAdapter.setItems(folderList, folderAdapter.diffItemCallback)
}
```

#### 2.1.9 `onActivityCreated` 初始化（L149-165）

```kotlin
override fun onActivityCreated(savedInstanceState: Bundle?) {
    isShowingFolder = isFolderViewMode  // 跟随 sourceGroupStyle
    initRecyclerView()
    initSearchView()
    if (isShowingFolder) {
        upFolderView()
    } else {
        upBookSource()
    }
    initLiveDataGroup()
    initSelectActionBar()
    resumeCheckSource()
    if (!LocalConfig.bookSourcesHelpVersionIsLast) {
        showHelp("SourceMBookHelp")
    }
}
```

#### 2.1.10 `BookSourceAdapter.showMenu` 兼容（BookSourceAdapter.kt L168）

将 `callBack.sort == BookSourceSort.Default` 改为同时检查 sourceSort：
```kotlin
popupMenu.menu.findItem(R.id.menu_top).isVisible = 
    callBack.sort == BookSourceSort.Default && AppConfig.sourceSort == 0
popupMenu.menu.findItem(R.id.menu_bottom).isVisible = 
    callBack.sort == BookSourceSort.Default && AppConfig.sourceSort == 0
```

---

### 2.2 Task #60：RssSourceActivity 重构

与 BookSourceActivity 同构，差异点：

| 差异项 | BookSource | RssSource |
|--------|-----------|-----------|
| 类型数量 | 5（文本/音频/图片/文件/视频） | 3（网页/图片/视频） |
| 类型映射 | type_text→0, type_audio→1, type_image→2, type_file→3, type_video→4 | type_web→0, type_image→1, type_video→2 |
| 排序变量 | 已有 `sort`/`sortAscending` | **无**，需新增 |
| DAO 字段 | bookSourceName/Type/Group/Url | sourceName/Type/Group/Url |

#### 2.2.1 RssSourceActivity 新增排序变量（L86 区域）

```kotlin
private var sortAscending = true
private var sort: RssSourceSort = RssSourceSort.Default  // 复用枚举或直接用 sourceSort
```

**简化说明**：RssSource 无独立 BookSourceSort 枚举，直接用 `AppConfig.sourceSort` 驱动 | 已知上限：RssSource 无 weight/respondTime 字段，sourceSort 的 Weight/Respond 选项对 RssSource 无效 | 升级路径：新增 RssSourceSort 枚举或在 sortSources 中对缺失字段降级处理

#### 2.2.2 RssSourceActivity `sortSources` 实现

```kotlin
private fun sortSources(data: List<RssSource>): List<RssSource> {
    val sorted = when (AppConfig.sourceSort) {
        1 -> data.sortedWith { o1, o2 -> o1.sourceName.cnCompare(o2.sourceName) }
        2 -> data.sortedByDescending { it.enabled }
        3 -> data.sortedBy { it.type }  // RssSource.type
        4 -> data.sortedBy { it.sourceGroup ?: "" }
        5 -> data.sortedBy { it.sourceUrl }
        else -> data  // 0=手动，用 customOrder
    }
    return if (sortAscending) sorted else sorted.reversed()
}
```

#### 2.2.3 其他重构项

与 BookSourceActivity 2.1.1-2.1.9 同构，文件名/字段名替换：
- `upBookSource` → `upSourceFlow`
- `BookSourcePart` → `RssSource`
- `bookSourceName` → `sourceName`，`bookSourceType` → `type`，`bookSourceGroup` → `sourceGroup`，`bookSourceUrl` → `sourceUrl`
- 类型映射用 `type_web`/`type_image`/`type_video`（3 项）
- `AppConfig.rssViewMode` 相关逻辑改为 `AppConfig.sourceGroupStyle`（RssSource 共用 sourceGroupStyle 配置，已在 AppConfig 中统一）
- 新增 `adapterCompact`/`adapterGrid` 懒加载（RssSourceAdapterCompact/RssSourceAdapterGrid）
- 新增 `onBackPressed` 子目录返回逻辑

**注意**：RssSourceActivity 的 `initSearchView`（L308-325）使用内部匿名 `OnQueryTextListener`，调用 `upSourceFlow(newText)`，需确保 `upSourceFlow` 重构后兼容。

---

### 2.3 Task #61：验证收尾

#### 2.3.1 updateLog.md 更新

在 `app/src/main/assets/updateLog.md` 顶部 `## cronet版本:` 行之后追加：

```markdown
**2026/07/08**
- 书源/订阅源管理界面布局深度重构：新增列表/紧凑/网格2-6列共7种视图模式
- 分组样式扩展为3种：列表平铺/按类型/按分组
- 新增排序功能（手动/名称/启用/类型/分组/URL）
- 修复搜索框回填type:/group:导致子目录内搜索失效的问题，改为隐藏字段方案
- 文件夹样式对齐书架风格，配置对话框参考书架重构
```

#### 2.3.2 编译验证

```bash
./gradlew :app:assembleDebug
```

#### 2.3.3 真机验证（逍遥模拟器 127.0.0.1:21503）

| 用例 | 预期结果 |
|------|----------|
| 默认启动书源管理 | 显示列表平铺 + 列表视图 |
| 配置对话框切换"按类型" | 根目录显示 6 个类型文件夹 |
| 配置对话框切换"网格3列" | 源项以 3 列网格显示 |
| 点击类型文件夹 | 进入子目录，搜索框保持原样可用 |
| 子目录内输入名称搜索 | 仅在该类型内筛选 |
| 子目录内按返回键 | 返回根目录文件夹视图 |
| 切换排序为"按名称" | 列表按名称排序 |
| 订阅源管理界面 | 同样支持 3 种分组 + 7 种视图 + 6 种排序 |

---

## 三、假设与决策

### 3.1 假设

1. **RssSource 共用 sourceGroupStyle/sourceLayout/sourceSort 配置**：AppConfig 中 sourceGroupStyle 等配置对书源和订阅源统一生效（已在前序任务确认）
2. **BookSourceAdapterCompact/Grid 不支持拖拽排序和选择模式**：网格模式下批量操作需切换回列表模式（与书架行为一致）
3. **旧菜单排序项保留**：menu_sort_manual/auto/name/url/time/respondTime/enable 保留，与 sourceSort 配置共存（sourceSort!=0 时优先）
4. **no_group 文件夹点击**：依赖搜索框"未分组"关键字触发 flowNoGroup（简化处理，首版不做独立状态变量）

### 3.2 决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 排序系统 | 双轨制：sourceSort 配置（6项）+ 旧菜单 sort（7项）共存 | 保留 Weight/Update/Respond 等书源特有排序，不破坏现有功能 |
| 状态变量方案 | currentType/currentGroup 隐藏字段 | 彻底解决搜索框回填反模式 |
| 返回键行为 | 子目录内返回→根目录，根目录返回→退出 | 符合用户预期，不触碰搜索框 |
| RssSource 排序 | 直接用 sourceSort 驱动，无独立枚举 | RssSource 无 weight/respondTime 字段，简化处理 |
| no_group 处理 | 首版依赖搜索框关键字 | 简化状态机，升级路径明确 |

### 3.3 不做的事（YAGNI）

- 不为 RssSource 新建 RssSourceSort 枚举（直接用 sourceSort）
- 不为 no_group 新增独立状态变量（依赖搜索框关键字）
- 不重构 BookSourceAdapter 的拖拽逻辑（保持现有实现）
- 不移除旧菜单排序项（保留兼容）

---

## 四、实施顺序

1. **BookSourceActivity 重构**（Task #59）
   - 1.1 新增状态变量 + adapterCompact/adapterGrid 懒加载
   - 1.2 重构 upBookSource + 新增 sortSources
   - 1.3 重构 onFolderClick
   - 1.4 重构菜单类型筛选
   - 1.5 重构 showFolderConfig + 新增 applyConfigChange
   - 1.6 重构 applyListView/applyFolderView
   - 1.7 新增 onBackPressed
   - 1.8 更新 upFolderView + onActivityCreated
   - 1.9 更新 BookSourceAdapter.showMenu 兼容
2. **RssSourceActivity 重构**（Task #60）— 同构
3. **updateLog.md + 编译验证**（Task #61）
4. **真机验证**

---

## 五、验证步骤

### 5.1 编译验证
```bash
./gradlew :app:assembleDebug
```

### 5.2 功能验证（逍遥模拟器）

| 用例 | 预期结果 |
|------|----------|
| 默认启动书源管理 | 列表平铺 + 列表视图 |
| 配置切换"按类型" | 6 个类型文件夹 |
| 配置切换"按分组" | 分组文件夹 |
| 配置切换"网格3列" | 3 列网格 |
| 点击类型文件夹 | 进入子目录，搜索框不变 |
| 子目录内搜索 | 仅筛该类型 |
| 子目录返回 | 回根目录文件夹视图 |
| 菜单"类型→文本" | 进文本子目录（隐藏字段） |
| 切换排序"按名称" | 按名称排序 |
| 订阅源界面 | 同上支持 |

### 5.3 回归验证
- 旧配置用户升级后迁移正确
- 拖拽排序在列表模式仍可用
- 书源启用/禁用/选择等功能不受影响

---

## 六、风险与回退

| 风险 | 缓解措施 |
|------|----------|
| 双排序系统冲突 | sourceSort!=0 时优先，sourceSort==0 回退旧逻辑 |
| 网格适配器选择模式缺失 | 文档说明网格模式不支持批量选择，需切列表 |
| 子目录返回逻辑与系统返回键冲突 | 覆写 onBackPressed，子目录优先返回根目录 |
| RssSource 无 weight 字段排序异常 | sortSources 中 RssSource 跳过 Weight 选项 |
