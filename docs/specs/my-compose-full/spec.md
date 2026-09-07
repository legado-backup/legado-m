# spec.md — "我的"全域 Compose 化

## Intent
用户要求："我的"底栏打开的所有子页面、子子页面**零遗漏**全员 Compose 化，且先行完成**归一化设计系统**——同一套风格、组件复用、样式统一、全部由主题模式体系管理、禁止硬编码。穷尽枚举（page-tree.md 附录）修订后：一级 16 + 二级 32 + 三级叶子 + 对话框约 40 类，档位 C-full 13 / C-mixed 30 / C-none 7 / 对话框 40；孤儿/死代码 7 项同步治理。

## 归一化设计系统（页面模板四型，迁移=套模板）

| 模板 | 适用页面型 | 固定骨架 | 组件族映射 |
|------|-----------|---------|-----------|
| T1 设置型 | ConfigActivity 各 configTag Fragment / About 内容 | ComposeSettingFragment + SettingPageSpec/SectionSpec/ActionSpec | appSettingPanelBackground+RowDecoration（G8-A）、LegadoMiuixSwitch（G9）、showCompose 系弹框（G7/G11） |
| T2 管理列表型 | 管理族/顶栏包/导航栏/分享模板/缓存/封面集合等 | AppManagementScaffold + composeHost | AppManagementCard/ListRow（G8-B）、SelectionBottomBar、ModernActionPopup（G6）、AppPackageManageScreen 共享壳（TopBarManage/ShareNote 样板） |
| T3 编辑型 | 规则/提供方/模板编辑页 | composeHost 单容器 + 统一编辑组件 | showComposeTextInputDialog（G11）、AppDialogFrame（G7）、统一输入组件 |
| T4 浏览型 | 搜索/画廊/阅读记录统计等 | LazyColumn/LazyGrid + 统一空状态 | 卡片=AppManagementCard、菜单=AppDropdownMenu（G6）、空状态=统一空状态组件 |

**主题模式体系管理声明**：四型模板的取色一律经 `rememberAppSettingPalette`/`rememberAppManagementPalette`（ThemeUiPalette 单源，G2）；顶栏经 `resolvePageBarColorWithAlpha`（G5）；分日夜双键配置（背景图/字体缩放）按 isNight 维度取值；禁硬编码（G1）。模板内不允许任何页面私有颜色/样式常量。

## 豁免域（既定）
ReadBookActivity（阅读器）/ ReadMangaActivity / VideoPlayerActivity（播放器）/ SourceLoginActivity（Transparent 特殊页）——仅登记不迁移。

## Scope
### 包含
- 归一化设计系统落地：四型模板定稿 + 组件族映射表（本文件）作为全部迁移页的唯一参照
- 一级 16 页 + 二级 32 页（含孤儿治理 7 项）+ 对话框 40 类统一（View Dialog 系→ComposeDialogFragment 基线）
- 分波执行（tasks.md W1-W6，按模板分批：同模板页面同批迁移摊薄成本）

### 不包含
- 豁免域四页（见上）；主 Tab 内容区（master-track 范畴）；顶栏取色逻辑变更（一期已单源）
- 对话框的行为变更（仅渲染层统一到 ComposeDialogFragment 基线）
- BookSourceEditActivity/BookSourceDebugActivity：master-track B2/B3 已排（CodeView 编辑器+调试样板），本 spec 只登记不重复排期

## 分波与页面树映射（tasks.md 对应，红队 R1-P0 修复后穷举版）

> W0 前置（红队 R5-P0）：SubBarDebug 定稿——GlassTopAppBar shadow(0.dp) 实验回滚或定稿（恢复 barElevation 消费）、TopBarConfig.kt Log.d 热路径日志清除，L1 门禁自 W1 起可满足。

