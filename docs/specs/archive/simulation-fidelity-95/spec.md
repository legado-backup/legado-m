# Spec: JAR 仿真端 100% 测试校验准确性

> **第七轮修正**：设计目标从"100%兼容运行"（完全复刻真机）修正为"100%测试校验准确性"（JAR测试通过则真机通过，JAR失败时能准确区分源规则问题还是仿真端问题）

---

## Intent

开源阅读真机的书源和订阅源，在 JAR 仿真服务端实现 **100% 测试校验准确性**。即：**JAR测试通过则真机也能通过；JAR测试失败时，能准确区分是源规则问题还是仿真端问题**。不追求完全复刻真机的所有行为（如持久化/安全沙箱/性能差异等不影响校验结果的行为）。

**与旧目标的区别**：
- 旧目标"100%兼容运行"：要求所有方法行为与真机完全一致，包括持久化/安全沙箱/性能等 → 185个GAP中40%是过度修复
- 新目标"100%测试校验准确性"：只要求影响测试校验结果的行为与真机一致 → 52个必需修复 + 28个可选修复 + 10个重新设计 + 75个过度修复（不实施）

---

## Scope

### 核心定义：什么算"100%测试校验准确性"

| 场景 | 判定 | 责任方 |
|------|------|--------|
| JAR测试通过，真机也能通过 | ✅ 准确 | - |
| JAR测试通过，但真机失败（假阳性） | ❌ 必须修复 | 仿真端 |
| JAR测试失败，但真机能运行（假阴性） | ❌ 必须修复 | 仿真端 |
| JAR测试失败，真机也失败（源规则问题） | ✅ 准确（正确识别源规则问题） | 源规则 |
| 真机也运行失败（网站改版/反爬/域名失效/SSL过期） | ➖ 不计入 | 网站 |
| Android 平台特有方法（WebView/UI/硬件） | 🔄 委托路径 | 平台限制 |
| 持久化/安全沙箱/性能差异（不影响校验结果） | ➖ 不计入 | 过度修复 |

### 涵盖范围

#### 1. 仿真端方法兼容性修复（46 个可修复方法）

**A. 低难度修复（12 个）**：
- 6 个属性 var→val 签名修正（concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib）
- timeFormat 格式对齐
- connect 错误时 url 修正
- getTxtInFolder 删除 folder
- importScript 异常类型替换
- aesEncodeToString 对齐真机 bug（反向引入）

**B. 中难度修复（18 个）**：
- 6 个 base64/AES flags 映射完善（base64Decode/Encode/aesDecodeArgs/tripleDES/digest/HMac）
- 3 个 get/head/post 改用 Jsoup.connect 对齐真机
- 2 个 ajaxAll/ajaxTestAll 并发实现
- 2 个 downloadFile 流式下载 + 路径修正
- toNumChapter 章节号转换
- log 接入 Debug 回调
- putConcurrent 实现
- executeSortUrlJs 注入 source 变量
- evalJS 实现 sharedScope

**C. 高难度修复（16个→8个，第七轮修正：砍掉8个过度修复）**：
- ~~4个压缩文件解压（unArchiveFile/unzipFile/un7zFile/unrarFile）~~ ❌ 延后
- ~~4个Rar/7z内容读取（getRar/get7zByteArrayContent/StringContent）~~ ❌ 延后
- ~~4个配置读取（getReadBookConfig/Map + getThemeConfig/Map）~~ 🔄 重新设计：只补充userAgent/customHosts
- ~~refreshExplore实现~~ ❌ 过度修复
- refreshJSLib实现SharedJsScope ✅ 保留
- getLoginInfoMap实现RowUi解析 ✅ 保留
- getHeaderMap对齐AppConfig.userAgent ✅ 保留
- debugExplore infoMap实现 ✅ 保留

#### 2. 不可实现方法委托路径（21 个）

**A. WebView 渲染委托（9 个）**：
- webView/webViewGetSource/webViewGetOverrideUrl（各 3 重载）
- 委托 Python Selenium 执行 JS 渲染
- WebViewRequiredException 携带请求信息，Python 端回传结果

**B. Android UI 交互委托（5 个）**：
- startBrowser/startBrowserAwait/getVerificationCode → Selenium 浏览器自动化 + OCR
- openVideoPlayer/openUrl → 纯 UI 功能，对书源验证无影响

**C. Android 硬件信息配置（4 个）**：
- androidId/getWebViewUA → 环境变量 LEGADO_ANDROID_ID/LEGADO_WEBVIEW_UA
- getLoginInfo/putLoginInfo → 依赖 androidId 修复

**D. Toast 输出替代（2 个）**：
- toast/longToast → 日志文件记录

**E. Debugger WebView 委托（1 个）**：
- debugContent useWebView → 依赖 Selenium 委托

#### 3. 仿真端已知问题修复（2 个）

- BT之家 PKIX 证书链缺失 → 配置 OkHttp 信任所有证书（SSLHelper）
- 阳光电影 DNS 返回 0.0.0.0 → 配置 OkHttp 公共 DNS 回退

#### 3a. 遗漏排查新增修复（17 个，源码核实）

> **第二轮设计文档完成后，用户要求"深度分析全面排查"。启动子代理逐行对比源码，核实并新增 17 个 GAP。**

**H. OkHttpUtils 方法补全（3 个，P1）**：
- newCallResponseBody：下载文件/获取图片需要的中间层方法
- decompressed：处理 application/zip 响应（如压缩主题文件）
- await 协程取消：协程取消时底层 OkHttp 请求也需取消

**I. RssSourceDebugger 逻辑修正（5 个，P0-P2）**：
- **GAP-22（P0）**：ruleDescription 有值时应跳过内容页解析（真机 `Debug.kt:123-134`），仿真端总是调用内容页
- key::url 格式和搜索关键字调试入口
- 取消机制（CompositeCoroutine）
- 校验模式（CheckSource 集成）
- 无参 key 调试入口

