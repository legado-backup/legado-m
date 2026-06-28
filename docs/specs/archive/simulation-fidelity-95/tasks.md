# Tasks: JAR 仿真端 100% 测试校验准确性

> **格式说明**：`- [ ] X.Y` 未完成 / `- [x] X.Y ✅ YYYY-MM-DD` 已完成
> **强制规则**：每个任务有源码行号引用 + 验证方法
> **更新日期**：2026-06-21（第七轮深度审查修正：设计目标从"100%兼容运行"修正为"100%测试校验准确性"，砍掉75个过度修复项，重新设计10个GAP的修复方案）

---

## 方向 0：已完成修复（历史记录）

> 以下任务在前一轮已完成，保留作为历史记录。

- [x] 0.1 icu4j 编码检测移植 ✅ 2026-06-21
- [x] 0.2 SSL/cookieJar/限流补全 ✅ 2026-06-21
- [x] 0.3 htmlFormat 实现 ✅ 2026-06-21
- [x] 0.4 繁简转换实现 ✅ 2026-06-21
- [x] 0.5 BaseSource.evalJS 补全 ✅ 2026-06-21
- [x] 0.6 getHeaderMap @js: 支持 ✅ 2026-06-21
- [x] 0.7 login 方法实现 ✅ 2026-06-21
- [x] 0.8 登录信息管理方法 ✅ 2026-06-21
- [x] 0.9 发现页调试实现 ✅ 2026-06-21
- [x] 0.10 setVariable/getVariable 签名修正 ✅ 2026-06-21
- [x] 0.11 OkHttpUtils.text() 编码检测 ✅ 2026-06-21
- [x] 0.12 nextChapterUrl/tocUrl/isWebFile/isVolume 修复 ✅ 2026-06-21

---

## 方向 1：低难度方法修复（12 个，P0）

> **目标**：修复 12 个低难度不兼容方法
> **源码依据**：`BaseSource.kt` / `JsExtensions.kt` / `JsEncodeUtils.kt`

### 1.1 属性 var→val 签名修正（6 个）

- [ ] 1.1.1 阅读 `BaseSource.kt` 确认 concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib 均为 var
- [ ] 1.1.2 修改 `BaseSourceInterface.kt`：6 个属性 val→var
- [ ] 1.1.3 验证：编译通过 + 签名与真机一致

### 1.2 其他低难度修复（6 个）

- [ ] 1.2.1 dateFormat：读取 `LEGADO_DATE_FORMAT` 环境变量，默认 `"yyyy/MM/dd HH:mm"`（对齐真机 `AppConst.kt:38-40`）
- [ ] 1.2.2 connect：catch 块中 url 改用 `analyzeUrl.url`
- [ ] 1.2.3 getTxtInFolder：添加 `folder.delete()`
- [ ] 1.2.4 importScript：`IllegalStateException` → `NoStackTraceException`
- [ ] 1.2.5 aesEncodeToString：反向引入真机 bug（decryptStr）
- [ ] 1.2.6 验证：编译通过 + 行为与真机一致

---

## 方向 2：中难度方法修复（18 个，P0）

> **目标**：修复 18 个中难度不兼容方法
> **源码依据**：`JsExtensions.kt` / `JsEncodeUtils.kt` / `BaseSource.kt`

### 2.1 base64/AES flags 映射完善（6 个）

- [ ] 2.1.1 阅读 `JsEncodeUtils.kt` 确认 android.util.Base64 flags 值
- [ ] 2.1.2 实现 `mapBase64Flags(flags)` 映射函数
- [ ] 2.1.3 修改 base64Decode/base64DecodeToByteArray/base64Encode
- [ ] 2.1.4 修改 aesDecodeArgsBase64Str/tripleDESEncodeArgsBase64Str/tripleDESDecodeArgsBase64Str
- [ ] 2.1.5 修改 digestBase64Str/HMacBase64
- [ ] 2.1.6 验证：编解码结果与 android.util.Base64 一致

### 2.2 HTTP 方法对齐（3 个）

- [ ] 2.2.1 确认 get/head/post 的 SSLHelper/cookieJarHeader/ConcurrentRateLimiter 已注入
- [ ] 2.2.2 确认 followRedirects(false) 已设置
- [ ] 2.2.3 验证：自签名证书网站可访问 + cookieJar 启用的源 header 正确

### 2.3 并发请求实现（2 个）

- [ ] 2.3.1 ajaxAll：使用 CompletableFuture + 线程池
- [ ] 2.3.2 ajaxTestAll：同上
- [ ] 2.3.3 验证：并发请求正确返回

### 2.4 其他中难度修复（7 个）

- [ ] 2.4.1 downloadFile：改用 OkHttp 流式下载 + 修正路径计算
- [ ] 2.4.2 toNumChapter：移植 AppPattern + StringUtils
- [ ] 2.4.3 log：接入 Debug 回调，写入日志文件
- [ ] 2.4.4 putConcurrent：实现 updateConcurrentRate
- [ ] 2.4.5 executeSortUrlJs：注入 source 变量
- [ ] 2.4.6 evalJS：实现 sharedScope（SharedJsScope）
- [ ] 2.4.7 验证：所有方法行为与真机一致

---

## 方向 3：高难度方法修复（16个→8个，第七轮修正：砍掉8个过度修复）

> **目标**：修复高难度不兼容方法（第七轮修正：原16个中8个标注为过度修复/延后/重新设计）
> **源码依据**：`ArchiveUtils.kt` / `ReadBookConfig.kt` / `ThemeConfig.kt` / `SharedJsScope.kt`

### 3.1 ~~压缩文件解压（4 个）~~ ❌ 延后（第七轮修正）

> **移除理由**：方向5延后，100个失败源中0个压缩文件相关。遇到实际需求再做。

- ~~3.1.1 在 `build.gradle.kts` 添加 `commons-compress` 依赖~~
- ~~3.1.2 移植 `ArchiveUtils.kt`~~
- ~~3.1.3 实现 unArchiveFile/unzipFile/un7zFile/unrarFile~~
- ~~3.1.4 验证：zip/7z/rar 文件正确解压~~

