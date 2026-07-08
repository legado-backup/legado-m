# Design: 书源/订阅源布局设置重做

## Technical Approach

### 1. Bug 修复：书源分组不生效

**根因**：`BookSourceActivity.kt:149-161` 的 `groupMenuLifecycleOwner` 设计——分组数据 Flow 通过 `flowWithLifecycleAndDatabaseChangeFirst(groupMenuLifecycleOwner.lifecycle, ...)` 绑定到自定义 LifecycleOwner。该 LifecycleOwner 只在 `onMenuOpened` 时触发 `ON_START`，但 Flow 异步发射数据来不及在菜单打开瞬间填充菜单项。

**修复方案**：移除 `groupMenuLifecycleOwner`，`initLiveDataGroup` 改为 `lifecycleScope` 直接 collect（对齐订阅源 `initGroupFlow` 实现）。

```kotlin
// 修复前（BookSourceActivity.kt:493-516）
private fun initLiveDataGroup() {
    lifecycleScope.launch {
        appDb.bookSourceDao.flowGroups().flowOn(IO)
            .flowWithLifecycleAndDatabaseChange(lifecycle, ...)
            .flowWithLifecycleAndDatabaseChangeFirst(groupMenuLifecycleOwner.lifecycle, ...)
            .conflate().distinctUntilChanged()
            .collect { ... }
    }
}

// 修复后（对齐订阅源 initGroupFlow）
private fun initLiveDataGroup() {
    lifecycleScope.launch {
        appDb.bookSourceDao.flowGroups().flowOn(IO).conflate().collect {
            groups.clear()
            groups.addAll(it)
            upGroupMenu()
            if (isShowingFolder) upFolderView()
        }
    }
}
```

同时移除 `groupMenuLifecycleOwner` 定义和 `onMenuOpened/onPanelClosed` 中的相关调用。

### 2. 视图模式扩展

**值域设计**（向后兼容）：

| 值 | 模式 | LayoutManager | Item Layout |
|----|------|---------------|-------------|
| 0 | 列表 | LinearLayoutManager | item_book_source_list.xml（现有） |
| 1 | 文件夹 | GridLayoutManager(动态列数) | item_source_folder_grid.xml（现有） |
| 2 | 紧凑列表 | LinearLayoutManager | item_book_source_compact.xml（新建） |
| 3 | 网格2列 | GridLayoutManager(2) | item_book_source_grid.xml（新建） |
| 4 | 网格3列 | GridLayoutManager(3) | item_book_source_grid.xml（新建） |

**视图切换逻辑**：
```kotlin
private fun applyListView() {
    when (sourceViewMode) {
        2 -> { // 紧凑列表
            binding.recyclerView.layoutManager = LinearLayoutManager(this)
            binding.recyclerView.adapter = adapter // compact item type
        }
        3, 4 -> { // 网格
            val spanCount = sourceViewMode - 1 // 3→2列, 4→3列
            binding.recyclerView.layoutManager = GridLayoutManager(this, spanCount)
            binding.recyclerView.adapter = adapter // grid item type
        }
        else -> { // 0=列表
            binding.recyclerView.layoutManager = LinearLayoutManager(this)
            binding.recyclerView.adapter = adapter // list item type
        }
    }
}
```

**Adapter 多视图类型**：Adapter 的 `getItemViewType` 根据 `sourceViewMode` 返回不同 type，`onCreateViewHolder` 根据typeinflate 不同 layout。

### 3. 类型筛选

**DAO 新增方法**：

```kotlin
// BookSourceDao.kt
@Query("select * from book_sources_part where bookSourceType = :type order by customOrder asc")
fun flowByType(type: Int): Flow<List<BookSourcePart>>

// RssSourceDao.kt
@Query("select * from rssSources where type = :type order by customOrder")
fun flowByType(type: Int): Flow<List<RssSource>>
```

**菜单结构**（新增类型 SubMenu）：
```xml
<item android:id="@+id/menu_type" android:title="类型">
    <menu>
        <group android:id="@+id/source_type" android:checkableBehavior="single">
            <item android:id="@+id/menu_type_all" android:title="全部" android:checked="true"/>
            <item android:id="@+id/menu_type_0" android:title="网页"/>
            <item android:id="@+id/menu_type_1" android:title="图片"/>
            <item android:id="@+id/menu_type_2" android:title="视频"/>
        </group>
    </menu>
</item>
```

**筛选逻辑**：通过 `searchView.setQuery("type:2", true)` 触发，`upBookSource/upSourceFlow` 新增 `type:` 前缀分支。

### 4. 订阅源排序

**新增枚举**：
```kotlin
// RssSourceSort.kt（新建）
enum class RssSourceSort {
    Default, Name, Url, Update, Enable
}
```

**AppConfig 新增**：
```kotlin
var rssSort: Int
    get() = appCtx.getPrefInt(PreferKey.rssSort, 0)
    set(value) = appCtx.putPrefInt(PreferKey.rssSort, value)
```

**排序逻辑**（在 `upSourceFlow` 的 map 操作符中）：
```kotlin
}.map { data ->
    when (sort) {
        RssSourceSort.Name -> data.sortedWith { o1, o2 -> o1.sourceName.cnCompare(o2.sourceName) }
        RssSourceSort.Url -> data.sortedBy { it.sourceUrl }
        RssSourceSort.Update -> data.sortedByDescending { it.lastUpdateTime }
        RssSourceSort.Enable -> data.sortedByDescending { it.enabled }
        else -> data // Default = customOrder
    }
}
```

