# Tasks: 视频与图片播放器审查与优化整合

> 任务清单基于 5 份原始审查报告 + 3 份风格架构审查报告，共识别 32 ERROR + 38 WARN + 13 INFO。
> 优先级：P0（ERROR，阻断交付）→ P1（WARN，影响体验）→ P2（INFO，可选优化）。
> 规范遵循：coding-philosophy.md（极简≠残缺、精准修改）、version-delivery-sync.md（文档同步）、output-safety.md（违禁词规避）。
> 风格基线：review-project-ui-style-guide.md §9.2 十二条硬规范。
>
> **R2 修订声明**：基于多维度审查报告（review-report.md）的 R2 修订建议进行优化，共修订 12 个点（P0×7 + P1×4 + P2×2）。核心变更：
> 1. AD-01 修订：从"移除 L4 URL 后缀兜底"改为"保留 L4 但不缓存"（与源码 ExoPlayerHelper.kt:127-136 实际状态一致）
> 2. AD-06 修订：resetView 已改为 FIT_CENTER（非 CENTER_INSIDE）；横屏 fitXY 改为 centerCrop（避免变形）
> 3. AD-10 修订：补充 7 类遗漏硬编码颜色（共 22 类）；新增 transparent70/80/100 色阶
> 4. AD-12 修订：BasePlayerActivity 高风险，改为"扩展函数 + 工具类"方案（PlayerControlsHelper + ActivityExtensions.toggleSystemBar）
> 5. P0 分批策略：P0-A 功能修复 18 项（阶段 2-7）+ P0-B 风格统一 14 项（阶段 11-12 前移至阶段 8 之前）
> 6. 文档同步拆分到各代码修复阶段内（阶段 8 仅保留全局索引同步）
> 7. 测试脚本引用补全（ai_tests/scripts/）+ 测试数据源清单（9.0）
>
> **R3 修订声明**：基于 R2 后用户两次"需调整"深度审查，识别 R2 回避用户核心矛盾，完成 5 项核心修订：
> 1. AD-01 L4 决策修订：从"保留 L4 不缓存（与源码一致）"改为"过渡计划——本期保留 L4 不缓存作安全网，下版本基于命中率数据评估完全移除（响应'用户要移除 L4'核心诉求）"
> 2. AD-06 横屏交互补充：centerCrop 会裁剪边缘，补充"双击切换 fitCenter ↔ centerCrop 查看完整图片"交互闭环
> 3. AD-12 方案明确：废弃 BasePlayerActivity 基类抽取原方案；明确方案A（BaseBottomSheetDialog）+ 方案B（PlayerControlsHelper）双采纳
> 4. tasks.md 9.2 脚本引用修正：`l2_verify_video_player.py --scenario sniff` 实际未支持 sniff 子场景，改为 quick_build_install.py + import_rss_source.py + 直接 adb logcat Grep；补充 L4 命中率统计验证
> 5. spec.md/README.md 同步：§3.2 方案E 否决理由 / §1 诉求1 状态 / §3.3 Drawbacks / §7 已知限制 均与 R3 决策对齐
>
> **R4 修订声明（核心能力提升，非文档层面）**：用户2026-07-26 15:20 批评 R3"文档层面打转未真正改进嗅探能力"，启动 3 份并行调研（浏览器嗅探五层架构+ExoPlayer/Video.js/hls.js/GSYVideoPlayer 成熟方案+项目源码差距）。R4 从"5 级识别链+L4 保留/移除之争"升级为"7 维度交叉验证+MediaSource 智能选择+降级链"，对齐浏览器五层架构。用户2026-07-26 15:38 审查通过，视频+图片全部实施，顺序：视频P0→视频P1→图片P0→图片P1。完整方案见 [R4-enhancement-plan.md](./R4-enhancement-plan.md)。R4 任务清单见本文件末尾"## R4 任务清单（核心能力提升）"。

## 阶段顺序声明（R2 修订，P0-7）

> **R2 修订背景**：spec.md §4.1 将 14 个架构风格 ERROR 列为 P0，但原 tasks.md 将它们排在阶段 11-14（最后），违反"代码与文档同步"原则与 P0 优先级。
> 本次修订明确分批策略，将 P0 拆为 P0-A（功能修复）与 P0-B（风格统一）两批，P0-B 前移至阶段 8 之前。

| 批次 | 阶段范围 | 任务类型 | 任务数 | 说明 |
|------|---------|---------|--------|------|
| **P0-A 功能修复（第一批）** | 阶段 2-7 | 原功能 ERROR | 18 项 | 视频 ERROR 5 + 图片设计 ERROR 10 + 图片代码 ERROR 6 + 交叉验证 ERROR 2（部分去重） |
| **P0-B 风格统一（第二批）** | 阶段 11-12（前移至阶段 8 之前） | 架构风格 ERROR | 14 项 | 视频架构风格 6 + 图片 vs 视频风格 8（去重后） |
| **P1** | 阶段 3/6/13 | WARN 项 | - | 视频 WARN 4 + 图片 WARN 6 + 通用基类 5 |
| **验证** | 阶段 9/14 | 真机+回归 | - | 功能验证 9.x + 风格验证 14.x |

**执行顺序**：阶段 1（准备）→ 阶段 2-7（P0-A 功能修复，每阶段末尾同步文档）→ 阶段 11-12（P0-B 风格统一，前移）→ 阶段 13（P1 通用基类）→ 阶段 8（全局索引同步）→ 阶段 9（功能验证）→ 阶段 14（风格验证）。
**注意**：阶段编号保持原顺序（不重排），但实际执行顺序按上表"执行顺序"行；阶段 8 已拆分到各代码修复阶段内，仅保留全局索引同步（INDEX.md / updateLog.md）。

## 1. 准备工作

- [ ] 1.1 确认审查报告问题清单（32 ERROR + 38 WARN + 13 INFO）
  - 验证：Read 8 份审查报告，统计问题数量与分级一致（原始 5 份：视频设计 2E+5W+4I / 视频代码 1E+4W+6I / 图片设计 10E+7W+3I / 图片代码 3E+6W+3I / 交叉验证 2E+5W+3I；新增 3 份风格审查：视频架构风格 6E+11W+8I / 图片vs视频风格 8E+6W+5I / 项目UI风格基线 0E+0W+0I）
- [ ] 1.2 备份核心源码到 bak 目录（ExoPlayerHelper.kt / Exo2MediaPlayer.kt / ImageGalleryActivity.kt / ImageGalleryViewModel.kt / ImageArticlePagerAdapter.kt / ImagePageAdapter.kt / ReadRss.kt / VideoFragment.kt / VideoSettingsPanel.kt / activity_video_player.xml / fragment_video.xml / layout_rotate_toolbar.xml / bg_rotate_toolbar.xml）
  - 验证：LS 确认 bak 目录存在 13 个备份文件
- [ ] 1.3 加载 coding-philosophy.md 编码哲学规范
  - 验证：Read 确认规范已加载（极简≠残缺、精准修改原则、简化标注规则）

## 2. 视频 ERROR 修复（P0）

- [ ] 2.1 保留 L4 URL 后缀兜底但不缓存（R2 修订，P0-2，对应 design.md AD-01）
  - 修复点：**R2 修订**——从原"移除 L4 URL 后缀兜底"改为"保留 L4 但不缓存"，与源码 `ExoPlayerHelper.kt:127-136` 实际状态一致。具体：(1) 移除 L1.5 URL 后缀快速路径；(2) 保留 L4 `getMimeType(url)` 兜底调用，但 L4 结果**不写入 `MimeSnifferCache`**（避免误判固化，可重试嗅探）；(3) 5 级识别链：缓存→Content-Type→magic number→URL 后缀兜底（不缓存）→返回 null
  - 依据：视频设计报告 E-1 + R2 修订（源码实际仍保留 L4 兜底，原方案"移除 L4"与源码不符，违反"设计文档为源码变更权威"原则）
  - 验证：Grep 确认 sniffMimeType 中无 L1.5 URL 后缀快速路径；Read 确认 L4 兜底调用后无 `MimeSnifferCache.put` 调用
  - **同步文档（R2 修订，P0-6）**：更新 `docs/specs/exoplayer-resilience/design.md` AD-02（5 级链保留 L4 兜底不缓存）+ `spec.md` Scenario 5 修订（嗅探失败→L4 URL 后缀兜底不缓存→返回 null→ExoPlayer Extractor.sniff()）+ Drawbacks 补充"URL 后缀兜底可能误判但不缓存可重试"
- [ ] 2.2 修复 Exo2MediaPlayer.scope 协程泄漏（release() 调用 scope.cancel()）
  - 修复点：重写 release()，调用 scope.cancel() 后 super.release()，并清空 currentSniffJob
  - 依据：视频代码报告 E1（Activity 销毁后嗅探协程可能继续运行 3 秒，浪费资源）
  - 验证：Grep 确认 release() 方法含 scope.cancel()
- [ ] 2.3 修复 3003 常量误判（isUnrecoverableError 加入 ERROR_CODE_PARSING_BITSTREAM_MALFORMED）
  - 修复点：isUnrecoverableError 条件加入 ERROR_CODE_PARSING_BITSTREAM_MALFORMED，删除 L339 错误注释
  - 依据：视频代码报告 W1（源码注释错误，导致 bitstream malformed 错误不被计数，无法触发自动降级）
  - 验证：Grep 确认常量存在
- [ ] 2.4 审计 getMediaItem 改 suspend 影响面（列出所有调用方）
  - 修复点：列出 AnalyzeUrl.getMediaItem() 所有调用方（AudioPlayService/VideoPlay 等），评估协程上下文兼容性，文档化是否需要改 suspend
  - 依据：视频设计报告 E-2（tasks.md 未列出调用方审计任务）+ 视频代码报告 I6（实际未改 suspend，音频路径不嗅探可接受）
  - 验证：调用方清单文档化（写入 design.md 或单独审计文档）