**J. 持久化深度差异（5 个，P1-P2）**：
- CookieStore 无持久化（真机 Room SQLite，仿真端 ConcurrentHashMap）
- CookieManager 精简为 2 个方法（缺少 saveResponse，响应 Cookie 不自动保存）
- CacheManager 无持久化（真机三层缓存，仿真端纯内存）
- getFile 根目录不同（误报修正：有完整文件操作，仅根目录不同）
- WebCookie 用内存 Map 替代 android.webkit.CookieManager

**K. 新发现遗漏（4 个，P2-P4）**：
- Debug.kt 严重简化（真机 362 行，仿真端 10 行）
- await 回调顺序不一致（无功能影响）
- AnalyzeUrl 缺 getGlideUrl/getMediaItem（不影响调试）
- 缺 CheckSource 校验功能

#### 3b. 第四轮深度排查新增修复（31个，4子代理逐行源码核实）

> **第三轮设计文档完成后，用户要求"深度分析全面排查"。启动4个子代理分别从 AnalyzeRule规则引擎 / JsExtensions扩展函数 / HTTP网络层 / 调试器+数据模型 四个角度，逐行对比实现行为。发现31个新遗漏。**

**L1. P0级新发现（6个）**：
- GAP-36: JsExtensions委托模式并发覆盖（全局单例source/ruleData被覆盖）
- GAP-37: ConcurrentRateLimiter空实现（withLimit直接执行block，无限流）
- GAP-38: getSubDomain域名提取不一致（仅剥离www前缀，不处理多级TLD）
- GAP-39: 搜索阶段ruleData注入对象不同（真机用RuleData()，仿真端用book）
- GAP-40: 详情阶段缺少removeAllBookType/addType类型重置
- GAP-41: RSS调试ruleData注入对象不同（真机用RuleData()，仿真端不传）

**L2. P1级新发现（14个）**：
- GAP-42: createSymmetricCrypto底层差异（SymmetricCryptoAndroid vs hutool）
- GAP-43: replaceFont多字节字符处理（toStringArray vs toCharArray）
- GAP-44/45/46: AnalyzeUrl仿真端多余功能（followRedirects/header JS/ajax override）
- GAP-47/52: loginCheckJs检测缺失（搜索/RSS阶段）
- GAP-48: 详情阶段isWebFile判断方式不同
- GAP-49: 目录阶段缺少preUpdateJs执行
- GAP-50/51/53: 分页处理差异（目录/正文/RSS列表）
- GAP-54: Book数据模型差异（type/origin默认值，infoHtml/tocHtml存储方式）
- GAP-55: SearchBook数据模型缺失

**L3. P2级新发现（11个）**：
- GAP-56: evalJS注入Stub对象（无持久化）
- GAP-57: getZipByteArrayContent循环逻辑差异（真机有bug）
- GAP-58: BookChapter数据模型差异
- GAP-59: BookSource/RssSource继承体系差异
- GAP-60/61/62/63: RSS调试仿真端多余功能
- GAP-64: SSLHelper缺失双向认证
- GAP-65/66: AnalyzeUrl缺失/移除功能

#### 3c. 第五轮深度排查新增修复（41个，2子代理逐行源码核实）

> **第四轮设计文档完成后，用户质问"设计能否满足100%仿真"。启动2个子代理分别从 WebBook/Rss核心业务模块 和 Rhino/Gson/并发/异常基础架构 两个角度，逐行对比实现行为。发现41个新遗漏。**

**M1. WebBook/Rss核心业务模块差异（30个，第七轮修正：5个P0必需+16个P1可选+9个P2不修复）**：
- **P0（5个，必需修复）**：loginCheckJs完全缺失、ruleNextPage=="PAGE"特殊处理缺失、init规则执行方式不同（getElement vs getString）、BookContent正文格式化链完全缺失、checkRedirect重定向检测缺失
- **P1（16个，可选修复）**：preUpdateJs缺失、并发分页缺失、章节字段提取不完整、formatJs缺失、reverse/去重缺失、subContentRule缺失、titleRule缺失、replaceRegex前置处理缺失、bookUrlPattern匹配缺失、字段格式化缺失、RssParserDefault降级缺失、sortUrls缓存缺失、~~exploreKinds完全缺失~~（过度修复）、搜索结果respondTime缺失、多源合并缺失、Book变量注入不完整
- **P2（9个，不修复）**：~~BookChapterList/BookContent/RssParserByRule/BookInfo/BookList模块未复用~~（过度修复）、~~各阶段规则类型处理差异~~（过度修复）

**M2. Rhino/Gson/并发/异常基础架构差异（11个，第七轮修正：2个P0重新设计+4个过度修复+5个保留）**：
- **P0（2个，重新设计）**：Rhino JS引擎配置→只移植WrapFactory（移除对ClassShutter的调用）+instructionObserverThreshold（自定义observeInstructionCount直接抛异常）+maximumInterpreterStackDepth=1000、并发模型→只添加withTimeout超时控制
- ~~P1（2个）~~：~~缓存机制差异（scriptCache上限）~~（过度修复）、依赖注入差异（保留，与GAP-36合并）
- ~~P2（3个）~~：~~RhinoContext生命周期管理~~（过度修复）、WrapFactory（保留，AD-11必需）、~~ClassShutter~~（过度修复）
- **P3（4个）**：Gson序列化/NoStackTraceException/正则表达式/字符编码检测 ✅ 已完全对齐

#### 3d. 第六轮深度排查新增修复（29个，2子代理逐行源码核实）

