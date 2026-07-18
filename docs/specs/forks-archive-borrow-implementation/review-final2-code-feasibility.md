# 修复后代码可行性审查报告（第二轮修复验证）

> **审查时间**：2026-07-18
> **审查范围**：前一轮 6 严重 + 6 中等发现是否真正修复 + 是否引入新问题
> **审查方法**：Read/Grep 只读工具对照 spec.md / tasks.md / design.md / README.md 验证修复
> **审查员**：修复后代码可行性审查子代理
> **前序报告**：`review-code-feasibility.md`（v1.0，547 行）

---

## 1. 审查概述

### 1.1 审查目标
验证前一轮审查发现的 6 项严重问题 + 6 项中等问题是否真正修复，是否引入新问题，是否遗漏修复。

### 1.2 审查方法
- 读取 spec.md（666 行）/ tasks.md（482 行）/ design.md（约 1314 行）/ README.md（727 行）
- Grep 验证关键修复点：RssWebActivity→ReadRssActivity / markwon 4.6.2 / ReadBookConfig / SourceSelectDialog Compose 改写 / stableSearchBookKey / VideoPlayer.kt:600 / Migration_98_to_99 / RssSortViewModel
- Grep 验证遗漏点：TopBarSearchStyle / applyUiBodyTypefaceDeep / uiTypeface / activity_rss_search.xml
- 验证 §4 文件清单总数同步、P0 数量一致性

### 1.3 审查结论总览
| 维度 | 已修复 | 未修复 | 修复不完整 |
|------|--------|--------|-----------|
| 严重发现（6 项） | 5 | 1 | 0 |
| 中等发现（6 项） | 3 | 2 | 1 |
| 新发现问题 | - | 1 | - |
| **合计** | **8** | **3** | **1** |

**总评**：⚠️ 需补充修复（核心严重发现 #2 + 中等发现 #6 完全未修复；中等发现 #2 修复不完整；新发现 1 项跨文档不一致）

---

## 2. 修复有效性验证（逐项验证）

### 2.1 严重发现验证

#### 🔴 严重发现 #1：RSS-E-06 任务实际已完成 — ✅ 已完全修复

**验证证据**：
- `spec.md` REQ-P0-005（第 230-249 行）：实施状态标注"✅ 已完成（仅 WebView 层需真机验证）"，技术前提明确"`ReadRssActivity.kt:421` 已实现 cacheMode 逻辑"，文件名修正说明"原 design.md §4.1 #9 文件名 `RssWebActivity.kt` 错误，正确文件为 `ReadRssActivity.kt`"
- `tasks.md` 1.5（第 66-72 行）：1.5.1 和 1.5.2 标记 `[x]` 已完成，1.5.3 真机验证保留 `[ ]`
- `design.md` §4.1 #9（第 858 行）：文件路径已修正为 `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt`，操作描述标注"cacheFirst 已在 ReadRssActivity.kt:421 实现，仅需真机验证行为"
- `README.md` §9.4.5（第 462-463 行）：新增"已完成任务标注"章节，明确"RSS-E-06 ✅ 已完成（仅 WebView 层需真机验证）"+ 文件名修正记录

**结论**：✅ 4 个文档全部同步修复，无遗漏。

---

#### 🔴 严重发现 #2：RssSearchActivity 借鉴源依赖本项目不存在的主题扩展 — ❌ 完全未修复

**验证证据**：
- Grep `TopBarSearchStyle|applyUiBodyTypefaceDeep|uiTypeface` 全项目（除前一轮审查报告自身）：
  - `spec.md` REQ-P0-001（第 145-164 行）：仅标注"本项目基类为 VMBaseActivity，无 BaseSearchActivity"，**未提及 3 个主题扩展依赖**
  - `design.md` §4.1 #1（第 850 行）：仅标注"RSS 搜索 Activity（继承 VMBaseActivity 本项目基类，激活 searchUrl 字段，**ui/rss/search/ 为新建子目录**）"，**未提及主题扩展依赖**
  - `design.md` ADR-007（第 209 行）：仍写"+ RssSearchViewModel.kt + RssSearchAdapter.kt"，**未提及主题扩展依赖**
  - `tasks.md` 1.1（第 21-33 行）：仅说明基类和子目录，**未提及主题扩展依赖**
  - `README.md`：未提及主题扩展依赖

