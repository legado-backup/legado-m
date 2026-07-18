# 设计合理性深度审查报告（spec.md + tasks.md）

> **审查时间**：2026-07-18
> **审查范围**：`docs/specs/forks-archive-borrow-implementation/` 下的 `spec.md` + `tasks.md`（对照 `design.md` / `analysis-task-priority.md` / `analysis-report.md`）
> **审查方法**：源文档交叉比对 + 项目源码事实验证（Grep/Glob/Read） + P0 逐项沙盘推演
> **输出安全**：源名称用代号（Archive 项目 / 本项目），域名用代号（站点A/B），URL 用路径模式，敏感字段隐藏为***

---

## 1. 审查概述

### 1.1 审查目标

本审查聚焦三大问题：

1. **设计合理性**：Intent/Scope/Approach/Requirements/Scenarios 是否合理？
2. **实施阶段问题识别**：哪些问题会延迟到实施阶段才暴露？如何提前避免？
3. **技术可行性验证**：每个 P0 任务的"技术前提"是否在源码层面成立？

### 1.2 审查方法

- **文档交叉比对**：spec.md ↔ tasks.md ↔ design.md ↔ analysis-task-priority.md ↔ analysis-report.md 五份文档相互对照
- **源码事实验证**：用 Grep/Glob/Read 工具直接验证 spec 与 design 中提及的关键源码事实（文件存在性、字段存在性、默认值、行数、类继承关系等）
- **P0 沙盘推演**：对 14 项 P0 任务逐项模拟实施过程，识别可能的问题

### 1.3 关键审查发现概览（重要）

经源码事实验证，发现 **多处严重事实偏差**，会在 P0 实施阶段立刻暴露为"阻塞型问题"：

| # | 偏差类型 | spec/design 描述 | 源码实际 | 影响任务 |
|---|---------|-----------------|---------|---------|
| 1 | 表不存在 | "修改 ReadRecentBook.kt"（视频书写入最近阅读） | 本项目无此实体/DAO/表，仅 fork 仓库中有 | REQ-P0-013 / VIDEO-E-01 |
| 2 | 基类不存在 | "RssSearchActivity 继承自 BaseSearchActivity" | 本项目无 BaseSearchActivity，仅有 VMBaseActivity | REQ-P0-001 / RSS-B-01 |
| 3 | 文件路径错误 | EpubFile.kt 在 `app/.../help/book/EpubFile.kt` | 实际在 `app/.../model/localBook/EpubFile.kt` | REQ-P0-009/010, EPUB-B-01/02 |
| 4 | 文件路径错误 | RssFragment.kt 在 `app/.../ui/rss/RssFragment.kt` | 实际在 `app/.../ui/main/rss/RssFragment.kt` | REQ-P0-001/011, RSS-B-01/05 |
| 5 | 文件路径错误 | VideoActivity.kt 在 `app/.../ui/rss/video/VideoActivity.kt` | 本项目无 VideoActivity.kt，仅有 `ui/video/VideoPlayerActivity.kt`，且无 `ui/rss/video/` 目录 | REQ-P0-004/012, VIDEO-B-01/02 |
| 6 | 文件路径错误 | ChoiceSpeedDialog.kt 在 `app/.../ui/rss/video/` | 实际在 `app/.../help/gsyVideo/ChoiceSpeedDialog.kt` | REQ-P0-014, VIDEO-E-02 |
| 7 | 文件路径错误 | Exo2MediaPlayer.kt 在 `app/.../ui/rss/video/` | 实际在 `app/.../help/gsyVideo/Exo2MediaPlayer.kt` | REQ-P1-013, VIDEO-E-03 |
| 8 | 默认值已是 true | "RSS 列表页 cacheFirst 默认 true（需调整）" | RssSource.kt:113 已是 `cacheFirst: Boolean = true` | REQ-P0-005 / RSS-E-06（部分工作已"自然完成"） |
| 9 | 依赖已引入 | "P2 引入 sora-editor 代码编辑器" | app/build.gradle:355-358 已引入 soraEditor BOM+core+language.textmate | REQ-P2-002 / DEPS-B-03（任务工作量评估错误） |
| 10 | 行数偏差 | "EpubFile.kt ~700 行" | 实际 429 行 | design.md §1.1 / ADR-009（背景事实偏差） |
| 11 | 入口存在性 | "PaperInkHelper/VideoBookPreloader/RssSearchActivity 等为本项目新增" | ✅ 已验证本项目确实不存在（在 fork 仓库中有），spec 描述正确 | 新增类无问题 |

**结论速览**：spec/tasks 整体设计意图合理，但**存在多处可在实施第一天就暴露的严重事实偏差**，必须先修订才能进入实施阶段。详见 §7。

---

## 2. spec.md 设计合理性审查

### 2.1 Intent 合理性

#### 2.1.1 Intent 是否真实反映用户需求

spec.md §1 Intent 描述：基于 v5.0 终版决策，将 54 项 B（Borrow）决策落地为本项目代码改造，按 P0/P1/P2 分阶段实施，最大化用户感知收益。

**合理性评估**：✅ 合理
- Intent 与决策来源（forks-archive-comparison v5.0 终版）一致
- "最大化用户感知收益" 与 v5.0 用户价值导向原则（ADR-005 四维度评估）一致
- 明确"不借鉴 64 项" 的边界，避免无效改造

#### 2.1.2 是否与 v5.0 决策一致

**⚠️ 存在版本混用问题**：

- spec.md §1 自称"基于 forks-archive-comparison 的 v5.0 终版决策"
- 但 §2.1 v5.1 调整说明又引入"基于 analysis-task-priority.md 用户价值再评估"的 4 项 P1→P0 升级
- 这意味着 spec.md 实际是 **v5.1 版本**，但 §1 仍写"基于 v5.0 终版"
- design.md ADR-002 同样存在此问题（"P0 范围调整为 14 项"实际是 v5.1 调整，但 ADR 标题仍是 v5.0 上下文）

**建议**：将 spec.md §1 修订为"基于 v5.1 调整版决策（v5.0 终版 + analysis-task-priority.md 用户价值再评估）"。

#### 2.1.3 是否有遗漏的核心需求

**逐模块核查**：

| 模块 | spec 是否覆盖 | 遗漏点 |
|------|-------------|--------|
| RSS | ✅ 10 项全覆盖 | 无遗漏 |
| EPUB | ✅ 10 项全覆盖 | EPUB-B-06/B-07 已合并说明（§4.3.2 注），无遗漏 |
| THEME | ✅ 13 项全覆盖 | 无遗漏 |
| VIDEO | ✅ 5 项全覆盖 | 无遗漏 |
| DEPS | ✅ 8 项全覆盖 | 无遗漏 |
| BUILD | ✅ 8 项全覆盖 | 无遗漏 |

**结论**：54 项决策在 spec 中全部有对应 Requirement，无遗漏。

### 2.2 Scope 合理性

#### 2.2.1 Scope 大小评估

- **P0 14 项**：合理。每项用户价值 ≥4.5，覆盖 5 大模块核心场景
- **P1 19 项**：合理。中高收益 13 项 + 开发者侧 6 项
- **P2 21 项**：合理。技术升级 5 + 用户中价值 7 + UI 优化 9（放在最后）
- **总计 54 项**：与 v5.0 终版决策数一致

#### 2.2.2 排除内容合理性

spec.md §2.2 明确排除 5 类内容：

1. AI 模块 11 项（全量否决）→ ✅ 用户明确反对，理由充分
2. BUILD 配置差异 5 项 → ✅ 用户无感知
3. 其他 48 项不借鉴决策 → ✅ 用户价值低于阈值
4. 跨模块重构 → ✅ 控制风险
5. 新功能开发 → ✅ 仅借鉴已验证功能

**结论**：Scope 边界清晰，排除项有合理依据。

#### 2.2.3 边界清晰度

**⚠️ 存在模糊边界**：

- THEME-B-03（主题包 ZIP 导入导出，P1）vs THEME-E-04（主题包导入导出格式，P1）功能重叠，spec 未明确二者边界
- analysis-task-priority.md §6.1 已建议合并，但 spec/tasks 仍保留为两项独立任务
- 同样问题存在于：THEME-B-05（字体内嵌支持）vs EPUB-E-02（字体内嵌）

**建议**：在 spec.md 中明确每对"功能重叠"任务的边界划分（如 THEME-B-03 负责 ZIP 容器，THEME-E-04 负责内部 JSON Schema）。

### 2.3 Approach 合理性

#### 2.3.1 三阶段实施策略

spec.md §3.1 三阶段（P0 立即 / P1 季度 / P2 年度）+ design.md ADR-001 详细论证。

**合理性评估**：✅ 合理
- 备选方案（一次性全部 / 只 P0 / 无序实施）否决理由充分
- 三阶段对应 P0/P1/P2 优先级，与用户价值评估对齐
- 每阶段独立可验证，风险分散

#### 2.3.2 Alternatives 评估

spec.md §3.2 列出 6 个备选方案并否决，评估如下：

