# real-device-bugfix-0908-followup 规格

> 用户真机反馈三项（2026-09-08）。前置：real-device-bugfix-0908（86d0eb0c3）/ my-compose-full W0-W7 收官批次。

## 用户反馈原文要点

1. 发现设置"经典发现"后，发现栏目头部是纯黑色，不像其他头部一样显示壁纸/透出壁纸。
2. 顶栏图标颜色与尺寸体系混乱：书源管理左上角返回图标黑色；编辑书源页右上角三点以外的图标黑色；多页图标不是白色；图标大小粗细不一；日/夜主题切换后图标颜色不跟随（日间应深色反差、夜间应浅色）。
3. 主题设置→摘录分享模板，点击启动即崩：`ShareNoteTemplateManageActivity IndexOutOfBoundsException: index=3 count=1`。

## 根因分析（源码实锤）

### T1 经典发现头部纯黑
- 经典发现模式头部是 `fragment_explore.xml` 的 `TitleBar`（`topBarColorManaged=true`），而非现代模式使用的 `MainTopBarView`（top_bar）。
- `TitleBar` managed 分支（TitleBar.kt L194-201）只铺 `TopBarConfig.resolveBackgroundColor(config)` **纯色相**，不走 `resolvePageBarColorWithAlpha`（色相+透明度合一，AD-01 v1.5 唯一取色入口），不渲染顶栏包壁纸图 → 其他头部（MainTopBarView/GlassTopAppBar 同源半透明合成）显示壁纸/透壁纸时，发现头部为不透明纯色（夜间主题下呈纯黑）。
- 次要项：managed 分支恒挂 `elevation = context.elevation`，半透明底挂阴影会形成灰白框（GlassTopAppBar W0 定稿已规避，TitleBar 未同步）。

### T2 顶栏图标颜色/尺寸混乱
- **根因 A（GlassTopAppBar 自绘分支漏内容色作用域）**：W6.5 自绘分支（barHeight/secondRow 槽，管理族 48dp 档）的 Column/Row 未包 `CompositionLocalProvider(LocalContentColor provides contentColor)`——M3 分支有 `navigationIconContentColor/actionIconContentColor` 而自绘分支 Icon 默认 LocalContentColor=主题 onSurface（黑）→ 书源管理等管理页返回图标黑色。
- **根因 B（MenuActionIcon 显式 tint 违反 R5 继承决策）**：`AppMenuSheet.kt` MenuActionIcon `tint = action.tint ?: MaterialTheme.colorScheme.onSurfaceVariant`——顶栏 action 图标被硬钉到主题 surface 色，既不随顶栏容器色对比度（日间浅底→黑图标 ✔ 但夜间深底→灰而非白），也不随日夜切换反差（用户实测"颜色不对应"）。注释（L144-145）明确 R5 决策为"tint 不显式指定，由宿顶栏 actionIconContentColor 统一继承"——W7.2 双源扩展时实现偏离了自家决策。
- **根因 C（尺寸不一）**：M3 分支 nav 图标 20dp（2.4 定稿）、action 图标 M3 默认 24dp（AOAdapt 已登记偏差）、TopBarActionRow 溢出 MoreVert 20dp、TopBarActionRow 一级 MenuActionIcon 无 size（24dp）——同栏 20/24 混排。"粗细不一"为 drawable 资产线条差异（iconRes 资源 vs Material Icons），资产级统一登记后续迭代。

### T3 摘录分享模板启动崩溃
- `ShareNoteTemplateManageActivity.initComposeContent()`（W3.3）：`index = indexOfChild(recyclerView)` 在 removeView **之前**计算（activity_theme_manage.xml 原始序 index=3），随后连续 removeView(recyclerView/tabBar/tvSummary/btnAdd) 4 次 → 容器只剩 [topbar ComposeView]（count=1），`addView(cv, 3)` 越界崩溃。
- 同批 7 页中 ThemeManage/TopBarManage/NavigationBarManage/DiscoverySuiteManage 用了 `index.coerceAtMost(container.childCount)` 安全写法，BubbleManage 直接 append，**仅 ShareNoteTemplate 漏套用防越界**（W3.3 实施偏差）。

## 修复设计

### T1（最小对齐，不动页面结构）
`TitleBar.kt` managed 分支（init + refreshTopBarAppearance 两处）：
- 底色改 `TopBarConfig.resolvePageBarColorWithAlpha(context, config)`（色相+透明度合一，与其他头部同源）。
- 底色 alpha < 0xFF 时 `elevation = 0`（对齐 GlassTopAppBar W0"半透明不画阴影"定稿）。
- 不动页面结构；经典发现头部迁移 MainTopBarView（彻底方案）登记后续迭代（与 D4 批3 同批评估）。

### T2（三个编辑点，全部收敛单源）
1. `GlassTopAppBar.kt` 自绘分支：Column 外包 `CompositionLocalProvider(LocalContentColor provides contentColor)`——nav/actions/secondRow 全部继承对比度内容色，与 M3 分支行为对齐。
2. `AppMenuSheet.kt` MenuActionIcon：`tint = action.tint ?: LocalContentColor.current`（显式 tint 仍优先）——顶栏继承 actionIconContentColor/LocalContentColor，菜单场景继承菜单内容色，恢复 R5 决策。
3. `TopBarActionRow`：一级图标 `MenuActionIcon(action, Modifier.size(20.dp))` 与 nav/MoreVert 对齐（同栏 20dp 统一）。粗细不一属资产级，登记后续迭代不做代码处理。

### T3（一处防越界）
`ShareNoteTemplateManageActivity.kt` L154：`container.addView(cv, index)` → `index.coerceAtMost(container.childCount)`，对齐同批 4 页写法。

## 验收标准
- 经典发现头部与其他 Tab 头部同色（半透明透壁纸，日/夜均验证）。
- 管理族（书源管理）、编辑书源、14 共用布局迁移页：顶栏图标颜色 = 容器对比度色，日/夜切换跟随；同栏图标 20dp 统一。
- 摘录分享模板页正常启动、列表/弹框/导入导出可用。
- 编译零错 + L2 自测（模拟器 dump 结构验证）+ 全场景零 FATAL。
