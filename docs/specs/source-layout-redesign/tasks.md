# Tasks: 书源/订阅源布局设置重做

> 关联文档：[README.md](./README.md) | [spec.md](./spec.md) | [design.md](./design.md)
>
> 任务编排原则：数据层 → UI 资源层 → Adapter 层 → Activity 集成层 → 文档同步 → 验证。
> 同一层内的任务相互独立，可并行；跨层任务存在依赖，须按顺序执行。

---

## Phase 1: Bug 修复（书源分组不生效）

> 优先级最高，独立于其他任务，可先行实施验证。

- [ ] 1.1 移除 `BookSourceActivity.kt` 中的 `groupMenuLifecycleOwner`
  - 删除 L149-161 的 `groupMenuLifecycleOwner` 定义
  - 删除 `onMenuOpened` / `onPanelClosed` 中的 `groupMenuLifecycleOwner.onMenuOpened/onMenuClosed()` 调用
  - **验证**：编译通过，搜索 `groupMenuLifecycleOwner` 全项目无残留引用

- [ ] 1.2 重写 `initLiveDataGroup()` 方法
  - 改为 `lifecycleScope.launch { appDb.bookSourceDao.flowGroups().flowOn(IO).conflate().collect { ... } }`
  - collect 块内：`groups.clear()` → `groups.addAll(it)` → `upGroupMenu()` → `if (isShowingFolder) upFolderView()`
  - 对齐订阅源 `RssSourceActivity.initGroupFlow()` 的实现
  - **验证**：编译通过，真机进入书源管理页 → 点击菜单 → 分组子菜单立即显示分组项（非空）

---

## Phase 2: 数据层（DAO + 配置 + 枚举）

> 为 UI 层提供数据查询能力和配置持久化能力。

- [ ] 2.1 `BookSourceDao.kt` 新增 `flowByType` 方法
  - 在 `BookSourceDao.kt` 中添加：`@Query("select * from book_sources_part where bookSourceType = :type order by customOrder asc") fun flowByType(type: Int): Flow<List<BookSourcePart>>`
  - 注意：`book_sources_part` 是 DatabaseView，字段名是 `bookSourceType`（不是 `type`）
  - **验证**：编译通过

- [ ] 2.2 `RssSourceDao.kt` 新增 `flowByType` 方法
  - 在 `RssSourceDao.kt` 中添加：`@Query("select * from rssSources where type = :type order by customOrder") fun flowByType(type: Int): Flow<List<RssSource>>`
  - **验证**：编译通过

- [ ] 2.3 新建 `RssSourceSort.kt` 枚举
  - 路径：`app/src/main/java/io/legado/app/ui/rss/source/manage/RssSourceSort.kt`
  - 内容：`enum class RssSourceSort { Default, Name, Url, Update, Enable }`
  - 参考 `BookSourceSort.kt` 的结构
  - **验证**：编译通过

- [ ] 2.4 `PreferKey.kt` 新增配置 key
  - 新增 `const val rssSort = "rssSort"`
  - 新增 `const val rssSortAscending = "rssSortAscending"`
  - **验证**：编译通过

- [ ] 2.5 `AppConfig.kt` 新增订阅源排序配置
  - 新增 `var rssSort: Int`（getPrefInt 默认 0，对应 RssSourceSort.Default）
  - 新增 `var rssSortAscending: Boolean`（getPrefBoolean 默认 true）
  - **验证**：编译通过

---

## Phase 3: UI 资源层（菜单 + 布局 + 对话框）

> 新增菜单项、item 布局、统一配置对话框。

- [ ] 3.1 `book_source.xml` 新增类型筛选 SubMenu
  - 在 `menu_group` 的 `<menu>` 内（`source_group` 之前或之后）新增：
    ```xml
    <item android:id="@+id/menu_type" android:title="@string/source_type">
      <menu>
        <group android:id="@+id/source_type_book" android:checkableBehavior="single">
          <item android:id="@+id/menu_type_all" android:title="@string/all" android:checked="true"/>
          <item android:id="@+id/menu_type_0" android:title="@string/type_text"/>
          <item android:id="@+id/menu_type_1" android:title="@string/type_audio"/>
          <item android:id="@+id/menu_type_2" android:title="@string/type_image"/>
          <item android:id="@+id/menu_type_3" android:title="@string/type_file"/>
          <item android:id="@+id/menu_type_4" android:title="@string/type_video"/>
        </group>
      </menu>
    </item>
    ```
  - **验证**：菜单预览可见类型子菜单

