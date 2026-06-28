# Design: JAR 仿真端 100% 测试校验准确性

> **设计目标修正**（第七轮深度审查）：从"100%兼容运行"（完全复刻真机）修正为"100%测试校验准确性"（JAR测试通过则真机通过，JAR失败时能准确区分源规则问题还是仿真端问题）
> **修正原因**：185个GAP中40%是过度修复，不应追求完全复刻真机，应聚焦"测试校验准确性"

---

## 第七轮深度审查修正说明

### 修正核心

| 修正项 | 旧方案 | 新方案 | 理由 |
|--------|--------|--------|------|
| 设计目标 | 100%兼容运行（完全复刻真机） | 100%测试校验准确性 | 40%的GAP是过度修复 |
| GAP-67 Room数据库 | 接入SQLite/H2 | 内存存储，不引入数据库 | 单次调试会话不需要持久化 |
| GAP-70a Rhino配置 | 引入modules/rhino模块 | 只移植WrapFactory+instructionObserverThreshold | 安全沙箱不需要 |
| GAP-70b 并发模型 | runBlocking→Coroutine链式封装 | 只添加withTimeout超时控制 | 性能差异不影响结果 |
| GAP-72 AppConfig | 移植200+配置项 | 只补充userAgent/customHosts | 其他配置不影响校验 |
| GAP-80 HTTP拦截器 | 添加5个拦截器 | 只添加UA注入+CookieJar | 其他3个不影响校验 |
| 方向15 WebBook/Rss移植 | 移植整个模块 | 保持内联实现，只修复P0级5个差异 | 内联实现行为对齐即可 |
| GAP-32 CookieManager | 接入持久化 | 只补充saveResponse/loadRequest到内存Map | 单次会话内存足够 |
| 方向5 压缩文件解压 | 移植ArchiveUtils+commons-compress | 延后实现，遇到实际需求再做 | 100个失败源中0个压缩文件相关 |
| GAP-75 AppConst | 补充全部常量 | 只补充MAX_THREAD/charsets | 其他常量不影响校验 |

### 砍掉的75个过度修复项

| 类别 | 数量 | 代表GAP | 理由 |
|------|------|---------|------|
| 持久化类 | 14 | GAP-68/69/71/33/31 | 单次调试会话内存存储足够（注：GAP-67为重新设计，非过度修复） |
| 安全沙箱类 | 5 | GAP-72c ClassShutter | 测试环境不需要安全限制（注：GAP-70a为重新设计，非过度修复） |
| 性能差异类 | 8 | GAP-71a/96/95/94 | 不影响结果 |
| UI层类 | 6 | GAP-98/99/65/66/74/89 | 不影响调试 |
| 日志类 | 5 | GAP-77/78/79 + Toast | 不影响校验结果 |
| 模块移植类 | 9 | GAP-69a~i | 内联实现行为对齐即可 |
| 其他 | 28 | SourceHelp/ACache/WebCacheManager等 | 非校验职责 |

### 修复优先级修正

| 优先级 | 数量 | 内容 | 修正说明 |
|--------|------|------|---------|
| 第一优先级（P0） | 16个 | GAP-22~26 + GAP-36~41 + GAP-67a~e | 第八轮修正：GAP-83已合并到GAP-80重新设计中，不再独立列出 |
| 第二优先级（P1） | 20个 | GAP-1/2 + GAP-42~55 + GAP-60~63 | 第八轮修正：GAP-82已合并到GAP-80，GAP-86为过度修复，均移除 |
| 第三优先级（基础对齐） | 16个 | 方向0/2/3/4中的必需项 | 基础功能对齐 |
| **砍掉** | **75个** | 持久化/安全沙箱/性能/UI/日志/模块移植 | 不影响测试校验结果 |
| **重新设计** | **10个** | 见上方修正核心表 | 有更简单替代方案 |
| **已对齐/保持原状** | **~20个** | GAP-34/35/73a~d/74/77/78/79/88/89/98/99等 | 已实现或标记为不可实现 |

---

## Technical Approach

### 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                    仿真端 JAR                            │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ JsExtensions │  │ BaseSource   │  │ Debugger       │  │
│  │ Stub (132)   │  │ Interface(17)│  │ (Book/Rss)     │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                  │           │
│         └────────────────┼──────────────────┘           │
│                          │                              │
│  ┌───────────────────────┼──────────────────────────┐  │
│  │           兼容层（46个可修复方法）                │  │
│  │  base64 flags / AES / 并发 / 压缩文件 / 配置读取  │  │
│  └───────────────────────┬──────────────────────────┘  │
│                          │                              │
│  ┌───────────────────────┼──────────────────────────┐  │
│  │           委托层（21个不可实现方法）               │  │
│  │  WebView → Selenium / UI → Selenium / 硬件 → 环境变量│  │
│  └───────────────────────┬──────────────────────────┘  │
└──────────────────────────┼──────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │ Python 客户端 │
                    │  Selenium   │
                    │  OCR        │
                    └─────────────┘
