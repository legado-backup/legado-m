# 修复后依赖链与文件冲突复审报告

> **审查时间**：2026-07-18
> **审查范围**：基于前一轮 `review-dependency-conflict.md` 提出的 3 严重 + 3 中等 + 3 轻微问题，验证 design.md / tasks.md 修复是否生效，并检查是否引入新冲突
> **审查方法**：读取修复后的 design.md / tasks.md / spec.md，逐项对照前一轮问题，用 Grep 验证关键描述一致性
> **审查员**： forks-archive-borrow-implementation 修复后审查员

---

## 1. 审查概述

### 1.1 审查输入
- 前一轮审查报告：`review-dependency-conflict.md`（3 严重 + 3 中等 + 3 轻微）
- 修复后的 design.md（v2.2 修订版，含 ADR-002 / §4.1 / §4.2 / §4.8 / §5.1 / §6.1 修订）
- 修复后的 tasks.md（v5.2 文档修复版，含 1.4 / 1.5 / 1.14 修订）
- spec.md（验证三文档一致性）

### 1.2 审查重点
1. 3 严重问题修复有效性
2. 3 中等问题修复有效性
3. 修复是否引入新冲突（特别是 ADR-002 串行链与 tasks.md 1.4.2/1.14.2 修复后描述的兼容性）
4. design.md / tasks.md / spec.md 三文档一致性

---

## 2. 修复有效性验证（逐项）

### 2.1 🔴 严重 #1：VideoPlayerActivity.kt 被 3 任务修改，ADR-002 遗漏 VIDEO-E-02 同文件冲突

**修复证据**：
- design.md ADR-002 组D（line 110-112）明确：
  > "VIDEO-E-02 (ChoiceSpeedDialog 增强) [与 VIDEO-B-01/B-02 共用 VideoPlayerActivity.kt，必须串行执行：VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02]"
  > "注：VideoPlayerActivity.kt 被 3 个 P0 任务修改（VIDEO-B-01/B-02/E-02），必须严格串行执行"
- design.md §6.1（line 1038-1040）同步更新
- design.md ADR-008（line 228）追加："同文件串行约束：VideoPlayerActivity.kt 被 VIDEO-B-01/B-02/E-02 共用，必须严格串行执行"
- tasks.md 1.14（line 151）追加："⚠️ 同文件冲突提示：VIDEO-B-01/B-02/E-02 都修改 `VideoPlayerActivity.kt`，必须按顺序串行：VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02"

**验证结论**：✅ **严重 #1 已修复**——ADR-002 / §6.1 / ADR-008 / tasks.md 1.14 四处均明确串行约束

---

### 2.2 🔴 严重 #2：design.md §4.1 #9 RssWebActivity.kt 不存在

**修复证据**：
- design.md §4.1 #9（line 858）已修正：
  > "9 | `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt` | 修改 | WebView cacheFirst 默认 true（订阅文章加载入口，P0；cacheFirst 已在 ReadRssActivity.kt:421 实现，仅需真机验证行为） | RSS-E-06"
- tasks.md 1.5.2（line 68）已修正并标注：
  > "✅ 已完成（`app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt:421` 已实现 `cacheMode = if (s.cacheFirst) WebSettings.LOAD_CACHE_ELSE_NETWORK else WebSettings.LOAD_DEFAULT`；原 design.md §4.1 #9 标注的 `RssWebActivity.kt` 文件不存在，正确文件为 `ReadRssActivity.kt`）"
- design.md §4.1 #7（line 856）同步标注："数据层已完成（RssSource.kt:113 cacheFirst: Boolean = true 已是默认值），仅 WebView 层需验证"

**三文档一致性验证**：
- design.md §4.1 #9 = ReadRssActivity.kt ✅
- tasks.md 1.5.2 = ReadRssActivity.kt:421 ✅
- spec.md 未直接涉及此文件路径，无矛盾 ✅

**验证结论**：✅ **严重 #2 已修复**——文件路径已统一为 ReadRssActivity.kt，并标注数据层+WebView 层均已完成

---

### 2.3 🔴 严重 #3：R22 风险定义在 design.md 与 analysis-p0-strategy-risks.md 中矛盾

