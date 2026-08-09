# spec.md — 书源/订阅源架构机制层互补（V2）

> V2 版本：基于用户反馈"要的是相互机制的互补，不期望相互添加字段"重新设计。
> V1 版本（增量字段借鉴）已推翻。

## Intent（意图）

Legado 项目中 BookSource 与 RssSource 在长期演化中各自形成了独特**机制**：
- **BookSource 机制层**：5 步网络流程（search/explore/info/chapter/content）+ `concurrentRate`+`Semaphore` 并发控制 + 结构化规则对象（SearchRule/BookInfoRule/TocRule/ContentRule）+ `preciseSearch` 精准搜索 + `preUpdateJs` 预执行 JS
- **RssSource 机制层**：2 步网络流程（getArticles/getContent）+ `parseConcurrency` 字段（未落地）+ 扁平 String 规则 + WebView 精细控制（singleUrl/injectJs/shouldOverrideUrlLoading 等）+ `contentWhitelist`/`contentBlacklist` URL 过滤 + `preload`/`cacheFirst` 缓存策略 + F-P1-F 预连接机制 + 多线路多集按需采集

**两类源在机制层存在显著重复与互补**：
- WebBook.kt 中 4 处重复的 `runCatching + checkJs + getErrStrResponse` 网络请求模式，Rss.kt 中 2 处相同模式 → 应抽取统一网络客户端
- BookSource 有并发控制（`Semaphore`），RssSource 有 `parseConcurrency` 字段但未落地 → 应统一并发控制
- RssSource 有 URL 黑白名单，BookSource 无 → 应统一过滤机制（BookSource 用 AppConfig 全局配置，不增实体字段）
- RssSource 有预连接机制，BookSource 无 → 应抽取统一预连接工具

本 spec 旨在**抽取 6 个共享机制组件**，让两类源共享同一套工程能力，实现真正的机制互补，**零实体字段增加、零数据库迁移**。

## Scope（范围）

### 做什么
1. 深入对比两类源在 8 个维度（数据模型/网络层/规则引擎/并发缓存/UI/调试/导入导出/扩展能力）的**机制层**差异
2. 抽取 6 个共享机制组件：
   - **M1 SourceConcurrencyController**：统一并发控制
   - **M2 SourceContentFilter**：统一正文 URL 过滤
   - **M3 SourceCacheManager**：统一缓存策略
   - **M4 SourcePreconnectHelper**：统一预连接
   - **M5 SourceWebViewController**：统一 WebView 控制
   - **M6 SourceNetworkClient**：统一网络请求
3. 重构 WebBook.kt 中 4 处重复网络请求模式，调用 M6
4. 重构 Rss.kt 中 2 处重复网络请求模式，调用 M6
5. RssSource.parseConcurrency 字段通过 M1 实际落地
6. BookSource 通过 M2/M3/M4/M5 获得 RssSource 的过滤/缓存/预连接/WebView 控制能力（用 AppConfig 全局配置，不增实体字段）

### 不做什么
- ❌ 不增加 BookSource/RssSource 任何实体字段
- ❌ 不修改数据库 schema（无需 v89→v90 迁移）
- ❌ 不修改现有字段语义
- ❌ 不重写 AnalyzeRule 核心规则引擎
- ❌ 不合并 BookSource 与 RssSource 为统一实体
- ❌ 不修改 WebBook/Rss 网络层主体流程（仅替换重复模式为组件调用）
- ❌ 不修改现有 JSON 协议

### 边界条件
- 现有源 JSON 不变：所有现有字段语义保持
- 现有调用点：WebBook.kt 4 处 + Rss.kt 2 处网络请求重构后行为等同
- AppConfig 全局配置：新增配置项有默认值，默认值使行为等同改造前
- 并发场景：M1 SourceConcurrencyController 单例需线程安全（`@Synchronized` 或 `Mutex`）
- 异常情况：组件调用失败时降级到原 WebBook/Rss 直接调用，不抛异常中断主流程
- 兼容性：M6 SourceNetworkClient 必须支持 `loginCheckJs`/`checkRedirect`/`SourceLastHostHelper.fillBack` 全部现有流程