- [ ] 3.2 `rss_source.xml` 新增排序 + 类型筛选 SubMenu
  - 新增排序 SubMenu（参考 `book_source.xml` 的 `action_sort` 结构，仅含手动/名称/URL/更新时间/启用状态 + 倒序）
  - 新增类型筛选 SubMenu（仅含全部/网页/图片/视频，对应 type 0/1/2）
  - **验证**：菜单预览可见排序和类型子菜单

- [ ] 3.3 `strings.xml` 新增字符串资源
  - 新增：`source_type`（类型）、`type_text`（文本）、`type_audio`（音频）、`type_image`（图片）、`type_file`（文件）、`type_video`（视频）
  - 新增：`view_mode_list`（列表）、`view_mode_compact`（紧凑列表）、`view_mode_grid_2`（网格2列）、`view_mode_grid_3`（网格3列）、`view_mode_folder`（文件夹）
  - 新增：`sort_by_lastUpdateTime`（如已存在则复用）
  - **验证**：编译通过，无字符串资源缺失警告

- [ ] 3.4 新建 `item_book_source_compact.xml`
  - 路径：`app/src/main/res/layout/item_book_source_compact.xml`
  - 紧凑列表 item：单行显示源名 + 启用状态指示，高度小于列表 item
  - 参考 `item_book_source_list.xml`（如存在）的结构，精简布局
  - **验证**：布局预览可见

- [ ] 3.5 新建 `item_book_source_grid.xml`
  - 路径：`app/src/main/res/layout/item_book_source_grid.xml`
  - 网格 item：卡片样式，源名 + 启用状态，固定宽度
  - **验证**：布局预览可见

- [ ] 3.6 新建 `item_rss_source_compact.xml`
  - 路径：`app/src/main/res/layout/item_rss_source_compact.xml`
  - 参考 `item_book_source_compact.xml` 结构，适配订阅源字段（sourceName / sourceUrl）
  - **验证**：布局预览可见

- [ ] 3.7 新建 `item_rss_source_grid.xml`
  - 路径：`app/src/main/res/layout/item_rss_source_grid.xml`
  - 参考 `item_book_source_grid.xml` 结构
  - **验证**：布局预览可见

- [ ] 3.8 新建 `dialog_source_config.xml`
  - 路径：`app/src/main/res/layout/dialog_source_config.xml`
  - 参考 `dialog_bookshelf_config.xml` 结构
  - 包含：RadioGroup `rgView`（5个 RadioButton：列表/紧凑/网格2列/网格3列/文件夹）+ RadioGroup `rgSort`（5-7个排序项）+ SeekBar `sbMargin`
  - **验证**：布局预览可见，所有 ID 命名规范

---

## Phase 4: Adapter 层（多视图类型支持）

> Adapter 支持 getItemViewType 返回不同视图类型，按类型 inflate 不同 layout。

- [ ] 4.1 `BookSourceAdapter.kt` 支持多视图类型
  - 新增 `viewMode` 属性（由 Activity 设置）
  - 重写 `getItemViewType()`：根据 `viewMode` 返回 0=列表 / 2=紧凑 / 3-4=网格
  - `onCreateViewHolder` 根据 viewType inflate 对应 layout
  - `convert` 方法根据 viewType 绑定不同字段
  - **验证**：编译通过，三种视图类型均能正确显示数据

- [ ] 4.2 `RssSourceAdapter.kt` 支持多视图类型
  - 同 4.1，适配订阅源字段
  - **验证**：编译通过，三种视图类型均能正确显示数据

- [ ] 4.3 `SourceFolderAdapter.kt` 移除 `showConfigDialog`
  - 移除 companion object 中的 `showConfigDialog` 方法（迁移到 Activity）
  - 保留 `calculateSpanCount` 和 `spacingPx`（仍被使用）
  - **验证**：编译通过，搜索 `SourceFolderAdapter.showConfigDialog` 全项目无残留引用

---

## Phase 5: Activity 集成层（核心逻辑）

> 将数据层、UI 资源层、Adapter 层集成到 Activity，实现完整功能。

- [ ] 5.1 `BookSourceActivity.kt` 扩展 `applyListView()` 方法
  - 根据 `AppConfig.sourceViewMode` 选择 LayoutManager 和 item 类型：
    - 0 → LinearLayoutManager + 列表 item
    - 2 → LinearLayoutManager + 紧凑 item
    - 3 → GridLayoutManager(2) + 网格 item
    - 4 → GridLayoutManager(3) + 网格 item
  - 设置 `adapter.viewMode = AppConfig.sourceViewMode`
  - **验证**：切换视图模式后列表布局正确变化

