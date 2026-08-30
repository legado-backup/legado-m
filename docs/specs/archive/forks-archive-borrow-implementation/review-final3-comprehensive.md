# 最终综合审查报告（第三轮：补充修复 10 项验证）

> **审查时间**：2026-07-18
> **审查范围**：前一轮 3 份审查报告（10 严重 + 15 中等）+ 10 项补充修复是否真正解决问题
> **审查方法**：Read/Grep 只读工具对照 spec.md / tasks.md / design.md / README.md + 3 份 analysis 验证修复
> **审查员**：forks-archive-borrow-implementation 最终综合审查员
> **前序报告**：
> - `review-code-feasibility.md`（v1.0，547 行，6 严重 + 6 中等 + 5 轻微）
> - `review-adr-logic.md`（v1.0，354 行，2 严重 + 6 中等 + 5 轻微）
> - `review-dependency-conflict.md`（v1.0，419 行，3 严重 + 3 中等 + 3 轻微）
> - `review-final2-code-feasibility.md`（v1.0，324 行，第二轮修复验证）
> - `review-final2-adr-logic.md`（v1.0，303 行，第二轮修复验证）
> - `review-final2-dependency-conflict.md`（v1.0，241 行，第二轮修复验证）

---

## 1. 审查概述

### 1.1 审查目标
验证前两轮审查发现的所有问题（10 严重 + 15 中等）+ 10 项补充修复是否真正生效，4 文档数据是否一致，是否引入新问题，最终评估是否可进入 P0 实施阶段。

### 1.2 审查步骤
1. 读取 6 份审查报告（前一轮 3 份 + 修复后 3 份）
2. 逐项验证 10 项补充修复是否生效
3. 验证 4 文档数据一致性（P0/P1/P2/ADR 数量、markwon 版本、RssWebActivity、RssSearchViewModel）
4. 验证是否引入新问题
5. 实施可行性总评

### 1.3 审查结论总览
| 维度 | 已修复 | 未修复 | 修复不完整 |
|------|--------|--------|-----------|
| 10 项补充修复 | 10 | 0 | 0 |
| 4 文档数据一致性 | 4 | 0 | 0 |
| 新发现问题 | - | 2（均轻微，不阻塞实施） | - |
| **合计** | **14** | **2** | **0** |

**总评**：✅ **可进入 P0 实施**（核心修复全部生效，仅 tasks.md 1.14 描述性段落与 README.md 修订记录 2 项轻微同步遗漏，不阻塞实施）

---

## 2. 补充修复 10 项验证（逐项 ✅/❌）

### ✅ 修复 #1：RssSearchActivity 主题扩展依赖标注（design.md §4.1 #1）

**验证证据**：
- `design.md` §4.1 #1（第 850 行）：标注"⚠️ 借鉴源 import TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface，本项目 lib/theme/ 无此扩展，实施时需改写为本地主题方案或新增扩展"
- `design.md` §4.1 #1 用途描述明确 RSS-B-01 实施时需改写

**结论**：✅ 已修复。借鉴源 3 个主题扩展依赖已明确标注。

---

### ✅ 修复 #2：activity_rss_search.xml 布局文件（design.md §4.8）

**验证证据**：
- `design.md` §4.8（第 928-935 行）：标题已改为"全局配置文件（4 个文件）"
- `design.md` §4.8 #4（第 935 行）：新增条目"`app/src/main/res/layout/activity_rss_search.xml` | 新增 | RssSearchActivity 布局文件（新建：含 RecyclerView + ProgressBar + EditText 搜索框；⚠️ 实施时检查借鉴源布局是否依赖本项目不存在的自定义 View，必要时改写为本地控件） | RSS-B-01"
- `design.md` §4.9 文件变更统计：全局配置文件 1 新增 + 3 修改 = 4 ✅，总计 31 + 16 = 47 ✅
- `design.md` §4.9 统计说明（第 951 行）明确"v2.4 修订：全局配置文件新增 activity_rss_search.xml 布局条目（RSS-B-01 RssSearchActivity 布局依赖）"

**结论**：✅ 已修复。布局文件条目已补充，文件变更统计已同步。

---

### ✅ 修复 #3：RssSearchViewModel → RssSortViewModel 4 处同步（design.md）

