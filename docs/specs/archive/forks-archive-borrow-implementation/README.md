# Forks Archive 借鉴实施 - 状态追踪

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> **项目代号**：forks-archive-borrow-implementation
> **创建时间**：2026-07-18
> **当前阶段**：OpenSpec 设计阶段 - 修复迭代中（检查点4 需调整反馈后，正在全量修复+优化）
> **决策版本**：v5.0 终版（54 借鉴 / 64 不借鉴 / 0 待评估）
> **实施范围**：54 项借鉴决策（P0: 14 / P1: 19 / P2: 21）
> **ADR 决策**：27 个（含拆分 ADR-010 为 010a/010b，合并 ADR-011/012 为 ADR-011，新增 ADR-019~027）
> **实施方式**：AI 执行，按依赖顺序实施（无工期估算）

---

## 1. 项目概述

### 1.1 项目目标

将 Archive 项目 54 项有用户价值的功能/优化点融合到本项目（阅读 Sigma / E 分支），按 P0/P1/P2 三级优先级分阶段实施，最大化用户感知收益，同时控制实施风险与改造成本。

### 1.2 评估方法论

- **forks-reference 五阶段对比流程**：准备 → 分类对比 → 差异识别 → 价值评估 → 借鉴决策
- **用户价值四维度评估**：用户直接感知 / 用户核心场景 / 实施成本 vs 收益 / 用户额外负担
- **三态决策表**：借鉴（Borrow）/ 不借鉴（Skip）/ 待评估（Evaluate）
- **收益/风险/复杂度三维评分**：每个决策项量化评估
- **子代理并行编排**：7 个子代理并行分析 7 个模块（单子代理 ≤12 文件）
- **中间文件防丢失**：每个子代理写入详细中间文件（500-800 行）

### 1.3 最终决策

| 决策类型 | 数量 | 占比 |
|---------|------|------|
| 借鉴（Borrow） | 54 | 45.8% |
| 不借鉴（Skip） | 64 | 54.2% |
| 待评估（Evaluate） | 0 | 0% |
| **合计** | **118** | **100%** |

**借鉴项按优先级分布**：

| 优先级 | 数量 | 实施窗口 |
|--------|------|---------|
| P0 立即启动 | 14 | AI 执行，按依赖顺序实施 |
| P1 季度规划 | 19 | AI 执行，按依赖顺序实施 |
| P2 年度规划 | 21 | AI 执行，按依赖顺序实施 |
| **合计** | **54** | - |

---

## 2. 文档索引

### 2.1 本项目文档（forks-archive-borrow-implementation/）

| 文档 | 状态 | 说明 |
|------|------|------|
| spec.md | ✅ 已完成 | Intent/Scope/Approach/Requirements(P0 14+P1 19+P2 21)/Scenarios(S1-S11) |
| tasks.md | ✅ 已完成 | 54 项实施任务清单，按 P0/P1/P2 三级分类 |
| design.md | ✅ 已完成 | ADR 决策 + 数据流图 + 文件变更清单 + 风险缓解 |
| README.md | ✅ 本文档 | 状态追踪 + 文档索引 + 决策汇总 |
| review-spec-tasks.md | ✅ 已完成 | spec.md + tasks.md 审查报告 |
| review-design-readme.md | ✅ 已完成 | design.md + README.md 审查报告 |
| review-cross-optimization.md | ✅ 已完成 | 交叉审查+决策优化报告 |
| review-design-rationality-spec-tasks.md | ✅ v2.2 新增 | 第三轮审查：spec.md + tasks.md 设计合理性审查（1194 行） |
| review-design-rationality-design.md | ✅ v2.2 新增 | 第三轮审查：design.md 设计合理性审查（1628 行） |
| review-implementation-simulation.md | ✅ v2.2 新增 | 第三轮审查：实施过程仿真模拟审查（2006 行） |

### 2.2 关联分析文档（forks-archive-comparison/）

| 文档 | 状态 | 说明 |
|------|------|------|
| README.md | ✅ 已完成 | 对比分析项目状态追踪 |
| spec.md | ✅ 已完成 | 对比分析 spec |
| design.md | ✅ 已完成 | 含 6 个 ADR Y-Statement |
| tasks.md | ✅ 已完成 | 对比分析任务清单 |
| analysis-report.md | ✅ v2.0 最终版 | 181 项差异 + Top 10 重大发现（516 行 9 章节） |
| borrow-decisions.md | ✅ v2.0 最终版 | 118 项借鉴决策表（385 行） |
| user-value-reassessment.md | ✅ 已完成 | 47 项借鉴点用户价值重评估 |
| pending-evaluation-reassessment.md | ✅ 已完成 | 36 项待评估重评估 |
| final-adjustment.md | ✅ 已完成 | v5.0 最终调整（8 项强制决策 + UI 优化升级） |
| intermediate/SA-1-theme.md | ✅ 已完成 | 主题模块深度分析（630 行） |
| intermediate/SA-2-epub.md | ✅ 已完成 | EPUB 模块深度分析（700 行） |
| intermediate/SA-3-ai-assistant.md | ✅ 已完成 | AI 助手模块深度分析（748 行） |
| intermediate/SA-4-rss-explore.md | ✅ 已完成 | RSS/发现页模块深度分析（774 行） |
| intermediate/SA-5-video.md | ✅ 已完成 | 视频播放模块深度分析（508 行） |
| intermediate/SA-6-build.md | ✅ 已完成 | 构建配置深度分析（786 行） |
| intermediate/SA-7-deps.md | ✅ 已完成 | 依赖深度分析（10 章节） |

---

## 3. v5.0 最终决策汇总

### 3.1 决策演进历程

| 版本 | 借鉴 | 不借鉴 | 待评估 | 关键变更 |
|------|------|--------|--------|---------|
| v1.0 初版 | 47 | 35 | 36 | 基于 181 项差异的初版决策 |
| v2.0 整合版 | 47 | 35 | 36 | 整合 7 个中间文件 |
| v3.0 用户价值重评估 | 47 | 35 | 36 | AI 模块 6 项否决 + 视觉特效 3 项否决 |
| v4.0 待评估强制决策 | 45 | 65 | 8 | 9 项升级借鉴（1 P0 + 8 P1）/ 19 项不借鉴 / 8 项保持 |
| **v5.0 终版** | **54** | **64** | **0** | 8 项待评估强制决策 + 3 项 UI 优化升级 |

### 3.2 v5.0 借鉴决策按优先级

#### P0（14 项 - 用户核心场景优先）

> v1.2 调整：原 P0 10 项 + 新增 4 项（RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02）+ 保留 THEME-B-02 = 14 项（与 spec.md/tasks.md/design.md 一致）