- [x] 5.2 `BookSourceActivity.kt` 新增类型筛选分支
  - 在 `upBookSource(searchKey)` 方法中新增 `searchKey.startsWith("type:")` 分支
  - 解析 type 值，调用 `appDb.bookSourceDao.flowByType(type)`
  - 在 `onCompatOptionsItemSelected` 中处理 `menu_type_*` 菜单项，调用 `searchView.setQuery("type:X", true)`
  - **验证**：点击类型菜单项后列表正确筛选

- [ ] 5.3 `BookSourceActivity.kt` 实现统一配置对话框
  - 新建 `showSourceConfig()` 方法，使用 `DialogSourceConfigBinding`
  - 替换 `showFolderConfig()` 调用 `SourceFolderAdapter.showConfigDialog` 的逻辑
  - 对话框 OK 回调：保存视图模式 + 排序 + 间距，调用 `applyListView()` / `applyFolderView()` 刷新
  - **验证**：对话框显示正常，切换配置后视图立即刷新

- [ ] 5.4 `RssSourceActivity.kt` 扩展 `applyListView()` 方法
  - 同 5.1，适配订阅源
  - **验证**：切换视图模式后列表布局正确变化

- [ ] 5.5 `RssSourceActivity.kt` 新增排序逻辑
  - 新增 `sort` 和 `sortAscending` 变量
  - 在 `upSourceFlow` 的 Flow map 操作符中根据 `sort` 排序
  - 在 `onCompatOptionsItemSelected` 中处理排序菜单项
  - **验证**：切换排序方式后列表顺序正确变化

- [x] 5.6 `RssSourceActivity.kt` 新增类型筛选分支
  - 同 5.2，适配订阅源（仅 type 0/1/2）
  - **验证**：点击类型菜单项后列表正确筛选

- [ ] 5.7 `RssSourceActivity.kt` 实现统一配置对话框
  - 同 5.3，适配订阅源
  - **验证**：对话框显示正常，切换配置后视图立即刷新

---

## Phase 6: 文档同步

- [x] 6.1 更新 `app/src/main/assets/updateLog.md`
  - 在 `## cronet版本:` 行之后追加日期条目：
    ```
    **2026/07/08**
    - 书源管理分组菜单不生效的问题已修复
    - 书源/订阅源管理新增紧凑列表、网格2列、网格3列视图模式
    - 订阅源管理新增排序功能（手动/名称/URL/更新时间/启用状态）
    - 书源/订阅源管理新增按类型筛选（网页/图片/视频等）
    - 书源/订阅源布局设置入口统一为"布局设置"对话框
    ```

- [ ] 6.2 更新 `docs/INDEX.md`
  - 在 OpenSpec 索引区添加 source-layout-redesign 条目
  - 状态标记为 ✅ 已实施（待真机验证后）

---

## Phase 7: 编译验证

- [x] 7.1 执行 release 编译验证
  - 命令：`.\gradlew.bat assembleRelease`（或 assembleDebug）
  - **验证**：BUILD SUCCESSFUL，无编译错误、无 lint 致命错误

- [ ] 7.2 检查 Room schema 是否需要更新
  - 本次未修改 entity 的 @ColumnInfo，**无需**提升数据库版本
  - **验证**：确认 `AppDatabase.kt` version 仍为 93，schemas 目录无需新增 JSON

---

## Phase 8: 真机验证

- [x] 8.1 安装到逍遥模拟器
  - ADB 路径：`D:\Program Files\Microvirt\Memu\adb.exe`
  - 端口：`127.0.0.1:21503`
  - 包名：`io.legado.app.debug`
  - 命令：`adb install -r app/build/outputs/apk/debug/app-debug.apk`

- [ ] 8.2 验证书源分组 Bug 已修复
  - 进入书源管理页 → 点击菜单 → 分组
  - **预期**：分组子菜单立即显示所有分组项（非空）
  - 点击某个分组 → 列表筛选为该分组的源

- [ ] 8.3 验证书源视图模式切换
  - 菜单 → 布局设置 → 分别切换列表/紧凑/网格2列/网格3列/文件夹
  - **预期**：每种模式布局正确，切换无崩溃

