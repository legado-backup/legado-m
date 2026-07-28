# 任务清单

> 基于V2深度架构分析报告（player-deep-analysis-20260726-v2.md），按5个Phase组织，全部P0/P1任务都有成熟方案参考支撑。
>
> **任务覆盖核对**：9个P0（P0-1/2/3/9/10/11/12/13/14）+ 8个P1（P1-4/5/6/15/16/17/18/19）+ 4个P2（P2-8/20/21/22），全部纳入，无遗漏。

## Phase 1: 可观测性+错误反馈闭环（P0）

- [x] 1.1 补充播放成功埋点（STATE_READY/onRenderedFirstFrame）【P0-9】
  - 成熟方案参考：ExoPlayer官方指南
  - 验收标准：logcat可统计播放成功率
  - 文件变更：Exo2MediaPlayer.kt
- [x] 1.2 重试耗尽后发送videoPlayError事件+UI错误提示【P0-1】
  - 成熟方案参考：hls.js错误恢复机制（startLoad/recoverMediaError）
  - 验收标准：所有失败场景有UI提示
  - 文件变更：Exo2MediaPlayer.kt, VideoPlayerActivity.kt
- [x] 1.3 sniffVideoType双回调竞态修复（AtomicBoolean）【P0-2】
  - 成熟方案参考：Kotlin协程最佳实践（AtomicBoolean/Mutex）
  - 验收标准：无双回调
  - 文件变更：ExoPlayerHelper.kt
- [x] 1.4 SniffingMime日志输出到logcat
  - 成熟方案参考：-（可观测性基础设施）
  - 验收标准：ai_test可用logcat分析嗅探日志
  - 文件变更：ExoPlayerHelper.kt

## Phase 2: 视频播放器核心能力补齐（P0）

- [x] 2.1 BandwidthMeter动态调整缓冲参数【P0-10】
  - 成熟方案参考：developer.android.com官方指南
  - 验收标准：不同网络环境缓冲策略合理
  - 文件变更：ExoPlayerHelper.kt 或 Exo2MediaPlayer.kt
- [x] 2.2 首帧预加载（I-frame）【P0-11】
  - 成熟方案参考：快手官方博客（首帧命中率90%+）
  - 验收标准：首帧命中率≥80%
  - 文件变更：新增 FirstFramePreloader.kt
- [x] 2.3 下一个视频预加载（256KB，WiFi 3个/4G 1个）【P0-12】
  - 成熟方案参考：抖音官方博客
  - 验收标准：滑动流畅度提升
  - 文件变更：新增 VideoPreloader.kt
- [x] 2.4 指数退避重试策略（1s/2s/4s/8s/16s）【P1-17】
  - 成熟方案参考：hls.js源码config.ts
  - 验收标准：避免固定间隔重试雪崩
  - 文件变更：Exo2MediaPlayer.kt
- [x] 2.5 显式指定MediaSource类型【P1-15】
  - 成熟方案参考：ExoPlayer GitHub issue #1343
  - 验收标准：所有MediaSource显式指定
  - 文件变更：ExoPlayerHelper.kt

## Phase 3: 图片播放器核心诉求补齐（P0）

- [ ] 3.1 点击图片后切换为左右滚动播放（ViewPager2+PhotoView）【P0-14】
  - 成熟方案参考：BigImageViewer
  - 验收标准：ImageGalleryActivity内实现横向播放
  - 文件变更：ImageGalleryActivity.kt, 新增 ImageDetailViewPagerAdapter.kt
- [ ] 3.2 图片金字塔（多分辨率瓦片，SSIV）【P0-13】
  - 成熟方案参考：微信读书团队博客+SSIV
  - 验收标准：长图不OOM
  - 文件变更：新增 ImagePyramidLoader.kt, ImageCanvasAdapter.kt
- [ ] 3.3 图片适配性最大尺寸展示【P1-18】
  - 成熟方案参考：自定义GlideModule
  - 验收标准：所有图片最大尺寸展示
  - 文件变更：ImageCanvasAdapter.kt
- [ ] 3.4 图片预加载时机智能判断（LayoutManager.onScrolled）【P1-19】
  - 成熟方案参考：RecyclerView最佳实践
  - 验收标准：上下滑动切换不卡顿
  - 文件变更：ImageGalleryActivity.kt, ImageCanvasAdapter.kt