| # | 决策ID | 决策项 | 用户价值 | 实施成本 | 用户场景 |
|---|--------|--------|---------|---------|---------|
| 1 | RSS-B-01 | RssSearchActivity | 5.0 | 低 | 用户搜索订阅内容 |
| 2 | RSS-B-05 | RssFragment openRssSearch 入口 | 4.8 | 低 | RSS 搜索入口集成 |
| 3 | DEPS-B-01 | markwon 4.6.2 扩展 | 5.0 | 低 | 订阅文章渲染 |
| 4 | THEME-B-01 | 纸墨风格 | 5.0 | 低 | 阅读视觉体验 |
| 5 | THEME-B-02 | 字体撞色检测 | 4.8 | 低 | 避免配色错误 |
| 6 | VIDEO-B-01 | VideoBookPreloader | 5.0 | 低 | 视频播放加速 |
| 7 | RSS-E-06 | cacheFirst 默认值 | 4.8 | 低 | RSS 加载更快 |
| 8 | RSS-B-02 | SourceSelectDialog | 4.5 | 中 | 源管理简化 |
| 9 | RSS-B-03 | SearchBookMergeUtils | 4.5 | 中 | 搜索结果统一 |
| 10 | EPUB-B-01 | 章节资源索引 | 4.5 | 低 | EPUB 加载加速 |
| 11 | EPUB-B-02 | 资源过滤+标题归一化 | 4.5 | 低 | EPUB 阅读体验 |
| 12 | VIDEO-B-02 | 章节链接缓存+下一集预加载 | 4.8 | 中 | 视频连续看剧流畅 |
| 13 | VIDEO-E-01 | ReadRecentBook 写入 | 4.5 | 低 | 视频书最近阅读 |
| 14 | VIDEO-E-02 | ChoiceSpeedDialog 增强 | 4.5 | 低 | 视频倍速交互优化 |

#### P1（19 项 - 性能体验增强）

> v1.2 调整：原 P1 23 项 - 升级 P0 4 项（RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02）= 19 项（THEME-B-02 保留 P0）

**用户中高收益（13 项）**：RSS-E-05、THEME-E-05、EPUB-E-04、DEPS-B-04、EPUB-E-02、RSS-B-04、THEME-B-03/04/05、THEME-E-04、EPUB-B-03、EPUB-E-06、VIDEO-E-03

**开发者侧优化（6 项）**：BUILD-B-01/02/03/04/05、DEPS-B-05

#### P2（21 项 - UI 优化与扩展）

- **技术升级类（5 项）**：DEPS-B-02、DEPS-B-03、DEPS-B-09、THEME-B-06、THEME-B-08
- **用户中价值类（7 项）**：THEME-B-07、EPUB-B-05/06/07/08、RSS-B-06、BUILD-B-06/07/08
- **UI 优化类（9 项，放在最后）**：THEME-E-01/02/03、EPUB-E-03/05、RSS-E-03/04、DEPS-B-06/08

### 3.3 v5.0 不借鉴决策（64 项，5 大类）

| 类别 | 数量 | 说明 |
|------|------|------|
| AI 模块全量否决 | 11 | 用户反馈"AI 模块收益太小且需要 API key 配置" |
| BUILD 配置差异 | 5 | flavorDimensions / applicationIdSuffix 等 Archive 特定配置 |
| 视觉特效 | 3 | 过度装饰的动画效果 |
| 重复功能 | 20 | 本项目已有等效或更优实现 |
| 架构不兼容 | 25 | Archive 自研架构无法移植 |

### 3.4 v5.0 修复迭代补充（v1.2）

基于 3 份审查报告（review-spec-tasks.md / review-design-readme.md / review-cross-optimization.md）+ 2 份深度分析报告（analysis-task-priority.md / analysis-adr-decisions.md）的修复迭代补充：

| 补充项 | v1.0 原状态 | v1.1 修复后 | v1.2 修复后 |
|--------|--------|----------|----------|
| ADR 数量 | 12 个（ADR-001~012） | 18 个（新增 ADR-013~018） | **27 个**（拆分 ADR-010 为 010a/010b + 合并 ADR-011/012 为 ADR-011 + 新增 ADR-019~027） |
| P0 实施策略 | 串行化执行 | 分组并行执行（4 个并行组） | AI 执行，按依赖顺序实施（无工期估算） |
| P0 任务数量 | 10 项 | 10 项 | **14 项**（新增 RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02；THEME-B-02 保留 P0） |

**v1.2 ADR 全量清单（27 个）**：

| ADR | 标题 | 类型 | v1.2 调整 |
|-----|------|------|---------|
| ADR-001 | 三阶段实施策略 | 实施策略类 | 保持 |
| ADR-002 | P0 阶段分组顺序执行 | 实施策略类 | 保持 |
| ADR-003 | AI 模块全量否决 | 模块决策类 | 保持 |
| ADR-004 | UI 优化放最后并接受包体积增加 | 实施策略类 | 保持 |
| ADR-005 | 用户价值评估四维度标准 | 评估方法类 | 保持 |
| ADR-006 | 锁定依赖不升级 | 工程约束类 | 保持 |
| ADR-007 | RSS 搜索增强双轨方案 | 模块决策类 | 保持 |
| ADR-008 | 视频模块保持本项目架构 | 模块决策类 | 保持 |
| ADR-009 | EPUB 渲染引擎不替换 | 模块决策类 | 保持 |
| ADR-010a | 主题导入导出（P0 阶段仅本地视觉） | 模块决策类 | **拆分**（从 ADR-010 拆出，P0/P1 部分） |
| ADR-010b | 主题包云端同步与扩展能力 | 模块决策类 | **拆分**（从 ADR-010 拆出，P2 部分） |
| ADR-011 | 任务完成强制流程（代码+文档+测试三件套） | 质量保证类 | **合并**（原 ADR-011 + ADR-012） |
| ADR-013 | 数据库迁移安全策略 | 工程约束类 | 保持（v1.1 新增） |
| ADR-014 | 网络层兼容性与限流策略 | 工程约束类 | 保持（v1.1 新增） |
| ADR-015 | 协程调度与错误处理统一策略 | 工程约束类 | 保持（v1.1 新增） |
| ADR-016 | 性能基准测试与回归保护 | 质量保证类 | 保持（v1.1 新增） |
| ADR-017 | 资源文件变更规范 | 工程约束类 | 保持（v1.1 新增） |
| ADR-018 | 国际化文案规范 | 工程约束类 | 保持（v1.1 新增） |
| ADR-019 | 网络安全与隐私策略 | 工程约束类 | **新增**（高优先级，P0 实施前确立） |
| ADR-020 | 性能预算策略 | 工程约束类 | **新增**（高优先级，P0 实施前确立） |
| ADR-021 | 错误处理与异常上报统一策略 | 工程约束类 | **新增**（高优先级，P0 实施前确立） |
| ADR-022 | 兼容性策略 | 工程约束类 | **新增**（中优先级，P0 实施中确立） |
| ADR-023 | 日志策略 | 工程约束类 | **新增**（中优先级，P0 实施中确立） |
| ADR-024 | 测试覆盖率策略 | 质量保证类 | **新增**（中优先级，P0 实施中确立） |
| ADR-025 | 发布策略 | 质量保证类 | **新增**（中优先级，P0 完成后确立） |
| ADR-026 | 代码质量策略 | 质量保证类 | **新增**（低优先级，P1 实施中确立） |
| ADR-027 | 用户反馈策略 | 质量保证类 | **新增**（低优先级，P2 完成后确立） |