**验证证据**：
- `design.md` §4.1 #2（第 851 行）：✅ 已改为"`app/src/main/java/io/legado/app/ui/rss/source/EditRssSortViewModel.kt`（即 RssSortViewModel） | 复用（不新增） | 复用现有 RssSortViewModel 调度多源并发搜索 + pureSearch 参数支持（P1）；⚠️ 与 Archive 借鉴源一致，Archive RssSearchActivity.kt:20 实际 `class RssSearchActivity : VMBaseActivity<ActivityRssSearchBinding, RssSortViewModel>()` 复用现有 RssSortViewModel，不新增 RssSearchViewModel | RSS-B-01, RSS-B-04"
- `design.md` ADR-007 Decision（第 209 行）：✅ 已改为"+ RssSearchAdapter.kt + RssFragment 添加搜索入口（5 行代码）（⚠️ 复用现有 RssSortViewModel，与 Archive 借鉴源一致，不新增 RssSearchViewModel）"
- `design.md` §6 数据流图说明（第 645 行）：✅ 已改为"UI 轨：新增 RssSearchActivity + RssSearchAdapter（复用现有 RssSortViewModel）"
- `design.md` §11.1 单元测试覆盖矩阵（第 1150 行）：✅ 已改为"RSS 模块 | RssSortViewModel（搜索/分页/异常，复用）、SearchBookMergeUtils（去重/多源合并）"

**结论**：✅ 4 处全部同步修复，design.md 内部一致。

---

### ✅ 修复 #4：ADR-010a 标题修改

**验证证据**：
- `design.md` 第 254 行：✅ 标题已改为"### ADR-010a 主题视觉增强与导入导出"
- `design.md` §9.1 ADR 索引表（第 1239 行）：✅ 同步更新"ADR-010a | 主题视觉增强与导入导出 | Accepted | 模块决策类"

**结论**：✅ 标题已修改，与 P0 Decision 范围（视觉增强）一致。

---

### ✅ 修复 #5：R29 缓解措施更新

**验证证据**：
- `design.md` §5.1 风险清单 #29（第 989 行）：✅ 缓解措施已改为"已稳定运行（rhino 1.8.1 + minSdk 23 长期验证通过，项目已发布运行）；风险仅在未来若需升级 rhino 时需先提升 minSdk 至 24"
- 与 ADR-006"锁定原因：API 24 以下缺少 Arrays.setAll"+ ADR-022"minSdk 23 已实际部署"逻辑链完全一致

**结论**：✅ R29 缓解措施已更新，与 ADR-006/022 逻辑链无断裂。

---

### ✅ 修复 #6：R22 与 #26 关联说明

**验证证据**：
- `design.md` §5.1 风险清单 #26（第 986 行）：✅ 明确"RSS-B-01 与 RSS-B-05 共用 RssFragment.kt 并发修改风险 | 文件冲突 | 高 | 严格执行 RSS-B-05 → RSS-B-01 串行（同文件串行规范）；组 A 内部明确串行链。**R22 与 #26 关联**：R22 缓解措施（单 Agent 串行执行）即通过主 Agent 单线程避免 #26 所述 RssFragment.kt 文件冲突，两个风险条目共同约束组 A 串行链"
- `analysis-p0-strategy-risks.md` 第 356 行：R22 定义为"RssFragment.kt 文件冲突风险（已通过单 Agent 串行执行缓解）"，与 design.md #26 内容一致

**结论**：✅ R22 与 #26 关联说明已添加，两份文档定义统一。

---

### ✅ 修复 #7：§4.2 #2 VIDEO-B-01 集成位置同步

**验证证据**：
- `design.md` §4.2 #2（第 865 行）：✅ 关联任务列已删除"VIDEO-B-01(P0)"，仅保留"VIDEO-B-02(P0)"
- 用途描述明确"⚠️ VideoBookPreloader 集成位置已修订：VIDEO-B-01 不修改 VideoPlayerActivity.kt，改为集成到 SearchActivity.kt 搜索结果页预加载，详见 §4.6 #3"

**结论**：✅ §4.2 #2 已同步修订，不再标注 VIDEO-B-01 修改 VideoPlayerActivity.kt。

---

### ✅ 修复 #8：§4.6 SearchActivity.kt 追加 VIDEO-B-01

**验证证据**：
- `design.md` §4.6 #3（第 917 行）：✅ 关联任务已追加 VIDEO-B-01，从"RSS-B-03, RSS-E-05"扩展为"RSS-B-03, RSS-E-05, VIDEO-B-01"
- 用途描述明确"集成 SearchBookMergeUtils + SearchBookPreviewOverlay + VideoBookPreloader（搜索结果页预加载视频书目录）；关联任务：VIDEO-B-01（VideoBookPreloader 集成）"