> **第五轮排查完成后，用户要求"深度分析全面排查"。启动2个子代理分别从 数据持久化/配置/日志/缓存 和 网络层/资源加载/业务模型 两个角度，逐行对比实现行为。发现29个新遗漏。**

**N1. P0级新发现（2个，第七轮修正：全部重新设计）**：
- GAP-67: ~~Room数据库完全缺失~~ → 重新设计：内存存储（ConcurrentHashMap），不引入数据库
- GAP-80: ~~HTTP拦截器全部缺失~~ → 重新设计：只添加UA注入+CookieJar（不添加5个拦截器）

**N2. P1级新发现（8个，第七轮修正：4个过度修复+1个重新设计+3个保留）**：
- ~~GAP-68: Cookie持久化差异~~ ❌ 过度修复（内存存储）
- ~~GAP-69: CacheManager三层缓存降级~~ ❌ 过度修复（内存存储）
- ~~GAP-71: SharedPreferences完全缺失~~ ❌ 过度修复（不需要配置持久化）
- GAP-72: ~~AppConfig极简Stub~~ → 重新设计：只补充userAgent + customHosts
- GAP-81: DecompressInterceptor缺失 → ⚠️ 可选修复（OkHttp内置gzip解压，deflate需额外处理）
- GAP-82: CookieJar拦截器缺失 ✅ 保留
- GAP-83: UA自动注入拦截器缺失 ✅ 保留
- ~~GAP-84: Keep-Alive/Cache-Control头注入缺失~~ ❌ 过度修复（OkHttp内置连接池管理）

**N3. P2级新发现（10个，第七轮修正：7个过度修复+2个保留+1个可选）**：
- ~~GAP-70: ACache文件缓存缺失~~ ❌ 过度修复
- GAP-73: userAgent默认值差异 ✅ 保留
- GAP-75: ~~AppConst常量大量缺失~~ → 重新设计：只补充MAX_THREAD + charsets + dateFormat/timeFormat
- GAP-76: customHosts/DNS自定义解析缺失 ✅ 保留（需实现hostMap/addressCache解析逻辑）
- ~~GAP-77: AppLog完全缺失~~ ❌ 过度修复
- ~~GAP-85: BookSourceExtensions缺失~~ ❌ 过度修复
- ~~GAP-86: RssSourceExtensions缺失~~ ❌ 过度修复
- ~~GAP-87: SourceHelp完全缺失~~ ❌ 过度修复
- GAP-88: ReplaceAnalyzer缺失 → ⚠️ 可选修复
- ~~GAP-91: AppConfig网络配置极简~~ ❌ 过度修复

**N4. P3级新发现（9个，第七轮修正：5个过度修复+4个保持原状）**：
- GAP-74: isCronet固定false ✅ 保持原状（不可实现）
- ~~GAP-78: LogUtils文件日志缺失~~ ❌ 过度修复
- ~~GAP-79: recordLog配置缺失~~ ❌ 过度修复
- GAP-89: SourceVerificationHelp缺失 ✅ 保持原状（委托路径已实现）
- ~~GAP-94: ajax不传coroutineContext~~ ❌ 过度修复
- ~~GAP-95: ajaxAll无并发~~ ❌ 过度修复
- ~~GAP-96: compileScriptCache缓存上限差异~~ ❌ 过度修复
- GAP-98: GlideImageGetter缺失 ✅ 保持原状（UI层不可实现）
- GAP-99: ReadBook全局单例缺失 ✅ 保持原状（UI层不可实现）

#### 4. 失败源优化（用真实源测试验证）

**A. RSS sortUrl 生成器 bug 修复（31 个源）**：
- 根因：sortUrl 字段被批量填充为 JSON 对象 `{"content":"class.content"}`
- 修复：修正生成器字段映射逻辑，sortUrl 应为 URL 模板

**B. 搜索规则不匹配修复（23 个源）**：
- 根因：搜索规则选择器未匹配网站真实 HTML
- 修复：用浏览器 F12 检查搜索结果页 HTML，重写选择器

**C. bookList 类型错误修复（2 个源）**：
- 根因：bookList 规则返回 String 而非 List
- 修复：改用 class.xxx 列表选择器

**D. URL 模板错误修复（2 个源）**：
- 根因：搜索 URL 变量语法错误
- 修复：使用 Legado 的 `{{key}}`/`searchKey` 变量语法

### 不涵盖范围

- 真机也失败的源（网站改版/反爬/域名失效/SSL过期）——非仿真端责任
- 源规则本身写错（真机也失败）——非仿真端责任
- 需要 Android 硬件的方法（无替代方案时）——平台限制

---

## Approach

### 核心策略：真机源码逐行对齐 + 真实源测试验证

#### 策略 1：源码移植优先（第七轮修正：移除过度修复项）

所有方法修复均基于真机源码逐行分析，优先**直接移植真机源码**：

| 修复类别 | 策略 | 理由 |
|---------|------|------|
| ~~压缩文件解压~~ | ~~移植 ArchiveUtils + Apache Commons Compress~~ | ~~真机使用 ArchiveUtils~~ → 第七轮延后 |
| ~~配置读取~~ | ~~移植 ReadBookConfig/ThemeConfig~~ | ~~真机使用 SharedPreferences~~ → 第七轮重新设计：只补充userAgent/customHosts |
| base64/AES flags | 完善 flags 映射表 | 真机使用 android.util.Base64 |
| 并发请求 | 使用 CompletableFuture/线程池 | 真机使用 runBlocking + flow.mapAsync |
| SharedJsScope | 移植 SharedJsScope（Rhino Scope 管理） | 真机使用 getShareScope |
| WrapFactory | 移植WrapFactory（移除对ClassShutter的调用） | 真机使用RhinoWrapFactory（AD-11修正） |

#### 策略 2：委托路径实现

