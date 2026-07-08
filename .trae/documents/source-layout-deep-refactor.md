# 书源/订阅源布局深度重构方案（学习书架布局反哺）

> **目标**：将书架布局的两维度独立架构（分组样式 + 视图模式 + 排序）反哺到书源/订阅源管理界面，并修复搜索框回填 `type:`/`group:` 反模式。

---

## 一、摘要

当前书源/订阅源布局只有 2 种视图（列表/文件夹）+ 2 种分组样式（按分组/按类型），远低于书架的 7 种视图 + 2 种分组样式 + 6 种排序。用户强烈要求深度学习书架布局，本次重构将：

1. **分组样式** 从 2 种扩展为 3 种：列表（平铺）/ 按类型 / 按分组
2. **视图模式** 从 2 种扩展为 7 种：列表 / 紧凑 / 网格 2-6 列
3. **排序功能** 新增 6 种排序选项
4. **搜索框** 改为隐藏字段方案，禁止回填 `type:`/`group:`，进入子目录后搜索框仍可用
5. **文件夹样式** 对齐书架 grid 风格
6. **配置对话框** 参考 `dialog_bookshelf_config.xml` 重构

---

## 二、当前状态分析

### 2.1 书架架构（学习对象）

书架采用**两维度独立**设计：

| 维度 | 配置项 | 取值 | 说明 |
|------|--------|------|------|
| 分组样式 | `bookGroupStyle` | 0=Tab, 1=Folder | 控制分组组织方式 |
| 视图模式 | `bookshelfLayout` | 0=列表, 1=紧凑, 2-6=网格2-6列 | 控制单项显示方式 |
| 排序 | `bookshelfSort` | 0-5 | 控制排序 |
| 间距 | `bookshelfMargin` | 0-60, 默认12 | 卡片间距 |

关键文件：
- [BaseBookshelfFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt) - `configBookshelf()` 读取/保存配置
- [BookshelfFragment2.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/style2/BookshelfFragment2.kt) - Folder 模式：单一 Adapter 混合显示 group+book，点击进入子分类
- [BooksFragment.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/style1/books/BooksFragment.kt) L67-79 - 按 bookshelfLayout 选择 Adapter（List/List2/Grid）
- [dialog_bookshelf_config.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/dialog_bookshelf_config.xml) - 配置对话框模板

### 2.2 当前书源/订阅源架构（重构对象）

| 配置项 | 取值 | 问题 |
|--------|------|------|
| `sourceViewMode` | 0=列表, 1=文件夹 | 与分组样式耦合，应拆分 |
| `sourceFolderStyle` | 0=按分组, 1=按类型 | 缺"列表平铺"选项 |
| `sourceFolderMargin` | 0-60 | ✅ 可复用 |
| 无 | - | 缺视图模式维度（紧凑/网格） |
| 无 | - | 缺排序维度 |

关键问题：
1. **搜索框回填反模式**：`searchView.setQuery("type:X"/"group:X", true)` 导致进入子分类后搜索框失效
2. **视图模式单一**：只有列表项（item_book_source.xml），无紧凑/网格变体
3. **文件夹样式**：用首字占位（可接受），但卡片风格与书架不完全一致
4. **DAO 查询缺口**：`flowByType(type)` 无名称搜索组合，`flowGroupSearch(key)` 也无名称搜索组合

---

## 三、提议变更

### 3.1 配置维度重构（AppConfig + PreferKey）

**新增 3 个配置属性，废弃 2 个旧属性（保留迁移兼容）**：

| 新配置项 | 取值 | 默认值 | PreferKey |
|----------|------|--------|-----------|
| `sourceGroupStyle` | 0=列表(平铺), 1=按类型, 2=按分组 | 0 | `sourceGroupStyle` |
| `sourceLayout` | 0=列表, 1=紧凑, 2-6=网格2-6列 | 0 | `sourceLayout` |
| `sourceSort` | 0=手动, 1=名称, 2=启用, 3=类型, 4=分组, 5=URL | 0 | `sourceSort` |
| `sourceMargin` | 0-60 | 12 | `sourceMargin`（复用旧 sourceFolderMargin） |

**迁移逻辑**（AppConfig 初始化时执行一次）：
```
旧 sourceViewMode=0 + sourceFolderStyle=0 → sourceGroupStyle=0
旧 sourceViewMode=1 + sourceFolderStyle=0 → sourceGroupStyle=2
旧 sourceViewMode=1 + sourceFolderStyle=1 → sourceGroupStyle=1
旧 sourceViewMode=0 + sourceFolderStyle=1 → sourceGroupStyle=0
```