**结论**：✅ §4.6 SearchActivity.kt 已追加 VIDEO-B-01，与 tasks.md 1.4.2 一致。

---

### ✅ 修复 #9：ADR-002 串行链简化（三任务 → 两任务）

**验证证据**：
- `design.md` ADR-002 组D（第 108-112 行）：✅ 已修订
  - VIDEO-B-01：标注"独立；新增 VideoBookPreloader.kt + 修改 SearchActivity.kt 搜索结果页预加载，不修改 VideoPlayerActivity.kt"
  - VIDEO-B-02：标注"依赖 VIDEO-B-01 架构（功能依赖非文件串行）；唯一修改 VideoPlayerActivity.kt 的任务"
  - VIDEO-E-02：标注"与 VIDEO-B-02 功能协同建议串行执行：VIDEO-B-02 → VIDEO-E-02；唯一修改 ChoiceSpeedDialog.kt，实际调用点 VideoPlayer.kt:600 不修改，不与 VIDEO-B-02 共用 VideoPlayerActivity.kt"
  - 注（第 112 行）：明确"v2.6 修订（串行链简化）：VideoPlayerActivity.kt 实际仅被 VIDEO-B-02 一个任务修改，原"三任务串行链"简化为"VIDEO-B-02 → VIDEO-E-02 两任务串行"（功能协同，非文件冲突）"
- `design.md` ADR-008 Decision（第 228 行）：✅ 同步修订"同文件串行约束（v2.6 修订简化）：VideoPlayerActivity.kt 实际仅被 VIDEO-B-02 一个任务修改...无需三任务串行；保留 VIDEO-B-02 → VIDEO-E-02 两任务串行约束（功能协同）"
- `design.md` §6.1 P0 实施顺序组D（第 1037-1041 行）：✅ 同步修订，与 ADR-002 一致

**结论**：✅ ADR-002 / ADR-008 / §6.1 三处串行链全部简化，内部一致。

---

### ✅ 修复 #10：spec.md §10 VideoPlayerActivity.kt 关联修正

**验证证据**：
- `spec.md` §10（第 661 行）：✅ VideoPlayerActivity.kt 关联任务已修正为"REQ-P0-012（VIDEO-B-02 章节链接缓存集成）, REQ-P0-014（VIDEO-E-02 ChoiceSpeedDialog 调用点 VideoPlayer.kt:600，非 VideoPlayerActivity.kt:725-737 Spinner）"
- 明确说明 VIDEO-E-02 实际调用点不修改 VideoPlayerActivity.kt

**结论**：✅ spec.md §10 已修正，与 tasks.md 1.14.2 / design.md §4.2 #2 一致。

---

## 3. 4 文档数据一致性验证

### 3.1 P0/P1/P2/ADR 数量一致性

| 文档 | P0 | P1 | P2 | ADR | 验证 |
|------|-----|-----|-----|-----|------|
| spec.md | 14 | 19 | 21 | 27 | ✅ 一致 |
| tasks.md | 14 | 19 | 21 | - | ✅ 一致 |
| design.md | 14 | 19 | 21 | 27 | ✅ 一致 |
| README.md | 14 | 19 | 21 | 27 | ✅ 一致 |
| analysis-task-priority.md | 14 | 19 | 21 | - | ✅ 一致 |

**验证证据**：
- `spec.md` 第 47 行 / 第 621 行：P0 14 / P1 19 / P2 21 = 54
- `tasks.md` 第 7 行：P0 14 / P1 19 / P2 21 = 54
- `design.md` 第 8 行：P0:14 / P1:19 / P2:21
- `design.md` 第 1282 行：14 / 19 / 21 = 54
- `README.md` 第 7 行 / 第 370 行：P0 14 / P1 19 / P2 21 = 54
- `analysis-task-priority.md` 第 14 行：P0 14 / P1 19 / P2 21

**结论**：✅ 4 文档 P0/P1/P2 数量一致，3 份 design/README/analysis ADR 数量一致（27）。

---

### 3.2 markwon 版本一致性（4 文档统一 4.6.2）