| 备选 | 否决理由 | 评估 |
|------|---------|------|
| 1. 一次性全部实施 | 风险集中、周期过长 | ✅ 合理 |
| 2. 只实施 P0 | 遗漏中高收益 | ✅ 合理 |
| 3. 不分优先级 | 难以追踪 | ✅ 合理 |
| 4. 引入 AI 模块 | 用户反对 | ✅ 合理 |
| 5. 不借鉴 UI 优化 | 用户接受包体积 | ✅ 合理 |
| 6. 子代理并行 P0 | 违反并发文件修改规范 | ⚠️ 部分合理 |

**备选 6 的问题**：spec 否决"子代理并行"的理由是"源码文件修改必须串行化"，但 design.md ADR-002 又提出"4 个并行组"方案（组内串行、组间并行）。**spec 与 design 在并行策略上存在表述矛盾**。

实际上 design.md ADR-002 + R22 风险已承认"单 Agent 4 组并行退化为串行执行"，即真正落地时仍是串行。spec.md §3.2 备选 6 的否决理由应改为"AI 主 Agent 实际串行执行，分组仅用于工作组织"。

#### 2.3.3 Drawbacks 可接受性

spec.md §3.3 列出 6 项 Drawbacks，逐项评估：

1. 分阶段周期长 → 可接受（AI 执行无工期估算）
2. P2 UI 优化增加 2-5MB → 可接受（用户已同意）
3. 部分借鉴点需兼容性评估 → 可接受（已在 design.md 风险清单 R15/R16/R17 覆盖）
4. 与现有功能冲突 → ⚠️ 实际比预期严重（详见 §4）
5. 依赖升级风险 → 可接受（锁定依赖 ADR-006）
6. P1/P2 优先级可能调整 → 可接受

**结论**：Drawbacks 整体可接受，但第 4 项"与现有功能冲突"在源码事实验证下比 spec 预期更严重。

### 2.4 Requirements 合理性（重点）

#### 2.4.1 P0 14 项 Requirement 逐项审查

| REQ | 决策ID | 用户故事清晰 | 验收标准可量化 | 技术可行 | 依赖正确 | 风险评估 |
|-----|--------|-------------|--------------|---------|---------|---------|
| P0-001 | RSS-B-01 | ✅ | ✅（响应<3s） | ⚠️ 基类不存在 | ✅ | 未提 |
| P0-002 | DEPS-B-01 | ✅ | ✅ | ✅ | ✅ | 未提 |
| P0-003 | THEME-B-01 | ✅ | ✅（FPS≥50） | ✅ | ✅ | 未提 |
| P0-004 | VIDEO-B-01 | ✅ | ✅（首帧-30%） | ⚠️ 路径错误 | ✅ | 未提 |
| P0-005 | RSS-E-06 | ✅ | ✅（<500ms） | ❌ 默认值已是 true | ✅ | 未提 |
| P0-006 | THEME-B-02 | ✅ | ✅ | ✅ | ✅ | 未提 |
| P0-007 | RSS-B-02 | ✅ | ✅（≥2步） | ✅ | ✅ | 未提 |
| P0-008 | RSS-B-03 | ✅ | ✅ | ✅ | ✅ | 未提 |
| P0-009 | EPUB-B-01 | ✅ | ✅（<1s） | ⚠️ 路径错误 | ✅ | 未提 |
| P0-010 | EPUB-B-02 | ✅ | ✅ | ⚠️ 路径错误 | ✅ | 未提 |
| P0-011 | RSS-B-05 | ✅ | ✅ | ⚠️ 路径错误 | ✅ | 未提 |
| P0-012 | VIDEO-B-02 | ✅ | ✅ | ⚠️ 路径错误 | ✅ | 未提 |
| P0-013 | VIDEO-E-01 | ✅ | ✅ | ❌ 表不存在 | ✅ | 未提 |
| P0-014 | VIDEO-E-02 | ✅ | ✅ | ⚠️ 路径错误 | ✅ | 未提 |

**P0 Requirement 突出问题**：

**🔴 严重问题 1：REQ-P0-005 cacheFirst 默认值已是 true**
- spec.md §4.1 REQ-P0-005 验收标准："RSS 列表页 cacheFirst 默认 true"
- 源码事实：`RssSource.kt:113` 已是 `var cacheFirst: Boolean = true`
- 意味着 RSS 列表页部分验收标准"自然完成"，剩余工作仅有"WebView cacheFirst 默认 true"和"用户可在设置中关闭"
- 实施工作量被高估，spec 应修订为"WebView cacheFirst 默认值调整 + 关闭选项 UI"

**🔴 严重问题 2：REQ-P0-013 ReadRecentBook 表不存在**
- spec.md §4.1 REQ-P0-013："视频书播放时写入 ReadRecentBook 表"
- design.md ADR-013："VIDEO-E-01 ReadRecentBook 写入涉及数据库 schema 变更"
- design.md §4.2 文件清单："修改 ReadRecentBook.kt"
- 源码事实：本项目 `app/src/main/java/io/legado/app/data/entities/` 目录下**没有 ReadRecentBook.kt**，仅有 ReadRecord.kt / ReadRecordDetail.kt / ReadRecordShow.kt
- spec 描述"低实施成本"错误，实际需要：新建实体 + DAO + Migration + 数据库 version 升级 + 覆盖安装测试
- 这意味着 REQ-P0-013 实际是"高成本"任务，应重新评估优先级

**🔴 严重问题 3：REQ-P0-001 BaseSearchActivity 不存在**
- spec.md §4.1 REQ-P0-001："新增 RssSearchActivity.kt 继承自 BaseSearchActivity"
- design.md ADR-007："新增 RssSearchActivity.kt（继承 BaseSearchActivity）"
- 源码事实：本项目无 BaseSearchActivity.kt，仅有 `VMBaseActivity` 作为基类（SearchActivity 继承自 VMBaseActivity）
- 实施时需选择：① 改为继承 VMBaseActivity ② 先创建 BaseSearchActivity 抽象基类（额外工作量未计入）

**⚠️ 中等问题 4：多处文件路径错误**
- spec.md §4.1 REQ-P0-009/010 引用 `EpubFile.kt`，design.md §4.4 路径写 `app/src/main/java/io/legado/app/help/book/EpubFile.kt`
- 实际路径：`app/src/main/java/io/legado/app/model/localBook/EpubFile.kt`（package `io.legado.app.model.localBook`）
- spec.md §4.1 REQ-P0-001/011 引用 `RssFragment.kt`，design.md §4.1 路径写 `app/src/main/java/io/legado/app/ui/rss/RssFragment.kt`
- 实际路径：`app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt`（package `io.legado.app.ui.main.rss`）
- design.md §4.2 引用 `VideoActivity.kt` 路径 `app/src/main/java/io/legado/app/ui/rss/video/VideoActivity.kt`
- 实际：本项目无 VideoActivity.kt，仅有 `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`，且无 `ui/rss/video/` 目录
- 同样错误：ChoiceSpeedDialog.kt、Exo2MediaPlayer.kt 实际在 `help/gsyVideo/` 而非 `ui/rss/video/`

**⚠️ 中等问题 5：所有 P0 Requirement 均无"风险评估"字段**
- spec.md §4.1 每个 REQ 都有"决策ID/用户价值/实施成本/用户场景/技术要点/验收标准"
- 但**全部缺失"风险评估"字段**
- design.md §5.1 风险清单虽有 30 项，但未与具体 REQ 一一映射
- 建议在每个 REQ 中补充"风险等级 + 关联风险编号"

#### 2.4.2 P1 19 项 Requirement 抽查

**抽查发现**：

| 问题类型 | 涉及 REQ | 描述 |
|---------|---------|------|
| 与 P0 冲突 | 无 | P1 与 P0 无直接冲突 |
| 重复 | REQ-P1-007（THEME-B-03）↔ REQ-P1-010（THEME-E-04） | 功能重叠，analysis-task-priority.md §6.1 建议合并但 spec 未采纳 |
| 重复 | REQ-P1-005（EPUB-E-02）↔ REQ-P1-009（THEME-B-05） | 字体内嵌功能重叠 |
| 遗漏 | REQ-P1-014~018（BUILD-B 系列） | BUILD-B-01/03/04 用户价值 2.8/3.0/3.0 低于 P1 下限 3.8，按 ADR-005 评分标准应降级 P2，但 spec 仍归 P1 |
| 路径错误 | REQ-P1-013（VIDEO-E-03） | design.md §4.2 路径 `ui/rss/video/Exo2MediaPlayer.kt` 错误，实际在 `help/gsyVideo/` |

**🔴 中等问题 6：P1 包含低于 P1 下限的任务**
- spec.md 附录 B 优先级判定标准：P1 用户价值 3.8-4.8
- 但 REQ-P1-016（BUILD-B-01）用户价值 2.8、REQ-P1-017（BUILD-B-03）3.0、REQ-P1-018（BUILD-B-04）3.0
- 这 3 项均低于 P1 下限 3.8，按 spec 自己的判定标准应归 P2
- analysis-task-priority.md §3.20~3.22 已建议降级 P2，但 spec.md §4.2.2 仍归 P1
- 这是 spec 内部一致性问题