**修改文件**：
- [AppConfig.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/config/AppConfig.kt) L249-275：新增 `sourceGroupStyle`/`sourceLayout`/`sourceSort` 属性，保留旧属性加 `@Deprecated` 注解，新增 `migrateSourceConfig()` 迁移方法
- [PreferKey.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/PreferKey.kt) L226-230：新增 `sourceGroupStyle`/`sourceLayout`/`sourceSort` 常量

### 3.2 DAO 新增组合查询方法

**BookSourceDao.kt** 新增 2 个方法：

```kotlin
@Query(
    """select bp.* from book_sources_part bp
    where bp.bookSourceType = :type
    and (bp.bookSourceName like '%' || :searchKey || '%'
        or bp.bookSourceGroup like '%' || :searchKey || '%'
        or bp.bookSourceUrl like '%' || :searchKey || '%'
        or bp.bookSourceComment like '%' || :searchKey || '%')
    order by bp.customOrder asc"""
)
fun flowByTypeSearch(type: Int, searchKey: String): Flow<List<BookSourcePart>>

@Query(
    """select * from book_sources_part 
    where (bookSourceGroup = :group
        or bookSourceGroup like :group || ',%' 
        or bookSourceGroup like  '%,' || :group
        or bookSourceGroup like  '%,' || :group || ',%')
    and (bookSourceName like '%' || :searchKey || '%'
        or bookSourceGroup like '%' || :searchKey || '%'
        or bookSourceUrl like '%' || :searchKey || '%'
        or bookSourceComment like '%' || :searchKey || '%')
    order by customOrder asc"""
)
fun flowGroupSearchExact(group: String, searchKey: String): Flow<List<BookSourcePart>>
```

**RssSourceDao.kt** 同样新增 2 个方法（字段名替换为 sourceName/sourceGroup/sourceUrl/sourceComment）。

**修改文件**：
- [BookSourceDao.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/dao/BookSourceDao.kt) L103 后新增
- [RssSourceDao.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/data/dao/RssSourceDao.kt) L69 后新增

### 3.3 Activity 搜索隐藏字段方案重构

**核心设计**：Activity 维护状态变量，搜索框只做名称搜索，进入子目录不触碰搜索框。

```kotlin
// 新增状态变量（BookSourceActivity / RssSourceActivity）
private var currentType: Int = -1        // -1=全部, 0-4=具体类型
private var currentGroup: String? = null // null=根目录, 非空=在某个分组内
private val inSubDirectory: Boolean get() = currentType >= 0 || currentGroup != null
```

**加载逻辑重构**（`upBookSource` 方法）：

```kotlin
private fun upBookSource(searchKey: String? = null) {
    // 名称搜索关键字（去掉 type:/group: 前缀的历史兼容）
    val nameQuery = searchKey?.let { 
        when {
            it.startsWith("type:") -> ""   // 历史回填，清空
            it.startsWith("group:") -> ""  // 历史回填，清空
            else -> it
        }
    }
    
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
            // 根目录：名称搜索
            !nameQuery.isNullOrEmpty() -> appDb.bookSourceDao.flowSearch(nameQuery)
            // 根目录：全部
            else -> appDb.bookSourceDao.flowAll()
        }
        // ... 排序逻辑保持不变
    }
}
```

**文件夹点击逻辑**（`onFolderClick`）：

```kotlin
override fun onFolderClick(group: String) {
    when (AppConfig.sourceGroupStyle) {
        1 -> { // 按类型
            currentType = mapTypeStringToInt(group)  // "文本"→0, "音频"→1, etc.
            currentGroup = null
        }
        2 -> { // 按分组
            currentType = -1
            currentGroup = group
        }
    }
    // 不触碰 searchView！搜索框保持原样
    applyListView()  // 切换到列表视图显示子目录内容
    upBookSource(searchView.query?.toString())
    invalidateOptionsMenu()
}
```

**返回逻辑**（`onBackPressed` / 工具栏返回）：

```kotlin
// 返回根目录：重置状态变量，不触碰搜索框
private fun backToRoot() {
    if (inSubDirectory) {
        currentType = -1
        currentGroup = null
        if (AppConfig.sourceGroupStyle == 0) {
            applyListView()
        } else {
            applyFolderView()
            upFolderView()
        }
        upBookSource(searchView.query?.toString())
    } else {
        finish()  // 退出 Activity
    }
}
```

