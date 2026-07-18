# 交叉审查与决策优化报告

> **审查时间**：2026-07-18
> **审查对象**：forks-archive-borrow-implementation 项目 4 个设计文档
> **审查范围**：4 个设计文档（spec/tasks/design/README）+ 5 个对照源文档
> **审查方法**：逐项核对决策数量、任务ID、优先级、依赖链、ADR、文件变更、风险、阻塞点
> **输出原则**：源名称用代号（Archive 项目 / 本项目），域名用代号（站点A/B/C），URL 用路径模式

---

## 1. 审查概述

### 1.1 审查范围

| 文档类别 | 文档路径 | 用途 |
|---------|---------|------|
| 主文档1 | `spec.md` | Intent/Scope/Approach/Requirements/Scenarios |
| 主文档2 | `tasks.md` | 54 项任务清单（P0/P1/P2 三级分类） |
| 主文档3 | `design.md` | 12 ADR + 3 数据流图 + 33 文件变更 + 12 风险 |
| 主文档4 | `README.md` | 状态追踪 + 文档索引 + 决策汇总 |
| 对照源1 | `../forks-archive-comparison/borrow-decisions.md` | v2.0 借鉴决策表（118 项） |
| 对照源2 | `../forks-archive-comparison/final-adjustment.md` | v5.0 最终决策（54 借鉴/64 不借鉴/0 待评估） |
| 对照源3 | `../forks-archive-comparison/analysis-report.md` | v2.0 对比报告（181 项差异） |
| 对照源4 | `../forks-archive-comparison/user-value-reassessment.md` | 47 项借鉴点重评估 |
| 对照源5 | `../forks-archive-comparison/pending-evaluation-reassessment.md` | 36 项待评估重评估 |

### 1.2 总体结论

**整体评估**：4 个设计文档主体框架完整、决策演进链路清晰（v1.0→v5.0）、用户价值导向原则得到贯彻。但存在 **5 类严重问题** 和 **8 类中等问题** 需要修复后才能进入实施阶段：

| 严重程度 | 数量 | 主要类别 |
|---------|------|---------|
| 🔴 严重 | 5 | 模块分布数字错误 / P2 分类不一致 / 依赖关系错误 / 状态标注滞后 / 文件变更遗漏 |
| 🟡 中等 | 8 | 决策ID 命名重复 / ADR 覆盖不全 / 任务合并机会 / 阻塞点未识别 |
| 🟢 轻微 | 7 | 优先级微调 / 实施策略优化 / 文档表述精炼 |

**结论**：**不建议直接进入实施阶段**，需先修复 5 类严重问题（约 1-2 小时工作量），中等问题可在实施过程中逐步优化。

---

## 2. 跨文档一致性审查结果

### A1. 决策数量一致性

#### A1.1 总体决策数量对比

| 文档 | 借鉴总数 | P0 | P1 | P2 | 不借鉴 | 待评估 |
|------|---------|----|----|----|-------|--------|
| spec.md | 54 | 10 | 23 | 21 | 64 | 0 |
| tasks.md | 54 | 10 | 23 | 21 | 64 | 0 |
| design.md | 54 | 10 | 23 | 21 | 64 | 0 |
| README.md | 54 | 10 | 23 | 21 | 64 | 0 |
| final-adjustment.md（对照源） | 54 | 10 | 23 | 21 | 64 | 0 |

✅ **总体决策数量一致**：4 个主文档与对照源 final-adjustment.md 在总量上完全一致。

#### A1.2 模块分布数量对比（🔴 严重不一致）

| 模块 | spec.md §2.1 | design.md §9.3 | README.md §8.1 | final-adjustment.md §5.3 | 实际任务列表核对 | 一致性 |
|------|-------------|-----------------|-----------------|-------------------------|----------------|--------|
| RSS 模块 | **8** | 10 | 10 | 10 | 10 | 🔴 spec.md 错误 |
| EPUB 模块 | **10** | 11 | 11 | 11 | 11 | 🔴 spec.md 错误 |
| THEME 模块 | **12** | 13 | 13 | 13 | 13 | 🔴 spec.md 错误 |
| VIDEO 模块 | 5 | 5 | 5 | 5 | 5 | ✅ 一致 |
| DEPS 模块 | **9** | 7 | 7 | 7 | 7 | 🔴 spec.md 错误 |
| BUILD 模块 | **10** | 8 | 8 | 8 | 8 | 🔴 spec.md 错误 |
| 合计 | 54 | 54 | 54 | 54 | 54 | ✅ 合计一致 |

🔴 **严重问题 1**：`spec.md §2.1 模块分布表数字全部错误`（除 VIDEO 模块外）：
- RSS 模块写 8 项，实际 10 项（RSS-B-01/02/03/04/05/06 + RSS-E-03/04/05/06）
- EPUB 模块写 10 项，实际 11 项（EPUB-B-01/02/03/05/06/07/08 + EPUB-E-02/03/04/05/06）
- THEME 模块写 12 项，实际 13 项（THEME-B-01~08 + THEME-E-01~05）
- DEPS 模块写 9 项，实际 7 项（DEPS-B-01/02/03/04/05/06/08/09，但 BUILD-B-06/07/08 合并算 1 项任务对应 3 个决策ID，DEPS 实际 7 个决策ID）
- BUILD 模块写 10 项，实际 8 项（BUILD-B-01~08）

虽然合计 54 项一致（凑巧），但模块分布错误会导致资源分配与模块责任人误判，必须修复。

### A2. 任务ID 一致性

#### A2.1 P0 任务ID 一致性（10 项）

| # | spec.md | tasks.md | design.md | README.md | final-adjustment.md | 一致性 |
|---|---------|----------|-----------|-----------|---------------------|--------|
| 1 | RSS-B-01 | RSS-B-01 | RSS-B-01 | RSS-B-01 | RSS-B-01 | ✅ |
| 2 | DEPS-B-01 | DEPS-B-01 | DEPS-B-01 | DEPS-B-01 | DEPS-B-01 | ✅ |
| 3 | THEME-B-01 | THEME-B-01 | THEME-B-01 | THEME-B-01 | THEME-B-01 | ✅ |
| 4 | VIDEO-B-01 | VIDEO-B-01 | VIDEO-B-01 | VIDEO-B-01 | VIDEO-B-01 | ✅ |
| 5 | RSS-E-06 | RSS-E-06 | RSS-E-06 | RSS-E-06 | RSS-E-06 | ✅ |
| 6 | THEME-B-02 | THEME-B-02 | THEME-B-02 | THEME-B-02 | THEME-B-02 | ✅ |
| 7 | RSS-B-02 | RSS-B-02 | RSS-B-02 | RSS-B-02 | RSS-B-02 | ✅ |
| 8 | RSS-B-03 | RSS-B-03 | RSS-B-03 | RSS-B-03 | RSS-B-03 | ✅ |
| 9 | EPUB-B-01 | EPUB-B-01 | EPUB-B-01 | EPUB-B-01 | EPUB-B-01 | ✅ |
| 10 | EPUB-B-02 | EPUB-B-02 | EPUB-B-02 | EPUB-B-02 | EPUB-B-02 | ✅ |

✅ **P0 任务ID 完全一致**

#### A2.2 P1 任务ID 一致性（23 项）

逐项核对后，4 个文档 P1 23 项任务ID 完全一致，包括：
- 用户中高收益 17 项：RSS-B-05, VIDEO-B-02, VIDEO-E-01, VIDEO-E-02, RSS-E-05, THEME-E-05, EPUB-E-04, DEPS-B-04, EPUB-E-02, RSS-B-04, THEME-B-03, THEME-B-04, THEME-B-05, THEME-E-04, EPUB-B-03, EPUB-E-06, VIDEO-E-03
- 开发者侧优化 6 项：BUILD-B-02, BUILD-B-05, BUILD-B-01, BUILD-B-03, BUILD-B-04, DEPS-B-05

✅ **P1 任务ID 完全一致**

#### A2.3 P2 任务ID 一致性（21 项）

P2 21 项任务ID 在 4 个文档中完全一致，但**分类不一致**（详见 A3.3 节）。

