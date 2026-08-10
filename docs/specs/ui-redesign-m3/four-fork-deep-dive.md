# 四 Fork 前端对标 + 组件化 + 鸿蒙布局方案

> 依据：HapeLee/legado-with-MD3、GEd520/legados、Rimchars/legado、joestar817/legado_NG 四仓逐源码深挖 + mgz0227/legado-Harmony（鸿蒙版）布局范例。全部带真实文件佐证。

## 一、四仓 UI 架构横向对比

```mermaid
graph LR
  subgraph 架构路线
    A[HapeLee<br/>全 Compose + Nav3 + Koin] -->|双引擎主题<br/>BottomSheet 主力| C[最激进]
    B[legados<br/>View核心+Compose新页] -->|组件库半成品<br/>我的页=旧痛例| D[均衡]
    E[Rimchars<br/>View核心+Dlg+125Compose] -->|设置组件族完整<br/>居中Dialog| F[完整组件化]
    G[legado_NG<br/>双端Token设计系统] -->|Glassmorphism<br/>NDS 工程]| H[最现代]
  end
```

| 维度 | HapeLee | legados | Rimchars | legado_NG | 结论 |
|------|---------|---------|----------|-----------|------|
| Compose 文件 | 339 | 70 | 125 | 45 | 全覆盖全替换 | 
| 导航 | Nav3 sealed | startActivity | startActivity | Activity+Fragment | 不引入 Nav3 |
| 设置组件 | settingItem/18文件 SplicedColumnGroup | 无（零散） | AppSettingComponents/731行 | Ng dual 18+7 | **借鉴 Rimchars 组件族** |
| 弹窗策略 | BottomSheet 150+ | BottomSheet 预埋 | 居中 Dialog 分级 | ng 展开卡 | **BSheet 主力+Dialog 分级兜底** |
| 我的页 | 搜索+书库组前置 | **旧长列表(痛点活例)** | 分段卡+搜索 | MD3 分组卡 | **做鸿蒙三级布局** |
| 阅读浮层 | 37 Sheet 单渲染 | ReadMenu View | View | 玻璃浮坞/玻璃抽屉 | 保留 View+BSheet 浮层 |
| 主题 | 14 模式 MaterialKolor | Store→lerp | Store→3层桥 | 双端 Token 系统 | **ThemeStore 权威源不变** |
| 玻璃拟态 | MagicalBottomBar | GlassCard(未用) | liquidglass | NgGlassSurface 自研 | 顶栏/浮底轻量毛玻璃 |

## 二、原版痛点清单（逐条对应解法）

| # | 原版痛点 | fork 佐证 | 本 spec 解法 |
|---|---------|-----------|--------------|
| P1 | **我的/设置长线性列表混排**：备份、主题、书源、系统设置一长串，高频难找 | legados MyFragment=Preference 长列表（文件说明）；Rimchars 分段卡+全站搜索 | **MyCenter 三级布局**（详见 §四）：统计卡→高频功能卡→低频列表 |
| P2 | 系统设置子页链式跳转深、多层嵌套弹窗 | HapeLee Sheet 150+、Rimchars Dialog 分级 | BottomSheet 主力+Dialog 分级兜底；高频设置 ≤2 步 |
| P3 | 设置入口无搜索，找项靠翻 | Rimchars MySettings buildVisibleSections 全站搜索精确落 key | 我的/设置页顶部搜索框 |
| P4 | 卡片组件零散：设置行、开关行、滑杆行无统一组件 | Rimchars 731 行组件族、HapeLee 18 文件 | 自建 `AppSettingComponents`（见 §三） |
| P5 | 未读角标刺眼红数字 | HapeLee IconWithNumberBadge、legados BadgePill | 6dp 小圆点（DESIGN-MD 禁红数字） |
| P6 | 阅读设置藏在多层 Dialog，调整字号/亮度路径深 | HapeLee ReaderMoreActionsSheet（宫格）| 阅读浮层 Sheet hub，1 步直达 |
| P7 | 书架-阅读无过渡，生硬跳转 | HapeLee BookCoverSharedElement | 封面 Hero 开关（默认关闭） |
| P8 | View/Compose 颜色漂移 | legado_NG 双端 Token、Rimchars palette+signature | ThemeStore 单一权威源+XML/Compose 同源 |

