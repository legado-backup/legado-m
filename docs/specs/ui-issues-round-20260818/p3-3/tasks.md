# tasks.md — P3-3 长尾页 Compose 化收尾（专项任务）

> 任务按「逐页回执」粒度拆解，每页完成必须在 design.md §7 回执表登记（缺失=未完成，门禁）。任务编号前缀 `P3-3#`。
>
> 完成级别约定（禁止混用）：**L1**=代码完成+编译；**L2**=功能可运行；**L3**=真实场景回测。代码改后必须再次核验确保改动正确无遗漏（用户基础规则）。

## 阶段 0 — 前置核实与准备

- [x] P3-3#0.1 **已核实**：`ReplaceRuleActivity` 顶栏/搜索经源码 Read（:117/:168/:175）确认已 Compose（`ReplaceRuleScreen.kt` 实为 `ReplaceRuleTopBar`，已接入 Activity），主体仍 View 内核（RecyclerView+拖拽+滑选）→ 顶栏免动、仅主体迁移（结论记入 design §1.1/§3.6/§6/§7）
- [x] P3-3#0.2 **已核实**：各候选页私有弹框清单确定——搜索/全文搜索/RSS搜索 `SearchScopeDialog`、RSS文章 `ReadRecordDialog`、目录 `TxtTocRuleDialog`/`TxtTocRuleEditDialog`/`ImportTxtTocRuleDialog`；订阅源管理多为公共 `alert{}`/`AlertDialog`（IO 库公共包装），私有 dialog 仅 `ImportRssSourceDialog`/`GroupManageDialog`/`CheckRssSourceConfig` + `SourceFolderAdapter.showConfigDialog`；公共弹框族 `ui/widget/components/`（AppDropdownMenu/AppModalBottomSheet/AppSelectDialog/AppEditDialog）确认存在（AD-P33-05 收敛目标确定）
- [x] P3-3#0.3 **已核实**：公共组件 EmptyStatePlaceholder/VerticalScrollbar/LazyListFastScroller/ListCard/SettingsCard 在 `ui/widget/components/` 下可用（与已交付 OtherConfig/BackupConfig 同源）
- [x] P3-3#0.4 编译基线确认：改动前先 `./gradlew assembleAppDebug` 确认基线可编译（防迁移过程混入预存问题）

## 阶段 1 — 搜索页（🥇 优先级最高）

- [x] P3-3#1.1 `SearchActivity` 内容区改 `binding.composeHost.setContent { SearchScreen(...) }`，壳保留 VM 获取与副作用（startActivityForBook/加入书架/Dialog 回调）
- [x] P3-3#1.2 新增 `SearchScreen.kt`：搜索结果 `LazyColumn`(key=bookUrl)（search 主体；历史/书架 chip 保留 View——见实施反哺）
- [x] P3-3#1.3 Item 复用公共组件（ListCard/TagChip/EmptyStatePlaceholder）；空态 EmptyStatePlaceholder；加载更多 LazyListState+derivedStateOf 触底
- [x] P3-3#1.4 `SearchScopeDialog` 弹框收敛【保持现状】：搜索范围选择本就走 AppDropdownMenu 菜单（隐藏一级）+ SearchScopeDialog（二级高级）；无高频输入性能问题（输入防抖已由顶栏 searchView 链式 Flow 承担）；`SearchScopeDialog` 保留（壳 handler onSearchScopeOk 沿用）
- [x] P3-3#1.5 点击项回调到壳现有 handler（showBookInfo）；长按/滑选多选：搜索主体原 SearchAdapter 本就无长按/滑选（仅点击），无迁移缺口；书架/历史 chip 的滑选/爆炸删除保留 View（AD-P33-04 独立任务）
- [x] P3-3#1.6 编译门禁（L1，BUILD SUCCESSFUL；L2 待真机验证：搜索→选书源→进详情全链路；历史删除/清空；≥200 项滚动流畅）
  - **实施反哺**：历史 `HistoryKeyAdapter`(Flexbox)+`BookAdapter`+`SearchScopeDialog` 保留 View/原实现——搜索主体 `LazyColumn` 化已完成，历史/书架 chip 列表为低风险轻量流派（且含长按 ExplosionField 爆炸删除动画，Compose 无等价），按 AD-P33-04 拆独立任务验证，不阻塞搜索主体迁移；差异已在 design.md §7 回执登记

## 阶段 2 — 全文搜索

- [x] P3-3#2.1 `SearchContentActivity` 内容区改 composeHost.setContent + 新增 `SearchContentScreen.kt`
- [x] P3-3#2.2 `SearchContentAdapter`+`SearchResult` → `LazyColumn`(key 由 index 承担；Item 复用 ListCard)
- [x] P3-3#2.3 点击跳阅读页定位 + 命中词高亮（getHtmlCompat 复用）+ 触底/首末条跳转（LazyListState+FastScroller）
- [x] P3-3#2.4 编译门禁已过（L1，BUILD SUCCESSFUL；L2 待真机验证）

