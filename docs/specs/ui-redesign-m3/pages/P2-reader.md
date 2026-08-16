# 页面详细设计文档 · P2 阅读器页（ReadBook 壳-核分离版 · v2）

> **主文档引用**：README「文档索引」+ ui-standards §10「页面设计文档索引表」。
> **task 对应**：tasks.md `12.16o`（v2.8 预审）、`12.24`（Phase4 浮层 Sheet 化）、`P0-reader-migration`（R0-R4 迁移）。
> **另一 AI 开发本文档范围时只读本文档 + ui-standards §3.4 规格书，禁止自行发明样式。**

## 0. 页面身份

- **页面名 / 文件锚点**：`ui/read/ReadBookActivity.kt`（1875 行）+ `activity_book_read.xml`（壳）｜正文引擎 `ui/page/` 下 29 个文件
- **骨架归类**：S4 详情/阅读页（主）+ S5 全屏沉浸页（弹层/浮层体系）复合
- **对应 task**：tasks.md `12.16o`（v2.8 预审）、`12.24`（Phase4 浮层 Sheet 化）；pages-inventory B1 行
- **fork 借鉴来源**：forks-deep-dive §9（HapeLee ReaderLayoutCoordinator）、§10（MoRealm single activeSheet）、§11（legadoT DialogForm/Slider）、§12（youfeng Span 族）

## 1. 设计意图

> 原版阅读页 2000+ 行把「正文渲染 + 菜单 UI + 全部浮层」耦合在一个 XML+Dialog 壳里，改动任何 UI 都冒回归正文的风险，且弹窗层层嵌套（最多 3 层）。本轮目标：**壳-核分离**——正文引擎（page/ 29 文件）零改动，UI 壳（read_menu/search_menu/config 弹窗族/TextActionMenu）逐步 Compose 化，弹层收敛为**单一 activeSheet 单态**杜绝多层弹窗。这是 3 个开源 fork 共同验证的成功范式（HapeLee AndroidView 桥接正文+浮层全 Compose；MoRealm 全 Compose 但仿真翻页仍退回 AndroidView）。**正文零改动是红线（AD-02 不变）**。

## 2. 布局结构（文字框图 + 区块表）

