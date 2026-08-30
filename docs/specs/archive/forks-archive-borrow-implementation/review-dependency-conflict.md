# P0 14 项任务依赖链与文件冲突深度审查报告

> **审查时间**：2026-07-18
> **审查范围**：design.md ADR-002 分组方案（4 组 14 项 P0 任务）的文件依赖关系与并发冲突
> **审查方法**：读取 design.md + tasks.md，用 Grep/Glob/Read 验证关键文件路径与代码现状，构建文件→任务映射，识别冲突
> **审查员**：依赖链与文件冲突深度审查员

---

## 1. 审查概述

### 1.1 审查范围
- design.md §4 文件变更清单（45 项文件）
- design.md §6.1 实施顺序（4 组 14 项 P0 任务）
- design.md ADR-002 分组方案
- tasks.md P0 14 项任务的文件路径
- 实际源码文件现状（验证路径存在性、当前实现状态）

### 1.2 审查方法
1. 读取 design.md 与 tasks.md 全文
2. 提取 P0 14 项任务的文件路径清单
3. 构建"文件→任务"映射，识别被多任务修改的文件
4. 用 Grep/Glob/Read 验证关键文件路径存在性与代码现状
5. 对照 ADR-002 分组方案，验证同文件串行假设与跨组文件隔离假设
6. 检查 R22 风险定义一致性、strings.xml/Manifest/build.gradle 共享文件冲突

### 1.3 审查时间
2026-07-18 单次会话完成

---

## 2. 文件到任务映射表

### 2.1 被多个 P0 任务修改的源码文件

| 文件路径 | 修改任务 | 分组归属 | ADR-002 是否识别 |
|---------|---------|---------|----------------|
| `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | RSS-B-05（1.11.1 添加 openRssSearch）+ RSS-B-01（1.1.4 添加搜索入口） | 组A | ✅ 已识别为串行 |
| `app/src/main/java/io/legado/app/model/localBook/EpubFile.kt` | EPUB-B-01（1.9 spine 索引）+ EPUB-B-02（1.10 资源过滤+标题归一化） | 组C | ✅ 已识别为串行 |
| `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | VIDEO-B-01（集成 VideoBookPreloader）+ VIDEO-B-02（chapterLinkCache+preloadNextEpisode）+ VIDEO-E-02（1.14.2 集成倍速对话框） | 组D | ❌ **未识别 VIDEO-E-02 同文件冲突** |

### 2.2 被单个 P0 任务修改的源码文件（无冲突）

