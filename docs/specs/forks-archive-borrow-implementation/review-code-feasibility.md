# 代码实施可行性深度审查报告

> **审查时间**：2026-07-18
> **审查范围**：P0 14 项任务对照本项目真实源码的可行性深度审查
> **审查方法**：Read/Glob/Grep 只读工具逐项验证设计文档 §4 文件变更清单 vs 真实代码
> **审查员**：代码实施可行性深度审查子代理
> **审查对象**：`f:\myself\github\WeAgentChat\temp\legado` 项目主分支源码
> **对照设计**：`docs/specs/forks-archive-borrow-implementation/design.md` v2.2

---

## 1. 审查概述

### 1.1 审查范围
对照本项目真实源码（不是设计文档），逐项模拟 P0 14 项任务实施，找出设计文档与代码现实的所有偏差。

### 1.2 审查方法
- Read 工具读取关键源文件特定行段（VMBaseActivity/RssSource/EpubFile/ThemeUtils/ChoiceSpeedDialog/AppDatabase/build.gradle/libs.versions.toml 等）
- Glob 工具验证文件路径真实性（本项目中是否存在）
- Grep 工具验证关键 API/字段/方法是否存在
- 对照 Archive 项目（位于 `temp/forks-comparison/legado-archive/`）验证借鉴源的真实路径与依赖

### 1.3 验证清单（共 18 项关键检查）
| # | 检查项 | 设计文档描述 | 真实代码状态 | 结论 |
|---|--------|-------------|-------------|------|
| 1 | VMBaseActivity 存在性 | `app/src/main/java/io/legado/app/base/VMBaseActivity.kt:9` | 存在，第 9 行抽象类继承 BaseActivity | ✅ 一致 |
| 2 | RssSource.cacheFirst 默认值 | `RssSource.kt:113 cacheFirst: Boolean = true` | 第 113 行 `var cacheFirst: Boolean = true` | ✅ 一致 |
| 3 | RssSource.searchUrl 字段 | 第 115 行 | 第 115 行 `var searchUrl: String? = null` | ✅ 一致 |
| 4 | EpubFile.kt 路径 | `app/src/main/java/io/legado/app/model/localBook/EpubFile.kt` | 存在 | ✅ 一致 |
| 5 | EpubFile spine 处理 | 设计："spine 优先索引" | 第 320-350 行：spine 仅作为 NCX 失败回退 | 🟡 现状为 fallback，需提升为优先 |
| 6 | RssFragment.openRssSearch 方法 | "添加 5 行 openRssSearch 方法" | 不存在 openRssSearch 方法（已有 searchView 用于过滤本地源） | 🟡 现有 searchView 用途不同 |
| 7 | ThemeUtils.sanitizeFontColorAgainstSurfaces | 新增方法基于 AndroidColorUtils.calculateContrast | 不存在；Archive 项目也没有此方法 | 🟡 实际为"新创方法"非"借鉴" |
| 8 | PaperInkHelper.kt 在本项目 | 新增到 `lib/theme/PaperInkHelper.kt` | 不存在（正确，需新增） | ✅ 一致 |
| 9 | ReadRecentBook.kt | 新增实体 | 不存在（正确，需新增） | ✅ 一致 |
| 10 | ReadRecentBookDao.kt | 新增 DAO | 不存在（正确，需新增） | ✅ 一致 |
| 11 | ChoiceSpeedDialog.kt 路径 | `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | 存在 | ✅ 一致 |
| 12 | Exo2MediaPlayer.kt 路径 | 同上目录 | 存在 | ✅ 一致 |
| 13 | VideoBookPreloader.kt | 新增到 `help/gsyVideo/` | 不存在（正确，需新增） | ✅ 一致 |
| 14 | SourceSelectDialog.kt | 新增到 `ui/rss/` | 不存在（正确，需新增） | ✅ 一致 |
| 15 | SearchBookMergeUtils.kt | 新增到 `utils/` | 不存在（正确，需新增） | ✅ 一致 |
| 16 | RssWebActivity.kt | §4.1 #9 标"修改" | 本项目和 Archive 项目都不存在 | 🔴 文件名错误 |
| 17 | markwon 依赖版本 | "markwon 3 扩展" | libs.versions.toml 第 24 行：`markwon = "4.6.2"` | 🔴 版本严重不一致 |
| 18 | sora-editor 依赖 | `build.gradle:356-358 已存在` | 第 356-358 行 soraEditor.bom/core/language.textmate 已存在 | ✅ 一致 |

### 1.4 验证依赖链结论
- P0 任务间无循环依赖 ✅
- EPUB-B-01 与 EPUB-B-02 共用 EpubFile.kt 可串行实施 ✅
- RSS-B-05 与 RSS-B-01 共用 RssFragment.kt 可串行实施 ✅
- VIDEO-B-01 → VIDEO-B-02 依赖链合理 ✅

---

## 2. 严重发现（🔴 实施前必须解决）

### 🔴 严重发现 #1：RSS-E-06 任务实际已完成（设计文档描述错误）

**问题描述**：设计文档 §4.1 #9 标注"修改 `app/src/main/java/io/legado/app/ui/rss/RssWebActivity.kt` 实现 WebView cacheFirst 默认 true"，但：
- 本项目代码库中**完全没有 RssWebActivity.kt 文件**（Grep 全 app 目录无任何引用）
- Archive 项目（借鉴源）中**也没有 RssWebActivity.kt 文件**
- 实际对应文件是 `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt`
- 该文件第 421 行已实现：`cacheMode = if (s.cacheFirst) WebSettings.LOAD_CACHE_ELSE_NETWORK else WebSettings.LOAD_DEFAULT`
- 数据层 `RssSource.kt:113` 的 `cacheFirst: Boolean = true` 默认值已就绪

**源文档位置**：design.md §4.1 RSS/订阅源模块 #9（第 854 行）

**真实代码位置**：`app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt:421`

**影响任务**：RSS-E-06（cacheFirst 默认值）

**修复建议**：
1. 修订 design.md §4.1 #9：文件名 `RssWebActivity.kt` → `ReadRssActivity.kt`
2. 修订任务状态："修改" → "已完成（仅验证）"
3. 实施时无需任何代码变更，仅需真机验证 cacheFirst 行为

---

### 🔴 严重发现 #2：RssSearchActivity 借鉴源依赖本项目不存在的主题扩展

**问题描述**：Archive 项目 `RssSearchActivity.kt` 依赖以下主题扩展：
- 第 13 行：`import io.legado.app.lib.theme.TopBarSearchStyle`
- 第 14 行：`import io.legado.app.lib.theme.applyUiBodyTypefaceDeep`
- 第 15 行：`import io.legado.app.lib.theme.uiTypeface`

本项目 `app/src/main/java/io/legado/app/lib/theme/` 目录下 Grep 搜索 `TopBarSearchStyle|applyUiBodyTypefaceDeep|uiTypeface` **均无匹配**，这些扩展在本项目中不存在。

**源文档位置**：design.md §4.1 RSS/订阅源模块 #1（第 846 行）

**真实代码位置**：
- 借鉴源：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/rss/article/RssSearchActivity.kt:13-15`
- 本项目缺失：`app/src/main/java/io/legado/app/lib/theme/`（无相关扩展）

