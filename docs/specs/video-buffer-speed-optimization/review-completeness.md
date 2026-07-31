# video-buffer-speed-optimization 设计文档完整性审查报告

> **审查日期**：2026-07-28
> **审查对象**：README.md / spec.md / design.md / tasks.md（共 1545 行）
> **审查方法**：WebSearch 核实业界方案 + 源码交叉验证 + 边界文档对比
> **审查维度**：遗漏点 / 待优化点 / 成熟方案结合程度 / 效果可达性 / 用户角度 / 技术架构角度 / 边界划分

---

## 一、遗漏点清单

> 经 WebSearch 核实业界 7 大类成熟方案 + 源码交叉验证，识别出 11 项遗漏点。

| # | 遗漏的优化方案 | 来源 | 重要性 | 建议处理 |
|---|--------------|------|-------|---------|
| 1 | **Cronet 作为视频流 HttpDataSource 替代 OkHttp** | Media3 官方文档"Network stacks"明确推荐 Cronet 用于流媒体，YouTube 在用；项目已有 `CronetHelper.kt` 启用 QUIC/HTTP-3/HTTP-2/Brotli/AsyncDNS，但仅用于书源请求 | 🔴 高 | **新增 P1 评估项**：spec.md Alternatives 方案7 仅以"APK 体积大 1.5MB"为由否决过于简单，应评估 Cronet via Google Play Services 方案（不增加 APK 体积，与项目已有 Cronet 共享 engine）。Cronet 对弱网（QUIC 0-RTT）收益显著，可能比 OkHttp 任何调参都有效 |
| 2 | **DohDns 用于视频流 OkHttpClient** | 项目已有 `DohDns.kt`（DoH，DNS over HTTPS，防劫持+降时延），但仅注入 HttpHelper 的书源 OkHttpClient，视频流 OkHttpClient 未注入 | 🔴 高 | **新增 P0 项**：视频流 OkHttpClient 通过 `.dns(DohDns)` 注入，复用已有实现。视频流 DNS 污染/劫持会导致分片加载失败触发降级链，与缓冲速度直接相关 |
| 3 | **HTTP 预热（Warmup）完整方案** | 业界方案：DNS 预解析 + TCP 预连接 + TLS 预握手。项目 `ExoPlayerHelper.preResolveDns` 仅做 DNS 预解析（InetAddress.getAllByName），未做 TCP/TLS 预连接 | 🟡 中 | **新增 P1 项**：在 `preResolveDns` 基础上扩展，对好网档位预热前 N 个分片的 TCP+TLS 连接（OkHttp `ConnectionPool` 已支持连接复用，预热后连接进入池待用） |
| 4 | **SurfaceView 替代 TextureView** | Media3 官方耗电量文档明确："TextureView 在某些设备上功耗增加 30%，应尽可能优先使用 SurfaceView"；源码确认 `VideoFragment.kt` 使用 GSY 的 `mTextureViewContainer`（TextureView） | 🟡 中 | **新增 P1 评估项**：评估切换 SurfaceView 的兼容性（GSY 框架支持，但需确认动画/弹幕叠加需求）。对长视频播放场景，SurfaceView 双缓冲+硬件 Overlay 可降低解码功耗与丢帧率 |
| 5 | **HttpEngine (API 34+) 评估** | Media3 官方文档：API 34+ 推荐 HttpEngine 作为默认网络栈，内部用 Cronet，支持 HTTP/2/HTTP-3 over QUIC | 🟢 低 | **新增 P2 评估项**：项目 minSdk=23，但可在 API 34+ 设备优先使用 HttpEngine，低版本降级 OkHttp。实现复杂度高，优先级低 |
| 6 | **多 CDN 域名容灾** | 业界方案：主 CDN 失败后切换备用 CDN 域名。视频流分片加载失败时仅触发降级链（HLS→DASH→Progressive），未尝试同格式备用 CDN | 🟢 低 | **不采纳**：项目是聚合播放器，CDN 由源站决定，客户端无法控制多 CDN，此方案不适用 |
| 7 | **Cache 温度策略（热/温/冷）** | 业界方案：热缓存（内存，首帧）+ 温缓存（磁盘，当前视频）+ 冷缓存（磁盘 LRU，历史） | 🟢 低 | **已部分覆盖**：design.md 1.4 已评估"内存级 LruCache 叠加"（P2），与本方案本质一致。建议文档明确"温度"分层概念 |
| 8 | **自定义 ABR 算法（LSTM+TFLite）** | 业界案例：AI ABR 卡顿率从 8.2 降到 2.1 次/分，带宽利用率 63%→89% | 🟢 低 | **不采纳**：项目已声明 P3 远期方向（README §十）。本 spec 聚焦 P0/P1，AI ABR 复杂度过高，决策合理 |
| 9 | **关键帧对齐（Keyframe Alignment）** | 业界方案：HLS 分片边界对齐关键帧，避免解码器等待关键帧 | 🟢 低 | **不采纳**：关键帧对齐由服务端编码决定，客户端无法控制，此方案不适用 |
| 10 | **音视频同步优化（AV Sync）** | 业界方案：调整音频渲染延迟对齐视频帧 | 🟢 低 | **不采纳**：ExoPlayer 默认 AV Sync 已优化良好，无明确痛点证据，不引入 |
| 11 | **Brotli 压缩用于 m3u8/mpd 清单** | 项目 `CronetHelper.kt` 已启用 Brotli（L45），但视频流 OkHttp 未启用；Brotli 对文本清单（m3u8/mpd）压缩率优于 gzip | 🟢 低 | **已部分覆盖**：视频分片本身已压缩（H.264/H.265），Brotli 无收益；m3u8/mpd 清单体积小（<100KB），Brotli 收益有限。低优先级 |

