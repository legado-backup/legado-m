# spec.md - 004 真机测试问题功能规范

> **根因修正说明**：初审基于错误时间戳分析（spec.md v1 中"09:32:55 Activity 重建"实为日志解析错误）。
> 重新逐行分析 004 日志 12219 行后，发现真实根因如下，已全面重写。

## 一、问题清单

### V-004-P0-1: 首帧渲染延迟 4808ms（用户感知"第一个视频失败"）

**现象**：用户反馈"一个订阅源进去第一个视频总是失败的，下拉或切换另外一个就好了"

**日志证据**（004 日志 19:16:58 - 19:17:07，唯一一次成功播放的会话）：
- 19:16:58.199 VideoPlayerActivity onCreate（用户点击视频）
- 19:16:57.695-697 DoH server#1/#2/#3 全部失败 UnknownHostException
- 19:17:00.898 prepareAsyncInternal callCount=1（延迟 2.7s 才开始准备——等待 initSource）
- 19:17:00.956 sniff job started
- 19:17:04.081 sniffVideoType success contentType=2 HLS（嗅探耗时 3123ms）
- 19:17:05.707 **first frame rendered: latency=4808ms**（首帧渲染 4.8s）
- 19:17:05.725 STATE_READY play success
- 19:17:07.013 onPause（用户 1.3s 后切换下一个）

**影响**：
- 首帧渲染 4.8s 用户感知"卡住"或"失败"
- DoH 全部失败期间 DNS 解析延迟累积到首帧
- 用户切换下一个视频时，由于 DoH 已熔断走系统 DNS，DNS 缓存命中，首帧延迟降低

**根因**：
1. **DoH 冷启动失败**：首次启动时 DoH 服务器全部 UnknownHostException，但当前逻辑仍尝试 DoH 解析（3 次失败才熔断），每次 DoH 尝试消耗 2-3s
2. **嗅探等待 DNS**：sniffVideoType 的 Range 请求需先 DNS 解析，DoH 失败期间 DNS 解析延迟 2-3s
3. **子 m3u8 加载**：主 m3u8 解析后子 m3u8 请求延迟 1s（首次连接未预热）

### V-004-P0-2: 18:48-19:16 期间 9 次 VideoPlayerActivity 启动但播放器未初始化

**现象**：用户在 18:48-19:16 期间快速切换 9 个视频源/视频，每次都启动 VideoPlayerActivity，但日志中没有任何 prepareAsyncInternal/sniffVideoType/STATE_READY 日志

**日志证据**（004 日志 141-8824 行，系统日志段）：
- 18:48:45 VideoPlayerActivity@1d3891b 启动
- 18:49:01 VideoPlayerActivity@35ad487 启动（16s 后）
- 18:49:08 VideoPlayerActivity@6fec015 启动（7s 后）
- 18:50:00 VideoPlayerActivity@ea11d6 启动（52s 后）
- 18:50:47 VideoPlayerActivity@392401f 启动（47s 后）
- 18:51:59 VideoPlayerActivity@8c8e7b6 启动（72s 后）
- 18:52:24 VideoPlayerActivity@829ac89 启动（25s 后）
- 18:53:13 VideoPlayerActivity@386a51e 启动（49s 后）
- 18:53:28 VideoPlayerActivity@5c6b6a8 启动（15s 后）
- **8825 行起（19:16:47）才有 AppLog 输出**——前 9 次 Activity 期间 AppLog 完全无输出

**影响**：
- 用户感知"第一个视频总是失败"——9 次进入视频播放器都没有播放
- AppLog 无输出导致无法定位具体失败原因

**根因假设**（需进一步验证）：
1. **AppLog 未初始化**：09:39 崩溃后 App 可能进入异常状态，AppLog 未正常初始化，直到 19:16 重新启动才恢复
2. **VideoPlay.initSource 失败**：onActivityCreated 中 `if (!VideoPlay.initSource(...)) { finish() }` 直接退出，但 initSource 失败原因无日志（AppLog 未输出）
3. **Activity 快速切换**：用户切换太快，initSourceJob 在 onPause 时被取消（T2.8 修复），播放器未到 prepareAsyncInternal 就被销毁

### V-004-P1-1: DoH 冷启动失败立即熔断

**现象**：DoH 服务器全部 UnknownHostException，3 次失败触发熔断 5min

**日志证据**（004 日志 9279-9562 行）：
- 19:16:57.695-697 DoH server#1/#2/#3 全部失败（host=gu***）
- 19:16:58.762-765 DoH 又一组失败（host=im***）
- 19:17:03.225-230 DoH 又一组失败（host=vo***）
- 19:17:03.230 **consecutive DoH failures, disable DoH 5min, fallback system DNS**

