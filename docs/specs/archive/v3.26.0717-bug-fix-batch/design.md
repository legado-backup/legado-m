# Design - v3.26.0717 真机测试 Bug 批量修复

## Technical Approach

按问题分模块独立修复，每个修复点最小侵入：

1. **问题 1**：在 `RssSourceEditActivity.kt` 显示逻辑中，`parseConcurrency=0` 时改为显示系统配置值并标注"（继承全局）"
2. **问题 2**：为 `ColorPickerDialog` 包装暗色主题 Context，确保预设色块在暗色主题下正常显示
3. **问题 3**：在 `ruleMatchesOfChapter` 中对 `highlightRules` 创建本地副本（`toList()`）后再迭代
4. **问题 4**：在 `OtherConfigFragment.upPreferenceSummary` 中，rss/image concurrency 使用带值的字符串模板
5. **问题 5**：在 `BookSourceActivity.kt` 域名分组排序逻辑中加入 Weight 排序 + sortAscending 支持 + 异常 URL 过滤
6. **问题 6**：先评估当前布局差异，列清单后用户确认再修复

## Architecture Decisions

### AD-01: 替换规则崩溃修复方案 — 本地副本

- **Context**: `ReadBook.highlightRules` 是 `@Volatile List<HighlightRule>`，实际可能是 ArrayList
- **Concern**: 多线程并发：UI 线程迭代 `highlightRules.map {}` 时，另一线程调用 `loadHighlightRules` 重新赋值触发 ArrayList 内部修改
- **Decision**: 在 `ruleMatchesOfChapter` 入口处对 `highlightRules` 创建本地不可变副本 `val rulesSnapshot = highlightRules.toList()`，后续迭代使用副本
- **Goal**: 消除 ConcurrentModificationException，保留 @Volatile 可见性语义
- **Tradeoff**: 每次调用创建一次副本（List 浅拷贝），开销极小（典型 <10 元素）
- **Status**: Proposed

### AD-02: 高亮颜色选择器主题适配方案 — ContextWrapper

- **Context**: `ColorPickerDialog`（com.jaredrummler.android.colorpicker）内部使用固定主题渲染预设色块
- **Concern**: 暗色主题下预设色块背景与色块颜色混淆，全部显示为白色
- **Decision**: 创建 `ContextWrapper` 包装暗色主题样式，传给 `ColorPickerDialog.newBuilder()`，强制使用亮色主题渲染对话框
- **Goal**: 暗色主题下预设色块正常显示颜色
- **Tradeoff**: 颜色选择器对话框始终为亮色风格，与暗色主题视觉不完全一致
- **Status**: Proposed

### AD-03: 域名分组排序逻辑修复方案

- **Context**: 当前域名分组模式使用 `compareBy { "#"判断 }.thenBy { host }.thenByDescending { lastUpdateTime }`
- **Concern**: 
  - 同组内不按 Weight 排序，违背用户"智能排序按权重"预期
  - `sortAscending` 参数未传入分组排序逻辑，导致反序复选框无效
  - `getSourceHost` 对异常 URL（如 "http://example.com" 缺失路径）返回协议名
- **Decision**: 
  - 分组排序改为 `compareBy { host=="#" }.thenBy { host }.thenBy { sortAscending 取反 Weight比较 }`
  - `getSourceHost` 增加对 "http"/"https" 协议名的过滤，返回 "#"
  - 域名分组时也应用搜索过滤（已在 flow 层完成，需确认 data 来源）
- **Goal**: 域名分组按权重排序，反序生效，异常 URL 不显示为分组名
- **Tradeoff**: 改动域名分组排序逻辑，可能影响用户已有分组排序习惯
- **Status**: Proposed

### AD-04: 其他设置并发数显示方案

- **Context**: `upPreferenceSummary` 中 rss/image concurrency 使用固定字符串 `R.string.rss_parse_concurrency_summary`
- **Concern**: summary 不显示当前设置值，与 threadCount（显示具体数字）不一致
- **Decision**: 改用带占位符的字符串模板（如 `getString(R.string.rss_parse_concurrency_summary, value)`），与 threadCount 一致
- **Goal**: summary 显示当前设置数
- **Tradeoff**: 需修改 strings.xml 增加带占位符的字符串
- **Status**: Proposed

## Data Flow

### 替换规则崩溃修复数据流