**遗漏点小计**：11 项，其中 🔴 高优 2 项（Cronet 集成、DohDns 复用）、🟡 中优 2 项（HTTP 预热、SurfaceView）、🟢 低优 7 项。

---

## 二、待优化点清单

> 基于四文档已有方案，找出可进一步优化的地方。

| # | 待优化点 | 当前方案 | 建议优化 | 收益评估 |
|---|---------|---------|---------|---------|
| 1 | **LoadControl 分档参数激进程度不一致** | spec.md R1.3：WEAK 3s/20s, MEDIUM 5s/60s, GOOD 5s/180s；design.md 1.1.3：GOOD maxBuffer=120s | **统一两文档参数**：spec.md R1.3 与 design.md 1.1.3 不一致（GOOD maxBuffer 180s vs 120s），实施时需确认。建议 GOOD 档 8s/180s（更激进），与 R3 video-prebuffer-enhancement 的 maxBuffer=120s 协调 | 消除文档矛盾，避免实施歧义 |
| 2 | **OkHttp connectTimeout 过激进** | spec.md R8.1：connectTimeout(1s)；tasks.md §3.2：connectTimeout=10s | **统一为 5s**：1s 在跨国 CDN/弱网下会误杀正常慢请求（design.md Drawbacks 已承认），10s 过保守。建议 5s 平衡，并保留用户可调 `videoHttpTimeoutSec` | 减少误杀，保持激进 |
| 3 | **OkHttp readTimeout 过激进** | spec.md R8.2：readTimeout(500ms) | **调整为 3s**：500ms 在慢速 CDN 下会频繁超时触发重试，反而加剧卡顿。HLS 分片平均 2-10MB，500ms 内下载不完属正常 | 避免重试风暴 |
| 4 | **OkHttp 连接池参数** | 当前 10 连接, 5min keep-alive | **调整为 5 连接, 5min**：视频流是单长连接（HLS 主清单+少量分片并发），10 连接过多占用内存。配合 Dispatcher maxRequestsPerHost=16，实际并发由 Dispatcher 控制 | 内存节省 |
| 5 | **HLS 超时配置矛盾** | spec.md R8：connectTimeout 1s, readTimeout 500ms；tasks.md §3.2：connectTimeout 10s, readTimeout 15s | **统一为 5s/3s**：两文档参数 10 倍差异，需统一。HLS 分片加载本质是 HTTP 请求，应与 OkHttp 全局超时一致 | 消除文档矛盾 |
| 6 | **setAdaptiveSelectionMarginMs(1500) 偏保守** | spec.md R5.2：1500ms | **调整为 2500ms**：1.5s 缓冲余量在弱网下仍可能 rebuffer，2.5s 更稳妥。配合 setMinDurationForQualityIncreaseMs(20000) 避免抖动 | 弱网卡顿降低 |
| 7 | **AnalyticsListener 采样频率** | spec.md R7.8：每分钟输出汇总 | **增加事件驱动告警**：除每分钟汇总外，TTFB>800ms / 单次 rebuffer>2s 时立即输出 WARN（不等汇总），便于实时定位 | 问题定位时效性提升 |
| 8 | **bufferForPlayback 降得太激进** | design.md AD-10：GOOD 档 500ms | **调整为 800ms**：500ms 在弱网下首帧后立即 rebuffer 概率高（design.md 已承认），800ms 平衡首帧速度与稳定性。WEAK 档保留 500ms 不变 | 二次卡顿降低 |
| 9 | **CacheDataSink fragment size 调整** | design.md 1.4.3：2MB；当前 5MB（DEFAULT_FRAGMENT_SIZE） | **评估 1MB**：HLS 小分片（如 10s ts 约 2-5MB）2MB 仍可能浪费，1MB 更细粒度。但写入次数增加 IO 开销，需实测 | 待真机验证 |
| 10 | **HTTP/2 分域策略实现复杂度** | design.md AD-02：自定义 Interceptor 捕获 StreamResetException 后降级 | **简化为白名单**：维护已知问题 CDN 白名单（HTTP_1_1），其他默认 HTTP_2。减少首次 StreamResetException 的 200ms 开销 | 实现简化 |
| 11 | **CacheControl.maxAge 移除决策** | design.md AD-11：移除 | **保留但调整**：maxAge=1天 对直播流有害（design.md 已指出），但对点播 VOD 无害。建议按是否直播动态设置：VOD maxAge=1天, LIVE maxAge=0 | 直播兼容性 |
| 12 | **bandwidthMeter 共享注入** | design.md AD-12：注入 DefaultTrackSelector | **补充归池处理**：PlayerInstancePool 归池时 bandwidthMeter 不重置（AD-12 已决策），但需确认跨播放器实例的带宽估计污染风险 | 决策已合理，需验证 |

