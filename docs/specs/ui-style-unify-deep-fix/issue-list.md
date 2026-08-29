# ui-style-unify-deep-fix 问题清单

> ## 🔴🆕 本文件包含 X XML 资产卫生批（2026-08-28 compose-migration-audit 审计新增，P3）
>
> **文末「X XML 资产卫生批」章节含 X1-X5 五条**（X1 删 47 孤儿 layout XML / X2 12 pref XML 收尾 / X3 存疑宿主确认 / X4 BookInfo View 版退役评估 / X5 权威源文档治理 8 项）。任务条目见 tasks.md **§2.6（2.6.1-2.6.6）+ 执行顺序表次序 4.6**。执行代理请勿跳过。

> 来源：3 个全盘排查子代理（2026-08-27）组件级盘点。三大问题域：H 头部 / D 弹框 / S 订阅切换。
> 每条含：源码定位 → 影响 → 修复方案 → 优先级。P0=高可见/用户点开即见/结构性；P1=中频；P2=低频/细节。
> ⚠️ 实施前必须逐条 Read 目标文件核实当前状态，禁止凭排查报告直接改（排查快照可能滞后）。

## 主题纳管判定标准（核心判据）

每个页面/组件/弹框的全部样式参数（背景/文字/按钮/圆角/字体/间距/状态色）是否都能被"主题设置/界面设置"统一管理：

- ✅ **已纳管** = 全部参数从主题体系读取 → 保留
- ⚠️ **部分纳管** = 仅部分参数随主题 → 补齐缺口
- ❌ **未纳管** = 硬编码/系统默认/不读主题 → 必须修复
- 仅三类可登记"主题体系外"且须说明由哪个设置项管理：语义色（Danger 红等）/ 媒体内容画布 / 阅读器正文可配置色（阅读设置管理面）
- **禁止以"豁免/合理存量"跳过未纳管项**（上轮 G6 对 38 旧弹框的"存量保留"判定错误，本次撤销）

## H 头部样式统一

### H6 [P0 用户实锤] 设置宿主页 ConfigActivity 头部背景黑色 + 三点菜单系统样式（✅ 已完成 2026-08-27，见 tasks 2.2.0；⚠️ 2026-08-28 补修"头部不占满"）
- **实施结果**（2026-08-27 14:03 实况核查）：ConfigTopBar 已带背景（读 TopBarConfig/壁纸/透明度）；三点菜单已改 AppDropdownMenu（渲染层对齐 ModernActionPopup 视觉）替代 MenuProvider 系统菜单；recreateOnThemeChange=false 按主题架构 v2 保留（ThemeSync 即时换肤）
- **2026-08-28 补修（用户复测实锤"主题设置头部不是占满头部"）**：`ConfigActivity.kt` ConfigTopBar modifier 顺序错误——`statusBarsPadding()` 位于 `background()` 之前，背景只画 56dp 内容区，**状态栏区域透明露出窗口底色**。已修正为 `clip→background→statusBarsPadding→height` 顺序（背景铺满含状态栏且被圆角裁切）。编译验证见 2.2.8
- **剩余**：真机视觉回归（归 R2）
- **用户实锤**（2026-08-27）："备份与恢复页面，头部现在设置主题顶栏颜色后一直是黑色，并且右上角三个点点看的弹框样式明显和主流右上角弹框样式不一致"；（2026-08-28 复测）"主题设置头部不是占满头部"
- **定位**：
  - 头部：`ui/config/ConfigActivity.kt` `ConfigTopBar`（Compose Row，**无 background**——只有 `statusBarsPadding().height(56.dp)`，背景透出窗口默认色/黑色）；`recreateOnThemeChange = false`（改色经 ThemeSync 换肤，但顶栏本身无背景色 → 顶栏颜色不随主题顶栏设置变化）
  - 菜单：`ConfigActivity` 用**隐藏 Toolbar + `setSupportActionBar(menuToolbar)` 承载 Fragment `MenuProvider` 系统菜单**（`ui/config/ConfigActivity.kt` L63-70/L133）；已核实仅 **2 个设置页**实现 MenuProvider 系统菜单——`BackupConfigFragment`（备份与恢复，L64/L133/L139）+ `ThemeConfigFragment`（主题设置，L27/L33/L132）；其余 ComposeSettingFragment 子页（AiConfig/OtherConfig/CoverConfig/WelcomeConfig/SubscriptionConfig/DiscoveryConfig/DiscoverySubscriptionConfig）**无菜单注册**，不受影响 → 右上角三点弹框为**系统 Toolbar 菜单样式**（用户实锤备份与恢复页）
- **影响**：①备份与恢复/主题设置等设置页头部顶栏颜色不随"主题设置→顶栏管理"变化（用户实测黑色）②右上角三点菜单与主流 ModernActionPopup 样式不一致（用户实测）
- **纳管状态**：ConfigTopBar = ❌ 头部背景未纳管（无 background）；菜单 = ❌ 系统样式未纳管
- **方案**：①ConfigTopBar 增背景（读 TopBarConfig/ThemeStore 背景色，随顶栏设置） ②设置页三点菜单从 MenuProvider 系统菜单改为 `ModernActionPopup`（对齐主流，参考 ThemeManageActivity 模式）——需改造 ConfigActivity 菜单承载方式 ③评估 recreateOnThemeChange=false 是否导致顶栏色不刷新
- **优先级**：P0（用户实锤、高可见）

### H8 [P0 用户实锤] AppDropdownMenu（M3 原生）菜单体系与主流 ModernActionPopup 不一致（最大覆盖面）（✅ 渲染层已完成 2026-08-27；⚠️ 实测使用 44 文件非 38；剩余头部接入 TopBarConfig 评估）
- **实施结果**（2026-08-27 14:03 实况核查）：AppDropdownMenu 渲染层已改自绘 `Surface(style.surface/panelRadius)`+点击行（对齐 ModernActionPopup 视觉），38 个既有调用点零改动达成；`components/ModernActionPopup.kt` 死代码已删；AllBookmarkScreen 裸 M3 已切 AppDropdownMenu
- **口径同步**：实测 `AppDropdownMenu` 使用 **44 文件**（原记 38 = 33 import + 5 同包；新增 ConfigActivity/BackupConfigFragment/ThemeConfigFragment/HttpDebugScreen 等调用点）——渲染层改动对新增调用点零影响
- **剩余**：替换净化页/字典页头部接入 TopBarConfig 评估（本条目头部说明）；真机视觉回归替换编辑/字典页三点菜单（归 R2）
- **用户实锤**（2026-08-27）："替换净化页面，头部颜色明显没有被纳管～但是右上角的三个点的弹框样式符合整体弹框样式，但是点进他的子页面替换规则编辑页面，右上角三个点弹框样式明显不符，字典规则页面，头部样式有问题，右上角三个点弹框样式明显不符"
- **定位**：`ui/widget/components/AppDropdownMenu.kt`（M3 原生 `DropdownMenu`/`DropdownMenuItem` + `MaterialTheme.colorScheme`）——**38 个文件**使用（33 import + 5 同包含 ImportSourceSheet）：ReplaceEditActivity（替换规则编辑页，用户实锤）、DictRuleScreen（字典规则页，用户实锤）、HighlightRuleScreen、TxtTocRuleScreen、AutoTaskScreen/Edit、DownloadManageScreen、FileManageScreen、StorageManageScreen、RecycleBinScreen、CacheActivity、WebViewActivity、CodeEditActivity、AudioPlayActivity、BookshelfManageActivity、SearchContentActivity、UrlRecordScreen、ReadRecordScreen、RssSourceEditActivity、RssSourceDebugActivity、RssSearchActivity、ReadRssActivity、RssSortActivity、RssFavoritesActivity、BookInfoActivity、BookInfoEditScreen、ImportBookScreen、ImageGalleryActivity、GroupManageComposeDialog、SourcePickerDialog、SourceLoginDialog、DirectLinkUploadConfig、VideoPlayerActivity、SettingsSelectableRow、MenuLayer（阅读器中屏）、GroupHeader、ImportSourceSheet；另 `AllBookmarkScreen` 裸用 M3 DropdownMenu（漏网）
- **主流参照**：`ui/widget/ModernActionPopup.kt`（自绘 Compose Surface 圆角卡片 + `rememberAppDialogStyle` + `LegadoMiuixChoiceRow`，全主题纳管）——23 个文件（主界面书架/订阅/发现/搜索/阅读器长按菜单均用此，用户认可的主流形态）
- **影响**：用户在主界面看到 ModernActionPopup（圆角卡片），进入所有 Compose 化次级页面（替换编辑/字典/高亮/TXT目录/自动任务/下载/文件/存储/回收站/缓存等）变成 M3 原生下拉菜单 → **视觉明显不符**。根因：上轮 G7 只清 PopupMenu→ModernActionPopup（View 体系），未覆盖 Compose 页面的 M3 DropdownMenu 体系
- **头部说明**（用户实锤同源）：替换净化页（ReplaceRuleActivity AppManagementScaffold）头部读 `AppConfig.immersiveManageBar` → primaryColor/backgroundColor（随主题主色，但**不读 TopBarConfig 顶栏管理**的标签色/壁纸），用户实测"头部颜色没被顶栏管理纳管"；字典规则页（DictRuleScreen GlassTopAppBar）头部读 primaryColor（随主题但同样不读 TopBarConfig 顶栏管理）
- **纳管状态**：AppDropdownMenu = ⚠️ 部分纳管（M3 colorScheme 随主题色但不随圆角倍率/弹框族规范，视觉非主流）；替换净化/字典头部 = ⚠️ 部分纳管（随主题主色但不随顶栏管理 TopBarConfig）
- **方案**（子代理推荐，最优）：①**菜单统一**：保留 AppDropdownMenu 的定位能力（锚点/弹出方位/点外关闭/滚动），仅把条目渲染层从 `DropdownMenuItem` 换成自绘 `Surface`（style.surface/stroke/panelRadius）+ `LegadoMiuixChoiceRow`，对齐 ModernActionPopup 视觉——`MenuAction` 数据驱动不变 → **38 个调用点零改动**；同步清理 0 调用的 `components/ModernActionPopup.kt`（命名混淆）+ `AllBookmarkScreen` 裸 M3 切到 AppDropdownMenu ②**头部**：评估替换净化/字典页头部接入 TopBarConfig（如管理页头部需随顶栏管理，参考 MainTopBarView 读法）
- **优先级**：P0（用户实锤 + 最大覆盖面 38 文件）


