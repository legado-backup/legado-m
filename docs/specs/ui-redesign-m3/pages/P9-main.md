# P9 · 主框架 MainActivity（S1 骨架样板）· v2

> 骨架级样板页（S1 主框架 Tab 页）完整设计文档。开发/接线本页时只读本文档 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：MainActivity → `ui/main/MainActivity.kt` + `activity_main.xml`（ViewPager + ComposeView 底栏）
- **骨架归类**：S1 主框架 Tab 页（唯一 S1 页，全 App 壳层样板）
- **对应 task**：tasks.md 12.20（PillNavigationBar 接线）、12.21（真机 FR-11）、V-1；pages-inventory A1
- **fork 借鉴来源**：background/forks-deep-dive §9（MoRealm PillNavigationBar）、§11（325506 Nav3 底部 Tab 用 HorizontalPager 不嵌套 NavHost 教训）

## 1. 设计意图

MainActivity 是 S1 主框架唯一页，承载 ViewPager 4 Tab（书架/发现/订阅/我的）壳层。核心目标：底部导航换为 **PillNavigationBar**（AD-17，受控组件），消灭旧 BottomNavigationView 私有实现与 `defaultTabs()` 硬编码/失真问题，同时**保留 ViewPager/Fragment 架构**（不改内核）。是 S1 骨架样板，后续无其他 S1 页，但它定义全 App 的「底栏 + 壳层」范式（insets/回顶/双击退出/换肤重建/Tab 保活）。

## 2. 布局结构

```
┌─────────────────────────────────────┐
│ ViewPager 内容区（4 Fragment）        │  ← 书架/发现/订阅/我的
├─────────────────────────────────────┤
│ ┌─ 底部导航（PillNavigationBar）───┐  │  ← ComposeView 桥接
│ │ 4 Tab 均分 + BadgeDot 角标       │  │
│ └─────────────────────────────────┘  │
└─────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 内容区 | `ViewPager2`/FragmentStatePagerAdapter | MainViewModel + 4 Fragment | 内核保留（offscreenPageLimit=3） |
| 底栏 | `PillNavigationBar`（§3.4） | `selectedTab←pagePosition` / `onTabSelect←viewPagerMain.setCurrentItem` | ComposeView + LegadoTheme 包裹 |
| 角标 | `BadgeDot`（§3.4，PillNavTab.badgeCount） | `onUpBooksLiveData` | 书架上新；-1=纯圆点 |

## 3. 组件选型（§3.4 规格引用）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `PillNavigationBar` | Row surface 底 + 0.5dp 顶分割线；垂直 4dp(Row)/2dp(Tab)；labelSmall Bold(选中)/Regular(未选中)；选中态图标/文字 primary 变色+tween(200)（**无选中底胶囊**，08-14 按 bug① 简化）；Tab 图标 22dp；Tab weight(1f)≥48dp | 底部 4 Tab 导航 |
| `BadgeDot` | error 底、10sp、>99 显示 99+ | 书架上新角标 |

> 接线要点：`selectedTab` 受控映射 `pagePosition`（`:196`）；`onTabSelect` → `viewPagerMain.setCurrentItem(index,false)`；tabs 按 `upBottomMenu`（showDiscovery/showRSS）动态过滤构建；`LegadoTheme` 必须包裹（PillNavigationBar 读 MaterialTheme.colorScheme）；insets 用 `windowInsetsPadding(WindowInsets.navigationBars)` 对齐旧 `:202-206`。

## 4. 交互流程

| 触发 | 行为 | ≤2 步 | 备注 |
|------|------|-------|------|
| 单击 Tab | 切 ViewPager Tab | ✅ | `setCurrentItem(index,false)` |
| Tab 重选（书架/发现） | 书架双击回顶 / 发现收起 | ✅ | 沿用 `:172-190` 双守卫 300ms |
| ViewPager 滑动 | 同步选中态 | ✅ | onPageSelected → selectedTab |
| 返回键 | 非首页回书架 → 书架 back → 双击退出 | ✅ | 沿用 `:101-121` 优先级链 |
| 书架样式切换 | recreate 重建（Tab 位置保活） | — | rememberSaveable 保 pagePosition |

## 5. 状态管理（§4 范式）

- 数据源：MainViewModel + `onUpBooksLiveData`（角标）/ Fragment 业务
- 受控组件：`PillNavigationBar(selectedTab, onTabSelect, tabs, ...)` state 全提升到 MainActivity
- **Tab 保活**：`savedInstanceState` 存 `pagePosition`；`recreate` 已存则跳过 `upHomePage` 无条件覆盖（修复旧 V6：用户在"我的"页切主题回来被打回默认首页）
- **禁止**：`defaultTabs()` 硬编码「书架/发现/历史/我的」（已废弃，History 语义失真）；tabs 用 stringResource 显式构建真实四 Tab

## 6. 三态（壳层页，无列表三态）

- 壳层页不承担列表三态（各 Fragment 自管）；MainActivity 仅需崩溃提示/隐私协议等弹窗。

## 7. i18n 与无障碍

- Tab label 用 `stringResource(R.string.*)`（书架/发现/订阅/我的），**禁止硬编码中文**
- 崩溃提示正文（`:301`）迁 `R.string`；`"password"` hint（`:279`）迁资源
- 触控：Tab ≥48dp；Insets 处理避免底部遮挡

## 8. 验收标准（交付门禁）

- [ ] PillNavigationBar 接线完成，4 Tab 均分 + 角标正常；旧 BottomNavigationView/defaultTabs 已退役
- [ ] 组件来自 §3 表，规格与 §3.4 逐项一致
- [ ] 无硬编码色/字号；无私有复制角标（BadgeView 已退役）
- [ ] Tab 位置跨 recreate 保活（修复 V6）；回顶/双击退出/返回链完整
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）——12.21 已 ✅
- [ ] §3.3 实施回执已填（tasks + pages-inventory A1）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt

```
Material 3 Android 阅读App 高保真UI设计稿，主框架 4 Tab（书架/发现/订阅/我的），底部 NavigationBar 4 个圆角胶囊选中底色，书架上新小圆点未读角标，低饱和护眼色系，大量留白，无花哨渐变，像素精度，中文界面
```

## 10. 变更记录

- 2026-08-12：PillNavigationBar 接线完成（tasks 12.20/12.21，FR-11 真机 ✅）
- 2026-08-13：建立本完整文档（S1 骨架样板，对齐现状 + V6 Tab 保活等违例登记）