**待优化点小计**：12 项，其中文档矛盾 3 项（高优）、参数激进度调整 5 项（中优）、实现细节优化 4 项（低优）。

---

## 三、成熟方案结合程度评估

> 基于 WebSearch 核实的业界成熟方案，评估四文档结合程度。

| 成熟方案 | 是否结合 | 结合程度 | 建议补充 |
|---------|---------|---------|---------|
| **Media3 官方 DefaultPreloadManager** | ❌ 未结合 | 无 | 仅 video-prebuffer-enhancement 提及 P2 远期搁置。本 spec 聚焦当前视频，DefaultPreloadManager 主要用于下一集预加载，本 spec 不结合合理。但建议在附录补充"为何不结合"说明 |
| **ExoPlayer 官方 Buffering 策略指南** | ✅ 已结合 | 高 | design.md 附录 A 已对照，setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds(true) 直接采纳官方建议 |
| **B 站/YouTube 激进缓冲策略** | 🟡 部分 | 中 | tasks.md 附录 A 提及"B站 SD 优先 + 大缓冲 + 快速降级"，但未深度对标。建议补充 B 站具体参数（如 maxBuffer 时长、ABR 切换阈值）的对照分析 |
| **抖音/快手短视频预加载策略** | ❌ 未结合 | 无 | 短视频预加载属 video-prebuffer-enhancement 范畴，本 spec 不结合合理 |
| **Google ExoPlayer 官方案例** | ✅ 已结合 | 高 | design.md 引用 ExoPlayer 官方 benchmark（chunkless preparation 首帧降 30%+） |
| **CSDN 性能调优案例** | 🟡 部分 | 中 | tasks.md 附录 A 提及"ExoPlayer Buffering 策略（社区）"，但未具体引用 CSDN 案例的量化数据（如内存降 40%、首帧降 50%）。建议补充量化基准 |
| **Media3 官方 Cronet 网络栈指南** | ❌ 未结合 | 无 | **重大遗漏**：官方明确推荐 Cronet 用于流媒体，spec.md Alternatives 方案7 仅以 APK 体积为由否决，未评估 Cronet via Google Play Services（0 体积增量） |
| **OkHttp 官方 EventListener 指南** | ✅ 已结合 | 高 | design.md 1.3 + spec.md R3 完整采纳 |
| **OkHttp 官方 Dispatcher 文档** | ✅ 已结合 | 高 | spec.md R9 完整采纳 |
| **Android 官方 SurfaceView/TextureView 选型** | ❌ 未结合 | 无 | **遗漏**：官方明确 TextureView 功耗+30%，本 spec 未评估 SurfaceView 切换 |
| **Media3 官方耗电量指南** | ❌ 未结合 | 无 | 官方建议优先 SurfaceView + 隧道模式（TV），本 spec 未涉及 |
| **HttpDNS/DoH 防劫持方案** | ❌ 未结合 | 无 | **遗漏**：项目已有 DohDns 但未用于视频流 |