**修复证据**：
- design.md §5.1 #26（line 985）新增独立的 RssFragment.kt 冲突风险条目：
  > "26 | RSS-B-01 与 RSS-B-05 共用 RssFragment.kt 并发修改风险 | 文件冲突 | 高 | 严格执行 RSS-B-05 → RSS-B-01 串行（同文件串行规范）；组 A 内部明确串行链"
- design.md §5.1 #22（line 981）仍然保留原定义：
  > "22 | 单人 Agent 4 组并行退化为串行执行（主 Agent 单线程，4 组无法真正并行） | 高 | 高 | 接受串行现实，按组顺序执行（A→B→C→D）..."
- design.md ADR-002（line 90）仍引用"与 R22 缓解措施一致"
- design.md §6.1（line 1015）仍引用"与 R22 缓解措施一致"

**未完全修复点**：
- 前一轮建议"统一 R22 定义：以 analysis-p0-strategy-risks.md:356 为准（R22 = RssFragment.kt 文件冲突风险）"，但 design.md §5.1 #22 仍保留"单 Agent 串行"定义，未改为 R36/R37
- design.md §5.1 #26 新增了 RssFragment.kt 冲突风险（与 analysis-p0-strategy-risks.md R22 内容一致），但编号是 #26 而非 R22，导致 design.md 内部存在"#22 单 Agent 串行"和"#26 RssFragment.kt 冲突"两个不同的"R22 候选定义"
- ADR-002 / §6.1 中"与 R22 缓解措施一致"含义模糊：若指 #22 则为"接受串行现实"，若指 #26 则为"同文件串行规范"

**验证结论**：⚠️ **严重 #3 部分修复**——新增 #26 显式列出 RssFragment.kt 冲突风险（内容与 analysis-p0-strategy-risks.md 一致），但 R22 编号本身在 design.md 内部仍存在歧义（#22 vs #26），ADR-002 / §6.1 引用"R22 缓解措施"含义未明确化

---

### 2.4 🟡 中等 #1：tasks.md 1.14.2 描述与代码不符（Spinner vs ChoiceSpeedDialog）

**修复证据**：
- tasks.md 1.14.2（line 146）已明确：
  > "修改 ChoiceSpeedDialog 调用点（⚠️ 实际调用点是 `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt:600` 实例化 ChoiceSpeedDialog，**不是** `VideoPlayerActivity.kt:725-737`——VideoPlayerActivity.kt:725-737 用的是 Spinner 实现倍速，并非 ChoiceSpeedDialog）"

**验证结论**：✅ **中等 #1 已修复**——明确指出 ChoiceSpeedDialog 实际调用点是 VideoPlayer.kt:600，与 VideoPlayerActivity.kt:725-737 的 Spinner 实现区分清楚

---

### 2.5 🟡 中等 #2：VIDEO-B-01 集成位置描述不一致（SearchActivity.kt vs VideoPlayerActivity.kt）

**修复证据**：
- tasks.md 1.4.2（line 58）已明确：
  > "集成到 SearchActivity.kt（搜索结果页预加载视频书目录；⚠️ **不是 VideoPlayerActivity.kt**——VideoBookPreloader 在搜索结果页预加载，VideoPlayerActivity.kt 是视频播放页）"
- tasks.md 1.4 说明（line 64）追加：
  > "⚠️ 原 tasks.md 描述"集成到 VideoPlayerActivity.kt"是错误的（design.md §4.2 #2 错误标注），正确集成位置是 `app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt`"
- spec.md §4.1 REQ-P0-004 验收标准（line 225）一致：
  > "[ ] 搜索结果页预加载视频书目录"

**未完全修复点**：
- design.md §4.2 #2（line 865）**未同步修订**，仍标注：
  > "2 | `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | 修改 | 集成 VideoBookPreloader + chapterLinkCache + preloadNextEpisode | VIDEO-B-01(P0), VIDEO-B-02(P0)"
