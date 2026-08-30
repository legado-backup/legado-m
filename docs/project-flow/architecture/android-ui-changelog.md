# Android UI 架构 · 统计与变更记录册（android-ui-changelog）

> **隶属关系**：本文档由原 `docs/project-flow/architecture/android-ui.md`（1988 行/26 章）拆分而来，四册同目录：
> - 姊妹册 [android-ui-core.md](android-ui-core.md) — 主框架/活动/Fragment/基类/导航/启动引导 + 顶栏体系（N1）+ Compose 化现状（N2）
> - 姊妹册 [android-ui-pages.md](android-ui-pages.md) — 核心页面布局与交互 + 书源调试/搜索范围/发现页/关联导入/辅助工具 + 订阅页双模式（N3）+ 发现页缓存加固（N4）
> - 姊妹册 [android-ui-media-theme.md](android-ui-media-theme.md) — 阅读/排版/漫画/音频/Widget/主题/资源/横屏 + EPUB 渲染与高亮（N5）+ 播放器画质增强（N6）
> - **本册 android-ui-changelog.md** — UI 层源码统计（重数修正版）+ 时敏优化记录（原 §25/§26）
>
> **一句话定位**：UI 层体量统计权威数据源与历史时敏优化记录归档。

## 本册目录

| 章 | 内容 | 对应原章 |
|----|------|---------|
| §1 | UI 层源码统计（2026-08-30 重数修正） | 原 §18 |
| §2 | UI/UX 优化记录（2026-07-04） | 原 §25 |
| §3 | 书源/订阅源文件夹视图重构（2026-07-08） | 原 §26 |

---

## 1. UI 层源码统计

> 2026-08-30 实测重数（原稿数字已全面修正）。原稿统计基于早期快照（如 ui/ ~260 文件、ReadBookActivity 1716 行、菜单 91 个），与当前代码差距巨大，禁止再引用旧数字。

### 1.1 总体规模

| 指标 | 数值（实测 2026-08-30） | 原稿旧值 |
|------|------|------|
| ui/ 下 .kt 文件总数 | **675** | ~260 |
| ui/widget/ Kotlin 文件 | **128**（子目录 13 个） | 60 / 10 子目录 |
| ui/widget/compose/ | 20 文件 | —（新增） |
| ui/widget/components/ | 33 文件 | —（新增） |
| 布局 XML（res/layout） | **167**（另 layout-land 4） | 216 |
| 菜单 XML（res/menu） | **16** | 91 |
| 自定义属性组 | **46** 个 declare-styleable | 23 |
| 主题感知控件 | **8** 个 ThemeView（lib/theme/view/ 实测文件清单复核） | 8 |

### 1.2 大文件 Top 榜

| 文件 | 行数（实测） | 原稿旧值 | 备注 |
|------|------|------|------|
| ui/main/explore/ExploreFragment.kt | 4004 | 未记录 | 发现页（缓存加固见 pages 册 §9） |
| ui/main/rss/RssFragment.kt | 1464 | 未记录 | 订阅页双模式（pages 册 §8） |
| ui/book/read/ReadBookActivity.kt | **5208** | 1716 | 全 ui/ 最大；override 方法 125 个 |
| ui/book/read/page/provider/TextChapterLayout.kt | **2656** | 1271 | 排版引擎 |
| ui/config/NavigationBarManageActivity.kt | 1283 | 未记录 | 底部导航管理 |
| ui/widget/image/PhotoView.kt | 1294 | 1260 | Widget 最大 |
| ui/book/source/manage/BookSourceActivity.kt | 1204 | 未记录 | 书源管理 |
| ui/book/manga/ReadMangaActivity.kt | 993 | 856 | 漫画阅读 |
| ui/config/AiConfigFragment.kt | 971 | 未记录 | 调试工具箱（全 Compose） |
| ui/widget/dialog/BottomWebViewDialog.kt | 944 | 884 | WebView 弹窗 |
| ui/book/source/edit/BookSourceEditActivity.kt | 856 | 未记录 | 书源编辑 |
| ui/main/MainActivity.kt | 2548 | 441（原文锚点） | 主框架 |

### 1.3 布局前缀分布（实测 2026-08-30）

| 前缀 | 数量 | 原稿旧值 |
|------|------|------|
| activity_ | 63 | 40 |
| item_ | 42 | 67 |
| view_ | 21 | 25 |
| dialog_ | 18 | 61 |
| fragment_ | 8 | 10 |
| popup_ | 4 | 4 |
| video_ | 3 | 4 |
| 合计 | 167 | 216 |

### 1.4 页面布局组件统计（历史快照，待重数）