| 文件路径 | 修改任务 | 分组 |
|---------|---------|------|
| `app/src/main/java/io/legado/app/ui/rss/search/RssSearchActivity.kt`（新增） | RSS-B-01 | 组A |
| `app/src/main/java/io/legado/app/ui/rss/search/RssSearchViewModel.kt`（新增） | RSS-B-01 | 组A |
| `app/src/main/java/io/legado/app/ui/rss/search/RssSearchAdapter.kt`（新增） | RSS-B-01 | 组A |
| `app/src/main/java/io/legado/app/ui/rss/SourceSelectDialog.kt`（新增） | RSS-B-02 | 组A |
| `app/src/main/java/io/legado/app/utils/SearchBookMergeUtils.kt`（新增） | RSS-B-03 | 组A |
| `app/src/main/java/io/legado/app/lib/theme/PaperInkHelper.kt`（新增） | THEME-B-01 | 组B |
| `app/src/main/java/io/legado/app/lib/theme/ThemeUtils.kt` | THEME-B-02 | 组B |
| `app/src/main/java/io/legado/app/help/gsyVideo/VideoBookPreloader.kt`（新增） | VIDEO-B-01 | 组D |
| `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | VIDEO-E-02 | 组D |
| `app/src/main/java/io/legado/app/data/entities/ReadRecentBook.kt`（新增） | VIDEO-E-01 | 组D |
| `app/src/main/java/io/legado/app/data/dao/ReadRecentBookDao.kt`（新增） | VIDEO-E-01 | 组D |
| `app/src/main/java/io/legado/app/data/AppDatabase.kt` | VIDEO-E-01（version 98→99 + Migration + entities 加入 ReadRecentBook::class） | 组D |
| `app/build.gradle` | DEPS-B-01（markwon-strikethrough/tasklist/linkify 依赖） | 组D |

### 2.3 被多任务修改的共享资源文件

| 文件路径 | 修改任务 | 冲突风险 |
|---------|---------|---------|
| `app/src/main/AndroidManifest.xml` | 仅 RSS-B-01（1.1.5 注册 RssSearchActivity） | 🟢 无冲突 |
| `app/src/main/res/values/strings.xml` | RSS-B-01（1.1.6）+ THEME-B-01（1.3.3 配置开关）+ 其他新增界面任务 | 🟡 需主 Agent 串行管理 |
| `app/proguard-rules.pro` | RSS-B-01（1.1.7）+ 其他新增类任务（未列子任务） | 🟡 需补充子任务 |

---

## 3. 严重发现 🔴（实施时会文件冲突）

### 3.1 🔴 VideoPlayerActivity.kt 被 3 个 P0 任务修改但分组方案未识别 VIDEO-E-02 同文件冲突

**问题描述**：
design.md §4.2 #2 明确指出 `VideoPlayerActivity.kt` 被 VIDEO-B-01 与 VIDEO-B-02 修改（集成 VideoBookPreloader + chapterLinkCache + preloadNextEpisode）。tasks.md 1.14.2 明确指出 VIDEO-E-02 也要"在 `VideoPlayerActivity.kt` 中集成倍速对话框"。因此 VideoPlayerActivity.kt 实际被 3 个 P0 任务修改。

但 ADR-002 分组方案只识别了 "VIDEO-B-02 依赖 VIDEO-B-01 [同文件串行]"，对 VIDEO-E-02 的描述是"独立，可与 VIDEO-B-02 并行"，**这是错误的**！VIDEO-E-02 与 VIDEO-B-01/VIDEO-B-02 共用 VideoPlayerActivity.kt，必须串行执行。

**涉及任务**：
- VIDEO-B-01（1.4，集成 VideoBookPreloader 到 VideoPlayerActivity.kt）
- VIDEO-B-02（1.12，集成 chapterLinkCache + preloadNextEpisode 到 VideoPlayerActivity.kt）
- VIDEO-E-02（1.14，集成倍速对话框到 VideoPlayerActivity.kt）

**涉及文件**：`app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`

**冲突类型**：同文件并发修改冲突（违反并发文件修改规范"同一源码文件的所有 Edit 必须由主 Agent 串行执行"）

**代码现状验证**：
- Grep 验证 `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` 当前无 `VideoBookPreloader|chapterLinkCache|preloadNextEpisode` 引用（确认需新增）
- VideoPlayerActivity.kt:725-737 当前用 Spinner 实现倍速（不是 ChoiceSpeedDialog），VIDEO-E-02 集成倍速对话框需修改此处

**修复建议**：
1. 修订 ADR-002 组D 分组，明确 VideoPlayerActivity.kt 的串行链：
   - VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02（同文件严格串行）
2. 删除"VIDEO-E-02 独立，可与 VIDEO-B-02 并行"的错误描述
3. 在 R26 风险条目中追加 VideoPlayerActivity.kt 三任务串行约束

---

### 3.2 🔴 design.md §4.1 #9 文件路径错误：RssWebActivity.kt 不存在

**问题描述**：
design.md §4.1 #9 列出文件 `app/src/main/java/io/legado/app/ui/rss/RssWebActivity.kt`，标注用途为"WebView cacheFirst 默认 true（订阅文章加载入口）"。但 Grep/Glob 验证显示该文件根本不存在。

实际订阅文章加载入口是 `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt`，且 `ReadRssActivity.kt:421` 已实现 cacheFirst 逻辑：
```kotlin
cacheMode = if (s.cacheFirst) WebSettings.LOAD_CACHE_ELSE_NETWORK else WebSettings.LOAD_DEFAULT
```

**涉及任务**：RSS-E-06（1.5，cacheFirst 默认值）

**涉及文件**：
- 错误路径：`app/src/main/java/io/legado/app/ui/rss/RssWebActivity.kt`（不存在）
- 正确路径：`app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt`（已实现 cacheFirst）

**冲突类型**：design.md 文件路径错误，导致实施时找不到文件

**代码现状验证**：
- Glob `app/src/main/java/io/legado/app/ui/rss/RssWebActivity.kt` → 不存在
- Grep `cacheFirst` in `ReadRssActivity.kt:421` → 已实现
- RssSource.kt:113 `cacheFirst: Boolean = true` → 数据层已完成（tasks.md 1.5.1 已标记 ✅）

**修复建议**：
1. design.md §4.1 #9 路径修正为 `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt`
2. tasks.md 1.5.2 标注"WebView 层 cacheFirst 已在 ReadRssActivity.kt:421 实现，仅需真机验证"
3. RSS-E-06 整体可标记为已完成（数据层 + WebView 层均就绪）

---

### 3.3 🔴 R22 风险定义在 design.md 与 analysis-p0-strategy-risks.md 中不一致

**问题描述**：
ADR-002 多次引用"与 R22 缓解措施一致"，但 R22 的定义在两份文档中互相矛盾：

- `analysis-p0-strategy-risks.md:356`：R22 = "RSS-B-01 与 RSS-B-05 共用 RssFragment.kt 并发修改风险"（文件冲突类型）
- `design.md:998`：R22 = "单 Agent 串行，高影响高概率"（流程类型）
- `design.md §5.1 风险清单 #22`：R22 = "单人 Agent 4 组并行退化为串行执行（主 Agent 单线程，4 组无法真正并行）"

