# 视频/图片播放器审查与优化整合

> 状态：✅ R4 修订完成，已开始实施（用户2026-07-26 15:38 审查通过）
> **图片部分已废弃**：图片播放器优化由 [image-player-vertical-canvas-optimization](../image-player-vertical-canvas-optimization/README.md) 取代（V4 设计审查通过，用户 2026-07-26 19:20 选择"通过"）。本 spec 仅保留视频播放器优化部分。
> **R4 修订（核心能力提升，非文档层面）**：从"5 级识别链+L4 保留/移除之争"升级为"7 维度交叉验证+MediaSource 智能选择+降级链"，对齐浏览器五层架构。预期抓取+40%/识别+50%/播放+55%。完整方案见 [R4-enhancement-plan.md](./R4-enhancement-plan.md)
> 创建时间：2026-07-26
> 修订时间：2026-07-26（R2 修订：基于多维度审查报告修复 14 P0 + 12 P1 + 11 P2 问题）
> 任务类型：OpenSpec 四文档之一（功能概述）

## 1. 功能概述

本次任务基于 8 份多维度审查报告（5 份原始审查 + 3 份架构风格审查），对视频播放器（exoplayer-resilience）与图片播放器（image-gallery-activity）进行审查与优化整合，共整合 **32 个 ERROR + 44 个 WARN + 32 个 INFO** 问题（合计 108 项，含风格审查新增 14 ERROR + 11 WARN），形成统一修复与优化方案，系统性解决用户多次批评的"功能设计不是很好"问题。

> 统计口径说明：原始 5 份审查报告 18E+27W+13I=58 项；新增 3 份架构风格审查后扩展为 32E+44W+32I=108 项（去重后）。

审查覆盖范围：
- 设计文档完整性（spec.md 五要素 + ADR Y-Statement 模板合规性）
- 源码实现一致性（设计文档 vs 代码偏差识别）
- 用户反馈响应度（6 条核心诉求逐项核对闭环）
- 架构一致性（视频 vs 图片基础设施层对比）

## 2. 核心能力

### 2.1 视频播放器优化

- **MIME 嗅探策略修订**：移除 L1.5 URL 后缀快速路径，L4 URL 后缀仅作 L2/L3 前置帧分析失败时的兜底，且兜底结果不缓存（避免误判固化）
- **ExoPlayer 协程生命周期修复**：Exo2MediaPlayer.scope 在 release() 时未取消导致泄漏，重写 release() 调用 `scope.cancel()` 后 `super.release()`
- **3003 常量误判修复**：bitstream malformed 错误未计数到 unrecoverableFailCount，导致无法触发自动 WebView 降级
- **getMediaItem 改 suspend 影响面审计**：列出 AudioPlayService/VideoPlay 等所有调用方，确保协程上下文
- **日志规范化**：Log.d/Log.e 违规调用统一改用 AppLog.put（含 ExoFallback/onPlayerError/ExoHeader 三处）

### 2.2 图片播放器优化

- **header/cookie 复用统一**：对齐视频播放器架构，新增 ImagePlay.currentPlayHeaders 字段跨文章复用 headers；OkHttpModelLoader.sourceOriginOption + refererOption 注入 Referer/Cookie
- **多线程预缓存设计**：参考 VideoPlay.preloadNextArticleHtml，新增 ImagePlay.preloadNextArticleImages + preloadedArticles 去重集合
- **双 ViewPager 嵌套 Bug 修复**：
  - 适配器复用失效（else 分支应改 updateSource 而非新建）
  - WebView 预热循环 loadUrl 覆盖（改串行队列 + onPageFinished 链式）
  - loadArticleContent 协程未取消（用 Job 跟踪 + cancel 上一个协程）
