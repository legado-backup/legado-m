# rss-classic-layout-align 实施任务

> 权威设计：`docs/specs/rss-classic-layout-align/design.md`（AD-01~04）
> 格式：`- [ ] X.Y`，完成勾选；行号基准 2026-08-29 源码，实施时以精读复核为准。

## §0 权威顺序声明

- [ ] 0.1 本任务清单基于**已实核定案**（核查报告已定案，无待裁决项）：P1→S1、P2/P3/P5→S2、P4→S3、P6→S4、P7→S5，方案与 AD-01~04 已锁定，**直接按 §1 → §2 顺序实施，禁止重开方案讨论**；若 §1 精读与 design.md 锚点冲突（行号漂移/结构变化），以精读结果修正锚点并在本节登记偏差，不改设计决策。
- [ ] 0.2 实施顺序固定：§1 精读 → 2.1(S1) → 2.2(S3) → 2.3(S2) → 2.4(S4) → 2.5(S5) → §3 验证 → §4 收尾；2.3 依赖 2.1 的 margin state 与 2.2 的弹框字段结论，禁止乱序。

## §1 源码精读（实施前置，逐项复核 design.md 锚点）

- [ ] 1.1 `FilletImageView.kt` API 核验：确认 radius 仅 init 从 styleable 读取（:26-62）、四角字段 `private var`、无运行时 setter → 确认 2.4.1 最小扩展方案（公开 setter）可行；同时确认 `UiCorner.actionRadius(context)` 返回 px（UiCorner.kt:44-46，`getDimension × UiCorner.scale()`），与 `getDimensionPixelOffset` 同单位。
- [ ] 1.2 `SourceFolderConfigDialog.kt` 选项数组结构核验：确认 layouts（:243-251）/sorts（:252-259）当前 `mapIndexed` 隐式赋值、`SourceFolderConfigValues`（:90-96）字段集、`applyConfig`（:203-235）变更聚合与 `create`（:286-303）初始值装配路径；确认 `SourceFolderConfigDialog.create` 全项目唯一调用点为 RssFragment:1167（isBookSource=false）。
- [ ] 1.3 `RssAdapter.kt` ViewHolder 核验：确认 `convert`（:33-50）绑定 tvName/ivIcon、`registerListener`（:52-65）长按菜单锚点；确认 item_rss.xml 的另一消费点为 RssFragment 头部固定卡片（:1044-1055，ItemRssBinding 直接 inflate），两处均需应用主题圆角 + 标题字体。
- [ ] 1.4 参照与旁证核验：BookshelfScreen.kt:279-285（margin 全驱动写法）、RssFragment.kt:182-183（folderComposeItems/Covers `mutableStateOf` 范式，margin state 照此）、RssFragment.kt:291-296（observeEvent 范式）、SourceFolderAdapter.kt:77-78（View 版同款语义反置，确认 2.5 删双写后不可达）、strings.xml 缺 `layout_auto`/`source_sort_6`。

## §2 核心实施

### 2.1 S1 margin 参数化（P1）

- [ ] 2.1.1 `SourceFolderComposeGrid` 新增 `margin: Int` 参数；`val m = margin.coerceAtLeast(2).dp`；contentPadding 改 `PaddingValues(start=m, top=m, end=m, bottom=m)`、horizontal/verticalArrangement 改 `spacedBy(m)`（逐行对齐 BookshelfScreen.kt:279-285，删除 12/8/12/16 硬编码）。
- [ ] 2.1.2 `RssFragment` 新增 `private var folderComposeMargin by mutableStateOf(AppConfig.sourceMargin)`（与 folderComposeItems 同款，:182 旁）；`initFolderComposeView()` 传 `margin = folderComposeMargin`。
- [ ] 2.1.3 `showFolderConfig()` 的 `onConfigChanged` 回调内同步 `folderComposeMargin = AppConfig.sourceMargin`（保证滑条应用后网格实时重组，无需重进页面）。

### 2.2 S3 showBookname 语义修正 + 跨页监听（P4）