## 三、组件化方案（Resuable Component Architecture）

### 公共组件库 `ui/widget/components/`（提议新建/对齐）

| 组件 | 借鉴 | 用途 | 关键实现 |
|------|------|------|---------|
| `AppSettingPalette` + `rememberAppSettingPalette()` | Rimchars | 设置页统一取色（19 色+themeSignature） | 前景按背景明暗推导，不依赖 night 标志 |
| `AppSettingSectionTitle` | Rimchars | 分组标题 | accent 14sp Medium |
| `AppManagementCard` | Rimchars | 卡片容器 | Canvas 圆角+底图+1dp 描边+按压态 |
| `AppManagementListRow` | Rimchars | 列表行（title/subtitle/switch/actions） | 15sp+12sp subtitle+开关+操作 icon |
| `Modifier.appSettingPanelBackground` | Rimchars | 圆角面板底 | drawWithCache |
| `Modifier.appSettingRowDecoration` | Rimchars | 首末行圆角+16dp 内缩分隔线+danger | drawWithCache |
| `SwipeActionContainer` | legados | 列表左/右滑操作 | drag+Spring MediumLow（可直接抄，已落地验证） |
| `VerticalScrollbar` | legados | 长列表缩略滚动 | 绝对手指位/轨道高 |
| `AppModalBottomSheet` | HapeLee/legados | 统一底部弹层 | skipPartiallyExpanded+titleLarge+插槽 |
| `SplicedColumnGroup` | HapeLee | 拼接卡片组（自动分隔线） | 多 item 自动插 Divider |
| `GlassTopAppBar` | HapeLee/legado_NG | 磨砂顶栏 | 背景 alpha+blur（克制，eInk 禁用） |
| `BadgePill` | legados | 小圆点未读 | 6dp primary 色 |
| `SummaryCard`+`BookStackView` | legados | 顶部统计卡（书籍封面堆叠） | zIndex+rotate±3° |
| `MetricGrid` | legados | 2×2 统计卡 | chunked(2)+weight |
| `SettingsSearchBar` | Rimchars/legado_NG | 页面内搜索框 | BasicTextField 圆角+focus 描边 |

**组件分层**：`ui/widget/components/`（无业务）+ `ui/main/my/components/`（我的页专用）+ `ui/book/read/sheet/`（阅读浮层）。

## 四、我的页（MyCenter）鸿蒙三级布局 — 核心页重设计

### 布局结构（文字框图）

```
┌────────────────────────────────────┐
│ 磨砂顶栏：标题「我的」  [搜索] [⚙设置]  │
├────────────────────────────────────┤
│ ① 用户区 Card（18dp 圆角）             │
│   [头像 48dp] 昵称            [云盘]    │
│   今日阅读 · 32 分钟                   │  ← 用 readTime 真实数据（非占位）
├────────────────────────────────────┤
│ ② 统计卡行（4 列 MetricGrid）           │
│  读过 12 │ 在读 3 │ 书签 45 │ 时长 9h    │  ← 数据来自 Room（source/remoteBook）
├────────────────────────────────────┤
│ ③ 高频功能卡片组（2×2 或 4 子项）        │
│ [备份恢复][主题设置][书源管理][WebDAV]   │  ← 鸿蒙中心思想：备份/主题/书源/净化 前置
│ [本地书籍][净化规则](可滑第二屏)          │
├────────────────────────────────────┤
│ ④ Web 服务卡（独立）                   │
│ Web服务 [Switch][?]  wifi传书/电脑阅读   │
├────────────────────────────────────┤
│ ⑤ 低频列表（卡片分组，layoutWeight滚动） │
│ 帮助中心 │ 关于我们 │ 清理缓存 │ 文件管理   │
│ 书签 │ 阅读记录 │ 精确管理               │
└────────────────────────────────────┘
```

### 交互流程

