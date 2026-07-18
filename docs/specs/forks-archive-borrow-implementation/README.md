# Forks Archive 借鉴实施 - 状态追踪

> **项目代号**：forks-archive-borrow-implementation
> **创建时间**：2026-07-18
> **当前阶段**：OpenSpec 设计阶段 - 修复迭代中（检查点4 需调整反馈后，正在全量修复+优化）
> **决策版本**：v5.0 终版（54 借鉴 / 64 不借鉴 / 0 待评估）
> **实施范围**：54 项借鉴决策（P0: 13 / P1: 20 / P2: 21）
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
| P0 立即启动 | 13 | AI 执行，按依赖顺序实施 |
| P1 季度规划 | 20 | AI 执行，按依赖顺序实施 |
| P2 年度规划 | 21 | AI 执行，按依赖顺序实施 |
| **合计** | **54** | - |

---

## 2. 文档索引

### 2.1 本项目文档（forks-archive-borrow-implementation/）

| 文档 | 状态 | 说明 |
|------|------|------|
| spec.md | ✅ 已完成 | Intent/Scope/Approach/Requirements(P0 10+P1 23+P2 21)/Scenarios(S1-S11) |
| tasks.md | ✅ 已完成 | 54 项实施任务清单，按 P0/P1/P2 三级分类 |
| design.md | ✅ 已完成 | ADR 决策 + 数据流图 + 文件变更清单 + 风险缓解 |
| README.md | ✅ 本文档 | 状态追踪 + 文档索引 + 决策汇总 |
| review-spec-tasks.md | ✅ 已完成 | spec.md + tasks.md 审查报告 |
| review-design-readme.md | ✅ 已完成 | design.md + README.md 审查报告 |
| review-cross-optimization.md | ✅ 已完成 | 交叉审查+决策优化报告 |

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

#### P0（13 项 - 用户核心场景优先）

> v1.2 调整：原 P0 10 项 + 新增 4 项（RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02）- 调整 1 项（THEME-B-02 从 P0 移到 P1，按模块分布表 THEME P0=1）= 13 项

| # | 决策ID | 决策项 | 用户价值 | 实施成本 | 用户场景 |
|---|--------|--------|---------|---------|---------|
| 1 | RSS-B-01 | RssSearchActivity | 5.0 | 低 | 用户搜索订阅内容 |
| 2 | RSS-B-05 | RssFragment openRssSearch 入口 | 4.8 | 低 | RSS 搜索入口集成 |
| 3 | DEPS-B-01 | markwon 3 扩展 | 5.0 | 低 | 订阅文章渲染 |
| 4 | THEME-B-01 | 纸墨风格 | 5.0 | 低 | 阅读视觉体验 |
| 5 | VIDEO-B-01 | VideoBookPreloader | 5.0 | 低 | 视频播放加速 |
| 6 | RSS-E-06 | cacheFirst 默认值 | 4.8 | 低 | RSS 加载更快 |
| 7 | RSS-B-02 | SourceSelectDialog | 4.5 | 中 | 源管理简化 |
| 8 | RSS-B-03 | SearchBookMergeUtils | 4.5 | 中 | 搜索结果统一 |
| 9 | EPUB-B-01 | 章节资源索引 | 4.5 | 低 | EPUB 加载加速 |
| 10 | EPUB-B-02 | 资源过滤+标题归一化 | 4.5 | 低 | EPUB 阅读体验 |
| 11 | VIDEO-B-02 | 章节链接缓存+下一集预加载 | 4.8 | 中 | 视频连续看剧流畅 |
| 12 | VIDEO-E-01 | ReadRecentBook 写入 | 4.5 | 低 | 视频书最近阅读 |
| 13 | VIDEO-E-02 | ChoiceSpeedDialog 增强 | 4.5 | 低 | 视频倍速交互优化 |

#### P1（20 项 - 性能体验增强）

> v1.2 调整：原 P1 23 项 - 升级 P0 4 项（RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02）+ 接收 1 项（THEME-B-02 从 P0 移入）= 20 项

