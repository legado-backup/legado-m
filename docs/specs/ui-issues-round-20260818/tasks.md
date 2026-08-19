# tasks.md — UI 问题综合整改任务清单

> 本 spec 针对 2026-08-18 用户反馈的 9 大 UI 问题，按 P0（Bug 修复）→ P1（发现/订阅整改）→ P2（弹框与样式统一）→ P3（功能裁剪回溯与 Compose 化补全）四阶段整改，5. 阶段为验证与交付。当前状态：⏳ P0/P1 已完成（编译通过），执行 P2。涉及 `ui/main/`、`ui/explore/`、`ui/book/source/edit/`、`ui/widget/components/` 等目录；除阅读详情页外逐步收敛到 Compose 体系（对齐 ui-redesign-m3 规范）。

## 0. 准备
- [x] 0.1 通读四文档：`docs/specs/ui-issues-round-20260818/{spec.md,design.md,README.md}`（若已生成）+ `docs/specs/ui-redesign-m3/{ui-standards.md,implementation-spec.md,pages-inventory.md}`，确认 9 大问题根因与整改红线
- [x] 0.2 盘点 9 大问题代码锚点（MainActivity/BaseBookshelfFragment/BookshelfFragment1-2/ExploreFragment/BookSourceEditActivity/WelcomeScreen/BookInfoActivity/BaseActivity/AppConfig 等），确认 P0-P3 阶段划分与依赖顺序
- [x] 0.3 确认 git 基线：`git log` 定位 8 月 4 号前版本（问题 9 功能裁剪回溯的对比基线）+ 当前 updateLog 最新条目（问题 3/9 交付前需追加）

## 1. P0 Bug 修复
- [x] 1.1 **问题1（书架标签头部不按原标签展示）**：`BaseBookshelfFragment.configBookshelf()` 切换 `AppConfig.bookGroupStyle` 时 `notifyMain=true` 之外追加触发 fragment RECREATE（对齐 `MainActivity.getFragmentId` 按 `bookGroupStyle==1` 分发 style2/style1 的语义）；补齐 style1 头部固定 Tab（全部/本地）且位置对齐原版 Toolbar+TabLayout。涉及文件：`ui/main/MainActivity.kt`、`ui/main/bookshelf/BaseBookshelfFragment.kt`、`ui/main/bookshelf/style1/BookshelfFragment1.kt`、`ui/widget/components/`（BookshelfScreen 头部）。验收：切换「标签/文件夹」后书架立即重建且 style1 头部固定「全部/本地」Tab 位置与原版一致
- [x] 1.2 **问题8（长按书架书进详情 book is null）**：`BookshelfFragment1/2.onBookLongClick` 只 putExtra("name"/"author") → **仅补传 `bookUrl` extra**（保留 name/author 兼容），复用 `BookInfoViewModel.initData` 已有兜底链「getBook(name,author) → getBook(bookUrl) → getSearchBook(bookUrl)」（`BookInfoViewModel.kt:62-81` 已核实）。⚠️ 禁用 `startActivityForBook(book)`——该函数进**阅读页** ReadBookActivity，非详情页（见 design.md AD-02）。涉及文件：`ui/main/bookshelf/style1/BookshelfFragment1.kt`、`style2/BookshelfFragment2.kt`（BookInfoActivity.kt/BookInfoViewModel.kt 仅核对不改）。验收：长按任意书（含空名/重名）进详情不再报 book is null
- [x] 1.3 **问题2（沉浸式操作栏头部未联动）**：`PreferKey.immNavigationBar` 目前仅作用底部导航栏（`BaseActivity.setNavigationBarColorAuto`）→ 开启后联动头部状态栏/顶栏沉浸（复用 transparentStatusBar 方案）。涉及文件：`base/BaseActivity.kt`、`constant/PreferKey.kt`、`help/config/AppConfig.kt`、`ui/theme/ComposeActivitySupport.kt`。验收：开启沉浸式操作栏后底部导航栏与头部状态栏/顶栏同时沉浸

