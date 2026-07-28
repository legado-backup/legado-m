# 播放器成熟方案对齐 - 功能规格

> **创建时间**：2026-07-26
> **状态**：🔄 设计中
> **来源**：
> - [V2 深度架构分析报告](../player-deep-analysis-20260726-v2.md)（21 项短板清单 + 5 Phase 优化策略 + 验收标准）
> - [行业成熟方案查证报告](../../temp-analysis/industry-mature-solutions-verification-report-20260726.md)（49 个权威来源交叉验证）

---

## §1 Intent（为什么做）

V2 深度架构分析（架构合理性 + 效果验证 + 成熟方案支撑三维验证）发现当前播放器体系存在三类必须补齐的短板：

1. **10% AI 臆想设计**："五级识别链"是自创术语（WHATWG MIMESNIFF 规范只有三级：Content-Type → magic number → octet-stream）；L3 URL 后缀检测违反规范（规范明确禁止 URL 后缀用于 MIME 判断）
2. **20% 成熟方案遗漏（8 项）**：BandwidthMeter 动态调整、首帧预加载（I-frame）、下一个视频预加载（256KB）、图片金字塔、显式 MediaSource、渐进式加载、DoH、指数退避重试——全部有权威来源支撑但当前未实现
3. **图片播放器 3 个用户核心诉求未实现**：
   - "点击图片后切换为左右滚动播放"未实现（当前跳转 ImageDetailActivity，匹配度 0%）
   - "图片适配性最大尺寸展示"未完全实现（匹配度 70%，未处理超宽图/超长图等极端尺寸）
   - "上下滑动切换时下一个图片无法加载"部分未解决（匹配度 80%，预加载时机不智能）

叠加 8 个日志实证问题（重试耗尽无失败事件、嗅探双回调竞态、连接重置 0% 可用、缺失播放成功埋点等），导致**视频播放失败用户无感知、播放成功率无法量化、首屏速度与滑动流畅度落后于行业标杆、长图存在 OOM 风险**。

**本 spec 目标**：以 49 个权威来源验证的行业成熟方案为基准，分 5 个 Phase 补齐上述短板，将视频抓取/播放成功率和图片阅读体验提升到行业成熟水平；同时修正 AI 臆想设计，并保持"不实现域名前置"的正确决策。

---

## §2 Scope（做什么 / 不做什么）

### 2.1 做什么（5 个 Phase，21 项任务）

| Phase | 目标 | 任务数 | 优先级 | 预估工期 |
|-------|------|--------|--------|---------|
| Phase 1 | 可观测性 + 错误反馈闭环 | 4 | P0 | 1-2 天 |
| Phase 2 | 视频播放器核心能力补齐 | 5 | P0 | 2-3 天 |
| Phase 3 | 图片播放器核心诉求补齐 | 5 | P0 | 2-3 天 |
| Phase 4 | 网络层韧性 | 4 | P1 | 1-2 天 |
| Phase 5 | 架构优化（规范对齐） | 3 | P2 | 1 天 |

### 2.2 不做什么（非目标）

| 非目标 | 理由 |
|--------|------|
| ❌ 实现域名前置 | Google/Amazon/Microsoft 2018 年全部禁用，技术已失效（Stanford 研究 + Google 官方声明），维持 V2"正确决策"，以 DoH 替代 |
| ❌ 重复已实现功能 | 三级识别链、降级链、图片四级降级链、单画布垂直滚动、多线程并行加载等已完成且验证达标，不重复建设 |
| ❌ 替换播放器内核 | 继续基于 ExoPlayer（media3）+ GSY 封装演进，不引入新播放器内核 |
| ❌ 改动书源/订阅源规则引擎 | 本 spec 只触及播放器与网络层，规则引擎（CSS/JSONPath/XPath/正则/JS）不在范围内 |
| ❌ 全量重写图片播放器 | 在现有 ImageGalleryActivity + Glide 架构上增量补齐，不重写已完成且达标的垂直画布架构 |

---

## §3 Approach（怎么做）

### 3.1 Selected Approach（选定的技术方案及理由）

**总体策略**：按"先可观测、再补核心、后强韧性、终对齐规范"的依赖顺序串行执行 5 个 Phase；每项任务必须携带成熟方案参考落地，禁止新增 AI 臆想设计。

**Phase 顺序与依赖逻辑**：

