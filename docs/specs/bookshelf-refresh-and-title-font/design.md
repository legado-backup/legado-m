# Design：书架下拉刷新转圈不消失 + 顶栏标题字号不统一修复

## Technical Approach

### 问题1：刷新转圈不消失

**现状链路（缺陷）**：

1. `BookshelfFragment1.kt:131-138`（style2 同款于 `BookshelfFragment2.kt:113-120`）：`onRefresh` 中 `refreshing = true` → `activityViewModel.upToc(...)` → `lifecycleScope.launch { delay(1000); refreshing = false }`
2. `BookshelfScreen.kt:192-198`：`PullToRefreshBox(isRefreshing = isRefreshing, onRefresh = onRefresh)` 受控模式绑定
3. `MainViewModel.kt:120-128`：`upToc` 仅入队（`execute(upTocPool)` → `addToWaitUp` → `startUpTocJob`），无完成回调；逐本完成 `postEvent(EventBus.UP_BOOKSHELF)`，书架未消费
4. `MainViewModel.kt:160-174`：`upTocJob = viewModelScope.launch(upTocPool)`，队列排空后 `upTocJob = null`（174 行）——这是唯一权威的"刷新完成"信号点

**目标链路（修复）**：

1. `MainViewModel`：新增 `private val _upTocIdle = MutableStateFlow(true)`，公开 `val upTocIdle: StateFlow<Boolean>`；`upToc()` 入队时置 false，`upTocJob = null` 排空处置 true（`cacheBookJob` 路径不置 false，只跟踪 upToc 队列语义）
2. `BookshelfFragment1/2` 的 `onRefresh` 改为：

```kotlin
onRefresh = {
    refreshJob?.cancel()
    refreshing = true
    activityViewModel.upToc(currentBooks, onlyUpdateRead)
    refreshJob = viewLifecycleOwner.lifecycleScope.launch {
        val idle = withTimeoutOrNull(5000) {
            activityViewModel.upTocIdle.first { it }
        }
        if (idle != null) {
            activityViewModel.upTocConsumed()   // 消费型复位，见 AD-02
        }
        refreshing = false
    }
}
```

3. `refreshing` 保持 `viewLifecycleOwner` 关联的 `mutableStateOf`（若现状为 Fragment 级成员需迁移，实施时核实）；`refreshJob` 为视图级可空 Job 成员

### 问题2：标题字号统一（全顶栏族排版归位）

**全仓普查结论**（两轮扩查，用户质疑驱动）：

| 顶栏组件 | 覆盖页面 | 字号 | 字重 | 判定 |
|---------|---------|------|------|------|
| `MainTopBarView`（非书架 Mode） | 订阅/我的/阅读记录/发现 | 20f | View 默认 | 基线 ✓ |
| `MainTopBarView` BOOKSHELF 特判（:187） | 书架 | **24f** | View 默认 | ❌ 唯一字号违规 |
| `GlassTopAppBar`（:120-137） | 一般 Compose 子页 | titleLarge=20sp | Medium | 基线 ✓ |
| `ConfigTopBar`（ConfigActivity.kt:244-253） | 备份与恢复等全部设置子页 | titleLarge.fontSize=20sp ✓ | **SemiBold 覆写** | ⚠️ 字重漂移 |
| `AppManagementScaffold`（:188-199） | 书源/订阅源/替换规则/订阅规则/书架分组 | **subtitleLargeX=19sp** | **SemiBold** | ❌ 双漂移 |
| `TitleBar`（View 子页，MaterialToolbar） | 传统子页 | 默认 20sp | 默认 | 基线 ✓ |

豁免（历史裁决）：阅读器/视频播放器顶栏（T7）、欢迎页 49sp 品牌大字、弹框/卡片标题。

修复（三处归位到 `LegadoTypography.titleLarge` = 20sp/Medium 基线，AD-19 既有基线非新选值）：

