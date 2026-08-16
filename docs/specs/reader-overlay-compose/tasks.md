# tasks.md · 阅读器浮层 Compose 化（S5 骨架）

> OpenSpec 四文档之三。对应 ui-redesign-m3 `V-7`（支干 P1 样板）之 S5 阅读器浮层。
> 状态：🔄 设计中。正文零改动红线贯穿（page/ 29 文件 + ReadView + 三信号 + 锚点 + insets + 主题线）。

## 1. 准备工作
- [ ] 1.1 复核现状：ReadBookActivity 菜单层/浮层/状态现状（`read_menu`/`search_menu`/`composeSheetHost`）
- [ ] 1.2 确认正文零改动边界 6 条清单（page/ 29 文件、menuLayoutIsVisible 三信号、选区锚点、insets 双轨、主题双事件线、PageView 反向依赖）

## 2. 阶段1：菜单层 Compose 化（顶栏+底栏+scrim+ReaderUiState）
- [x] 2.1 新增 `ReaderUiState.kt`（data class + StateFlow + sealed `ReadBookSheet`）
- [x] 2.2 新增菜单顶栏（返回/书名/章节/换源/刷新/⋮）— 并入 MenuLayer.kt 的 MenuTitleBar
- [x] 2.3 新增菜单底栏（上一章/进度 Slider/下一章 + 工具网格）— 并入 MenuLayer.kt 的 MenuBottomBar
- [x] 2.4 `MenuLayer`（scrim + AnimatedVisibility）— 暂未做 3s 无操作自动淡出（P2 收尾时评估）
- [x] 2.5 `composeSheetHost.setContent` 接线菜单层；ReadView 保持 XML 垫底
- [x] 2.6 渲染回调 handler.post 切主线程 → updateMenuLayerState 同步（当前同步刷新点：showMenuBar/开关操作后）
- [x] 编译 assembleAppDebug 通过；正文零改动 grep 校验通过（read 包仅 BaseReadBookActivity/ReadBookActivity/ReaderUiState 变更，page/ 引擎零改动）
- 待验证：菜单浮现/淡出/scrim 收起 → 🔴 FR-11 统一真机验证（6.5）

## 3. 阶段2：activeSheet 单态收敛
- [x] 3.1 收敛现有独立 Sheet 入口到 `activeSheet: ReadBookSheet?` 单态宿主（showTocSheet → readerUiState.showSheet(ReadBookSheet.Toc)，散落 mutableStateOf 移除）
- [x] 3.2 目录 Sheet 接入 BookTocBookmarkSheet（双 Tab 基座，无回归）— 渲染条件改 `uiState.activeSheet == ReadBookSheet.Toc`
- [x] 3.3 消除嵌套（任意时刻最多一个 Sheet）：菜单层与 Sheet 层互斥（打开任一 Sheet 前先 hideMenu）；hideMenu 仅当 activeSheet==null 才隐藏 composeSheetHost
- 验证：目录/书签 Sheet 弹出/关闭；无叠加嵌套；Back 关闭正确 → 🔴 FR-11 统一真机验证（6.5）
- 说明：Search/AutoRead/ReadAloud 为 DialogFragment（独立窗口层，非 Sheet），暂留原实现，Back 链在阶段4统一

## 4. 阶段3：阅读设置 Sheet（最高优先级）
- [x] 4.1 新增 `ReaderMenuSheet.kt`（SettingsCard 分组：字号/亮度/夜间/行距/对齐 + 扩展翻页/字体）
- [x] 4.2 进度/亮度/字号滑块：拖动菜单 alpha≤30% 实时预览 + 松手 conflate 串行提交 — 本阶段用 M3 Slider onValueChange 实时生效（字号/行距/亮度），与菜单层同步；alpha≤30% 预览与 conflate 串行提交留 P2 收尾统一评估
- 验证：调字号/亮度实时预览；滑块不抖动不回弹；无硬编码 → 🔴 FR-11 统一真机验证（6.5）
- 说明：对齐/翻页动画/字体为扩展点击行，点击调起原 ReadStyleDialog；「更多设置」调起原 MoreConfigDialog 保全全部功能

## 5. 阶段4：Back 链 + i18n/无障碍
- [x] 5.1 BackHandler 优先级链：弹层→搜索→自动翻页→菜单路由→退出阅读 — 改造 `ReadBookActivity` `onBackPressedDispatcher` 回调：activeSheet 弹层最优先 → 全文搜索 `isShowingSearchResult` → 恢复进度 → 朗读暂停 → 自动翻页 `isAutoPage` → 菜单路由 `menuVisible` → disableReturnKey → finish（设计 R6）
- [x] 5.2 i18n：新文案 zh+en 双语，禁硬编码中文/色/字号 — 本阶段无新文案；ReaderMenuSheet/ReaderUiState 全 stringResource
- [x] 5.3 菜单按钮 ≥48dp；Icon contentDescription；颜色仅 colorScheme — `MenuToolItem` 补 `heightIn(min=48.dp)`+`semantics{role=Button}`；`MenuFloatingButton` 应用 contentDescription 参数（修复参数未使用的无障碍缺陷）；Slider 用 M3 内置语义
- 验证：Back 逐层回退正确；grep 无硬编码中文/Log.d/e 残留 → 🔴 FR-11 统一真机验证（6.5）

## 6. 收尾
- [x] 6.1 P2 §8 验收逐条勾选（布局一致/组件规格/正文零改动/单态/三态/i18n/回执/grep）— 2026-08-14 完成，7/8 项勾选，仅剩 6.5 真机项
- [x] 6.2 updateLog.md 追加（基于 git diff）— 2026-08-13 阶段一~四条目已追加
- [x] 6.3 tasks.md + pages-inventory 实施回执（§3.3 AD-23）— 见下方「页面回执」
- [x] 6.4 文档同步（docs/INDEX.md + task-navigation.md）— 2026-08-14 完成
- [ ] 6.5 🔴 FR-11 统一真机验证（V-7/MEmu+ai_tests\venv，重点：翻页手势/滑块预览/选区菜单/Back 链）— 2026-08-14 交用户真机回归（新测试包 3.26.081411）

## 页面回执：S5 阅读器浮层（§3.3 AD-23）

- **实施范围**（2026-08-13）：阶段1 菜单层 Compose 化（MenuLayer：scrim+顶栏+亮度条+底栏工具网格，26 项回调绑定）；阶段2 activeSheet 单态收敛（ReadBookSheet sealed + readerUiState.showSheet，散落 mutableStateOf 移除，菜单与 Sheet 互斥）；阶段3 阅读设置 Sheet（ReaderMenuSheet：SettingsCard 分组，字号/亮度/夜间/行距/对齐 + 扩展点击行调原 ReadStyleDialog/MoreConfigDialog 保全功能）；阶段4 Back 链 + i18n/无障碍
- **组件复用**：MenuLayer/ReaderMenuSheet/ReaderUiState（ui/widget/components 新增）；复用 AppModalBottomSheet/SettingsCard/BookTocBookmarkSheet；正文 ReadView/PageView 等 page/ 引擎零改动（壳-核分离 AD-01/AD-02）
- **私有组件 0**；三态齐全；无硬编码色/字号/中文（全 colorScheme+stringResource）；正文零改动红线 6 条全部保留（git status page/ 零变更）
- **真机状态**：🔴 FR-11 待用户回归（2026-08-14 用户自测 3.26.081411，重点：翻页手势/滑块预览/选区菜单/Back 链）

## AOAdapt 日志
（实施中遇调整/失败时记录）
