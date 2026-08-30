# 任务清单 - sniff-stability-enhance-20260731（嗅探稳定性增强）

> **功能名**：sniff-stability-enhance-20260731
> **目标**：通过 9 个 FR 的实施，提升嗅探稳定性、降低重复请求、优化 DNS 与 Cronet 健康度管理。
> **包类型约束**：代码优化任务，真机测试必须使用测试包 `io.legado.miss.app.debug`；最终交付使用正式包 `io.legado.miss.app.release`。

---

## FR 概览

| FR | 优先级 | 主题 | 关键文件 |
|----|--------|------|----------|
| FR-1 | P0 | R5 嗅探去重锁 | VideoUrlExtractor.kt |
| FR-2 | P1 | DoH 负缓存时长优化 + 健康检查 | DohDns.kt / App.kt |
| FR-3 | P1 | 视频流强制 HTTP/1.1 | CronetInterceptor.kt / HttpHelper.kt / ExoPlayerHelper.kt |
| FR-4 | P1 | favicon.ico 缓存 | FaviconCache.kt(新建) / HttpHelper.kt |
| FR-5 | P2 | StreamReset 重用 NonCancellable | StreamResetRetryInterceptor.kt |
| FR-6 | P2 | Cronet 探测跳过日志采样 | CronetInterceptor.kt |
| FR-7 | P2 | 证书错误记忆缓存 | CronetInterceptor.kt |
| FR-8 | P3 | play.php 类 URL 预解析 | VideoUrlExtractor.kt |
| FR-9 | P3 | window.__videoUrls__ 解析容错 | BackstageWebView.kt |

---

## 1. 准备工作

- [ ] 1.1 备份关键源码到 .bak 目录（VideoUrlExtractor.kt / DohDns.kt / CronetInterceptor.kt / StreamResetRetryInterceptor.kt / HttpHelper.kt / ExoPlayerHelper.kt / BackstageWebView.kt）
- [ ] 1.2 读取并核实关键源码当前状态（VideoUrlExtractor.extractVideoUrlForEpisode / DohDns.NEGATIVE_CACHE_TTL_MS / CronetInterceptor.intercept / StreamResetRetryInterceptor.intercept）
- [ ] 1.3 确认日志分析报告中的优化点（extracted_8/log_analysis_report.md）

---

## 2. P0 核心修复（FR-1 R5 嗅探去重锁）

- [ ] 2.1 VideoUrlExtractor.kt 在object内定义r5InProgress `ConcurrentHashMap<String, Deferred<String?>>` + r5CleanupScope（VideoUrlExtractor是object单例，无需companion object）
- [ ] 2.2 VideoUrlExtractor.kt 在 extractWithWebView 方法入口去重：检查 r5InProgress[path] 复用 + 创建新 Deferred + 60s 清理（覆盖4个调用路径）
- [ ] 2.3 VideoUrlExtractor.kt 新增 extractVideoUrlForEpisodeInternal 方法（原 extractVideoUrlForEpisode 逻辑迁移）
- [ ] 2.3.1 FR-1（W8 整改）实施时同步更新 VideoUrlExtractor.kt:38 源码注释为"4处调用方（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552）"（原注释为3处且行号过时）
- [ ] 2.4 编译验证 P0 修复（测试包 io.legado.miss.app.debug）

---

## 3. P1 修复（FR-2 / FR-3 / FR-4）

- [ ] 3.1 FR-2 DohDns.kt NEGATIVE_CACHE_TTL_MS 从 `30_000L` 改为 `10_000L`
- [ ] 3.2 FR-2 DohDns.kt 新增 dohHealthStatus `ConcurrentHashMap` + HealthEntry data class
- [ ] 3.3 FR-2 DohDns.kt 新增 preheatDohServers() 方法（探测 2 个 DoH 服务器延迟 + 选择更优为主）
- [ ] 3.3.1 FR-2（E7 整改）DohDns.kt 修复 asyncPreheatDoh()（L262）探测域名从 cloudflare-dns.com 改为 www.baidu.com，与 preheatDohServers 统一探测域名；明确两者职责分工（preheatDohServers 启动预热 / asyncPreheatDoh 冷启动失败后恢复）
- [ ] 3.4 FR-2 App.kt 在 IO 协程块调用 DohDns.preheatDohServers()（参考 preInitCronetEngine 调用方式）
- [ ] 3.5 FR-3 CronetInterceptor.kt 新增 isVideoStreamPath 函数（检查 .m3u8 / .mp4 / .ts / .flv / .mkv / .webm 后缀）
- [ ] 3.6 FR-3 CronetInterceptor.kt intercept 方法开头新增视频流跳过 Cronet 逻辑
- [ ] 3.7 FR-3 HttpHelper.kt 新增 videoStreamClient（protocols=listOf(Protocol.HTTP_1_1)）
- [ ] 3.7.1 FR-3（E6 整改：诊断先行）实施前在 CronetInterceptor.isProtocolError 分支（L324）增加诊断日志输出请求 path + 调用栈，确认 ERR_HTTP2_PROTOCOL_ERROR 真实来源（验证是否来自 ExoPlayerHelper L417/L740）
- [ ] 3.7.2 FR-3（E6 整改：三重覆盖）ExoPlayerHelper.kt L417/L740 okHttpClient.newCall 改用 HttpHelper.videoStreamClient，强制 HTTP/1.1（视频流播放主路径 okhttpDataFactory 已 HTTP/1.1，此为协议错误真实来源）
- [ ] 3.8 FR-4 新建 FaviconCache.kt（object 单例，LruCache 内存 + 磁盘缓存 24h + 并行请求合并）
- [ ] 3.9 FR-4 HttpHelper.kt intercept 检查 path=/favicon.ico 命中缓存直接返回
- [ ] 3.10 编译验证 P1 修复（测试包 io.legado.miss.app.debug）

