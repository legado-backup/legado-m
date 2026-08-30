# 真机测试问题修复 - 任务清单

> **依据**：design.md / spec.md
> **执行纪律**：每 Phase 完成后编译验证；同一文件 Edit 串行；代码变更后 updateLog.md 编译前更新；全部完成后按 ai_e2e_testing_workflow 真机验证（测试包 io.legado.miss.app.debug）

---

## Phase A：P0 止血（崩溃 + 图片全挂）

- [ ] **A1. V-P0-1 TrackSelector 每实例独立**
  - [ ] PlayerInstancePool.kt：删 `sharedTrackSelector` 单例，新增 `createTrackSelector()` 工厂；acquire 新建实例各自持有
  - [ ] Exo2MediaPlayer.kt:455-457 改用池实例自带/新建 selector
  - [ ] 日志：acquire hit/miss 输出 selector hash
  - 验收：并发 prepare 0 FATAL；各实例 selector hash 不同
- [ ] **A2. I-P0-1 防盗链头链路修复**
  - [ ] 实施首查：V4 数据流 item.articleIndex 与 ImagePlay.rssArticles 下标映射是否错位
  - [ ] ImageGalleryActivity/ViewModel 显式持有 sourceOrigin + 每图 referer，传入 ImageCanvasAdapter（全局态仅作兜底）
  - [ ] headers 缺失 WARN 日志 + 一次性兜底回填
  - 验收：站点E 场景成功率 ≥95%；403 去重计数日志
- [ ] **A3. I-P0-2 图片降级链修复**
  - [ ] onWebViewFallback 内 WebView 操作 `withContext(Dispatchers.Main)` 包裹
  - [ ] Adapter 按 position 维护降级阶段状态机（0→4 级），onLoadFailed 逐级推进+日志
  - [ ] 预热完成（onPageFinished/5s 超时）触发同域失败图重载
  - 验收：四级降级逐级触发有日志；无异常吞没
- [ ] **A4. Phase A 编译验证**（assembleDebug BUILD SUCCESSFUL）

## Phase B：P1 机制（视频降级链 + 网络）

- [x] **B1. V-P1-1 直链后缀识别 + 启发式降级链**
  - [x] ExoPlayerHelper.guessTypeByUrl 补直链后缀（.mp4/.mkv/.webm/.flv/.avi/.mov/.ts/.m2ts/.mp3/.m4a/.aac/.flac → TYPE_OTHER）
  - [x] 抽 `guessTypeByUrl(url)` 共用入口；buildFallbackTypes UNKNOWN 分支按启发式排序（直链 → [OTHER, HLS, DASH]）
  - 验收：.mp4 首试 Progressive 无 MANIFEST_MALFORMED 试错；m3u8 首选 HLS
- [x] **B2. V-P1-2 3003 白名单 + 末端兜底 + 手动入口**
  - [x] isUnrecoverableError 补 ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED(3003)
  - [x] 末端解析失败（currentFallbackIndex == size-1）直接发 VIDEO_FALLBACK_WEBVIEW + VIDEO_PLAY_ERROR
  - [x] 错误弹框已有"用 WebView 播放"手动按钮（canUseWebView 判定）
  - 验收：全降级失败 WebView 兜底 100% 触发；3003 有 unrecoverable error 日志
- [x] **B3. N-P1-1 Cronet 恢复迟滞**
  - [x] 连续 2 次探测成功才切回；探测超时 ≤3s
  - 验收：弱网抖动每会话降级 ≤1 次
- [x] **B4. N-P1-2 DohDns 修复**
  - [x] IDN/xn-- 旁路系统 DNS（含 toASCII 异常旁路）；三服务器并行（单 2s/总 3s）；负缓存 30s；成功服务器置顶；缓存键含记录类型
  - 验收：IDN <500ms；非 IDN DoH 成功率 >0；无 9s 阻塞
- [x] **B5. Phase B 编译验证**（BUILD SUCCESSFUL in 3m 21s）

## Phase C：P1 体验（图片 UX）

- [ ] **C1. I-P1-1 工具栏对齐视频播放器**：收藏 + 三点菜单（刷新/配置/浏览器打开/日志）
- [ ] **C2. I-P1-2 占位底图 + 进度指示**：placeholder→crossfade；错误占位+点击重试；顶部 第X/共Y张 + 加载状态点
- [ ] **C3. Phase C 编译验证**

## Phase D：P2 收尾

- [ ] **D1. N-P2-1 日志脱敏**：AnalyzeUrl.kt:448 附近 sanitizeUrl；VideoSubTitle 事件源标题脱敏
- [ ] **D2. N-P2-2 RedirectCache**：跨域名命中修正 Referer；LRU 淘汰加锁
- [ ] **D3. I-P2-1 渐进式加载**：大图 thumbnail(0.1f)
- [ ] **D4. T-P2 ai_test 分析脚本**：统计播放成功率/首帧 READY 率/3003 计数/图片 403 率/降级触发率

## Phase E：交付

- [ ] **E1. updateLog.md 更新**（git diff 三步法，编译前完成）
- [ ] **E2. 全量编译 + 打包**（assembleDebug）
- [ ] **E3. 真机验证**（fixed_test_workflow；测试包；收集嗅探/降级/图片加载日志）
- [ ] **E4. 问题闭环记录**（issues-found.md）

---

> R-P1 高亮问题任务见独立 spec：`docs/specs/highlight-rule-fix-20260727/tasks.md`（待视频+图片完成后实施）
