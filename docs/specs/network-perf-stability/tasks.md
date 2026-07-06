# tasks.md - 网络性能与稳定性深度优化 + 延伸版本功能借鉴任务清单

> **状态**：🔄 设计中（第四版，基于 8 份深度分析文档整合）
> **创建日期**：2026-07-06
> **最新调整**：2026-07-06（整合优化点影响分析 + 缺失功能分析，对齐 spec.md / design.md 第四版）
> **格式**：`- [ ] X.Y` 任务清单 + AOAdapt 日志
> **核心原则**：稳定性优先，借鉴成熟实现，不偏离生态，分阶段实施

---

## 任务总览

| 阶段 | 优化点 | 功能借鉴 | 风险等级 | 实施策略 |
|------|--------|----------|----------|----------|
| **P0** | 9 项（A1/A2/A4/B3/B4/B5/B6/C2/P0-6） | 3 项短平快（F-P0-1~3） | 低 | 立即实施 |
| **P1** | 8 项（A3/A6/A7/B1/B2/C3/C4/C5） | 5 项中等难度（F-P1-1~5） | 中 | 谨慎实施 |
| **P2** | 5 项评估（P2-1~P2-5） | 3 项长期（F-P2-1~3） | 评估 | 完成P0/P1后评估 |
| **P3** | 5 项暂缓（A5/C1/C6/C7/C8） | 2 项长期（F-P3-1~2） | 高 | 暂缓实施 |

---

## 一、P0 阶段：低风险稳定性修复 + 短平快功能借鉴（必做）

### 1. CancellationException 透传修复（A1 + A4）

- [ ] 1.1 修复 `Coroutine.kt:182-190` executeInternal 的 catch 块，加 CancellationException 守卫
  - Action: [待填写]
  - Observation: [待填写]
  - Adapt: [待填写]
- [ ] 1.2 修复 `WebBook.kt` 5 处 catch 块（L88, L159, L234, L331, L436），加 CancellationException 守卫
- [ ] 1.3 修复 `FlowExtensions.kt:59-70` mapParallelSafe 的 catch 块，加 CancellationException 守卫
- [ ] 1.4 修复 `OkHttpExceptionInterceptor.kt:13-17` 的 catch 块，加 CancellationException 守卫（A4）
- [ ] 1.5 编写单元测试 `CoroutineTest`（验证取消异常正确传播）
  - Level 3 验证：协程取消不触发 error 回调

### 2. mutexMap 线程安全修复（A2）

- [ ] 2.1 修复 `BookSourceExtensions.kt:27`，`mutexMap` 从 `hashMapOf` 改为 `ConcurrentHashMap`
- [ ] 2.2 修复 `BookSourceExtensions.kt:50`，`mutexMap[bookSourceUrl] ?: Mutex().apply{...}` 改为 `computeIfAbsent`
- [ ] 2.3 编译验证 + 发现页加载测试
  - Level 2 验证：发现页分类列表正常显示

### 3. MainViewModel poll() 线程安全修复（B3）

- [ ] 3.1 修复 `MainViewModel.kt:55`，`waitUpTocBooks` 从 `LinkedList` 改为 `ConcurrentLinkedQueue`
- [ ] 3.2 保留 `addToWaitUp` 的 `@Synchronized`（保护复合操作）
- [ ] 3.3 编译验证 + 主页刷新测试
  - Level 2 验证：主页书架刷新正常

### 4. CacheBook.close() 同步修复（B4）

- [ ] 4.1 修复 `CacheBook.kt:116-121`，`close()` 方法添加 `@Synchronized` 注解
- [ ] 4.2 编译验证 + 缓存停止测试
  - Level 1 验证：编译通过 + 缓存停止无异常

### 5. BookHelp 互斥失效修复（B5）

- [ ] 5.1 修复 `BookHelp.kt:261-262`，调整 finally 块顺序：先 `mutex.unlock()` 后 `downloadImages.remove(src)`
- [ ] 5.2 编译验证 + 图片下载测试
  - Level 2 验证：图片下载并发场景无死锁

### 6. WebViewPool 池化修复（B6，借鉴阅读Archive）