#### A2.4 任务ID 命名规范一致性

✅ 命名规范一致：RSS-B-/VIDEO-B-/THEME-B-/EPUB-B-/DEPS-B-/BUILD-B- 为借鉴类，-E- 为原待评估升级类。

#### A2.5 潜在命名冲突（🟡 中等问题）

🟡 **中等问题 1**：**KitBinding 命名重复**
- `THEME-B-08`：KitBinding（P2 技术升级类）
- `THEME-E-03`：KitBinding 跨组件绑定（P2 UI 优化类）
- design.md 文件变更清单中二者共用 `KitBinding.kt` 一个文件
- **建议**：合并为 1 个任务，或明确区分为"机制实现"（THEME-B-08）和"UI 应用"（THEME-E-03）两个阶段

🟡 **中等问题 2**：**EPUB-B-04 vs EPUB-E-04 命名冲突**
- borrow-decisions.md v2.0 中：EPUB-B-04 相邻章节预加载（P1 借鉴）
- borrow-decisions.md v2.0 中：EPUB-E-04 相邻预加载策略（待评估）
- user-value-reassessment.md 中：EPUB-B-04 保留 P1
- pending-evaluation-reassessment.md 中：EPUB-E-04 升级为 P1
- final-adjustment.md v5.0 中：仅保留 EPUB-E-04（P1）
- spec/tasks/design/README 中：仅 EPUB-E-04
- **风险**：EPUB-B-04 是否被错误删除？还是与 EPUB-E-04 是同一功能的两个评估版本？
- **建议**：在 spec.md 附录中明确说明"EPUB-B-04 已合并至 EPUB-E-04"以避免后续疑惑

### A3. 优先级一致性

#### A3.1 P0 优先级一致性

✅ P0 10 项在 4 个文档中完全一致（详见 A2.1）。

#### A3.2 P1 优先级一致性

✅ P1 23 项在 4 个文档中完全一致。

#### A3.3 P2 优先级一致性（🔴 严重不一致）

🔴 **严重问题 2**：**P2 任务分类在 tasks.md 与 spec.md/design.md 之间不一致**

| 决策ID | spec.md 分类 | design.md §6.3 分类 | tasks.md 分类 | 一致性 |
|--------|-------------|---------------------|--------------|--------|
| THEME-B-06 (AppearanceKit) | 技术升级类 | 技术升级类 | **用户中价值类** | 🔴 tasks.md 错误 |
| THEME-B-08 (KitBinding) | 技术升级类 | 技术升级类 | **用户中价值类** | 🔴 tasks.md 错误 |
| EPUB-B-08 (双模式开关) | 用户中价值类 | 用户中价值类 | **技术升级类** | 🔴 tasks.md 错误 |
| BUILD-B-06/07/08 (android-fast) | 用户中价值类 | 用户中价值类 | **技术升级类** | 🔴 tasks.md 错误 |

**影响**：
1. 实施顺序混乱：tasks.md 把架构演进类（THEME-B-06/08）放在用户中价值类前实施，与 design.md 实施顺序冲突
2. 资源分配错误：技术升级类需要架构师资源，用户中价值类需要业务开发资源，分类错误导致资源错配
3. 验收标准混淆：技术升级类验收侧重兼容性，用户中价值类验收侧重用户感知

**修复建议**：以 spec.md 和 design.md 的分类为准，修正 tasks.md §3.1 和 §3.2 的分类。

### A4. 依赖链一致性

#### A4.1 关键依赖链对比

| 依赖关系 | tasks.md | design.md ADR-002 | spec.md | 一致性 |
|---------|----------|-------------------|---------|--------|
| RSS-B-05 → RSS-B-01 | ✅ 标注 | ✅ 标注 | 未明确 | ✅ |
| VIDEO-B-02 → VIDEO-B-01 | ✅ 标注 | ✅ 标注 | 未明确 | ✅ |
| THEME-E-04 → THEME-B-03 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| EPUB-B-02 → EPUB-B-01 | ✅ 标注 | ✅ 标注 | 未明确 | ✅ |
| EPUB-B-03 → EPUB-B-01 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| EPUB-E-04 → EPUB-B-01 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| EPUB-B-06 → EPUB-B-01 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| EPUB-B-08 → EPUB-B-01, EPUB-B-02 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| THEME-B-08 → THEME-B-06 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| THEME-E-03 → THEME-B-08 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| THEME-E-02 → THEME-B-03 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| THEME-B-07 → THEME-B-03 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| EPUB-E-03 → EPUB-B-06 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| EPUB-E-05 → EPUB-B-07 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| EPUB-B-07 → EPUB-E-06 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| RSS-E-03 → RSS-B-01 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| RSS-E-05 → RSS-B-03 | ✅ 标注 | 未明确 | 未明确 | ✅ |
| BUILD-B-06/07/08 → BUILD-B-02 | ✅ 标注 | 未明确 | 未明确 | ✅ |

#### A4.2 依赖关系错误（🔴 严重不一致）

🔴 **严重问题 3**：**design.md ADR-002 中 THEME-B-01 → THEME-B-02 的依赖关系错误**

design.md ADR-002 P0 串行化执行中描述：
```
THEME-B-01 (纸墨风格) → THEME-B-02 (字体撞色检测)
```

但 tasks.md 中 THEME-B-02 (1.6) 的依赖明确标注为：**"无"**

**分析**：
- THEME-B-01 是 PaperInkHelper.kt（基于 Paint.setShadowLayer 的纸墨风格）
- THEME-B-02 是 ThemeColorUtils.kt 中新增 sanitizeFontColorAgainstSurfaces 方法（基于 AndroidColorUtils.calculateContrast 的撞色检测）
- 两者功能独立，无代码依赖关系
- 两者修改不同文件（PaperInkHelper.kt vs ThemeColorUtils.kt），无文件冲突

**结论**：design.md ADR-002 的依赖描述是错误的，应修正为"THEME-B-01 和 THEME-B-02 相互独立，可并行实施"。

#### A4.3 依赖链长度分析

| 依赖链 | 长度 | 风险等级 |
|--------|------|---------|
| EPUB-B-01 → EPUB-B-06 → EPUB-E-03 | 3 | 🟡 中 |
| EPUB-B-01 → EPUB-B-02 → EPUB-B-08 | 3 | 🟡 中 |
| THEME-B-06 → THEME-B-08 → THEME-E-03 | 3 | 🟡 中 |
| EPUB-E-06 → EPUB-B-07 → EPUB-E-05 | 3 | 🟡 中 |
| RSS-B-01 → RSS-B-05 | 2 | 🟢 低 |
| RSS-B-01 → RSS-E-03 | 2 | 🟢 低 |
| VIDEO-B-01 → VIDEO-B-02 | 2 | 🟢 低 |
| BUILD-B-02 → BUILD-B-06/07/08 | 2 | 🟢 低 |

✅ **无超过 3 级的依赖链，无循环依赖**。

### A5. ADR 一致性

#### A5.1 ADR 数量与覆盖

design.md 中 12 个 ADR，4 个文档中 ADR 数量一致（仅在 design.md 中详细描述）。