**菜单类型筛选重构**（`onCompatOptionsItemSelected`）：
- 移除 `menu_type_all/0~4` 直接设置 `searchView.setQuery("type:X", true)` 的逻辑
- 改为设置 `currentType` 状态变量 + 调用 `upBookSource()`
- `menu_type_all` → `currentType = -1`

**视图切换逻辑**（`showFolderConfig` 回调）：

```kotlin
// 配置变更后的视图应用
private fun applyConfigChange() {
    // 根据 sourceGroupStyle 决定根目录显示模式
    when (AppConfig.sourceGroupStyle) {
        0 -> { // 列表平铺：直接显示所有源
            currentType = -1
            currentGroup = null
            applyListView()
            upBookSource(searchView.query?.toString())
        }
        1, 2 -> { // 按类型/按分组：显示文件夹
            if (inSubDirectory) {
                applyListView()  // 子目录内保持列表视图
                upBookSource(searchView.query?.toString())
            } else {
                applyFolderView()
                upFolderView()
            }
        }
    }
}
```

**修改文件**：
- [BookSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceActivity.kt) - 重构 `upBookSource`/`onFolderClick`/`onCompatOptionsItemSelected`/`showFolderConfig`/返回逻辑
- [RssSourceActivity.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceActivity.kt) - 同上（类型映射 0=网页/1=图片/2=视频）

### 3.4 视图模式适配器（学习书架 BooksAdapter 模式）

**新增 3 个适配器**（书源/订阅源共用一套，差异通过参数控制）：

| 适配器 | sourceLayout | 布局文件 | 说明 |
|--------|--------------|----------|------|
| `BookSourceAdapter`（改造现有） | 0=列表 | item_book_source.xml（保留） | 完整信息：名称+URL+启用+类型 |
| `BookSourceAdapterCompact`（新增） | 1=紧凑 | item_book_source_compact.xml（新增） | 单行：名称+启用开关+类型徽章 |
| `BookSourceAdapterGrid`（新增） | 2-6=网格 | item_book_source_grid.xml（新增） | 卡片：名称+类型图标+启用指示 |

**Activity 中适配器选择逻辑**（参考 BooksFragment L67-79）：

```kotlin
private val sourceAdapter: RecyclerView.Adapter<*> by lazy {
    when (AppConfig.sourceLayout) {
        0 -> BookSourceAdapter(this, callBack, binding.rvBookSource)
        1 -> BookSourceAdapterCompact(this, callBack)
        else -> BookSourceAdapterGrid(this, callBack)
    }
}

private fun applyListView() {
    val layoutManager = when (AppConfig.sourceLayout) {
        0, 1 -> LinearLayoutManager(this)
        else -> GridLayoutManager(this, AppConfig.sourceLayout)
    }
    binding.rvBookSource.layoutManager = layoutManager
    binding.rvBookSource.adapter = sourceAdapter
}
```

**新建文件**：
- `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapterCompact.kt`
- `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceAdapterGrid.kt`
- `app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceAdapterCompact.kt`
- `app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceAdapterGrid.kt`
- `app/src/main/res/layout/item_book_source_compact.xml`
- `app/src/main/res/layout/item_book_source_grid.xml`
- `app/src/main/res/layout/item_rss_source_compact.xml`
- `app/src/main/res/layout/item_rss_source_grid.xml`

**简化说明**：紧凑/网格适配器仅支持显示核心信息（名称+启用+类型），不支持拖拽排序和选择模式 | 已知上限：网格模式下批量操作需切换回列表模式 | 升级路径：为网格适配器添加 LongClick 进入选择模式

### 3.5 文件夹样式对齐书架

**item_source_folder_grid.xml 优化**：
- 保留 3:4 比例 + 主题色背景 + 首字占位（当前实现合理）
- 新增：类型文件夹使用类型图标（矢量图）替代首字
- 新增：BadgeView 显示文件夹内源数量（可选，需 DAO COUNT 查询）

**SourceFolderAdapter 改造**：
- 数据模型从 `String` 改为 `data class SourceFolder(val name: String, val type: Int, val count: Int)`
- 按类型文件夹：显示类型图标
- 按分组文件夹：显示首字
- 支持网格列数随 sourceLayout 变化

**修改文件**：
- [item_source_folder_grid.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/item_source_folder_grid.xml) - 新增 iv_folder_type_icon（类型图标 ImageView）
- [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) - 数据模型扩展，convert 逻辑分类型/分组

**简化说明**：文件夹源数量显示需新增 DAO COUNT 查询，首版不做 | 已知上限：用户无法看到文件夹内源数量 | 升级路径：新增 `countByType(type)` / `countByGroup(group)` DAO 方法