#### 2.4.3 P2 21 项 Requirement 抽查

**抽查发现**：

| 问题类型 | 涉及 REQ | 描述 |
|---------|---------|------|
| 与 P0 冲突 | 无 | P2 与 P0 无直接冲突 |
| 任务已部分完成 | REQ-P2-002（DEPS-B-03 sora-editor） | app/build.gradle:355-358 已引入 soraEditor BOM+core+language.textmate，spec 描述"引入 sora-editor"工作量评估错误 |
| 重复 | REQ-P2-005（THEME-B-08 KitBinding 基础机制）↔ REQ-P2-021（THEME-E-03 KitBinding 跨组件绑定） | analysis-task-priority.md §6.1 已建议合并，spec 未采纳 |
| 重复 | REQ-P2-010~012（BUILD-B-06/07/08） | analysis-task-priority.md §6.1 建议 BUILD-B-06+B-08 合并，spec 未采纳 |

### 2.5 Scenarios 合理性

#### 2.5.1 S1-S11 场景覆盖

| 场景 | 覆盖 REQ | 关键步骤 | 评估 |
|------|---------|---------|------|
| S1 RSS 搜索 | P0-001 | 6 步 | ✅ 完整 |
| S2 订阅文章渲染 | P0-002 | 4 步 | ✅ 完整 |
| S3 阅读视觉 | P0-003 | 4 步 | ✅ 完整 |
| S4 视频播放加速 | P0-004 | 4 步 | ✅ 完整 |
| S5 RSS 加载加速 | P0-005 | 3 步 | ⚠️ 步骤 1"系统优先从缓存加载（cacheFirst=true）"描述与现状矛盾（已是 true） |
| S6 字体撞色检测 | P0-006 | 4 步 | ✅ 完整 |
| S7 EPUB 阅读 | P0-009/010 | 5 步 | ✅ 完整 |
| S8 统一源选择 | P0-007 | 4 步 | ✅ 完整 |
| S9 搜索结果合并 | P0-008 | 5 步 | ✅ 完整 |
| S10 P1 综合 | 多项 | 6 步 | ⚠️ 仅列表，无详细步骤 |
| S11 P2 综合 | 多项 | 4 步 | ⚠️ 仅列表，无详细步骤 |

#### 2.5.2 遗漏的关键场景

**⚠️ 遗漏场景 1：VIDEO-E-01 视频书最近阅读**
- spec.md §5 没有 S 场景描述"用户播放视频书 → 视频书出现在最近阅读"
- 这是 REQ-P0-013 的核心用户故事，但 S 场景未覆盖

**⚠️ 遗漏场景 2：VIDEO-E-02 视频倍速切换**
- spec.md §5 没有 S 场景描述"用户切换倍速 → 倍速切换无卡顿"
- 这是 REQ-P0-014 的核心用户故事

**⚠️ 遗漏场景 3：VIDEO-B-02 连续看剧**
- spec.md §5 没有 S 场景描述"用户看完一集 → 自动预加载下一集"
- 这是 REQ-P0-012 的核心用户故事

**⚠️ 遗漏场景 4：覆盖安装兼容性**
- 涉及数据库迁移的任务（REQ-P0-013、REQ-P1-008）缺少"覆盖安装"场景
- design.md ADR-013 要求覆盖安装测试，但 spec.md §5 未体现

**建议**：补充 S12-S15 四个场景，覆盖视频场景三件套 + 覆盖安装兼容性。

#### 2.5.3 场景描述清晰度

S1-S9 描述清晰，每步可验证。S10/S11 是"综合场景"，仅列步骤无详细描述，**作为 P1/P2 验收依据不足**。

---

## 3. tasks.md 设计合理性审查

### 3.1 任务可行性（重点）

#### 3.1.1 P0 14 项任务逐项审查

| 任务ID | 描述清晰 | 子任务完整 | 依赖正确 | 验收可量化 | 技术难点 | 资源需求 | 风险评估 |
|--------|---------|----------|---------|-----------|---------|---------|---------|
| 1.1 RSS-B-01 | ✅ | ✅ 6 子任务 | ✅ | ✅ | ⚠️ 基类选择 | 无 | 未提 |
| 1.2 DEPS-B-01 | ✅ | ✅ 5 子任务 | ✅ | ✅ | 无 | 无 | 未提 |
| 1.3 THEME-B-01 | ✅ | ✅ 4 子任务 | ✅ | ✅ | 无 | 无 | 未提 |
| 1.4 VIDEO-B-01 | ✅ | ✅ 4 子任务 | ✅ | ✅ | ⚠️ 路径错误 | 无 | 未提 |
| 1.5 RSS-E-06 | ✅ | ✅ 3 子任务 | ✅ | ✅ | ❌ 默认值已是 true | 无 | 未提 |
| 1.6 THEME-B-02 | ✅ | ✅ 4 子任务 | ✅ | ✅ | 无 | 无 | 未提 |
| 1.7 RSS-B-02 | ✅ | ✅ 4 子任务 | ✅ | ✅ | 无 | 无 | 未提 |
| 1.8 RSS-B-03 | ✅ | ✅ 4 子任务 | ✅ | ✅ | 无 | 无 | 未提 |
| 1.9 EPUB-B-01 | ✅ | ✅ 4 子任务 | ✅ | ✅ | ⚠️ 路径错误 | 无 | 未提 |
| 1.10 EPUB-B-02 | ✅ | ✅ 4 子任务 | ✅ | ✅ | ⚠️ 路径错误 | 无 | 未提 |
| 1.11 RSS-B-05 | ✅ | ✅ 2 子任务 | ✅ 依赖 1.1 | ✅ | ⚠️ 路径错误 | 无 | 未提 |
| 1.12 VIDEO-B-02 | ✅ | ✅ 3 子任务 | ✅ 依赖 1.4 | ✅ | ⚠️ 路径错误 | 无 | 未提 |
| 1.13 VIDEO-E-01 | ✅ | ✅ 2 子任务 | ✅ | ✅ | ❌ 表不存在 | 无 | 未提 |
| 1.14 VIDEO-E-02 | ✅ | ✅ 2 子任务 | ✅ | ✅ | ⚠️ 路径错误 | 无 | 未提 |

**P0 任务可行性总结**：

- ✅ 描述清晰度：14/14 全部清晰
- ✅ 依赖正确性：14/14 依赖关系正确（含已修正的 1.11→1.1、1.12→1.4）
- ⚠️ 子任务完整性：1.13 VIDEO-E-01 仅 2 子任务，未覆盖"新建实体/DAO/Migration"
- ❌ 技术可行性：1.5（默认值已 true）、1.13（表不存在）2 项存在严重技术可行性问题
- ⚠️ 技术难点：1.1（基类）、1.4/1.9/1.10/1.11/1.12/1.14（路径错误）6 项存在技术难点
- ❌ 风险评估：14 项全部未在任务级标注风险评估

**🔴 严重问题 7：1.13 VIDEO-E-01 子任务不完整**
- tasks.md §1.13 仅 2 子任务："1.13.1 视频书播放时写入 ReadRecentBook 表" + "1.13.2 真机验证"
- 实际需要的子任务（源码事实：表不存在）：
  - 1.13.0a 新建 ReadRecentBook.kt 实体（@Entity + @Parcelize + 字段默认值）
  - 1.13.0b 新建 ReadRecentBookDao.kt（CRUD + 查询）
  - 1.13.0c AppDatabase 升级 version + 编写 Migration（AutoMigration 或手写）
  - 1.13.0d 视频书播放时写入逻辑（区分 BookType.video）
  - 1.13.0e 覆盖安装兼容性测试（旧版本→新版本）
  - 1.13.0f 真机验证视频书出现在最近阅读
- 实际工作量是 tasks.md 描述的 3-5 倍

**🔴 严重问题 8：1.5 RSS-E-06 部分子任务已完成**
- tasks.md §1.5.1："RSS 列表页 cacheFirst 默认 true（RssSource 序列化默认值）"
- 源码事实：`RssSource.kt:113` 已是 `var cacheFirst: Boolean = true`
- 子任务 1.5.1 实际无工作量，应删除或改为"验证已存在的默认值"
- tasks.md 应修订为：
  - 1.5.1 验证 RssSource.cacheFirst 默认值已是 true（无需修改）
  - 1.5.2 WebView cacheFirst 默认 true（订阅文章加载入口）
  - 1.5.3 添加用户关闭选项 UI
  - 1.5.4 真机验证 RSS 加载速度

### 3.2 依赖关系合理性

#### 3.2.1 依赖链长度

- 最长依赖链 3 层（THEME-B-06 → THEME-B-08 → THEME-E-03），远低于 5 层警戒线 ✅
- P0 内部依赖链最长 2 层（VIDEO-B-01 → VIDEO-B-02；RSS-B-05 → RSS-B-01）✅

#### 3.2.2 循环依赖检查

analysis-task-priority.md §5.3 已确认无循环依赖，本审查复核确认 ✅。

#### 3.2.3 遗漏的依赖（已修正验证）