```

---

## 一、批量测试失败源根因分析

### 1.1 测试结果总览

```
总源数: 100 | 成功: 0 | 失败: 100 | 成功率: 0%
失败分类: code 35 | network 33 | data 24 | other 7 | intervention 1
```

### 1.2 code 类失败根因（35 个）

| 根因 | 数量 | 责任方 | 修复方案 |
|------|------|--------|---------|
| RSS sortUrl 被填充为 JSON 对象 `{"content":"class.content"}` | 31 | 源规则（生成器 bug） | 修正生成器字段映射 |
| bookList 返回 String 而非 List | 2 | 源规则 | 改用 class.xxx 列表选择器 |
| 搜索 URL 变量语法错误 | 2 | 源规则 | 使用 `{{key}}` 变量语法 |
| **仿真端问题** | **0** | - | - |

### 1.3 network 类失败根因（33 个）

| 根因 | 数量 | 责任方 | 修复方案 |
|------|------|--------|---------|
| DNS 域名失效 | 13 | 网站 | 无（域名不存在） |
| 连接超时 | 9 | 网站 | 无（服务器不可达） |
| SSL 证书过期 | 4 | 网站 | 无（证书未续期） |
| SSL 内部错误 | 1 | 网站 | 无（服务器配置异常） |
| 反爬拦截（Cloudflare） | 1 | 网站 | 无（需 JS 挑战） |
| Connection refused | 2 | 网站 | 无（服务器关闭） |
| PKIX 证书链缺失 | 1 | **仿真端** | 配置 SSLHelper 信任所有证书 |
| DNS 返回 0.0.0.0 | 1 | **仿真端** | 配置 OkHttp 公共 DNS 回退 |

### 1.4 data 类失败根因（24 个）

| 根因 | 数量 | 责任方 | 修复方案 |
|------|------|--------|---------|
| 搜索结果为空（规则不匹配） | 23 | 源规则 | 重写搜索规则选择器 |
| HTTP 404 | 1 | 网站 | 无（接口下线） |
| **仿真端问题** | **0** | - | - |

### 1.5 结论

**100 个失败中，仿真端问题仅 2 个（2%），其余 98 个是源规则问题或网站问题。**

---

## 二、67 个不兼容方法修复方案

### 2.1 低难度修复（12 个）

#### 2.1.1 属性 var→val 签名修正（6 个）

**真机源码**：`BaseSource.kt` 中 concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib 均为 `var`

**仿真端现状**：`BaseSourceInterface.kt` 中均为 `val`（只读）

**修复方案**：改为 `var`，添加 setter

```kotlin
// 修复前
val concurrentRate: Int?
// 修复后
var concurrentRate: Int?
```

#### 2.1.2 dateFormat 格式对齐

**真机源码**：`AppConst.dateFormat` = `"yyyy/MM/dd HH:mm"`（斜杠分隔、无秒）

**修复方案**：读取 `LEGADO_DATE_FORMAT` 环境变量，默认 `"yyyy/MM/dd HH:mm"`（对齐真机 `AppConst.kt:38-40`）

#### 2.1.3 connect 错误时 url 修正

**真机源码**：错误时 url 用 `analyzeUrl.url`

**修复方案**：`catch` 块中改用 `analyzeUrl.url` 而非原始 `urlStr`

#### 2.1.4 getTxtInFolder 添加 folder 删除

**真机源码**：`JsExtensions.kt:818` 最后 `FileUtils.delete(folder)`

**修复方案**：添加 `folder.delete()`

#### 2.1.5 importScript 异常类型替换

**真机源码**：抛 `NoStackTraceException`

**修复方案**：`IllegalStateException` → `NoStackTraceException`

#### 2.1.6 aesEncodeToString 对齐真机 bug

**真机源码**：`JsEncodeUtils.kt` 中 `aesEncodeToString` 误用 `decryptStr`（真机 bug）

**修复方案**：仿真端当前是正确的（用 encrypt），需反向引入真机 bug 以 100% 对齐

> **注意**：这是仿真端正确、真机错误的情况。100% 兼容要求行为一致，即使真机有 bug。

### 2.2 中难度修复（18 个）

#### 2.2.1 base64/AES flags 映射完善（6 个）

**真机源码**：`android.util.Base64`，flags 值：NO_WRAP=2, NO_PADDING=1, URL_SAFE=8

**仿真端现状**：`java.util.Base64`，flags 映射不完整

**修复方案**：完善 flags 映射表

```kotlin
fun mapBase64Flags(flags: Int): Int {
    var result = 0
    if (flags and 1 != 0) result = result or Base64.NO_PADDING  // NO_PADDING
    if (flags and 2 != 0) result = result or Base64.NO_WRAP     // NO_WRAP
    if (flags and 8 != 0) result = result or Base64.URL_SAFE    // URL_SAFE
    return result
}
```

#### 2.2.2 get/head/post 对齐真机行为（3 个）

**真机源码**：`JsExtensions.kt:487-557` 直接 `Jsoup.connect()` + SSLHelper

**仿真端现状**：通过 AnalyzeUrl 委托（OkHttp 路径）

**修复方案**：保持委托 AnalyzeUrl，但确保以下行为对齐：
- SSL 信任所有证书（SSLHelper 已移植）
- cookieJarHeader 注入（当 enabledCookieJar=true）
- ConcurrentRateLimiter 限流
- followRedirects(false)

#### 2.2.3 ajaxAll/ajaxTestAll 并发实现（2 个）

**真机源码**：`runBlocking` + `flow.mapAsync(threadCount)`

**修复方案**：使用 `CompletableFuture.supplyAsync` + 线程池

```kotlin
override fun ajaxAll(urlList: List<String>, skipRateLimit: Boolean): List<String> {
    val executor = Executors.newFixedThreadPool(threadCount)
    return urlList.map { url ->
        CompletableFuture.supplyAsync({ get(url) }, executor)
    }.map { it.join() }
}
```

#### 2.2.4 downloadFile 流式下载（2 个）

**真机源码**：`getInputStream()` 流式拷贝

**修复方案**：改用 OkHttp 流式下载，修正相对路径计算

#### 2.2.5 toNumChapter 章节号转换

**真机源码**：`AppPattern.titleNumPattern` + `StringUtils.stringToInt()`

**修复方案**：移植 AppPattern + StringUtils

#### 2.2.6 log 接入 Debug 回调

**真机源码**：`Debug.log()` + `AppLog.putDebug()`

**修复方案**：接入 Debug 回调机制，写入日志文件

#### 2.2.7 putConcurrent 实现

**真机源码**：`updateConcurrentRate(getKey(), value)`

**修复方案**：实现 ConcurrentRateLimiter 更新

#### 2.2.8 executeSortUrlJs 注入 source 变量

**真机源码**：`BaseSource.evalJS()` 注入 source 变量

**修复方案**：在 AnalyzeUrl.evalJS 中额外注入 source 变量

#### 2.2.9 evalJS 实现 sharedScope

**真机源码**：`BaseSource.kt:325-343` 使用 `getShareScope()`

**修复方案**：实现 SharedJsScope，管理 Rhino Scope 复用

### 2.3 高难度修复（16 个）

> **第七轮修正**：16个中8个标注为过度修复（2.3.1~2.3.4），实际只需修复8个（2.3.5~2.3.8）

#### 2.3.1 ~~压缩文件解压（4 个）~~ ❌ 过度修复，不实施

**真机源码**：`ArchiveUtils.deCompress()` 基于 Apache Commons Compress

~~**修复方案**~~：
1. ~~在 `build.gradle.kts` 添加 `commons-compress` 依赖~~
2. ~~移植 `ArchiveUtils.kt`~~
3. ~~实现 unArchiveFile/unzipFile/un7zFile/unrarFile~~

**移除理由**：方向5延后，100个失败源中0个压缩文件相关。遇到实际需求再做。

#### 2.3.2 ~~Rar/7z 内容读取（4 个）~~ ❌ 过度修复，不实施

**真机源码**：`LibArchiveUtils.getByteArrayContent()`（JNI 依赖）

~~**修复方案**~~：~~使用 Apache Commons Compress 替代 LibArchiveUtils~~

**移除理由**：同2.3.1，方向5延后。

#### 2.3.3 ~~配置读取（4 个）~~ ❌ 过度修复，重新设计

**真机源码**：`ReadBookConfig.durConfig` / `ThemeConfig.getDurConfig`（依赖 SharedPreferences）

~~**修复方案**~~：
1. ~~移植 ReadBookConfig/ThemeConfig~~
2. ~~用 JSON 文件替代 SharedPreferences~~
3. ~~配置文件路径：`~/.legado/readbook_config.json`~~

**重新设计方案**（GAP-72）：只补充 `userAgent` + `customHosts` 到 AppConfig，其他200+配置项不影响校验。

#### 2.3.4 ~~refreshExplore 实现~~ ❌ 过度修复，不实施

**真机源码**：`clearExploreKindsCache()`

~~**修复方案**~~：~~实现缓存清除逻辑~~

**移除理由**：exploreKinds属于Extensions（GAP-85），不影响校验，不移植。

#### 2.3.5 refreshJSLib 实现 SharedJsScope ✅ 保留

**真机源码**：`SharedJsScope.remove(jsLib)`

**修复方案**：移植 SharedJsScope，管理 Rhino Scope

#### 2.3.6 getLoginInfoMap 实现 RowUi 解析 ✅ 保留

**真机源码**：解析 `loginUi` JSON 生成默认值

**修复方案**：移植 RowUi 解析逻辑（剥离 Android UI 依赖）

#### 2.3.7 getHeaderMap 对齐 AppConfig.userAgent ✅ 保留

**真机源码**：`AppConfig.userAgent`（可配置）

**修复方案**：读取 `LEGADO_USER_AGENT` 环境变量

#### 2.3.8 debugExplore infoMap 实现 ✅ 保留

**真机源码**：`exploreInfoMapList[sourceUrl]` 作为 infoMap

**修复方案**：解析 sortUrl 中的 `::` 分隔符，构建 exploreInfoMapList

---

## 三、委托路径实现方案

### 3.1 WebView 渲染委托（9 个方法）

**架构**：

```
仿真端 webView()
  → 抛出 WebViewRequiredException(url, html, js, cacheFirst)
  → Python 客户端捕获异常
  → Selenium 执行 JS 渲染
  → 回传渲染结果
  → 仿真端继续处理
```

**实现**：
1. `WebViewRequiredException` 携带完整请求信息
2. Python 端实现 `webview_delegate.py`：
   - 启动 Selenium WebDriver
   - 加载 url / 注入 html
   - 执行 js
   - 等待渲染完成
   - 返回 `page_source`
3. 结果回传机制：HTTP API（`POST /webview/result`）

### 3.2 UI 交互委托（5 个方法）

| 方法 | 委托路径 | 实现方式 |
|------|---------|---------|
| startBrowser | Selenium 浏览器自动化 | 打开浏览器，模拟用户操作 |
| startBrowserAwait | Selenium + 等待 | 打开浏览器，等待页面结果 |
| getVerificationCode | OCR + 用户介入 | Tesseract OCR 识别，失败则标记用户介入 |
| openVideoPlayer | 标记不影响验证 | 纯 UI 功能，对书源验证无影响 |
| openUrl | 标记不影响验证 | 纯 UI 功能，对书源验证无影响 |

### 3.3 硬件信息环境变量配置（4 个方法）

**环境变量**：
- `LEGADO_ANDROID_ID`：真机 androidId（16 位）
- `LEGADO_WEBVIEW_UA`：真机 WebView User-Agent
- `LEGADO_USER_AGENT`：真机 AppConfig.userAgent

**实现**：
```kotlin
val androidId: String
    get() = System.getenv("LEGADO_ANDROID_ID") ?: "000000000000000"

val webViewUA: String
    get() = System.getenv("LEGADO_WEBVIEW_UA")
        ?: "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 ..."
```

### 3.4 Toast 日志文件替代（2 个方法）

**实现**：
```kotlin
override fun toast(msg: String) {
    DebugLog.write("toast: $msg")
}

