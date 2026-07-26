# 视频/图片播放器审查与优化整合 spec

> 状态：✅ R4 修订完成，已开始实施（用户2026-07-26 15:38 审查通过，视频+图片全部实施，顺序：视频P0→视频P1→图片P0→图片P1）
> **R4 修订（核心能力提升）**：从"5 级识别链+L4 保留/移除之争"升级为"7 维度交叉验证+MediaSource 智能选择+降级链"，对齐浏览器五层架构。完整方案见 [R4-enhancement-plan.md](./R4-enhancement-plan.md)
> 来源：review-video-design.md / review-video-code.md / review-image-design.md / review-image-code.md / review-cross-validation.md / review-video-architecture-style.md / review-image-vs-video-style.md / review-project-ui-style-guide.md / review-report.md
> 问题统计：32 个 ERROR + 44 个 WARN + 32 个 INFO（合计 108 项，含架构风格一致性审查新增 14 ERROR + 11 WARN）
> R2 修订：基于多维度审查报告（review-report.md）修复 14 P0 + 12 P1 + 11 P2 问题
> R3 修订：基于 R2 后用户两次"需调整"深度审查，识别 R2 回避用户核心矛盾，明确 AD-01 L4 过渡计划+下版本评估完全移除 / AD-06 横屏双击切回 fitCenter / AD-12 明确方案B 采纳+废弃 BasePlayerActivity / tasks.md 9.2 修正脚本引用

## 1. Intent（意图）

用户多次批评视频/图片播放器"功能设计不是很好"，并要求"全面深度分析"。本 spec 整合 8 份审查报告 + 1 份多维度审查整合报告（review-report.md）发现的 32 个 ERROR + 44 个 WARN + 32 个 INFO（合计 108 项）问题，形成统一的视频/图片播放器优化方案，确保用户核心诉求 100% 落地。

**整体架构风格一致性诉求**（2026-07-26 13:25 用户反馈）：站在整个项目整体架构角度，审视为什么内置图片播放器风格和视频播放器风格不一样，以及视频播放器里面的功能按钮、弹框风格是否和项目整体风格一致。要求统一视频/图片播放器的 UI 风格、功能按钮、弹框风格，确保与项目整体风格（TitleBar 主题色体系 / alert DSL / BaseDialogFragment 基类 / WindowInsetsControllerCompat 沉浸式 API / 4dp Grid 间距 / M3 圆角规范）完全对齐。基于 3 份架构风格审查报告（review-video-architecture-style.md / review-image-vs-video-style.md / review-project-ui-style-guide.md）新增 14 个 ERROR + 11 个 WARN。

**用户核心诉求清单**（基于项目记忆 + 交叉验证报告 §2）：

| # | 用户原话摘要 | 当前响应状态 |
|---|------------|------------|
| 1 | "为什么还会走到 URL 兜底正则匹配" | R3 修订：过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除（响应核心矛盾） |
| 2 | "嗅探完要去获取前置帧分析视频类型" | L2/L3 已实现 |
| 3 | "移除 L1.5 URL 后缀检测，所有 URL 都应先做前置帧分析" | L1.5 已移除，L4 兜底仅作安全网 |
| 4 | "嗅探准确性 > 性能" | 部分响应（保留 L4 安全网，但 R3 补充下版本评估机制） |
| 5 | "图片加载不出来，考虑复用 header/cookie" | 源码已实现，但 design.md 缺 ADR |
| 6 | "用户改成网页模式别自动转为图片查看器" | 源码已回退，但 design.md 完全未记录 |
| 7 | "图片不是适配性最大尺寸展示" | R3 修订：横屏 centerCrop + 双击切回 fitCenter 查看完整图片 |
| 8 | "上下滑动切换时下一个图片内容无法加载" | 源码已实现预加载，design.md 未同步 |
| 9 | "样式真他妈的丑 + 没有返回按钮" | 返回按钮已修复，UI 样式未美化 |
| 10 | "为什么图片播放器风格和视频播放器不一样，视频功能按钮弹框是否和项目整体风格一致" | 架构风格审查已完成，新增 14 ERROR + 11 WARN 待修复 |

## 2. Scope（范围）

### 2.1 在范围内（必须覆盖）

> R2 修订：明确 selectableItemBackgroundBorderless 改造范围仅限图片播放器（activity_image_gallery.xml + item_image_page.xml），不影响项目其他模块（dialog_read_aloud.xml / dialog_book_change_source.xml 等）的 selectableItemBackgroundBorderless 使用。

**视频播放器**：
- 视频 MIME 嗅探优化（移除 URL 后缀兜底，改为返回 null 让 ExoPlayer 内置 sniff 尝试）
- 视频 ExoPlayer 协程生命周期管理（Exo2MediaPlayer.scope 泄漏修复）
- 视频 3003 常量误判修复（PlaybackException.ERROR_CODE_PARSING_BITSTREAM_MALFORMED）
- 视频 getMediaItem 改 suspend 影响面审计
- 视频日志规范化（Log.d/Log.e → AppLog.put）
- 视频 design.md AD-02 修订（4 级识别链）+ AD-04 缓存 key 策略修订
- 视频 Drawbacks 补充"URL 后缀兜底误判"风险

**图片播放器**：
- 图片 header/cookie 复用 ADR 补全（design.md 新增 AD-07）
- 图片多线程预缓存设计（design.md 新增 AD-08，对齐 VideoPlay.preloadedArticles）
- 图片 articleStyle==2 路由回退决策文档化（design.md 新增 AD-06）
- 图片尺寸适配性最大展示（scaleType 策略：FIT_CENTER vs CENTER_CROP 评估）
- 图片跨文章预加载设计（design.md 新增章节，对齐 VideoPlay.preloadNextArticleHtml）
- 图片适配器复用 Bug 修复（ImageArticlePagerAdapter.bind else 分支）
- 图片 WebView 预热循环覆盖 Bug 修复（改为串行队列）
- 图片协程未取消 Bug 修复（loadArticleContent 用 Job 跟踪）
- 图片 Scenarios 补全两个核心场景（手动网页模式 + 防盗链重试）
- 图片 ADR Status 修正（Proposed → Accepted，已落地决策）
- 图片 spec.md R3.1/R3.4 与代码/任务统一
- 图片 tasks.md 补全 5 项缺失任务
- 图片返回按钮修复文档化（design.md 新增章节）
- 图片 4 级兜底解析策略文档化（design.md 新增 AD-08 解析策略）

