# spec.md — 我的页头部统一

## Intent

「我的」页（`MyFragment`）当前头部使用传统 XML `TitleBar`（AppBarLayout+Toolbar），与书架/订阅/发现三页共用的 `MainTopBarView` 顶栏组件观感不一致，且仅能跟随顶栏底色管理（bugfix ③），无法被顶栏设置 / 主题设置 / 样式管理全量控制（胶囊 / 圆角 / 壁纸 / 字号 / 搜索入口）。用户多次要求统一仍未生效。

本次将「我的」页头部迁移到 `MainTopBarView`（新增 `Mode.MY`），使四个主 Tab 页头部观感一致，且头部样式天然受 `TopBarConfig` + 主题 token + `TOP_BAR_CHANGED` 事件全量管理。

**本次三大铁律（用户明确要求）**：
1. **一套组件**：「我的」页与书架/订阅/发现共用同一 `MainTopBarView` 顶栏组件，彻底弃用 `TitleBar` 头部。
2. **可管理**：头部样式严格受「顶栏设置 / 主题设置 / 管理设置-样式管理」控制，不写死任何颜色/形状。
3. **功能不丢**：保留「我的」页设置项就地过滤搜索能力（`view_search`），入口迁移到顶栏搜索（`searchEntry`/`searchButton`）。

## Scope

### In-Scope（本次实现）

1. **布局**：`fragment_my_config.xml` 将 `TitleBar`（`title_bar`）替换为 `MainTopBarView`（`top_bar`）；`view_search` 由常显改为默认隐藏，由顶栏搜索入口触发展开。
2. **组件**：`MainTopBarView` 新增 `Mode.MY`，定义该模式下按钮可见性（`searchButton`/`moreButton` 可见，`filter/star/refresh/login` 隐藏）与标题字号。
3. **接线**：`MyFragment` 移除 `setSupportToolbar(binding.titleBar.toolbar)`，改为顶栏接线（`setMode(MY)`、标题、搜索入口、更多菜单）。
4. **搜索交互**：顶栏搜索入口（regular 风格 `searchEntry` 胶囊 / 默认风格 `searchButton`）点击 → 显示并聚焦就地 `view_search`，保留现有 `applySearchQuery` 过滤逻辑。
5. **刷新链路**：复用 `MainActivity.refreshMainTopBars` 对 `MainTopBarView` 的 `refreshStyle()` 刷新，无需额外事件接入。

### Out-of-Scope（本次不实现）

- 不改 `MySettingsScreen`（Compose 设置列表）内容与架构。
- 不迁移其他页面（书架/订阅/发现）已有实现。
- 不改 `TitleBar.kt`（子页面仍使用它，仅主界面「我的」页弃用）。
- 不引入新依赖、不改数据库 schema。

## Approach

### Selected Approach：顶栏组件复用 —— 将「我的」页迁移到 `MainTopBarView`，新增 `Mode.MY`

复用已被书架/订阅/发现验证的 `MainTopBarView` 顶栏体系，为「我的」页新增一个 `Mode.MY` 形态：

1. **组件**：`MainTopBarView.setMode` 增加 `Mode.MY` 分支——`moreButton` 可见（帮助菜单入口）、`searchButton` 可见（默认风格搜索入口）、标题字号 20f（与订阅/发现一致）。
2. **布局**：`fragment_my_config.xml` 将 `TitleBar` 换成 `MainTopBarView`（id=`top_bar`），`view_search` 默认 `gone`，保留 `pre_fragment`（Compose 列表）。
3. **接线**：`MyFragment` 移除 `setSupportToolbar`，在 `onFragmentCreated` 中接线 `topBar`（`applyStatusBarPadding`、`setMode(MY)`、`setTitle(我的)`、`setSearchHint`、`searchEntry/searchButton` 点击展开就地搜索、`moreButton` 点击帮助）。
4. **就地搜索**：新增 `showSettingsSearch()`——显示 `view_search` 并请求焦点；原有 `initSearchView`/`applySearchQuery` 过滤链路不动。

理由：与书架/订阅/发现共用同一组件后，「我的」页观感/体感与三者天然一致，且颜色/圆角/胶囊/壁纸/字号全部读取 `TopBarConfig` + 主题 token，被「顶栏设置/主题设置/管理设置」统一管理。改动集中在 1 个布局 + 1 个组件枚举分支 + 1 个 Fragment 接线，回归风险低。**这是用户确认的唯一方向（AskUserQuestion 已选「改用 MainTopBarView」）。**

### Alternatives Considered