- design.md §4.6 #3（line 917）SearchActivity.kt 条目**未追加 VIDEO-B-01**：
  > "3 | `app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt` | 修改 | 集成 SearchBookMergeUtils + SearchBookPreviewOverlay | RSS-B-03, RSS-E-05"

**验证结论**：⚠️ **中等 #2 部分修复**——tasks.md 1.4.2 已修复并明确集成位置为 SearchActivity.kt，但 design.md §4.2 #2 仍错误标注 VIDEO-B-01(P0) 修改 VideoPlayerActivity.kt，design.md §4.6 SearchActivity.kt 条目未追加 VIDEO-B-01

---

### 2.6 🟡 中等 #3：design.md §4.8 错误把 VIDEO-B-01 列入 Manifest 修改

**修复证据**：
- design.md §4.8 #2（line 933）已修正：
  > "2 | `app/src/main/AndroidManifest.xml` | 修改 | 新增 Activity 注册（RssSearchActivity 新增 Activity 必须在 Manifest 注册；VideoPlayerActivity 已在 Manifest:178 注册无需重复；VideoBookPreloader 是单例类不需注册） | RSS-B-01"

**验证结论**：✅ **中等 #3 已修复**——明确删除 VIDEO-B-01 Manifest 修改条目，关联任务仅保留 RSS-B-01，并补充说明 VideoBookPreloader 不需注册

---

### 2.7 🟢 轻微问题（前一轮 3 项轻微未要求强制修复）

- 轻微 #1（strings.xml 串行管理）：design.md ADR-002 未追加专门规则，但 R24/R26 已涵盖，spec.md ADR-018 已规范 ⚠️ 未专门修复
- 轻微 #2（AppDatabase.kt 关注）：tasks.md 1.13.2 已标注 version=98 → 99 迁移，design.md §4.2 #5/#6 已列出 ReadRecentBook.kt/DAO ✅ 已修复
- 轻微 #3（proguard-rules.pro 子任务）：tasks.md 仅 1.1.7 列出 RssSearchActivity keep 规则，其他新增类任务未补充 proguard 子任务 ⚠️ 未完全修复

---

## 3. 新发现冲突（修复后引入）

### 3.1 ⚠️ 新冲突 #1：design.md ADR-002 串行链与 tasks.md 1.4.2/1.14.2 修复后描述矛盾

**问题描述**：
修复后 tasks.md 明确：
- 1.4.2：VIDEO-B-01 集成到 `SearchActivity.kt`（**不修改 VideoPlayerActivity.kt**）
- 1.14.2：VIDEO-E-02 调用点是 `VideoPlayer.kt:600`（**不修改 VideoPlayerActivity.kt**，仅修改 ChoiceSpeedDialog.kt）

但 design.md 仍按原描述强调三任务共用 VideoPlayerActivity.kt：
- ADR-002（line 108-112）："VideoPlayerActivity.kt 被 3 个 P0 任务修改（VIDEO-B-01/B-02/E-02），必须严格串行执行"
- §4.2 #2（line 865）："VideoPlayerActivity.kt 修改 | 集成 VideoBookPreloader + chapterLinkCache + preloadNextEpisode | VIDEO-B-01(P0), VIDEO-B-02(P0)"
- §6.1（line 1036-1040）："VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02 必须串行"
- ADR-008（line 228）："VideoPlayerActivity.kt 被 VIDEO-B-01/B-02/E-02 共用，必须严格串行执行"

**冲突类型**：修复后引入的逻辑矛盾——若按 tasks.md 1.4.2/1.14.2 修复后描述，则 VideoPlayerActivity.kt 实际只被 VIDEO-B-02 一个任务修改，无需三任务串行链；若按 design.md ADR-002 描述，则 tasks.md 1.4.2/1.14.2 修复方向错误（应回退）。

**影响**：实施时主 Agent 难以判断 VideoPlayerActivity.kt 实际修改者，可能误改文件或误加串行约束。