tasks.md v5.1 已采纳 analysis-task-priority.md §5.1 的 5 处依赖补充建议：
- ✅ THEME-E-05 → THEME-B-04（2.1.2 已补充）
- ✅ THEME-B-07 → THEME-E-04（3.2.1 已补充）
- ✅ EPUB-B-08 → EPUB-B-03（3.2.3 已补充）
- ✅ THEME-E-02 → THEME-E-01（3.3.2 已补充）
- ✅ VIDEO-E-03 → VIDEO-B-01（2.1.13 已补充）

#### 3.2.4 不必要的依赖（已修正验证）

- ✅ EPUB-E-05 → EPUB-E-06 已删除（3.3.4 已修正）

#### 3.2.5 遗漏的依赖（本审查新发现）

**🟡 中等问题 9：1.13 VIDEO-E-01 应补充对 BookType.video 的依赖说明**
- 视频书通过 `BookType.video = 0b100` 区分（已验证 BookType.kt:14）
- VIDEO-E-01 实施时需在 ReadRecentBook 写入逻辑中检查 `book.type and BookType.video != 0`
- 这不是任务级依赖，但是实施级约束，建议在子任务 1.13.1 中补充说明

**🟡 中等问题 10：1.4 VIDEO-B-01 应补充对 SearchActivity/搜索结果页的依赖说明**
- spec.md REQ-P0-004："在搜索结果页预加载视频书目录"
- 但 tasks.md §1.4.2 仅说"集成到搜索结果页"，未指明具体是 SearchActivity 还是其他 Activity
- 源码事实：本项目有 `app/src/main/java/io/legado/app/ui/book/search/SearchActivity.kt`
- 建议补充子任务说明"集成到 SearchActivity.kt 视频书搜索结果分支"

#### 3.2.6 关键路径合理性

- 关键路径起点：EPUB-B-01（被 EPUB-E-04/EPUB-B-03/EPUB-E-03/EPUB-B-08 依赖）
- 关键路径起点：THEME-B-03（被 THEME-E-04/THEME-E-02/THEME-B-07 依赖）
- 关键路径起点：BUILD-B-02（被 BUILD-B-06/BUILD-B-07 依赖）
- 这 3 个关键节点应在各自 P 阶段优先启动 ✅

### 3.3 任务粒度合理性

#### 3.3.1 任务过大（>5 子任务）

无。所有任务子任务数 ≤6 ✅

#### 3.3.2 任务过小（<2 子任务）

- 1.11 RSS-B-05：2 子任务（5 行代码）→ analysis-task-priority.md §6.1 建议合并到 1.1，但 tasks.md 保留独立
- 1.13 VIDEO-E-01：2 子任务 → 实际应扩展为 5-6 子任务（见表 §3.1.1 严重问题 7）
- 1.14 VIDEO-E-02：2 子任务 → 粒度合理（增强 ChoiceSpeedDialog）

#### 3.3.3 任务粒度不均

**🟡 中等问题 11：P0 任务粒度极不均衡**
- 最小：1.11 RSS-B-05（5 行代码，2 子任务）
- 最大：1.13 VIDEO-E-01（实际需要新建实体+DAO+Migration，应 5-6 子任务）
- 比例：约 100:1
- 建议参照 analysis-task-priority.md §6.1 合并 RSS-B-05 到 RSS-B-01

**🟡 中等问题 12：高成本任务未拆分**
- analysis-task-priority.md §6.2 建议 4 项高成本任务拆分（THEME-B-03/THEME-B-06/EPUB-B-03/EPUB-E-03）
- tasks.md 仍保留为单任务，未采纳拆分建议
- THEME-B-03 主题包 ZIP 导入导用 1428 行代码，单任务风险高

### 3.4 任务ID 规范性

#### 3.4.1 任务ID 唯一性

- ✅ 54 项任务 ID 唯一（决策ID + 序号组合）
- ✅ 与 spec.md 决策ID 一一对应

#### 3.4.2 命名规范性

- P0 任务命名：`1.1 ~ 1.14` ✅ 规范
- P1 任务命名：`2.1.1 ~ 2.2.6` ✅ 规范
- P2 任务命名：`3.1.1 ~ 3.3.9` ✅ 规范
- 与决策ID 映射：✅ 一致

#### 3.4.3 与 spec.md 一致性

- ✅ P0 14 项与 spec.md §4.1 REQ-P0-001~014 一一对应
- ✅ P1 19 项与 spec.md §4.2 一致
- ✅ P2 21 项与 spec.md §4.3 一致

---

## 4. 实施阶段问题识别（重点）

### 4.1 技术实施问题（14 项 P0 逐项沙盘推演）

#### 4.1.1 RSS-B-01 RssSearchActivity（1.1）

**实施步骤沙盘**：
1. 创建 RssSearchActivity.kt → ❌ 阻塞：spec 说继承 BaseSearchActivity，但项目中无此类
2. 创建 RssSearchViewModel.kt → ✅ 可参考 SearchViewModel 模式
3. 创建 RssSearchAdapter.kt → ✅ 可参考 SearchAdapter 模式
4. RssFragment 添加搜索入口 → ⚠️ 路径错误：spec 说 `ui/rss/RssFragment.kt`，实际 `ui/main/rss/RssFragment.kt`
5. 单元测试 → ✅
6. 真机验证 → ✅

**实施时会发现的问题**：
- 🔴 第 1 步阻塞：需要决策基类选择
  - 方案 A：改为继承 `VMBaseActivity<ActivityRssSearchBinding, RssSearchViewModel>`（与 SearchActivity 一致）
  - 方案 B：先创建 BaseSearchActivity 抽象基类（额外工作量，需重构 SearchActivity）
  - 推荐方案 A，spec 需修订

- ⚠️ 第 4 步路径错误：需修正为 `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt`
- ⚠️ searchUrl 字段使用方式：spec 说"激活 searchUrl 字段"，但未明确搜索时如何构造 URL（是简单替换关键词还是用规则引擎解析）
- ⚠️ 多源并发搜索性能：5 源并发 + 3s 超时，需复用本项目已有 Semaphore 限流（design.md ADR-014 已说明，但 spec.md REQ-P0-001 未提）
- ⚠️ 搜索结果聚合去重：spec.md REQ-P0-001 说"按订阅源分组展示"，但 REQ-P0-008 SearchBookMergeUtils 说"按书名+作者去重"，二者逻辑不同
  - RSS 搜索结果应按"文章标题+源"分组，不是"书名+作者"
  - 建议明确：REQ-P0-001 是 RSS 文章搜索（按源分组），REQ-P0-008 是书籍搜索（按书名+作者去重）

**实施前必须解决**：
- 修订基类选择（spec.md REQ-P0-001 + design.md ADR-007）
- 修订 RssFragment.kt 路径
- 明确 searchUrl 字段的使用方式
- 明确 RSS 搜索结果聚合逻辑（与 SearchBookMergeUtils 区分）

#### 4.1.2 DEPS-B-01 markwon 3 扩展（1.2）

**实施步骤沙盘**：
1. 添加 markwon-strikethrough 依赖 → ✅ app/build.gradle 已有 markwon-core 等，新增依赖无障碍
2. 添加 markwon-tasklist 依赖 → ✅
3. 添加 markwon-linkify 依赖 → ✅
4. 配置 Markwon 引擎使用新扩展 → ⚠️ 需找到订阅文章渲染入口
5. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ 第 4 步：需定位订阅文章渲染入口（RssReadActivity 或 RssWebActivity），spec 未指明具体文件
- ⚠️ markwon 版本兼容性：当前 markwon-core 版本未验证，新增扩展需版本一致
- ⚠️ Markwon 实例化方式：是单例还是每次创建？需检查现有代码

**风险等级**：低

#### 4.1.3 THEME-B-01 纸墨风格（1.3）

**实施步骤沙盘**：
1. 创建 PaperInkHelper.kt → ✅ 基于 Paint.setShadowLayer，纯 Android SDK
2. 集成到阅读界面 → ⚠️ 需定位 ContentTextView/PageView 具体位置
3. 添加主题配置开关 → ⚠️ 需定位 ReadConfig 入口
4. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ 集成点不明确：spec 说"ContentTextView/PageView"，但未指明完整路径
- ⚠️ 性能影响：Paint.setShadowLayer 在长文本渲染时可能掉帧，需 FPS ≥50 验证
- ⚠️ 与现有字体渲染冲突：本项目可能有自定义字体渲染逻辑，需检查是否冲突

**风险等级**：低-中

#### 4.1.4 VIDEO-B-01 VideoBookPreloader（1.4）

**实施步骤沙盘**：
1. 创建 VideoBookPreloader.kt → ⚠️ 路径错误：design.md 说 `help/gsyVideo/`（与 ChoiceSpeedDialog 同目录），但 Archive 在 `ui/video/`
2. 集成到搜索结果页 → ⚠️ 需明确是 SearchActivity 还是其他
3. 真机验证 → ✅
4. 单元测试 → ✅

