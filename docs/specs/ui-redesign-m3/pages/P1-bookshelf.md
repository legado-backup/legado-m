# P1 书架（Bookshelf 主 Grid）

> 参考：Mihon Hero+网格模式（封面大图 + 圆角卡片 + 底部角标）、legados 系 LazyVerticalGrid 书架、Suml-1_Legado_Max 网格角标、现状 style1/2。

## 一、布局结构（文字框图）

```
┌──────────────────────────────────┐
│ 磨砂顶栏：分组图标 + 搜索框 + 切换列表/网格 │  (collapse top 24dp)
├──────────────────────────────────┤
│ 分组 Tab 行（横向滚动，选中下划线）      │  ← SourceFolderAdapter 分组导航
├──────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐        │
│ │ 封面16:9 │ │ 封面 │ │ 封面 │        │  ← LazyVerticalGrid(3列)
│ │ Cover │ │Cover │ │Cover │        │    封面圆角12dp
│ │ 书名   │ │书名  │ │书名  │        │
│ │ ●新   │ │      │ │      │        │  ← 6dp 小圆点角标（非红数字）
│ └──────┘ └──────┘ └──────┘        │
├──────────────────────────────────┤
│ 底部 BottomNavigationBar（4 Tab）   │
└──────────────────────────────────┘
空态：无库存时展示 插图+引导（去书城/导入本地书）
```

- 默认消息 Grid 3 列；支持切换列表（清单）视图，保留 group 头 sticky。
- 搜索框输入时进入书籍搜索（ContentResolver 应用内+网络同步）。

## 二、交互流程

| 触发 | 行为 |
|------|------|
| 点封面 | 进书籍详情（BookInfo）或直达正文（设置项可选） |
| 长按封面 | BottomSheet：下载/移除/替换封面/移至分组 |
| 长按分组 Tab | 分组管理菜单（重命名/排序/隐藏） |
| 左滑书籍 | 快捷操作（读、详情、置顶） |
| 顶栏搜索 | 进入搜索页，结果分 网络/导出 两段 |
| 空态"去发现" | 跳 ExploreShow/搜索页 |

## 三、Compose 组件实现思路

- 容器：`Scaffold + TopAppBar(磨砂)` + `LazyVerticalGrid(GridCells.Fixed(3))` 在 `navigationBarsPadding` 内。
- 封面：`CoverImage` = Glide-compose（复用现状 `ImageLoader` 语义）+ 圆角 `12dp` + 网页背景隔离；底部书名 14sp/两行截断。
- 角标：`BadgePill`（6dp 圆点，primary 色 onSurface 变体）。
- 空态：`EmptyState(icon, msg, actionBtn)` 复用组件，action 跳 `SearchActivity`。
- 分组头：`stickyHeader` 或顶部 TabRow。
- 列表模式：`LazyColumn`，Item = 封面 48dp + 书名 + 阅读进度（线性 Progress）。
- 与现状衔接：布局 View 层可先用 `GridLayoutManager`+ItemDecoration 复刻视觉，后续移至 Compose。

## 四、绘图 Prompt

```
Material 3 Android 阅读App 书架页 高保真UI：3列圆角封面网格（封面16:9），
浅色米白主题大量留白，顶部磨砂搜索栏，书籍封面上有6dp圆点角标，
封面下方书名12sp灰字，底部NavigationBar 4个圆角图标Tab，
页面右侧个别卡片轻微浮动（Hero），整体低饱和护眼色，无高饱和撞色。
```

## 五、关键 NFR

- 长列表滚动 60fps；封面懒加载（Glide 复用现状）。
- 分组切换不回列表顶部（保持 ScrollState）。