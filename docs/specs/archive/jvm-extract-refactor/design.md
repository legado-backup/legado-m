# Design: JVM 仿真服务端架构重构

## 1. Technical Approach（技术方案）

### 1.1 总体架构对比

```
当前架构（问题）：
┌─────────────────────────────────────────┐
│  .trae/skills/.../tools/mvp1-build/     │
│  ├── MinimalMockJsExtensions.kt  ← 猜测  │
│  ├── MockSymmetricCrypto.kt      ← 猜测  │
│  ├── MockCookieStore.kt          ← 猜测  │
│  ├── AnalyzeRule.kt               ← 猜测  │
│  ├── AnalyzeUrl.kt                ← 猜测  │
│  └── RssSourceDebugger.kt        ← 猜测  │
│  问题：行为与真机不一致，bug 层出不穷       │
└─────────────────────────────────────────┘

目标架构（正确）：
┌─────────────────────────────────────────┐
│  .trae/skills/legado-source-creator/tools/legado-jvm/（从源码抽取）          │
│  ├── io/legado/app/model/analyzeRule/    │
│  │   ├── AnalyzeRule.kt     ← 真机源码    │
│  │   ├── AnalyzeUrl.kt      ← 真机源码    │
│  │   ├── AnalyzeByJSoup.kt  ← 真机源码    │
│  │   ├── AnalyzeByJSonPath.kt ← 真机源码  │
│  │   ├── AnalyzeByXPath.kt  ← 真机源码    │
│  │   ├── AnalyzeByRegex.kt  ← 真机源码    │
│  │   ├── QueryTTF.java      ← 真机源码    │
│  │   ├── RuleAnalyzer.kt    ← 真机源码    │
│  │   ├── RuleData.kt        ← 真机源码    │
│  │   ├── RuleDataInterface.kt ← 真机源码  │
│  │   └── CustomUrl.kt      ← 真机源码    │
│  ├── io/legado/app/data/entities/        │
│  │   ├── BookSource.kt      ← 真机源码    │
│  │   └── RssSource.kt      ← 真机源码    │
│  ├── io/legado/app/help/                 │
│  │   ├── JsExtensionsInterface.kt ← 接口  │
│  │   └── JsExtensionsStub.kt  ← JVM 实现  │
│  ├── io/legado/app/utils/                │
│  │   ├── NetworkUtilsStub.kt             │
│  │   └── CacheManagerStub.kt            │
│  └── io/legado/ruleengine/               │
│      ├── RuleEngineServer.kt  ← 入口     │
│      ├── RssSourceDebugger.kt ← 调试器   │
│      └── BookSourceDebugger.kt ← 调试器  │
│  优势：行为与真机一致，bug 大幅减少        │
└─────────────────────────────────────────┘
```

### 1.2 抽取策略详解

#### A 级（直接复制，零修改）

```kotlin
// RuleDataInterface.kt — 直接复制，零修改（38 行，零依赖）
// RuleAnalyzer.kt — 直接复制，零修改（378 行，纯算法，无任何 import）
// RuleData.kt — 仅替换 GSON 引用（30 行）：
//   原: import io.legado.app.utils.GSON
//   改: import com.google.gson.Gson; private val GSON = Gson()
// CustomUrl.kt — 替换 GSON + 处理 AnalyzeUrl.paramPattern 依赖（49 行）：
//   原: import io.legado.app.utils.GSON; import io.legado.app.utils.fromJsonObject
//   改: import com.google.gson.Gson; private val GSON = Gson()
//   隐藏依赖: 引用 AnalyzeUrl.paramPattern（同包静态 Pattern），需内联或同步抽取
```

#### B 级（删 @Keep 注解 + 处理隐藏依赖）

```kotlin
// AnalyzeByJSoup.kt — 删 @Keep（524 行，依赖 RuleAnalyzer 同包）
// AnalyzeByJSonPath.kt — 删 @Keep + 替换 printOnDebug（171 行）：
//   隐藏依赖: import io.legado.app.utils.printOnDebug（跨包，封装 Android Log）
//   改: 替换为 println() 或自建日志接口
// AnalyzeByRegex.kt — 删 @Keep（60 行，纯 JDK）
// QueryTTF.java — 删 @Keep（1055 行，纯 JDK，最大的文件但依赖最干净）
```

#### C 级（替换 TextUtils.join）

```kotlin
// AnalyzeByXPath.kt
// 源码参照: app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeByXPath.kt#L138
// 原: import android.text.TextUtils; TextUtils.join("\n", it)
// 改: it.joinToString("\n")  // Kotlin 标准库 joinToString 等价替代
```

#### D 级 — 数据模型（移除 Room/Parcelize + 处理嵌套实体）

> **⚠️ 最严重的隐藏依赖**：BookSource/RssSource 通过 `BaseSource` 接口间接继承 `JsExtensions`，而 JsExtensions 有 77 个 import 语句。这是整个抽取的最大隐藏依赖链。
>
> **源码参照**：
> - `app/src/main/java/io/legado/app/data/entities/BaseSource.kt#L33`：`interface BaseSource : JsExtensions`
> - `app/src/main/java/io/legado/app/help/JsExtensions.kt#L89`：`interface JsExtensions : JsEncodeUtils`（77 个 import）
> - BookSource/RssSource 均继承 BaseSource，间接依赖整个 JsExtensions 生态
>
> **抽取策略**：移除 `: BaseSource` 继承，BookSource/RssSource 改为独立 POJO。JsExtensions 方法由 JsExtensionsStub 在 AnalyzeRule/AnalyzeUrl 中注入，不需要数据模型继承。

```kotlin
// BookSource.kt（315 行，表面 13 个 import，实际通过 BaseSource 隐藏 77+ 个间接依赖）
// 原:
//   @Entity(tableName = "book_sources", indices = [Index(value = ["bookSourceUrl"], unique = true)])
//   data class BookSource(
//       @PrimaryKey
//       @ColumnInfo(name = "bookSourceUrl") var bookSourceUrl: String = "",
//       ...
//   ) : Parcelable {
//       @Parcelize constructor(...)
//   }
// 改:
//   data class BookSource(
//       var bookSourceUrl: String = "",
//       ...
//   ) : Serializable
// 隐藏依赖（需同步抽取或创建 Stub）:
//   - 6 个 Rule 实体: BookInfoRule, ContentRule, ExploreRule, ReviewRule, SearchRule, TocRule
//   - AudioPlay（model 层）
//   - GSON, fromJsonObject, splitNotBlank（utils 层）
// 同理: RssSource.kt（214 行，表面 3 个 import，同样通过 BaseSource 隐藏 77+ 个依赖，并非"最独立"）
```

#### D 级 — JsExtensions 接口拆分（1199 行，49 个内部依赖）

> **⚠️ 核心瓶颈**：JsExtensions 是整个抽取的最大障碍。1199 行、49 个内部依赖、直接依赖 2 个 Activity + appCtx + WebView + Toast。与 AnalyzeUrl 存在循环依赖（JsExtensions 调用 AnalyzeUrl，AnalyzeUrl 实现 JsExtensions）。

```kotlin
// JsExtensionsInterface.kt — 纯接口，无 Android 依赖
interface JsExtensionsInterface {
    // 加解密
    fun aesEncode(data: String, key: String, iv: String, transformation: String): String
    fun aesDecode(data: String, key: String, iv: String, transformation: String): String
    // HTTP
    fun get(url: String, headers: String): String
    fun post(url: String, body: String, headers: String): String
    // Cookie
    fun getCookie(url: String, key: String?): String
    // 规则
    fun getString(ruleStr: String): String
    fun getStringList(ruleStr: String): List<String>
    // WebView 降级
    fun webViewGetSource(url: String, header: String, js: String, regex: String): String
    // startBrowserAwait/getVerificationCode 不可用，抛异常
    // ...
}

// JsExtensionsStub.kt — JVM 实现
class JsExtensionsStub(
    private val source: BookSource,
    private val ruleData: RuleDataInterface
) : JsExtensionsInterface {
    override fun webViewGetSource(url: String, header: String, js: String, regex: String): String {
        // 简化说明：WebView 降级为 HTTP+正则 | 已知上限：无法执行 JS 动态加载 | 升级路径：集成 Selenium
        val response = AnalyzeUrl(url, source = source).getStrResponse()
        val html = response.body ?: ""
        val pattern = Regex(regex, RegexOption.IGNORE_CASE)
        return pattern.find(html)?.value ?: ""
    }
    // ...
}
```