### 3.2 ~~Rar/7z 内容读取（4 个）~~ ❌ 延后（第七轮修正）

> **移除理由**：同3.1，方向5延后。

- ~~3.2.1 用 Apache Commons Compress 替代 LibArchiveUtils~~
- ~~3.2.2 实现 getRarByteArrayContent/get7zByteArrayContent~~
- ~~3.2.3 实现 getRarStringContent/get7zStringContent（含编码检测）~~
- ~~3.2.4 验证：Rar/7z 文件内容正确读取~~

### 3.3 ~~配置读取（4 个）~~ 🔄 重新设计（第七轮修正）

> **重新设计方案**：只补充userAgent + customHosts到AppConfig，不移植ReadBookConfig/ThemeConfig。

- ~~3.3.1 移植 ReadBookConfig（用 JSON 文件替代 SharedPreferences）~~
- ~~3.3.2 移植 ThemeConfig（用 JSON 文件替代）~~
- ~~3.3.3 实现 getReadBookConfig/getReadBookConfigMap/getThemeConfig/getThemeConfigMap~~
- ~~3.3.4 验证：配置正确读取~~
- **新方案**：在AppConfig中补充userAgent（读取LEGADO_USER_AGENT环境变量）+ customHosts（读取LEGADO_CUSTOM_HOSTS环境变量）

### 3.4 其他高难度修复（4个→3个，第七轮修正：refreshExplore标注为过度修复）

- ~~3.4.1 refreshExplore：实现 clearExploreKindsCache~~ ❌ 过度修复（exploreKinds不影响校验）
- [ ] 3.4.2 refreshJSLib：实现 SharedJsScope.remove
- [ ] 3.4.3 getLoginInfoMap：移植 RowUi 解析逻辑
- [ ] 3.4.4 debugExplore：实现 exploreInfoMapList 解析
- [ ] 3.4.5 验证：所有保留的方法行为与真机一致

---

## 方向 4：委托路径实现（21 个，P1）

> **目标**：实现 21 个不可实现方法的委托路径
> **源码依据**：`BackstageWebView.kt` / `SourceVerificationHelp.kt`

### 4.1 WebView 渲染委托（9 个）

- [ ] 4.1.1 WebViewRequiredException 携带完整请求信息（url/html/js/cacheFirst）
- [ ] 4.1.2 Python 端实现 `webview_delegate.py`（Selenium 执行 JS 渲染）
- [ ] 4.1.3 实现结果回传机制（HTTP API）
- [ ] 4.1.4 验证：需 WebView 渲染的源可调试

### 4.2 UI 交互委托（5 个）

- [ ] 4.2.1 startBrowser → Selenium 浏览器自动化
- [ ] 4.2.2 startBrowserAwait → Selenium + 等待
- [ ] 4.2.3 getVerificationCode → OCR + 用户介入
- [ ] 4.2.4 openVideoPlayer/openUrl → 标记不影响验证
- [ ] 4.2.5 验证：需要登录的源可调试

### 4.3 硬件信息环境变量配置（4 个）

- [ ] 4.3.1 LEGADO_ANDROID_ID 环境变量注入
- [ ] 4.3.2 LEGADO_WEBVIEW_UA 环境变量注入
- [ ] 4.3.3 getLoginInfo/putLoginInfo 依赖 androidId 修复
- [ ] 4.3.4 验证：AES 加密解密与真机一致

### 4.4 Toast 日志文件替代（2 个）

- [ ] 4.4.1 toast/longToast → 写入日志文件
- [ ] 4.4.2 验证：日志文件正确记录

### 4.5 Debugger WebView 委托（1 个）

- [ ] 4.5.1 debugContent useWebView → 依赖 Selenium 委托
- [ ] 4.5.2 验证：需 WebView 渲染正文的源可调试

---

## 方向 5：仿真端已知问题修复（2 个，P0）

> **目标**：修复批量测试发现的 2 个仿真端问题
> **源码依据**：`SSLHelper.kt` / `OkHttpUtils.kt`

### 5.1 BT之家 PKIX 证书链修复

- [ ] 5.1.1 确认 SSLHelper 已配置信任所有证书
- [ ] 5.1.2 确认 AnalyzeUrl 的 OkHttpClient 注入了 SSLHelper
- [ ] 5.1.3 验证：BT之家可访问

### 5.2 阳光电影 DNS 修复

- [ ] 5.2.1 配置 OkHttp 公共 DNS 回退（223.5.5.5）
- [ ] 5.2.2 验证：阳光电影 DNS 解析正确

---

## 方向 8：OkHttpUtils 方法补全（3个，P1）

> **目标**：补充仿真端 OkHttpUtils 缺失的 3 个方法
> **源码依据**：真机 `OkHttpUtils.kt:45-50,61-77,97-111`

### 8.1 newCallResponseBody 补充

- [ ] 8.1.1 阅读真机 `OkHttpUtils.kt:45-50` 确认 newCallResponseBody 实现
- [ ] 8.1.2 在仿真端 `OkHttpUtils.kt` 补充该方法（返回 `newCallResponse(retry, builder).body`）
- [ ] 8.1.3 验证：下载文件/获取图片正常

### 8.2 decompressed 补充

- [ ] 8.2.1 阅读真机 `OkHttpUtils.kt:97-111` 确认 decompressed 实现
- [ ] 8.2.2 在仿真端补充该方法及 import（ZipInputStream/okio）
- [ ] 8.2.3 验证：application/zip 响应可正确解压

### 8.3 await 协程取消补充

- [ ] 8.3.1 阅读真机 `OkHttpUtils.kt:61-77` 确认 invokeOnCancellation 实现
- [ ] 8.3.2 在仿真端 `await` 方法中补充 `cont.invokeOnCancellation { cancel() }`
- [ ] 8.3.3 调整回调顺序与真机一致（onFailure 在前）
- [ ] 8.3.4 验证：协程取消时底层 OkHttp 请求也取消