- [ ] 2.5 更新 exoplayer-resilience 设计文档（spec.md / design.md / tasks.md 同步 AD-01 决策）
  - 修复点：spec.md 5 级链改 4 级 + Scenario 5 修订（嗅探失败返回 null，不再走 URL 后缀）+ design.md AD-02 Decision 改为"4 级识别链"
  - 依据：视频设计报告 §9（spec.md/design.md 改进点 1）
  - 验证：Read 确认文档已更新

## 3. 视频 WARN 修复（P1）

- [ ] 3.1 修复日志规范（Log.d/Log.e → AppLog.put/AppLog.putDebug）
  - 修复点：Exo2MediaPlayer.kt L346,368 + ExoPlayerHelper.kt L334,337 统一改用 AppLog.put
  - 依据：视频代码报告 W2/W3/W4（违反"日志用 AppLog.put"规范，logcat 可能泄露 urlPath）
  - 验证：Grep "android.util.Log.d|android.util.Log.e" 确认 0 残留
- [ ] 3.2 修复 MimeSnifferCache key 策略文档不一致
  - 修复点：design.md AD-04 更新为"完整 URL（含 query）"，与源码实现一致；补充缓解措施（对含 token 的 URL 跳过缓存）
  - 依据：视频代码报告 §2.2（实现优于设计文档，但文档未同步）+ 视频设计报告 W-2/W-5
  - 验证：Read design.md AD-04 确认 key 策略为"完整 URL"
- [ ] 3.3 补充 Drawbacks（URL 后缀误判风险）
  - 修复点：spec.md Drawbacks 章节补充"URL 后缀兜底对动态 URL 误判"风险
  - 依据：视频设计报告 W-1（Drawbacks 遗漏 URL 后缀误判风险）
  - 验证：Read spec.md Drawbacks 确认新增条目
- [ ] 3.4 补充测试构造方法（R2 修订，P0-13，补充场景 3/4 触发条件）
  - 修复点：tasks.md 任务 4.9/7.4 补充本地 mock 服务器构造方法（返回非视频内容）+ 测试源清单（m3u8+mp4+flv 三类）
  - **R2 修订（P0-13）补充场景 3/4 构造方法**：
    - 场景 3（3003 bitstream malformed 降级）：构造方法 1——本地 mock 服务器返回截断的 mp4 流（仅返回前 1024 字节后断开连接），触发 `ERROR_CODE_PARSING_BITSTREAM_MALFORMED (3003)`；构造方法 2——准备已知 malformed 测试源[6]（代号，含损坏的 mp4 头部），logcat Grep "BITSTREAM_MALFORMED|isUnrecoverableError" 确认常量存在并触发自动降级
    - 场景 4（协程取消）：播放长 URL 视频源（如长 query 参数的 m3u8），嗅探启动后立即按返回键，logcat Grep "CancellationException|loadJob.*cancel|preloadedArticles.*skip" 观察 CancellationException 重新抛出（禁止 runCatching 吞掉）
  - 依据：视频设计报告 W-4 + R2 修订（场景 3/4 触发条件在原 tasks.md 完全缺失）
  - 验证：Read tasks.md 确认测试构造方法文档化；mock 服务器/已知 malformed 源[6] 准备就绪

## 4. 图片 ERROR 修复 - 设计层（P0）

- [ ] 4.1 补全 AD-06 header/cookie 复用 ADR（design.md）
  - 修复点：新增 AD-06，说明 sourceOriginOption 来源（订阅源 sourceUrl）、refererOption 兜底机制（文章页 URL）、AnalyzeUrl 自动注入 header/cookie 路径
  - 依据：图片设计报告 E2 + 交叉验证 §4.1（用户 09:56 明确要求"复用 header？cookie？"）
  - 验证：Read design.md 确认 AD-06 章节 Y-Statement 六要素齐全
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` 新增 AD-06 章节
- [ ] 4.2 补全 AD-07 多线程预缓存 ADR（design.md）
  - 修复点：新增 AD-07，参考 VideoPlay.preloadNextArticleHtml 设计 ImagePlay.preloadNextArticleImages(currentIndex)，用协程 async 预加载下一篇文章图片 URL 列表
  - 依据：图片设计报告 E3（用户 09:56 明确要求"多线程预缓存"）
  - 验证：Read design.md 确认 AD-07 章节含协程 async 预加载设计
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` 新增 AD-07 章节
- [ ] 4.3 补全 AD-08 articleStyle==2 路由回退 ADR（design.md）
  - 修复点：新增 AD-08，复述 ReadRss.kt L41-43 的回退逻辑，明确"用户主动选择网页模式时走 ReadRssActivity，禁止自动转为图片查看器"
  - 依据：图片设计报告 E1 + 交叉验证 E-01（用户 10:09 明确决策，源码已回退但文档未记录）
  - 验证：Read design.md 确认 AD-08 决策与 ReadRss.kt L41-43 一致
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` 新增 AD-08 章节 + spec.md R3.1 修正
- [ ] 4.4 补全图片尺寸适配 ADR（design.md，R2 修订对齐 AD-06 R2）
  - 修复点：**R2 修订**——新增 ADR，评估 FIT_CENTER vs CENTER_CROP vs PhotoView 动态 scale，明确 scaleType 策略：初始 fitCenter + 重置 fitCenter（PhotoView.scale = 1f 不改变 scaleType）+ 横屏切 centerCrop（裁剪填充无变形，原"fitXY"已废弃）+ 长图支持垂直滚动
  - 依据：图片设计报告 E4 + 交叉验证 E-02/W-03 + R2 修订（用户 13:02 明确要求"适配性最大尺寸展示"；源码已改 FIT_CENTER，原方案 CENTER_INSIDE 过时；横屏 fitXY 变形风险）
  - 验证：Read design.md 确认 ADR 含 scaleType 决策（横屏 centerCrop 而非 fitXY）
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` AD-06 R2 修订内容
- [ ] 4.5 补全跨文章预加载 ADR（design.md）
  - 修复点：新增 ADR，参考 VideoPlay.preloadNextArticleHtml 设计 ImageGalleryViewModel.preloadNextArticle()，含触发时机+缓存策略
  - 依据：图片设计报告 E5（用户 13:02 明确反馈"上下滑动切换时下一个图片内容无法加载"）
  - 验证：Read design.md 确认 ADR 含预加载触发时机+缓存策略
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` 新增跨文章预加载 ADR
- [ ] 4.6 修正 spec R3.4 与 design AD-05 / tasks 3.4 三方矛盾
  - 修复点：统一为"ruleContent 为空时用 article.link 作为单图URL，仍启动 ImageGalleryActivity（隐藏页码）"
  - 依据：图片设计报告 E7（三处不一致：spec 表述含糊 / design 暗示单图走 Activity / tasks 明确走 Activity）
  - 验证：Read spec.md R3.4 + design.md AD-05 + tasks.md 3.4 确认三处一致
- [ ] 4.7 补全 Scenarios 两个核心场景（用户手动选择网页模式 / 防盗链失败重试）
  - 修复点：spec.md 新增 Scenario 6（用户将图片订阅源改为网页模式 → 走 ReadRssActivity）+ Scenario 7（图片防盗链失败 → 注入 Referer/cookie 重试 → 成功显示）
  - 依据：图片设计报告 E8/E9（用户 10:09 + 09:56 核心痛点场景缺失）
  - 验证：Read spec.md 确认 Scenario 6/7 存在
- [ ] 4.8 修正所有 ADR Status（Proposed → Accepted）
  - 修复点：AD-01~AD-05 已进入开发中的 ADR 改为 Accepted（按 ADR Y-Statement 模板，决策应有明确状态）
  - 依据：图片设计报告 W1
  - 验证：Grep "Status: Proposed" 确认 AD-01~AD-05 已改为 Accepted
- [ ] 4.9 补全 tasks 5 项关键任务（header/cookie/预缓存/适配展示/预加载）
  - 修复点：image-gallery-activity/tasks.md 新增 5 项任务（2.17 header/cookie 复用 / 2.18 多线程预缓存 / 2.19 图片适配性最大尺寸 / 2.20 跨文章预加载 / 3.6 articleStyle==2 路由回退）
  - 依据：图片设计报告 E10
  - 验证：Read tasks.md 确认 5 项任务存在
- [ ] 4.10 修正 tasks 7.2 真实源名称（违反 output-safety 规范）
  - 修复点：将真实源名称改为"图片订阅源[N]"代号
  - 依据：图片设计报告 W2（违反 output-safety 规范）
  - 验证：Grep 确认 tasks.md 7.2 无真实源名称

## 5. 图片 ERROR 修复 - 代码层（P0）

- [ ] 5.1 修复 ImageArticlePagerAdapter 适配器复用失效（bind 方法 if/else 两分支都新建 adapter）
  - 修复点：bind 方法 else 分支改为 imagePageAdapter?.updateSource(sourceOrigin, referer) 而非新建
  - 依据：图片代码报告 Bug1（两分支逻辑等价，复用逻辑失效，导致 ViewPager2 状态丢失、图片重新加载、滑动卡顿）
  - 验证：Read 确认 bind 方法修复
- [ ] 5.2 修复 WebView 预热循环覆盖（forEach loadUrl 改为串行或多 WebView 实例）
  - 修复点：改为串行预热（一个域名 onPageFinished 后再加载下一个），或用多个 WebView 实例并行预热；同时按域名去重预热（用 preheatedDomains 集合判断）
  - 依据：图片代码报告 Bug2（多域名场景只有最后一个域名被预热，其他域名图片仍可能因 JS 挑战防护加载失败）
  - 验证：Read 确认预热逻辑修复
- [ ] 5.3 修复 ViewModel.loadArticleContent 协程未取消（增加 Job 取消机制）
  - 修复点：在 loadArticleContent 入口添加 private var loadJob: Job?，调用前 loadJob?.cancel()；或改 Flow + collectLatest
  - 依据：图片代码报告 Bug3（快速切换文章时多个 execute 并发执行，后到的 postValue 覆盖先到的正确数据，数据错乱）
  - 验证：Read 确认 Job 取消机制存在
- [ ] 5.4 修复图片尺寸适配（R2 修订，P0-3 + P1-3，对齐 design.md AD-06 R2）
  - 修复点：**R2 修订**——源码 `ImagePageAdapter.kt:165` resetView 已改为 `FIT_CENTER`（与初始 `fitCenter` 一致），但需进一步修订：
    (1) resetView 改为 `PhotoView.scale = 1f` 重置缩放，**不改变 scaleType**（原方案通过改变 scaleType 重置，会导致重置后图片显示行为变化）
    (2) 横屏切换从原"fitXY"改为 `centerCrop`（裁剪填充，无变形，充满 View；原 fitXY 会导致非等比拉伸变形）
    (3) 长图支持垂直滚动
    (4) item_image_page.xml scaleType 统一为 fitCenter
  - 依据：图片代码报告 Bug5 + 交叉验证 W-03 + R2 修订（源码已改 FIT_CENTER，原方案"CENTER_INSIDE 一致"过时；横屏 fitXY 自相矛盾，会导致变形）
  - 验证：真机验证图片尺寸（横屏 centerCrop 无变形，长图可垂直滚动，重置后缩放可恢复）
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` AD-06 R2 修订内容（resetView 不改 scaleType + 横屏 centerCrop）
- [ ] 5.5 实现 ImagePlay.preloadNextArticleImages（参考 VideoPlay.preloadNextArticleHtml）
  - 修复点：参考 VideoPlay.preloadNextArticleHtml（L1040）实现 ImagePlay.preloadNextArticleImages(currentIndex)，用协程 async 预加载下一篇文章图片 URL 列表
  - 依据：图片设计报告 E3/E5 + 交叉验证 §6.1（VideoPlay 已有参考实现，ImagePlay 缺失）
  - 验证：真机验证跨文章预加载