## Approach（方案）

### Selected Approach（选定方案）

**机制层抽取 + 共享组件复用**：抽取 6 个共享机制组件，让 BookSource 和 RssSource 都通过组件接口获得对方优点，**零实体字段增加**。

理由：
1. **真正机制互补**：抽取共享组件，而非字段复制
2. **零字段增加**：不增加实体字段，避免数据库迁移
3. **代码复用**：减少 WebBook/Rss 重复逻辑（6 处网络请求模式统一）
4. **可扩展**：未来新源类型可直接复用机制组件
5. **符合用户期望**：关注机制层而非表层字段

### Alternatives Considered（否决的替代方案）

| 方案 | 描述 | 否决理由 |
|------|------|----------|
| V1 增量字段借鉴 | 在两类源实体上互相新增字段 | **用户明确拒绝**："不期望相互添加字段" |
| 方案 B | 合并 BookSource 和 RssSource 为统一 Source 实体 | 破坏性变更巨大，影响 21 实体+21 DAO+大量 UI，JSON 协议不兼容 |
| 方案 C | 抽象 BaseSource 通用接口让两者完全统一字段 | BaseSource 已存在但仅含通用字段，强行统一业务字段会破坏语义边界 |
| 方案 D | 保留差异，仅做文档对比不实施借鉴 | 无法落地价值，用户痛点不解决 |
| 方案 E | 重写两类源为统一 Source 抽象层+插件化业务层 | 工程量超 100 文件，超出"机制互补"范围 |
| 方案 F | 仅在 WebBook/Rss 内部各自重构不抽组件 | 错失机制互补机会，重复代码仍存在 |
| 方案 G | 抽取所有 6 个组件一次性实施 | 风险高，应分批抽取验证 |

### Drawbacks（选定方案的已知缺点）

| 缺点 | 接受理由 |
|------|----------|
| D1：6 个组件接口设计需要仔细考虑兼容性 | 接口设计遵循"最小化+向后兼容"原则，参考现有实现 |
| D2：现有调用点需要重构（WebBook.kt 4 处 + Rss.kt 2 处） | 重构后行为等同，每个调用点独立验证 |
| D3：AppConfig 全局配置需要新增条目（非实体字段） | AppConfig 已有大量全局配置先例，新增条目无迁移成本 |
| D4：机制抽取可能引入回归风险 | 分批抽取（M6→M1→M4→M2→M3→M5），每批独立 L2 真机验证 |
| D5：M5 SourceWebViewController 需要适配两类源差异 | 接口设计支持 source 类型判断，RssSource 用自身字段，BookSource 用全局配置 |
| D6：抽取后调试可能变复杂（调用链变长） | 组件接口日志完善，AppLog 记录调用链 |

### Prior Art（参考的类似工作）
- `BaseSource` 接口已有通用字段抽象（header/loginUrl/concurrentRate 等），证明机制抽取可行
- `SourceLastHostHelper` 已是共享工具（WebBook/Rss 都调用），证明跨实体工具抽取模式可行
- `warmUpConnection`（在 Rss.kt 中）已是工具函数，证明预连接机制可抽取
- `AppConfig` 已有 `bookSourceJobTimeout`/`concurrentSyncBook` 等全局配置先例

## Requirements（需求）

### R1：零字段增加与零数据库迁移（P0 必须满足）
- R1.1：不修改 BookSource/RssSource 任何实体字段定义
- R1.2：不修改 AppDatabase.kt 数据库版本（保持 v89）
- R1.3：不修改现有 JSON 协议
- R1.4：现有源 JSON 导入行为等同改造前

### R2：M1 SourceConcurrencyController（统一并发控制）
- R2.1：新增 `app/src/main/java/io/legado/app/help/source/SourceConcurrencyController.kt` 单例
- R2.2：提供 `suspend fun <T> withConcurrency(source: BaseSource, action: suspend () -> T): T` 接口
- R2.3：内部根据 source 类型读取 `concurrentRate`（BookSource）或 `parseConcurrency`（RssSource）
- R2.4：RssSource.parseConcurrency 字段通过此组件实际落地（修复现有未落地 BUG）
- R2.5：BookSource 的 `concurrentRate` 解析逻辑统一到此组件
- R2.6：线程安全：`@Synchronized` 保护 Semaphore 缓存

