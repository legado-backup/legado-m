# Tasks: video-player-m3u8-fix

## 1. 准备工作
- [x] 1.1 确认需求范围（m3u8 播放失败根因分析）
- [x] 1.2 阅读相关源码（ExoPlayerHelper.kt / Exo2MediaPlayer.kt）
- [x] 1.3 实际 WebFetch 分析 m3u8 URL 内容（发现 AES-128 加密+相对路径密钥+跨域 TS）

## 2. 核心实现

### P0（必须修复）
- [ ] 2.1 ExoPlayerHelper.sniffVideoType 添加 m3u8 URL 短路检测
  - 位置：`isHtmlInterfaceUrl` 检查之后、`hasResult` 声明之前
  - 逻辑：URL 以 `.m3u8` 结尾时直接返回 `SniffResult(contentType=C.TYPE_HLS, mimeType=APPLICATION_M3U8)`
- [ ] 2.2 Exo2MediaPlayer.applyMediaSourceByType 添加 setDefaultHeaders 注入
  - 位置：`val effectiveUrl = ...` 之后、`val mediaSource = when(contentType)` 之前
  - 逻辑：`if (currentHeaders.isNotEmpty()) ExoPlayerHelper.setDefaultHeaders(currentHeaders)`
  - 这是 **AES-128 加密 m3u8 播放失败的核心修复**

### P1（重要优化）
- [ ] 2.3 ExoPlayerHelper.okhttpDataFactory 移除 setCacheControl 配置
  - 删除 `.setCacheControl(CacheControl.Builder().maxAge(1, TimeUnit.DAYS).build())`
  - 删除 `import okhttp3.CacheControl`（如果无其他引用）

### P2（改进优化）
- [ ] 2.4 Exo2MediaPlayer.buildFallbackTypes 修改 HLS 降级链为 [HLS, Progressive]
  - `C.TYPE_HLS -> listOf(C.TYPE_HLS, C.TYPE_OTHER)`
  - UNKNOWN 默认降级链也改为 `listOf(C.TYPE_HLS, C.TYPE_OTHER)`
- [ ] 2.5 ExoPlayerHelper.createMediaSource 增强 LoadErrorHandlingPolicy
  - 指数退避重试：`2^retryCount * 1000ms`（1s/2s/4s/8s/16s），最多 5 次
- [ ] 2.6 Exo2MediaPlayer.applyMediaSourceByType HlsMediaSource 添加 LoadErrorHandlingPolicy
  - 同 2.5 策略

## 3. 验证
- [ ] 3.1 编译验证（确认无编译错误）
- [ ] 3.2 真机测试：AES-128 加密 m3u8 URL 播放验证（用户提供的 URL）
- [ ] 3.3 真机测试：标准 m3u8 URL 播放验证
- [ ] 3.4 真机测试：动态 URL（play.php?format=m3u8）播放验证
- [ ] 3.5 回归测试：mp4/dash 等非 m3u8 格式播放不受影响