### H7 [P1] 其余可见系统菜单样式点（漫画阅读/发现经典）（✅ 已完成 2026-08-27，见 tasks 2.2.0b；死 menu XML 随 H17 清理）
- **定位**（深挖子代理 2026-08-27 补齐"系统菜单承载"维度）：真实可见系统菜单共 4 处——①ConfigActivity 宿主（H6，2 子页）②`ReadMangaActivity`（`view_manga_menu.xml:18` MangaMenu 内置 TitleBar attachToActivity=true，`menuInflater.inflate(book_manga)`，漫画菜单开合时右上角系统溢出可见）③`ExploreFragment` 经典模式（`fragment_explore.xml:12` attachToActivity=false + `setSupportToolbar(自身 TitleBar)` + `menuInflater.inflate(main_explore)`，经典模式可见）
- **影响**：漫画阅读菜单/发现页经典模式右上角弹框为系统样式，与 ModernActionPopup 不一致
- **纳管状态**：❌ 系统菜单样式（仅 tint 不换样式）
- **方案**：①ReadManga 漫画菜单 → ModernActionPopup ②ExploreFragment 经典模式菜单 → ModernActionPopup（现代/精选模式已 ModernActionPopup，经典模式对齐）③其余 7 处 menuInflater.inflate（book_source/rss_source/replace_rule/source_subscription/book_read_record/book_read/AiImageProviderManage）为 Compose 迁移后死代码（注入隐藏 Toolbar 用户不可见）→ 清理死代码（可选）
- **优先级**：P1（可见但非用户实锤）

### H9 [P0 用户实锤] 精准管理页背景色未纳管 + SettingsCard/SettingsClickRow 组件体系与主设置页分裂（✅ 根背景+组件取色已完成 2026-08-27，见 tasks 2.2.0d；回归归 R2）
- **实施结果**（2026-08-27 14:03 实况核查）：PreciseManageScreen L40 根背景 `.background(palette.page)` + divider `palette.divider`；SettingsCard/SettingsClickRow 取色已归位调色板（SettingsCard containerColor → Color(palette.row)、标题 → accent；SettingsClickRow 文字 → primaryText/secondaryText、图标 tint → secondaryText）
- **剩余**：5 文件 13 处使用点视觉回归（PreciseManage/AutoTaskEdit/BookInfoEdit/StorageManage/VideoSettingsPanel，归 R2）
- **用户实锤**（2026-08-27）："精准管理页面，主页面的样式，你不感觉和我的主页面样式不一致吗？"
- **定位**：
  - 页面根容器：`ui/config/PreciseManageScreen.kt` L40 `.background(MaterialTheme.colorScheme.surface)`——**M3 派生色**（surface = lerp(bg, neutral, 4%/10%)，见 `ui/widget/components/ThemeSpec.kt` L57），与主设置页标准 `palette.settings.page = Color(context.backgroundColor)`（ThemeStore 背景色直读）不一致 → 主题设置自定义背景色后页面背景偏色
  - 组件体系：该页用 `SettingsCard`（`ui/widget/components/SettingsCard.kt` L37 `containerColor = MaterialTheme.colorScheme.surfaceVariant`，M3 派生色）+ `SettingsClickRow`（`ui/widget/components/SettingsClickRow.kt` L57/L66/L77/L88 `onSurface/onSurfaceVariant`，M3 派生色），而主设置页（MySettingsScreen/SettingSpecScreen/ComposePreferenceScreen）用 `appSettingPanelBackground`/`appSettingRowDecoration`（AppSettingPalette 直读调色板色）——**两套组件体系并存**
- **同类组件使用点**（SettingsCard/SettingsClickRow 全量 5 文件 13 处）：SettingsCard 使用 3（`PreciseManageScreen` L43 / `AutoTaskEditScreen` L110 / `BookInfoEditScreen` L128）、SettingsClickRow 使用 10（`PreciseManageScreen` L44/54/64/74 ×4 / `StorageManageScreen` L149 ×1 / `VideoSettingsPanelContent` L240/246/261/267/285 ×5）——均为 M3 派生色，与主设置页调色板体系不一致
- **影响**：用户设置主题背景色/卡片色后，精准管理页背景与主设置页明显偏色（M3 surface 是 bg 向 neutral 偏移 4-10% 的派生色，非 bg 本身）；卡片/文字色同理
- **纳管状态**：PreciseManageScreen 根背景 = ❌ 未纳管（M3 surface 非 backgroundColor）；SettingsCard/SettingsClickRow = ⚠️ 部分纳管（M3 colorScheme 随主题但取色路径与调色板体系不一致）
- **方案**：①PreciseManageScreen L40 改 `.background(palette.settings.page)`（对齐主设置页，用 rememberAppSettingPalette）②SettingsCard/SettingsClickRow 内部取色改为 AppSettingPalette 调色板（containerColor → UiCorner.surfaceColor(themeUiPalette.cardColor)、文字 → palette.primaryText/secondaryText、标题 → palette.accent），消除两套体系 ③回归验证 5 文件 13 处全量使用点
- **优先级**：P0（用户实锤、高可见）
- **为什么上轮没发现（根因复盘）**：上轮 G1-G11 判据 C1-C6 只覆盖"硬编码色/硬编码圆角/硬编码字号/View直写色值/误用MaterialTheme/不订阅主题事件"——`MaterialTheme.colorScheme.surface` 表面看"用了 MaterialTheme = 随主题"被 C5 误判为已纳管，实际它是 **M3 派生色（lerp 偏移）非 backgroundColor 直读**；且 F-UI-THEME 用例集未覆盖精准管理页背景对比断言。判据漏洞：**误用 MaterialTheme 判定未区分"M3 派生色"与"主题背景色直读"**。

### H10 [P1] 列表项 M3 派生色归位（DictRule/Highlight/Download + ListCard 默认色，与直色体系分裂）（✅ 已完成 2026-08-27，见 tasks 2.4.1）
- **定位**（搜索子代理 + 主代理核验 2026-08-27）：
  - `ui/highlight/HighlightRuleScreen.kt` L217-237 `HighlightRuleItem`：`Surface(color = MaterialTheme.colorScheme.surface)` + 文字 `colorScheme.onSurface`（M3 派生色）
  - `ui/dict/rule/DictRuleScreen.kt` 列表项：同类 M3 surface/onSurface 取色
  - `ui/download/DownloadManageScreen.kt` L419 `ListCard` + `ui/widget/components/ListCard.kt` L41 默认 `containerColor = MaterialTheme.colorScheme.surface`（M3 派生色）
  - 对照：书源/订阅源/替换规则管理页列表项用 `AppManagementCard`（`palette.settings.row` 直色）——**同是列表项，两套色源**
- **影响**：字典规则/高亮规则/下载管理列表项底色与书源/订阅源管理列表项不同（M3 surface 派生色 vs 直色 palette.settings.row），同 App 内列表项底色来源分裂
- **纳管状态**：⚠️ 部分纳管（M3 colorScheme 随主题但取色路径与 AppManagementCard 直色不一致）
- **方案**：①HighlightRuleItem/DictRule 列表项 `colorScheme.surface` → `palette.settings.row`（AppSettingPalette 直色，对齐管理页列表项）；文字 `onSurface` → `palette.primaryText/secondaryText` ②ListCard 默认 containerColor 改调色板入参（调用方 DownloadManageScreen 传 palette 直色，或 ListCard 内部走 rememberAppSettingPalette）③回归对比书源管理列表项视觉一致
- **优先级**：P1（可见列表项、非用户实锤，但与 H9 同源同批治理）