### R3：M2 SourceContentFilter（统一WebView资源过滤）
- R3.1：新增 `app/src/main/java/io/legado/app/help/source/SourceContentFilter.kt` 工具对象
- R3.2：提供 `fun filterUrl(url: String, source: BaseSource): Boolean` 接口（true=允许，false=过滤）
- R3.3：RssSource 调用时使用自身 `contentWhitelist`/`contentBlacklist` 字段
- R3.4：BookSource 调用时使用 `AppConfig.bookSourceContentBlacklist`/`AppConfig.bookSourceContentWhitelist` 全局配置
- R3.5：AppConfig 新增两个全局配置项（默认空=不过滤）
- R3.6：ReadRssActivity.kt shouldInterceptRequest 调用 `SourceContentFilter.filterUrl` 替换内联过滤
- R3.7：BottomWebViewDialog.kt shouldInterceptRequest 新增 `SourceContentFilter.filterUrl` 调用（BookSource 视频源 WebView 获得过滤能力）

### R4：M3 SourceCacheManager（统一WebView缓存策略）
- R4.1：新增 `app/src/main/java/io/legado/app/help/source/SourceCacheManager.kt` 单例
- R4.2：提供 `fun isCacheFirst(source: BaseSource): Boolean` 接口
- R4.3：RssSource 调用时使用自身 `cacheFirst` 字段
- R4.4：BookSource 调用时使用 `AppConfig.bookSourceCacheFirst` 全局配置（默认 false=沿用现有行为）
- R4.5：ReadRssActivity.kt WebView 设置调用 `SourceCacheManager.isCacheFirst` 替换内联判断
- R4.6：BottomWebViewDialog.kt WebView 设置新增 `SourceCacheManager.isCacheFirst` 默认值（BookSource 视频源 WebView 获得缓存优先能力）

### R5：M4 SourcePreconnectHelper（统一预连接）
- R5.1：新增 `app/src/main/java/io/legado/app/help/source/SourcePreconnectHelper.kt` 工具对象
- R5.2：抽取 Rss.kt 中 F-P1-F 预连接实现到此工具
- R5.3：提供 `suspend fun preconnectTopN(urls: List<String>, n: Int = 3)` 接口
- R5.4：Rss.kt 调用此工具（替换原内联实现）
- R5.5：BookChapterList.analyzeChapterList 加载完成后调用此工具预连接前 3 章
- R5.6：失败不影响主流程（kotlin.runCatching 包裹）

### R6：M5 SourceWebViewController（统一WebView控制）
- R6.1：新增 `app/src/main/java/io/legado/app/help/source/SourceWebViewController.kt` 工具对象
- R6.2：提供 `fun applyConfig(webView: WebView, source: BaseSource)` 接口
- R6.3：RssSource 调用时使用自身 `singleUrl`/`injectJs`/`preloadJs`/`shouldOverrideUrlLoading`/`enableJs`/`loadWithBaseUrl`/`showWebLog`/`style` 字段
- R6.4：BookSource 视频源（type=4）调用时使用 `AppConfig.bookSourceInjectJs`/`AppConfig.bookSourceEnableJs` 全局配置
- R6.5：现有 RssSource WebView 调用点替换为组件调用

### R7：M6 SourceNetworkClient（统一网络请求）
- R7.1：新增 `app/src/main/java/io/legado/app/help/source/SourceNetworkClient.kt` 单例
- R7.2：提供 `suspend fun requestWithLoginCheck(analyzeUrl: AnalyzeUrl, source: BaseSource, checkJs: String?): StrResponse` 接口
- R7.3：内部封装 `runCatching + getStrResponseAwait + checkJs + getErrStrResponse + checkRedirect + SourceLastHostHelper.fillBack` 完整流程
- R7.4：WebBook.kt 4 处重复模式（searchBook/exploreBook/getBookInfo/getChapterList/getContent）替换为组件调用
- R7.5：Rss.kt 2 处重复模式（getArticles/getContent）替换为组件调用
- R7.6：行为等同改造前（包括 CancellationException 守卫）