**结论**：❌ **完全未修复**。前一轮审查明确建议"同步补充 design.md §4.1 #1 注明借鉴时需同步处理 3 个主题扩展依赖"，但本轮 4 个文档均未补充。RSS-B-01 实施时若直接借鉴 Archive 项目 RssSearchActivity.kt，将因 `import io.legado.app.lib.theme.TopBarSearchStyle` 等 3 个 import 找不到符号而编译失败。

---

#### 🔴 严重发现 #3：SourceSelectDialog 借鉴源是 Compose 实现依赖本项目不存在的 Compose 组件 — ✅ 已修复

**验证证据**：
- `spec.md` REQ-P0-007（第 268-287 行）：技术前提明确"⚠️ Archive 项目 `SourceSelectDialog.kt` 是 **Compose 实现**，依赖 LegadoMiuixCard/LegadoMiuixChoiceRow/rememberAppDialogStyle/toMiuixPalette 等 Compose 组件（本项目均无）"，技术要点明确"新增 SourceSelectDialog.kt（BottomSheetDialog + RecyclerView，**非 Compose 实现**）"
- `design.md` §4.1 #5（第 854 行）：标注"统一源选择 Dialog（BottomSheetDialog，book/rss 源统一选择）"，隐含标注改写方案
- `tasks.md` 1.7：未明确标注，但 spec.md 已充分标注

**结论**：✅ 已修复（spec.md 标注充分，design.md 隐含标注 BottomSheetDialog 而非 Compose）。

---

#### 🔴 严重发现 #4：SearchBookMergeUtils 借鉴源依赖本项目不存在的 stableSearchBookKey 扩展函数 — ✅ 已修复

**验证证据**：
- `spec.md` REQ-P0-008（第 288-308 行）：技术前提明确"⚠️ Archive 项目 `SearchBookMergeUtils.kt` 调用 `book.stableSearchBookKey()` 扩展函数（5 处调用）。本项目 Grep 全项目搜索 `fun.*stableSearchBookKey` 无匹配，**本项目无此扩展函数**"，技术要点明确"按书名+作者去重（**改写实现**，不依赖 stableSearchBookKey 扩展）"，验收标准明确"去重逻辑正确（书名+作者，不依赖 stableSearchBookKey）"
- `design.md` §4.1 #6（第 855 行）：标注"搜索结果合并工具（按书名+作者去重，保留多源信息）"，隐含标注改写方案

**结论**：✅ 已修复（spec.md 标注充分）。

---

#### 🔴 严重发现 #5：PaperInkHelper 借鉴源依赖 ReadBookConfig.paperInkStrength 字段（设计文档遗漏 ReadBookConfig 修改条目） — ✅ 已完全修复

**验证证据**：
- `spec.md` REQ-P0-003（第 186-211 行）：实施成本标注"中（需同步修改 ReadBookConfig 新增 paperInkStrength 字段，成本上调）"，技术前提明确"⚠️ Archive 项目 `PaperInkHelper.kt` 依赖 `ReadBookConfig.paperInkStrength` 字段（第 5/10/47 行）。本项目 `app/src/main/java/io/legado/app/help/config/ReadBookConfig.kt` Grep `paperInkStrength|paperInk` 无匹配，**本项目无此字段**"，验收标准明确"修改 `ReadBookConfig.kt` 新增 paperInkStrength 字段 + 配置实体 + JSON 序列化"
- `design.md` §4.3 #1（第 875 行）：标注"借鉴源依赖 ReadBookConfig.paperInkStrength 字段，本项目无此字段，必须同步修改 ReadBookConfig.kt 新增 paperInkStrength 字段 + 配置实体字段 + JSON 序列化 + 条件回退"
- `design.md` §4.3 #12（第 886 行）：✅ **新增** ReadBookConfig.kt 修改条目"新增 paperInkStrength 字段（Int 类型，coerceIn(0, 100) 限定范围）+ 配置实体字段 + JSON 序列化 + 条件回退逻辑；PaperInkHelper.kt 编译依赖此字段，必须同步修改"
- `design.md` §4.9 文件变更统计（第 942 行）：主题管理模块从 11 文件升至 12 文件，新增 9 + 修改 3 = 12 ✅
- `design.md` §4.9 统计说明（第 950 行）：✅ 明确"v2.3 修订：主题管理模块新增 ReadBookConfig.kt 修改条目（PaperInkHelper 编译依赖 paperInkStrength 字段）"
- `README.md` §15.3 A4（第 680 行）：✅ 明确"design.md §4.3 补充 ReadBookConfig.kt 修改条目"