### H11 [P0/P1 修正] 列表项卡片 M3 surface 归位（AutoTask/TxtTocRule/AllBookmark/Highlight/DictRule/RecycleBin，与 H10 同源）（✅ 6/6 完成 2026-08-28 收口；TxtTocRuleScreen:268 palette.row 源码亲核）
- **实施结果**（2026-08-27 14:03 实况核查）：AutoTaskScreen L283 ✅ / AllBookmarkScreen L146 ✅ / HighlightRuleScreen L218 ✅（Phase 1）/ DictRuleScreen L241 ✅（Phase 1）/ RecycleBinScreen L291 ✅ 全部归位 `palette.row`；**仅剩 TxtTocRuleScreen L253 列表项卡片 `colorScheme.surface` 待归位**（归 Phase 2 剩余实施）
- **定位修正**（主代理逐一 Read 根容器复核 2026-08-27）：原判"6 页**根容器** colorScheme.surface"**不实**——这 6 页根容器均为 `Column/Box(Modifier.fillMaxSize())` **无 background**（透宿主窗口背景，AutoTaskActivity XML 亦无背景），`MaterialTheme.colorScheme.surface` 实际出现在**列表项卡片 Surface**：
  - `ui/autoTask/AutoTaskScreen.kt` L283、`ui/dict/rule/DictRuleScreen.kt` L241、`ui/book/toc/rule/TxtTocRuleScreen.kt` L253、`ui/book/bookmark/AllBookmarkScreen.kt` L146(chip)、`ui/highlight/HighlightRuleScreen.kt` L218、`ui/source/recycle/RecycleBinScreen.kt` L291（均 `Surface(color = MaterialTheme.colorScheme.surface)` + shadowElevation 8.dp）
  - 真正 M3 surface **根背景**仅 1 页：`PreciseManageScreen` L40（H9）
  - 与 `ui-page-matrix.md` 统计（"colorScheme.surface 8 = Debug 7 + 角色 1"）存在原矛盾——矩阵口径正确，H11 初判系本任务交付物间未交叉校验所致
- **影响**：这 6 页**列表项卡片**底色与书源/订阅源管理页列表项（AppManagementCard 直色 palette.settings.row）不同源，同 App 内列表项底色分裂；页面根背景本身无 M3 surface，无需根背景修复
- **纳管状态**：⚠️ 部分纳管（列表项卡片 M3 派生色，H10 同源）
- **方案**：6 页列表项卡片 `Surface(color = MaterialTheme.colorScheme.surface)` → `palette.settings.row`（AppSettingPalette 直色，shadowElevation 保留）；文字 `onSurface` → `palette.primaryText/secondaryText`；与 H10（DictRule/Highlight/Download + ListCard）合并为"**列表项卡片取色同源**"全量治理
- **优先级**：P0（AutoTask/Highlight/DictRule/RecycleBin 高频列表页）；P1（TxtToc/AllBookmark 中频）

### H12 [P1] Debug 调试页 8 页 M3 TopAppBar 脱离主色体系（✅ 已完成 2026-08-27，见 tasks 2.2.0f；7/7 全归位）
- **定位**：`ui/debug/DebugToolsScreen.kt` L87 / `HttpDebugScreen.kt` L198 / `RegexTestScreen.kt` L293 / `PingTestScreen.kt` L73 / `TimestampConvertScreen.kt` L94 / `EncodeToolsScreen.kt` L61 / `CurlTestScreen.kt` L158 直接用 `TopAppBar(`（未走 GlassTopAppBar 封装），取色 `MaterialTheme.colorScheme.secondary/onSecondary`——**与主流 GlassTopAppBar(primaryColor 主色) 不同色源**；另 `MyFeatureBooksActivity.kt` L122 原生 M3；根背景走 `LegadoBackgroundBox` 默认 `colorScheme.background`（M3 派生，非 page 直色）
- **影响**：Debug 工具页顶栏用 secondary 色（非主色体系），与其他功能页顶栏主色不一致；根背景 M3 background 不随 ThemeStore 背景色
- **纳管状态**：⚠️ 部分纳管（DebugBaseActivity 独立承载；M3 colorScheme 随主题但脱离 primaryColor 主色 + 顶栏管理）
- **方案**：①Debug 8 页 `TopAppBar(` → `GlassTopAppBar`（primaryColor 主色，对齐所有功能页）②`LegadoBackgroundBox` 兜底色 `colorScheme.background` → `palette.settings.page`（或 context.backgroundColor）③MyFeatureBooks 原生 M3 → GlassTopAppBar（并入 H3/H5）
- **优先级**：P1（Debug 工具页低频，但顶栏主色不一致肉眼可见）

### H13 [P1 已决策] GlassTopAppBar 不消费顶栏管理 TopBarConfig（壁纸/圆角/透明度）（✅ 已完成 2026-08-27，见 tasks 2.2.0g）
- **实施结果**（2026-08-27 14:03 实况核查）：GlassTopAppBar 已接入 `TopBarConfig.currentConfig`——STYLE_REGULAR 顶栏包启用时消费壁纸/背景色/圆角/透明度（对齐 MainTopBarView renderBackgroundLayer），默认样式维持 colorPrimary
- **剩余**：真机重点回归订阅页/书架毛玻璃（归 R2/R3）
- **定位**：`ui/widget/components/GlassTopAppBar.kt` 取色链路仅 `containerColor ?: Color(context.primaryColor)` + barElevation——**不读 TopBarConfig**（壁纸/背景色/圆角/透明度）；对照 MainTopBarView 完整消费 TopBarConfig
- **影响**：用户设置"顶栏管理"壁纸/圆角后，GlassTopAppBar 页面（~40 个 Compose 功能页）不随顶栏管理变化，只随主色；与 MainTopBarView 页面（主界面/高阶管理页）行为不一致
- **纳管状态**：⚠️ 部分纳管（随主色但不随顶栏管理壁纸/圆角）
- **方案**（2026-08-27 **用户裁决：接入**，非评估/登记）：GlassTopAppBar 增加 `TopBarConfig.currentConfig` 消费（壁纸/背景色/圆角/透明度），与 MainTopBarView 对齐；接入后 ~40 个 Compose 功能页顶栏全部随顶栏管理；真机重点回归订阅页/书架（30% 透明度毛玻璃如受壁纸影响需登记例外）
- **优先级**：P1（已决策，归 Phase 2）

### H14 [P2] 角色系列 4 页底色硬编码黑白（page + card + cardAlt + stroke，不读主题背景色）（✅ 已完成 2026-08-27，见 tasks 2.2.0h）
- **实施结果**（2026-08-27 14:03 实况核查）：BookCharacterComposeScreens.kt L142 已改 `H14: page/card/cardAlt/stroke 归位调色板`（page → 调色板、card/cardAlt → UiCorner 卡面色、stroke → 分隔线），覆盖 Manage/Edit/Card/Relation 4 页
- **剩余**：真机视觉回归角色管理/编辑/关系页（归 R2）
- **定位**：`ui/book/character/compose/BookCharacterComposeScreens.kt` L142 `val page = ContextCompat.getColor(context, if (night) R.color.md_grey_900 else R.color.white)`——page 底色仅按日/夜模式二元切换（硬编码 md_grey_900/white），**不读 ThemeStore/主题设置背景色**；L143 `card = if (night) 0xff202329 else 0xfff7f8fb`、L144 `cardAlt`（blend）、L147 `stroke`（0x26ffffff/0x17000000）同为**硬编码十六进制**，均不读主题——四者一并治理，覆盖 BookCharacterManage/Edit/Card/Relation 4 页
- **影响**：用户自定义主题背景色/卡片色/阅读间距包等外观设置在这 4 页不生效（page/card 均固定日夜晚二元色）；与主设置页 backgroundColor 直读体系分裂
- **纳管状态**：❌ 未纳管（硬编码黑白 + 硬编码十六进制，仅 isNightTheme 切换）
- **方案**：page 底色 → `palette.settings.page` 直读；`card`/`cardAlt` → `UiCorner.surfaceColor(themeUiPalette.cardColor)`（或 palette.settings.row 同源）；`stroke` → `palette.divider`/border 直读；颜色源统一 AppSettingPalette（rememberCharacterStyle 改造），与 H9/H11 同类治理
- **优先级**：P2（角色功能页低频）
- **为什么上轮没发现**：Character 系列为独立自绘样式体系（rememberCharacterStyle），绕开了主调色板；本轮逐页 Read 矩阵才暴露（判据 C1-C6 均不覆盖该自绘体系）。

### 登记豁免（矩阵核实确认，不做改造）
- **AudioPlayActivity**（播放页）：`Theme.Dark` 固定 + recreateOnThemeChange=false（代码注释明确），沉浸封面播放页——登记豁免，归播放器红线（Out of Scope）
- **QrCodeFragment**（相机扫描）：纯相机画面无主题元素——豁免
- **ImageCropActivity**（裁剪页）：transparent + 固定黑状态栏——豁免（系统裁剪交互）
- **VideoFragment/VideoPlayerActivity 沉浸层**：播放器手势红线，不改造（G 系列已确认）
- **ReadRecordActivity(about)**：Compose 自绘壳层头部脱离 MainTopBar/Glass 体系——**并入 AD-08 Phase2 收敛**（不单独豁免）
- **BookSource/RssSource/ReplaceRule/RuleSub + AiImageProviderManage/LibraryContainerManage/ReadRecordFragment**：保留 `onCompatCreateOptionsMenu` 系统菜单残存（AppManagementScaffold/隐藏 Toolbar 下不可见）——并入 H7 ③死代码清理