```
┌────────────────────────────────────────────┐
│ ① 正文层（AndroidView，全屏，垫底）              │  ← page/ 零改动
│    ReadView（Canvas 排版+翻页动画+手势）        │
│    + textMenuPosition(0×0 锚点)                │
│    + cursorLeft/cursorRight(选区光标)          │
│  ───────────────────────────────────────────  │
│ ② 菜单层 AnimatedVisibility（点击中屏浮现）      │
│    ├─ scrim 全屏遮罩（点击收起）                │
│    ├─ 顶栏 MenuTitleBar（磨砂，TopCenter）       │
│    ├─ 亮度竖条（左/右，可配置）                  │
│    └─ 底栏 MenuBottomBar（贴底或悬浮药丸）       │
│ ③ 搜索层 ReadBookSearchBar（结果 n/N 胶囊）     │
│ ④ 弹层区（一次一个 activeSheet）                │
│ ⑤ 选区菜单 TextActionSelectionMenu（光标旁）     │
│ ⑥ 朗读/翻译悬浮胶囊（可选，TopEnd/BottomEnd）    │
└────────────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|------------------|----------|------|
| 正文层 | `AndroidView(ReadView)` 零改动 | ReadBook 单例 | 沉浸式，顶到状态栏 |
| 顶栏 | `MenuTitleBar`（surface α0.86，API31+ RenderEffect blur，低版本纯色降级） | ReaderUiState.menuVisible | 返回/书名/章节/换源/刷新/⋮ |
| 底栏 | `MenuBottomBar`（贴底默认/悬浮药丸 16dp 边距+圆角+不透明 surface 可配） | ReaderUiState | 上一章/进度 Slider/下一章+工具网格 |
| 搜索层 | `ReadBookSearchBar`（结果 n/N 胶囊） | ReaderUiState.searchState | 现 search_menu Compose 化 |
| 弹层区 | `AppModalBottomSheet`（§3.4：surface，skipPartiallyExpanded）或 L2 Dialog 族 | activeSheet 单态 | 一次一个 |
| 选区菜单 | `TextActionSelectionMenu`（坐标来自 View 锚点） | textMenuPosition | 现 TextActionMenu Compose 化 |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `AppModalBottomSheet` | surface 底、圆角顶、skipPartiallyExpanded=true | 阅读设置/目录/书签/高亮 Sheet 容器 |
| `ConfirmDialog` / `AppEditDialog` / `AppSelectDialog` / `AppNumberPickerDialog` / `AppTextDialog` | 12.22 已建 L2 族 ✅ | config/ 12 Dialog 收敛去向 |
| `AppMenuSheet` | 富操作列表 | 更多操作 |
| `GroupHeader` | titleSmall Bold、行≥48dp | 目录/书签分组 |
| `BadgeDot` | error 底、10sp、count>99 显示 99+ | 目录未读章标记 |
| `SettingsCard` | 圆角 **18dp**、标题 h16 v12、surfaceVariant、1dp elevation | 阅读设置分组容器 |
| `ReadMenuSlider`（🔵 待建，§3.4 阅读器族） | 拖动时菜单 alpha≤30% 实时预览 | 进度/亮度/字号 |
| `BookTocBookmarkSheet`（✅ 已接线 12.24） | 双 Tab：目录/书签 + 「章节列表」TextButton | **现状**：Phase4 已接线的阅读器浮层容器 |
| `ReaderBookSheet`（🔵 待建，R2 演进） | 三 Tab：目录/书签/高亮，72% 高 | **蓝图**：未来增强（敬畏现状双 Tab 基座） |
| `TextActionSelectionMenu` | 选区菜单（色盘 2 行 6 色，无二级） | 长按高亮文字 |

> ⚠️ 滑动组件的拖动手势须限定 sheet 区域消费（`Modifier.pointerInput`），避免与正文翻页误触；正文 View 层手势全部保留不动。

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 点击正文中屏 | 菜单层浮现（AnimatedVisibility）；3s 无操作自动淡出 | ✅ | menuState.visible |
| 点击 scrim | 菜单收起 | ✅ | |
| 底栏「目录」 | **现状**：弹 `activeSheet=Toc` 的 `BookTocBookmarkSheet`（双 Tab 目录/书签 + 章节列表）｜**蓝图**：R2 演进 `ReaderBookSheet`（三 Tab 目录/书签/高亮，72% 高） | 1 | 现状双 Tab 为基座，勿误判为已建三 Tab |
| 底栏「更多」 | 阅读设置 Sheet（字号/亮度/夜间/行距/对齐一屏，扩展翻页/字体） | 1 | 最高优先级 |
| 长按高亮文字 | TextActionSelectionMenu（色盘 2 行 6 色，直接改该段，无二级） | 1 | |
| Back 键 | 优先级链：弹层→搜索→自动翻页→菜单路由→退出阅读 | ✅ | MoRealm 模式 |
| 进度 Slider 拖动 | 菜单整体 alpha≤30% 实时预览正文，松手 commit（conflate+串行） | ✅ | 防「拖到 70% 回弹 40%」 |

## 5. 状态管理（§4 范式）

- 数据源：现有 `ReadBookViewModel` 保持（业务/数据不动）；新增**轻量 `ReaderUiState`**（menuVisible/activeSheet/activeDialog/routeStack/searchState）单 StateFlow 下发。
- 渲染回调线程语义保持：IO 线程渲染回调一律 `handler.post {}` 切主线程（SharedFlow 语义，零逻辑漂移）。
- 弹层状态：`activeSheet: ReadBookSheet?`（sealed interface 全量枚举）+ `activeDialog: ReadBookDialog?`，单一来源。
- **避免幽灵恢复**（MoRealm restoreToken）：`loadChapter` 每次赋 `System.nanoTime()` token，LaunchedEffect 仅 token 变时触发。
- **禁止**：Fragment 散落 mutableStateOf；跨层共享 ViewModel 传易变 Config。

## 6. 三态（加载/空态/错误）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | 正文 ChapterProvider::upViewSize + `awaitViewport(2s)` 等排版就绪 | 治「先画后排闪烁」；目录骨架可 `ShelfGridSkeleton` |
| 空态 | 目录空 → `EmptyStatePlaceholder`（Icon48+标题+副标） | 章节列表为空提示 |
| 错误 | 章节加载失败 → `EmptyStatePlaceholder` 错误分支 + 重试按钮 | 文案 i18n |

## 7. i18n 与无障碍

- 新文案：`strings.xml`（zh+en）双语；禁硬编码中文（正文侧现有日志文案登记 §6.1 存量清零清单）。
- 菜单按钮 ≥48dp（`ReadMenuGlassButtonSurface` 48dp 玻璃/40dp 普通圆形）；Icon contentDescription；颜色只 colorScheme。
- 沉浸式 `enableEdgeToEdge`，systemBars 自动配色；隐藏状态栏时顶栏吃 inset，正文 `vwStatusBar` 占位不动。

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [x] 布局与 §2 框图一致（6 层区块齐全、无多无少）— S5 阶段1 菜单层（scrim+顶栏+亮度条+底栏工具网格）+ 阶段3 阅读设置 Sheet 落地，阶段4 收尾复核通过
- [x] 组件全部来自 §3 表，规格与 §3.4 逐项一致（圆角/间距/字号/色槽）— MenuLayer/ReaderMenuSheet 全 colorScheme+stringResource，无硬编码色/字号（2026-08-13 各阶段 grep 校验）
- [x] **正文零改动**：page/ 5 个文件（ContentTextView/HighlightDraw/ReadView/PageView/AutoPager）+ `menuLayoutIsVisible` 三信号（BaseReadBookActivity:68/246、ReadBookActivity:359/388/762/997/1856）+ insets 双轨（PageView vwStatusBar/vwNavigationBar）+ PageView 反向依赖 Activity（PageView.kt:44 readBookActivity）全部保留，git status page/ 目录零变更（2026-08-14 复核）
- [x] 弹层收敛为单一 activeSheet，无 3 层嵌套；BackHandler 优先级链正确 — 阶段2 单态收敛 + 阶段4 onBackPressedDispatcher 回调（弹层→搜索→自动翻页→菜单路由→退出）
- [x] 三态齐全；空态/错误态文案 i18n；无硬编码色/字号；无私有复制组件 — 阶段4 i18n/无障碍（按钮≥48dp/contentDescription）
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv），重点：翻页手势/滑块预览/选区菜单/Back 链 — 🔴 由用户真机回归（2026-08-14 用户自测新测试包 3.26.081411）
- [x] §3.3 实施回执已填（tasks + pages-inventory）— 2026-08-14 已填（见 tasks.md「页面回执：S5 阅读器浮层」）
- [x] grep 无 `android.util.Log.d/e` 残留 — ReadBookActivity/ReaderUiState/MenuLayer 全 grep 零残留（2026-08-13/14 复核）
- [ ] **P2 收尾待办登记**（2026-08-15，D-5）：3s 无操作自动淡出（§4 菜单层设计项，reader-overlay tasks 2.4 推迟）+ 滑块拖动 alpha≤30% 实时预览与松手 conflate+串行提交（§4 滑块设计项，reader-overlay tasks 4.2 推迟）— 两设计与实现现状不符（当前拖动直接生效），随 P2-reader R0-R4 收尾统一评估

## 9. 绘图 Prompt

```
Material 3 Android 阅读器页高保真UI：大面积纯色纸感正文占据全屏，
顶/底各一条半透磨砂栏（顶部含返回/书名/章节，底部为悬浮药丸含进度条与工具网格），
正文区文字下方有淡色下划线高亮，底部一角 Mini 阅读进度圆点，皮肤暖黄纸感，
UI 控件只在操作时浮现，无花哨渐变、无刺眼高饱和，沉浸式无状态栏。
```

## 10. 变更记录

- 2026-08-13：v1→v2 升级（套模板 10 节，对齐 12.24 Phase4 浮层 Sheet 化现状，task 12.16o/12.24）
- 历史：v1 确立壳-核分离三层架构、正文零改动红线 6 条、迁移路径 R0-R4