**成熟方案结合程度总评**：**中等**。ExoPlayer/OkHttp 官方指南结合程度高，但 Cronet/SurfaceView/HttpDNS 三项官方明确推荐的方案未结合，存在显著提升空间。

---

## 四、效果可达性评估

> 评估四文档方案实施后是否能达到明显效果。

| 指标 | 文档目标 | 现实评估 | 风险 |
|------|---------|---------|------|
| **TTFB < 500ms** | spec.md R7 + tasks.md §0.3 | 🟡 中等可达 | 好网+本地缓存命中可达成；弱网/冷启动难以达成。500ms 是 ExoPlayer 官方低延迟场景建议值，对点播偏激进。建议分档：好网<500ms, 中网<1s, 弱网<2s |
| **缓冲中断 < 1次/小时** | spec.md R7 + tasks.md §0.3 | 🟢 高可达 | setTargetBufferBytes(-1) + maxBuffer=120s 解除大小阈值截断后，好网下 rebuffer 概率显著降低。1次/小时目标现实 |
| **丢帧率 < 0.1%** | spec.md R7 + tasks.md §0.3 | 🟡 中等可达 | forceEnableMediaCodecAsynchronousQueueing 可降低丢帧，但 0.1% 是高标准（业界一般 0.5%-1%）。中高端机可达成，低端机难。建议分档：GOOD<0.1%, MID<0.5% |
| **带宽利用率 > 90%** | spec.md R7 + tasks.md §0.3 | 🔴 难可达 | 带宽利用率受 CDN 质量、TCP 拥塞控制、HTTP/1.1 队头阻塞等多因素影响，90% 是极高目标（YouTube 业界约 80-85%）。建议调整为 >80% |
| **HLS 首帧降 30%+** | design.md 1.2.3 | 🟢 高可达 | setAllowChunklessPreparation 是官方 benchmark 验证的零成本收益，30%+ 数据可信 |
| **maxBuffer 真正生效** | design.md 1.1.3 | 🟢 高可达 | setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds(true) 直接修复"50MB 截断"根因，效果确定 |
| **缓存故障不中断播放** | design.md 1.4.3 | 🟢 高可达 | FLAG_IGNORE_CACHE_ON_ERROR 是标准容错，效果确定 |
| **弱网码率自动降级** | spec.md R5 | 🟢 高可达 | setMaxVideoSizeSd + setAdaptiveSelectionMarginMs 标准方案，效果确定 |
| **网络瓶颈可观测** | design.md 1.3 + 1.7 | 🟢 高可达 | OkHttp EventListener + AnalyticsListener 双层埋点，效果确定 |

**效果可达性总评**：**中等偏高**。核心 P0 项（setTargetBufferBytes + chunkless preparation + FLAG_IGNORE_CACHE_ON_ERROR）效果确定，能直接修复"用户感觉没效果"的根因。但量化指标（TTFB<500ms / 带宽>90%）偏激进，建议分档调整。

---

## 五、用户角度评估

- **用户感知度**：🟢 **高**
  - setTargetBufferBytes(-1) 修复"120s 缓冲变 40s"问题 → 用户直接感知"缓冲条更长了"
  - setAllowChunklessPreparation 降低 HLS 首帧 30%+ → 用户直接感知"秒开"
  - FLAG_IGNORE_CACHE_ON_ERROR 消除"偶尔卡死" → 用户直接感知"播放更稳定"
  - setMaxVideoSizeSd 弱网降级 → 用户感知"不卡了但模糊"（可接受）