```text
Phase 1（可观测性）─► Phase 2（视频核心）─► Phase 3（图片核心）─► Phase 4（网络韧性）─► Phase 5（架构规范）
      │                     │                    │                    │                   │
      └─ 埋点是后续量化验收前置  └─ P0 体验短板      └─ P0 用户核心诉求    └─ P0 稳定后做韧性  └─ 收尾，低风险
```

| Phase | 核心任务 | 成熟方案参考 |
|-------|---------|------------|
| **Phase 1：可观测性 + 错误反馈闭环**（P0） | 播放成功埋点（STATE_READY / onRenderedFirstFrame）；重试耗尽发送 videoPlayError 事件 + UI 错误提示；sniffVideoType 双回调竞态修复（AtomicBoolean）；SniffingMime 日志输出 logcat | ExoPlayer 官方；hls.js 错误恢复；Kotlin 协程最佳实践 |
| **Phase 2：视频核心能力补齐**（P0） | BandwidthMeter 动态调整缓冲参数；首帧预加载（I-frame + 首帧缓存）；下一个视频预加载（256KB + 网络感知队列）；指数退避重试（1s/2s/4s/8s/16s）；显式指定 MediaSource 类型 | Android 开发者官方指南；快手官方博客；抖音官方博客；hls.js 源码；ExoPlayer GitHub issue #1343 |
| **Phase 3：图片核心诉求补齐**（P0） | 点击图片切换左右滚动播放（ViewPager2 + PhotoView）；图片金字塔（多分辨率瓦片 + BitmapRegionDecoder）；图片适配性最大尺寸展示（极端尺寸处理）；智能预加载（onScrolled 结合滚动速度/位置）；渐进式加载（JPEG/WebP） | BigImageViewer；微信读书团队博客；SSIV；业界通用做法 |
| **Phase 4：网络层韧性**（P1） | DoH（自定义 OkHttp Dns，失败降级系统 DNS）；302 重定向缓存（自定义 Interceptor）；Cronet 降级宽限期 + 恢复探测；视频型订阅源正文解析降级 | Square 官方博客 + okhttp-dnsoverhttps；OkHttp Interceptor 最佳实践 |
| **Phase 5：架构优化**（P2） | 播放器实例池（3 实例复用）；"五级识别链"术语修正为"三级识别链 + URL 后缀兜底"；L3 URL 后缀检测降级为 Range 失败时兜底 | GSYVideoPlayer；WHATWG MIMESNIFF 规范 |

**选定理由**：

1. **可观测性先行**：V2 证实"播放成功率无法量化"（缺失成功埋点），没有量化基准就无法验证 Phase 2-4 的收益，Phase 1 是所有后续验收的前置条件
2. **P0 体验短板优先**：首帧预加载 / 下一个视频预加载 / 图片金字塔 / 横向播放直接决定用户可感知体验，且全部有官方方案支撑，风险低、收益高
3. **规范对齐收尾**：术语修正与 URL 后缀降级属于文档 + 实现的小幅调整，放在最后避免与功能改造产生冲突

### 3.2 Alternatives Considered（否决的替代方案及理由）

| # | 替代方案 | 否决理由 |
|---|---------|---------|
| 1 | **只修 8 个日志实证问题，不补齐成熟方案遗漏** | 日志问题修复仅解决"失败可见"，无法解决首屏速度慢、滑动卡顿、长图 OOM 等核心体验短板；8 项遗漏均有官方方案支撑且经快手/抖音/微信读书生产验证，放弃等于主动落后于行业标杆 |
| 2 | **只做视频播放器，不做图片播放器** | 图片播放器 3 个用户核心诉求匹配度仅 0% / 70% / 80%，"点击图片切换左右滚动"完全未实现；图片阅读是用户同等重要的核心场景，不做则体验闭环缺失 |
| 3 | **不修正 AI 臆想设计**（保留"五级识别链"术语 + L3 URL 后缀必经检测） | 违反 WHATWG MIMESNIFF 规范（规范明确禁止 URL 后缀用于 MIME 判断）；自创术语误导后续维护者与协作 AI；URL 后缀作为必经步骤增加误判风险，必须降级为兜底 |
| 4 | **实现域名前置应对 SNI 阻断/连接重置** | 域名前置已被 Google/Amazon/Microsoft 于 2018 年全部禁用（Stanford 研究 + Google 官方声明），技术已失效；应采用 DoH（Square 官方方案）替代 |
| 5 | **5 个 Phase 并行一次性全量实施** | 21 项任务并行改造冲突风险高（Exo2MediaPlayer / ExoPlayerHelper 为公共热点文件）；且无量化基准（Phase 1 埋点）则无法验证后续 Phase 收益，必须串行推进 |

