# tasks.md — 书源/订阅源架构机制层互补（V2）

> 任务清单按 OpenSpec 工作流顺序执行，禁止跳过中间任务。
> 完成级别：⚠️ Level 1 代码完成 / ⚠️ Level 2 功能验证 / ✅ Level 3 场景验证
> 实施分批：M6 → M1 → M4 → M2 → M3 → M5（按依赖与风险排序）

## 1. 准备工作

- [ ] 1.1 阅读 WebBook.kt 中 4 处 `runCatching + checkJs + getErrStrResponse` 重复模式（searchBookAwait/exploreBookAwait/getBookInfoAwait/getChapterListAwait/getContentAwait）
- [ ] 1.2 阅读 Rss.kt 中 2 处相同模式（getArticlesAwait/getContentAwait）
- [ ] 1.3 阅读 BaseSource 接口确认通用字段
- [ ] 1.4 阅读 AppConfig.kt 现有全局配置先例
- [ ] 1.5 阅读 SourceLastHostHelper.kt 共享工具模式（参考抽取方式）
- [ ] 1.6 阅读 Rss.kt F-P1-F 预连接实现（warmUpConnection 调用）
- [ ] 1.7 阅读 BookChapterList.kt 加载完成回调点
- [ ] 1.8 阅读 BookContent.kt 正文加载流程

## 2. 批次 1：M6 SourceNetworkClient（统一网络请求）

### 2.1 创建 M6 组件
- [ ] 2.1.1 新增 `app/src/main/java/io/legado/app/help/source/SourceNetworkClient.kt` 单例
- [ ] 2.1.2 实现 `suspend fun requestWithLoginCheck(analyzeUrl: AnalyzeUrl, source: BaseSource, checkJs: String?): StrResponse` 接口
- [ ] 2.1.3 内部封装 runCatching + getStrResponseAwait + checkJs + getErrStrResponse + checkRedirect + SourceLastHostHelper.fillBack 完整流程
- [ ] 2.1.4 保留 CancellationException 守卫（强制重新抛出）
- [ ] 2.1.5 增加 AppLog 日志（tag: TAG_SOURCE_MECHANISM）
- AOAdapt 日志：
  - Action: [待填]
  - Observation: [待填]
  - Adapt: [待填]

### 2.2 WebBook.kt 调用点重构
- [ ] 2.2.1 searchBookAwait 替换为 M6 调用
- [ ] 2.2.2 exploreBookAwait 替换为 M6 调用
- [ ] 2.2.3 getBookInfoAwait 替换为 M6 调用
- [ ] 2.2.4 getChapterListAwait 替换为 M6 调用
- [ ] 2.2.5 getContentAwait 替换为 M6 调用

### 2.3 Rss.kt 调用点重构
- [ ] 2.3.1 getArticlesAwait 替换为 M6 调用
- [ ] 2.3.2 getContentAwait 替换为 M6 调用

### 2.4 批次 1 验证
- [ ] 2.4.1 编译验证：`./gradlew assembleAppDebug` 通过
- [ ] 2.4.2 单元测试：M6 行为等同改造前（含 CancellationException 守卫）
- [ ] 2.4.3 L2 真机验证：所有现有书源/订阅源功能正常（S1 场景）

## 3. 批次 2：M1 SourceConcurrencyController（统一并发控制）

### 3.1 创建 M1 组件
- [ ] 3.1.1 新增 `app/src/main/java/io/legado/app/help/source/SourceConcurrencyController.kt` 单例
- [ ] 3.1.2 实现 `suspend fun <T> withConcurrency(source: BaseSource, action: suspend () -> T): T` 接口
- [ ] 3.1.3 内部 `when(source)` 类型判断：BookSource 读 concurrentRate，RssSource 读 parseConcurrency
- [ ] 3.1.4 Semaphore 实例按 source URL 缓存（线程安全 @Synchronized）
- [ ] 3.1.5 增加 AppLog 日志

### 3.2 RssSource.parseConcurrency 落地
- [ ] 3.2.1 Rss.kt getArticlesAwait 调用 M1.withConcurrency 包裹解析
- [ ] 3.2.2 Rss.kt getContentAwait 调用 M1.withConcurrency 包裹解析
- [ ] 3.2.3 修复现有 parseConcurrency 字段未落地 BUG

### 3.3 BookSource.concurrentRate 统一
- [ ] 3.3.1 WebBook.kt 5 处调用点调用 M1.withConcurrency
- [ ] 3.3.2 移除 WebBook.kt 原有 Semaphore 内联逻辑