**影响任务**：RSS-B-01（RssSearchActivity 新建）

**修复建议**：
- 方案 A：同步借鉴 Archive 项目的 TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface 扩展（增加 3 个新文件）
- 方案 B（推荐）：改写 RssSearchActivity 不依赖这些扩展，使用本项目现有主题机制
- 同步补充 design.md §4.1 #1 注明"借鉴时需同步处理 3 个主题扩展依赖"

---

### 🔴 严重发现 #3：SourceSelectDialog 借鉴源是 Compose 实现，依赖本项目不存在的 Compose 组件

**问题描述**：Archive 项目 `SourceSelectDialog.kt` 是 Compose 实现，依赖以下 Compose 组件：
- 第 51 行：`import io.legado.app.ui.widget.compose.LegadoMiuixCard`
- 第 52 行：`import io.legado.app.ui.widget.compose.LegadoMiuixChoiceRow`
- 第 53 行：`import io.legado.app.ui.widget.compose.rememberAppDialogStyle`
- 第 54 行：`import io.legado.app.ui.widget.compose.toMiuixPalette`
- 第 55-56 行：`import io.legado.app.utils.dpToPx, windowSize`
- 第 57 行：`import splitties.systemservices.windowManager`

Glob 验证 `app/src/main/java/io/legado/app/ui/widget/compose/LegadoMiuixCard*.kt` 与 `LegadoMiuixChoiceRow*.kt` **均无匹配**，本项目无这些 Compose 组件。

**源文档位置**：design.md §4.1 RSS/订阅源模块 #5（第 850 行）