**修复建议**（二选一）：
- **方案 A（推荐）**：保持 tasks.md 1.4.2/1.14.2 修复后描述，同步修订 design.md：
  - §4.2 #2 删除 VIDEO-B-01(P0) 标注，仅保留 VIDEO-B-02(P0)
  - §4.6 SearchActivity.kt 条目追加 VIDEO-B-01
  - ADR-002 / §6.1 / ADR-008 修订为"VideoPlayerActivity.kt 仅被 VIDEO-B-02 修改，无同文件串行约束"
  - 串行链简化为"VIDEO-B-02 依赖 VIDEO-B-01 架构（功能依赖，非文件串行）"
- **方案 B**：保持 design.md ADR-002 串行链，回退 tasks.md 1.4.2/1.14.2 修复，明确 VIDEO-B-01 同时修改 SearchActivity.kt + VideoPlayerActivity.kt，VIDEO-E-02 同时修改 ChoiceSpeedDialog.kt + VideoPlayerActivity.kt（但需说明 VideoPlayerActivity.kt 中 VIDEO-B-01/E-02 的具体修改点）

### 3.2 ⚠️ 新冲突 #2：spec.md §10 文件路径映射表与 tasks.md 1.14.2 不一致

**问题描述**：
- spec.md §10（line 661）："VideoActivity.kt | `app/src/main/java/io/legado/app/ui/rss.video/VideoActivity.kt` | 本项目无此文件，实际为 `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt` | REQ-P0-014"
- spec.md §10（line 662）："ChoiceSpeedDialog.kt | `app/src/main/java/io/legado/app/ui/rss.video/` | `app/src/main/java/io/legado/app/help/gsyVideo/ChoiceSpeedDialog.kt` | REQ-P0-014"
- tasks.md 1.14.2：明确 ChoiceSpeedDialog 调用点是 `VideoPlayer.kt:600`（非 VideoPlayerActivity.kt）

spec.md §10 把 VideoPlayerActivity.kt 关联到 REQ-P0-014（VIDEO-E-02），但 tasks.md 1.14.2 修复后说 VIDEO-E-02 不修改 VideoPlayerActivity.kt。

**冲突类型**：spec.md §10 与 tasks.md 1.14.2 描述不一致

**修复建议**：
- spec.md §10 line 661 关联任务改为"REQ-P0-012 (VIDEO-B-02)"（VideoPlayerActivity.kt 实际由 VIDEO-B-02 修改）
- 或补充说明"VIDEO-E-02 调用 ChoiceSpeedDialog 的实际位置在 VideoPlayer.kt:600，非 VideoPlayerActivity.kt"

### 3.3 ⚠️ 新冲突 #3：design.md §4.6 SearchActivity.kt 未标注 VIDEO-B-01

**问题描述**：
- design.md §4.6 #3（line 917）："SearchActivity.kt 修改 | 集成 SearchBookMergeUtils + SearchBookPreviewOverlay | RSS-B-03, RSS-E-05"
- tasks.md 1.4.2 明确 VIDEO-B-01 也修改 SearchActivity.kt 集成 VideoBookPreloader

design.md §4.6 SearchActivity.kt 关联任务未包含 VIDEO-B-01，与 tasks.md 1.4.2 不一致。

**修复建议**：design.md §4.6 #3 关联任务改为"RSS-B-03, RSS-E-05, VIDEO-B-01"，用途追加"集成 VideoBookPreloader 视频书预加载"。

---

## 4. 遗漏修复问题

### 4.1 遗漏 #1：design.md §4.2 #2 未同步删除 VIDEO-B-01(P0) 标注

**问题**：tasks.md 1.4 已修复 VIDEO-B-01 集成位置为 SearchActivity.kt，但 design.md §4.2 #2 仍标注 VideoPlayerActivity.kt 关联 VIDEO-B-01(P0)。

**影响**：实施时可能误把 VideoBookPreloader 集成到 VideoPlayerActivity.kt（视频播放页），与"搜索结果页预加载"目标不符。

**修复建议**：design.md §4.2 #2 关联任务列删除"VIDEO-B-01(P0)"，仅保留"VIDEO-B-02(P0)"，用途描述删除"集成 VideoBookPreloader"，仅保留"chapterLinkCache + preloadNextEpisode"。

### 4.2 遗漏 #2：design.md ADR-002 串行链描述过度约束