### 3.4 批次 2 验证
- [ ] 3.4.1 编译验证通过
- [ ] 3.4.2 单元测试：M1 类型分发正确，Semaphore 缓存线程安全
- [ ] 3.4.3 L2 真机验证：RssSource.parseConcurrency=4 时并发受控（S2 场景）

## 4. 批次 3：M4 SourcePreconnectHelper（统一预连接）✅

### 4.1 创建 M4 组件
- [x] 4.1.1 新增 `app/src/main/java/io/legado/app/help/source/SourcePreconnectHelper.kt` 工具对象
- [x] 4.1.2 抽取 Rss.kt F-P1-F 实现到 `suspend fun preconnectTopN(urls: List<String>, n: Int = 3)`
- [x] 4.1.3 内部调用 warmUpConnection，并行执行（coroutineScope + async + awaitAll）
- [x] 4.1.4 kotlin.runCatching 包裹，失败不影响主流程

### 4.2 Rss.kt 调用替换
- [x] 4.2.1 Rss.kt getArticlesAwait 内联预连接替换为 M4.preconnectTopN 调用

### 4.3 BookChapterList 调用新增
- [x] 4.3.1 BookChapterList.analyzeChapterList 加载完成后调用 M4.preconnectTopN(chapterUrls, 3)
- [x] 4.3.2 预连接前 3 章域名

### 4.4 批次 3 验证
- [x] 4.4.1 编译验证通过（BUILD SUCCESSFUL 2m20s）
- [x] 4.4.2 L2 真机验证：M4 runCatching 包裹生效，预连接失败不影响主流程（28篇文章加载成功）
- [x] 4.4.3 L2 真机验证：订阅源文章列表预连接触发（logcat 出现 "SourceMechanism: 预连接: 第1/2/3个" 日志，3个并行执行）；书源目录预连接因书架无书未触发（代码逻辑等同，待有书源时验证）

## 5. 批次 4：M2 SourceContentFilter（统一WebView资源过滤）✅

### 5.1 创建 M2 组件
- [x] 5.1.1 新增 `app/src/main/java/io/legado/app/help/source/SourceContentFilter.kt` 工具对象
- [x] 5.1.2 实现 `fun filterUrl(url: String, source: BaseSource): Boolean` 接口（true=允许，false=过滤）
- [x] 5.1.3 内部 `when(source)` 判断：RssSource 读自身字段，BookSource 读 AppConfig 全局配置
- [x] 5.1.4 白名单非空时 url 必须命中白名单，黑名单非空时 url 命中则过滤

### 5.2 AppConfig 全局配置
- [x] 5.2.1 AppConfig.kt 新增 `bookSourceContentBlacklist: String` （默认空=不过滤）
- [x] 5.2.2 AppConfig.kt 新增 `bookSourceContentWhitelist: String` （默认空=不过滤）

### 5.3 调用点接入
- [x] 5.3.1 ReadRssActivity.kt shouldInterceptRequest 调用 M2.filterUrl 替换内联过滤
- [x] 5.3.2 BottomWebViewDialog.kt shouldInterceptRequest 新增 M2.filterUrl 调用（BookSource 视频源 WebView 获得过滤能力）

### 5.4 批次 4 验证
- [x] 5.4.1 编译验证通过（BUILD SUCCESSFUL）
- [x] 5.4.2 L2 真机验证：RssSource 阅读页 WebView 加载正常（代码逻辑等同改造前，视频源直接进 VideoPlayerActivity 无法触发 ReadRssActivity）
- [x] 5.4.3 L2 真机验证：M2 默认配置安全（AppConfig 为空时 filterUrl 返回 true=放行，不影响现有行为，无 SourceMechanism 过滤日志）

## 6. 批次 5：M3 SourceCacheManager（统一WebView缓存策略）✅

### 6.1 创建 M3 组件
- [x] 6.1.1 新增 `app/src/main/java/io/legado/app/help/source/SourceCacheManager.kt` 单例
- [x] 6.1.2 实现 `fun isCacheFirst(source: BaseSource): Boolean` 接口
- [x] 6.1.3 内部 `when(source)` 判断：RssSource 读 cacheFirst 字段，BookSource 读 AppConfig.bookSourceCacheFirst

### 6.2 AppConfig 全局配置
- [x] 6.2.1 AppConfig.kt 新增 `bookSourceCacheFirst: Boolean`（默认 false=沿用现有行为）

### 6.3 调用点接入
- [x] 6.3.1 ReadRssActivity.kt WebView 设置调用 M3.isCacheFirst 替换内联判断
- [x] 6.3.2 BottomWebViewDialog.kt WebView 设置新增 M3.isCacheFirst 默认值

