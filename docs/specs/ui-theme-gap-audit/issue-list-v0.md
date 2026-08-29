# UI 主题管理缺口 问题清单 v0

> 阶段 1 静态审计汇总（2026-08-26）。判据：C1 硬编码颜色(Kotlin) / C2 硬编码颜色(XML) / C3 硬编码圆角 / C4 硬编码字号 / C5 误取色源 / C6 不响应主题；管理面 M2/M6/M7 专项。
> 每条含：源码定位 → 影响 → 修复方案 → 优先级 P0(全局联动/观感割裂) / P1(单页/单族) / P2(细节)。
> 数据来源：判据 Grep 扫描 + 4 个核验子代理报告（圆角/字号/联动/布局色）。

## P0 — 全局联动失效 / 风格割裂（建议一次修复优先清空）

### G1 [C4] 字号体系未收敛（全局）
- **现状**：`fontSize = N.sp` 硬编码 **678 处 / 96 文件**（合规走 `MaterialTheme.typography` 仅 199 处/64 文件）。阈值集中在 10/11/12/13/14/15/16/17/18/20sp 离散点，隐含"隐性刻度表"未抽象。
- **重灾区**：`ui/config/`（AI 配置 25 文件：AiProviderEditScreen、AiProviderManageActivity、AiImageProviderManageScreen、AppearanceKitActivity…）、`ui/book/read/`（ReadAloudPlayerPanel 54、SpeakEngineDialog 24、SpeakerGroupManageDialog 26…）、`ui/main/`（AiChatScreen 20、DiscoverySuiteManageActivity 22…）、`ui/about/ReadRecordOverviewCard.kt`(16)。
- **影响**：主题设置改"字号缩放"（`fontScale`/`fontScaleN`）无法对硬编码字号全局生效 → 设置项半失效（P0 联动缺口）。
- **修复方案**：①在 `theme/LegadoTheme.kt` 收敛 10~20sp 为具名字号 token（对齐 `res/values/dimens.xml` text_10sp~text_36sp 刻度表）；②全量 678 处替换为 `MaterialTheme.typography.*` 或刻度引用；③按功能域分批（config→read→main→about→其余），编译+VL 对账 fontScale 生效面。
- **优先级**：P0。

### G2 [C3] 圆角 token 未覆盖（全局）
- **现状**：`RoundedCornerShape(N.dp)` 直接硬编码 **47 处**（84 文件中 198 处已走 `style.*`/palette/dialogStyle，72 处显式 `AppShapes.*`）。特殊语义：`50`(圆形)、`999.dp`(胶囊)、`0.dp`(直角) 未抽语义 token。
- **重灾区**：`ui/main/bookshelf/BookshelfConfigDialog.kt`(890/1020/1025/1073 圆形)、`ui/book/toc/TocComposeScreen.kt`(545/594/626/734)、`ui/config/AppearanceKitActivity.kt`(570-763 六处含 999 胶囊)、`ui/config/ThemeManageActivity.kt`(2483/2538~2582)、`ui/main/ai/compose/AiChatScreen.kt`(851/1106/1168)、朗读域（ReadAloudSystemFloatingWindow 14dp、BgTextConfigDialog 5dp、SpeakerGroupManageDialog 0dp）等。
- **影响**：主题"圆角倍率"（`uiCornerScale`/AppShapes）对这些组件不生效 → 圆角风格割裂。
- **修复方案**：①`AppShapes.kt` 增补语义 token（Circle/Capsule/Corner0 等）；②47 处替换；③配置管理页（AppearanceKit/ThemeManage）优先。
- **优先级**：P0。