**v1.2 调整说明**：
- **ADR-010 拆分**：主题导入导出（P0/P1）与云端同步（P2）在用户额外负担、实施阶段、风险等级上差异显著，拆分为 ADR-010a + ADR-010b
- **ADR-011 + ADR-012 合并**：同属"任务完成后的强制流程"，合并为 ADR-011 任务完成强制流程（代码+文档+测试三件套）
- **ADR-019 ~ ADR-027 新增**：覆盖网络安全、性能预算、错误处理、兼容性、日志、测试覆盖率、发布、代码质量、用户反馈 9 个维度
- **净变化**：18 - 1（合并）+ 1（拆分）+ 9（新增）= 27 个

**P0 分组并行实施策略（4 个并行组，AI 执行按依赖顺序实施）**：

| 并行组 | 任务 | 修改文件 |
|--------|------|---------|
| 组1（RSS 主线） | RSS-B-05 → RSS-B-01 → RSS-B-02 + RSS-B-03 + RSS-E-06 | RssSearchActivity.kt / RssFragment.kt / SourceSelectDialog.kt / SearchBookMergeUtils.kt / RssSource.kt |
| 组2（THEME 视觉） | THEME-B-01 + THEME-B-02（并行） | PaperInkHelper.kt / ThemeColorUtils.kt |
| 组3（EPUB 加速） | EPUB-B-01 + EPUB-B-02（并行） | EpubFile.kt |
| 组4（VIDEO 增强） | VIDEO-B-01 → VIDEO-B-02 + VIDEO-E-01 + VIDEO-E-02 + DEPS-B-01 | VideoBookPreloader.kt / VideoActivity.kt / ReadRecentBook.kt / ChoiceSpeedDialog.kt / app/build.gradle |

---

## 4. 核心发现

### 4.1 Top 10 重大发现（来自 analysis-report.md）

1. **Archive 自研浏览器级 EPUB 渲染引擎**：46 文件 16000+ 行 vs 本项目 700 行（差距 23 倍）
2. **本项目视频模块已大幅领先 Archive**：8167 行 vs 4189 行（多约 3978 行）
3. **本项目 RssSource 实体已有 searchUrl 字段但无 Activity 使用**：数据已就绪但 UI 入口缺失
4. **Archive 重做主题管理**：日间/夜间/背景图/界面颜色/导入导出/云端同步
5. **两边走完全不同优化方向**：Archive 重广度 vs 本项目重性能
6. **Archive ExoPlayerHelper 存在 SPLIT_TAG Bug**：本项目已用 setMimeType 修复
7. **Archive VideoBookPreloader（90 行）值得借鉴**：搜索结果页预加载视频书目录
8. **锁定依赖两边完全一致**：jsoup 1.16.2 / rhino 1.8.1 / hutool 5.8.22
9. **AI 模块两边都有但用户价值评估为低**：需 API key 用户收益小
10. **UI 优化（liquidglass / lottie / KitBinding）虽增加包体积但用户体验提升值得**

### 4.2 设计哲学对比

| 维度 | Archive 项目 | 本项目 |
|------|------------|--------|
| 增强方向 | 体验广度（AI/主题/EPUB/订阅/RSS） | 性能稳定性 + 视频深度优化 |
| 工程哲学 | 大而全（16000+ 行 EPUB 引擎、35 文件 AI 体系） | 极简≠残缺（书源规则引擎主航道） |
| 依赖策略 | 引入 5 个新依赖扩展能力 | 锁定 10 项核心依赖保稳定 |
| 混淆策略 | minify=false（牺牲体积换开发便利） | minify=true（牺牲开发便利换体积） |
| CI 策略 | 9 个 CI 含 4 个 armv8 专用 + 增量缓存 | 5 个 CI 静态双架构 |

### 4.3 反模式警示

| 反模式 | 来源 | 警示 |
|--------|------|------|
| SPLIT_TAG 拼接 headers | Archive ExoPlayerHelper | 借鉴视频功能时避免 |
| DiscoverySuite 130KB+ 套件 | Archive 发现页 | 体量过大与极简哲学冲突 |
| minify=false | Archive release | 本项目不应降级 |
| Glide 用 kapt | 本项目 | Windows 跨盘 bug，待迁移 ksp |
| 实体字段膨胀 | 反例 | EPUB 增强应走独立磁盘目录 |

---

## 5. 实施阶段路线图

### 5.1 Phase 1: P0 用户核心场景（14 项 - 分组并行）

- **实施策略**：AI 执行，按依赖顺序实施（4 个并行组，文件隔离原则，主 Agent 协调）
- **关键依赖链**：RSS-B-05 → RSS-B-01，VIDEO-B-01 → VIDEO-B-02
- **完成标准**：所有 P0 任务实施完成 + 真机测试通过
- **文档同步**：updateLog.md + forks-reference.md + project_memory
- **实施方式**：AI 执行，按依赖顺序实施（无工期估算）

**4 个并行组任务分配**：

| 并行组 | 任务执行顺序 | 实施方式 |
|--------|------------|----------|
| 组 A（RSS 主线） | RSS-B-05 → RSS-B-01 → RSS-B-02 + RSS-B-03 + RSS-E-06 | AI 执行，按依赖顺序实施 |
| 组 B（THEME 视觉） | THEME-B-01 + THEME-B-02（并行） | AI 执行，按依赖顺序实施 |
| 组 C（EPUB 加速） | EPUB-B-01 + EPUB-B-02（并行） | AI 执行，按依赖顺序实施 |
| 组 D（VIDEO 增强） | VIDEO-B-01 → VIDEO-B-02 + VIDEO-E-01 + VIDEO-E-02 + DEPS-B-01 | AI 执行，按依赖顺序实施 |

**P0 任务明细（14 项）**：