---

## 方向 9：RssSourceDebugger 逻辑修正（5个，P0-P2）

> **目标**：修正 RssSourceDebugger 与真机 Debug.kt 的 5 处逻辑差异
> **源码依据**：真机 `Debug.kt:111-184,24,78-85,87-109`

### 9.1 GAP-22 ruleDescription 逻辑修正（P0 最高优先级）

- [ ] 9.1.1 阅读真机 `Debug.kt:123-134` 确认 ruleDescription 逻辑（有值时跳过内容页）
- [ ] 9.1.2 修改 `RssSourceDebugger.kt:295-296`：添加 ruleDescription 判断逻辑
- [ ] 9.1.3 验证：ruleDescription 有值时不请求内容页，输出"存在描述规则，不解析内容页"

### 9.2 GAP-23 key::url 调试入口

- [ ] 9.2.1 阅读真机 `Debug.kt:142-184` 确认三种 key 格式分发逻辑
- [ ] 9.2.2 在 `debug()` 方法中增加 `key.contains("::")` 分支和搜索关键字分支
- [ ] 9.2.3 验证：key::url 格式和搜索关键字可正常调试

### 9.3 GAP-24 取消机制

- [ ] 9.3.1 阅读真机 `Debug.kt:24,78-85` 确认 CompositeCoroutine 实现
- [ ] 9.3.2 为 RssSourceDebugger 添加 CoroutineScope 参数和 cancel() 方法
- [ ] 9.3.3 验证：长时间调试任务可被中断

### 9.4 GAP-25 校验模式

- [ ] 9.4.1 阅读真机 `Debug.kt:27,87-109` 确认 CheckSource 集成逻辑
- [ ] 9.4.2 添加 isChecking 状态标志、记录响应时间、输出校验结果摘要
- [ ] 9.4.3 验证：批量校验可用

### 9.5 GAP-26 无参 key 入口

- [ ] 9.5.1 阅读真机 `Debug.kt:111-140` 确认无 key 重载实现
- [ ] 9.5.2 将 key 改为可选参数（`key: String? = null`），无 key 时调试第一个分类
- [ ] 9.5.3 验证：无 key 时默认调试第一个分类

---

## 方向 10：持久化实现（5个→2个保留，第七轮修正：3个标注为过度修复）

> **目标**：修正仿真端持久化层与真机的差异（第七轮修正：持久化不影响单次校验结果，砍掉3个过度修复）
> **源码依据**：真机 `CookieStore.kt`/`CookieManager.kt`/`CacheManager.kt`/`JsExtensions.kt:701-714`

### 10.1 ~~GAP-31 CookieStore 持久化~~ ❌ 过度修复（第七轮修正）

> **移除理由**：重启后Cookie丢失不影响单次校验结果。校验期间Cookie保存在内存即可。

- ~~10.1.1 阅读真机 `CookieStore.kt:30` 确认 Room SQLite 持久化逻辑~~
- ~~10.1.2 仿真端接入 JSON 文件持久化（路径 `~/.legado/cookies.json`）~~
- ~~10.1.3 验证：重启后 Cookie 不丢失~~

### 10.2 GAP-32 CookieManager 补充 saveResponse（🔄 改为内存Map实现）

- [ ] 10.2.1 阅读真机 `CookieManager.kt:29-50` 确认 saveResponse 实现
- [ ] 10.2.2 在 CookieManagerStub 中补充 saveResponse（从 Response headers 解析 Cookie 并保存到内存Map）
- [ ] 10.2.3 补充 loadRequest（从内存Map加载 Cookie 到请求头）
- [ ] 10.2.4 验证：HTTP 响应的 Set-Cookie 自动保存，后续请求自动携带（单次校验期间有效）

### 10.3 ~~GAP-33 CacheManager 持久化~~ ❌ 过度修复（第七轮修正）

> **移除理由**：同10.1，缓存重启丢失不影响单次校验结果。

- ~~10.3.1 阅读真机 `CacheManager.kt:62,67` 确认三层缓存逻辑~~
- ~~10.3.2 仿真端接入文件系统持久化（路径 `~/.legado/cache/`）~~
- ~~10.3.3 验证：重启后缓存不丢失~~

### 10.4 GAP-34 getFile 描述修正（误报，保留）

- [ ] 10.4.1 确认仿真端 `JsExtensionsStub.kt:453-465` 有完整文件操作
- [ ] 10.4.2 修正 GAP 描述为"根目录不同（tmpdir vs externalCache），行为等价"
- [ ] 10.4.3 验证：无需代码修改

### 10.5 GAP-35 WebCookie 描述修正（保留）

- [ ] 10.5.1 确认仿真端 `CookieStoreStub.kt:21` 用 ConcurrentHashMap 替代 android.webkit.CookieManager
- [ ] 10.5.2 修正 GAP 描述为"使用内存 Map 替代，无法同步到 WebView（JVM 限制，可接受）"
- [ ] 10.5.3 验证：无需代码修改

---

## 方向 11：新发现遗漏修复（4个，P2-P4）

> **目标**：修复源码核实发现的 4 个新遗漏
> **源码依据**：真机 `Debug.kt`/`OkHttpUtils.kt`/`AnalyzeUrl.kt`

### 11.1 新-1 Debug.kt 状态管理补充

- [ ] 11.1.1 阅读真机 `Debug.kt` 全文（362行）确认状态管理逻辑
- [ ] 11.1.2 仿真端 Debug.kt 补充 debugMessageMap/debugTimeMap/isChecking 状态管理
- [ ] 11.1.3 保留 log 回调机制
- [ ] 11.1.4 验证：Debug 状态依赖代码行为正常

### 11.2 新-2 await 回调顺序对齐

- [ ] 11.2.1 调整仿真端 `OkHttpUtils.kt:55-63` 回调顺序（onFailure 在前）
- [ ] 11.2.2 验证：无功能影响，符合精准对齐原则

### 11.3 新-3 AnalyzeUrl 标记不实现

