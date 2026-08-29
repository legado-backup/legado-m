# §9.2 取色规范

> 取色有两层来源，按优先级「用户自定义 key → 运行时推导 → R.color 兜底」解析。
> 取色核心入口：`app/src/main/java/io/legado/app/lib/theme/ThemeUiPalette.kt`。

## 一、Compose 主题调色板 `ThemeUiPalette` 的 key 表

`data class ThemeUiPalette` 定义 6 个 UI 面颜色，由 `themeUiPalette()` / `rememberThemeUiPalette()` 产出：

| 字段 | PreferKey（可自定义 key） | 兜底（R.color / 推导） | 用途 |
|------|--------------------------|------------------------|------|
| `cardColor` | `themeCardColor` (+N) | `R.color.background_card` | 卡片/行底色 |
| `mutedColor` | `themeMutedColor` (+N) | `R.color.background_menu` | 弱化/底栏底色 |
| `searchFieldBackgroundColor` | `themeSearchFieldBackgroundColor` (+N) | `R.color.background_menu` | 搜索框底色 |
| `tabBackgroundColor` | `themeTabBackgroundColor` (+N) | `R.color.background_menu` | Tab 底色 |
| `shelfColor` | `themeShelfColor` (+N) | 无自定义时=`backgroundColor`（背景色） | 书架底色 |
| `dividerColor` | （无独立 key） | 无自定义面时=`R.color.bg_divider_line`；有自定义面时按前景明暗推导（黑/白 + 10%/16% 透明度） | 分隔线色 |

辅助状态：`hasCustomCardColor` / `hasCustomMutedColor`（是否有自定义面）。

### 关联 key 组（依赖签名变更而重算）

- **颜色 key 组**：`themeCardColor`、`themeMutedColor`、`themeSearchFieldBackgroundColor`、`themeTabBackgroundColor`、`themeShelfColor`（均含夜 +N 变体）。
- **形状 key 组**：面板边框色 `panelBorderColor(+N)`、边框透明度 `panelBorderAlpha(+N)`、面板背景图 `panelBgImage(+N)` 及缩放 `panelBgScaleType(+N)`、圆角缩放 `uiCornerScale(+N)`、搜索/回评跟随 `uiCornerSearchFollow/ReplyFollow`、布局透明度 `uiLayoutAlpha`、`dialogAlpha`、卡片阴影 `themeCardShadow(+N)`、背景模糊 `themeCardBackgroundBlur(+N)`、封面阴影 `bookCoverShadow`。
- **字体 key 组**：`fontScale(+N)`、`uiFontPath(+N)`、`titleFontPath(+N)`、`uiFontColor(+N)`、`titleFontColor(+N)`。
- **全局依赖**：`themeMode`、`cPrimary/cAccent/cBackground/cBBackground`（含夜 `cN*`）。

### 取色解析函数

- `themeColorOrDefault(key, @ColorRes defaultColor)`：可自定义 key 优先，否则 `ContextCompat.getColor(defaultColor)`。
- `themeColorOrNull(key)`：读到可解析的十六进制才返回，否则 null。
- `themeCardColorOrDefault` / `themeMutedColorOrDefault` / `themeSearchFieldBackgroundColorOrDefault` / `themeTabBackgroundColorOrDefault` / `themeShelfColorOrDefault` / `themeDividerColorOrDefault`：各字段兜底。
- `themeUiSignature()`：生成签名串，用于记住调色板并对监听变更失效重算。
- 十六进制归一化：支持 `#RGB/#ARGB/#RRGGBB/#AARRGGBB`、`0x`/`0X` 前缀；输出统一 `#AARRGGBB`。

## 二、`res/values/colors.xml` 的 R.color 兜底色（局部）

colors.xml 中与 UI 面颜色相关的兜底色（`background`、`background_card`、`background_menu` 等引用 `md_grey_*` 主题色）：