不可实现方法通过委托路径实现"行为等价"：

| 不可实现方法 | 委托路径 | 实现方式 |
|------------|---------|---------|
| WebView 渲染 | Python Selenium | WebViewRequiredException 携带请求信息 → Python 执行 → 回传结果 |
| UI 交互 | Selenium + OCR | UserInterventionException 携带上下文 → Selenium/OCR 处理 |
| 硬件信息 | 环境变量 | LEGADO_ANDROID_ID/LEGADO_WEBVIEW_UA 环境变量注入 |
| Toast | 日志文件 | 写入 debug.log 文件 |

#### 策略 3：真实源测试验证

用真实书源和订阅源测试，验证修复效果：

1. **修复 31 个 RSS 源 sortUrl bug** → 重新测试
2. **重写 23 个 book 源搜索规则** → 用真实网站 HTML 验证
3. **修复 2 个仿真端问题**（PKIX + DNS）→ 重新测试
4. **全量回归测试** → 目标：真机能运行的源，仿真端也能运行

### 架构原则

1. **不引入新重型依赖**：icu4j 用项目内源码，chinese-transfer 仅几百 KB
2. **保持 object 单例**：SSLHelper/HtmlFormatter/ChineseUtils 均为 object
3. **Android 依赖隔离**：Android 专有 API 用 JDK 替代或委托
4. **与真机逐行对齐**：每个方法实现后必须有源码行号引用
5. **委托路径必须有回传机制**：异常携带上下文 → 委托处理 → 回传结果

---

## Requirements

### REQ-01: 低难度方法修复（12 个）

- 6 个属性 var→val 签名修正
- timeFormat 对齐 AppConst.dateFormat
- connect 错误时 url 修正为 analyzeUrl.url
- getTxtInFolder 添加 folder 删除
- importScript 改用 NoStackTraceException
- aesEncodeToString 对齐真机 bug
- **验证**：编译通过 + 签名与真机一致

### REQ-02: 中难度方法修复（18 个）

- 6 个 base64/AES flags 映射完善（NO_WRAP=2 等全部对齐）
- 3 个 get/head/post 改用 Jsoup.connect 或对齐 AnalyzeUrl 行为
- 2 个 ajaxAll/ajaxTestAll 并发实现（CompletableFuture）
- 2 个 downloadFile 流式下载 + 路径修正
- toNumChapter 章节号转换
- log 接入 Debug 回调机制
- putConcurrent 实现 updateConcurrentRate
- executeSortUrlJs 注入 source 变量
- evalJS 实现 sharedScope
- **验证**：base64 编解码与真机一致 + 并发请求正确

### REQ-03: 高难度方法修复（8个，第七轮修正：原16个砍掉8个过度修复）

> **第七轮修正**：原16个中8个标注为过度修复（压缩文件解压4个+Rar/7z内容读取4个+配置读取4个→重新设计+refreshExplore→过度修复），实际只需修复8个

- ~~4个压缩文件解压（引入Apache Commons Compress）~~ ❌ 过度修复，延后
- ~~4个Rar/7z内容读取~~ ❌ 过度修复，延后
- ~~4个配置读取（ReadBookConfig/ThemeConfig剥离Android依赖）~~ 🔄 重新设计：只补充userAgent/customHosts到AppConfig
- ~~refreshExplore实现clearExploreKindsCache~~ ❌ 过度修复，exploreKinds不影响校验
- refreshJSLib实现SharedJsScope ✅ 保留
- getLoginInfoMap实现RowUi解析 ✅ 保留
- getHeaderMap对齐AppConfig.userAgent ✅ 保留
- debugExplore infoMap实现 ✅ 保留
- **验证**：SharedJsScope正确管理Scope + loginUi正确解析 + UA正确注入 + exploreInfoMap正确构建

### REQ-04: WebView 委托路径实现（9 个）

- WebViewRequiredException 携带完整请求信息（url/html/js/cacheFirst）
- Python Selenium 端实现 webView 渲染委托
- 结果回传机制（HTTP API 或文件交换）
- **验证**：需要 WebView 渲染的源可调试

### REQ-05: UI 交互委托路径实现（5 个）

- startBrowser → Selenium 浏览器自动化
- getVerificationCode → OCR 自动识别 + 用户介入
- openVideoPlayer/openUrl → 标记为不影响验证
- **验证**：需要登录的源可调试

### REQ-06: 硬件信息环境变量配置（4 个）

- LEGADO_ANDROID_ID 环境变量注入
- LEGADO_WEBVIEW_UA 环境变量注入
- getLoginInfo/putLoginInfo 依赖 androidId 修复
- **验证**：AES 加密解密与真机一致

### REQ-07: 仿真端已知问题修复（2 个）

- BT之家 PKIX → 配置 SSLHelper 信任所有证书
- 阳光电影 DNS → 配置 OkHttp 公共 DNS 回退（223.5.5.5）
- **验证**：BT之家和阳光电影可访问

### REQ-08: 失败源优化（58 个源）

- 31 个 RSS 源 sortUrl bug 修复
- 23 个 book 源搜索规则重写
- 2 个 bookList 类型错误修复
- 2 个 URL 模板错误修复
- **验证**：修复后重新批量测试，真机能运行的源仿真端也能运行

### REQ-09: 全量回归测试

- 用 100 个真实源全量测试
- 对比真机结果（如有真机测试数据）
- 目标：真机能运行的源，仿真端也能运行
- **验证**：成功率显著提升（排除网站问题后）

### REQ-10: OkHttpUtils 方法补全（3个，P1）

> **遗漏排查新增**：源码核实确认仿真端 OkHttpUtils 缺少 3 个方法