- [ ] 11.3.1 确认 getGlideUrl/getMediaItem 是 Android UI 层功能
- [ ] 11.3.2 标记为不实现（不影响书源/订阅源调试）
- [ ] 11.3.3 验证：无需代码修改

### 11.4 新-4 CheckSource 校验补充

- [ ] 11.4.1 阅读真机 `Debug.kt:87-109` 确认 CheckSource 校验逻辑
- [ ] 11.4.2 补充 startChecking/finishChecking/getRespondTime/updateFinalMessage
- [ ] 11.4.3 验证：批量校验可用

---

## 方向 12：第四轮P0级修复（6个，P0）

> **目标**：修复第四轮深度排查发现的6个P0级新遗漏
> **源码依据**：4子代理逐行源码核实

### 12.1 GAP-36 JsExtensions委托模式并发覆盖

- [ ] 12.1.1 阅读真机 `AnalyzeRule.kt:55-62` 确认直接实现JsExtensions模式
- [ ] 12.1.2 将JsExtensionsStub从全局单例改为实例化模式（每个AnalyzeRule实例创建独立JsExtensions实例）
- [ ] 12.1.3 验证：并发调试多个书源时JS中source/book变量正确指向对应书源

### 12.2 GAP-37 ConcurrentRateLimiter空实现

- [ ] 12.2.1 阅读真机 `ConcurrentRateLimiter.kt:9-131` 确认完整限流实现
- [ ] 12.2.2 移植ConcurrentRecord数据类、concurrentRecordMap、fetchStart/getConcurrentRecord/withLimit方法
- [ ] 12.2.3 验证：设置了concurrentRate的书源仿真端正确限流

### 12.3 GAP-38 getSubDomain域名提取不一致

- [ ] 12.3.1 阅读真机 `NetworkUtils.kt:212-223` 确认PublicSuffixDatabase使用
- [ ] 12.3.2 引入OkHttp的PublicSuffixDatabase或移植真机getSubDomain完整实现
- [ ] 12.3.3 验证：多级子域名网站（如mail.example.com）Cookie域名正确匹配

### 12.4 GAP-39 搜索阶段ruleData注入对象不同

- [ ] 12.4.1 阅读真机 `WebBook.kt:60` 确认独立RuleData()创建
- [ ] 12.4.2 修改 `BookSourceDebugger.kt:124`：搜索阶段创建独立RuleData()注入
- [ ] 12.4.3 验证：搜索URL的JS规则中访问ruleData属性行为与真机一致

### 12.5 GAP-40 详情阶段缺少类型重置

- [ ] 12.5.1 阅读真机 `WebBook.kt:197-198` 确认removeAllBookType+addType
- [ ] 12.5.2 在BookSourceDebugger详情阶段添加类型重置逻辑
- [ ] 12.5.3 验证：文件类书源（bookSourceType=3）正确设置webFile位

### 12.6 GAP-41 RSS调试ruleData注入对象不同

- [ ] 12.6.1 阅读真机 `Rss.kt:42` 确认独立RuleData()创建
- [ ] 12.6.2 修改 `RssSourceDebugger.kt:207-213`：RSS调试创建独立RuleData()注入
- [ ] 12.6.3 验证：RSS列表页URL的JS规则中访问ruleData属性行为与真机一致

---

## 方向 13：第四轮P1级修复（14个，P1）

> **目标**：修复第四轮深度排查发现的14个P1级新遗漏
> **源码依据**：4子代理逐行源码核实

### 13.1 GAP-42 createSymmetricCrypto底层差异

- [ ] 13.1.1 移植SymmetricCryptoAndroid，覆写encryptBase64使用android.util.Base64
- [ ] 13.1.2 验证：加密结果Base64编码与真机一致

### 13.2 GAP-43 replaceFont多字节字符处理

- [ ] 13.2.1 移植toStringArray()方法
- [ ] 13.2.2 验证：多字节字符（emoji/生僻字）正确处理

### 13.3 GAP-44/45/46 AnalyzeUrl移除仿真端多余功能

- [ ] 13.3.1 移除AnalyzeUrl中的followRedirects字段和逻辑（GAP-44）
- [ ] 13.3.2 移除AnalyzeUrl init块中的header JS执行逻辑（GAP-45）
- [ ] 13.3.3 移除AnalyzeUrl中的ajax override，改为直接使用JsExtensionsStub.ajax（GAP-46）
- [ ] 13.3.4 验证：移除后不影响现有通过的源

### 13.4 GAP-47/52 loginCheckJs检测补充

- [ ] 13.4.1 在BookSourceDebugger搜索阶段添加loginCheckJs检测（GAP-47）
- [ ] 13.4.2 在RssSourceDebugger添加loginCheckJs检测（GAP-52）
- [ ] 13.4.3 验证：需要登录的书源正确检测登录态

### 13.5 GAP-48/49 详情阶段修复

- [ ] 13.5.1 使用扩展属性book.isWebFile替代魔法数判断（GAP-48）
- [ ] 13.5.2 在目录阶段添加preUpdateJs执行（GAP-49）
- [ ] 13.5.3 验证：文件类书源isWebFile判断正确 + preUpdateJs书源目录页变量初始化

### 13.6 GAP-50/51/53 分页处理对齐

- [ ] 13.6.1 对齐真机BookChapterList的nextTocUrl分页逻辑（GAP-50）
- [ ] 13.6.2 对齐真机BookContent的nextContentUrl分页逻辑（GAP-51）
- [ ] 13.6.3 对齐真机Rss模块的ruleNextPage分页逻辑（GAP-53）
- [ ] 13.6.4 验证：多页目录/正文/RSS列表的书源分页正确

### 13.7 GAP-54/55 数据模型修复

- [ ] 13.7.1 Book: type默认值改为BookType.text(0b1)，origin改为"loc_book"，infoHtml/tocHtml改@Ignore（GAP-54）
- [ ] 13.7.2 新增SearchBook数据模型，搜索阶段通过SearchBook中间转换（GAP-55）
- [ ] 13.7.3 验证：isWebFile判断正确 + 搜索结果处理与真机一致

