# 子页面头部不跟随系统主题颜色 — 根因分析与统一修复方案

> 状态：只读分析（2026-08-16）
> 范围：`ui-redesign-m3` 迁移期间，View 顶栏与 Compose 顶栏主题色来源不一致的问题
> 结论先行：**根因不是「不刷新」，而是「两套顶栏用了两套色源」** —— View `TitleBar` 用固定 `primaryColor`，Compose `GlassTopAppBar` 用派生 `surface`。切日/夜时前者基本不变、后者跟着变，导致页面间头部观感割裂；另有若干「双轨过渡」页面同时存在两套顶栏结构，属过渡期历史包袱。

---

## 1. 两套顶栏色源盘点

| 维度 | View `TitleBar` | Compose `GlassTopAppBar` |
|------|----------------|--------------------------|
| 文件 | `app/src/main/java/io/legado/app/ui/widget/TitleBar.kt` | `app/src/main/java/io/legado/app/ui/widget/components/GlassTopAppBar.kt` |
| 背景色 | `context.primaryColor`（`TitleBar.kt:189`） | `MaterialTheme.colorScheme.surface`（`GlassTopAppBar.kt:37-38`） |
| 取色链路 | `Context.primaryColor` → `ThemeStore.primaryColor(context)`（`lib/theme/MaterialValueHelper.kt:61-62`）→ SharedPreferences `KEY_PRIMARY_COLOR` 单个存值 | `LegadoTheme{}`（`ui/theme/LegadoTheme.kt:23-55`）→ 读 ThemeStore 5 核心色 → `ThemeSpec.toM3Scheme()`（`widget/components/ThemeSpec.kt:34-93`）→ 34 槽位 |
| 日/夜行为 | **不区分**：日/夜都显示同一个存好的 primary 色（默认蓝灰 #455A64，日/夜主题配置里 cPrimary/cNPrimary 默认值相同） | **区分**：`isLight = !isNightTheme && isColorLight(bgColor)`（`LegadoTheme.kt:35`），`surface = lerp(bg, 白/黑, 4%/10%)`（`ThemeSpec.kt:43`）→ 夜模式 surface 显著变暗 |
| 标题/图标前景 | 跟随 Toolbar theme（`view_title_bar.xml` / `view_title_bar_dark.xml`） | `colorScheme.onSurface` |
| 状态栏色 | `ThemeStore.statusBarColor`（`BaseActivity.setupSystemBar`，`base/BaseActivity.kt:175-188`） | 同左（`setupLegadoComposeSystemBar`，`ui/theme/ComposeActivitySupport.kt:55-65`） |

**同一页面内日/夜观察结果差异**：
- 切系统暗色后：Compose 页面头部 → 变暗（surface），View 页面头部 → 保持原 primary 蓝灰（基本不变）。
- 观感：前者「跟随主题」，后者「不跟随」——这正是用户反馈「很多子页面的头部不跟随当前系统主题颜色」的直接来源。

---

## 2. 根因分析（按概率排序）

### 根因 A（主因）：两套顶栏色源不同步
- View `TitleBar` 背景固定取 `primaryColor`，与是否夜间无关；Compose `GlassTopAppBar` 取按昼夜推导的 `surface`。
- 只要一个 Activity 还挂着 View `TitleBar`（或其 XML 布局里残留可见 TitleBar），它的头部就不会跟随昼夜切换；而同一个 App 里其它已迁移 Compose 顶栏的页面头部会跟随。同屏对比即「不跟随」。
- 该差异在切换「应用内主题」时同样存在（`ThemeConfig.applyTheme` 会把 `KEY_PRIMARY_COLOR` 覆写成当前主题的 primary，见 `help/config/ThemeConfig.kt:415-448`，但日/夜两套 primary 默认值相同，所以 View 头部观感几乎不变）。