**JsExtensions 隐藏依赖清单（49 个内部依赖中的关键项）**：
- `appCtx`（splitties 全局 Context）→ Android Context 深度绑定
- `OnLineImportActivity` / `OpenUrlConfirmActivity` → UI 层 Activity
- `BackstageWebView` → Android WebView + JS Bridge
- `SourceVerificationHelp` → 验证码 UI 对话框
- `ReadBookConfig` / `ThemeConfig` → Android 配置层
- `SourceHelp.openVideoPlayer` → 视频播放器 Activity
- `externalCache` → Android 外部存储

#### D 级 — AnalyzeRule（抽象依赖，973 行，35 个内部依赖）

> **⚠️ 架构级重构**：AnalyzeRule 不仅是规则解析器，还实现了 JsExtensions 接口。`evalJS` 中 `bindings["java"] = this` 将自身注入为 JS 全局变量 `java`，JS 代码通过 `java.xxx()` 调用其方法。这是理解整个规则引擎的关键机制。

```kotlin
// AnalyzeRule.kt
// 原: import io.legado.app.help.JsExtensions
// 改: import io.legado.app.help.JsExtensionsInterface
// 原: import io.legado.app.help.CacheManager
// 改: import io.legado.app.help.CacheManagerInterface
// 原: import io.legado.app.utils.NetworkUtils
// 改: import io.legado.app.utils.NetworkUtilsStub
// 原: import android.text.TextUtils; TextUtils.isEmpty(str)
// 改: str.isNullOrBlank()
// 隐藏依赖（需创建 Stub 或接口）:
//   - BackstageWebView（getWebJsResult 调用）→ WebView 降级
//   - WebBook（reGetBook/refreshTocUrl 调用）→ 业务层降级
//   - BookSource/Book/BookChapter（Room 实体）→ 使用抽取后的 POJO
//   - GSON/GSONStrict/fromJsonObject/isJson/isDataUrl 等 utils → 同步抽取
```

**evalJS 机制说明（核心调用链）**：
```
AnalyzeRule.evalJS(jsStr, result)
  ↓ buildScriptBindings { bindings["java"] = this }  // this = AnalyzeRule 实例
  ↓ RhinoScriptEngine.getRuntimeScope(bindings)
  ↓ compileScriptCache(jsStr).eval(scope, coroutineContext)  // CompiledScript 缓存(上限16)
  ↓ JS 代码中 java.ajax(url) → Rhino 反射调用 AnalyzeRule.ajax(url)
  ↓ ajax(url) 内部创建 AnalyzeUrl → 递归调用链
```

#### D 级 — AnalyzeUrl（移除 Glide/ExoPlayer，978 行，42 个内部依赖）

> **⚠️ Android 依赖最重**：同时依赖 Glide + ExoPlayer + WebView 三大 Android 组件，是 5 个 D 级文件中抽取难度最高的。

```kotlin
// AnalyzeUrl.kt
// 删除: import com.bumptech.glide.load.model.GlideUrl
// 删除: import androidx.media3.common.MediaItem
// 删除: 相关方法（getGlideUrl/getMediaItem 等）
// 原: import android.util.Base64
// 改: import java.util.Base64
// 隐藏依赖（需创建 Stub 或接口）:
//   - AppConfig.isCronet → Google Cronet（Android 专属网络库），改为固定 false
//   - ExoPlayerHelper.createMediaItem → media3，删除相关方法
//   - GlideHeaders → Glide，删除相关方法
//   - BackstageWebView → WebView 降级
//   - ConcurrentRateLimiter → 限流，可简化为无限制
//   - CookieManager/CookieStore → 使用 CookieStoreStub
//   - 40 个 io.legado.app.* 内部依赖需逐一处理
```

### 1.3 执行流程层覆盖（关键补充）

> **⚠️ 第三轮审查发现**：设计文档原 14 个核心类仅覆盖"规则引擎层"，完全遗漏了"执行流程层"。新 JAR 的 RuleEngineServer/RssSourceDebugger/BookSourceDebugger 需要复现以下真实执行流程。

#### 书源执行流程（4 阶段）

```
WebBook.searchBookAwait / exploreBookAwait / getBookInfoAwait / getChapterListAwait / getContentAwait
  ↓
① AnalyzeUrl 构造请求（initUrl: analyzeJs → replaceKeyPageJs → analyzeUrl）
  ↓
② getStrResponseAwait（okhttp 请求 或 BackstageWebView）
  ↓
③ loginCheckJs 检测（evalJS 检查登录状态）
  ↓
④ checkRedirect（重定向检测）
  ↓
⑤ 分发到解析器:
   - BookList.analyzeBookList（搜索/发现）
   - BookInfo.analyzeBookInfo（详情）
   - BookChapterList.analyzeChapterList（目录）
   - BookContent.analyzeContent（正文）
```

#### RSS 源执行流程（2 阶段）

```
RssSource.sortUrls() → 检测 @js:/<js> 前缀 → BaseSource.evalJS 生成分类
  ↓
① Rss.getArticlesAwait: AnalyzeUrl 构造请求 → RssParserByRule.parseXML 解析列表
   - ruleArticles 为空时回退 RssParserDefault.parseXML
  ↓
② Rss.getContentAwait: AnalyzeUrl 构造请求 → AnalyzeRule.getString 解析正文
```

#### 三层 evalJS 注入变量差异（关键机制）

| 层级 | 实现类 | evalJS 注入变量 | 触发场景 |
|------|--------|----------------|---------|
| 源级别 | BaseSource | java/source/baseUrl=getKey()/cookie/cache | sortUrl @js、header @js、loginUi @js、loginCheckJs |
| URL级别 | AnalyzeUrl | java/baseUrl/cookie/cache/page/key/book/source/result/infoMap | URL 中的 @js、<js>、{{js}} |
| 规则级别 | AnalyzeRule | java/cookie/cache/source/book/result/baseUrl/chapter/title/src/nextChapterUrl/rssArticle/fromBookInfo | 规则中的 @js、<js>、{{js}} |

> **关键**：JS 代码中 `java.xxx()` 调用通过 Rhino 反射路由到 JsExtensions 方法。三层 evalJS 注入变量不同，仿真需区分。

#### 执行流程层的处理策略

| 类 | 策略 | 说明 |
|----|------|------|
| WebBook | **不抽取，Debugger 内联实现** | WebBook 是协程入口，JVM 用同步调用替代 |
| Rss | **不抽取，Debugger 内联实现** | 同上 |
| BookList/BookInfo/BookChapterList/BookContent | **不抽取，Debugger 内联实现** | 解析逻辑由 AnalyzeRule 承担，Debugger 直接调用 |
| RssParserByRule | **不抽取，Debugger 内联实现** | 列表解析逻辑由 AnalyzeRule.getElements 承担 |
| RssParserDefault | **不抽取，跳过** | XML 回退解析，JVM 环境中 ruleArticles 不为空时不触发 |
| BaseSource | **不抽取，拆解继承** | BookSource/RssSource 移除继承，JsExtensions 由 Stub 注入 |
| SharedJsScope | **简化实现** | 共享 JS 作用域，JVM 用简单 Map 缓存替代 |
| loginCheckJs | **Debugger 内联** | 登录检测逻辑在 Debugger 中直接调用 evalJS |
| checkRedirect | **Debugger 内联** | 重定向检测在 Debugger 中直接记录日志 |

> **结论**：执行流程层类不抽取到新模块，而是在 RssSourceDebugger/BookSourceDebugger 中内联实现。Debugger 直接调用 AnalyzeUrl + AnalyzeRule 完成请求和解析，跳过 WebBook/Rss 的协程封装。

### 1.4 modules/rhino 模块复用