| ADR | 标题 | spec.md 体现 | tasks.md 体现 | README.md 体现 | 一致性 |
|-----|------|-------------|--------------|----------------|--------|
| ADR-001 | 三阶段实施策略 | ✅ §3.1 | ✅ 三阶段分类 | ✅ §5 路线图 | ✅ |
| ADR-002 | P0 串行化执行 | ✅ §附录D | ✅ 依赖标注 | ✅ §6.7 | ✅（但依赖描述有误，见 A4.2） |
| ADR-003 | AI 模块全量否决 | ✅ §2.2 | ✅ 无 AI 任务 | ✅ §3.3 | ✅ |
| ADR-004 | UI 优化放最后 | ✅ §4.3.3 | ✅ §3.3 | ✅ §5.3 | ✅ |
| ADR-005 | 用户价值四维度 | ✅ §附录B | ✅ 用户价值列 | ✅ §1.2 | ✅ |
| ADR-006 | 锁定依赖不升级 | ✅ §附录D | ✅ 无升级任务 | ✅ §10.2 | ✅ |
| ADR-007 | RSS 搜索双轨方案 | ✅ §4.1 REQ-P0-001 | ✅ 1.1 | ✅ §4.1 发现3 | ✅ |
| ADR-008 | 视频模块保持架构 | ✅ §4.1 REQ-P0-004 | ✅ 1.4 | ✅ §4.1 发现2 | ✅ |
| ADR-009 | EPUB 引擎不替换 | ✅ §4.1 REQ-P0-009/010 | ✅ 1.9/1.10 | ✅ §4.1 发现1 | ✅ |
| ADR-010 | 主题云端同步 | ✅ §4.3.2 REQ-P2-006 | ✅ 3.2.2 | ✅ §4.1 发现4 | ✅ |
| ADR-011 | 文档同步与版本交付 | ✅ §附录D | ✅ §5 验收 | ✅ §9.2 | ✅ |
| ADR-012 | 真机测试强制流程 | ✅ §附录D | ✅ 真机验证子项 | ✅ §7.4 | ✅ |

✅ **12 个 ADR 在 4 个文档中均得到体现**。

#### A5.2 ADR 决策与最终决策一致性

✅ ADR-003 AI 模块全量否决与 final-adjustment.md §5.4 一致（11 项否决）
✅ ADR-004 UI 优化升级（3 项）与 final-adjustment.md §3.3 一致
✅ ADR-006 锁定 10 项依赖与 analysis-report.md §3.3 发现10 一致

---

## 3. 遗漏项识别

### B1. 决策遗漏

#### B1.1 v5.0 借鉴决策覆盖性

✅ **v5.0 的 54 项借鉴决策全部体现在 spec.md Requirements 中**（详见 A2 任务ID 一致性）。

#### B1.2 v5.0 不借鉴决策覆盖性

✅ spec.md §2.2 明确列出"不包含的内容"：
1. AI 模块 11 项（全量否决）
2. BUILD 配置差异 5 项
3. 其他 48 项不借鉴决策
4. 跨模块重构
5. 新功能开发

合计 64 项不借鉴决策已明确排除。

#### B1.3 v5.0 升级的 9 项（来自待评估）覆盖性

✅ 9 项升级为 P2 的决策全部在 tasks.md §3.3 中有对应任务：
- THEME-E-01, THEME-E-02, EPUB-E-03, EPUB-E-05, RSS-E-03, RSS-E-04（6 项来自待评估强制决策）
- DEPS-B-06, DEPS-B-08, THEME-E-03（3 项来自 UI 优化升级）

#### B1.4 v5.0 升级的 3 项 UI 优化覆盖性

✅ 3 项 UI 优化升级全部在 tasks.md §3.3 中有对应任务：
- DEPS-B-06 liquidglass（3.3.7）
- DEPS-B-08 lottie（3.3.8）
- THEME-E-03 KitBinding（3.3.9）

#### B1.5 潜在决策遗漏（🟡 中等问题）

🟡 **中等问题 3**：**EPUB-B-04 在 v5.0 中可能被遗漏**

- borrow-decisions.md v2.0：EPUB-B-04 相邻章节预加载（P1 借鉴）
- user-value-reassessment.md v3.0：EPUB-B-04 保留 P1
- borrow-decisions.md v2.0：EPUB-E-04 相邻预加载策略（待评估）
- pending-evaluation-reassessment.md v4.0：EPUB-E-04 升级为 P1
- final-adjustment.md v5.0：仅保留 EPUB-E-04（P1）
- spec/tasks/design/README：仅 EPUB-E-04

**判断**：EPUB-B-04 和 EPUB-E-04 描述高度相似（"相邻章节预加载" vs "相邻预加载策略"），可能是同一功能在 v2.0 中被同时归为借鉴和待评估两个状态。v5.0 最终统一为 EPUB-E-04。

**建议**：在 spec.md 附录中补充说明"EPUB-B-04 已合并至 EPUB-E-04"，避免后续审查时疑惑。

### B2. ADR 遗漏

#### B2.1 已有 ADR 覆盖范围

12 个 ADR 覆盖：实施策略 / 串行化 / AI 否决 / UI 优化 / 价值评估 / 依赖锁定 / RSS 搜索 / 视频架构 / EPUB 引擎 / 主题同步 / 文档同步 / 真机测试。

#### B2.2 缺失的 ADR（🟡 中等问题）

🟡 **中等问题 4**：**数据库迁移决策缺乏 ADR**

- design.md 文件变更清单 §4.2 第 5 项明确标注："`ReadRecentBook.kt` | 修改 | 视频书写入最近阅读（P1，需评估数据库迁移）"
- design.md §9.5 实施约束第 5 项："如涉及 DB 变更必须先评估迁移安全（database-migration-safety.md），如 VIDEO-E-01 ReadRecentBook 写入"
- 但没有专门的 ADR 说明数据库迁移策略

**建议新增 ADR-013**：数据库迁移安全策略
- Context：VIDEO-E-01 涉及 ReadRecentBook 表写入，可能需要数据库 version 升级
- Decision：遵守 database-migration-safety.md 规范，编写 Migration，评估向后兼容性
- Consequences：增加数据库版本号，需确保覆盖安装不丢数据

🟡 **中等问题 5**：**网络层兼容性决策缺乏 ADR**

- RSS-B-01 RssSearchActivity 涉及多源并发搜索（图 1 数据流），可能触发网络层限流
- RSS-B-04 pureSearch 参数涉及 URL 解析逻辑变更
- 但没有专门的 ADR 说明网络层兼容性策略

**建议新增 ADR-014**：网络层兼容性与限流策略
- Context：RSS 多源并发搜索可能触发站点限流，pureSearch 参数改变 URL 解析逻辑
- Decision：复用本项目已有 Semaphore 限流（最大并发 5-10），单源超时 3s，pureSearch 参数向后兼容
- Consequences：避免站点封禁，保证现有 RSS 源兼容性

🟡 **中等问题 6**：**协程调度策略决策缺乏 ADR**

- 项目规范要求"协程用自定义 Coroutine.async{}...onError{}.onSuccess{} 链式封装"
- 多个任务（RSS-B-01, VIDEO-B-01, EPUB-E-04 等）涉及协程使用
- 但没有专门的 ADR 统一说明协程调度策略

**建议新增 ADR-015**：协程调度与错误处理统一策略
- Context：54 项任务中多个涉及异步操作，需统一协程使用规范
- Decision：所有异步操作使用 Coroutine.async{}...onError{}.onSuccess{} 链式封装，异常用 Coroutine.onError，禁止 CoroutineExceptionHandler
- Consequences：代码风格统一，异常处理一致

🟡 **中等问题 7**：**性能基准测试决策缺乏 ADR**

- spec.md 验收标准中多处提及性能指标（如 RSS 搜索 < 3s、视频首帧下降 ≥ 30%、EPUB 首章加载 < 1s、FPS ≥ 50）
- 但没有专门的 ADR 说明性能基准测试方法学

**建议新增 ADR-016**：性能基准测试与回归保护
- Context：P0/P1/P2 验收均涉及性能指标，需建立可重复测量的基准
- Decision：每项性能相关任务建立基线测量→改造后测量→对比报告的三步流程，使用 swipe_test_log.py 等脚本
- Consequences：性能指标可验证，避免回归

### B3. 文件变更遗漏

#### B3.1 文件变更覆盖性核对（🔴 严重不一致）

逐项核对 54 项任务在 design.md §4 文件变更清单中的体现：

**P0 任务（10 项）文件变更覆盖**：

