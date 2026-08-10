# P4 我的 / 设置（MyCenter / Config）— 鸿蒙三级布局版

> 核心痛点解决：原版"一长串 Preference 列表混排"（备份、主题、书源、系统设置全在同一线性列表，高频难找）——参考 mgz0227/legado-Harmony MyCenter 三级布局 + Mihon 卡片分组 + Rimchars AppSettingComponents 组件族。

## 一、布局结构（文字框图 · 我的 Tab）

```
┌────────────────────────────────────┐
│ 磨砂顶栏：标题「我的」   [搜索][⚙设置]      │
├────────────────────────────────────┤
│ ① 用户区 Card（18dp 圆角 渐变底）         │
│   [头像 48dp] 昵称             [云盘]    │
│   今日阅读 · 32 分钟（真实 readTime 数据）  │
├────────────────────────────────────┤
│ ② 统计卡行（4 列 MetricGrid，chunked(2)） │
│   读过 12 │ 在读 3 │ 书签 45 │ 时长 9h      │
├────────────────────────────────────┤
│ ③ 高频功能卡片组（2×2/左右滑第二屏）        │
│  [备份恢复][主题设置][书源管理][WebDAV同步] │
│  [本地书籍][净化规则][订阅源][下载管理]      │
├────────────────────────────────────┤
│ ④ Web 服务卡（独立 Card）                │
│   Web服务 [Switch][?] wifi传书/电脑阅读   │
├────────────────────────────────────┤
│ ⑤ 低频列表（统一卡片分组，滚动）            │
│   帮助中心 │ 关于我们 │ 清理缓存 │ 文件管理   │
│   书签 │ 阅读记录 │ 精确管理               │
└────────────────────────────────────┘
```

## 二、交互流程

| 触发 | 行为 | 步数 |
|------|------|------|
| 点统计卡 | 进 ReadRecord / 成就页 | 1 |
| 点[备份恢复] | 弹 BottomSheet 选本地/WebDAV → 对应页 | 2 |
| 点[书源管理]/[主题设置] | 直达对应 Activity/Fragment | 1 |
| 顶栏[搜索] | 过滤我的页全部组项（Rimchars buildVisibleSections 模式）命中即跳 | 1 |
| 顶栏[⚙设置] | 进设置分组页（外观/阅读/网络/管理） | 1 |
| 低频列表任一项 | startActivity | 1 |
| 卡片长按 | 快捷菜单（如备份=快速备份） | 1 |

## 三、Compose 组件实现思路（复用优先）

复用既有/新建公共组件：
- ① 用户区：`SummaryCard`（渐变底+BoxWithConstraints 自适应）+ 真实 `readStats`（Room）。
- ② 统计：`MetricGrid`（2×2 chunked）+ `ClickableStatTile`（48dp 高）。
- ③ 功能卡：`AppManagementCard` + `FeatureTile`（icon 48dp 圆角卡片，2 列）。
- ④ WebDAV：`AppManagementListRow(Switch)` 变体。
- ⑤ 低频：`SplicedColumnGroup` + 15 个 `AppManagementListRow`（title/subtitle/chevron）。
- 整页：`Scaffold + GlassTopAppBar` + `LazyColumn(spacedBy(8...16dp))`。
- 颜色：`rememberAppSettingPalette()`（Rimchars 桥，含 themeSignature）保证主题切换即时重绘。

集成：
- **整页 Compose 化替换 MyFragment**（或 Fragment 内 setContent），不动 ConfigActivity 的 Preference 子页（它们保留 View）。
- 数据：`MyViewModel`（Room book/rss/readTime 统计 + AppConfig 开关）。
- 清理 legados 式死代码：删 `pref_main.xml` 中已无 key 的 fileManage/storageManage/downloadManage 残留点击处理器。

## 四、绘图 Prompt

```
Material 3 Android 阅读App"我的"页高保真：顶部磨砂栏，首卡用户头像+今日阅读时长，
第二行四个小圆角统计数字卡（读过/在读/书签/时长），第三区2列大功能卡片
（备份/主题/书源/WebDAV）圆角18dp 带图标，Web服务独立卡带开关，
下方统一卡片分组列表（帮助/关于/缓存/文件），浅色米白留白底，低饱和护眼。
```

## 五、Key NFR

- 现有全部配置项保留（书源编辑/净化/替换不删减），仅重排信息架构。
- `pref_main.xml` 死代码清除后需回归 4 组入口（书源/主题/备份/RSS）。
- 统计卡用真实 Room 数据（区别于鸿蒙版写死占位）。
- 列表 60fps；开关即时持久化。