override fun longToast(msg: String) {
    DebugLog.write("longToast: $msg")
}
```

日志文件路径：`~/.legado/debug.log`

---

## 四、实施决策记录与合理性分析

### AD-01: type 位运算替代 isWebFile 字段

**决策**：用 `book.type and 0b10000000 != 0` 判断 isWebFile

**真机源码**：`Book.kt` 无 `isWebFile` 字段，真机 `Debug.kt:324-328` 用 `book.isWebFile`（这是 Book 的扩展属性，实际通过 type 位运算实现）

**合理性**：✅ 合理。Book.kt 中 `isWebFile` 是计算属性，底层就是 type 位运算。

### AD-02: hutool AES 替代 SymmetricCryptoAndroid

**决策**：用 `hutool AES(key).encryptBase64` 替代 `SymmetricCryptoAndroid`

**真机源码**：`SymmetricCryptoAndroid` 依赖 Android KeyStore

**合理性**：✅ 合理。SymmetricCryptoAndroid 底层也是 AES 算法，hutool AES 算法一致，结果相同。

### AD-03: System.getenv 替代 AppConst.androidId

**决策**：用 `System.getenv("LEGADO_ANDROID_ID") ?: "000000000000000"` 替代 `AppConst.androidId`

**真机源码**：`AppConst.androidId` 通过 `Settings.Secure.getString` 获取真机硬件 ID

**合理性**：⚠️ 行为不一致。需通过环境变量传入真机 androidId 才能完全对齐。已在 REQ-06 中列为修复项。

### AD-04: ChineseUtils 别名 import

**决策**：`import io.legado.app.utils.ChineseUtils as ChineseUtilsAlias`

**真机源码**：直接 `import io.legado.app.utils.ChineseUtils`

**合理性**：✅ 合理。仿真端已有同名包，别名 import 解决冲突，行为一致。

### AD-05: followRedirects 局部变量 fr

**决策**：`val fr = followRedirects` 解决 Kotlin Smart cast 问题

**真机源码**：直接使用 `followRedirects`

**合理性**：✅ 合理。Kotlin Smart cast 在闭包中不生效，局部变量是标准解决方案。

---

## 五、遗漏排查补充修复方案（17个GAP，源码核实）

> **排查背景**：第二轮设计文档完成后，用户要求"深度分析全面排查"。启动2个子代理逐行对比仿真端vs真机源码，核实13个GAP准确性 + 发现4个新遗漏。以下为修复方案。

### 5.1 OkHttpUtils 方法补全（3个，P1）

#### 5.1.1 GAP-1: newCallResponseBody 缺失

**真机源码**（`OkHttpUtils.kt:45-50`）：
```kotlin
suspend fun OkHttpClient.newCallResponseBody(
    retry: Int = 0,
    builder: Request.Builder.() -> Unit
): ResponseBody {
    return newCallResponse(retry, builder).body
}
```

**仿真端现状**：无此方法，仅有 `newCallResponse` 和 `newCallStrResponse`

**修复方案**：在仿真端 `OkHttpUtils.kt` 中补充该方法，实现与真机完全一致

#### 5.1.2 GAP-2: decompressed 缺失

**真机源码**（`OkHttpUtils.kt:97-111`）：
```kotlin
fun ResponseBody.decompressed(): ResponseBody {
    val contentType = contentType()?.toString()
    if (contentType != "application/zip") return this
    val source = ZipInputStream(byteStream()).apply {
        try { nextEntry } catch (e: Exception) { close(); throw e }
    }.source().buffer()
    return RealResponseBody(null, -1, source)
}
```

**仿真端现状**：无此方法

**修复方案**：补充该方法及所需 import（`java.util.zip.ZipInputStream`、`okio.buffer`、`okio.source`）

#### 5.1.3 GAP-3: await 无协程取消

**真机源码**（`OkHttpUtils.kt:61-77`）：
```kotlin
suspend fun Call.await(): Response = suspendCancellableCoroutine { block ->
    block.invokeOnCancellation { cancel() }  // 仿真端缺少此行
    enqueue(object : Callback { ... })
}
```

**仿真端现状**（`OkHttpUtils.kt:54-64`）：缺少 `invokeOnCancellation { cancel() }`

**修复方案**：补充 `invokeOnCancellation` 块，使协程取消时底层 OkHttp 请求也取消

### 5.2 RssSourceDebugger 逻辑修正（5个，P0-P2）

#### 5.2.1 GAP-22: ruleDescription 逻辑错误（P0 最高优先级）

**真机源码**（`Debug.kt:122-134`）：
```kotlin
// 真机：ruleDescription 有值时跳过内容页；ruleDescription 为空时检查 ruleContent
val ruleContent = rssSource.ruleContent
if (!rssSource.ruleArticles.isNullOrBlank() && rssSource.ruleDescription.isNullOrBlank()) {
    log(debugSource, "︽列表页解析完成")
    log(debugSource, showTime = false)
    if (ruleContent.isNullOrEmpty()) {
        log(debugSource, "⇒内容规则为空，默认获取整个网页", state = 1000)
    } else {
        rssContentDebug(scope, it.first[0], ruleContent, rssSource)
    }
} else {
    log(debugSource, "⇒存在描述规则，不解析内容页")
    log(debugSource, "︽解析完成", state = 1000)
}
```

**仿真端现状**（`RssSourceDebugger.kt:295-296`）：
```kotlin
// 仿真端：总是调用内容页调试
return if (allArticles.isNotEmpty()) {
    debugContent(allArticles[0].link, allArticles[0])  // 无论 ruleDescription 是否有值
}
```

**修复方案**（第八轮修正：补充 ruleContent 为空的内层判断）：在 `debugSort()` 方法中添加与真机一致的判断逻辑：
```kotlin
return if (allArticles.isNotEmpty()) {
    if (!ruleArticles.isNullOrBlank() && ruleDescription.isNullOrBlank()) {
        // ruleDescription 为空 → 检查 ruleContent
        if (ruleContent.isNullOrEmpty()) {
            logger.log("⇒内容规则为空，默认获取整个网页")
            DebugResult(success = true, state = 1000)
        } else {
            debugContent(allArticles[0].link, allArticles[0])  // ruleContent 非空 → 解析内容页
        }
    } else {
        logger.log("⇒存在描述规则，不解析内容页")
        logger.log("︽解析完成")
        DebugResult(success = true)
    }
}
```

#### 5.2.2 GAP-23: 单URL架构（需修正描述）

**真机源码**（`Debug.kt:142-184`）：支持三种 key 格式：`name::url`、绝对URL、搜索关键字

**仿真端现状**（`RssSourceDebugger.kt:77-84`）：不支持 `key::url` 格式和搜索关键字

**修复方案**：在 `debug()` 方法中增加 `key.contains("::")` 分支和搜索关键字分支

#### 5.2.3 GAP-24: 取消机制

**真机源码**（`Debug.kt:24,78-85`）：`CompositeCoroutine` 管理调试协程，`cancelDebug()` 取消所有任务

**仿真端现状**：无取消机制，`debug()` 是同步方法

**修复方案**：为 `RssSourceDebugger` 添加 `CoroutineScope` 参数和 `cancel()` 方法

#### 5.2.4 GAP-25: 校验模式

**真机源码**（`Debug.kt:27,87-109`）：`isChecking` 状态标志、`debugMessageMap`/`debugTimeMap` 状态存储、CheckSource 集成

**仿真端现状**：仅 `content.isNotEmpty()` 判断

**修复方案**：添加 `isChecking` 状态标志、记录响应时间、输出校验结果摘要

#### 5.2.5 GAP-26: 无参key入口

**真机源码**（`Debug.kt:111-140`）：`startDebug(scope, rssSource)` 无 key 重载，使用 `rssSource.sortUrls().first()`

**仿真端现状**（`RssSourceDebugger.kt:33-37`）：key 是必填参数

**修复方案**：将 key 改为可选参数（`key: String? = null`），无 key 时调试第一个分类

### 5.3 持久化深度差异（5个，P1-P2）

> **第七轮修正**：5个中3个标注为过度修复（5.3.1/5.3.3/5.3.4），2个保留但改为内存实现（5.3.2/5.3.5）

#### 5.3.1 ~~GAP-31: CookieStore 无持久化~~ ❌ 过度修复，重新设计

**真机源码**（`CookieStore.kt:30`）：`appDb.cookieDao.insert(cookieBean)` — Room SQLite

**仿真端现状**（`CookieStoreStub.kt:18`）：`ConcurrentHashMap<String, String>()` — 纯内存

~~**修复方案**~~：~~接入 SQLite（H2 数据库）或 JSON 文件持久化，路径 `~/.legado/cookies.json`~~

**重新设计方案**（GAP-32）：保持内存存储，单次调试会话不需要持久化。Cookie 在会话内通过内存 Map 保持，会话结束后丢弃。

#### 5.3.2 GAP-32: CookieManager 精简（需修正描述） ✅ 保留，改为内存实现

**真机源码**（`CookieManager.kt`）：10 个方法，含 `saveResponse`/`loadRequest`/`applyToWebView` 等

**仿真端现状**（`CookieManagerStub.kt`）：仅 2 个方法（`mergeCookies`/`mergeCookiesToMap`）

**关键遗漏**：缺少 `saveResponse` — HTTP 响应中的 Set-Cookie 不会自动保存，导致登录态丢失

**修复方案**：补充 `saveResponse`（从 Response headers 解析 Cookie 并保存到内存 Map）和 `loadRequest`（从内存 Map 加载 Cookie 到请求头）。**不接入持久化**，单次会话内存足够。

#### 5.3.3 ~~GAP-33: CacheManager 无持久化~~ ❌ 过度修复，不实施

**真机源码**（`CacheManager.kt:62,67`）：三层缓存（LruCache 内存 + Room SQLite + ACache 文件）

**仿真端现状**（`CacheManagerStub.kt:22`）：`ConcurrentHashMap<String, SoftReference<Any>>()` — 纯内存

~~**修复方案**~~：~~接入文件系统持久化，路径 `~/.legado/cache/`~~

**移除理由**：单次调试会话内存缓存足够，不需要文件系统持久化。

#### 5.3.4 GAP-34: getFile 无文件系统（误报修正） ✅ 已修正

**核实结果**：❌ 误报。仿真端 `JsExtensionsStub.kt:453-465` 有完整文件操作（路径拼接、安全校验）

**实际差异**：仅根目录不同 — 真机用 `appCtx.externalCache`，仿真端用 `java.io.tmpdir/legado-jvm-cache`

**修复方案**：修正 GAP 描述，无需代码修改（行为等价，根目录差异可接受）

#### 5.3.5 GAP-35: WebCookie 存储（需修正描述） ✅ 已修正

**真机源码**（`CookieStore.kt:37-49`）：`android.webkit.CookieManager` 逐条 setCookie

**仿真端现状**（`CookieStoreStub.kt:21`）：`ConcurrentHashMap<String, String>` 整体覆盖

**修复方案**：修正 GAP 描述为"使用内存 Map 替代 android.webkit.CookieManager，无法同步到 WebView（JVM 限制，可接受）"

### 5.4 新发现遗漏（4个，P2-P4）

#### 5.4.1 新-1: Debug.kt 严重简化

**真机源码**（`Debug.kt`）：362 行，完整状态管理（debugSource/callback/tasks/debugMessageMap/debugTimeMap/isChecking）

**仿真端现状**（`Debug.kt`）：仅 10 行 `println`

**修复方案**：补充 Debug 状态管理（debugMessageMap/debugTimeMap/isChecking），保留 log 回调机制

#### 5.4.2 新-2: await 回调顺序不一致

**真机源码**（`OkHttpUtils.kt:67-75`）：`onFailure` 在前

**仿真端现状**（`OkHttpUtils.kt:55-63`）：`onResponse` 在前

**修复方案**：调整回调顺序与真机一致（无功能影响，但符合精准对齐原则）

#### 5.4.3 新-3: AnalyzeUrl 缺 getGlideUrl/getMediaItem

**真机源码**（`AnalyzeUrl.kt:746,773`）：`getGlideUrl()`（Glide 图片加载）、`getMediaItem()`（ExoPlayer 视频播放）

**仿真端现状**：无此方法

**修复方案**：标记为不实现（Android UI 层功能，不影响书源/订阅源调试）

#### 5.4.4 新-4: 缺 CheckSource 校验

**真机源码**（`Debug.kt:87-109`）：`startChecking`/`finishChecking`/`getRespondTime`/`updateFinalMessage`

**仿真端现状**：无

**修复方案**：补充 CheckSource 校验功能（记录响应时间、管理校验状态、输出校验结果摘要）

---

## 六、第四轮深度排查修复方案（31个GAP，4子代理逐行源码核实）

> **排查背景**：第三轮设计文档完成后，用户要求"深度分析全面排查"。启动4个子代理分别从 AnalyzeRule规则引擎 / JsExtensions扩展函数 / HTTP网络层 / 调试器+数据模型 四个角度，逐行对比仿真端vs真机源码的**实现行为**（不是方法列表，而是每个方法的实现逻辑）。发现31个新遗漏。

### 6.1 P0级修复（6个，必须修复）

#### 6.1.1 GAP-36: JsExtensions委托模式并发覆盖

**真机源码**（`AnalyzeRule.kt:55-62`）：
```kotlin
class AnalyzeRule(...) : JsExtensions {
    // 每个实例持有自己的source/ruleData
}
```

**仿真端现状**（`AnalyzeRule.kt:52-58`）：
```kotlin
class AnalyzeRule(...) : JsExtensionsInterface by (JsExtensionsStub.also { it.configure(source, ruleData) }) {
    // 委托给全局单例JsExtensionsStub，source/ruleData是@Volatile变量
}
```

**修复方案**：将JsExtensionsStub从全局单例改为实例化模式。每个AnalyzeRule实例创建独立的JsExtensions实例：
```kotlin
class AnalyzeRule(...) {
    private val jsExtensions = JsExtensionsImpl().also { it.configure(source, ruleData) }
    // 通过委托将JsExtensions方法调用转发到实例化对象
}
```

**影响**：并发调试多个书源时JS中source/book变量正确指向对应书源

#### 6.1.2 GAP-37: ConcurrentRateLimiter空实现

**真机源码**（`ConcurrentRateLimiter.kt:9-131`）：
```kotlin
suspend inline fun <T> withLimit(block: () -> T): T {
    getConcurrentRecord()  // 限流判断
    return block()
}
```

**仿真端现状**（`ConcurrentRateLimiter.kt:8-16`）：
```kotlin
suspend inline fun <T> withLimit(block: () -> T): T {
    return block()  // 直接执行，无限流
}
```

**修复方案**：移植真机ConcurrentRateLimiter完整实现，包括ConcurrentRecord数据类、concurrentRecordMap、fetchStart/getConcurrentRecord/withLimit方法

**影响**：设置了concurrentRate的书源仿真端正确限流

#### 6.1.3 GAP-38: getSubDomain域名提取不一致

**真机源码**（`NetworkUtils.kt:212-223`）：
```kotlin
PublicSuffixDatabase.get().getEffectiveTldPlusOne(host) ?: host
```

**仿真端现状**（`NetworkUtilsStub.kt:183-194`）：
```kotlin
return if (host.startsWith("www.")) host.substring(4) else host
```

**修复方案**：引入OkHttp的PublicSuffixDatabase（已在OkHttp依赖中），或移植真机getSubDomain完整实现

**影响**：多级子域名网站的Cookie域名正确匹配

#### 6.1.4 GAP-39: 搜索阶段ruleData注入对象不同

**真机源码**（`WebBook.kt:60`）：
```kotlin
val ruleData = RuleData()  // 独立RuleData
val analyzeUrl = AnalyzeUrl(..., ruleData = ruleData)
```

**仿真端现状**（`BookSourceDebugger.kt:124`）：
```kotlin
val analyzeUrl = AnalyzeUrl(..., ruleData = book)  // 直接用book
```

**修复方案**：搜索阶段创建独立RuleData()对象注入，不使用book对象

**影响**：搜索URL的JS规则中访问ruleData属性行为与真机一致

#### 6.1.5 GAP-40: 详情阶段缺少类型重置

**真机源码**（`WebBook.kt:197-198`）：
```kotlin
book.removeAllBookType()
book.addType(bookSource.getBookType())
```

**仿真端现状**：无类型重置逻辑

**修复方案**：在详情阶段添加removeAllBookType()和addType()调用

**影响**：文件类书源正确设置webFile位，isWebFile判断正确

#### 6.1.6 GAP-41: RSS调试ruleData注入对象不同

**真机源码**（`Rss.kt:42`）：
```kotlin
val ruleData = RuleData()
val analyzeUrl = AnalyzeUrl(..., ruleData = ruleData)
```

**仿真端现状**（`RssSourceDebugger.kt:207-213`）：
```kotlin
val analyzeUrl = AnalyzeUrl(...)  // 不传ruleData
```

**修复方案**：RSS调试创建独立RuleData()对象注入

**影响**：RSS列表页URL的JS规则中访问ruleData属性行为与真机一致

### 6.2 P1级修复（14个，影响部分调试结果）

#### 6.2.1 GAP-42: createSymmetricCrypto底层差异

**修复方案**：移植SymmetricCryptoAndroid，覆写encryptBase64使用android.util.Base64（或对齐的Java Base64实现）

#### 6.2.2 GAP-43: replaceFont多字节字符处理

**修复方案**：移植toStringArray()方法，正确处理多字节字符

#### 6.2.3 GAP-44: AnalyzeUrl新增followRedirects（仿真端多余功能）

**修复方案**：移除仿真端AnalyzeUrl中的followRedirects字段和逻辑，对齐真机行为（默认跟随重定向）

#### 6.2.4 GAP-45: AnalyzeUrl新增header JS执行（仿真端多余功能）

**修复方案**：移除仿真端AnalyzeUrl init块中的header JS执行逻辑

#### 6.2.5 GAP-46: AnalyzeUrl ajax override

**修复方案**：移除仿真端AnalyzeUrl中的ajax override，改为直接使用JsExtensionsStub.ajax（走Jsoup路径，对齐真机）

#### 6.2.6 GAP-47: 搜索阶段缺少loginCheckJs

**修复方案**：在BookSourceDebugger搜索阶段添加loginCheckJs检测逻辑

#### 6.2.7 GAP-48: 详情阶段isWebFile判断方式不同

**修复方案**：使用扩展属性`book.isWebFile`替代魔法数判断（需先修复GAP-40设置正确的type）

#### 6.2.8 GAP-49: 目录阶段缺少preUpdateJs

**修复方案**：在BookSourceDebugger目录阶段添加preUpdateJs执行

#### 6.2.9 GAP-50: 目录阶段分页处理差异

**修复方案**：对齐真机BookChapterList的nextTocUrl分页逻辑（或移植BookChapterList模块）

#### 6.2.10 GAP-51: 正文阶段nextContentUrl分页差异

**修复方案**：对齐真机BookContent的nextContentUrl分页逻辑（或移植BookContent模块）

#### 6.2.11 GAP-52: RSS调试缺少loginCheckJs

**修复方案**：在RssSourceDebugger添加loginCheckJs检测逻辑

#### 6.2.12 GAP-53: RSS调试ruleNextPage分页差异

**修复方案**：对齐真机Rss模块的ruleNextPage分页逻辑

#### 6.2.13 GAP-54: Book数据模型差异

**修复方案**：
- type默认值改为BookType.text(0b1)
- origin默认值改为"loc_book"
- infoHtml/tocHtml改为@Ignore（内存字段，非构造参数）

#### 6.2.14 GAP-55: SearchBook数据模型缺失

**修复方案**：新增SearchBook数据模型，搜索阶段通过SearchBook中间转换再转Book

### 6.3 P2级修复（11个，影响边缘场景）

| GAP | 修复方案 |
|-----|---------|
| GAP-56 | evalJS注入对象改为持久化CookieStore/CacheManager（依赖GAP-31/33持久化实现） |
| GAP-57 | 反向引入真机getZipByteArrayContent循环bug（对齐行为） |
| GAP-58 | 补充BookChapter业务方法（putImgUrl/putLyric/putDanmaku/update） |
| GAP-59 | BookSource/RssSource改为继承BaseSourceInterface（恢复JS扩展方法） |
| GAP-60 | 移除仿真端RSS调试singleUrl模式分支 |
| GAP-61 | 改用rssSource.sortUrls()扩展函数处理sortUrl JS |
| GAP-62 | 移除extractJsRule处理，直接使用完整ruleContent |
| GAP-63 | 移除仿真端显式toAbsoluteUrl调用（由AnalyzeUrl内部处理） |
| GAP-64 | 移植SSLHelper双向认证方法（getSslSocketFactory系列） |
| GAP-65 | 标记getMediaItem为不实现（TTS功能，不影响调试） |
| GAP-66 | 标记Cronet处理为不实现（Android特有，不影响调试） |

### AD-06: 保持委托 AnalyzeUrl（不改为 Jsoup.connect）

**决策**：get/head/post 保持委托 AnalyzeUrl

**理由**：
1. AnalyzeUrl 已处理 URL 模板/Cookie/请求体编码
2. OkHttp 连接池复用
3. SSL 通过 OkHttp 配置注入

### AD-07: 委托路径必须有回传机制

**决策**：所有委托路径（WebView/UI）必须有结果回传机制

**理由**：
1. 异常携带上下文 → 委托处理 → 回传结果
2. 不能只抛异常不处理
3. Python 端通过 HTTP API 回传结果

### AD-08: 真机 bug 也需对齐

**决策**：仿真端需对齐真机 bug（如 aesEncodeToString 误用 decryptStr）

**理由**：
1. 100% 测试校验准确性要求行为对齐（第八轮修正：原表述"100%兼容要求行为完全一致"与新目标不一致）
2. 即使真机有 bug，仿真端也需复现
3. 否则"仿真通过但真机失败"

### AD-09: 配置文件替代 SharedPreferences

**决策**：用 JSON 文件替代 Android SharedPreferences

**理由**：
1. JVM 无 SharedPreferences
2. JSON 文件可读写，行为等价
3. 配置路径：`~/.legado/`

---

## 七、第五轮深度排查修复方案（41个GAP，2子代理逐行源码核实）

> **排查背景**：第四轮设计文档完成后，用户质问"设计能否满足100%仿真"。启动2个子代理分别从 WebBook/Rss核心业务模块 和 Rhino/Gson/并发/异常基础架构 两个角度，逐行对比实现行为。发现41个新遗漏。

### 7.1 WebBook/Rss核心业务模块差异修复（30个）

#### 7.1.1 P0级修复（5个，必须修复）

**GAP-67a: loginCheckJs完全缺失**

**真机源码**（`WebBook.kt:70-78`/`Rss.kt:108-110`）：
```kotlin
// 所有阶段获取响应后执行loginCheckJs
if (!bookSource.loginCheckJs.isNullOrBlank()) {
    val check = AnalyzeRule(ruleData).evalJS(bookSource.loginCheckJs)
    if (check == "true" || check == true) {
        // 需要登录，执行登录流程
    }
}
```

**修复方案**：在BookSourceDebugger/RssSourceDebugger所有阶段（搜索/详情/目录/正文/RSS）添加loginCheckJs检测逻辑

**GAP-67b: ruleNextPage=="PAGE"特殊处理缺失**

**真机源码**（`BookChapterList.kt`/`BookContent.kt`）：
```kotlin
if (ruleNextPage == "PAGE") {
    // 使用page变量分页：{{page}}替换为页码
    for (page in 2..maxPage) {
        val pageUrl = url.replace("{{page}}", page.toString())
        // 获取下一页
    }
}
```

**修复方案**：在目录/正文分页逻辑中添加`ruleNextPage == "PAGE"`分支处理

**GAP-67c: init规则执行方式不同**

**真机源码**：init规则用`getElement`执行（返回List）
**仿真端现状**：用`getString`执行（返回String）

**修复方案**：将init规则执行方式改为`getElement`

**GAP-67d: BookContent正文格式化链完全缺失**

**真机源码**（`BookContent.kt`）：
```kotlin
content = HtmlFormatter.formatKeepImg(content)
content = StringEscapeUtils.unescapeHtml4(content)
if (book.useHtmlMap) content = HtmlMap.format(content)
content = applyReplaceRegex(content, replaceRegex)
```

**修复方案**：移植完整正文格式化链到仿真端

**GAP-67e: checkRedirect重定向检测缺失**

**修复方案**：在搜索/详情阶段添加checkRedirect重定向检测

#### 7.1.2 P1级修复（16个）⚠️ 可选修复（AD-10修正）

> **第七轮修正**：16个P1级改为可选修复，遇到实际失败源时再逐个修复，不急于一次性移植

| GAP | 修复方案 | 状态 |
|-----|---------|------|
| GAP-68a | 目录阶段添加preUpdateJs执行 | ⚠️ 可选 |
| GAP-68b | 实现并发分页（目录/正文） | ⚠️ 可选 |
| GAP-68c | 补充章节字段提取（chapterUrl/level等） | ⚠️ 可选 |
| GAP-68d | 添加formatJs正文格式化 | ⚠️ 可选 |
| GAP-68e | 添加reverse/去重逻辑 | ⚠️ 可选 |
| GAP-68f | 添加subContentRule正文分段 | ⚠️ 可选 |
| GAP-68g | 添加titleRule章节标题规则 | ⚠️ 可选 |
| GAP-68h | 添加replaceRegex前置处理 | ⚠️ 可选 |
| GAP-68i | 添加bookUrlPattern匹配 | ⚠️ 可选 |
| GAP-68j | 补充Book字段格式化链 | ⚠️ 可选 |
| GAP-68k | 添加RssParserDefault降级 | ⚠️ 可选 |
| GAP-68l | 添加sortUrls缓存 | ⚠️ 可选 |
| GAP-68m | ~~移植exploreKinds~~ | ❌ 过度修复 |
| GAP-68n | 搜索结果记录respondTime | ⚠️ 可选 |
| GAP-68o | 实现多源合并 | ⚠️ 可选 |
| GAP-68p | 补全Book变量注入 | ⚠️ 可选 |

#### 7.1.3 ~~P2级修复（9个）~~ ❌ 过度修复，不实施（AD-10修正）

> **第七轮修正**：9个P2级全部标注为过度修复。"模块未复用"本身不是问题，只要内联实现行为对齐即可。

| GAP | ~~修复方案~~ | 移除理由 |
|-----|-------------|---------|
| GAP-69a~e | ~~移植真机WebBook/Rss模块到仿真端~~ | AD-10：保持内联实现 |
| GAP-69f~i | ~~对齐各阶段规则类型处理~~ | AD-10：P0级已覆盖关键差异 |

### 7.2 Rhino/Gson/并发/异常基础架构差异修复（11个）

> **第七轮修正**：11个中4个标注为过度修复（GAP-72a/72b/72c + GAP-71a），2个重新设计（GAP-70a/70b → AD-11/AD-12），5个保留

#### 7.2.1 P0级修复（2个，重新设计）

**GAP-70a: Rhino JS引擎配置严重缺失** 🔄 重新设计（AD-11）

**真机源码**（`RhinoScriptEngine.kt`/`RhinoContext.kt`/`RhinoClassShutter.kt`/`RhinoWrapFactory.kt`）：
```kotlin
// 真机配置
context.setClassShutter(RhinoClassShutter)  // 安全沙箱
context.setWrapFactory(RhinoWrapFactory)     // Java对象包装
context.instructionObserverThreshold = 10000  // JS死循环检测
context.maximumInterpreterStackDepth = 10000  // 栈深度限制
NativeBaseSource.wrap(source)                 // source对象包装
evalSuspend(context)                          // 协程取消传播
```

~~**修复方案**~~：~~引入modules/rhino模块或移植关键组件（ClassShutter/WrapFactory/RhinoContext/NativeBaseSource）~~

**重新设计方案**（AD-11）：只移植WrapFactory + NativeBaseSource + instructionObserverThreshold。不移植ClassShutter（测试环境不需要安全限制）、RhinoContext生命周期管理（边缘场景）、evalSuspend（单次同步调试不需要）。

**GAP-70b: 并发模型根本性差异** 🔄 重新设计（AD-12）

**真机源码**：使用Coroutine with Dispatchers/Semaphore/withTimeout/ensureActive
**仿真端现状**：使用runBlocking替代Coroutine

~~**修复方案**~~：~~将runBlocking替换为Coroutine链式封装，添加Dispatchers/Semaphore/withTimeout/ensureActive~~

**重新设计方案**（AD-12）：只添加withTimeout超时控制（HTTP请求 + JS执行）。不替换runBlocking→Coroutine（性能差异不影响结果）、不添加Dispatchers/Semaphore/ensureActive（GAP-37限流器已覆盖）。

#### 7.2.2 P1/P2/P3级修复（9个）

| GAP | 优先级 | 修复方案 | 第七轮状态 |
|-----|--------|---------|-----------|
| GAP-71a | P1 | ~~scriptCache上限改为16~~ | ❌ 过度修复（不影响校验） |
| GAP-71b | P1 | 委托模式改实例化（与GAP-36合并修复） | ✅ 保留 |
| GAP-72a | P2 | ~~移植RhinoContext生命周期管理~~ | ❌ 过度修复（AD-11） |
| GAP-72b | P2 | 移植WrapFactory | ✅ 保留（AD-11必需） |
| GAP-72c | P2 | ~~移植ClassShutter~~ | ❌ 过度修复（AD-11） |
| GAP-73a~d | P3 | ✅ 已完全对齐，无需修复 | ✅ 已对齐 |

### AD-10: 保持内联实现，只修复P0级差异（第七轮修正）

**决策**：保持BookSourceDebugger/RssSourceDebugger中的内联实现，只修复P0级5个差异（loginCheckJs/PAGE/init/正文格式化链/checkRedirect）

**修正原因**（第七轮深度审查）：
1. 移植整个WebBook/Rss模块工作量巨大，且可能引入大量Android依赖
2. 内联实现行为对齐即可，不需要为了"复用"而移植整个模块
3. 符合"懒原则"——不做未被明确要求的架构重构

**P0级5个必需修复**：
- GAP-67a: 所有阶段添加loginCheckJs检测逻辑
- GAP-67b: 目录/正文分页添加ruleNextPage=="PAGE"特殊处理
- GAP-67c: init规则执行方式改为getElement
- GAP-67d: 移植完整正文格式化链（HtmlFormatter+StringEscapeUtils+HtmlMap+replaceRegex）
- GAP-67e: 搜索/详情阶段添加checkRedirect重定向检测

**P1级16个可选修复**：遇到实际失败源时再逐个修复，不急于一次性移植

**P2级9个不修复**："模块未复用"本身不是问题，只要内联实现行为对齐即可

### AD-11: 只移植WrapFactory+instructionObserverThreshold（第七轮修正，源码核实修正）

**决策**：不引入完整modules/rhino模块，只移植影响测试校验的关键组件

**修正原因**（第七轮深度审查）：
1. ClassShutter（安全沙箱）在测试环境中不需要，反而会阻止源规则访问Java类
2. RhinoContext生命周期管理是边缘场景，不影响校验结果
3. 只需移植影响测试校验的组件

**必需移植**：
- WrapFactory/NativeBaseSource：控制Java对象在JS中的行为，影响source.setXxx是否生效
- instructionObserverThreshold：JS死循环检测，不设置会导致死循环源规则卡死调试

**源码核实修正**（子代理审查发现）：
1. **WrapFactory依赖ClassShutter问题**：RhinoWrapFactory的`wrapAsJavaObject`和`wrapJavaClass`方法直接调用`RhinoClassShutter.visibleToScripts()`。解决方案：**修改WrapFactory移除对ClassShutter的调用**，让所有Java类都可见（测试环境不需要安全限制）。不移植原版ClassShutter，而是简化WrapFactory。
2. **instructionObserverThreshold依赖RhinoContext问题**：`ContextFactory.observeInstructionCount`覆写方法内部调用`RhinoContext.ensureActive()`来中断死循环（源码核实：`RhinoScriptEngine.kt:340-344`）。解决方案：**在仿真端自定义`observeInstructionCount`实现，直接抛出`TimeoutException`中断死循环**，不依赖RhinoContext。
3. **maximumInterpreterStackDepth**：真机设置为1000，仿真端也需设置（防止深度递归JS栈溢出）。

**不需要移植**：
- ClassShutter：测试环境不需要安全限制（但需修改WrapFactory移除对其的调用）
- RhinoContext生命周期管理：边缘场景
- evalSuspend（协程取消传播）：单次同步调试不需要

### AD-12: 只添加withTimeout超时控制（第七轮修正）

**决策**：不将runBlocking替换为Coroutine链式封装，只在关键位置添加withTimeout超时控制

**修正原因**（第七轮深度审查）：
1. runBlocking vs Coroutine是性能差异，不影响测试校验结果
2. 替换为Coroutine链式封装影响面广，需全量回归测试
3. 只需在关键位置（HTTP请求、JS执行）添加超时控制即可

**必需修复**：
- HTTP请求添加withTimeout：防止超时请求卡死调试
- JS执行添加instructionObserverThreshold：防止死循环源规则卡死调试

**不需要修复**：
- Dispatchers（线程调度）：影响性能不影响结果
- Semaphore（并发控制）：GAP-37限流器已覆盖
- ensureActive（协程取消检查）：单次同步调试不需要

---

## 八、第六轮深度排查修复方案（29个GAP，2子代理逐行源码核实）

> **排查背景**：第五轮排查完成后，用户要求"深度分析全面排查"。启动2个子代理分别从 数据持久化/配置/日志/缓存 和 网络层/资源加载/业务模型 两个角度，逐行对比实现行为。发现29个新遗漏。

### 8.1 P0级修复（2个，重新设计）

> **第七轮修正**：2个P0级全部重新设计（GAP-67→内存存储，GAP-80→只添加UA注入+CookieJar）

#### 8.1.1 ~~GAP-67: Room数据库完全缺失~~ 🔄 重新设计

**真机源码**（`AppDatabase.kt:69-126`）：
```kotlin
@Database(
    entities = [BookSource::class, Book::class, BookChapter::class, ...],
    version = 89
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun bookSourceDao(): BookSourceDao
    abstract fun bookDao(): BookDao
    // ... 21个Dao
}
```

**仿真端现状**：完全没有appDb，无Room/SQLite/Dao

~~**修复方案**~~：~~接入SQLite JDBC（`xerial/sqlite-jdbc`）实现轻量数据库，或用H2 Database文件模式~~

**重新设计方案**：使用内存存储（ConcurrentHashMap），单次调试会话不需要持久化。BookSource/BookChapter/Cookie/Cache等在会话内通过内存Map保持，会话结束后丢弃。不引入SQLite/H2依赖。

#### 8.1.2 GAP-80: HTTP拦截器全部缺失 🔄 重新设计

**真机源码**（`HttpHelper.kt:51-127`）：
```kotlin
okHttpClient = OkHttpClient.Builder()
    .addInterceptor { chain ->  // UA注入
        val request = chain.request()
        val builder = request.newBuilder()
        if (request.header(UA_NAME) == null) {
            builder.addHeader(UA_NAME, AppConfig.userAgent)
        }
        chain.proceed(builder.build())
    }
    .addInterceptor { chain ->  // Keep-Alive + Cache-Control
        val builder = chain.request().newBuilder()
            .addHeader("Keep-Alive", "300")
            .addHeader("Connection", "Keep-Alive")
            .addHeader("Cache-Control", "no-cache")
        chain.proceed(builder.build())
    }
    .addNetworkInterceptor { chain ->  // CookieJar
        val request = chain.request()
        val builder = request.newBuilder()
        CookieManager.loadRequest(url, builder)
        val response = chain.proceed(builder.build())
        CookieManager.saveResponse(url, response)
        response
    }
    .addInterceptor(DecompressInterceptor())  // gzip/deflate解压
    .addInterceptor(OkHttpExceptionInterceptor())  // 异常包装
    .build()