| 任务 | 文件变更 | 覆盖状态 |
|------|---------|---------|
| RSS-B-01 | RssSearchActivity.kt + RssSearchViewModel.kt + RssSearchAdapter.kt + RssFragment.kt | ✅ |
| DEPS-B-01 | app/build.gradle | ✅ |
| THEME-B-01 | PaperInkHelper.kt | ✅ |
| VIDEO-B-01 | VideoBookPreloader.kt + VideoActivity.kt | ✅ |
| RSS-E-06 | RssSource.kt（但 spec.md 还提到 "WebView cacheFirst 默认 true"，design.md 未列出 WebView 相关文件） | 🟡 部分 |
| THEME-B-02 | ThemeColorUtils.kt | ✅ |
| RSS-B-02 | SourceSelectDialog.kt | ✅ |
| RSS-B-03 | SearchBookMergeUtils.kt | ✅ |
| EPUB-B-01 | EpubFile.kt | ✅ |
| EPUB-B-02 | EpubFile.kt | ✅ |

🟡 **RSS-E-06 文件变更不完整**：spec.md 验收标准要求"WebView cacheFirst 默认 true"，但 design.md 文件变更清单仅列出 RssSource.kt，未列出 WebView 相关文件（如 RssActivity.kt 或 WebReadActivity.kt）。

**P1 任务（23 项）文件变更覆盖**：

| 任务 | 文件变更覆盖状态 |
|------|----------------|
| RSS-B-05 | ✅ RssFragment.kt |
| VIDEO-B-02 | ✅ VideoActivity.kt |
| VIDEO-E-01 | ✅ ReadRecentBook.kt |
| VIDEO-E-02 | ✅ ChoiceSpeedDialog.kt |
| RSS-E-05 | ✅ SearchBookPreviewOverlay.kt + SearchActivity.kt |
| THEME-E-05 | 🔴 **遗漏**（主题预览能力无对应文件） |
| EPUB-E-04 | ✅ EpubFile.kt |
| DEPS-B-04 | ✅ app/build.gradle |
| EPUB-E-02 | 🔴 **遗漏**（EPUB 字体内嵌无对应文件） |
| RSS-B-04 | 🔴 **遗漏**（pureSearch 参数无对应文件） |
| THEME-B-03 | ✅ ThemePackageManager.kt |
| THEME-B-04 | ✅ ThemeConfig.kt |
| THEME-B-05 | ✅ ThemeFontHelper.kt |
| THEME-E-04 | ✅ ThemePackageManager.kt |
| EPUB-B-03 | ✅ EpubFile.kt |
| EPUB-E-06 | ✅ EpubTextSelector.kt |
| VIDEO-E-03 | ✅ Exo2MediaPlayer.kt |
| BUILD-B-01/02/03/04/05 | ✅ .github/workflows/ + app/build.gradle |
| DEPS-B-05 | ✅ app/build.gradle |

**P2 任务（21 项）文件变更覆盖**：

| 任务 | 文件变更覆盖状态 |
|------|----------------|
| DEPS-B-02 | ✅ app/build.gradle |
| DEPS-B-03 | ✅ app/build.gradle |
| DEPS-B-09 | ✅ app/build.gradle |
| THEME-B-06 | ✅ AppearanceKitManager.kt |
| THEME-B-08 | ✅ KitBinding.kt |
| THEME-B-07 | ✅ ThemeCloudSyncHelper.kt |
| EPUB-B-05 | ✅ EpubAnnotationHelper.kt |
| EPUB-B-06 | 🔴 **遗漏**（分页缓存架构无对应文件） |
| EPUB-B-07 | 🟡 部分覆盖（与 EPUB-E-06 共用 EpubTextSelector.kt，但错误回退机制无对应文件） |
| EPUB-B-08 | 🔴 **遗漏**（双模式开关无对应文件） |
| RSS-B-06 | ✅ ExploreModernListScreen.kt |
| BUILD-B-06/07/08 | ✅ .github/workflows/ |
| THEME-E-01 | 🔴 **遗漏**（5 种 RED 格式兼容无对应文件） |
| THEME-E-02 | 🔴 **遗漏**（主题包目录化结构无对应文件） |
| EPUB-E-03 | 🔴 **遗漏**（分页缓存架构无对应文件，与 EPUB-B-06 重复） |
| EPUB-E-05 | 🔴 **遗漏**（错误回退机制无对应文件，与 EPUB-B-07 重复） |
| RSS-E-03 | ✅ RssFragment.kt |
| RSS-E-04 | ✅ view_flexbox_tab.xml |
| DEPS-B-06 | ✅ LiquidGlassHelper.kt |
| DEPS-B-08 | ✅ lottie_loading.json |
| THEME-E-03 | ✅ KitBinding.kt |

🔴 **严重问题 4**：**文件变更清单遗漏至少 9 项任务的文件变更**：

| # | 任务ID | 任务描述 | 遗漏文件（建议） |
|---|--------|---------|----------------|
| 1 | THEME-E-05 | 主题预览能力 | ThemePreviewHelper.kt（新增） |
| 2 | EPUB-E-02 | EPUB 字体内嵌 | EpubFontHelper.kt（新增） |
| 3 | RSS-B-04 | pureSearch 参数 | RssSearchViewModel.kt（修改，已存在但未标注） |
| 4 | EPUB-B-06 | 分页缓存架构 | EpubPageCacheHelper.kt（新增） |
| 5 | EPUB-B-08 | 双模式开关 | EpubFile.kt（修改，已存在但未标注 useExperimentalEpubCore 开关） |
| 6 | THEME-E-01 | 5 种 RED 格式兼容 | RedThemeParser.kt（新增） |
| 7 | THEME-E-02 | 主题包目录化结构 | ThemePackageManager.kt（修改，已存在但未标注目录化改造） |
| 8 | EPUB-E-03 | 分页缓存架构 | 与 EPUB-B-06 共用文件，但 design.md 未说明 |
| 9 | EPUB-E-05 | 错误回退机制 | EpubErrorFallbackHelper.kt（新增） |

**修复建议**：在 design.md §4 文件变更清单中补充这 9 项任务的文件变更。

#### B3.2 资源文件变更遗漏

🟡 **中等问题 8**：**资源文件（drawable/layout/values）变更未充分体现**

- design.md §4.5 列出 `view_flexbox_tab.xml`（RSS-E-04 FlexboxLayout 标签栏）
- design.md §4.6 列出 `lottie_loading.json`（DEPS-B-08 lottie 动画）
- 但以下资源文件变更未体现：
  - THEME-B-01 纸墨风格可能涉及阅读设置界面布局修改（添加开关）
  - RSS-B-01 RssSearchActivity 可能涉及搜索结果布局 XML
  - RSS-B-02 SourceSelectDialog 可能涉及 Dialog 布局 XML
  - THEME-E-05 主题预览可能涉及预览布局 XML
  - DEPS-B-06 liquidglass 可能涉及主题样式资源

**修复建议**：在 design.md §4 补充"资源文件变更子清单"。

### B4. 风险遗漏

#### B4.1 已识别风险（12 项）

design.md §5.1 列出 12 项风险，覆盖：工期/架构/体积/性能/数据/依赖/质量/文档/EPUB实体/SPLIT_TAG/视觉/构建。

#### B4.2 遗漏的风险（🟡 中等问题）

🟡 **遗漏风险 1**：**数据库迁移风险**
- VIDEO-E-01 涉及 ReadRecentBook 表写入，可能需要数据库 version 升级
- 若处理不当可能导致覆盖安装丢数据
- **建议补充**：在 design.md §5.1 风险清单中新增"数据库迁移风险"（影响：高，概率：低）

🟡 **遗漏风险 2**：**网络层兼容性风险**
- RSS-B-01 多源并发搜索可能触发站点限流
- RSS-B-04 pureSearch 参数变更可能影响现有 RSS 源兼容性
- **建议补充**：在 design.md §5.1 风险清单中新增"网络层兼容性风险"（影响：中，概率：中）

🟡 **遗漏风险 3**：**协程调度冲突风险**
- VideoBookPreloader 接入 ReadBook 状态机可能与现有协程调度冲突
- 多个 P0 任务（VIDEO-B-01, EPUB-E-04 等）涉及协程使用，若不规范统一可能导致内存泄漏
- **建议补充**：在 design.md §5.1 风险清单中新增"协程调度冲突风险"（影响：中，概率：中）