| 触发 | 行为 | 距离 |
|------|------|------|
| 点统计卡 | 进 ReadRecord / 成就页 | 1 步 |
| 点[备份恢复] | BackupConfig（先弹 BottomSheet 选本地/WebDAV） | 2 步 |
| 点[书源管理] | BookSourceActivity | 1 步 |
| 顶栏[搜索] | 搜索框过滤我的页 5 组内容+jump key | 1 步 |
| 点[⚙设置] | 设置分页（外观/阅读/网络/管理 4 大组） | 1 步 |
| 低频列表任一项 | startActivity | 1 步 |

### Compose 实现思路

- 整页 Compose 化：`Scaffold + GlassTopAppBar` + `LazyColumn`。
- ① 用户区复用 `SummaryCard`（渐变底）+ 真实 `readStats` 数据。
- ② 复用 `MetricGrid`（2×2 chunked）+ `ClickableStatTile`。
- ③ 复用 `AppManagementCard` + `FeatureTile`（icon 48dp 圆角卡片）。
- ④ 复用 `AppManagementListRow(Switch)`。
- ⑤ 复用 `SplicedColumnGroup` + 15 个 `AppManagementListRow`。
- 数据：`MyViewModel`（Room readTime/lastRead/book 统计）+`AppConfig` 开关。
- **回填路径**：Roman`precise-manage`/`folder-view-welcome-refactor` 的入口保持一致，pref_main.xml 死代码清除（legados 教训）。

## 五、设置页（Config）分组设计

```
设置（5 大组，新建 Home）
├─ 外观与主题：三套内置+暗夜紫、字体、排版、阅读背景
├─ 阅读：字号/行距/翻页动画/高亮/净化  ← 高频前置
├─ 书架与书源：书架布局/书源管理入口/分组
├─ 网络与缓存：Web 服务/缓存/下载
└─ 管理与同步：备份恢复/WebDAV/日志/关于
```
每项 = `AppSettingRow`，卡片内与卡片间 8dp 间距；长按项直接弹快捷操作。

## 六、与现有基础设施的接缝

| 基础设施 | 现状 | 本次改动 |
|---------|------|---------|
| `ThemeStore` + `LegadoTheme` | 理解保留 | 不动，作为唯一主题源 |
| `ThemeConfig`/`applyDayNight` | 保留 | 不动 |
| `MyFragment` (View) | Preference 长列表 | **整页 Compose 化替换**（新 Activity 或 Fragment 内 setContent） |
| `ConfigActivity` (View) | 分类配置 | 入口保留，样式 MD3 token 化 |
| `ReadMenu` (View) | 保留 | 浮层 Sheet 化（ADR-06） |
| 现有 Compose 基建 | setLegadoContent | 复用 |

- 注意事项：`pref_main.xml` 里 fileManage/storageManage/downloadManage 死代码（legados 教训）→ 本次一并清除，防止 UI 与逻辑脱节。

## 七、学习小结（一句话）

1. **HapeLee**：学「全 Compose 的组件库范式 + SplicedColumnGroup + BottomSheet 主力」，但 Nav3/Koin 不引。
2. **legados**：学「SwipeActionContainer/VerticalScrollbar/CommonPageColors + 统计卡模板」，并吸取“我的页没跟上、组件库有壳无肉”的教训。
3. **Rimchars**：学「AppSettingComponents 731 行组件族 + palette+signature 取色桥 + 全站搜索」，这是最可直接落地的组件化武装。
4. **legado_NG**：学「双端 Token 系统思路 + Glassmorphism + NDS 工程验收」，但不引 MaterialKolor/MaterialK 依赖。
5. **鸿蒙版**：学「我的页统计卡→高频卡→低频列表的三级信息架构」与「WebDAV 独立卡」——这是用户点名要的布局方案，且用真实数据（区别于鸿蒙版写死占位）。

## 八、风险与红线

- 组件化推进**不破坏**既有 View 页面（迁移渐进，非全量）。
- 阅读器正文/翻页引擎绝不动（REM 前端路由）；仅浮层 Sheet 化。
- 不引入新第三方 UI 框架依赖（MaterialK/GDEY）；MaterialK(o)? 已否决。
- 「我的」页 Compose 化前后功能等价，pref 死代码清理需回归 4 组入口。