### 3.3 Drawbacks（选定方案的已知缺点和接受理由）

| # | 缺点 | 影响 | 接受理由 |
|---|------|------|---------|
| 1 | **首帧预加载增加内存与流量占用** | 每个预加载视频额外消耗约 1-2MB 流量 + 首帧缓存内存 | 快手官方数据首帧命中率 90%+，首屏体验收益远大于成本；采用网络感知策略（WiFi 预加载 3 个 / 4G 预加载 1 个）控制流量消耗 |
| 2 | **图片金字塔增加实现复杂度** | 引入瓦片切割 / 分层加载 / BitmapRegionDecoder 等子系统 | 长图 OOM 是崩溃级风险必须解决；SSIV / BigImageViewer 为成熟开源组件（GitHub 高 star）可直接集成，避免自研瓦片引擎 |
| 3 | **DoH 增加 DNS 解析延迟** | 额外一次 HTTPS DNS 查询往返 | 按 TTL 缓存结果（默认 300 秒）摊薄成本；DoH 失败自动降级系统 DNS；仅对疑似被污染域名启用，全局延迟可控 |
| 4 | **播放器实例池增加常驻内存** | 3 个播放器实例常驻内存 | GSYVideoPlayer（38k+ stars）生产验证 3 实例池内存稳定；避免频繁创建/销毁导致的内存抖动与滑动卡顿，净收益为正 |
| 5 | **指数退避拉长极端场景恢复时间** | 第 5 次重试需等待 16s（累计约 31s） | 固定间隔重试在弱网/服务抖动时会形成请求雪崩；hls.js 生产验证指数退避 + 最多 5 次是业界标准平衡点；重试耗尽后有 UI 提示兜底（Phase 1），用户可决策 |
| 6 | **可观测性日志增加 I/O 开销** | 埋点 / 嗅探日志写入 logcat 与 AppLog | 日志级别可控（release 包可降级）；无量化数据则无法验证优化收益，属必要成本 |

### 3.4 Prior Art（类似工作参考：49 个权威来源，分类列出）

> 全部来源经 15 次检索交叉验证，详见[行业成熟方案查证报告](../../temp-analysis/industry-mature-solutions-verification-report-20260726.md)。按输出安全规范仅列来源名称，不附完整链接。

**Chrome 嗅探架构（4 个）**

1. How browsers work（Tamar Ben Cohen，Medium 技术博客）
2. debugbear 权威博客（preload scanner 机制）
3. WHATWG MIMESNIFF 官方规范
4. MDN X-Content-Type-Options 文档

**ExoPlayer 最佳实践（7 个）**

5. Android 开发者官方指南 - ExoPlayer 错误码表
6. ExoPlayer GitHub issue #10984（BehindLiveWindowException）
7. Medium 技术博客 - Buffering in ExoPlayer
8. Medium 技术博客 - JioCinema 缓冲逻辑案例
9. Android 开发者官方指南 - 轨道选择 / ABR
10. ExoPlayer GitHub issue #1343（MediaSource 选择）
11. Medium 技术博客 - m3u8 播放实践

**短视频播放器实例池（3 个）**

12. 快手技术团队官方博客（腾讯云开发者社区，首帧 I-frame 预加载，命中率 90%+）
13. 抖音技术团队官方博客（掘金，256KB 预加载 + 网络感知）
14. GitHub GSYVideoPlayer（38k+ stars，3 实例播放器池）

**图片阅读器（4 个）**

15. 微信读书团队博客（CSDN，图片金字塔 / 长图方案）
16. 微信开发者社区（长图渲染技术讨论）
17. GitHub SSIV（davemorrissey，瓦片加载 + BitmapRegionDecoder）
18. GitHub BigImageViewer（Piasy，大图 / 漫画阅读器）

**域名前置与 DoH（6 个）**

19. Wikipedia - Domain fronting
20. GreatFire 技术分析（域名前置原理）
21. Stanford 研究论文（域名前置现状）
22. Google 官方声明（2018 年禁用域名前置）
23. Square 官方博客 - OkHttp DoH
24. GitHub okhttp-dnsoverhttps 模块