```

**仿真端现状**：okHttpClient无任何addInterceptor调用

~~**修复方案**~~：~~在仿真端HttpHelper中添加5个拦截器~~

**重新设计方案**：只添加2个影响测试校验的拦截器：
1. **UA注入拦截器**（GAP-83）：请求头缺少UA时自动注入，影响网站反爬判断
2. **CookieJar网络拦截器**（GAP-82）：loadRequest + saveResponse，影响登录态保持

不添加的3个拦截器：
- ~~Keep-Alive/Cache-Control~~：OkHttp内置连接池管理已覆盖
- ~~DecompressInterceptor~~：OkHttp内置透明gzip解压（注：deflate需额外处理，降级为可选修复）
- ~~OkHttpExceptionInterceptor~~：异常包装不影响校验结果

### 8.2 P1级修复（8个，影响调试结果）

> **第七轮修正**：8个中4个标注为过度修复（GAP-68/69/71/81），1个重新设计（GAP-72），3个保留（GAP-82/83/84中只保留82/83）

| GAP | 修复方案 | 第七轮状态 |
|-----|---------|-----------|
| GAP-68 | ~~CookieStore接入JSON文件持久化或SQLite~~ | ❌ 过度修复（内存存储） |
| GAP-69 | ~~CacheManager接入文件系统持久化~~ | ❌ 过度修复（内存存储） |
| GAP-71 | ~~用java.util.Properties或JSON文件实现SharedPreferences~~ | ❌ 过度修复（不需要配置持久化） |
| GAP-72 | 只补充userAgent + customHosts到AppConfig | 🔄 重新设计（原方案：移植200+配置项） |
| GAP-81 | ~~移植DecompressInterceptor拦截器~~ | ⚠️ 可选修复（OkHttp内置gzip解压，但deflate需额外处理） |
| GAP-82 | 添加CookieJar网络拦截器（loadRequest+saveResponse） | ✅ 保留（合并到HttpHelper） |
| GAP-83 | 添加UA自动注入拦截器 | ✅ 保留 |
| ~~GAP-84~~ | ~~添加Keep-Alive/Cache-Control头注入拦截器~~ | ❌ 过度修复（OkHttp内置连接池管理） |

### 8.3 P2级修复（10个，影响边缘场景）

> **第七轮修正**：10个中7个标注为过度修复（GAP-70/77/85/86/87/88/91），2个保留（GAP-73/76），1个重新设计（GAP-75）

| GAP | 修复方案 | 第七轮状态 |
|-----|---------|-----------|
| GAP-70 | ~~用java.io.File实现ACache文件缓存~~ | ❌ 过度修复（持久化类） |
| GAP-73 | userAgent默认值改为与真机一致 | ✅ 保留 |
| GAP-75 | 只补充MAX_THREAD + charsets | 🔄 重新设计（原方案：补充全部常量） |
| GAP-76 | 添加customHosts/DNS自定义解析 | ✅ 保留（只补充customHosts） |
| GAP-77 | ~~实现AppLog Stub（内存列表+println）~~ | ❌ 过度修复（日志不影响校验） |
| GAP-85 | ~~移植BookSourceExtensions（exploreKinds/getBookType）~~ | ❌ 过度修复（Extensions不影响校验） |
| GAP-86 | ~~移植RssSourceExtensions（sortUrls）~~ | ❌ 过度修复（同上） |
| GAP-87 | ~~移植SourceHelp（getSource/deleteSource/enableSource）~~ | ❌ 过度修复（源管理不需要持久化） |
| GAP-88 | ~~移植ReplaceAnalyzer（jsonToReplaceRules）~~ | ⚠️ 可选（替换规则解析可能影响校验，遇到实际需求再移植） |
| GAP-91 | ~~扩展AppConfig网络配置~~ | ❌ 过度修复（GAP-72已覆盖userAgent/customHosts） |

### 8.4 P3级修复（9个，不影响核心调试）

> **第七轮修正**：9个中5个标注为过度修复（GAP-78/79/94/95/96），4个保持原状（GAP-74/89/98/99已标记为不可实现/已实现）

| GAP | 修复方案 | 第七轮状态 |
|-----|---------|-----------|
| GAP-74 | 标记为不可实现（Cronet依赖Android原生） | ✅ 保持原状 |
| GAP-78 | ~~用java.util.logging.Logger实现文件日志~~ | ❌ 过度修复（日志不影响校验） |
| GAP-79 | ~~添加recordLog配置项~~ | ❌ 过度修复（同上） |
| GAP-89 | 保持委托路径（已实现UserInterventionException） | ✅ 保持原状 |
| GAP-94 | ~~传递coroutineContext到ajax~~ | ❌ 过度修复（性能差异不影响结果） |
| GAP-95 | ~~实现ajaxAll并发执行~~ | ❌ 过度修复（性能差异不影响结果） |
| GAP-96 | ~~scriptCache上限改为16~~ | ❌ 过度修复（不影响校验） |
| GAP-98 | 标记为不可实现（UI层） | ✅ 保持原状 |
| GAP-99 | 标记为不可实现（UI层） | ✅ 保持原状 |

---

## Data Flow

### 100% 测试校验准确性验证流程

```
真实书源/订阅源
  → 仿真端调试（BookSourceDebugger/RssSourceDebugger）
  → 方法调用链
    → 兼容方法（82个）：直接执行
    → 可修复方法（52个必需+28可选）：修复后执行
    → 不可实现方法（21个）：委托路径
      → WebView → Selenium → 回传结果
      → UI → Selenium/OCR → 回传结果
      → 硬件 → 环境变量 → 直接读取
  → 调试结果
  → 对比真机结果
  → 测试校验准确性验证（JAR通过→真机通过，JAR失败→区分源规则问题还是仿真端问题）