1. `MainTopBarView.kt:187`：`if (mode == Mode.BOOKSHELF) 24f else 20f` → `20f`
2. `ConfigTopBar` 标题 Text（ConfigActivity.kt:244-253）：删除 `fontSize = MaterialTheme.typography.titleLarge.fontSize` 与 `fontWeight = FontWeight.SemiBold` 两行覆写，改为 `style = MaterialTheme.typography.titleLarge`，保留 `color = palette.primaryText` 与 `fontFamily = palette.titleFontFamily`
3. `AppManagementScaffold` 标题 Text（AppManagementScaffold.kt:188-199）：`fontSize = subtitleLargeX.fontSize` + `fontWeight = SemiBold` → `style = MaterialTheme.typography.titleLarge`，保留 `fontFamily = palette.settings.titleFontFamily` 与配色

### 问题3：右侧图标按钮尺寸统一（用户裁决：统一 20dp）

普查实锤四层四规格（含图标资产风格）：

| 顶栏 | 行高 | 按钮容器 | 图标绘制 | 图标资产 |
|------|------|---------|---------|---------|
| `MainTopBarView`（主 Tab） | — | 34dp（dimen `bookshelf_action_button_size`，Archive 对齐） | ~18dp（CENTER_INSIDE + 8dp padding） | 自绘 ic_*.xml |
| `GlassTopAppBar`（子页，:144-149） | 64dp（M3 TopAppBar 默认） | 48dp（M3 IconButton） | 24dp（M3 默认） | 调用方传入 |
| `ConfigTopBar`（设置子页，:254-277） | 56dp | 48dp（M3 IconButton） | 24dp（M3 默认） | M3 imageVector |
| `AppManagementScaffold`（5 管理页，`AppManagementIconAction` AppSettingComponents.kt:599-617） | 48dp | 36dp | 20dp | 自绘 ic_*.xml |

修复：`GlassTopAppBar` 的 nav/action Icon 与 `ConfigTopBar` 的 primaryActions/MoreVert Icon 统一加 `Modifier.size(20.dp)`（24→20dp，观感与管理页/主 Tab 拉齐）；`AppManagementScaffold` 20dp 保持；主 Tab 34dp 容器豁免（Archive 对齐既定值）。IconButton 容器尺寸不动，点击热区不受影响。

"粗细"差异根因 = 图标资产描边（自绘 vector 描边宽度各异 vs M3 Icons 标准描边），统一需全量梳理 ic_*.xml 资产，**登记 issue-list 独立专项**，本任务不实施。

**规范沉淀**（用户指令）：普查终版 + 基线口径沉淀到 `docs/project-flow/ui-standards/spacing-corner-typography.md`（顶栏标题排版基线 + 顶栏图标按钮基线小节），后续顶栏开发/审查按规范执行。

## Architecture Decisions

### AD-01: 复位信号采用 MainViewModel 队列空闲 StateFlow 而非 EventBus 事件
- **Context**: 书架刷新经 `MainViewModel.upToc` 投入池化异步更新队列，逐本完成 post `UP_BOOKSHELF` 事件，但事件不含"队列是否排空"信息
- **Concern**: 复位动画需要权威的"全部更新完成"信号
- **Decision**: 在 `MainViewModel` 增加 `upTocIdle: StateFlow<Boolean>`，以 `upTocJob` 生命周期为信号源（入队 false / 排空 true）
- **Goal**: 转圈寿命与真实刷新完成对齐，信号可被 `first{}` 挂起消费
- **Tradeoff**: `MainViewModel` 公开面增加一个 StateFlow；接受，改动小且语义清晰
- **Status**: Proposed

### AD-02: idle 信号采用"消费型复位"避免残留脏状态
- **Context**: 若上次刷新排空后 `upTocIdle` 停留 true，下次刷新时序为 `upToc()` 置 false 之前，`onRefresh` 中 `first{}` 可能先读到旧 true 立即复位（竞态）
- **Concern**: `upToc()`（viewModelScope 异步）与 `onRefresh`（UI 线程）的执行顺序不保证
- **Decision**: `onRefresh` 在启动协程前显式复位信号（或在 `upToc()` 返回前同步置 false，实施时按最小改动择一），确保 `first{}` 等待的是本次刷新的排空事件；同时 5s `withTimeoutOrNull` 兜底保证任何信号丢失下转圈必收回
- **Goal**: 消除"读到上一次的 true"竞态；信号异常时不永久滞留
- **Tradeoff**: MainViewModel 需暴露一个消费/复位方法或采用同步置位；接受，均为单点小改动
- **Status**: Proposed