**实施时会发现的问题**：
- ⚠️ 预加载触发时机：spec 说"搜索视频书时预加载目录"，但搜索结果可能是非视频书混合，需判断 `book.type == BookType.video`
- ⚠️ 缓存策略：90 行代码的缓存逻辑未明确（TTL？LRU？内存还是磁盘？）
- ⚠️ 与 SearchActivity 集成：搜索结果页是 SearchActivity，需在 SearchAdapter 或 BookAdapter 中触发预加载
- ⚠️ 协程规范：spec 未明确使用 Coroutine.async 链式封装（design.md ADR-015 已强制，但 tasks.md §1.4 未提）

**风险等级**：中

#### 4.1.5 RSS-E-06 cacheFirst 默认值（1.5）

**实施步骤沙盘**：
1. RSS 列表页 cacheFirst 默认 true → ❌ RssSource.kt:113 已是 true，子任务无工作量
2. WebView cacheFirst 默认 true → ⚠️ 需定位 RssWebActivity 或 RssReadActivity
3. 真机验证 → ✅

**实施时会发现的问题**：
- 🔴 子任务 1.5.1 已"自然完成"：RssSource.cacheFirst 默认值已是 true
- ⚠️ WebView cacheFirst 实施点不明确：spec 说"订阅文章加载入口"，但未指明是 RssWebActivity 还是 RssReadActivity
- ⚠️ 用户关闭选项 UI：spec 说"用户可在设置中关闭"，但未指明设置页面具体位置

**实施前必须解决**：
- 修订 tasks.md §1.5.1 为"验证 RssSource.cacheFirst 默认值已是 true（无需修改）"
- 明确 WebView cacheFirst 实施点
- 明确用户关闭选项 UI 位置

**风险等级**：低（工作量被高估）

#### 4.1.6 THEME-B-02 字体撞色检测（1.6）

**实施步骤沙盘**：
1. 实现 sanitizeFontColorAgainstSurfaces 方法 → ⚠️ 需定位 ThemeColorUtils.kt（spec 说存在但未验证）
2. 集成 AndroidColorUtils.calculateContrast → ⚠️ 需确认 AndroidColorUtils 是否本项目已有
3. 在主题设置界面添加撞色检测提示 → ⚠️ 需定位主题设置界面
4. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ AndroidColorUtils 来源：是 Android SDK 还是 androidx.core？
  - 实际：androidx.core.graphics.ColorUtils.calculateContrast
  - spec 写"AndroidColorUtils"可能误导
- ⚠️ 撞色阈值：spec 说"对比度低于阈值时提示"，但未定义阈值（WCAG 标准 4.5:1？）
- ⚠️ 触发时机：spec 说"主题配置保存时触发"，但用户可能即时调整颜色，需考虑实时检测

**风险等级**：低-中

#### 4.1.7 RSS-B-02 SourceSelectDialog（1.7）

**实施步骤沙盘**：
1. 创建 SourceSelectDialog.kt → ✅
2. 实现 book/rss 源统一选择 → ⚠️ 需考虑数据源合并逻辑
3. 集成到源管理界面 → ⚠️ 需定位 BookSource/RssSource 管理界面
4. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ "统一选择"含义不明确：是 Tab 切换 book/rss 源，还是混合列表？
- ⚠️ 数据源合并：BookSource 和 RssSource 是两个独立表，合并查询需考虑性能
- ⚠️ "简化操作步骤 ≥2 步"：当前源选择流程未文档化，无法量化简化效果

**风险等级**：中

#### 4.1.8 RSS-B-03 SearchBookMergeUtils（1.8）

**实施步骤沙盘**：
1. 创建 SearchBookMergeUtils.kt → ✅
2. 实现搜索结果合并逻辑 → ⚠️ 去重逻辑需考虑多源信息保留
3. 集成到搜索界面 → ⚠️ 路径需修正
4. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ 与 REQ-P0-001 RSS 搜索结果展示逻辑冲突：
  - REQ-P0-001 说"按订阅源分组展示"
  - REQ-P0-008 说"按书名+作者去重"
  - 二者去重逻辑不同，需明确 SearchBookMergeUtils 是否用于 RSS 搜索
- ⚠️ SearchActivity 集成：spec 说"集成到 SearchActivity"，但 SearchActivity 已有搜索逻辑，需考虑侵入性
- ⚠️ 多源信息保留格式：spec 说"保留多源信息"，但未明确 UI 展示方式（折叠列表？多源徽章？）

**风险等级**：中

#### 4.1.9 EPUB-B-01 章节资源索引（1.9）

**实施步骤沙盘**：
1. 修改 EpubFile.kt 使用 spine 优先索引 → ⚠️ 路径错误：spec 说 `help/book/EpubFile.kt`，实际 `model/localBook/EpubFile.kt`
2. 真机验证 → ✅
3. 单元测试 → ✅
4. 性能基准测试 → ✅

**实施时会发现的问题**：
- ⚠️ EpubFile.kt 实际 429 行（spec/design 说 ~700 行），架构比预期简单，改造影响面可能更大
- ⚠️ spine 索引兼容性：异常 EPUB（无 spine / spine 为空）需处理
- ⚠️ 与 EPUB-B-02 共用 EpubFile.kt：必须串行（design.md ADR-002 已说明）
- ⚠️ Book.kt 实体零扩展原则：缓存数据走独立磁盘目录（design.md ADR-009），但 tasks.md §1.9 未提此约束

**风险等级**：低

#### 4.1.10 EPUB-B-02 资源过滤+标题归一化（1.10）

**实施步骤沙盘**：
1. 实现非内容资源过滤 → ⚠️ 路径错误同 1.9
2. 实现标题归一化 → ⚠️ 需明确归一化规则（HTML 标签清理？空白处理？）
3. 真机验证 → ✅
4. 单元测试 → ✅

**实施时会发现的问题**：
- ⚠️ "非内容资源"定义：图片/CSS/字体是过滤掉还是单独处理？spec 未明确
- ⚠️ 标题归一化规则：spec 说"去除前后空白/换行/HTML 标签"，但 EPUB 标题可能含 XS3 标签嵌套，需考虑规则完整性
- ⚠️ 与 EPUB-B-01 共用 EpubFile.kt 串行约束

**风险等级**：低

#### 4.1.11 RSS-B-05 RssFragment openRssSearch 入口（1.11）

**实施步骤沙盘**：
1. RssFragment 添加 openRssSearch 方法 → ⚠️ 路径错误同 1.1
2. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ 与 1.1 RSS-B-01 共用 RssFragment.kt 串行约束
- ⚠️ 5 行代码工作量极小，单独成任务增加协调成本（analysis-task-priority.md §6.1 已建议合并）

**风险等级**：低

#### 4.1.12 VIDEO-B-02 章节链接缓存+下一集预加载（1.12）

**实施步骤沙盘**：
1. 实现 chapterLinkCache（TTL 30 分钟）→ ⚠️ 缓存实现方式未明确（内存？磁盘？）
2. 实现 preloadNextEpisode 机制 → ⚠️ "下一集"如何识别（RssEpisode 顺序？）
3. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ 缓存实现：内存 LRU？HashMap+Timer？spec 未明确
- ⚠️ "下一集"识别：需查询 RssEpisode 表获取顺序，spec 未说明
- ⚠️ 与 VIDEO-B-01 集成：预加载逻辑接入 VideoBookPreloader 还是 VideoPlayerActivity？spec 未明确
- ⚠️ VideoActivity.kt 路径错误：实际是 VideoPlayerActivity.kt

**风险等级**：中

#### 4.1.13 VIDEO-E-01 ReadRecentBook 写入（1.13）

**实施步骤沙盘**：
1. 视频书播放时写入 ReadRecentBook 表 → ❌ 阻塞：表不存在
2. 真机验证 → ✅

**实施时会发现的问题**：
- 🔴 ReadRecentBook 表在本项目不存在，需新建：
  - 实体（@Entity + @Parcelize + 字段默认值）
  - DAO（CRUD + 查询）
  - AppDatabase version 升级 + Migration
  - 覆盖安装兼容性测试
- 🔴 实际工作量是 tasks.md 描述（2 子任务）的 3-5 倍
- ⚠️ 与现有 ReadRecord 表关系：ReadRecord 已存在，是否复用还是新建独立表？
  - design.md ADR-013 备选 C "使用 SharedPreferences 视频书记录 → 否决（与最近阅读统一管理冲突）"
  - 但 spec 未明确 ReadRecentBook 与 ReadRecord 的关系
- ⚠️ 视频书区分：需通过 `book.type and BookType.video != 0` 判断（BookType.kt:14 已有 video=0b100）

**实施前必须解决**：
- 修订 tasks.md §1.13 扩展为 5-6 子任务（新建实体/DAO/Migration/写入逻辑/覆盖安装测试/真机验证）
- 明确 ReadRecentBook 与 ReadRecord 的关系
- 重新评估实施成本（从"低"改为"中-高"）

**风险等级**：高（数据库迁移 + 表新建）

#### 4.1.14 VIDEO-E-02 ChoiceSpeedDialog 增强（1.14）

**实施步骤沙盘**：
1. 增强 ChoiceSpeedDialog 倍速选项 → ⚠️ 路径错误：spec 说 `ui/rss/video/`，实际 `help/gsyVideo/`
2. 真机验证 → ✅