- **articleStyle==2 路由回退决策文档化**：ReadRss.kt 已实现回退（用户主动选网页模式时走 ReadRssActivity），但 design.md 缺 ADR，需追加 AD-06 记录决策
- **图片尺寸适配性最大展示**：评估 FIT_CENTER vs CENTER_CROP vs PhotoView 动态 scale，解决 CENTER_INSIDE 限制最大尺寸问题
- **UI 样式美化**：页码圆角毛玻璃、旋转工具栏阴影圆角、错误布局图标、加载进度文字提示、返回按钮修复说明
- **重试与预热状态清理**：btn_retry 重置 isFirstPreheatCompleted + preheatedDomains.clear()
- **沉浸式 API 升级**：SYSTEM_UI_FLAG 废弃常量改用 WindowInsetsControllerCompat（兼容 API 30+）

### 2.3 跨播放器一致性优化

- **HeaderInjector 公共接口抽象**：长期统一视频/图片 Header/Cookie 注入机制（视频走 OkHttpDataSource.Factory，图片走 Glide RequestOptions）
- **图片错误处理对齐视频自动降级**：评估图片加载失败自动切换加载策略的可行性
- **文档同步机制强化**：源码增量功能必须同步更新 design.md ADR 章节，避免"源码先行、文档滞后"

## 3. 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| README.md | `docs/specs/player-review-and-optimization/README.md` | 功能概述（本文件） |
| spec.md | `docs/specs/player-review-and-optimization/spec.md` | 需求规约（Intent/Scope/Approach/Requirements/Scenarios） |
| design.md | `docs/specs/player-review-and-optimization/design.md` | 设计文档（ADR 决策 + 技术要点） |
| tasks.md | `docs/specs/player-review-and-optimization/tasks.md` | 实施任务清单（按 Phase 分层） |

## 4. 审查报告索引

5 份审查报告位于 `docs/temp-analysis/` 目录下：

| 报告 | 文件 | 核心发现 |
|------|------|---------|
| 视频设计审查 | `review-video-design.md` | 2 ERROR + 5 WARN + 4 INFO；URL 后缀兜底未移除与用户诉求冲突 |
| 视频代码审查 | `review-video-code.md` | 1 ERROR + 4 WARN + 6 INFO；scope 泄漏 + 3003 常量误判 |
| 图片设计审查 | `review-image-design.md` | 10 ERROR + 7 WARN + 3 INFO；5 项核心诉求未充分响应 |
| 图片代码审查 | `review-image-code.md` | 3 ERROR + 9 WARN + 3 INFO；适配器复用/WebView 预热/协程未取消 |
| 多维度交叉验证 | `review-cross-validation.md` | 2 ERROR + 5 WARN + 3 INFO；源码忠实但文档滞后 |

## 5. 背景与动机

### 5.1 用户多次批评"功能设计不是很好"

用户在 2026-07-26 期间多次批评视频/图片播放器的功能设计质量，明确要求"全面深度分析"。具体痛点：

- **视频**：URL 后缀兜底未移除，与"前置帧分析优先"诉求冲突；getMediaItem 改 suspend 影响面未审计
- **图片**：header/cookie 未复用、多线程预缓存缺失、articleStyle==2 路由回退未文档化、图片尺寸不适配、跨文章预加载失效
- **样式**：图片播放器样式简陋、返回按钮缺失、错误布局无图标
- **响应闭环**：6 条核心诉求中仅 1 条充分响应，5 条未充分响应（header/cookie/预缓存/路由回退/适配展示/预加载）

### 5.2 整合优化动机

5 份审查报告共发现 58 个问题（18 ERROR + 27 WARN + 13 INFO），分散在视频与图片两条独立优化线。但部分问题具有共性（协程生命周期、日志规范、Header/Cookie 复用机制），分散修复会导致：

- 重复设计同类方案（如协程取消机制在视频/图片各设计一次）
- 视频/图片架构一致性进一步偏离（Header/Cookie 注入机制不同）
- 文档同步成本高（design.md ADR 章节需多次补全）

因此需要整合为统一优化方案，确保共性问题统一修复、架构对齐问题统一规划、文档同步一次性完成。