**用户中高收益（14 项）**：THEME-B-02、RSS-E-05、THEME-E-05、EPUB-E-04、DEPS-B-04、EPUB-E-02、RSS-B-04、THEME-B-03/04/05、THEME-E-04、EPUB-B-03、EPUB-E-06、VIDEO-E-03

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
| P0 任务数量 | 10 项 | 10 项 | **13 项**（新增 RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02；THEME-B-02 移到 P1） |

**v1.2 ADR 全量清单（27 个）**：

| ADR | 标题 | 类型 | v1.2 调整 |
|-----|------|------|---------|
| ADR-001 | 三阶段实施策略 | 实施策略类 | 保持 |
| ADR-002 | P0 阶段分组并行执行 | 实施策略类 | 保持 |
| ADR-003 | AI 模块全量否决 | 模块决策类 | 保持 |
| ADR-004 | UI 优化放最后并接受包体积增加 | 实施策略类 | 保持 |
| ADR-005 | 用户价值评估四维度标准 | 评估方法类 | 保持 |
| ADR-006 | 锁定依赖不升级 | 工程约束类 | 保持 |
| ADR-007 | RSS 搜索增强双轨方案 | 模块决策类 | 保持 |
| ADR-008 | 视频模块保持本项目架构 | 模块决策类 | 保持 |
| ADR-009 | EPUB 渲染引擎不替换 | 模块决策类 | 保持 |
| ADR-010a | 主题导入导出 | 模块决策类 | **拆分**（从 ADR-010 拆出，P0/P1 部分） |
| ADR-010b | 主题包云端同步 | 模块决策类 | **拆分**（从 ADR-010 拆出，P2 部分） |
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
| 组2（THEME 视觉） | THEME-B-01（独立） | PaperInkHelper.kt |
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

### 5.1 Phase 1: P0 用户核心场景（13 项 - 分组并行）

- **实施策略**：AI 执行，按依赖顺序实施（4 个并行组，文件隔离原则，主 Agent 协调）
- **关键依赖链**：RSS-B-05 → RSS-B-01，VIDEO-B-01 → VIDEO-B-02
- **完成标准**：所有 P0 任务实施完成 + 真机测试通过
- **文档同步**：updateLog.md + forks-reference.md + project_memory
- **实施方式**：AI 执行，按依赖顺序实施（无工期估算）

**4 个并行组任务分配**：

| 并行组 | 任务执行顺序 | 实施方式 |
|--------|------------|----------|
| 组 A（RSS 主线） | RSS-B-05 → RSS-B-01 → RSS-B-02 + RSS-B-03 + RSS-E-06 | AI 执行，按依赖顺序实施 |
| 组 B（THEME 视觉） | THEME-B-01（独立） | AI 执行，按依赖顺序实施 |
| 组 C（EPUB 加速） | EPUB-B-01 + EPUB-B-02（并行） | AI 执行，按依赖顺序实施 |
| 组 D（VIDEO 增强） | VIDEO-B-01 → VIDEO-B-02 + VIDEO-E-01 + VIDEO-E-02 + DEPS-B-01 | AI 执行，按依赖顺序实施 |

**P0 任务明细（13 项）**：

| 任务 | 决策ID | 用户价值 | 所属并行组 |
|------|--------|---------|----------|
| RssSearchActivity | RSS-B-01 | 5.0 | 组 A RSS 主线 |
| RssFragment openRssSearch 入口 | RSS-B-05 | 4.8 | 组 A RSS 主线 |
| markwon 3 扩展 | DEPS-B-01 | 5.0 | 组 D VIDEO 增强 |
| 纸墨风格 | THEME-B-01 | 5.0 | 组 B THEME 视觉 |
| VideoBookPreloader | VIDEO-B-01 | 5.0 | 组 D VIDEO 增强 |
| cacheFirst 默认值 | RSS-E-06 | 4.8 | 组 A RSS 主线 |
| SourceSelectDialog | RSS-B-02 | 4.5 | 组 A RSS 主线 |
| SearchBookMergeUtils | RSS-B-03 | 4.5 | 组 A RSS 主线 |
| EPUB 章节资源索引 | EPUB-B-01 | 4.5 | 组 C EPUB 加速 |
| EPUB 资源过滤+标题归一化 | EPUB-B-02 | 4.5 | 组 C EPUB 加速 |
| 章节链接缓存+下一集预加载 | VIDEO-B-02 | 4.8 | 组 D VIDEO 增强 |
| ReadRecentBook 写入 | VIDEO-E-01 | 4.5 | 组 D VIDEO 增强 |
| ChoiceSpeedDialog 增强 | VIDEO-E-02 | 4.5 | 组 D VIDEO 增强 |