- **配置复杂度**：🟡 **中**
  - spec.md R13 + tasks.md §9 提供三档（省流/平衡/激进）+ 4 个高级参数（videoBufferTargetBytes/videoHttpTimeoutSec/videoAdaptiveBitrateEnabled/videoPerformanceMonitorEnabled）
  - 4 个高级参数对普通用户过于复杂（如"targetBufferBytes=-1 是什么意思"）
  - design.md AD-08 又新增 videoMaxResolution（720p/1080p/1440p/4K）
  - design.md 又新增 videoHttpProtocol（auto/h2/h1）

- **建议简化方案**：
  1. **主入口仅三档**：省流/平衡/激进（已有），默认"激进"（中高端机）
  2. **高级参数折叠**：4-6 个高级参数放入"高级设置"折叠区，默认不展开
  3. **参数语义化**：videoBufferTargetBytes → "缓冲大小限制"（无限制/100MB/500MB/1GB）
  4. **移除冗余**：videoHttpProtocol 与 videoHttpTimeoutSec 可合并为"网络策略"（自动/极速/稳定）
  5. **A/B 测试**：上线后通过 AnalyticsListener 数据验证哪档最受欢迎，默认值动态调整

---

## 六、技术架构角度评估

- **架构复杂度**：🔴 **高**
  - 7 层联合优化（LoadControl + HLS + OkHttp + CacheDataSource + ABR + Decoder + AnalyticsListener）
  - 新增 4 个文件（VideoAnalyticsListener / VideoEventListener / HttpProtocolInterceptor / DeviceCodecBlacklist）
  - 修改 4 个文件（ExoPlayerHelper / Exo2MediaPlayer / PlayerInstancePool / VideoPlay）
  - 12 个 ADR 决策（AD-01 到 AD-12）

- **各层冲突**：🟡 **有（已识别）**
  1. **LoadControl 不热切换 vs AdaptiveLoadControl 热切换**：spec.md R10 要求 AdaptiveLoadControl 运行时热切换，但 design.md AD-01 + 附录 B 明确放弃热切换（路径 A）。**文档内部矛盾**，需统一
  2. **setMaxVideoSizeSd vs setMaxVideoSize(1920,1080)**：spec.md R5.1 用 setMaxVideoSizeSd()（限制 720p），design.md AD-08 用 setMaxVideoSize(1920,1080)（限制 1080p）。**两文档参数不一致**
  3. **HTTP/2 策略矛盾**：spec.md Alternatives 方案2 保留 HTTP_1_1 降级开关，design.md AD-02 改为分域策略。**方案描述不一致**
  4. **AsyncLoadControl 命名混乱**：spec.md R10 称 AdaptiveLoadControl，design.md 附录 B 称 Dynamic LoadControl，需统一术语

- **最小改动最大收益方案**：
  - **P0 必做（4 项，2-3 行代码）**：setTargetBufferBytes(-1) + setPrioritizeTimeOverSizeThresholds(true) + setAllowChunklessPreparation + FLAG_IGNORE_CACHE_ON_ERROR
  - **P0 监控必做（1 项，新增 1 文件）**：AnalyticsListener（无监控即无优化）
  - **P1 高收益（3 项）**：forceEnableMediaCodecAsynchronousQueueing + setMaxVideoSize + DohDns 注入（遗漏点 2）
  - **P1 中收益（2 项）**：OkHttp EventListener + Dispatcher 并发
  - **P2 评估**：分域 HTTP/2 + 自定义 ChunkSource + 多级缓存

- **建议优先级调整**：
  1. 将"遗漏点 2：DohDns 注入视频流"提升为 P0（零成本复用已有实现）
  2. 将"遗漏点 1：Cronet 评估"提升为 P1（可能比 OkHttp 调参收益大）
  3. 将"待优化点 1-3-5：文档参数统一"列为 P0 前置任务（实施前必须消除矛盾）
  4. 将"待优化点 10：HTTP/2 分域策略简化"列为 P1（降低实现复杂度）

- **向后兼容性**：✅ **良好**
  - 所有优化均基于 Media3 1.10.1 + OkHttp 现有 API
  - 用户可调档位兜底
  - DeviceCodecBlacklist + WEAK 档降级保护