## 6. 优化策略

### 6.1 优先级分层

- **P0 必须修复**：18 个 ERROR（阻断交付，含 scope 泄漏、适配器复用失效、WebView 预热覆盖、协程未取消、URL 后缀兜底、articleStyle 路由 ADR 缺失等）
- **P1 强烈建议**：影响用户体验的 WARN（图片尺寸适配、重试未清预热状态、日志规范、对齐 VideoPlay 字段）
- **P2 后续完善**：架构一致性 WARN（HeaderInjector 抽象、错误处理对齐、Alternatives 充实）
- **P3 可选优化**：INFO 级问题（Glide placeholder、setHasStableIds、冗余代码清理）

### 6.2 整合原则

- **共性问题统一修复**：协程取消机制、日志规范、Header/Cookie 复用
- **个性问题独立修复**：视频 MIME 嗅探策略、图片双 ViewPager 嵌套 Bug
- **文档同步一次性**：所有 ADR 补全、所有 spec.md 验收标准补全、所有 tasks.md 任务补全
- **真机验证必须**：按 `ai_tests/scripts/` 脚本完成 L1/L2 验证，使用测试包 `io.legado.miss.app.debug`

## 7. 已知限制

- 图片 CENTER_INSIDE 尺寸适配问题源码已改为 FIT_CENTER（R2 修订：原设计文档描述与源码不符，已修正），但 resetView 仍通过改变 scaleType 重置，需改为 PhotoView.scale = 1f 不改变 scaleType。**R3 修订**：横屏 centerCrop 会裁剪边缘，补充双击切回 fitCenter 查看完整图片交互（无内容丢失）
- 视频 design.md AD-04 缓存 key 策略与源码实现不一致（设计说去 query，源码用完整 URL），需同步设计文档
- 视频 L4 URL 后缀兜底源码实际保留但改为"不缓存"（R3 修订：明确过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除，若命中率<5% 则完全移除 L4）
- 图片 FragmentStateAdapter 改造（R2.18）需拆分 ImagePageFragment 重构内层适配器，风险较高需充分真机验证（R2 修订：建议优先实施 Bug1 简单修复，架构重写降级为 P2 长期建议）
- BasePlayerActivity 基类抽取（原方案）已废弃（R3 修订：视频/图片业务差异大，基类膨胀反模式风险高）。**R3 明确方案**：方案A（BaseBottomSheetDialog 基类，项目薄弱点）+ 方案B（PlayerControlsHelper 工具类，替代 BasePlayerActivity）双采纳
- HeaderInjector 公共接口抽象为长期建议，本期不强制实施
- GSY 视频控制器布局（video_layout_controller*.xml）的硬编码颜色清理是否纳入本期范围需在实施前确认（R2 修订：spec.md §2.2 已显式排除或纳入）

## 8. 状态标记

🔄 设计中（R3 修订完成，待用户审查）

## 9. R2 修订记录

基于多维度审查报告（review-report.md）完成以下修订：

| 修订项 | 修订前 | 修订后 |
|--------|--------|--------|
| 问题统计 | 三处口径不一致（18E+27W+13I / 32E+38W+13I / 32E+44W+32I） | 统一为 32E+44W+32I=108（含风格审查） |
| AD-01 决策 | "移除 L4 URL 后缀兜底" | "保留 L4 但不缓存"（与源码一致） |
| AD-06 Context | "源码 resetView 用 CENTER_INSIDE" | "源码已改为 FIT_CENTER，但 resetView 仍改变 scaleType" |
| AD-06 决策 | "横屏切 fitXY" | "横屏切 centerCrop，fitXY 仅作长图 fallback" |
| AD-10 颜色映射 | "#80000000 → transparent50" | "新增 transparent80/transparent70 色阶" |
| AD-12 风险 | 未充分评估 | 补充 abstract 方法清单 + 真机回归场景，建议改用扩展函数方案 |
| ADR 编号引用 | spec.md R2.1-R2.5 与 design.md AD 错位 | 统一修正（R2.1→AD-05, R2.2→AD-03, R2.3→AD-04, R2.4→AD-06） |
| 数据流图1 | 声明 4 级链，源码实际 5 级 | 增补 L4 分支与源码对齐 |
| R1.6 硬编码颜色 | 仅覆盖 8 类 | 补充至 15 类（含视频 tint 5 处） |
| R2.18 改造 | P0 强制实施 | 降级为 P2 长期建议，优先 Bug1 简单修复 |
| tasks.md 顺序 | 文档同步放最后 | 拆分到各代码修复阶段内 |
| tasks.md §9 | 无脚本引用 | 引用 ai_tests/scripts/ 具体脚本 |
| spec.md §2.2 | 与 R2.19 矛盾 | 明确区分手动三选项（本期 P0）vs 自动降级（长期 P2） |