### H1 [P2 修正] 管理页头部形态差异（MainTopBarView 56dp vs AppManagementTopBar 48dp）（✅ 已裁决登记 AD-01，不替换组件，2026-08-27）
- **定位**：`ThemeManageActivity`/`TopBarManageActivity`/`AppearanceKitActivity` 等用 `MainTopBarView(SUB)`（56dp，View 体系）；`BookSourceActivity`/`RssSourceActivity`/`ReplaceRuleActivity`/`RuleSubActivity`/`BookshelfTagManageScreen` 用 `AppManagementScaffold`（AppManagementTopBar 48dp，Compose 体系）
- **影响**：两套头部高度/字体/返回形态不同，用户切换管理页时视觉跳变
- **纳管状态**：**两者均已全量纳管** ✅——AppManagementTopBar 从 `AppSettingPalette`（AppDialogStyle/themeUiPalette/UiCorner）取色（page/row/primaryText/accent/danger/panelRadius/字体全读主题体系）；MainTopBarView 读 TopBarConfig + ThemeStore。差异仅为形态（高度/技术栈），非"未纳管"
- **方案**（AD-01 修正）：**不替换组件**（替换会破坏管理页搜索框/多选底栏 AppManagementScaffold 能力，且技术倒退）。调整为：①按页面类型归类确认——列表管理页（书源/订阅源/替换/规则/书架标签）统一 AppManagementScaffold 形态；设置管理页（主题/顶栏/外观）统一 MainTopBarView(SUB) 形态 ②若用户要求全 App 头部高度一致，则在设计评审确认后再评估统一到哪个基线（风险：破坏既有 Compose 管理页 UI）
- **优先级**：P2（已纳管，仅形态差异，视觉跳变非功能缺陷）

### H2 [P2 修正] ConfigActivity 自绘顶栏注释与实现不符（✅ 注释已修正 2026-08-27，见 tasks 2.2.2）
- **定位**：`ui/config/ConfigActivity.kt` ConfigTopBar（56dp Row 自绘，注释误写 GlassTopAppBar）
- **影响**：注释误导维护者（ConfigTopBar 文字/字体实际用 rememberAppSettingPalette 已随主题纳管；**但背景未纳管归 H6**，注释需一并澄清）
- **纳管状态**：⚠️ **文字/字体已纳管**（ConfigTopBar 用 `rememberAppSettingPalette()` 取色：primaryText/titleFontFamily/bodyFontFamily/56dp——读主题体系，随主题联动）；**背景未纳管**（无 background，见 H6）
- **方案**：①修正注释（ConfigTopBar → 标注"专有设置中心顶栏，读 AppSettingPalette"）②背景增色归 H6 处理，本条目仅注释
- **优先级**：P2（文字/字体已纳管，纯注释问题；背景已由 H6 P0 覆盖）

### H3 [P0 修正] Compose 自绘顶栏未纳管孤例（AiChat 硬编码黑背景）（✅ 已完成/豁免登记 2026-08-27，见 tasks 2.2.3/2.2.4/2.2.6：AiChat=scrim/onAccent 豁免、MyFeatureBooks→Glass、自绘顶栏→Glass 基线）
- **定位**：`AiChatScreen.kt` L851 `.background(Color.Black)` 硬编码页面背景 + L1886 `Color.White` tint；`MyFeatureBooksActivity`（原生 material3 `TopAppBarDefaults.topAppBarColors()` 默认色，未走项目主题）；`OpenUrlConfirmActivity`/`VerificationCodeActivity`（原生 androidx Toolbar）；`TocComposeScreen`(TocTopBar 带搜索+Tab)/`AiProviderManageActivity`(AiProviderTopBar)/`AiWorldBookManageScreen`(WorldBookTopBar)/`RelaySettingsActivity`(RelayTopBar)/`AiImageProviderManageScreen`(AiImageProviderTopBar)/`AiProviderEditActivity`(AppDialogTitleBar)
- **影响**：AiChat 黑背景/MyFeatureBooks 默认 M3 色完全不随主题（用户改主题看不到变化）；其余自绘顶栏部分随主题但形态各异
- **纳管状态**：AiChat = ❌ **未纳管**（Color.Black 硬编码）；MyFeatureBooks = ❌ **未纳管**（M3 默认色）；Toc/AiProvider/AiWorldBook/Relay/AiImageProvider = ⚠️ 部分纳管（自绘结构、视觉参数不统一）
- **方案**：①AiChat L851 硬编码 Color.Black → `context.backgroundColor`/ThemeStore 主题色；L1886 Color.White → 主题内容色 ②MyFeatureBooks → `GlassTopAppBar` 或对齐 Compose 头部规范（读 primaryColor/ThemeSync） ③OpenUrlConfirm/VerificationCode 原生 Toolbar → 项目头部组件 ④Toc 等自绘顶栏视觉参数对齐（高度/圆角/返回/字体 token）
- **优先级**：P0（AiChat/MyFeatureBooks 未纳管，用户改主题无效）

### H4 [P1] 旧 TitleBar 残留（✅ 4/4 已完成 2026-08-27，见 tasks 2.2.5）
- **定位**：`ReadRecordActivity`/`ReadRecordFragment`、`S3ContainerManageActivity`、`LibraryContainerManageActivity`、`AiImageProviderEditActivity`（均 activity_*_s3_container_manage / activity_read_record 等 TitleBar 布局）
- **影响**：旧 View 顶栏，与主流 MainTopBarView/GlassTopAppBar 风格不一致
- **纳管状态**：⚠️ 部分纳管（managed=true 时随顶栏管理，但默认 topBarColorManaged=false 需显式开启，且结构为旧 TitleBar）
- **方案**：按各页技术栈迁移 → MainTopBarView(SUB)（View 页）或 GlassTopAppBar（Compose 页）
- **优先级**：P1

### H5 [P2] 原生 M3 / 原生 Toolbar 孤例（并入 H3 处理）（✅ 已并入 H3 完成 2026-08-27：MyFeatureBooks→Glass；OpenUrlConfirm/VerificationCode 并入 D1 弹框迁移范畴）
- **定位**：`MyFeatureBooksActivity`（原生 material3 TopAppBar 未封装）、`OpenUrlConfirmActivity`/`VerificationCodeActivity` Dialog 用原生 androidx Toolbar
- **影响**：完全脱离项目头部体系，不随顶栏管理
- **纳管状态**：❌ 未纳管（原生 MaterialTheme / 原生 Toolbar，不读项目主题体系）
- **方案**：并入 H3 统一处理（MyFeatureBooks → 对齐 Compose 头部规范；OpenUrlConfirm/VerificationCode → 对齐项目弹框头部）
- **优先级**：P2（与 H3 合并）

### H15 [P1 用户实锤] 自绘头部未接入 TopBarConfig 族（H13 遗留面，AppManagementScaffold + 5 同类）（✅ 已完成 2026-08-28，见 tasks 2.2.0i：AppManagementTopBar 接入 + 5 处换 GlassTopAppBar，A 批编译门禁通过）
- **用户实锤**（2026-08-28）："替换净化页面头部底色"不随顶栏管理设置变化
- **主体定位**：`ui/widget/compose/AppManagementScaffold.kt:115-119`——`AppManagementTopBar` 头部底色只读 `AppConfig.immersiveManageBar` 开关（true→`backgroundColor`/false→`primaryColor`），**完全不消费 TopBarConfig**。H13 裁决只覆盖 GlassTopAppBar 系。
- **审查扩围（visual-audit-topbar-config.md）**：同类未接入自绘头部还有 5 处——`AiProviderTopBar`（AiProviderManageActivity.kt:225）/`AiImageProviderTopBar`（AiImageProviderManageScreen.kt:127）/`LibraryContainerTopBar`（LibraryContainerManageScreen.kt:117，⚠️硬编码中文）/`S3ContainerTopBar`（S3ContainerManageScreen.kt:115）/人物志头部（BookCharacterComposeScreens.kt:256-288，⚠️TextButton"返回"+硬编码中文）——54dp 系群组性离群（主流 56dp）。
- **影响面**：替换净化（用户实锤）/书源管理/订阅源管理/RuleSub/书架标签 + AiProvider/AiImageProvider/双容器管理/人物志 ≈ **11 页**
- **方案**：①AppManagementTopBar 接入 TopBarConfig（消费 resolveBackgroundColor/壁纸/cornerRadius，参照 ConfigTopBar/GlassTopAppBar；**前置裁决**：immersiveManageBar 与 TopBarConfig 优先级，建议顶栏管理配置优先、开关回落）②5 同类头部统一换 GlassTopAppBar ③顺带修硬编码中文 ④TocTopBar/AiChatTopBar 补豁免 KDoc（可追溯性）
- **优先级**：P1

### H16 [P1 用户实锤] AppDropdownMenu 与 ModernActionPopup 实现差异 6 项——"三点菜单不符"的感知主因（✅ 已完成 2026-08-28，见 tasks 2.2.0j：6 项对齐全落地，调用点零改动，A 批编译门禁通过）
- **用户实锤**（2026-08-28）："好多页面右上角三个点打开的弹框不符合 Archive 的主题规范"
- **定位**（visual-audit-menu-survey.md §四）：AppDropdownMenu 渲染层虽已对齐取色/圆角（H8，2026-08-27），但与 ModernActionPopup 存在 **6 项实现差异**：①海拔阴影（M3 默认投影 vs 显式 0dp）②边框（无 vs 条件 1dp panelBorderColor 描边）③字体（Text 未设 bodyFontFamily vs CompositionLocalProvider 强制）④条目组件（自绘 Surface+Row vs LegadoMiuixChoiceRow）⑤条目行高（44dp vs 42 可撑高）⑥宽度策略（自适应 vs 124-244dp 估算）
- **影响**：47 文件/59 调用点全部受影响——即使取色正确，阴影/描边/字体/条目形态的差异让用户感知"不符合规范"
- **方案**：AppDropdownMenu 对齐 ModernActionPopup 视觉语言（补 bodyFontFamily + 海拔/描边策略对齐 + 条目行组件对齐），保持 M3 DropdownMenu 定位能力与调用点签名零改动
- **优先级**：P1（47 文件覆盖面）