## 2. P1 发现订阅整改
- [x] 2.1 **问题5（发现/订阅头部与搜索框规则）**：发现/订阅默认展示「标签」且默认「按类型分组」——`sourceGroupStyle` 默认值 `0`（列表平铺）→ **`1`（按类型分组）**、`sourceGroupMode` 默认 `0`（标签），标签展示判定沿用现成 `isTagMode = sourceGroupStyle!=0 && sourceGroupMode==0`（`ExploreFragment.kt:148`）；`sourceGroupStyle==0`（用户主动选列表平铺）时不显示标签行、普通列表。分组/文件夹模式（`sourceGroupMode==1`）隐藏搜索框，进入文件夹（`isShowingFolder=false`）时显示搜索框且搜索范围限当前文件夹（`flowGroupSearchExact(currentGroup, searchKey)`/`flowByTypeSearch` 现成 DAO 分支）。⚠️ 注意：发现/订阅配置 key 是 `AppConfig.sourceGroupStyle/sourceGroupMode`，**不是** `bookGroupStyle`（后者是书架的）。涉及文件：`ui/main/explore/ExploreFragment.kt`、`ui/main/rss/RssFragment.kt`、`help/config/AppConfig.kt`（默认值 0→1）、`ui/widget/components/SettingsSearchBar.kt`。验收：默认标签+按类型与书架一致、分组模式无搜索框、进文件夹显示搜索框且结果限当前分组（✅ 编译通过，真机待 5.4）
- [x] 2.2 **问题6（去掉发现/订阅右上角分组弹框）**：移除 `ExploreFragment.buildMenuActions` 中 Groups header 与动态分组入口。涉及文件：`ui/main/explore/ExploreFragment.kt`。验收：右上角三点菜单不再出现分组弹框入口（✅ 已移除，菜单改含 文件夹配置/分组管理/批量改分组）
- [x] 2.3 **问题4（发现/订阅批量分组设置）**：发现/订阅右上角菜单新增「分组管理」入口（替换 P1-2 移除的动态分组列表位置）→ 分组 CRUD **复用已存在** `ui/book/source/manage/GroupManageDialog.kt`（书源）/`ui/rss/source/manage/GroupManageDialog.kt`（订阅源）；**批量改分组（多选源 → 移入/移出分组）已交付**（原"能力缺口"判断有误：管理页 `BookSourceViewModel`/`RssSourceViewModel` 已有同名批量方法，发现/订阅页用的 `ExploreViewModel`/`RssViewModel` 需各补一份——已新增；`BatchGroupDialog.kt` 方案 B 落地，全选/反选/移入/移出）。涉及文件：`ui/main/explore/ExploreFragment.kt`、`ui/main/rss/RssFragment.kt`、`ui/book/source/manage/GroupManageDialog.kt`（复用）、`ui/rss/source/manage/GroupManageDialog.kt`（复用）、新增 `ui/widget/BatchGroupDialog.kt`、`ExploreViewModel.kt`、`RssViewModel.kt`。验收：书源/订阅源可多选并批量归入/移出目标分组，分组变更后标签行/文件夹视图即时刷新（✅ 编译通过，真机待 5.4）
- [x] 2.4 回归验证：发现/订阅 Tab 切换、搜索（含文件夹内限定搜索）、分组移动、默认标签一致性，logcat 无异常。验收：上述场景全部通过且与原书架行为一致（编译级通过；真机 L2 待 5.4 统一验证）

## 3. P2 弹框与样式统一
- [ ] 3.1 **问题7（书源编辑页头部还原）**：`BookSourceEditActivity` 头部 FlowRow+Checkbox+DropdownMenu 还原贴近原版简洁样式（参考 `RssSourceEditActivity` 保留顶栏+原 XML 表单的做法）；订阅源编辑页保持现状不退化。涉及文件：`ui/book/source/edit/BookSourceEditActivity.kt`、`ui/rss/source/edit/RssSourceEditActivity.kt`。验收：书源编辑页头部观感与订阅源编辑页一致且贴近原版
- [ ] 3.2 **问题9（弹框三样式统一公共组件族）**：统一 `AppDropdownMenu`（右上角）/ `AppModalBottomSheet`（底部）/ Dialog 族（悬浮居中）三样式组件，梳理并登记到 `ui/widget/components/`，替换散落页面自建弹框。涉及文件：`ui/widget/components/AppDropdownMenu.kt`、`AppModalBottomSheet.kt`、各页面 Dialog 调用点、ui-standards §3 组件族。验收：全应用弹框仅三样式，无页面私有弹框
- [ ] 3.3 **问题9（组件风格统一）**：`SettingsToggleRow` 统一为 M3 Switch（含动画/颜色随主题），覆盖各页面 Toggle/Checkbox 混用；开关组件全部走统一封装。涉及文件：`ui/widget/components/SettingsToggleRow.kt`、各设置页。验收：开关组件样式全应用一致且跟随主题
- [ ] 3.4 回归验证：书源/订阅源编辑、设置页开关、弹框调用点逐一验证无布局错乱。验收：P2 改动无回归

