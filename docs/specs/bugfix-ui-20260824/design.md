# bugfix-ui-20260824 技术设计

## Technical Approach

### ① 订阅源/书源/文件夹列表图片四角圆弧

**现状**（源码核实 + 用户真机确认 + 深度调研）：

`RssArticlesFragment` 按 `articleStyle` 切换 5 种布局（映射表）：

| articleStyle | 名称 | Adapter | Item 布局 | LayoutManager | 图片圆角 |
|---|---|---|---|---|---|
| 0 | 列表 | RssArticlesAdapter | item_rss_article.xml | Linear | ❌（带 16dp 左 padding） |
| 1 | 单列 | RssArticlesAdapter1 | item_rss_article_1.xml | Linear | ❌（带 12dp 三向 padding） |
| 2 | 双列 | RssArticlesAdapter2 | item_rss_article_2.xml | Grid(2) | ❌（bg_img_border 1dp 直角边框） |
| 3 | 瀑布 | RssArticlesAdapter3 | item_rss_article_3.xml | Staggered | ⚠️ CardView 12dp 圆角卡片，但**不裁剪子 View** |
| 4 | 三列 | RssArticlesAdapter4 | item_rss_article_4.xml | Grid(3) | ❌（bg_img_border 1dp 直角边框） |

UI 设置入口：订阅源编辑页 `ly_type` Spinner（activity_rss_source_edit.xml）+ 文章列表"切换布局"菜单（RssSortViewModel.switchLayout）。

**方案**：无圆角 4 布局（style 0/1/2/4）的 ImageView 替换为 `FilletImageView`（`app:radius="12dp"`）。

**阻塞点与处理**：
1. **padding 冲突（style 0/1，必须处理）**：`FilletImageView` 的 onDraw 用 `getWidth()/getHeight()`（含 padding）画 clipPath，图片绘制在 padding 内缩区 → **ImageView 自带非零 padding 时四角仍直角**。`item_rss_article.xml` 16dp 左 padding、`item_rss_article_1.xml` 12dp 三向 padding 必须改为 margin/父容器间距。
2. **background 直角不跟随（style 2/4）**：`bg_img_border`（corners=1dp）在 clip 前绘制，方形边框不随圆角 → 移除该 background 或替换为 12dp 圆角边框 drawable。
3. **CardView 不裁剪子 View（style 3）**：CardView 默认不自动 clipToOutline，瀑布 ImageView 四角可能仍直角盖在圆角卡片上 → 给 item_rss_article_3.xml CardView 加 `android:clipToOutline="true"`（对齐 item_search_waterfall.xml 先例）；或改用 FilletImageView。真机确认后定。
4. **radius 默认 5dp**：每个替换节点必须显式 `app:radius="12dp"`。
5. **绑定代码**：子 Adapter 用 ViewBinding 且无 ImageView 类型强转，FilletImageView extends AppCompatImageView 全兼容，绑定代码零改动。
6. **layout-land 变体**：`layout-land/item_rss_article_3.xml` 与竖屏结构一致，同步处理。
7. 范围外：`item_rss_article_info_source.xml` 不属本列表 Adapter 绑定，不动。

### ② 搜索框样式统一

**现状**（源码核实）：
- 订阅经典形态：`composeSearchBar` + `SettingsSearchBar`（Compose BasicTextField，40dp 高，surfaceVariant 浅底，AppShapes.Button 圆角）
- 发现经典形态：`titleBar` 内嵌 View `SearchView`（`bg_searchview` 35dp 全胶囊形）
- 书架/发现现代：`MainTopBarView` searchEntry 搜索入口（`TopBarSearchStyle` 18dp 圆角）
- 书源管理：`AppManagementScaffold` 顶部搜索框

**方案**：以 archive 订阅头部 searchEntry 的 **18dp 圆角**为统一口径，收窄为同一组件样式（SettingsSearchBar 风格 Compose 浅底 40dp）。

**根因**：`SettingsSearchBar` 用 `AppShapes.Button`(12dp)、发现经典 `bg_searchview` 用 35dp 全胶囊形，与 archive 18dp 均不一致 → 各页搜索框观感发散。

**实施**：
```kotlin
// AppShapes.kt 新增 18dp 搜索 token
val Search: RoundedCornerShape = RoundedCornerShape(18.dp)
// SettingsSearchBar.kt：Button(12dp) → Search(18dp)
.background(MaterialTheme.colorScheme.surfaceVariant, AppShapes.Search)
// bg_searchview.xml：corners 35dp → 18dp（发现经典 SearchView 同步）
```