**架构风格一致性**（基于 3 份风格审查报告新增）：
- 视频播放器架构风格对齐项目规范（VideoFragment 改继承 VMBaseFragment / VideoSettingsPanel 改继承 BaseDialogFragment / 清除硬编码颜色 #1A2B4A/#8AB4F8/#000000 / 清除 Log.d 残留 / 协程改 Coroutine.async{} 链式封装 / legacyContainer 整体清理）
- 图片播放器风格对齐视频播放器（TitleBar 主题色对齐移除 #80000000 硬编码 / AlertDialog 改走 alert DSL + applyTint() / 按钮背景统一 bg_rotate_toolbar → bg_overlay_button 24dp → 12dp 圆角 / 沉浸式 API 统一 window.setFlags → toggleSystemBar/WindowInsetsControllerCompat / 圆角规范统一 24dp/12dp 混用 → 12dp）
- 提取 BaseBottomSheetDialog 基类（统一 BottomSheet 样式：圆角 16dp + drag_handle_bg + 主题背景，视频/图片/项目其他 BottomSheet 共享）+ 通用沉浸式播放器基类（视频/图片共用：toggleSystemBar + scheduleAutoHide + hideControlsAnimated + showControlsAnimated 封装）

### 2.2 不在范围内（明确排除）

> R2 修订：明确区分手动三选项降级链（本期 P0）vs 自动降级（长期 P2），消除原 §2.2 与 R2.19 的语义矛盾。

- 音频路径（AudioPlayService）的 MIME 嗅探改造（暂缓，音频路径不嗅探可接受）
- 视频播放器主体 UI 重写（主体架构合理：VMBaseActivity+TitleBar+alert DSL，仅修复 Fragment/BottomSheet 基类继承+硬编码颜色+Log.d+协程封装，不重写主体 UI）
- 图片播放器主体架构重写（双 ViewPager2 + ImagePlay 单例已落地保留，R2.18 FragmentStateAdapter 改造降级为 P2 长期建议，本期仅实施 Bug1 简单修复）
- 新增功能开发（如音频播放器、字幕支持等）
- 视频/图片 Header/Cookie 公共接口抽象（长期建议，本期不实施）
- 图片错误处理**自动**降级对齐视频（长期 P2，本期仅手动三选项降级链：alert {} 重试/浏览器打开/复制URL）
- GSY 视频控制器布局（video_layout_controller.xml / video_layout_controller_full.xml）的硬编码颜色清理（GSY 第三方组件布局，本期不修改，避免影响 GSY 内部逻辑）
- 项目其他模块的 selectableItemBackgroundBorderless 使用（仅图片播放器范围改造）

## 3. Approach（方案）

### 3.1 Selected Approach（选定方案）

**分层修复策略**：
1. **第一层**：修复 32 个 ERROR 级问题（阻断交付，含 14 个架构风格 ERROR）
2. **第二层**：修复 44 个 WARN 级关键项（影响用户体验，含 11 个架构风格 WARN）
3. **第三层**：处理 32 个 INFO 级问题（可选优化）

每个修复必须基于审查报告的具体证据（含文件路径+行号），修复后必须更新对应设计文档（design.md ADR 章节）。**代码修复与文档同步进行，禁止"先改代码后补文档"**（R2 修订：tasks.md 已将文档同步拆分到各代码修复阶段内，阶段 8 仅保留全局索引同步）。

**修复优先级**（按用户诉求紧迫度，R2 修订分批策略）：
- **P0-A 功能修复**（第一批）：18 个原功能 ERROR（视频 3 + 图片 13 + 交叉验证 2），用户最痛问题优先解决
- **P0-B 风格统一**（第二批）：14 个架构风格 ERROR（视频 6 + 图片 8），整体架构风格一致性诉求
- **P1**：44 个 WARN 中影响用户体验的关键项（如图片尺寸适配、UI 样式、ADR Status、架构风格统一）
- **P2**：32 个 INFO 级优化项（含 R2.18 FragmentStateAdapter 改造降级）

### 3.2 Alternatives Considered（否决的替代方案）

| 替代方案 | 否决理由 |
|---------|---------|
| 方案A：仅修复 ERROR，保留 WARN/INFO | 否决：WARN 中包含图片尺寸适配未真正修复等用户直接感知的问题，不修复会再次被批评 |
| 方案B：整体重写图片播放器 | 否决：用户要求"参考视频播放器架构"而非重写，且核心架构（双ViewPager2+ImagePlay单例）已落地，仅需补全缺失功能 |
| 方案C：仅更新设计文档不改代码 | 否决：存在 3 个图片代码 ERROR Bug（适配器复用/WebView预热/协程取消）+ 1 个视频代码 ERROR（scope 泄漏）必须修复 |
| 方案D：分两个独立 OpenSpec 任务 | 否决：视频和图片播放器在 header/cookie 复用、预缓存、错误处理上存在架构一致性需求，合并处理避免重复设计 |
| 方案E：保留 L4 URL 后缀兜底，仅文档说明 | R3 修订否决理由：R2 选择"保留 L4 不缓存"虽对齐源码但回避用户核心矛盾，R3 改为"过渡计划"——本期保留 L4 不缓存作为安全网（防止 L2/L3 失败场景完全无法播放），下版本（v1.x+1）基于 L4 命中率数据（logcat 统计）评估完全移除。若命中率<5% 则下版本完全移除 L4，返回 null 让 ExoPlayer Extractor.sniff() 尝试。原方案E "仅文档说明不改进"否决（未真正改进），R3 "过渡计划+下版本评估"采纳 |
| 方案F：仅统一颜色，保留架构差异 | 否决：图片用 RecyclerView.Adapter 嵌套 ViewPager2 易内存泄漏（每个 ViewHolder 持有内层 adapter 引用，复用时重建 adapter），必须改为 FragmentStateAdapter + Fragment 拆分解耦生命周期；仅改颜色不解决架构隐患 |
| 方案G：重写视频播放器UI | 否决：视频播放器主体架构合理（VMBaseActivity+TitleBar+alert DSL+四级降级链），仅需修复 Fragment/BottomSheet 基类继承+硬编码颜色+Log.d+协程封装，重写将破坏已验证可用的播放/降级/PiP 功能，风险收益比不合理 |

### 3.3 Drawbacks（选定方案的缺点）