### H17 [P2] 菜单漏网点收敛（系统菜单/裸 M3 残留 4+1 处）+ 新死代码清理（✅ 已完成 2026-08-28，见 tasks 2.2.0k：漏网 4 处合规化 + ReadRecordFragment 死链清空语义归位 ReadRecordActivity.clearAll + 死 menu XML 38 个删除，A 批编译门禁通过）
- **定位**（visual-audit-menu-survey.md §二/三）：**漏网活跃**：①`CurlTestScreen.kt:386-417` 裸 M3 DropdownMenu 三点 ②`ReplaceRuleActivity.kt:307-310` onCompatCreateOptionsMenu inflate replace_rule（TitleBar 未 GONE，系统样式菜单——⚠️本页主体已 Compose，菜单为遗漏残留）③`ExploreFragment.kt:341-350` 经典模式 main_explore（条件可达；⚠️二次亲核：menu_group 分组项已走 ModernActionPopup :3609→:3623，仅其余菜单项系统样式）④`LibraryContainerManageActivity.kt:106-109` menu.add 导入/导出 ⑤`ReadRecordFragment.kt:316-324` 存疑（需真机确认 TitleBar 可见性）。**新死代码 5**：RuleSubActivity:55/BookSourceActivity:314/RssSourceActivity:210/ReadMangaActivity:520/AiImageProviderManageActivity:125（均 titleBar GONE 后 inflate 仍执行）+ VideoFragment:15 死 import + 约 31 个死 menu XML
- **方案**：①-④漏网点 → AppDropdownMenu（Compose）或 ModernActionPopup（View），⑤真机核实后处置；死代码删除随 D 批/H7 收尾统一
- **优先级**：P2（Curl 为调试页低频；替换规则页菜单用户可达）

## D 弹框样式统一

### D1 [P0/P1] BaseDialogFragment 旧 View 弹框 36 个 + BasePrefDialogFragment 2 个（仅背景色联动）
- **定位**（2026-08-27 弹框家族子代理逐文件核实，实测 36 个）：
  - read/config：`SpeakEngineDialog`/`HttpTtsEditDialog`/`BgTextConfigDialog`/`SpeakerGroupManageDialog`/`ReadAloudDialog`
  - read：`ContentEditDialog`/`EffectiveReplacesDialog`/`ReadSelectionImageDialog`/`SelectionSearchEngineManageDialog`
  - book：`ChangeBookSourceDialog`/`ChangeChapterSourceDialog`(changesource)、`ChangeCoverDialog`(changecover)、`CacheChapterDialog`(cache)、`TxtTocRuleDialog`/`TxtTocRuleEditDialog`(toc/rule)、`SourcePickerDialog`(manage)、`ServersDialog`(import/remote)
  - association：`AddToBookshelfDialog`/`OpenUrlConfirmDialog`/`VerificationCodeDialog`
  - about：`AppLogDialog`/`CrashLogsDialog`｜file：`FilePickerDialog`｜font：`FontSelectDialog`｜login：`SourceLoginDialog`
  - rss：`ChangeRssArticleSourceDialog`(search)、`RssFavoritesDialog`(favorites)、`ReadRecordDialog`(article)
  - dict：`DictDialog`｜widget/dialog：`VariableDialog`/`PhotoDialog`/`CodeDialog`
  - code/config：`ChangeThemeDialog`/`SettingsDialog`｜video/config：`SettingsDialog`｜main/ai：`AiImagePreviewDialog`
- **主代理复核补漏（2026-08-27）**：①`lib/prefs/IconListPreference.IconDialog`（R.layout.dialog_recycler_view）、`ui/widget/keyboard/KeyboardAssistsConfig`（同 layout）为子代理名单**遗漏**的 BaseDialogFragment 子类 → 一并入队列 ②`CacheChapterDialog`/`SettingsDialog`(code/config)/`SettingsDialog`(video/config) 为**多行继承**（`class X :` 换行 `BaseDialogFragment(...)`），单行 grep 易漏 → 实施前以 grep `BaseDialogFragment(`（含跨行）+ 逐文件 Read 核对全量名单为准
- **延伸预判**：`ReadAloudConfigDialog`/`MoreConfigDialog`（继承 `BasePrefDialogFragment`，无附加色仅墨水屏透明处理）→ 一并入队列评估
- **影响**：与主流 Compose 弹框视觉割裂，仅背景色随主题，按钮/列表/输入框/文字色固定硬编码
- **纳管状态**：⚠️ 部分纳管（仅 `setBackgroundColor(ThemeStore.backgroundColor())` 联动背景；控件样式不随主题设置）→ **撤销上轮 G6"已主题化存量保留"判定**
- **方案**（AD-02）：全部迁移 `ComposeDialogFragment` + `AppDialogFrame`（全纳管）。P0=高频可见（ContentEdit/ChangeBookSource/ChangeChapterSource/Dict/SourcePicker/Servers 等）先行；P1=其余分批；WaitDialog/PhotoDialog/CodeDialog 特殊场景（多页复用的纯展示型）可先登记"过渡期保留"但**必须纳入迁移队列**，不得永久豁免
- **优先级**：P0（P0 子集）→ P1（其余）

### D2 [P0] 系统 AlertDialog（alert{} DSL 71 文件 162 处 + 内联 9 处）
- **定位**：`lib/dialogs/AndroidAlertBuilder.kt`（`alert{}` DSL，71 文件 162 处调用，重点：AndroidDialogs.kt 定义 18 / VideoPlayer / ReadBookActivity 6 / CacheActivity 6 / AutoTaskActivity / SearchActivity / ReadMenu / MainActivity / BookInfoActivity / Chapter 族 / BookSourceEditActivity 等；**主代理复核 2026-08-27：`import lib.dialogs.alert` = 76 文件，差 5 系 import 未直接调用，实施前 grep 复核**）；内联 `AlertDialog.Builder`（ReadBookActivity:3680/HighlightRuleActivity×3/ExploreFragment:2159/ReadAiFloatingPanel:570/ReadRecordComponentConfigDialog:87/ReadRecordWidgetUi:192/273/AdvancedTitleConfigDialog:325）
- **影响**：系统原生样式，完全不随主题设置
- **纳管状态**：❌ 未纳管（系统 AlertDialog 默认样式，不读项目主题体系）
- **方案**（AD-02）：高频确认/单选/多选/输入 → ComposeConfirmDialog/ComposeSingleChoiceDialog/ComposeMultiChoiceDialog/ComposeTextInputDialog（已具备，见 AppComposeDialogs.kt）；P0 优先迁移用户可见高频点
- **优先级**：P0（高频）→ P1（其余）

### D3 [P1] Import 系列 + M3 @Composable 弹框对齐 AppDialogFrame
- **定位**：Import 系列 7 个（`ImportBookSourceDialog`/`ImportDictRuleDialog`/`ImportReplaceRuleDialog`/`ImportRssSourceDialog`/`ImportTxtTocRuleDialog`/`ImportHttpTtsDialog`/`ImportThemeDialog`）已全部 ComposeDialogFragment 化 + `ImportSourceSheet.kt`；另核实 **M3 @Composable 弹框组件 5 个**（`AppConfirmDialog`/`AppEditDialog`/`AppTextDialog`/`SingleChoiceDialog`/`ConfirmDialog`，material3 默认 Surface，无透明度/面板背景图）
- **影响**：随主题但卡片/按钮/间距与主流 AppDialogFrame 不一致
- **纳管状态**：✅ 已纳管（LegadoTheme 包裹随主题）但**风格非 AppDialogFrame** → 视觉对齐
- **方案**：ImportSourceSheet 内部改 AppDialogStyle（Miuix 卡片 + ThemeStore 取色）；M3 5 组件渲染对齐 AppDialogFrame（补面板背景图/圆角倍率/透明度支持）
- **优先级**：P1

### D4 [P2] 散点弹框（实测 13 个）
- **定位**：`WaitDialog`/`UrlOptionDialog`（raw Dialog）、`NumberPickerDialog`（AlertDialog.Builder+着色）、`AdvancedTitleConfigDialog`（DialogFragment+ViewBinding）、`SelectionWebSearchDialog`/`BottomWebViewDialog`/`HighlightStyleDialog`（BottomSheetDialogFragment）、`PageKeyDialog`（ComponentDialog）、`ChoiceEpisodeDialog`/`ChoiceSpeedDialog`（raw Dialog）、`ReadRecordComponentConfigDialog`（AlertDialog+ComposeView AppDialogFrame）、`PackageSyncTaskDialog`（AndroidAlertBuilder 定制）+ 边界 `SourceSelectDialog`（ComponentDialog+ComposeView）
- **影响**：零散不统一
- **纳管状态**：⚠️ 部分纳管（WaitDialog/UrlOptionDialog ViewBinding 直写色；AdvancedTitleConfigDialog applyUi*；NumberPickerDialog applyTint；SelectionWebSearch/BottomWebView WebView 场景）
- **方案**：优先迁移纯展示型（WaitDialog/UrlOptionDialog/NumberPickerDialog/PageKeyDialog）→ ComposeDialogFragment；WebView 承载类（SelectionWebSearch/BottomWebView）登记"过渡期保留"但补主题取色；HighlightStyle/AdvancedTitleConfig/ChoiceEpisode/ChoiceSpeed 按场景评估或登记
- **优先级**：P2