- 补充 `newCallResponseBody` 扩展函数（真机 `OkHttpUtils.kt:45-50`）
- 补充 `decompressed` 扩展函数（真机 `OkHttpUtils.kt:97-111`，处理 application/zip 响应）
- 补充 `await` 方法的 `invokeOnCancellation` 协程取消（真机 `OkHttpUtils.kt:61-77`）
- **验证**：下载文件/获取图片/zip响应解压正常 + 协程取消时底层请求也取消

### REQ-11: RssSourceDebugger 逻辑修正（5个，P0-P2）

> **遗漏排查新增**：源码核实确认 RssSourceDebugger 与真机 Debug.kt 存在 5 处逻辑差异

- **P0**：修正 ruleDescription 逻辑（GAP-22）— ruleDescription 有值时跳过内容页解析（对齐 `Debug.kt:123-134`）
- 补充 key::url 格式和搜索关键字调试入口（GAP-23，对齐 `Debug.kt:142-184`）
- 添加取消机制（GAP-24，对齐 `Debug.kt:24,78-85` CompositeCoroutine）
- 补充校验模式（GAP-25，对齐 `Debug.kt:27,87-109` CheckSource 集成）
- 添加无参 key 调试入口（GAP-26，对齐 `Debug.kt:111-140`）
- **验证**：RSS 源调试结果与真机一致 + ruleDescription 有值时不请求内容页

### REQ-12: 持久化实现（5个，P1-P2，第七轮修正：改为内存存储）

> **第七轮修正**：原方案接入SQLite/JSON文件持久化，修正为内存存储（单次调试会话不需要持久化）

- ~~CookieStore接入持久化（GAP-31）~~ ❌ 过度修复，保持内存存储
- CookieManager补充saveResponse/loadRequest方法（GAP-32）✅ 保留，但改为内存Map实现
- ~~CacheManager接入持久化（GAP-33）~~ ❌ 过度修复，保持内存存储
- getFile根目录修正（GAP-34）✅ 已修正（误报，行为等价）
- WebCookie存储修正描述（GAP-35）✅ 已修正
- **验证**：HTTP响应的Set-Cookie自动保存到内存Map + 后续请求自动携带Cookie + 登录态在会话内保持

### REQ-13: 新发现遗漏修复（4个，P2-P4）

> **遗漏排查新增**：源码核实发现 4 个新遗漏

- Debug.kt 补充状态管理（新-1，真机 362 行完整状态管理，仿真端仅 10 行 println）
- await 回调顺序对齐（新-2，真机 onFailure 在前，仿真端 onResponse 在前）
- AnalyzeUrl 标记 getGlideUrl/getMediaItem 为不实现（新-3，Android UI 层功能，不影响调试）
- 补充 CheckSource 校验功能（新-4，对齐 `Debug.kt:87-109`）
- **验证**：Debug 状态依赖代码行为正常 + 批量校验可用

### REQ-14: 第四轮P0级修复（6个，P0）

> **第四轮深度排查新增**：4子代理逐行源码核实发现6个P0级新遗漏

- GAP-36: JsExtensions委托模式改为实例化模式（消除并发覆盖）
- GAP-37: 移植ConcurrentRateLimiter完整限流实现
- GAP-38: getSubDomain对齐PublicSuffixDatabase（处理多级TLD）
- GAP-39: 搜索阶段创建独立RuleData()注入（不用book对象）
- GAP-40: 详情阶段添加removeAllBookType+addType类型重置
- GAP-41: RSS调试创建独立RuleData()注入
- **验证**：并发调试source/book变量正确 + 限流生效 + Cookie域名匹配 + ruleData属性行为一致 + 文件类书源isWebFile判断正确

### REQ-15: 第四轮P1级修复（14个，P1）

> **第四轮深度排查新增**：4子代理逐行源码核实发现14个P1级新遗漏

- GAP-42: 移植SymmetricCryptoAndroid对齐encryptBase64
- GAP-43: 移植toStringArray()处理多字节字符
- GAP-44/45/46: 移除AnalyzeUrl仿真端多余功能（followRedirects/header JS/ajax override）
- GAP-47/52: 补充loginCheckJs检测（搜索/RSS阶段）
- GAP-48: 使用扩展属性book.isWebFile替代魔法数判断
- GAP-49: 目录阶段添加preUpdateJs执行
- GAP-50/51/53: 对齐真机分页处理逻辑（目录/正文/RSS列表）
- GAP-54: Book数据模型对齐（type/origin默认值，infoHtml/tocHtml改@Ignore）
- GAP-55: 新增SearchBook数据模型
- **验证**：加密结果一致 + 多字节字符正确 + 多余功能移除后不影响现有源 + loginCheckJs检测生效 + 分页逻辑一致 + 数据模型行为一致

### REQ-16: 第四轮P2级修复（11个，P2）

> **第四轮深度排查新增**：4子代理逐行源码核实发现11个P2级新遗漏

- GAP-56: evalJS注入持久化CookieStore/CacheManager
- GAP-57: 反向引入真机getZipByteArrayContent循环bug
- GAP-58: 补充BookChapter业务方法
- GAP-59: BookSource/RssSource改为继承BaseSourceInterface
- GAP-60/61/62/63: 移除RSS调试仿真端多余功能
- GAP-64: 移植SSLHelper双向认证方法
- GAP-65/66: 标记getMediaItem/Cronet为不实现
- **验证**：边缘场景行为一致 + 继承体系修改后JS执行正常

### REQ-17: 第五轮WebBook/Rss模块修复（5个P0必需+16个P1可选+9个P2不修复，第七轮修正）

> **第七轮修正**（AD-10）：保持内联实现，不移植整个WebBook/Rss模块。只修复P0级5个差异，P1级16个改为可选修复，P2级9个不修复。