- [x] 8.4 验证书源类型筛选
  - 菜单 → 类型 → 分别选择 文本/音频/图片/文件/视频
  - **预期**：列表仅显示对应类型的源
  - **实测**：文件夹视图"按类型"显示 6 个类型文件夹（全部分组/文本/音频/图片/文件/视频），点击"文本"→ query=type:0 → flowByType(0) 筛选生效

- [ ] 8.5 验证订阅源视图模式切换
  - 同 8.3，在订阅源管理页验证

- [ ] 8.6 验证订阅源排序
  - 菜单 → 排序 → 分别选择 手动/名称/URL/更新时间/启用状态 + 倒序
  - **预期**：列表顺序正确变化

- [x] 8.7 验证订阅源类型筛选
  - 菜单 → 类型 → 分别选择 网页/图片/视频
  - **预期**：列表仅显示对应类型的源
  - **实测**：文件夹视图"按类型"显示 4 个类型文件夹（全部分组/网页/图片/视频），点击"视频"→ query=type:2 → flowByType(2) 筛选生效

- [x] 8.8 日志分析
  - 抓取 logcat 日志：`adb logcat -d > temp/tmp/source-layout-test.log`
  - 检查关键字：`FATAL EXCEPTION`、`IllegalStateException`、`Room cannot verify`
  - **预期**：无崩溃日志、无异常堆栈
  - **实测**：logcat 无 FATAL EXCEPTION，仅 ADB input 命令的 Debug 日志

---

## AOAdapt 日志

> 记录实施过程中与设计文档不一致的发现、决策调整、踩坑。

### 2026-07-08 初始创建

- **设计文档与实施一致**：四文档基于对 `BookSourceActivity.kt`、`RssSourceActivity.kt`、`BookSourceDao.kt`、`RssSourceDao.kt`、`AppConfig.kt`、`SourceFolderAdapter.kt`、`book_source.xml`、`rss_source.xml` 的源码分析生成，未发现设计与源码冲突。
- **待实施时确认事项**：
  - `BookSourceAdapter.kt` 和 `RssSourceAdapter.kt` 的现有结构需在 Phase 4 实施时进一步读取确认（当前基于推断）
  - `dialog_bookshelf_config.xml` 的具体结构需在 Phase 3.8 实施时读取参考
  - `item_book_source_list.xml` 是否存在需在 Phase 3.4 实施时确认（若不存在则参考现有 list item 布局）
- **Room schema 影响**：本次仅新增 DAO 查询方法，未修改 entity，无需 Migration。

### 2026-07-08 Phase 3 文件夹视图"按类型"遗漏修复

- **问题发现**：用户反馈"选了按类型，没有按类型字段进行文件夹归类展示"。根因定位：Phase 3 实施时菜单 XML（menu_type_*）、DAO（flowByType）、配置对话框（sourceFolderStyle Spinner）都已就绪，但 Activity 层处理逻辑完全缺失：
  1. `upFolderView()` 未根据 `sourceFolderStyle` 生成不同文件夹列表（始终生成"按分组"列表）
  2. `onFolderClick()` 未处理类型文件夹点击（无法映射到 `type:X` 查询）
  3. `upBookSource()`/`upSourceFlow()` 未处理 `type:` 前缀查询
  4. `onCompatOptionsItemSelected()` 未处理 `menu_type_*` 菜单项
  5. `showFolderConfig()` 的"仅样式变更"分支未调用 `upFolderView()` 刷新文件夹数据（仅重应用布局）
- **修复内容**：
  - `BookSourceActivity.kt`：修改 upFolderView/onFolderClick/upBookSource/onCompatOptionsItemSelected/showFolderConfig 共 5 处
  - `RssSourceActivity.kt`：同样修改 5 处（类型映射 0=网页/1=图片/2=视频）
  - `values-zh/strings.xml`：补充 source_type/type_text/type_audio/type_image/type_file/type_video/type_web 共 7 条中文翻译
- **验证结果**：编译通过（BUILD SUCCESSFUL）+ 真机验证通过（书源显示 6 个类型文件夹、订阅源显示 4 个类型文件夹、点击筛选 type:X 生效、logcat 无崩溃）
- **教训**：菜单 XML 定义了选项 ≠ Activity 有处理逻辑；配置对话框有 Spinner ≠ upFolderView 读取了该配置。后续实施必须逐层验证"配置项→读取→生效"完整链路。

### 2026-07-08 Phase 5 Activity 集成层深度重构（continuation 方案完成）