**播放器错误恢复（5 个）**

25. GitHub video-dev/hls.js（错误分类 + startLoad/recoverMediaError）
26. Bitsontherun 技术博客（hls.js 错误恢复实践）
27. Akamai 官方博客（Video.js 错误恢复）
28. THEOplayer 官方文档（PlayerErrorRecovery 接口）
29. hls.js 源码 config.ts（指数退避重试参数）

**其他补充来源（20 个）**

30-49. Chromium 源码（sniffing_util.cc / mime_sniffer.cc）、Chromium issue 432581（204 No Content 处理）、掘金/CSDN 等技术社区补充来源，已在查证报告正文逐项引用。

---

## §4 Requirements（需求清单）

> 共 20 项需求（P0 × 9 + P1 × 8 + P2 × 3），覆盖 V2 报告全部 21 项短板：P2-21 / P2-22 合并为 REQ-P2-3；Phase 1 的"SniffingMime 日志输出"并入 REQ-P0-4 可观测性需求；P0-3 与 P1-5 同属 DoH 方案但场景不同（视频连接重置 vs 图片 DNS 过滤），分别列项。

### 4.1 P0 需求（9 项，必须立即修复）

| ID | 需求 | V2 任务 | 成熟方案参考 | 验收标准 |
|----|------|---------|------------|---------|
| REQ-P0-1 | 播放失败事件闭环：重试耗尽后发送 videoPlayError 事件 + UI 错误提示 | P0-1 | hls.js 错误恢复（startLoad/recoverMediaError） | 所有失败场景（重试耗尽 / 降级链结束）均有 UI 提示 + logcat 失败事件，无静默失败 |
| REQ-P0-2 | sniffVideoType 双回调竞态修复（AtomicBoolean/Mutex 保证单次回调） | P0-2 | Kotlin 协程最佳实践 | 同一 URL 嗅探仅回调一次，logcat 无双回调记录，状态不混乱 |
| REQ-P0-3 | DoH 绕过 DNS 污染/SNI 阻断（自定义 OkHttp Dns，失败降级系统 DNS） | P0-3 | Square 官方博客 + GitHub okhttp-dnsoverhttps | 连接重置类场景（站点D 类型）可建立连接；DoH 失败自动降级系统 DNS，正常域名不受影响 |
| REQ-P0-4 | 播放成功埋点 + 嗅探日志可观测（STATE_READY/onRenderedFirstFrame 埋点；SniffingMime 日志输出 logcat） | P0-9 + Phase 1 日志任务 | ExoPlayer 官方（STATE_READY/onRenderedFirstFrame） | logcat 可统计播放成功率；ai_test 脚本可基于日志自动化分析 |
| REQ-P0-5 | BandwidthMeter 动态调整缓冲参数（替代硬编码 minBufferMs/maxBufferMs） | P0-10 | Android 开发者官方指南（ABR / 轨道选择） | WiFi/4G/弱网环境下缓冲策略合理，无频繁 rebuffer；日志可见带宽测量回调生效 |
| REQ-P0-6 | 首帧预加载（I-frame 预加载 + 首帧内存缓存） | P0-11 | 快手官方博客（首帧命中率 90%+） | 首帧命中率 ≥80%（日志统计）；滑动到目标视频时首帧立即显示 |
| REQ-P0-7 | 下一个视频预加载（256KB + 网络感知队列） | P0-12 | 抖音官方博客（256KB + WiFi 3 个 / 4G 1 个） | WiFi 预加载 3 个、4G 预加载 1 个；滑动切换无黑屏等待；LRU 淘汰生效 |
| REQ-P0-8 | 图片金字塔（多分辨率瓦片 + 可视区域按需加载） | P0-13 | 微信读书团队博客 + SSIV（BitmapRegionDecoder） | 万像素级长图浏览不 OOM；内存占用与图片尺寸解耦；缩放时加载对应层级瓦片 |
| REQ-P0-9 | 点击图片切换左右滚动播放（ImageGalleryActivity 内 ViewPager2 + PhotoView） | P0-14 | BigImageViewer + ViewPager2/PhotoView | 点击图片后在当前 Activity 内左右滑动切换，支持双击/双指缩放；不再跳转 ImageDetailActivity |

### 4.2 P1 需求（8 项，重要优化）