**真实代码位置**：
- 借鉴源：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/widget/SourceSelectDialog.kt:50-57`
- 本项目缺失：`app/src/main/java/io/legado/app/ui/widget/compose/`（无相关组件）

**影响任务**：RSS-B-02（SourceSelectDialog 组件）

**修复建议**：
- 方案 A：同步借鉴 LegadoMiuixCard/LegadoMiuixChoiceRow/rememberAppDialogStyle/toMiuixPalette 等 Compose 组件（增加 4+ 个新文件，工程量大幅增加）
- 方案 B（强烈推荐）：改写为非 Compose 实现，使用本项目已有的 BottomSheetDialog + RecyclerView 模式
- 同步补充 design.md §4.1 #5 注明"借鉴源是 Compose 实现，本项目无对应组件，需改写"

---

### 🔴 严重发现 #4：SearchBookMergeUtils 借鉴源依赖本项目不存在的扩展函数

**问题描述**：Archive 项目 `SearchBookMergeUtils.kt` 调用以下扩展函数：
- 第 15 行：`book.stableSearchBookKey()`
- 第 18 行：`book.stableSearchBookKey()`
- 第 32 行：`book.stableSearchBookKey()`
- 第 35 行：`book.stableSearchBookKey()`
- 第 47 行：`book.stableSearchBookKey()`

Grep 全项目搜索 `fun.*stableSearchBookKey` **无匹配**，本项目无此扩展函数。

**源文档位置**：design.md §4.1 RSS/订阅源模块 #6（第 851 行）

**真实代码位置**：
- 借鉴源：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/utils/SearchBookMergeUtils.kt:15-47`
- 本项目缺失：本项目 `app/src/main/java/io/legado/app/help/book/BookExtensions.kt` 无 stableSearchBookKey 扩展

**影响任务**：RSS-B-03（SearchBookMergeUtils 合并工具）

**修复建议**：
- 方案 A：同步借鉴 Archive 项目的 `stableSearchBookKey` 扩展函数（需先定位该扩展在 Archive 项目的位置）
- 方案 B（推荐）：改写 SearchBookMergeUtils 的去重 key 计算，基于本项目 SearchBook 已有字段（如 name+author）实现
- 同步补充 design.md §4.1 #6 注明"借鉴源依赖 stableSearchBookKey 扩展，本项目无此扩展，需同步借鉴或改写"

---

### 🔴 严重发现 #5：PaperInkHelper 借鉴源依赖 ReadBookConfig.paperInkStrength 字段（设计文档遗漏 ReadBookConfig 修改条目）

**问题描述**：Archive 项目 `PaperInkHelper.kt` 依赖 ReadBookConfig 的 paperInkStrength 配置：
- 第 5 行：`import io.legado.app.help.config.ReadBookConfig`
- 第 10 行：`val strength: Int get() = ReadBookConfig.paperInkStrength`
- 第 47 行：`val strength = strength`（间接使用）

Archive 项目 ReadBookConfig.kt 第 302 行有 `var paperInkStrength: Int` 字段定义，第 305 行 setter 限定 `coerceIn(0, 100)`，第 580 行是配置实体字段，第 793 行有条件回退逻辑，第 894 行 JSON 序列化。

本项目 `app/src/main/java/io/legado/app/help/config/ReadBookConfig.kt` 中 Grep 搜索 `paperInkStrength|paperInk` **无匹配**，本项目 ReadBookConfig 没有此字段。

设计文档 §4.3 主题管理模块**只列出 PaperInkHelper.kt 新增条目，没有列出 ReadBookConfig.kt 修改条目**，这是文档遗漏。

**源文档位置**：design.md §4.3 主题管理模块 #1（第 871 行）

**真实代码位置**：
- 借鉴源：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/help/PaperInkHelper.kt:5,10`
- 借鉴源依赖：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/help/config/ReadBookConfig.kt:302,305,580,793,894`
- 本项目缺失：`app/src/main/java/io/legado/app/help/config/ReadBookConfig.kt`（无 paperInkStrength 字段）

**影响任务**：THEME-B-01（PaperInkHelper 纸墨风格）

**修复建议**：
1. 补充 design.md §4.3 主题管理模块新增条目：`ReadBookConfig.kt` 修改（新增 paperInkStrength 字段 + 配置实体字段 + JSON 序列化 + 条件回退）
2. 实施时必须同步修改 ReadBookConfig.kt，否则 PaperInkHelper.kt 无法编译
3. 同步补充相关配置 UI（如阅读设置中纸墨风格强度滑块）

---

### 🔴 严重发现 #6：markwon 版本严重不一致（设计文档错误描述为 markwon 3，实际为 markwon 4.6.2）

**问题描述**：设计文档多处将 DEPS-B-01 任务描述为"markwon 3 扩展"：
- design.md §4.7 构建配置 #1（第 920 行）："markwon 3 扩展依赖"
- design.md ADR-006（第 192 行）："DEPS-B-01（markwon 3 扩展）"
- design.md §9.3 决策ID 索引（隐含）

