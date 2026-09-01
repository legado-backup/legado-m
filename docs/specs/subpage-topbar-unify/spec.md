# spec.md — 子页面头部统一：全 App TitleBar 子页迁移 MainTopBarView

## Intent

四主页面（书架/订阅/发现/我的）头部已统一为 `MainTopBarView`，受主题 / 顶栏设置全量管理。但全 App 约 18 个子页面 Activity 仍在布局中使用传统 `TitleBar`（[TitleBar.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/widget/TitleBar.kt)），其 `topBarColorManaged` 默认 `false`，仅在显式开启时跟随顶栏 **背景色**，无法被圆角 / 壁纸 / 胶囊 / 字号 / 搜索入口等顶栏全套样式管理；且另有一部分页面头部用 `MaterialToolbar` 或 Compose 自绘，形成**多套不同样式**并存。

用户明确要求：**全 App 所有 `TitleBar` 子页面头部统一，并迁移到 `MainTopBarView`**，使子页面头部同样受主题设置 / 顶栏设置 / 样式管理统一管控，消除多套样式。

## Scope

### In-Scope（本次实现）

1. **组件扩展**：`MainTopBarView` 新增通用子页面形态（新增 `Mode.SUB` 或等效机制），补齐子页面头部所需能力：
   - 返回导航（左上返回箭头，代替原 `TitleBar` 的 `navigationIcon` + `onSupportNavigateUp`）。
   - 菜单（原 `about:blank` 等 Activity 用 `setSupportActionBar` 挂的 overflow 菜单，改由 `MainTopBarView` 承载）。
   - 副标题（`TitleBar.subtitle` 场景）。
   - 自定义内容插槽（原 `TitleBar.contentLayout`）。
2. **布局迁移**：将使用 `io.legado.app.ui.widget.TitleBar` 的子页面布局 XML 的头部替换为 `MainTopBarView`。
3. **代码接线**：对应 Activity / Fragment 移除 `setSupportActionBar(binding.titleBar.toolbar)`，改为 `MainTopBarView` 接线（返回、菜单、标题、副标题、内容）。
4. **样式一致**：子页面头部观感与主页面一致，颜色 / 圆角 / 胶囊 / 壁纸 / 字号全部读取 `TopBarConfig` + 主题 token，被顶栏设置 / 主题设置 / 样式管理全量管理。

### Out-of-Scope（本次不实现）

- **`MaterialToolbar` 弹窗**（`dialog_*.xml`，约 18 处）：弹窗头部语义与页面顶栏不同，不迁移。
- **非 `TitleBar` 布局**：Compose 自绘页面头部、`fragment_explore`（发现经典主 Tab 变体）等不属「子页面 TitleBar」范畴，单独评估。
- **`TitleBar.kt` 组件删除**：迁移完成并验证后再评估废弃；过渡期保留以防回退。
- 不引入新依赖、不改数据库 schema。

## Approach

### Selected Approach：扩展 `MainTopBarView` 增加通用子页形态，按页面批量迁移

复用已验证的 `MainTopBarView` 体系，新增一个「子页」形态（`Mode.SUB`），为其补齐返回 / 菜单 / 副标题 / 自定义内容能力，再按**页面优先级分批**将 TitleBar 子页面迁移过去：

1. **组件**：`MainTopBarView` 新增 `Mode.SUB`：
   - `titleSelect`（标题 + 向下箭头）在子页态改为「标题 + 返回箭头」，点击返回（复用宿主 `onBackPressed`）。
   - 暴露 `setMenu` / `setSubtitle` / `setContentLayout` API，替代 `TitleBar` 对应能力。
   - `setMode(Mode.SUB)` 中按钮可见性按子页语义配置（默认更多按钮隐藏，由页面按需 `setActionsVisible`）。
2. **迁移批次**（每批 = 一类相似页面，迁移后立即编译 + 真机回归）：
   - **批次 A（列表/管理页）**：`activity_book_source`、`activity_rss_source`、`activity_cache_manage`、`activity_read_record`、`activity_theme_manage`。
   - **批次 B（编辑页）**：`activity_book_source_edit`、`activity_paragraph_rule_edit`、`activity_replace_rule`、`activity_rule_sub`、`activity_ai_image_provider_edit`。
   - **批次 C（详情/杂项）**：`activity_about`、`activity_explore_show`、`activity_cover_collection_detail`、`activity_cover_collection_manage`、`activity_s3_container_manage`、`activity_source_debug`、`activity_ai_image_gallery`。
3. **接线规范**：统一从 `Activity` 移除 `setSupportActionBar`，改用 `topBar.setMode(Mode.SUB)` + `topBar.setNavigationOnClick` / 菜单 API；返回键与 `onBackPressedDispatcher` 对接。
4. **刷新链路**：复用 `MainTopBarView.refreshStyle()` / `TOP_BAR_CHANGED` 事件，子页面头部随主题变更自动刷新。