### G3 [C2] 视频影像 UI 硬编码颜色（全局样式割裂，呼应 video-player-theme-unify）
- **现状**：`res/layout/fragment_video.xml`（根背景 #000000 + 9 处 #FFFFFF tint/文字）、`video_layout_controller.xml`（遮罩 #99000000 + 白字）、`video_layout_controller_full.xml`（9 处白字）、`bg_video_ctrl_btn.xml`（#66757575/#33757575）、`bottom_progress_buffer.xml`（三段黑白）、`video_seek_*.xml`（黑白）、`activity_audio_play.xml`（#90000000）等 **20+ 处**纯黑/白/灰，不随主题。
- **影响**：改主色/夜间主题时视频播放器控制层固定黑白灰，与全局观感割裂；深色悬浮层与明色主题冲突。
- **修复方案**：按 `video-player-theme-unify` 设计执行：控制条/进度条/按钮底色接入 `ThemeStore` + `UiCorner`；深色悬浮层改为主题动态色；`fragment_video` 根背景与文字 tint 取主题色。
- **优先级**：P0（本条与 video-player-theme-unify 规格合并实施）。

## P1 — 单页 / 单族风格过期或联动盲区

### G4 [C6] 调试工具 7 页主题联动盲区
- **定位**：`ui/debug/{DebugTools,EncodeTools,HttpDebug,CurlTest,PingTest,RegexTest,TimestampConvert}Activity` 均 `AppCompatActivity` 直连，不订阅 RECREATE（BaseActivity 之外），仅靠 `initLegadoComposeTheme()`+`LegadoThemeWithBackground`。
- **影响**：改色时系统栏/窗口背景热切换盲区；不确定 Compose 根是否全部经 `LegadoTheme`（读 version）。
- **修复**：抽公共基类（继承 BaseActivity 或统一主题初始化）+ 核验 Compose 根包裹 `LegadoTheme`。
- **优先级**：P1。

### G5 [C6] View 型弹窗未包 LegadoTheme（改色不刷新盲区）
- **定位**：`AdvancedTitleConfigDialog`(DialogFragment)、`PageKeyDialog`(ComponentDialog)、`BgTextConfigDialog`、`HttpTtsEditDialog`、`SpeakEngineDialog`、`SpeakerGroupManageDialog`（均 BaseDialogFragment）、`SelectionWebSearchDialog`(BottomSheetDialogFragment)、`ContentEditDialog`、`EffectiveReplacesDialog` —— 未见包裹 `LegadoTheme`；View 绑定型 `MoreConfigDialog`(BasePrefDialogFragment)。
- **影响**：这些弹窗既不订阅 RECREATE 又不读 `ThemeSync.version`，改色后不刷新（弹框族观感漂移）。
- **修复**：包 `LegadoTheme`（读 version）或迁移 `ComposeDialogFragment` 家族。
- **优先级**：P1。

### G6 [M6] BaseDialogFragment 旧 View 弹框残留（弹框多风格主战场）
- **定位（~20 个）**：`AppLogDialog`、`CrashLogsDialog`、`AddToBookshelfDialog`、`ChangeThemeDialog`、`DictDialog`、`OpenUrlConfirmDialog`、`VerificationCodeDialog`、`SourcePickerDialog`、`TxtTocRuleDialog`、`TxtTocRuleEditDialog`、`ChangeCoverDialog`、`ServersDialog`、`ServerConfigDialog`、`ChangeBookSourceDialog`、`ChangeChapterSourceDialog`、`ChangeSourceDialogTheme`、`WaitDialog`、`VariableDialog`、`UrlOptionDialog`、`PhotoDialog`、`CodeDialog`、`BottomWebViewDialog`、`NumberPickerDialog` 等（`dialog_*` XML 43 个为承载布局）。
- **影响**：与 ComposeDialog 家族并存的旧 View 弹框 → 圆角/宽度/取色/底部操作区完全另一套风格。
- **修复**：按 dialog-shell.md 基线迁移 ComposeDialogFragment 家族 + `AppDialogFrame/AppDialogStyle`；保留 `WaitDialog`/`CodeDialog` 评估（重用于多页）。
- **优先级**：P1。