**结论**：✅ 已完全修复（spec/design/README 全部同步，文件清单总数已同步至 12）。

---

#### 🔴 严重发现 #6：markwon 版本严重不一致（设计文档错误描述为 markwon 3，实际为 markwon 4.6.2） — ✅ 已完全修复

**验证证据**：
- `spec.md` REQ-P0-002（第 165-184 行）：✅ 标题改为"markwon 4.6.2 扩展"，技术前提明确"⚠️ markwon 核心已实现（`app/build.gradle:329-332` 已引入 markwon core+image-glide+tables+html），本任务仅需补充扩展依赖并验证功能完整性"
- `tasks.md` 1.2（第 35-45 行）：✅ 标题"markwon 4.6.2 扩展"，1.2.0 标记 `[x]` 已实现，1.2.6 明确"验证 3.x 与 4.x API 兼容性（现有 4 个依赖 core/image-glide/tables/html 与新扩展 tasklist/strikethrough/linkify 的 API 兼容性）"，说明部分明确"⚠️ **markwon 3.x 与 4.x API 不兼容**，借鉴 Archive 项目时（如 Archive 用 markwon 3）需进行 API 适配"
- `design.md` §4.7 #1（第 925 行）：✅ "markwon 4.6.2 扩展依赖（补充 ext.tasklist/ext.strikethrough 等子依赖）"
- `design.md` ADR-006（第 194 行）：✅ "sora-editor + markwon 已引入（非新增依赖，`app/build.gradle:329-332, 356-358` 已存在），DEPS-B-01（markwon 4.6.2 扩展）与 DEPS-B-02（sora-editor）仅需验证版本兼容性 + 补充缺失子依赖"
- `design.md` 风险 #15（第 974 行）：✅ "markwon 兼容性风险（DEPS-B-01 markwon 4.6.2 扩展与现有渲染链兼容性未评估；注意 4.x 与 3.x API 不兼容）"
- `README.md` §3.2 P0 列表（第 110 行）：✅ "markwon 4.6.2 扩展"

**结论**：✅ 已完全修复（4 个文档全部同步至 4.6.2，并明确 3.x 与 4.x API 不兼容警示）。

---

### 2.2 中等发现验证

#### 🟡 中等发现 #1：借鉴源路径与目标路径多处不一致 — ✅ 已修复

**验证证据**：
- `spec.md` §E 文件路径对照表（第 653-666 行）：✅ 新增 6 行路径对照表（EpubFile.kt / RssFragment.kt / VideoActivity.kt / ChoiceSpeedDialog.kt / Exo2MediaPlayer.kt / ThemeColorUtils.kt）

**结论**：✅ 已修复。

---

#### 🟡 中等发现 #2：RssSearchActivity 实际复用 RssSortViewModel（设计文档新增 RssSearchViewModel 错误） — ⚠️ 修复不完整