| 任务 | 决策ID | 用户价值 | 所属并行组 |
|------|--------|---------|----------|
| RssSearchActivity | RSS-B-01 | 5.0 | 组 A RSS 主线 |
| RssFragment openRssSearch 入口 | RSS-B-05 | 4.8 | 组 A RSS 主线 |
| markwon 4.6.2 扩展 | DEPS-B-01 | 5.0 | 组 D VIDEO 增强 |
| 纸墨风格 | THEME-B-01 | 5.0 | 组 B THEME 视觉 |
| 字体撞色检测 | THEME-B-02 | 4.8 | 组 B THEME 视觉 |
| VideoBookPreloader | VIDEO-B-01 | 5.0 | 组 D VIDEO 增强 |
| cacheFirst 默认值 | RSS-E-06 | 4.8 | 组 A RSS 主线 |
| SourceSelectDialog | RSS-B-02 | 4.5 | 组 A RSS 主线 |
| SearchBookMergeUtils | RSS-B-03 | 4.5 | 组 A RSS 主线 |
| EPUB 章节资源索引 | EPUB-B-01 | 4.5 | 组 C EPUB 加速 |
| EPUB 资源过滤+标题归一化 | EPUB-B-02 | 4.5 | 组 C EPUB 加速 |
| 章节链接缓存+下一集预加载 | VIDEO-B-02 | 4.8 | 组 D VIDEO 增强 |
| ReadRecentBook 写入 | VIDEO-E-01 | 4.5 | 组 D VIDEO 增强 |
| ChoiceSpeedDialog 增强 | VIDEO-E-02 | 4.5 | 组 D VIDEO 增强 |

### 5.2 Phase 2: P1 性能体验增强（19 项）

- **包含**：RSS 订阅源优化、ExoPlayerHelper Bug 修复、主题扩展（THEME-B-03 主题包 ZIP 导入导出、THEME-B-04 Config 字段扩展等）等
- **完成标准**：所有 P1 任务实施完成 + 真机测试通过
- **文档同步**：同 Phase 1
- **实施方式**：AI 执行，按依赖顺序实施（无工期估算）

### 5.3 Phase 3: P2 UI 优化与扩展（21 项）

- **包含**：liquidglass、lottie、KitBinding 等
- **完成标准**：所有 P2 任务实施完成 + 真机测试通过 + APK 体积测量
- **文档同步**：同 Phase 1 + APK 体积对比报告
- **特殊要求**：UI 优化 9 项放在最后实施，集中回归测试
- **实施方式**：AI 执行，按依赖顺序实施（无工期估算）

---

## 6. 关键决策原则

1. **用户价值优先**：所有借鉴决策基于"用户使用软件的实际收益"标准
2. **AI 模块全量否决**：需 API key 配置的功能用户收益小，全量否决
3. **UI 优化可接受包体积增加**：用户体验提升值得（用户明确反馈）
4. **锁定依赖不升级**：jsoup / rhino / hutool 保持锁定版本
5. **三阶段实施策略**：P0 优先 → P1 增强 → P2 扩展
6. **真机测试强制**：每阶段完成后必须执行 ai_tests/scripts/ 验证
7. **源码修改串行化**：同一源码文件的所有 Edit 必须串行执行（并发文件修改规范）
8. **数据库变更安全**：如涉及 DB 变更必须先评估迁移安全
9. **调试日志清理**：每项任务完成前 Grep 确认无 `android.util.Log.d/e` 残留
10. **版本交付同步**：编译前必须基于 git diff 真实变更更新 updateLog.md
11. **数据库迁移安全**（v1.1 新增）：遵守 database-migration-safety.md，version 变更需编写 Migration，字段必须有默认值确保向后兼容
12. **网络层兼容性**（v1.1 新增）：新功能作为可选模式默认关闭，多源并发搜索复用 Semaphore 限流（5-10），单源超时 3s
13. **协程调度统一**（v1.1 新增）：所有异步操作使用本项目链式封装 `Coroutine.async{}...onError{}.onSuccess{}`，禁止 CoroutineExceptionHandler
14. **性能基准与回归测试**（v1.1 新增）：P0 完成后必测，建立基线→改造→对比三步流程，使用 swipe_test_log.py 等脚本
15. **资源文件命名规范**（v1.1 新增）：drawable/layout/values 文件命名遵循项目前缀规范，避免命名冲突
16. **国际化与字符串管理**（v1.1 新增）：所有用户可见字符串放入 strings.xml，禁止硬编码中文文案

---

## 7. 关联资源

### 7.1 本项目源码

- **项目根目录**：`f:\myself\github\WeAgentChat\temp\legado`
- **项目主规范**：`./AGENTS.md`
- **项目记忆**：`c:\Users\shiyq\.trae-cn\memory\projects\-f-myself-github-WeAgentChat-temp-legado\project_memory.md`

### 7.2 Archive 项目源码（仅供对比分析，不修改）

- **克隆位置**：`./temp/forks-comparison/legado-archive/`
- **来源**：GitHub 私仓（用户有仓库权限）
- **最新 tag**：`private-armv8-3.26.07071245`

### 7.3 规范文档

- **OpenSpec 工作流**：`~/.trae-cn/user_rules/openspec-workflow.md`
- **forks-reference 方法论**：`./docs/project-rules/forks-reference.md`
- **版本交付同步**：`./docs/project-rules/version-delivery-sync.md`
- **AI 自动端到端测试**：`./docs/project-rules/ai_e2e_testing_workflow.md`
- **改造过程日志记录**：`./docs/project-rules/logging-during-refactoring.md`
- **真机测试流程复用**：`./docs/project-rules/real-device-test-reuse.md`

### 7.4 测试脚本入口

| 脚本 | 用法 | 说明 |
|------|------|------|
| quick_build_install.py | `python ai_tests/scripts/quick_build_install.py` | 编译+安装+L1 验证 |
| import_rss_source.py | `python ai_tests/scripts/import_rss_source.py <json>` | 导入订阅源 |
| l2_verify_video_player.py | `python ai_tests/scripts/l2_verify_video_player.py [--scenario SCENARIO]` | L2 验证视频播放器 |
| swipe_test_log.py | `python ai_tests/scripts/swipe_test_log.py [clear\|capture\|analyze]` | 日志分析 |

> **venv Python**：必须使用 `ai_tests\venv\Scripts\python.exe`，禁止公共 Python

---

## 8. 模块分布与决策明细

### 8.1 借鉴项按模块分布

> v1.2 调整：P0 从 10 项升级为 14 项（新增 RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02；THEME-B-02 保留 P0）