Legado 的 `modules/rhino` 模块已经几乎 JVM 就绪（31 个源文件，2 个有 Android 依赖）：

```groovy
// modules/rhino/build.gradle
// 原: plugins { id: 'com.android.library' }
// 改: plugins { id: 'org.jetbrains.kotlin.jvm' }
// 依赖全部 JVM 兼容：rhino + coroutines-core + okhttp + androidx.collection
```

**实际需改 5-6 处（涉及 2 个源文件 + build.gradle）（非仅改 Gradle 插件）**：
1. 改 build.gradle 插件：`android.library` → `kotlin("jvm")`
2. 改 RhinoClassShutter.kt：`android.os.Build.VERSION.SDK_INT >= Build.VERSION_CODES.O` → JVM 等价判断（直接假定 true，JVM 都支持 nio.file）
3. 移除 `androidx.collection` 依赖（检查是否有代码引用，若有替换为 `java.util`）
4. 移除 `android.content.Context::class.java` 在 protectedClasses 中的引用
5. 删除空的 AndroidManifest.xml
6. 替换 ClassNameMatcher.kt 的 androidx.collection.LruCache：改为 java.util.LinkedHashMap + 手动 LRU 逻辑

可以直接将 `modules/rhino` 作为新模块的依赖，或将其源码合并到 `.trae/skills/legado-source-creator/tools/legado-jvm/`。

## 2. Architecture Decisions（架构决策）

### AD-1: 抽取而非重写

**决策**：从 Legado 真机源码直接抽取核心类，移除 Android 依赖，而非从零重写。

**理由**：

* 当前 MinimalMockJsExtensions/MockSymmetricCrypto 等自造类行为与真机不一致

* ZeroPadding、`{{page}}`、相对URL 等问题在真机源码中已正确处理

* 抽取方式可保证行为一致性，减少 bug

### AD-2: 单 JAR 打包

**决策**：合并 MVP1-4 为单一 fat JAR。

**理由**：

* 4 个 JAR 增加维护复杂度

* 用户和 AI 都不需要区分 MVP1-4 的功能边界

* 单 JAR 更易于部署和版本管理

### AD-3: JsExtensions 接口拆分

**决策**：将 JsExtensions 拆分为 Interface + Stub，而非直接修改源码。

**理由**：

* JsExtensions 直接依赖 Activity/WebView/Context，无法直接抽取

* 接口拆分允许未来在 Android 环境中使用真实实现

* Stub 实现可逐步完善，不影响接口稳定性

### AD-4: 批处理模式优先于常驻服务

**决策**：实现 `batch` 命令（一次处理多个源），而非常驻 HTTP 服务。

**理由**：

* 批处理模式实现简单，只需修改 stdin/stdout 协议

* 常驻服务需要端口管理、心跳检测、连接池等额外复杂度

* 批处理已能解决性能问题（7 个源从 30+ 秒降到 <15 秒）

### AD-5: 保留 stdin/stdout JSON 协议

**决策**：新 JAR 保留与 MVP1-4 相同的 stdin/stdout JSON 协议。

**理由**：

* debug-source.py 等客户端脚本无需大改

* 向后兼容，降低迁移成本

### AD-6: 旧 MVP1-4 标记 deprecated

**决策**：不删除旧 MVP1-4 目录，标记为 deprecated。

**理由**：

* 保留历史代码供参考

* 避免误删有用的测试数据

### AD-7: modules/rhino 直接复用

**决策**：将 `modules/rhino` 的 Gradle 插件改为 `kotlin-jvm`，作为新模块的依赖。

**理由**：

* modules/rhino 31 个源文件中仅 1 个（RhinoClassShutter.kt）有 Android 依赖

* 需改 3-5 处（插件+Build依赖+androidx.collection+Context引用），非仅改插件

* Rhino 引擎是规则解析的核心依赖

### AD-8: Python 客户端全面适配（非仅改 JAR 路径）

**决策**：Python 客户端需要全面适配性改造，包括 10+ 个脚本的逻辑适配，而非仅改 JAR 路径。

**理由**：
- 新 JAR 的行为可能与旧仿真端有细微差异（如错误信息格式、Cookie 处理行为）
- 批处理模式需要客户端配合（组装 batch 命令、解析进度输出）
- site_type_detector / obstacle_resolver 等需要与新 JAR 的 CookieStore/NetworkUtils 对齐
- error_translator 需要翻译新 JAR 可能产生的新错误类型

### AD-9: Skill 文档全面适配（非仅改路径引用）

**决策**：Skill 的 SKILL.md / references / troubleshooting / 经验教训需要全面适配新架构。

**理由**：
- SKILL.md 中的架构描述从「从零仿真」改为「源码抽取」，5 阶段工作流需适配
- troubleshooting 79 条陷阱中，部分陷阱（ZeroPadding/`{{page}}`/相对URL）在新 JAR 中已自动修复，需移除
- 新 JAR 的 JsExtensionsStub 有降级限制（WebView 无法执行 JS），需新增对应陷阱
- basic-memory 中的旧经验需标注过时，新架构经验需写入

### AD-10: 大规模真实源抽样测试（26,583 源 → 300 抽样）

**决策**：用 temp/book/（23,881 书源）和 temp/rss/（2,702 订阅源）进行科学抽样测试，而非逐一测试。

**理由**：
- 26,583 个源逐一测试不现实（即使批处理也需要数小时）
- 科学抽样（书源 200 + 订阅源 100 = 300）已能覆盖主要网站类型和规则模式
- 抽样测试的通过率可作为整体质量的置信区间估计
- 失败源的分析可发现新 JAR 的系统性问题

### AD-11: BaseSource 接口不抽取，拆解继承链

**决策**：不抽取 BaseSource 接口，BookSource/RssSource 移除 `: BaseSource` 继承，改为独立 POJO。

**理由**：
- BaseSource 是 `interface BaseSource : JsExtensions`，继承它会拖入 77 个 import 的重型依赖链
- JsExtensions 方法（ajax/getCookie/base64Decode 等）在真机中由 AnalyzeRule/AnalyzeUrl 实现，数据模型不需要继承
- JVM 环境中 JsExtensionsStub 在 AnalyzeRule/AnalyzeUrl 中注入，与数据模型无关
- 移除继承后 BookSource/RssSource 变为纯数据容器，Gson 序列化/反序列化更简单

### AD-12: 执行流程层内联实现，不抽取 WebBook/Rss

**决策**：WebBook/Rss/BookList/BookInfo/BookChapterList/BookContent/RssParserByRule 等执行流程层类不抽取到新模块，在 Debugger 中内联实现。

**理由**：
- 执行流程层类深度绑定 Android 协程（Coroutine.async/onSuccess/onError 链式封装）
- JVM 环境用同步调用替代协程，不需要 WebBook 的异步封装
- 解析逻辑（getString/getElements/getStringList）由 AnalyzeRule 承担，Debugger 直接调用即可
- 抽取执行流程层会引入大量协程/ViewModel/Repository 依赖，得不偿失

## 3. Data Flow（数据流）

### 3.1 单源调试流程

```
debug-source.py
  ↓ stdin: {"cmd":"debugRssSource","sourceJson":"...","key":"分类"}
JVM 启动
  ↓
RuleEngineServer.main()
  ↓ 解析 JSON 命令
RssSourceDebugger.debugSort()
  ↓ AnalyzeUrl 构造 URL（真机源码逻辑）
  ↓ AnalyzeUrl.getStrResponse()（okhttp 请求）
  ↓ AnalyzeRule.getStringList()（真机源码逻辑）
  ↓ stdout: {"type":"log","msg":"...","html":"..."}
RssSourceDebugger.debugContent()
  ↓ AnalyzeUrl 构造内容 URL
  ↓ AnalyzeRule.getString()（真机源码逻辑）
  ↓ stdout: {"type":"result","success":true,"summary":{...}}
JVM 退出
```

### 3.2 批处理流程

