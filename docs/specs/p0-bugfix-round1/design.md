# Design: P0 核心 Bug 修复

## Technical Approach

### 1. C-01 sourceSort 拆分（配置层，先改底层）

**现状**：
- PreferKey.kt:235 `sourceSort`（共享）
- AppConfig.kt:268-272 `sourceSort`（共享，默认 0）
- PreferKey.kt:239-240 `rssSort`/`rssSortAscending`（已定义未使用，C-05 死代码）
- AppConfig.kt:335-345 `rssSort`/`rssSortAscending`（已定义未使用）

**修复**：
1. PreferKey.kt：`sourceSort` 改名为 `bookSourceSort`（书源专用），保留 `sourceSort` 兼容读取
2. AppConfig.kt：`sourceSort` 改名为 `bookSourceSort`，启用 `rssSort`（订阅源专用）
3. BookSourceActivity.kt：菜单 `AppConfig.sourceSort` → `AppConfig.bookSourceSort`，sortSources 用 `bookSourceSort`
4. RssSourceActivity.kt：菜单 `AppConfig.sourceSort` → `AppConfig.rssSort`，sortSources 用 `rssSort`
5. SourceFolderAdapter.kt：配置对话框按 Activity 类型区分（传入 isBookSource 参数）

**ADR-01**：sourceSort 拆分
- Context：BookSource 和 RssSource 共享 sourceSort 导致排序串扰
- Decision：拆分为 bookSourceSort + rssSort，启用已有 rssSort 死代码
- Consequences：书源和订阅源排序独立， rssSort 死代码激活

### 2. V-01 视频换集静音（独立模块）

**现状**：VideoPlayer.kt:161-163
```kotlin
if (VideoPlay.muteOnStart) {
    getGSYVideoManager().player?.setNeedMute(true)
}
```

**修复**：
```kotlin
getGSYVideoManager().player?.setNeedMute(isMuted)
```

initView 中保持 `isMuted = VideoPlay.muteOnStart`（仅首次播放应用 muteOnStart），换集时 onPrepared 用 isMuted（跟随用户当前状态）。

**ADR-02**：onPrepared 静音策略
- Context：onPrepared 每次换集强制静音，覆盖用户手动取消静音
- Decision：onPrepared 用 isMuted 而非 muteOnStart
- Consequences：换集保持用户静音状态，首次播放仍应用 muteOnStart

### 3. F-01 搜索框解耦（首页）

**现状**：RssFragment.kt:276-285 onFolderClick
```kotlin
else -> searchView.setQuery("group:$group", true)  // 错误：回填搜索框
```

**修复**：
1. RssFragment.kt 添加 `private var currentGroup: String? = null`
2. onFolderClick 改为：
```kotlin
override fun onFolderClick(group: String) {
    isShowingFolder = false
    applyListView()
    requireActivity().invalidateOptionsMenu()
    currentGroup = when (group) {
        getString(R.string.all_groups) -> null
        getString(R.string.no_group) -> getString(R.string.no_group)
        else -> group
    }
    searchView.setQuery("", false)  // 清空搜索框，不触发查询
    upRssFlowJob()  // 直接触发查询
}
```
3. upRssFlowJob 改为用 currentGroup + searchKey 组合：
```kotlin
private fun upRssFlowJob() {
    val searchKey = searchView.query?.toString()
    upRssFlowJob?.cancel()
    upRssFlowJob = viewLifecycleOwner.lifecycleScope.launch {
        val flow = when {
            currentGroup == getString(R.string.no_group) && searchKey.isNullOrBlank() ->
                appDb.rssSourceDao.flowEnabledNoGroup()  // 已有
            currentGroup == getString(R.string.no_group) && !searchKey.isNullOrBlank() ->
                appDb.rssSourceDao.flowNoGroupSearch(searchKey)  // 新增（见下方 DAO 新增）
            currentGroup != null && !searchKey.isNullOrBlank() ->
                appDb.rssSourceDao.flowGroupSearchExact(currentGroup!!, searchKey)  // 已有
            currentGroup != null && searchKey.isNullOrBlank() ->
                appDb.rssSourceDao.flowEnabledByGroup(currentGroup!!)  // 已有
            currentGroup == null && !searchKey.isNullOrBlank() ->
                appDb.rssSourceDao.flowEnabled(searchKey)  // 已有
            else -> appDb.rssSourceDao.flowEnabled()  // 已有
        }
        // ... collect flow
    }
}
```
4. 菜单 menu_group_text 快捷筛选也改为设置 currentGroup，不回填 searchView
5. ExploreFragment.kt 同理（用 BookSourceDao 的对应方法，需新增 flowExploreNoGroupSearch）