| ID | 需求 | V2 任务 | 成熟方案参考 | 验收标准 |
|----|------|---------|------------|---------|
| REQ-P1-1 | RSS 正文解析异常分支治理（视频型订阅源正文为空不抛异常） | P1-4 | 业界通用做法（内部日志治理，无单一权威文档） | 视频型订阅源正文为空时走正常降级分支，异常噪音日志清零 |
| REQ-P1-2 | 图片 CDN 域名 DNS 过滤治理（DoH 覆盖图片域名解析） | P1-5 | Square 官方博客（DoH） | 被本地 DNS 过滤的图片 CDN（站点A 类型）恢复可访问，图片加载成功率提升 |
| REQ-P1-3 | 302 重定向缓存（自定义 OkHttp Interceptor 缓存重定向结果） | P1-6 | OkHttp Interceptor 最佳实践 | 同一 URL 不重复发起 302 跳转请求，带宽消耗下降，日志可见缓存命中 |
| REQ-P1-4 | 显式指定 MediaSource 类型（按嗅探结果，不依赖 URL 后缀自动检测） | P1-15 | ExoPlayer GitHub issue #1343 | 所有 MediaSource 均显式指定类型；URL 无后缀/后缀错误时仍选对 MediaSource |
| REQ-P1-5 | 渐进式图片加载（JPEG/WebP 渐进式，先模糊后清晰） | P1-16 | 微信读书团队博客 | 图片按"缩略图 → 预览图 → 原图"顺序呈现，感知加载时间缩短 |
| REQ-P1-6 | 指数退避重试策略（1s/2s/4s/8s/16s，最多 5 次） | P1-17 | hls.js 源码 config.ts | 重试间隔严格按指数退避序列执行；无固定间隔重试；日志可见退避序列 |
| REQ-P1-7 | 图片适配性最大尺寸展示（处理超宽图/超长图等极端尺寸） | P1-18 | 自定义 GlideModule / View layout（业界通用做法） | 所有图片（含极端尺寸）按屏幕适配最大尺寸展示，无过小显示/拉伸变形 |
| REQ-P1-8 | 图片预加载时机智能判断（LayoutManager.onScrolled 结合滚动速度/位置） | P1-19 | LayoutManager.onScrolled 精确控制（业界通用做法） | 上下滑动切换时目标图片已加载完成，无白屏等待；快速滚动时暂停加载省流量 |

### 4.3 P2 需求（3 项，体验与规范优化）

| ID | 需求 | V2 任务 | 成熟方案参考 | 验收标准 |
|----|------|---------|------------|---------|
| REQ-P2-1 | Cronet 降级阈值宽限期 + 恢复探测 | P2-8 | 业界通用做法（内部策略优化，无单一权威文档） | 启动 300ms 内不累计失败计数；Cronet 降级后可探测恢复，Cronet 优势不丧失 |
| REQ-P2-2 | 播放器实例池（3 个实例复用） | P2-20 | GSYVideoPlayer（GitHub 38k+ stars） | 快速滑动不卡顿；内存稳定无抖动；超过 3 个实例时释放最旧实例 |
| REQ-P2-3 | AI 臆想设计修正（术语 + 实现）："五级识别链"改为"三级识别链 + URL 后缀兜底"；L3 URL 后缀检测降级为 Range 请求失败时兜底 | P2-21 + P2-22 | WHATWG MIMESNIFF 官方规范 | 文档术语与规范一致；URL 后缀不再作为必经检测步骤；识别行为符合规范 |

### 4.4 总体验收标准（继承 V2）

1. **可量化**：播放成功率、首帧命中率（≥80%）、图片加载成功率均有埋点统计，可对比优化前后提升幅度
2. **可观测**：嗅探 / 播放成功 / 播放失败 / 降级 / 首帧预加载 / 图片金字塔加载等关键事件全部有 logcat 日志
3. **用户无感知失败清零**：所有失败场景都有 UI 错误提示 + 用户决策入口
4. **稳定性不回归**：保持 0 崩溃 / 0 ANR / 0 OOM
5. **成熟方案对齐**：所有 P0/P1 任务均有成熟方案参考支撑，无新增 AI 臆想
6. **ai_test 自动化**：所有验收标准可用 ai_tests/scripts 自动化验证（代码优化任务使用测试包 io.legado.miss.app.debug 真机验证）

---

## §5 Scenarios（核心场景）

### 场景 1：视频嗅探成功（三级识别链 + 显式 MediaSource）