| 模块 | P0 | P1 | P2 | 小计 | 备注 |
|------|---|---|---|------|------|
| SA-1 主题管理（THEME） | 2 | 5 | 6 | 13 | 含 AppearanceKit 套件架构；THEME-B-02 保留 P0 |
| SA-2 EPUB | 2 | 4 | 4 | 10 | 渐进式优化策略 |
| SA-3 AI 助手 | 0 | 0 | 0 | 0 | 全量否决 |
| SA-4 RSS/发现页 | 5 | 2 | 3 | 10 | P0 占比最高（含 RSS-B-05 升级） |
| SA-5 视频（VIDEO） | 4 | 1 | 0 | 5 | 本项目已领先；VIDEO-B-02/E-01/E-02 升级 P0 |
| SA-6 构建（BUILD） | 0 | 5 | 3 | 8 | CI 优化为主 |
| SA-7 依赖（DEPS） | 1 | 2 | 5 | 8 | UI 优化集中在 P2 |
| **合计** | **14** | **19** | **21** | **54** | - |

### 8.2 不借鉴项按类别分布

| 类别 | 数量 | 说明 |
|------|------|------|
| AI 模块全量否决 | 11 | 需 API key，用户收益小 |
| BUILD 配置差异 | 5 | 用户无感知 |
| 体量过大 | 8 | 与极简哲学冲突 |
| 已有更优实现 | 10 | 本项目已大幅领先 |
| 性能难感知 | 5 | 用户无直接感知 |
| 小众需求 | 3 | 非核心场景 |
| 非通用 | 4 | 只对部分用户有价值 |
| 已知 Bug | 4 | 借鉴时需避免 |
| 技术架构 | 8 | 用户无感知 |
| 其他 | 6 | 重复或已否决 |
| **合计** | **64** | - |

---

## 9. 当前状态与下一步

### 9.1 当前状态

| 检查点 | 状态 | 说明 |
|--------|------|------|
| 检查点 1 | ✅ 已完成 | spec.md 已完成（Intent/Scope/Approach/Requirements/Scenarios） |
| 检查点 2 | ✅ 已完成 | tasks.md 已完成（54 项任务清单，按 P0/P1/P2 分类） |
| 检查点 3 | ✅ 已完成 | design.md 已完成（v5.0 决策整合，含 ADR + 数据流图 + 文件变更清单） |
| 检查点 4 | 🔄 需调整 | 用户验收需调整 - 三大调整已完成（P0 范围升级 4 项变 14 项 + ADR 全量调整变 27 个 + 删除工期估算改为 AI 执行），等待三次验收 |

### 9.2 下一步

1. **完成 4 个文档全量修复**（spec/tasks/design/README）
2. **修复完成后再次发起检查点4 验收**
3. **通过后进入实施阶段**：Phase 1 P0 分组并行实施（4 个并行组，14 项任务，AI 执行按依赖顺序实施）
4. **每阶段完成后**：
   - 执行真机测试（ai_tests/scripts/）
   - 同步 updateLog.md（基于 git diff 真实变更）
   - 更新 issues-found.md 问题清单
   - 清理调试日志（Grep 确认无 `android.util.Log.d/e` 残留）
   - 写入项目记忆与经验索引

### 9.3 Phase 1 启动条件

- [ ] 用户通过检查点 4 验收
- [ ] 确认实施顺序（建议：RSS-B-01 → DEPS-B-01 → THEME-B-01 → VIDEO-B-01 → ...）
- [ ] 创建 Phase 1 任务跟踪 Issue

### 9.4 实施前必须确认的事实清单（v2.2 新增）

> 基于第三轮深度审查，实施前必须逐项确认以下事实，避免按 fork 仓库（Archive 项目）假设实施。

#### 9.4.1 文件路径已修正

| # | 文件 | 修正说明 |
|---|------|---------|
| 1 | `EpubFile.kt` | EPUB-B-01/B-02 修改目标文件，路径已核实 |
| 2 | `RssFragment.kt` | RSS-B-01/B-05 修改目标文件，路径已核实（注意与 RSS-B-05 串行） |
| 3 | `VideoPlayerActivity.kt` | VIDEO-B-02 修改目标文件，路径已核实 |
| 4 | `ChoiceSpeedDialog.kt` | VIDEO-E-02 修改目标文件，路径已核实 |
| 5 | `Exo2MediaPlayer.kt` | VIDEO-E-03 修改目标文件，路径已核实 |
| 6 | `ThemeUtils.kt` | THEME-B-02 修改目标文件，路径已核实（撞色检测方法新增位置） |

#### 9.4.2 新增子目录

| # | 子目录 | 关联任务 |
|---|--------|---------|
| 1 | `ui/rss/search/` | RSS-B-01（RssSearchActivity 及其 ViewModel/Adapter） |
| 2 | `ui/video/` | VIDEO-E-01/E-02（视频模块新增组件，避免与现有 video 模块文件冲突） |

#### 9.4.3 新增文件

| # | 文件 | 关联任务 | 备注 |
|---|------|---------|------|
| 1 | `ReadRecentBook.kt` | VIDEO-E-01 | 本项目无此文件，需新建（参考 fork 仓库实现） |
| 2 | `ReadRecentBookDao.kt` | VIDEO-E-01 | 本项目无此文件，需新建（Room DAO） |

#### 9.4.4 配置文件修改

| # | 配置文件 | 修改内容 | 关联任务 |
|---|---------|---------|---------|
| 1 | `strings.xml` | 新增用户可见字符串（双版本 values/ + values-zh/） | 所有 P0 任务（ADR-018） |
| 2 | `AndroidManifest.xml` | 新增 Activity 注册（RssSearchActivity 等） | RSS-B-01 |
| 3 | `proguard-rules.pro` | 新增反射类 keep 规则 | 涉及反射的新增类（B10 阻塞点） |

#### 9.4.5 已完成任务标注（v2.3 新增）

> 基于第四轮深度审查（review-code-feasibility.md / review-adr-logic.md / review-dependency-conflict.md），以下 P0 任务实际已完成，仅需真机验证。

| # | 任务 | 状态 | 证据 | 备注 |
|---|------|------|------|------|
| 1 | RSS-E-06（cacheFirst 默认值） | ✅ 已完成（仅 WebView 层需真机验证） | `ReadRssActivity.kt:421` 已实现 `cacheMode = if (s.cacheFirst) WebSettings.LOAD_CACHE_ELSE_NETWORK else WebSettings.LOAD_DEFAULT`；`RssSource.kt:113` `cacheFirst: Boolean = true` 默认值已就绪 | 数据层 + WebView 层均就绪，仅需真机验证 cacheFirst 行为 |
| 2 | RssWebActivity.kt 文件名修正 | ✅ 已修正为 `ReadRssActivity.kt` | design.md §4.1 #9 原标注的 `RssWebActivity.kt` 在本项目不存在，正确文件为 `app/src/main/java/io/legado/app/ui/rss/read/ReadRssActivity.kt` | 实施时无需修改文件名，仅需路径修正 |