🟡 **遗漏风险 4**：**内存泄漏风险**
- VideoBookPreloader 单例缓存目录数据，若未及时释放可能导致内存泄漏
- chapterLinkCache（VIDEO-B-02）TTL 30 分钟，若清理不及时可能内存累积
- **建议补充**：在 design.md §5.1 风险清单中新增"内存泄漏风险"（影响：中，概率：中）

🟡 **遗漏风险 5**：**ANR 风险**
- RSS 搜索响应时间要求 < 3s，若多源并发搜索在主线程同步等待可能触发 ANR
- EPUB 章节加载若在主线程解析大型 EPUB 文件可能触发 ANR
- **建议补充**：在 design.md §5.1 风险清单中新增"ANR 风险"（影响：高，概率：低）

🟡 **遗漏风险 6**：**国际化缺失风险**
- 新增 RssSearchActivity、SourceSelectDialog 等界面可能包含硬编码中文文案
- 若项目支持多语言，需同步更新 strings.xml
- **建议补充**：在 design.md §5.1 风险清单中新增"国际化缺失风险"（影响：低，概率：中）

🟡 **遗漏风险 7**：**性能回退风险**
- composeBom 升级（DEPS-B-02）可能引入 Compose API 兼容性问题导致性能回退
- Glide ksp 迁移（DEPS-B-09）可能引入图片加载性能回退
- **建议补充**：在 design.md §5.1 风险清单中新增"性能回退风险"（影响：中，概率：中）

🟡 **遗漏风险 8**：**真机测试覆盖不足风险**
- 54 项任务中部分任务（如 THEME-E-05 主题预览、EPUB-E-06 文本选择器）的验收标准模糊
- 现有 ai_tests/scripts/ 脚本可能未覆盖所有新增功能
- **建议补充**：在 design.md §5.1 风险清单中新增"真机测试覆盖不足风险"（影响：高，概率：中）

---

## 4. 阻塞点识别与避免方案

### C1. 技术阻塞点

#### C1.1 VideoBookPreloader 集成阻塞

**阻塞点**：VIDEO-B-01 VideoBookPreloader 需要接入 ReadBook 状态机（design.md 图 2），但 design.md 未详细说明接入点。

**影响**：若 ReadBook 状态机理解不足，可能导致预加载时机错误，反而影响搜索结果页性能。

**避免方案**：
1. 实施前先绘制 ReadBook 状态机时序图，明确预加载触发点
2. 在搜索结果页 onBindViewHolder 时触发预加载（而非 onCreate）
3. 使用 Coroutine.async 异步预加载，设置 500ms 超时保护
4. 真机测试预加载不阻塞搜索结果页渲染（FPS ≥ 50）

#### C1.2 主题包云端同步依赖外部 WebDAV 服务

**阻塞点**：THEME-B-07 主题包云端同步（P2）需要 WebDAV 服务，design.md 图 3 提到 WebDAV/云端上传，但未说明：
- 是否复用本项目现有 WebDAV 能力？
- 是否需要用户新增 WebDAV 配置？
- 冲突合并策略是否已实现？

**影响**：若需新开发 WebDAV 客户端，工作量可能超预期。

**避免方案**：
1. 实施前先调研本项目现有 WebDAV 能力（如 AppConfig 中是否已有 WebDAV 配置）
2. 复用现有 WebDAV 客户端，避免重复开发
3. 用户配置 WebDAV 是 P2 阶段，可在 P1 阶段提前调研

#### C1.3 Android API 级别依赖

**阻塞点**：部分任务可能依赖特定 Android API 级别：
- THEME-B-01 纸墨风格使用 Paint.setShadowLayer（API 1+，无问题）
- THEME-B-02 字体撞色检测使用 AndroidColorUtils.calculateContrast（需确认 API 级别）
- DEPS-B-06 liquidglass 液态玻璃效果（需确认 minSdk 兼容性）

**影响**：若依赖 API 24+ 而 minSdk 23，可能导致低版本设备崩溃。

**避免方案**：
1. 实施前检查每个新增 API 的 minSdk 要求
2. 使用 @RequiresApi 注解 + 运行时版本判断
3. 真机测试覆盖 Android 6.0（API 23）设备

### C2. 资源阻塞点

#### C2.1 大代码量任务（>500 行）

| 任务 | 预计代码量 | 风险等级 |
|------|----------|---------|
| THEME-B-03 主题包 ZIP 导入导出 | 基于 Archive 1428 行实现，可裁剪 | 🟡 中 |
| THEME-B-06 AppearanceKit 套件架构 | 基于 Archive 905 行实现，可裁剪 | 🟡 中 |
| EPUB-B-06 分页缓存架构 | 高（架构重构） | 🔴 高 |
| RSS-B-06 ExploreModernListScreen Compose | 高（Compose 重写） | 🔴 高 |
| DEPS-B-03 sora-editor 代码编辑器 | 中（依赖引入 + 适配） | 🟡 中 |

**避免方案**：
1. 大代码量任务拆分为多个子任务（每个子任务 ≤ 500 行）
2. 优先借鉴 Archive 已验证实现，避免从零开发
3. 每个子任务独立真机测试

#### C2.2 新增依赖任务

| 任务 | 新增依赖 | 包体积影响 |
|------|---------|----------|
| DEPS-B-04 | reorderable 3.1.0 | 低 |
| DEPS-B-05 | lazycolumnscrollbar 2.2.0 | 低 |
| DEPS-B-06 | liquidglass 1.0.3 | +1-2MB |
| DEPS-B-08 | lottie 6.6.6 | +2-3MB |
| DEPS-B-03 | soraEditor BOM + core + language.textmate | 中 |

**避免方案**：
1. UI 优化类依赖（liquidglass/lottie）放在 P2 最后实施
2. 分阶段引入依赖，每阶段测量 APK 体积
3. APK 体积增长上限 5MB（UI 优化类合计）

#### C2.3 架构重构任务

| 任务 | 重构范围 | 风险等级 |
|------|---------|---------|
| THEME-B-06 AppearanceKit 套件架构 | 主题管理架构重构 | 🔴 高 |
| EPUB-B-06 分页缓存架构 | EPUB 渲染架构重构 | 🔴 高 |
| EPUB-B-08 双模式开关 | EPUB 渲染架构双轨化 | 🔴 高 |
| DEPS-B-09 Glide ksp 迁移 | 构建系统迁移 | 🟡 中 |

**避免方案**：
1. 架构重构任务必须先编写设计文档（子 spec）
2. 保留回退方案（如 EPUB-B-08 双模式开关保留原 EpubFile 入口）
3. 分阶段迁移，每阶段真机验证

### C3. 依赖阻塞点

#### C3.1 依赖链过长任务

✅ **无超过 3 级的依赖链**（详见 A4.3）。

#### C3.2 P2 任务依赖 P0/P1 任务

| P2 任务 | 依赖的 P0/P1 任务 | 阻塞风险 |
|--------|------------------|---------|
| EPUB-E-03 (P2) | EPUB-B-06 (P2) → EPUB-B-01 (P0) | 🟡 中（P2 依赖 P2 依赖 P0） |
| EPUB-E-05 (P2) | EPUB-B-07 (P2) → EPUB-E-06 (P1) | 🟡 中（P2 依赖 P2 依赖 P1） |
| THEME-E-03 (P2) | THEME-B-08 (P2) → THEME-B-06 (P2) | 🟡 中（P2 依赖 P2 依赖 P2） |
| BUILD-B-06/07/08 (P2) | BUILD-B-02 (P1) | 🟢 低 |
| RSS-E-03 (P2) | RSS-B-01 (P0) | 🟢 低 |

**避免方案**：
1. P0/P1 任务按计划完成后，再启动依赖它们的 P2 任务
2. P2 任务实施前先确认依赖的 P0/P1 任务已完成
3. 若 P0/P1 任务延期，相应 P2 任务应顺延

---

## 5. 决策优化建议

### D1. 优先级调整建议

#### D1.1 可升级为 P0 的 P1 项（🟢 轻微优化）