- [ ] 6.1 修改 `WebViewPool.kt`，增加 `closed` 标志
- [ ] 6.2 增加 `isActiveWebView(webView: WebView? = null)` 方法（引用相等检查）
- [ ] 6.3 修改 `destroy()` 方法，增加 closed 和 callback 清理，重入安全
- [ ] 6.4 修改 `EvalJsRunnable.run`，检查改为 `isActiveWebView(mWebView.get())`
- [ ] 6.5 编写单元测试 `WebViewPoolTest`（验证引用相等检查）
  - Level 3 验证：批量 WebView 书源校验不出现数据串错

### 7. 307/308 重定向处理（C2，借鉴蛋蛋Max）

- [ ] 7.1 阅读 `OkHttpUtils.kt:29-43` 当前 `newCallResponse` 实现
- [ ] 7.2 借鉴蛋蛋Max 实现，增加 307/308 状态码处理
- [ ] 7.3 重定向时保持原 method 和 body
- [ ] 7.4 跟随 Location header
- [ ] 7.5 受 retry 次数限制
- [ ] 7.6 编写单元测试 `OkHttpUtilsTest`（覆盖 307/308 重定向场景）
  - Level 3 验证：307/308 重定向保持 POST body

**参考实现（蛋蛋Max）**：
```kotlin
if (response.code == 307 || response.code == 308) {
    response.header("Location")?.let { location ->
        val redirectRequest = currentRequest.newBuilder()
            .url(location)
            .method(currentRequest.method, currentRequest.body)  // 保持 method+body
            .headers(currentRequest.headers)
            .build()
        response.close()
        response = newCall(redirectRequest).await()
        if (response.isSuccessful) return response
        currentRequest = redirectRequest
    }
}
```

### 8. SSLContext 协议修正（P0-6）

- [ ] 8.1 修复 `SSLHelper.kt:57`，`SSLContext.getInstance("SSL")` → `getInstance("TLS")`
- [ ] 8.2 编译验证 + HTTPS 书源访问测试
  - Level 2 验证：HTTPS 书源访问正常

### 9. P0 功能借鉴 - 调试工具集（F-P0-1，借鉴蛋蛋Max）

- [ ] 9.1 新增 6 个调试工具 Activity：编码转换/HTTP 请求/curl 命令/ping/正则测试/时间戳转换
- [ ] 9.2 每个工具支持复制结果
- [ ] 9.3 入口在 `ui/main/MyFragment` 增加"调试工具"入口
- [ ] 9.4 端到端验证
  - Level 3 验证：6 个调试工具均可正常使用

### 10. P0 功能借鉴 - 备份选择器（F-P0-2，借鉴蛋蛋Max）

- [ ] 10.1 新增 `BackupController.kt`，实现 `/backupPreview` 接口
- [ ] 10.2 备份预览功能（6 大类：书籍/源/规则/语音/配置/其他）
- [ ] 10.3 分类聚合 + 可折叠详情
- [ ] 10.4 一键备份 ZIP
- [ ] 10.5 端到端验证
  - Level 3 验证：备份预览 + 一键备份功能可用

### 11. P0 功能借鉴 - Web 端备份管理（F-P0-3，借鉴蛋蛋Max）

- [ ] 11.1 移植 `src/views/BackupManager.vue`
- [ ] 11.2 移植 `src/router/backupRouter.ts`
- [ ] 11.3 移植 `src/pages/backup/{index.html,main.js}`
- [ ] 11.4 修改 `router/index.ts` 集成 backupRoutes
- [ ] 11.5 修改 `views/BookShelf.vue` 增加"数据备份"入口按钮
- [ ] 11.6 修改 `api/api.ts` 新增 `BackupItemInfo`/`BackupOverview` 类型 + `getBackupPreview()`/`getBackupUrl()` 方法
- [ ] 11.7 确认后端 `WebServer.kt` 已实现 `/backup` 和 `/backupPreview` 接口
- [ ] 11.8 端到端验证
  - Level 3 验证：Web 端一键备份功能可用

### 12. P0 阶段集成验证

- [ ] 12.1 运行全量单元测试
- [ ] 12.2 现有书源/RSS 源功能回归测试
- [ ] 12.3 编译通过，无新增警告
- [ ] 12.4 AOAdapt 日志汇总