**问题**：若按 tasks.md 1.4.2/1.14.2 修复后描述，VideoPlayerActivity.kt 实际只被 VIDEO-B-02 修改，但 design.md ADR-002 仍强调三任务串行链，导致过度约束并行性。

**影响**：实施时主 Agent 可能不必要地串行化组D 三个任务，降低执行效率。

**修复建议**：见 §3.1 方案 A。

### 4.3 遗漏 #3：proguard-rules.pro 子任务仅 RSS-B-01 补充，其他新增类未补充

**问题**：tasks.md 仅 1.1.7 列出 RssSearchActivity keep 规则，其他新增类任务（VIDEO-B-01 VideoBookPreloader / THEME-B-01 PaperInkHelper / RSS-B-02 SourceSelectDialog / RSS-B-03 SearchBookMergeUtils / VIDEO-E-01 ReadRecentBook）未补充 proguard-rules.pro 修改子任务。

**影响**：Release 包（minify=true）可能因混淆导致反射失败。

**修复建议**：每个新增类任务补充 proguard-rules.pro 修改子任务（如 1.4.5、1.3.5、1.7.5、1.8.5、1.13.5）。

---

## 5. 总评

### 5.1 修复统计

| 严重度 | 总数 | 已修复 | 部分修复 | 未修复 |
|--------|------|--------|---------|--------|
| 🔴 严重 | 3 | 2 | 1 | 0 |
| 🟡 中等 | 3 | 2 | 1 | 0 |
| 🟢 轻微 | 3 | 1 | 0 | 2 |
| **合计** | **9** | **5** | **2** | **2** |

### 5.2 总评结论

⚠️ **需补充修复**

### 5.3 待补充修复项清单

| # | 待修复项 | 优先级 | 涉及文件 |
|---|---------|--------|---------|
| 1 | 统一 R22 定义：design.md §5.1 #22 改为 R36（或合并入 #26），ADR-002 / §6.1 "与 R22 缓解措施一致"明确为"按 R26 RssFragment.kt 同文件串行原则处理" | 🔴 高 | design.md |
| 2 | design.md §4.2 #2 删除 VIDEO-B-01(P0) 标注，§4.6 SearchActivity.kt 条目追加 VIDEO-B-01 | 🔴 高 | design.md |
| 3 | design.md ADR-002 / §6.1 / ADR-008 同步修订：VideoPlayerActivity.kt 仅被 VIDEO-B-02 修改，简化串行链描述（见 §3.1 方案 A） | 🔴 高 | design.md |
| 4 | spec.md §10 line 661 VideoPlayerActivity.kt 关联任务改为 REQ-P0-012（VIDEO-B-02），或补充说明 VIDEO-E-02 实际调用点 | 🟡 中 | spec.md |
| 5 | tasks.md 为新增类任务补充 proguard-rules.pro 修改子任务（VIDEO-B-01/THEME-B-01/RSS-B-02/RSS-B-03/VIDEO-E-01） | 🟡 中 | tasks.md |
| 6 | design.md ADR-002 追加 strings.xml 串行管理规则（轻微 #1） | 🟢 低 | design.md |

### 5.4 修复有效性总评

前一轮 9 项问题中 5 项已完整修复（严重 #1/#2 + 中等 #1/#3 + 轻微 #2），2 项部分修复（严重 #3 + 中等 #2），2 项未修复（轻微 #1/#3）。修复引入 3 项新冲突，主要集中在 design.md 与 tasks.md 1.4.2/1.14.2 修复后描述的同步问题——tasks.md 已正确修复 VIDEO-B-01 集成位置和 VIDEO-E-02 调用点，但 design.md ADR-002 / §4.2 #2 / §4.6 / ADR-008 未同步修订，导致三任务串行链描述与实际修改文件矛盾。建议按本报告 §3.1 方案 A 同步修订 design.md，使 design.md 与 tasks.md 描述一致。

---

**审查报告完成**。修复总体方向正确，但 design.md 与 tasks.md 同步性不足，需补充 3 项高优先级修订（统一 R22 定义 + 同步 §4.2/§4.6 + 简化 ADR-002 串行链）才能完全消除实施时文件冲突风险。