---

## 方向 14：第四轮P2级修复（11个，P2）

> **目标**：修复第四轮深度排查发现的11个P2级新遗漏
> **源码依据**：4子代理逐行源码核实

### 14.1 GAP-56/57/58/59 核心类修复

- [ ] 14.1.1 GAP-56: evalJS注入对象改为持久化CookieStore/CacheManager
- [ ] 14.1.2 GAP-57: 反向引入真机getZipByteArrayContent循环bug
- [ ] 14.1.3 GAP-58: 补充BookChapter业务方法
- [ ] 14.1.4 GAP-59: BookSource/RssSource改为继承BaseSourceInterface

### 14.2 GAP-60/61/62/63 RSS调试多余功能移除

- [ ] 14.2.1 GAP-60: 移除仿真端RSS调试singleUrl模式分支
- [ ] 14.2.2 GAP-61: 改用rssSource.sortUrls()扩展函数处理sortUrl JS
- [ ] 14.2.3 GAP-62: 移除extractJsRule处理，直接使用完整ruleContent
- [ ] 14.2.4 GAP-63: 移除仿真端显式toAbsoluteUrl调用

### 14.3 GAP-64/65/66 网络层标记不实现

- [ ] 14.3.1 GAP-64: 移植SSLHelper双向认证方法
- [ ] 14.3.2 GAP-65: 标记getMediaItem为不实现
- [ ] 14.3.3 GAP-66: 标记Cronet处理为不实现

---

## 方向 15：第五轮WebBook/Rss模块修复（30个→5个P0保留+16个P1可选+9个P2过度修复，第七轮修正）

> **目标**：移植真机WebBook/Rss核心业务模块到仿真端（第七轮修正：P2级9个模块移植标注为过度修复，P1级16个改为可选修复）
> **源码依据**：2子代理逐行源码核实

### 15.1 P0级修复（5个，必须修复，保留）

- [ ] 15.1.1 GAP-67a: 所有阶段添加loginCheckJs检测逻辑
- [ ] 15.1.2 GAP-67b: 目录/正文分页添加ruleNextPage=="PAGE"特殊处理
- [ ] 15.1.3 GAP-67c: init规则执行方式改为getElement
- [ ] 15.1.4 GAP-67d: 移植完整正文格式化链（HtmlFormatter+StringEscapeUtils+HtmlMap+replaceRegex）
- [ ] 15.1.5 GAP-67e: 搜索/详情阶段添加checkRedirect重定向检测
- [ ] 15.1.6 验证：所有P0级修复后调试结果与真机一致

### 15.2 P1级修复（16个→可选修复，第七轮修正）

> **修正说明**：P1级修复影响部分调试结果，但不影响核心校验准确性。遇到实际失败源时再实施。

- [ ] 15.2.1 GAP-68a: 目录阶段添加preUpdateJs执行（可选）
- [ ] 15.2.2 GAP-68b: 实现并发分页（目录/正文）（可选）
- [ ] 15.2.3 GAP-68c: 补充章节字段提取（chapterUrl/level等）（可选）
- [ ] 15.2.4 GAP-68d: 添加formatJs正文格式化（可选）
- [ ] 15.2.5 GAP-68e: 添加reverse/去重逻辑（可选）
- [ ] 15.2.6 GAP-68f: 添加subContentRule正文分段（可选）
- [ ] 15.2.7 GAP-68g: 添加titleRule章节标题规则（可选）
- [ ] 15.2.8 GAP-68h: 添加replaceRegex前置处理（可选）
- [ ] 15.2.9 GAP-68i: 添加bookUrlPattern匹配（可选）
- [ ] 15.2.10 GAP-68j: 补充Book字段格式化链（可选）
- [ ] 15.2.11 GAP-68k: 添加RssParserDefault降级（可选）
- [ ] 15.2.12 GAP-68l: 添加sortUrls缓存（可选）
- [ ] 15.2.13 GAP-68m: 移植exploreKinds（可选）
- [ ] 15.2.14 GAP-68n: 搜索结果记录respondTime（可选）
- [ ] 15.2.15 GAP-68o: 实现多源合并（可选）
- [ ] 15.2.16 GAP-68p: 补全Book变量注入（可选）
- [ ] 15.2.17 验证：可选修复实施后调试结果与真机一致

### 15.3 ~~P2级修复（9个）~~ ❌ 过度修复（第七轮修正）

> **移除理由**：模块移植成本高，但内联实现已能覆盖核心校验场景。移植完整模块属于过度修复。

- ~~15.3.1 GAP-69a: 移植BookChapterList模块~~
- ~~15.3.2 GAP-69b: 移植BookContent模块~~
- ~~15.3.3 GAP-69c: 移植RssParserByRule模块~~
- ~~15.3.4 GAP-69d: 移植BookInfo模块~~
- ~~15.3.5 GAP-69e: 移植BookList模块~~
- ~~15.3.6 GAP-69f~i: 对齐各阶段规则类型处理~~
- ~~15.3.7 验证：移植模块后全量回归测试~~

---

## 方向 16：第五轮Rhino/并发基础架构修复（11个→2个P0重新设计+2个保留+3个过度修复+4个已对齐，第七轮修正）

> **目标**：修复Rhino引擎配置和并发模型差异（第七轮修正：GAP-70a/70b重新设计，GAP-71a/72a/72c标注为过度修复）
> **源码依据**：2子代理逐行源码核实

### 16.1 P0级修复（2个→重新设计，第七轮修正）

> **重新设计方案（AD-11/AD-12）**：
> - AD-11：只移植WrapFactory（移除对ClassShutter的调用）+ NativeBaseSource + instructionObserverThreshold（自定义observeInstructionCount直接抛TimeoutException）+ maximumInterpreterStackDepth=1000
> - AD-12：只添加withTimeout超时控制（HTTP请求+JS执行）