**需新增 DAO 方法（2个）**：

RssSourceDao.kt 新增 `flowNoGroupSearch(searchKey)`：
```sql
SELECT * FROM rssSources 
where enabled = 1 
and (sourceGroup is null or sourceGroup = '' or sourceGroup like '%未分组%')
and (sourceName like '%' || :searchKey || '%' 
    or sourceGroup like '%' || :searchKey || '%' 
    or sourceUrl like '%' || :searchKey || '%'
    or sourceComment like '%' || :searchKey || '%') 
order by customOrder
```

BookSourceDao.kt 新增 `flowExploreNoGroupSearch(searchKey)`：
```sql
select * from book_sources_part 
where enabledExplore = 1 and hasExploreUrl = 1
and (bookSourceGroup is null or bookSourceGroup = '' or bookSourceGroup like '%未分组%')
and (bookSourceGroup like '%' || :searchKey || '%' 
    or bookSourceName like '%' || :searchKey || '%') 
order by customOrder asc
```

**已有 DAO 方法对照表**（核实结果）：

| DAO | 方法 | 状态 |
|-----|------|------|
| RssSourceDao | flowEnabledNoGroup() | ✅ 已有（RssSourceDao.kt:97） |
| RssSourceDao | flowNoGroupSearch(searchKey) | ❌ 需新增 |
| RssSourceDao | flowGroupSearchExact(group, searchKey) | ✅ 已有（RssSourceDao.kt:94） |
| RssSourceDao | flowEnabledByGroup(searchKey) | ✅ 已有（RssSourceDao.kt:118） |
| RssSourceDao | flowEnabled(searchKey) | ✅ 已有（RssSourceDao.kt:108） |
| RssSourceDao | flowEnabled() | ✅ 已有 |
| BookSourceDao | flowExploreNoGroup() | ✅ 已有（BookSourceDao.kt:97） |
| BookSourceDao | flowExploreNoGroupSearch(searchKey) | ❌ 需新增 |
| BookSourceDao | flowGroupSearchExact(group, searchKey) | ✅ 已有（BookSourceDao.kt:130） |
| BookSourceDao | flowGroupExplore(key) | ✅ 已有（BookSourceDao.kt:165） |
| BookSourceDao | flowExplore(key) | ✅ 已有（BookSourceDao.kt:153） |

**ADR-03**：currentFilter 解耦 searchView
- Context：searchView 作为归类信息载体，用户输入名称后归类丢失
- Decision：引入 currentGroup 字段，searchView 只接收名称，用 DAO 组合查询
- Consequences：归类信息和名称搜索独立，用户体验正确

### 4. M-01/M-02 compact/grid 选择模式（管理页）

**现状**：BookSourceAdapterCompact/Grid 和 RssSourceAdapterCompact/Grid 无 selection 机制，Activity 硬编码 list adapter

**修复**：
1. 给 compact/grid adapter 添加 selection 机制（参考 list adapter）：
   - `private val selected = mutableSetOf<String>()`（用 bookSourceUrl/sourceUrl 作为 key）
   - `val selection: List<BookSourcePart/RssSource> get() = selected.mapNotNull { ... }`
   - `fun selectAll(selectAll: Boolean)` / `fun revertSelection()`
   - `fun setSelection(url: String, selected: Boolean)` / `fun checkSelectedInterval(...)`
   - `val dragSelectCallback = object : DragSelectTouchHelper.Callback { ... }`