- [ ] 2.2.1 SourceFolderComposeGrid.kt:87 `if (showBookname != 1)` → `if (showBookname == 1)`（K7 语义 1=显示分组名，对齐书架 BookshelfScreen.kt:311-312）。
- [ ] 2.2.2 弹框补「书名显示」tile：`显示(1)/隐藏(0)` 两项；初始值归一 `if (AppConfig.showBookname == 1) 1 else 0`（存量 2=遮罩为书架专属，非 1 按 0 处理，**禁止写回 2**）；applyConfig 写 `AppConfig.showBookname`（写入前同规则归一）。
- [ ] 2.2.3 `RssFragment.onFragmentCreated` 新增：`observeEvent<String>(EventBus.BOOKSHELF_STRUCTURE_CHANGED) { applyView(); if (isShowingFolder) upFolderView() }`（复用既有事件零新增；参照 :291 NOTIFY_MAIN 观察范式；applyView 文件夹态内部已调 upFolderView，显式再调为幂等双保险）。

### 2.3 S2 弹框补齐（P2/P3/P5，Compose 选项数组写法互斥注意）

- [ ] 2.3.1 layouts 清理为 6 项并改**显式 value 映射**（禁 mapIndexed）：`自动(0)`、`Grid2(2)`…`Grid6(6)`；新增字符串 `layout_auto`（values "Auto" + values-zh "自动"）；初始值 `sourceLayout` 归一：1（存量紧凑）视同 0 匹配选项；`effectiveSpanCount()`（RssFragment:1083-1087）已有 0/1 回退自适应，无需改动。
- [ ] 2.3.2 sorts 补第 7 项：新增字符串 `source_sort_6`（values "By Update Time" + values-zh "更新时间"），显式 value=6；`sortSources()` 已有 `6 -> sortedByDescending { lastUpdateTime }`（RssFragment:1359）分支，排序逻辑零改动。
- [ ] 2.3.3 排序区新增升降序 tile：`升序(1)/降序(0)` 两 chip（复用 SourceFolderSelectItem 机制）；`SourceFolderConfigValues` 增加 `sortAscending: Boolean` 字段，UI 值 1/0 与 Boolean 互转；仅 `isBookSource == false` 时渲染该 tile。
- [ ] 2.3.4 `applyConfig()` 补写：`AppConfig.rssSortAscending = values.sortAscending`（仅 !isBookSource 且值变更时置 changed）；书名显示写入（见 2.2.2）；沿用现有 changed 聚合统一触发 `onConfigChanged`；`create()` 初始值装配同步补 `sortAscending = AppConfig.rssSortAscending` 与书名显示归一初值。

### 2.4 S4 item_rss 视效对齐（P6）

- [ ] 2.4.1 `FilletImageView` 最小扩展：新增公开函数（如 `updateCornerRadius(radiusPx: Int)`）——四角字段统一赋值 + `invalidate()`；不改 init/styleable 逻辑，不动其它使用方。
- [ ] 2.4.2 item_rss.xml：删根布局 `android:padding="16dp"`（间距单源交 GridSpacingItemDecoration）；删 iv_icon `app:radius="12dp"`（改运行时设置）；tv_name `android:lines="2"` → `android:minLines="2"`；其余（50dp 1:1、textColor primaryText、10dp marginTop）保持不动。
- [ ] 2.4.3 `RssAdapter.convert`（:39-49）内追加：`binding.tvName.applyUiTitleTypeface(binding.root.context)` + `ivIcon.updateCornerRadius(UiCorner.actionRadius(context).roundToInt())`；RssFragment 头部卡片（:1047-1054）同步追加两行（requireContext()）。
- [ ] 2.4.4 登记视效差量：tvName 应用后标题色切换为 titleTextColor（applyUiTitleTypeface 内建行为）、圆角随 uiCornerScale 联动，均为对齐预期。

### 2.5 S5 死代码清理（P7）