### 5.2 Phase 2: P1 性能体验增强（20 项）

- **包含**：RSS 订阅源优化、ExoPlayerHelper Bug 修复、主题扩展（含 THEME-B-02 字体撞色检测）等
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

> v1.2 调整：P0 从 10 项升级为 13 项（新增 RSS-B-05、VIDEO-B-02、VIDEO-E-01、VIDEO-E-02；THEME-B-02 移到 P1）

| 模块 | P0 | P1 | P2 | 小计 | 备注 |
|------|---|---|---|------|------|
| SA-1 主题管理（THEME） | 1 | 6 | 6 | 13 | 含 AppearanceKit 套件架构；THEME-B-02 移到 P1 |
| SA-2 EPUB | 2 | 4 | 4 | 10 | 渐进式优化策略 |
| SA-3 AI 助手 | 0 | 0 | 0 | 0 | 全量否决 |
| SA-4 RSS/发现页 | 5 | 2 | 3 | 10 | P0 占比最高（含 RSS-B-05 升级） |
| SA-5 视频（VIDEO） | 4 | 1 | 0 | 5 | 本项目已领先；VIDEO-B-02/E-01/E-02 升级 P0 |
| SA-6 构建（BUILD） | 0 | 5 | 3 | 8 | CI 优化为主 |
| SA-7 依赖（DEPS） | 1 | 2 | 5 | 8 | UI 优化集中在 P2 |
| **合计** | **13** | **20** | **21** | **54** | - |

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
| 检查点 4 | 🔄 需调整 | 用户验收需调整 - 三大调整执行中（P0 范围升级 4 项变 13 项 + ADR 全量调整变 27 个 + 删除工期估算改为 AI 执行） |

### 9.2 下一步

1. **完成 4 个文档全量修复**（spec/tasks/design/README）
2. **修复完成后再次发起检查点4 验收**
3. **通过后进入实施阶段**：Phase 1 P0 分组并行实施（4 个并行组，13 项任务，AI 执行按依赖顺序实施）
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

---

## 11. 变更历史

| 时间 | 版本 | 变更内容 |
|------|------|----------|
| 2026-07-18 | v1.0 | 初始创建：基于 v5.0 最终决策生成 spec/tasks/design/README |
| 2026-07-18 | v1.1 | 全量修复+优化：修复 5 类严重问题 + 8 项中等问题 + 新增 6 个 ADR（ADR-013~018）+ 优化 P0 为分组并行（4 组）|
| 2026-07-18 | v1.2 | 三大调整：P0 范围升级 4 项变 13 项 + ADR 全量调整变 27 个 + 删除工期估算（AI 执行无需工期）|

---

## 12. 文档使用说明

### 12.1 阅读顺序建议

1. **首次阅读**：第 1 章项目概述 → 第 3 章决策汇总 → 第 9 章当前状态
2. **实施参考**：第 5 章路线图 → 第 10 章技术约束 → tasks.md 任务清单
3. **决策追溯**：第 4 章核心发现 → borrow-decisions.md 决策表 → analysis-report.md 分析报告
4. **模块深度**：intermediate/SA-*-*.md 对应模块中间文件

### 12.2 维护规则

- **状态更新**：每阶段完成后更新第 9 章当前状态
- **变更记录**：所有重大变更记录到第 11 章变更历史
- **文档同步**：tasks.md 完成进度同步更新到第 9.1 节检查点表
- **决策调整**：如实施过程中决策调整，需同步更新 spec.md + 第 3 章决策汇总

---

**文档完成**。本文档基于 v5.0 终版决策生成，作为 forks-archive-borrow-implementation 项目的状态追踪与文档索引中心。后续实施进度将通过第 9 章当前状态章节同步更新。