### 根因 B（次因）：双轨过渡页面残留 View 顶栏结构
已 Compose 化但 XML 仍保留 View `TitleBar` 的页面，存在两套顶栏结构叠加的过渡形态：
- `BookSourceActivity`：`activity_book_source.xml` 顶部仍是 View `TitleBar`（`showTopBar=false` 传给 Compose `BookSourceScreen`，源码注释「双轨过渡，View 顶栏/菜单/批量栏保留」，`ui/book/source/manage/BookSourceActivity.kt:126,199-223`）。
- `VideoPlayerActivity`：`activity_video_player.xml:39` 仍含旧 `TitleBar`（`attachToActivity=false`，但 `compose_top_bar` 已接管）。
- 这类页面头部色仍由 View `TitleBar` 决定 → 同样不跟随昼夜。

### 根因 C（潜在 Bug）：跟随系统模式下的上下文注入路径不一致
- `AppContextWrapper.wrap()`（`base/AppContextWrapper.kt:41-52`）在 `attachBaseContext` 阶段强制改写 `uiMode`（themeMode "1"/"3"→NIGHT_NO，"2"→NIGHT_YES，else→跟随系统）。
- `AppConfig.isNightTheme`（`help/config/AppConfig.kt:177-183`）读取同一份 `themeMode` 判定（"3"=墨水屏强制浅色）。
- 两者判定逻辑一致，故 `LegadoTheme` 的 `isNightTheme` 与 View 侧资源解析基本一致。**但**：themeMode="3" 在 wrapper 里被强制成 NIGHT_NO（浅色），而 `isNightTheme` 返回 false —— 一致，无矛盾。
- 注意：**没有发现「Compose 页面漏包 LegadoTheme 导致 MaterialTheme 不是应用主题」的实例**（全仓 Compose 页面 60+ 处 `setContent` 均包了 `LegadoTheme` 或 `setLegadoContent`）。

### 根因 D（无此问题）：Activity 重建时机
- `ThemeConfig.applyDayNight`（`ThemeConfig.kt:69-74`）→ `initNightMode`（`AppCompatDelegate.setDefaultNightMode`）+ `postEvent(EventBus.RECREATE)`；`App.kt:187-194` 在 `onConfigurationChanged` 检测 `CONFIG_UI_MODE` 变化时调用 `applyDayNight`；`MainActivity`/`ConfigActivity` 订阅 RECREATE 后 `recreate()`。
- 因此切日/夜后 Activity 会被重建，`TitleBar.init` 会重跑并重新读 `context.primaryColor` —— 色源本身不变，重建也不会让它变。**重建机制正常，不是根因。**

---

## 3. 使用 View TitleBar 的页面清单（需改造）

> 以下为 `res/layout/` 中仍引用 `<io.legado.app.ui.widget.TitleBar>` 的页面/布局，按其当前可见头部归类。

### 3.1 仍以 View TitleBar 为可见头部（头部色 = primaryColor，不跟随昼夜）
| 页面 | 宿主 | 布局 | 备注 |
|------|------|------|------|
| 书源管理 | `BookSourceActivity` | `activity_book_source.xml:8` | **双轨**：View 顶栏 + Compose 列表（showTopBar=false） |
| 我的 | `MyFragment`（`fragment_my_config.xml:8`） | `fragment_my_config.xml` | 主 Tab |
| 发现 | `ExploreFragment`（`fragment_explore.xml:9`） | `fragment_explore.xml` | 主 Tab，含搜索 |
| 订阅 | `RssFragment`（`fragment_rss.xml:9`） | `fragment_rss.xml` | 主 Tab，含搜索 |
| 书架（样式1） | `BookshelfFragment1`（`fragment_bookshelf1.xml:8`） | `fragment_bookshelf1.xml` | 主 Tab，含 TabLayout |
| 书架（样式2） | `BookshelfFragment2`（`fragment_bookshelf2.xml:8`） | `fragment_bookshelf2.xml` | 主 Tab，含 TabLayout |
| 捐赠 | `DonateActivity`（`activity_donate.xml:9`） | `activity_donate.xml` | 纯 View |
| 换源弹窗 | `SourcePickerDialog`（`dialog_source_picker.xml:9`） | `dialog_source_picker.xml` | 弹窗 |