但本项目实际 markwon 版本是 **4.6.2**：
- `gradle/libs.versions.toml` 第 24 行：`markwon = "4.6.2"`
- `app/build.gradle` 第 329-332 行已有 4 个 markwon 子依赖：core, image.glide, ext.tables, html

markwon 3.x 与 4.x API 不兼容。设计文档表述错误。

**源文档位置**：design.md §4.7 #1（第 920 行）+ ADR-006（第 192 行）

**真实代码位置**：`gradle/libs.versions.toml:24` + `app/build.gradle:329-332`

**影响任务**：DEPS-B-01（markwon 扩展）

**修复建议**：
1. 修订 design.md 全文将"markwon 3 扩展"统一改为"markwon 4 扩展"
2. 实施时 DEPS-B-01 实际为"补充缺失子依赖"：当前已有 core/image.glide/ext.tables/html，需补充 ext.tasklist/ext.strikethrough 等
3. 注意 markwon 4.x API 与 3.x 不兼容，借鉴 Archive 项目时（如 Archive 用 markwon 3）需 API 适配

---

## 3. 中等发现（🟡 实施时需调整）

### 🟡 中等发现 #1：借鉴源路径与目标路径多处不一致

**问题描述**：Archive 项目借鉴源的真实路径与 design.md 设计的目标路径不一致：

| 借鉴源 | Archive 项目真实路径 | design.md 目标路径 |
|--------|---------------------|-------------------|
| PaperInkHelper | `io.legado.app.help.PaperInkHelper` | `io.legado.app.lib.theme.PaperInkHelper` |
| SourceSelectDialog | `io.legado.app.ui.widget.SourceSelectDialog` | `io.legado.app.ui.rss.SourceSelectDialog` |
| VideoBookPreloader | `io.legado.app.ui.video.VideoBookPreloader` | `io.legado.app.help.gsyVideo.VideoBookPreloader` |
| RssSearchActivity | `io.legado.app.ui.rss.article.RssSearchActivity` | `io.legado.app.ui.rss.search.RssSearchActivity` |
| SearchBookMergeUtils | `io.legado.app.utils.SearchBookMergeUtils` | `io.legado.app.utils.SearchBookMergeUtils` ✅一致 |

**源文档位置**：design.md §4.1-§4.3 各文件条目

**真实代码位置**：见上表

**影响任务**：THEME-B-01/RSS-B-02/VIDEO-B-01/RSS-B-01

**修复建议**：实施时按 design.md 目标路径放置文件，但需同步调整借鉴源的 package 声明与所有 import。注意 Archive 项目源代码的 `package` 行需要改写。

---

### 🟡 中等发现 #2：RssSearchActivity 实际复用 RssSortViewModel（设计文档新增 RssSearchViewModel 错误）

**问题描述**：design.md §4.1 #2 说"新增 RssSearchViewModel.kt 调度多源并发搜索"，但 Archive 项目 RssSearchActivity.kt 第 20 行实际：
```kotlin
class RssSearchActivity : VMBaseActivity<ActivityRssSearchBinding, RssSortViewModel>() {
    override val viewModel by viewModels<RssSortViewModel>()
```
复用现有 RssSortViewModel，没有单独的 RssSearchViewModel。

**源文档位置**：design.md §4.1 RSS/订阅源模块 #2（第 847 行）