| 波次 | 模板 | 页面（穷举，红队 R1 修复：16 缺口页全部归属） |
|------|------|------------------------------|
| W0 前置 | — | SubBarDebug 定稿（shadow 决策+Log 清除）；manageBgAlpha 收窄裁决（G12 修订回写 architecture.md） |
| W1 | T2 | AppearanceKit/AppearanceKitEdit（顶栏+布局统一）；ThemeManage 顶栏+布局统一（自造组件清零拆至 W5，红队 R5 拆波） |
| W2 | T1+T4 | RssSearch(T4 列表+空状态)/About(T1 去壳)/ReadRecord 清残留/MyFragment 本体；**验收含 SettingsSearchActivity 回归**（复用路由连带） |
| W3 | T2 | TopBarManage/NavigationBarManage（含 alert{}×2 清零）/ShareNoteTemplate 收尾 + **AdvancedTitleManage 纳入** + 孤儿治理（死代码删除含 ConfigActivity 分发分支与 ConfigTag 常量同步删；删前运行时入口审计：searchTarget 深链核查） |
| W4 | T2 重写 | CacheManage（**ViewModel 复用+ItemTouchHelper→LazyColumn 拖拽重实现**）/CoverCollectionDetail |
| W5 | T2+T3 | **缺口穷举补入**：BookSourceActivity/RssSourceActivity/TxtTocRuleActivity/ReplaceRuleActivity（含 ReplaceEdit）/DictRuleActivity/HighlightRuleActivity/AutoTaskActivity(+Edit)/AiProviderManageActivity(+Edit)/AiImageProviderManageActivity(+Edit)/S3ContainerManage/LibraryContainerManage/RelaySettingsActivity/AllBookmarkActivity/CoverCollectionManage/BookInfoManage/BubbleManage/AiWorldBookManage——管理列表/编辑型统一（含 View 手术残留收尾：ReplaceRule titleBar GONE+removeView 等） |
| W6 | T4+清扫 | LogActivity/SettingsSearchActivity/UrlRecord/StorageManage/DownloadManage/FileManage/RssArticleInfo/**AiImageGallery/DebugTools（明确迁移）/QrCode/WebViewActivity/VerificationCode/OpenUrlConfirm（补登记后定迁移或豁免）**轻改收尾 + 对话框 40 类按形态分组（全屏/输入/多选/排序/预览）→ComposeDialogFragment 基线清扫 |
| 并行 | — | MainTopBarView Mode.SUB Tier 分档随波次（Tier×波次映射表见 tasks）；BookSourceEdit/BookSourceDebug 随 master-track B2/B3（**需在 master-track spec 登记坐实**） |

**manageBgAlpha 收窄裁决（红队 R2-P1/R5-P1）**：resolvePageBarColorWithAlpha 现对所有 Glass 页统一乘 fraction（40 页非管理页也随动）。裁决：fraction 语义保持"顶栏族全局"（修订 G12 表述），管理族封闭清单概念废除——理由：六验已确认全站半透明一致是用户诉求。回写 architecture.md。

**门禁编号声明（红队 R4-P1）**：本 spec 门禁表编号为 MC-1..13（避免与 migration-registry 既有 G1-G11 冲突）；architecture.md 权威源为"三条铁律+Checklist 0-8"，本表是其迁移场景展开。

## Approach（精简三要素）

### Selected Approach
**先归一化设计系统、后按模板分波套用**：四型页面模板（T1 设置/T2 管理列表/T3 编辑/T4 浏览）定稿作为唯一参照，全部待迁移页按模板归类分 6 波执行（同模板同批摊薄成本），每页迁移=去 View 顶栏（统一组件）+ 内容套模板 + 自造组件清零（G1-G13 门禁逐条核对）。落地理由：80% 页面已验证模板可复用；TopBarManage/ShareNote 已是归一化样板可直接参照；分波隔离可验收可回退。

### Alternatives Considered
| 备选 | 否决理由 |
|------|---------|
| 一次性全量重写 | 回归面巨大（含重交互页），与 master-track 波次冲突 |
| 只迁顶栏不清内容（半吊子） | 用户要求全员 Compose 化，View 残留（RecyclerView/alert{}）不清则 View 体系永不消亡 |
| 逐页自由迁移（不做模板归类） | 组件族漂移必然复发（本轮白框/黑头教训：自由度失控） |

### Drawbacks
- **风险点**：W4 CacheManage 重交互（多选/拖拽排序/清理）回归风险最高——SelectionBottomBar 已验证模式兜底
- **风险点**：MyFragment 是入口枢纽（路由 21+），纯化仅换壳、MySettingsData 路由零改动
- **风险点**：半透明观感受各页背景层数影响（跨页深浅差异）——页面背景体系统一属 main-topbar-transparent-align 范畴，本 spec 迁移页一律不新增私有背景层
- **接受理由**：80% 已完成，剩余为模式化清扫；每波独立验收可回退
- **兜底预案**：每页迁移前备份 bak；波次间 git 隔离；ThemeManage 等重页迁移后真机全功能回归

## Requirements（四型模板 + 门禁 G1-G13 全波适用）

### Requirement: 页面归一化（全部待迁移页）
每页 View 顶栏删除（MainTopBarView Mode.SUB 引用移除）、View 内容区（RecyclerView/Preference/自造卡）替换为四型模板对应组件族、XML 布局清理为 composeHost 单容器、自造成分按"页面内部组件统一表"清零。

#### Scenario: 应用主题页迁移后
- **WHEN** 打开应用主题页
- **THEN** 顶栏为统一组件（透壁纸语义不变），主题卡片列表为 Compose 渲染，ViewBinding 仅剩 composeHost

### Requirement: C-none 页重写（2 页）
CacheManageActivity / CoverCollectionDetailActivity 以 composeHost + AppManagementScaffold 模板重写，交互功能（多选/排序/清理/收藏浏览）100% 保留。

#### Scenario: 缓存管理迁移后功能等价
- **WHEN** 缓存管理页执行多选、排序、清理
- **THEN** 全部操作可用且结果与迁移前一致（数据零丢失）

### Requirement: MyFragment 本体纯化
View 壳（fragment_my_config）+ View 顶栏 → Compose 壳；MySettingsData 路由逻辑零改动。

#### Scenario: 我的 Tab 入口回归
- **WHEN** 我的 Tab 全部入口逐一点击
- **THEN** 21+ 跳转全部正常（路由零回归）

### Requirement: Mode.SUB 消亡联动
每页迁移时 MainTopBarView 对应 SUB 引用删除；全部完成后 MainTopBarView 仅剩主 Tab 消费（与 subpage-topbar-unify 二期三期衔接）。

### Requirement: 孤儿/死代码治理（7 项）
随 W3 波次：ThemeEditorDialogFragment、DiscoveryConfigFragment、SubscriptionConfigFragment 死代码删除；fileManage 死分支路由删除；AdvancedTitleManageActivity 纳入顶栏统一；CrashLogsDialog/ReadRecordComponentConfigDialog 登记（主界面域）。

## Scenarios（验证总纲）
- L1：每波编译通过 + Grep 无 android.util.Log 残留
- L2：每波真机逐页验证（入口可达 + 顶栏统一组件 + 功能等价）
- L3：全域完成后回归：我的 Tab 全入口点击 + 深浅主题 + 全局壁纸开关 + 顶栏包切换

---

## 迁移强制门禁（编号 MC-1..13，展开自 architecture.md 三条铁律+Checklist 0-8；避免与 migration-registry 既有 G1-G11 编号冲突）

| 编号 | 条款 | 迁移动作 |
|------|------|---------|
| MC-1 | 禁硬编码色（Color(0xFF...)/BLACK/WHITE/R.color.md_*） | 迁移页清零自造色值 |
| MC-2 | 取色唯一基线：页面根=palette.settings.page、卡片/行=settings.row；禁 colorScheme.surface 系页面级取色 | 自造取色替换 |
| MC-3 | 禁自造组件（顶栏自绘 Row/自绘菜单/XML 弹框/M3 默认卡片均违例） | 自造组件替换（见组件统一表） |
| MC-4 | 顶栏三基线；禁 M3 TopAppBar/原生 Toolbar | 顶栏统一组件（一期已定） |
| MC-5 | 顶栏色单源 resolvePageBarColor(WithAlpha)+contrastOn | 已就位，迁移页直接消费 |
| MC-6 | 菜单单基线 ModernActionPopup/AppDropdownMenu；禁新建系统溢出 | 迁移页菜单替换 |
| MC-7 | 弹框基线 ComposeDialogFragment+AppDialogFrame；禁 BaseDialogFragment/alert{} DSL | alert{} 违例清零（NavigationBarManage×2 等） |
| MC-8 | 卡片/列表基线：设置族 A（appSettingPanelBackground+RowDecoration）/管理族 B（AppManagementCard/ListRow） | 自造卡替换（AppearanceKit 自造卡等） |
| MC-9 | 开关一律 LegadoMiuixSwitch；裸 Switch 仅白名单 | 自绘开关行替换（ThemeManage switch row） |
| MC-10 | 图标语义：onClick 真实挂载、禁静默收拢、禁硬编码 tint | 迁移时逐图标核查 |
| MC-11 | 输入弹框一律 showComposeTextInputDialog | 迁移页输入框替换 |
| MC-12 | manageBgAlpha 顶栏族全局生效（六验裁决：全站半透明一致）；弹框透明度走 dialogAlpha | 迁移页遵守 |
| MC-13 | 同屏一致+登记：新页与同类既有页视觉一致，完成后同步 ui-standards+migration-registry | 每波收尾动作 |

## 页面内部组件统一表（10 页自造成分清零清单）

| 页面 | 必替换项（✗ 自造 → 基线） | 严重度 |
|------|--------------------------|--------|
| ThemeManageActivity | ThemePackageTabs 自造 tabs→统一 Tab 组件；自绘 View switch row→LegadoMiuixSwitch；AlertDialog+ViewBinding 编辑大弹框→AppDialogFrame；alert{}(:1201)→showCompose 系；第三方 ColorPickerDialog→优化版取色器 | 高 |
| NavigationBarManageActivity | alert{} ×2（L337/L464）→showCompose 系 | 高 |
| AppearanceKitActivity | 自造 AppearanceKitCard→AppManagementCard | 中 |
| AppearanceKitEditActivity | 自造 SettingPanel→appSettingPanel 基线；自绘 Save/Delete Button→统一按钮；M3 OutlinedTextField→统一输入 | 中 |
| AboutActivity | 壳层 llAbout 自绘圆角卡→去壳（内容已是 ComposeSettingFragment） | 中 |
| CacheManageActivity | 全页重写：ItemCacheManageBookBinding→LazyColumn+AppManagementListRow；tvEmpty 空状态→统一空状态组件 | 高（重写） |
| CoverCollectionDetailActivity | UiCorner 自绘卡→AppManagementCard；View Grid→LazyVerticalGrid | 高（重写） |
| RssSearchActivity | ItemRssSearchBinding→LazyColumn；补空结果空状态组件（替换弹窗引导） | 中 |
| TopBarManageActivity | 无自造（AppPackageManageScreen 样板） | — |
| ShareNoteTemplateManageActivity | 无自造（样板页，作为迁移参照） | — |

## 主题配置验证矩阵（每波 L3 必测组合）

| 配置项 | 取值 | 读取入口 | 验证要求 |
|--------|------|---------|---------|
| 深浅主题 | 日/夜/跟随系统/E-Ink | AppConfig.themeMode/isNightTheme | 迁移页双模式截图对比 |
| 颜色主题 | ThemeStore 色槽（primary/accent/backgroundColor 等） | ThemeUiPalette/rememberAppSettingPalette | 换色实时跟随 |
| 顶栏包 | style default/regular × wallpaper × backgroundColor | TopBarConfig.currentConfig | 三种包形态顶栏正确 |
| 全局背景图 | bgImage/bgImageN（**分日夜双键**） | decorView 铺设（BaseActivity.upBackgroundImage） | 有图/无图两态透明正确 |
| 管理页透明度 | manageBgAlpha 0-100 | AppConfig.manageBgAlphaFraction | 半透明/实色两态 |
| 沉浸开关 | immersiveManageBar bool | TopBarConfig 决策链第二级 | 开关两态 |
| 字体缩放 | fontScale/fontScaleN（**分日夜双键**） | ThemeRuntimeKeys.fontScale | 放大后文字不截断 |

**日夜分键约束**：带昼夜切换 Tab 的迁移页（TopBar/NavigationBar/ThemeManage），顶栏配置必须按 isNight 维度取 `currentConfig(context, isNight)`，禁止只取单模式缓存。

---

## Delta 2026-09-07: 顶栏 3→1 组件归一（W1 验收通过后追加，用户裁决"通过（推荐）"）

> 背景：W1 三页验证了 `installGlassTopBar` 运行时替换模式可行；一期"保留三基线"为过渡态结论（回归面+管理族耦合+GlassTopAppBar 缺双行插槽三卡点），本 Delta 声明终态与消亡路线，卡点随波次逐一拆除。与 subpage-topbar-unify 二期 L177-179 的 3→1 分期路线衔接并收编入本 spec 波次。

### MODIFIED Requirements

### Requirement: MC-4 顶栏基线终态（替换原"三基线"表述）
过渡期维持三基线；W6 收官后全站子页面唯一顶栏组件 = GlassTopAppBar。MainTopBarView 仅剩主界面 4 Tab 消费（Mode.MAIN，筛选栏 chip 承载，**不在本 spec 范围**）；AppManagementTopBar 消灭（委托 GlassTopAppBar）。

#### Scenario: W6 收官后顶栏清点
- **WHEN** 全域迁移完成，Grep MainTopBarView / AppManagementTopBar
- **THEN** MainTopBarView 仅剩 Mode.MAIN 主 Tab 消费（Mode.SUB 枚举与 22 页引用清零）；AppManagementTopBar 定义删除（脚手架内部委托 GlassTopAppBar）

### ADDED Requirements

### Requirement: GlassTopAppBar 插槽扩展（归一技术前置，W6 执行）
为承接管理族形态，GlassTopAppBar 新增：①`bottomSlot: (@Composable () -> Unit)?` 双行第二行承载（搜索框内嵌/筛选条）②高度档参数化（compact 48dp / 默认 M3 64dp）③选择态联动参数（selectionActive: Boolean 等价语义）。不改变既有 66 处消费点默认行为（新参数全部带默认值）。

#### Scenario: 插槽扩展零回归
- **WHEN** 插槽扩展合入且未改任何调用点
- **THEN** 既有 66 文件 167 处消费点视觉与行为不变（编译 + 抽样 L2）

### Requirement: AppManagementTopBar 委托收官（3→2→1）
AppManagementScaffold 内置顶栏改为组合 GlassTopAppBar（消费 compact 档+bottomSlot+选择态参数），保留管理族视觉等价（48dp 紧凑/搜索框内嵌/选择态联动/Action danger-tint 语义）；完成后删除 AppManagementTopBar 独立定义。

#### Scenario: 管理族视觉等价
- **WHEN** 书源管理页（AppManagementScaffold 消费页）委托后打开
- **THEN** 顶栏 48dp+搜索框+选择态视觉与委托前等价，多选/搜索/菜单功能等价（L2）

### Requirement: MainTopBarView Mode.SUB 22 页随波次消亡（3→1 主路径）
维持既有 Mode.SUB 消亡联动 Requirement，按两个口径绑定波次：**口径 A（共用容器 22 页，tasks 0.3 映射表）**：W1 3 页（已完成）/W2 About/W3 4 页/W5 2 页（BookInfoManage/BubbleManage）/W6 3 页/跨域 10 页随 master-track B2/B3/B4-c；**口径 B（W5 穷举批 17 页，tasks 5.1-5.3）**：规则族 6+Ai 族 5+容器管理族 6 等非共用容器页，迁移时各自删除本页 View 顶栏。每页迁移即删该页 SUB 引用；tasks 7.2 全域清零确认为本 Delta 的终态验收点。

#### Scenario: 波次页顶栏消亡
- **WHEN** 任一 View 宿主页完成迁移
- **THEN** 该页 MainTopBarView Mode.SUB 引用删除，顶栏由 GlassTopAppBar（installGlassTopBar 运行时替换或 composeHost 内嵌）承载，透壁纸语义不变