## 阶段 3 — 目录页（三 Tab 列表，最复杂）

- [ ] P3-3#3.1 `ChapterListFragment` → `ChapterListScreen.kt`：`LazyColumn` 章节目录，高亮当前章/未读标识/点到跳章（TocActivityResult 沿用）
- [ ] P3-3#3.2 `BookmarkFragment` → `BookmarkScreen.kt`：书签 `LazyColumn` + 点击跳阅读 + 滑选多选删除
- [ ] P3-3#3.3 `HighlightFragment` → `HighlightScreen.kt`：高亮 `LazyColumn` + 点击跳阅读 + 滑选多选删除
- [ ] P3-3#3.4 `TxtTocRuleDialog`/`TxtTocRuleEditDialog`/`WaitDialog` 核对收敛（WaitDialog 公共保留）
- [ ] P3-3#3.5 三 LazyColumn 在 ViewPager2 内独立 ScrollState 状态保持验证
- [ ] P3-3#3.6 编译门禁 + L2 运行验证（目录快速跳章/书签高亮增删/当前章定位）

## 阶段 4 — 订阅源管理（风险最高，建议放靠后）

- [ ] P3-3#4.1 `RssSourceActivity` 多视图列表 Compose 化：`RssSourceManageScreen.kt` 按 `sourceLayout` 切换 `LazyVerticalGrid`↔`LazyColumn`（复用 ListLayoutMenu 公共组件）
- [ ] P3-3#4.2 Item 复用公共组件；`SelectActionBar` 批量启用/禁用/分组语义保留（View 组件或 Compose 底部栏，实施决策）
- [ ] P3-3#4.3 订阅源私有弹窗收敛：公共 `alert{}`/`AlertDialog` 已合格；私有 dialog（`ImportRssSourceDialog`/`GroupManageDialog`/`CheckRssSourceConfig`/`SourceFolderAdapter.showConfigDialog`）规范归属，无页面私有新增
- [ ] P3-3#4.4 **独立任务**：`DragSelectTouchHelper` 拖拽滑选迁移或 `AndroidView(RecyclerView)` 桥接（AD-P33-04，不阻塞本页验收）
- [ ] P3-3#4.5 编译门禁 + L2 运行验证（三视图切换/批量操作/分组管理）
- [ ] P3-3#4.6 L3 真实场景回测（大源数滚动+批量分组）

## 阶段 5 — RSS 文章列表（纯 View 最独立）

- [ ] P3-3#5.1 `RssArticlesFragment` 内容区改 composeHost.setContent + 新增 `RssArticleListScreen.kt`
- [ ] P3-3#5.2 `RssArticlesAdapter1-5` 五种样式 → `LazyColumn`/`LazyVerticalGrid` 按展示样式切换
- [ ] P3-3#5.3 `LoadMoreView` 预加载 → LazyListState 触底自动加载
- [ ] P3-3#5.4 `ReadRecordDialog` → Dialog 族核对
- [ ] P3-3#5.5 编译门禁 + L2 运行验证（分页/样式切换/点击读文/收藏删除）

## 阶段 6 — 替换规则（顶栏已 Compose，仅主体迁移）/ RSS 搜索

- [ ] P3-3#6.1 替换规则：新增 `ReplaceRuleListScreen.kt` 将主体 `RecyclerView` 列表迁为 `LazyColumn`（`ReplaceRuleViewModel` 沿用；点选/长按/过滤回调上抛到现有壳 handler）；顶栏 `ReplaceRuleTopBar`/`ReplaceRuleScreen.kt` **免动**（0.1 已核实）
- [ ] P3-3#6.2 替换规则手势独立任务：拖拽排序（ItemTouchHelper 语义）+ 滑选多选（DragSelectTouchHelper）保留 View 层或桥接（AD-P33-04），不阻塞 6.1 主体迁移
- [ ] P3-3#6.3 替换规则 L2 验证：主体 Compose 化后过滤条件（启用/停用/无分组/分组:xx）与实时搜索结果正常，导入/导出/扫码/删除/启用/停用/置顶不回归
- [ ] P3-3#6.4 `RssSearchActivity` 内容区改 composeHost.setContent + 新增 `RssSearchScreen.kt`：结果/历史 `LazyColumn`
- [ ] P3-3#6.5 `ChangeRssArticleSourceDialog`/`SearchScopeDialog` 收敛公共弹框族
- [ ] P3-3#6.6 编译门禁 + L2 运行验证（RSS 关键词搜索/历史/结果进详情）

## 阶段 7 — 收尾门禁

- [ ] P3-3#7.1 新增字符串全部进 `strings.xml`（无硬编码）；Grep `Color(0x..)`/私有弹框零残留
- [ ] P3-3#7.2 design.md §7 回执表逐页登记完成级别（缺失=未完成）
- [ ] P3-3#7.3 实施中与设计不符的决策反哺到 design.md（AD 或新增「实施反哺」段）
- [ ] P3-3#7.4 updateLog.md 基于真实 diff 更新；tasks/INDEX/ai_memory_main 状态同步