| 方案 | 说明 | 否决理由 |
|------|------|---------|
| 保留 `TitleBar` 深度接入主题 | 扩展 `TitleBar.refreshTopBarAppearance` 同步顶栏管理的圆角/壁纸/字号/搜索入口等全部属性 | `TitleBar` 是通用子页组件，为其注入 `MainTopBarView` 全套视觉属性会污染所有子页面、改动面大；且观感仍可能有细微差异；用户已明确选择改用 `MainTopBarView` |
| 仅接入顶栏底色背景（现状） | 维持 bugfix ③ 已实现的 `topBarColorManaged` 背景色跟随 | 只能跟背景色，无法跟胶囊/圆角/壁纸/字号/搜索入口，用户实测多次不生效，明确不满意 |
| 新增一套全局 Compose 头部组件替换四页 | 抽统一 Compose 顶栏 | 书架/订阅/发现已用 View 层 `MainTopBarView` 且观感达标，再造 Compose 头部会引入双实现、放大工作量、风险高 |

### Drawbacks

- 顶栏高度变化：`MainTopBarView`（标题行 + 搜索入口）比原 `TitleBar` 略高，压缩 Compose 列表可视区。「我的」页为 `LinearLayout` 顺排，顶栏增高自然下推内容，无需覆盖式补偿；真机确认观感。
- 就地搜索框由常显改为「点击搜索入口后展开」：交互变化一次，用户需点击顶栏搜索图标/胶囊才出现过滤框。
- `TitleBar` 的 `setSupportToolbar` 移除后，`main_my` 菜单（帮助）需改为 `moreButton` 弹窗入口。
- 影响「发现经典」形态：`refreshMainTopBars` 中 `TitleBar` 分支（bugfix ③）仍保留，不影响子页面与发现经典。

接受上述缺点：换取与书架/订阅/发现完全一致的观感 + 可被主题设置全量管理，且复用已验证组件、改动量小、回归风险低。

### Prior Art

- 书架/订阅/发现三页当前实现：`BaseBookshelfFragment.initComposeTopBar()`（[BaseBookshelfFragment.kt#L100-L117](../../../app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt#L100-L117)）、`RssFragment`、`ExploreFragment` 均用 `MainTopBarView` 顶栏接线。
- 本项目标签统一设计文档：`docs/specs/tag-mode-unify/`（已验证 `MainTopBarView` 顶栏标签体系可用）。
- Rimchars archive：`temp/forks-comparison/Rimchars_legado/.../my/MyFragment.kt` —— 该 fork 的「我的」页同样用 `TitleBar`，非本需求参考目标；本需求目标是**内部四页统一**。

## Requirements

### 功能需求（FR）

- **FR-1** 「我的」页头部改用 `MainTopBarView`（`Mode.MY`），与书架/订阅/发现同一组件。
- **FR-2** 「我的」页头部样式可被顶栏设置 / 主题设置 / 样式管理全量管理：修改圆角 / 胶囊 / 壁纸 / 字号 / 搜索入口后，「我的」页跟随刷新（`TOP_BAR_CHANGED` → `refreshStyle()`）。
- **FR-3** 顶栏搜索入口（regular 风格 `searchEntry` 胶囊 / 默认风格 `searchButton`）点击后显示并聚焦就地 `view_search`，保留设置项就地过滤搜索能力。
- **FR-4** `moreButton`（更多）入口可触发「我的」页帮助（原 `main_my` 菜单的 `menu_help`）。
- **FR-5** 标题显示「我的」，搜索提示文案合理（如 `R.string.my` / 搜索设置项提示）。

### 非功能需求（NFR）

- **N1** 不引入新依赖，不改数据库 schema，不改 `MySettingsScreen`。
- **N2** 沿用现有协程/状态管理模式（Compose 内容 + View 层顶栏）。
- **N3** 无残留调试日志；编译通过；「我的」页关键交互（搜索展开/过滤/主题变更刷新）真机验证。
- **N4** updateLog 同步更新（编译前）。

## Scenarios

### 正常场景

1. 用户进入「我的」页：头部为 `MainTopBarView`（标题「我的」+ 搜索入口 + 更多按钮），与书架/订阅/发现观感一致。
2. 用户在顶栏设置修改圆角/胶囊/壁纸 → 四个 Tab 页头部同步刷新，「我的」页同样生效。
3. 用户点顶栏搜索入口 → 就地搜索框展开并聚焦 → 输入关键词 → 设置项实时过滤。
4. 用户点「更多」→ 弹出帮助入口 → 进入帮助页。

### 边界/异常场景

1. 顶栏设置/主题变更（`TOP_BAR_CHANGED`）：`MainTopBarView.applyTopBarStyle` 自动刷新，无 Compose 版本号依赖。
2. 搜索框关闭/清空：`applySearchQuery("")` 恢复全量设置项。
3. 「我的」页在 sidebar/standard 底栏模式下布局不受影响（`MainTopBarView` 自身状态栏 padding 处理）。
4. 切回「我的」页（`onResume`）：头部样式保持与主题一致，无需额外刷新。