**验证证据**：
- `tasks.md` 1.1.2（第 23 行）：✅ 明确"复用现有 RssSortViewModel（⚠️ **不新增 RssSearchViewModel**——Archive 项目 RssSearchActivity.kt:20 实际 `class RssSearchActivity : VMBaseActivity<ActivityRssSearchBinding, RssSortViewModel>()` 复用现有 RssSortViewModel，与 Archive 借鉴源一致，降低实施风险）"
- `tasks.md` 1.1 说明（第 33 行）：✅ "⚠️ ViewModel 复用现有 RssSortViewModel，无需新建"
- `design.md` §4.1 #2（第 851 行）：❌ **未修改**，仍写"RssSearchViewModel.kt | 新增/修改 | RSS 搜索 ViewModel（调度多源并发搜索）+ pureSearch 参数支持（P1）"
- `design.md` ADR-007 Decision（第 209 行）：❌ **未修改**，仍写"+ RssSearchViewModel.kt + RssSearchAdapter.kt"
- `design.md` 数据流图说明（第 645 行）：❌ **未修改**，仍写"UI 轨：新增 RssSearchActivity + RssSearchViewModel + RssSearchAdapter"
- `design.md` §11.1 单元测试覆盖矩阵（第 1150 行）：❌ **未修改**，仍写"RSS 模块 | RssSearchViewModel（搜索/分页/异常）、SearchBookMergeUtils（去重/多源合并）"
- `spec.md` REQ-P0-001（第 145-164 行）：未明确说明 ViewModel 复用方案

**结论**：⚠️ **修复不完整**。tasks.md 已修复，但 design.md 4 处未同步（§4.1 #2 / ADR-007 / 第 645 行 / 第 1150 行），存在跨文档不一致。实施者参考 design.md 时可能错误地新增 RssSearchViewModel.kt。

---

#### 🟡 中等发现 #3：RssFragment.kt 已有 searchView 但用途不同，新增 openRssSearch 入口需明确入口设计 — ✅ 已修复

**验证证据**：
- `spec.md` REQ-P0-011（第 340-353 行）：✅ 已标注"RssFragment 添加 openRssSearch 方法"，与 REQ-P0-001 入口配套
- `tasks.md` 1.11（第 119-124 行）：✅ 已标注入口配套，与 RSS-B-01 依赖关系

**结论**：✅ 已修复（虽未明确说明入口设计细节，但入口配套关系明确）。

---

#### 🟡 中等发现 #4：AppDatabase version=98，VIDEO-E-01 需新增 Migration_98_to_99 — ✅ 已完全修复

**验证证据**：
- `tasks.md` 1.13.2（第 136 行）：✅ 明确"⚠️ **AppDatabase.kt 当前 version=98**，需新增 `Migration_98_to_99` 手写 Migration + entities 数组加入 `ReadRecentBook::class` + version 升级 98→99；迁移范围需包含 pureSearch 字段，与 design.md ADR-013 一致；schema 导出 + 真机验证覆盖安装流程"
- `design.md` ADR-013（第 325 行）：✅ "VIDEO-E-01 ReadRecentBook 表创建：`CREATE TABLE IF NOT EXISTS readRecentBook (...)`，新建实体 + DAO"
- `design.md` ADR-002 组D（第 109 行）：✅ 标注"VIDEO-E-01 (ReadRecentBook 写入，v5.1 调整后已升级 P0) [含 DB Migration_98_to_99，实施复杂度高于其他 P0 任务，建议拆分为子任务串行，需遵循 ADR-013 迁移流程]"
- `spec.md` REQ-P0-013（第 370-388 行）：✅ 已标注"需新增 ReadRecentBook 实体+DAO+Migration（本项目当前无此表，仅 fork 仓库有）"

**结论**：✅ 已完全修复（4 个文档全部标注 Migration_98_to_99 + version 98→99）。

---

#### 🟡 中等发现 #5：VIDEO-E-02 ChoiceSpeedDialog 当前已较完善，需对比 Archive 看是否有进一步借鉴点 — ✅ 已修复

**验证证据**：
- `tasks.md` 1.14.2（第 146 行）：✅ 明确"修改 ChoiceSpeedDialog 调用点（⚠️ 实际调用点是 `app/src/main/java/io/legado/app/help/gsyVideo/VideoPlayer.kt:600` 实例化 ChoiceSpeedDialog，**不是** `VideoPlayerActivity.kt:725-737`——VideoPlayerActivity.kt:725-737 用的是 Spinner 实现倍速，并非 ChoiceSpeedDialog）"
- `design.md` ADR-002 组D（第 110 行）：✅ 标注"VIDEO-E-02 与 VIDEO-B-01/B-02 共用 VideoPlayerActivity.kt，必须串行执行：VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02"
- `design.md` ADR-008（第 228 行）：✅ 标注"同文件串行约束：VideoPlayerActivity.kt 被 VIDEO-B-01/B-02/E-02 共用，必须严格串行执行"