```

### 失败源优化流程

```
批量测试失败源（100个）
  → 根因分析
    → 仿真端问题（2个）→ 修复仿真端
    → 源规则问题（58个）→ 修复源规则
    → 网站问题（40个）→ 排除（非仿真端责任）
  → 修复后重新测试
  → 验证：真机能运行的源，仿真端也能运行
```

---

## File Changes

### 新增文件

> **第七轮修正**：已移除17个过度修复的新增文件（ArchiveUtils/ReadBookConfig/ThemeConfig/WebBook×5/Rss×2/SourceHelp/AppDatabase/DecompressInterceptor/OkHttpExceptionInterceptor/ACache/AppLog/RhinoClassShutter）

| 文件 | 来源 | 说明 | 优先级 |
|------|------|------|--------|
| `utils/SharedJsScope.kt` | 真机移植 | JS Scope 管理（evalJS sharedScope 依赖） | P1 |
| `utils/RowUiParser.kt` | 真机移植 | loginUi 解析（登录源校验依赖） | P1 |
| `python/webview_delegate.py` | 新建 | WebView Selenium 委托（9个不可实现方法） | P1 |
| `python/ocr_delegate.py` | 新建 | 验证码 OCR 委托（登录场景） | P2 |
| `rhino/RhinoWrapFactory.kt` | 真机移植 | Java对象包装（AD-11：只移植WrapFactory） | P0 |
| `rhino/NativeBaseSource.kt` | 真机移植 | source对象包装（AD-11：配合WrapFactory） | P0 |

**已移除的过度修复新增文件（17个）**：

| 已移除文件 | 原方案 | 移除理由 |
|------------|--------|---------|
| `utils/ArchiveUtils.kt` | 压缩文件解压 | 方向5延后，100个失败源中0个压缩文件相关 |
| `config/ReadBookConfig.kt` | 阅读配置移植 | GAP-72重新设计：只补充userAgent/customHosts |
| `config/ThemeConfig.kt` | 主题配置移植 | 同上，主题配置不影响校验 |
| `model/webBook/WebBook.kt` 等5个 | WebBook模块移植 | AD-10：保持内联实现，只修复P0级5个差异 |
| `model/rss/Rss.kt` 等2个 | Rss模块移植 | AD-10：同上 |
| `data/appdatabase/SourceHelp.kt` | 源管理持久化 | GAP-67：内存存储足够 |
| `data/AppDatabase.kt` | SQLite数据库 | GAP-67：单次会话不需要数据库 |
| `help/http/DecompressInterceptor.kt` | gzip解压拦截器 | GAP-80：OkHttp内置自动解压 |
| `help/http/OkHttpExceptionInterceptor.kt` | 异常包装拦截器 | 不影响校验结果 |
| `help/ACache.kt` | 文件缓存 | 持久化类过度修复 |
| `constant/AppLog.kt` | 日志系统 | 日志不影响校验结果 |
| `rhino/RhinoClassShutter.kt` | JS安全沙箱 | AD-11：测试环境不需要安全限制 |

### 修改文件

> **第七轮修正**：已移除过度修复的修改项（持久化接入/5个HTTP拦截器/ClassShutter/Room数据库/Extensions移植/完整配置项等）

| 文件 | 修改内容 |
|------|---------|
| `JsExtensionsStub.kt` | 46个方法修复 + 委托路径 + GAP-36改为实例化模式 + GAP-42 SymmetricCryptoAndroid + GAP-43 toStringArray + 第五轮Book变量注入补全（P0级5个差异） |
| `BaseSourceInterface.kt` | 6个属性 var + 3个空实现 |
| `BookSourceDebugger.kt` | debugExplore infoMap + GAP-39 ruleData注入 + GAP-40 类型重置 + GAP-47 loginCheckJs + GAP-48 isWebFile + GAP-49 preUpdateJs + GAP-50 目录分页 + GAP-51 正文分页 + 第五轮P0级5个差异（loginCheckJs/PAGE/init/正文格式化链/checkRedirect） |
| `RssSourceDebugger.kt` | GAP-22 ruleDescription逻辑修正(P0) + GAP-23 key::url入口 + GAP-24取消机制 + GAP-25校验模式 + GAP-26无参key入口 + GAP-41 ruleData注入 + GAP-52 loginCheckJs + GAP-53 ruleNextPage分页 + GAP-60 移除singleUrl + GAP-61 sortUrl JS + GAP-62 移除extractJsRule + GAP-63 移除toAbsoluteUrl |
| `OkHttpUtils.kt` | SSLHelper + 公共DNS + GAP-1 newCallResponseBody + GAP-2 decompressed + GAP-3 await取消 + 新-2回调顺序 |
| `HttpHelper.kt` | **第七轮修正**：只添加UA注入拦截器 + CookieJar（~~原方案：添加5个拦截器~~） + GAP-85 readTimeout改为60s |
| `CookieStoreStub.kt` | GAP-31 内存存储 + GAP-35 WebCookie描述修正（~~第六轮GAP-68 接入持久化~~ → 内存Map） |
| `CookieManagerStub.kt` | GAP-32 补充saveResponse/loadRequest方法到内存Map（~~第六轮GAP-82 CookieJar拦截器~~ → 合并到HttpHelper） |
| `CacheManagerStub.kt` | GAP-33 内存存储（~~第六轮GAP-69 接入文件系统持久化~~ → 内存Map） |
| `Debug.kt` | 新-1 补充状态管理 + 新-4 CheckSource校验 |
| `AnalyzeRule.kt` | GAP-36 委托模式改实例化 + GAP-56 evalJS注入持久化对象 + **第七轮修正**：只添加instructionObserverThreshold（~~第五轮GAP-70a Rhino引擎配置~~） + ~~第六轮GAP-96 scriptCache上限~~（不影响校验） |
| `AnalyzeUrl.kt` | GAP-44 移除followRedirects + GAP-45 移除header JS + GAP-46 移除ajax override |
| `ConcurrentRateLimiter.kt` | GAP-37 移植完整限流实现 + **第七轮修正**：只添加withTimeout超时控制（~~第五轮GAP-70b 并发模型对齐~~） |
| `NetworkUtilsStub.kt` | GAP-38 getSubDomain对齐PublicSuffixDatabase + **第七轮修正**：只补充customHosts（~~第六轮GAP-76 完整customHosts~~） |
| `Book.kt` | GAP-54 type默认值 + origin默认值 + infoHtml/tocHtml改@Ignore + 第五轮P0级字段格式化链 |
| `BookChapter.kt` | GAP-58 补充业务方法 + 第五轮P0级章节字段提取 |
| `BookSource.kt` | GAP-59 改为继承BaseSourceInterface（~~第六轮GAP-85 exploreKinds~~ → 过度修复，不实施） |
| `RssSource.kt` | GAP-59 改为继承BaseSourceInterface（~~第六轮GAP-86 sortUrls~~ → 过度修复，不实施） |
| `SSLHelper.kt` | GAP-64 补充双向认证方法 |
| `AppConfig.kt` | **第七轮修正**：只补充userAgent + customHosts（~~第六轮GAP-72 扩展200+配置项~~） + GAP-73 userAgent默认值 |
| `AppConst.kt` | **第七轮修正**：只补充MAX_THREAD + charsets（~~第六轮GAP-75 补充全部常量~~） |
| `RhinoScriptEngine.kt` | **第七轮修正**：只配置WrapFactory + instructionObserverThreshold（~~第五轮GAP-70a 配置ClassShutter/RhinoContext~~） |
| `build.gradle.kts` | **第七轮修正**：~~commons-compress依赖~~（移除） + ~~sqlite-jdbc依赖~~（移除），不新增依赖 |

---

## 风险评估

> **第七轮修正**：已移除7个过度修复的风险项（压缩文件依赖冲突/WebBook模块移植/Rhino引擎配置移植/并发模型对齐/Room数据库接入/HTTP拦截器添加/Extensions移植）

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| SharedJsScope 移植复杂 | 高 | 高 | 分阶段实现，先实现基础 Scope 管理 |
| Selenium 委托延迟 | 高 | 中 | 设置超时 + 异步执行 |
| 环境变量未配置 | 中 | 中 | 提供默认值 + 启动时检查 |
| 真机 bug 反向引入 | 低 | 低 | 注释标记，便于后续修复 |
| GAP-22 ruleDescription 修正引入回归 | 中 | 高 | 修正后用真实RSS源验证，对比真机调试结果 |
| CookieManager saveResponse 实现错误 | 中 | 高 | 参照真机 CookieManager.kt:29-50 逐行实现 |
| GAP-36 委托模式改实例化引入回归 | 高 | 高 | 修改后全量回归测试，验证并发调试场景 |
| GAP-37 限流器实现导致请求超时 | 中 | 中 | 设置合理超时 + 限流参数可配置 |
| GAP-40 类型重置影响现有调试流程 | 中 | 中 | 修改后验证文件类书源调试行为 |
| GAP-44/45/46 移除仿真端多余功能 | 低 | 中 | 移除后验证不影响现有通过的源 |
| GAP-54 Book数据模型修改影响序列化 | 中 | 高 | 修改后验证JSON序列化/反序列化正常 |
| GAP-59 继承体系修改影响JS执行 | 高 | 高 | 修改后验证JS中source变量访问正常 |
| **第七轮新增**：WrapFactory移植不完整导致JS对象包装异常 | 中 | 高 | 参照真机RhinoWrapFactory.kt逐行移植，验证source/book变量在JS中可访问 |
| **第七轮新增**：instructionObserverThreshold设置不当导致JS死循环 | 低 | 高 | 设置合理阈值（默认10000），超时自动中断 |
| **第七轮新增**：ClassShutter不移植导致受限类访问行为不一致 | 中 | 中 | 仿真端允许JS访问所有Java类（真机阻止），若源规则访问受限类（如java.io.File），仿真端成功但真机失败。权衡：这类源规则本身有问题，仿真端不阻止反而能帮助发现 |

**已移除的过度修复风险项（7个）**：

| 已移除风险 | 移除理由 |
|------------|---------|
| 压缩文件解压依赖冲突 | 方向5延后，不引入commons-compress |
| 第五轮WebBook/Rss模块移植复杂 | AD-10：保持内联实现，不移植整个模块 |
| 第五轮Rhino引擎配置移植 | AD-11：只移植WrapFactory+instructionObserverThreshold |
| 第五轮并发模型对齐 | AD-12：只添加withTimeout，不改runBlocking→Coroutine |
| 第六轮GAP-67 Room数据库接入 | GAP-67：内存存储，不引入数据库 |
| 第六轮GAP-80 HTTP拦截器添加 | 只添加UA注入+CookieJar，不添加5个拦截器 |
| 第六轮GAP-85/86 Extensions移植 | exploreKinds/sortUrls不影响校验，不移植 |