**影响**：
- 冷启动场景 DoH 不可达时，前 3 次解析每个消耗 2-3s（并行查询超时）
- 累计 6-9s 延迟叠加到首帧渲染
- 熔断后系统 DNS 兜底，但首次系统 DNS 解析仍需时间

**根因**：
- DoH 服务器在冷启动场景可能不可达（网络未完全建立/防火墙阻断）
- 当前逻辑：3 次全服务器失败才熔断，每次 2-3s → 累计 6-9s
- 应优化为：冷启动场景首次 DoH 失败立即走系统 DNS，DoH 异步预热

### V-004-P1-2: Cronet Request Canceled 日志噪音

**现象**：用户快速切换视频时 Cronet 请求被取消，日志输出 ERROR 级别干扰

**日志证据**（004 日志 9492-9510 行）：
- 19:16:59.508 Cronet Request Canceled（用户切换视频导致）
- 19:17:13.680 Cronet Request Canceled（用户退出视频播放器导致）
- 输出为 `W System.err` + `E io.legado.app.constant.AppLog` 双重日志

**影响**：
- 日志噪音干扰真实问题定位
- 用户正常切换被误记为错误

**根因**：
- CronetInterceptor 将 Request Canceled 当作错误输出 ERROR 级别
- 实际是正常取消（用户切换/退出），应降级为 DEBUG 级别

### V-004-P2-1: 嗅探耗时 3123ms

**现象**：sniffVideoType 耗时 3123ms（成功视频），主要消耗在 DNS 解析

**日志证据**：
- 19:17:00.956 sniff job started
- 19:17:04.081 sniffVideoType success elapsed=3123ms
- 期间 19:17:03.225-230 DoH 失败 → 系统兜底 DNS

**根因**：
- DoH 失败期间 Range 请求等待 DNS 解析（2-3s）
- DoH 熔断后系统 DNS 首次解析仍需时间（未缓存）

## 二、验收标准

### V-004-P0-1 验收标准
- [ ] 首帧渲染时间 ≤ 2 秒（冷启动场景，DoH 熔断后系统 DNS 兜底）
- [ ] 嗅探耗时 ≤ 1.5 秒（DNS 缓存命中场景）
- [ ] 用户感知"第一个视频失败"不再出现（首帧 ≤ 2s + 进度提示）

### V-004-P0-2 验收标准
- [ ] AppLog 在 VideoPlayerActivity 启动后立即输出（不依赖 App 重启）
- [ ] 18:48-19:16 期间的 9 次 Activity 启动场景不再出现（initSource 失败有日志+重试）
- [ ] VideoPlay.initSource 失败时记录详细原因（不静默 finish）

### V-004-P1-1 验收标准
- [ ] DoH 冷启动首次失败立即走系统 DNS（不等 3 次熔断）
- [ ] DoH 异步预热（不阻塞首帧渲染）
- [ ] 日志中无连续 3 次 DoH 全服务器失败累计 6-9s 延迟

### V-004-P1-2 验收标准
- [ ] Cronet Request Canceled 降级为 DEBUG 级别日志
- [ ] 日志中无 `W System.err: Cronet Request Canceled` 噪音

### V-004-P2-1 验收标准
- [ ] 嗅探前 DNS 预解析（域名预热）
- [ ] 子 m3u8 预取（主 m3u8 解析后立即预取子 m3u8）
- [ ] 嗅探耗时 ≤ 1.5 秒（DNS 缓存命中场景）

## 三、非目标

- 不重构 VideoPlayerActivity 整体架构
- 不修改 PlayerInstancePool 的池化策略（V-P0-1 已修复 TrackSelector 崩溃）
- 不修改图片播放器（004 日志中图片播放器无崩溃）
- 不修改高亮规则（已独立 spec 处理）
- **不修改 BUFFERING 超时阈值**（004 日志中未触发 BUFFERING timeout，12s 阈值无需调整）
- **不修改降级链类型校验**（004 日志中未触发降级链误判，buildFallbackTypes 逻辑正确）

## 四、依赖

- 004 真机日志：`issues/user/temp/20260727/004/Downloadslogs(1).(4)..zip`（解压后 logcat.txt 12219 行）
- 前序修复：realdevice-test-fix-003-20260727（V-P0-1 TrackSelector + I-P0-1/I-P0-2 图片防盗链）
- 相关源码：
  - `app/src/main/java/io/legado/app/ui/video/VideoPlayerActivity.kt`（onActivityCreated/initSource）
  - `app/src/main/java/io/legado/app/help/gsyVideo/Exo2MediaPlayer.kt`（prepareAsyncInternal/sniffVideoType）
  - `app/src/main/java/io/legado/app/help/http/DohDns.kt`（DoH 熔断逻辑）
  - `app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt`（Request Canceled 日志级别）
  - `app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt`（sniffVideoType/DNS 预解析）
