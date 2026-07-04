# Tasks: 依赖升级性能优化 + minSdk 迁移 + WebView 性能修复

## Phase 0: minSdk 21→23 迁移（前置条件）

- [ ] 0.1 修改 `app/build.gradle` 中 minSdk 从 21 改为 23
- [ ] 0.2 清理 `NetworkUtils.kt` API<23 兼容分支（移除旧 ConnectivityManager 逻辑，只保留 NetworkCapabilities）
- [ ] 0.3 清理 `AudioPlayActivity.kt` API<M 调速按钮隐藏（移除条件判断，M+ 默认显示）
- [ ] 0.4 清理 `AppDatabase.kt` setLocale 版本保护（移除 if 判断，直接调用 db.setLocale）
- [ ] 0.5 清理 `Request.kt` 权限降级逻辑（移除 API<M 分支，实际路径为 lib.permission）
- [ ] 0.6 简化 `ViewExtensions.kt` requestLayoutBroken：`<=M` 改为 `==M`（API 23 仍有 bug，不可删除；O..Q 条件独立保留）
- [ ] 0.7 清理 `WebViewPool.kt` 第 84 行 `>=M` 守卫（移除条件判断，直接调用 setOnScrollChangeListener）
- [ ] 0.8 清理 `BottomWebViewDialog.kt` 第 348/433 行 `>=M` 守卫
- [ ] 0.9 清理 `SystemUtils.kt` 第 19 行 API<M early return
- [ ] 0.10 确认 desugar 依赖保留（不移除 desugar_jdk_libs_nio）
- [ ] 0.11 修正 `libs.versions.toml` 中 rhino 注释（"Android 8 以下" → "API 33 以下不可用，desugaring 不覆盖 VarHandle"）
- [ ] 0.12 修正 `libs.versions.toml` 中 commons-text 注释（"Android 6 以下" → "API 24 以下不可用，desugaring 不覆盖 Arrays.setAll"）
- [ ] 0.13 Phase 0 编译验证：`gradlew assembleAppDebug`

## Phase 1: P0 层升级（低风险高收益）

- [ ] 1.1 升级 Kotlin Coroutines 1.10.2 → 1.11.0
  - 修改 libs.versions.toml 中 coroutines 版本
  - 验证：零代码修改，编译即可
  - 性能增益：Channel 9.8x 加速、SharedFlow 修复、R8 GC 修复

- [ ] 1.2 升级 AndroidX Core 1.17.0 → 1.19.0
  - 修改 libs.versions.toml 中 core 版本
  - 移除 `#noinspection GradleDependency` 注释
  - ⚠️ core-ktx 1.19.0 变空壳（扩展函数已移入 core 主模块），保留 core-ktx 依赖声明
  - 验证：编译通过即可，无需代码修改

- [ ] 1.3 升级 AndroidX Lifecycle 2.9.4 → 2.11.0
  - 修改 libs.versions.toml 中 lifecycle 版本
  - 移除 `#noinspection GradleDependency` 注释
  - 验证：2.11.0 已是稳定版（二次审查确认）；项目仅用 lifecycle-common-java8 + lifecycle-service
  - 性能增益：内存优化、LifecycleEffect、SavedStateHandle 改进

- [ ] 1.4 升级 AndroidX Activity 1.11.0 → 1.13.0
  - 修改 libs.versions.toml 中 activity 版本
  - 移除 `#noinspection GradleDependency` 注释
  - 验证：12 处 OnBackPressedDispatcher 均在 super.onCreate() 后调用，零 NPE 风险
  - 性能增益：NavigationEvent、PiP 支持

- [ ] 1.5 升级 Material Design 1.13.0 → 1.14.0
  - 修改 libs.versions.toml 中 material 版本
  - 验证：AppCompat 主题不受影响；enableEdgeToEdge 零使用
  - 性能增益：Bug 修复（已进入维护模式）

- [ ] 1.6 升级 Media3 1.8.0 → 1.10.1
  - 修改 libs.versions.toml 中 media3 版本
  - 移除 `#noinspection GradleDependency` 注释
  - 删除 `Exo2MediaPlayer.kt` 中未使用的 DefaultHttpDataSource import
  - ⚠️ 需验证 gsyVideoPlayer-exo2 与 media3 1.10.x 兼容性（运行时测试视频播放）
  - 性能增益：ExoPlayer 优化、StuckPlayer 检测

- [ ] 1.7 升级 Firebase BOM 33.2.0 → 34.12.0
  - 修改 libs.versions.toml 中 firebaseBom 版本
  - 移除 `#noinspection GradleDependency` 注释
  - 验证：项目已用非 KTX 模块名，仅改版本号