**涉及任务**：ADR-002 引用 R22 缓解措施的所有 P0 任务

**涉及文件**：
- `docs/specs/forks-archive-borrow-implementation/design.md`
- `docs/specs/forks-archive-borrow-implementation/analysis-p0-strategy-risks.md`

**冲突类型**：文档内部矛盾，导致 R22 缓解措施的实际含义不明确

**修复建议**：
1. 统一 R22 定义：建议以 `analysis-p0-strategy-risks.md:356` 为准（R22 = RssFragment.kt 文件冲突风险）
2. design.md §5.1 风险清单 #22 改为 R36 或 R37（避免与 R22 冲突）
3. design.md ADR-002 中"与 R22 缓解措施一致"明确为"按 RssFragment.kt 同文件串行原则处理"

---

## 4. 中等发现 🟡（隐藏依赖未识别）

### 4.1 🟡 VIDEO-E-02 tasks.md 1.14.2 描述与实际代码不符

**问题描述**：
tasks.md 1.14.2 描述"在 `VideoPlayerActivity.kt` 中集成倍速对话框"，但 VideoPlayerActivity.kt:725-737 当前使用 Spinner 实现倍速（1x/2x/3x/5x/10x），并非 ChoiceSpeedDialog。

实际 ChoiceSpeedDialog 在 `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt:600` 被实例化调用（非 VideoPlayerActivity 直接调用）。

**涉及任务**：VIDEO-E-02（1.14）

**涉及文件**：
- `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`（当前用 Spinner）
- `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt`（实际调用 ChoiceSpeedDialog）
- `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt`（增强目标）

**冲突类型**：tasks.md 描述与代码现状不符，实施时可能改错文件

**代码现状验证**：
- Grep `ChoiceSpeedDialog|setSpeed` in `VideoPlayerActivity.kt` → 仅 `playerView.setSpeed(speedValues[position], true)` 在 line 734（Spinner 触发）
- Grep `ChoiceSpeedDialog` → 实际在 `VideoPlayer.kt:600` 实例化