- [ ] 16.1.1 GAP-70a（重新设计-AD-11）：
  - 移植 RhinoWrapFactory（修改移除对 RhinoClassShutter.visibleToScripts() 的调用，让所有Java类都可见）
  - 移植 NativeBaseSource
  - 自定义 observeInstructionCount 实现（直接抛出 TimeoutException 中断死循环，不依赖 RhinoContext.ensureActive()）
  - 设置 maximumInterpreterStackDepth=1000（对齐真机）
- [ ] 16.1.2 GAP-70b（重新设计-AD-12）：只添加 withTimeout 超时控制（HTTP请求+JS执行）
- [ ] 16.1.3 验证：JS执行行为与真机一致 + 超时控制正常

### 16.2 P1/P2级修复（5个→2个保留+3个过度修复，第七轮修正）

- ~~16.2.1 GAP-71a: scriptCache上限改为16（对齐真机）~~ ❌ 过度修复（第七轮修正：缓存大小不影响校验结果）
- [ ] 16.2.2 GAP-71b: 委托模式改实例化（与GAP-36合并修复）✅ 保留
- ~~16.2.3 GAP-72a: 移植RhinoContext生命周期管理~~ ❌ 过度修复（第七轮修正：生命周期管理不影响单次校验）
- [ ] 16.2.4 GAP-72b: 移植WrapFactory ✅ 保留（合并到AD-11中实施）
- ~~16.2.5 GAP-72c: 移植ClassShutter~~ ❌ 过度修复（第七轮修正：ClassShutter不移植，WrapFactory移除对其调用）
- [ ] 16.2.6 验证：Rhino引擎配置与真机一致

### 16.3 P3级确认（4个，已对齐）

- [x] 16.3.1 GAP-73a~d: Gson序列化/NoStackTraceException/正则表达式/字符编码检测 ✅ 已完全对齐

---

## 方向 17：第六轮P0级修复（2个→重新设计，第七轮修正）

> **目标**：修复Room数据库缺失和HTTP拦截器缺失（第七轮修正：GAP-67改为内存存储，GAP-80改为只添加UA注入+CookieJar）
> **源码依据**：2子代理逐行源码核实

### 17.1 GAP-67: ~~Room数据库完全缺失~~ 🔄 重新设计（内存存储）

> **重新设计方案**：不移植Room数据库，改用内存Map存储。持久化不影响单次校验结果。

- ~~17.1.1 阅读真机 `AppDatabase.kt:69-126` 确认数据库结构（20个实体，21个Dao）~~
- ~~17.1.2 接入SQLite JDBC（`xerial/sqlite-jdbc`）或H2 Database~~
- ~~17.1.3 实现核心Dao（BookSourceDao/BookDao/BookChapterDao/CookieDao/CacheDao）~~
- ~~17.1.4 验证：数据持久化正常工作~~
- **新方案**：所有数据存储改为内存Map实现（BookSource/Book/BookChapter/Cookie/Cache均使用ConcurrentHashMap）
- [ ] 17.1.5 验证：单次校验期间数据读写正常

### 17.2 GAP-80: ~~HTTP拦截器全部缺失~~ 🔄 重新设计（只添加UA注入+CookieJar）

> **重新设计方案**：不移植全部5个拦截器，只添加UA注入拦截器和CookieJar网络拦截器。其他拦截器（Keep-Alive/Cache-Control头注入、DecompressInterceptor、OkHttpExceptionInterceptor）不影响校验结果。

- ~~17.2.1 阅读真机 `HttpHelper.kt:51-127` 确认5个拦截器配置~~
- [ ] 17.2.2 添加UA自动注入拦截器（无UA时注入AppConfig.userAgent）
- ~~17.2.3 添加Keep-Alive/Cache-Control头注入拦截器~~ ❌ 过度修复
- [ ] 17.2.4 添加CookieJar网络拦截器（loadRequest+saveResponse，内存Map实现）
- ~~17.2.5 移植DecompressInterceptor（gzip/deflate解压）~~ ❌ 过度修复（OkHttp内置透明gzip解压，deflate改为可选修复）
- ~~17.2.6 移植OkHttpExceptionInterceptor（异常包装）~~ ❌ 过度修复
- [ ] 17.2.7 验证：HTTP请求行为与真机一致（UA注入+Cookie自动携带）

---

## 方向 18：第六轮P1级修复（8个→1个重新设计+2个保留+4个过度修复+1个可选修复，第七轮修正）

> **目标**：修复Cookie/Cache/SharedPreferences/AppConfig/拦截器差异（第七轮修正：4个持久化标注为过度修复，GAP-72重新设计，GAP-81改为可选修复）
> **源码依据**：2子代理逐行源码核实

### 18.1 ~~持久化修复（4个）~~ ❌ 过度修复（第七轮修正）

> **移除理由**：持久化不影响单次校验结果，已在方向10/17中说明。

- ~~18.1.1 GAP-68: CookieStore接入JSON文件持久化或SQLite~~ ❌ 过度修复
- ~~18.1.2 GAP-69: CacheManager接入文件系统持久化~~ ❌ 过度修复
- ~~18.1.3 GAP-71: 用java.util.Properties或JSON文件实现SharedPreferences~~ ❌ 过度修复
- [ ] 18.1.4 GAP-72（重新设计）：从环境变量读取关键配置项（LEGADO_CUSTOM_HOSTS/LEGADO_RECORD_LOG/LEGADO_THREAD_COUNT等），不移植SharedPreferences
- [ ] 18.1.5 验证：配置项从环境变量正确读取

### 18.2 HTTP拦截器修复（4个→2个保留+1个过度修复+1个可选修复，第七轮修正）

> **修正说明**：GAP-82/83已合并到方向17.2中实施。GAP-84标注为过度修复，GAP-81改为可选修复。