- [ ] 1.8 ⏸️ Fragment 保持 1.8.9 不变
  - 原因：1.9.0 仅有 alpha 版，当前即为最新稳定版

- [ ] 1.9 P0 层全量编译验证
  - 执行 `gradlew assembleAppDebug`
  - 确认 APK 生成成功
  - 验证 gsyVideoPlayer 视频播放功能

## Phase 2: WebView 性能修复（代码层）

- [ ] 2.1 W1: 前台 WebView 设置硬件加速层
  - WebViewPool.preInitWebView(): 设置 setLayerType(HARDWARE)
  - WebViewPool.release(): 重置 setLayerType(HARDWARE)（保持池中 WebView layerType 一致）
  - WebViewActivity: acquire 后设置 setLayerType(HARDWARE)
  - BottomWebViewDialog: acquire 后设置 setLayerType(HARDWARE)
  - ReadRssActivity: acquire 后设置 setLayerType(HARDWARE)
  - BookInfoActivity: acquire 后设置 setLayerType(HARDWARE)
  - WebViewLoginFragment: acquire 后设置 setLayerType(HARDWARE)
  - VideoPlayerActivity: acquire 后设置 setLayerType(HARDWARE)
  - BackstageWebView: **不设置**（后台不需要 GPU 渲染）

- [ ] 2.2 W2: WebViewActivity 显式声明硬件加速
  - AndroidManifest.xml 中 WebViewActivity 添加 `android:hardwareAccelerated="true"`

- [ ] 2.3 WebView 修复编译验证
  - 执行 `gradlew assembleAppDebug`
  - 确认 APK 生成成功

## Phase 3: P1 层升级（中风险高收益，需适配）

- [ ] 3.1 升级 OkHttp 5.3.2 → 5.4.0
  - 修改 libs.versions.toml 中 okhttp 版本
  - ⚠️ 运行时验证：编译后运行 ObsoleteUrlFactory.main() 测试
  - 专项验证 ObsoleteUrlFactory 兼容性（okio Pipe/Buffer 行为）
  - 验证 Cronet 集成
  - 如果运行时失败：回退 OkHttp 到 5.3.2

- [ ] 3.2 P1 层编译验证
  - 执行 `gradlew assembleAppDebug`
  - 确认 APK 生成成功

## Phase 4: 验证 + 文档同步

- [ ] 4.1 编译完整 APK
  - 执行 `gradlew assembleAppDebug`
  - 确认无编译错误和警告

- [ ] 4.2 功能验证
  - 书架显示和操作
  - 搜索和书源管理
  - 阅读界面（翻页、目录、书签）
  - 网络请求（AnalyzeUrl/Cronet/WebView）
  - 数据库操作（导入/导出/备份）
  - WebView 浏览器页面滚动流畅度
  - RSS 文章阅读流畅度
  - 后台书源解析（BackstageWebView 仍正常工作）
  - 返回键处理（OnBackPressedDispatcher 12 处）
  - 音频播放（ExoPlayer 升级后）
  - 视频播放（gsyVideoPlayer + media3 1.10.1）
  - 生命周期（lifecycle 2.11.0 升级后 Activity/Fragment 生命周期）

- [ ] 4.3 性能对比
  - 对比升级前后的 APK 大小
  - 对比升级前后的冷启动时间
  - WebView 滚动流畅度主观评估

- [ ] 4.4 更新 updateLog.md
  - 追加 minSdk 提升说明
  - 追加依赖升级优化记录
  - 追加 WebView 性能优化记录

- [ ] 4.5 更新 docs/project-flow/quick-reference.md
  - 更新版本锁定速查表
  - 更新 minSdk 信息

- [ ] 4.6 更新 docs/project-flow/architecture/overview.md
  - 更新关键版本信息

- [ ] 4.7 更新 tasks.md 完成状态

## P2 待办（延后）

- [ ] P2.1 webkit 1.14.0 → 1.16.0（需 minSdk≥24，后续评估）
- [ ] P2.2 fragment 1.8.9 → 1.9.0（待 1.9.0 稳定版发布）
- [ ] P2.3 Room 2.7.1 → 2.8.4（KMP 架构变更，需单独评估适配风险）
- [ ] P2.4 commons-text 1.13.1 升级（需 minSdk≥24，desugaring 不覆盖 Arrays.setAll）
- [ ] P2.5 shouldInterceptRequest 结果缓存（风险过高：过滤绕过/缓存一致性/线程阻塞，需设计安全方案后实施）