### AD-03: 复位协程迁移 viewLifecycleOwner.lifecycleScope + 单一 Job 管理
- **Context**: 现状 `lifecycleScope.launch { delay(1000); refreshing = false }` 挂 Fragment 级 scope，页面销毁时协程被取消导致 `refreshing` 冻结 true；重复下拉会产生多个并发复位协程
- **Concern**: 生命周期冻结与并发竞态
- **Decision**: 复位协程改挂 `viewLifecycleOwner.lifecycleScope`，用单一 `refreshJob` 成员管理（新刷新先 cancel 旧协程）；`refreshing` 状态归属视图生命周期
- **Goal**: 视图销毁即取消复位逻辑且不展示冻结状态；连续刷新无竞态
- **Tradeoff**: 无；纯正确性修正
- **Status**: Proposed

### AD-04: 标题字号去特判统一 20sp，不纳入 TopBarConfig 主题体系
- **Context**: `MainTopBarView.kt:187` 按 Mode 硬编码 24/20sp；全仓普查实锤：`LegadoTypography.titleLarge = 20sp`（LegadoTheme.kt 注释"对齐 View ToolbarTitle 20sp，主题统一 AD-19"）、`GlassTopAppBar` 用 `titleLarge`=20sp、子页 `TitleBar`（MaterialToolbar 默认 ToolbarTitle）=20sp、`MainTopBarView` 其余 Mode 均 20f——全 App 顶栏标题基线 20sp 为主题规范既定值，书架 24sp 是唯一违规孤例
- **Concern**: 统一字号的最小改动 vs 主题化架构改动
- **Decision**: 删除 `Mode.BOOKSHELF` 特判统一 20f，即回归主题规范 AD-19 既有基线，非新选数值；不新增 TopBarConfig 字号字段
- **Goal**: 书架对齐全 App 主题排版基线，改动一行可验证
- **Tradeoff**: 放弃字号主题化能力；接受——基线已统一且无差异化消费方，未来有需求再扩展（升级路径：TopBarConfig 加字段 + applyTopBarStyle 消费）
- **Status**: Proposed

### AD-05: material3 受控 PullToRefreshBox 竞态不通过升级 BOM 解决
- **Context**: composeBom 2025.04.01（material3 1.3.2）受控模式存在指示器收回竞态的已知问题；BOM 版本升级影响全 App
- **Concern**: 根因 A/B 修复后是否仍残留指示器滞留
- **Decision**: 主因修复后真机观察；若竞态仍复现，单独立项评估 BOM 升级或 `PullToRefreshState` 手动控制，不在本任务内升级版本
- **Goal**: 控制本次改动影响面
- **Tradeoff**: 竞态风险延后处理；接受——主因（冻结 true + 脱钩）已消除，竞态为小概率叠加因素
- **Status**: Proposed

### AD-06: 顶栏标题字重统一 Medium，删除 ConfigTopBar/AppManagementScaffold 的 SemiBold 覆写
- **Context**: 全仓普查发现三处排版漂移：书架 24sp、ConfigTopBar 20sp+SemiBold（用户实感"备份与恢复字大"主因）、AppManagementScaffold 19sp+SemiBold（5 管理页）；`LegadoTypography.titleLarge = 20sp/Medium` 为 AD-19 既有基线，GlassTopAppBar 与 View TitleBar 均已对齐
- **Concern**: 顶栏族排版跨页不一致，且无任何设计文档支撑差异化
- **Decision**: 三处全部归位 `MaterialTheme.typography.titleLarge`（20sp/Medium）；保留各顶栏 palette 字体族与配色消费不变；不新增 TopBarConfig 排版字段
- **Goal**: 全 App 顶栏标题"一套排版基线"，用户跨页无感知跳变
- **Tradeoff**: 管理页标题 19→20sp、字重 600→500，视觉略轻；接受——统一性优先，且基线是主题规范既定值；升级路径：未来需要差异化时经 TopBarConfig 扩展并全族一致消费
- **Status**: Proposed