## S 订阅页经典/新版切换结构修复

### S1 [P0] updateRssSourceNameWidth layout 监听跨模式残留
- **定位**：`RssFragment.kt` L419/L420（modern 注册 addOnLayoutChangeListener）+ L493-505（函数体无 usingModernRss guard）
- **影响**：切回 classic 后标题宽度仍被钳制 96~190dp，截断经典形态标题
- **方案**：函数体加 `if (!usingModernRss) return`；classic 模式移除 layout 监听（save/remove 配对）
- **优先级**：P0

### S2 [P0] 切换依赖 onResume 兜底，不监听事件
- **定位**：`RssFragment.kt` L311-315（onResume 比对）vs MainActivity L2326（NOTIFY_MAIN 仅刷新外观）
- **影响**：设置页改模式后若 fragment 未重新 onResume，切换不生效
- **方案**：RssFragment 增 `observeEvent(EventBus.NOTIFY_MAIN)` 监听，收到后比对 modernRssPage 触发 applyRssMode；onResume 保留为兜底
- **优先级**：P0

### S3 [P0] classic 运行时状态未重置
- **定位**：`RssFragment.kt` L368（仅重置 isShowingFolder）vs L237/L240/L250（currentGroup/currentType/selectedRssTag）
- **影响**：切回经典后可能按残留分组/类型筛选显示
- **方案**：新增 `resetRssModeState()`，applyRssMode 时重置 currentGroup/currentType/selectedRssTag/currentSorts
- **优先级**：P0

### S4 [P1] rssTopOverlaySpace/rssTopOverlayEnabled 跨模式旧值
- **定位**：`RssFragment.kt` L687-691（renderCurrentSort runOnCommit 先消费旧值）
- **影响**：overlay 时序风险（随后被 updateModernRssTopBarOverlay 校正，轻微）
- **方案**：resetRssModeState 中清空 overlay 状态
- **优先级**：P1

### S5 [P2] classicHeaderReady 一次性标记永久驻留
- **定位**：`RssFragment.kt` L166/L941-952（header 永久挂在 adapter）
- **影响**：状态永久驻留（modern 下 recyclerView gone 无害）
- **方案**：改为 per-mode 判定，classic 模式才挂 header
- **优先级**：P2

### S6 [P1] sortHostViewModel 跨模式保留旧源
- **定位**：`RssFragment.kt` L606-609（presentSource 时重置 url/source）
- **影响**：切回 modern 前一刻状态残留
- **方案**：applyRssMode 时 reset sortHostViewModel 相关状态
- **优先级**：P1

## T 主题体系架构偏差（2026-08-28 深度分析新增，Archive 三大主题体系 vs OURS）

> 来源①：Archive 参考快照主题体系深度分析（底稿 `docs/temp-analysis/theme-arch-1-mode.md`/-2-theme/-3-setting + 偏差矩阵 `theme-arch-gap-matrix.md`；架构规范 `ui-standards/theme-architecture.md`）。
> 来源②（T7-T12）：OURS 进化增量审计（底稿 `theme-evolution-audit-mechanism.md` + `theme-evolution-audit-data.md`）——以 Archive 体系标准审计 v2 进化（ThemeSync/豁免机制/wrap/外观套件）的实现质量；四道核心红线（单点写入/工厂键/令牌双事件/预览同源）零新增违规，缺陷集中在豁免机制落地落差与事件双消费。
> 判定口径：确认缺陷 / 需补兜底 者入本批次；有意改造（ThemeSync v2/recreateOnThemeChange 豁免机制本身/AppContextWrapper 翻转/AppearanceKit 编排层）**保留，禁止回退对齐 Archive**；本批次修的是进化的**实现落差**（如豁免宣称未实现、事件双消费），非推翻进化。

### T1 [P1 确认缺陷✅复核维持] 跟随系统模式链路缺 NIGHT_MASK 过滤 + 防抖，自动路径不套 AppearanceKit
- **定位**：`App.kt:221-228`——`newConfig.diff(oldConfig) and CONFIG_UI_MODE` 全位 diff 直触 `applyDayNight`。Archive 参照 `archive-ref .../App.kt:157-179`：①`UI_MODE_NIGHT_MASK` 掩码只比夜间位（原注释："只处理真正的亮暗切换，忽略车载/底座等 uiMode 类型变化，避免无谓重建"）②`themeMode=="0"` 前置检查 ③generation+Job cancel+Mutex 三重防抖 ④AppearanceKit.applyCurrentModeTheme 先行套用。
- **复核（2026-08-28 主代理亲核源码）**：OURS `applyDayNight`（ThemeConfig.kt:106-113）无幂等短路（全量 applyTheme+initNightMode+双事件广播）→ 车载/底座/电视等 type 位变化会误触发全局 recreate；快速亮暗切换无防抖 → recreate 风暴。NIGHT_MASK 过滤是 Archive 体系组成防御（非可选优化），对齐=体系内进化。
- **影响**：①车载/底座 uiMode 变化误触发全部 Activity recreate（状态丢失+瞬时卡顿）②系统定时亮暗+频繁手切场景连续重建。
- **方案**：对齐 Archive 四件套（NIGHT_MASK 掩码 + themeMode=="0" 前置 + 防抖协程 + AppearanceKit 套用）。改动前必读 `theme-architecture.md` 红线 7。
- **优先级**：P1（维持）

### T2 [P2 需补兜底（复核降级 P1→P2）] upBackgroundImage 缺回落四件套（仅豁免页/同实例场景残留）
- **定位**：`BaseActivity.kt:204-216`（OURS）。Archive 参照 `BaseActivity:235-259+` 四件套：①`!imageBg || isEInkMode` → 回落窗口背景色 ②`hasBgImage` 预检 + drawable null → 回落 ③OOME/Exception → 回落 ④`applyRootBackgroundPolicy`（imageBg 且非 E-Ink 时清 root 背景）。OURS 实况：imageBg=false 不进 if（不清旧图不回落）、null 不动作、异常仅记日志无回落、无 E-Ink 分支（`AppConfig.isEInkMode` 全仓可用但此处未用）、无清 root。
- **复核（2026-08-28）**：非豁免页随 RECREATE recreate 自愈（新实例 initTheme 重设背景 tint），残留仅发生在**豁免页（ConfigActivity 等 3 页）同实例内改背景图设置**场景——而改背景图设置恰在豁免宿主页内，场景真实但影响中低（切走再回即自愈）。
- **影响**：豁免页上关闭背景图/换图失败后页面残留旧图；E-Ink 设备背景图未跳过。
- **方案**：对齐 Archive 四件套（回落窗口背景色 + E-Ink 分支 + 清 root policy）。
- **优先级**：P2（复核降级：影响面收窄至豁免页场景）

### T3 [P3 ✅核实完成→建议关闭] AudioPlayActivity 豁免 recreate 的 View 侧刷新核实
- **定位**：`AudioPlayActivity:92-93` 注释明确 v2 设计意图："沉浸播放页不随主题事件重建（避免打断播放），**Compose 侧经 ThemeSync 刷新**"——豁免本身是有意进化（保留），非缺陷。
- **全量亲核（2026-08-28 二次亲核）**：该页全文 **无 View 侧主题色消费**（backgroundColor/primaryColor/setBackgroundColor/upBackgroundImage 均 0 命中），顶栏为 Compose（:148 composeTopBar.setContent）→ v2 豁免+ThemeSync 已完整覆盖，**无需补兜底**。
- **处置**：关闭条目；在 AudioPlayActivity:92 注释处追加一行"经核实无 View 侧主题色消费，豁免+ThemeSync 覆盖完整（2026-08-28 审查）"固化结论，防后续审计重复排查。
- **优先级**：P3（仅注释动作）

### T4 [P2 定性修正：漏改上游进化，应对齐] initTheme Auto 分支仍用上游旧写法 isColorLight，Archive 已进化 isNightTheme
- **定位**：`BaseActivity.kt:194-198`（OURS）——`ColorUtils.isColorLight(primaryColor)` 决定 Light/Dark style。Archive `BaseActivity:208-215` 用 `AppConfig.isNightTheme`。
- **复核（2026-08-28 主代理亲核）**：isColorLight 是上游 gedoor/legado 原版写法，Archive 在其体系内已进化为模式判定（保证 style 与页面实际模式一致）；OURS 停留在旧写法=**漏跟 Archive 进化**，非 OURS 有意改造。按"以 Archive 体系为基、进化修改"方针应直接对齐。
- **影响**：深主色+日间模式下弹窗/菜单 style 与页面模式相反（色调漂移）。
- **方案**：`initTheme` else 分支改 `AppConfig.isNightTheme` 判定（对齐 Archive）；编译+深主色日间场景真机确认。
- **优先级**：P2