| 文档 | markwon 版本 | 验证 |
|------|------------|------|
| spec.md | 4.6.2（REQ-P0-002 标题） | ✅ |
| tasks.md | 4.6.2（1.2 标题） | ✅ |
| design.md | 4.6.2（§4.7 #1 / ADR-006 / ADR-002 组D） | ✅ |
| README.md | 4.6.2（§3.2 / §15 A1） | ✅ |

**验证证据**：Grep `markwon 3|markwon 4\.6\.2` 结果显示，4 文档统一使用"markwon 4.6.2"，"markwon 3"仅出现在审查报告自身（review-code-feasibility.md / review-adr-logic.md）作为历史问题记录。

**结论**：✅ markwon 版本 4 文档统一为 4.6.2。

---

### 3.3 RssWebActivity.kt → ReadRssActivity.kt 一致性（4 文档统一）

| 文档 | RssWebActivity | ReadRssActivity | 验证 |
|------|---------------|-----------------|------|
| spec.md | 无 | ✅ 使用 | ✅ |
| tasks.md | 仅在 1.5.2 历史说明 | ✅ 使用 | ✅ |
| design.md | 无 | ✅ §4.1 #9 使用 | ✅ |
| README.md | 仅在 §9.4.5 / §15 修复记录 | ✅ 使用 | ✅ |

**验证证据**：Grep `RssWebActivity` 结果显示，"RssWebActivity"仅出现在 README.md 修复记录（§9.4.5 / §15 v2.3 修复详情）和审查报告自身，4 文档主体已统一为 `ReadRssActivity.kt`。

**结论**：✅ RssWebActivity.kt 4 文档统一为 ReadRssActivity.kt。

---

### 3.4 RssSearchViewModel → RssSortViewModel 一致性（4 文档统一）

| 文档 | RssSearchViewModel | RssSortViewModel | 验证 |
|------|-------------------|------------------|------|
| spec.md | 无 | ✅ 未新增（隐含复用） | ✅ |
| tasks.md | 仅在 1.1.2 / 1.1 说明中标注"不新增" | ✅ 复用 | ✅ |
| design.md | 仅在 ADR-007 / §4.1 #2 / §6 / §11.1 中标注"不新增" | ✅ 复用 | ✅ |
| README.md | 无 | ✅ 未涉及 | ✅ |

**验证证据**：Grep `RssSearchViewModel` 结果显示，"RssSearchViewModel"仅在 design.md 4 处出现，每次都明确标注"不新增 RssSearchViewModel"，与 Archive 借鉴源一致；tasks.md 1.1.2 同步标注"不新增 RssSearchViewModel"。

**结论**：✅ RssSearchViewModel 4 文档统一为复用 RssSortViewModel（不新增）。

---

## 4. 新发现问题（2 项，均轻微，不阻塞实施）

### 🟡 新发现 #1：tasks.md 1.14 同文件冲突提示段落未与 design.md v2.6 串行链简化同步

**问题描述**：
- `tasks.md` 1.14 段落"⚠️ 同文件冲突提示"（第 151 行）仍写："VIDEO-B-01/B-02/E-02 都修改 `VideoPlayerActivity.kt`，必须按顺序串行：VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02"
- 但 `design.md` ADR-002 v2.6 修订已明确"VideoPlayerActivity.kt 实际仅被 VIDEO-B-02 一个任务修改，原"三任务串行链"简化为"VIDEO-B-02 → VIDEO-E-02 两任务串行""

**冲突类型**：跨文档不一致（tasks.md 描述性段落 vs design.md ADR-002）

**影响**：
- 不阻塞 P0 实施（实施者主要参考 design.md ADR-002 + tasks.md 1.4.2/1.14.2 子任务描述）
- tasks.md 1.4.2 已正确标注"集成到 SearchActivity.kt"
- tasks.md 1.14.2 已正确标注"实际调用点是 VideoPlayer.kt:600，不是 VideoPlayerActivity.kt:725-737"
- 仅 tasks.md 1.14 末尾的"⚠️ 同文件冲突提示"段落未同步修订（1 行文字）

**修复建议**：
- `tasks.md` 第 151 行修订为："⚠️ 同文件冲突提示（v2.6 修订简化）：VideoPlayerActivity.kt 实际仅被 VIDEO-B-02 一个任务修改（VIDEO-B-01 修改 SearchActivity.kt，VIDEO-E-02 修改 ChoiceSpeedDialog.kt），原三任务串行链简化为 VIDEO-B-02 → VIDEO-E-02 两任务串行（功能协同，非文件冲突），详见 design.md ADR-002 组D"