- **P0（5个，必需修复）**：loginCheckJs完全缺失（所有阶段）、ruleNextPage=="PAGE"特殊处理缺失、init规则执行方式不同（getElement vs getString）、BookContent正文格式化链完全缺失、checkRedirect重定向检测缺失
- **P1（16个，可选修复）**：preUpdateJs缺失、并发分页缺失、章节字段提取不完整、formatJs缺失、reverse/去重缺失、subContentRule缺失、titleRule缺失、replaceRegex前置处理缺失、bookUrlPattern匹配缺失、字段格式化缺失、RssParserDefault降级缺失、sortUrls缓存缺失、~~exploreKinds完全缺失~~（过度修复）、搜索结果respondTime缺失、多源合并缺失、Book变量注入不完整
- **P2（9个，不修复）**：~~BookChapterList/BookContent/RssParserByRule/BookInfo/BookList模块未复用~~（过度修复，内联实现行为对齐即可）、~~各阶段规则类型处理差异~~（过度修复，P0级已覆盖关键差异）
- **验证**：P0级5个差异修复后，所有阶段调试结果与真机一致。P1级遇到实际失败源时再逐个修复。

### REQ-18: 第五轮Rhino/并发基础架构修复（第七轮修正：2个P0重新设计+4个过度修复+5个保留）

> **第七轮修正**（AD-11/AD-12）：GAP-70a重新设计为只移植WrapFactory+instructionObserverThreshold（源码核实修正：WrapFactory需移除对ClassShutter的调用，instructionObserverThreshold需自定义observeInstructionCount直接抛异常），GAP-70b重新设计为只添加withTimeout。GAP-71a/72a/72c标注为过度修复。

- **GAP-70a（P0，重新设计-AD-11）**：只移植WrapFactory（移除对ClassShutter的调用）+ NativeBaseSource + instructionObserverThreshold（自定义observeInstructionCount直接抛TimeoutException） + maximumInterpreterStackDepth=1000
- **GAP-70b（P0，重新设计-AD-12）**：只添加withTimeout超时控制（HTTP请求+JS执行），不替换runBlocking→Coroutine
- ~~GAP-71a（P1）~~ ❌ 过度修复（scriptCache上限不影响校验）
- GAP-71b（P1）✅ 保留（委托模式改实例化，与GAP-36合并修复）
- ~~GAP-72a（P2）~~ ❌ 过度修复（RhinoContext生命周期管理，AD-11不需要）
- GAP-72b（P2）✅ 保留（移植WrapFactory，AD-11必需）
- ~~GAP-72c（P2）~~ ❌ 过度修复（ClassShutter，AD-11不需要）
- GAP-73a~d（P3）✅ 已完全对齐
- **验证**：JS执行中source/book变量正确包装 + 死循环源规则被instructionObserverThreshold中断 + HTTP请求超时不卡死

### REQ-19: 第六轮P0级修复（2个，P0，第七轮修正：全部重新设计）

> **第七轮修正**：GAP-67重新设计为内存存储（不引入数据库），GAP-80重新设计为只添加UA注入+CookieJar（不添加5个拦截器）

- **GAP-67（重新设计）**：~~接入SQLite JDBC或H2 Database~~ → 使用内存存储（ConcurrentHashMap），单次调试会话不需要持久化，不引入SQLite/H2依赖
- **GAP-80（重新设计）**：~~添加5个拦截器~~ → 只添加2个影响测试校验的拦截器：UA注入拦截器（GAP-83）+ CookieJar网络拦截器（GAP-82）。不添加Keep-Alive/Cache-Control（OkHttp内置连接池管理）、DecompressInterceptor（OkHttp内置gzip解压，deflate降级为可选修复）、OkHttpExceptionInterceptor（异常包装不影响校验）
- **验证**：内存存储在会话内正常工作 + UA注入行为与真机一致 + CookieJar自动管理Cookie

### REQ-20: 第六轮P1级修复（第七轮修正：4个过度修复+1个重新设计+3个保留）

> **第七轮修正**：8个中4个标注为过度修复（GAP-68/69/71/84），1个重新设计（GAP-72），3个保留（GAP-81降级为可选+GAP-82/83保留）

- ~~GAP-68: Cookie持久化差异~~ ❌ 过度修复（内存存储）
- ~~GAP-69: CacheManager三层缓存降级~~ ❌ 过度修复（内存存储）
- ~~GAP-71: SharedPreferences完全缺失~~ ❌ 过度修复（不需要配置持久化）
- **GAP-72（重新设计）**：~~移植200+配置项~~ → 只补充userAgent + customHosts到AppConfig
- **GAP-81（可选修复）**：DecompressInterceptor — OkHttp内置gzip解压，deflate需额外处理，遇到实际需求再移植
- **GAP-82** ✅ 保留：CookieJar拦截器（loadRequest+saveResponse，合并到HttpHelper）
- **GAP-83** ✅ 保留：UA自动注入拦截器
- ~~GAP-84: Keep-Alive/Cache-Control头注入~~ ❌ 过度修复（OkHttp内置连接池管理）
- **验证**：UA注入行为与真机一致 + CookieJar自动管理Cookie + 配置可读取userAgent/customHosts

### REQ-21: 第六轮P2/P3级修复（第七轮修正：12个过度修复+2个保留+2个重新设计+3个保持原状）

> **第七轮修正**：19个中12个标注为过度修复，2个保留（GAP-73/76），2个重新设计（GAP-75/88可选），3个保持原状（GAP-74/89/98/99已标记为不可实现/已实现）