| 任务 | 当前优先级 | 用户价值 | 实施成本 | 建议优先级 | 理由 |
|------|----------|---------|---------|----------|------|
| THEME-E-05 主题预览能力 | P1 | 4.3 | 中 | 可考虑 P0 | 用户选主题前可预览，直接提升体验，与 THEME-B-01/02 同模块可协同实施 |
| VIDEO-B-02 章节链接缓存+下一集预加载 | P1 | 4.8 | 中 | 保持 P1 | 虽用户价值 4.8，但依赖 VIDEO-B-01（P0），建议作为 VIDEO-B-01 的连续工作流 |

**说明**：
- THEME-E-05 升级 P0 的理由：用户价值 4.3，与 THEME-B-01/02（P0）同模块，可共用主题管理入口，增量成本低
- 但若 P0 已锁定 10 项，建议保持 P1，避免 P0 范围蔓延

#### D1.2 可升级为 P1 的 P2 项

| 任务 | 当前优先级 | 用户价值 | 建议优先级 | 理由 |
|------|----------|---------|----------|------|
| EPUB-B-07 错误回退+文本选择器 | P2 | 3.7 | 可考虑 P1 | EPUB 体验改善，与 EPUB-E-06（P1）功能重叠，可合并实施 |
| EPUB-E-05 错误回退机制 | P2 | 3.7 | 可考虑 P1 | 与 EPUB-B-07 是同一功能两个决策ID，合并后可升级 |

**说明**：
- EPUB-B-07 和 EPUB-E-05 内容重复（都是错误回退+文本选择器），建议合并为 1 项任务
- 合并后用户价值 3.7，实施成本中等，可升级为 P1

#### D1.3 可降级或拆分的 P0 项

✅ **P0 10 项均无需降级或拆分**：
- 所有 P0 项用户价值 ≥ 4.5
- 所有 P0 项实施成本为低或中
- 所有 P0 项100% 聚焦用户核心场景

#### D1.4 可并行实施的 P0 项（🟢 轻微优化）

design.md ADR-002 采用 P0 串行化执行，但实际上以下 P0 任务无依赖关系且修改不同文件，可并行实施：

| 可并行组 | 任务 | 修改文件 | 并行安全性 |
|---------|------|---------|----------|
| 组1 | DEPS-B-01 (app/build.gradle) + THEME-B-01 (PaperInkHelper.kt) | 不同文件 | ✅ 可并行 |
| 组2 | RSS-E-06 (RssSource.kt) + EPUB-B-01 (EpubFile.kt) | 不同文件 | ✅ 可并行 |
| 组3 | RSS-B-02 (SourceSelectDialog.kt) + RSS-B-03 (SearchBookMergeUtils.kt) | 不同文件 | ✅ 可并行 |
| 组4 | VIDEO-B-01 (VideoBookPreloader.kt) + THEME-B-02 (ThemeColorUtils.kt) | 不同文件 | ✅ 可并行 |

**优化建议**：
- 修正 design.md ADR-002：将"P0 10 项任务按依赖链串行执行"改为"P0 10 项任务按文件隔离原则分组并行实施"
- 主 Agent 协调 4 个并行组，每组 2-3 项任务
- 预计 P0 工期可从 10-15 人天缩短至 6-10 人天

### D2. 新增 ADR 建议

#### D2.1 建议新增 ADR 清单

| ADR编号 | 标题 | 理由 | 优先级 |
|--------|------|------|--------|
| ADR-013 | 数据库迁移安全策略 | VIDEO-E-01 涉及 ReadRecentBook 表写入 | 🟡 中 |
| ADR-014 | 网络层兼容性与限流策略 | RSS 多源并发搜索可能触发站点限流 | 🟡 中 |
| ADR-015 | 协程调度与错误处理统一策略 | 54 项任务中多个涉及异步操作 | 🟡 中 |
| ADR-016 | 性能基准测试与回归保护 | P0/P1/P2 验收均涉及性能指标 | 🟡 中 |
| ADR-017 | 资源文件变更规范 | 多个任务涉及 drawable/layout/values 变更 | 🟢 轻微 |
| ADR-018 | 国际化文案规范 | 新增界面可能包含硬编码中文 | 🟢 轻微 |

#### D2.2 ADR-013 数据库迁移安全策略（建议草案）

- **Status**：Proposed
- **Context**：VIDEO-E-01 ReadRecentBook 写入涉及数据库变更，可能需要 version 升级。项目规范 database-migration-safety.md 要求"数据库 version 变更/@DatabaseView 修改/实体字段修改/新增 migration 任务"必须先评估迁移安全。
- **Decision**：
  1. VIDEO-E-01 实施前先评估 ReadRecentBook 表是否需要新增字段
  2. 若需新增字段，编写 Migration（如 Migration_N_to_N+1）
  3. 字段必须有默认值，确保向后兼容
  4. 覆盖安装测试：旧版本数据保留，新版本可正常读取
- **Consequences**：增加数据库版本号，需确保覆盖安装不丢数据
- **Alternatives**：
  - 备选 A：直接修改实体字段不加 Migration → 否决（违反 database-migration-safety.md）
  - 备选 B：使用 SharedPreferences 存储视频书记录 → 否决（与最近阅读统一管理冲突）

#### D2.3 ADR-014 网络层兼容性与限流策略（建议草案）

- **Status**：Proposed
- **Context**：RSS-B-01 RssSearchActivity 涉及多源并发搜索（图 1 数据流），可能触发站点限流。RSS-B-04 pureSearch 参数变更可能影响现有 RSS 源兼容性。
- **Decision**：
  1. RSS 多源并发搜索限制最大并发数 5-10（复用本项目已有 Semaphore 限流）
  2. 单源搜索超时 3s，超时后跳过该源
  3. pureSearch 参数向后兼容：默认 false，仅在 RssSource 显式配置时启用
  4. 借鉴 Archive 时保留本项目并行解析 + lastHost 回填 + F-P1-F 预连接优势
- **Consequences**：避免站点封禁，保证现有 RSS 源兼容性
- **Alternatives**：
  - 备选 A：无并发限制 → 否决（可能触发站点限流）
  - 备选 B：串行搜索 → 否决（搜索响应时间无法满足 < 3s）

### D3. 任务合并/拆分建议

#### D3.1 可合并的任务（🟡 中等问题）

| 合并组 | 任务 | 合并理由 | 合并后任务ID |
|--------|------|---------|------------|
| 合并组1 | EPUB-B-07 + EPUB-E-05 | 都是"错误回退+文本选择器"，内容重复 | EPUB-B-07（保留） |
| 合并组2 | EPUB-B-06 + EPUB-E-03 | 都是"分页缓存架构"，内容重复 | EPUB-B-06（保留） |
| 合并组3 | THEME-B-08 + THEME-E-03 | 都是 KitBinding 跨组件绑定，design.md 共用 KitBinding.kt | THEME-B-08（保留） |
| 合并组4 | EPUB-B-08 + EPUB-E-07 | EPUB-E-07 已否决，但 EPUB-B-08 双模式开关功能保留 | EPUB-B-08（保留） |

**合并后任务数**：54 - 4 = 50 项

**注意**：合并后需同步更新 spec.md / tasks.md / design.md / README.md 的任务数量。

#### D3.2 可拆分的任务

| 任务 | 拆分理由 | 拆分后 |
|------|---------|--------|
| THEME-B-03 主题包 ZIP 导入导出 | 基于 Archive 1428 行实现，工作量大 | 拆分为 THEME-B-03a（ZIP 导入）+ THEME-B-03b（ZIP 导出） |
| THEME-B-06 AppearanceKit 套件架构 | 基于 Archive 905 行实现，架构重构 | 拆分为 THEME-B-06a（套件基础架构）+ THEME-B-06b（跨组件绑定） |
| EPUB-B-06 分页缓存架构 | 高成本架构重构 | 拆分为 EPUB-B-06a（缓存策略设计）+ EPUB-B-06b（缓存实现） |

### D4. 实施策略优化

#### D4.1 三阶段实施策略评估

✅ **三阶段策略总体合理**：P0/P1/P2 按用户价值与实施成本动态平衡，风险分散。

#### D4.2 P0 串行化策略优化（🟢 轻微优化）