**实施时会发现的问题**：
- ⚠️ "增强"含义不明确：增加倍速档位（如 2.5x）？还是 UI 改造？
- ⚠️ 与 ExoPlayer 倍速实现：当前倍速通过 PlayerParameters 实现，新增档位需验证 ExoPlayer 支持
- ⚠️ 音频质量影响：高倍速可能导致音频失真，spec 未提

**风险等级**：低

### 4.2 数据库迁移问题

#### 4.2.1 涉及数据库迁移的任务

| 任务ID | 迁移类型 | 风险 | 现状评估 |
|--------|---------|------|---------|
| 1.13 VIDEO-E-01 | 新建表（ReadRecentBook） | 高 | 🔴 spec 未识别为迁移任务 |
| 2.1.8 THEME-B-04 | 字段扩展（Config 30+ 字段） | 中 | ⚠️ spec 说"低实施成本"但实际需 Migration |
| 2.1.6 RSS-B-04 | 新增字段（pureSearch） | 低 | ⚠️ spec 未提迁移 |
| 1.5 RSS-E-06 | 默认值调整（已是 true） | 无 | ✅ 无迁移 |

#### 4.2.2 迁移方案安全性

design.md ADR-013 已定义"AutoMigration + runCatching 兜底 + 覆盖安装兼容性测试"三段式策略 ✅。

#### 4.2.3 覆盖安装影响

- 🔴 VIDEO-E-01 新建表：覆盖安装时旧版本无此表，AutoMigration 会自动创建，但需验证
- ⚠️ THEME-B-04 字段扩展：新增字段必须有默认值（@ColumnInfo defaultValue），否则 AutoMigration 失败
- ⚠️ RSS-B-04 pureSearch 字段：Boolean 默认 false，需通过 @ColumnInfo(defaultValue = "0") 保证向后兼容

**建议**：在 tasks.md 中为每个涉及 DB 的任务补充"数据库迁移子任务"，明确 Migration 编号。

### 4.3 网络层兼容性问题

#### 4.3.1 涉及网络层变更的任务

| 任务ID | 网络变更 | 兼容性风险 |
|--------|---------|-----------|
| 1.1 RSS-B-01 | 多源并发搜索 | 中（站点限流风险） |
| 2.1.6 RSS-B-04 | pureSearch 参数 | 低（默认 false） |
| 3.2.1 THEME-B-07 | WebDAV 云同步 | 中（协议兼容性） |

#### 4.3.2 兼容性测试需求

- RSS-B-01 多源并发搜索：需测试 5 源/10 源/20 源并发，验证 Semaphore 限流是否生效
- RSS-B-04 pureSearch：需测试纯 URL 源兼容性
- THEME-B-07 WebDAV：需测试不同 WebDAV 服务端兼容性（Nextcloud / 群晖 / 自建）

design.md ADR-014 已定义网络层兼容性策略 ✅。

### 4.4 UI 兼容性问题

#### 4.4.1 涉及 UI 变更的任务

| 任务ID | UI 变更 | 屏幕适配需求 |
|--------|---------|------------|
| 1.1 RSS-B-01 | 新增 RssSearchActivity | 横竖屏适配 |
| 1.3 THEME-B-01 | 阅读设置开关 | 阅读设置入口适配 |
| 1.7 RSS-B-02 | SourceSelectDialog | BottomSheet 适配 |
| 2.1.1 RSS-E-05 | SearchBookPreviewOverlay | 覆盖层适配 |
| 3.3.7 DEPS-B-06 | liquidglass 视觉效果 | API 23 兼容性 |
| 3.3.8 DEPS-B-08 | lottie 动画 | 性能适配 |

#### 4.4.2 屏幕适配测试

design.md ADR-022 已定义"5.0-10 寸屏幕 + 横竖屏 + 平板"适配要求 ✅。

#### 4.4.3 API 23 兼容性

- 🔴 liquidglass 1.0.3：spec 未验证 API 23 兼容性，design.md ADR-022 要求验证
- 🔴 lottie 6.6.6：同上
- ⚠️ rhino 1.8.1 锁定原因之一是 API 24 以下缺少 Arrays.setAll，需确认 minSdk 23 是否受影响

**建议**：P2 UI 优化类任务实施前必须先验证依赖在 API 23 下的运行时兼容性。

### 4.5 性能问题

#### 4.5.1 可能影响性能的任务

| 任务ID | 性能风险 | 验证方法 |
|--------|---------|---------|
| 1.3 THEME-B-01 | Paint.setShadowLayer 渲染开销 | FPS ≥50 测量 |
| 1.4 VIDEO-B-01 | 预加载阻塞 UI | 搜索结果页 FPS 测量 |
| 1.9 EPUB-B-01 | spine 索引性能 | 首章加载时间 <1s |
| 1.12 VIDEO-B-02 | 缓存 TTL 失效性能 | 连续看剧帧率 |
| 3.3.7 DEPS-B-06 | liquidglass 渲染开销 | 整体 FPS 测量 |
| 3.3.8 DEPS-B-08 | lottie 动画内存占用 | 内存峰值测量 |

#### 4.5.2 性能基准测试

design.md ADR-016 + ADR-020 已定义性能基准与预算策略 ✅。

**🔴 中等问题 13：性能基线建立未列入 P0 任务**
- design.md R21 已识别此风险："性能基准未建立（ADR-016/020 要求 P0 前建立基线，但 P0 任务清单未列入此项）"
- 但 tasks.md §1 P0 14 项任务中仍无"基线建立"任务
- 建议在 P0 启动前增加任务 1.0"性能基线建立"作为前置任务

### 4.6 测试问题

#### 4.6.1 难以测试的任务

| 任务ID | 测试难点 | 建议测试方式 |
|--------|---------|------------|
| 1.3 THEME-B-01 | 视觉效果难以自动化测试 | 真机肉眼验证 + FPS 测量 |
| 1.6 THEME-B-02 | 撞色检测阈值主观 | 单元测试覆盖边界 case + 真机验证 |
| 1.4 VIDEO-B-01 | 预加载缓存命中难以验证 | 单元测试 + 真机首帧时间对比 |
| 1.12 VIDEO-B-02 | 连续看剧流畅度主观 | 真机验证 + 帧率测量 |
| 3.3.7 DEPS-B-06 | 液态玻璃视觉效果主观 | 真机肉眼验证 |

#### 4.6.2 真机测试需求

design.md ADR-011 已强制"每项必须真机测试" ✅。

#### 4.6.3 E2E 测试需求

design.md §7 已定义 4 层测试策略（单元/集成/真机/回归）✅。

**🟡 中等问题 14：E2E 测试脚本覆盖不全**
- ai_tests/scripts/ 现有脚本：quick_build_install.py / import_rss_source.py / l2_verify_video_player.py / swipe_test_log.py
- 但 P0 涉及的 RSS 搜索、EPUB 阅读、主题撞色检测等场景无对应 E2E 脚本
- 建议在 P0 启动前补充对应 E2E 测试脚本

---

## 5. 风险评估

### 5.1 高风险任务

| 任务ID | 风险点 | 风险等级 | 缓解措施 |
|--------|-------|---------|---------|
| 1.13 VIDEO-E-01 | 表不存在，实际需新建实体+DAO+Migration | 高 | 修订 tasks.md 扩展子任务；重新评估成本为"中-高" |
| 2.1.7 THEME-B-03 | 1428 行高成本，与现有扁平结构兼容性 | 高 | 拆分为 3 个子任务（导入/导出/格式规范） |
| 3.1.4 THEME-B-06 | 905 行架构重构，影响面广 | 高 | 拆分为 3 个子任务；先做 POC 验证 |
| 3.2.1 THEME-B-07 | 高成本 + 用户需配置云盘 | 高 | 保持 P2 长期规划；充分评估 WebDAV 兼容性 |
| 3.3.3 EPUB-E-03 | 架构重构成本高 | 高 | 拆分为 3 个子任务 |
| 3.2.4 RSS-B-06 | Compose 重写高成本 | 高 | 保持 P2 长期规划 |
| 3.2.3 EPUB-B-08 | 高成本技术架构 | 高 | 保持 P2 长期规划 |
| 3.1.1 DEPS-B-02 | Compose API 兼容性风险 | 高 | 分阶段升级（2025.04.01 → 07.00 → 10.00） |
| 3.3.2 THEME-E-02 | 与现有结构不兼容 | 高 | 保持 P2 长期规划 |
| 1.4 VIDEO-B-01 | 预加载需严格不阻塞 UI | 中-高 | 真机 FPS 测量；Coroutine.async 链式封装 |

### 5.2 中风险任务