**修复建议**：
1. tasks.md 1.14.2 明确修改目标，二选一：
   - 方案 A：用 ChoiceSpeedDialog 替换 VideoPlayerActivity.kt 中 Spinner（修改 VideoPlayerActivity.kt + ChoiceSpeedDialog.kt）
   - 方案 B：仅增强 ChoiceSpeedDialog.kt 选项，VideoPlayer.kt 自动调用（不修改 VideoPlayerActivity.kt）
2. 推荐方案 B，避免 VideoPlayerActivity.kt 三任务串行压力

---

### 4.2 🟡 VIDEO-B-01 集成位置描述不一致

**问题描述**：
- tasks.md 1.4.2："集成到搜索结果页（搜索视频书时预加载目录）"
- design.md §4.2 #2："VideoPlayerActivity.kt 修改 | 集成 VideoBookPreloader + chapterLinkCache + preloadNextEpisode | VIDEO-B-01(P0), VIDEO-B-02(P0)"

搜索结果页应该是 `SearchActivity.kt`（已存在），不是 `VideoPlayerActivity.kt`（视频播放页）。VideoBookPreloader 的目的是"搜索结果页预加载视频书目录"，应在搜索结果页集成，而非视频播放页。

**涉及任务**：VIDEO-B-01（1.4）

**涉及文件**：
- `app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt`（搜索结果页，正确目标）
- `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`（design.md 错误描述）

**冲突类型**：tasks.md 与 design.md 描述不一致，实施时可能改错文件

**修复建议**：
1. 明确 VideoBookPreloader 在 SearchActivity.kt 集成（搜索结果页），不在 VideoPlayerActivity.kt
2. design.md §4.2 #2 删除"VIDEO-B-01(P0)"对 VideoPlayerActivity.kt 的标注
3. design.md §4.6 新增条目：SearchActivity.kt 修改 | 集成 VideoBookPreloader | VIDEO-B-01

---

### 4.3 🟡 design.md §4.8 AndroidManifest.xml 修改范围错误

**问题描述**：
design.md §4.8 #2 描述 "VIDEO-B-01" 也需要 Manifest 注册。但 Grep 验证 `app/src/main/AndroidManifest.xml` 显示 `VideoPlayerActivity` 已在 line 178 注册（已存在）。

VIDEO-B-01 新增的是 `VideoBookPreloader.kt`（普通单例类，非 Activity），不需要在 Manifest 注册。design.md §4.8 把 VIDEO-B-01 列入 Manifest 修改是错误的。

**涉及任务**：VIDEO-B-01

**涉及文件**：`app/src/main/AndroidManifest.xml`

**冲突类型**：design.md 修改范围错误，实施时可能误改 Manifest

**代码现状验证**：
- Grep `VideoPlayerActivity|SearchActivity|RssSearch` in `AndroidManifest.xml`：
  - line 178: `android:name="io.legado.app.ui.video.VideoPlayerActivity"`（已存在）
  - line 246: `android:name=".ui.book.search.SearchActivity"`（已存在）
  - RssSearchActivity 不存在（需 RSS-B-01 新增注册）

**修复建议**：
1. design.md §4.8 #2 删除 "VIDEO-B-01" 条目
2. 仅保留 RSS-B-01 注册 RssSearchActivity

---

## 5. 轻微发现 🟢（资源文件冲突）

### 5.1 🟢 strings.xml 多任务修改未在分组方案中明确串行管理

**问题描述**：
ADR-018 要求所有新增字符串入 strings.xml。R26 风险已识别"国际化字符串未列入 P0 子任务"。但 ADR-002 分组方案没明确 strings.xml 的串行管理规则。

