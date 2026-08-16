# design.md · 阅读器浮层 Compose 化（S5 骨架）

> OpenSpec 四文档之二。规格基础：`P2-reader.md`（v2）+ `ui-standards.md §3.4`。
> 状态：🔄 设计中。

## 1. Technical Approach（技术方法）

**总体**：在 `composeSheetHost`（`ReadBookActivity.kt:1265` 已有 `setContent`）基础上，将菜单层 + 浮层整体 Compose 化。正文 `ReadView` 保持 XML 垫底（AndroidView 桥接思想，z-order 最底），Compose 浮层叠加其上。新增 `ReaderUiState` 单 StateFlow 作为 UI 状态唯一来源，替换散落 `isMenuVisible` 等 mutableBoolean。

**分层**：
1. **状态层**：`ReaderUiState`（data class + StateFlow，含 `menuVisible/activeSheet/activeDialog/routeStack/searchState`）。
2. **菜单层**：`MenuLayer`（Compose，AnimatedVisibility 控制）：scrim + 顶栏 `MenuTitleBar` + 底栏 `MenuBottomBar`。
3. **弹层区**：`activeSheet: ReadBookSheet?` 单态宿主，sealed interface 枚举所有 Sheet。
4. **接线**：`ReadBookActivity` 保留正文/业务逻辑，UI 壳委托 Compose。

**正文零改动边界**：`menuLayoutIsVisible` 三信号（L520-540 等）保持从正文状态反推，不迁移逻辑；选区锚点坐标 `textMenuPosition` 原样传给 Compose 菜单；insets 双轨 / 主题双事件线不动。

## 2. Architecture Decisions（ADR Y-Statement）

### AD-01: 菜单层 Compose 化但保留 ReadView 垫底
- **Context**: 正文是 Canvas 排版 AndroidView，无法纯 Compose 承载；现有 `read_menu` 自定义 View 承载菜单 UI。
- **Concern**: 菜单 Compose 化不能破坏正文渲染与 z-order。
- **Decision**: 正文 ReadView 保持 XML 垫底，`composeSheetHost` 承载 Compose 菜单层 + 浮层，Compose 叠加其上。
- **Goal**: 壳-核分离，正文零改动，UI 可 Compose 化。
- **Tradeoff**: View+Compose 混合 z-order/insets 协调需谨慎。
- **Status**: Proposed

### AD-02: activeSheet 单态收敛（杜绝 3 层嵌套）
- **Context**: 现有多个独立 visible 控制（`compose_sheet_host.visibility` 等），弹窗最多嵌套 3 层，Back 链混乱。
- **Concern**: 多弹窗叠加导致状态与 Back 不可控。
- **Decision**: sealed interface `ReadBookSheet` 全量枚举，`ReaderUiState.activeSheet` 单一来源，一次一个。
- **Goal**: 任意时刻最多一个 Sheet，Back 链可预期。
- **Tradeoff**: 需要把现有独立弹窗入口统一收敛到单态宿主，接线量增加。
- **Status**: Proposed

### AD-03: ReaderUiState 单 StateFlow（禁散落 mutableStateOf）
- **Context**: 现状 Activity 散落 `isMenuVisible` 等 mutableBoolean。
- **Concern**: 状态分散导致跨组件同步难、易竞态。
- **Decision**: 轻量 `ReaderUiState` data class + 单 StateFlow，Compose 层 collectAsState 订阅。
- **Goal**: UI 状态单一来源，主线程一致下发。
- **Tradeoff**: 需维护状态合并与 update 逻辑；业务数据仍留 ReadBookViewModel 不动。
- **Status**: Proposed

### AD-04: 渲染回调保持 IO→主线程 post
- **Context**: 正文渲染回调可能在工作线程。
- **Concern**: 直接更新 Compose 状态可能线程不安全。
- **Decision**: 渲染回调一律 `handler.post {}` 切主线程（SharedFlow 语义，零逻辑漂移）。
- **Goal**: 线程语义与现状一致，无竞态。
- **Status**: Proposed

### AD-05: 进度 Slider 拖动 alpha≤30% 预览 + conflate 串行提交
- **Context**: P2 §4 防「拖到 70% 回弹 40%」。
- **Concern**: 拖动实时跳页抖动。
- **Decision**: 拖动时菜单整体 alpha≤30% 实时预览正文，松手 commit（conflate+串行）。
- **Goal**: 拖动顺滑、提交准确。
- **Status**: Proposed

## 3. Data Flow（数据流）

```
ReadBookViewModel(业务不动) ──▶ ReadBookActivity 回调 ──▶ handler.post(主线程)
                                                            │
                                        ReaderUiState(StateFlow 单源)
                                         ├─ menuVisible (点击中屏/3s淡出)
                                         ├─ activeSheet (ReadBookSheet? 单态)
                                         ├─ activeDialog
                                         ├─ routeStack (Back 链)
                                         └─ searchState
                                                            │
                              Compose 层 (collectAsState)   ▼
                        MenuLayer(scrim+顶栏+底栏) + activeSheet 宿主
                                                            │ 点击/操作
                                        ReaderUiState.update { ... }
```

- 正文状态（章节/进度/亮度）通过现有 ReadView 回调反推，不迁移逻辑，仅映射到 ReaderUiState 展示字段。
- 渲染回调 IO→主线程 post 后 update ReaderUiState，零逻辑漂移。

## 4. File Changes（文件变更）

| 文件 | 操作 | 说明 |
|------|------|------|
| `ui/book/read/ReadBookActivity.kt` | 修改 | UI 壳委托 Compose；`composeSheetHost.setContent` 承载菜单层+浮层；Back 链接入 |
| `ui/widget/components/MenuTitleBar.kt` | 新增 | 顶栏（返回/书名/章节/换源/刷新/⋮），磨砂 |
| `ui/widget/components/MenuBottomBar.kt` | 新增 | 底栏（上一章/进度 Slider/下一章 + 工具网格），贴底/悬浮药丸 |
| `ui/widget/components/ReaderMenuSheet.kt` | 新增 | 阅读设置 Sheet（SettingsCard 分组，字号/亮度/夜间/行距/对齐+扩展） |
| `ui/book/read/ReaderUiState.kt` | 新增 | data class + StateFlow + sealed ReadBookSheet |
| `res/layout/activity_book_read.xml` | 修改 | 保留 read_view/compose_sheet_host；`read_menu`/`search_menu` 视阶段替换 |
| `res/values*/strings.xml` | 修改 | 新增菜单/设置文案 zh+en |
| `ui/widget/components/`（既有） | 复用 | SettingsCard/AppModalBottomSheet/GroupHeader/BadgeDot/ReadMenuSlider(待建) |

> 分阶段实施：阶段1 菜单层 Compose 化（顶栏+底栏+scrim+ReaderUiState）→ 阶段2 activeSheet 单态收敛 → 阶段3 阅读设置 Sheet → 阶段4 Back 链 + i18n/无障碍。每阶段编译+真机验证，正文零改动红线贯穿。