- ~~GAP-70: ACache文件缓存缺失~~ ❌ 过度修复（持久化类）
- **GAP-73** ✅ 保留：userAgent默认值改为与真机一致
- **GAP-75（重新设计）**：~~补充全部常量~~ → 只补充MAX_THREAD + charsets + dateFormat/timeFormat
- **GAP-76** ✅ 保留：添加customHosts（需实现hostMap/addressCache解析逻辑）
- ~~GAP-77: AppLog完全缺失~~ ❌ 过度修复（日志不影响校验）
- ~~GAP-85: BookSourceExtensions缺失~~ ❌ 过度修复（Extensions不影响校验）
- ~~GAP-86: RssSourceExtensions缺失~~ ❌ 过度修复（同上）
- ~~GAP-87: SourceHelp完全缺失~~ ❌ 过度修复（源管理不需要持久化）
- **GAP-88（可选修复）**：ReplaceAnalyzer — 替换规则解析可能影响校验，遇到实际需求再移植
- ~~GAP-91: AppConfig网络配置极简~~ ❌ 过度修复（GAP-72已覆盖userAgent/customHosts）
- **P3保持原状**：GAP-74（Cronet不可实现）、GAP-89（委托路径已实现）、GAP-98/99（UI层不可实现）
- ~~GAP-78: LogUtils文件日志缺失~~ ❌ 过度修复（日志不影响校验）
- ~~GAP-79: recordLog配置缺失~~ ❌ 过度修复（同上）
- ~~GAP-94: ajax不传coroutineContext~~ ❌ 过度修复（性能差异不影响结果）
- ~~GAP-95: ajaxAll无并发~~ ❌ 过度修复（性能差异不影响结果）
- ~~GAP-96: compileScriptCache缓存上限差异~~ ❌ 过度修复（不影响校验）
- **验证**：userAgent/customHosts正确读取 + customHosts DNS解析生效 + 边缘场景行为一致

---

## Scenarios

### Scenario 1: RSS sortUrl bug 修复验证

```
给定: 31 个 RSS 源 sortUrl 被错误填充为 JSON 对象
当: 修正生成器字段映射，sortUrl 改为 URL 模板
预期: sortUrl 解析不再报 SelectorParseException
验证: 31 个 RSS 源至少进入 articleList 阶段
```

### Scenario 2: 搜索规则重写验证

```
给定: 23 个 book 源搜索结果为空
当: 用浏览器 F12 检查搜索结果页 HTML，重写选择器
预期: 搜索结果非空
验证: 23 个 book 源搜索阶段通过
```

### Scenario 3: PKIX 证书链修复验证

```
给定: BT之家 SSL 证书链缺失
当: 配置 SSLHelper 信任所有证书
预期: SSL 连接成功
验证: BT之家可访问
```

### Scenario 4: base64 flags 对齐验证

```
给定: 书源使用 base64Decode(str, 2) (NO_WRAP)
当: 完善 flags 映射
预期: 解码结果与真机一致
验证: 编解码结果与 android.util.Base64 一致
```

### Scenario 5: ~~压缩文件解压验证~~ ❌ 延后（第七轮修正）

```
给定: 书源使用 unArchiveFile/getRarStringContent
当: ~~移植 ArchiveUtils + Apache Commons Compress~~
预期: ~~压缩文件正确解压~~
验证: ~~Rar/7z/zip 文件内容正确读取~~
注: 第七轮修正，方向5延后，100个失败源中0个压缩文件相关。遇到实际需求再做。
```

### Scenario 6: WebView 委托验证

```
给定: 书源需要 webView() 渲染 JS
当: 抛出 WebViewRequiredException 携带请求信息
预期: Python Selenium 执行 JS 渲染并回传结果
验证: 需 WebView 的源可调试
```

### Scenario 7: 硬件信息环境变量验证

```
给定: 书源使用 androidId 作为 AES key
当: 设置 LEGADO_ANDROID_ID 环境变量为真机 androidId
预期: AES 加密解密与真机一致
验证: getLoginInfo/putLoginInfo 结果与真机一致
```

### Scenario 8: 全量回归测试

```
给定: 100 个真实源（修复后）
当: 执行批量测试
预期: 排除网站问题后，真机能运行的源仿真端也能运行
验证: 成功率显著提升（目标：排除网站问题后 100%）
```

### Scenario 9: ruleDescription 逻辑修正验证（P0）

```
给定: RSS 源 ruleDescription 有值，ruleContent 为空
当: 执行 RSS 源调试
预期: 跳过内容页解析，输出"存在描述规则，不解析内容页"
验证: 调试结果与真机 Debug.kt:123-134 行为一致，不多请求内容页
```

### Scenario 10: CookieManager saveResponse 验证

```
给定: 网站返回 Set-Cookie 响应头
当: 仿真端发送 HTTP 请求获取响应
预期: CookieManager.saveResponse 自动解析并保存 Cookie
验证: 后续请求自动携带保存的 Cookie，登录态不丢失
```

### Scenario 11: OkHttpUtils decompressed 验证

```
给定: 网站返回 application/zip 类型的响应体
当: 调用 decompressed() 方法
预期: 使用 ZipInputStream 解压，返回解压后的 ResponseBody
验证: 压缩主题文件/TXT规则可正确读取
```

### Scenario 12: JsExtensions委托模式并发覆盖验证（P0）

```
给定: 并发调试2个不同书源（书源A和书源B）
当: 书源A的JS规则调用 java.getSource()
预期: 返回书源A（不是书源B）
验证: 委托模式改为实例化后，并发调试source变量正确指向对应书源
```

### Scenario 13: ConcurrentRateLimiter限流验证（P0）

```
给定: 书源设置 concurrentRate = "3/1000"（每秒最多3次）
当: 仿真端连续发送10个请求
预期: 请求间有等待间隔，不会瞬间发出所有请求
验证: 限流器实现后，请求频率不超过3次/秒
```

### Scenario 14: getSubDomain多级TLD验证（P0）