1. **修复范围较大**（32 ERROR + 44 WARN + 32 INFO=108 项），实施周期较长
2. **部分修复需要真机验证**（如图片尺寸适配、WebView 预热、协程取消、亮/暗主题切换、沉浸式 API），增加测试成本
3. **视频 URL 后缀兜底保留但不缓存（R3 修订：过渡计划）**——本期保留 L4 不缓存作为安全网（防止 L2/L3 失败场景完全无法播放），下版本（v1.x+1）基于 L4 命中率数据（logcat 统计 `L4 suffix fallback used` 出现次数 / 总嗅探次数）评估完全移除。若命中率<5% 则下版本完全移除 L4。过渡期 magic number 失败场景仍可能误判，但"不缓存"避免误判固化，可重试嗅探
4. **图片 articleStyle==2 回退决策**需同步更新 spec/design/tasks 三文档，文档同步成本高
5. **图片 4 级兜底解析策略文档化**后，design.md 篇幅增加，可读性略降
6. **视频 getMediaItem 改 suspend 影响面审计**可能发现额外调用方需改造，工作量不可预估
7. **图片 FragmentStateAdapter 改造（R2.18）已降级为 P2**（R2 修订：本期仅实施 Bug1 简单修复，架构重写降为长期建议），降低实施风险
8. **提取 BaseBottomSheetDialog 基类（R4.37）**影响视频/图片及项目其他 BottomSheet，需回归验证无样式回归；**BasePlayerActivity 基类抽取（AD-12）高风险**（R2 修订：建议改用扩展函数+工具类方案，避免基类膨胀反模式）

## 4. Requirements（需求，按优先级）

### 4.1 P0 必须（32 个 ERROR）

> R2 修订：分批策略声明——P0-A 功能修复（18 项）优先实施，P0-B 风格统一（14 项）第二批实施。tasks.md 阶段 11-12 已前移至阶段 7 之后、阶段 8 文档同步之前。

#### 视频 P0（3 项）

**R1.1 URL 后缀兜底保留但不缓存（R3 过渡计划）**（视频设计 E-1，R3 修订）
- 需求：5 级识别链保留 L4 URL 后缀兜底但**不缓存**（与源码实际状态一致），L1.5 URL 后缀快速路径已移除。**R3 修订**：本期保留 L4 不缓存作为安全网（防止 L2/L3 失败场景完全无法播放），下版本（v1.x+1）基于 L4 命中率数据（logcat 统计 `L4 suffix fallback used` 出现次数 / 总嗅探次数）评估完全移除。若命中率<5% 则下版本完全移除 L4，返回 null 让 ExoPlayer Extractor.sniff() 尝试。
- 验证：Grep `getMimeType(url)` 在 sniffMimeType 函数内仍有调用（L4 兜底）；L4 兜底结果不写入 MimeSnifferCache（注释 `P0-2 修复：URL 后缀兜底结果不缓存`）；logcat 统计 L4 命中率（R3 新增）
- 文件：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt:127-136`

**R1.2 getMediaItem 改 suspend 影响面审计**（视频设计 E-2）
- 需求：审计 `AnalyzeUrl.getMediaItem()` 所有调用方，确保协程上下文；列出 AudioPlayService/VideoPlay 等调用点
- 验证：tasks.md 新增"审计 getMediaItem 调用方"任务；调用方清单完整
- 文件：`app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt`

**R1.3 Exo2MediaPlayer scope 泄漏修复**（视频代码 E1）
- 需求：重写 `release()`，调用 `scope.cancel()` + `currentSniffJob = null` 后 `super.release()`
- 验证：Exo2MediaPlayer.kt 重写 release()；Activity 销毁后协程立即取消
- 文件：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt:57`

#### 视频架构风格 P0（6 项，基于 review-video-architecture-style.md）

**R1.4 VideoFragment 改继承 VMBaseFragment**（视频架构 E1）
- 需求：VideoFragment 从直接 `Fragment()` 改为继承项目 `VMBaseFragment`/`BaseFragment`，引入 ViewBinding delegate 替换 findViewById，复用基类 observeLiveBus 机制
- 验证+文件：VideoFragment.kt 不再直接继承 Fragment()；Grep "findViewById" 无残留；`ui/video/VideoFragment.kt:49`

**R1.5 VideoSettingsPanel 改继承 BaseDialogFragment**（视频架构 E2）
- 需求：VideoSettingsPanel 从直接 `BottomSheetDialogFragment` 改为继承项目 `BaseDialogFragment`（或新增 BaseBottomSheetDialog 基类），复用 E-Ink 适配、backgroundColor 主题统一、onDismissListener 能力
- 验证+文件：VideoSettingsPanel.kt 不再直接继承 BottomSheetDialogFragment；主题背景跟随 ThemeStore；`ui/video/VideoSettingsPanel.kt:48`

**R1.6 视频清除硬编码颜色**（视频架构 E3/E4，R2 修订：补充至 15 类）
- 需求：清除视频模块所有硬编码颜色，对齐项目主题色板
- 修订内容（共 15 类）：
  - `fragment_video.xml:17` 根布局 `#000000` → `?attr/colorBackground`
  - `activity_video_player.xml:64` legacyContainer `#1A2B4A` → `@color/background_card`
  - `activity_video_player.xml:72` legacyContainer `#8AB4F8` → `@color/secondaryText`
  - `activity_video_player.xml:298` `#80000000` → `@color/transparent80`（新增色阶）
  - `activity_video_player.xml:310` `#FFFFFF` → `@color/primaryText`
  - `switch_episode_video_dialog.xml:5` `#80121212` → `@color/transparent80`
  - `switch_episode_video_dialog.xml:24,25,29` `#00000000` → `@color/transparent100`（新增色阶）
  - `switch_speed_video_dialog.xml:15,16,18` `#00000000` → `@color/transparent100`
  - `switch_video_dialog_item.xml:12` `#FFFFFF` → `@color/primaryText`
  - `fragment_video.xml:52,86,172,188,201` `android:tint="#FFFFFF"` → `app:tint="@color/white"`（R4.35 扩展视频覆盖）
  - `WebViewVideoPlayer.kt:57` `Color.BLACK` → `ContextCompat.getColor(context, R.color.background)`
  - **排除**：`video_layout_controller.xml` / `video_layout_controller_full.xml`（GSY 第三方组件布局，spec.md §2.2 已显式排除）
