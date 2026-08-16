# Forks 深度学习清单（学了什么 / 怎么学）

> 本卷回答 DESIGN-MD 审查中"学习了哪些开源项目、学习了他们什么"。全部为**逐源码核实**（附真实路径佐证），可移植性评级 1-5★。

## 1. 书架实现（Compose 先行派）

### 学 HapeLee / 325506：`FastScrollLazyVerticalGrid` 书架
- 源码：`ui/main/bookshelf/BookshelfScreen.kt`（HapeLee 339 Compose 文件）；`FastScrollLazyVerticalGrid`（自研封装 `widget/components/lazylist/`）= `LazyVerticalGrid` + 右侧快速滚动条。
- 列数：`lambda if (mode==0) list else grid` 用 `GridCells.Fixed(columns)`；**列表模式 = 高列数网格 + 间距 0**（书架保留 Grid 语义）。
- 间距：grid 8.dp / list 0.dp；contentPadding 底部按 raised sheet 模式留 120dp（`adaptiveContentPaddingBookshelf`）。
- 封面：`CoilBookCover.kt` 默认圆角 **4.dp**（非 18）；书架项 `aspectRatio(5/7)`+`clip(RoundedCornerShape(4.dp))`。
- 角标：overlay 叠层——TopEnd 未读（受 `showBadgeDot`，非红数字）、BottomStart 源标签、BottomCenter 更新进度条；`animateEnterExit`。
- gridStyle=1 标题压封面下缘 + `Brush.verticalGradient(Transparent→Black)`。
- 拖拽排序：`rememberReorderableLazyGridState`（199 行内完全可移植）。

**对我们的决策**：保留「默认 Grid 3 列」设计，但**封面圆角从 18dp 降到 12dp（封面本体），外层卡片才是 18dp**——区分"图片圆角 vs 卡片圆角"双层，避免图片被圆角吃掉太狠。未读用 TopEnd 小圆点（非 HapeLee 的 TextCard 数字，对齐 DESIGN-MD 禁红数字）。

### 学自：legadoT / dandanmax：View 书架底线
- legadoT：`BookshelfFragment2` 列数 = `bookshelfLayout + 2`（数值越大列越多）——不需要 Compose 也能三态布局。
- dandanmax：View 双风格 + `BaseBookshelfHeader`；无共享动画。

**决策**：书架 UI 的 Compose 化优先级 = **P1 中高**。若选择保守路线，可先只用 View `GridLayoutManager + ItemDecoration` 复刻同款视觉（成本约为 Compose 的 1/4），读工匠 phase-2 再上 Compose（AD-07）。

## 2. 书架 → 阅读器过渡（Hero so laughing）

### 学自 HapeLee / 325506：SharedTransitionLayout
- 关键实现：`BookCoverSharedElement.kt` → `key = "book-cover:$bookUrl"`；圆角过渡 `transition.animateFloat("book-cover-corner-radius")`（缓存上限 256 key）。
- View 侧：`MaterialContainerTransform`（scrimColor=Transparent）用于 AudioPlay/ReadManga。

### 对我们的取舍
- 目标仓库 `PageView` → `ReadBookPage` 是 View 正文 + Compose 壳。过渡用 **Compose `SharedTransitionLayout` 单点 key** 成本可控；但**默认暂不启用**（读区性能与覆盖安装回归，AD-08），先落"表项圆角 hover 微反馈"，封面 Hero 作为开关选项。

## 3. 阅读器（核心路径，学到最关键）

### 学自 HapeLee：正文 View + 浮层 Compose 的混合范式（决定性证据）
- 正文**不是 Compose**：`ContentTextView`（`AbstractTextView` Canvas + StaticLayout）、`PageView`/`ReadView` FrameLayout、7 种翻页 delegate。
- Compose 壳：`ReadBookScreen + ReadBookController + ReadBookViewModel` 承载**手势与状态**，正文仍是 View。
- **浮层全 Compose**：`ReadBookSheet` sealed interface **37 种**，`activeSheet` 单态互斥，由**一个 `when` 渲染**（不各自弹窗）。
  - `ReaderMoreActionsSheet`：「更多」12 宫格→4 列网格 `HorizontalPager` 每页 8 动作 + 可编辑。
  - `ReaderBookSheet`：目录/信息/书签 三 Tab HorizontalPager + CardTabRow，maxHeight 72%。**这就是"目录/书签 BottomSheet"教科书实现**。
  - `ReadAloudScreen`：全屏播放器式 ModalBottomSheet（`fillMaxSize`, dragHandle=null）。
- 手势：亮度/音量区状态机、pinch 缩放、首帧延迟优化。

### 学 HapeLee：双引擎 ModalBottomSheet
`AppModalBottomSheet` = Miuix WindowBottomSheet + MaterialExpressive **可切换引擎**（maxHeight 80%）。我们已 claim Miuix 较重的依赖，参考其**单实例互斥 + sheet 分层**思想即可：

| 我们的阅读 UI 层级 | 实现 | 参照 |
|---|---|---|
| 顶栏（返回/书名/章节） | 磨砂 Compose 壳 | HapeLee ReadBookXxx |
| 底栏（目录/字号/夜间/更多） | BottomSheet Trigger | 佳面板 |
| 阅读设置面板 | 拉伸 Sheet → 字号/行距/翻页/背景/朗读 | 现状 ReadStyleDialog 改造 |
| 目录/书签/信息 | `ReaderBookSheet` 三 Tab | HapeLee 课本 |
| 高亮/划线 | 色盘 chooser + 下划线族 | youfeng |

### 学 legadoT：无法 Compose 的兜底怎么做
阅读菜单用 View `BottomSheetDialog`（MenuPosition 底部 —— 目标仓目前 ReadMenu 是普通 View 布局），先可做 `动画类 + BottomSheetBehavior` 无碎改造。

## 4. 主题引擎（三派主线）