### G7 [M7] 三点菜单双风格（ModernActionPopup vs PopupMenu）
- **现状**：新族 `ModernActionPopup`：RssFragment/ExploreFragment/BaseBookshelfFragment/SearchActivity/ThemeManage/TopBarManage/NavigationBarManage/SettingSpecScreen；**旧 `PopupMenu` 残留**：`ChangeChapterSourceAdapter`、`ChangeBookSourceAdapter`、`SelectActionBar`、`RssAdapter`、`VideoFragment`(×2)、`ExploreAdapter`、`BookSourceEditActivity`、`BookSourceDebugActivity`（共 9 处）。
- **影响**：右上角/条目长按菜单呈现两套风格，改主题后旧款不跟随。
- **修复**：9 处 PopupMenu → `ModernActionPopup` 展望（保留适配器内轻量场景评估）。
- **优先级**：P1。

### G8 [M2] 书源编辑/调试页头部仍旧 TitleBar+PopupMenu
- **定位**：`BookSourceEditActivity`、`BookSourceDebugActivity` 用 `binding.titleBar.moreButton`+`PopupMenu`（subpage-topbar-unify 未覆盖；BookSourceEditActivity 正在 Compose 化 WIP）。
- **影响**：书源编辑/调试头部不随"顶栏管理/主题设置"（bugfix ③ 之外的单页缺口）。
- **修复**：迁移 `MainTopBarView(Mode.SUB)`（含 action 插槽承载原菜单）或至少 `topBarColorManaged` 局部读配色。
- **优先级**：P1。

### G9 [C1] Kotlin 硬编码颜色集中（阅读/朗读域为主）
- **定位**：`Color(0x` 35 处/14 文件；`Color.(Black|White|...)` 81 处/22 文件。集中：`ReadAloudPlayerPanel`(20)、`SpeakerGroupManageDialog`(11)、`SpeakEngineDialog`(12)、`ClickActionConfigDialog`(9)、`BookInfoComposeRoute`(7)、`ReadAloudSystemFloatingWindow`(5)、`BookCharacterComposeScreens`(36)、`BgTextConfigDialog`(7)、`DiscoverySuiteHomeScreen`(20)。
- **影响**：跟随主题失效（朗读面板/对话框为高概率孤儿样式）。
- **修复**：改 `MaterialTheme.colorScheme`/`ThemeStore`；朗读域优先（与 G1/G2 同批）。
- **优先级**：P1。

## P2 — 细节偏差

### G10 [C2] 其余布局硬编码色
- **定位**：`activity_image_crop.xml`(#111111 遮罩)、`widget_read_goal.xml`/`widget_read_rank.xml`（黑字透明度 #DE000000/#99000000）、`activity_main.xml`(#66000000)、`bg_image_crop_toolbar`/`bg_rotate_toolbar`/`bg_overlay_button`、`item_image_canvas.xml`(底部叠加条 #80000000/#FFFFFF)。
- **修复**：主题 token 化；阅读统计卡文字色接入主题文字色。
- **优先级**：P2。

### G11 [C2] 图标品牌色/几何色（低优先）
- **定位**：`ic_bottom_*` #2f45a6（品牌蓝）、大量 `ic_*` 灰系 #595757 / 黑 / 白（视频用白）。
- **修复**：图标矢量色属固有属性；确认应用 `TintHelper` 时除外。仅登记。
- **优先级**：P2。

## 汇总

| 优先级 | 条数 | 覆盖 | 建议批次 |
|--------|------|------|---------|
| P0 | 3（G1 字号/G2 圆角/G3 视频色） | 全局联动 + 样式割裂 | 修复轮第一批 |
| P1 | 6（G4-G9） | 单页/单族 + 弹框家族 + 菜单家族 | 修复轮第二批 |
| P2 | 2（G10/G11） | 细节 | 修复轮第三批 |

> 注：所有条目的"修复方案"为方向级，实施时以 `frontend-ui-standards.md` 为强制基线 + 逐条源码核验细化；静态与运行时对账（AD-03）在测试轮（R1）后合并为 v1，补充 VL 发现的运行时缺口。