P0 任务中需修改 strings.xml 的：
- RSS-B-01（1.1.6，搜索相关字符串）
- THEME-B-01（1.3.3，主题配置开关文案）
- 其他新增界面任务（VIDEO-E-02 倍速选项、RSS-B-02 源选择器等）

**涉及任务**：RSS-B-01, THEME-B-01, VIDEO-E-02, RSS-B-02 等

**涉及文件**：`app/src/main/res/values/strings.xml`

**冲突类型**：共享资源文件并发修改冲突

**修复建议**：
1. ADR-002 追加规则：strings.xml 由主 Agent 串行编辑，每组完成后批量更新
2. R26 缓解措施具体化：每组 P0 任务完成代码后统一追加 strings.xml 条目

---

### 5.2 🟢 AppDatabase.kt 仅 VIDEO-E-01 修改（无冲突但需关注）

**问题描述**：
AppDatabase.kt 当前 version=98，VIDEO-E-01 加 ReadRecentBook 表需要：
- 修改 `entities` 数组加入 `ReadRecentBook::class`
- 修改 `version = 99`
- 添加 Migration 98→99

P0 范围内仅 VIDEO-E-01 修改 AppDatabase.kt，无冲突。但 P1 阶段 RSS-B-04 pureSearch 字段也会修改 AppDatabase.kt，届时需协调。

**涉及任务**：VIDEO-E-01（1.13.2）

**涉及文件**：`app/src/main/java/io/legado/app/data/AppDatabase.kt`

**冲突类型**：无 P0 阶段冲突，P1 阶段需关注

**代码现状验证**：
- Read 当前 AppDatabase.kt line 76-86: `version = 98`, entities 数组未包含 ReadRecentBook
- Grep `ReadRecentBook` in AppDatabase.kt → 无匹配

**修复建议**：
1. P0 阶段 VIDEO-E-01 独占 AppDatabase.kt，无冲突
2. P1 阶段 RSS-B-04 实施时需重新评估 Migration 链（98→99→100）

---

### 5.3 🟢 proguard-rules.pro 多任务修改未明确

**问题描述**：
- RSS-B-01（1.1.7）明确修改 proguard-rules.pro 新增 RssSearchActivity keep 规则
- 其他新增类（VideoBookPreloader/PaperInkHelper/SearchBookMergeUtils/SourceSelectDialog/ReadRecentBook）也需要 keep 规则
- 但 tasks.md 没有为这些任务列出 proguard-rules.pro 修改子任务

**涉及任务**：VIDEO-B-01, THEME-B-01, RSS-B-02, RSS-B-03, VIDEO-E-01

**涉及文件**：`app/proguard-rules.pro`

**冲突类型**：共享资源文件并发修改冲突 + 子任务遗漏

**代码现状验证**：
- Grep `RssSearch|VideoBookPreloader|PaperInk|ThemeUtils|SearchBookMerge|SourceSelect|ReadRecent|ChoiceSpeed|VideoPlayerActivity` in `proguard-rules.pro` → 无匹配（确认需要新增）

**修复建议**：
1. 每个新增类任务补充 proguard-rules.pro 修改子任务
2. 由主 Agent 串行编辑 proguard-rules.pro，避免冲突

---

## 6. 跨组依赖验证（无隐藏依赖）

### 6.1 ✅ 组A RSS-B-01 RssSearchActivity 不依赖组B ThemeUtils 字体撞色检测

- RSS-B-01 是搜索 Activity，THEME-B-02 是主题工具类
- 两者功能独立，无代码依赖
- 跨组依赖确实不存在 ✅

### 6.2 ✅ 组D VIDEO-B-02 依赖组D VIDEO-B-01 实例（已识别）

- VIDEO-B-02 章节链接缓存依赖 VIDEO-B-01 的预加载架构
- ADR-002 已识别 "VIDEO-B-02 依赖 VIDEO-B-01" ✅

### 6.3 ✅ build.gradle 依赖无冲突