- **回归测试**：🟡 **中**
  - tasks.md §10 已列出真机测试方案（HLS/MP4/DASH 各 3 个，5 分钟/个）
  - 但未覆盖：缓存损坏场景、网络切换场景、低端机异步解码崩溃场景、HLS 5xx 重试场景（spec.md Scenario 5-7 有场景描述但 tasks.md 未对应测试用例）
  - 建议补充：spec.md 10 个 Scenario 与 tasks.md §10 测试用例的映射表

---

## 七、与 video-prebuffer-enhancement 边界划分评估

- **边界清晰度**：🟢 **高**
  - README §1.2 + design.md §七 均明确划分：本 spec = 当前视频缓冲速度，video-prebuffer-enhancement = 下一集预加载
  - 作用阶段、核心组件、用户感知均有对照表

- **重复内容清单**：

| # | 重复项 | 本 spec 描述 | prebuffer spec 描述 | 冲突情况 |
|---|--------|-------------|---------------------|---------|
| 1 | LoadControl 不热切换 | design.md AD-01 沿用 prebuffer AD-09 路径 A | prebuffer AD-09 决策路径 A | ✅ 一致（本 spec 显式声明沿用） |
| 2 | setAllowChunklessPreparation | design.md 1.2 列为 P0 | prebuffer §8.5 列为 P1 待实施 | 🟡 **冲突**：prebuffer 已声明 P1 待实施，本 spec 也列为 P0。需确认由哪个 spec 实施 |
| 3 | 设备档位检测（HIGH/MID） | design.md 隐式引用 DeviceTier | prebuffer §8.2 已实施 DeviceInfoHelper | ✅ 协调（本 spec 复用） |
| 4 | maxBuffer 参数 | spec.md R1.3：GOOD 180s | prebuffer §1.2：HIGH+GOOD 120s | 🔴 **冲突**：参数不一致，需统一 |
| 5 | cacheKey 策略 | design.md 未涉及 | prebuffer §8.2 已统一 cacheKey | ✅ 协调（本 spec 不涉及） |
| 6 | AppLog release 日志 | design.md AD-04 引用 prebuffer AD-16 | prebuffer §8.2 已修复 | ✅ 协调（本 spec 复用） |
| 7 | 用户可配置参数 | spec.md R13 + tasks.md §9 | prebuffer §8.2 已实施 4 个参数 | 🟡 **部分重叠**：videoMaxBufferSec 两 spec 都涉及，需确认是否同一参数 |
| 8 | SimpleCache 共享 | design.md 1.4 隐式共享 | prebuffer §8.2 已扩展容量到 2048MB | ✅ 协调（本 spec 复用） |
| 9 | OkHttp 配置 | design.md 1.3 独立优化 | prebuffer 未涉及 | ✅ 不重叠 |
| 10 | AnalyticsListener | design.md 1.7 新增 7 类指标 | prebuffer §8.6 仅命中率计数器 | 🟡 **部分重叠**：两 spec 都有 AnalyticsListener，需确认是同一实例还是两个独立实例 |

- **建议处理**：
  1. **统一 maxBuffer 参数**：本 spec GOOD 档 180s vs prebuffer HIGH+GOOD 120s，建议统一为 120s（与 prebuffer 已实施一致，避免回归）
  2. **明确 setAllowChunklessPreparation 实施归属**：建议归本 spec P0 实施（本 spec 聚焦当前视频首帧，更契合）
  3. **明确 AnalyticsListener 实例归属**：建议本 spec 的 VideoAnalyticsListener 与 prebuffer 的命中率计数器合并为单一实例（避免双实例性能开销）
  4. **补充边界声明**：在两 spec 的 README 中互相引用，明确"对方已实施项本 spec 不重复实施"

---

## 八、总体评估

### 8.1 量化总结

| 维度 | 数量 | 等级 |
|------|------|------|
| 遗漏点数量 | 11 项（高优 2 / 中优 2 / 低优 7） | 中等 |
| 待优化点数量 | 12 项（高优 3 文档矛盾 / 中优 5 参数 / 低优 4 实现） | 中等 |
| 成熟方案结合程度 | 12 项成熟方案，已结合 5 项，部分结合 2 项，未结合 5 项 | **中等** |
| 效果可达性 | 9 项指标，高可达 6 项，中等 2 项，难达 1 项 | **中等偏高** |
| 文档内部矛盾 | 4 处（LoadControl 热切换 / setMaxVideoSize / HTTP/2 策略 / 命名术语） | 需修复 |
| 与 prebuffer 边界冲突 | 2 处（maxBuffer 参数 / chunkless preparation 归属） | 需协调 |