**影响范围**：订阅经典（RssFragment composeSearchBar）、发现经典（SearchView）、书源管理（AppManagementScaffold/SettingsSearchBar）；现代 MainTopBarView 已是 18dp 无需动。

### ③ 顶栏管理颜色头部生效（ADR-01）

**现状**：
- 读 `TopBarConfig` 的：书架 `BaseBookshelfFragment`、发现现代 `ExploreFragment.topBar`、订阅 `RssFragment.topBar`、阅读记录 `ReadRecordFragment.topBar`（均 MainTopBarView）
- 不读 `TopBarConfig` 的：我的 `MyFragment`（`TitleBar` + `view_search`）、发现经典 `ExploreFragment.titleBar`（`TitleBar` + `view_search`）

**方案**：见 ADR-01，用户决策后实施。

### ④ 订阅布局分组模式视图设置生效

**根因**：`RssFragment.applyListView()` / `applyFolderView()` / `initFolderComposeView()` 均用 `SourceFolderAdapter.calculateSpanCount()`（90dp 卡片屏幕自适应），**不读 `AppConfig.sourceLayout`** → 网格列数设置（Grid2-6）无效。

**修复**：
```kotlin
// 新增统一列数计算：sourceLayout 2-6 显式指定列数；0/1（列表/紧凑列表，订阅源无此语义）回退屏幕自适应
private fun effectiveSpanCount(): Int {
    val layout = AppConfig.sourceLayout
    return if (layout in 2..6) layout
    else SourceFolderAdapter.calculateSpanCount(requireContext(), AppConfig.sourceMargin)
}
```
三处（applyListView/applyFolderView/initFolderComposeView）改用 `effectiveSpanCount()`。

**文案**：`values/strings.xml` `source_group_mode_folder` = "分组" → "文件夹"（检查 values-zh 是否覆盖）。

### ⑤ 经典订阅切回头部标签销毁

**根因**：`applyClassicRssMode()` → `initComposeTopBar()` 未清空现代形态设置的 `primaryBar`（源标签）/`tagsBar`（分类标签）。

**修复**：`initComposeTopBar()` 开头清空：
```kotlin
binding.topBar.setPrimaryItems(emptyList(), -1)
binding.topBar.tagsBar.submitItems(emptyList(), -1)
binding.topBar.showTags(false)
```
（参考 ExploreFragment L3197-3201 清空范式）

### ⑥ 我的-工具与相关文件管理重复入口

**现状**：`MyFragment.buildSections()` L460 `actionRow("fileManage", R.string.file_manage, ...)`；`PreciseManageFragment` 已聚合文件管理（`onFileManageClick → FileManageActivity`）。

**修复**：删除 L460 的 fileManage 行。保留精准管理内入口。

### ⑦ 关于页头部软件名

**根因**：`activity_about.xml` 头部 `app_name_sigma`；`values-zh/strings.xml` L1938 `app_name_sigma = 阅读Archive`。

**修复**：`values-zh/strings.xml` `app_name_sigma` → "阅读M"（`values/strings.xml` 已是"阅读M"）。检查 values-zh-rHK 等变体。

### ⑧ 欢迎页标题

**根因**：`WelcomeScreen.kt` 标题用 `welcome_title`；`values-zh/strings.xml` L264 `welcome_title = 阅读`。

**修复**：`values-zh/strings.xml` `welcome_title` → "阅读M"（`values/strings.xml` "Read" 保持英文默认）。

### ⑨ 前端 UI 规范沉淀子规范

**现状**（源码核实）：
- `docs/project-rules/` 下**无**前端 UI 规范文档（23 个规范文件均为后端/流程/测试类）
- `docs/specs/ui-redesign-m3/ui-standards.md` 属自研增量 Compose 化（ui-redesign-m3）旧规范，其组件六族/页面骨架基于自研实现，未反映 archive 整体迁移后的实际 UI 架构（MainTopBarView/SourceFolderConfigDialog/GlassTopAppBar 等）

**方案**：基于 archive 迁移后的实际 UI 架构，新建子规范 `docs/project-rules/frontend-ui-standards.md`，沉淀：
1. 页面骨架：S1 主框架（PillNavigationBar/底部栏）/ S2 列表管理页（GlassTopAppBar + SettingsSearchBar）/ S3 表单编辑 / S4 详情 / S5 阅读器（View 内核红线）/ S6 弹层
2. 组件六族（archive 版）：TopBar（MainTopBarView/TitleBar 选用原则）、列表项、卡片、菜单（ModernActionPopup）、Dialog（ComposeDialog 家族）、搜索框（SettingsSearchBar 统一）
3. 主题接入：LegadoTheme/ThemeSpec/TopBarConfig 使用规范
4. 状态管理范式：Compose state 单态、协程 Coroutine.async 链式
5. 改造/新建页面检查清单：真机功能点覆盖门禁