- [ ] 18.2.1 GAP-81（可选修复）：OkHttp内置透明gzip解压，deflate需额外处理（遇到deflate编码响应时再实施）
- [ ] 18.2.2 GAP-82: 添加CookieJar网络拦截器 ✅ 保留（已合并到方向17.2.4）
- [ ] 18.2.3 GAP-83: 添加UA自动注入拦截器 ✅ 保留（已合并到方向17.2.2）
- ~~18.2.4 GAP-84: 添加Keep-Alive/Cache-Control头注入拦截器~~ ❌ 过度修复（第七轮修正：不影响校验结果）
- [ ] 18.2.5 验证：HTTP行为与真机一致（UA注入+Cookie自动携带）

---

## 方向 19：第六轮P2/P3级修复（19个→2个保留+2个重新设计+3个保持原状+12个过度修复，第七轮修正）

> **目标**：修复Extensions/AppLog/AppConst等差异（第七轮修正：12个标注为过度修复，2个重新设计，3个保持原状）
> **源码依据**：2子代理逐行源码核实

### 19.1 P2级修复（10个→2个保留+2个重新设计+3个保持原状+3个过度修复，第七轮修正）

- ~~19.1.1 GAP-70: 用java.io.File实现ACache文件缓存~~ ❌ 过度修复（第七轮修正：文件缓存不影响校验结果）
- [ ] 19.1.2 GAP-73: userAgent默认值改为与真机一致 ✅ 保留
- [ ] 19.1.3 GAP-75: 补充AppConst缺失常量 ✅ 保留
- [ ] 19.1.4 GAP-76（重新设计）：customHosts/DNS自定义解析改为从环境变量读取（LEGADO_CUSTOM_HOSTS）
- [ ] 19.1.5 GAP-77: 实现AppLog Stub（内存列表+println）✅ 保持原状（已实现）
- ~~19.1.6 GAP-85: 移植BookSourceExtensions（exploreKinds/getBookType）~~ ❌ 过度修复（第七轮修正：exploreKinds不影响校验）
- ~~19.1.7 GAP-86: 移植RssSourceExtensions（sortUrls）~~ ❌ 过度修复（第七轮修正：sortUrls缓存不影响校验）
- ~~19.1.8 GAP-87: 移植SourceHelp（getSource/deleteSource/enableSource）~~ ❌ 过度修复（第七轮修正：源管理不影响校验）
- [ ] 19.1.9 GAP-88: 移植ReplaceAnalyzer（jsonToReplaceRules）✅ 保持原状（已实现）
- [ ] 19.1.10 GAP-91（重新设计）：扩展AppConfig网络配置（从环境变量读取userAgent/customHosts/threadCount等）
- [ ] 19.1.11 验证：保留项行为一致

### 19.2 P3级修复（9个→2个保留+3个保持原状+4个过度修复，第七轮修正）

- [ ] 19.2.1 GAP-74: 标记为不可实现（Cronet依赖Android原生）✅ 保持原状
- [ ] 19.2.2 GAP-78: 用java.util.logging.Logger实现文件日志 ✅ 保持原状（已实现）
- [ ] 19.2.3 GAP-79: 添加recordLog配置项 ✅ 保持原状（已实现）
- [ ] 19.2.4 GAP-89: 保持委托路径（已实现UserInterventionException）✅ 保持原状
- ~~19.2.5 GAP-94: 传递coroutineContext到ajax~~ ❌ 过度修复（第七轮修正：不影响校验结果）
- ~~19.2.6 GAP-95: 实现ajaxAll并发执行~~ ❌ 过度修复（第七轮修正：串行也能得到正确结果）
- ~~19.2.7 GAP-96: scriptCache上限改为16~~ ❌ 过度修复（第七轮修正：同GAP-71a）
- [ ] 19.2.8 GAP-98: 标记为不可实现（UI层）✅ 保持原状
- [ ] 19.2.9 GAP-99: 标记为不可实现（UI层）✅ 保持原状

---

## 方向 6：失败源优化（58 个源，P0）

> **目标**：用真实源测试验证，修复 58 个源规则问题
> **源码依据**：批量测试报告 `batch-test-report.json`

### 6.1 RSS sortUrl 生成器 bug 修复（31 个源）

- [ ] 6.1.1 分析 31 个 RSS 源的 sortUrl 字段错误填充原因
- [ ] 6.1.2 修正生成器字段映射逻辑
- [ ] 6.1.3 重新生成 31 个 RSS 源
- [ ] 6.1.4 验证：31 个 RSS 源至少进入 articleList 阶段

### 6.2 搜索规则重写（23 个源）

- [ ] 6.2.1 用浏览器 F12 检查 23 个 book 源搜索结果页 HTML
- [ ] 6.2.2 重写搜索规则选择器
- [ ] 6.2.3 验证：23 个 book 源搜索阶段通过

### 6.3 bookList 类型错误修复（2 个源）

- [ ] 6.3.1 修复哔哩哔哩漫画 bookList 选择器
- [ ] 6.3.2 修复腾讯视频 bookList 选择器
- [ ] 6.3.3 验证：bookList 返回 List 类型

### 6.4 URL 模板错误修复（2 个源）

- [ ] 6.4.1 修复番茄小说搜索 URL 变量语法
- [ ] 6.4.2 修复荔枝FM搜索 URL
- [ ] 6.4.3 验证：搜索 URL 变量正确替换

---

## 方向 7：全量回归测试（P0）

> **目标**：验证 100% 测试校验准确性（第七轮修正）
> **验证标准**：JAR测试通过则真机也能通过；JAR测试失败时，能准确区分是源规则问题还是仿真端问题

### 7.1 重新构建 JAR

- [ ] 7.1.1 重新构建 fatJar
- [ ] 7.1.2 验证：JAR 启动正常

### 7.2 全量批量测试

- [ ] 7.2.1 用 100 个真实源全量测试
- [ ] 7.2.2 统计成功率
- [ ] 7.2.3 分析失败源根因（区分仿真端/源规则/网站）
- [ ] 7.2.4 验证：JAR测试通过则真机也能通过；JAR失败时能准确区分源规则问题还是仿真端问题

### 7.3 经验反哺

- [ ] 7.3.1 将修复经验写入 basic-memory
- [ ] 7.3.2 更新 simulation-gap-report.md
- [ ] 7.3.3 更新 tasks.md 完成状态