- DEPS-B-01 添加 markwon-strikethrough/tasklist/linkify
- VIDEO 任务不依赖 markwon 扩展
- VideoPlayerActivity.kt:100-103 已使用 markwon，DEPS-B-01 完成后可能需要扩展配置（在 ReadRssActivity 或订阅文章渲染入口配置 Markwon 实例）
- DEPS-B-01 主要修改 build.gradle，与 VIDEO 任务文件不同
- 暂无冲突 ✅

---

## 7. 分组方案总评

### 7.1 总评结论

⚠️ **需修订分组方案**

### 7.2 修订要点

| # | 修订内容 | 优先级 |
|---|---------|--------|
| 1 | 修订 ADR-002 组D 分组，明确 VideoPlayerActivity.kt 三任务串行链：VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02 | 🔴 严重 |
| 2 | 修订 design.md §4.1 #9，RssWebActivity.kt 路径修正为 ReadRssActivity.kt，并标注 RSS-E-06 WebView 层已完成 | 🔴 严重 |
| 3 | 统一 R22 定义（design.md vs analysis-p0-strategy-risks.md 矛盾） | 🔴 严重 |
| 4 | 修订 tasks.md 1.14.2，明确 VIDEO-E-02 修改目标（ChoiceSpeedDialog.kt vs VideoPlayerActivity.kt Spinner） | 🟡 中等 |
| 5 | 修订 design.md §4.2 #2，明确 VideoBookPreloader 在 SearchActivity.kt 集成（非 VideoPlayerActivity.kt） | 🟡 中等 |
| 6 | 修订 design.md §4.8 #2，删除 VIDEO-B-01 的 Manifest 修改条目 | 🟡 中等 |
| 7 | ADR-002 追加 strings.xml 串行管理规则 | 🟢 轻微 |
| 8 | 为新增类任务补充 proguard-rules.pro 修改子任务 | 🟢 轻微 |

### 7.3 修订后分组方案建议

```
组A（RSS 主线，5 项）
  ├─ RSS-B-05 → RSS-B-01 [RssFragment.kt 同文件串行]
  ├─ RSS-B-02 [独立]
  ├─ RSS-B-03 [独立]
  └─ RSS-E-06 [✅ 数据层+WebView 层均已完成，仅真机验证]

组B（THEME 视觉，2 项）
  ├─ THEME-B-01 [独立]
  └─ THEME-B-02 [独立]

组C（EPUB 加速，2 项）
  ├─ EPUB-B-01 → EPUB-B-02 [EpubFile.kt 同文件串行]

组D（VIDEO 增强，5 项，修订后）
  ├─ VIDEO-B-01 [集成到 SearchActivity.kt，不在 VideoPlayerActivity.kt]
  ├─ VIDEO-B-02 [依赖 VIDEO-B-01，VideoPlayerActivity.kt 串行 #1]
  ├─ VIDEO-E-02 [依赖 VIDEO-B-02，VideoPlayerActivity.kt 串行 #2]（修订：删除"独立"描述）
  ├─ VIDEO-E-01 [独立，修改 AppDatabase.kt，无冲突]
  └─ DEPS-B-01 [独立，修改 build.gradle]
```

### 7.4 共享文件串行管理规则（新增）

| 共享文件 | 修改任务 | 串行规则 |
|---------|---------|---------|
| `app/src/main/AndroidManifest.xml` | 仅 RSS-B-01 | 🟢 无冲突 |
| `app/src/main/res/values/strings.xml` | RSS-B-01 + THEME-B-01 + 其他 | 🟡 主 Agent 串行编辑，每组完成后批量更新 |
| `app/proguard-rules.pro` | RSS-B-01 + 其他新增类任务 | 🟡 主 Agent 串行编辑，补充遗漏子任务 |
| `app/build.gradle` | 仅 DEPS-B-01 | 🟢 无冲突 |
| `app/src/main/java/io/legado/app/data/AppDatabase.kt` | 仅 VIDEO-E-01 | 🟢 无冲突 |