### 8.2 核心结论

1. **方案整体可行**：7 层联合优化的技术方向正确，P0 项（setTargetBufferBytes + chunkless preparation + FLAG_IGNORE_CACHE_ON_ERROR + AnalyticsListener）能直接修复"用户感觉没效果"的根因，效果确定。

2. **存在重大遗漏**：**Cronet 集成**与 **DohDns 复用**两项高优遗漏点可能比文档中任何 OkHttp 调参收益都大。Cronet 的 QUIC/HTTP-3 对弱网优化显著（YouTube 在用），DohDns 已实现只需 1 行代码注入视频流 OkHttpClient。建议立即补充评估。

3. **文档内部矛盾必须修复**：4 处文档矛盾（LoadControl 热切换 / setMaxVideoSize / HTTP/2 策略 / 命名术语）会导致实施歧义，必须在实施前统一。

4. **量化指标偏激进**：TTFB<500ms / 带宽>90% 两项目标过高，建议分档调整（好网/中网/弱网不同阈值）。

5. **配置复杂度需简化**：4-6 个高级参数对普通用户过于复杂，建议主入口仅三档 + 高级设置折叠。

### 8.3 修订建议

**是否需要重大修订**：🟡 **是（中度修订）**

**修订优先级**：
1. 🔴 P0（实施前必须）：修复 4 处文档内部矛盾 + 统一与 prebuffer 的 maxBuffer 参数 + 明确 chunkless preparation 实施归属
2. 🔴 P0（实施前必须）：补充 DohDns 注入视频流 OkHttpClient（1 行代码，零成本）
3. 🟡 P1（实施前评估）：补充 Cronet 作为视频流 HttpDataSource 的评估章节
4. 🟡 P1（实施前评估）：补充 SurfaceView vs TextureView 评估章节
5. 🟢 P2（可选）：简化用户配置参数 + 补充 Scenario 与测试用例映射表

**修订后预期**：遗漏点从 11 项降至 7 项（移除 4 项不适用），待优化点从 12 项降至 8 项（修复 4 处矛盾），成熟方案结合程度从"中等"提升至"高"。

---

## 附录：审查依据

### A.1 WebSearch 核实来源（节选）

- Media3 官方 Network stacks 文档（Cronet/HttpEngine/OkHttp 对比）
- Media3 官方 DefaultPreloadManager 文档
- Media3 官方耗电量文档（SurfaceView vs TextureView）
- Media3 官方直播文档（LiveConfiguration.targetOffsetMs）
- ExoPlayer 官方 Buffering 策略指南
- OkHttp 官方 EventListener / Dispatcher 文档
- 业界案例：CSDN ExoPlayer 性能优化实战（内存降 40%、首帧降 50%）
- 业界案例：AI ABR 自适应码率（卡顿率 8.2→2.1 次/分）
- 业界案例：Android 网络优化（HTTPDNS / 连接复用 / HTTP/2）

### A.2 源码交叉验证

- `CronetHelper.kt`：已启用 QUIC/HTTP-3/HTTP-2/Brotli/AsyncDNS（L42-L45），仅用于书源请求
- `DohDns.kt`：已实现 DoH（DNS over HTTPS），仅注入 HttpHelper 的 OkHttpClient
- `ExoPlayerHelper.kt#preResolveDns`（L238）：仅 DNS 预解析，未做 TCP/TLS 预连接
- `VideoFragment.kt`：使用 GSY 的 mTextureViewContainer（TextureView）
- `ExoPlayerHelper.kt#createLoadControlByTier`：已分档但未启用 setTargetBufferBytes(-1)
- `ExoPlayerHelper.kt#createMediaSource` HLS 分支：未启用 setAllowChunklessPreparation（design.md 已指出）

### A.3 边界文档对比

- `video-prebuffer-enhancement/README.md`：已读，P0 已实施，P1 待实施
- 边界划分清晰，但 maxBuffer 参数与 chunkless preparation 归属存在冲突