### AD-07: 顶栏图标绘制尺寸统一 20dp，主 Tab 34dp 容器豁免，粗细专项登记
- **Context**: 右侧图标按钮四层四规格（主 Tab 34dp/~18dp、GlassTopAppBar 48dp/24dp、ConfigTopBar 48dp/24dp、AppManagementScaffold 36dp/20dp），用户实感"大小+粗细不一致"
- **Concern**: 完全统一受行高物理约束（34~64dp），且粗细属图标资产层影响全 App
- **Decision**（用户裁决 2026-08-28）: GlassTopAppBar/ConfigTopBar 图标 24→20dp（两处组件内收敛）；AppManagementScaffold 20dp 保持；主 Tab 豁免（Archive 对齐既定 dimen）；IconButton 容器不动保热区；粗细=图标资产描边专项登记 issue-list
- **Goal**: 跨页图标观感一致，改动收敛在 2 个顶栏组件内
- **Tradeoff**: 子页/设置页图标缩小 17%；接受——与全族观感一致优先；20dp 档为四层中两族既有值，改动面最小
- **Status**: Proposed

## Data Flow

修复后刷新数据流：

1. 用户下拉 → `PullToRefreshBox` 触发 `onRefresh`（BookshelfScreen 受控绑定）
2. Fragment：cancel 旧 `refreshJob` → `refreshing = true` → `activityViewModel.upToc(...)` 入队 → 启动复位协程挂 `viewLifecycleOwner.lifecycleScope`
3. MainViewModel：`upToc()` 置 `upTocIdle = false` → 更新池逐本更新 → 排空 `upTocJob = null` 处置 `upTocIdle = true`
4. 复位协程：`upTocIdle.first { it }`（5s 超时兜底）→ `refreshing = false` → 指示器收回
5. 视图销毁 → 复位协程随 viewLifecycle 取消 → 无冻结展示

字号链路无数据流变化：`setMode()` → `titleText.textSize = 20f`（原 24f 分支删除）。

## File Changes

| 文件 | 变更类型 | 变更内容 |
|------|---------|---------|
| `app/src/main/java/io/legado/app/ui/main/MainViewModel.kt` | 修改 | 新增 `upTocIdle: StateFlow<Boolean>` + 信号置位/复位逻辑（upToc 入队 / upTocJob 排空点） |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/style1/BookshelfFragment1.kt` | 修改 | `onRefresh` 复位逻辑重写（AD-02/AD-03），新增 `refreshJob` 成员 |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/style2/BookshelfFragment2.kt` | 修改 | 同 BookshelfFragment1（113-120 行同款逻辑） |
| `app/src/main/java/io/legado/app/ui/widget/MainTopBarView.kt` | 修改 | 187 行去除 `Mode.BOOKSHELF` 24sp 特判，统一 20f（AD-04） |
| `app/src/main/java/io/legado/app/ui/config/ConfigActivity.kt` | 修改 | `ConfigTopBar` 标题改 `style = titleLarge` 删 SemiBold 覆写（AD-06）；action/MoreVert 图标加 `size(20.dp)`（AD-07） |
| `app/src/main/java/io/legado/app/ui/widget/components/GlassTopAppBar.kt` | 修改 | nav/action 图标加 `size(20.dp)`（AD-07） |
| `app/src/main/java/io/legado/app/ui/widget/compose/AppManagementScaffold.kt` | 修改 | 顶栏标题改 `style = titleLarge`，19sp/SemiBold → 20sp/Medium（AD-06） |
| `docs/project-flow/ui-standards/spacing-corner-typography.md` | 文档 | 沉淀顶栏标题排版基线（20sp/Medium）+ 顶栏图标按钮基线（20dp 档）+ 四层普查终版（AD-06/AD-07 配套规范） |

不改动：`BookshelfScreen.kt`（受控绑定不变）、`TopBarConfig.kt`、`LegadoTheme.kt`（基线本身就是权威）、`MainTopBarView` 图标尺寸（豁免）、ic_*.xml 图标资产（粗细专项）、依赖版本。