> 本轮对应方案文档：`source-layout-deep-refactor.md` + `source-layout-refactor-continuation.md`，Task #53-#68。
> 旧 tasks.md 的 Phase 4（Adapter 多视图类型 getItemViewType 方案）已废弃，改为独立适配器（adapterCompact/adapterGrid）方案；Phase 5 各项通过新方案实现。

- **BookSourceActivity.kt 完整重构**（Task #62-#65）：
  - 新增状态变量 `currentType`/`currentGroup`/`inSubDirectory`/`isShowingFolder`，替换旧 `isFolderViewMode` 单一布尔
  - 新增 `adapterCompact`/`adapterGrid` 懒加载
  - 菜单排序项同步 `AppConfig.sourceSort = 0`（使旧 sort 逻辑生效）；快捷筛选词/类型/动态分组菜单改用状态变量
  - `applyListView` 支持 `sourceLayout` 0=列表/1=紧凑/2-6=网格；`applyFolderView` 改用 `sourceMargin`
  - `showFolderConfig` 使用新签名（`onConfigChanged` 回调）+ `applyConfigChange` 统一应用
  - `upBookSource` 完全重构（隐藏字段方案 + DAO 组合查询 `flowByTypeSearch`/`flowGroupSearchExact`）
  - 新增 `sortSources` 方法（双轨排序：sourceSort!=0 用新配置，==0 回退旧 sort 逻辑）
  - 新增 `onBackPressed`（子目录返回根目录）
  - `onFolderClick` 重构（状态变量，不触碰搜索框）
- **BookSourceAdapter.kt**（Task #66）：`showMenu` 中 `menu_top`/`menu_bottom` 可见性增加 `AppConfig.sourceSort == 0` 检查
- **RssSourceActivity.kt 完整重构**（Task #67）：同构 BookSourceActivity，类型映射 0=网页/1=图片/2=视频
- **搜索框反模式修复**（核心诉求）：禁止回填 `type:`/`group:` 到搜索框，改为隐藏字段 `currentType`/`currentGroup` 传给后端，搜索框只做名称搜索；进入子目录后搜索框仍可正常使用
- **教训**：两维度独立架构（分组样式 × 视图模式）必须用独立配置项，不能用单一 sourceFolderStyle 耦合；搜索框回填前缀词是反模式，用户输入与筛选状态应分离。

### 2026-07-08 Task #68 编译验证发现并修复 3 个问题

- **问题1：BookSourceDao view 缺列**：`flowByTypeSearch`/`flowGroupSearchExact` 直接从 `book_sources_part` view 引用 `bookSourceComment`，但 view 的 SELECT 列表不含该列，KSP 编译报 `no such column: bookSourceComment`。修复：参照已有 `flowSearch` 的 join 模式，改为 `from book_sources b join book_sources_part bp`，用 `b.bookSourceComment`（完整表含该列），返回 `bp.*`。RssSourceDao 无此问题（RssSource 是 @Entity 表，含 sourceComment）。
- **问题2：collect 适配器硬编码**：`upBookSource`/`upSourceFlow` 的 collect 中 `adapter.setItems` 硬编码列表适配器，网格/紧凑视图下数据不更新到 `adapterGrid`/`adapterCompact`（因为 `when` 表达式推断为公共父类型 RecyclerAdapter，`diffItemCallback` 是各子类自定义字段，父类无该字段导致 Unresolved reference）。修复：collect 中按 `AppConfig.sourceLayout` 用 `when` 分发到具体适配器调用 `setItems`。
- **问题3：RssSourceActivity 排序菜单遗漏**：`rss_source.xml` 定义了 6 个排序菜单项（manual/name/url/time/enable/desc），但 `onCompatOptionsItemSelected` 未处理，点击无反应。修复：补全 6 项映射到 `sourceSort` 配置（manual=0/name=1/enable=2/url=5/time=6/desc 切换 sortAscending）+ `onPrepareOptionsMenu` 同步 `menu_sort_desc` 勾选 + `sortSources` 扩展 `sourceSort=6`（按 lastUpdateTime）。BookSourceActivity 的 sortSources 也加 sourceSort=6（防御性处理共享配置）。
- **验证结果**：`./gradlew.bat :app:assembleDebug` BUILD SUCCESSFUL，仅剩 onBackPressed 的 deprecated 警告（Android API 33+ 通用问题，@Suppress("DEPRECATION") 部分抑制，不影响功能）。