---

## 10. 关键技术约束

### 10.1 代码约束

- **协程**：用自定义 `Coroutine.async{}...onError{}.onSuccess{}` 链式封装（非标准 launch+try/catch）
- **异步双版本**：`xxx()` 返回 `Coroutine<T>` + `xxxAwait()` 挂起函数
- **核心业务**：用 `object` 单例（`ReadBook`, `WebBook`, `AppConfig`），不引入 DI 框架
- **Room 实体**：`data class` + `@Parcelize` + `@Entity`，字段全部有默认值
- **错误处理**：用 `kotlin.runCatching`（带 `kotlin.` 前缀），字符串判空用 `isNullOrBlank()`
- **日志**：用 `AppLog.put()`，异常用 `Coroutine.onError`，禁止 Timber / `CoroutineExceptionHandler`

### 10.2 Landmines 警示

- **jsoup 1.16.2 锁定**：破坏性变更 jsoup#2017，不可升级
- **rhino 1.8.1 锁定**：API 24 以下缺少 Arrays.setAll，不可升级
- **hutool 5.8.22 锁定**：书源加解密依赖，不可升级
- **ReadBook 全局单例**：多 Activity 共享，改状态需 `@Synchronized` 或 `Mutex` 保护
- **Vue3 构建**：vite build 后 sync.js 仅在 GitHub Actions 执行，本地需手动复制
- **NoStackTraceException**：所有业务异常继承此类，覆写 `fillInStackTrace()`

### 10.3 数据库安全

如涉及 DB 变更（如 RssSource 字段调整、ReadRecentBook 写入）：
1. 必须先评估迁移安全（database-migration-safety.md）
2. 数据库 version 变更需编写 Migration
3. `@DatabaseView` 修改需评估影响
4. 实体字段修改需评估向后兼容性

### 10.4 关键事实标注（v2.2 新增）

> 基于第三轮深度审查确认的本项目关键事实，实施前必须核对这些事实，避免按 fork 仓库（Archive 项目）假设实施。

| # | 事实 | 证据位置 | 实施影响 |
|---|------|---------|---------|
| F1 | **本项目 minSdk=23** | `build.gradle:66` | 所有新增依赖必须支持 API 23+；rhino 1.8.1 锁定原因之一是 API 24 以下缺少 Arrays.setAll（minSdk 已提升至 23 但仍低于 24），ADR-022 兼容性策略以此为基线 |
| F2 | **sora-editor + markwon 已引入** | `build.gradle:329-332, 356-358` | DEPS-B-01（markwon 4.6.2 扩展）仅需添加扩展依赖，无需新增核心库；DEPS-B-03（sora-editor）已引入，P2 任务仅做能力扩展 |
| F3 | **本项目无 ReadRecentBook.kt** | 本项目源码扫描 | 仅 fork 仓库（Archive 项目）有 ReadRecentBook.kt；VIDEO-E-01 实施时需新建 `ReadRecentBook.kt` + `ReadRecentBookDao.kt`（参考 fork 仓库实现） |
| F4 | **本项目无 BaseSearchActivity** | 本项目源码扫描 | 本项目只有 `VMBaseActivity`；RSS-B-01 实施时 `RssSearchActivity` 父类需重新评估（继承 VMBaseActivity 或 SearchActivity，而非 BaseSearchActivity） |

---

## 11. 变更历史

| 时间 | 版本 | 变更内容 |
|------|------|----------|
| 2026-07-18 | v1.0 | 初始创建：基于 v5.0 最终决策生成 spec/tasks/design/README |
| 2026-07-18 | v1.1 | 全量修复+优化：修复 5 类严重问题 + 8 项中等问题 + 新增 6 个 ADR（ADR-013~018）+ 优化 P0 为分组并行（4 组）|
| 2026-07-18 | v1.2 | 三大调整：P0 范围升级 4 项变 14 项 + ADR 全量调整变 27 个 + 删除工期估算（AI 执行无需工期）|
| 2026-07-18 | v2.2 | 第三轮深度审查全量修复：基于 3 份审查报告（共 4828 行）全量修复 12 项严重问题（A.事实偏差类 6 项 + B.ADR 决策类 5 项 + C.跨文档矛盾类 1 项），详见 §12 v2.2 修复详情 |
| 2026-07-18 | v2.3 | 第四轮深度审查全量修复：基于 3 份审查报告（共约 1300 行）全量修复 10 项严重 + 15 项中等问题（A.代码可行性 6 项 + B.ADR 逻辑链 6 项 + C.依赖链冲突 6 项），数据基线保持不变（P0=14/P1=19/P2=21/ADR=27），详见 §15 v2.3 修复详情 |

---

## 12. v2.2 修复详情（2026-07-18）

> 基于第三轮深度审查（3 份报告共 4828 行）的全量修复，统一 P0=14 / P1=19 / P2=21 / ADR=27 数据基线。

### 12.1 审查报告来源（3 份，共 4828 行）

| 报告 | 行数 | 主要审查范围 |
|------|------|------------|
| review-design-rationality-spec-tasks.md | 1194 | spec.md + tasks.md 设计合理性审查 |
| review-design-rationality-design.md | 1628 | design.md 设计合理性审查 |
| review-implementation-simulation.md | 2006 | 实施过程仿真模拟审查 |

### 12.2 12 项严重问题分类与修复

#### A. 事实偏差类（6 项）

| # | 问题 | 修复 |
|---|------|------|
| A1 | ReadRecentBook.kt 存在性误判 | 标注"本项目无 ReadRecentBook.kt（仅 fork 仓库有）"，实施时需新建该文件 |
| A2 | BaseSearchActivity 存在性误判 | 标注"本项目无 BaseSearchActivity（只有 VMBaseActivity）"，RssSearchActivity 父类需重新评估 |
| A3 | cacheFirst 默认值描述偏差 | 修正 cacheFirst 默认值变更影响范围说明 |
| A4 | 文件路径错误 | 修正 EpubFile.kt/RssFragment.kt/VideoPlayerActivity.kt/ChoiceSpeedDialog.kt/Exo2MediaPlayer.kt/ThemeUtils.kt 等文件路径标注 |
| A5 | sora-editor+markwon 引入状态偏差 | 标注"sora-editor+markwon 已引入（build.gradle:329-332, 356-358）"，DEPS-B-01/P2 任务无需新增依赖 |
| A6 | 子目录结构缺失 | 补充新增子目录说明：ui/rss/search/ + ui/video/ |