- [ ] 5.6 对齐 header/cookie 复用（OkHttpStreamFetcher sourceOriginOption + refererOption 模式）
  - 修复点：参考 OkHttpStreamFetcher sourceOriginOption + refererOption 模式，新增 ImagePlay.currentPlayHeaders 字段跨文章复用 headers
  - 依据：图片代码报告 Bug4 + 图片设计报告 E2（VideoPlay 有 currentPlayHeaders 跨文章复用，ImagePlay 缺失）
  - 验证：Grep 确认复用逻辑

## 6. 图片 WARN 修复（P1）

- [ ] 6.1 补全 ImagePlay.currentPlayHeaders / preloadedArticles
  - 修复点：对齐 VideoPlay 字段，新增 currentPlayHeaders（跨文章复用 headers）+ preloadedArticles（预加载去重 MutableSet<String>）
  - 依据：图片代码报告 Bug4（性能略低，快速滑动时重复预加载）
  - 验证：Read ImagePlay.kt 确认两个字段存在
- [ ] 6.2 修复 resetView scaleType 不一致
  - 修复点：调用 PhotoView.reset() 或 setScale(1f)，不再改变 scaleType
  - 依据：图片代码报告 Bug5（resetView 用 CENTER_INSIDE 与初始 fitCenter 不一致，重置后图片显示行为变化）
  - 验证：Read ImagePageAdapter.kt resetView 确认未改变 scaleType
- [ ] 6.3 替换 SYSTEM_UI_FLAG_*（API 30+ 废弃）
  - 修复点：改用 WindowInsetsControllerCompat（minSdk 23 可用，兼容性需评估）
  - 依据：图片代码报告 Bug8（SYSTEM_UI_FLAG_FULLSCREEN/HIDE_NAVIGATION/IMMERSIVE_STICKY 在 API 30+ 已废弃，Android 11+ 沉浸式可能失效）
  - 验证：Grep "SYSTEM_UI_FLAG" 确认 0 残留
- [ ] 6.4 修复错误重试未清预热状态
  - 修复点：btn_retry 点击时重置 isFirstPreheatCompleted = false + preheatedDomains.clear()
  - 依据：图片代码报告 Bug9（重试时不会重新预热，JS 挑战防护场景重试仍可能失败）
  - 验证：Read ImageGalleryActivity.kt btn_retry 点击逻辑确认重置
- [ ] 6.5 清理 WebView 清理代码冗余
  - 修复点：删除 webChromeClient = null（从未设置过）和 removeJavascriptInterface("Android")（从未添加过）
  - 依据：图片代码报告 Bug6（无功能影响，但代码冗余、误导）
  - 验证：Read onDestroy 确认冗余代码已删除