**当前策略**（design.md ADR-002）：P0 10 项任务按依赖链串行执行。

**优化建议**：
- 修正 ADR-002 中错误的依赖描述（THEME-B-01 → THEME-B-02 实际无依赖）
- 改为"按文件隔离原则分组并行实施"（详见 D1.4）
- 主 Agent 协调 4 个并行组，每组 2-3 项任务

#### D4.3 P2 UI 优化策略评估

✅ **UI 优化放最后策略合理**：
- 9 项 UI 优化放在 P2 最后实施，降低包体积增长风险
- 集中回归测试便于发现问题
- APK 体积增长上限 5MB（UI 优化类合计）

#### D4.4 建议的实施顺序优化

**P0 优化顺序**（基于文件隔离原则）：

```
Week 1:
  ├─ 并行组 A: DEPS-B-01 (markwon 扩展) → EPUB-B-01 (spine 索引) → EPUB-B-02 (资源过滤)
  ├─ 并行组 B: THEME-B-01 (纸墨风格) + THEME-B-02 (撞色检测) [同模块串行]
  ├─ 并行组 C: RSS-E-06 (cacheFirst) → RSS-B-02 (SourceSelectDialog) → RSS-B-03 (SearchBookMerge)
  └─ 并行组 D: VIDEO-B-01 (VideoBookPreloader)

Week 2:
  └─ RSS-B-01 (RssSearchActivity) [独立大任务，单独 1-2 天]
```

**预计 P0 工期**：6-10 人天（vs 原 10-15 人天）

---

## 6. 用户价值再评估

### E1. P0 10 项用户价值评估

#### E1.1 逐项评估

| # | 决策ID | 用户直接感知 | 用户核心场景 | 实施成本vs收益 | 用户额外负担 | 综合评分 | 评估结论 |
|---|--------|------------|-------------|---------------|------------|---------|---------|
| 1 | RSS-B-01 | 5（搜索订阅内容） | 5（订阅核心） | 5（1 Activity+5 行） | 5（无配置） | **5.0** | ✅ 保持 P0 |
| 2 | DEPS-B-01 | 5（渲染更完整） | 5（订阅核心） | 5（仅添加依赖） | 5（无配置） | **5.0** | ✅ 保持 P0 |
| 3 | THEME-B-01 | 5（视觉提升） | 5（阅读核心） | 5（60 行代码） | 5（无配置） | **5.0** | ✅ 保持 P0 |
| 4 | VIDEO-B-01 | 5（播放更快） | 5（视频核心） | 5（90 行代码） | 5（无配置） | **5.0** | ✅ 保持 P0 |
| 5 | RSS-E-06 | 4（加载更快） | 5（RSS 核心） | 5（默认值调整） | 5（无配置） | **4.8** | ✅ 保持 P0 |
| 6 | THEME-B-02 | 4（避免配色错误） | 5（阅读核心） | 5（低成本） | 5（自动检测） | **4.8** | ✅ 保持 P0 |
| 7 | RSS-B-02 | 4（源管理简化） | 5（源管理核心） | 4（中等成本） | 5（无配置） | **4.5** | ✅ 保持 P0 |
| 8 | RSS-B-03 | 4（搜索结果统一） | 5（搜索核心） | 4（中等成本） | 5（无配置） | **4.5** | ✅ 保持 P0 |
| 9 | EPUB-B-01 | 4（EPUB 加载快） | 4（EPUB 次核心） | 5（低成本） | 5（无配置） | **4.5** | ✅ 保持 P0 |
| 10 | EPUB-B-02 | 4（EPUB 体验改善） | 4（EPUB 次核心） | 5（低成本） | 5（无配置） | **4.5** | ✅ 保持 P0 |

#### E1.2 P0 评估结论

✅ **P0 10 项用户价值评估全部通过**：
- 综合评分区间 4.5-5.0，符合 P0 标准（≥4.5）
- 100% 聚焦用户核心场景（订阅/阅读/视频/EPUB）
- 0 项需 API key 或用户额外配置
- 0 项是纯技术架构或开发者侧优化
- 无降级建议

### E2. 不借鉴项重新审视

#### E2.1 AI 模块 11 项否决合理性

✅ **否决合理**：
- 用户明确反馈"AI 模块，我都不建议加入到我的项目中去，因为收益太小了，还需要配置模型 api key"
- 本项目定位为"阅读器"，不是"AI 助手"
- AI 能力对用户核心场景（看书/订阅/视频）无直接帮助
- 需 API key 增加用户使用门槛
- 11 项否决（6 借鉴 + 5 待评估）符合用户价值导向原则

**保持否决**：AI 模块 11 项全部保持不借鉴。

#### E2.2 视觉特效 3 项否决合理性

✅ **否决已调整**：
- DEPS-B-06 liquidglass：v3.0 否决 → v5.0 升级为 P2（用户接受包体积增加）
- DEPS-B-08 lottie：v3.0 否决 → v5.0 升级为 P2（用户接受包体积增加）
- THEME-E-03 KitBinding：v3.0 否决 → v5.0 升级为 P2（UI 一致性）
- DEPS-B-07 miuix.android：保持否决（只对小米用户有价值，非通用）

**结论**：视觉特效 3 项否决已在 v5.0 中调整，用户反馈已充分体现在最终决策中。

#### E2.3 重复功能 20 项否决合理性

✅ **否决合理**：
- 视频相关 4 项：本项目视频模块已大幅领先（8167 行 vs 4189 行）
- RSS 并行解析 + lastHost 回填：本项目已有
- Compose 依赖完整性：本项目更完整
- minify=true 策略：本项目更优
- DiscoverySuite 套件（4 文件 130KB+）：体量过大与极简哲学冲突
- 等

**保持否决**：重复功能 20 项全部保持不借鉴。

#### E2.4 其他不借鉴项审视

| 类别 | 数量 | 审视结论 |
|------|------|---------|
| BUILD 配置差异 | 5 | ✅ 保持否决（用户无感知） |
| 体量过大 | 8 | ✅ 保持否决（与极简哲学冲突） |
| 性能难感知 | 5 | ✅ 保持否决（用户无直接感知） |
| 小众需求 | 3 | ✅ 保持否决（非核心场景） |
| 非通用 | 4 | ✅ 保持否决（只对部分用户有价值） |
| 已知 Bug | 4 | ✅ 保持否决（借鉴时需避免） |
| 技术架构 | 8 | ✅ 保持否决（用户无感知） |
| 其他 | 6 | ✅ 保持否决（重复或已否决） |

✅ **64 项不借鉴决策全部合理**，无需升级。

#### E2.5 用户价值再评估结论

✅ **v5.0 终版决策经再评估后保持稳定**：
- 54 项借鉴决策全部合理
- 64 项不借鉴决策全部合理
- 0 项需调整
- 用户价值导向原则得到贯彻

---

## 7. 综合修复清单（按优先级排序）

### 🔴 严重（必须修复才能进入实施）

- [ ] **修复1**：spec.md §2.1 模块分布数字错误
  - 影响文件：`spec.md`
  - 修复建议：RSS 8→10, EPUB 10→11, THEME 12→13, DEPS 9→7, BUILD 10→8
  - 工作量：5 分钟

- [ ] **修复2**：tasks.md P2 分类与 spec.md/design.md 不一致
  - 影响文件：`tasks.md` §3.1 和 §3.2
  - 修复建议：以 spec.md 和 design.md 分类为准，调整 THEME-B-06/08 归技术升级类，EPUB-B-08/BUILD-B-06/07/08 归用户中价值类
  - 工作量：10 分钟

- [ ] **修复3**：design.md ADR-002 中 THEME-B-01 → THEME-B-02 依赖关系错误
  - 影响文件：`design.md` ADR-002
  - 修复建议：删除"THEME-B-01 → THEME-B-02"依赖描述，改为"THEME-B-01 和 THEME-B-02 相互独立，可并行实施"
  - 工作量：5 分钟

