# P3 书籍详情页（BookInfo）

> 参考：HapeLee MD3 封面共享转场（MaterialContainerTransform）、legados 卡片风格、现状 BookInfoActivity 能力全保留。

## 一、布局结构（文字框图）

```
┌──────────────────────────────┐
│ 磨砂顶栏：返回 │ 封面占位 │ 更多(kebab) │
├──────────────────────────────┤
│ ┌─────────┬───────────────┐  │
│ │ 封面圆角 │ 标题(20sp)     │  │
│ │ 12:16   │ 作者/字数/状态  │  │
│ │ (Hero)  │ 评分星级        │  │
│ └─────────┴───────────────┘  │
│ [开始阅读]  [加入书架]  卡片按钮12dp │
├──────────────────────────────┤
│ 简介（展开/收起，最长6行）         │
│ 章节目录预览（最新3章 + 查看全部）   │
│ 相似推荐（横向 封面 Grid）        │
└──────────────────────────────┘
```

## 二、交互流程

| 触发 | 行为 |
|------|------|
| 点"开始阅读" | 进入 ReadBookActivity（封面 Hero 转场到阅读页） |
| 点"加入书架" | 即时状态变更 + Toast |
| 点封面 | 大图预览（替换/分享） |
| 长按封面 | 替换封面 / 保存网络图 |
| 点目录"全部" | 打开目录 BottomSheet（章节分组列表，深色 tick 标记已读） |
| 顶部 kebab | 更多（编辑、删除、导出、添加分组） |

## 三、Compose 组件实现思路

- `Scaffold + TopAppBar`，body 用 `LazyColumn`。
- `HeroCover` = `GlideImage` + `Modifier.graphicsLayer` 共享元素（key = `book-cover:$bookUrl`，参考 325506 fork）。
- 操作按钮：`BottomActionBar` 固定底部（两个 `Button` 12dp 圆角 + 完整高度 52dp）。
- 目录/相似榜单复用 `BookRowItem` 与 `ReadingProgressBar` 组件。
- 状态管理复用现状 `BookInfoViewModel` 数据流（不改业务）。

## 四、绘图 Prompt

```
Material 3 Android 阅读App 书籍详情页高保真：顶部磨砂栏，
左侧大圆角封面（Hero效果放大留白），右作者书名小字，底部两个圆角主操作按钮
"开始阅读""加入书架"，浅色暖黄背景护眼，下方简介线性与目录列表，低饱和配色无撞色。
```

## 五、Key NFR

- 封面加载不卡列表（Glide 懒加载、占位）。
- 共享转场仅在 disable 开关关闭时启用，兼容 低端设备。