**结论**：✅ 已修复（虽未明确说"ChoiceSpeedDialog 已较完善"，但修正了调用点 + 串行约束清晰）。

---

#### 🟡 中等发现 #6：RssSearchActivity 缺少配套布局文件 — ❌ 完全未修复

**验证证据**：
- Grep `activity_rss_search` 全项目（除前一轮审查报告自身）：
  - `design.md` §4.8（第 928-934 行）：❌ 仍然只列 3 个全局配置文件（strings.xml / AndroidManifest.xml / proguard-rules.pro），**未列 activity_rss_search.xml 新增条目**
  - `design.md` §4.9 文件变更统计：未列入布局文件
  - `spec.md` / `tasks.md` / `README.md`：均未提及 activity_rss_search.xml

**结论**：❌ **完全未修复**。前一轮审查明确建议"补充 design.md §4.8 新增条目：`app/src/main/res/layout/activity_rss_search.xml` 新增（布局文件）"，但本轮未补充。RSS-B-01 实施时若遗漏布局文件，将导致 `ActivityRssSearchBinding::inflate` 找不到对应布局而编译失败。

---

## 3. 新发现问题（修复引入的新问题）

### 🟡 新发现 #1：design.md 多处 RssSearchViewModel 与 tasks.md 1.1.2 决策矛盾

**问题描述**：tasks.md 1.1.2 明确"复用现有 RssSortViewModel，⚠️ **不新增 RssSearchViewModel**"，但 design.md 4 处仍写新增 RssSearchViewModel.kt：
- design.md §4.1 #2（第 851 行）：操作列写"新增/修改"，用途列写"RSS 搜索 ViewModel"
- design.md ADR-007 Decision（第 209 行）：UI 轨描述"+ RssSearchViewModel.kt + RssSearchAdapter.kt"
- design.md §6 数据流图说明（第 645 行）："UI 轨：新增 RssSearchActivity + RssSearchViewModel + RssSearchAdapter"
- design.md §11.1 单元测试覆盖矩阵（第 1150 行）："RSS 模块 | RssSearchViewModel（搜索/分页/异常）"

**影响**：跨文档不一致。实施者参考 design.md 时可能错误地新增 RssSearchViewModel.kt，违反 tasks.md 1.1.2 决策。

**修复成本**：低（仅 design.md 4 处文字修订）

**建议**：
1. design.md §4.1 #2：操作改为"复用（不新增）"，用途改为"复用现有 RssSortViewModel 调度多源并发搜索 + pureSearch 参数支持（P1）"
2. design.md ADR-007 Decision：删除"+ RssSearchViewModel.kt"，添加"（复用现有 RssSortViewModel，与 Archive 借鉴源一致）"
3. design.md 第 645 行：改为"UI 轨：新增 RssSearchActivity + RssSearchAdapter（复用现有 RssSortViewModel）"
4. design.md §11.1 单元测试覆盖矩阵：改为"RSS 模块 | RssSortViewModel（搜索/分页/异常，复用）、SearchBookMergeUtils（去重/多源合并）"

---

## 4. 遗漏修复问题

### 🔴 遗漏 #1：严重发现 #2 完全未修复（RssSearchActivity 主题扩展依赖）

**问题描述**：前一轮审查明确发现 Archive 项目 `RssSearchActivity.kt` 依赖本项目不存在的 3 个主题扩展：
- 第 13 行：`import io.legado.app.lib.theme.TopBarSearchStyle`
- 第 14 行：`import io.legado.app.lib.theme.applyUiBodyTypefaceDeep`
- 第 15 行：`import io.legado.app.lib.theme.uiTypeface`

前一轮审查明确建议"同步补充 design.md §4.1 #1 注明借鉴时需同步处理 3 个主题扩展依赖"，但本轮修复 4 个文档均未补充。