理由：同一组件后，子页面与主页面观感天然一致、全量受主题管理；`Mode.SUB` 使子页差异收敛在组件内；分批迁移降低单次回归面。

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 增强 `TitleBar` 完整接入主题 | 给 `TitleBar` 注入 `MainTopBarView` 全套视觉属性（圆角/壁纸/胶囊/字号/搜索入口） | `TitleBar` 是 AppBarLayout 体系，难支持 backgroundLayer 壁纸/胶囊图层；为单一组件注入全套属性污染所有 `TitleBar`；与主页面仍有观感差异 |
| 仅让子页面 `TitleBar` 跟随顶栏背景色 | 扩展 `topBarColorManaged` 默认开启 | 只能跟背景色，无法跟圆角/壁纸/胶囊/字号/搜索入口，观感仍不一致（bugfix③早已存在，用户明确不满意） |
| 新建独立 Compose 子页头部组件 | 抽一套 Compose 头部覆盖子页 | 与主页面 `MainTopBarView` 双实现，观感难保证一致；重构面积大 |

### Drawbacks

- **迁移面大**：约 18 个 Activity + 布局 + 接线，需分批进行、逐批编译与真机回归，工期长、回归风险高。
- **`setSupportActionBar` 移除**：依赖系统 ActionBar / `onSupportNavigateUp` 的页面需改写返回与菜单接线，个别页面（菜单项多、需层级返回）改造工作量大。
- **`MainTopBarView` 增高**：子页头部（标题行 + 标签行）可能比原 `TitleBar` 略高，压缩正文可视区，需真机确认。
- **过渡期双组件并存**：`TitleBar.kt` 保留（部分弹窗/页面仍用），维护成本短期上升。

接受上述缺点，换取「子页面与主页面观感完全一致 + 全量受主题管理」，且复用已验证组件、无新增依赖。

### Prior Art

- 主页面（书架/订阅/发现）实现：`BaseBookshelfFragment.initComposeTopBar()`（[BaseBookshelfFragment.kt L100-L117](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt#L100-L117)）、`RssFragment`、`ExploreFragment` 均用 `MainTopBarView`。
- 「我的」页主入口迁移：`docs/specs/my-topbar-unify/`（`Mode.MY`，已验证主 Tab 页迁移可行）。
- 标签体系统一：`docs/specs/tag-mode-unify/`。

## Requirements

### 功能需求（FR）

- **FR-1** `MainTopBarView` 新增通用子页形态（`Mode.SUB` 或等效），支持返回 / 菜单 / 副标题 / 自定义内容。
- **FR-2** 全 App 所有 `TitleBar` 子页面头部迁移到 `MainTopBarView`，观感与主页面一致。
- **FR-3** 子页面头部样式受顶栏设置 / 主题设置 / 样式管理全量管理（改圆角/胶囊/壁纸/字号/搜索入口后跟随刷新），无硬编码颜色。
- **FR-4** 子页面的返回导航、菜单、副标题、自定义内容行为不丢（功能等价迁移）。
- **FR-5** 迁移过程分批交付，每批编译通过且目标页面真机回归通过。

### 非功能需求（NFR）

- **N1** 不引入新依赖、不改数据库 schema。
- **N2** 无残留调试日志；`TitleBar.kt` 在全部迁移后评估废弃（不在本次强制删除）。
- **N3** updateLog 同步更新（编译前）。
- **N4** 迁移不改变子页面原有业务逻辑（仅头部壳层替换）。

## Scenarios

### 正常场景

1. 用户进入「书源管理」：头部为 `MainTopBarView`（返回箭头 + 标题 + 菜单），与主页面观感一致。
2. 用户改顶栏设置（圆角/壁纸/胶囊）→ 所有子页面头部同步刷新（含已迁移页面）。
3. 用户点返回箭头 → 回到上一级页面（`onBackPressedDispatcher`）。
4. 用户点菜单 → 弹出 `TitleBar` 迁移前的等价菜单项。

### 边界/异常场景

1. 首页/末页返回：子页面返回箭头行为与系统返回一致（无残留 Activity 栈问题）。
2. 夜间/日间主题切换：子页面头部颜色、字号自动刷新。
3. 旧包覆盖安装：已迁移页面无 `setSupportActionBar` 残留导致的空白/崩溃。
4. 编辑类页面（`activity_book_source_edit`）头部含自绘扩展区：`Mode.SUB` 自定义内容插槽承载，观感与未迁移前等价。

## X2 互斥门禁：与 compose 整页迁移名单交叉核查（2026-09-01）

总线 master-track-orchestration tasks 2.14 交叉核查：本 spec 批次 A/B/C 页名单（17 项）与 compose-migration-status-audit B4 待迁页 7 项（B5 AllBookmark / B14 ExploreShow / B15 StorageManage / D2 RssSourceEdit / D3 RssSourceDebug / D5 RssSearch+ArticleInfo / D7 RssFavorites）求交集，**唯一命中 `activity_explore_show`（ExploreShowActivity，批次 C 4.2）**。

**门禁声明（ExploreShowActivity）**：该页列入 compose 整页迁移名单（compose B4-c），禁止对其实施独立的 View 顶栏改动（避免双改冲突），顶栏改造随整页 Compose 迁移一并落地。实况注记：本 spec 4.2 的 MainTopBarView(Mode.SUB) 替换已先期完成（编译通过，真机回归待设备），compose 侧整页迁移实施时须以该现状为输入，将顶栏一次性收敛为 Compose 头部；4.2 真机回归结论应同步抄送 compose spec registry 作为迁移输入基线。

其余 6 项经核查不在本 spec 页名单（D3 RssSourceDebugActivity 布局为 `activity_rss_source_debug`，与 4.6 `activity_source_debug` = BookSourceDebugActivity 非同页），无互斥约束。