- [ ] 2.5.1 删除 `RssFragment.applyFolderView()`（:1071-1080 含注释；精读复核全项目无调用点）。
- [ ] 2.5.2 删除 `upFolderView()` 内 `folderAdapter.setItems(...)`（:1244）与 `folderAdapter.upCovers(...)`（:1254）双写；FolderItem 类保留（ComposeGrid 数据模型）。
- [ ] 2.5.3 Grep `folderAdapter` 全量引用：若仅剩字段声明则连同声明与相关 import 一并清理（以编译器 unused 告警为准）；`SourceFolderAdapter` 类保留（`calculateSpanCount/spacingPx` 仍被 applyListView/effectiveSpanCount 引用）。
- [ ] 2.5.4 SourceFolderAdapter.kt:77-78 同款 `showBookname != 1` 语义反置**登记不修**（删除双写后不可达），写入本 spec 目录 issues 登记（README 或 issues-found，防后续误判为回归）。

## §3 验证

### 3.1 编译门禁

- [ ] 3.1.1 `./gradlew compileAppDebugKotlin` 通过，零报错；Grep `android.util.Log.d|android.util.Log.e` 确认无残留调试日志（统一走 AppLog）。
- [ ] 3.1.2 确认产物为测试包基线（后续打包走 `build-legado.bat`，构建后执行 `stop-daemons.bat` 清场，见 4.3）。

### 3.2 模拟器 L2（真机/模拟器验证，禁止只改码不测；入口 `ai_tests/venv/Scripts/python.exe`）

- [ ] 3.2.1 margin 实时生效：文件夹视图 → 弹框拖动 margin 滑条（0→60）→ 应用 → Compose 网格四向间距/横向/纵向间距实时变化，无需重进页面；与书架文件夹同 margin 值观感一致。
- [ ] 3.2.2 排序生效：弹框排序选「更新时间」（第 7 项可达）→ 列表按更新时间排序；切换升序/降序 → 顺序翻转；重进订阅页配置保持。
- [ ] 3.2.3 跨页同步：书架侧做结构变更（改书名/分组调整）→ 切回订阅经典文件夹视图 → 分组名/封面同步刷新（STRUCTURE 事件链路）；连续触发多次无重复堆积（幂等）。
- [ ] 3.2.4 源卡片视效：列表视图源卡片标题应用标题字体（与顶栏字重一致）、圆角为主题圆角（非固定 12dp，切换 uiCornerScale 联动）、item 无 16dp padding 与 decoration 叠加（间距不异常变宽）；头部「订阅源」入口卡片同效。
- [ ] 3.2.5 弹框选项回归：视图模式恰 6 项（自动/Grid2-6，无「列表/紧凑列表」残留）；存量 `sourceLayout=1` 环境打开弹框显示「自动」且不异常；书名显示两项（显示→分组名出现，隐藏→仅封面）；应用后立即生效；modern 订阅形态回归无变化；书源管理页（未走此弹框）无感知。
- [ ] 3.2.6 AOAdapt 日志预留：关键路径（弹框 applyConfig 写入、STRUCTURE 事件回调、margin 重组）按 `AppLog.putDebugWithTag("RssLayoutAlign", ...)` 预留调试锚点，真机问题可凭 logcat 定位（tag 过滤，head_limit≤20）。

## §4 收尾

- [ ] 4.1 updateLog：编译/交付前基于 `git diff` 逐文件对照，在 `app/src/main/assets/updateLog.md` 的 `## cronet版本:` 之后、已有条目之前追加用户语言条目（文件夹间距实时可调、排序升降序+更新时间、书名显示开关、书架结构变更同步订阅、源卡片字体圆角对齐主题、弹框选项精简），禁漏项禁合并旧条目。
- [ ] 4.2 文档同步：本 spec 目录补 `how-to.md` 经验沉淀（Compose 网格 margin 参数化对齐书架写法、Compose 弹框选项数组显式 value 映射防错位、复用结构事件做跨页同步）；检查 issues-found/INDEX/ai_memory_main 是否需追加本任务结论；`docs/specs/rss-classic-layout-align/` 内登记 2.5.4 观察项。
- [ ] 4.3 daemon 清理：若实施中走直接 `gradlew` 命令或 IDE 构建，结束后必须执行 `stop-daemons.bat` 清场（Gradle + Kotlin daemon 残留防内存打爆）。