```
debug-source.py --batch sources/*.json
  ↓ stdin: {"cmd":"batch","sources":[{...},{...},...]}
JVM 启动（一次）
  ↓
RuleEngineServer.main()
  ↓ 解析 batch 命令
for each source:
  RssSourceDebugger.debugSort()
  RssSourceDebugger.debugContent()
  ↓ stdout: {"type":"result","sourceName":"...","success":true,...}
  ↓ stdout: {"type":"batch_progress","current":3,"total":7}
stdout: {"type":"batch_complete","results":[...]}
JVM 退出（一次）
```

## 4. File Changes（文件变更）

### 4.1 新增文件

| 文件                                                                             | 说明               |
| ------------------------------------------------------------------------------ | ---------------- |
| `.trae/skills/legado-source-creator/tools/legado-jvm/build.gradle.kts`                                            | 新 Gradle 模块配置    |
| `.trae/skills/legado-source-creator/tools/legado-jvm/settings.gradle.kts`                                         | 模块设置             |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/model/analyzeRule/*.kt`        | 11 个抽取的规则引擎类     |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/data/entities/BookSource.kt`   | 抽取的书源模型          |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/data/entities/RssSource.kt`    | 抽取的 RSS 源模型      |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/help/JsExtensionsInterface.kt` | JS 扩展接口          |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/help/JsExtensionsStub.kt`      | JS 扩展 JVM 实现     |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/utils/NetworkUtilsStub.kt`     | 网络工具 JVM 实现      |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/utils/CacheManagerStub.kt`     | 缓存管理 JVM 实现      |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/help/CookieStoreInterface.kt`  | Cookie 存储接口      |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/app/help/CookieStoreStub.kt`       | Cookie 存储 JVM 实现 |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/RuleEngineServer.kt`    | 服务端入口            |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/RssSourceDebugger.kt`   | RSS 源调试器         |
| `.trae/skills/legado-source-creator/tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/BookSourceDebugger.kt`  | 书源调试器            |

### 4.2 修改文件

| 文件                                                               | 修改内容                                  |
| ---------------------------------------------------------------- | ------------------------------------- |
| `modules/rhino/build.gradle`                                     | 插件从 `android.library` 改为 `kotlin-jvm` |
| `.trae/skills/legado-source-creator/scripts/debug-source.py`     | JAR 路径改为新 JAR                         |
| `.trae/skills/legado-source-creator/scripts/test_all_sources.py` | JAR 路径改为新 JAR                         |

### 4.3 标记 deprecated

| 文件/目录                               | 说明                 |
| ----------------------------------- | ------------------ |
| `.trae/skills/legado-source-creator/tools/mvp1-build/` | 标记为 deprecated，不删除 |
| `.trae/skills/legado-source-creator/tools/legado-rule-engine-mvp*.jar` | 标记为 deprecated，不删除 |

## 5. 风险与缓解

| 风险                              | 概率 | 影响 | 缓解措施                    |
| ------------------------------- | -- | -- | ----------------------- |
| JsExtensions 方法太多（500+行），接口拆分遗漏 | 中  | 高  | 先列出所有 public 方法，逐一映射到接口 |
| AnalyzeRule 内部依赖比预期更多           | 中  | 中  | 逐个 import 排查，创建对应 Stub  |
| modules/rhino 改插件后编译失败          | 低  | 中  | 保留原模块，新模块直接复制 rhino 源码  |
| 真实源优化后发现规则本身有缺陷                 | 高  | 中  | 标记为需用户介入，输出修复建议         |
| BaseSource 继承链拆解导致编译错误 | 中 | 高 | 移除继承后逐一修复编译错误，JsExtensions 方法由 Stub 注入 |
| 执行流程层内联实现遗漏关键步骤 | 中 | 中 | 对照源码调用链逐一实现 loginCheckJs/checkRedirect/分页机制 |

## 6. JsExtensions 方法清单与处理策略（源码参照）

> **源码参照**：`app/src/main/java/io/legado/app/help/JsExtensions.kt`（102 方法）+ `app/src/main/java/io/legado/app/help/JsEncodeUtils.kt`（30 方法）= **132 个方法**
>
> **抽取原则**：每个方法必须先读源码再定策略，禁止臆测。策略分三类：
> - **完整实现**：纯 JVM 逻辑或依赖已抽取的类，可直接用
> - **Stub 降级**：依赖 Android 平台（WebView/Activity/Context/文件系统），降级为 HTTP 或空实现
> - **不可用**：纯 UI 交互，JVM 无法实现，抛出明确异常

### 6.1 JsExtensions 自身方法（102 个）

| 分类 | 方法签名 | 源码行号 | 策略 | Stub 实现说明 |
|------|---------|---------|------|-------------|
| **抽象** | `getSource(): BaseSource?` | L91 | 完整实现 | 由 Debugger 传入 |
| **抽象** | `getTag(): String?` | L92 | 完整实现 | 由 Debugger 传入 |
| **HTTP** | `ajax(url: Any): String?` | L100 | 完整实现 | 委托 AnalyzeUrl（已抽取） |
| **HTTP** | `ajax(url: Any, callTimeout: Long?): String?` | L104 | 完整实现 | 同上 |
| **HTTP** | `ajaxAll(urlList: Array<String>): Array<StrResponse>` | L124 | 完整实现 | runBlocking+flow，JVM 兼容 |
| **HTTP** | `ajaxAll(urlList, skipRateLimit): Array<StrResponse>` | L127 | 完整实现 | 同上 |
| **HTTP** | `ajaxTestAll(urlList, timeout): Array<StrResponse>` | L143 | 完整实现 | 同上 |
| **HTTP** | `ajaxTestAll(urlList, timeout, skipRateLimit): Array<StrResponse>` | L146 | 完整实现 | 同上 |
| **HTTP** | `connect(urlStr: String): StrResponse` | L164 | 完整实现 | 委托 AnalyzeUrl |
| **HTTP** | `connect(urlStr, header: String?): StrResponse` | L180 | 完整实现 | 同上 |
| **HTTP** | `connect(urlStr, header, callTimeout): StrResponse` | L184 | 完整实现 | 同上 |
| **HTTP** | `get(urlStr, headers): Connection.Response` | L483 | 完整实现 | Jsoup.connect，JVM 兼容 |
| **HTTP** | `get(urlStr, headers, timeout): Connection.Response` | L487 | 完整实现 | 同上 |
| **HTTP** | `head(urlStr, headers): Connection.Response` | L509 | 完整实现 | 同上 |
| **HTTP** | `head(urlStr, headers, timeout): Connection.Response` | L513 | 完整实现 | 同上 |
| **HTTP** | `post(urlStr, body, headers): Connection.Response` | L535 | 完整实现 | 同上 |
| **HTTP** | `post(urlStr, body, headers, timeout): Connection.Response` | L539 | 完整实现 | 同上 |
| **WebView** | `webView(html, url, js): String?` | L203 | **Stub 降级** | HTTP+正则替代，已知限制：无法执行 JS |
| **WebView** | `webView(html, url, js, cacheFirst): String?` | L215 | **Stub 降级** | 同上 |
| **WebView** | `webViewGetSource(html, url, js, sourceRegex): String?` | L231 | **Stub 降级** | 同上 |
| **WebView** | `webViewGetSource(html, url, js, sourceRegex, cacheFirst): String?` | L234 | **Stub 降级** | 同上 |
| **WebView** | `webViewGetSource(html, url, js, sourceRegex, cacheFirst, delayTime): String?` | L241 | **Stub 降级** | 同上 |
| **WebView** | `webViewGetOverrideUrl(html, url, js, overrideUrlRegex): String?` | L266 | **Stub 降级** | 同上 |
| **WebView** | `webViewGetOverrideUrl(html, url, js, overrideUrlRegex, cacheFirst): String?` | L269 | **Stub 降级** | 同上 |
| **WebView** | `webViewGetOverrideUrl(html, url, js, overrideUrlRegex, cacheFirst, delayTime): String?` | L276 | **Stub 降级** | 同上 |
| **UI** | `openVideoPlayer(url, title)` | L302 | **不可用** | 抛 NoStackTraceException |
| **UI** | `openVideoPlayer(url, title, isFloat)` | L313 | **不可用** | 同上 |
| **UI** | `startBrowser(url, title)` | L322 | **不可用** | 抛异常，提示需真机 |
| **UI** | `startBrowser(url, title, html)` | L326 | **不可用** | 同上 |
| **UI** | `startBrowserAwait(url, title): StrResponse` | L334 | **不可用** | 同上 |
| **UI** | `startBrowserAwait(url, title, refetchAfterSuccess): StrResponse` | L338 | **不可用** | 同上 |
| **UI** | `startBrowserAwait(url, title, refetchAfterSuccess, html): StrResponse` | L342 | **不可用** | 同上 |
| **UI** | `getVerificationCode(imageUrl): String` | L354 | **不可用** | 同上 |
| **UI** | `toast(msg)` | L1088 | **Stub 降级** | 改为 log() 输出到 stdout |
| **UI** | `longToast(msg)` | L1096 | **Stub 降级** | 同上 |
| **UI** | `openUrl(url)` | L1138 | **不可用** | 抛异常 |
| **UI** | `openUrl(url, mimeType)` | L1147 | **不可用** | 同上 |
| **Cookie** | `getCookie(tag): String` | L407 | 完整实现 | 委托 CookieStoreStub |
| **Cookie** | `getCookie(tag, key): String` | L412 | 完整实现 | 同上 |
| **文件** | `getFile(path): File` | L701 | **Stub 降级** | 改为临时目录，移除 appCtx |
| **文件** | `readFile(path): ByteArray?` | L716 | **Stub 降级** | 同上 |
| **文件** | `readTxtFile(path): String` | L725 | **Stub 降级** | 同上 |
| **文件** | `readTxtFile(path, charsetName): String` | L735 | **Stub 降级** | 同上 |
| **文件** | `deleteFile(path): Boolean` | L747 | **Stub 降级** | 同上 |
| **文件** | `unzipFile(zipPath): String` | L758 | **Stub 降级** | ArchiveUtils JVM 兼容 |
| **文件** | `un7zFile(zipPath): String` | L768 | **Stub 降级** | 同上 |
| **文件** | `unrarFile(zipPath): String` | L778 | **Stub 降级** | 同上 |
| **文件** | `unArchiveFile(zipPath): String` | L788 | **Stub 降级** | 同上 |
| **文件** | `getTxtInFolder(path): String` | L802 | **Stub 降级** | 同上 |
| **文件** | `importScript(path): String` | L363 | **Stub 降级** | HTTP 下载或本地读取 |
| **文件** | `cacheFile(urlStr): String` | L378 | **Stub 降级** | 委托 CacheManagerStub |
| **文件** | `cacheFile(urlStr, saveTime): String` | L387 | **Stub 降级** | 同上 |
| **文件** | `downloadFile(url): String` | L426 | **Stub 降级** | 临时目录 |
| **文件** | `downloadFile(content, url): String` | L462 | **Stub 降级** | 同上（Deprecated） |
| **压缩** | `getZipStringContent(url, path): String` | L827 | 完整实现 | JVM ZipInputStream |
| **压缩** | `getZipStringContent(url, path, charsetName): String` | L834 | 完整实现 | 同上 |
| **压缩** | `getRarStringContent(url, path): String` | L846 | **Stub 降级** | LibArchiveUtils 需适配 |
| **压缩** | `getRarStringContent(url, path, charsetName): String` | L853 | **Stub 降级** | 同上 |
| **压缩** | `get7zStringContent(url, path): String` | L865 | **Stub 降级** | 同上 |
| **压缩** | `get7zStringContent(url, path, charsetName): String` | L872 | **Stub 降级** | 同上 |
| **压缩** | `getZipByteArrayContent(url, path): ByteArray?` | L883 | 完整实现 | JVM ZipInputStream |
| **压缩** | `getRarByteArrayContent(url, path): ByteArray?` | L911 | **Stub 降级** | LibArchiveUtils 需适配 |
| **压缩** | `get7zByteArrayContent(url, path): ByteArray?` | L929 | **Stub 降级** | 同上 |
| **Base64** | `base64Decode(str: String?): String` | L581 | 完整实现 | hutool Base64 |
| **Base64** | `base64Decode(str, charset): String` | L586 | 完整实现 | 同上 |
| **Base64** | `base64Decode(str, flags): String` | L591 | 完整实现 | EncoderUtils 需适配：android.util.Base64→java.util.Base64 |
| **Base64** | `base64DecodeToByteArray(str): ByteArray?` | L595 | 完整实现 | 同上 |
| **Base64** | `base64DecodeToByteArray(str, flags): ByteArray?` | L602 | 完整实现 | 同上 |
| **Base64** | `base64Encode(str): String?` | L610 | 完整实现 | 同上 |
| **Base64** | `base64Encode(str, flags): String?` | L615 | 完整实现 | 同上 |
| **Hex** | `hexDecodeToByteArray(hex): ByteArray?` | L620 | 完整实现 | hutool HexUtil |
| **Hex** | `hexDecodeToString(hex): String?` | L626 | 完整实现 | 同上 |
| **Hex** | `hexEncodeToString(utf8): String?` | L632 | 完整实现 | 同上 |
| **转换** | `strToBytes(str): ByteArray` | L560 | 完整实现 | 纯 JVM |
| **转换** | `strToBytes(str, charset): ByteArray` | L564 | 完整实现 | 纯 JVM |
| **转换** | `bytesToStr(bytes): String` | L569 | 完整实现 | 纯 JVM |
| **转换** | `bytesToStr(bytes, charset): String` | L573 | 完整实现 | 纯 JVM |
| **时间** | `timeFormatUTC(time, format, sh): String?` | L640 | 完整实现 | 纯 JVM SimpleDateFormat |
| **时间** | `timeFormat(time): String` | L652 | 完整实现 | 纯 JVM |
| **编码** | `encodeURI(str): String` | L657 | 完整实现 | java.net.URLEncoder |
| **编码** | `encodeURI(str, enc): String` | L666 | 完整实现 | 同上 |
| **编码** | `htmlFormat(str): String` | L675 | **Stub 降级** | HtmlFormatter 需 JVM 适配 |
| **编码** | `t2s(text): String` | L680 | **Stub 降级** | ChineseUtils 需 JVM 适配 |
| **编码** | `s2t(text): String` | L685 | **Stub 降级** | 同上 |
| **字体** | `queryBase64TTF(data): QueryTTF?` | L951 | 完整实现 | QueryTTF 已抽取（Deprecated） |
| **字体** | `queryTTF(data, useCache): QueryTTF?` | L962 | **Stub 降级** | AppCacheManager 需 Stub |
| **字体** | `queryTTF(data): QueryTTF?` | L1006 | **Stub 降级** | 同上 |
| **字体** | `replaceFont(text, error, correct, filter): String` | L1016 | 完整实现 | 纯逻辑 |
| **字体** | `replaceFont(text, error, correct): String` | L1053 | 完整实现 | 同上 |
| **工具** | `toNumChapter(s): String?` | L1066 | 完整实现 | 纯逻辑 |
| **工具** | `toURL(urlStr): JsURL` | L1077 | 完整实现 | JsURL JVM 兼容 |
| **工具** | `toURL(url, baseUrl): JsURL` | L1081 | 完整实现 | 同上 |
| **工具** | `log(msg): Any?` | L1104 | **Stub 降级** | Debug→stdout |
| **工具** | `logType(any)` | L1116 | **Stub 降级** | 同上 |
| **工具** | `randomUUID(): String` | L1128 | 完整实现 | java.util.UUID |
| **工具** | `androidId(): String` | L1133 | **Stub 降级** | 返回固定值或空 |
| **工具** | `getWebViewUA(): String` | L690 | **Stub 降级** | 返回固定 UA |
| **配置** | `getReadBookConfig(): String` | L1170 | **Stub 降级** | 返回默认配置 JSON |
| **配置** | `getReadBookConfigMap(): Map<String, Any>` | L1174 | **Stub 降级** | 同上 |
| **配置** | `getThemeMode(): String` | L1182 | **Stub 降级** | 返回 "0" |
| **配置** | `getThemeConfig(): String` | L1190 | **Stub 降级** | 返回默认 JSON |
| **配置** | `getThemeConfigMap(): Map<String, Any?>` | L1195 | **Stub 降级** | 同上 |

### 6.2 JsEncodeUtils 继承方法（30 个）

> **源码参照**：`app/src/main/java/io/legado/app/help/JsEncodeUtils.kt`

| 分类 | 方法签名 | 源码行号 | 策略 | 说明 |
|------|---------|---------|------|------|
| **MD5** | `md5Encode(str): String` | L22 | 完整实现 | MD5Utils JVM 兼容 |
| **MD5** | `md5Encode16(str): String` | L27 | 完整实现 | 同上 |
| **对称加密** | `createSymmetricCrypto(transformation, key: ByteArray?, iv: ByteArray?): SymmetricCrypto` | L45 | **Stub 降级** | SymmetricCryptoAndroid→SymmetricCrypto（hutool） |
| **对称加密** | `createSymmetricCrypto(transformation, key: ByteArray): SymmetricCrypto` | L54 | **Stub 降级** | 同上 |
| **对称加密** | `createSymmetricCrypto(transformation, key: String): SymmetricCrypto` | L61 | **Stub 降级** | 同上 |
| **对称加密** | `createSymmetricCrypto(transformation, key: String, iv: String?): SymmetricCrypto` | L68 | **Stub 降级** | 同上 |
| **非对称** | `createAsymmetricCrypto(transformation): AsymmetricCrypto` | L80 | 完整实现 | AsymmetricCrypto JVM 兼容 |
| **签名** | `createSign(algorithm): Sign` | L87 | 完整实现 | Sign JVM 兼容 |
| **AES** | `aesDecodeToByteArray(str, key, transformation, iv): ByteArray?` | L106 | 完整实现 | 委托 createSymmetricCrypto（Deprecated） |
| **AES** | `aesDecodeToString(str, key, transformation, iv): String?` | L124 | 完整实现 | 同上（Deprecated） |
| **AES** | `aesDecodeArgsBase64Str(data, key, mode, padding, iv): String?` | L145 | 完整实现 | android.util.Base64→java.util.Base64 |
| **AES** | `aesBase64DecodeToByteArray(str, key, transformation, iv): ByteArray?` | L170 | 完整实现 | 委托 createSymmetricCrypto |
| **AES** | `aesBase64DecodeToString(str, key, transformation, iv): String?` | L188 | 完整实现 | 同上 |
| **AES** | `aesEncodeToByteArray(data, key, transformation, iv): ByteArray?` | L205 | 完整实现 | 同上 |
| **AES** | `aesEncodeToString(data, key, transformation, iv): String?` | L223 | 完整实现 | 同上 |
| **AES** | `aesEncodeToBase64ByteArray(data, key, transformation, iv): ByteArray?` | L240 | 完整实现 | 同上 |
| **AES** | `aesEncodeToBase64String(data, key, transformation, iv): String?` | L258 | 完整实现 | 同上 |
| **AES** | `aesEncodeArgsBase64Str(data, key, mode, padding, iv): String?` | L280 | 完整实现 | 同上 |
| **DES** | `desDecodeToString(data, key, transformation, iv): String?` | L296 | 完整实现 | 同上 |
| **DES** | `desBase64DecodeToString(data, key, transformation, iv): String?` | L307 | 完整实现 | 同上 |
| **DES** | `desEncodeToString(data, key, transformation, iv): String?` | L318 | 完整实现 | 同上 |
| **DES** | `desEncodeToBase64String(data, key, transformation, iv): String?` | L329 | 完整实现 | 同上 |
| **3DES** | `tripleDESDecodeStr(data, key, mode, padding, iv): String?` | L351 | 完整实现 | 同上 |
| **3DES** | `tripleDESDecodeArgsBase64Str(data, key, mode, padding, iv): String?` | L376 | 完整实现 | android.util.Base64→java.util.Base64 |
| **3DES** | `tripleDESEncodeBase64Str(data, key, mode, padding, iv): String?` | L406 | 完整实现 | 委托 createSymmetricCrypto |
| **3DES** | `tripleDESEncodeArgsBase64Str(data, key, mode, padding, iv): String?` | L432 | 完整实现 | android.util.Base64→java.util.Base64 |
| **摘要** | `digestHex(data, algorithm): String` | L456 | 完整实现 | hutool DigestUtil |
| **摘要** | `digestBase64Str(data, algorithm): String` | L471 | 完整实现 | android.util.Base64→java.util.Base64 |
| **HMac** | `HMacHex(data, algorithm, key): String` | L488 | 完整实现 | hutool HMac |
| **HMac** | `HMacBase64(data, algorithm, key): String` | L506 | 完整实现 | android.util.Base64→java.util.Base64 |

### 6.3 方法统计

| 策略 | JsExtensions | JsEncodeUtils | 合计 | 占比 |
|------|-------------|--------------|------|------|
| **完整实现** | 59 | 27 | 86 | 65% |
| **Stub 降级** | 35 | 3 | 38 | 29% |
| **不可用** | 8 | 0 | 8 | 6% |
| **合计** | 102 | 30 | 132 | 100% |

> **关键结论**：65% 的方法可直接完整实现（含 base64 替换），29% 需 Stub 降级（主要是 WebView/UI/文件操作），仅 6% 完全不可用（纯 UI 交互）。

## 7. 防"瞎猜测"机制（强制流程）

> **核心原则**：本次改造的最核心流程以及代码参照对象一定是 Legado 开源阅读的源码。禁止任何形式的臆测。

### 7.1 强制四步流程

每个抽取/改造任务必须严格遵循以下四步，缺一不可：

```
步骤1: 读源码 → 步骤2: 写代码 → 步骤3: 对比测试 → 步骤4: 提交
(必须读)     (按源码写)    (同输入同输出)    (附源码路径)
```

| 步骤 | 动作 | 产出 | 禁止行为 |
|------|------|------|---------|
| **1.读源码** | 阅读 Legado 源码对应文件+行号 | 源码路径引用 | ❌ 跳过直接写代码 |
| **2.写代码** | 按源码逻辑抽取，仅移除 Android 依赖 | 抽取后的类 | ❌ 从零重写/臆测行为 |
| **3.对比测试** | 同输入→对比输出（源码 vs 抽取后） | 测试报告 | ❌ 只编译不测试 |
| **4.提交** | 提交时附源码路径+diff 说明 | commit | ❌ 无源码引用的提交 |

### 7.2 源码参照路径规范

每个任务必须标注源码参照路径，格式：

```
源码参照: app/src/main/java/io/legado/app/{路径}/{文件名}.kt#L{起始行}-L{结束行}
```

示例：
```
源码参照: app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeRule.kt#L1-L50
```

### 7.3 禁止行为清单

| 禁止行为 | 正确做法 |
|---------|---------|
| ❌ 不读源码就写代码 | ✅ 先 Read 源码文件，理解逻辑再动手 |
| ❌ 凭经验臆测方法行为 | ✅ 查源码确认方法签名和返回值 |
| ❌ 从零重写已有逻辑 | ✅ 抽取源码，仅移除 Android 依赖 |
| ❌ 修 bug 靠猜测 | ✅ 查源码找根因，对比行为差异 |
| ❌ 只编译不测试 | ✅ 编写对比测试，同输入同输出 |
| ❌ 遇到报错就瞎改 | ✅ 读报错信息→查源码→定位根因→修复 |

### 7.4 报错处理流程

遇到编译/运行报错时：

```
报错 → 1.读取完整报错信息 → 2.定位报错位置 → 3.查 Legado 源码对应逻辑
     → 4.对比差异 → 5.修复 → 6.回归测试
```

**禁止**：报错 → 瞎改 → 再报错 → 再瞎改 → 无限循环

## 8. 增量验证门禁

> 每个阶段完成后必须通过验证门禁，未通过禁止进入下一阶段。

### 8.1 阶段一门禁：A/B/C 级抽取

| 检查项 | 通过标准 | 验证方法 |
|--------|---------|---------|
| 编译通过 | `gradlew :legado-jvm:compileKotlin` 成功 | 执行命令 |
| 源码 diff | diff 仅含 Android 依赖移除 | `diff` 对比 |
| 行为对比 | AnalyzeByJSoup 解析 HTML 结果一致 | 单元测试 |
| 方法覆盖 | 9 个类的 public 方法全部覆盖 | 检查清单 |

### 8.2 阶段二门禁：D 级抽取

| 检查项 | 通过标准 | 验证方法 |
|--------|---------|---------|
| 编译通过 | D 级 5 个类编译成功 | 执行命令 |
| JsExtensions 方法覆盖 | 132 个方法全部有策略 | 对照第6节清单 |
| AnalyzeRule 五种规则 | CSS/XPath/JSONPath/Regex/JS 全部通过 | 单元测试 |
| AnalyzeUrl URL 构造 | `{{page}}`/`@js:`/header/body 全部通过 | 单元测试 |
| 行为对比 | 与旧仿真端对比，行为一致或更优 | 对比测试 |

### 8.3 阶段三门禁：单 JAR 打包

| 检查项 | 通过标准 | 验证方法 |
|--------|---------|---------|
| fat JAR 生成 | `gradlew fatJar` 成功 | 执行命令 |
| JAR 大小 | <15MB | `ls -la` |
| 启动成功 | `java -jar` 启动无报错 | 执行命令 |
| 协议兼容 | stdin/stdout JSON 正确 | 手动测试 |

### 8.4 阶段四门禁：批处理+Python 适配

| 检查项 | 通过标准 | 验证方法 |
|--------|---------|---------|
| 批处理 7 源 | 总耗时 <15 秒 | 计时 |
| Python 脚本 | 10+ 脚本全部适配 | 逐个执行 |
| 错误处理 | 新错误类型有翻译 | error_translator 测试 |

### 8.5 阶段五门禁：真实源优化

| 检查项 | 通过标准 | 验证方法 |
|--------|---------|---------|
| 8 源测试 | 通过率 >85% | 测试报告 |
| 失败源分析 | 每个有分类+建议 | 报告检查 |

### 8.6 阶段六门禁：Skill 适配

| 检查项 | 通过标准 | 验证方法 |
|--------|---------|---------|
| SKILL.md | <500 行，与实际一致 | 行数+内容检查 |
| 79 条陷阱 | 与新 JAR 行为一致 | 逐条核对 |
| 经验教训 | 旧经验标注过时 | basic-memory 检查 |

### 8.7 阶段七门禁：大规模测试

| 检查项 | 通过标准 | 验证方法 |
|--------|---------|---------|
| 书源 200 个 | 通过率 >70% | 测试报告 |
| 订阅源 100 个 | 通过率 >75% | 测试报告 |
| 失败分析 | 每个有分类+建议 | 报告检查 |

## 9. 79 条陷阱映射表（自动修复/保留/新增）

> **源码参照**：`.trae/skills/legado-source-creator/references/troubleshooting/_index.md`（6 子文档，79 条陷阱）
>
> **映射目的**：源码抽取后，部分陷阱会被自动修复（因使用真机逻辑），部分保留（规则编写本身），部分新增（Stub 降级限制）。Skill 适配阶段需据此更新陷阱清单。

### 9.1 自动修复类（源码抽取后不再出现）

| 陷阱# | 陷阱描述 | 自动修复原因 |
|--------|---------|-------------|
| #72 | searchUrl中`<js>`不能用`{{key}}` | AnalyzeUrl 源码抽取后，evalJS 正确绑定 `bindings["key"]=key` |
| #75 | header @js:中`{{baseUrl}}`不替换 | AnalyzeUrl 源码抽取后，replaceKeyPageJs 正确处理 |
| #77 | Legado URL拼接不用abs:href | NetworkUtils.getAbsoluteURL 源码抽取，行为一致 |
| ZeroPadding | Java不支持的AES填充 | hutool SymmetricCrypto 支持 ZeroPadding |
| `{{page}}`模板 | URL中`{{page}}`未替换 | AnalyzeUrl 构造函数正确接收 page 参数 |
| 相对URL拼接 | 相对URL转绝对URL错误 | NetworkUtils.getAbsoluteURL 源码逻辑 |
| String→List类型 | String 返回值当 List 处理 | AnalyzeRule 源码正确处理类型转换 |

### 9.2 保留类（与源码抽取无关，规则编写本身陷阱）

| 陷阱# | 陷阱描述 | 保留原因 |
|--------|---------|---------|
| #1 | ES5 only | Rhino 引擎限制，与抽取无关 |
| #2 | java遮蔽Java包 | Rhino 语法限制 |
| #5 | getElements返回类型 | 规则编写陷阱 |
| #6 | NativeObject属性 | Rhino 语法限制 |
| #9 | Java String→JS | Rhino 语法限制 |
| #11 | decryptStr vs decrypt | API 使用陷阱 |
| #12 | loginCheckJs不返回result | 规则编写陷阱 |
| #14 | RssSource字段扁平 | 数据模型陷阱 |
| #15 | type选择 | 源配置陷阱 |
| #17 | enableJs≠webView | 源配置陷阱 |
| #19 | URL拼接缺`/` | 规则编写陷阱 |
| #37 | WebFetch丢标签 | 工具限制 |
| #42 | sourceIcon域名 | 规则编写陷阱 |
| #47 | CSS伪类冲突 | 规则编写陷阱 |
| #52 | ajax()返回String | API 使用陷阱 |
| #53 | Mirages图片加密 | 加密场景陷阱 |
| #55 | loginCheckJs必须返回StrResponse | 规则编写陷阱 |
| #57 | loginCheckJs无限循环 | 规则编写陷阱 |
| #58 | ruleContent拆分`<js>`和HTML | 规则编写陷阱 |
| #59 | 多播放源优先选m3u8 | 规则编写陷阱 |
| #60 | JS中result可能是Element | 规则编写陷阱 |
| #61 | java.ajax()空URL崩溃 | 规则编写陷阱 |
| #62 | @CSS:前缀必须 | 规则编写陷阱 |
| #63 | ruleImage用result.select() | 规则编写陷阱 |
| #64 | ruleArticles排除表头 | 规则编写陷阱 |
| #65 | Playwright无法破CF盾 | 工具限制 |
| #66 | 应用层搜索验证码 | 反爬场景陷阱 |
| #68 | Rhino正则不能含单引号 | Rhino 语法限制 |
| #69 | ruleContent不要嵌入HTML模板 | 规则编写陷阱 |
| #73 | searchUrl避免用<js>标签 | 规则编写陷阱 |
| #74 | loginCheckJs中result是StrResponse | 规则编写陷阱 |
| #76 | @CSS:前缀vs自定义语法 | 规则编写陷阱 |

### 9.3 新增类（因 Stub 降级产生的新陷阱）

| 新陷阱# | 陷阱描述 | 新增原因 | Skill 应对 |
|---------|---------|---------|-----------|
| #80 | webView()降级为HTTP+正则 | JsExtensionsStub 无法执行 JS | 标注：需真机 WebView 的源不可用 |
| #81 | webViewGetSource()降级 | 同上 | 标注：m3u8 提取可能失败 |
| #82 | startBrowser()不可用 | JsExtensionsStub 抛异常 | 标注：CF 盾需用户真机处理 |
| #83 | startBrowserAwait()不可用 | 同上 | 标注：验证码需用户真机处理 |
| #84 | getVerificationCode()不可用 | 同上 | 标注：验证码需用户真机处理 |
| #85 | openVideoPlayer()不可用 | JsExtensionsStub 抛异常 | 标注：视频播放需真机 |
| #86 | CookieStore内存实现 | CookieStoreStub 无持久化 | 标注：Cookie 重启后丢失 |
| #87 | CacheManager内存实现 | CacheManagerStub 无持久化 | 标注：缓存重启后丢失 |
| #88 | 文件操作改为临时目录 | appCtx.externalCache 不可用 | 标注：文件路径与真机不同 |
| #89 | androidId返回固定值 | AppConst.androidId 不可用 | 标注：androidId 不唯一 |
| #90 | getWebViewUA返回固定UA | WebSettings 不可用 | 标注：UA 可能被网站识别 |

### 9.4 映射统计

| 类别 | 数量 | 占比 | Skill 适配动作 |
|------|------|------|-------------|
| **自动修复** | 7 | 9% | 移除陷阱条目，标注"已由源码抽取修复" |
| **保留** | 32 | 41% | 保持不变，继续作为规则编写陷阱 |
| **新增** | 11 | 14% | 新增陷阱条目，标注 Stub 降级限制 |
| **未列出** | 29 | 37% | 需在 Skill 适配阶段逐一核对完整79条 |

> **关键结论**：源码抽取自动修复 7 条陷阱（ZeroPadding/`{{page}}`/相对URL 等历史问题），新增 11 条 Stub 降级陷阱（主要是 WebView/UI 不可用），保留 32 条规则编写陷阱。Skill 适配阶段需移除7条、新增11条、保留32条、核对29条。

## 10. Python 客户端适配差异点清单

> **源码参照**：`.trae/skills/legado-source-creator/scripts/` 目录下 10+ 个 Python 脚本
>
> **适配原则**：不只是改 JAR 路径，要适配新 JAR 的行为差异

### 10.1 差异点清单

| 脚本 | 差异点 | 适配动作 | 源码参照 |
|------|--------|---------|---------|
| `debug-source.py` | JAR 路径变更 + batch 模式 | 改路径+添加`--batch`参数 | 新 JAR RuleEngineServer |
| `test_all_sources.py` | 批处理输出格式 | 解析 batch_progress+batch_complete | 新 JAR batch 命令 |
| `quick-verify.py` | 验证逻辑适配 | 错误信息格式可能变化 | 新 JAR 错误输出 |
| `deep-verify.py` | 深度验证逻辑适配 | 同上 | 同上 |
| `classify-and-fix.py` | 分类修复逻辑 | 新 JAR 行为差异（WebView降级） | JsExtensionsStub |
| `site_type_detector.py` | CookieStore/NetworkUtils 对齐 | CookieStoreStub 内存实现 | CookieStoreStub |
| `obstacle_resolver.py` | 登录/CF/验证码处理 | Stub 无法 startBrowser | JsExtensionsStub |
| `error_translator.py` | 新错误类型翻译 | Stub 降级异常+NoStackTraceException | JsExtensionsStub |
| `auto_fixer.py` | AnalyzeRule 行为适配 | 源码抽取后行为一致 | AnalyzeRule 源码 |
| `degradation_chain.py` | 降级链能力边界 | WebView/UI 不可用的降级路径 | JsExtensionsStub |

### 10.2 关键适配点

1. **batch 模式**：debug-source.py 需添加 `--batch` 参数，组装 batch 命令，解析进度输出
2. **错误信息格式**：新 JAR 使用 NoStackTraceException，error_translator 需翻译新异常类型
3. **CookieStore 行为**：CookieStoreStub 内存实现，重启后丢失，site_type_detector 需适配
4. **WebView 降级**：obstacle_resolver 需检测 WebView 降级场景，引导用户真机处理
5. **文件路径**：文件操作改为临时目录，相关脚本需适配路径差异

## 11. Skill 适配差异点清单

> **源码参照**：`.trae/skills/legado-source-creator/` 目录下所有文档
>
> **适配原则**：JAR 和 Python 客户端改造完成后，Skill 本身需全面适配新架构

### 11.1 差异点清单

| 文档/目录 | 差异点 | 适配动作 | 源码参照 |
|----------|--------|---------|---------|
| `SKILL.md` | JAR 路径+架构描述+5阶段工作流 | 改路径+改描述+适配Phase 3 | 新 JAR 架构 |
| `AI_README.md` | JAR 路径+验证脚本清单 | 改路径+改清单 | 同上 |
| `references/_INDEX.md` | JAR 路径+架构描述 | 改路径+改描述 | 同上 |
| `references/rule-grammar/` | 规则语法与 AnalyzeRule 行为 | 确认行为一致 | AnalyzeRule 源码 |
| `references/url-template/` | URL 模板与 AnalyzeUrl 行为 | 确认行为一致 | AnalyzeUrl 源码 |
| `references/entity-fields/` | 字段定义与 BookSource/RssSource | 确认字段一致 | BookSource/RssSource 源码 |
| `references/example-sources/` | 示例源能在新 JAR 通过 | 重新验证 | 新 JAR |
| `troubleshooting/` 79条 | 陷阱映射（第9节） | 移除7+新增11+保留32+核对29 | 第9节映射表 |
| `js-extensions/` 11个文档 | Stub 实现状态标注 | 每个方法标注：完整/降级/不可用 | 第6节方法清单 |
| `js-patterns/` 11个文档 | Rhino 执行一致 | 确认行为一致 | Rhino 源码 |
| `references/site-features/` | 高频问题模式 | 适配 Stub 降级场景 | JsExtensionsStub |
| `references/special-scenarios/` | 登录/验证码/加密/视频 | 标注 Stub 限制 | JsExtensionsStub |
| `scripts/verify-*.py` 7个 | JAR 路径+行为适配 | 改路径+适配行为 | 新 JAR |
| basic-memory 经验 | 旧经验标注过时+新经验写入 | 标注+写入 | 新架构经验 |

### 11.2 关键适配点

1. **SKILL.md 架构描述**：从「从零仿真」改为「从 Legado 源码抽取」
2. **79条陷阱**：按第9节映射表移除/新增/保留
3. **js-extensions/ 标注**：每个方法标注实现状态（完整/降级/不可用）
4. **经验教训**：basic-memory 旧经验标注"已过时（旧仿真端）"，新经验写入"源码抽取架构"
5. **验证脚本**：7个 verify-*.py 脚本改 JAR 路径+适配行为

## 12. 回滚策略与抽取后验证策略

### 12.1 回滚策略

| 场景 | 回滚动作 | 回滚条件 |
|------|---------|---------|
| 阶段一失败 | 删除 `.trae/skills/legado-source-creator/tools/legado-jvm/`，用旧 MVP1-4 | A/B/C 级编译失败 |
| 阶段二失败 | 保留阶段一，回退 D 级到旧仿真 | JsExtensions 接口拆分失败 |
| 阶段三失败 | 保留阶段一二，回退到多 JAR | fat JAR 打包失败 |
| 阶段四失败 | 保留阶段一二三，回退 Python 脚本 | Python 适配失败 |
| 整体失败 | 恢复旧 MVP1-4 + 旧 Python 脚本 | git revert |

**回滚保障**：
- 旧 MVP1-4 目录标记 deprecated 但不删除
- 旧 Python 脚本通过 git 版本控制可恢复
- 每个阶段完成后 git commit，便于回滚

### 12.2 抽取后验证策略

| 验证类型 | 验证方法 | 通过标准 |
|---------|---------|---------|
| **编译验证** | `gradlew :legado-jvm:compileKotlin` | 成功 |
| **单元测试** | 每个抽取类的关键 public 方法 | 关键方法 100% 覆盖（132 方法中关键方法约 40 个） |
| **行为对比** | 同输入→对比输出（源码 vs 抽取后） | 100% 一致 |
| **集成测试** | 7 RSS + 1 书源真实源测试 | 通过率 >85% |
| **大规模测试** | 300 个抽样源 | 书源>70%/订阅源>75% |
| **性能测试** | 批处理 7 源耗时 | <15 秒 |
| **协议兼容** | debug-source.py 调用 | 无兼容性错误 |

### 12.3 行为对比测试方法

```
1. 从 Legado 源码提取方法的测试用例
2. 同输入分别用旧仿真端和新 JAR 执行
3. 对比输出结果
4. 如果不一致，分析差异原因
5. 修复后重新对比
```

**关键对比方法**：
- `AnalyzeRule.getString()`：同 HTML+同规则 → 对比输出
- `AnalyzeRule.getStringList()`：同 HTML+同规则 → 对比输出
- `AnalyzeUrl` URL 构造：同 sourceJson+同 key+同 page → 对比 URL
- `JsExtensionsStub.aesDecode()`：同密文+同 key+同 iv → 对比明文