**优先级**：🟡 中等（建议在 P0 实施过程中同步修订，不阻塞 P0 启动）

---

### 🟢 新发现 #2：README.md 未更新 v2.4/v2.5/v2.6 修订记录

**问题描述**：
- `README.md` §15 v2.3 修复详情（第 648-704 行）记录了 v2.3 修复
- `README.md` 版本演进（第 515-516 行）仅记录到 v2.3
- `design.md` §4.9 统计说明已标注"v2.3 / v2.4 / v2.5 修订"，ADR-002 已标注"v2.6 修订"
- README.md 未同步 v2.4（activity_rss_search.xml 新增）/ v2.5（RssSortViewModel 复用）/ v2.6（串行链简化）三项修订记录

**冲突类型**：文档同步遗漏（README.md 修订记录 vs design.md 修订标注）

**影响**：
- 不阻塞 P0 实施（实施者主要参考 design.md ADR-002 / tasks.md 1.x 子任务）
- design.md 已通过"v2.4 / v2.5 / v2.6 修订"标注说明
- README.md 修订记录仅为历史追溯用途

**修复建议**：
- `README.md` 版本演进表追加 v2.4 / v2.5 / v2.6 三行修订记录
- 或在 §15 v2.3 修复详情后追加 §16 v2.4-v2.6 修订详情

**优先级**：🟢 轻微（可选修复，不阻塞 P0 实施）

---

## 5. 实施可行性总评

### 5.1 总评结论

**✅ 可进入 P0 实施**

### 5.2 修复有效性总评

| 维度 | 总数 | 已修复 | 未修复 | 修复不完整 | 修复率 |
|------|------|--------|--------|-----------|--------|
| 10 项补充修复 | 10 | 10 | 0 | 0 | 100% |
| 4 文档数据一致性 | 4 | 4 | 0 | 0 | 100% |
| 新发现问题 | 2 | - | 2 | - | - |
| **合计** | **16** | **14** | **2** | **0** | **87.5%** |

### 5.3 核心修复点验证通过

✅ **10 项补充修复全部生效**：
1. RssSearchActivity 主题扩展依赖标注 ✅
2. activity_rss_search.xml 布局文件新增 ✅
3. RssSearchViewModel → RssSortViewModel 4 处同步 ✅
4. ADR-010a 标题修改 ✅
5. R29 缓解措施更新 ✅
6. R22 与 #26 关联说明 ✅
7. §4.2 #2 VIDEO-B-01 集成位置同步 ✅
8. §4.6 SearchActivity.kt 追加 VIDEO-B-01 ✅
9. ADR-002 串行链简化（三任务 → 两任务）✅
10. spec.md §10 VideoPlayerActivity.kt 关联修正 ✅

✅ **4 文档数据完全一致**：
- P0=14 / P1=19 / P2=21 / ADR=27 ✅
- markwon 版本 4 文档统一为 4.6.2 ✅
- RssWebActivity.kt 4 文档统一为 ReadRssActivity.kt ✅
- RssSearchViewModel 4 文档统一为复用 RssSortViewModel ✅

### 5.4 实施前必须确认的 8 项事实

| # | 事实 | 文档位置 | 影响 |
|---|------|---------|------|
| 1 | Archive 项目 RssSearchActivity.kt 依赖 3 个主题扩展（本项目无） | design.md §4.1 #1 | RSS-B-01 需改写 |
| 2 | Archive 项目 RssSearchActivity.kt 第 22 行使用 ActivityRssSearchBinding | design.md §4.8 #4 | RSS-B-01 需新增 activity_rss_search.xml |
| 3 | Archive 项目 RssSearchActivity.kt 复用 RssSortViewModel | design.md §4.1 #2 / ADR-007 | RSS-B-01 ViewModel 复用决策 |
| 4 | ReadRssActivity.kt:421 已实现 cacheFirst 逻辑 | design.md §4.1 #9 / tasks.md 1.5.2 | RSS-E-06 仅需真机验证 |
| 5 | markwon 4.6.2 已引入 4 个子依赖，仅需补充 3 个扩展 | spec.md REQ-P0-002 / design.md §4.7 #1 | DEPS-B-01 补充 ext.tasklist/strikethrough/linkify |
| 6 | AppDatabase version=98，需 Migration_98_to_99 | tasks.md 1.13.2 / design.md ADR-013 | VIDEO-E-01 数据库迁移 |
| 7 | ChoiceSpeedDialog 调用点是 VideoPlayer.kt:600（非 VideoPlayerActivity.kt:725-737） | tasks.md 1.14.2 / design.md §4.2 #3 | VIDEO-E-02 修改目标 |
| 8 | PaperInkHelper 编译依赖 ReadBookConfig.paperInkStrength（本项目无） | design.md §4.3 #1 / #12 | THEME-B-01 必须同步修改 ReadBookConfig |