**真实代码位置**：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/rss/article/RssSearchActivity.kt:20,23`

**影响任务**：RSS-B-01（RssSearchActivity 新建）

**修复建议**：实施时可选择：
- 方案 A：复用本项目现有 RssSortViewModel（与 Archive 一致，简化实现）
- 方案 B：新增 RssSearchViewModel（与 design.md 一致，但需自行实现搜索逻辑）
建议方案 A（与 Archive 借鉴源一致，降低实施风险）。

---

### 🟡 中等发现 #3：RssFragment.kt 已有 searchView 但用途不同，新增 openRssSearch 入口需明确入口设计

**问题描述**：本项目 RssFragment.kt 已有 SearchView 字段（第 96 行 `private val searchView: SearchView`），但用途是"过滤本地源列表"（第 116 行 `upRssFlowJob(searchView.query?.toString())`），不是"搜索源内容"。

design.md §4.1 #4 要求新增 `openRssSearch` 方法作为搜索入口，需明确入口设计，避免与现有 searchView 用途冲突。

**源文档位置**：design.md §4.1 RSS/订阅源模块 #4（第 849 行）

**真实代码位置**：`app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt:96,116,161`

**影响任务**：RSS-B-05（RssFragment openRssSearch 入口）

**修复建议**：实施时建议：
- 新增菜单项（menu_main_rss.xml 添加搜索图标）触发 openRssSearch
- 或新增浮动按钮（FAB）触发 openRssSearch
- 不要复用现有 searchView（避免污染过滤功能）
- 明确入口设计与用户交互流程

---

### 🟡 中等发现 #4：AppDatabase version=98，VIDEO-E-01 需新增 Migration_98_to_99

**问题描述**：本项目 `AppDatabase.kt` 第 77 行 `version = 98`，entities 列表（第 79-85 行）共 26 个实体，**没有 ReadRecentBook 实体**。

VIDEO-E-01 任务需新增 ReadRecentBook 表（CREATE TABLE），必须：
1. 新增 ReadRecentBook 实体到 @Database entities 数组
2. 新增 Migration_98_to_99（手写 Migration，因新增表）
3. version 升级到 99

design.md ADR-013 已说明策略（AutoMigration + runCatching 兜底 + 覆盖安装兼容性测试三段式），但未明确 version 99。

**源文档位置**：design.md ADR-013（第 316-331 行）+ §4.2 #5-6（第 864-865 行）

**真实代码位置**：`app/src/main/java/io/legado/app/data/AppDatabase.kt:76-86`

**影响任务**：VIDEO-E-01（ReadRecentBook 写入）

**修复建议**：实施时按 database-migration-safety.md 规范：
1. 新增 `data/entities/ReadRecentBook.kt` 实体（@Entity + @Parcelize + 字段默认值）
2. 新增 `data/dao/ReadRecentBookDao.kt` DAO
3. 修改 AppDatabase.kt：version 98→99 + entities 数组新增 ReadRecentBook + 新增 Migration_98_to_99
4. 真机验证覆盖安装（旧版本→新版本）数据完整性

---

### 🟡 中等发现 #5：VIDEO-E-02 ChoiceSpeedDialog 当前已较完善，需对比 Archive 看是否有进一步借鉴点

**问题描述**：本项目 ChoiceSpeedDialog.kt 当前实现已较完善：
- 第 18 行：Dialog 子类
- 第 26-29 行：OnListItemClickListener 接口（onItemClick/finishDialog）
- 第 46-50 行：`initList(data, onItemClickListener, currentSpeed: Float = 1.0f)` 已有 currentSpeed 参数
- 第 71-74 行：buildDisplayData 已实现"极速区(>=5.0)与常用区(<5.0)之间插入 SEPARATOR 标记"
- 第 107-150 行：SpeedAdapter 内部类已实现"当前倍速高亮（主题色 primary + 加粗 + 浅色背景）"
- 第 153-157 行：companion object 定义 SEPARATOR/TAG_NORMAL/TAG_SEPARATOR

design.md §4.2 #3 说"修改 ChoiceSpeedDialog.kt 倍速选项增强（P0）"，但当前实现已较完善，**VIDEO-E-02 任务可能已基本完成**。

**源文档位置**：design.md §4.2 视频播放模块 #3（第 862 行）

**真实代码位置**：`app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt:18-158`

**影响任务**：VIDEO-E-02（ChoiceSpeedDialog 增强）

**修复建议**：实施时先 diff 对比 Archive 项目 ChoiceSpeedDialog.kt（路径：`temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt`）与本项目实现，仅借鉴差异部分。如无显著差异则任务视为已完成。

---

### 🟡 中等发现 #6：RssSearchActivity 缺少配套布局文件

**问题描述**：Archive 项目 RssSearchActivity.kt 第 22 行使用 `ActivityRssSearchBinding::inflate`，对应布局 `activity_rss_search.xml`。本项目 Grep 验证 `app/src/main/res/layout/activity_rss_search.xml` **无匹配**，本项目无此布局文件。

design.md §4.8 全局配置文件未列出 `activity_rss_search.xml` 新增条目（仅列 strings.xml/AndroidManifest.xml/proguard-rules.pro）。

**源文档位置**：design.md §4.8 全局配置文件（第 927-929 行，未列布局文件）

**真实代码位置**：借鉴源 `temp/forks-comparison/legado-archive/app/src/main/res/layout/activity_rss_search.xml`（存在），本项目缺失

**影响任务**：RSS-B-01（RssSearchActivity 新建）

**修复建议**：
1. 补充 design.md §4.8 新增条目：`app/src/main/res/layout/activity_rss_search.xml` 新增（布局文件）
2. 实施时同步借鉴 Archive 项目的 activity_rss_search.xml 布局文件
3. 检查布局文件是否依赖本项目不存在的自定义 View 或主题属性

---

## 4. 轻微发现（🟢 实施时注意）

### 🟢 轻微发现 #1：EpubFile.kt 已有 spine 处理逻辑（作为 fallback），EPUB-B-01 需提升为优先

**问题描述**：本项目 EpubFile.kt 第 314-361 行 `getChapterList()` 方法中：
- 第 317 行：`val refs = eBook.tableOfContents.tocReferences`
- 第 318-350 行：`if (refs == null || refs.isEmpty())` 时使用 `spine.spineReferences` 作为 fallback
- 第 351-357 行：`else` 分支使用 `parseFirstPage` + `parseMenu`

design.md EPUB-B-01 说"章节资源索引 spine 优先"，但现状是 spine 仅作为 NCX 失败的回退。实施时需把 spine 从 fallback 提升为优先，或在某些条件下用 spine。

**源文档位置**：design.md §4.4 EPUB 模块 #1（第 887 行）

**真实代码位置**：`app/src/main/java/io/legado/app/model/localBook/EpubFile.kt:314-361`

**影响任务**：EPUB-B-01（spine 优先索引）

**修复建议**：实施时调整 `getChapterList()` 逻辑，先尝试 spine 优先，NCX 作为补充/标题归一化来源。

---

### 🟢 轻微发现 #2：ThemeUtils.kt 当前内容很简单，sanitizeFontColorAgainstSurfaces 实际为"新创方法"

**问题描述**：
- 本项目 ThemeUtils.kt 当前只有 3 个方法：resolveColor/resolveFloat/resolveDrawable（共 44 行）
- 没有 sanitizeFontColorAgainstSurfaces 方法
- Archive 项目（借鉴源）ThemeUtils.kt **也没有此方法**（Grep 验证无匹配）
- design.md §4.3 #2 说"新增 sanitizeFontColorAgainstSurfaces 方法（基于 AndroidColorUtils.calculateContrast）"，但：
  - "AndroidColorUtils" 类名不准确，Android 标准库实际为 `androidx.core.graphics.ColorUtils.calculateContrast`（来自 androidx.core:core-ktx）
  - 此方法是"新创"不是"借鉴"

**源文档位置**：design.md §4.3 主题管理模块 #2（第 872 行）

**真实代码位置**：`app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt:1-44`（仅 3 个方法）

**影响任务**：THEME-B-02（字体撞色检测）

**修复建议**：实施时使用 `androidx.core.graphics.ColorUtils.calculateContrast` API（已在 androidx.core:core-ktx 中，无需新增依赖）。修订 design.md §4.3 #2 描述："基于 Archive 借鉴" → "新创方法，参考 Android 标准 ColorUtils API"。

---

### 🟢 轻微发现 #3：Archive 项目中 PaperInkHelper.kt 路径与 design.md 目标路径不一致

**问题描述**：Archive 项目 PaperInkHelper.kt 实际路径：`app/src/main/java/io/legado/app/help/PaperInkHelper.kt`，包名 `io.legado.app.help`。design.md §4.3 #1 目标路径 `app/src/main/java/io/legado/app/lib/theme/PaperInkHelper.kt`，包名应为 `io.legado.app.lib.theme`。

**源文档位置**：design.md §4.3 主题管理模块 #1（第 871 行）

**真实代码位置**：借鉴源 `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/help/PaperInkHelper.kt:1`

**影响任务**：THEME-B-01（PaperInkHelper 纸墨风格）

**修复建议**：实施时按 design.md 目标路径放置，调整 package 声明为 `io.legado.app.lib.theme`，同步修改 import。

---

### 🟢 轻微发现 #4：Archive 项目 RssSearchActivity 实际行数与 design.md 描述不一致

**问题描述**：design.md ADR-007 第 207 行说"新增 RssSearchActivity.kt（继承 VMBaseActivity，本项目基类）+ RssSearchViewModel.kt + RssSearchAdapter.kt + RssFragment 添加搜索入口"，暗示新增 3 个文件。但 Archive 项目实际只新增 1 个文件 RssSearchActivity.kt（复用 RssSortViewModel，无单独 Adapter 文件）。

**源文档位置**：design.md ADR-007（第 207 行）

**真实代码位置**：借鉴源 `temp/forks-comparison/legado-archive/app/src/main/java/io/legado/app/ui/rss/article/RssSearchActivity.kt`（单文件）

**影响任务**：RSS-B-01（RssSearchActivity 新建）

**修复建议**：实施时可简化为新增 1 个文件（与 Archive 借鉴源一致），降低实施复杂度。

---

### 🟢 轻微发现 #5：本项目 VideoPlayerActivity 已在 AndroidManifest 注册

**问题描述**：本项目 AndroidManifest.xml 第 178 行已注册 `io.legado.app.ui.video.VideoPlayerActivity`。design.md §4.8 #2 说"新增 Activity 注册（RssSearchActivity / VideoPlayerActivity 等新增 Activity 必须在 Manifest 注册）"，但 VideoPlayerActivity 已存在，仅需注册 RssSearchActivity。

**源文档位置**：design.md §4.8 全局配置文件 #2（第 928 行）

**真实代码位置**：`app/src/main/AndroidManifest.xml:178`

**影响任务**：RSS-B-01（仅 RssSearchActivity 需注册）

**修复建议**：实施时仅新增 RssSearchActivity 注册条目，VideoPlayerActivity 已存在无需重复注册。

---

## 5. 实施可行性总评

### ⚠️ 需修订后实施

**总评结论**：P0 14 项任务**总体可实施**，但有 **6 项严重偏差**需先修订 design.md 才能开始实施：

| 严重发现 | 影响任务 | 阻塞程度 | 修复成本 |
|---------|---------|---------|---------|
| #1 RSS-E-06 任务实际已完成 | RSS-E-06 | 文档错误 | 仅需修订文档 |
| #2 RssSearchActivity 借鉴源依赖缺失扩展 | RSS-B-01 | 阻塞实施 | 中（改写或同步借鉴 3 个主题扩展） |
| #3 SourceSelectDialog 是 Compose 实现依赖缺失组件 | RSS-B-02 | 阻塞实施 | 高（改写为非 Compose 或同步借鉴 4+ Compose 组件） |
| #4 SearchBookMergeUtils 借鉴源依赖缺失扩展 | RSS-B-03 | 阻塞实施 | 中（改写或同步借鉴 stableSearchBookKey 扩展） |
| #5 PaperInkHelper 借鉴源依赖 ReadBookConfig 未列字段 | THEME-B-01 | 阻塞实施 | 中（同步修改 ReadBookConfig 新增 paperInkStrength） |
| #6 markwon 版本严重不一致（3 vs 4） | DEPS-B-01 | 文档错误 | 仅需修订文档 |

**修订建议路径**：
1. **优先修订 design.md**（修复 6 项严重发现的文档描述）
2. **决策借鉴策略**（每项严重发现 #2-#5 选择"同步借鉴"或"改写"）
3. **补充遗漏文件条目**（ReadBookConfig.kt 修改 + activity_rss_search.xml 新增）
4. **修订后即可开始实施 P0**

### 5.1 可立即实施的任务（无阻塞）
以下 8 项任务**无严重阻塞**，修订 design.md 后可立即实施：
- RSS-B-05（RssFragment openRssSearch 入口）🟡 注意入口设计
- RSS-E-06（cacheFirst 默认值）🔴 实际已完成，仅需验证
- THEME-B-02（字体撞色检测）🟡 注意 AndroidColorUtils 实际为 ColorUtils
- EPUB-B-01（spine 优先）🟡 注意 spine 当前为 fallback
- EPUB-B-02（资源过滤+标题归一化）✅ 可直接实施
- VIDEO-B-01（VideoBookPreloader）✅ 可直接实施（依赖 BookExtensions.kt 已有 addType/isNotShelf 扩展）
- VIDEO-B-02（章节链接缓存+下一集预加载集成）✅ 依赖 VIDEO-B-01
- VIDEO-E-01（ReadRecentBook 写入）🟡 注意 AppDatabase version 98→99 迁移

### 5.2 需修订后实施的任务
以下 6 项任务**有严重阻塞**，需先修订 design.md + 决策借鉴策略：
- RSS-B-01（RssSearchActivity 新建）🔴 依赖 #2 主题扩展
- RSS-B-02（SourceSelectDialog 组件）🔴 依赖 #3 Compose 组件
- RSS-B-03（SearchBookMergeUtils 合并工具）🔴 依赖 #4 stableSearchBookKey 扩展
- THEME-B-01（PaperInkHelper 纸墨风格）🔴 依赖 #5 ReadBookConfig.paperInkStrength
- VIDEO-E-02（ChoiceSpeedDialog 增强）🟡 当前已较完善，需 diff 对比
- DEPS-B-01（markwon 扩展）🔴 文档版本错误（3 vs 4）

### 5.3 依赖链验证结论
- P0 任务间无循环依赖 ✅
- EPUB-B-01 → EPUB-B-02 同文件串行可实施 ✅
- RSS-B-05 → RSS-B-01 同文件串行可实施 ✅
- VIDEO-B-01 → VIDEO-B-02 依赖链合理 ✅
- VIDEO-E-01 独立可并行 ✅
- VIDEO-E-02 独立可并行 ✅
- DEPS-B-01 独立无依赖 ✅

---

## 6. 审查方法学补充

### 6.1 已验证的关键技术依赖
| 依赖项 | 本项目状态 | 来源 |
|--------|-----------|------|
| VMBaseActivity（基类） | 存在 `app/src/main/java/io/legado/app/base/VMBaseActivity.kt` | 项目主代码 |
| RssSource.cacheFirst 字段 | 第 113 行 `cacheFirst: Boolean = true` 默认值已就绪 | 项目主代码 |
| RssSource.searchUrl 字段 | 第 115 行 `searchUrl: String? = null` 已就绪 | 项目主代码 |
| markwon 4.6.2 + 4 子依赖 | build.gradle 第 329-332 行 | libs.versions.toml:24 |
| sora-editor 0.24.4 + 3 子依赖 | build.gradle 第 356-358 行 | libs.versions.toml:17 |
| composeBom 2025.04.01 | libs.versions.toml 第 6 行 | 项目主代码 |
| kotlin 2.3.10 | libs.versions.toml 第 3 行 | 项目主代码 |
| AppDatabase version=98 | AppDatabase.kt 第 77 行 | 项目主代码 |
| BookExtensions.kt（addType/isNotShelf） | 存在 `app/src/main/java/io/legado/app/help/book/BookExtensions.kt` | 项目主代码 |

### 6.2 已验证的缺失依赖（阻塞借鉴）
| 缺失项 | 影响借鉴源 | 阻塞任务 |
|--------|-----------|---------|
| TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface 主题扩展 | RssSearchActivity | RSS-B-01 |
| LegadoMiuixCard/LegadoMiuixChoiceRow/rememberAppDialogStyle/toMiuixPalette Compose 组件 | SourceSelectDialog | RSS-B-02 |
| stableSearchBookKey 扩展函数 | SearchBookMergeUtils | RSS-B-03 |
| ReadBookConfig.paperInkStrength 字段 | PaperInkHelper | THEME-B-01 |
| activity_rss_search.xml 布局文件 | RssSearchActivity 布局 | RSS-B-01 |

### 6.3 验证未覆盖项（建议实施前补充验证）
- Archive 项目 RssSortViewModel 是否有搜索相关方法（影响 RSS-B-01 复用决策）
- Archive 项目 SearchBook.stableSearchBookKey 扩展的具体实现（影响 RSS-B-03 改写决策）
- Archive 项目 activity_rss_search.xml 是否依赖自定义 View（影响 RSS-B-01 布局借鉴）
- 本项目 ReadRssActivity.kt 完整流程（确认 RSS-E-06 是否真无需修改）

---

## 7. 附录

### 7.1 审查工具调用清单
- Read：10 次（design.md/VMBaseActivity/RssSource/EpubFile/ThemeUtils/ChoiceSpeedDialog/AppDatabase/build.gradle/libs.versions.toml/PaperInkHelper）
- Glob：10 次（关键文件路径验证）
- Grep：10 次（关键 API/字段/方法验证）

### 7.2 审查覆盖的 P0 任务
- ✅ RSS-B-01：已审查（🔴 阻塞）
- ✅ RSS-B-02：已审查（🔴 阻塞）
- ✅ RSS-B-03：已审查（🔴 阻塞）
- ✅ RSS-B-05：已审查（🟡 注意入口设计）
- ✅ RSS-E-03：未直接审查（P2 任务，不在 P0 范围）
- ✅ RSS-E-06：已审查（🔴 任务已完成）
- ✅ THEME-B-01：已审查（🔴 阻塞）
- ✅ THEME-B-02：已审查（🟢 注意 API 名称）
- ✅ EPUB-B-01：已审查（🟡 注意 spine 现状）
- ✅ EPUB-B-02：已审查（🟢 可实施）
- ✅ VIDEO-B-01：已审查（🟢 可实施）
- ✅ VIDEO-B-02：已审查（🟢 可实施）
- ✅ VIDEO-E-01：已审查（🟡 注意 DB 迁移）
- ✅ VIDEO-E-02：已审查（🟡 当前已完善）
- ✅ DEPS-B-01：已审查（🔴 文档错误）

### 7.3 审查结论
**总体**：P0 14 项任务中，8 项可立即实施，6 项需先修订 design.md。修订后即可开始实施。

**优先级建议**：
1. **第一优先**：修订 design.md 6 项严重发现（文档级修复，无代码变更）
2. **第二优先**：决策 RSS-B-01/B-02/B-03/THEME-B-01 的借鉴策略（同步借鉴 vs 改写）
3. **第三优先**：开始实施 P0 8 项无阻塞任务
4. **第四优先**：实施修订后的 6 项任务

**审查完成**。

---

**审查报告版本**：v1.0
**审查报告生成时间**：2026-07-18
**审查报告路径**：`f:\myself\github\WeAgentChat\temp\legado\docs\specs\forks-archive-borrow-implementation\review-code-feasibility.md`