```
给定: Cookie来自 mail.example.co.uk
当: getSubDomain("http://mail.example.co.uk")
预期: 返回 "example.co.uk"（不是 "mail.example.co.uk"）
验证: PublicSuffixDatabase正确处理多级TLD
```

### Scenario 15: 搜索阶段ruleData注入验证（P0）

```
给定: 书源搜索URL的JS规则中访问 result.bookUrl
当: 执行搜索调试
预期: ruleData为独立RuleData()（bookUrl为空），不是book对象
验证: 搜索URL的JS规则中访问ruleData属性行为与真机一致
```

### Scenario 16: 详情阶段类型重置验证（P0）

```
给定: 文件类书源（bookSourceType=3）
当: 执行详情调试
预期: book.type被设置为webFile位(0b10000000)，isWebFile判断为true
验证: 文件类书源正确跳过目录解析
```

### Scenario 17: AnalyzeUrl多余功能移除验证（P1）

```
给定: 书源header中使用@js:语法
当: 执行调试
预期: 仿真端不执行header JS（对齐真机行为）
验证: 移除followRedirects/header JS/ajax override后，调试结果与真机一致
```

### Scenario 18: loginCheckJs检测验证（P1）

```
给定: 书源配置了loginCheckJs
当: 搜索/RSS阶段获取响应后
预期: 执行loginCheckJs检测登录态
验证: 需要登录的书源正确检测登录状态
```

### Scenario 19: Book数据模型默认值验证（P1）

```
给定: 新建Book对象
当: 检查type和origin默认值
预期: type = BookType.text(0b1)，origin = "loc_book"
验证: 数据模型默认值与真机一致
```

### Scenario 20: loginCheckJs全阶段检测验证（P0，第五轮）

```
给定: 书源配置了loginCheckJs
当: 执行搜索/详情/目录/正文/RSS调试
预期: 所有阶段获取响应后执行loginCheckJs检测
验证: 需要登录的书源所有阶段正确检测登录态
```

### Scenario 21: ruleNextPage=="PAGE"分页验证（P0，第五轮）

```
给定: 书源目录/正文使用ruleNextPage=="PAGE"分页
当: 执行目录/正文调试
预期: 使用page变量分页，{{page}}替换为页码
验证: PAGE分页的书源目录/正文正确获取多页内容
```

### Scenario 22: 正文格式化链验证（P0，第五轮）

```
给定: 书源正文包含HTML实体/自定义字体/替换规则
当: 执行正文调试
预期: HtmlFormatter.formatKeepImg + StringEscapeUtils.unescapeHtml4 + useHtmlMap + replaceRegex全部执行
验证: 正文格式化结果与真机一致
```

### Scenario 23: WrapFactory+instructionObserverThreshold验证（P0，第五轮，第七轮修正）

```
给定: 书源JS规则中访问source对象属性 + 死循环源规则
当: 执行JS规则
预期: WrapFactory正确包装source对象（移除对ClassShutter的调用） + instructionObserverThreshold触发后自定义observeInstructionCount直接抛TimeoutException中断死循环
验证: source.setXxx在JS中生效 + 死循环源规则被中断不卡死调试
注: 第七轮修正（AD-11），不移植ClassShutter，修改WrapFactory移除对其的调用。不移植RhinoContext，自定义observeInstructionCount实现。
```

### Scenario 24: withTimeout超时控制验证（P0，第五轮，第七轮修正）

```
给定: 书源设置超时时间 + HTTP请求超时
当: 请求超时
预期: withTimeout超时控制生效，请求被中断
验证: 超时请求不卡死调试
注: 第七轮修正（AD-12），不替换runBlocking→Coroutine，只添加withTimeout超时控制。
```

### Scenario 25: 内存存储验证（P0，第六轮，第七轮修正）

```
给定: 调试过程中保存BookSource/BookChapter/Cookie
当: 在同一会话内多次调试
预期: 数据在内存Map中正确保持，会话内可读取
验证: ConcurrentHashMap内存存储在会话内正常工作
注: 第七轮修正，GAP-67重新设计为内存存储，不引入SQLite/H2数据库。单次调试会话不需要持久化。
```

### Scenario 26: HTTP拦截器验证（P0，第六轮）

```
给定: 书源未显式设置UA
当: 仿真端发送HTTP请求
预期: 自动注入Chrome UA（不是okhttp/4.x）
验证: UA注入行为与真机一致
```

### Scenario 27: CookieJar自动管理验证（P1，第六轮）

```
给定: 书源设置enabledCookieJar=true
当: 仿真端发送HTTP请求
预期: CookieJar拦截器自动loadRequest/saveResponse
验证: Cookie自动管理行为与真机一致
```

### Scenario 28: ~~DecompressInterceptor验证~~ ⚠️ 可选修复（第七轮修正）

```
给定: 网站返回Content-Encoding: deflate
当: 仿真端获取响应
预期: ~~DecompressInterceptor自动解压deflate~~
验证: ~~deflate压缩的网站可正确解析~~
注: 第七轮修正，OkHttp内置透明gzip解压，但deflate需额外处理。降级为可选修复，遇到实际deflate压缩的网站再移植DecompressInterceptor。
```

### Scenario 29: 100%测试校验准确性评估（第七轮修正）

```
给定: 所有必需修复完成（52个P0+P1+基础对齐）
当: 用100个真实源全量测试
预期: 排除网站问题后，JAR测试通过的源真机也能通过，JAR测试失败的源能准确区分源规则问题还是仿真端问题
验证: 对于不依赖WebView/UI/Android原生的源，达到100%测试校验准确性
注: 第七轮修正，设计目标从"100%兼容运行"修正为"100%测试校验准确性"。不追求完全复刻真机（持久化/安全沙箱/性能差异等不影响校验结果的行为不修复）。75个过度修复项不实施，10个GAP重新设计为更简单替代方案。
```