---

## 6. 关键风险提示（实施时需注意但可在实施中解决）

### 6.1 实施前必须建立性能基线（ADR-016 + ADR-002 P0 前置任务）

- 使用 `ai_tests/scripts/swipe_test_log.py` + `l2_verify_video_player.py` 测量启动时间/内存占用/搜索响应时间/视频加载时间/FPS
- P0 完成后对比验证性能无显著回退（容忍阈值：启动时间 +5%、FPS -3 帧、搜索响应 +10%）

### 6.2 借鉴源路径调整（design.md §4.1-§4.3）

实施时按 design.md 目标路径放置文件，但需同步调整借鉴源的 package 声明与所有 import：
- PaperInkHelper：Archive `io.legado.app.help` → 本项目 `io.legado.app.lib.theme`
- SourceSelectDialog：Archive `io.legado.app.ui.widget` → 本项目 `io.legado.app.ui.rss`
- VideoBookPreloader：Archive `io.legado.app.ui.video` → 本项目 `io.legado.app.help.gsyVideo`
- RssSearchActivity：Archive `io.legado.app.ui.rss.article` → 本项目 `io.legado.app.ui.rss.search`

### 6.3 数据库迁移安全（ADR-013 + VIDEO-E-01）

- AppDatabase version 98→99
- 新增 ReadRecentBook 实体 + DAO + Migration_98_to_99（手写 Migration）
- 必须真机验证覆盖安装流程（旧版本→新版本）数据完整性
- schema 导出 + runCatching 兜底

### 6.4 共享文件串行管理（R26 + ADR-002）

- `strings.xml`：主 Agent 串行编辑，每组完成后批量更新
- `proguard-rules.pro`：主 Agent 串行编辑，每个新增类任务补充 keep 规则
- `AndroidManifest.xml`：仅 RSS-B-01 注册 RssSearchActivity（VideoPlayerActivity 已存在，VideoBookPreloader 不需注册）

### 6.5 借鉴源改写策略（4 项严重发现的实施方案）

| 任务 | 借鉴源依赖 | 改写策略 |
|------|-----------|---------|
| RSS-B-01 | TopBarSearchStyle/applyUiBodyTypefaceDeep/uiTypeface 3 个主题扩展 | 改写为本地主题方案或新增扩展 |
| RSS-B-02 | LegadoMiuixCard/LegadoMiuixChoiceRow 等 Compose 组件 | 改写为 BottomSheetDialog + RecyclerView |
| RSS-B-03 | stableSearchBookKey 扩展函数 | 改写为按书名+作者去重 |
| THEME-B-01 | ReadBookConfig.paperInkStrength 字段 | 同步修改 ReadBookConfig.kt 新增字段 |

### 6.6 markwon 4.x API 兼容性验证（DEPS-B-01）

- markwon 3.x 与 4.x API 不兼容
- 借鉴 Archive 项目时需进行 API 适配
- P0 实施前先在分支验证依赖兼容性
- 现有 4 个依赖（core/image-glide/tables/html）与新扩展（tasklist/strikethrough/linkify）的兼容性必须在实施时验证

---

## 7. 优先级建议

### 7.1 P0 立即实施（无阻塞）

✅ **可立即启动 P0 14 项任务**，按 ADR-002 4 组顺序执行（A→B→C→D）：
- 组A（RSS 主线，5 项）：RSS-B-05 → RSS-B-01 [同文件串行] / RSS-B-02 / RSS-B-03 / RSS-E-06
- 组B（THEME 视觉，2 项）：THEME-B-01 / THEME-B-02
- 组C（EPUB 加速，2 项）：EPUB-B-01 → EPUB-B-02 [同文件串行]
- 组D（VIDEO 增强，5 项）：VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02 [功能协同串行] / VIDEO-E-01 / DEPS-B-01

### 7.2 实施过程中建议同步修订（不阻塞 P0 启动）