### 3.6 配置对话框重构（参考 dialog_bookshelf_config.xml）

**dialog_source_folder_config.xml 重构**：

```xml
<!-- 1. 分组样式 Spinner（3选项） -->
<Spinner id="sp_group_style" entries="@array/source_group_style_new" />
<!-- source_group_style_new: 列表(平铺) / 按类型 / 按分组 -->

<!-- 2. 视图模式 RadioGroup（7选项） -->
<RadioGroup id="rg_layout">
    <RadioButton text="@string/layout_list" />           <!-- 0 -->
    <RadioButton text="@string/layout_list_compact" />   <!-- 1 -->
    <RadioButton text="@string/layout_grid2" />          <!-- 2 -->
    <RadioButton text="@string/layout_grid3" />          <!-- 3 -->
    <RadioButton text="@string/layout_grid4" />          <!-- 4 -->
    <RadioButton text="@string/layout_grid5" />          <!-- 5 -->
    <RadioButton text="@string/layout_grid6" />          <!-- 6 -->
</RadioGroup>

<!-- 3. 排序 RadioGroup（6选项） -->
<RadioGroup id="rg_sort">
    <RadioButton text="@string/source_sort_0" />  <!-- 手动 -->
    <RadioButton text="@string/source_sort_1" />  <!-- 名称 -->
    <RadioButton text="@string/source_sort_2" />  <!-- 启用 -->
    <RadioButton text="@string/source_sort_3" />  <!-- 类型 -->
    <RadioButton text="@string/source_sort_4" />  <!-- 分组 -->
    <RadioButton text="@string/source_sort_5" />  <!-- URL -->
</RadioGroup>

<!-- 4. 间距 SeekBar -->
<DetailSeekBar id="sb_margin" max="60" />
```

**SourceFolderAdapter.showConfigDialog 重构**：
- 参数从 `currentViewMode: Int` 改为 `onConfigChanged: () -> Unit`（配置变更后由 Activity 决定如何刷新）
- 保存 sourceGroupStyle/sourceLayout/sourceSort/sourceMargin 4 个配置
- 调用 `onConfigChanged()` 回调，Activity 内执行 `applyConfigChange()`

**修改文件**：
- [dialog_source_folder_config.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/layout/dialog_source_folder_config.xml) - 完全重构
- [SourceFolderAdapter.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt) - showConfigDialog 方法重构
- [arrays.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/values/arrays.xml) L36-39 - 新增 `source_group_style_new` 数组

### 3.7 排序实现

**Activity 排序逻辑**（参考 BookshelfFragment2 L182-202）：

```kotlin
private fun sortSources(list: List<BookSourcePart>): List<BookSourcePart> {
    return when (AppConfig.sourceSort) {
        0 -> list.sortedBy { it.customOrder }                              // 手动
        1 -> list.sortedWith { o1, o2 -> o1.bookSourceName.cnCompare(o2.bookSourceName) }  // 名称
        2 -> list.sortedByDescending { it.enabled }                       // 启用
        3 -> list.sortedBy { it.bookSourceType }                          // 类型
        4 -> list.sortedBy { it.bookSourceGroup ?: "" }                   // 分组
        5 -> list.sortedBy { it.bookSourceUrl }                           // URL
        else -> list.sortedBy { it.customOrder }
    }
}
```

**修改文件**：
- BookSourceActivity.kt / RssSourceActivity.kt - 在 `upBookSource` 的 map 逻辑中替换现有排序

### 3.8 资源文件更新

**arrays.xml 新增**：
```xml
<string-array name="source_group_style_new">
    <item>@string/source_group_style_list</item>
    <item>@string/source_group_style_by_type</item>
    <item>@string/source_group_style_by_group</item>
</string-array>
```

**strings.xml 新增**（中文）：
```xml
<string name="source_group_style_list">列表</string>
<string name="source_group_style_by_type">按类型</string>
<string name="source_group_style_by_group">按分组</string>
<string name="source_sort_0">手动排序</string>
<string name="source_sort_1">按名称</string>
<string name="source_sort_2">按启用状态</string>
<string name="source_sort_3">按类型</string>
<string name="source_sort_4">按分组</string>
<string name="source_sort_5">按URL</string>
```

**修改文件**：
- [arrays.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/values/arrays.xml)
- [strings.xml](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/res/values/strings.xml) + values-zh/strings.xml

### 3.9 updateLog.md 更新