2. compact adapter convert 添加 cb 复选框渲染 + 点击选择逻辑
3. grid adapter convert 添加 foreground 高亮选择逻辑
4. Activity 添加 `fun currentAdapter(): RecyclerAdapter<*,*>` 方法：
```kotlin
private fun currentAdapter() = when (AppConfig.sourceLayout) {
    1 -> adapterCompact
    in 2..6 -> adapterGrid
    else -> adapter
}
```
5. Activity 内所有 `adapter.selection`/`adapter.selectAll()` 改为 `currentAdapter().xxx`
6. itemTouchCallback 和 DragSelectTouchHelper 改为按 currentAdapter() 动态获取
7. 校验进度 notifyItemRangeChanged 改用 currentAdapter()

**ADR-04**：compact/grid selection 简化方案
- Context：compact/grid adapter 无 selection，P2 会提取基类
- Decision：P0 直接给 compact/grid 加 selection，P2 的 M-10 再提取基类
- Consequences：selection 逻辑重复，但 P0 快速恢复功能可用

## Data Flow

### F-01 修复后数据流

```
用户点击文件夹 → onFolderClick(group)
  → currentGroup = group
  → searchView.setQuery("", false)  // 清空，不触发
  → upRssFlowJob()
    → currentGroup != null && searchKey.notBlank() → flowGroupSearchExact(group, searchKey)
    → currentGroup != null && searchKey.blank() → flowEnabledByGroup(group)
    → currentGroup == null && searchKey.notBlank() → flowEnabled(searchKey)
    → currentGroup == null && searchKey.blank() → flowEnabled()
    → collect → adapter.setItems()

用户输入名称 → searchView.onQueryTextChange
  → upRssFlowJob()  // currentGroup 保持，searchKey 变更
    → 同上组合查询
```

### C-01 修复后数据流

```
BookSource 菜单排序 → AppConfig.bookSourceSort = X → sortSources() 用 bookSourceSort
RssSource 菜单排序 → AppConfig.rssSort = X → sortSources() 用 rssSort
两者独立，互不影响
```

## File Changes

### 配置层（C-01）
1. app/src/main/java/io/legado/app/constant/PreferKey.kt — sourceSort → bookSourceSort
2. app/src/main/java/io/legado/app/help/config/AppConfig.kt — sourceSort → bookSourceSort，启用 rssSort
3. app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt — 配置对话框按 Activity 类型区分

### 书源管理页（M-01 + C-01）
4. app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt — sourceSort → bookSourceSort + currentAdapter()
5. app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapterCompact.kt — 添加 selection
6. app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapterGrid.kt — 添加 selection

### 订阅源管理页（M-02 + C-01）
7. app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt — sourceSort → rssSort + currentAdapter()
8. app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceAdapterCompact.kt — 添加 selection
9. app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceAdapterGrid.kt — 添加 selection

### DAO 层（F-01 依赖，新增组合查询方法）
10. app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt — 新增 flowNoGroupSearch(searchKey)
11. app/src/main/java/io/legado/app/data/dao/BookSourceDao.kt — 新增 flowExploreNoGroupSearch(searchKey)

### 首页（F-01）
12. app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt — currentGroup + 组合查询
13. app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt — currentGroup + 组合查询

### 视频播放器（V-01）
14. app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt — onPrepared 用 isMuted

### 布局 XML（M-01 compact cb 复选框）
15. app/src/main/res/layout/item_book_source_compact.xml — 确认 cb 复选框存在
16. app/src/main/res/layout/item_rss_source_compact.xml — 确认 cb 复选框存在

## 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| M-01/M-02 selection 逻辑与 list adapter 不一致 | 中 | 选择状态错误 | 参照 list adapter 逐字段对比 |
| F-01 currentGroup 与 no_group 特殊处理遗漏 | 中 | 未分组源显示错误 | 仔细处理 no_group 分支 |
| C-01 旧 sourceSort 配置迁移 | 低 | 旧用户排序丢失 | 保留 sourceSort 兼容读取，迁移到 bookSourceSort |
| V-01 isMuted 初始化时序 | 低 | 首次播放不静音 | 确认 initView 在 onPrepared 前执行 |