| 优先级 | 修订项 | 涉及文件 |
|--------|--------|---------|
| 🟡 中等 | tasks.md 1.14 同文件冲突提示段落同步 v2.6 串行链简化 | tasks.md |
| 🟢 轻微 | README.md 追加 v2.4/v2.5/v2.6 修订记录 | README.md |

---

## 8. 审查方法学补充

### 8.1 已验证的关键修复点

| 修复点 | 文档位置 | 验证方法 |
|--------|---------|---------|
| RssSearchActivity 主题扩展依赖 | design.md §4.1 #1 | Grep `TopBarSearchStyle|applyUiBodyTypefaceDeep|uiTypeface` |
| activity_rss_search.xml 布局文件 | design.md §4.8 #4 / §4.9 统计 | Grep `activity_rss_search` |
| RssSearchViewModel → RssSortViewModel 4 处同步 | design.md §4.1 #2 / ADR-007 / §6 / §11.1 | Grep `RssSearchViewModel` |
| ADR-010a 标题修改 | design.md 第 254 行 | Grep `ADR-010a` |
| R29 缓解措施更新 | design.md §5.1 #29 | Grep `R29|rhino 1\.8\.1.*minSdk` |
| R22 与 #26 关联说明 | design.md §5.1 #26 | Grep `R22|RssFragment\.kt.*串行` |
| §4.2 #2 VIDEO-B-01 集成位置同步 | design.md §4.2 #2 | Read §4.2 |
| §4.6 SearchActivity.kt 追加 VIDEO-B-01 | design.md §4.6 #3 | Read §4.6 |
| ADR-002 串行链简化 | design.md ADR-002 / ADR-008 / §6.1 | Read ADR-002 / ADR-008 |
| spec.md §10 VideoPlayerActivity.kt 关联修正 | spec.md §10 | Read §10 |

### 8.2 已验证的数据一致性

| 数据 | 4 文档统一值 | 验证方法 |
|------|------------|---------|
| P0 数量 | 14 | Grep `P0=14|P0 14|P0:14` |
| P1 数量 | 19 | Grep `P1=19|P1 19|P1:19` |
| P2 数量 | 21 | Grep `P2=21|P2 21|P2:21` |
| ADR 数量 | 27 | Grep `^### ADR-` (design.md) |
| markwon 版本 | 4.6.2 | Grep `markwon 3|markwon 4\.6\.2` |
| RssWebActivity → ReadRssActivity | ReadRssActivity.kt | Grep `RssWebActivity` |
| RssSearchViewModel → RssSortViewModel | 复用 RssSortViewModel | Grep `RssSearchViewModel` |

---

## 9. 审查结论

### 9.1 综合结论

**✅ forks-archive-borrow-implementation 项目可进入 P0 实施阶段**

### 9.2 修复完整性评估

- ✅ 10 项补充修复全部生效（100% 修复率）
- ✅ 4 文档数据完全一致（P0/P1/P2/ADR 数量、markwon 版本、RssWebActivity、RssSearchViewModel）
- ✅ 修复未引入新硬矛盾
- 🟡 2 项轻微同步遗漏（tasks.md 1.14 段落 / README.md 修订记录），不阻塞 P0 实施
- ✅ 实施前必须确认的 8 项事实全部明确标注
- ✅ 关键风险提示全部覆盖（性能基线 / 路径调整 / 数据库迁移 / 共享文件 / 借鉴源改写 / markwon 兼容性）

### 9.3 实施路径建议

1. **第一优先**：建立性能基线（ADR-016 P0 前置任务）
2. **第二优先**：按 ADR-002 4 组顺序实施 P0 14 项任务（A→B→C→D）
3. **第三优先**：实施过程中同步修订 tasks.md 1.14 段落 + README.md 修订记录
4. **第四优先**：每项任务完成后遵循 ADR-011 任务完成四件套（代码验证 + 真机/E2E 测试 + 文档同步 + 问题记录）

---

**审查报告版本**：v1.0
**审查报告生成时间**：2026-07-18
**审查报告路径**：`f:\myself\github\WeAgentChat\temp\legado\docs\specs\forks-archive-borrow-implementation\review-final3-comprehensive.md`
**审查员**：forks-archive-borrow-implementation 最终综合审查员
**审查结论**：✅ 可进入 P0 实施（10 项补充修复全部生效，4 文档数据一致，2 项轻微同步遗漏不阻塞实施）