- [ ] 3.5 渐进式加载（JPEG/WebP）【P1-16】
  - 成熟方案参考：微信读书团队博客
  - 验收标准：先模糊后清晰
  - 文件变更：ImageCanvasAdapter.kt

## Phase 4: 网络层韧性（P1）

- [x] 4.1 DoH（绕过DNS污染，OkHttp Dns接口）【P0-3 + P1-5】
  - 成熟方案参考：Square官方博客 + GitHub okhttp-dnsoverhttps
  - 验收标准：站点A图片CDN可访问
  - 文件变更：新增 DohDns.kt, OkHttpClient配置
- [x] 4.2 302重定向缓存（自定义Interceptor）【P1-6】
  - 成熟方案参考：OkHttp最佳实践
  - 验收标准：同一URL不重复302
  - 文件变更：新增 RedirectCacheInterceptor.kt
- [x] 4.3 Cronet降级阈值宽限期+恢复探测【P2-8】
  - 成熟方案参考：-（日志实证问题修复）
  - 验收标准：启动300ms内不累计
  - 文件变更：CronetHelper.kt
- [x] 4.4 RSS正文解析视频型订阅源降级【P1-4】
  - 成熟方案参考：-（日志实证问题修复）
  - 验收标准：视频型订阅源正文为空不抛异常
  - 文件变更：RssParser.kt 或相关文件

## Phase 5: 架构优化（P2）

- [x] 5.1 播放器实例池（3个实例）【P2-20】
  - 成熟方案参考：GSYVideoPlayer（38k+ stars）
  - 验收标准：滑动不卡顿，内存稳定
  - 文件变更：新增 PlayerInstancePool.kt
- [x] 5.2 修正"五级识别链"术语为"三级识别链+URL后缀兜底"【P2-21】
  - 成熟方案参考：WHATWG MIMESNIFF规范
  - 验收标准：文档术语准确
  - 文件变更：所有设计文档
- [x] 5.3 L3 URL后缀检测降级为Range失败时兜底【P2-22】
  - 成熟方案参考：WHATWG MIMESNIFF规范
  - 验收标准：符合规范
  - 文件变更：ExoPlayerHelper.kt

## 验证

- [x] 6.1 编译验证（assembleDebug）
- [ ] 6.2 ai_test自动化验证（播放成功率/首帧命中率/图片加载成功率）
- [ ] 6.3 真机测试验证（测试包io.legado.miss.app.debug）
- [ ] 6.4 0崩溃/0 ANR/0 OOM验证
- [x] 6.5 文档同步（updateLog.md + INDEX.md）

## Phase 7: 交付前终审修复（2026-07-27，基于三路并行代码审查报告）

- [x] 7.1 图片画布 Glide 销毁守卫（ImageCanvasAdapter.kt）
  - 问题：9 处 Glide.with 中 6 条异步路径（loadImage/showSsivImage/loadIntoPhotoView/2×postDelayed 重试/onRecycled）在 Activity 销毁后触发会抛 IllegalArgumentException（crash-2026-07-26 同类铁证）
  - 修复：新增 isGlideUsable() 守卫统一兜底
- [x] 7.2 重定向缓存兼容（RedirectCacheInterceptor.kt）
  - 问题：仅处理 301/302；Location 相对路径缓存后命中时 url() 抛 IllegalArgumentException
  - 修复：补 307/308 状态码 + resolve 相对 Location 为绝对 URL（缓存 key 已含 query 验证无需改）
- [x] 7.3 Cronet 探测节奏缺口（CronetInterceptor.kt）
  - 问题：非协议错误的探测失败不刷新降级计时，降级态下每个请求都立即重探测白等一次
  - 修复：任何探测失败均刷新 degradedTimeMs（主体 try-catch 已覆盖 lazy 引擎访问，无需重构避免 chain.proceed 二次调用风险）
- [x] 7.4 DoH 稳定性重构（DohDns.kt）
  - 问题：全局接线（HttpHelper builder.dns）但无缓存/单服务器/10s 超时，全 App 每个新连接都付出 DoH 往返延迟，单点故障直接退化
  - 修复：3 服务器轮询（3s 快速失败）+ 成功结果 5 分钟缓存（上限 200）+ 连续 3 次全失败熔断 5 分钟（对齐 Cronet 降级模式）+ lazy 初始化兜底 + 日志域名脱敏
- [x] 7.5 终审后编译验证 + 重新打包（legado_miss_app_3.26.072709.apk）