### 3.2 布局残留 View TitleBar、但已 Compose 化顶栏（应清理残留）
| 页面 | 布局 | 说明 |
|------|------|------|
| 视频播放器 | `activity_video_player.xml:39` | `compose_top_bar` 已接管，旧 TitleBar 遗留（attachToActivity=false） |
| 图片详情 | `activity_image_detail.xml` | `compose_top_bar` 已接管 |
| 阅读菜单 | `view_read_menu.xml:18` | 阅读器菜单内 TitleBar（特殊场景，另议） |

> 说明：`activity_image_gallery.xml`、`activity_rss_article_info.xml`、`fragment_video.xml` 的顶栏已彻底替换为 `ComposeView`（compose_top_bar），不再含 View `TitleBar` 引用（grep 命中为注释/历史说明，非活动节点）。`fragment_video.xml` 命中为悬浮返回按钮注释，非 TitleBar。

### 3.3 统计对比
- 使用 Compose `GlassTopAppBar` 的页面/组件：**约 50 个**（见 `ui/` 全仓 `GlassTopAppBar` 引用，含纯 Compose 页与 compose_top_bar 桥接页）。
- 仍以 View `TitleBar` 为可见头部：**8 个**（3.1 清单）+ 3 个残留（3.2）。
- 结论：Compose 顶栏已是多数，View 顶栏是少数遗留，**统一方向应为「View TitleBar → GlassTopAppBar」**。

---

## 4. 统一修复方案（给主代理实施）

### 方案选型：推荐「逐步把 View TitleBar 替换为 GlassTopAppBar」
理由：
1. 与 `ui-standards.md` 的既有规范一致（「所有 Compose 页面必须包 LegadoTheme{}」「GlassTopAppBar 为统一顶栏容器」，见 `docs/specs/ui-redesign-m3/ui-standards.md:11-14,53`）。
2. 全仓已 50 个页面用 Compose 顶栏，统一到一个色源（`surface`）成本最低、观感一致。
3. 反向「统一 TitleBar 色源」不可取：会破坏已迁移页面的既有视觉，且 View 体系没有 `surface` 这类昼夜推导槽位，改动面更大。

### 4.1 公共组件改动（GlassTopAppBar 是否需要调色源？）
- **当前 `surface` 色源无需改**：它已正确跟随昼夜（`LegadoTheme` → `ThemeSpec.toM3Scheme`），与设计规范一致。
- 可选的增强（非必须，P2）：当页面主体是 `colorScheme.background`（带背景图时）而顶栏是 `surface` 时，两者色差极小；如需「顶栏=页面背景色」可加一个 `containerColor: Color = MaterialTheme.colorScheme.surface` 参数，默认值保持现状，不破坏现有 50 处调用。
- 建议新增 **`ViewTitleBarColors` 收敛函数**（放 `lib/theme/MaterialValueHelper.kt` 或 `ui/widget/components`）：供 View 页在替换前临时对齐 `primaryColor` → `backgroundColor`（不推荐长期用，仅过渡）。

### 4.2 页面改动清单（按优先级）

**P0 —— 主 Tab 页（用户最常看到「不跟随」的页面）**
1. `MyFragment`（fragment_my_config.xml）→ 顶栏换 `compose_top_bar` + `GlassTopAppBar`
2. `ExploreFragment`（fragment_explore.xml）→ 同上（保留搜索框逻辑，search 下沉到 Compose `SettingsSearchBar`）
3. `RssFragment`（fragment_rss.xml）→ 同上
4. `BookshelfFragment1/2`（fragment_bookshelf1/2.xml）→ 顶栏换 Compose，TabLayout 由 Compose TabRow 接管或保留

**P1 —— 双轨/残留页（头部色仍是 primaryColor）**
5. `BookSourceActivity` → 删除 XML View `TitleBar`，`BookSourceScreen` 切 `showTopBar=true`（顶栏/搜索/菜单全部由 Compose 接管）
6. `DonateActivity` → 顶栏 Compose 化
7. `SourcePickerDialog` → 顶栏 Compose 化（或按 `BaseComposeDialogFragment` 范式迁移）

