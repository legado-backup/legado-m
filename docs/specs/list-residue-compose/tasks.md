# tasks.md — 遗留列表 Compose 化收尾（CacheActivity + ExploreFragment 瀑布列表）

## 1. 缓存列表页 Compose 化（遗留项 7.11ai）

### 1.1 CacheScreen.kt 纯 Compose 列表

- [x] 1.1 `CacheScreen.kt` 新增：纯 Compose `LazyColumn` + `itemsIndexed(key = { it.bookUrl })`
- [x] 1.2 item @Composable 迁移 7 字段：`name` / `author` /（下载进度 + 本地标记）/（播放或停止图标）/（导出）/（导出消息）/（导出进度条）
- [x] 1.3 点击回调：`ivDownload` → `onDownloadToggle(book)`；`tvExport` → `onExport(book)`；条目本体无点击
- [x] 1.4 `upDownloadIv` 语义：isLocal 隐藏 + 运行/停止图标切换
- [x] 1.5 `upExportInfo` 语义：`exportMsg` / `exportProgress` 迁移为 Compose 状态

### 1.2 CacheActivity.kt 改造

- [x] 1.6 移除 `initRecyclerView()`/`CacheAdapter` 接线，`setContent` 改装配 `CacheScreen`（保留顶栏 `GlassTopAppBar` + `AppDropdownMenu`）
- [x] 1.7 `initBookData()` 数据流（flowByGroup → 过滤 !isAudio → 排序）改为 `mutableStateListOf<Book>`
- [x] 1.8 菜单 `adapter.getItems()` / `getItem(position)` → 读 Compose 列表状态（按 `bookUrl` 定位）
- [x] 1.9 局部刷新：`upAdapterLiveData` / `EXPORT_BOOK` / `UP_DOWNLOAD` → 按 `bookUrl` 更新 Compose 状态，不再 `notifyItemChanged`
- [x] 1.10 编译通过；删除 `CacheAdapter.kt`；确认全仓无残留引用

## 2. 探索瀑布列表 Compose 化（遗留项 7.11aj）

### 2.1 瀑布列表变体

- [x] 2.1 `ExploreModernListScreen` 新增瀑布变体：`LazyVerticalStaggeredGrid`（对应 `layoutMode==2`）
- [x] 2.2 瀑布 item @Composable：封面 + `aspectRatio`（由原 `setImageSizeRatio` 宽高比字段换算）
- [x] 2.3 瀑布点击复用 `showBookInfo(book)`（`searchBookDao.insert` + `SearchBookOpenHelper.open`）
- [x] 2.4 滚动到底加载更多：`derivedStateOf` / `LaunchedEffect` 触发 `loadDiscoverBooks(false)`，去重处理
- [x] 2.5 瀑布与既有现代列表共享 loading / HasMore / 空态 / 回调闭包

### 2.2 ExploreFragment.kt 瀑布段替换

- [x] 2.6 `rvDiscoverBooks` + `ExploreShowWaterfallAdapter` 分支移除，瀑布走 Compose 状态驱动
- [x] 2.7 `currentDiscoverScrollTarget()` 的 `rvDiscoverBooks` 分支 → Compose 状态
- [x] 2.8 `updateModernTopBarOverlay()` padding / clipToPadding / swipeRefresh offset → `composeDiscoverTopPadding` 统一接管
- [x] 2.9 `applyDiscoverBookContainerMargins()` → Compose `modifier.padding`
- [x] 2.10 辅助状态（`composeDiscoverLoading` / `HasMore` / `TopPadding` / `layoutMode` / `listStyle` / `ScrollToTopSignal` / `BookshelfVersion`）接入瀑布分支
- [x] 2.11 `classic` / `suite` / 现代列表（`layoutMode != 2`）回归不受破坏

### 2.3 删除适配器

- [x] 2.12 编译通过；删除 `ExploreShowWaterfallAdapter.kt`；确认全仓无残留引用

## 3. 收尾验证

- [x] 3.1 真机回归——缓存页（2026-08-25 082520 测试包，模拟器 Android 9）：顶栏 GlassTopAppBar（返回/下载/分组按钮 content-desc 命中）✓、更多菜单 13 项全值与迁移前等价（导出所有/自定义Epub导出章节/导出文件夹/缓存并发率(默认)/缓存分项/多线程导出/导出文件名/日志/替换净化/导出格式(txt)/导出编码(UTF-8)/导出到 WebDav/TXT 导出图片）✓、下载子菜单（下载全部章节/下载之后章节）✓、分组切换 7 条目（全部/本地/本地未分组/网络未分组/视频/音频/更新失败）✓、Compose 列表容器(recycler_view)挂载 ✓。⚠️ 列表 7 字段/播停切换/导出进度依赖书架有书数据，本次模拟器书架为空跳过字段行断言（表格校验脚本 verify_cache_explore_20260825.py --scene cache 已更新断言锚点为真实 content-desc）
- [x] 3.2a 真机回归——探索瀑布（部分）：三模式切换 prefs 写入+重启生效（封面模式页面呈现 ✓）。⚠️ 模拟器无发现源（"当前没有发现源！"），瀑布网格/滚动加载更多/点击进详情无法触发，需有发现源数据后再补；StaggeredGrid 类名在 uiautomator dump 中不出现（Compose 合并节点），脚本按文本量增量判定加载更多
- [ ] 3.2b 探索瀑布补充验证（待有发现源数据）：封面宽高比不塌陷（截图人工）、滚动到底加载更多去重、点击进详情、顶栏 overlay/padding 跟随主题
- [x] 3.3 残留检查：Grep `Log.d|Log.e` 0 残留；Grep `CacheAdapter` / `ExploreShowWaterfallAdapter` 无引用（2026-08-25 实施后已确认）
- [x] 3.4 编译（`assembleAppDebug` SUCCESS 2026-08-25 20:33）后清场：已验证无残留 gradle/java 构建进程（IDE 语言服务器除外），后续编译前必须先 Get-Process 校验
- [x] 3.5 `updateLog.md` 编译前同步（缓存页/探索瀑布两则条目）
- [x] 3.6 `docs/project-flow/ui-standards/migration-registry.md` 登记 7.11ai / 7.11aj
- [x] 3.7 `docs/INDEX.md` 登记本 spec（`list-residue-compose`）

## AOAdapt 日志

> 实施阶段记录：遇到问题按 `Action → Observation → Adapt` 追加，格式如下。

```
### YYYY-MM-DD HH:MM 记录标题
- Action: 本次采取的行动（改动/步骤）
- Observation: 观察到的结果/问题（错误码/异常/行为差异）
- Adapt: 据此调整的方案（后续步骤/修正确认）
```

- 待实施阶段追加。