- **前置**：用户打开含视频的 RSS 文章
- **流程**：VideoUrlExtractor 提取视频 URL → 三级识别链嗅探（Content-Type → Range 请求 magic number → 默认推断，URL 后缀仅作兜底）→ 按嗅探结果显式构建 MediaSource → ExoPlayer 起播
- **预期**：STATE_READY + onRenderedFirstFrame 埋点写入 logcat，播放成功率可统计；无 URL 后缀误判（对应 REQ-P0-4 / REQ-P1-4 / REQ-P2-3）

### 场景 2：视频播放失败降级与提示（错误反馈闭环）

- **前置**：视频加载触发网络错误（如连接失败/超时/HTTP 状态码错误）
- **流程**：错误码分类处理 → 指数退避重试（1s/2s/4s/8s/16s，最多 5 次）→ 重试失败沿降级链切换 MediaSource 类型 → 降级链结束自动降级 WebView → 重试耗尽发送 videoPlayError 事件 + UI 错误提示
- **预期**：无静默失败；所有失败场景有 UI 提示 + 用户决策入口；logcat 全程可追溯（对应 REQ-P0-1 / REQ-P1-6）

### 场景 3：短视频滑动预加载（首帧 + 下一个视频）

- **前置**：用户处于短视频列表，当前视频播放中
- **流程**：当前视频播放至 50% → 预加载下一个视频前 256KB（WiFi 队列 3 个 / 4G 队列 1 个，LRU 淘汰）→ 同步完成首帧 I-frame 预加载并缓存到内存
- **预期**：滑动切换时首帧立即显示（命中率 ≥80%），无黑屏等待；4G 下流量消耗受控（对应 REQ-P0-6 / REQ-P0-7）

### 场景 4：长图阅读（图片金字塔防 OOM）

- **前置**：用户打开含超长图的文章
- **流程**：图片金字塔将长图分为多分辨率层级瓦片 → 按当前缩放级别与可视区域按需加载瓦片（BitmapRegionDecoder）→ LRU 内存缓存 + 磁盘缓存 → 按滑动方向预加载下一屏瓦片
- **预期**：万像素级长图流畅缩放不 OOM；内存占用与图片尺寸解耦（对应 REQ-P0-8）

### 场景 5：图片加载失败降级（四级降级链 + DoH）

- **前置**：Glide 加载图片失败（网络错误 / CDN 域名被本地 DNS 过滤）
- **流程**：Glide 重试 → OkHttp 兜底（经 DoH 解析被过滤域名）→ WebView 即时预热 → 网页模式回退
- **预期**：被本地 DNS 过滤的图片 CDN（站点A 类型）恢复可访问；每级降级有日志；最终失败有 UI 提示（对应 REQ-P1-2 / REQ-P0-3，复用已有四级降级链）

### 场景 6：点击图片进入左右滚动播放

- **前置**：用户在 ImageGalleryActivity 垂直浏览图片流
- **流程**：点击任意图片 → Activity 内切换为 ViewPager2 + PhotoView 横向播放模式 → 左右滑动切换图片 → 双击/双指缩放查看细节 → 相邻图片已被智能预加载
- **预期**：不再跳转 ImageDetailActivity；切换无白屏；极端尺寸图片按最大适配尺寸展示（对应 REQ-P0-9 / REQ-P1-7 / REQ-P1-8）

---

## §6 关联文档

| 文档 | 关系 |
|------|------|
| [V2 深度架构分析报告](../player-deep-analysis-20260726-v2.md) | 本 spec 的直接依据（短板清单 + Phase 策略 + 验收标准来源） |
| [行业成熟方案查证报告](../../temp-analysis/industry-mature-solutions-verification-report-20260726.md) | 49 个权威来源验证依据 |
| [exoplayer-resilience](../exoplayer-resilience/) | 前置 spec（sniffVideoType + 降级链架构，本 spec 在其上演进） |
| [player-review-and-optimization](../player-review-and-optimization/) | 关联 spec（R4 增强计划） |
| [video-playback-failure-fix-20260726](../video-playback-failure-fix-20260726/) | 关联 spec（27 个 Bug 修复，与本 spec 日志问题部分互补） |
| [image-player-vertical-canvas-optimization](../image-player-vertical-canvas-optimization/) | 前置 spec（图片垂直画布架构，Phase 3 在其上补齐） |