- [ ] 6.6 修正 clear() 注释误导
  - 修复点：修正 ImagePlay.clear() 注释，或保留 lastPlayedArticleLink 不清（与 RssArticlesFragment.onResume 使用后立即清空的行为对齐）
  - 依据：图片代码报告 Bug7（注释说"保留 lastPlayedArticleLink"，但实际使用后立即清空，注释误导维护者）
  - 验证：Read ImagePlay.kt clear() 确认注释与实现一致
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` Bug 修复章节

## 7. 交叉验证 ERROR 修复（P0）

- [ ] 7.1 同步 articleStyle==2 回退决策到三文档（spec/design/tasks）
  - 修复点：spec.md R3.1 修正为"type==1 且用户未手动选择网页模式时启动 ImageGalleryActivity；用户手动选择网页模式时走 ReadRssActivity" + design.md AD-08 + tasks.md 同步
  - 依据：交叉验证 E-01（design.md 完全缺失，违反"设计文档为源码变更权威"原则）+ 图片设计报告 E6
  - 验证：Read spec.md R3.1 + design.md AD-08 + tasks.md 确认三处一致
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` AD-08 章节 + `spec.md` R3.1 修正
- [ ] 7.2 补全返回按钮和图片尺寸适配的文档记录
  - 修复点：design.md 追加"返回按钮修复"章节（setSupportActionBar 时序问题 + 三重保障）+ "图片尺寸适配策略"ADR
  - 依据：交叉验证 E-02（design.md 未响应两个用户问题：返回按钮缺失 + 图片尺寸适配）
  - 验证：Read design.md 确认两个章节存在
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` "返回按钮修复"+"图片尺寸适配"章节

## 8. 全局索引同步（强制，R2 修订，P0-6）

> **R2 修订（P0-6）**：原"文档同步"章节已拆分到各代码修复阶段内（见阶段 2.1/4.1-4.5/5.4/6.6/7.1/7.2 末尾的"同步文档"子任务）。本阶段仅保留全局索引同步——INDEX.md / updateLog.md / task-navigation.md，确保导航与交付日志在所有代码修复完成后统一更新。

- [ ] 8.1 更新 docs/INDEX.md（移动 exoplayer-resilience 和 image-gallery-activity 状态）
  - 修复点：状态从"设计中"移动到"已实施待验证"
  - 依据：version-delivery-sync 规范
  - 验证：Read INDEX.md 确认状态更新
- [ ] 8.2 更新 assets/updateLog.md（基于 git diff 分析真实变更）
  - 修复点：基于 git diff 分析真实代码变更，生成用户可感知的更新日志（通俗语言描述，不暴露内部技术术语）
  - 依据：version-delivery-sync 规范（禁止文字合并已有条目，必须基于代码分析）
  - 验证：Read updateLog.md 确认新增条目基于真实代码变更
- [ ] 8.3 更新 docs/project-flow/task-navigation.md（如有模块代码锚点变更）
  - 修复点：如有模块代码锚点变更则同步
  - 依据：version-delivery-sync 规范
  - 验证：Read task-navigation.md 确认锚点同步

## 9. 验证

> **R2 修订（P1-10）包名声明**：本节所有真机验证任务必须使用测试包 `io.legado.miss.app.debug`（uid=10064），按 `package-naming.md` 规范选择（代码优化任务用测试包，便于定位问题）。
> **R2 修订（P0-11）脚本引用**：本节所有真机验证任务必须使用 `ai_tests/scripts/` 下固定脚本，禁止在 `temp/` 创建临时脚本；Python 解释器必须用 `ai_tests\venv\Scripts\python.exe`。

### 9.0 测试数据准备（R2 修订，P0-12）

- [ ] 9.0 导入测试数据源（用代号替代真实源名称，遵循 output-safety 规范）
  - 修复点：用 `python ai_tests/scripts/import_rss_source.py <json>` 导入以下测试源：
    - 视频测试源[1]（m3u8 格式）
    - 视频测试源[2]（mp4 格式）
    - 视频测试源[3]（flv 格式）
    - 图片测试源[4]（单域名，验证基础加载）
    - 图片测试源[5]（多 CDN 域名，验证多域名预热 Bug2 修复）
    - 视频测试源[6]（已知 malformed mp4，验证 3003 降级，对应阶段 3.4 场景 3）
  - 依据：P0-12（原 tasks.md 9.x 验证任务中无任何源导入步骤，可执行性偏弱）+ output-safety 规范（源名称用代号）
  - 验证：`adb shell pm list packages` 确认测试包已安装；导入脚本返回成功；源列表中可见源[1]-源[6]代号

### 9.1 编译+安装+L1 验证（R2 修订，P0-11）

- [ ] 9.1 编译测试包并安装到真机/模拟器（io.legado.miss.app.debug）
  - 验证：`python ai_tests/scripts/quick_build_install.py` 编译+安装+L1 验证一键完成（替代原 `./gradlew assembleDebug`，按 ai_e2e_testing_workflow 规范）
  - 依据：P0-11（原 9.1 仅引用 `./gradlew assembleDebug`，未用项目固定脚本）

### 9.2 真机验证视频嗅探（R3 修订——修正脚本引用）

- [ ] 9.2 真机验证视频嗅探（L2 验证：播放视频触发嗅探，收集 SniffingMime 日志）
  - 验证：
    1. `python ai_tests/scripts/quick_build_install.py` 编译+安装+L1 验证
    2. `python ai_tests/scripts/import_rss_source.py ai_tests/data/video_source_1.json` 导入视频测试源[1]（m3u8）
    3. 真机播放视频触发嗅探，`adb logcat -s SniffingMime:* MimeSnifferCache:* ExoFallback:*` 收集日志
    4. logcat Grep `SniffingMime|MimeSnifferCache|L4 suffix fallback used` 确认嗅探流程正常（cache hit / sniffed success / L4 suffix fallback 不缓存等场景）
    5. **R3 新增**：logcat 统计 `L4 suffix fallback used` 出现次数 / 总嗅探次数，计算 L4 命中率（用于 AD-01 下版本评估完全移除 L4 决策）
    6. logcat Grep `MimeSnifferCache.*put` 确认 L4 兜底结果不写入缓存（验证 AD-01 不缓存决策生效）
  - 依据：P0-11（原 9.2 未引用 l2_verify_video_player.py 脚本）+ R3 修订（`l2_verify_video_player.py --scenario sniff` 实际未支持 sniff 子场景，改为直接 logcat Grep + 手动真机操作）

### 9.3 真机验证图片加载（L2 验证）

- [ ] 9.3 真机验证图片加载（L2 验证：图片类型订阅源，验证 header/cookie 复用 + 多线程预缓存）
  - 验证：logcat Grep "getContentAwait|sourceOriginOption|refererOption" 确认无 "getContentAwait failed" 错误，图片正常加载；cookie 长度记录（不引用内容）
  - 依据：原 9.3 + R2 修订补充 logcat 关键词

### 9.4 真机验证图片尺寸适配（R2 修订对齐 5.4）

- [ ] 9.4 真机验证图片尺寸适配（L2 验证：不同尺寸图片，验证适配性最大展示）
  - 验证：真机观察图片充满屏幕（无短边留白），横屏 centerCrop 无变形（原 fitXY 已废弃），长图可垂直滚动，重置按钮后缩放可恢复（PhotoView.scale = 1f）
  - 依据：原 9.4 + R2 修订（横屏改 centerCrop）

### 9.5 真机验证跨文章预加载（R2 修订，P0-11）

- [ ] 9.5 真机验证跨文章预加载（L2 验证：上下滑动切换，验证下一张图片预加载）
  - 验证：`python ai_tests/scripts/swipe_test_log.py capture` 捕获滑动日志 → `python ai_tests/scripts/swipe_test_log.py analyze` 分析预加载触发情况；真机观察切换无加载延迟；logcat Grep "preloadNextArticle|preloadedArticles" 确认预加载触发
  - 依据：P0-11（原 9.5 未引用 swipe_test_log.py 脚本）

### 9.6 真机验证 articleStyle==2 路由回退（R2 修订，P0-11 + P1-11）

- [ ] 9.6 真机验证 articleStyle==2 路由回退（手动改成网页模式，验证走 ReadRssActivity）
  - 验证：`python ai_tests/scripts/dump_ui_safe_v2.py` 抓取 Activity 栈确认走 ReadRssActivity（非 ImageGalleryActivity）；logcat Grep "ImagePlay.*set.*position|ReadRss.*articleStyle" 确认路由分支
  - 依据：P0-11（原 9.6 未引用 dump_ui_safe_v2.py）+ P1-11（补充 logcat 关键词 "ImagePlay.*set.*position"）

### 9.7 Grep 确认无调试日志残留

- [ ] 9.7 Grep 确认无调试日志残留（android.util.Log.d/e 零残留）
  - 验证：Grep "android.util.Log.d|android.util.Log.e" 确认 0 残留
  - 依据：原 9.7

### 9.8 真机验证视频播放器亮/暗主题切换

- [ ] 9.8 真机验证视频播放器亮/暗主题切换（所有颜色跟随主题）
  - 验证：真机切换亮/暗主题，观察视频模块所有颜色跟随主题（无硬编码残留，22 类硬编码清理验证，对应阶段 11.3）
  - 依据：原 9.8 + R2 修订（22 类硬编码）

### 9.9 真机验证图片播放器亮/暗主题切换

- [ ] 9.9 真机验证图片播放器亮/暗主题切换
  - 验证：真机切换亮/暗主题，观察图片模块所有颜色跟随主题
  - 依据：原 9.9

### 9.10 真机对比视频/图片播放器 TitleBar/按钮/弹框风格视觉一致性（R2 修订，P0-11）

- [ ] 9.10 真机对比视频/图片播放器 TitleBar/按钮/弹框风格视觉一致性
  - 验证：`python ai_tests/scripts/dump_ui_safe_v2.py` 抓取 TitleBar/按钮 DOM 结构对比；真机并列打开两个播放器，观察 TitleBar/按钮/弹框风格统一
  - 依据：P0-11（原 9.10 未引用 dump_ui_safe_v2.py 抓取 DOM）

### 9.11 真机验证 BottomSheet 弹框使用统一基类（R2 修订，P1-8）

- [ ] 9.11 真机验证 BottomSheet 弹框使用统一基类
  - 验证：真机触发 VideoSettingsPanel，确认圆角/拖拽/背景一致（**R2 修订 P1-8**：移除 ImageInfoPanel 引用——图片模块当前无 BottomSheet 组件需求，本期不新建 ImageInfoPanel）
  - 依据：原 9.11 + R2 修订 P1-8（移除 ImageInfoPanel）

### 9.12 真机验证沉浸式模式使用统一 API（无旧 API 警告）

- [ ] 9.12 真机验证沉浸式模式使用统一 API（无旧 API 警告）
  - 验证：logcat Grep "SYSTEM_UI_FLAG|window.setFlags" 确认无废弃警告
  - 依据：原 9.12

### 9.13 真机验证协程取消（R2 修订，P0-13 + P1-11，对应阶段 3.4 场景 4）

- [ ] 9.13 真机验证协程取消（场景 4：嗅探启动后立即按返回键）
  - 验证：播放长 URL 视频源（如长 query 参数的 m3u8），嗅探启动后立即按返回键；logcat Grep "loadJob.*cancel|preloadedArticles.*skip|CancellationException" 观察 CancellationException 重新抛出（禁止 runCatching 吞掉）
  - 依据：P0-13（场景 4 触发条件构造方法）+ P1-11（补充 logcat 关键词 "loadJob.*cancel|preloadedArticles.*skip"）

### 9.14 AskUserQuestion 验收检查点

- [ ] 9.14 AskUserQuestion 验收检查点
  - 验证：AskUserQuestion 三选项结构（通过/需调整/拒绝），用户选择"通过"后方可标记任务完成
  - 依据：原 9.13 + core-spec.md AskUserQuestion 强制规范

## 10. AOAdapt 日志（实施过程记录）

> **R2 修订（P2-6）**：实施阶段实时填写（当前为模板，实施时记录关键决策与调整）。格式：Action / Observation / Adapt。
> **R2 修订（P2-8）**：阶段行已补全，覆盖全部实施阶段。

| 阶段 | Action | Observation | Adapt |
|------|--------|-------------|-------|
| 准备 | - | - | - |
| 视频 P0（阶段 2） | - | - | - |
| 图片 P0（阶段 4-5） | - | - | - |
| 交叉验证 P0（阶段 7） | - | - | - |
| 文档同步（各阶段末尾，R2 拆分） | - | - | - |
| 风格对齐 P0-B（阶段 11-12，R2 前移） | - | - | - |
| 通用基类 P1（阶段 13） | - | - | - |
| 全局索引同步（阶段 8） | - | - | - |
| 真机验证（阶段 9） | - | - | - |
| 风格验证（阶段 14） | - | - | - |
| 回归验证 | - | - | - |

## 11. 视频播放器架构风格对齐（P0）

- [ ] 11.1 VideoFragment 改继承 VMBaseFragment（原继承 Fragment()）
  - 修复点：移除直接 Fragment() 继承，引入 ViewBinding delegate 替换 findViewById，复用基类 observeLiveBus 机制
  - 依据：视频架构风格报告 E1（VideoFragment.kt:49 失去项目基类统一生命周期管理、Theme 适配能力）
  - 验证：Grep 确认 VideoFragment 类签名含 VMBaseFragment
- [ ] 11.2 VideoSettingsPanel 改继承 BaseDialogFragment（原继承 BottomSheetDialogFragment）
  - 修复点：移除直接 BottomSheetDialogFragment 继承，复用基类 E-Ink 适配、backgroundColor 主题统一、onDismissListener 能力
  - 依据：视频架构风格报告 E2（VideoSettingsPanel.kt:48 失去基类能力）
  - 验证：Grep 确认 VideoSettingsPanel 类签名含 BaseDialogFragment
- [ ] 11.3 清除视频硬编码颜色（R2 修订，P0-9 + P0-10，共 22 类，对齐 design.md AD-10 R2）
  - 修复点：**R2 修订**——原方案仅列出 3 类硬编码颜色（#1A2B4A/#8AB4F8/#000000），遗漏 7 类共 14 处。本次修订补充完整 22 类硬编码颜色清单（详见 design.md AD-10 "硬编码颜色完整清单"）：
    - 视频 module 关键修订项（R2 新增 7 类）：
      - `activity_video_player.xml:298` `#80000000` → `@color/transparent80`（**新增色阶**）
      - `switch_episode_video_dialog.xml:24,25,29` `#00000000` → `@color/transparent100`（**新增色阶**）
      - `switch_speed_video_dialog.xml:15,16,18` `#00000000` → `@color/transparent100`
      - `switch_video_dialog_item.xml:12` `#FFFFFF` → `@color/primaryText`
      - `WebViewVideoPlayer.kt:57` `Color.BLACK` → `R.color.background`
      - `fragment_video.xml:52,86,172,188,201` `android:tint="#FFFFFF"` → `app:tint="@color/white"`（R4.35 tint 规范扩展）
    - 原方案保留项：fragment_video.xml:17 #000000 → ?attr/colorBackground；activity_video_player.xml:64 #1A2B4A → @color/background_card；activity_video_player.xml:72 #8AB4F8 → @color/secondaryText；activity_video_player.xml:310 #FFFFFF → @color/primaryText；switch_episode_video_dialog.xml:5 #80121212 → @color/transparent80
    - GSY 第三方布局（video_layout_controller*.xml）本期不修改，spec.md §2.2 已显式排除
    - **新增 colors.xml 色阶定义**：`transparent70`(#B3000000) / `transparent80`(#80000000) / `transparent100`(#00000000)
  - 依据：视频架构风格报告 E3/E4 + W2 + R2 修订（原方案遗漏 14 处 + transparent50 色阶映射错误，#80000000 应映射 transparent80 而非 transparent50）
  - 验证：Grep 确认 activity_video_player.xml / fragment_video.xml / switch_*_video_dialog.xml / switch_video_dialog_item.xml / WebViewVideoPlayer.kt 无硬编码颜色；Read colors.xml 确认新增 3 个色阶
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` AD-10 完整 22 类硬编码颜色清单
- [ ] 11.4 清除视频 Log.d 残留（3处，VideoPlayerActivity.kt L280/853/874）
  - 修复点：替换为 AppLog.put()，Grep 验证零残留
  - 依据：视频架构风格报告 E5（违反"日志用 AppLog.put()"硬性规范，AGENTS.md 明确禁止）
  - 验证：Grep "android.util.Log.d|android.util.Log.e" 在视频模块 0 残留
- [ ] 11.5 视频协程改 Coroutine.async{}.onError{}.onSuccess{} 链式封装（原 lifecycleScope.launch）
  - 修复点：替换 lifecycleScope.launch + try/catch 模式为项目自定义 Coroutine 链式封装
  - 依据：视频架构风格报告 E6（违反项目协程规范，AGENTS.md Code Style 核心条目）
  - 验证：Grep 确认视频模块无 lifecycleScope.launch 直接调用
- [ ] 11.6 视频三套按钮风格统一为 2 套（悬浮+面板，移除 VideoCtrlButton/VideoPanelButton 其中一套）
  - 修复点：保留沉浸式悬浮按钮（bg_overlay_button，tint 改为 ?attr/colorAccent）+ 面板按钮（VideoPanelButton），废弃 VideoCtrlButton（legacyContainer 已废弃）
  - 依据：视频架构风格报告 W1（三套按钮字号/圆角/背景色均不统一，违反设计一致性原则）
  - 验证：Read 确认按钮样式定义
- [ ] 11.7 视频字号硬编码改 dimen（11sp/12sp/13sp → 项目标准字号 dimen）
  - 修复点：11sp → font_size_xs 或 text_label_small；12sp → font_size_normal 或 text_label_medium；13sp → font_size_normal
  - 依据：视频架构风格报告 W3（项目无 11sp/12sp/13sp 标准字号，字号规范不一致）
  - 验证：Grep 确认视频布局无硬编码 sp 字号
- [ ] 11.8 视频间距硬编码改 spacing_* dimen
  - 修复点：4dp → @dimen/spacing_xs；8dp → @dimen/spacing_sm；12dp → @dimen/spacing_md；16dp → @dimen/spacing_lg
  - 依据：视频架构风格报告 W9（全部硬编码数字未引用 spacing_* dimen）
  - 验证：Grep 确认视频布局无硬编码 dp 间距
- [ ] 11.9 视频 PopupMenu 主题化（应用 Style.PopupMenu 主题）
  - 修复点：VideoFragment.kt:733 用 ContextThemeWrapper 包裹，应用 R.style.Style_PopupMenu
  - 依据：视频架构风格报告 W4（未应用 Style.PopupMenu 主题，暗亮主题下样式可能不一致）
  - 验证：Read 确认 PopupMenu 样式
- [ ] 11.10 视频全屏返回按钮统一用项目组件（原 btn_back_overlay）
  - 修复点：评估保留 TitleBar 但隐藏标题/菜单，仅显示返回按钮；或抽取 FullScreenBackButton 通用组件供其他需要全屏的 Activity 复用
  - 依据：视频架构风格报告 W5（偏离项目统一 TitleBar 组件）
  - 验证：Read 确认全屏返回按钮实现
- [ ] 11.11 视频 legacyContainer 整体清理（旧模式代码路径已永不执行）
  - 修复点：删除 activity_video_player.xml 中 legacyContainer 布局（line 30-315）+ VideoPlayerActivity.kt 中 useViewPagerMode = true 硬编码分支 + 旧模式代码
  - 依据：视频架构风格报告 §9.5（legacyContainer 已废弃，旧模式代码路径永不执行，减少维护负担）
  - 验证：Grep 确认 legacyContainer 相关代码已移除

## 12. 图片播放器风格对齐视频播放器（P0）

- [ ] 12.1 图片TitleBar 颜色硬编码改主题色（#80000000/Color.WHITE → primaryColor/primaryTextColor）
  - 修复点：移除 ImageGalleryActivity.initTitleBar() 中的 setBackgroundColor + setTextColor 硬编码，改用 TitleBar 默认主题机制；若需深色背景，XML 中用 app:themeMode="1" 启用 dark 模式
  - 依据：图片vs视频风格报告 E1（图片硬编码颜色，未走 TitleBar 默认主题机制）
  - 验证：Grep 确认 ImageGalleryActivity 无 Color.parseColor 硬编码
- [ ] 12.2 图片AlertDialog 改走 alert DSL + applyTint()（原原生 AlertDialog.Builder().setItems()）
  - 修复点：长按菜单改为 alert(title = "图片操作") { setItems(arrayOf("保存图片", "分享图片", "复制URL")) { ... } }；错误兜底改为 alert {} + positiveButton/neutralButton/negativeButton 三选项；自动应用 applyTint() 主题色
  - 依据：图片vs视频风格报告 E2/E8（原生 AlertDialog 无主题强调色、无圆角背景，与视频弹框样式割裂）
  - 验证：Grep 确认 ImageGalleryActivity 使用 alert {} DSL
- [ ] 12.3 图片按钮背景统一（bg_rotate_toolbar → bg_overlay_button，24dp → 12dp 圆角）
  - 修复点：旋转工具栏容器和按钮统一用 bg_overlay_button（12dp 圆角 + #80000000），移除 selectableItemBackgroundBorderless 与 bg_rotate_toolbar
  - 依据：图片vs视频风格报告 E3/E4（图片工具栏 24dp 圆角 + #B3000000 与视频 12dp 圆角 + #80000000 割裂；图片按钮无背景在浅色图片上几乎不可见）
  - 验证：Read 确认按钮背景 drawable 引用
- [ ] 12.4 图片沉浸式 API 统一（window.setFlags/systemUiVisibility → toggleSystemBar/WindowInsetsControllerCompat）
  - 修复点：ImageGalleryActivity.toggleImmersive() 改用 toggleSystemBar(show) 工具方法，移除 window.setFlags(FLAG_LAYOUT_NO_LIMITS) 与 systemUiVisibility
  - 依据：图片vs视频风格报告 E5（旧 API 在 API 30+ 已废弃，Android 11+ 沉浸式可能失效）
  - 验证：Grep 确认 ImageGalleryActivity 无 window.setFlags/systemUiVisibility
- [ ] 12.5 图片架构模式统一（RecyclerView.Adapter 嵌套 ViewPager2 → FragmentStateAdapter + Fragment）
  - 修复点：拆 ImagePageFragment，参考 VideoFragment，将每个图集页拆为 Fragment，用 FragmentStateAdapter 替代 RecyclerView.Adapter 嵌套 ViewPager2；Fragment 自管 PhotoView + 旋转状态 + 长按菜单
  - 依据：图片vs视频风格报告 E7（图片架构更容易内存泄漏，ViewHolder 持有多个 adapter 引用，回收时序复杂）
  - 验证：Read 确认 ImageArticlePagerAdapter 实现 FragmentStateAdapter
- [ ] 12.6 图片错误降级链补全（内嵌 tvError/btnRetry → alert {} 四级降级对话框）
  - 修复点：图片错误时用 alert {} 提供"重试"/"浏览器打开"/"复制URL"三选项，与视频四级降级链对齐
  - 依据：图片vs视频风格报告 E8（图片错误兜底仅内嵌布局，无降级链，缺少用户决策入口）
  - 验证：Read 确认错误降级链实现
- [ ] 12.7 图片按钮点击效果统一（selectableItemBackgroundBorderless → bg_overlay_button）
  - 修复点：图片按钮改用 bg_overlay_button，与视频一致，半透明黑底始终可见
  - 依据：图片vs视频风格报告 E4（图片按钮在浅色图片上几乎不可见）
  - 验证：Read 确认按钮点击效果
- [ ] 12.8 图片圆角规范统一（24dp/12dp 混用 → 统一 12dp）
  - 修复点：旋转工具栏圆角改为 12dp，与页码指示器 12dp 和视频 12dp 对齐
  - 依据：图片vs视频风格报告 E6（图片内部圆角规范已不统一，与视频 12dp 也不一致）
  - 验证：Grep 确认圆角值统一
- [ ] 12.9 图片自动隐藏+动画（3秒+alpha+translationY，参考视频播放器）
  - 修复点：参考 VideoFragment.scheduleAutoHide(3000L) + hideControlsAnimated() + showControlsAnimated()，为图片旋转工具栏+页码+TitleBar 实现 3 秒自动隐藏 + 300ms 淡入淡出
  - 依据：图片vs视频风格报告 W3/W6（图片无控件自动隐藏机制，沉浸式切换无动画硬切）
  - 验证：Read 确认自动隐藏动画实现
- [ ] 12.10 图片返回按钮统一 onBackPressedDispatcher（原 finish()）
  - 修复点：setNavigationOnClickListener { onBackPressedDispatcher.onBackPressed() }，与视频对齐
  - 依据：图片vs视频风格报告 W1（图片返回行为不统一，全屏退出行为差异）
  - 验证：Grep 确认 onBackPressedDispatcher.onBackPressed 调用
- [ ] 12.11 图片 tint 写法统一 app:tint（原 android:tint）
  - 修复点：图片布局中 app:tint="@android:color/white" 改为 app:tint="@color/white"（项目颜色引用）；视频也建议改为 @color/white 引用统一
  - 依据：图片vs视频风格报告 W2（app:tint 兼容性更好，颜色引用风格统一）
  - 验证：Grep 确认 app:tint 使用
- [ ] 12.12 图片 longSnackbar 引入（带操作场景用 Snackbar，原仅 toastOnUi）
  - 修复点：图片保存图片/分享等可能误操作的场景，用 longSnackbar 提供撤销入口（参考视频 binding.root.longSnackbar(R.string.jump_to_another_app, R.string.confirm)）
  - 依据：图片vs视频风格报告 W4（图片无确认型 Snackbar）
  - 验证：Grep 确认 longSnackbar 调用
- [ ] 12.13 UI 样式美化总任务（R2 修订，P0-8，对应 spec.md R4.9）
  - 修复点：**R2 修订新增**——spec.md R4.9（UI 样式美化任务）在原 tasks.md 中找不到对应任务项，本次补全。包含三维度美化：
    - **配色维度**：视频/图片播放器所有硬编码颜色清理完毕（22 类，对应阶段 11.3 + 12.1）；新增 transparent70/80/100 色阶；亮/暗/E-Ink 三模式主题切换验证
    - **图标维度**：视频/图片播放器所有图标统一引用项目 drawable（bg_overlay_button / drag_handle_bg / image_loading 等）；android:tint 统一改 app:tint（对应阶段 12.11）；删除冗余 bg_rotate_toolbar 等遗留 drawable
    - **间距维度**：视频/图片播放器所有硬编码 dp 间距改 spacing_* dimen（对应阶段 11.8）；所有硬编码 sp 字号改 font_size_* dimen（对应阶段 11.7）；圆角规范统一 12dp（对应阶段 12.8）
  - 依据：P0-8（spec.md R4.9 在 tasks.md 找不到对应任务）+ spec.md R4.9 + design.md AD-10/AD-11
  - 验证：真机并列打开视频/图片播放器，三维度（配色/图标/间距）视觉风格统一；Grep 确认无硬编码颜色/sp 字号/dp 间距残留

## 13. 提取通用播放器基类（P1，R2 修订，对齐 design.md AD-12 R2 方案 A+B）

> **R2 修订（P1-1）**：原方案"提取 BasePlayerActivity 基类"高风险——视频（全屏/PiP/字幕/倍速）与图片（PhotoView 缩放/旋转/长按菜单）业务差异大，共同点仅 3 个方法（toggleSystemBar + scheduleAutoHide + hideControlsAnimated），且 `toggleSystemBar` 已在 `ActivityExtensions.kt:187` 作为扩展函数存在，无需继承。改为"扩展函数 + 工具类"方案（方案 B）。
> BaseBottomSheetDialog 基类抽取保留（方案 A，风险等级中，项目当前无统一基类是真实薄弱点）。

- [ ] 13.1 新建 BaseBottomSheetDialog 基类（R2 保留方案 A，圆角16dp+drag_handle+主题背景+E-Ink适配）
  - 修复点：新建基类，封装圆角 corner_large 16dp 顶部圆角 + drag_handle_bg 拖拽指示 + ThemeStore.backgroundColor() 主题背景 + AppConfig.isEInkMode 描边适配；供 VideoSettingsPanel / HighlightStyleDialog / BottomWebViewDialog / NumberPickerDialog 共享
  - 依据：项目UI风格规范 §4.2 + R2 修订（图片模块当前无 BottomSheet 组件需求，移除 ImageInfoPanel 引用，P1-8）
  - 验证：Read 确认基类文件存在+关键方法
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` AD-12 方案 A
- [ ] 13.2 新建 PlayerControlsHelper 工具类（R2 修订方案 B，替代 BasePlayerActivity 基类抽取）
  - 修复点：**R2 修订**——放弃 BasePlayerActivity 基类抽取，改为抽取 `PlayerControlsHelper` 工具类（`ui/base/PlayerControlsHelper.kt`），封装 `scheduleAutoHide(delay: Long)` / `hideControlsAnimated()` / `showControlsAnimated()` 三个方法；`toggleSystemBar(show)` 复用已有 `ActivityExtensions.kt:187` 扩展函数，无需重新抽象
  - 依据：R2 修订 P1-1（BasePlayerActivity 高风险——视频/图片业务差异大，共同点仅 3 个方法；toggleSystemBar 已有扩展函数）
  - 验证：Read 确认 PlayerControlsHelper.kt 文件存在+三个方法签名
  - **同步文档（R2 修订，P0-6）**：同步 `docs/specs/image-gallery-activity/design.md` AD-12 方案 B
- [ ] 13.3 VideoPlayerActivity 调用 PlayerControlsHelper 工具类方法（R2 修订，非继承）
  - 修复点：**R2 修订**——从原"改继承 BasePlayerActivity"改为"调用 PlayerControlsHelper 工具类方法"（非继承关系）；保留 VMBaseActivity 继承不变；在 VideoPlayerActivity 中持有一个 PlayerControlsHelper 实例，委托调用 scheduleAutoHide / hideControlsAnimated / showControlsAnimated
  - 依据：R2 修订 P1-1（规避基类膨胀反模式，工具类调用不如继承优雅但规避风险）
  - 验证：Grep 确认 VideoPlayerActivity 含 PlayerControlsHelper 实例引用
- [ ] 13.4 ImageGalleryActivity 调用 PlayerControlsHelper 工具类方法（R2 修订，非继承）
  - 修复点：**R2 修订**——同 13.3，从原"改继承 BasePlayerActivity"改为"调用 PlayerControlsHelper 工具类方法"（非继承关系）；保留 VMBaseActivity 继承不变；在 ImageGalleryActivity 中持有一个 PlayerControlsHelper 实例，委托调用
  - 依据：R2 修订 P1-1（同 13.3）
  - 验证：Grep 确认 ImageGalleryActivity 含 PlayerControlsHelper 实例引用
- [ ] 13.5 VideoSettingsPanel 改继承 BaseBottomSheetDialog（R2 保留）
  - 修复点：阶段 11.2 已改为继承 BaseDialogFragment，进一步改为继承 BaseBottomSheetDialog（若 BaseBottomSheetDialog 继承 BaseDialogFragment 则兼容）
  - 依据：阶段 13.1 基类抽取后的必然重构
  - 验证：Grep 确认继承关系

## 14. 风格统一验证（新增）

- [ ] 14.1 真机验证视频播放器亮/暗主题切换（所有颜色跟随主题）
  - 修复点：切换亮/暗主题，观察视频模块所有颜色跟随主题（无硬编码残留）
  - 依据：阶段 11.3 颜色硬编码清除后的真机验证
  - 验证：真机切换主题，观察视频模块颜色跟随
- [ ] 14.2 真机验证图片播放器亮/暗主题切换
  - 修复点：切换亮/暗主题，观察图片模块所有颜色跟随主题
  - 依据：阶段 12.1 TitleBar 颜色硬编码清除后的真机验证
  - 验证：真机切换主题，观察图片模块颜色跟随
- [ ] 14.3 真机对比视频/图片播放器 TitleBar/按钮/弹框风格视觉一致性
  - 修复点：真机并列打开两个播放器，观察 TitleBar/按钮/弹框风格统一
  - 依据：阶段 11/12 风格对齐后的整体一致性验证
  - 验证：真机观察视觉一致性
- [ ] 14.4 真机验证 BottomSheet 弹框使用统一基类（R2 修订，P1-8）
  - 修复点：**R2 修订**——真机触发 VideoSettingsPanel，确认圆角/拖拽/背景一致（**R2 修订 P1-8**：移除 ImageInfoPanel 引用——图片模块当前无 BottomSheet 组件需求，本期不新建 ImageInfoPanel）
  - 依据：阶段 13.1 BaseBottomSheetDialog 基类抽取后的真机验证 + R2 修订 P1-8
  - 验证：真机观察 BottomSheet 风格统一
- [ ] 14.5 真机验证沉浸式模式使用统一 API（无旧 API 警告）
  - 修复点：logcat 确认无 SYSTEM_UI_FLAG 废弃警告，无 window.setFlags 旧 API 警告
  - 依据：阶段 12.4 沉浸式 API 统一后的真机验证
  - 验证：logcat Grep 确认无旧 API 警告

---

## R 编号↔任务编号映射表（R2 修订，P0-8 + P1-9）

> **R2 修订背景**：
> - P0-8：spec.md R4.9（UI 样式美化任务）在原 tasks.md 中找不到对应任务项，已新增阶段 12.13 补全
> - P1-9：spec.md R2.10 原引用任务编号 2.17/2.18/2.19/2.20/3.6，但 tasks.md 实际编号为 4.1/4.2/4.3/4.4/4.5，spec.md R2.10 已修正，本映射表明确对应关系

| spec.md R 编号 | tasks.md 任务编号 | 任务描述 | 对应 design.md ADR |
|---------------|------------------|---------|------------------|
| R2.10 | 4.1 | 补全 AD-06 header/cookie 复用 ADR | AD-03（图片 header/cookie 复用） |
| R2.10 | 4.2 | 补全 AD-07 多线程预缓存 ADR | AD-04（图片多线程预缓存） |
| R2.10 | 4.3 | 补全 AD-08 articleStyle==2 路由回退 ADR | AD-05（articleStyle==2 路由回退） |
| R2.10 | 4.4 | 补全图片尺寸适配 ADR | AD-06（图片尺寸适配，R2 修订） |
| R2.10 | 4.5 | 补全跨文章预加载 ADR | AD-04（跨文章预加载） |
| R4.9 | 12.13 | UI 样式美化总任务（配色/图标/间距三维度） | AD-10/AD-11 |
| R2.1 | 2.1 | 保留 L4 URL 后缀兜底但不缓存（R2 修订） | AD-01（R2 修订） |
| R2.3 | 5.4 | 修复图片尺寸适配（resetView 不改 scaleType + 横屏 centerCrop） | AD-06（R2 修订） |
| R2.9 | 11.3 | 清除视频硬编码颜色（22 类完整清单） | AD-10（R2 修订） |
| R2.12 | 13.1 + 13.2 | BaseBottomSheetDialog 基类 + PlayerControlsHelper 工具类（方案 A+B） | AD-12（R2 修订） |

> 注：本表仅列出 R2 修订涉及的关键 R 编号映射；其他 R 编号（如 R3.x/R4.x）与 tasks.md 任务编号的对应关系在原任务项的"依据"字段已体现。

## 任务统计

| 阶段 | 任务数 | 优先级 | 依据 |
|------|--------|--------|------|
| 1. 准备工作 | 3 | - | 规范要求 |
| 2. 视频 ERROR | 5 | P0 | 视频设计 E-1/E-2 + 视频代码 E1/W1 |
| 3. 视频 WARN | 4 | P1 | 视频设计 W-1~W-5 + 视频代码 W2~W4 |
| 4. 图片设计 ERROR | 10 | P0 | 图片设计 E1~E10 |
| 5. 图片代码 ERROR | 6 | P0 | 图片代码 Bug1~Bug3 + 交叉验证 W-03 |
| 6. 图片 WARN | 6 | P1 | 图片代码 Bug4~Bug9 |
| 7. 交叉验证 ERROR | 2 | P0 | 交叉验证 E-01/E-02 |
| 8. 全局索引同步（R2 拆分） | 3 | 强制 | version-delivery-sync 规范（原 5 项拆分到各阶段，仅保留 INDEX/updateLog/task-navigation） |
| 9. 验证 | 15 | - | ai_e2e_testing_workflow 规范 + 风格统一验证（R2 新增 9.0 数据准备 + 9.13 协程取消） |
| 10. AOAdapt 日志 | 1 | - | 实施过程记录（R2 补全阶段行至 11 行） |
| 11. 视频架构风格对齐 | 11 | P0 | 视频架构风格报告 E1~E6 + W1~W11 |
| 12. 图片风格对齐视频 | 13 | P0 | 图片vs视频风格报告 E1~E8 + W1~W6（R2 新增 12.13 UI 样式美化） |
| 13. 提取通用基类 | 5 | P1 | 项目UI风格规范 §4.2 + 图片vs视频 §10.3（R2 改为 PlayerControlsHelper 方案） |
| 14. 风格统一验证 | 5 | - | 阶段 11-13 真机验证 |
| **合计** | **89** | - | - |

## 问题分级汇总

| 审查报告 | ERROR | WARN | INFO | 小计 |
|---------|-------|------|------|------|
| 视频设计 | 2 | 5 | 4 | 11 |
| 视频代码 | 1 | 4 | 6 | 11 |
| 图片设计 | 10 | 7 | 3 | 20 |
| 图片代码 | 3 | 6 | 3 | 12 |
| 交叉验证 | 2 | 5 | 3 | 10 |
| 视频架构风格 | 6 | 11 | 8 | 25 |
| 图片vs视频风格 | 8 | 6 | 5 | 19 |
| 项目UI风格基线 | 0 | 0 | 0 | 0 |
| **合计** | **32** | **44** | **32** | **108** |

> 注：原始统计 32 ERROR + 38 WARN + 13 INFO 已含风格审查新增问题（去重后）；上述汇总表展示全量分级，部分 WARN/INFO 与原有问题重叠已合并。

---

## R4 任务清单（核心能力提升）

> **来源**：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §5 实施路线图
> **优先级**：P0（核心能力提升，对齐浏览器五层架构）+ P1（降级链 + 加密流）
> **预期收益**：抓取 +40% / 识别 +50% / 播放 +55%（[R4-enhancement-plan.md](./R4-enhancement-plan.md) §4.3）
> **包名规范**：所有真机验证必须使用测试包 `io.legado.miss.app.debug`（按 `package-naming.md` 规范，代码优化任务用测试包）
> **执行顺序**：Phase 1（视频 P0）→ Phase 2（视频 P1）→ Phase 3（图片 P0）→ Phase 4（图片 P1）→ Phase 5（文档同步与验收）

### Phase 1：视频 P0 改造（核心能力提升）

- [ ] R4-T1: MimeSniffer.kt 扩展完整 Magic Number 签名表（17 项 + 二次校验 + MPEG-TS 多次匹配）
  - 修复点：当前 MimeSniffer.kt L60-L102 仅支持 6 种格式（MP4/M3U8/FLV/TS/MKV/MPD），扩展为 17 项完整签名表（对齐 WHATWG §6.2 + Go `net/http/sniff.go` + Java `VideoMagicNumberEnum`）。MPEG-TS 特殊处理：0x47 单字节匹配会误判，需扫描前 188 字节内是否多次出现 0x47（间隔 188 字节，至少 3 次匹配）。AVI/WAV 二次校验：RIFF 容器需检查偏移 8 是否为 "AVI " / "WAVE"。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.1 + 调研报告 research-browser-sniffing.md §6.1 缺陷7
  - 验证：Read MimeSniffer.kt 确认签名表扩展为 17 项；单元测试覆盖 MP4/WebM/MKV/FLV/AVI/WMV/MPEG-PS/MPEG-TS/OGG/MP3/ADTS/WAV/FLAC
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/MimeSniffer.kt`

- [ ] R4-T2: MimeSniffer.kt 新增 `isReallyM3u8` / `isReallyMpd` / `detectMoovPosition` 主动 Probe 函数
  - 修复点：当前仅看 URL 后缀 + Content-Type 判断 m3u8/mpd，未下载内容验证。新增主动 Probe 函数：`isReallyM3u8(body: ByteArray): Boolean`（首行 `#EXTM3U`）/ `isReallyMpd(body: ByteArray): Boolean`（根元素 `<MPD>`）/ `detectMoovPosition(head: ByteArray): MoovPosition`（FRONT/BACK/UNKNOWN）。触发时机：当 URL 后缀或 Content-Type 提示是 HLS/DASH 时，主动下载清单内容（前 8KB 足够）验证。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.3 + §2.3.9 + 调研报告 research-browser-sniffing.md §6.1 缺陷1/4
  - 验证：Grep 确认 3 个新函数存在；单元测试覆盖标准 m3u8/mpd 内容 + 错误内容
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/MimeSniffer.kt`

- [ ] R4-T3: MimeSniffer.kt 修改 `SNIFF_LENGTH` 从 1KB 提升到 8KB
  - 修复点：当前 `sniffWithRangeRequest` 读前 1KB（`bytes=0-1023`），提升到 8KB（对齐 ExoPlayer 默认 ExtractorInput 缓冲区）。新增常量 `const val SNIFF_LENGTH = 8 * 1024`，`sniffWithRangeRequest` 用 `bytes=0-${SNIFF_LENGTH - 1}`。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.4 + 调研报告 research-browser-sniffing.md §6.1 缺陷2
  - 验证：Grep 确认 `SNIFF_LENGTH = 8 * 1024`；Range 请求头为 `bytes=0-8191`
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/MimeSniffer.kt` + `ExoPlayerHelper.kt`

- [ ] R4-T4: ExoPlayerHelper.kt 新增 `createMediaSource` 函数（按嗅探结果分发 MediaSource）
  - 修复点：当前 ExoPlayerHelper.kt L304-L319 已初始化 DefaultExtractorsFactory，但未按嗅探结果分发 MediaSource。新增 `createMediaSource(sniff: SniffResult, url, dataSourceFactory): MediaSource` 函数：HLS → HlsMediaSource（含 CustomHlsKeyManager 支持 AES-128）/ DASH → DashMediaSource / SS → SsMediaSource / PROGRESSIVE → ProgressiveMediaSource + DefaultExtractorsFactory（含全部 14 个 Extractor）/ UNKNOWN → 抛 UnrecognizedInputFormatException 进入降级链。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.2 + 调研报告 research-mature-players.md（ExoPlayer DefaultExtractorsFactory 三级排序）
  - 验证：Read ExoPlayerHelper.kt 确认 `createMediaSource` 函数存在；4 种 MediaSource 类型分支完整
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`

- [ ] R4-T5: ExoPlayerHelper.kt 新增 `sniffVideoType` 函数（7 维度交叉验证）
  - 修复点：新增 `sniffVideoType(url, headers): SniffResult` 函数，实现 7 维度交叉验证架构：(1) Content-Type 提示（弱信号）(2) 最终 URL 后缀提示（弱信号，重定向后）(3) 初始 URL 后缀提示（弱信号）(4) Magic Number 匹配（强信号，17 项完整签名表）(5) 主动 Probe 清单内容（强信号，HLS/DASH）(6) MP4 moov 位置检测（FRONT/BACK/UNKNOWN）(7) Accept-Ranges 检测（断点续传支持）。返回 SniffResult 含 contentType + mimeType + moovPosition + supportsRange。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.2 + 调研报告 research-browser-sniffing.md §6.2
  - 验证：Read ExoPlayerHelper.kt 确认 `sniffVideoType` 函数存在；7 维度交叉验证逻辑完整
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`

- [ ] R4-T6: ExoPlayerHelper.kt 替换 UA 为浏览器 UA + 启用 setAllowCrossProtocolRedirects(true)
  - 修复点：当前使用 `Util.getUserAgent(context, "Legado")` 生成 UA `Legado/1.0 (Linux; U; Android 13)`，部分站点 CDN 拒绝非浏览器 UA。替换为浏览器 UA `Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36`，并启用 `setAllowCrossProtocolRedirects(true)` 支持 HTTP↔HTTPS 跨协议重定向。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.5
  - 验证：Grep 确认 BROWSER_UA 常量；Grep 确认 `setAllowCrossProtocolRedirects(true)`
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`

- [ ] R4-T7: Phase 1 编译验证 + 真机测试（用 io.legado.miss.app.debug 测试包）
  - 修复点：编译测试包验证语法 + 安装到真机/模拟器，用 m3u8/mp4/flv/ts/mkv 五类视频源验证嗅探准确率
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §5 Phase 1 + ai_e2e_testing_workflow 规范
  - 验证：`python ai_tests/scripts/quick_build_install.py` 编译+安装+L1 验证；`adb logcat -s SniffingMime:* MimeSnifferCache:* ExoFallback:*` 收集嗅探日志；5 类视频源各播放 1 次，统计嗅探成功率
  - 包名：`io.legado.miss.app.debug`（测试包，uid=10064）

### Phase 2：视频 P1 改造（降级链 + 加密流）

- [ ] R4-T8: Exo2MediaPlayer.kt 新增 `playWithFallback` 函数（HLS→DASH→Progressive 降级链）
  - 修复点：当前单一 MediaSource 失败即整体失败，仅 3003 错误触发自动 WebView 降级。新增 `playWithFallback(url, headers): Boolean` 函数，实现 4 步降级链：(1) 按嗅探结果选择 MediaSource (2) 嗅探失败 → 尝试 HLS（最常见场景）(3) 尝试 DASH (4) 用 DefaultExtractorsFactory 全量嗅探（Progressive）。每步 5 秒超时（未触发 STATE_READY 则判定失败并尝试下一步），全部失败触发 VIDEO_FALLBACK_WEBVIEW 事件。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.6 + 调研报告 research-browser-sniffing.md §6.1 缺陷5
  - 验证：Read Exo2MediaPlayer.kt 确认 `playWithFallback` 函数存在；4 步降级链完整；每步 5 秒超时
  - 文件：`app/src/main/java/io/legado/app/service/web/Exo2MediaPlayer.kt`

- [ ] R4-T9: ExoPlayerHelper.kt 修改 `sniffWithRangeRequest` 支持重定向感知 + 最终 URL 嗅探
  - 修复点：当前嗅探时用初始 URL 判断后缀，未感知 302 重定向后 URL 变化。使用 OkHttp `followRedirects(true)` + `response.request().url` 获取最终 URL，用最终 URL 后缀 + Content-Type 双维度判断。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.7 + 调研报告 research-browser-sniffing.md §6.1 缺陷6
  - 验证：Read sniffWithRangeRequest 确认 `finalUrl = response.request.url` 存在；用最终 URL 后缀判断
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`

- [ ] R4-T10: 新建 CustomHlsKeyManager.kt 实现 AES-128 HLS 加密流支持
  - 修复点：当前不支持 `#EXT-X-KEY:METHOD=AES-128` 标签的 m3u8，播放黑屏。新建 `CustomHlsKeyManager` 实现 `HlsKeyManager` 接口，密钥请求带 Referer + BROWSER_UA 防盗链头，返回 `HlsKeyManager.KeyResult(keyData, iv, C.KEY_TYPE_AES)`。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §2.3.8
  - 验证：Read CustomHlsKeyManager.kt 文件存在；实现 HlsKeyManager 接口；密钥请求带 Referer + UA 头
  - 文件：`app/src/main/java/io/legado/app/help/exoplayer/CustomHlsKeyManager.kt`（新建）

- [ ] R4-T11: Phase 2 编译验证 + 真机测试（覆盖 m3u8+mp4+flv+加密 HLS 四类源）
  - 修复点：编译测试包 + 真机测试降级链触发情况 + AES-128 加密流播放
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §5 Phase 2
  - 验证：`python ai_tests/scripts/quick_build_install.py` 编译+安装+L1 验证；`adb logcat -s SniffingMime:* ExoFallback:* HlsKeyManager:*` 收集日志；4 类视频源各播放 1 次，验证降级链触发 + 加密流播放成功
  - 包名：`io.legado.miss.app.debug`（测试包，uid=10064）

### Phase 3：图片 P0 改造（核心能力提升）

- [ ] R4-T12: ImageGalleryActivity.kt 修复 WebView 预热循环覆盖（改串行队列）
  - 修复点：当前 `forEach { loadUrl }` 循环覆盖，多域名场景只有最后一个域名被预热。改为串行预热（一个域名 `onPageFinished` 后再加载下一个），或用多个 WebView 实例并行预热。推荐方案A（串行预热）：内存占用低，符合移动端资源约束。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §3.3.1 + 图片代码审查报告 Bug2
  - 验证：Read ImageGalleryActivity.kt 确认预热逻辑改为串行；多域名场景全部预热（preheatedDomains.size == uniqueDomains.size）
  - 文件：`app/src/main/java/io/legado/app/ui/book/read/rss/ImageGalleryActivity.kt`

- [ ] R4-T13: ImagePlay.kt 实现 `preloadNextArticleImages` + `preloadedArticles` 去重
  - 修复点：当前无跨文章预加载，上下滑动切换时下一张图片无法加载。参考 `VideoPlay.preloadNextArticleHtml`（L1040）实现 `preloadNextArticleImages(currentIndex)`：用协程 async 预加载下一篇文章图片 URL 列表，`preloadedArticles: MutableSet<String>` 去重，`preloadedImageUrls: MutableMap<String, List<String>>` 缓存，用 `Glide.preload()` 预加载前 3 张。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §3.3.2 + 图片设计报告 E3/E5
  - 验证：Read ImagePlay.kt 确认 `preloadNextArticleImages` 函数存在；preloadedArticles 去重逻辑；Glide.preload() 前 3 张
  - 文件：`app/src/main/java/io/legado/app/help/image/ImagePlay.kt`

- [ ] R4-T14: ImagePlay.kt 新增 `currentPlayHeaders` 字段跨文章复用 headers
  - 修复点：当前缺 `currentPlayHeaders` 字段跨文章复用 headers。新增 `currentPlayHeaders: Map<String, String>?` 字段（@Synchronized get/set），对齐 `VideoPlay`。`loadArticleContent` 中复用 currentPlayHeaders，避免每次重新解析 headerMap。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §3.3.3 + 图片代码审查报告 Bug4
  - 验证：Read ImagePlay.kt 确认 `currentPlayHeaders` 字段存在；@Synchronized 注解；loadArticleContent 中复用
  - 文件：`app/src/main/java/io/legado/app/help/image/ImagePlay.kt`

- [ ] R4-T15: Phase 3 编译验证 + 真机测试（图片源 + 防盗链源）
  - 修复点：编译测试包 + 真机测试 WebView 预热 + 跨文章预加载 + header/cookie 复用
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §5 Phase 3
  - 验证：`python ai_tests/scripts/quick_build_install.py` 编译+安装+L1 验证；多域名图片源验证全部预热；上下滑动切换验证预加载触发；防盗链源验证 header/cookie 复用
  - 包名：`io.legado.miss.app.debug`（测试包，uid=10064）

### Phase 4：图片 P1 改造（降级链）

- [ ] R4-T16: ImagePageAdapter.kt 实现图片加载失败降级链（Glide→OkHttp+Cookie→WebView 预热→网页模式）
  - 修复点：当前图片加载失败仅显示 `tvError` + `btnRetry`，无降级。实现四级降级链：(1) Glide 直接加载（含 Referer/Cookie 注入）(2) OkHttp + sourceOriginOption + refererOption 兜底 (3) WebView 预热获取 Cloudflare cookies 后重试 (4) 降级为网页模式（ReadRssActivity，用户主动选择）。Glide `RequestListener.onLoadFailed` 中触发降级链。
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §3.3.4 + 图片vs视频风格报告 E8
  - 验证：Read ImagePageAdapter.kt 确认 `retryWithFreshCookie` 函数存在；四级降级链完整
  - 文件：`app/src/main/java/io/legado/app/ui/book/read/rss/ImagePageAdapter.kt`

- [ ] R4-T17: Phase 4 编译验证 + 真机测试
  - 修复点：编译测试包 + 真机测试图片加载失败降级链触发情况
  - 依据：[R4-enhancement-plan.md](./R4-enhancement-plan.md) §5 Phase 4
  - 验证：`python ai_tests/scripts/quick_build_install.py` 编译+安装+L1 验证；构造图片加载失败场景（断网/防盗链），验证降级链触发
  - 包名：`io.legado.miss.app.debug`（测试包，uid=10064）

### Phase 5：文档同步与验收

- [ ] R4-T18: 更新 design.md/spec.md/tasks.md/README.md 体现 R4 能力提升方案（已完成✅状态行已更新，本任务仅补充遗漏细节）
  - 修复点：四文档顶部状态行已更新为"R4 修订完成，已开始实施"；本任务补充 design.md 中 R4 改造清单的代码锚点（MimeSniffer.kt L60-L102 / ExoPlayerHelper.kt L304-L319 / Exo2MediaPlayer.kt 等），spec.md 中 R4 收益矩阵（§4.3），README.md 中 R4 改造范围说明
  - 依据：version-delivery-sync 规范 + R4-enhancement-plan.md
  - 验证：Read 四文档确认 R4 信息完整

- [ ] R4-T19: 更新 assets/updateLog.md（基于 git diff 分析真实代码变更）
  - 修复点：基于 `git diff` 分析 R4-T1~T17 真实代码变更，生成用户可感知的更新日志（通俗语言描述，不暴露内部技术术语）。重点描述：视频播放器嗅探能力提升（抓取/识别/播放成功率提升）/ 图片播放器跨文章预加载 + 防盗链降级。
  - 依据：version-delivery-sync 规范（禁止文字合并已有条目，必须基于代码分析）
  - 验证：Read updateLog.md 确认新增条目基于真实代码变更

- [ ] R4-T20: 更新 docs/INDEX.md 状态
  - 修复点：将 player-review-and-optimization 状态从"设计中"更新为"R4 实施中"
  - 依据：version-delivery-sync 规范
  - 验证：Read INDEX.md 确认状态更新

- [ ] R4-T21: AskUserQuestion 验收检查点
  - 修复点：R4 全部任务完成后，用 AskUserQuestion 三选项结构（通过/需调整/拒绝）让用户验收
  - 依据：core-spec.md AskUserQuestion 强制规范
  - 验证：用户选择"通过"后方可标记 R4 任务完成

### R4 任务统计

| Phase | 任务数 | 优先级 | 预期收益 |
|-------|--------|--------|---------|
| Phase 1 视频 P0 | 7 | P0 | 抓取 +25% / 识别 +50% / 播放 +35% |
| Phase 2 视频 P1 | 4 | P1 | 播放 +35%（降级链 + 加密流） |
| Phase 3 图片 P0 | 4 | P0 | 抓取 +30% / 播放 +35% |
| Phase 4 图片 P1 | 2 | P1 | 播放 +15%（降级链） |
| Phase 5 文档同步与验收 | 4 | - | 文档与代码一致 |
| **合计** | **21** | - | 综合：抓取 +40% / 识别 +50% / 播放 +55% |
