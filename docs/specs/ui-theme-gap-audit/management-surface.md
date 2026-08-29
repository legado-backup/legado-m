# 设置项管理面（management-surface.md）

> FR-1 产出（tasks 1.1），基于 `constant/PreferKey.kt` + `help/config/ThemeConfig.kt` + `help/config/TopBarConfig.kt` 提取（2026-08-26）。
> 用途：审计/用例判定"组件是否被设置项管理"的 key 锚点（M1/M2/M3/M4 判定基准）。

## 1. 主色体系（M1）— ThemeConfig + ThemeStore

| PreferKey | 含义 | 日/夜 |
|-----------|------|-------|
| `cPrimary` / `cNPrimary` | 主色 | 日/夜 |
| `cAccent` / `cNAccent` | 强调色 | 日/夜 |
| `cBackground` / `cNBackground` | 背景色 | 日/夜 |
| `cBBackground` / `cNBBackground` | 底部背景色 | 日/夜 |
| `bgImage` / `bgImageN` | 背景图 | 日/夜 |
| `bgImageBlurring` / `bgImageNBlurring` | 背景图模糊 | 日/夜 |
| `bgImageCrop` / `bgImageNCrop` | 背景图裁剪 | 日/夜 |
| `fontScale` / `fontScaleN` | 字号缩放 | 日/夜 |
| `themeMode` | 日夜模式 | 全局 |
| `mainTransparentStatusBar` | 沉浸状态栏 | 全局 |
| `immersiveManageBar` | 沉浸导航栏 | 全局 |

## 2. 扩展表面色（M1 扩展，Archive 字段）

| PreferKey | 含义 | 日/夜 |
|-----------|------|-------|
| `themeCardColor` / `themeCardColorN` | 卡片色 | 日/夜 |
| `themeMutedColor` / `themeMutedColorN` | 弱化色 | 日/夜 |
| `themeSearchFieldBackgroundColor` / N | 搜索框底色 | 日/夜 |
| `themeTabBackgroundColor` / N | 标签栏色 | 日/夜 |
| `themeShelfColor` / `themeShelfColorN` | 书架色 | 日/夜 |
| `themeCardShadow` / N | 卡片阴影 | 日/夜 |
| `themeCardBackgroundBlur` / N | 卡片背景模糊 | 日/夜 |
| `panelBgImage` / `panelBgImageN` | 面板背景图 | 日/夜 |
| `panelBgScaleType` / N | 面板缩放类型 | 日/夜 |
| `panelBorderColor` / `panelBorderColorN` | 面板边框色 | 日/夜 |
| `panelBorderAlpha` / N | 面板边框透明度 | 日/夜 |

## 3. 顶栏（M2）— TopBarConfig

| key | 含义 |
|-----|------|
| `topBarPackageDay` / `topBarPackageNight` | 顶栏配置包（日/夜） |
| `mainLayoutPreset` | 主布局预设（影响顶栏默认样式） |

> 顶栏明细配置（标签栏色/选中色/壁纸/圆角/胶囊/搜索显隐）封装于 TopBarConfig 配置包的 theme.json/top_bar.json，UI 消费方 = `MainTopBarView` + `TitleBar(topBarColorManaged)`。

## 4. 主框架/底部导航（M1/M7 扩展）

| key | 含义 |
|-----|------|
| `mainBottomNavItems` | 底部导航项配置 |
| `bottomBarLayoutMode` | 底栏布局模式 |
| `bottomBarSidebarGravity` | 侧边栏重力 |
| `bottomBarEffectMode` | 底栏特效模式（毛玻璃等） |
| `themePackageSyncTasks` | 主题包同步任务 |

> 注：字号刻度表（M4）定义在 `theme/LegadoTheme.kt`（typography）+ `res/values/dimens.xml`（text_10sp~text_36sp）；圆角 token（M3）定义在 `ui/widget/components/AppShapes.kt`（7 token）+ `lib/theme/UiCorner`（View 侧）。

## 5. 判定规则速查（供审计/用例引用）

- "被 M1 管理" = 组件取色来自 `MaterialTheme.colorScheme`（由 LegadoTheme 桥接 ThemeStore）或 `ThemeStore.x`/`PreferKey.theme*`。
- "被 M2 管理"（头部）= 使用 `MainTopBarView` 或 `TitleBar` 置 `topBarColorManaged=true`。
- "被 M3 管理"（圆角）= 使用 `AppShapes.*` 或 `UiCorner.*`，无 `RoundedCornerShape(N.dp)` 魔数。
- "被 M4 管理"（字号）= 使用 `MaterialTheme.typography.*` 或刻度表，无 `fontSize = N.sp` 魔数。
- "被 M5 管理"（搜索框）= 使用 `SettingsSearchBar`/`TopBarSearchStyle`/`bg_searchview`（18dp）。
- "被 M6 管理"（弹框）= `ComposeDialogFragment` 子类；`BaseDialogFragment`+`dialog_*` XML 为残留。
- "被 M7 管理"（菜单/弹层）= 三点菜单 `ModernActionPopup`；底部弹层 `AppModalBottomSheet`　拖。