- [ ] **修复4**：design.md 文件变更清单遗漏至少 9 项任务
  - 影响文件：`design.md` §4
  - 修复建议：补充 THEME-E-05, EPUB-E-02, RSS-B-04, EPUB-B-06, EPUB-B-08, THEME-E-01, THEME-E-02, EPUB-E-03, EPUB-E-05 的文件变更
  - 工作量：30 分钟

- [ ] **修复5**：README.md §2.1 中 design.md 状态标注滞后
  - 影响文件：`README.md` §2.1
  - 修复建议：将 design.md 状态从"🔄 创建中"改为"✅ 已完成"
  - 工作量：1 分钟

### 🟡 中等（建议修复）

- [ ] **修复6**：补充 ADR-013 数据库迁移安全策略
  - 影响文件：`design.md` §2
  - 修复建议：新增 ADR-013（详见 D2.2）
  - 工作量：15 分钟

- [ ] **修复7**：补充 ADR-014 网络层兼容性与限流策略
  - 影响文件：`design.md` §2
  - 修复建议：新增 ADR-014（详见 D2.3）
  - 工作量：15 分钟

- [ ] **修复8**：补充 ADR-015 协程调度与错误处理统一策略
  - 影响文件：`design.md` §2
  - 修复建议：新增 ADR-015
  - 工作量：15 分钟

- [ ] **修复9**：补充 ADR-016 性能基准测试与回归保护
  - 影响文件：`design.md` §2
  - 修复建议：新增 ADR-016
  - 工作量：15 分钟

- [ ] **修复10**：design.md §5.1 风险清单补充 8 项遗漏风险
  - 影响文件：`design.md` §5.1
  - 修复建议：补充数据库迁移/网络层兼容/协程调度/内存泄漏/ANR/国际化/性能回退/真机测试覆盖 8 项风险
  - 工作量：20 分钟

- [ ] **修复11**：EPUB-B-04 在 v5.0 中可能被遗漏
  - 影响文件：`spec.md` 附录
  - 修复建议：在 spec.md 附录中说明"EPUB-B-04 已合并至 EPUB-E-04"
  - 工作量：5 分钟

- [ ] **修复12**：KitBinding 命名重复（THEME-B-08 vs THEME-E-03）
  - 影响文件：`spec.md` / `tasks.md` / `design.md`
  - 修复建议：合并为 1 项任务，或明确区分为"机制实现"和"UI 应用"两个阶段
  - 工作量：15 分钟

- [ ] **修复13**：RSS-E-06 文件变更不完整
  - 影响文件：`design.md` §4.1
  - 修复建议：补充 WebView 相关文件变更（如 WebReadActivity.kt 或 RssActivity.kt）
  - 工作量：5 分钟

### 🟢 轻微（可选优化）

- [ ] **修复14**：P0 串行化策略优化
  - 影响文件：`design.md` ADR-002
  - 修复建议：改为"按文件隔离原则分组并行实施"（详见 D1.4）
  - 工作量：15 分钟

- [ ] **修复15**：任务合并优化
  - 影响文件：`spec.md` / `tasks.md` / `design.md` / `README.md`
  - 修复建议：合并 EPUB-B-07+EPUB-E-05, EPUB-B-06+EPUB-E-03, THEME-B-08+THEME-E-03
  - 工作量：30 分钟

- [ ] **修复16**：补充资源文件变更子清单
  - 影响文件：`design.md` §4
  - 修复建议：补充 drawable/layout/values 变更清单
  - 工作量：15 分钟

- [ ] **修复17**：大代码量任务拆分
  - 影响文件：`tasks.md`
  - 修复建议：THEME-B-03/B-06/EPUB-B-06 拆分为子任务
  - 工作量：20 分钟

- [ ] **修复18**：补充 ADR-017 资源文件变更规范
  - 影响文件：`design.md` §2
  - 修复建议：新增 ADR-017
  - 工作量：10 分钟

- [ ] **修复19**：补充 ADR-018 国际化文案规范
  - 影响文件：`design.md` §2
  - 修复建议：新增 ADR-018
  - 工作量：10 分钟

- [ ] **修复20**：优化 P0 实施顺序
  - 影响文件：`design.md` §6.1
  - 修复建议：改为 4 个并行组实施（详见 D4.4）
  - 工作量：15 分钟

---

## 8. 总体结论与建议

### 8.1 是否可以进入实施阶段？

**结论**：**不建议直接进入实施阶段**，需先修复 5 类严重问题（修复1-5），预计工作量约 50 分钟。

### 8.2 需要修复的严重问题数量

| 严重程度 | 数量 | 预计工作量 |
|---------|------|----------|
| 🔴 严重 | 5 | 50 分钟 |
| 🟡 中等 | 8 | 2 小时 |
| 🟢 轻微 | 7 | 2 小时 |
| **合计** | **20** | **约 5 小时** |

### 8.3 优化后的决策汇总

#### 8.3.1 决策数量（修复后）

| 决策类型 | 数量 | 备注 |
|---------|------|------|
| 借鉴（Borrow） | 54 | 保持不变 |
| 不借鉴（Skip） | 64 | 保持不变 |
| 待评估（Evaluate） | 0 | 保持不变 |

#### 8.3.2 模块分布（修复后）

| 模块 | P0 | P1 | P2 | 小计 |
|------|---|---|---|------|
| RSS 模块 | 4 | 3 | 3 | 10 |
| EPUB 模块 | 2 | 4 | 5 | 11 |
| THEME 模块 | 2 | 5 | 6 | 13 |
| VIDEO 模块 | 1 | 4 | 0 | 5 |
| DEPS 模块 | 1 | 2 | 4 | 7 |
| BUILD 模块 | 0 | 5 | 3 | 8 |
| **合计** | **10** | **23** | **21** | **54** |

#### 8.3.3 新增 ADR 清单（建议）

| ADR | 标题 | 优先级 |
|-----|------|--------|
| ADR-013 | 数据库迁移安全策略 | 🟡 中 |
| ADR-014 | 网络层兼容性与限流策略 | 🟡 中 |
| ADR-015 | 协程调度与错误处理统一策略 | 🟡 中 |
| ADR-016 | 性能基准测试与回归保护 | 🟡 中 |
| ADR-017 | 资源文件变更规范 | 🟢 轻微 |
| ADR-018 | 国际化文案规范 | 🟢 轻微 |

#### 8.3.4 实施策略优化（建议）

| 优化项 | 原策略 | 优化后策略 |
|--------|--------|----------|
| P0 实施 | 串行化 10-15 人天 | 分组并行 6-10 人天 |
| P2 分类 | tasks.md 与 spec.md 不一致 | 统一以 spec.md 分类为准 |
| 文件变更 | 遗漏 9 项 | 补充完整 |
| 风险清单 | 12 项 | 补充 8 项至 20 项 |
| ADR 数量 | 12 个 | 新增 6 个至 18 个 |

### 8.4 最终建议

1. **立即修复 5 类严重问题**（约 50 分钟），修复后可进入 P0 实施阶段
2. **P0 实施采用分组并行策略**（4 个并行组），预计工期 6-10 人天
3. **中等问题在 P0 实施过程中同步修复**，不阻塞 P0 启动
4. **轻微问题在 P1/P2 实施过程中逐步优化**
5. **P0 完成后进行阶段验收**，确认 P0 10 项真机测试通过后再启动 P1

### 8.5 审查完成声明

本审查报告基于 4 个设计文档 + 5 个对照源文档的逐项核对，覆盖：
- ✅ 跨文档一致性（A1-A5 共 5 大类）
- ✅ 遗漏项识别（B1-B4 共 4 大类）
- ✅ 阻塞点识别（C1-C3 共 3 大类）
- ✅ 决策优化建议（D1-D4 共 4 大类）
- ✅ 用户价值再评估（E1-E2 共 2 大类）
- ✅ 综合修复清单（20 项，按优先级排序）

**审查结论**：4 个设计文档主体框架完整，但存在 5 类严重问题需修复后才能进入实施阶段。修复后预计可顺利推进 P0/P1/P2 三阶段实施。

---

**审查报告完成**。共发现 20 项修复项（5 严重 / 8 中等 / 7 轻微），建议优先修复 5 类严重问题后进入 P0 实施阶段。