**影响**：RSS-B-01 实施时若直接借鉴 Archive 项目 RssSearchActivity.kt，将因 3 个 import 找不到符号而编译失败。

**建议**：
1. design.md §4.1 #1：补充"⚠️ 借鉴源依赖本项目不存在的 3 个主题扩展（TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface），实施时需改写不依赖这些扩展，使用本项目现有主题机制"
2. spec.md REQ-P0-001：技术前提补充"⚠️ 借鉴源依赖 3 个主题扩展（本项目无），实施时需改写"
3. tasks.md 1.1：补充子任务"1.1.0 改写 RssSearchActivity 不依赖 TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface 3 个主题扩展"

---

### 🔴 遗漏 #2：中等发现 #6 完全未修复（activity_rss_search.xml 布局文件缺失）

**问题描述**：前一轮审查明确发现 design.md §4.8 全局配置文件未列出 `activity_rss_search.xml` 新增条目，本轮修复完全未补充。

**影响**：RSS-B-01 实施时若遗漏布局文件，将导致 `ActivityRssSearchBinding::inflate` 找不到对应布局而编译失败。

**建议**：
1. design.md §4.8：新增条目"`app/src/main/res/layout/activity_rss_search.xml` | 新增 | RssSearchActivity 布局文件（参考 Archive 项目同名布局，需检查是否依赖本项目不存在的自定义 View）| RSS-B-01"
2. design.md §4.9 文件变更统计：全局配置文件从 3 升至 4（新增 1 + 修改 3 = 4），总计 31 + 15 = 46 → 32 + 15 = 47

---

### ⚠️ 遗漏 #3：中等发现 #2 修复不完整（design.md RssSearchViewModel 未同步）

详见 §3 新发现 #1，需补充修复 design.md 4 处。

---

## 5. 总评

### 5.1 修复有效性总评

| 维度 | 总数 | 已修复 | 未修复 | 修复不完整 | 修复率 |
|------|------|--------|--------|-----------|--------|
| 严重发现 | 6 | 5 | 1 | 0 | 83.3% |
| 中等发现 | 6 | 3 | 2 | 1 | 50.0% |
| 新发现问题 | 1 | - | 1 | - | - |
| **合计** | **13** | **8** | **4** | **1** | **61.5%** |

### 5.2 总评结论

**⚠️ 需补充修复**

修复有效性整体良好（严重发现 83.3% 修复率），核心修复点（RSS-E-06 已完成 / markwon 4.6.2 / ReadBookConfig.paperInkStrength / SourceSelectDialog Compose 改写 / SearchBookMergeUtils stableSearchBookKey 改写 / Migration_98_to_99）均已正确修复，文件清单总数同步正确（§4.3 12 个文件 / §4.9 合计 46 个文件 / P0=14 保持不变 / markwon 4.6.2 任务无不兼容描述）。

但仍有 **4 项问题需补充修复**：

#### 必须修复（阻塞实施）：
1. **🔴 遗漏 #1**：严重发现 #2 RssSearchActivity 主题扩展依赖（TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface）— 4 个文档均未标注，RSS-B-01 实施会编译失败
2. **🔴 遗漏 #2**：中等发现 #6 activity_rss_search.xml 布局文件缺失 — design.md §4.8 未补充，RSS-B-01 实施会编译失败

#### 建议修复（避免跨文档不一致）：
3. **⚠️ 遗漏 #3 / 新发现 #1**：design.md 4 处 RssSearchViewModel 未同步修改为 RssSortViewModel — tasks.md 1.1.2 已修复但 design.md 4 处未同步

### 5.3 修复路径建议

1. **第一优先**：补充严重发现 #2 主题扩展依赖标注（design.md §4.1 #1 + spec.md REQ-P0-001 + tasks.md 1.1）
2. **第二优先**：补充中等发现 #6 activity_rss_search.xml 布局文件条目（design.md §4.8 + §4.9 统计）
3. **第三优先**：同步 design.md 4 处 RssSearchViewModel → RssSortViewModel（§4.1 #2 / ADR-007 / §6 / §11.1）
4. **修复后即可进入实施 P0**

### 5.4 实施前必须确认的事实