### T5 [P2 功能回退] 高刷管理缺失（Archive 有 OURS 无）
- **定位**：全仓 0 命中（Archive `BaseActivity:283-327` 有帧率管理）。
- **影响**：高刷设备上未按 Archive 策略管理刷新率（功耗/流畅度策略缺失），非视觉缺陷。
- **方案**：评估从 Archive 搬入高刷管理（ independence 低，可独立小任务）；或登记不搬（若产品决策不需要）。
- **处置（2026-08-28 T 批核实）**：定性=产品决策型非缺陷，维持登记不搬；是否引入高刷管理待用户产品决策（若决策引入，作为独立小任务从 Archive 搬入 BaseActivity 帧率管理）。
- **优先级**：P2

### T6 [P3 卫生] MAIN_THEME_BACKGROUND_CHANGED 死事件清理
- **定位**：全仓 4 发送 0 订阅（theme-arch-gap-matrix.md R5）。
- **影响**：无功能影响；误导后续 AI 以为存在背景图单独刷新通道（架构认知污染）。
- **方案**：删除 4 处发送点（或留一处注释说明由 RECREATE+ThemeSync 取代的历史），同步 `theme-architecture.md` 红线 3 措辞。
- **优先级**：P3（卫生级）

### T7 [P2 进化缺陷] 阅读器未豁免 recreate：注释宣称豁免但实现缺失，与 Archive 原位刷新双轨叠加
- **定位**：`BaseActivity.kt:55-57` 注释宣称"阅读器覆写 recreateOnThemeChange=false"，实际 `BaseReadBookActivity`/`ReadBookActivity` **均未覆写** → 阅读中切主题/日夜整页 recreate。Archive 标准：阅读器 `onNightThemeChanged` 原位刷新（不打断阅读）。
- **来源**：进化增量审计（theme-evolution-audit-mechanism.md M2）——v2 豁免机制设计意图与实现落差。
- **影响**：阅读中改主题色/切日夜 → 阅读页整体重建（闪黑+阅读位置 UI 重建），偏离 Archive"原位刷新"标准。
- **方案**：①ReadBookActivity 覆写 `recreateOnThemeChange=false` 并实现原位刷新（订阅 ThemeSync 重刷阅读配置/背景，参照 ConfigActivity/VideoPlayerActivity 豁免兜底模式）②对齐 BaseActivity:55-57 注释与实现一致。
- **⚠️ 施工陷阱（visual-audit-event-consistency.md 核实）**：read 包 ThemeSync/setupSystemBar/upBackgroundImage 引用 **0 命中**——若只按注释补 `override=false` 而不补兜底，将直接致**阅读器主题不刷新**（比现状更糟）。兜底与覆写必须同一提交落地。
- **⚠️⚠️ 实施新发现的双重穿透（2026-08-28 真机铁证）**：覆写+原位刷新落地后，真机菜单实验（阅读菜单开启态 `cmd uimode night no`）实锤菜单被强制关闭=Activity 仍被重建，**两个独立穿透源**：①系统 uimode config change 标准重建（ReadBookActivity/AudioPlayActivity/ConfigActivity 的 manifest configChanges 均无 `uiMode`，VideoPlayerActivity 有故豁免一直有效）②AppCompatDelegate.setDefaultNightMode 变化时对所有 Activity 的自动 recreate。**修复**：①三页 manifest 补 `uiMode`（对齐 VideoPlayerActivity 基线）②BaseActivity.initTheme（super.onCreate 前）对豁免页 `delegate.setLocalNightMode` 锁定当前生效值（阻断 delegate 自动 recreate；锁定值随新实例 onCreate 重读）。**复测铁证：菜单保持打开=IN_PLACE_REFRESH，且阅读区背景随日夜间正确切换（黑↔护眼绿），0 崩溃**。
- **优先级**：P2（切主题场景触发，阅读为最高频场景建议靠前）✅ 2026-08-28 完成并真机验证

### T8 [P2 进化缺陷] RECREATE 自订阅残留与基类统一消费叠加 → 双 recreate（3 处，审查扩围）
- **定位**：①`MainActivity.kt:2320-2323` 遗留自订阅（refreshMainThemeBackground+recreate）+ 基类 recreate → 双重建 ②`NavigationBarManageActivity.kt:234-236` 自订阅 loadPackages()（基类 recreate 令其结果作废，冗余 IO）③`TopBarManageActivity.kt:130-132` 同类。v2 将 RECREATE 消费上移 BaseActivity 时未清理各页旧订阅。
- **来源**：进化增量审计 + visual-audit-event-consistency.md 任务1（合法保留：VideoPlayerActivity 自订阅仅刷色非 recreate、DebugBaseActivity 独立继承链）。
- **影响**：①主页面每次主题变更重建两次（闪两次+性能）②②③冗余消费/重建后动作作废。
- **方案**：删除三处自订阅（依赖基类统一消费；MainActivity 背景刷新并入基类豁免分支或 onCreate），全仓 Grep 确认无其他残留。
- **优先级**：P2

### T9 [P3 已知权衡登记] 套件投影补发第二次 RECREATE（偏离双事件原子收尾）
- **定位**：`AppConfig.kt:114-119`——外观套件异步投影完成后补发第二次 RECREATE（注释明示为补偿，确保套件投影套用）。Archive 标准：双事件原子收尾单次。
- **影响**：手动切日夜时页面 recreate 两次（视觉闪两次）。
- **方案**：登记为已知权衡（补偿性设计，注释已固化）；若优化需将投影套用并入 applyDayNight 主链单次收尾，实施前验证套件投影时序。
- **优先级**：P3

### T10 [P3 进化缺陷，✅二次亲核修正机制：随 T2 一并修复] 豁免页无背景图时窗口底色残留
- **定位**：豁免分支（BaseActivity.kt:108-115）已调用 `setupSystemBar()+upBackgroundImage()`；但 OURS `upBackgroundImage`（:204-216）在 `imageBg=false`/加载失败时 early-return **不恢复窗口底色**（initTheme 的 applyBackgroundTint 不重跑）→ 无背景图用户改主题背景色后豁免页底色残留旧色。
- **二次亲核修正（2026-08-28）**：残留真因 = upBackgroundImage 缺回落（T2 四件套之一），非豁免分支漏调——**修 T2 即同时修复 T10**（tasks 2.5.2 已合并 T2+T10）。
- **方案**：随 T2 落地（upBackgroundImage 增 `!imageBg` 回落窗口背景色分支即闭环）。
- **优先级**：P3（随 T2）

### T11 [P3 进化缺陷] 首装预设非原子写入（dNThemeName 与 themeMode 分两次提交）
- **定位**：`App.kt:117-120` 附近——首装预设夜间主题名与 themeMode 非同一 editor 批量提交，中间崩溃致语义半套且不重试。
- **来源**：进化增量审计（数据层）。
- **方案**：合并为单 editor 批量提交（apply 原子性）。
- **优先级**：P3（首装一次性窗口，概率极低）

### T12 [P3 卫生·进化审计扩展] 注释失准/死代码/常量字面量
- **定位**：①`ThemeSync.kt:14` 注释失准（recreateActivities 非 bump 写点）+ `ThemeSync.kt:11` "仅 MainActivity/ConfigActivity 订阅"已过期（v2 上移基类）②`ThemeStore.markChanged` 死代码 0 调用 ③App.kt 3 处"暗夜紫"字面量未用 `DARK_PURPLE_THEME_NAME` 常量 ④DebugBaseActivity 系 7 调试页直继 AppCompatActivity 不经 AppContextWrapper wrap（values-night 跟系统不跟 App，调试页可接受，登记即可）。
- **方案**：修注释/删死代码/字面量换常量；④登记豁免。
- **优先级**：P3（卫生级）

### T13 [P3 进化缺陷] 异步背景图下载成功补发 RECREATE 无伴随 bump → 豁免页 Compose 背景图盲区
- **定位**：`ThemeConfig.kt:479-485`——背景图异步下载成功后仅补发 RECREATE，无 ThemeSync.bump。
- **来源**：visual-audit-event-consistency.md 任务3。
- **影响**：豁免宿主（ConfigActivity）停留时背景图下载完成 → Compose 侧背景图层不刷新（View 侧经基类 recreate 刷新，豁免页两侧不同步）。
- **方案**：补发处伴随 ThemeSync.bump（保持双令牌恒成对原则，参照 applyTheme 收尾）。
- **优先级**：P3

## X XML 资产卫生批（2026-08-28 compose-migration-audit 审计新增，🆕 P3；X1/X2/X4/X5 ✅ 已处置 2026-08-28，X3 归 R3 真机走查）

> 来源：`docs/temp-analysis/compose-migration-audit-20260828.md`（Compose 化完成度深度审计修订版 R2，二次全面审查产出，先读 ui-standards 7 份子规范 + 3 权威源校准后落盘）。
> 定性：XML 资产卫生 + 收尾确认批，全部 P3，与 H/D/S/T 批正交，可穿插任意编译批次执行。任务条目 = tasks 2.6 批（次序 4.6）。