---

## 8. 附录

### 8.1 验证证据清单

| 验证项 | 验证方法 | 验证结果 |
|--------|---------|---------|
| RssSearchActivity.kt 不存在 | Glob `app/src/main/java/io/legado/app/ui/rss/search/**` | No file found ✅ |
| ReadRecentBook.kt 不存在 | Glob `app/src/main/java/io/legado/app/data/entities/ReadRecentBook.kt` | No file found ✅ |
| VideoBookPreloader.kt 不存在 | Glob `app/src/main/java/io/legado/app/help/gsyVideo/VideoBookPreloader.kt` | No file found ✅ |
| RssWebActivity.kt 不存在 | Glob `app/src/main/java/io/legado/app/ui/rss/RssWebActivity.kt` | IO error ✅ |
| ReadRssActivity.kt cacheFirst 已实现 | Grep `cacheFirst` in ReadRssActivity.kt:421 | 已实现 ✅ |
| RssSource.kt:113 cacheFirst=true | Read RssSource.kt line 113 | `var cacheFirst: Boolean = true` ✅ |
| VideoPlayerActivity.kt 无 VideoBookPreloader 引用 | Grep `VideoBookPreloader\|chapterLinkCache\|preloadNextEpisode` | No matches found ✅ |
| VideoPlayerActivity.kt 用 Spinner 而非 ChoiceSpeedDialog | Grep `ChoiceSpeedDialog\|setSpeed` in VideoPlayerActivity.kt | 仅 `playerView.setSpeed` (Spinner 触发) ✅ |
| ChoiceSpeedDialog 实际调用点在 VideoPlayer.kt:600 | Grep `ChoiceSpeedDialog` | `VideoPlayer.kt:600: val choiceSpeedDialog = ChoiceSpeedDialog(mContext)` ✅ |
| AppDatabase.kt version=98 | Read AppDatabase.kt line 76-86 | `version = 98` ✅ |
| AppDatabase.kt 无 ReadRecentBook | Grep `ReadRecentBook` in AppDatabase.kt | No matches found ✅ |
| VideoPlayerActivity 已在 Manifest:178 | Grep `VideoPlayerActivity\|SearchActivity\|RssSearch` in AndroidManifest.xml | line 178 + line 246 ✅ |
| build.gradle markwon 在 line 329-332 | Grep `markwon\|sora` in build.gradle | line 329-332 + line 355 ✅ |
| RssFragment.kt 当前无 openRssSearch | Grep `RssSearchActivity\|openRssSearch\|startActivity` | 无 openRssSearch ✅ |
| proguard-rules.pro 无新增类 keep 规则 | Grep 新增类名 | No matches found ✅ |

### 8.2 R22 定义矛盾证据

| 文档 | 行号 | R22 定义 |
|------|------|---------|
| analysis-p0-strategy-risks.md | 356 | "RSS-B-01 与 RSS-B-05 共用 RssFragment.kt 并发修改风险"（文件冲突类型） |
| design.md | 998 | "单 Agent 串行，高影响高概率"（流程类型） |
| design.md | 976（§5.1 #22） | "单人 Agent 4 组并行退化为串行执行"（流程类型） |
| design.md | 1314 | "R22 单 Agent 串行"（流程类型） |

### 8.3 文件路径错误证据

| design.md 条目 | 错误路径 | 正确路径 | 验证 |
|---------------|---------|---------|------|
| §4.1 #9 | `app/src/main/java/io/legado/app/ui/rss/RssWebActivity.kt` | `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt` | Glob 验证不存在 + Grep 验证 ReadRssActivity.kt:421 已实现 cacheFirst |

---

**审查报告完成**。共发现 3 项严重问题（🔴）+ 3 项中等问题（🟡）+ 3 项轻微问题（🟢）+ 3 项跨组依赖验证通过（✅）。分组方案总体合理但需修订 8 处后才能避免实施时文件冲突。