> 以下小节为原稿 2026-07-08 基于当时 50 个主布局文件的分析结论；布局总量已从 216 变为 167，**明细数字已不可信，标注待重数**。结论性特征仍具参考价值。

共分析 **50 个主布局文件**（40 Activity + 10 Fragment），总 UI 组件 **416 个**，平均每页 8.3 个组件。（待重数）

**组件数 Top 10 页面**（待重数）：

| 页面 | 布局文件 | 组件数 | 复杂度来源 |
|------|----------|--------|-----------|
| 书籍详情 | activity_book_info.xml | 41 | 11层LinearLayout嵌套+7个TextView+6个ImageView |
| 音频播放 | activity_audio_play.xml | 27 | 6个ImageButton+5个View+5个TextView |
| 代码编辑 | activity_code_edit.xml | 24 | 6个LinearLayout+4个Button+4个TextView |
| 替换规则编辑 | activity_replace_edit.xml | 24 | 7个TextInputLayout+7个ThemeEditText |
| 书籍信息编辑 | activity_book_info_edit.xml | 22 | 6个LinearLayout+4个TextInputLayout+4个ThemeEditText |
| 书源调试 | activity_source_debug.xml | 18 | 11个TextView（调试消息区） |
| 书源编辑 | activity_book_source_edit.xml | 16 | 6个ThemeCheckBox（规则开关） |
| RSS源编辑 | activity_rss_source_edit.xml | 16 | 4个ThemeCheckBox+2个Spinner |
| 视频播放 | activity_video_player.xml | 16 | 5个LinearLayout+2个RecyclerView |
| RSS源调试 | activity_rss_source_debug.xml | 14 | 7个TextView（调试消息区） |

**全局组件类型分布（Top 10）**（待重数）：

| 组件类型 | 出现次数 | 说明 |
|---------|---------|------|
| LinearLayout | 73 | 最常用布局容器 |
| TextView | 60 | 最基础展示组件 |
| TitleBar（自定义） | 40 | 几乎每页必备的标题栏 |
| ConstraintLayout | 24 | 现代布局容器 |
| FrameLayout | 24 | 简单堆叠容器 |
| RecyclerView | 15 | 列表展示 |
| ThemeCheckBox（自定义） | 13 | 主题感知复选框 |
| FastScrollRecyclerView（自定义） | 12 | 带快速滚动的列表 |
| TextInputLayout | 11 | 输入框容器 |
| ThemeEditText（自定义） | 11 | 主题感知输入框 |

**特征总结**（定性结论，仍成立）：
- **约半数页面仅 3~5 个组件**：采用 TitleBar + RecyclerView 的极简模式
- **编辑页最复杂**：表单类页面组件密度最高
- **阅读页特殊**：布局组件少，ReadView/ReadMenu 内部承载大量逻辑
- **自定义组件占比高**：TitleBar、FastScrollRecyclerView、ThemeCheckBox 为三大高频自定义组件

---

## 2. UI/UX 优化记录（2026-07-04）

> 基于深度 16 维度分析，完成 8 个任务组的系统性 UI 优化。详细设计文档见 [specs/android-ui-optimization/](../../../specs/android-ui-optimization/)

### 2.1 Design Token 体系（新增）

| Token 组 | Token 数 | 值范围 |
|----------|---------|--------|
| Corner Radius | 4 | 4dp / 8dp / 12dp / 16dp |
| Typography Scale | 12 | 11sp~36sp（M3 子集） |
| Spacing (4dp Grid) | 6 | 4dp~32dp |
| Elevation (M3 Level) | 6 | 0dp~12dp |

### 2.2 关键变更摘要

| 类别 | 变更数 | 说明 |
|------|--------|------|
| P0 Bug 修复 | 11 | 暗色不可见/WCAG 对比度/Toast Android 11+/viewport 异常 |
| Design Token | 4 组 | Corner/Typography/Spacing/Elevation |
| 暗色模式补全 | 5 项 | highlight/error/success/lightBlue/硬编码色替换 |
| 布局现代化 | 7 项 | 触控目标/BottomNav/FAB Elevation/Crossfade/SoftInputMode |
| 圆角统一 | 4 级 | shape_corner_extra_small/small/medium/large |
| 图标修正 | 6 项 | viewport/dp尺寸/fillColor 统一 |
| 触控目标修复 | 26+ | seek 控制/播放控制/列表项操作图标→48dp |
| Popup 圆角 | 3 个 | shape_corner_small (8dp) |

### 2.3 新增 Drawable

- `shape_corner_extra_small.xml` (4dp) — 极小圆角，适用于紧凑组件
- `shape_corner_small.xml` (8dp) — 小圆角，适用于 Popup/ActionMenu
- `shape_corner_medium.xml` (12dp) — 中等圆角，适用于 Card/Dialog（替代原 3dp 的 shape_card_view）
- `shape_corner_large.xml` (16dp) — 大圆角，适用于大容器

