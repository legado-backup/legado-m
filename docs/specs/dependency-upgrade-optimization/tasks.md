# Tasks: 依赖升级性能优化 + minSdk 迁移 + WebView 性能修复

## Phase 0: minSdk 21→23 迁移（前置条件）

- [ ] 0.1 修改 `app/build.gradle` 中 minSdk 从 21 改为 23
- [ ] 0.2 清理 `NetworkUtils.kt` API<23 兼容分支（移除旧 ConnectivityManager 逻辑，只保留 NetworkCapabilities）
- [ ] 0.3 清理 `AudioPlayActivity.kt` API<M 调速按钮隐藏（移除条件判断，M+ 默认显示）
- [ ] 0.4 清理 `AppDatabase.kt` setLocale 版本保护（移除 if 判断，直接调用 db.setLocale）
- [ ] 0.5 清理 `Request.kt` 权限降级逻辑（移除 API<M 分支）
- [ ] 0.6 评估 `ViewExtensions.kt` requestLayoutBroken 标记是否可简化
- [ ] 0.7 确认 desugar 依赖保留（不移除 desugar_jdk_libs_nio）
- [ ] 0.8 Phase 0 编译验证：`gradlew assembleAppDebug`

## Phase 1: P0 层升级（低风险高收益）

- [ ] 1.1 升级 Kotlin Coroutines 1.10.2 → 1.11.0
  - 修改 libs.versions.toml 中 coroutines 版本
  - 验证：零代码修改，编译即可
  - 性能增益：Channel 9.8x 加速、SharedFlow 修复、R8 GC 修复

- [ ] 1.2 升级 AndroidX Lifecycle 2.9.4 → 2.11.0
  - 修改 libs.versions.toml 中 lifecycle 版本
  - 移除 libs.versions.toml 中 `#noinspection GradleDependency` 注释
  - 验证：9 处 onCleared() 中的 super.onCleared() 可保留
  - 性能增益：内存优化、Bug 修复

- [ ] 1.3 升级 AndroidX Core-KTX 1.17.0 → 1.19.0
  - 修改 libs.versions.toml 中 core 版本
  - 移除 `#noinspection GradleDependency` 注释（如有）
  - 验证：KTX 空壳但 import 路径不变；bundleOf 14 文件仅废弃警告
  - 性能增益：Bug 修复

- [ ] 1.4 升级 AndroidX Activity 1.11.0 → 1.13.0
  - 修改 libs.versions.toml 中 activity 版本
  - 移除 `#noinspection GradleDependency` 注释
  - ⚠️ 回归测试 OnBackPressedDispatcher 延迟初始化：12 处使用点
    - BaseActivity.kt:90, WebViewActivity.kt:125, FileManageActivity.kt:61
    - PermissionActivity.kt:157, ReadBookActivity.kt:280, ChangeChapterSourceDialog.kt:124
    - ImportBookActivity.kt:64, RemoteBookActivity.kt:50, MainActivity.kt:101
    - VideoPlayerActivity.kt:209, ReadRssActivity.kt:167, RssSortActivity.kt:225
  - 性能增益：NavigationEvent、PiP 支持、EdgeToEdge 修复

- [ ] 1.5 升级 AndroidX Fragment 1.8.9 → 1.9.0
  - 修改 libs.versions.toml 中 fragment 版本
  - 验证：变更极少，FragmentActivity 仅 2 处类型检查
  - 性能增益：Predictive back 修复

- [ ] 1.6 升级 Material Design 1.13.0 → 1.14.0
  - 修改 libs.versions.toml 中 material 版本
  - 移除 `#noinspection GradleDependency` 注释（如有）
  - 验证：AppCompat 主题不受影响；enableEdgeToEdge 零使用
  - 性能增益：Bug 修复

- [ ] 1.7 升级 Media3 1.8.0 → 1.10.1
  - 修改 libs.versions.toml 中 media3 版本
  - 移除 `#noinspection GradleDependency` 注释
  - 删除 `Exo2MediaPlayer.kt` 中未使用的 DefaultHttpDataSource import
  - 验证：核心 API 全兼容
  - 性能增益：ExoPlayer 优化、StuckPlayer 检测

- [ ] 1.8 升级 Firebase BOM 33.2.0 → 34.12.0
  - 修改 libs.versions.toml 中 firebaseBom 版本
  - 移除 `#noinspection GradleDependency` 注释
  - 验证：项目已用非 KTX 模块名，仅改版本号
  - 性能增益：性能监控优化

- [ ] 1.9 P0 层全量编译验证
  - 执行 `gradlew assembleAppDebug`
  - 确认 APK 生成成功

## Phase 2: WebView 性能修复（代码层）

- [ ] 2.1 W1: 前台 WebView 设置硬件加速层
  - WebViewActivity: acquire 后设置 setLayerType(HARDWARE)
  - BottomWebViewDialog: acquire 后设置 setLayerType(HARDWARE)
  - ReadRssActivity: acquire 后设置 setLayerType(HARDWARE)
  - BookInfoActivity: acquire 后设置 setLayerType(HARDWARE)
  - WebViewLoginFragment: acquire 后设置 setLayerType(HARDWARE)
  - BackstageWebView: **不设置**（后台不需要 GPU 渲染）

- [ ] 2.2 W2: WebViewActivity 显式声明硬件加速
  - AndroidManifest.xml 中 WebViewActivity 添加 `android:hardwareAccelerated="true"`

- [ ] 2.3 W3替代: shouldInterceptRequest 结果缓存
  - 为 getModifiedContentWithJs() 添加内存缓存
  - 缓存 key = URL + JS_URL 组合
  - 缓存随 WebView 释放而清除

- [ ] 2.4 WebView 修复编译验证
  - 执行 `gradlew assembleAppDebug`
  - 确认 APK 生成成功

## Phase 3: P1 层升级（中风险高收益，需适配）

- [ ] 3.1 升级 OkHttp 5.3.2 → 5.4.0
  - 修改 libs.versions.toml 中 okhttp 版本
  - 专项验证 ObsoleteUrlFactory 兼容性（okio Pipe/Buffer 行为）
  - 验证 Cronet 集成
  - 编译验证

- [ ] 3.2 升级 Room 2.7.1 → 2.7.x 最新补丁
  - 修改 libs.versions.toml 中 room 版本
  - 验证数据库迁移路径（89 版本、38 处 SupportSQLiteDatabase）
  - 编译验证

- [ ] 3.3 升级 Glide 5.0.5 → 5.0.x 最新补丁
  - 修改 libs.versions.toml 中 glide 版本
  - 验证自定义 ModelLoader 兼容性（OkHttpModelLoader/FilePathLoader/LegadoDataUrlLoader）
  - 验证自定义 BitmapTransformation 兼容性（Blur/Grayscale/Epaper）
  - 编译验证

- [ ] 3.4 升级 AppCompat 1.7.1 → 1.7.x 最新补丁
  - 修改 libs.versions.toml 中 appcompat 版本
  - 编译验证

- [ ] 3.5 P1 层全量编译验证
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
- [ ] P2.2 commons-text 1.13.1 升级验证（在 API 23 模拟器上测试 desugaring 是否解决 Arrays.setAll）
- [ ] P2.3 bundleOf 迁移（14 文件，从 bundleOf() 改为 Bundle().apply {}，可选清理）
- [ ] P2.4 launchWhenResumed 迁移（2 处，改为 repeatOnLifecycle，可选清理）
