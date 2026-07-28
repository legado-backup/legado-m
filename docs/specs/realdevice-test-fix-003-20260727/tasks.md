# tasks.md — realdevice-test-fix-003-20260727

## Phase A：P0 崩溃修复

- [ ] **A1. V-003-P0-2 prepareAsyncInternal 重入保护**
  - [ ] `Exo2MediaPlayer.kt` 新增 `isPreparing: AtomicBoolean` 字段
  - [ ] prepareAsyncInternal 入口 `compareAndSet(false, true)` 守卫，重入跳过 + 日志
  - [ ] finally 块重置 `isPreparing.set(false)`
  - 验收：prepareAsyncInternal 不被重入；无重复 acquire/createLoadControl
- [ ] **A2. I-003-P0-1 Glide destroyed activity 守卫**
  - [ ] `ImageCanvasAdapter.preloadAround` 入口添加 `isDestroyed/isFinishing` 前置守卫
  - [ ] `ImageGalleryActivity` onScrollStateChanged 回调入口添加守卫
  - 验收：Activity 销毁后快速滑动不崩溃
- [ ] **A3. Phase A 编译验证**（assembleDebug BUILD SUCCESSFUL）

## Phase B：P1 功能缺陷修复

- [ ] **B1. V-003-P1-1 BUFFERING 降级链设计缺陷修复**
  - [ ] `Exo2MediaPlayer.buildFallbackTypes` 清单类型降级链移除 Progressive
  - [ ] HLS → [HLS, DASH]；DASH → [DASH, HLS]；SS → [SS, HLS, DASH]
  - [ ] UNKNOWN/null 后缀 → [HLS, DASH]（移除 Progressive）
  - [ ] 直链/TYPE_OTHER 保留 [OTHER, HLS, DASH]
  - 验收：HLS 流 BUFFERING 超时不降级到 Progressive；无 21 Extractor 全失败
- [ ] **B2. I-003-P1-2 URL 拼接 %0A Bug 修复**
  - [ ] 找到 parseImageUrls strategy 1 (newline split) 实现
  - [ ] 分割后对每个 URL 执行 `trim()` + 过滤含 `%0A`/`\n` 的残留
  - [ ] 添加日志记录过滤前后数量变化
  - 验收：解析出的 URL 不含 %0A/换行符；404 次数显著下降
- [ ] **B3. I-003-P1-3 图片播放器 UX 对齐**
  - [ ] B3.1 工具栏：`activity_image_gallery.xml` 添加 Toolbar + `R.menu.image_gallery` + `ImageGalleryActivity` menu 逻辑
  - [ ] B3.2 占位底图：`ImageCanvasAdapter` RequestOptions placeholder/error/crossfade + 错误点击重试
  - [ ] B3.3 进度指示：顶部 `第 X/共 Y 张` + ViewHolder 加载状态点
  - 验收：菜单四项可用；占位→crossfade 无闪烁；进度联动准确；错误点击可重试
- [ ] **B4. Phase B 编译验证**（assembleDebug BUILD SUCCESSFUL）

## Phase C：P2 优化

- [ ] **C1. V-003-P2-1 LoadControl 重复创建修复**
  - [ ] `PlayerInstancePool` 按 tier 缓存 LoadControl（ConcurrentHashMap）
  - 验收：acquire 时不重复创建 LoadControl
- [ ] **C2. T-003-P2-1 ai_test 分析脚本**
  - [ ] 新建 `ai_tests/scripts/analyze_player_stats.py`
  - [ ] 实现 analyze(log_path) 函数（Grep 过滤 + 统计计数）
  - 验收：脚本可解析 logcat 输出统计报告

## Phase D：交付

- [ ] **D1. updateLog.md 更新**（git diff 三步法，编译前完成）
- [ ] **D2. 全量编译 + 打包**（assembleDebug，含 Phase A/B/C 全部修复）
- [ ] **D3. 真机验证**（fixed_test_workflow；测试包；收集嗅探/降级/图片加载日志）
- [ ] **D4. 问题闭环记录**（issues-found.md）