**P2 —— 布局残留清理（头部已 Compose 化，仅清死代码）**
8. `activity_video_player.xml:39` 旧 TitleBar 删除（确认无代码引用后）
9. `activity_image_detail.xml` 残留 TitleBar 节点清理
10. `view_read_menu.xml` 阅读器菜单 TitleBar（与阅读器沉浸式联动，需单独评审）

**改造模板**（与已迁移页面一致）：
```kotlin
binding.composeTopBar.setContent {
    LegadoTheme {
        GlassTopAppBar(
            title = getString(R.string.xxx),
            navIcon = Icons.AutoMirrored.Filled.ArrowBack,
            onNavClick = { finish() },
            actions = { /* 菜单/图标按钮 */ }
        )
    }
}
```
- 布局：XML 里把 `<io.legado.app.ui.widget.TitleBar>` 换成 `<androidx.compose.ui.platform.ComposeView android:id="@+id/compose_top_bar" android:layout_height="wrap_content">`。
- 状态栏：保持 `BaseActivity.setupSystemBar()` 或 `ComposeActivitySupport.setupLegadoComposeSystemBar()` 不动，与顶栏无关。

### 4.3 明确公共/页面边界
- **公共组件**：`GlassTopAppBar`（已可用，不需改）；可选新增 `containerColor` 参数（默认 surface）。
- **页面改动**：上述 10 个页面的 XML 布局 + Activity/Fragment 的顶栏初始化代码。
- **禁止**：在 View 页直接改 `TitleBar.kt` 的取色逻辑（会改变所有 View 页观感，且 View 体系无昼夜槽位，改不干净）。若短期内无法全量替换，可用「过渡方案」：`TitleBar` 增加可选 attr（如 `app:useBackgroundColorAsContainer`），默认 false 保持现状，需对齐的页面显式开启 —— 但这只是止血，最终仍应替换为 Compose。

---

## 5. 关键文件索引

| 文件 | 关键位置 |
|------|---------|
| `app/src/main/java/io/legado/app/ui/widget/TitleBar.kt` | `:189` `setBackgroundColor(context.primaryColor)` |
| `app/src/main/java/io/legado/app/ui/widget/components/GlassTopAppBar.kt` | `:37-41` `colorScheme.surface` |
| `app/src/main/java/io/legado/app/ui/theme/LegadoTheme.kt` | `:23-55` ThemeStore → M3 映射 |
| `app/src/main/java/io/legado/app/ui/widget/components/ThemeSpec.kt` | `:34-93` toM3Scheme，surface 推导 |
| `app/src/main/java/io/legado/app/lib/theme/ThemeStore.kt` | `:197` primaryColor 读取 |
| `app/src/main/java/io/legado/app/lib/theme/MaterialValueHelper.kt` | `:61-62` Context.primaryColor |
| `app/src/main/java/io/legado/app/help/config/ThemeConfig.kt` | `:69-74` applyDayNight；`:415-448` applyTheme |
| `app/src/main/java/io/legado/app/help/config/AppConfig.kt` | `:177-183` isNightTheme |
| `app/src/main/java/io/legado/app/base/AppContextWrapper.kt` | `:41-52` uiMode 注入 |
| `app/src/main/java/io/legado/app/base/BaseActivity.kt` | `:175-188` setupSystemBar |
| `app/src/main/java/io/legado/app/ui/theme/ComposeActivitySupport.kt` | `:41-65` Compose 页主题/系统栏初始化 |
| `docs/specs/ui-redesign-m3/ui-standards.md` | `:11-14` 主题接入规范；`:53` 顶栏规范；`:221` GlassTopAppBar 真值行 |

---

## 6. 遗留风险与后续建议
1. `BookSourceActivity` 的「双轨」是过渡期设计，长期应删 View 侧顶栏（含 `binding.titleBar.findViewById(R.id.search_view)` 的搜索逻辑迁移到 Compose `SettingsSearchBar`）。
2. 换源弹窗 `SourcePickerDialog` 与阅读器菜单 `view_read_menu.xml` 属于沉浸式/浮层场景，改造前需确认状态栏与沉浸式逻辑不受影响。
3. 全量替换后建议回归：日/夜切换、应用内主题切换、背景图模式（顶栏 surface vs 页面 background 在带图模式下的对比度）。