#### B. ADR 决策类（5 项）

| # | 问题 | 修复 |
|---|------|------|
| B1 | ADR-002 与 R22 矛盾 | 统一 ADR-002（P0 分组并行）与 R22（RssFragment.kt 并发修改风险）的描述，明确文件隔离原则 |
| B2 | ADR-013 pureSearch 策略 | 修正 ADR-013 数据库迁移安全策略与 pureSearch 的关系说明（pureSearch 不涉及数据库变更） |
| B3 | 文件清单不完整 | 补充 design.md 文件变更清单遗漏的文件（ReadRecentBookDao.kt 等） |
| B4 | minSdk 描述偏差 | 标注"本项目 minSdk=23（build.gradle:66）"，修正 ADR-022 兼容性策略的基线 |
| B5 | ADR-010b 范围 | 明确 ADR-010b 主题包云端同步仅覆盖 P2 部分，与 ADR-010a 拆分边界清晰 |

#### C. 跨文档矛盾类（1 项）

| # | 问题 | 修复 |
|---|------|------|
| C1 | P0 范围+P1 下限跨文档不一致 | 4 份文档（README/spec/tasks/design）+ 3 份分析报告统一为 P0=14 / P1=19 / P2=21 / ADR=27 |

### 12.3 v2.2 修复后数据基线

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| P0 数量 | 10/13/14 混用 | **14** |
| P1 数量 | 19/23 混用 | **19** |
| P2 数量 | 21 | **21** |
| ADR 数量 | 18/27 混用 | **27** |
| 总借鉴数 | 54 | **54** |

---

## 13. 文档使用说明

### 13.1 阅读顺序建议

1. **首次阅读**：第 1 章项目概述 → 第 3 章决策汇总 → 第 9 章当前状态
2. **实施参考**：第 5 章路线图 → 第 10 章技术约束 → tasks.md 任务清单
3. **决策追溯**：第 4 章核心发现 → borrow-decisions.md 决策表 → analysis-report.md 分析报告
4. **模块深度**：intermediate/SA-*-*.md 对应模块中间文件

### 13.2 维护规则

- **状态更新**：每阶段完成后更新第 9 章当前状态
- **变更记录**：所有重大变更记录到第 11 章变更历史
- **文档同步**：tasks.md 完成进度同步更新到第 9.1 节检查点表
- **决策调整**：如实施过程中决策调整，需同步更新 spec.md + 第 3 章决策汇总

---

## 14. 文档清理记录

### 14.1 清理时间

- **清理时间**：2026-07-18
- **触发原因**：CP4 五次验收用户反馈"为防止后续执行任务实施时被不相关的设计文档干扰，对不相关的报告或文件做最后一次审查清理"
- **清理策略**：移动审查报告到 `archive/` 子目录（用户确认）

### 14.2 清理范围

将 9 份历史审查报告从根目录移动到 `archive/` 子目录，根目录仅保留 7 份核心文档。

**移动的 9 份审查报告**：

| # | 报告名 | 来源轮次 | 行数 |
|---|--------|---------|------|
| 1 | review-spec-tasks.md | 第一轮审查 | spec+tasks 审查 |
| 2 | review-design-readme.md | 第一轮审查 | design+README 审查 |
| 3 | review-cross-optimization.md | 第一轮审查 | 跨文档优化审查 |
| 4 | review-design-rationality-spec-tasks.md | 第三轮审查 | spec+tasks 设计合理性 |
| 5 | review-design-rationality-design.md | 第三轮审查 | design 设计合理性 |
| 6 | review-implementation-simulation.md | 第三轮审查 | P0 实施模拟+交叉验证 |
| 7 | review-final-spec-tasks.md | 最终审查 | spec+tasks 修复质量审查 |
| 8 | review-final-design.md | 最终审查 | design 修复质量审查 |
| 9 | review-final-cross-simulation.md | 最终审查 | 交叉审查+实施模拟 |

### 14.3 清理后目录结构

```
docs/specs/forks-archive-borrow-implementation/
├── spec.md                          # 需求规格（412 行）
├── tasks.md                         # 任务清单（482 行）
├── design.md                        # 设计文档（1314 行，27 ADR）
├── README.md                        # 本文档（含清理记录）
├── analysis-task-priority.md        # 任务优先级分析（1281 行）
├── analysis-adr-decisions.md        # ADR 决策分析（1147 行）
├── analysis-p0-strategy-risks.md    # P0 策略风险分析（1074 行）
└── archive/                         # 历史审查报告归档
    ├── review-spec-tasks.md
    ├── review-design-readme.md
    ├── review-cross-optimization.md
    ├── review-design-rationality-spec-tasks.md
    ├── review-design-rationality-design.md
    ├── review-implementation-simulation.md
    ├── review-final-spec-tasks.md
    ├── review-final-design.md
    └── review-final-cross-simulation.md
```

### 14.4 清理后实施工作流

- **实施阶段参考文档**：仅根目录 7 份核心文档
- **历史审查报告查阅**：如需追溯审查历史，访问 `archive/` 子目录
- **避免干扰原则**：实施期间不再打开 `archive/` 中的审查报告，避免历史问题清单干扰当前实施

---

## 15. v2.3 修复详情（2026-07-18）

> 基于第四轮深度审查（3 份报告共约 1300 行）的全量修复，聚焦代码可行性、ADR 逻辑链、依赖链冲突三个维度。数据基线保持不变：P0=14 / P1=19 / P2=21 / ADR=27。

### 15.1 审查报告来源（3 份）

| 报告 | 主要审查维度 | 关键发现 |
|------|------------|---------|
| review-code-feasibility.md | 代码实施可行性（对照本项目真实源码逐项验证 P0 14 项任务） | 6 项严重发现（RSS-E-06 已完成 / 借鉴源依赖缺失扩展 / markwon 版本错误等） |
| review-adr-logic.md | ADR 决策逻辑链（27 个 ADR 内部+间逻辑一致性） | 2 项严重硬矛盾（ADR-008 vs ADR-002 P1/P0 矛盾 / ADR-001 备选 B P0 项数矛盾）+ 6 项中等 |
| review-dependency-conflict.md | P0 14 项任务依赖链与文件冲突 | 3 项严重（VideoPlayerActivity.kt 三任务同文件冲突未识别 / RssWebActivity.kt 不存在 / R22 定义矛盾）+ 3 项中等 |

### 15.2 修复范围总览

| 维度 | 严重 | 中等 | 小计 |
|------|------|------|------|
| 代码可行性 | 6 | 6 | 12 |
| ADR 逻辑链 | 2 | 6 | 8 |
| 依赖链冲突 | 3 | 3 | 6 |
| **合计** | **11** | **15** | **26** |

