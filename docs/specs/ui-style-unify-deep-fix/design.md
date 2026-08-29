# ui-style-unify-deep-fix 技术设计

## Technical Approach

### 1. 组件级盘点结论（3 排查子代理 2026-08-27）

#### H 头部样式（源码核验修正结论）

> 主代理源码核验（MainTopBarView/GlassTopAppBar/AppManagementScaffold/AppSettingComponents/ConfigActivity/AiChatScreen/MyFeatureBooksActivity）：
> **绝大多数头部组件已全量随主题纳管**，真正的"未纳管"孤例很少。之前子代理报告的"5 类分裂"中，多数为"已纳管但形态不同"（高度 48/56dp、View/Compose 技术栈），非功能缺陷。

| 组件 | 路径 | 纳管状态 | 处理 |
|------|------|---------|------|
| `MainTopBarView(SUB)` | ui/widget/MainTopBarView.kt | ✅ 全量纳管（TopBarConfig+ThemeStore） | 基线（保留） |
| `GlassTopAppBar` | ui/widget/components/GlassTopAppBar.kt | ✅ 全量纳管（primaryColor+barElevation+ThemeSync） | 基线（保留） |
| `AppManagementTopBar` | ui/widget/compose/AppManagementScaffold.kt | ✅ 全量纳管（AppSettingPalette=AppDialogStyle/themeUiPalette/UiCorner） | 列表管理页基线（保留） |
| `ConfigTopBar` | ui/config/ConfigActivity.kt | ⚠️ 文字/字体已纳管（rememberAppSettingPalette），**背景未纳管**（无 background） | 修背景（H6）+ 修注释（H2） |
| `TitleBar` 残留 | ReadRecord/S3Container/LibraryContainer/AiImageProviderEdit | ⚠️ 部分纳管（managed 需显式开） | 迁移 MainTopBarView/GlassTopAppBar（H4） |
| `AiChatScreen` 背景 | ui/main/ai/compose/AiChatScreen.kt L851 | ❌ **未纳管**（Color.Black 硬编码） | 改主题色（H3） |
| `MyFeatureBooks` | ui/main/my/MyFeatureBooksActivity.kt | ❌ **未纳管**（M3 TopAppBarDefaults 默认色） | 改 GlassTopAppBar（H3/H5） |
| `OpenUrlConfirm`/`VerificationCode` | ui/association/*.kt | ❌ **未纳管**（原生 Toolbar） | 改项目头部（H5） |
| `TocTopBar`/`AiProviderTopBar`/`WorldBookTopBar`/`RelayTopBar`/`AiImageProviderTopBar`/`AppDialogTitleBar` | 各 Compose 页 | ⚠️ 部分纳管（自绘、参数不统一） | 视觉参数对齐（H3） |
| `ConfigActivity` 头部（ConfigTopBar） | ui/config/ConfigActivity.kt L188-223 | ❌ **未纳管**（无 background，透出窗口色/黑色）+ recreateOnThemeChange=false | 增背景随顶栏设置（H6 用户实锤） |
| `ConfigActivity` 三点菜单 | ui/config/ConfigActivity.kt L63-70/L133 + BackupConfigFragment/ThemeConfigFragment MenuProvider | ❌ **未纳管**（隐藏 Toolbar + MenuProvider 系统菜单，非 ModernActionPopup） | 改 ModernActionPopup（H6） |
| `ReadManga` 漫画菜单 | ui/book/manga/ReadMangaActivity.kt + view_manga_menu.xml | ❌ 系统菜单样式 | 改 ModernActionPopup（H7） |
| `ExploreFragment` 经典模式菜单 | ui/main/explore/ExploreFragment.kt L341-347 | ❌ 系统菜单样式 | 改 ModernActionPopup（H7） |
| 7 处 menuInflater.inflate 死代码（book_source 等） | BookSource/RssSource/ReplaceRule/RuleSub/ReadRecord/ReadBook/AiImageProviderManage | 注入隐藏 Toolbar 用户不可见 | 清理（可选） |

> **H6/H7/H8 说明**：深挖"菜单承载方式/组件体系"维度发现**四套菜单体系并存**：
> ①`ModernActionPopup`（自绘圆角卡片，23 文件，主界面主流，用户认可）②`AppDropdownMenu`（M3 原生 DropdownMenu，**38 文件 = 33 import + 5 同包**，Compose 次级页面，视觉与①明显不符——用户实锤替换编辑/字典页）③系统 Toolbar 菜单（隐藏 Toolbar+MenuProvider，ConfigActivity 宿主 2 子页用户实锤+漫画+发现经典）④`PopupMenu`（上轮 G7 已清）。统一方向：AppDropdownMenu 渲染层对齐 ModernActionPopup 视觉（38 调用点零改动）。
> **排查盲区教训：不能只按头部组件清单盘点，必须覆盖宿主页架构、菜单承载方式、组件体系三个维度。**

#### D 弹框样式（5 家族视觉体系，118 文件全核实）

> 弹框统一按"主题纳管判定"执行：36 个旧 View 弹框仅 `setBackgroundColor(ThemeStore.backgroundColor())` 联动背景、控件硬编码 → **撤销上轮 G6"存量保留"判定，全部入迁移队列**（上轮误计 38，实测 36）+ BasePrefDialogFragment 2 个一并评估；系统 AlertDialog 完全不随主题；Import 系列已随主题但风格非主流。基线 = ComposeDialogFragment + AppDialogFrame（全量纳管）。

| 类别 | 实现 | 数量 | 随主题 | 处理 |
|------|------|------|--------|------|
| D-A 主流 Compose | `ComposeDialogFragment` + `AppDialogFrame`/`AppDialogStyle` | 49 文件（9 工厂+40 子类） | ✅ 全纳管 | 基线（保留） |
| D-B 旧 View | `BaseDialogFragment` 家族 | 36（+pref 2） | ⚠️ 仅背景色 | **D1 全部入迁移队列（撤销存量判定），P0/P1/P2 分级** |
| D-C 系统弹框 | `alert{}` DSL / 内联 `AlertDialog.Builder` | 71 文件 162 处 + 9 处（主代理复核 `import lib.dialogs.alert`=76 文件，实施前 grep 复核） | ❌ 不随 | **D2 收敛 ComposeConfirmDialog 族** |
| D-D Compose 非主流 | Import 系 7 + M3 @Composable 5（AppConfirm/AppEdit/AppText/SingleChoice/Confirm） | 12 | ✅（material3 默认） | **D3 对齐 AppDialogStyle** |
| D-E 散点 | raw Dialog 4 / BottomSheetDialogFragment 3 / ComponentDialog 2 / AlertDialog+ViewBinding 4 | 13 | ⚠️ 部分 | **D4 迁移/登记** |

#### S 订阅切换结构遗留（6 个）

| # | 遗留 | 位置 | 影响 |
|---|------|------|------|
| S1 | `updateRssSourceNameWidth` layout 监听跨模式残留（无 guard） | RssFragment L419/L420 + L493-505 | classic 下标题宽度被钳制 96~190dp |
| S2 | 切换靠 onResume 兜底，RssFragment 不监听 NOTIFY_MAIN | L311-315 vs MainActivity L2326 | fragment 未重新 onResume 则切换不生效 |
| S3 | classic 状态 currentGroup/currentType/selectedRssTag 未重置 | L368 vs L237/L240/L250 | 切回经典后残留上次分组/类型筛选 |
| S4 | rssTopOverlaySpace/rssTopOverlayEnabled 跨模式旧值 | L687-691 | overlay 时序风险 |
| S5 | classicHeaderReady 一次性标记永久驻留 | L166/L941-952 | 状态永久驻留（modern 下无害） |
| S6 | sortHostViewModel 跨模式保留旧源 | L606-609 | 切回 modern 前状态残留 |

### 2. 统一基线定义

- **View 页面头部基线**：`MainTopBarView(Mode.SUB)`（读 TopBarConfig + 主题 token）
- **Compose 页面头部基线**：`GlassTopAppBar`（读 primaryColor/elevation/ThemeSync）
- **管理页基线**：`AppManagementScaffold`（AppManagementTopBar 读 AppSettingPalette，全量纳管）
- **设置宿主页基线**：ConfigActivity 头部增背景（读 TopBarConfig/ThemeStore）——见 AD-01 补充/H6
- **弹框基线**：`ComposeDialogFragment` + `AppDialogFrame`/`rememberAppDialogStyle`
- **菜单统一基线**：ModernActionPopup 视觉（自绘圆角卡片 + LegadoMiuixChoiceRow + AppDialogStyle）；AppDropdownMenu 渲染层对齐（38 调用点零改动）——见 AD-05
- **订阅切换状态机**：applyRssMode() 为唯一入口，切换时统一 reset 状态

### 3. 修复分层

- **H6 ConfigActivity 宿主页**（P0 用户实锤）：ConfigTopBar 增背景（读 TopBarConfig/ThemeStore）+ 三点菜单 MenuProvider 系统菜单 → ModernActionPopup + 评估 recreateOnThemeChange
- **H8 菜单体系统一**（P0 用户实锤，最大覆盖面）：AppDropdownMenu 渲染层对齐 ModernActionPopup 视觉（38 调用点零改动）；清理 0 调用 components/ModernActionPopup.kt；AllBookmarkScreen 裸 M3 切入；替换净化/字典头部接入 TopBarConfig 评估
- **H9 精准管理页背景 + 设置组件体系**（P0 用户实锤）：PreciseManageScreen L40 M3 surface 背景 → palette.settings.page（ThemeStore 直读）；SettingsCard/SettingsClickRow M3 派生色 → AppSettingPalette 调色板（5 文件 13 处：SettingsCard 3 + SettingsClickRow 10）
- **H10 列表项 M3 派生色归位**（P1，H9 同源）：DictRule/Highlight/Download 列表项 + ListCard 默认色 → palette.settings.row（AppManagementCard 直色对齐）
- **H11 列表项卡片 M3 surface 归位**（P0/P1，主代理修正：原判"6 页根背景 surface"不实）：AutoTask/TxtTocRule/AllBookmark/Highlight/DictRule/RecycleBin 列表项卡片 `Surface(color = MaterialTheme.colorScheme.surface)` → `palette.settings.row`（与 H10 同源合并治理；真正 M3 surface 根背景仅 PreciseManageScreen 1 页归 palette.settings.page）
- **H12 Debug 8 页 M3 TopAppBar 归位**（P1）：Debug 家族 7 页 + MyFeatureBooks 裸 M3 TopAppBar（secondary 色）→ GlassTopAppBar（primaryColor 主色）+ LegadoBackgroundBox 兜底色改 page 直色
- **H13 GlassTopAppBar 接入 TopBarConfig**（P1，2026-08-27 用户裁决接入）：玻璃顶栏随顶栏管理壁纸/背景色/圆角/透明度，与 MainTopBarView 对齐（真机重点回归订阅页/书架毛玻璃）
- **H7 系统菜单样式点**（P1）：ReadManga 漫画菜单 + ExploreFragment 经典模式 → ModernActionPopup
- **H3/H5 未纳管孤例**（P0）：AiChat 硬编码黑背景 → 主题色；MyFeatureBooks 原生 M3 → GlassTopAppBar；原生 Toolbar → 项目头部
- **H4 TitleBar 残留迁移**：ReadRecord/S3Container/LibraryContainer/AiImageProviderEdit → MainTopBarView(SUB)
- **H1/H2**（P2）：管理页双形态登记说明（不替换组件）；ConfigActivity 注释修正
- **D1 旧弹框迁移**（全入队列）：P0 高频可见 → ComposeDialogFragment；P1/P2 分批
- **D2 系统弹框收敛**：alert{} 高频确认/选择 → ComposeConfirmDialog/ComposeSingleChoiceDialog
- **D3 Import 系列对齐**：ImportSourceSheet 改 AppDialogStyle
- **S1-S6 订阅切换修复**：逐项加 guard/重置/事件/隔离

## Architecture Decisions

### AD-01: 管理页头部形态差异（保留双形态，按页面类型归类）
- **Context**: 用户点开书源管理/订阅源管理（AppManagementTopBar 48dp）与主题管理/顶栏管理（MainTopBarView 56dp），同是"管理页"但头部形态不同
- **Concern**: 初判"双体系分裂需统一"，但源码核验发现**两者均已全量纳管**（AppManagementTopBar 读 AppSettingPalette=AppDialogStyle/themeUiPalette/UiCorner；MainTopBarView 读 TopBarConfig+ThemeStore）。替换组件会破坏 AppManagementScaffold 的搜索框/多选底栏能力且技术倒退
- **Decision**: **不替换组件**。按页面类型归类：列表管理页（书源/订阅源/替换/规则/书架标签）保持 AppManagementScaffold 形态；设置管理页（主题/顶栏/外观）保持 MainTopBarView(SUB) 形态。视觉差异（48/56dp）为技术栈形态差异，登记说明而非强改。若用户明确要求全 App 头部高度一致，另行评审（风险高）
- **Goal**: 同类型管理页头部形态一致；避免破坏既有 Compose 管理页能力
- **Tradeoff**: 两形态并存（48/56dp）观感仍有差异——接受，因两者均已随主题纳管（满足用户"主题设置统一管理"核心诉求），强改组件回归风险大于观感收益
- **Status**: Accepted（用户质疑"别改错"后修正）

### AD-02: 弹框收敛基线 = ComposeDialogFragment + AppDialogFrame
- **Context**: 主流 Compose 弹框 49 个已统一（AppDialogFrame 全量纳管，从 AppDialogStyle 取色）；36 个旧 View（+pref 2）+ 71 文件 162 处系统 AlertDialog + M3 @Composable 5 个 + 散点 13 并存
- **Concern**: 全量立即迁移 36 个旧弹框风险高；部分（WaitDialog/PhotoDialog/CodeDialog）被多页复用场景特殊
- **Decision**: 确立 `ComposeDialogFragment` + `AppDialogFrame`/`AppDialogStyle` 为唯一弹框基线；36 个旧 View 弹框（+BasePrefDialogFragment 2）全部纳入迁移队列（撤销上轮 G6"存量保留"判定——上轮误计为 38，实测 36），按 P0（高可见高频）/P1/P2 分优先级迁移；WaitDialog/PhotoDialog/CodeDialog 等特殊场景登记"过渡期保留"但必须入队，不得永久豁免；系统 AlertDialog 高频确认/选择类收敛 ComposeConfirmDialog 族
- **Goal**: 弹框全 App 风格一致，全部样式参数均被主题设置统一纳管
- **Tradeoff**: 分批迁移期间两类并存（过渡期）——接受，以"每批编译+复测"控制回归；过渡期保留项必须登记理由与入队计划
- **Status**: Accepted

### AD-03: 订阅切换修复 = 状态机统一入口 + 事件即时生效
- **Context**: applyRssMode() 是唯一渲染入口，但 S1-S6 六个遗留导致跨模式残留/切换不即时
- **Concern**: 改事件链路可能影响 MainActivity 现有 NOTIFY_MAIN 消费；改状态重置可能影响正常使用
- **Decision**: ①`applyRssMode()` 内统一调用 `resetRssModeState()` 重置 classic 运行时状态（currentGroup/currentType/selectedRssTag/currentSorts）+ modern overlay 状态 ②`updateRssSourceNameWidth` 加 `usingModernRss` guard 且 classic 时移除 layout 监听 ③RssFragment 增加 `observeEvent(NOTIFY_MAIN)` 监听切换即时生效（替代纯 onResume 兜底，onResume 保留为兜底） ④sortHostViewModel 在 applyRssMode 时 reset ⑤classicHeaderReady 改为 per-mode 判定
- **Goal**: 经典↔新版切换即时生效、无任何跨模式残留
- **Tradeoff**: 增加事件监听带来少量复杂度——接受，事件驱动是即时生效的唯一途径；onResume 兜底保留防止事件丢失
- **Status**: Accepted

### AD-04: 自绘 Compose 顶栏收敛
- **Context**: ~10 个自绘顶栏高度/圆角/字体/返回按钮各异（56/48/54dp），MyFeatureBooks 用原生 M3，AiChat 硬编码背景
- **Concern**: 统一封装成新组件成本高，且各页有特殊需求（Toc 带搜索框+Tab、AiChat 带聊天栏）
- **Decision**: 不自建新组件库；将 ~10 个自绘顶栏的**视觉参数对齐到 AppManagementPalette/AppDialogTitleBar 规范**（统一高度 48dp、圆角、返回按钮、字体 token），MyFeatureBooks 原生 M3 → 对齐同类 Compose 头部，AiChat 硬编码背景 → ThemeStore 主题色；Toc/AiProvider 等复杂头部仅对齐视觉参数不改结构
- **Goal**: 自绘顶栏视觉参数一致，无原生/硬编码孤例
- **Tradeoff**: 不对齐结构（各页保留自定义能力）——接受，视觉一致性优先于代码复用；结构统一留待未来全 Compose 迁移
- **Status**: Accepted

### AD-05: 菜单统一基线 = ModernActionPopup 视觉（AppDropdownMenu 渲染层对齐）
- **Context**: 用户实锤替换规则编辑页/字典规则页三点弹框样式与主流不一致。深挖发现四套菜单体系并存：ModernActionPopup（自绘圆角卡片，23 文件，主界面主流，用户认可）+ AppDropdownMenu（M3 原生 DropdownMenu，38 文件 = 33 import + 5 同包，Compose 次级页）+ 系统 Toolbar 菜单（可见 4 处 + 残存 7 处死代码）+ PopupMenu（G7 已清）
- **Concern**: AppDropdownMenu 调用点 38 个，逐一迁移成本高；反向把主界面改成 M3 会推翻用户已认可的主流视觉
- **Decision**: **以 ModernActionPopup 视觉为统一基线**（rememberAppDialogStyle + LegadoMiuixChoiceRow + UiCorner 圆角，全主题纳管）。方案：**保留 AppDropdownMenu 的定位能力（锚点/弹出方位/点外关闭/滚动），仅把条目渲染层从 `DropdownMenuItem` 换成自绘 `Surface`（style.surface/stroke/panelRadius）+ `LegadoMiuixChoiceRow`**——`MenuAction` 数据驱动不变 → **38 个调用点零改动**；同步删除 0 调用 `components/ModernActionPopup.kt`（命名混淆）+ AllBookmarkScreen 裸 M3 切入；系统 Toolbar 菜单收敛 ModernActionPopup（可见 4 处：ConfigActivity/漫画/发现经典；残存 7 处死代码清理）
- **Goal**: 全 App 三点菜单统一为 ModernActionPopup 视觉，全部随主题纳管
- **Tradeoff**: 改造 AppDropdownMenu 渲染层需保持 DropdownMenu 弹出定位语义（锚点计算/滚动/点外关闭）——接受，仅替换条目渲染层不影响定位；真机验证弹出行为不回归
- **Status**: Accepted

### AD-06: 页面背景/设置组件取色基线 = AppSettingPalette 直读（M3 派生色一律归位）
- **Context**: 用户实锤精准管理页主页面样式与主设置页不一致。静态核实根因：PreciseManageScreen 根容器 `.background(MaterialTheme.colorScheme.surface)` + SettingsCard/SettingsClickRow 用 M3 派生色（surface/surfaceVariant/onSurface/onSurfaceVariant）。而 M3 colorScheme 虽由 ThemeSpec.toM3Scheme 从 bg 派生，但 surface = lerp(bg, neutral, 4%/10%)、surfaceVariant = lerp(bg, onBg, 5%/14%)——**是偏移色，非 backgroundColor 直读**
- **Concern**: 上轮 C5"误用 MaterialTheme"判据把所有 `MaterialTheme.colorScheme.xxx` 一律判为"已随主题"——但 M3 派生色与调色板直读在自定义背景色/卡片色下明显偏色；若继续放任会持续产生"主页面 vs 子页面"色差
- **Decision**: 确立取色基线——**页面根容器背景统一 `palette.settings.page`（= Color(context.backgroundColor) = ThemeStore 直读）；设置类卡片/行/文字统一 AppSettingPalette（primaryText/secondaryText/accent/UiCorner.surfaceColor）**。凡 Compose 页面根容器/设置组件出现 `MaterialTheme.colorScheme.surface/surfaceVariant/onSurface` 且语义为"页面背景/设置卡片"的，一律归位到调色板直读；仅保留 M3 派生色用于确实需要中性灰浮层语义的场景（多选底栏 surface、列表项卡片、调试工具输入框等，登记说明）
- **Goal**: 所有管理页/设置页根容器背景与主设置页一致（主题背景色直读），无 M3 派生色偏色
- **Tradeoff**: SettingsCard/SettingsClickRow 取色改调色板需评估其对 5 文件 13 处使用点（AutoTaskEdit/BookInfoEdit/StorageManage/VideoSettingsPanel + PreciseManage 自身 5 行）的视觉影响——接受，统一调色板是收敛方向；逐点回归
- **Status**: Accepted

### AD-07: 组件体系单一化治理（根治"一类组件多种模式"，用户 2026-08-27 二次质疑）
- **Context**: 用户质疑"为什么这么多不一致组件？有没有考虑后续一致性问题从根源所有组件系的差异化，别一类组件用好几种模式，看着特别不像一个成熟软件"。全量盘查确认六类组件全部存在多实现分裂：
  - 顶栏 8 种（GlassTopAppBar ~40 / MainTopBarView ~35 / 自绘私有Row ~8 / 旧TitleBar ~20 / M3直用 8 / AppManagementTopBar ~6 / ConfigTopBar 1 / 弹窗Toolbar ~18）
  - 三点菜单 3 种活跃（AppDropdownMenu 38：**M3 原生 33 import + 5 同包** / ModernActionPopup：**View 版 `ui/widget/ModernActionPopup.kt` 在用 23 + Compose 版 `ui/widget/components/ModernActionPopup.kt` 0 调用死代码** / 系统 Toolbar 菜单 可见 4 + 残存 7）
  - 弹框 5 家族（A 新 Compose 49 文件 / B 旧 View BaseDialogFragment 36 + pref 2 / alert{}DSL 71 文件 162 处 / M3 @Composable 5 / D 散点 13）
  - 设置卡片/行 3 套（appSettingPanelBackground 10 / SettingsCard M3 6 / AppManagementCard 21）
  - 列表项 2 套色源（管理页 AppManagementCard 直色 vs 字典/高亮/下载 M3 surface）
  - 根容器背景 3 种（palette.settings.page ~13 / M3 派生色系（根背景 surface 1 页 PreciseManage + 列表项卡片 surface 6 页 + Debug background 7 页）/ context.backgroundColor）——主代理 2026-08-27 逐页 Read 修正口径
  - > 注：以上数量为实测统计口径（页面矩阵子代理 2026-08-27；详见 docs/temp-analysis/ui-component-system-analysis-*.md + ui-page-matrix.md）。ComposeDialogFragment 族 = 49 文件（9 工厂 + 40 子类，含 ReaderBottomSheet 3）；BaseDialogFragment=36（逐文件核实）+BasePrefDialogFragment 2；alert DSL=71 文件 162 处调用；AppDropdownMenu=33 import+5 同包含 ImportSourceSheet。
- **Concern**: 若只按 H9 单点修复，M3 派生色组件（ListCard/SettingsCard/AppDropdownMenu/字典高亮列表项）仍会继续与直色体系并存，下次用户仍会点出"某页又不一致"——必须从**组件层/取色层**根治，而非逐页打补丁
- **Decision**: 确立**组件单一来源（Single Source of Truth）**治理：
  1. **取色唯一基线** = `rememberAppSettingPalette()`（页面/行/文字/强调色直读）+ `rememberAppDialogStyle()`（弹框/菜单面板）+ `UiCorner`（圆角/透明度/壁纸/边框）——**禁止 Compose 页面级/卡片级使用 `MaterialTheme.colorScheme.surface/surfaceVariant/onSurface` 做视觉取色**（M3 仅允许在确需中性灰浮层语义处使用并登记，如多选底栏/调试工具输入框）
  2. **组件收敛**：顶栏 → GlassTopAppBar/MainTopBarView/AppManagementTopBar 三基线（自绘私有 Row 顶栏并入 AppManagementScaffold 或对齐视觉参数）；菜单 → AppDropdownMenu 渲染层对齐 ModernActionPopup 视觉（AD-05，38 调用点零改动）+ **删除 0 调用死代码 `components/ModernActionPopup.kt`（消除同名双实现混淆）**；弹框 → ComposeDialogFragment+AppDialogFrame（AD-02，36 旧 View+pref2 + alert{} 分批迁移）；设置卡片/列表项 → `appSettingPanelBackground`/`AppManagementCard`（直色），SettingsCard/ListCard M3 取色归位直色
  3. **新增代码门禁**：新增 Compose 页面/组件必须走上述单一来源取色（Grep 检查 `MaterialTheme.colorScheme.surface` 新增即拒）；F-UI-THEME 增加"同类页面取色同源"断言
- **Goal**: 每类组件收敛到单一权威实现 + 单一取色来源，杜绝"同类页面两种底色来源"，从根源消除一致性回潮
- **Tradeoff**: 治理面大（涉及全部 Compose 组件与历史遗留），需分批执行 + 每批编译/复测；短期内 View/Compose 双栈必然并存（技术栈天然两分），但**取色来源统一**后双栈视觉一致——接受，分批收敛是唯一可控路径
- **Status**: Accepted

### AD-08: 彻底统一四阶段路线图（基于组件实现树 + 125 页矩阵）
- **Context**: 组件体系深挖子代理 + 页面矩阵子代理（2026-08-27）产出了四大组件族完整实现树（顶栏 8 种/菜单 3 活跃/弹框 5 家族/卡片三族）+ **125 页五维矩阵** + 弹框迁移对照矩阵（落盘 docs/temp-analysis/ui-component-system-analysis-*.md + ui-page-matrix.md），发现 H11（6 页列表项卡片 M3 surface，初判"根背景"经主代理 Read 修正）、H12（Debug 8 页 M3 顶栏脱离主色）、H13（GlassTopAppBar 不消费 TopBarConfig）、H14（角色系列 4 页 page/card/stroke 底色硬编码）四个新问题，另登记豁免 AudioPlay/QrCode/ImageCrop/播放器沉浸层
- **Concern**: 修复顺序若随意，会出现"根背景归位了但顶栏还分裂/顶栏统一了但弹框没迁移"的中间态混乱；需要分阶段收敛，每阶段内部自洽、可独立验证
- **Decision**: 四阶段路线图（Phase 内串行，Phase 间可分批验收）：
  - **Phase 1 取色源统一（无 UI 风险先行）**：确立 AppSettingPalette + AppDialogStyle + UiCorner 为唯一取色基线；M3 派生组件（SettingsCard/SettingsClickRow/ListCard）归位直色（H9/H10）；AppDropdownMenu 渲染层对齐 ModernActionPopup 视觉（H8）；删死代码 components/ModernActionPopup
  - **Phase 2 根背景 + 顶栏收敛**：PreciseManage 根背景 M3 surface → palette.page（H9）+ 6 页列表项卡片 surface → palette.settings.row（H10/H11 合并归位）；自绘 Row 5 管理页 → AppManagementScaffold（H3/H4）+ ReadRecordActivity 壳层归位；ConfigTopBar 增背景（H6）；Debug M3 → Glass（H12）；Glass 接入 TopBarConfig（H13，2026-08-27 已裁决）；系统 Toolbar 可见 4 处 → ModernActionPopup（H6/H7）+ 残存 7 处死代码清理；角色系列 page/card/stroke 底色归位调色板（H14）
  - **Phase 3 弹框收敛（大批量分批）**：D1 36 旧 BaseDialogFragment（+pref 2）按迁移矩阵 → Compose 族（P0 先行）；D2 alert{} 71 文件高频点 → ComposeConfirmDialog 族；D3 M3 5 组件 + Import 系对齐 AppDialogFrame（留 AppModalBottomSheet/AppMenuSheet）；D4 13 散点迁移/登记；AppDialogFrame 补面板背景图支持
  - **Phase 4 机制防回潮（收尾）**：Grep 门禁（M3 surface 页面/卡片级新增即拒）；F-UI-THEME 增"取色同源"断言；一致性矩阵维护为常驻文档；updateLog/文档同步
- **Goal**: 每阶段独立可验证（编译+复测），最终同类页面同组件同取色，无回潮通道
- **Tradeoff**: 四阶段总时长较长（D 弹框迁移量大）——接受，分批控制回归；Phase1 先行快速见效（用户最早能看到菜单/卡片一致），Phase3 弹框最后（量大低频面广）
- **Status**: Accepted

## Data Flow

### 订阅切换修复数据流

```
设置页 SubscriptionConfigFragment
  → onSettingPreferenceChanged(PreferKey.modernRssPage)
  → postEvent(EventBus.NOTIFY_MAIN, false)      [已有]
  → RssFragment.observeEvent(NOTIFY_MAIN)       [新增]
      → if (usingModernRss != AppConfig.modernRssPage) applyRssMode()   [即时生效]
  → applyRssMode()
      → resetRssModeState()                      [新增：重置 classic 状态 + overlay + viewmodel]
      → if (usingModernRss) applyModernRssMode() else applyClassicRssMode()
  → onResume() 兜底比对（保留）
```

### 弹框迁移数据流

```
旧调用点 xxx.show(...)
  → 迁移 ComposeDialogFragment 子类（setContent + AppDialogFrame）
  → 交互事件走 Compose 回调 → 与调用方回调协议对齐
```

## File Changes

### H 头部+菜单统一

| 文件 | 变更 |
|------|------|
| `ui/config/ConfigActivity.kt`（H6 P0） | ①ConfigTopBar 增背景（读 TopBarConfig/ThemeStore 随顶栏设置）②三点菜单 MenuProvider 系统菜单 → ModernActionPopup（改造隐藏 Toolbar 承载方式）③评估 recreateOnThemeChange=false |
| `ui/config/BackupConfigFragment.kt` + `ThemeConfigFragment.kt` 等 9 设置页（H6 P0） | MenuProvider 系统菜单 → ModernActionPopup（随 ConfigActivity 改造） |
| `ui/widget/components/AppDropdownMenu.kt`（H8 P0） | 渲染层 DropdownMenuItem → 自绘 Surface(style.surface/stroke/panelRadius) + LegadoMiuixChoiceRow（对齐 ModernActionPopup，38 调用点零改动） |
| `ui/widget/components/ModernActionPopup.kt`（H8） | 0 调用死代码 → 删除（消除命名混淆） |
| `ui/config/PreciseManageScreen.kt`（H9 P0） | L40 `.background(MaterialTheme.colorScheme.surface)` → `.background(palette.settings.page)`（rememberAppSettingPalette 直读 ThemeStore 背景色） |
| `ui/widget/components/SettingsCard.kt` + `SettingsClickRow.kt`（H9 P0） | M3 派生色 → AppSettingPalette 调色板（containerColor → UiCorner.surfaceColor(themeUiPalette.cardColor)、文字 → primaryText/secondaryText、标题 → accent） |
| `ui/autoTask/AutoTaskEditScreen.kt` / `ui/book/info/edit/BookInfoEditScreen.kt` / `ui/book/storage/StorageManageScreen.kt` / `ui/video/VideoSettingsPanelContent.kt`（H9 回归） | SettingsCard/SettingsClickRow 取色归位后逐点回归 |
| `ui/highlight/HighlightRuleScreen.kt` + `ui/dict/rule/DictRuleScreen.kt`（H10 P1） | 列表项 `colorScheme.surface/onSurface` → `palette.settings.row`/`primaryText`（对齐 AppManagementCard） |
| `ui/widget/components/ListCard.kt` + `ui/download/DownloadManageScreen.kt`（H10 P1） | ListCard 默认 containerColor M3 surface → 调色板直色入参 |
| 6 页列表项卡片（AutoTaskScreen L283 / TxtTocRuleScreen L253 / AllBookmarkScreen L146 / HighlightRuleScreen L218 / DictRuleScreen L241 / RecycleBinScreen L291）（H11 P0/P1） | 列表项卡片 `Surface(color = MaterialTheme.colorScheme.surface)` → `palette.settings.row`（与 H10 同源合并治理；根背景仅 PreciseManageScreen 1 页归 palette.settings.page） |
| `ui/debug/DebugToolsScreen.kt` + `HttpDebugScreen.kt` + `RegexTestScreen.kt` + `PingTestScreen.kt` + `TimestampConvertScreen.kt` + `EncodeToolsScreen.kt` + `CurlTestScreen.kt` + `ui/theme/ComposeActivitySupport.kt`（H12 P1） | Debug 7 页 `TopAppBar(` → GlassTopAppBar（primaryColor）；LegadoBackgroundBox 兜底色 → palette.settings.page |
| `ui/widget/components/GlassTopAppBar.kt`（H13 P1 已裁决） | 接入 TopBarConfig（壁纸/背景色/圆角/透明度），与 MainTopBarView 对齐 |
| `ui/book/bookmark/AllBookmarkScreen.kt`（H8） | 裸 M3 DropdownMenu → AppDropdownMenu |
| `ui/book/manga/ReadMangaActivity.kt` + `view_manga_menu.xml`（H7） | 系统溢出菜单 → ModernActionPopup |
| `ui/main/explore/ExploreFragment.kt`（H7） | 经典模式系统菜单 → ModernActionPopup |
| `ui/main/my/MyFeatureBooksActivity.kt`（H3/H5 P0） | 原生 M3 TopAppBar → GlassTopAppBar |
| `ui/main/ai/compose/AiChatScreen.kt`（H3 P0） | 硬编码 Color.Black/White → 主题色 |
| `ui/association/OpenUrlConfirmActivity.kt` / `VerificationCodeActivity.kt`（H5） | 原生 Toolbar → 项目头部 |
| `ui/about/ReadRecordActivity.kt` + `ReadRecordFragment`（H4） | TitleBar → MainTopBarView(SUB)（或对齐 GlassTopAppBar，按其技术栈） |
| `ui/config/S3ContainerManageActivity.kt` / `LibraryContainerManageActivity.kt` / `AiImageProviderEditActivity.kt`（H4） | TitleBar → MainTopBarView(SUB) |
| 其余自绘顶栏（Toc/AiProvider/AiWorldBook/Relay/AiImageProvider/AppDialogTitleBar）（H3） | 视觉参数对齐 AppManagementPalette |
| 7 处 menuInflater.inflate 死代码（book_source 等）（H7 可选） | 清理死代码 |

### D 弹框收敛（P0 优先清单，实施时按 issue-list 分级）

| 文件 | 变更 |
|------|------|
| 36 个 `BaseDialogFragment` 子类 + 2 pref（P0 高可见优先） | 迁移 `ComposeDialogFragment` + `AppDialogFrame` |
| `ui/association/Import*.kt`（7 个）+ `ImportSourceSheet.kt` | material3 默认 → AppDialogStyle 对齐 |
| alert{} DSL 高频调用点（71 文件筛 P0） | → ComposeConfirmDialog / ComposeSingleChoiceDialog / ComposeTextInputDialog |

### S 订阅切换修复

| 文件 | 变更 |
|------|------|
| `ui/main/rss/RssFragment.kt` | S1 guard + 监听移除；S2 observeEvent；S3 resetRssModeState；S4/S5/S6 reset |
| `ui/widget/MainTopBarView.kt`（如涉及） | 支持监听移除接口 |

> 完整逐项清单（含优先级、源码行锚点、验证方式）见 `issue-list.md`。实施时以实际源码核验为准，禁止凭经验臆测。