### 5. 统一配置对话框

新建 `dialog_source_config.xml`，参考 `dialog_bookshelf_config.xml` 结构：
- RadioGroup `rgView`：列表/紧凑列表/网格2列/网格3列/文件夹
- RadioGroup `rgSort`：手动/名称/URL/更新时间/启用状态
- SeekBar `sbMargin`：间距

替换 `SourceFolderAdapter.showConfigDialog()` 为 Activity 内的 `showSourceConfig()` 方法。

## Architecture Decisions

### ADR-1: 视图模式值域设计

**Context**：需要扩展视图模式，同时保持向后兼容

**Decision**：采用扩展式值域（0=列表/1=文件夹/2=紧凑/3=网格2列/4=网格3列），而非学习书架的连续值域（0=列表/1=紧凑/>=2=网格）

**Y-Statement**：
- **Doing**：扩展式值域，保留 0 和 1 的现有语义
- **Solving**：向后兼容问题——旧用户的 `sourceViewMode` 值不需要迁移
- **Consequence**：值域不连续（0/2/3/4 是列表类，1 是文件夹类），但 `isFolderViewMode = (sourceViewMode == 1)` 判断无需修改

### ADR-2: 类型筛选用 searchView 前缀而非独立状态

**Context**：类型筛选可以独立于分组筛选，也可以组合使用

**Decision**：复用 searchView 的 `type:` 前缀机制（与 `group:` 前缀一致）

**Y-Statement**：
- **Doing**：通过 `searchView.setQuery("type:2", true)` 触发类型筛选
- **Solving**：复用现有筛选链路，减少新增 UI 组件
- **Consequence**：类型和分组无法同时筛选（searchView 只能有一个 query），但符合现有架构约束

### ADR-3: 订阅源排序枚举独立于书源

**Context**：订阅源没有 weight/respondTime 字段

**Decision**：新建 `RssSourceSort` 枚举，仅包含订阅源支持的排序方式

**Y-Statement**：
- **Doing**：独立的 `RssSourceSort` 枚举
- **Solving**：避免引入订阅源不支持的字段
- **Consequence**：两个枚举不完全一致，但各自精确匹配实体字段

## Data Flow

```
用户操作                          状态变更                    数据流
─────────                        ────────                   ──────
点击菜单"分组"→"XXX"    →  searchView.query="group:XXX"
                           ↓
                        upBookSource("group:XXX")
                           ↓
                        BookSourceDao.flowGroupSearch("XXX")
                           ↓
                        Flow<List<BookSourcePart>> → adapter.setItems()

点击菜单"类型"→"视频"    →  searchView.query="type:2"
                           ↓
                        upBookSource("type:2")
                           ↓
                        BookSourceDao.flowByType(2)
                           ↓
                        Flow<List<BookSourcePart>> → adapter.setItems()

点击菜单"排序"→"名称"    →  sort = BookSourceSort.Name
                           ↓
                        upBookSource(searchView.query)
                           ↓
                        Flow.map { data.sortedBy... }
                           ↓
                        adapter.setItems()

点击菜单"布局设置"       →  showSourceConfig()
                           ↓
                        dialog_source_config.xml
                           ↓
                        AppConfig.sourceViewMode = newValue
                           ↓
                        applyListView() / applyFolderView()
```

## File Changes

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `BookSourceActivity.kt` | 修改 | 移除 groupMenuLifecycleOwner；扩展 applyListView；新增类型筛选分支；统一配置对话框 |
| `RssSourceActivity.kt` | 修改 | 扩展 applyListView；新增排序逻辑；新增类型筛选分支；统一配置对话框 |
| `BookSourceDao.kt` | 修改 | 新增 `flowByType(type: Int)` 方法 |
| `RssSourceDao.kt` | 修改 | 新增 `flowByType(type: Int)` 方法 |
| `AppConfig.kt` | 修改 | 新增 `rssSort` / `rssSortAscending` 配置项 |
| `PreferKey.kt` | 修改 | 新增 `rssSort` / `rssSortAscending` key |
| `BookSourceSort.kt` | 不变 | 保持现有枚举 |
| `RssSourceSort.kt` | 新建 | 订阅源排序枚举 |
| `book_source.xml` | 修改 | 新增类型筛选 SubMenu |
| `rss_source.xml` | 修改 | 新增排序 SubMenu + 类型筛选 SubMenu |
| `dialog_source_config.xml` | 新建 | 统一配置对话框布局 |
| `item_book_source_compact.xml` | 新建 | 紧凑列表 item 布局 |
| `item_book_source_grid.xml` | 新建 | 网格 item 布局 |
| `item_rss_source_compact.xml` | 新建 | 订阅源紧凑列表 item 布局 |
| `item_rss_source_grid.xml` | 新建 | 订阅源网格 item 布局 |
| `BookSourceAdapter.kt` | 修改 | 支持多视图类型（getItemViewType） |
| `RssSourceAdapter.kt` | 修改 | 支持多视图类型 |
| `SourceFolderAdapter.kt` | 修改 | 移除 showConfigDialog（迁移到 Activity） |
| `strings.xml` | 修改 | 新增字符串资源 |
| `updateLog.md` | 修改 | 追加用户可感知的变更说明 |