## 10. R3 修订记录

基于 R2 修订后用户两次"需调整"未指定详情的深度审查，识别 R2 修订回避了用户核心矛盾，完成以下修订：

| 修订项 | R2 状态 | R3 修订后 | 修订理由 |
|--------|---------|----------|---------|
| **AD-01 L4 决策** | "保留 L4 不缓存（与源码一致）"——回避用户核心矛盾 | **过渡计划**：本期保留 L4 不缓存作安全网，下版本（v1.x+1）基于 L4 命中率数据（logcat 统计）评估完全移除，若命中率<5% 则完全移除 | 用户两次明确批评"为什么还会走到 url 兜底"，本质要"移除 L4"而非"保留不缓存"；R2 用"文档对齐源码"回避了"用户真正想要的功能改进" |
| **AD-06 横屏交互** | 横屏切 centerCrop，但未补充"如何查看被裁剪部分" | 补充**双击切换 fitCenter ↔ centerCrop** 查看完整图片；双指缩放/拖动查看裁剪部分 | centerCrop 会裁剪边缘内容，需补充查看交互避免内容丢失 |
| **AD-12 方案选择** | "方案A BaseBottomSheetDialog + 方案B PlayerControlsHelper"两方案并存未明确 | **明确双采纳**：方案A（BaseBottomSheetDialog 基类）+ 方案B（PlayerControlsHelper 工具类）；**废弃** BasePlayerActivity 基类抽取原方案 | R2 两方案并存导致 tasks.md 13.x 易混淆，R3 明确选择消除歧义 |
| **tasks.md 9.2 脚本引用** | 引用 `l2_verify_video_player.py --scenario sniff`，但脚本实际未支持 sniff 子场景 | 改为 `quick_build_install.py` + `import_rss_source.py` + 直接 `adb logcat` Grep；补充 L4 命中率统计验证 | 脚本能力与文档引用不符，导致测试验证不能闭环 |
| **spec.md §3.2 方案E** | "保留 L4 即违反核心诉求"否决，但 R2 决策与方案E 否决理由冲突 | 修订否决理由：R2 "保留不缓存"虽对齐源码但回避核心矛盾，R3 "过渡计划+下版本评估"采纳 | 消除 R2 决策与方案E 否决理由的逻辑冲突 |
| **spec.md §1 诉求1 状态** | "视频设计仍保留 L4，未充分响应" | "R3 修订：过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除（响应核心矛盾）" | 反映 R3 决策对用户核心矛盾的响应 |
| **spec.md §6 矩阵诉求1** | "R1.1（保留 L4 不缓存）" | "R1.1（R3 修订：过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除）" | 矩阵与 R3 决策对齐 |
| **spec.md §3.3 Drawbacks 第3条** | "L4 不缓存与源码实际状态一致" | "R3 修订：过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除" | Drawbacks 与 R3 决策对齐 |
| **README.md §7 已知限制** | "保留 L4 但不缓存（与源码一致）" | "R3 修订：明确过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除，若命中率<5% 则完全移除 L4" | README 与 R3 决策对齐 |