---

## 二、P1 阶段：中风险性能优化 + 中等难度功能借鉴（谨慎实施）

### 13. CookieStore LRU 淘汰（A3）

- [ ] 13.1 **先核实**：读取 `CookieManager.kt:114-131` 的 `removeCookie(url, key)` 实现，确认是删除单个 key 还是整个 domain
- [ ] 13.2 修复 `CookieStore.kt:85-90`，随机删除改为优先删除 tracking Cookie（_ga/_gid/_gat/Hm_lvt_*/_hjid）
- [ ] 13.3 其次按 key 长度降序删除
- [ ] 13.4 不新增 lastAccessTime 字段，避免数据库迁移
- [ ] 13.5 编写单元测试 `CookieStoreTest`（覆盖大 Cookie 场景）
  - Level 3 验证：大 Cookie 站点登录态保持

### 14. proxyClientCache LRU 上限（A6）

- [ ] 14.1 修复 `HttpHelper.kt:25-27`，`proxyClientCache` 改用 `LinkedHashMap` + `removeEldestEntry`（上限 20）
- [ ] 14.2 加同步包装（`synchronized(proxyClientLock)`）
- [ ] 14.3 编译验证 + 代理书源访问测试
  - Level 2 验证：代理书源访问正常 + 长跑后 cache 不超过 20 个条目

### 15. BackstageWebView 复用回调错乱修复（A7，与 B6 协同）

- [ ] 15.1 修改 `BackstageWebView.kt:243-247`，增加 `closed` 标志和 `isActiveWebView(webView)` 方法
- [ ] 15.2 修改 `destroy()` 方法，增加 closed 和 callback 清理，重入安全
- [ ] 15.3 修改 `EvalJsRunnable.run`，改为 `isActiveWebView(mWebView.get())` 检查
- [ ] 15.4 编译验证 + 书源批量校验测试
  - Level 3 验证：批量 WebView 书源校验不出现数据串错

### 16. 连接池调优（C3）

- [ ] 16.1 修改 `HttpHelper.kt:51-127` okHttpClient 配置
- [ ] 16.2 添加 `.connectionPool(ConnectionPool(50, 5, TimeUnit.MINUTES))`
- [ ] 16.3 验证派生客户端（okHttpClientManga、proxyClient）继承新连接池
- [ ] 16.4 编译验证 + 多书源访问测试
  - Level 2 验证：多书源访问连接复用率提升

### 17. customIp LRU 上限（C5）

- [ ] 17.1 修改 `AnalyzeUrl.kt:773`，`customIp` 改用 `LruCache<String, String>(100)`
- [ ] 17.2 LruCache 自身线程安全，put 操作同步保护
- [ ] 17.3 编译验证 + DNS 缓存场景测试
  - Level 2 验证：长跑后 customIp 不超过 100 个条目

### 18. BackstageWebView runBlocking 修复（B1）

- [ ] 18.1 在 `SourceHelp.kt` 新增 `getCachedBookSource(key: String): BookSource?` 内存缓存方法
- [ ] 18.2 `SourceHelp.loadBookSource` 等方法同步写入缓存
- [ ] 18.3 修改 `BackstageWebView.kt:118`，先读缓存，未命中再 `runBlocking(IO)` 查询数据库
- [ ] 18.4 编译验证 + 书源调试场景测试
  - Level 2 验证：书源调试场景主线程阻塞减少

### 19. BottomWebViewDialog runBlocking 优化（B2）

- [ ] 19.1 优化 `BottomWebViewDialog.kt:819-821` `runBlocking` 内部逻辑
- [ ] 19.2 `getModifiedContentWithJs` 内部改用同步 OkHttp 请求避免线程切换
- [ ] 19.3 不改变 runBlocking 本身（shouldInterceptRequest 必须 synchronous）
- [ ] 19.4 编译验证 + RSS 阅读/源编辑预览测试
  - Level 2 验证：RSS 阅读/源编辑预览功能正常

### 20. 内存泄漏治理（C4）