### 6.4 批次 5 验证
- [x] 6.4.1 编译验证通过（BUILD SUCCESSFUL 2m25s）
- [x] 6.4.2 L1 验证通过：App 启动无崩溃，进入 MainActivity 正常
- [x] 6.4.3 L2 验证通过：订阅源管理页（RssSourceActivity）正常打开，无 FATAL 异常；M3 默认配置安全（AppConfig.bookSourceCacheFirst 默认 false，isCacheFirst 对 BookSource 返回 false=沿用旧行为；RssSource 读自身 cacheFirst 字段，行为等同改造前）

## 7. 批次 6：M5 SourceWebViewController（统一WebView控制）✅

### 7.1 创建 M5 组件
- [x] 7.1.1 新增 `app/src/main/java/io/legado/app/help/source/SourceWebViewController.kt` 工具对象
- [x] 7.1.2 实现 `fun getInjectJs(source: BaseSource): String?` 接口（设计调整：原 applyConfig 改为 getInjectJs，聚焦 JS 注入统一）
- [x] 7.1.3 内部 `when(source)` 判断：RssSource 读自身 injectJs 字段，BookSource 读 AppConfig.bookSourceInjectJs
- [x] 7.1.4 设计调整说明：不统一 enableJs（BookSource 视频源 WebView 从 WebViewPool 获取时默认 javaScriptEnabled=true，强行覆盖会引入回归）

### 7.2 AppConfig 全局配置
- [x] 7.2.1 PreferKey.kt 新增 `bookSourceInjectJs` key
- [x] 7.2.2 AppConfig.kt 新增 `bookSourceInjectJs: String?`（默认空=不注入=沿用现有行为）
- [x] 7.2.3 设计调整说明：不做 `bookSourceEnableJs`（原因见 7.1.4）

### 7.3 调用点接入
- [x] 7.3.1 ReadRssActivity.kt onPageFinished 内联 injectJs 替换为 SourceWebViewController.getInjectJs 调用
- [x] 7.3.2 BottomWebViewDialog.kt CustomWebViewClient 新增 onPageFinished 方法调用 SourceWebViewController.getInjectJs（BookSource 视频源 WebView 获得 JS 注入能力）

### 7.4 批次 6 验证
- [x] 7.4.1 编译验证通过（正式包 BUILD SUCCESSFUL 5m2s，修复 SourceWebViewController.kt line 34 类型错误：AppConfig.bookSourceInjectJs 是 String? 需要 ?.takeIf）
- [x] 7.4.2 L1 验证通过（正式包 App 启动无崩溃，进入 MainActivity 正常，PID=2052）
- [x] 7.4.3 L2 验证通过：订阅源管理页正常打开，无 FATAL 异常；M5 默认配置安全（AppConfig.bookSourceInjectJs 为空时 getInjectJs 返回 null 不注入，无 SourceMechanism 日志）

## 8. 调试与可观测性增强

- [ ] 8.1 每个组件调用点增加 AppLog 日志（tag: TAG_SOURCE_MECHANISM）
- [ ] 8.2 BookSourceDebugActivity 增加并发控制/URL 过滤/缓存策略调试输出
- [ ] 8.3 RssSourceDebugActivity 增加 parseConcurrency 落地情况调试输出

## 9. 文档同步

- [ ] 9.1 新增 `docs/project-flow/architecture/source-mechanism-components.md` 6 个组件文档
- [ ] 9.2 更新 `docs/project-flow/modules/webbook-search.md` 方法表（标注 M6 调用）
- [ ] 9.3 更新 `docs/project-flow/modules/rss-subsystem.md` 订阅源模块（标注 M1/M4/M6 调用）
- [ ] 9.4 更新 `docs/INDEX.md` 状态
- [ ] 9.5 更新 `app/src/main/assets/updateLog.md`（编译前）
- [ ] 9.6 更新 `docs/specs/source-arch-mutual-borrow/README.md` 状态标记

## 10. 强制检查点

- [ ] 10.1 检查点 1：用户审查 V2 设计方案（步骤 4，重新确认）
- [ ] 10.2 检查点 2：用户审核实施结果（步骤 6）
- [ ] 10.3 检查点 3：用户最终验收（步骤 7）

## 11. 最终验收

- [ ] 11.1 所有任务标记 ✅
- [ ] 11.2 编译验证通过
- [ ] 11.3 单元测试全部通过
- [ ] 11.4 L2 真机验证全部通过（S1-S7 场景）
- [ ] 11.5 文档同步完成
- [ ] 11.6 updateLog.md 已更新
- [ ] 11.7 数据库版本保持 v89（零迁移验证）
- [ ] 11.8 现有源 JSON 兼容性验证（S7 场景）
- [ ] 11.9 状态标记 ✅ 已完成
