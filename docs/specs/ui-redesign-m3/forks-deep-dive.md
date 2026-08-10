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

## 6. 用户旅程：（目标仓走查 + fork 对照）

目标仓走查 5 个关键 journey（对齐第三子代理审计，实码路径）：
1. **进阅读**：书架→BookInfo→Read 一般 2-3 步（`startActivity` 直读可 1 步选项）。
2. **调字号/亮度/夜间**：阅读底栏「设置」→ReadStyleDialog（当前 1 步 1 弹窗，OK 但改动 Browse Tab）；亮度竖条 `vw_brightness_pos_adjust` 是本仓独有增强，**保留并打磨**。
3. **调目录**：底栏「目录」→TocDialog（现状 1 步弹窗→ 改 `Herlu` 三 Tab Sheet，加进度/书签）。
4. **搜索正文**：阅读浮层 `menu_search`（现状 OK）；书架顶栏全局搜索需要从 My 中的 `书源` 移出一级。
5. **排的书源管理**：现状在「我的」二级（`bookSourceManage`），应补**关键词搜索 + 顶栏入口**，改动 Source item 拥挤（启用/编辑/更多三控件同排）。

完整旅程/状态机图见 design.md §Data Flow/UX。

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