- [ ] 20.1 修改 `OkHttpStreamFetcher.kt:56`，`failUrl` 改 `LruCache<String, Boolean>(200)`
- [ ] 20.2 在 `ConcurrentRateLimiter` 新增 `clearRecord(sourceUrl: String)` 方法
- [ ] 20.3 修改 `SourceHelp.kt` 删源逻辑，删源时调用 `ConcurrentRateLimiter.clearRecord(sourceUrl)`
- [ ] 20.4 修改 `AnalyzeRule.kt:79`，`stringRuleCache` 改 `LruCache<String, String>(64)`
- [ ] 20.5 编译验证 + 24 小时长跑测试
  - Level 3 验证：24 小时长跑后 5 处内存泄漏全部修复

### 21. P1 功能借鉴 - 自动任务系统（F-P1-1，借鉴阅读T）

- [ ] 21.1 新增 `data/entities/AutoTask.kt` + `data/dao/AutoTaskDao.kt`
- [ ] 21.2 新增 `service/AutoTaskService.kt`（AlarmManager 调度）
- [ ] 21.3 新增 `ui/autoTask/AutoTaskActivity.kt` 等 UI 文件（9 个）
- [ ] 21.4 支持 Cron 表达式定时任务
- [ ] 21.5 支持书源更新/订阅源更新/书架备份等任务类型
- [ ] 21.6 端到端验证
  - Level 3 验证：自动任务定时执行正确

### 22. P1 功能借鉴 - 高亮规则系统（F-P1-2，借鉴蛋蛋Max/阅读T）

- [ ] 22.1 新增 `data/entities/HighlightRule.kt`
- [ ] 22.2 新增 `ui/book/read/HighlightRule*.kt`（编辑/配置/预览/分组管理，9 个文件）
- [ ] 22.3 实现关键词/正则高亮匹配
- [ ] 22.4 实现多种高亮样式（背景色/前景色/下划线/波浪线/双下划线/虚线）
- [ ] 22.5 实现颜色选择器、字体选择
- [ ] 22.6 实现高亮规则分组管理
- [ ] 22.7 端到端验证
  - Level 3 验证：高亮规则匹配正确，样式生效

### 23. P1 功能借鉴 - 调试日志面板 + 浮球（F-P1-3，借鉴蛋蛋Max）

- [ ] 23.1 新增 `ui/debug/DebugFloatBall*.kt`（Overlay 窗口）
- [ ] 23.2 新增 `ui/debug/DebugLogPanel*.kt`（日志分类显示：ERROR/WARN/INFO/DEBUG）
- [ ] 23.3 实现流程日志（请求/响应链路）
- [ ] 23.4 端到端验证
  - Level 3 验证：调试浮球 + 日志面板功能可用

### 24. P1 功能借鉴 - 阅读热力图（F-P1-4，借鉴蛋蛋Max）

- [ ] 24.1 按日期统计阅读时长
- [ ] 24.2 新增 `ui/book/read/ReadingHeatmap*.kt`（热力图可视化，GitHub 风格）
- [ ] 24.3 端到端验证
  - Level 3 验证：阅读热力图显示正确

### 25. P1 功能借鉴 - 书籍想法/笔记系统（F-P1-5，借鉴 Jingshiro）

- [ ] 25.1 新增 `data/entities/BookThought.kt`
- [ ] 25.2 新增 `ui/thought/Thought*.kt`（7 个 UI 文件）
- [ ] 25.3 实现读书笔记功能
- [ ] 25.4 实现 Markdown 生成
- [ ] 25.5 实现 Obsidian 集成导出
- [ ] 25.6 端到端验证
  - Level 3 验证：书籍笔记 + Obsidian 导出功能可用

### 26. P1 阶段集成验证

- [ ] 26.1 运行全量单元测试
- [ ] 26.2 24 小时长跑测试（目标无 OOM，内存增长 ≤ 50MB）
- [ ] 26.3 内存泄漏检测（LeakCanary 无报错）
- [ ] 26.4 连接复用率验证
- [ ] 26.5 功能借鉴端到端验证（含真机测试）
- [ ] 26.6 AOAdapt 日志汇总

---

## 三、P2 阶段：高风险项评估 + 长期功能借鉴（评估后决定是否实施）

