# 本项目 View→Compose 迁移实战工作流（W0-W7 + bugfix 批次沉淀）

> 来源：my-compose-full 45 页迁移（2026-09 收官）+ real-device-bugfix-0908/-0908-followup 实战。
> 本文是**项目特定**的迁移操作手册；通用方法论见 SKILL.md 决策框架，规范基线见 `frontend-ui-standards.md` / `ui-standards/architecture.md`。

## 1. 顶栏选型（3→1 归一收官终态）

| 页面类型 | 顶栏 | 备注 |
|---------|------|------|
| 子页/设置族/管理族 | `GlassTopAppBar` **单源** | 管理族经 `AppManagementScaffold` 委托（`AppManagementTopBar` 已删除）；共用布局页走 `installGlassTopBar` 运行时替换 |
| 主界面 Tab（书架/发现/订阅/我的） | `MainTopBarView` | Mode.SUB 枚举已删除，仅 Mode.MAIN 族保留 |
| "我的/发现经典"遗留 | `TitleBar`（managed=true） | 取色已收编 `resolvePageBarColorWithAlpha`；**新页面禁止使用**；经典发现迁移彻底方案登记后续迭代 |

取色唯一入口：`TopBarConfig.resolvePageBarColorWithAlpha`（色相+透明度合一）；前景一律 `contrastOn(容器色)`。

## 2. 迁移操作模式与陷阱（真机实锤，逐条含事故代码）

### 2.1 ComposeView 容器替换（最高频模式）
```kotlin
val container = binding.recyclerView.parent as? ViewGroup ?: return
val index = container.indexOfChild(binding.recyclerView)
container.removeView(binding.recyclerView)
// ...可能还有多个 removeView
container.addView(cv, index.coerceAtMost(container.childCount))  // ← 必须 coerceAtMost
```
- **addView 越界**（bugfix-0908f T3）：索引在 removeView 之前计算，批量移除后 childCount 收敛，裸 index → `IndexOutOfBoundsException`（摘录模板页 index=3 count=1 闪退）。**同批复制模板时必须逐页核对**（W3.3 曾漏改 1/7 页）。
- **removeView 静默 no-op**（bugfix-0908 T1）：titleBar 与 recyclerView **不同父容器**（根 LinearLayout vs 中间 FrameLayout）时，对错误 parent 的 removeView 不报错但无效 → 旧顶栏/搜索框残留（替换净化页双搜索框）。处理：优先 GONE，或 removeView 后断言可见性。

### 2.2 顶栏变体选择
- 共用 XML 布局且多页共存（如 activity_theme_manage 14 页）：**运行时替换**（`installGlassTopBar`：removeView(title_bar) + addView(ComposeView, 0)），XML 不动（改 XML 会炸未迁移页）。
- ConstraintLayout 宿主页：**禁用 installGlassTopBar 运行时替换**（约束链断裂），改布局内 `compose_top_bar` 直挂 + 约束顺延。
- 管理族列表页：直接用 `AppManagementScaffold`（已委托 Glass 族）。

### 2.3 内容色作用域（图标黑色事故根因）
- 自绘顶栏分支必须 `CompositionLocalProvider(LocalContentColor provides contentColor)` 包裹**整个**顶栏内容；M3 TopAppBar 自带三键 contentColor，自绘分支漏包 → nav/action 图标回落主题 onSurface（黑），日夜不跟随（书源管理返回/编辑书源图标黑实锤）。
- `MenuActionIcon` 默认 tint = `LocalContentColor.current`（R5 继承决策）；**禁止**显式钉 `MaterialTheme.colorScheme.onSurfaceVariant`（W7.2 回归实锤）。`action.tint` 显式指定仍最优先。
- 同栏图标统一 20dp（nav/一级/MoreVert）。

### 2.4 MenuAction 双源扩展的连锁排查
给 `MenuAction` 加字段（iconRes/enabled）后，**必须排查所有直接消费点**（`Icon(action.icon)`、`tint`、`enabled` 透传），不能只改渲染函数——W7.2 曾在 ConfigActivity/ImportBookScreen 两处编译暴露。

### 2.5 枚举/常量删除
删 Mode.SUB 类枚举时：全仓 grep 枚举引用（含 when 分支、isVisible 判断、签名参数），每处都要有去向（迁移/删除/保留注释），禁止留死分支。

### 2.6 弹框迁移
- 容器一律 `ComposeDialogFragment` + `AppDialogFrame`/`AppDialogStyle`；根节点显式背景 `rememberAppDialogStyle().surface`（漏背景=透明弹框）。
- dialogAlpha<100 时 `onStart` 按 `1f - layoutAlpha` 比例单调上浮 dimAmount（alpha=100 零改动；E-Ink 分支不受影响）。
- `showXxxDialog` 工厂函数调用点必须在 @Composable 作用域外（Activity 层），常见编译错：`@Composable invocations can only happen from a @Composable context`。

### 2.7 万级列表性能（1 万+行）
- 禁止万级 `joinToString` 指纹串驱动重组 → 改**整数版本信号**（宿主仅在实际变更时递增）。
- 分组头/行混排 → 预构建**扁平 RowModel 列表** + 单 `items(key)` 批量提交，消除 forEach 万级闭包展开与 content 作用域内 SnapshotStateMap 直读。
- 快照列表更新：`replaceAt` 等值分支 no-op（keyed LazyColumn 下 removeAt+add 同位重插 = 纯浪费 O(n)）；`replaceByIndex` 返回 changed 供宿主递增版本信号。
- 派生计算（如 host 解析）收敛到 Flow map 步（IO 线程）一次预计算，禁止比较器内重复查询/主线程写共享 Map。

### 2.8 编辑类/调试类同构页面
- 编辑类（表单）与调试类（流式日志）先抽公共组件族再复用：TabRow+字段行+校验+未保存拦截 / 流式日志列表。
- `onBack` lambda 内禁止直接读 Composable 状态（`@Composable invocations` 编译错），状态提升到函数体。
- XML root 类型必须是 `ComposeView`（非 FrameLayout）；内嵌 AndroidView 用 `ui.viewinterop` 包。

## 3. 交付纪律（含工具纪律）

1. 每波实施前备份到 `bak/`；**同一源码文件 Edit 串行**（并行 Edit 已 6 次竞态实锤）。
2. **Edit 后必须 rg 复核关键行落盘**（本会话多次静默未落盘，import 丢失致编译失败）。
3. 编译零错 ≠ 完成：真机/模拟器 dump 结构验证 + FATAL 计数 + 功能点逐项过。
4. 文档同步四件套：migration-registry 登记 + tasks.md 回执 + updateLog（编译前）+ INDEX。
5. updateLog 必须在编译前基于 git diff 更新（编译中途补写会漏打包）。

## 4. 验证层级速查

| 层级 | 手段 | 适用 |
|------|------|------|
| L1 | 编译 + 安装 + 启动零崩溃 | 每波必做 |
| L2 | dump 结构断言（resumed/视图可见性 flag/文本锚点）+ FATAL=0 | 每波必做 |
| L2 视觉 | 截图亮度差/VL 判定 | MEmu screencap 黑屏时留真机 |
| L3 | 真机全场景回归 | 交付级 |