- 验证：Grep "#1A2B4A\|#8AB4F8\|#000000\|#FFFFFF\|#80000000\|#00000000\|#80121212\|Color.BLACK" 在视频模块（排除 GSY 布局）无残留；亮/暗主题切换颜色跟随

**R1.7 视频清除 Log.d 残留**（视频架构 E5）
- 需求：VideoPlayerActivity.kt 中 3 处 `android.util.Log.d` 替换为 `AppLog.put()`
- 验证+文件：Grep "android.util.Log.d" 在 ui/video/ 目录无残留；`VideoPlayerActivity.kt:280,853,874`

**R1.8 视频协程改 Coroutine.async{} 链式封装**（视频架构 E6）
- 需求：将 `lifecycleScope.launch` + `try/catch` 模式改为项目自定义 `Coroutine.async{}.onError{}.onSuccess{}` 链式封装（AGENTS.md Code Style 核心条目）
- 验证+文件：Grep "lifecycleScope.launch" 在 ui/video/ 评估必要性；协程封装符合项目规范；`VideoPlayerActivity.kt:217,509` 等

**R1.9 视频 legacyContainer 整体清理**（视频架构 改进建议14）
- 需求：删除 activity_video_player.xml 中已废弃的 legacyContainer 布局（line 30-315）+ VideoPlayerActivity.kt 中 useViewPagerMode=true 硬编码后的旧模式代码分支，减少维护负担
- 验证+文件：Grep "legacyContainer" 在视频布局/代码无残留；旧模式代码路径已删除；`activity_video_player.xml:30-315`、`VideoPlayerActivity.kt:121`

#### 图片 P0（13 项）

**R2.1 articleStyle==2 路由回退 ADR 补全**（图片设计 E1 + 交叉验证 E-01，R2 修订 ADR 编号）
- 需求：design.md 新增 **AD-05**，复述 ReadRss.kt L41-43 的回退逻辑（R2 修订：原引用 AD-06 错位，实际 AD-05 才是路由回退）
- 验证：design.md 包含 AD-05，Status=Accepted；明确"用户主动选择网页模式时走 ReadRssActivity"

**R2.2 header/cookie 复用 ADR 补全**（图片设计 E2，R2 修订 ADR 编号）
- 需求：design.md 新增 **AD-03**，说明 sourceOriginOption 来源（订阅源 sourceUrl）、refererOption 兜底机制（R2 修订：原引用 AD-07 错位，实际 AD-03 才是 header/cookie 复用）
- 验证：design.md 包含 AD-03；引用 OkHttpStreamFetcher.kt L71-94 实现路径

**R2.3 多线程预缓存 ADR 补全**（图片设计 E3，R2 修订 ADR 编号）
- 需求：design.md 新增 **AD-04**，参考 VideoPlay.preloadNextArticleHtml，设计 ImagePlay.preloadNextArticleImages（R2 修订：原引用 AD-08 错位，实际 AD-04 才是多线程预缓存）
- 验证：design.md 包含 AD-04；明确协程 async 预加载下一篇文章图片 URL 列表

**R2.4 图片适配性最大尺寸展示设计**（图片设计 E4 + 交叉验证 E-02/W-03，R2 修订 ADR 编号 + Context 修正）
- 需求：design.md 新增 **AD-06**，明确 scaleType 策略（FIT_CENTER vs CENTER_CROP 评估）；resetView 不再用 scaleType 改变；R2 修订：源码实际已用 FIT_CENTER（非 CENTER_INSIDE），但 resetView 仍改变 scaleType，需改为 PhotoView.scale = 1f
- 验证：design.md 包含 AD-06；源码 ImagePageAdapter.kt L165 使用 FIT_CENTER；resetView 不再改变 scaleType

**R2.5 跨文章预加载设计**（图片设计 E5）
- 需求：design.md "技术要点" 新增章节，参考 VideoPlay.preloadNextArticleHtml，设计 ImageGalleryViewModel.preloadNextArticle
- 验证：design.md 包含跨文章预加载设计；触发时机+缓存策略明确

**R2.6 spec.md R3.1 与实际代码统一**（图片设计 E6）
- 需求：修正 R3.1 为"type==1 且用户未手动选择网页模式时启动 ImageGalleryActivity；用户手动选择网页模式时走 ReadRssActivity"
- 验证：spec.md R3.1 与 ReadRss.kt L41-43 实际代码一致

**R2.7 spec.md R3.4 与 design.md AD-05 / tasks.md 3.4 统一**（图片设计 E7）
- 需求：统一为"ruleContent 为空时用 article.link 作为单图URL，仍启动 ImageGalleryActivity（隐藏页码）"
- 验证：spec.md R3.4 / design.md AD-05 / tasks.md 3.4 三处表述一致

**R2.8 Scenarios 补充"用户手动选择网页模式"场景**（图片设计 E8）
- 需求：spec.md 新增 Scenario 6（用户将图片订阅源改为网页模式 → 走 ReadRssActivity）
- 验证：spec.md Scenarios 包含该场景；验证回退逻辑