## 4. P3 功能裁剪回溯与 Compose 化补全
- [ ] 4.1 **问题9（功能裁剪回溯清单）**：以 `897b42f95`（2026-08-02）为基线逐功能 diff。**设计阶段已完成调研**（`docs/temp-analysis/regression-diff.md`）：
  - [ ] 4.1.1 **恢复主题四态选择器（C1，高）**：`ThemeConfigFragment` 日/夜二态 → 四态 NameListPreference（跟随系统/日间/夜间/墨水屏），复用 `PreferKey.themeMode`/`AppContextWrapper` 现有逻辑（`AppConfig.kt:46,56` 已残留）。验收：墨水屏模式可从设置进入、`isEInkMode` 生效
  - [ ] 4.1.2 **恢复欢迎页 4 开关（C2，中）**：`WelcomeConfigScreen` 补 `welcomeShowText`/`welcomeShowTextDark`/`welcomeShowIcon`/`welcomeShowIconDark` 四个 `SettingsToggleRow`（日/夜两组），`WelcomeActivity.kt:92-105` 消费逻辑已存在。验收：日/夜模式文字/图标显隐可独立配置且生效
  - [ ] 4.1.3 **恢复书源排序「最近更新」（C3，中）**：`BookSourceScreen.kt:161-168` `ListSortOption` 补 `"6"`（`sortSources` 已有 `bookSourceSort==6 -> lastUpdateTime`）。验收：书源排序菜单含「最近更新」且生效
  - [ ] 4.1.4 **恢复桌面图标切换（C4，低）**：`ThemeConfigScreen` 补 `SettingsClickRow` 调用 `LauncherIconHelp.changeIcon()`（资源已就绪）。验收：可切换桌面图标
  - [ ] 4.1.5 **D1-D5 复核**：D1（书源管理文件夹视图 `isFolderViewMode` 硬编码 false）与问题4 批量分组设计冲突 → P1 一并决策；D3（style2 FastScroller）列为 Compose 增强；D2/D4/D5 暂不处理。输出 `regression-inventory.md` 三态清单（设计阶段已产出证据，实施阶段登记恢复回执）
- [ ] 4.2 **问题3（启动界面 + 我的页）**：
  - [ ] 4.2.1 欢迎页文字/图标显隐补齐（同 4.1.2）：`WelcomeConfigScreen` 补 4 开关 UI 入口；`WelcomeActivity` 桥接读取 `AppConfig.welcomeShowText/Dark`、`welcomeShowIcon/Dark` 传给 `WelcomeScreen`；`WelcomeScreen` 参数对齐日/夜独立语义。验收：欢迎页文字/图标显隐可配置且生效（与 8/2 基线一致）
  - [ ] 4.2.2 **我的页开关不生效修复（疑点1）**：`SettingsToggleRow.kt:33-39` 整行无 `clickable` → 加 `Modifier.clickable(enabled){ onCheckedChange(!checked) }`，整行 60dp 可切换。验收：我的页所有开关/单选行点击生效
  - [ ] 4.2.3 **sourceLayout 消费修复（疑点2）**：`BookSourceScreen.kt:377-382` 网格列数改读 `currentLayout`（`GridCells.Fixed(currentLayout)`）+ 菜单补 2-6 列细分；清理 `BookSourceActivity.kt:396-421` 对 `visibility=gone` recyclerView 的死接线。验收：书源管理页选网格列数与显示一致
  - [x] 4.2.4 我的页子页面 Compose 化补全：`OtherConfigFragment`→`OtherConfigScreen.kt`（✅ 已完成，2026-08-18）、`BackupConfigFragment`→`BackupConfigScreen.kt`（⏳ 待办，复用 SettingsCard/SettingsToggleRow/SettingsClickRow/SettingsSection，对齐 ThemeConfigScreen 范式）；主/子页面样式统一。验收：两个配置子页 Compose 化、功能点无丢失、样式统一
    - AOAdapt：Screen 初版缺失 7 个 extended 图标 import（Explore/RssFeed/FileDownload/AddAlert/FactCheck/BugReport/Update）+ `autoRefresh` key 误用 `"autoRefresh"`（PreferKey 实际为 `"auto_refresh"`）→ 已修复；Fragment 由 PreferenceFragment 改 Fragment+ComposeView，全部副作用（NumberPicker/文件选择/WebService 重启/recordLog/debugLogFloatingBall/processText）保留，`pref_config_other.xml` 确认无引用后删除
  - [ ] 4.2.5 发现/订阅内容区 Compose 化收尾：ExploreFragment/RssFragment 的 View `TabLayout` 替换为 Compose 标签行（P1 已含标签组件）；RecyclerView 列表主体维持（探索控件 JS 双求值链内核红线）。验收：发现/订阅头部全 Compose、列表功能不丢