| # | 事实 | 影响 |
|---|------|------|
| 1 | Archive 项目 RssSearchActivity.kt 依赖 3 个主题扩展（本项目无） | RSS-B-01 需改写 |
| 2 | Archive 项目 RssSearchActivity.kt 第 22 行使用 ActivityRssSearchBinding | RSS-B-01 需新增 activity_rss_search.xml |
| 3 | Archive 项目 RssSearchActivity.kt 复用 RssSortViewModel（不新增 RssSearchViewModel） | RSS-B-01 ViewModel 复用决策 |
| 4 | ReadRssActivity.kt:421 已实现 cacheFirst 逻辑 | RSS-E-06 仅需真机验证 |
| 5 | markwon 4.6.2 已引入 4 个子依赖，仅需补充 3 个扩展 | DEPS-B-01 补充 ext.tasklist/strikethrough/linkify |
| 6 | AppDatabase version=98，需 Migration_98_to_99 | VIDEO-E-01 数据库迁移 |
| 7 | ChoiceSpeedDialog 调用点是 VideoPlayer.kt:600（非 VideoPlayerActivity.kt:725-737） | VIDEO-E-02 修改目标 |
| 8 | PaperInkHelper 编译依赖 ReadBookConfig.paperInkStrength（本项目无） | THEME-B-01 必须同步修改 ReadBookConfig |

---

## 6. 审查工具调用清单
- Read：4 次（spec.md / tasks.md / README.md / design.md 关键段）
- Grep：8 次（RssWebActivity/ReadRssActivity / markwon / ReadBookConfig/PaperInkHelper / SourceSelectDialog/stableSearchBookKey / Compose/RssSortViewModel 等 / SearchActivity/VideoPlayer/Migration/AndroidManifest / §4 文件清单统计 / TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface/activity_rss_search / RssSortViewModel / RSS-B-01/RssSearchActivity）

## 7. 审查覆盖范围

### 7.1 已验证修复点（13 项）
- ✅ 严重 #1 RSS-E-06 已完成标注（spec/tasks/design/README）
- ❌ 严重 #2 RssSearchActivity 主题扩展依赖（未修复）
- ✅ 严重 #3 SourceSelectDialog Compose 改写（spec/design）
- ✅ 严重 #4 SearchBookMergeUtils stableSearchBookKey 改写（spec/design）
- ✅ 严重 #5 PaperInkHelper ReadBookConfig.paperInkStrength（spec/design/README + §4.3 #12 新增）
- ✅ 严重 #6 markwon 4.6.2（spec/tasks/design/README）
- ✅ 中等 #1 路径对照表（spec §E）
- ⚠️ 中等 #2 RssSortViewModel 复用（tasks 已修复，design 4 处未同步）
- ✅ 中等 #3 RssFragment openRssSearch 入口设计（spec/tasks）
- ✅ 中等 #4 AppDatabase Migration_98_to_99（spec/tasks/design）
- ✅ 中等 #5 ChoiceSpeedDialog 调用点 VideoPlayer.kt:600（tasks/design）
- ❌ 中等 #6 activity_rss_search.xml 布局文件（未修复）
- ✅ 新发现：§4 文件清单总数同步正确（12 文件 / 46 合计）

### 7.2 未引入新问题
- ✅ §4.3 标题"12 个文件"与内容一致
- ✅ §4.9 统计表"主题管理 9+3=12"与 §4.3 一致
- ✅ §4.9 合计"31+15=46"与各模块小计一致
- ✅ P0 数量保持 14 不变（RSS-E-06 仍属 P0 但已 completed）
- ✅ markwon 4.6.2 任务描述无不兼容（tasklist/strikethrough/linkify 都有 4.x 版本）
- ⚠️ 唯一新问题：design.md 4 处 RssSearchViewModel 与 tasks.md 1.1.2 决策矛盾（详见 §3 新发现 #1）

---

**审查报告版本**：v1.0
**审查报告生成时间**：2026-07-18
**审查报告路径**：`f:\myself\github\WeAgentChat\temp\legado\docs\specs\forks-archive-borrow-implementation\review-final2-code-feasibility.md`