### 派 A：HapeLee — 14 模式 + Custom 种子（全 M3 响应式）
- `AppThemeMode`：Dynamic(Monet默认)/GR/Lemon/WH/Eink 等 12 preset + Custom + Transparent。
- `ThemeEngine.baseByMode` 12 个 `BaseColorScheme`（light/dark 双套全量）。
- Custom = `MaterialKolor` 从 `seedColor`（`PaletteStyle` × `ColorSpec`）生成。
- 应用方式 `App.kt: infer(build) → MaterialTheme(colorScheme...) 全局下发，**无重建**（唯一一个响应式成功案例）。
- View 兜底：`ui/theme/Theme.kt` 读 `cPrimary/cNPrimary` → TintHelper/ThemeStore 供给未迁移 View。

### 4.2 legadoT — HCT 种子→30 token（非 Compose 动态，★4）
- `lib/theme/M3ColorScheme.kt`：`SchemeContent`（`Hct.fromInt(seed)`) × `MaterialDynamicColors` 逐 token `getArgb(scheme)` → primary/surface/...error 等 25+ 收口。
- **关键**：与目标一模一样的星表「背景锚定中性面」——彩色角色直接 M3 派生，surface/背景族**用用户背景色（ThemeStore.backgroundColor）做 tone 平移**（`色调(deltaVal)` shiftTone）形成 5 级 surfaceContainer 层。这才是「保住用户背景色 → 又 M3」的算法，**比 Target 现有 `lerp(bg, White, 0.04)` 更权威**。
- 落地：`lib/skin/attrs_skin.xml` 声明 `skin_background/skin_textColor...` →`SkinInflaterFactory`（LayoutInflater.Factory2）解析 → resolve(AppColorScheme.current) 一次性上色；切换全靠 `RECREATE`（注释：避免瞬时新旧混态）；E-ink `einkScheme()` 全黑白。

### 4.3 Jiehingro：XML token 换皮（最低风险，双落）
- colors.xml / values-night 共 13 个 md3 token（surface/onSurface/surfaceVariant/surfaceContainerHigh/Highest/outlineVariant/primary/onPrimary/primaryContainer...）+ 语义色全部改别名。
- Base.AppTheme parent = `Theme.MaterialComponents.DayNight.NoActionBar.Bridge`（target 仓现在是 AppCompat——可 bridge）。
- **书箱卡片圆角是 8dp shape**（非 MaterialCardView）——两版都靠 `bg_item_bookshelf_grid.xml` shape，本子0依赖。
- 缺点：只有 baseline 双色、无种子自适应（可接受）。

### 4.3 Suml-1：换肤 zip 一键（可后续做大件但本次不引）
- `ApplicationThemeManager`：`apply/export/importFile/captureCurrent`；zip 含 `application_theme.json(gv)` + `themes/{day,night}/background.jpg` + `topbar/...` + `bottombar/...icons` + `covers/{0..499}.jpg`；校验 2MB manifest / 64MB assets。
- 顶栏 `TopBarConfig`（tagBarColor/cornerScale 0-3）与底栏 `NavigationBarConfig`（layout floating/sidebar + glass/frosted）。

**我们的决策（AD-03/AD-05 深化）**：
- **主路线**：legadoT 的"HCT 种子 + 用户背景锚定中性面"是**最值得学的算法**；但**不在本 spec 引入 MC 动态库**（需 material 1.13.0 restricted API，故 AD-09 用 `Hct 迷你移植 + lerp 基线升级`可达 80% 效果）。
- **同时做**：Jingshiro 式 XML MD3 token 落地（把现有 View 页面的颜色改为 M3 语义 token），零代码、低风险、立刻有 M3 观感。
- **不引**：Suml zip 换肤（工作量大、本项目用户生态不依赖主题包）、Hipe Relize 的 Monet（min 23 动态色 Agregate 受限）。

## 5. 高亮/划线（最省事的"甜点"）

### 学 youfeng：Canvas 手绘五种下划线 + 规则引擎
- 载体：`HighlightStyleSpan`（透传）→ `TextChapterLayout.applyRuleSpans` 正则 `setSpan` → `TextBaseColumn` 携带字段 → `TextLine.drawStyledEnhanced/Visible`。
- 五种样式全部 **Canvas 手绘**（非 Span 重写）：
  - 实线 `canvas.drawLine`
  - 虚线 dash 8dp+gap 5
  - 波浪 `quadTo`（幅3/波长12）
  - 双线 lineSel+间隔3
  - SVG `SvgPathParser` 100×50 坐标系 translate/scale 后 `drawPath`；背景图 `BitmapShader(REPEAT)` LruCache 16MB。
- 规则引擎：`HighlightRuleStore.createDefaultRules` 内置 7 条预置（对话/书名/括号/标题/心理/强调/诗词）+ 代码级；UI 面板 `HighlightRuleConfigDialog` 列表 + `HighlightRuleEditDialog`（选色器 ColorPickerDialog）+ PresetRule 从底部面板弹出。

### 对我们的复制路径（★可行，前景 E 期）
- Target 现状已有 SolidUnderlineSpan 族（Dash/Double/Wave 等 6 个）—— youfeng 的**完整** Canvas pipeline（TextLine 重构）工作量大且与现状排版紧耦合，本 spec 只落：①高亮选色面板升级（BottomSheet 化，两行 6 色）②高亮样式可配置开关（沿用现状 span）。完整 Canvas 五线改可不本段范围。

## 6. 用户旅程：（目标仓走查 + fork 对照）目标仓走查 5 个关键 journey（对齐第三子代理审计，实码路径）：
1. **进阅读**：书架→BookInfo→Read 一般 2-3 步（`startActivity` 直读可 1 步选项）。
2. **调字号/亮度/夜间**：阅读底栏「设置」→ReadStyleDialog（当前 1 步 1 弹窗，OK 但改动 Browse Tab）；亮度竖条 `vw_brightness_pos_adjust` 是本仓独有增强，**保留并打磨**。
3. **调目录**：底栏「目录」→TocDialog（现状 1 步弹窗→ 改 `Herlu` 三 Tab Sheet，加进度/书签）。
4. **搜索正文**：阅读浮层 `menu_search`（现状 OK）；书架顶栏全局搜索需要从 My 中的 `书源` 移出一级。
5. **排的书源管理**：现状在「我的」二级（`bookSourceManage`），应补**关键词搜索 + 顶栏入口**，改动 Source item 拥挤（启用/编辑/更多三控件同排）。

完整旅程/状态机图见 design.md §Data Flow/UX。

## 7. 书源 / 订阅源管理页布局（2026-08-11 补证，用户追问后逐源码核验）

> 此前本卷仅在第 6 节写过一句现状观察，**未对 fork 的书源/订阅源管理页做布局深挖**——用户 2026-08-11 追问「有没有认真分析过书架/书源/订阅源布局样式并把学习融会贯通」后补做。以下为逐源码核验结论（真实路径+行号）。

### 7.1 HapeLee 书源管理页（BookSourceScreen，946 行，全 Compose MVI）
- 路径：`app/.../ui/book/source/manage/`（`RouteScreen` = ViewModel+effects 接线层；Screen = 纯 UI 无状态，state+onIntent+effects 三参）。
- **脚手架**：`RuleListScaffold`（公共规则列表壳：标题/副标题[当前分组名 or "全部"]/搜索开关/搜索框/全选反选/批量操作槽/下拉菜单槽/snackbarHost）——这是"书源/替换/订阅源通用列表页"的成熟模板，等价我们 S2 骨架 + 顶栏搜索 + 批量栏。
- **列表**：`FastScrollLazyColumn` + `Arrangement.spacedBy(8.dp)`（contentPadding 底部 +120dp 适配 raised sheet）；**分组头用 domain**（`contentType="domain-header"`，每次 domain 变化插一条 `AppText(titleSmall, primary)`）。
- **条目**：`ReorderableSelectionItem`（可拖拽排序 + 多选 + 开关）：
  - 拖拽条件 `sort==Default && !groupByDomain`；拖完 `dragOrder` 暂存，停拖后与 persisted 对比 diff → `CommitSortOrder`（防无变化提交）。
  - 选中态：`selectedIds.isNotEmpty()` 即进入多选流；左侧 60dp `DraggableSelectionHandler` 滑选覆盖层。
  - trailingAction：编辑按钮 + `BookSourceItemMenu`（登录/搜索/调试/删除/置顶底/探索开关，独立可读菜单）。
- **顶栏**：筛选（AppIcons.Filter → 分组筛 BottomSheet）+ 下拉（分组管理/本地导入/在线导入/域名分组开关 + PillDivider + **排序 7 维**：手动/权重/名称/URL/更新时间/响应时间/启用，末项升降序）。
- **批量操作** 11 项 ActionItem：启用/停用/探索开/探索关/加组/移除组/置顶/置底/**检查选中**/检查源（带参数 BottomSheet）/导出。
- **其余**：删组 TextListInputDialog / GroupManageBottomSheet / 导入 BatchImportDialog（选项：选新源/选更新源/保留原名/保留分组/保留启用/自定源组，语义 selected 勾选）/ 导出 FilePickerSheet（存本地 or 上传）。

### 7.2 HapeLee 订阅源管理页（RssSourceScreen，416 行）
- 同一 `RuleListScaffold` 脚手架（证明两者同构，可共享 S2 骨架）；列表 = `ReorderableSelectionItem`（title=name, subtitle=group, 无 domain 分组头）。
- 批量操作 6 项：启用/停用/加组/移除组/导出/检查选中；下拉菜单：分组管理 + 导入（在线/本地/默认源，二级菜单）+ PillDivider + **筛选**（全部/已启用/已禁用/需登录/未分组 + 各组）。
- 无三视图布局切换——书源与订阅源**都是单列表**。

### 7.3 MoRealm 书源管理页（BookSourceManageScreen，1305 行，最有借鉴价值）
- 路径：`app/src/main/java/com/morealm/app/ui/source/BookSourceManageScreen.kt`。**纯 Compose + StateFlow MVI**（非 RouteScreen 分层，ViewModel 直入 + hiltViewModel）。
- **进出多选**：`selectionMode` + `selectedUrls = rememberSaveable(listSaver)`（旋转/进程死亡保留）；`BackHandler(enabled=selectionMode)` **返回键优先退多选**。
- **顶栏双形态**：正常态 = 排序菜单 + 校验按钮 + 粘贴导入 + 添加 + Overflow（导出全部）；多选态 = 标题"已选 N" + Close 退出 + 全选 + 导出选中 + 删除选中（error 色）。
- **排序**：DropdownMenu 首行「当前：升序（点切降序）」独立条目 + 5 维（`SourceSortKey.entries`）——**点同一维度翻方向、点新维度切 key 保留方向**；当前选中维度 ✓+primary。排序 enum 用 **String key 持久化**（增删枚举安全 fallback，不用 ordinal）。
- **分组模式 Chips**：`GroupModeChips`（FilterChip 单选 + `horizontalScroll`）：不分组/按分组/按域名/按类型 4 选——**比 Legado 原版"文件夹视图"更直接**。分组在排序后执行（搜索→排序→分组，组内天然有序）。
- **可折叠 GroupHeader**（核心可学点）：折叠箭头 + 组名(titleSmall Bold) + **"启用数/总数"徽标** + 三点菜单（全部启用 (N)/全部停用 (N)，数量写进文案）；整行点击切折叠；`collapsedGroups` rememberSaveable + 切换分组模式时清空。
- **SourceItem 卡片化**（可学点）：填满宽 rounded `Box` + `drawBehind` 背景色动画（enabled=surfaceContainerHigh / disabled=surfaceVariant 30%）；选中 2dp primary 描边；主行「名称 + 校验分 N/4（≥4 tertiary / ≥2 secondary / else error，Bold）」；副行「group · url」；可展开校验 error 行；行尾 `Switch`（selectionMode 禁用）+ 登录态 **AssistChip**（已登录 ✓ primaryContainer / 未登录 LockOpen outlined，配 loginUrl 才显示）+ MoreVert（编辑/删除进 overflow，**不再三个按钮并排**）。
- **空态**：图标 48dp alpha20 + 「暂无书源/无匹配结果」+ CTA 按钮「导入书源」。
- **统计条**：Search 下「共 N 个书源 / 启用 M」labelSmall。
- **导入 Dialog**：自动聚焦 + 剪贴板嗅探（http/JSON 显示「使用剪贴板内容」AssistChip）+ 内联校验 + 本地文件按钮；删除多选二次确认。
- **调试陷阱记录**（值得移植到我们实现文档）：`BookSource.equals` 只比 url → **`equals`/dedup 吞 toggle** → 必须 `derivedStateOf(referentialEqualityPolicy)` 或把 `enabled` 单独提取为参数保证 Compose 重组。

### 7.4 对我们设计的启示（与现有设计比照，登记进 ui-standards）
| 维度 | fork 取向 | 我们现状 | 采纳决策 |
|---|---|---|---|
| 列表形态 | 均单列表，无三视图/网格书源 | 已设计 ListLayoutMenu 三视图（列表/紧凑/网格） | **按原版保留三视图**（Legado 功能红线 + ListLayoutMenu 已登记 P1 里程碑），但 **fork「单列表+分组折叠」作为分组态优先渲染路径** |
| 分组呈现 | MoRealm 分组 Chips + **可折叠 GroupHeader**（启用数徽标） | 书源 domain 分组头 / 订阅源文件夹视图（私有） | **新增 `GroupHeader(GroupChip)` 到 S2 骨架子件**：折叠箭头+组名+启用/总数徽标+组操作（由 AppMenuSheet 承接），ListLayoutMenu 分组态首接线 |
| 条目线布局 | ReorderableSelectionItem / 卡片 SourceItem（选中描边+背景色动画+评分+登录 chip） | 原版条目控件挤（启用/编辑/更多同排，forks-deep-dive:109 已记） | **条目宽化：编辑/删除进菜单**，登录态 AssistChip，校验分/错误可展示；拖拽+多选+滑选保留（ReorderableSelectionItem 即 SelectActionBar+SwAction 的 Compose 版） |
| 排序交互 | 下拉首行升降序 + 点同维度翻方向 | ListLayoutMenu 排序 6 同时 | **采纳 MoRealm 交互逻辑写入 ListLayoutMenu 规格**（维度+升降序一体，点同维翻转） |
| 状态工程 | referentialEqualityPolicy / enabled 独立参数 / String enum key | — | **写进 ui-standards §4 状态管理陷阱清单**（BookSource.equals 去重陷阱） |
| 多选 | BackHandler 退多选 / rememberSaveable(listSaver) | SelectActionBar + DragSelectTouchHelper | **采纳**：返回键优先退多选 + 选中集持久化 |

## 8. 横向结论（翻版）

| 领域 | 学到了 | 本 spec 采纳 | 不采纳理由 |
|---|---|---|---|
| 书架 | FastScrollGrid+8dp/封面4dp | Grid 12dp 封面 + 18dp 卡片 | 圆角双层 |
| 过渡 | SharedTransition key | 封面过渡作为开关 | 性能/回归 |
| 阅读浮层 | sealed 37 sheet 单渲染 | 单态激活 sheet → BottomSheet 族 | 直接佳 |
| 主题 | legadoT 背景锚定中性面 | 自有 lerp 基线升级 | 不引动态依赖 |
| 换肤 | Sum Man zip | ✗ | 需求小 |
| 高亮 | Canvas 五线+规则 | 选色面板+样式开关 | 排版耦合 |
| XML MD3 | Jingshiro token | XML token 重命名（低风险批） | — |

> 所有证据均来自本次深度分析（附源码文件与行号见上各节）。

## 9. 阅读 Archive（legado-archive，Rimchars 私有仓）深挖（2026-08-12 补充）

> 仓 `temp/forks-comparison/legado-archive`（remote=github.com/Rimchars/legado-private-armv8-release，单根 commit「修复日夜主题分离遗留问题与字体撞色防护」）。与 four-fork 深挖的 Rimchars_legado 是不同仓库。181 个 compose 文件，View 为主 + Compose 孤岛 + 大量新功能（AI/书角色/漫画滤镜/云书库）。本次聚焦可搬运细节，三个子代理并行深挖。

### 9.1 主题引擎（vs 我们 ThemeSpec toM3Scheme）
| 发现 | 位置 | 我们采纳 |
|---|---|---|
| **撞色守卫**：配置写入期 sanitizeFontColorAgainstSurfaces，MIN_FONT_SURFACE_CONTRAST=1.3，昼夜默认色兜底（可跨昼夜取最小对比度更高者），半透明前景先 composite 再算 | ThemeConfig.kt:755-812 | **★ 采纳**：toM3Scheme 生成后做 onSurface 系槽位对比度后处理 pass（成本极低） |
| **per-token 日夜双键**：17 对（fontScale/fontScaleN、uiFontColor/uiFontColorN…）+一次性迁移 migrateLegacyNightValues（键拆分前共用日键→升级复制到夜键防回落） | ThemeRuntimeKeys.kt:14-52、App.kt:135-140 | **★ 采纳思路**：若未来支持用户覆盖某 token，日夜各存一份+迁移模式 |
| **签名式重组合失效**：themeUiSignature() 拼依赖键字符串+remember(signature) | ThemeUiPalette.kt:149-183 | ★ 中：可替代逐 token 观察 |
| 背景层版本失效：MAIN_THEME_BACKGROUND_CHANGED 事件+mainBackgroundVersion++→remember 失效；fallback 色双态（夜 md_grey_900/日 md_grey_100） | MainActivity.kt:204,583、ThemeConfig.kt:183-195 | ★ 中：背景资源变化用版本号驱动比直接改 state 抗并发 |
| divider 由 surface 亮度派生（isColorLight 决定黑/白+alpha） | ThemeUiPalette.kt:229-236 | ★ 中：M3 outlineVariant 缺失场景 |
| 不可搬运：ThemeStore 扁平存储/AppCompatDelegate 日夜/Selector/TintHelper/墨水屏 | — | ✗ View 系统遗产 |

### 9.2 书架
| 发现 | 位置 | 我们采纳 |
|---|---|---|
| **快照缓存秒显**：内存 LRU12+磁盘 JSON24，buildKey 含 14 项配置+分组签名→sha256 前 32 位，原子写 | BookshelfSnapshotStore.kt | **★ 采纳（书架 P1 后置）**：切分组/改配置不白屏 |
| sealed UiModel（Folder/Book）+contentType 做 Lazy key 体系，文件夹与书同列表 | BookshelfComposeItems.kt:41-63 | ★ 采纳：免双结构 |
| @Immutable Palette+RenderConfig+remember 键含主题签名 | BookshelfComposeList.kt:63-153 | ★ 采纳：主题切换零手工同步 |
| 封面 remember(coverIdentityKey) 集成 CoverCollectionManager | BookshelfComposeCover.kt | ★ 中 |
| 每分组滚动位置记忆（DisposableEffect+LaunchedEffect+dataVersion 守卫） | BookshelfFragment2.kt:185-212 | ★ 采纳 |
| BookListCardSurface 布局与交互解耦（RowScope metrics，搜索/发现复用） | BookListCardComponents.kt:47-94 | ★ 采纳：可作通用卡片 |
| fork 缺：Compose 骨架屏/下拉刷新/多选/拖拽 | — | 这些我们已具备，互补 |

### 9.3 我的页
| 发现 | 位置 | 我们采纳 |
|---|---|---|
| **Preference XML 深度搜索深链**：解析 R.xml.pref_config_* 收集 title/key/summary，顶部搜索穿透到设置子页 ConfigActivity(configTag+targetKey) | MyFragment.kt:399-456 | **★ 采纳**：我们高频/低频卡无搜索穿透能力 |
| **区块级 ComposeView 渐进式浸润**：每个面板独立 setContent（ReadRecordFragment 6 个 ComposeView 面板） | ReadRecordFragment.kt:195-287 | ★ 采纳：与「ComposeView 桥接双轨」互补 |
| 我的页纯设置列表+统计独立页（2×2 概览卡+112 天热力图+排行 top5） | ReadRecordFragment.kt:390-431 | ○ 参考：我们 ProfileScreen3Level 已一级含统计卡，保留 |
| SettingsActionRow 无 ripple 自绘按压+danger 底色 10% | MySettingsScreen.kt:229-285 | ★ 中 |

### 9.4 书源管理（直接对照我们 BookSourceActivity 多选改造）
| 发现 | 位置 | 我们采纳 |
|---|---|---|
| **isSelectMode 由选择集派生**（isNotEmpty，清空自动退出，无独立标志） | BookSourceActivity.kt:638-639 | **★ 采纳**：替代我们 composeIsSelecting+composeSelectedUrls 双标志（需手动同步） |
| **底部批量栏 AnimatedVisibility**：计数点击=全选+主危险操作外置+其余 12 项收 ⋮ | AppManagementScaffold.kt:263-322 | **★ 采纳**：比行内 SelectActionBarCompose 视觉更统一 |
| **数据回流剪除已消失 URL**（selectedUrls.filter{ it in currentUrls }） | BookSourceActivity.kt:637-639 | ★ 采纳：防脏选中 |
| 拖拽排序 ReorderableItem+拖柄与长按多选共存（sh.calvin.reorderable，仅 Default 排序+搜索空+非域名分组时启用） | BookSourceScreen.kt:56-136 | ★ 采纳（若做拖拽）：拖柄局部 draggableHandle 不冲突 |
| 区间补选 checkSelectedInterval（min~max index） | BookSourceActivity.kt:1005-1018 | ★ 采纳：校验场景 |
| 智能导出（全选=全量、<30%=仅选中、否则 key 交集） | BookSourceViewModel.kt:145-179 | ★ 采纳 |
| fork 缺：空态（无 EmptyStatePlaceholder） | — | 我们已具备 |

### 9.5 阅读器浮层/通用组件
| 发现 | 位置 | 我们采纳 |
|---|---|---|
| **单 sheet 容器+SheetType 分派**（showSheet(t,index,args)） | ReadMenu.kt:255 | ★ 验证 P2 设计：与我们「单一 activeSheet 渲染」一致 |
| **ModernActionPopup 全 fork 通用弹层菜单**（书架/搜索/发现/RSS/设置/换源/阅读菜单全替换） | ModernActionPopup.kt | ★ 采纳：通用菜单族替代 PopupMenu（对应我们 AppMenuSheet 方向） |
| ComposeDialogFragment 家族 8 种（TextInput/TextForm/NumberPicker/MultiChoice/Confirm/SingleChoice/ActionList/FetchedModel）+AppDialogStyle→LegadoMiuixPalette | AppComposeDialogs.kt | ★ 采纳：我们 Dialog 族 6 待建可对齐此清单 |
| 气泡快捷切换 BubbleQuickSwitchDialog（位图预览气泡包） | BubbleQuickSwitchDialog.kt | ○ 参考：低优先 |
| AI/角色卡/朗读三模式/云书库 | help.ai、AiChat*、BookCharacter* | ✗ 前瞻参考，目标项目暂无 AI 需求 |

### 9.6 深挖结论（一句话）
阅读 Archive 的「快照缓存秒显 + Set 派生多选态 + 底部批量栏 + Preference XML 搜索深链 + 撞色守卫」五件套，直接指导我们 ui-redesign-m3 的书架/我的/书源三页桥接改造；其缺空态/骨架屏/下拉刷新恰是目标项目已具备的能力，互补不冲突。

## 10. Legado_Max（Suml-1/Legado_Max）深挖（2026-08-12 补充）

> 仓 `temp/forks-comparison/Suml-1_Legado_Max`（github.com/Suml-1/Legado_Max，128 个 Compose 文件）。与 four-fork 深挖的 youfeng/Suml-1 Max 系聚焦点不同：本次聚焦 **首页模块化系统 + Dialog/设置体系 + 阅读记录热力图 + 规则执行可视化**，三个 explore 子代理并行。

### 10.1 首页模块化系统（Homepage modules）
- **架构**：HomepageFragment（View 壳，activityViewModels() 防 ViewPager 销毁丢状态）→ HomepageScreen（Compose）→ HomepageViewModel（combine Flow + `_configVersion` 脏标记计数驱动全链路重算）→ Room 双表（homepage_modules/homepage_custom_sets）+ Domain enum。
- **模块类型 8 种**（enum `HomepageModuleType`，HomepageModels.kt:62-76，`when(type)` 分发非反射）：banner（横轮播）/ranking（纵排行，初始 5 展开 20）/gridRanking/grid（3 列手动分列）/card（横卡片 120dp）/infiniteGrid（无限加载）/buttonGroup（分类快捷按钮 ≤5 列）/waterfall（双列手动分流避免 LazyGrid 嵌套定高问题）。
- **加载状态机** sealed `ModuleLoadState`（Loading/Loaded/Buttons/RankingTabs/Error）+ 每类型专属 Skeleton（SkeletonPlaceholders.kt shimmer）。
- **★ 管理交互（最值得学）**：`HomepageModuleManageSheet`——单 AppModalBottomSheet 内 sealed `ManageScreen` + `AnimatedContent` 实现 7 页面横向滑动导航（SetList→SetDetail/BrowseSources→SourceBrowseDetail…）+ BackHandler 返回链 + 内嵌 8 个 AlertDialog；集=模块分组容器（书源集 src_/订阅源集 rss_/自定义集 cs_）；显隐 Switch + 长按拖拽排序（sh.calvin.reorderable，拖完 LaunchedEffect 持久化）+ 无限流模块每集互斥 + 书源 JSON 自动同步（MD5 增量）。
- **布局两种模式**：layoutMode=0 混合列表 / =1 分源 Tab（HorizontalPager+预加载）。
- **与 S1 契合点**：同运行在 FragmentStatePagerAdapter ViewPager 下，证明 Compose 模块页可平滑嵌入现有 Tab 框架；发现页与书架分组天然可复用模块化思路。
- **搬运评估**：★ 高 GlassCard/HomepageModuleType enum+fromKey/ModuleLoadState sealed+Skeleton/无状态模块组件（输入仅 List<Book>+回调）/拖拽排序（sh.calvin.reorderable:3.1.0）；★ 中 双层 Room 表/管理 Sheet 多级导航/combine+版本脏标记；★ 低 书源 JSON 同步（耦合 homepageModules 列）/分源 Tab（耦合集概念，仅思路参考）。

### 10.2 Dialog 体系 + 设置页
- **★ BaseComposeDialogFragment**（31 行，BaseComposeDialogFragment.kt:13-35）：ComposeView+`DisposeOnViewTreeLifecycleDestroyed`+LegadoTheme 包裹，子类只需实现 `@Composable DialogContent()`——Dialog 族 6 组件统一宿主基类的最佳起点。
- **★ AppConfirmDialog**（50 行，AppConfirmDialog.kt:14-49）：Material3 AlertDialog 封装，`destructive=true` 确认按钮 error 色，14 处实战（SourceRecycleBin/FileManage/UrlRecord 等）——直接改造成目标 ConfirmDialog。
- **⚠️ AppDialogScaffold 死代码教训**（AppDialogScaffold.kt:27-39）：定义了顶栏+内容+底栏骨架但**全仓零引用**——证明「抽象骨架不接线=负债」，目标项目 Dialog 族应以实际 Dialog 共性（顶栏 secondary 色+卡片 surfaceVariant+shapes.large）为准则而非先造骨架。
- **★ Sheet 内多级导航**：HomepageModuleManageSheet sealed ManageScreen+AnimatedContent+BackHandler——对应目标 S6「L1 Sheet 承载多级页面」统一方案最佳范本。
- **★ MultiSelectDialogContent**：分组多选+总大小+全选/全不选，数据模型 MultiSelectItem/Group 干净，目标 Dialog 族缺的「多选类」。
- **设置行**：fork 仅 2 种极薄行（AppSettingSwitchItem/AppSettingClickItem），是目标 SettingsClickRow/ToggleRow 的子集，不搬；GlassCard/TextCard（surfaceVariant α0.7 底+16dp 圆角/文字徽标 8dp）可搬为列表管理卡片基座。
- **★ 拖拽排序模式**：SetListPage/SetDetailPage 的 ReorderableItem+LaunchedEffect 持久化+触觉反馈+hapticFeedback+zIndex 提升被拖项——S2 列表管理页样板直接复用。
- **视觉 token**：弹窗顶栏=secondary（pageTopBarContainerColor）、卡片底=surfaceVariant（pageCardContainerColor），Dark `luminance()<0.18f` 手动 lerp 提亮。

### 10.3 阅读记录 + 热力图（★ 高价值）
- **★ HeatmapCalendar 热力图（强烈建议搬运）**：完全自包含纯 Compose（HeatmapCalendar.kt 661 行，无第三方），入参仅 `dailyReadCounts: Map<LocalDate,Int>` + `dailyReadTimes: Map<LocalDate,Long>`（HeatmapCalendar.kt:81-86）；COUNT/TIME 双模式 FilterChip 切换；归一化基线 6 次/120 分钟；网格周一起始 chunked(7)；单元格颜色 `lerp(primaryContainer α0.42, primary, (value/max)²)` 二次方强度+今日/选中描边+5 格图例+月份 3 Pill 统计。后端仅需目标 DAO 加一条 `GROUP BY date` SQL（fork ReadRecordDao.kt:201-205 getDailyStats）。
- **SummaryCard+BookStackView**：书籍数+总时长+封面错位堆叠（rotate ±3°）成就卡，与 MetricGrid 互补；深色自适应色可移植到 MetricTile（目标当前硬用 surfaceVariant 无暗色处理）。
- **★ CommonPageColors 深色自适应体系**：`MaterialTheme.colorScheme.background.luminance()<0.18f` + lerp 向亮抬升（pageCardElevatedContainerColor 暗=lerp(surface,onSurface,0.06) α0.98/亮=surface α0.95）——统一深色观感最佳实践。
- **数据层**：三表 readRecord（聚合 PK=deviceId+bookName+author）/readRecordDetail（每书每天）/readRecordSession（会话）；DAO SQL 下推搜索+分页 500/批防 CursorWindow 溢出；时间线合并连续会话（gap≤20min）。
- **4 模式大页**：AGGREGATE（日期头+详情卡）/TIMELINE（竖线圆点时间线）/LATEST/READ_TIME（时长倒序）；左滑删除+长按多选——超出统计卡范围，建议只摘 HeatmapCalendar，页面整体改造另立任务。

### 10.4 规则执行流程可视化（debug 族，★ 价值高成本高）
- **FlowLogRecorder**：object 单例，MutableSharedFlow(replay=1, extraBufferCapacity=64)+ArrayDeque 上限 500+防抖 100ms；`AppConfig.debugLogFloatingBall` 开关默认关。
- **埋点侵入**：AnalyzeRule.kt 38 处 startStep/endStep+logRuleExecution + AnalyzeUrl.kt 3 处——搬运需复制 41 处埋点到目标规则引擎核心，**回归风险大，建议增量接入（开关默认关）+ 书源自测回归**。
- **数据结构**：FlowStage 6 阶段枚举（NETWORK/PARSE/EXTRACT/REPLACE/VARIABLE/DATA_FLOW 带 emoji）；FlowLogItem 超大类（requestId/源类型/阶段/操作 + 网络+规则树+JS 环境+变量操作+数据流+实体快照六维）；RuleExecutionNode 递归树（RuleType 11 种 CSS/XPATH/JSONPATH/JS/WEB_JS/REGEX/REPLACE/GET/PUT/DEFAULT/ROOT）。
- **DebugFloatingBall**：56dp 渐变圆球+拖拽全屏+边缘吸附（snapThreshold=84dp）+位置持久化+未读 Badge 99 封顶；DebugLogPanelDialog 同样挂全屏 ComposeView 到 decorView+BackHandler。
- **DebugLogScreen**：TopAppBar（刷新/搜索/暂停/清空/导出）+ DebugCategoryTabs（ALL/APP/NETWORK/RULE/SOURCE/RSS/TOAST/CHECK/CRASH/READER 10 类带计数）+ SOURCE/RSS 子分类+FlowStageFilter 6 阶段 FilterChip；详情双轨 DebugLogDetailDialog/FlowLogDetailDialog（分区展示+弹窗内搜索高亮+复制全部）。
- 目标项目 debug 工具页（Encode/Http/Regex 等 6+1）与 fork **结构完全同源**（Card 区块+本地 remember 状态+无历史），无需搬运，仅需按 CommonPageColors 深色模式统一观感。
- **搬运陷阱**：fork debug UI 大量硬编码中文（FlowLogList「请求 #/条」、EncodeTools 13 条）；热力图依赖 formatReadDuration+rr_heatmap_* 约 20 字符串资源需一并带。

### 10.5 深挖结论（一句话）
Legado_Max 最值得搬的是 **HeatmapCalendar 热力图**（自包含高价值低成本，接 1 条 DAO SQL）+ **BaseComposeDialogFragment 基类** + **AppConfirmDialog** + **Sheet 内多级导航**（S6 弹窗统一方案范本）+ **CommonPageColors 深色自适应**；模块化首页作为发现/书架页重构的交互模型参考；FlowLog 规则可视化价值高但埋点侵入规则引擎核心，需开关保护+回归才敢动。

## 11. legado-with-MD3-DIY（325506）深挖（2026-08-12 补充）

> 仓 `temp/forks-comparison/325506_legado-with-MD3-DIY`（github.com/325506/legado-with-MD3-DIY，kt=1106 compose≈126，全量 Compose 迁移仓）。此前仅浅挖书架 FastScrollLazyVerticalGrid，本轮三个 explore 子代理并行深挖：**路由体系+关键功能页 / 主题引擎 / Dialog 体系**。

### 11.1 导航路由体系（★ 与目标 S1 最相关）
- **Jetpack Navigation 3（androidx.navigation3 1.0.1）单 Activity**：MainActivity.kt:257-311 定义 `@Serializable sealed interface MainRoute : NavKey`，14 子路由（MainRouteHome/Settings/SettingsOther/Search/BookInfo/ExploreShow/RssSort/RssRead…），参数走 data class 构造（MainRouteBookInfo(name,author,bookUrl)）；NavDisplay+entryProvider 单实例承载全部页面，entry<MainRouteHome>{MainScreen} 为首页；transitionSpec slide+fade 480ms。
- **★ 底部 Tab 不用 NavHost 嵌套**（避免双栈）：MainScreen.kt:163/382 `rememberPagerState + HorizontalPager` + WideNavigationRail/FloatingBottomBar 承载 4 Tab（Bookshelf/Explore/Rss/My）；二级页回调 onNavigateToXxx → MainActivity.kt:713 navigateToRoute 手动 backStack.clear()+add 控制栈深度（MainRouteBookInfo 仅 current 是 Home/Search/ExploreShow 才 add，否则重建 Home+route，L767-779）。
- **ConfigNavScreen**：纯列表页（5 个 ClickableSettingItem：Theme/Other/Read/Cover/Backup）→ backStack.add(MainRouteSettingsXxx)；支持外部 deep-link createIntent(configTag)。
- **★ BookInfoRoute 壳层模式**（BookInfoActivity 改造直接范本）：BookInfoRouteScreen.kt:41 控制器壳——持有 BookInfoViewModel、集中 5 个 ActivityResult launcher（Toc/选目录/编辑/换源/阅读 L55-81）、收集 viewModel.effects 副作用（Finish/OpenReader/OpenToc L94-159），委托纯 UI BookInfoScreen(state,onIntent)。编辑=独立 Activity BookInfoEditActivity（StartActivityContract 返回 RESULT_OK→onInfoEdited() 刷新）。
- **状态管理统一 MVI/UDF + Koin**：BaseViewModel:AndroidViewModel；BookInfoViewModel 三件套 MutableStateFlow<BookInfoUiState>+MutableSharedFlow<BookInfoEffect>+onIntent 单入口，UI collectAsStateWithLifecycle；di/appModule.kt viewModelOf 全量注册+带参 viewModel{(route)->}；跨页传参一律经 Nav3 route 构造参数，不做全局单例。
- **★ ListScaffold<T> 泛型列表模板**（list/ListScaffold.kt:42）：统一 DynamicTopAppBar(搜索/下拉)+选中滑入 SelectionBottomBar(L114-131)+FAB；ListUiState<T>(items,selectedIds,searchKey,isSearch,isLoading)；BookshelfManageScreen LazyColumn+ReorderableItem 拖拽(L461/692)+FloatingActionButtonMenu 批量栏(L395-458)+BackHandler 清选择(L268)+空态 TextCard；BookCacheManageScreen cacheSection 分组(L214)+animateItem+骨架仅 CircularProgressIndicator 居中(L140)。
- **对目标借鉴**：① S1 5 Tab 保持 ViewPager 或迁 HorizontalPager，二级页用 Nav3 全全局路由表替换 Fragment 栈；② Route 壳层=副作用编排与渲染分离；③ ListScaffold/ListUiState 泛型模板=一屏实现搜索+多选+批量栏；④ 编辑页独立 Activity result 回调可平移。

### 11.2 主题引擎（14 模式，新旧双体系桥接）
- **新体系 ui/theme/**：ThemeEngine.kt(object,L24-145) 流水线 getColorScheme(mode,darkTheme,isAmoled,paletteStyle,materialVersion,forceOpaque,customSeedColor)：resolveMode(L66)→resolveBaseColorScheme(L77: Dynamic→dynamicDark/Light SDK<31 回退 GR；Custom→materialkolor dynamicColorScheme；preset 直取)→applyAmoledIfNeeded(L120 纯黑覆写)→applyTransparentIfNeeded(L133 4 槽透明化)。
- **14 模式**（AppThemeMode.kt:3-18）：Dynamic + 12 预置（GR/Lemon/WH/Elink/Sora/August/Carlotta/Koharu/Yuuka/Phoebe/Mujika/Transparent）+ Custom（种子色）；光/暗/跟随=独立 themeMode pref→ColorSchemeMode。
- **预置 12 套=静态硬编码 light+dark 各 ~48 参数全量手写**（无 lerp/翻转向量算法），差异在 primary/secondary/tertiary 色相+中性底（GR 绿#4C662B、Elink 纯黑、Lemon 黄、August 陶土红#8F4C37、Yuuka 靛蓝#565992）。
- **BaseColorScheme**：abstract lightScheme/darkScheme+getColorScheme(darkTheme)，无算法；CustomColorScheme(seed,style,colorSpec)→materialkolor；LegadoColorScheme(LegadoTheme.kt:25-78) M3 48 槽+自定义 3 槽 cardContainer/onCardContainer/onSheetContent=51 槽。
- **覆写=整 scheme 替换+动画非单 token**：ThemeOverride.kt buildThemeOverrideState(seed,isDark,style,spec,usePureBlack)(L21,AMOLED 黑化 L37-44)→LocalLegadoThemeColors；ThemeColorSchemeOverride.kt ProvideColorSchemeOverride(L77-157) 注入全槽+Miuix 下重建 ThemeController，core animateColorSchemeAsState(L172-242) updateTransition 对 48 槽逐一 700ms 动画。
- **新旧桥接**：App.kt:124 applyDayNightInit→OldThemeConfig.initNightMode() 设 setDefaultNightMode 同时驱动 View+Compose isSystemInDarkTheme；OldThemeConfig.applyConfig(L168-181) 把旧 primaryColor 写 cPrimary/cNPrimary=旧主题借"种子色"注入新体系 Custom 模式；ThemeConfigScreen L629 存 cPrimary 时写 ThemeStore+DynamicColors.applyToActivitiesIfAvailable 供未迁移 View。
- **深色模式**：12 套全手写 darkScheme；AMOLED 后处理（surface/background 纯黑、SCLow=#0A0A0A、SC=#121212）；毛玻璃 tint 用 luminance()>=0.5 选 alpha（HazeLegado.kt:55）。
- **对目标借鉴**：① 预置主题=ColorScheme 对象+Map<enum,BaseColorScheme> 调度（类型安全零解析，但 48×2 维护成本高）——目标已有 AD-18 5色→34槽位公式/撞色守卫可保留，借鉴「预置主题定义化+种子色/风格/对比度三维用户覆写+双引擎(2021/2025 spec)抽象」；② 语义扩展槽 cardContainer 等 3 槽与 AD-11 XML 层互补；③ Miuix→M3 槽位映射表（AppTheme.kt:151-215）现成对照；④ Opaque/Transparent 双通道+运行时可切换（含"透明模式必须配背景图"校验）比目标半透明方案完整；⑤ 反例：无撞色守卫、12 套不可用户扩展、新旧双体系冗余。

### 11.3 Dialog 体系（4 View 基类 + AlertBuilder DSL + Compose 双引擎）
- **四个 View 基类**（全部 5 共同约定：onFragmentCreated 唯一抽象方法/onDismiss 透传/execute() 协程封装/beginTransaction().remove(this) 防重复 add/observeLiveBus）：
  - BaseDialogFragment(115行)：onCreateDialog 手动 inflate dialogView 塞进 MaterialAlertDialogBuilder.setView()；getView() 覆写返回缓存 view；软键盘/墨水屏适配。
  - BaseBottomSheetDialogFragment(73行)：横屏 peekHeight=屏幕高*0.7f(L34-39)+setNavigationBarColorAuto(themeColor(colorSurfaceContainer))(L33)。
  - BaseOverlayDialogFragment(62行)：onCreateDialog 返回裸 Dialog 无窗口装饰=浮动窗（阅读页悬浮工具）；show 前查 isAdded。
  - BasePrefDialogFragment(39行)：近乎空壳，仅墨水屏 LifecycleObserver。
- **AndroidDialogs 工厂（lib/dialogs/，View）**：Context.alert/Fragment.alert 顶层函数(L11-61)+progressDialog/indeterminateProgressDialog；AlertBuilder<D> DSL（customView/okButton/cancelButton/yesButton/noButton/items/singleChoiceItems/multiChoiceItems/build/show L87-105）；AndroidSelectors 选择器对话框。
- **7 个 Import 家族高度统一**（BookSource/RssSource/DictRule/HttpTts/ReplaceRule/TxtTocRule/Theme）：BaseDialogFragment 或 BaseBottomSheetDialogFragment(R.layout.dialog_recycler_view)+viewModels<ImportXxxViewModel>+私有 SourcesAdapter+CodeDialog.Callback；分叉仅 3 处=①基类选择(RSS/Dict 居中弹窗，书源/主题 BottomSheet)②ViewModel 解析逻辑③菜单项；其余(importSelect 执行/全选/空态 emptyView/wrong_format)逐字相同。Compose 侧已有重构版 ImportComponents.kt：SourceInputDialog+泛型 BatchImportDialog<T>(ImportState New/Update/Existing/Error)。
- **★ Compose 双引擎组件**：AppAlertDialog.kt(L41-134) `ThemeResolver.isMiuixEngine(composeEngine)` 时走 Miuix WindowDialog 否则 Material3 AlertDialog——统一弹窗容器按引擎切换；AppModalBottomSheet 同双引擎(L40-80)；data 重载缓存末值播放退出动画(L141-175)。
- **ui/widget/dialog/ 8 个通用类恰对齐目标 Dialog 族**：WaitDialog(裸 Dialog 封装+链式 API L10-56)/TextDialog(MD/HTML/TEXT 三模式+Markwon)/TextListDialog(RecyclerView+setLayout(0.9f,0.9f))/CodeDialog(Callback.onCodeSave)/PhotoDialog/VariableDialog(Callback)/UrlOptionDialog/BottomWebViewDialog；Confirm 用 alert{} DSL，NumberPicker 见 ui/widget/number/NumberPickerDialog.kt。
- **Group 双版本**：View(GroupEditDialog 表单+GroupManageDialog+GroupSelectDialog ItemTouchHelper 拖拽) vs Compose(GroupEditSheet=AppModalBottomSheet+GroupEditContent+GroupDeleteAction 内嵌 AppAlertDialog 确认 L55-282)。
- **Change 家族**：ChangeBookSourceDialog(548行,SearchView+换源列表+章节对比)/ChangeChapterSourceDialog/ChangeCoverDialog(3 列 Grid+dataFlow.conflate().collect 流式封面 L65-73)/ChangeSourceMigrationOptionsSheet(Compose,7 CheckboxItem+ConfirmDismissButtonsRow)。
- **对目标借鉴**：① 目标 Dialog 族 6 类的 325506 落地范式=alert{} DSL(Confirm/Select)+WaitDialog(Wait)+VariableDialog/TextDialog(Edit/Text)+NumberPickerDialog(NumberPicker)；② AppAlertDialog 双引擎(data 重载+退出动画)与 AppModalBottomSheet 是可直接搬范本；③ 7 Import 家族三处分叉=导入类弹窗统一化样板，对应目标书源/订阅源/净化/词典 4 个导入对话框；④ BaseOverlayDialogFragment 裸 Dialog 浮动窗=阅读页悬浮工具兜底。

### 11.4 深挖结论（一句话）
legado-with-MD3-DIY 最值得搬的是 **Nav3 单 Activity 全局路由+BookInfoRoute 壳层模式**（BookInfoActivity 改造直接范本）+ **ListScaffold/ListUiState 泛型列表模板**（一屏搜索+多选+批量栏）+ **AppAlertDialog/AppModalBottomSheet 双引擎封装**（Dialog 族容器）+ **AlertBuilder DSL**；主题引擎 14 模式的组织方式（预置定义化+三维用户覆写）供 AD-18 参考但全量搬代价高；7 Import 家族三处分叉=导入对话框统一化样板。

## 12. huajideshutiao/legado 深挖（2026-08-12 补充）

> 仓 `temp/forks-comparison/huajideshutiao_legado`（github.com/huajideshutiao/legado，kt=852 compose≈71）。Dialog 体系与已挖仓同源不赘述，本仓独有特色=**净化规则源三件套**（其他 fork 均无，对应目标项目「搜索/发现结果过滤」能力）。本次直接读源码深挖（子代理通道多次中断，改为前台直读）。

### 12.1 数据模型（SourceFilterRule.kt，72 行）
- Room 实体 `source_filter_rules`（@Parcelize+@Entity，主键 UUID string）：name/enabled(Bool 默认 true)/**pattern**(正则字符串)/**fields**(逗号分隔作用字段)/**scope**(作用范围字符串)/order(sortOrder)/createTime。
- **Field enum 5 种**：NAME/AUTHOR/INTRO/KIND/WORD_COUNT（SourceFilterRule.kt:39）。
- **Scope sealed 4 态**（SourceFilterRule.kt:42-47）：All(空→全部书源)/None(原串非空但无效→规则不生效)/Source(url 单源)/Groups(names 分组集)。
- **字符串协议**（parseScope:61-70）：空→All；含 `::`→`name::url` 单源；否则→逗号分组 CSV。
- **规则命中语义**：规则内部 fields 是 **OR**（任一字段被正则命中即规则命中）；多规则之间命中即丢弃（黑名单模型）。

### 12.2 生效引擎（SearchBookFilter.kt，169 行，★ 性能快照模式）
- object 单例 + **快照缓存**：@Volatile snapshot + EMPTY 占位；reload() 置 null 失效；ensure() @Synchronized 惰性编译（compileEnabled 预编译 Regex+fields+scope → Snapshot(rules, originToGroups)）。
- **apply(books): Pair<List<SearchBook>, Int>**（:53-58）返回过滤后列表+丢弃数——搜索/发现结果合并后统一调用，UI 可展示「过滤掉 N 条」。
- **matchesAnyRule**（:97-104）：先 inScope(origin, bookGroups) 再 matchesAnyField（field.extract 从 SearchBook 取字段 → regex.containsMatchIn）。忽略大小写可后续补。
- **rulesInScope(scope)**（:65-71）：列出指定 scope 下生效的启用规则（搜索页展示当前源生效的规则）。
- **appliesTo**（:73-95）scope 相交判定全矩阵（All/Source/Groups × 目标 All/Source/Groups）。
- **buildOriginToGroups**（:158-168）：书源 URL→分组集 Map 缓存（用 bookSourceGroup splitNotBlank AppPattern.splitGroupRegex），支持「按分组生效」的源判定。
- 缓存失效时机：规则增删改后 reload() + 书源增删改后须 reload（:20 注释）。

### 12.3 UI 三件套（管理 Activity + 编辑 Dialog + 导入 Dialog）
- **SourceFilterRuleActivity（276 行）**：VMBaseActivity+SearchView 搜索+SelectActionBar 批量栏（删除/启用/禁用/置顶/置底/导出）+DragSelectTouchHelper 滑选+ItemTouchCallback 拖拽排序+菜单（新增/本地导入 txt,json/在线导入/清空）；Room flowAll/flowSearch+conflate 实时刷新；空态 tvEmptyMsg。
- **SourceFilterEditDialog（130 行）**：BaseDialogFragment(dialog_source_filter_edit)；新增/编辑复用；5 字段 CheckBox 选择；**作用范围复用 SearchScopeDialog**（与搜索范围选择同源，:20 注释「作用范围复用 [SearchScopeDialog]」）；正则合法性校验（Regex(pattern) runCatching，:102）+ 至少选一字段校验；保存回调 onSourceFilterRuleSave(rule, isNew) → SearchBookFilter.save。
- **ImportSourceFilterRuleDialog（162 行）**：BaseDialogFragment(dialog_recycler_view)+ImportSourceFilterRuleViewModel；本地/在线导入 JSON；列表项带「新增/更新/已有」三态（:127-135 比较 pattern/fields/scope）+ CodeDialog 编辑（GSON 修改）+ 全选/反选/导入执行（WaitDialog 包裹）。
- **导入三态判定**：对比 item.pattern/fields/scope 与本地 checkRules——任一不同=更新，全同=已有，无本地=新增。

### 12.4 IBottomDialog + BaseBottomDialogFragment
- **IBottomDialog.kt（5 行）**：`interface IBottomDialog { var bottomDialog: Int }`——仅声明一个「底部弹窗」标记位，配合 BaseBottomDialogFragment 标记对话框以底部方式展示（极简协议）。
- 净化规则源对目标项目参考价值高：**搜索/发现结果过滤能力目标项目暂无**，huajideshutiao 给出完整闭环（数据模型+快照引擎+三套 UI），字段 OR/多规则黑名单/范围协议三件可直接搬，性能快照模式与目标 §4.6 书架快照缓存同思路可复用。

### 12.5 深挖结论（一句话）
huajideshutiao 独有价值=**搜索/发现结果过滤闭环**（SourceFilterRule 数据模型 + SearchBookFilter 快照引擎 + Activity/EditDialog/ImportDialog 三件套），其「规则字段 OR + 多规则黑名单 + scope 范围协议 + 惰性快照编译」可完整指导目标项目搜索过滤能力，UI 层可复用 Import 三态模式与 scope 复用 SearchScopeDialog 的思路。
