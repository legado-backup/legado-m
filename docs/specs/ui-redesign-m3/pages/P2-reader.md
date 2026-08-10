# P2 阅读器页（ReadBook）

> 参考：微信读书交互范式、HapeLee MD3 的 MaterialContainerTransform 封面转场、youfeng 高亮下划线 Span 族、现状 ReadMenu/ReadStyleDialog 全部能力。正文引擎保持原生 View（见 AD-02）。

## 一、布局结构（文字框图）

```
┌────────────────────────────────────┐
│ 状态栏（沉浸，正文延伸到顶）              │
├────────────────────────────────────┤
│                             ┌──┐   │
│                             │翻│   │
│     正文内容区（最大化）        │页│   │
│     TextChapterLayout 渲染    │热│   │
│     （原生 View，覆盖全屏）      │区│   │
│                             └──┘   │
│ 点击中屏 → 浮现：                    │
├────────────────────────────────────┤
│ 顶栏(磨砂)：返回│书名|章节名   ▣目录 ▢书签 │
│ 底栏(磨砂)：目录｜ 字号 │亮度 │夜间│ 更多 │
└────────────────────────────────────┘
自动隐藏：3s 无操作顶底栏淡出
```

## 二、交互流程（当前点击/长按映射）

| 触发 | 行为 |
|------|------|
| 点中央 1 次 | 显示/隐藏浮层（顶+底栏） |
| 点左/右/上下 | 按挠页区 preRender 规则翻页（保留 `ReadView` 原有 8 方向命中） |
| 长按文字 | 文本选择 + 快捷工具条（复制/划线/高亮/分享）——现状 TextActionMenu 改造 |
| 双击左/右 | 章前进/后退（可选） |
| 下滑顶栏 | 弹出 目录 BottomSheet |
| 底栏"更多" | BottomSheet 收纳 全部阅读设置（字号/间距/亮度/夜间/行距/对齐/段距/朗读） |
| 章节右上"收藏" | 书签/高亮列表 BottomSheet |

## 3. Compose 组件实现思路

- 正文：`AndroidView { PageView }` 全屏容器；翻页不受 Compose 影响。
- 浮层：`AnimatedVisibility` 两个半透壳（`Scrim`+blur 可选），containers 全透明避免挡正文。
- 常用面板：`ModalBottomSheet(item 48dp 高，可搜索)` 替代多级 Dialog（对齐 DESIGN-MD "禁嵌套弹窗"）。
- 阅读设置面板：`阅读设置Sheet(ReadingSheet)`，可拉伸，含 字号/行距/字体/翻页动画/背景风格 分组。
- 高亮样式选择：沿用现状 `HighlightStyleDialog`（BottomSheet）并可升级为拖拽调色。
- 配色：阅读颜独立 `ReadBookConfig.durConfig`，不走全局主题（避免误切）。

## 4. 绘图 Prompt

```
Material 3 Android 阅读器页高保真UI：大面积纯色纸感正文占据全屏，
页面顶部与底部各一条半透磨砂栏（顶部含返回/书名/章节，底部含目录/字号/夜间开关），
栏心留有留白，正文区文字下方有淡色下划线高亮，底部一角Mini阅读进度圆点，
皮肤为暖黄护眼纸感，UI控件只在操作时浮现，无花哨渐变、无刺眼高饱和。
```

## 5. Key NFR

- 正文零改动：PageView/TextChapterLayout/7 种翻页委托不动。
- 浮层动画零打断：浮层出现不触发 re-layout（模拟回退是否雷同）。
- 沉浸式：正文顶到状态栏，`enableEdgeToEdge`，systemBars 自动配色。