---

## 4. P2 优化（FR-5 / FR-6 / FR-7）

- [ ] 4.1 FR-5 StreamResetRetryInterceptor.kt 移除chain.call().cancel()，改用connectionPool.evictAll()清理连接
- [ ] 4.2 FR-5 StreamResetRetryInterceptor.kt 添加 NonCancellable 重试日志
- [ ] 4.3 FR-6 CronetInterceptor.kt 新增 probeSkipCount AtomicInteger
- [ ] 4.4 FR-6 CronetInterceptor.kt L189 改为每 10 次跳过输出 1 次汇总日志
- [ ] 4.5 FR-7 CronetInterceptor.kt 新增 certErrorCache `ConcurrentHashMap<String, Long>`
- [ ] 4.6 FR-7 CronetInterceptor.kt intercept 方法在尝试 Cronet 之前检查 certErrorCache 命中直接走 OkHttp
- [ ] 4.7 FR-7 CronetInterceptor.kt isCertificateError 分支写入 certErrorCache[host]=now+300000
- [ ] 4.8 编译验证 P2 优化（测试包 io.legado.miss.app.debug）

---

## 5. P3 优化（FR-8 / FR-9）

- [ ] 5.1 FR-8 VideoUrlExtractor.kt 新增 PlayerPageCacheEntry data class + playerPageCache `ConcurrentHashMap`
- [ ] 5.2 FR-8 VideoUrlExtractor.kt extractVideoUrlForEpisode 入口检查 playerPageCache 命中直接返回
- [ ] 5.3 FR-8 VideoUrlExtractor.kt 解析成功后写入 playerPageCache（TTL 5 分钟）
- [ ] 5.4 FR-9 BackstageWebView.kt 找到 window.__videoUrls__ 解析代码位置
- [ ] 5.5 FR-9 BackstageWebView.kt GSON.fromJsonArray 失败时添加正则提取容错
- [ ] 5.6 编译验证 P3 优化（测试包 io.legado.miss.app.debug）

---

## 6. 综合验证 + 正式包交付

- [ ] 6.1 更新 updateLog.md（基于 git diff 分析真实代码变更，9 个 FR 条目）
- [ ] 6.2 编译正式包 io.legado.miss.app.release（assembleAppRelease）
- [ ] 6.3 验证 mapping.txt 关键类全部保留（GEN_JNI / CronetLibraryLoaderJni / StreamResetRetryInterceptor / CronetInterceptor / DohDns / FaviconCache）
- [ ] 6.4 交付正式 APK 给用户真机 arm64 测试

---

## 7. E2E 测试 + 文档同步

- [ ] 7.1 用户真机 arm64 测试验证 9 个 FR 效果
- [ ] 7.2 文档同步（对照 AGENTS.md OpenSpec 章节文档同步映射表）
- [ ] 7.3 清理临时文件和调试代码

---

## AOAdapt 日志格式（遇到问题时记录）

当某个任务执行过程中遇到问题、观察异常或需调整方案时，在该任务项下追加 AOAdapt 日志：

```markdown
- [ ] 2.1 实现 XXX
  - Action: [执行了什么操作]
  - Observation: [观察到了什么结果]
  - Adapt: [基于观察做了什么调整]
```

**记录原则**：
- 仅在偏离原方案、遇到阻塞或需要权衡调整时记录
- Action / Observation / Adapt 三段缺一不可
- 调整后的方案需同步反映到后续相关任务
- 禁止记录源名称、域名、URL、cookie 等业务敏感信息，仅记录技术结论
