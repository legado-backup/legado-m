# Compose 动画（Animations）

> 核心：**选最小 API**。能用 `animate*AsState` 不用 `Animatable`，能用 `AnimatedVisibility` 不用手写状态机。动画是增强不是功能，先跑通功能再补动效。

## API 选择表

| 问题 | API | 何时用 |
|------|-----|--------|
| 子树显隐（进出场） | `AnimatedVisibility` | 菜单/浮层/列表项展开 |
| 单属性冲向目标值 | `animate*AsState`（`animateFloatAsState`/`animateDpAsState`/`animateColorAsState`…） | 数值/颜色/尺寸渐变 |
| 多值同一驱动 | `rememberTransition(targetState) { }` | 多属性同步过渡（scale+alpha 同动） |
| 尺寸平滑变化 | `Modifier.animateContentSize()` | 折叠展开内容块 |
| 同一槽位换整棵组合树 | `AnimatedContent` / `Crossfade` | 列表项类型切换/页面切换（按 contentKey 决定动画） |
| 手势/逐帧驱动 | `Animatable` | 拖拽、swipe、循环动画 |
| 弹簧物理 | `spring(dampingRatio, stiffness)` | 弹性回弹（Tab 切换、下拉回弹） |

## 常用弹簧参数

```kotlin
// 弹性（Bouncy）回弹 —— Tab 切换轻快
spring(
    dampingRatio = DampingRatioMediumBouncy,   // 轻微过冲回弹
    stiffness = StiffnessMedium,               // 中等刚度
)
```

| 参数 | 效果 |
|------|------|
| `DampingRatioLowBouncy` | 强回弹（夸张） |
| `DampingRatioMediumBouncy` | 轻回弹（推荐 UI） |
| `DampingRatioNoBouncy` | 无回弹（干脆利落） |
| `StiffnessLow` | 缓慢 |
| `StiffnessMedium`/`StiffnessMediumLow` | 平衡 |
| `StiffnessHigh` | 快而干脆 |

## 陷阱与规避

- `animateFloatAsState(alpha)` **只淡出不卸载**——要整体显隐用 `AnimatedVisibility`。
- 动画背景色：**不用** `background(color)`（每帧重绘整块），用 `Modifier.drawBehind { drawRect(color) }`。
- 导航自带转场时**勿重复** `AnimatedContent`（双重动画）。
- 帧率级动画值在 **layout/draw 块延迟读取**（见 performance.md），不在组合读。
- 全屏模糊/毛玻璃：本项目**不引入**第三方 blur 依赖（体积红线），用半透明 surface + 可选 `RenderEffect blur`（API31+），低版本降级纯色。
- 动画期间配合 `animateContentSize` 会跳变 → 需要精确尺寸动画时用 `Animatable(0f)` 显式驱动。

## Legado 项目实测经验

1. **PillNavigationBar 底部导航**（S1 已接线）：废弃悬浮半透明白色胶囊 → `surface` 实底 + 顶部细分割线；四项 Tab `weight` 等分均分；选中切换**仅柔和颜色过渡（无整体大缩放）**；选中项仅轻量圆形底色。用 spring 弹性过渡：
   ```kotlin
   val spring = spring(
       dampingRatio = DampingRatioMediumBouncy,
       stiffness = StiffnessMedium,
   )
   ```
   → 对应真机反馈 V-1（无「名字下方白条」、四项均匀、点击动画柔和、非选中无底色）。

2. **阅读器菜单 3s 无操作淡出**（P2 设计）：顶底栏用 `AnimatedVisibility` 进出场，菜单可见时暂停 AutoPager；3s 无操作自动收起为半透明胶囊（排除正在滚动/输入焦点）。

3. **进度/亮度滑块实时预览**：拖动时菜单整体透明度 ≤30% 露出正文；用 `LocalSliderDragState`（HapeLee）或等效监听 drag 态。

4. **浮层动画零打断**：阅读器浮层出现/消失**不触发正文 re-layout**（正文是原生 View，浮层 Compose 覆盖层独立）。

## 审查红旗

- 手写状态机代替 `AnimatedVisibility`/`AnimatedContent`。
- 每次重组重建动画 spec（应 `remember { }`）。
- 全屏动画+导航转场叠加。
- 动画把 State 写回组合阶段。
- 为了「动效」引入重依赖。