```
[UI 线程] ContentTextView.setContent
  → [UI 线程] ContentTextView.upHighlight
  → [UI 线程] ReadBook.ruleMatchesOfChapter
  → [UI 线程] val rulesSnapshot = highlightRules.toList()  ← 创建本地副本
  → [UI 线程] rulesSnapshot.map { ... }  ← 迭代副本，不受其他线程影响

[其他线程] ReadBook.loadHighlightRules
  → [其他线程] highlightRules = HighlightRuleStore.loadEnabled(...)  ← 整体替换引用
  → [其他线程] highlightRulesVersion++
```

### 域名分组排序数据流

```
[Flow] appDb.bookSourceDao.flowAll
  → [Flow.map] hostMap.clear()
  → [Flow.map] if (groupSourcesByDomain) {
      data.sortedWith(
        compareBy<BookSourcePart> { getSourceHost(...) == "#" }
          .thenBy { getSourceHost(...) }
          .thenByDescending { it.weight }  ← 新增：按权重降序
          .let { if (sortAscending) it else it.reversed() }  ← 新增：支持反序
      )
    } else {
      sortSources(data)
    }
  → [Flow.collect] adapter.setItems(data, ...)
```

## File Changes

### 修改文件清单

| # | 文件路径 | 修改内容 | 关联问题 |
|---|---------|---------|---------|
| 1 | `app/src/main/java/io/legado/app/ui/rss.source.edit/RssSourceEditActivity.kt` | parseConcurrency 显示逻辑：0 时显示系统配置值 | 问题 1 |
| 2 | `app/src/main/java/io/legado/app/ui.highlight.edit/HighlightRuleEditDialog.kt` | ColorPickerDialog 主题适配 | 问题 2 |
| 3 | `app/src/main/java/io/legado/app/model/ReadBook.kt` | ruleMatchesOfChapter 本地副本 | 问题 3 |
| 4 | `app/src/main/java/io/legado/app/ui.config/OtherConfigFragment.kt` | rss/image concurrency summary 显示值 | 问题 4 |
| 5 | `app/src/main/res/values/strings.xml` | 新增带占位符的字符串模板 | 问题 4 |
| 6 | `app/src/main/java/io/legado/app/ui.book.source.manage/BookSourceActivity.kt` | 域名分组排序逻辑 + getSourceHost 异常 URL 处理 | 问题 5 |
| 7 | `app/src/main/java/io/legado/app/ui.book.source.manage/BookSourceViewModel.kt` | 评估是否需要调整 getBookSources | 问题 5 |
| 8 | `app/src/main/java/io/legado/app/ui.book.source.manage/BookSourceAdapterCompact.kt` | 评估布局差异（问题 6） | 问题 6 |
| 9 | `app/src/main/java/io/legado/app/ui.book.source.manage/BookSourceAdapterGrid.kt` | 评估布局差异（问题 6） | 问题 6 |
| 10 | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceAdapterCompact.kt` | 评估布局差异（问题 6） | 问题 6 |
| 11 | `app/src/main/java/io/legado/app/ui.rss.source.manage/RssSourceAdapterGrid.kt` | 评估布局差异（问题 6） | 问题 6 |
| 12 | `app/src/main/assets/updateLog.md` | 编译前更新日志 | 全部 |
| 13 | `docs/INDEX.md` | 更新 spec 状态 | 全部 |

### 问题 6 评估方法

1. 读取 BookSourceAdapterCompact/Grid 当前布局 XML
2. 读取书架 BooksAdapterListByGrid 布局 XML
3. 对比字段：书名、作者、最新章节、更新时间、分组、启用状态
4. 对比布局：间距、字号、图标位置
5. 列出差异清单，在 tasks.md 中作为独立 Phase 处理

## 测试方案

### 单元测试（不强制）

- `ruleMatchesOfChapter` 并发场景测试（可选，因涉及 Android 组件）

### 编译验证

- 修改完成后 `./gradlew assembleAppDebug` 编译通过

### 真机回归测试（Phase 11）

1. 订阅源编辑页打开，验证解析并发显示
2. 暗色主题下打开高亮规则编辑页，点击颜色按钮，验证预设色块
3. 阅读小说时启用替换规则，翻页 10 次，验证不崩溃
4. 进入其他设置，验证 rss/图片并发下方显示当前值
5. 书源管理页：搜索过滤 + 域名分组 + 按权重排序 + 反序，验证排序和反序生效
6. 书源/订阅源列表/紧凑/网格视图，验证布局效果

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| ColorPickerDialog 主题适配不彻底 | 预设色块仍异常 | 备选方案：自定义颜色选择器 |
| 域名分组排序逻辑改动影响用户习惯 | 用户已有分组顺序变化 | 设计文档明确改动范围，用户确认后再实施 |
| 问题 6 布局评估耗时较长 | 任务延期 | 评估阶段不修改代码，先列清单 |