登记：`docs/INDEX.md`（项目规范表）+ `AGENTS.md` 子规范加载表（前端/UI 改造任务加载该规范）。

**实施结果**（2026-08-24）：已新建 `docs/project-rules/frontend-ui-standards.md`，覆盖：①设计 Token（AppShapes/UiCorner/字号/TopBarConfig/ThemeSpec）②页面骨架 S1-S6 分型 ③组件六族选用规则 ④View/Compose 混用红线 ⑤新页面改造检查清单 ⑥已知坑速查。已登记 docs/INDEX.md + AGENTS.md 子规范加载表。

### ⑩ debug 包体积分析与精简

**现状**（APK 实测分析）：
- debug 包 3.26.082317 = **74.88MB**（zip 压缩后 72.22MB）；release 包 3.26.081714 = **26.99MB**
- debug 未压缩构成：`classes*.dex` 合计 **130MB**（最大 classes21.dex 31.38MB / classes.dex 24.42MB）——**无 R8 混淆是 debug 体积主因**（debug 构建固有，需保留可调试性）
- so 库：`libcronet.151.0.7922.47.so` arm64 6.82MB + armeabi-v7a 4.09MB；`libarchive-jni.so` 1.94+1.51MB；`librenderscript-toolkit.so` 0.49+0.33MB
- 资源：`resources.arsc` 1.94MB（debug 未 shrink）；`assets/bg/` 0.98MB 背景图；`tables/` 2.88MB（简繁转换表）+ `tc/` 1.12MB（Cronet 证书）

**结论**：debug 包 70+MB 主要来自无混淆 dex，属 debug 构建特性；真正交付体积看 release（27MB）。精简方向：
1. **ABI 拆分**（可落地）：仅保留 arm64-v8a 可减 so ~6.3MB；armeabi-v7a 为 32 位老设备兼容项，需用户决策
2. **release 资源 shrink**：确认 `shrinkResources=true` + `resConfigs` 语言裁剪
3. **死代码/死资源**：`./gradlew lint` UnusedResources/UnusedDeclaration 检查，输出报告后清理
4. **基线对比**：与 archive 原版/历史 release 包体积对比，识别迁移引入的异常增量

**产出**：体积分析报告（docs/temp-analysis/ 或设计文档附录）+ 低成本项落地（ABI 拆分需用户确认）。

**实施结果**（2026-08-24，用户已确认 debug 只打 arm64）：
- `app/build.gradle` `ndk.abiFilters` 改为按构建类型动态选择：`assembleAppDebug` → 仅 `arm64-v8a`；`assembleAppRelease` → `arm64-v8a + armeabi-v7a`（保老设备兼容）；IDE 同步空任务默认双 ABI（release-safe，防误删 release 兼容性）。
- 实测 debug 包 **72.94MB → 66.83MB（−6.1MB）**；aapt 核对 `lib/` 仅剩 `arm64-v8a` 8 个 so，armv7 so 已移除。
- 剩余体积主体=无 R8 混淆 dex（60%+，classes21.dex 31.38MB 等），这是 debug 构建特性（保可调试性）；release 走 `minifyEnabled=true`+`shrinkResources=true` 已 27MB。无显著死资源（res/ 仅 2.6MB）。

### ⑪ 订阅页右上角三点菜单加分组管理入口

**现状**（源码核实）：
- `RssFragment.showRssMenu()`（L918-938）更多菜单仅：文件夹配置/阅读记录/动态分组/设置，**无"分组管理"入口**
- `ui/rss/source/manage/GroupManageDialog.kt` 已存在（ComposeDialogFragment，管理 RssSource 分组），`RssSourceActivity` 已通过 `menu_group_manage` 使用

**修复**：`showRssMenu()` 的 actions 增加一项（放在文件夹配置后）：
```kotlin
add(ModernActionPopup.Action(getString(R.string.group_manage)) {
    showDialogFragment<io.legado.app.ui.rss.source.manage.GroupManageDialog>()
})
```
`group_manage` string 已存在（RssSourceActivity 用）；分组增删改后 `groups` 集合由 groupsFlow 自动更新 → 菜单/标签联动刷新。

## Architecture Decisions