### R8：调试与可观测性（P1）
- R8.1：每个组件调用点增加 AppLog 日志（tag: `TAG_SOURCE_MECHANISM`）
- R8.2：BookSourceDebugActivity 增加并发控制/URL 过滤/缓存策略调试输出
- R8.3：RssSourceDebugActivity 增加 parseConcurrency 落地情况调试输出

### R9：文档同步（P0）
- R9.1：更新 `docs/project-flow/modules/webbook-search.md` 方法表（标注 M6 调用）
- R9.2：更新 `docs/project-flow/modules/rss-subsystem.md` 订阅源模块（标注 M1/M4/M6 调用）
- R9.3：新增 `docs/project-flow/architecture/source-mechanism-components.md` 6 个组件文档
- R9.4：更新 `docs/INDEX.md` 状态
- R9.5：更新 `app/src/main/assets/updateLog.md`

## Scenarios（场景）

### S1：M6 网络请求统一重构兼容
**前置**：WebBook.kt 中 searchBookAwait 原有 4 处 runCatching+checkJs 模式
**步骤**：
1. 替换为 `SourceNetworkClient.requestWithLoginCheck(analyzeUrl, bookSource, checkJs)` 调用
2. 执行搜索请求
3. 验证响应与改造前一致
**预期**：行为等同改造前，包括 CancellationException 守卫、checkJs 失败重试、checkRedirect 日志

### S2：M1 RssSource.parseConcurrency 落地
**前置**：订阅源 `parseConcurrency = 4`（已存在字段，原未落地）
**步骤**：
1. 用户触发多文章并行解析
2. Rss.kt 调用 `SourceConcurrencyController.withConcurrency(rssSource)` 包裹解析
3. Semaphore(4) 限制并发
4. 第 5 个解析等待
**预期**：CPU/内存可控，无 OOM，parseConcurrency 字段实际生效

### S3：M2 BookSource 正文 URL 过滤
**前置**：用户在 AppConfig 配置 `bookSourceContentBlacklist = "ad.*,popup.*"`
**步骤**：
1. 用户访问书源正文
2. BookContent.kt 调用 `SourceContentFilter.filterUrl(url, bookSource)`
3. URL 命中黑名单正则返回 false
4. 系统 skip 该 URL，加载下一章节
**预期**：广告/弹窗 URL 被过滤，正文正常加载，**BookSource 实体无字段增加**

### S4：M4 BookSource 章节预连接
**前置**：用户打开书源目录页
**步骤**：
1. BookChapterList.analyzeChapterList 加载完成
2. 调用 `SourcePreconnectHelper.preconnectTopN(chapterUrls, 3)`
3. 并行 HEAD 预连接前 3 章域名
4. 用户点击第 1 章
**预期**：点击响应时间减少 300-1000ms，**BookSource 实体无字段增加**

### S5：M5 BookSource 视频源 WebView 控制
**前置**：用户在 AppConfig 配置 `bookSourceInjectJs = "..."`
**步骤**：
1. 用户访问书源视频源（type=4）
2. WebView 创建时调用 `SourceWebViewController.applyConfig(webView, bookSource)`
3. 注入 JS 脚本
**预期**：JS 注入生效，**BookSource 实体无字段增加**

### S6：M3 BookSource 正文缓存优先
**前置**：用户在 AppConfig 配置 `bookSourceCacheFirst = true`
**步骤**：
1. 用户访问书源正文
2. BookContent.kt 调用 `SourceCacheManager.isCacheFirst(bookSource)` 返回 true
3. 优先读缓存，缓存命中时不发网络请求
**预期**：缓存命中时秒开，**BookSource 实体无字段增加**

### S7：现有源 JSON 兼容
**前置**：用户有改造前的 BookSource/RssSource JSON 备份
**步骤**：
1. 导入旧 JSON
2. 系统解析 JSON，所有现有字段语义保持
3. 数据库写入成功（v89 schema 不变）
4. 源可用，行为等同改造前
**预期**：零字段增加，零迁移，完全兼容