> 实际修复 10 项严重 + 15 项中等（部分严重项归类合并修复），详见各审查报告。

### 15.3 关键修复点

#### A. 代码可行性维度（review-code-feasibility.md）

| # | 问题 | 修复 |
|---|------|------|
| A1 | markwon 版本严重不一致（设计文档错误描述为 markwon 3，实际为 markwon 4.6.2） | README 全文"markwon 3 扩展"改为"markwon 4.6.2 扩展"（3 处） |
| A2 | RSS-E-06 任务实际已完成（`ReadRssActivity.kt:421` 已实现 cacheFirst 逻辑） | §9.4.5 新增已完成任务标注，标注"✅ 已完成（仅 WebView 层需真机验证）" |
| A3 | RssWebActivity.kt 在本项目不存在（正确文件为 `ReadRssActivity.kt`） | §9.4.5 标注文件名修正，design.md §4.1 #9 同步修正 |
| A4 | PaperInkHelper 借鉴源依赖 ReadBookConfig.paperInkStrength 字段（设计文档遗漏 ReadBookConfig 修改条目） | design.md §4.3 补充 ReadBookConfig.kt 修改条目，README 在 v2.3 修复详情中记录 |
| A5 | SourceSelectDialog 借鉴源是 Compose 实现依赖本项目不存在的 Compose 组件 | design.md §4.1 #5 注明需改写为非 Compose 实现，README 在 v2.3 修复详情中记录 |
| A6 | SearchBookMergeUtils 借鉴源依赖本项目不存在的 stableSearchBookKey 扩展函数 | design.md §4.1 #6 注明需同步借鉴或改写，README 在 v2.3 修复详情中记录 |

#### B. ADR 逻辑链维度（review-adr-logic.md）

| # | 问题 | 修复 |
|---|------|------|
| B1 | ADR-008 与 ADR-002 对 VIDEO-B-02/E-01/E-02 优先级阶段直接矛盾（P1 vs P0） | design.md ADR-008 Decision 将 VIDEO-B-02/E-01/E-02 从 P1 改为 P0，添加 v5.1 调整说明；README §3.2 P0 列表已含这 3 项，无需修改 |
| B2 | ADR-002 标题"分组并行"与内容"物理串行"不一致 | README ADR 全量清单 ADR-002 标题改为"P0 阶段分组顺序执行" |
| B3 | ADR-010a 标题"主题导入导出"与 Decision P0 阶段任务范围（视觉增强）不符 | README ADR 全量清单 ADR-010a 标题改为"主题导入导出（P0 阶段仅本地视觉）" |
| B4 | ADR-010b 标题"主题包云端同步"与 Decision 任务范围越界（含架构扩展任务） | README ADR 全量清单 ADR-010b 标题改为"主题包云端同步与扩展能力" |
| B5 | ADR-013 与 ADR-002 对 VIDEO-E-01 复杂度评估不一致 | design.md ADR-002 组D VIDEO-E-01 标注补充"涉及数据库迁移（ADR-013）"，README 在 v2.3 修复详情中记录 |
| B6 | ADR-016 要求 P0 前建立基线但 ADR-002 P0 任务清单未列入 | design.md ADR-002 P0 任务清单前增加"P0 前置任务：性能基线建立（ADR-016）"，README 在 v2.3 修复详情中记录 |

#### C. 依赖链冲突维度（review-dependency-conflict.md）

| # | 问题 | 修复 |
|---|------|------|
| C1 | VideoPlayerActivity.kt 被 3 个 P0 任务修改（VIDEO-B-01/B-02/E-02）但分组方案未识别 VIDEO-E-02 同文件冲突 | design.md ADR-002 组D 修订为 VIDEO-B-01 → VIDEO-B-02 → VIDEO-E-02 同文件严格串行链，README 在 v2.3 修复详情中记录 |
| C2 | design.md §4.1 #9 文件路径错误（RssWebActivity.kt 不存在） | 同 A3，§9.4.5 标注修正为 ReadRssActivity.kt |
| C3 | R22 风险定义在 design.md 与 analysis-p0-strategy-risks.md 中不一致 | design.md 统一 R22 定义为"RssFragment.kt 文件冲突风险"，README 在 v2.3 修复详情中记录 |
| C4 | VIDEO-E-02 tasks.md 1.14.2 描述与实际代码不符（VideoPlayerActivity.kt 用 Spinner 而非 ChoiceSpeedDialog） | tasks.md 1.14.2 明确修改目标，README 在 v2.3 修复详情中记录 |
| C5 | VIDEO-B-01 集成位置描述不一致（搜索结果页 vs 视频播放页） | design.md §4.2 #2 删除 VIDEO-B-01 对 VideoPlayerActivity.kt 的标注，新增 SearchActivity.kt 条目，README 在 v2.3 修复详情中记录 |
| C6 | design.md §4.8 AndroidManifest.xml 修改范围错误（VIDEO-B-01 不需要 Manifest 注册） | design.md §4.8 #2 删除 VIDEO-B-01 条目，仅保留 RSS-B-01 注册 RssSearchActivity，README 在 v2.3 修复详情中记录 |

### 15.4 v2.3 修复后数据基线

| 指标 | v2.2 修复后 | v2.3 修复后 |
|------|------------|------------|
| P0 数量 | 14 | **14**（不变） |
| P1 数量 | 19 | **19**（不变） |
| P2 数量 | 21 | **21**（不变） |
| ADR 数量 | 27 | **27**（不变） |
| 总借鉴数 | 54 | **54**（不变） |

> 数据基线保持不变，v2.3 修复仅修订文档描述与决策标注，不调整 P0/P1/P2 范围与 ADR 数量。

### 15.5 v2.3 新增审查报告索引

| 报告 | 路径 | 行数 | 审查维度 |
|------|------|------|---------|
| review-code-feasibility.md | `docs/specs/forks-archive-borrow-implementation/review-code-feasibility.md` | 547 | 代码实施可行性深度审查 |
| review-adr-logic.md | `docs/specs/forks-archive-borrow-implementation/review-adr-logic.md` | 356 | ADR 决策逻辑链深度审查 |
| review-dependency-conflict.md | `docs/specs/forks-archive-borrow-implementation/review-dependency-conflict.md` | 421 | P0 14 项任务依赖链与文件冲突深度审查 |

---

**文档完成**。本文档基于 v5.0 终版决策生成，作为 forks-archive-borrow-implementation 项目的状态追踪与文档索引中心。后续实施进度将通过第 9 章当前状态章节同步更新。