### 2.4 WCAG 对比度提升

| 颜色 | 修改前 | 修改后 | 对比度提升 |
|------|--------|--------|-----------|
| tv_text_summary (亮色) | #8A2C2C2C (~3.3:1) | #8A000000 (~4.6:1) | ✅ AA 达标 |
| primary (亮色) | md_light_blue_600 | md_light_blue_800 (~5.0:1) | ✅ AA 达标 |
| accent (暗色) | md_deep_orange_800 | md_deep_orange_500 (~5.5:1) | ✅ AA 达标 |

### 2.5 验证状态

| 验证项 | 结果 |
|--------|------|
| 自动化检查 (10项) | ✅ 全部通过 |
| Gradle 编译 | ✅ assembleAppDebug 成功 |
| APK 生成 | ✅ legado_app_3.26.070420.apk |
| 暗色模式视觉 | 🔄 需真机验证 |
| 触控目标视觉 | 🔄 需真机验证 |
| WCAG 对比度实测 | 🔄 需真机验证 |

---

## 3. 书源/订阅源文件夹视图重构（2026-07-08）

> 本次重构统一书源/订阅源列表的文件夹视图卡片样式，参考书架封面风格，并抽取通用的 Grid 间距装饰器与配置对话框。
> 页面侧消费方（书源管理页/订阅页经典形态）见 pages 册 §1.5 与 §8。

### 3.1 新增布局文件

| 布局文件 | 用途 |
|---------|------|
| `item_source_folder_grid.xml` | 书源/订阅源文件夹视图卡片：3:4 比例 + 首字占位 + 主题色背景 + MaterialCardView + selectableItemBackground |
| `dialog_source_folder_config.xml` | 文件夹视图配置对话框：分组样式 Spinner + 视图 RadioGroup + 间距 DetailSeekBar |

### 3.2 新增 Drawable

- `bg_source_folder_cover.xml`：文件夹封面主题色背景 drawable，用于无封面时的占位渐变背景

### 3.3 新增类

| 类 | 路径 | 职责 |
|----|------|------|
| `GridSpacingItemDecoration` | `ui/widget/recycler/GridSpacingItemDecoration.kt` | Grid 布局等间距装饰器，统一管理网格项间距，支持配置对话框实时调整 |

### 3.4 修改类

| 类 | 变更内容 |
|----|---------|
| `SourceFolderAdapter.kt` | 改用新布局 `item_source_folder_grid.xml`；新增 `showConfigDialog()`、`calculateSpanCount()`、`spacingPx()` |
| `BookSourceActivity` / `RssSourceActivity` / `ExploreFragment` / `RssFragment` | `switchViewMode()` → `showFolderConfig()`，`applyListView`/`applyFolderView` 重构 |
| `BitmapUtils.kt` | 新增 `cropBitmapToAspectRatio(srcPath, ratioW, ratioH)`，按指定宽高比裁剪图片 |
| `WelcomeConfigFragment.kt` | `setCoverFromUri()` 调用 `cropBitmapToAspectRatio` 进行封面裁剪 |
| `AutoTaskEditActivity.kt` | Cron 频率选择器（每天 / 每小时 / 自定义） |
| `OtherConfigFragment.kt` | 新增 `debug_tools` 入口 |
| `MyFragment.kt` | 移除 `debug_tools` 入口（迁移至 OtherConfigFragment） |

### 3.5 设计说明

- **卡片样式**：3:4 宽高比与书架书籍封面保持一致，无封面时使用分组名首字 + 主题色背景占位
- **主题色背景**：`bg_source_folder_cover.xml` 使用主题色，保证日/夜间模式视觉一致
- **交互反馈**：MaterialCardView 提供统一阴影和圆角，selectableItemBackground 提供点击 ripple 反馈
- **间距管理**：GridSpacingItemDecoration 统一管理网格间距，避免逐项设置 margin；间距可通过 `dialog_source_folder_config.xml` 配置对话框实时调整
- **入口迁移**：`debug_tools` 入口从 `MyFragment` 迁移至 `OtherConfigFragment`，与其它调试/工具类入口归并
- **后续演进**：订阅页经典形态的文件夹/标签/间距偏好已由 `sourceGroupStyle`/`sourceGroupMode`/`sourceMargin` 承接（原 `rssViewMode` 已删除），见 pages 册 §8.2

---

*本册由 android-ui.md 拆分生成（2026-08-30）。§2/§3 为历史时敏记录，保留原始日期与结论；§1 统计为 2026-08-30 实测，后续请重数更新。*