| 任务ID | 风险点 | 风险等级 |
|--------|-------|---------|
| 1.1 RSS-B-01 | 基类选择 + 多源并发性能 | 中 |
| 1.6 THEME-B-02 | 撞色阈值需调优 | 中 |
| 1.7 RSS-B-02 | 数据源合并性能 | 中 |
| 1.8 RSS-B-03 | 与 RSS-B-01 去重逻辑冲突 | 中 |
| 1.12 VIDEO-B-02 | 缓存实现方式 + 下一集识别 | 中 |
| 2.1.8 THEME-B-04 | Config 字段扩展需 Migration | 中 |
| 2.1.13 VIDEO-E-03 | 播放器增强基于预加载架构 | 中 |
| 3.1.3 DEPS-B-09 | Glide ksp 迁移兼容性 | 中 |
| 3.3.7 DEPS-B-06 | liquidglass API 23 兼容性 + 包体积 | 中 |
| 3.3.8 DEPS-B-08 | lottie 包体积 2-3MB | 中 |

### 5.3 低风险任务

| 任务ID | 风险等级 |
|--------|---------|
| 1.2 DEPS-B-01 | 低 |
| 1.3 THEME-B-01 | 低 |
| 1.5 RSS-E-06 | 低（工作量被高估） |
| 1.9 EPUB-B-01 | 低 |
| 1.10 EPUB-B-02 | 低 |
| 1.11 RSS-B-05 | 低 |
| 1.14 VIDEO-E-02 | 低 |
| 2.1.4 DEPS-B-04 | 低 |
| 2.1.5 EPUB-E-02 | 低 |
| 2.1.6 RSS-B-04 | 低 |
| 2.1.11 EPUB-B-03 | 低 |
| 2.2.x BUILD-B 系列 | 低 |

---

## 6. 实施建议

### 6.1 实施顺序建议

#### 6.1.1 P0 实施前必做（前置任务）

1. **修订 spec.md / tasks.md / design.md 中的事实偏差**（详见 §7 严重问题）
2. **建立性能基线**（design.md R21 已识别但未列入 tasks.md）
3. **补充 E2E 测试脚本**（RSS 搜索 / EPUB 阅读 / 主题撞色检测）
4. **验证 markwon / sora-editor 版本兼容性**

#### 6.1.2 P0 推荐实施顺序（修订后）

基于依赖关系 + 风险等级 + 事实偏差修正后的推荐顺序：

```
阶段 0：P0 前置（必做）
  0.1 修订 spec/tasks/design 事实偏差
  0.2 建立性能基线（swipe_test_log.py + l2_verify_video_player.py）
  0.3 补充 E2E 测试脚本

阶段 1：P0 第一梯队（用户价值 100，低成本，无依赖）
  1.1 DEPS-B-01 markwon 扩展（0.5 天）
  1.2 THEME-B-01 纸墨风格（1 天）
  1.3 THEME-B-02 字体撞色检测（1 天）

阶段 2：P0 RSS 主线（依赖链串行）
  2.1 RSS-B-01 + RSS-B-05 合并实施（1-2 天，含基类选择决策）
  2.2 RSS-E-06 cacheFirst 默认值（0.5 天，仅需 WebView 部分）
  2.3 RSS-B-02 SourceSelectDialog（2 天）
  2.4 RSS-B-03 SearchBookMergeUtils（2 天）

阶段 3：P0 EPUB 加速（共用 EpubFile.kt 串行）
  3.1 EPUB-B-01 spine 优先索引（0.5 天）
  3.2 EPUB-B-02 资源过滤+标题归一化（1 天，依赖 3.1 同文件串行）

阶段 4：P0 VIDEO 增强（关键路径）
  4.1 VIDEO-B-01 VideoBookPreloader（1 天）
  4.2 VIDEO-B-02 章节链接缓存（中，依赖 4.1）
  4.3 VIDEO-E-01 ReadRecentBook 写入（中-高，需新建表+Migration）
  4.4 VIDEO-E-02 ChoiceSpeedDialog 增强（0.5 天）
```

#### 6.1.3 P1 推荐实施顺序

参照 design.md §6.2，但建议：
- 优先实施 BUILD-B-02（BUILD 模块关键路径起点）
- 优先实施 THEME-B-03（THEME 模块关键路径起点，被 3 项 P2 依赖）
- 优先实施 THEME-B-04（被 THEME-E-05 依赖）

#### 6.1.4 P2 推荐实施顺序

参照 design.md §6.3，但建议：
- UI 优化类 9 项放在 P2 最后 ✅（已采纳）
- DEPS-B-02 composeBom 升级在 P2 最后实施 ✅（已采纳）
- THEME-B-06 AppearanceKit 拆分为 3 子任务后实施

### 6.2 实施前准备

#### 6.2.1 文档修订（必做）

1. 修订 spec.md §1 版本号（v5.0 → v5.1）
2. 修订 spec.md §4.1 REQ-P0-001 基类描述（BaseSearchActivity → VMBaseActivity）
3. 修订 spec.md §4.1 REQ-P0-005 cacheFirst 描述（已是 true，仅需 WebView 部分）
4. 修订 spec.md §4.1 REQ-P0-013 ReadRecentBook 描述（"修改" → "新建实体+DAO+Migration"）
5. 修订 design.md §4.1-4.7 文件路径（EpubFile/RssFragment/VideoActivity/ChoiceSpeedDialog/Exo2MediaPlayer）
6. 修订 design.md §1.1 EpubFile.kt 行数（~700 → ~429）
7. 修订 spec.md §4.3 REQ-P2-002 sora-editor 描述（已引入，需评估剩余工作量）
8. 修订 spec.md §4.2 REQ-P1-016/017/018 优先级（用户价值低于 P1 下限，应降级 P2）
9. 补充 spec.md §4.1 每个 REQ 的"风险评估"字段
10. 补充 spec.md §5 S12-S15 四个场景（视频三件套 + 覆盖安装）

#### 6.2.2 源码事实验证（必做）

1. 验证 ThemeColorUtils.kt 是否存在（THEME-B-02 依赖）
2. 验证 AndroidColorUtils.calculateContrast 在本项目的可用性
3. 验证 ContentTextView/PageView 阅读界面入口路径
4. 验证 RssWebActivity / RssReadActivity WebView 入口
5. 验证 markwon-core 版本号

#### 6.2.3 测试脚本补充（必做）

1. 补充 RSS 搜索 E2E 测试脚本
2. 补充 EPUB 阅读 E2E 测试脚本
3. 补充主题撞色检测 E2E 测试脚本
4. 补充视频预加载 E2E 测试脚本

### 6.3 实施中监控

#### 6.3.1 性能监控

- 每项任务完成后测量性能指标（启动时间 / 内存 / FPS / 搜索响应 / 视频首帧）
- 对比基线，超 ADR-020 预算时优先保留高用户价值项

#### 6.3.2 文档同步监控

- 每项任务完成后立即更新 updateLog.md（基于 git diff 真实变更分析）
- 每阶段完成后更新 tasks.md + project_memory.md + forks-reference.md + INDEX.md

#### 6.3.3 问题清单监控

- 所有实施问题记录到 issues-found.md
- 严重问题（阻塞型）必须当场解决，不得积累

### 6.4 实施后验证

#### 6.4.1 P0 完成验证

- 14 项 P0 任务全部完成
- 真机验证通过（每项任务的"真机验证"子项）
- 性能基准对比通过（ADR-016/020）
- assets/updateLog.md 更新
- 调试日志已清理（Grep "android.util.Log.d|android.util.Log.e" 确认无残留）
- 问题清单记录到 issues-found.md
- 覆盖安装兼容性测试通过（VIDEO-E-01 / THEME-B-04 涉及 DB）

#### 6.4.2 P1/P2 完成验证

- 19/21 项任务全部完成
- 模块级集成测试通过（P1）/ 完整回归测试通过（P2）
- APK 体积增长 ≤5MB（P2 UI 优化类）

---

## 7. 发现的问题（按严重程度排序）

### 🔴 严重问题（实施前必须解决）

#### S1. ReadRecentBook 表不存在（REQ-P0-013 / VIDEO-E-01）

- **现状**：spec.md 说"修改 ReadRecentBook.kt"，design.md §4.2 文件清单也说"修改"
- **事实**：本项目 `app/src/main/java/io/legado/app/data/entities/` 无 ReadRecentBook.kt
- **影响**：实施时阻塞，实际需新建实体+DAO+Migration，工作量是 spec 描述的 3-5 倍
- **修复**：修订 spec.md REQ-P0-013 + tasks.md §1.13 扩展子任务 + 重新评估成本为"中-高"

#### S2. BaseSearchActivity 不存在（REQ-P0-001 / RSS-B-01）

- **现状**：spec.md 说"继承 BaseSearchActivity"，design.md ADR-007 同
- **事实**：本项目无 BaseSearchActivity，仅有 VMBaseActivity
- **影响**：实施时阻塞，需决策基类选择
- **修复**：修订 spec.md REQ-P0-001 + design.md ADR-007 改为"继承 VMBaseActivity"

#### S3. cacheFirst 默认值已是 true（REQ-P0-005 / RSS-E-06）

- **现状**：spec.md 说"RSS 列表页 cacheFirst 默认 true"作为验收标准
- **事实**：RssSource.kt:113 已是 `var cacheFirst: Boolean = true`
- **影响**：子任务 1.5.1 无工作量，验收标准"自然完成"
- **修复**：修订 tasks.md §1.5.1 为"验证已存在的默认值"；spec.md REQ-P0-005 验收标准聚焦 WebView 部分