---

## 任务依赖关系

```
方向 1（低难度）──┐
方向 2（中难度）──┤
方向 3（高难度）──┤  第七轮修正：砍掉8个过度修复
方向 4（委托路径）─┤
方向 5（仿真端问题）┤
方向 6（失败源优化）┤
方向 8（OkHttpUtils）─┤
方向 9（RssDebugger）─┤
方向 10（持久化）──┤  第七轮修正：3个过度修复，2个保留
方向 11（新发现遗漏）─┤
方向 12（第四轮P0）─┤
方向 13（第四轮P1）─┤
方向 14（第四轮P2）─┤
方向 15（第五轮WebBook/Rss）─┤  第七轮修正：9个过度修复，16个可选
方向 16（第五轮Rhino/并发）─┤  第七轮修正：3个过度修复，2个重新设计
方向 17（第六轮P0）─┤  第七轮修正：2个重新设计（内存存储+UA注入+CookieJar）
方向 18（第六轮P1）─┤  第七轮修正：4个过度修复，1个重新设计，1个可选
方向 19（第六轮P2/P3）─┼──→ 方向 7（全量回归测试）
```

**关键依赖**：
- 方向 2.4.6（evalJS shared Scope）依赖方向 16.1.1（GAP-70a 重新设计-AD-11，含SharedJsScope）
- 方向 4.3.3（getLoginInfo）依赖方向 4.3.1（androidId）
- 方向 9.1（GAP-22 P0）应优先实施 — 直接影响调试结果一致性
- 方向 10.2（CookieManager saveResponse）应优先实施 — 影响登录态维持（内存Map实现）
- 方向 11.1（Debug.kt 状态管理）依赖方向 9（RssSourceDebugger 修正）
- **方向 12（第四轮P0）应优先实施** — 6个P0级新遗漏直接影响调试结果正确性
- 方向 13.5（GAP-48 isWebFile）依赖方向 12.5（GAP-40 类型重置）
- 方向 13.7（GAP-54 Book数据模型）应在方向 12.5 之前实施（影响type默认值）
- 方向 14.1.4（GAP-59 继承体系）影响JS执行，需全量回归测试
- **方向 15.1（第五轮WebBook/Rss P0）应优先实施** — 5个P0级新遗漏直接影响所有阶段调试结果
- **方向 16.1（第五轮Rhino/并发 P0）应优先实施** — 2个P0级重新设计影响JS执行和超时控制
- **方向 17（第六轮P0）应优先实施** — 内存存储和UA注入+CookieJar是基础设施（第七轮修正：不再移植Room数据库）
- 方向 18（第六轮P1）依赖方向 17（GAP-67 内存存储 + GAP-80 UA注入+CookieJar）
- 方向 7 依赖方向 1-6 + 8-19 全部完成

---

## 验收标准

| 标准 | 验证方法 | 目标 |
|------|---------|------|
| 46 个可修复方法 | 逐方法对比真机 | ✅ 行为一致 |
| 21 个委托路径 | Selenium/环境变量/日志 | ✅ 委托成功 |
| 2 个仿真端问题 | BT之家/阳光电影 | ✅ 可访问 |
| 58 个失败源优化 | 重新批量测试 | ✅ 修复后通过 |
| 3 个 OkHttpUtils 方法 | 下载文件/zip解压/协程取消 | ✅ 行为一致 |
| 5 个 RssSourceDebugger 逻辑 | RSS源调试对比真机 | ✅ 调试结果一致 |
| ~~5 个持久化差异~~ → **2 个保留** | CookieManager内存Map实现 | ✅ 单次校验期间有效 |
| 4 个新发现遗漏 | Debug状态/校验功能 | ✅ 补充完成 |
| **6 个第四轮P0新发现** | **并发调试/限流/域名/ruleData/类型重置** | **✅ 行为一致** |
| **14 个第四轮P1新发现** | **加密/字体/多余功能移除/loginCheckJs/分页/数据模型** | **✅ 行为一致** |
| **11 个第四轮P2新发现** | **边缘场景验证** | **✅ 补充完成** |
| **5 个第五轮WebBook/Rss P0** | **loginCheckJs/PAGE/init/正文格式化链/checkRedirect** | **✅ 所有阶段调试一致** |
| ~~16 个第五轮WebBook/Rss P1~~ → **16 个可选修复** | **preUpdateJs/并发分页/章节字段/formatJs/reverse等** | **⚠️ 遇到失败源时实施** |
| ~~9 个第五轮WebBook/Rss P2~~ → **❌ 9 个过度修复** | ~~移植真机模块~~ | **❌ 不实施** |
| **2 个第五轮Rhino/并发 P0** | **WrapFactory+instructionObserverThreshold/withTimeout** | **✅ JS执行一致** |
| ~~5 个第五轮Rhino/并发 P1/P2~~ → **2 个保留+3 个过度修复** | **GAP-71b委托模式/GAP-72b WrapFactory** | **✅ 配置一致** |
| ~~2 个第六轮P0~~ → **2 个重新设计** | **内存存储/UA注入+CookieJar** | **✅ 基础设施就绪** |
| ~~8 个第六轮P1~~ → **1 个重新设计+2 个保留+1 个可选+4 个过度修复** | **GAP-72环境变量/GAP-82/83拦截器/GAP-81可选** | **✅ HTTP行为一致** |
| ~~10 个第六轮P2~~ → **2 个保留+2 个重新设计+3 个保持原状+3 个过度修复** | **GAP-73/75 userAgent/AppConst/GAP-76/91环境变量** | **✅ 保留项一致** |
| ~~9 个第六轮P3~~ → **2 个保留+3 个保持原状+4 个过度修复** | **GAP-74/89/98/99 不可实现/GAP-78/79 已实现** | **✅ 不影响核心调试** |
| **全量回归测试** | **100 个真实源** | **JAR通过则真机通过；JAR失败能准确区分原因** |
| **100% 测试校验准确性** | **真机能运行的源** | **JAR测试结果与真机一致** |
