# spec.md · 阅读器浮层 Compose 化（S5 骨架）

> OpenSpec 四文档之一。规格基础：`docs/specs/ui-redesign-m3/pages/P2-reader.md`（v2 权威设计）+ `ui-standards.md §3.4`（组件规格唯一真值）。
> 功能名：`reader-overlay-compose`。状态：🔄 设计中。

## 1. Intent（意图）

阅读页 ReadBookActivity（1875 行）把「正文渲染 + 菜单 UI + 全部浮层」耦合在一个 XML+Dialog 壳里，改动任何 UI 都冒回归正文的风险，且弹窗层层嵌套（最多 3 层）。本轮实现 P2 设计文档的**壳-核分离**：正文引擎（page/ 29 文件）零改动，UI 壳（菜单层/浮层）逐步 Compose 化，弹层收敛为**单一 activeSheet 单态**杜绝多层弹窗。

本 spec 聚焦 **S5 阅读器浮层骨架样板页**的可交付第一阶段，为后续枝叶页提供样板范式。

## 2. Scope（范围）

### 做（本 S5 骨架阶段）
1. **菜单层 Compose 化**：点击中屏浮现的菜单层（顶栏 `MenuTitleBar` + 底栏 `MenuBottomBar` + scrim 遮罩），替换现有 `read_menu` 自定义 View；AnimatedVisibility 浮现 + 3s 无操作自动淡出。
2. **activeSheet 单态收敛**：弹层区一次一个 activeSheet（sealed interface 枚举），杜绝 3 层嵌套；现有 `composeSheetHost` 改造为单态宿主。
3. **阅读设置 Sheet**（最高优先级，P2 §4）：字号/亮度/夜间/行距/对齐 + 扩展翻页/字体，用 `SettingsCard` 分组容器。
4. **BackHandler 优先级链**：弹层→搜索→自动翻页→菜单路由→退出阅读。
5. **ReaderUiState**：轻量单 StateFlow（menuVisible/activeSheet/activeDialog/routeStack/searchState）下发，替换散落 mutableBoolean。

### 不做（红线/后续）
- ❌ **正文零改动**：page/ 29 个文件 + ReadView 嵌入 + `menuLayoutIsVisible` 三信号 + 选区锚点坐标 `textMenuPosition` + insets 双轨 + 主题双事件线 + PageView 反向依赖 Activity，全部保留不动。
- ❌ 翻页手势 / 正文渲染 / 阅读引擎逻辑不迁移（N 不迁移内核）。
- ❌ 不做 P2 蓝图 R2 的 `ReaderBookSheet` 三 Tab 演进（敬畏现状 `BookTocBookmarkSheet` 双 Tab 基座）。
- ❌ `search_menu` 搜索层 Compose 化留到后续阶段（本骨架仅菜单层 + activeSheet 单态）。

### 影响模块
- 主要改动：`ui/book/read/ReadBookActivity.kt`、`ui/widget/components/`（新增 MenuTitleBar/MenuBottomBar/阅读设置 Sheet）。
- 不碰：`ui/page/`（29 文件）、ReadBook 单例业务逻辑。

## 3. Approach（方法）

### Selected Approach
在 `composeSheetHost`（已有 setContent）基础上，将菜单层与浮层整体 Compose 化：新增 `ReaderUiState` 单 StateFlow，`ReadBookActivity` 通过 `setContent` 承载 Compose UI，正文仍由 XML 里的 ReadView（AndroidView 桥接思想）垫底。弹层用 sealed interface 单态。

### Alternatives Considered
| 方案 | 否决理由 |
|------|---------|
| 全量重写 ReadBookActivity 为纯 Compose | 正文引擎是 AndroidView Canvas 排版，无法纯 Compose 承载，且 1875 行全重写回归风险不可控（P2 引用 MoRealm 教训：仿真翻页仍退回 AndroidView） |
| 逐弹窗独立 Dialog 继续叠加 | 已造成 3 层嵌套、Back 链混乱，与 P2「单态收敛」目标相悖 |
| 引入 DI / 新状态库 | 违反项目约束（object 单例 + 自定义 Coroutine 封装），不引入新依赖 |

### Drawbacks
- View+Compose 混合架构下，正文与 Compose 层的 z-order/insets 协调需谨慎，首次接线可能引入视觉层叠问题。
- 菜单层从自定义 View 迁移 Compose 是最高风险点（涉及阅读器核心交互），需真机逐步验证，不能一次全量替换。
- 接受理由：P2 已由 3 个开源 fork（HapeLee/MoRealm/legadoT）共同验证此范式成功，正文零改动红线可守住。

### Prior Art
- `forks-deep-dive.md §9/§10/§11/§12`：HapeLee AndroidView 桥接、MoRealm activeSheet 单态、legadoT DialogForm、youfeng Span 族。
- 项目内已成功样板：S1/S2/S3/S4/S6 骨架页（SettingsCard/AppModalBottomSheet 等公共组件复用）。

## 4. Requirements（需求）

- R1 菜单层：点击正文中屏浮现顶栏+底栏+scrim；3s 无操作自动淡出；点击 scrim 收起。
- R2 顶栏 `MenuTitleBar`：返回/书名/章节/换源/刷新/⋮ 操作项，磨砂（API31+ RenderEffect blur，低版本纯色降级）。
- R3 底栏 `MenuBottomBar`：上一章/进度 Slider/下一章 + 工具网格；贴底默认，悬浮药丸可配置。
- R4 阅读设置 Sheet：字号/亮度/夜间/行距/对齐一屏 + 扩展翻页/字体；`SettingsCard` 分组容器；滑块拖动时菜单 alpha≤30% 实时预览。
- R5 activeSheet 单态：sealed interface `ReadBookSheet` 全量枚举，一次只显示一个，无嵌套。
- R6 BackHandler 优先级链正确（弹层→搜索→自动翻页→菜单路由→退出）。
- R7 `ReaderUiState` 单 StateFlow 下发（menuVisible/activeSheet/activeDialog/routeStack/searchState）。
- R8 正文零改动红线 6 条全部守住（见 Scope 不做 + §8 验收）。
- R9 i18n：新文案 zh+en 双语，禁硬编码中文/色/字号。
- R10 组件全部来自 §3.4，无私有复制组件；交互元素触控 ≥48dp。

## 5. Scenarios（场景）

- **正常**：阅读中点击中屏 → 菜单层浮现 → 点「更多」→ 阅读设置 Sheet 弹出 → 调字号/亮度实时预览 → 关闭 → 菜单 3s 淡出。
- **正常**：点「目录」→ activeSheet=Toc 的 BookTocBookmarkSheet（双 Tab）弹出 → Back 关闭回正文。
- **异常**：菜单浮现时再点其它入口 → activeSheet 单态替换，不叠加；Back 链逐层回退。
- **边界**：进度 Slider 拖动至 70% 松手 → 提交 70% 不回弹（conflate+串行）；渲染回调 IO 线程一律 handler.post 切主线程。
- **边界**：正文渲染回调期间菜单交互 → 状态经 ReaderUiState 单 Flow 下发，无竞态。