#### S4. 文件路径系统性错误（多处）

- **现状**：design.md §4 文件清单多处路径错误
- **事实**：
  - EpubFile.kt：`help/book/` → 实际 `model/localBook/`
  - RssFragment.kt：`ui/rss/` → 实际 `ui/main/rss/`
  - VideoActivity.kt：本项目无此文件，实际是 `ui/video/VideoPlayerActivity.kt`
  - ChoiceSpeedDialog.kt：`ui/rss/video/` → 实际 `help/gsyVideo/`
  - Exo2MediaPlayer.kt：`ui/rss/video/` → 实际 `help/gsyVideo/`
  - `ui/rss/video/` 目录在本项目不存在
- **影响**：实施时定位文件困难，可能误创建错误目录
- **修复**：全面修订 design.md §4.1-4.7 文件路径

#### S5. sora-editor 已引入（REQ-P2-002 / DEPS-B-03）

- **现状**：spec.md 说"P2 引入 sora-editor 代码编辑器"
- **事实**：app/build.gradle:355-358 已引入 soraEditor BOM+core+language.textmate
- **影响**：任务工作量评估错误，实际仅需"应用于书源规则编辑界面"
- **修复**：修订 spec.md REQ-P2-002 + tasks.md §3.1.2 描述

#### S6. P1 包含低于 P1 下限的任务（REQ-P1-016/017/018）

- **现状**：spec.md §4.2.2 将 BUILD-B-01/03/04 归为 P1
- **事实**：用户价值 2.8/3.0/3.0 低于 spec 自己定义的 P1 下限 3.8
- **影响**：spec 内部一致性问题；这些任务用户无感知，占用 P1 资源
- **修复**：降级 BUILD-B-01/03/04 为 P2（analysis-task-priority.md §3.20-3.22 已建议）

### 🟡 中等问题（实施前建议解决）

#### M1. spec.md 版本号混乱（v5.0 vs v5.1）

- spec.md §1 自称"基于 v5.0"，但 §2.1 引入 v5.1 调整
- 修复：统一为 v5.1

#### M2. spec 与 design 在并行策略上表述矛盾

- spec.md §3.2 备选 6 否决"子代理并行"
- design.md ADR-002 提出"4 组并行"
- design.md R22 承认"单 Agent 串行"
- 修复：统一表述为"4 组工作组织，主 Agent 串行执行"

#### M3. P0 任务粒度极不均衡

- 最小 5 行代码（RSS-B-05），最大需新建表+Migration（VIDEO-E-01）
- 修复：合并 RSS-B-05 到 RSS-B-01；扩展 VIDEO-E-01 子任务

#### M4. 高成本任务未拆分

- THEME-B-03（1428 行）、THEME-B-06（905 行）等未拆分
- 修复：参照 analysis-task-priority.md §6.2 拆分

#### M5. 功能重叠任务未合并

- THEME-B-03 + THEME-E-04
- THEME-B-05 + EPUB-E-02
- THEME-B-08 + THEME-E-03
- BUILD-B-06 + BUILD-B-08
- 修复：参照 analysis-task-priority.md §6.1 合并

#### M6. 所有 P0 Requirement 缺失"风险评估"字段

- spec.md §4.1 每个 REQ 无风险评估
- 修复：补充风险等级 + 关联 design.md 风险编号

#### M7. 性能基线建立未列入 P0 任务

- design.md R21 已识别，但 tasks.md §1 未列入
- 修复：增加任务 1.0 性能基线建立

#### M8. 国际化字符串未列入 P0 子任务

- design.md R24 已识别，但 tasks.md §1 未列入
- ADR-018 要求所有新增字符串入 strings.xml
- 修复：每个 P0 任务补充"strings.xml 化"子任务

#### M9. E2E 测试脚本覆盖不全

- P0 涉及的 RSS 搜索/EPUB 阅读/主题撞色检测等场景无对应 E2E 脚本
- 修复：P0 启动前补充对应脚本

#### M10. 遗漏 4 个关键场景

- S12 视频书最近阅读（VIDEO-E-01）
- S13 视频倍速切换（VIDEO-E-02）
- S14 连续看剧（VIDEO-B-02）
- S15 覆盖安装兼容性
- 修复：补充 spec.md §5 S12-S15

#### M11. VIDEO-E-01 与 ReadRecord 关系未明确

- 本项目已有 ReadRecord 表
- spec 未明确 ReadRecentBook 与 ReadRecord 是复用还是独立
- 修复：spec.md REQ-P0-013 补充说明

#### M12. EpubFile.kt 行数偏差

- spec/design 说 ~700 行
- 实际 429 行
- 修复：修订 design.md §1.1 + ADR-009 背景事实

### 🟢 轻微问题（实施中解决）

#### L1. spec.md §3.3 Drawbacks 第 4 项"与现有功能冲突"低估

- 实际比预期严重（多处事实偏差）
- 修复：补充说明"已在审查报告中识别多处冲突"

#### L2. SEARCH 结果去重逻辑冲突

- REQ-P0-001 说"按订阅源分组"
- REQ-P0-008 说"按书名+作者去重"
- 修复：spec.md 明确二者适用场景

#### L3. 部分子任务缺少明确验收标准

- 如 1.13.1"视频书播放时写入 ReadRecentBook 表"无量化标准
- 修复：补充"写入后查询最近阅读列表包含该视频书"

#### L4. S10/S11 综合场景描述过简

- 仅列步骤无详细描述
- 修复：补充详细步骤

#### L5. AndroidColorUtils 命名误导

- spec.md 写"AndroidColorUtils.calculateContrast"
- 实际是 androidx.core.graphics.ColorUtils
- 修复：修订为 ColorUtils.calculateContrast

---

## 8. 总体结论

### 8.1 spec.md + tasks.md 设计是否合理？

**整体评估**：🟡 **基本合理但需修订**

**合理性方面**：
- ✅ Intent 清晰，与 v5.0/v5.1 决策一致
- ✅ Scope 边界明确，54 项决策全覆盖
- ✅ Approach 三阶段策略合理
- ✅ 依赖关系正确（无循环，最长 3 层）
- ✅ 任务 ID 规范，与 spec.md 一致
- ✅ 风险清单 30 项全面（design.md）

**不合理方面**：
- 🔴 6 项严重事实偏差（S1-S6）会在实施第一天暴露为阻塞型问题
- 🟡 12 项中等问题（M1-M12）影响实施效率
- 🟢 5 项轻微问题（L1-L5）可在实施中解决

### 8.2 是否可以进入实施阶段？

**❌ 不可以立即进入实施阶段**

**必须先解决的阻塞型问题**（S1-S6）：
1. ReadRecentBook 表不存在 → 需修订 tasks.md §1.13 扩展子任务
2. BaseSearchActivity 不存在 → 需修订 spec.md REQ-P0-001 基类选择
3. cacheFirst 默认值已是 true → 需修订 tasks.md §1.5.1
4. 文件路径系统性错误 → 需修订 design.md §4.1-4.7
5. sora-editor 已引入 → 需修订 spec.md REQ-P2-002
6. P1 包含低于下限任务 → 需降级 BUILD-B-01/03/04 为 P2

**建议解决的中等问题**（M1-M12）：
- 至少解决 M3（任务粒度）、M6（风险评估）、M7（性能基线）、M9（E2E 脚本）4 项

### 8.3 需要解决的关键问题

#### 8.3.1 实施前必做（阻塞型）

1. 修订 spec.md / tasks.md / design.md 中的 6 项严重事实偏差（S1-S6）
2. 重新评估 VIDEO-E-01 实施成本（从"低"改为"中-高"）
3. 决策 RssSearchActivity 基类选择（推荐 VMBaseActivity）
4. 修订所有文件路径

#### 8.3.2 实施前建议做（效率型）

1. 合并 RSS-B-05 到 RSS-B-01（减少协调成本）
2. 拆分 THEME-B-03/THEME-B-06（降低单次风险）
3. 补充性能基线建立任务（design.md R21）
4. 补充 E2E 测试脚本
5. 补充每个 REQ 的风险评估字段
6. 补充 S12-S15 四个场景

#### 8.3.3 实施中监控

1. 性能基准对比（每项任务完成后）
2. 文档同步（每项任务完成后）
3. 问题清单（严重问题当场解决）

---

**审查报告完成**。本报告基于源文档交叉比对 + 项目源码事实验证，识别出 6 项严重问题、12 项中等问题、5 项轻微问题。**建议在修订 6 项严重事实偏差后再进入实施阶段**，以避免实施第一天就暴露阻塞型问题。

**关键发现速览**：
- spec.md 与 tasks.md 整体设计意图合理，但存在多处可在实施第一天暴露的事实偏差
- 最严重的 3 项偏差：ReadRecentBook 表不存在、BaseSearchActivity 不存在、cacheFirst 默认值已是 true
- 文件路径系统性错误涉及 6 个关键文件
- P0 任务粒度极不均衡（5 行代码 vs 新建表+Migration）
- 修订工作量预计 0.5-1 天，但可避免实施阶段数倍的返工成本