### X1 [P3 卫生] 孤儿 layout XML 清理（47 个）（✅ 已完成 2026-08-28，见 tasks 2.6.1：三渠道扫描实测 41 个全删，6 注释级引用保守保留，红线 3 布局未动）
- **定位**：`app/src/main/res/layout/` 下 41 个全孤儿 + 6 个注释级遗留。构成：dialog_ 31（D 批迁移遗留——宿主已改 ComposeDialogFragment，XML 未随迁删除）/ item_ 14（迁移后被变体或 Compose 列表取代）/ activity_config 1（已亲核闭环：ConfigActivity 纯代码 LinearLayout 容器 + ComposeView 顶栏，双渠道验证无引用）/ popup_highlight_rule_action 1（仅 popup_highlight_action 在用）。
- **完整清单**：审计报告 §七（compose-migration-audit-20260828.md）。
- **⚠️ 勿删 3 个仅 include 引用**：view_search（6 处 app:contentLayout/include）/ view_error / view_loading（均被 view_dynamic include，DynamicFrameLayout inflate）。
- **方案**：删前对每个文件 Grep 二次确认（`R.layout.<名>` + PascalCase Binding 类名双渠道）→ 删除 → 全量编译 → 安装冒烟（L1）。
- **优先级**：P3

### X2 [P3 卫生] 12 个 pref XML 搜索索引收尾（⚠️ 半步执行 2026-08-28，见 tasks 2.6.2：4 个零引用已删；7 个数据源 XML 简化保留待专项——模型化迁移需 7 Fragment buildPageSpec 静态化重构，P3 收益<回归风险）
- **定位**：`res/xml/pref_config_*.xml` ×12 已"半退役"——全工程无 `setPreferencesFromResource`/`addPreferencesFromResource`，设置 UI 本体 = MySettingsScreen（Compose）+ ComposePreferenceScreen；XML 唯一消费点 = `MySettingsData.kt:184` XmlPullParser 手动解析，**仅构建设置页搜索索引**。
- **方案**：搜索索引改读 Compose 数据模型（MySettingsSectionModel）→ 删除 12 个 XML；`xml/` 下 5 个框架机制文件（network_security_config/file_paths/spen_remote_actions/双 widget info）**永久保留**。
- **优先级**：P3

### X3 [P3 确认型] 存疑间接宿主运行时确认（4 处）
- **定位**：①UrlRecordActivity（存在 UrlRecordScreen.kt，宿主方式未确认）②WelcomeActivity+Launcher1~7（存在 WelcomeScreen.kt）③7 个 Debug 活动（DebugBaseActivity 含 @Composable，推断间接宿主）④旧书架 BooksFragment 死码确认（无引用可删）。
- **方案**：归 R2/R3 真机走查附加确认项，确认后更新页面矩阵与迁移登记。
- **优先级**：P3

### X4 [P3 评估型] BookInfoActivity View 版退役评估（✅ 评估完成 2026-08-28，见 tasks 2.6.4：结论=不退役保留双栈，属 loadStyle 运行时分支的有意 v2 进化，禁止回退）
- **定位**：`BookInfoActivity`（View 版）与 `BookInfoComposeActivity`（Compose 版）并存。
- **方案**：全仓确认所有入口跳转已切 Compose 版后退役 View 版（连带评估 activity_book_info.xml 归属）。
- **优先级**：P3

### X5 [P3 文档] 权威源文档治理 8 项（二次审查发现）（✅ 8 项全处置 2026-08-28：①§0 注记已更新②tasks checkbox 已勾③registry 六镜像已回填含 H15-H17 新增行④dialog-shell D1/D2/D3/D4 进度已回填⑤how-to 头部日期已更新⑥issue-list 标题 ✅ 标记已补齐（H1/H2/H3/H4/H5/H7/H10/H11/H12/H15/H16/H17/X1/X2/X4）⑦alert 双口径已 grep 复核=剩余 25 文件复杂型登记保留⑧H11 统一为 6/6（TxtTocRuleScreen:268 源码亲核权威）
- **清单**：①tasks §0 次序 3 ※ 注记滞后（仍列已完成的 H12/H7/H3/H5/H4/H1/H2）②tasks checkbox 落后实际（2.2.0c/d/e 内容标 ✅ 未勾）③migration-registry 六镜像滞后（H7/H12/D4 已完成仍记 [ ]；D1/D2/D3 进展未回填）④dialog-shell.md 未回填 D1 实施进度（38 全量队列定义 vs 4 迁+登记保留实况）⑤how-to.md 头部日期 08-27 滞后正文 08-28 条目⑥issue-list 标题 ✅ 标记不齐（H1/H2/H4/H5/H7/H10/H12）⑦alert{} 文件数 71 vs 76 双口径待 grep 复核（D2 实施前）⑧H11 完成度 §0 写 6/6 与 issue-list 5/6 矛盾（本次已核实 tasks 2.2.0e 为权威 = 5/6 剩 TxtTocRuleScreen L253，仅 §0 注记滞后）。
- **方案**：随 R2/R3 收尾（tasks 5.2 文档同步）一并处置，逐项勾销。
- **优先级**：P3

## 汇总

| 优先级 | 条数 | 覆盖 |
|--------|------|------|
| P0 | H6(ConfigActivity) + H8(AppDropdownMenu 38 文件) + H9(精准管理页根背景 M3 surface + SettingsCard 体系 5 文件 13 处) + **H11(6 页列表项卡片 M3 surface 归位)** + H3(AiChat/MyFeatureBooks) + D1(旧弹框 P0 子集)/D2(高频) + S1/S2/S3 | 用户实锤 ×3 + 真未纳管孤例 + 根背景(PreciseManage 1 页)+列表项卡片(6 页) M3 派生色 + 高可见弹框 + 订阅切换残留 |
| P1 | H7(漫画/发现经典系统菜单+残存清理) + H10(列表项 M3 派生色归位) + H12(Debug 8 页 M3 顶栏) + H13(Glass 不消费 TopBarConfig 评估) + H4 + D1(其余)/D3 + S4/S6 + **T1(跟随系统链路 NIGHT_MASK/防抖/AppearanceKit，复核维持) + H15(自绘头部未接入 TopBarConfig 族 11 页，含 5 同类扩围) + H16(AppDropdownMenu vs ModernActionPopup 差异 6 项，47 文件感知主因)** | 系统菜单样式点 / 列表项色源分裂 / 旧 TitleBar / 中频弹框 / **主题体系架构偏差 + 视觉实况审查（2026-08-28）** |
| P2 | H1(已纳管形态差异登记)/H2(注释)/H5(并入H3)/H14(角色系列底色 P2) + D4(13 散点) + S5 + **T2(背景图回落四件套，复核降级)/T4(Auto 分支对齐 isNightTheme，定性修正)/T5(高刷管理)/T7(阅读器豁免+施工陷阱警示)/T8(RECREATE 自订阅残留 3 处)/H17(菜单漏网 4+1+死代码)** | 细节/注释/散点/低频自绘体系 / **主题体系兜底与进化对齐项 + 菜单漏网** |
| P3 | **T3(AudioPlay 豁免核实型，复核降级)/T6(死事件清理)/T9(套件双 RECREATE 权衡登记)/T10(豁免页 tint 残留)/T11(首装原子性)/T12(卫生批)/T13(背景图补发缺 bump)** + **X1(47 孤儿 layout 清理)/X2(12 pref XML 搜索索引收尾)/X3(4 存疑宿主确认)/X4(BookInfo View 版退役评估)/X5(权威源治理 8 项)** | 卫生级/核实型 + **XML 资产卫生与收尾确认（2026-08-28 审计新增）** |

> **实施顺序**：先 S（订阅切换，独立可控）→ H6/H8/H9/H11/H3（用户实锤 + 最大覆盖面菜单/组件 + 根背景(PreciseManage 1 页)+列表项卡片(6 页) M3 派生色归位）→ D P0（弹框高频）→ H10/H12/H13/H7/H4/P1 分批 → 其余 P2。每批编译+复测。
> **核心教训**：①必须主代理亲自 Read 目标组件源码确认纳管状态，禁止凭子代理报告下结论 ②排查必须覆盖"宿主页架构/菜单承载方式/组件体系"三个维度，不能只按头部组件清单盘点（已漏 ConfigActivity 隐藏 Toolbar+MenuProvider、AppDropdownMenu M3 体系、SettingsCard/ListCard M3 派生色、M3 派生色根背景+列表项卡片（H11 曾误判二者）、Debug 页 M3 顶栏、Glass 不消费 TopBarConfig，六大盲区）③禁止"评估为存量/豁免"跳过未纳管项 ④判据 C5"误用 MaterialTheme"必须区分 M3 派生色（lerp 偏移）与主题背景色直读（H9/H11 教训）⑤同类组件必须核对"取色来源是否同一套"（直色体系 vs M3 派生体系），不能只看"是否写了 MaterialTheme" ⑥**必须逐页 Read 根容器背景取色，并区分"页面根背景"与"列表项卡片"再判定**（H11 初判把 6 页列表项卡片 M3 surface 误当根背景——实施前 Read 根容器确认真实背景，Grep 关键字不足且不得跨层误判）。

### T18 [P3] 顶栏图标「粗细」统一专项——自绘 ic_*.xml 描边 vs M3 Icons 标准描边（bookshelf-refresh-and-title-font 4.4 登记，2026-08-29）
- **现象**：四层顶栏图标资产混用（自绘 ic_*.xml 描边宽度各异 vs M3 Icons 标准描边），同屏观感粗细不一
- **范围**：全部自绘图标资产（影响面=App 全部 ic_*.xml，独立专项量级）
- **基线**：尺寸档已统一（spacing-corner-typography.md §顶栏图标按钮基线：Glass/Config 20dp、管理页 20dp、主 Tab 34dp 容器豁免）；粗细对齐 M3 视觉重量需逐资产梳理
- **来源**：bookshelf-refresh-and-title-font spec Out-of-Scope 明示登记