- [ ] 4.3 **问题9（Compose 化收尾）**：
  - [ ] 4.3.1 新增公共组件 `GroupTabRow.kt`（对齐书架 `BookGroupTabs` 的 ScrollableTabRow+SecondaryIndicator，入参 groups/selectedIndex/onTabSelect）——发现/订阅共用。验收：组件在 ui/widget/components/ 存在 + 签名完整
  - [ ] 4.3.2 发现/订阅标签行替换（P3-3a）：ExploreFragment/RssFragment 删 View `tabLayout`（fragment_explore.xml:17-23 槽位），改用 Compose 标签行；状态 currentGroup/currentType 保持，回调复用 6 分支查询。验收：标签与书架视觉一致、无硬编码色
  - [ ] 4.3.3 **弹框冗余合并（疑点5）**：`ConfirmDialog↔AppConfirmDialog`、`AppSelectDialog↔SingleChoiceDialog` 两对合并（保留 ConfirmDialog/AppSelectDialog 为唯一实现），同步调用点。验收：无功能重叠冗余组件
  - [ ] 4.3.4 **Compose 私有弹框收敛（疑点5，8 文件）**：HttpDebugScreen/CurlTestScreen/AllBookmarkScreen/BookInfoEditScreen/BookSourceEditActivity/AutoTaskEditScreen 的私有 `DropdownMenu`/`AlertDialog` → 公共族（AppDropdownMenu/AppAlertDialog）。验收：grep 0 私有弹框残留
  - [ ] 4.3.5 配置子页 Compose 化（P3-3b）：`BackupConfigFragment`→`BackupConfigScreen.kt`、`OtherConfigFragment`→`OtherConfigScreen.kt`（复用 SettingsSection/Card/ClickRow/ToggleRow，对齐 ThemeConfigScreen 范式）。验收：两子页全 Compose、功能项不漏
  - [ ] 4.3.6 书源/订阅源管理壳交付（E3/E5）：列表 LazyColumn 收敛 + ListLayoutMenu/SwipeActionContainer/GroupHeader 复用。验收：书源/订阅源管理列表为 Compose、布局切换/排序正常
  - [ ] 4.3.7 P3 长尾页增量推进（compose-status-inventory §5 ②b 表排名 5-13）：搜索/全文搜索/目录/缓存/书架管理/替换规则/视频/音频/图片/RSS 文章列表——逐页 Compose 化并填 §3.3 实施回执。验收：每页功能点全过 + 回执
  - [ ] 4.3.8 全量巡检门禁（P3-3c）：grep 页面私有弹框/私有组件清零（对齐 AD-21）；除 N 类页（阅读详情/漫画/视频/订阅源编辑/WebView/代码编辑器/扫码/透明窗）外，本批次涉及页面均为 Compose。验收：巡检 0 私有重复、回执完成率 100%

## 5. 验证与交付
- [ ] 5.1 逐问题验收：9 大问题（问题1-9）按上列验收点逐项核对，回归书架/发现/订阅/编辑页/我的/启动/弹框全链路。验收：9 大问题全部闭环
- [ ] 5.2 编译门禁：`./gradlew assembleAppDebug` BUILD SUCCESSFUL（修改依赖/签名/strings 后 `--rerun-tasks`）。验收：编译零错误
- [ ] 5.3 updateLog 同步：基于 `git diff` 逐文件对照更新 `app/src/main/assets/updateLog.md`（编译前强制，面向用户语言）。验收：updateLog 覆盖本批次全部变更
- [ ] 5.4 真机验证：按 `ai_tests/docs/fixed_test_workflow.md` 用 `ai_tests\venv\Scripts\python.exe` 跑 L2 用例（快速验证用 `quick_build_install.py`），覆盖 P0-P2 核心交互；测试包 `io.legado.miss.app.debug`。验收：真机通过且 issues-found.md 记录问题
- [ ] 5.5 文档同步：docs/INDEX.md、tasks/、issues-found、ai_memory_main 更新；大型任务结束沉淀经验。验收：文档索引与现状一致

