# Compose 性能诊断与稳定性（Performance & Stability）

> 核心：**只处理被测量出的问题**。先复现可感知过渡、取证据、分类主轴，再在轴起点做最小修正。不凭直觉加 `@Stable`/wrapper/remember。

## 诊断流程（先证据后修正）

1. **复现**：找到用户可感知的过渡（列表滚动卡顿/闪烁/跳帧），先取证据：
   - Layout Inspector → Recomposition 次数
   - `composeCompilerReports`（compiler 统计 stability）— 用 `./gradlew assembleAppDebug -PcomposeCompilerReports=true`
   - Profiler / systrace 帧时间线
2. **分类主轴**：
   - **重组轴**：参数稳定性差导致「输入没变却重组」
   - **布局轴**：layout/measure/draw 阶段慢（大列表 item 布局复杂）
   - **组合-布局回写**：组合读 layout/draw 时写的 State
3. **排除假线索**：真实数据变化、正确性缺陷、预期内重组不是性能问题。
4. **一次只改一个轴，重测**。改完必须回测，不能靠感觉。

## 关键知识

### 重组数量

- 要压的是「**输入没变却重组**」。输入真变了，重组是应该的，不许硬压。
- 常见原因：参数是 `Map`/`List`（不稳定）→ 用 `immutable` 注解的 data class 或 `remember { }` 缓存稳定引用。
- 大列表 item：把可变 State 读**下沉到最叶子 composable**，父层只收不可变数据。

### 帧率级 State 读（scroll/animation/gesture/layout/draw）

- 不能在**组合阶段**读滚动偏移/动画值（会导致每帧全树重组）。
- 应在 **layout/draw 阶段**延迟读取：`Modifier.graphicsLayer { rotationZ = ... }`、`drawBehind {}`、`layout { measurable.measure }` 内读。

### 禁止 back-write

- 组合体内**禁止写** snapshot state 来重建派生数据。
- 用 `remember(keys) { derived }` 计算派生值。

## 稳定性（Stability）

| 情形 | 做法 |
|------|------|
| 稳定 data class（只读、构造后不变） | `@Immutable`（不可变 class/val-only） |
| 内部有 `var` 但构造后不写 | `@Stable` |
| 普通 UI 状态 holder | `@Stable class XxxState`（见 state-and-effects.md） |
| 大对象/来自 DB 的模型 | 一般不需要注解；`remember(key) {}` 包裹即可 |

- `@Immutable` 误标不可变实际可变 → 假稳定性 bug。只在确定不改时用。
- 集合参数：`immutableListOf` 优于每次 `listOf(...)` 重建。
- 默认**不**加注解，出现重组问题时再证据驱动地加。

## 布局性能

- 大列表用 `LazyColumn`/`LazyVerticalGrid`，item 内**尽量少嵌套**（深嵌套 Box/Column 层数=measure 成本）。
- item 高度固定可 `Modifier.height()`（跳过 measure），但**不要**随便给，避免破坏内容。
- 图像：复用 Glide/Coil 缓存，**禁止**每帧重建 imageRequest。

## Legado 项目实测经验（AOAdapt 入库）

1. **我的页永久 loading（Phase2 真机教训）**：`produceState` + `LaunchedEffect` 双写同一 state → 双状态死锁。修复：**单 `produceState` 委托属性 + `if (stats == null)` 判空**。Compose 异步取数避免两个 effect 写同一状态。
2. **书架"先画双列再刷单列"闪变（V-4）**：loading 骨架屏需按布局类型动态匹配（`layout≥2` 用 `ShelfGridSkeleton`，否则 `ShelfListSkeleton`）。骨架屏=列表滚动性能与首帧观感的平衡点。
3. **网格列数 GridCells.Fixed 例外**：书架列数由 `AppConfig.bookshelfLayout`（1-4 用户显式选择）驱动，属用户控制，**登记为 §1.4 例外**（与 GeneratedCover 8 色同类豁免），不做大屏自适应叠加。
4. **封面懒加载**：`AndroidView + BookCover.load`（glide-compose 不引入，免新依赖），页面滚动 60fps。
5. **拖动滑块实时预览**（P2 阅读器）：Material Slider 拖动时菜单整体 `alpha ≤ 30%` 露出正文，松手 commit；用 conflate + 单 worker 串行预览，杜绝「拖到 70% 回弹 40%」。

## 审查红旗

- 凭直觉加 `@Stable`/remember 压重组，无测量证据。
- 组合体内 `val x = state.read()` 参与 layout/draw。
- 大列表 item 深度嵌套。
- 每帧重建 imageRequest / 字符串。
- 双 effect 写同一 state。