### 27. P2 优化点评估清单

- [ ] 27.1 评估 P2-1 retry 重试 IOException（**倾向不实施** - 主流版本都有意不重试，是生态设计选择）
- [ ] 27.2 评估 P2-2 Cronet 熔断器（自实现熔断需充分测试）
- [ ] 27.3 评估 P2-3 启用 Cronet 协程拦截器（协程版有 runBlocking 需先修复）
- [ ] 27.4 评估 P2-4 限流器 Mutex 化（锁结构变更风险高）
- [ ] 27.5 评估 P2-5 CacheBook 锁优化（@Synchronized 是稳定选择）

> P2 项不在本轮实施，完成 P0/P1 后单独评估每项，按收益/风险比排序。

### 28. P2 长期功能借鉴

- [ ] 28.1 评估 F-P2-1 AI 聊天框架（借鉴阅读NG/Rimchars/refgd，22+15+8 文件，三大 AI Provider 统一接口）
- [ ] 28.2 评估 F-P2-2 MCP 服务（借鉴阅读NG，7 文件，Legado 作为 MCP Server）
- [ ] 28.3 评估 F-P2-3 主题包管理器（借鉴蛋蛋Max/Rimchars）

> P2 功能借鉴需 3-6 个月，按价值/难度排序后单独 spec 实施。

---

## 四、P3 阶段：高风险项暂缓 + 长期功能借鉴（不在本轮实施）

### 29. P3 高风险优化暂缓清单

> **核心结论**：5 项高风险优化可能导致部分书源不可用，**强烈建议暂缓实施**。

- [ ] 29.1 ⏸️ A5 - ObsoleteUrlFactory 自定义证书失效修复（暂缓 - 修复后自签名证书书源不可用）
- [ ] 29.2 ⏸️ C1 - SOCKS5 隧道完整实现（暂缓 - 改动面大，风险高）
- [ ] 29.3 ⏸️ C6 - HttpLogInterceptor（暂缓 - 影响所有请求，需充分测试）
- [ ] 29.4 ⏸️ C7 - SSL 配置可选化（暂缓 - 默认不启用 unsafe SSL 后部分书源不可用）
- [ ] 29.5 ⏸️ C8 - NetworkLogInterceptor（暂缓 - 影响所有请求，需充分测试）

### 30. P3 长期功能借鉴

- [ ] 30.1 ⏸️ F-P3-1 Epub 独立渲染引擎（借鉴 Rimchars，5 文件，⭐⭐⭐⭐）
- [ ] 30.2 ⏸️ F-P3-2 阅读菜单自定义按钮（借鉴 Rimchars，4 文件，⭐⭐⭐，JS 注入）

> P3 项不在本轮实施，待 P0/P1/P2 完成后视情况评估。

---

## 五、文档同步与交付（强制）

### 31. 文档同步

- [ ] 31.1 更新 `docs/project-flow/architecture/network-layer.md`（连接池配置变化、307/308 重定向、CancellationException 守卫）
- [ ] 31.2 更新 `docs/project-flow/modules/service-layer.md`（缓存定期清理、自动任务系统）
- [ ] 31.3 更新 `docs/project-flow/quick-reference.md`（新增配置参数）
- [ ] 31.4 更新 `docs/INDEX.md`（spec 状态）
- [ ] 31.5 更新 `app/src/main/assets/updateLog.md`（用户可感知变更）
- [ ] 31.6 同步 `AGENTS.md`（延伸版本对比方法论子规范引用，已完成）

### 32. 最终验收

- [ ] 32.1 全量回归测试通过
- [ ] 32.2 编译通过，无新增警告
- [ ] 32.3 文档同步完成
- [ ] 32.4 updateLog.md 更新完成
- [ ] 32.5 临时文件清理（`docs/temp-analysis/` 可保留作为参考）
- [ ] 32.6 5 项高风险优化（P3）确认暂缓实施，不影响本轮稳定性

---

## AOAdapt 日志

> 每个任务完成后记录 Action / Observation / Adapt，遇问题时必须记录。

### 模板