```markdown
**2026/07/08**
- 书源/订阅源管理界面布局深度重构：新增列表/紧凑/网格2-6列共7种视图模式
- 分组样式扩展为3种：列表平铺/按类型/按分组
- 新增排序功能（手动/名称/启用/类型/分组/URL）
- 修复搜索框回填type:/group:导致子目录内搜索失效的问题，改为隐藏字段方案
- 文件夹样式对齐书架风格
```

---

## 四、假设与决策

### 4.1 假设

1. **书源/订阅源无封面图**：网格模式用首字+类型图标占位，不加载网络图片
2. **旧配置迁移**：用户首次升级时自动迁移，旧 `sourceViewMode`/`sourceFolderStyle` 废弃但保留兼容
3. **紧凑/网格模式不支持拖拽**：拖拽排序仅在列表模式（sourceLayout=0）下可用，与书架行为一致
4. **类型文件夹图标**：文本=文档图标，音频=音符图标，图片=图片图标，文件=文件图标，视频=播放图标（使用 Material Icons）

### 4.2 决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 适配器架构 | 分离 3 个适配器（List/Compact/Grid） | 对齐书架 BooksAdapterList/List2/Grid 模式 |
| 搜索隐藏字段 | Activity 状态变量 + DAO 组合查询 | 彻底解决回填反模式，子目录搜索可用 |
| 旧配置迁移 | 保留旧 key + 启动时迁移一次 | 避免用户配置丢失 |
| 文件夹源数量 | 首版不显示 | 需新增 COUNT 查询，首版聚焦核心需求 |
| 排序选项 | 6 种（手动/名称/启用/类型/分组/URL） | 覆盖书源常用排序场景 |

### 4.3 不做的事（YAGNI）

- 不引入 Tab 分组样式（书源场景不需要标签页切换）
- 不为网格模式实现批量选择（复杂度高，用户可切换列表模式操作）
- 不实现文件夹源数量徽章（需 COUNT 查询，首版省略）
- 不重构 BookSourceAdapter 的拖拽逻辑（保持现有实现）

---

## 五、验证步骤

### 5.1 编译验证
```bash
./gradlew :app:assembleDebug
```

### 5.2 功能验证（逍遥模拟器 127.0.0.1:21503）

| 用例 | 预期结果 |
|------|----------|
| 默认配置启动书源管理 | 显示列表平铺 + 列表视图 |
| 配置对话框切换"按类型" | 根目录显示 6 个类型文件夹 |
| 配置对话框切换"按分组" | 根目录显示分组文件夹 |
| 配置对话框切换"网格3列" | 文件夹/源项以 3 列网格显示 |
| 点击类型文件夹 | 进入子目录，显示该类型所有源，搜索框清空可用 |
| 子目录内输入名称搜索 | 仅在该类型内筛选名称，不回退到根目录 |
| 子目录内按返回键 | 返回根目录文件夹视图，搜索框内容保留 |
| 根目录输入名称搜索 | 全局名称搜索 |
| 菜单"类型→文本" | 进入文本类型子目录（隐藏字段方式） |
| 切换排序为"按名称" | 列表按名称排序 |
| 订阅源管理界面 | 同样支持 3 种分组 + 7 种视图 + 6 种排序 |

### 5.3 回归验证
- 旧配置用户升级后，配置正确迁移
- 拖拽排序在列表模式仍可用
- 书源启用/禁用/选择等现有功能不受影响

---

## 六、实施顺序

1. **AppConfig + PreferKey + 迁移逻辑**（基础设施）
2. **DAO 新增组合查询方法**（数据层）
3. **strings.xml + arrays.xml**（资源层）
4. **item_source_folder_grid.xml + SourceFolderAdapter**（文件夹样式）
5. **dialog_source_folder_config.xml 重构**（配置对话框）
6. **新增紧凑/网格适配器 + 布局**（视图层）
7. **BookSourceActivity 重构**（搜索隐藏字段 + 视图切换 + 排序）
8. **RssSourceActivity 重构**（同上）
9. **updateLog.md 更新**
10. **编译验证 + 真机验证**

---

## 七、风险与回退

| 风险 | 缓解措施 |
|------|----------|
| 旧配置迁移失败 | 保留旧 key，迁移失败时使用默认值 |
| 网格适配器性能问题 | 使用 RecyclerView.RecycledViewPool |
| 搜索隐藏字段与菜单筛选冲突 | 统一通过 currentType/currentGroup 状态变量 |
| 配置对话框布局复杂 | 参考 dialog_bookshelf_config.xml 已验证结构 |