| R.color 名 | 值 | 场景 |
|-----------|-----|------|
| `background` | `@color/md_grey_50` | 页面背景 |
| `background_card` | `@color/md_grey_100` | 卡片/面兜底（`cardColor`） |
| `background_menu` | `@color/md_grey_200` | 菜单/搜索框/Tab/弱化底兜底（`mutedColor`、搜索框、Tab） |
| `background_prefs` | `#7fffffff` | 设置项背景 |
| `bg_divider_line` | `#8fe0e0e0` | 分隔线兜底（`dividerColor` 无自定义面时） |
| `divider` | `#66666666` | 通用分隔线 |
| `primary` | `@color/md_light_blue_800` | 主色 |
| `primaryDark` | `@color/md_light_blue_900` | 深主色 |
| `accent` | `@color/md_pink_800` | 强调色 |
| `error` / `success` | `#eb4333` / `#439b53` | 错误/成功 |
| `transparent` | `#00000000` | 全透明 |
| `transparent10/20/30/50` | `#10/#20/#30/#50` + `000000` | 半透明遮罩层级 |

## 三、取值顺序速查

1. 用户在当前主题 mode 下自定义十六进制（如 `themeCardColor`）→ 最高优先。
2. 运行时推导（如 `dividerColor` 依据面明暗推导、自定义面判定）。
3. `ContextCompat.getColor(R.color.*)` 兜底。
4. 注意夜间模式统一使用 `*N` 后缀 key（由 `AppConfig.isNightTheme` 决定读取哪套）。

## 四、设置类主取色链（AI 开发取色唯一入口，2026-08-27 补充）

> 页面级 UI（设置/管理/功能页、Compose 组件）取色**第一优先走下列入口**，`ThemeUiPalette` 与 `R.color` 兜底仅作为低层能力：

| 取色入口 | 用途 | 关键来源 |
|---------|------|---------|
| `rememberAppSettingPalette()` → `palette.settings.page / row / primaryText / secondaryText / accent / danger / border / panelRadiusPx` | 页面背景 / 行 / 文字 / 强调（**page = `Color(context.backgroundColor)` = ThemeStore 直读**） | `ui/widget/compose/AppSettingComponents.kt` |
| `rememberAppDialogStyle()`（`AppDialogStyle` + `AppDialogFrame`） | 弹框 / 菜单面板（背景图 / 圆角 / 透明度 / 边框） | `ui/widget/compose/AppComposeDialogs.kt` |
| `UiCorner.panelRadius / actionRadius / layoutAlpha / panelImageDrawable / panelBorder*` | 圆角 / 透明度 / 面板背景图（全局 UI 圆角缩放） | `lib/theme/UiCorner.kt` |
| `Context.backgroundColor`（View 层 `ThemeStore.backgroundColor()`） | 页面根背景直色 | `lib/theme/ThemeStore.kt` |
| `Color(context.primaryColor)` | 顶栏容器色（GlassTopAppBar 主色） | `lib/theme/ThemeStore.kt` |

## 五、M3 派生色禁令（H9/H11 教训，2026-08-27 硬约束）

- **禁止**：Compose 页面级 / 卡片级视觉取色使用 `MaterialTheme.colorScheme.surface / surfaceVariant / onSurface / background`。
  - 原因：M3 `surface = lerp(bg, neutral, 4~10%)`、`surfaceVariant = lerp(bg, onBg, 5~14%)` 是**派生偏移色**，用户自定义主题背景/卡片色后与 `backgroundColor` 直读明显偏色（H9 精准管理页根背景 + H10/H11 列表项卡片 M3 surface 实锤，见 `docs/specs/ui-style-unify-deep-fix/issue-list.md`）。
- **允许的例外（须登记）**：确需"中性灰浮层/遮罩"语义处（多选底栏遮罩、调试工具输入框）；媒体画布 / 阅读正文可配置色 / 视频控制层（主题体系外清单）。
- **正例**：页面根背景一律 `palette.settings.page`；卡片 `UiCorner.surfaceColor(themeUiPalette.cardColor)`；文字 `palette.primaryText / secondaryText`。
- **门禁**：新增 Compose 页面出现 `colorScheme.surface`（页面/卡片级）→ 代码审查拒绝返回。