```markdown
- [x] X.Y 任务名称 ✅ Level N - 简要说明
  - Action: [执行了什么操作]
  - Observation: [观察到了什么结果]
  - Adapt: [基于观察做了什么调整]
```

### 设计阶段 AOAdapt 日志

- [x] 设计方案第一次调整 ✅ Level 1 - 基于延伸版本对比大幅调整
  - Action: 对比 5 个主流延伸版本（喵公子/Sigma/阅读T/蛋蛋Max/阅读NG）的 OkHttpUtils.kt 和 HttpHelper.kt
  - Observation: 主流版本（喵公子/Sigma/阅读T/阅读NG）网络层与本项目完全一致；蛋蛋Max 增加了 307/308 重定向处理
  - Adapt: 大幅调整方案 - 移除 retry 重试 IOException（生态设计选择）、移除锁结构优化（主流版本都用 @Synchronized）、移除 Cronet 熔断器（高风险）；新增 307/308 重定向处理（借鉴蛋蛋Max）

- [x] 设计方案第二次调整 ✅ Level 1 - 基于深度分析扩展
  - Action: 启动 6 个深度分析子代理并行工作，覆盖 Cronet/HttpClient/多线程/WebView/延伸版本网络层/延伸版本前端 六大组件
  - Observation: 识别出 22 个优化点（9 低风险/8 中风险/5 高风险）+ 25 个缺失功能
  - Adapt: P0 扩展到 9 项低风险优化 + 3 项短平快功能借鉴；P1 扩展到 8 项中风险优化 + 5 项中等难度功能借鉴；P3 暂缓 5 项高风险优化 + 2 项长期功能借鉴

- [x] 设计方案第三次调整 ✅ Level 1 - 基于优化点影响分析 + 缺失功能分析
  - Action: 深度分析 22 个优化点对现有功能的影响 + 分析 25 个缺失功能的借鉴价值
  - Observation: 9 项低风险优化不会导致功能不可用；5 项高风险优化可能导致部分书源不可用；25 个缺失功能按价值/难度排序
  - Adapt: 固化延伸版本对比方法论为子规范文档；P0/P1/P2/P3 分阶段实施功能借鉴；高风险项全部暂缓

- [x] 设计方案第四次调整 ✅ Level 1 - 基于用户要求"完全可以参考借鉴引入到我们的项目中去"
  - Action: 整合 8 份深度分析文档结论，重写四文档（README.md / spec.md / design.md / tasks.md）
  - Observation: 用户明确要求分阶段借鉴延伸版本功能
  - Adapt: tasks.md 第四版对齐 spec.md / design.md 第四版，按 P0(9优化+3功能)/P1(8优化+5功能)/P2(评估+3功能)/P3(5暂缓+2功能) 分阶段实施

---

## 完成级别说明

| 级别 | 含义 | 标记 |
|------|------|------|
| Level 1 - 代码完成 | 文件存在 + 编译通过 | ⚠️ |
| Level 2 - 功能验证 | 关键功能可运行 + 输出正确 | ⚠️ |
| Level 3 - 场景验证 | 真实数据回测通过 | ✅ |

**规则**：
- 任务标记格式：`- [x] X.Y ✅ Level 3 - 简要说明`
- 未达 Level 3 的任务必须注明缺失项
- 核心变更必须达到 Level 3 才能视为完成

---

## 风险提示

### 高风险项暂缓实施（P3）

> **5 项高风险优化可能导致部分书源不可用，强烈建议暂缓实施。**

| 编号 | 暂缓理由 |
|------|---------|
| A5 | 修复后传入自定义 TrustManager 不信任自签名证书，会导致 SSL 握手失败 → 书源不可用 |
| C1 | 阅读T 独有的协议级实现，改动面大，风险高 |
| C6 | 阅读T 独有，影响所有请求，需充分测试 |
| C7 | 默认不启用 unsafe SSL 后部分自签证书网站将无法访问 |
| C8 | 阅读NG 独有，影响所有请求，需充分测试 |

### 回滚策略

- 每个修复点独立提交，便于单独回滚
- P0 / P1 阶段分别合并，P1 出问题可回滚至 P0 完成状态
- 保留原实现作为注释参考（仅关键变更点）