**R2.9 Scenarios 补充"图片防盗链失败重试"场景**（图片设计 E9）
- 需求：spec.md 新增 Scenario 7（图片加载失败 → 注入 Referer/***>重试 → 成功显示）
- 验证：spec.md Scenarios 包含该场景；验证 4 级兜底解析

**R2.10 tasks.md 补全 5 项关键任务**（图片设计 E10，R2 修订任务编号）
- 需求：新增任务 4.1 header/cookie 复用（对应 AD-03）；4.2 多线程预缓存（对应 AD-04）；4.3 articleStyle==2 路由回退（对应 AD-05）；4.4 图片适配性最大尺寸（对应 AD-06）；4.5 跨文章预加载（对应新章节）（R2 修订：原引用 2.17/2.18/2.19/2.20/3.6 与 tasks.md 实际编号错位，已修正为 4.1-4.5）
- 验证：tasks.md 包含 5 项新任务（4.1-4.5）；每项有验证步骤；R 编号↔任务编号映射表已新增

**R2.11 ImageArticlePagerAdapter 适配器复用 Bug 修复**（图片代码 Bug1）
- 需求：`else` 分支改为 `imagePageAdapter?.updateSource(sourceOrigin, referer)` 而非新建
- 验证：ImageArticlePagerAdapter.kt L95-103 else 分支不再新建 adapter
- 文件：`app/src/main/java/io/legado/app/ui/image/ImageArticlePagerAdapter.kt`

**R2.12 WebView 预热循环覆盖 Bug 修复**（图片代码 Bug2）
- 需求：改为串行预热（一个域名 onPageFinished 后再加载下一个），或用多个 WebView 实例并行预热
- 验证：ImageGalleryActivity.kt L169-173 不再循环 loadUrl；多域名场景全部预热
- 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryActivity.kt`

**R2.13 ViewModel.loadArticleContent 协程取消 Bug 修复**（图片代码 Bug3）
- 需求：在 `loadArticleContent` 入口取消上一个协程（用 `Job` 跟踪），或用 `Flow` + `collectLatest` 替换
- 验证：ImageGalleryViewModel.kt L57-127 包含 `loadJob?.cancel()`；快速切换文章无数据错乱
- 文件：`app/src/main/java/io/legado/app/ui/image/ImageGalleryViewModel.kt`

#### 图片架构风格 P0（8 项，基于 review-image-vs-video-style.md）

**R2.14 图片 TitleBar 颜色硬编码改主题色**（图片vs视频 E1）
- 需求：移除 ImageGalleryActivity.initTitleBar() 中 setBackgroundColor(Color.parseColor("#80000000")) + setTextColor(Color.WHITE) 硬编码，改用 TitleBar 默认主题机制（primaryColor/primaryTextColor）；若需深色背景用 app:themeMode="1"
- 验证+文件：Grep "Color.parseColor\|Color.WHITE" 在 ImageGalleryActivity 无残留；TitleBar 颜色跟随主题；`ImageGalleryActivity.kt` initTitleBar

**R2.15 图片 AlertDialog 改走 alert DSL + applyTint()**（图片vs视频 E2/E8）
- 需求：长按菜单从 AlertDialog.Builder().setItems() 改为 alert {} DSL；错误兜底从 tvError+btnRetry 内嵌布局改为 alert {} 四级降级（重试/浏览器打开/复制URL）
- 验证+文件：Grep "AlertDialog.Builder" 在 ImageGalleryActivity 无残留；alert {} 自动应用 applyTint()；`ImageGalleryActivity.kt`

**R2.16 图片按钮背景统一**（图片vs视频 E3/E4/E6）
- 需求：旋转工具栏容器和按钮从 bg_rotate_toolbar（24dp 圆角+#B3000000）改为 bg_overlay_button（12dp 圆角+#80000000）；移除 selectableItemBackgroundBorderless 改用 bg_overlay_button
- 验证+文件：Grep "bg_rotate_toolbar\|selectableItemBackgroundBorderless" 在图片布局无残留；圆角统一 12dp；`bg_rotate_toolbar.xml`、`activity_image_gallery.xml`

**R2.17 图片沉浸式 API 统一**（图片vs视频 E5）
- 需求：toggleImmersive() 从 window.setFlags(FLAG_LAYOUT_NO_LIMITS) + systemUiVisibility（API 30+ 废弃）改为 toggleSystemBar(show) 工具方法（WindowInsetsControllerCompat）
- 验证+文件：Grep "FLAG_LAYOUT_NO_LIMITS\|systemUiVisibility" 在 ImageGalleryActivity 无残留；使用 toggleSystemBar；`ImageGalleryActivity.kt` toggleImmersive

**R2.18 图片架构模式统一**（图片vs视频 E7，R2 修订：降级为 P2 长期建议）
- 需求：R2 修订——本期仅实施 Bug1 简单修复（else 分支改 updateSource，见 R2.11），架构重写（FragmentStateAdapter + Fragment 拆分）降级为 P2 长期建议
- 理由：当前 Bug1 可通过简单 updateSource 修复，无需架构重写；Fragment 生命周期复杂，风险收益比不合理；若未来确需改造需配套真机回归测试覆盖快速滑动/横竖屏切换/内存泄漏
- 验证：R2.11 Bug1 修复后适配器复用生效；架构重写列入 P2 长期建议清单

**R2.19 图片错误降级链补全**（图片vs视频 E8）
- 需求：图片加载失败时用 alert {} 提供"重试"/"浏览器打开"/"复制URL"三选项，对齐视频四级降级链（ExoPlayer→WebView→系统浏览器）
- 验证+文件：图片错误时弹出 alert {} 对话框；提供三个操作入口；`ImageGalleryActivity.kt`/`ImagePageFragment.kt`

**R2.20 图片按钮点击效果统一**（图片vs视频 E4）
- 需求：按钮从 selectableItemBackgroundBorderless（透明+水波纹）改为 bg_overlay_button（半透明黑底），与视频按钮一致，解决浅色图片上按钮不可见问题
- 验证+文件：Grep "selectableItemBackgroundBorderless" 在图片布局无残留；按钮有半透明背景；`activity_image_gallery.xml`、`item_image_page.xml`

**R2.21 图片圆角规范统一**（图片vs视频 E6）
- 需求：旋转工具栏圆角从 24dp 改为 12dp，与页码指示器（12dp）和视频（12dp）统一
- 验证+文件：bg_rotate_toolbar 圆角改为 12dp；图片内部圆角统一 12dp；`bg_rotate_toolbar.xml`

#### 交叉验证 P0（2 项）

**R3.1 图片 design.md 返回按钮修复文档化**（交叉验证 E-02）
- 需求：design.md 新增"返回按钮修复"章节，记录 setSupportActionBar 时序问题+三重保障
- 验证：design.md 包含返回按钮修复说明；引用 ImageGalleryActivity.initTitleBar L199-207

**R3.2 视频 3003 常量误判修复**（视频代码 W1 提级）
- 需求：`isUnrecoverableError` 条件加入 `error.errorCode == PlaybackException.ERROR_CODE_PARSING_BITSTREAM_MALFORMED`；删除 L339 错误注释
- 验证：Exo2MediaPlayer.kt L340-343 包含 3003 常量；bitstream malformed 错误触发自动降级
- 文件：`app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`

### 4.2 P1 应该（38 个 WARN 中的关键项）

**视频 P1（5 项）**：
- R4.1 Drawbacks 补充"URL 后缀兜底误判"风险（视频设计 W-1）
- R4.2 缓存 key 用 URL path 去除 query 风险评估，改为"完整 URL hash"或"path + 关键 query"（视频设计 W-2/W-5）
- R4.3 review-report-v2 补 v3 设计层审查（视频设计 W-3）
- R4.4 任务 4.9/7.4 补充测试构造方法+测试源清单（视频设计 W-4）
- R4.5 视频日志统一规范：Log.d/Log.e → AppLog.put（视频代码 W2/W3/W4）

**图片 P1（7 项）**：
- R4.6 所有 ADR Status 修正为 Accepted（已落地决策）（图片设计 W1）
- R4.7 tasks 7.2 真实源名称改为"图片订阅源[N]"代号（图片设计 W2）
- R4.8 tasks 补充"返回按钮"任务（虽然已实现，任务清单应记录）（图片设计 W3）
- R4.9 tasks 补充"UI 样式美化"任务（配色/图标/间距）（图片设计 W4）
- R4.10 Alternatives Considered 扩充优劣对比矩阵（图片设计 W5）
- R4.11 Drawbacks 补充：单例生命周期风险+双 ViewPager2 性能风险+维护成本（图片设计 W6）
- R4.12 README.md L9 问题陈述同步改造后状态（图片设计 W7）

**图片代码 P1（6 项）**：
- R4.13 ImagePlay 新增 currentPlayHeaders + preloadedArticles 字段，对齐 VideoPlay（图片代码 Bug4）
- R4.14 resetView 改用 PhotoView.reset() 或 setScale(1f)，不再用 scaleType 改变（图片代码 Bug5）
- R4.15 删除 onDestroy WebView 清理冗余代码（webChromeClient=null/removeJavascriptInterface）（图片代码 Bug6）
- R4.16 修正 ImagePlay.clear() 注释误导（图片代码 Bug7）
- R4.17 SYSTEM_UI_FLAG_* 升级为 WindowInsetsControllerCompat（图片代码 Bug8）
- R4.18 错误重试清理预热状态（isFirstPreheatCompleted=false）（图片代码 Bug9）

**交叉验证 P1（5 项）**：
- R4.19 视频 design.md AD-02 显式声明"L1.5 已移除，L4 仅兜底且不缓存"（交叉验证 W-01）
- R4.20 图片 design.md 同步源码增量功能（WebView 预热方案 A / 4 级兜底解析 / 跨文章预加载 / 返回按钮修复）（交叉验证 W-02）
- R4.21 图片尺寸适配真机验证（FIT_CENTER vs CENTER_CROP）（交叉验证 W-03）
- R4.22 视频/图片 Header/Cookie 复用机制文档化差异（短期可接受，长期抽象公共接口）（交叉验证 W-04）
- R4.23 图片错误处理对齐视频自动降级评估（短期手动重试优化，长期评估自动降级）（交叉验证 W-05）

**视频代码 P1（4 项）**：
- R4.24 视频代码 W1 已提级为 R3.2（3003 常量误判）
- R4.25 INFO 项处理：createMediaItem getMimeType 冗余保留+注释说明（视频代码 I1）
- R4.26 INFO 项处理：if(!isActive) 冗余删除（视频代码 I2）
- R4.27 INFO 项处理：response.code != 200 冗余简化（视频代码 I3）

**架构风格 P1（11 项，基于 3 份风格审查报告）**：
- R4.28 视频三套按钮风格统一为 2 套（VideoCtrlButton/VideoPanelButton/悬浮按钮 → 保留悬浮+面板，废弃 VideoCtrlButton）（视频架构 W1）
- R4.29 视频字号硬编码改 dimen（11sp/12sp/13sp → font_size_normal 或新增 font_size_xs）（视频架构 W3）
- R4.30 视频间距硬编码改 spacing_* dimen（4dp/8dp/12dp/16dp → spacing_xs/sm/md/lg）（视频架构 W9）
- R4.31 视频 PopupMenu 主题化（ContextThemeWrapper + R.style.Style_PopupMenu）（视频架构 W4）
- R4.32 视频全屏返回按钮统一用项目组件（评估保留 TitleBar 隐藏标题或抽取 FullScreenBackButton）（视频架构 W5）
- R4.33 图片自动隐藏+动画（参考 VideoFragment.scheduleAutoHide(3000L) + alpha + translationY 300ms 淡入淡出）（图片vs视频 W3/W6）
- R4.34 图片返回按钮统一 onBackPressedDispatcher（setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }）（图片vs视频 W1）
- R4.35 tint 写法统一 app:tint（R2 修订：扩展视频覆盖，图片+视频均改为 app:tint="@color/white"）（图片vs视频 W2）
- R4.36 图片 longSnackbar 引入（保存图片/分享等可能误操作场景提供撤销入口）（图片vs视频 W4）
- R4.37 提取 BaseBottomSheetDialog 基类（统一 BottomSheet 样式：圆角 16dp + drag_handle_bg + 主题背景，VideoSettingsPanel/HighlightStyleDialog/NumberPickerDialog/BottomWebViewDialog 共享；R2 修订：分阶段实施，先 VideoSettingsPanel + 1 个播放器 BottomSheet 继承验证无回归后再推广）
- R4.38 提取通用沉浸式播放器基类（R2 修订：高风险，建议改用扩展函数+工具类方案；toggleSystemBar 已在 ActivityExtensions.kt:187 作为扩展函数存在无需继承；scheduleAutoHide/hideControlsAnimated/showControlsAnimated 抽取到 PlayerControlsHelper 工具类；若必须抽取基类需补充 abstract 方法清单 + 子类覆写约定 + 至少 3 个真机回归场景：视频全屏切换/视频PiP/图片长按菜单）

### 4.3 P2 可选（INFO 级问题）

- R5.1 TS 检测 offset>256 放宽到 1024（视频代码 I4）
- R5.2 手动降级 Toast 区分"多次失败"vs"用户手动"（视频代码 I5）
- R5.3 AnalyzeUrl.getMediaItem 未改 suspend 文档化（音频路径不嗅探可接受）（视频代码 I6）
- R5.4 spec.md 状态标记同步 R1 → R2（视频设计 I-1）
- R5.5 tasks.md 任务编号映射表 Layer1↔2.x（视频设计 I-2）
- R5.6 Scenario 5 描述随 E-1 修订同步（视频设计 I-3）
- R5.7 design.md 显式约束日志格式（sanitizeUrl）（视频设计 I-4）
- R5.8 图片文档结构优化（图片设计 I1/I2/I3）
- R5.9 图片代码 Glide 加 placeholder（图片代码 Bug10）
- R5.10 图片代码 ImagePlay.clear() 清理分页字段（图片代码 Bug11）
- R5.11 图片代码 ImagePageAdapter setHasStableIds（图片代码 Bug12）
- R5.12 交叉验证 design.md AD-03 实现位置更新（交叉验证 I-01）
- R5.13 交叉验证视频 design.md 状态更新为"已实施"（交叉验证 I-02）
- R5.14 交叉验证图片 design.md 状态字段补充（交叉验证 I-03）

## 5. Scenarios（核心验证场景）

### 5.1 视频 MIME 嗅探场景

**场景1：URL 后缀不明确的视频，必须通过前置帧分析识别类型**
- 前置条件：订阅源返回 `/play.php?id=xxx` 形式 URL，无后缀
- 操作：用户点击播放
- 预期：L1 缓存未命中 → L2 Content-Type 检测 → L3 magic number 读取 body 前 1KB → 识别为 m3u8/mp4/flv → 缓存结果
- 验证：logcat 输出 `SniffingMime: sniffed mimeType=..., elapsed=...ms`

**场景2：Range 请求失败时，返回 null 让 ExoPlayer 内置 sniff 尝试**
- 前置条件：服务端不支持 Range 请求（416 错误）或 3 秒超时
- 操作：用户点击播放
- 预期：L2/L3 失败 → **返回 null（不再走 URL 后缀兜底）** → ExoPlayer 用 Extractor.sniff() 内置嗅探
- 验证：sniffMimeType 返回 null；createMediaItem 不调用 setMimeType；ExoPlayer 自动识别

**场景3：连续 3 次不可恢复错误，自动降级 WebView**
- 前置条件：视频源返回 bitstream malformed（3003）/container malformed（3002）/manifest malformed（3004）/decoder init failed/decoding failed
- 操作：用户点击播放
- 预期：unrecoverableFailCount 累加到 3 → postEvent(VIDEO_FALLBACK_WEBVIEW) → VideoPlayerActivity 接收事件 → switchToWebViewMode 显示 Toast
- 验证：3003 常量正确触发降级（R3.2 修复后）

**场景4：协程取消时，sniffMimeType 正确重新抛出 CancellationException**
- 前置条件：用户在嗅探过程中（3 秒内）退出 Activity
- 操作：用户点击返回
- 预期：Exo2MediaPlayer.scope.cancel() 取消嗅探协程 → sniffWithRangeRequest 捕获 CancellationException 并重新抛出（不吞掉） → 协程立即终止，不再执行 setMediaItem/prepare
- 验证：R1.3 修复后 scope 不泄漏；CancellationException 不被 runCatching 吞掉

### 5.2 图片播放器场景

**场景5：用户手动选择网页模式，走 ReadRssActivity（不走 ImageGalleryActivity）**
- 前置条件：订阅源 articleStyle==2（图片列表样式），但用户在订阅源设置中选择"网页模式"
- 操作：用户点击文章
- 预期：ReadRss.readRss 检测到用户主动选择网页模式 → 走 ReadRssActivity → 不启动 ImageGalleryActivity
- 验证：ReadRss.kt L41-43 回退逻辑生效；AD-06 ADR 文档化（R2.1）

**场景6：图片类型订阅源自动路由到 ImageGalleryActivity**
- 前置条件：订阅源 type==1（图片订阅源），用户未手动选择网页模式
- 操作：用户点击文章
- 预期：ReadRss.readNoHtml → 设置 ImagePlay 单例字段 → 启动 ImageGalleryActivity → 双 ViewPager2 显示图集
- 验证：logcat `Grep "ImagePlay.*set.*position"` 确认 ImagePlay 单例字段全部设置；位置记忆生效（R2 修订：补充具体 logcat 关键词）

**场景7：图片加载失败，4 级兜底解析生效**
- 前置条件：ruleContent 是 JS 规则，执行抛 TypeError
- 操作：用户进入图集
- 预期：策略1 ruleContent 失败 → 策略2 body@html 重试 → 策略3 article.link 作为单图 URL → 策略4 最宽松兜底
- 验证：errorLiveData 不触发；至少显示一张图片（article.link）

**场景8：多域名 CDN 场景，WebView 预热所有域名**
- 前置条件：图集包含多个 CDN 域名（如站点A/站点B/站点C），且防护系统A（Cloudflare 类）启用 JS 挑战
- 操作：用户进入图集
- 预期：needPreheat 列出所有域名 → **串行预热（R2.12 修复后）** → 每个域名 onPageFinished 后再加载下一个 → CookieManager.flush() 同步 *** → Glide 复用 ***
- 验证：所有域名预热完成；多域名图片加载成功

**场景9：快速切换文章，协程正确取消避免数据错乱**
- 前置条件：用户在图集浏览，快速上下滑动切换多篇文章
- 操作：用户连续滑动 5 次以上
- 预期：loadArticleContent 入口取消上一个协程（R2.13 修复后） → 仅最后一个加载请求执行 → postValue 不被覆盖 → UI 显示正确文章的图片
- 验证：logcat `Grep "loadJob.*cancel|preloadedArticles.*skip"` 确认协程取消生效；无数据错乱（R2 修订：补充具体 logcat 关键词，原"数据被覆盖"非真实关键词）

### 5.3 架构风格一致性场景（基于风格审查报告）

**场景10：视频播放器在亮色/暗色/E-Ink 主题下，所有颜色跟随主题切换**
- 前置+操作：用户切换亮色/暗色/E-Ink 主题（或自定义 primaryColor/accentColor）→ 进入视频播放器触发播放/全屏/设置面板/错误对话框
- 预期：fragment_video.xml 根布局背景跟随 colorBackground（非 #000000）；legacyContainer 播放地址区用 background_card/secondaryText（非 #1A2B4A/#8AB4F8）；VideoSettingsPanel 背景跟随 ThemeStore.backgroundColor；AlertDialog 通过 applyTint() 应用 accentColor；E-Ink 模式下 BottomSheet 描边替代阴影
- 验证：R1.6 修复后亮/暗/E-Ink 主题切换颜色全部跟随；Grep 硬编码颜色无残留（R2 修订：扩展 E-Ink 模式覆盖）

**场景11：图片播放器与视频播放器的 TitleBar/按钮/弹框风格视觉一致**
- 前置+操作：用户先后进入图片播放器和视频播放器 → 对比 TitleBar 背景/文字色、悬浮按钮背景/圆角、长按菜单/错误对话框样式
- 预期：图片 TitleBar 用 primaryColor（非 #80000000 硬编码）；图片按钮用 bg_overlay_button 12dp 圆角（非 bg_rotate_toolbar 24dp）；图片长按菜单/错误用 alert {} DSL（非原生 AlertDialog）；两者圆角统一 12dp、按钮背景统一 #80000000
- 验证：R2.14/R2.15/R2.16/R2.21 修复后两者视觉风格一致

**场景12：视频/图片播放器的 BottomSheet 弹框使用统一基类**
- 前置+操作：用户在视频播放器打开 VideoSettingsPanel、图片播放器打开图片信息面板 → 对比圆角/拖拽指示/背景色/E-Ink 适配
- 预期：两者均继承 BaseBottomSheetDialog 基类；圆角统一 16dp（corner_large）；拖拽指示用 drag_handle_bg；背景跟随 ThemeStore.backgroundColor；E-Ink 模式去阴影加描边
- 验证：R4.37 实现后两者 BottomSheet 样式统一；E-Ink 模式适配一致

**场景13：视频/图片播放器的沉浸式模式使用统一 API**
- 前置+操作：用户在视频播放器单击切换 PURE 态、图片播放器单击切换沉浸式 → 对比两者沉浸式进入/恢复行为
- 预期：两者均用 toggleSystemBar(show) 工具方法（WindowInsetsControllerCompat）；图片不再用 window.setFlags/systemUiVisibility 旧 API；两者均支持 BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE；控件自动隐藏+淡入淡出动画一致
- 验证：R2.17/R4.33/R4.38 修复后沉浸式 API 统一；图片沉浸式有动画

### 5.4 边界场景（R2 修订新增）

**场景14：cookie 过期自动重新预热**
- 前置条件：图片 CDN 域名的 *** 已过期，首次加载图片返回 401/403
- 操作：用户进入图集
- 预期：Glide 加载失败 → 触发 WebView 预热重新获取 *** → CookieManager.flush() 同步 → 重试加载图片成功
- 验证：logcat `Grep "preheat.*retry|CookieManager.*flush"` 确认重新预热；图片最终加载成功

**场景15：横屏切换适配性最大展示无变形**
- 前置条件：用户在图集浏览横屏图片
- 操作：用户旋转设备至横屏
- 预期：scaleType 切换为 centerCrop（R2 修订：原 fitXY 改为 centerCrop 避免变形） → 图片充满屏幕无短边留白 → 无非等比拉伸变形
- 验证：真机观察横屏图片充满屏幕无变形；logcat 确认 scaleType 切换

---

## 6. 用户反馈响应矩阵

> R2 修订：修正 ADR 编号引用，对齐 design.md 实际编号（原矩阵错位已修正）

| # | 用户诉求 | 对应需求 | 对应 ADR/任务 | 验证场景 |
|---|---------|---------|-------------|---------|
| 1 | URL 兜底未移除 | R1.1（R3 修订：过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除） | 视频 design.md AD-01（R3 修订） | 场景1/2 + 9.2 L4 命中率统计 |
| 2 | 前置帧分析优先 | R1.1（已实现） | 视频 design.md AD-01 | 场景1 |
| 3 | L1.5 URL 后缀移除 | R1.1（已实现） | 视频 design.md AD-01 | 场景1 |
| 4 | 嗅探准确性>性能 | R1.1 | 视频 Drawbacks 补充 | 场景2 |
| 5 | 复用 header/cookie | R2.2 | 图片 design.md **AD-03**（原误引 AD-07） | 场景7/8 |
| 6 | articleStyle==2 回退 | R2.1/R2.6/R2.8 | 图片 design.md **AD-05**（原误引 AD-06） | 场景5 |
| 7 | 图片尺寸适配 | R2.4/R4.14 | 图片 design.md **AD-06**（原误引"新 ADR"） | 场景6/15 |
| 8 | 跨文章预加载 | R2.5/R2.10 | 图片 design.md **AD-04**（原误引"新章节"） | 场景9 |
| 9 | 样式丑+无返回按钮 | R3.1/R4.9 | 图片 design.md 返回按钮章节 + tasks.md 12.13 UI 样式美化总任务 | 场景6 |
| 10 | 整体架构风格一致性 | R1.4-R1.9/R2.14-R2.21/R4.28-R4.38 | 视频 design.md AD-09/10/11/12 | 场景10/11/12/13 |

## 7. 验收标准

### 7.1 代码验收

- 32 个 ERROR 全部修复，Grep 验证无残留（含 14 个架构风格 ERROR）
- 38 个 WARN 关键项修复（R4.1-R4.38，含 11 个架构风格 WARN）
- 真机测试通过 13 个核心场景（场景1-13，含 4 个架构风格场景）
- logcat 无"数据错乱"/"scope 泄漏"/"3003 未触发降级"警告；调试日志无 Log.d/Log.e 残留（R1.7 修复后视频模块无残留）
- Grep 验证视频模块无硬编码颜色（#1A2B4A/#8AB4F8/#000000，R1.6）；Grep 验证图片模块无原生 AlertDialog/旧沉浸式 API（R2.15/R2.17）
- 视频/图片播放器在亮色/暗色/E-Ink 主题下风格统一（场景10/11/12/13）

### 7.2 文档验收

- 视频 design.md AD-02 修订（4 级识别链）+ AD-04 缓存 key 策略修订
- 图片 design.md 新增 AD-06/AD-07/AD-08 + 返回按钮章节 + 图片尺寸适配 ADR
- 图片 spec.md R3.1/R3.4 修正 + Scenarios 补充场景 6/7
- 图片 tasks.md 补全 5 项缺失任务
- 所有 ADR Status 修正（Proposed → Accepted）；README.md 状态同步
- 架构风格审查报告归档（3 份报告存入 docs/temp-analysis/）；视频/图片 design.md 新增"架构风格对齐"章节（记录基类继承/硬编码清理/协程封装/沉浸式 API 统一决策）
- tasks.md 补全架构风格任务（R1.4-R1.9/R2.14-R2.21/R4.28-R4.38 对应任务项）

### 7.3 用户验收

- 用户核心诉求 10 条 100% 落地（见第 6 节矩阵，含整体架构风格一致性诉求）；真机测试 13 个场景全部通过（场景1-13，含 4 个架构风格场景）
- updateLog.md 同步更新（含架构风格对齐变更条目）