### AD-01: 顶栏管理颜色未生效页面的统一方案
- **Context**: 我的页（MyFragment）与发现经典（ExploreFragment）头部用传统 `TitleBar`，不读 `TopBarConfig`；书架/发现现代/订阅/阅读记录已用 `MainTopBarView` 读配置生效。
- **Concern**: 用户期望"顶栏管理设置颜色后我的头部生效、发现经典头部生效"，与 archive 一致。
- **Decision**（已定：局部读配色）:
  - 方案A/B 全迁移会破坏"我的页 view_search 内联过滤 + 发现经典动态分组 menu_group"，逐一比对 archive 后收敛为：**titleBar 局部读 TopBarConfig 配色**（仅背景/文字，保留原交互与搜索框/菜单）。
  - 落地：`TitleBar` 新增 `topBarColorManaged` 属性 + `refreshTopBarAppearance()`；`fragment_my_config.xml`/`fragment_explore.xml` 置 `true`；`MainActivity.refreshMainTopBars()` 改配置时刷新 TitleBar 配色。相比纯方案B，用属性开关把影响面收窄到主界面两个头部，不影响众阅读子页面。
- **Goal**: 顶栏管理颜色对主界面所有头部生效，行为对齐 archive。
- **Tradeoff**: 方案A 最彻底但改动大；纯方案B 影响面广；**局部读配色（已选）** 改动小且仅主界面头部读配置，保留内联搜索/动态菜单。
- **Status**: Accepted（已实施）

### AD-02: 订阅源列表列数读取 sourceLayout
- **Context**: 订阅源固定卡片网格，无列表/紧凑列表语义；用户要求网格列数设置生效。
- **Concern**: sourceLayout 0/1（列表/紧凑）对订阅源无意义，需回退策略。
- **Decision**: sourceLayout 2-6 直接作为列数；0/1 回退屏幕自适应。
- **Goal**: 网格列数设置实际生效，同时不破坏默认自适应。
- **Tradeoff**: 显式列数时卡片宽度随屏幕变化，可能不等宽；可接受。
- **Status**: Accepted

### AD-03: 订阅页分组管理入口复用既有 Dialog
- **Context**: 订阅主页面（RssFragment）更多菜单缺"分组管理"入口；`ui/rss/source/manage/GroupManageDialog`（ComposeDialogFragment）已存在并被 RssSourceActivity 使用。
- **Concern**: 用户期望订阅页三点菜单可直接管理订阅源分组，与 archive 迁移前行为一致。
- **Decision**: 在 `showRssMenu()` 复用既有 `GroupManageDialog`，不新建 Dialog/Activity。
- **Goal**: 订阅页入口恢复 + 复用既有实现（最小改动、零重复代码）。
- **Tradeoff**: 无新依赖；分组增删改由 groupsFlow 驱动菜单/标签联动刷新。
- **Status**: Accepted

## Data Flow

```
配置写入：SourceFolderConfigDialog.applyConfig → AppConfig.sourceLayout
      ↓
RssFragment.onConfigChanged → applyView() → effectiveSpanCount() → GridLayoutManager(spanCount)
      ↓
RecyclerView（列表/文件夹） / Compose 文件夹目录 按新列数渲染

分组管理：RssFragment.showRssMenu → showDialogFragment<GroupManageDialog> → groupsFlow → groups 更新 → 菜单/标签重组
```

## File Changes

| 文件 | 变更 |
|------|------|
| `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | ④⑤⑪：effectiveSpanCount + initComposeTopBar 清空标签 + showRssMenu 加分组管理 |
| `app/src/main/java/io/legado/app/ui/main/my/MyFragment.kt` | ③⑥：顶栏方案 + 删 fileManage 行 |
| `app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt` | ③：顶栏方案（经典模式） |
| `app/src/main/res/layout/fragment_my_config.xml` | ③：若方案A 改 topBar |
| `app/src/main/res/layout/fragment_explore.xml` | ③：若方案A 调整 topBar 位置 |
| `app/src/main/java/io/legado/app/ui/widget/TitleBar.kt` | ③：若方案B 读 TopBarConfig |
| `app/src/main/res/values/strings.xml` | ④：source_group_mode_folder→文件夹 |
| `app/src/main/res/values-zh/strings.xml` | ⑦⑧：app_name_sigma/welcome_title |
| `app/src/main/java/io/legado/app/ui/adapter/SourceFolderAdapter.kt` | ①（如补漏圆角） |
| `app/src/main/java/io/legado/app/ui/book/source/manage/BookSourceScreen.kt` | ①②（如补漏） |
| `docs/project-rules/frontend-ui-standards.md` | ⑨：新建 archive 迁移后前端 UI 规范 |
| `docs/INDEX.md` + `AGENTS.md` | ⑨：登记规范 + 子规范加载表 |
| `app/build.gradle`（或 ABI 配置） | ⑩：ABI 拆分（需用户确认） |
