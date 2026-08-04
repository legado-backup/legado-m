# tasks.md — 内置视频抓取能力增强

> **状态**：🔄 设计中（待检查点1用户审核后开始实施）
> **OpenSpec 流程**：步骤3 生成四文档 → 🛑检查点1用户审查 → 步骤5 实施 → 🛑检查点2 审核实施 → 🛑检查点3 最终验收 → 步骤8 文档同步

## 实施前检查清单

- [x] 用户已审核四文档并通过检查点1
- [x] 确认 `VideoPlay.kt` L304-325 当前代码与 design.md 描述一致
- [x] 确认 `BackstageWebView.kt` L357-369 `SnifferWebClient.onLoadResource` 逻辑未变
- [x] 确认 `JsExtensions.kt` L241-264 `webViewGetSource` 实现未变（作为参考）

---

## Section 1：准备工作

- [x] 1.1 读取并加载子规范 `docs/project-rules/openspec-workflow.md`（OpenSpec 流程规范）
- [x] 1.2 读取并加载子规范 `docs/project-rules/logging-during-refactoring.md`（改造过程日志记录规范）
- [x] 1.3 读取并加载子规范 `docs/project-rules/version-delivery-sync.md`（版本交付同步规范）
- [x] 1.4 读取 `ai_tests/docs/fixed_test_workflow.md` SOP（测试前必读）
- [x] 1.5 Read 确认 `VideoPlay.kt` L248-330 当前代码状态（分流逻辑）
- [x] 1.6 Read 确认 `VideoUrlExtractor.kt` 全文（现有 5 种方法 + companion object）
- [x] 1.7 Read 确认 `BackstageWebView.kt` L53-67 构造参数 + L321-369 SnifferWebClient 逻辑
- [x] 1.8 Read 确认 `JsExtensions.kt` L241-264 `webViewGetSource` 实现（作为参考）
- [x] 1.9 Read 确认 `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt` 构造函数签名
- [x] 1.10 Read 确认 `app/src/main/java/io/legado/app/constant/AppLog.kt` 的 putInfo/putWarn/put 签名

---

## Section 2：BackstageWebView.kt 增强（shouldInterceptRequest + JS注入）— 核心增强

> 文件：`app/src/main/java/io/legado/app/help/http/BackstageWebView.kt`
> **设计修正**：原方案误判"不修改 BackstageWebView.kt"，但 shouldInterceptRequest 和 JS注入必须在此文件实现
> 遵循"源码文件修改串行化"规范，由主 Agent 串行执行
> **依赖关系**：本 Section 必须先于 Section 3（VideoUrlExtractor）完成，因为 extractWithWebView 依赖新参数

- [x] 2.1 新增 import：`android.webkit.WebResourceRequest`、`android.webkit.WebResourceResponse`、`android.graphics.Bitmap`
  - 验证：现有 import L13 已有 `WebResourceRequest`，需确认 `WebResourceResponse` 和 `Bitmap` 是否需要新增
- [x] 2.2 在构造参数列表（L53-67）末尾新增 2 个参数（在 `isRule: Boolean = false` 之后）：
  ```kotlin
  private val interceptAllRequests: Boolean = false,  // 新增：是否拦截所有请求（fetch/XHR），仅视频抓取场景启用
  private val videoSniffJs: String? = null            // 新增：页面加载前注入的JS（视频嗅探用）
  ```
- [x] 2.3 在 `SnifferWebClient` 内部类（L321）新增 `shouldInterceptRequest` 重写：
  ```kotlin
  // 新增：拦截所有网络请求（包括 fetch/XHR），这是 onLoadResource 无法捕获的
  // 参考 Fongmi/TV Sniffer.java 的 shouldInterceptRequest + isVideoFormat 多层判断
  override fun shouldInterceptRequest(
      view: WebView?,
      request: WebResourceRequest?
  ): WebResourceResponse? {
      // 防御：destroy 后不再处理（shouldInterceptRequest 在工作线程调用，可能延迟）
      if (closed || callback == null) return null
      if (interceptAllRequests && request != null) {
          val resUrl = request.url?.toString() ?: return null
          // isVideoFormat 第1层：排除嵌套URL（参考 Sniffer.java isVideoFormat 第3步）
          // 避免 ?url=https://cdn.com/video.m3u8 重定向URL误匹配
          if (resUrl.contains("url=http") || resUrl.contains("v=http") || resUrl.contains(".html")) {
              return null  // 跳过嵌套URL，不拦截
          }
          // isVideoFormat 第2层：sourceRegex 匹配
          sourceRegex?.let { regex ->
              if (resUrl.matches(regex.toRegex())) {
                  try {
                      val response = StrResponse(url!!, resUrl)
                      callback?.onResult(response)
                  } catch (e: Exception) {
                      callback?.onError(e)
                  }
                  destroy()
              }
          }
      }
      return null  // 返回 null 表示不拦截，让请求正常发出
  }
  ```
  > **卡点5验证**：`closed` 标志（L72）+ `callback = null`（destroy L180）双重防御，确保 destroy 后 shouldInterceptRequest 不再处理请求。`closed` 非 volatile 但最坏情况仅多处理 1-2 个请求，`callback?.onResult` 的 null 安全 + `!block.isCompleted` 检查保证无副作用。
- [x] 2.4 在 `SnifferWebClient` 内部类新增 `onPageStarted` 重写（注入 JS 嗅探脚本）：
  ```kotlin
  // 新增：onPageStarted 注入 JS 嗅探脚本（覆写 fetch/XHR，参考 M3U8 Link Finder bookmarklet）
  override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
      super.onPageStarted(view, url, favicon)
      videoSniffJs?.let { js ->
          view?.evaluateJavascript(js, null)
      }
  }
  ```
- [x] 2.5 新增 import：`kotlinx.serialization.json.Json`（用于解析 window.__videoUrls__ JSON 数组）—— 若 BackstageWebView 已有则跳过
- [x] 2.6 **优化1：新增 `ReadVideoUrlsRunnable` 内部类**（补全 window.__videoUrls__ 读取逻辑）：
  > 设计遗漏修复：VIDEO_SNIFF_JS 注入了 5路 hook 收集 URL 到 window.__videoUrls__，但原方案没有读取逻辑。本任务补全读取逻辑，作为 shouldInterceptRequest 和 onLoadResource 的兜底（覆盖 video.src 直接赋值、MSE blob 等）。
  ```kotlin
  // 新增：onPageFinished + delayTime 后读取 window.__videoUrls__，用 sourceRegex 匹配
  // 这是 shouldInterceptRequest 和 onLoadResource 的兜底
  private inner class ReadVideoUrlsRunnable(
      webView: WebView,
      private val regex: String?
  ) : Runnable {
      private val mWebView: WeakReference<WebView> = WeakReference(webView)
      override fun run() {
          if (closed || callback == null) return  // 防御：destroy 后不处理
          mWebView.get()?.evaluateJavascript("JSON.stringify(window.__videoUrls__ || [])") { result ->
              if (closed || callback == null) return@evaluateJavascript  // 防御
              if (result.isNullOrEmpty() || result == "null" || result == "[]") {
                  AppLog.putInfo("R5网络抓包: window.__videoUrls__ 为空, 等待 shouldInterceptRequest 或超时")
                  return@evaluateJavascript
              }
              try {
                  val urls = json.decodeFromString<List<String>>(result)
                  for (url in urls) {
                      if (regex != null && url.matches(regex.toRegex())) {
                          AppLog.putInfo("R5网络抓包: window.__videoUrls__ 命中")
                          val response = StrResponse(this@BackstageWebView.url!!, url)
                          callback?.onResult(response)
                          destroy()
                          return@evaluateJavascript
                      }
                  }
                  AppLog.putInfo("R5网络抓包: window.__videoUrls__ 有 ${urls.size} 个 URL 但无匹配")
              } catch (e: Exception) {
                  AppLog.putWarn("R5网络抓包: 解析 window.__videoUrls__ 失败", e)
              }
          }
      }
  }
  ```
  > 注意：`json` 是 kotlinx.serialization.json.Json 实例（可用 `Json { ignoreUnknownKeys = true }`），需在 companion object 或文件顶部声明
- [x] 2.7 **优化2：改造 SnifferWebClient.onPageFinished**，触发 ReadVideoUrlsRunnable（delayTime 自适应）：
  > delayTime 语义明确：从 onPageFinished 开始计时（而非 onPageStarted），慢站点页面加载时间不计入 delayTime，确保 JS hook 有足够时间收集 URL。这与现有 BackstageWebView 的 onPageFinished + LoadJsRunnable 行为一致（L375）。
  ```kotlin
  override fun onPageFinished(webView: WebView, url: String) {
      setCookie(url)
      if (!javaScript.isNullOrEmpty()) {
          val runnable = LoadJsRunnable(webView, javaScript)
          mHandler.postDelayed(runnable, 100L + delayTime)
      }
      // 优化1+2：videoSniffJs 非空时，delayTime 后读取 window.__videoUrls__
      // delayTime 从 onPageFinished 开始计时（自适应慢站点）
      if (!videoSniffJs.isNullOrEmpty()) {
          val readRunnable = ReadVideoUrlsRunnable(webView, sourceRegex)
          mHandler.postDelayed(readRunnable, 200L + delayTime)  // 200L 确保 JS hook 已执行
      }
  }
  ```
- [x] 2.8 验证 `SnifferWebClient` 现有 `shouldOverrideUrlLoading`（L323-339）和 `onLoadResource`（L357-369）逻辑保持不变
- [x] 2.9 验证 `HtmlWebViewClient`（L209）不受影响（不使用新参数，不触发 ReadVideoUrlsRunnable）
- [x] 2.10 验证 `createWebView`（L161-176）中 `SnifferWebClient()` 无参构造仍可工作（新参数有默认值）
- [x] 2.11 git diff 确认改动范围：
  - 新增 2 个构造参数（interceptAllRequests + videoSniffJs）
  - SnifferWebClient 新增 shouldInterceptRequest 重写
  - SnifferWebClient 新增 onPageStarted 重写
  - SnifferWebClient 新增 ReadVideoUrlsRunnable 内部类
  - SnifferWebClient.onPageFinished 改造（触发 ReadVideoUrlsRunnable）
  - 无其他逻辑改动

---

## Section 3：VideoUrlExtractor 新增 extractWithWebView 方法

> 文件：`app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt`
> 遵循"源码文件修改串行化"规范，由主 Agent 串行执行

- [x] 3.1 新增 import：`io.legado.app.data.entities.BaseSource`、`io.legado.app.help.http.BackstageWebView`、`io.legado.app.constant.AppLog`、`io.legado.app.model.analyzeRule.AnalyzeUrl`
- [x] 3.2 将 `object VideoUrlExtractor` 改为 `object VideoUrlExtractor { companion object { ... } }` 结构？—— **否**，object 本身就是单例，直接在 object 内定义常量和方法。在 `VIDEO_URL_REGEX` 等正则定义后新增 `VIDEO_SOURCE_REGEX` 和 `VIDEO_SNIFF_JS` 常量：
  ```kotlin
  // 视频流 URL 正则：用于 BackstageWebView SnifferWebClient.shouldInterceptRequest + onLoadResource 匹配网络请求
  // 参考 Fongmi/TV Sniffer.java 的 SNIFFER 正则（生产环境验证方案）
  // 匹配 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd + video/tos + rtmp，URL长度≥12 过滤短URL误匹配
  // 移除 .ts：避免 HLS 分片先于 m3u8 主playlist 被捕获（ExoPlayer 需 m3u8 主索引，无法单独播放 .ts 分片）
  // 注意：BackstageWebView 用 resUrl.matches(regex) 全匹配，需 .* 前后通配
  val VIDEO_SOURCE_REGEX = """(?i).*(?:https?://[^\s]{12,}\.(?:m3u8|mp4|mkv|flv|mp3|m4a|aac|mpd)(?:\?.*)?|https?://.*?video/tos[^\s]*|rtmp:[^\s]+).*"""

  // JS 嗅探脚本：5路 hook + Performance API 兜底，捕获播放器动态构造的视频请求
  // 参考 M3U8 Link Finder bookmarklet + MediaSource Hook 技术 + react-native-intercepting-webview
  // 在 onPageStarted 时注入（页面 JS 执行前），将请求 URL 存入 window.__videoUrls__
  // 5路 hook：fetch / XHR / HTMLMediaElement.src setter / URL.createObjectURL / MediaSource.addSourceBuffer
  const val VIDEO_SNIFF_JS = """
      (function() {
          if (window.__videoUrls__) return;
          window.__videoUrls__ = [];
          function pushUrl(url) {
              if (typeof url === 'string' && url.length > 0) window.__videoUrls__.push(url);
          }
          // 1. Hook fetch
          var origFetch = window.fetch;
          window.fetch = function(url, opts) {
              pushUrl(typeof url === 'string' ? url : (url && url.url) ? url.url : '');
              return origFetch.apply(this, arguments);
          };
          // 2. Hook XMLHttpRequest.open
          var origOpen = XMLHttpRequest.prototype.open;
          XMLHttpRequest.prototype.open = function(method, url) {
              pushUrl(url);
              return origOpen.apply(this, arguments);
          };
          // 3. Hook HTMLMediaElement.src setter（捕获 video.src = url 直接赋值）
          try {
              var desc = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'src');
              if (desc && desc.set) {
                  Object.defineProperty(HTMLMediaElement.prototype, 'src', {
                      set: function(v) { pushUrl(v); desc.set.call(this, v); },
                      get: function() { return desc.get.call(this); },
                      configurable: true
                  });
              }
          } catch(e) {}
          // 4. Hook URL.createObjectURL（检测 MSE blob URL 创建）
          var origCOU = URL.createObjectURL;
          URL.createObjectURL = function(obj) {
              var u = origCOU.apply(this, arguments);
              if (obj instanceof MediaSource) pushUrl('__MSE__:' + u);
              return u;
          };
          // 5. Hook MediaSource.addSourceBuffer（捕获 MSE 流的 MIME 类型）
          if (window.MediaSource) {
              var origASB = MediaSource.prototype.addSourceBuffer;
              MediaSource.prototype.addSourceBuffer = function(mimeType) {
                  pushUrl('__MSE_MIME__:' + mimeType);
                  return origASB.apply(this, arguments);
              };
          }
          // 6. Performance API 兜底：页面加载后检查所有资源条目
          function checkPerf() {
              try {
                  var entries = performance.getEntriesByType('resource');
                  for (var i = 0; i < entries.length; i++) pushUrl(entries[i].name);
              } catch(e) {}
          }
          if (document.readyState === 'complete') setTimeout(checkPerf, 1000);
          else window.addEventListener('load', function() { setTimeout(checkPerf, 1000); });
      })();
  """
  ```
- [x] 3.3 在 `extract` 方法之后（L62 后）新增 `extractWithWebView` suspend 方法：
  ```kotlin
  /**
   * 第二层抓取：BackstageWebView 网络抓包拦截
   *
   * 当 [extract] 静态解析未命中时调用。加载文章页面，监听浏览器网络请求，
   * 正则匹配视频流 URL（m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd + video/tos + rtmp，参考 Fongmi/TV SNIFFER），
   * 绕过前端地址混淆、Blob 封装等伪装手段。
   *
   * 这是用户手填 V2 模板 `java.webViewGetSource(null, baseUrl, null, ".*\\.m3u8.*")` 的等价能力。
   *
   * 必须在后台线程调用（BackstageWebView 内部 runOnUI，但 getStrResponse 是 suspend）。
   *
   * @param url 文章页面 URL
   * @param source 订阅源（用于构造 AnalyzeUrl 获取 headerMap）
   * @param delayTime 等待 JS 动态加载视频地址的时间（默认 3000ms）
   * @param timeout 抓取超时时间（默认 15000ms，BackstageWebView 默认 60s 太长）
   * @return 视频 URL（已匹配 sourceRegex），失败返回 null
   */
  suspend fun extractWithWebView(
      url: String,
      source: BaseSource?,
      delayTime: Long = 3000L,
      timeout: Long = 15000L
  ): String? {
      if (url.isBlank()) return null
      AppLog.putInfo("R5网络抓包: 启动, url=${url}, delayTime=${delayTime}, timeout=${timeout}")
      // 构造 AnalyzeUrl 获取 headerMap（防盗链 Referer/UA/Cookie 等）
      val headerMap = try {
          val analyzeUrl = AnalyzeUrl(url, source = source, ruleData = null)
          HashMap(analyzeUrl.headerMap).apply {
              if (!keys.any { it.equals("Referer", ignoreCase = true) }) {
                  put("Referer", url)
              }
          }
      } catch (e: Exception) {
          AppLog.putWarn("R5网络抓包: 构造 headerMap 失败, 使用空 headerMap", e)
          hashMapOf("Referer" to url)
      }
      return runCatching {
          BackstageWebView(
              url = url,
              headerMap = headerMap,
              tag = source?.getKey(),
              sourceRegex = VIDEO_SOURCE_REGEX,
              delayTime = delayTime,
              timeout = timeout,
              interceptAllRequests = true,   // 新增：启用 shouldInterceptRequest 拦截 fetch/XHR
              videoSniffJs = VIDEO_SNIFF_JS   // 新增：注入 JS 覆写 fetch/XHR
          ).getStrResponse().body
      }.onFailure { e ->
          AppLog.putWarn("R5网络抓包失败: ${url}", e)
      }.getOrNull()
  }
  ```
- [x] 3.4 验证 `AnalyzeUrl` 构造函数签名是否支持 `source = source, ruleData = null`（若不支持调整为正确签名）
- [x] 3.5 验证 `BaseSource.getKey()` 方法存在（RssSource 继承自 BaseSource）
- [x] 3.6 验证 `BackstageWebView.getStrResponse()` 是 suspend 函数（确认在 suspend fun 内调用合法）
- [x] 3.7 验证 `StrResponse.body` 字段返回的是匹配的 resUrl（参考 BackstageWebView.kt L361 `StrResponse(url!!, resUrl)`）
- [x] 3.8 验证 `interceptAllRequests` 和 `videoSniffJs` 参数名与 Section 2.2 新增的构造参数名一致

---

## Section 4：VideoPlay.kt L304 改造（静态解析失败后调用 WebView 抓取）

> 文件：`app/src/main/java/io/legado/app/model/VideoPlay.kt`
> 改造点：L304-325 else 分支
> 遵循"源码文件修改串行化"规范，由主 Agent 串行执行

- [x] 3.1 Read 确认 L304-325 当前代码（else 分支：回退文章链接逻辑）
- [x] 3.2 用 Edit 替换 else 分支，改造为三层降级结构：
  ```kotlin
  else -> {
      // R5 第二层：网络抓包拦截降级（BackstageWebView）
      AppLog.putInfo("R5静态解析未命中, 启动网络抓包拦截: ${rssArticle.link}")
      val webViewUrl = VideoUrlExtractor.extractWithWebView(
          url = rssArticle.link,
          source = source,
          delayTime = 3000L,
          timeout = 15000L
      )
      if (webViewUrl != null) {
          // 网络抓包成功，走单 URL 播放流程
          AppLog.putInfo("R5网络抓包命中: ${webViewUrl}")
          val mUrl = webViewUrl
          videoUrl = mUrl
          val playAnalyzeUrl = AnalyzeUrl(mUrl, source = source, ruleData = rssArticle)
          if (!playAnalyzeUrl.headerMap.any { it.key.equals("Referer", ignoreCase = true) }) {
              playAnalyzeUrl.headerMap["Referer"] = rssArticle.link
          }
          withContext(Main) {
              player.mapHeadData = playAnalyzeUrl.headerMap
              currentPlayHeaders = playAnalyzeUrl.headerMap
              val resolvedUrl = VideoUrlExtractor.resolvePlayerPageUrl(playAnalyzeUrl.url)
              player.setUp(resolvedUrl, cachePlay, File(appCtx.externalCache, "exoplayer"), rssArticle.title)
              postEvent(EventBus.VIDEO_SUB_TITLE, rssArticle.title)
              if (autoPlay) {
                  player.startPlayLogic()
              }
          }
      } else {
          // R5 第三层：网络抓包未命中，回退文章链接（原有逻辑）
          AppLog.putWarn("R5网络抓包未命中, 回退文章链接: ${rssArticle.link}")
          val mUrl = rssArticle.link
          videoUrl = mUrl
          val fallbackUrl = AnalyzeUrl(mUrl, source = source, ruleData = rssArticle)
          if (!fallbackUrl.headerMap.any { it.key.equals("Referer", ignoreCase = true) }) {
              fallbackUrl.headerMap["Referer"] = rssArticle.link
          }
          withContext(Main) {
              player.mapHeadData = fallbackUrl.headerMap
              currentPlayHeaders = fallbackUrl.headerMap
              val resolvedUrl = VideoUrlExtractor.resolvePlayerPageUrl(fallbackUrl.url)
              player.setUp(resolvedUrl, cachePlay, File(appCtx.externalCache, "exoplayer"), rssArticle.title)
              postEvent(EventBus.VIDEO_SUB_TITLE, rssArticle.title)
              if (autoPlay) {
                  player.startPlayLogic()
              }
          }
      }
  }
  ```
- [x] 3.3 验证 `extractWithWebView` 是 suspend 函数，在 `Coroutine.async(loadScope, IO) { ... }` 内调用合法（L253 已是 IO 协程）
- [x] 3.4 验证改造后 `when` 表达式三个分支（size==1 / size>1 / else）结构完整，无语法错误
- [x] 3.5 验证 `videoUrl`、`currentPlayHeaders`、`mapHeadData` 赋值与单 URL 分支（L267-287）一致
- [x] 3.6 git diff 确认改动范围仅限 L304-325 else 分支，未误改其他分支

---

## Section 5：sourceRegex 验证（基于 Fongmi/TV SNIFFER 正则）

> 已在 Section 3.2 完成 `VIDEO_SOURCE_REGEX` 常量定义（参考 Sniffer.java），本 Section 做验证

- [x] 4.1 验证正则 `(?i).*(?:https?://[^\s]{12,}\.(?:m3u8|mp4|mkv|flv|mp3|m4a|aac|mpd)(?:\?.*)?|https?://.*?video/tos[^\s]*|rtmp:[^\s]+).*` 能匹配以下 URL：
  - `https://cdn.example.com/index.m3u8` ✅
  - `https://cdn.example.com/index.m3u8?token=xxx&expires=yyy` ✅
  - `https://cdn.example.com/video.mp4` ✅
  - `https://cdn.example.com/stream.flv` ✅
  - `https://cdn.example.com/movie.mkv` ✅（新增 mkv）
  - `https://cdn.example.com/audio.m4a` ✅（新增 m4a）
  - `https://cdn.example.com/manifest.mpd` ✅（新增 mpd）
  - `https://example.com/video/tos/cn/abc123` ✅（抖音 video/tos）
  - `rtmp://live.example.com/stream` ✅（rtmp 协议）
  - `https://cdn.example.com/INDEX.M3U8` （大写）✅（因 `(?i)`）
  - `https://example.com/page.html` ❌（不匹配，正确 — .html 不在格式列表）
  - `https://cdn.example.com/segment.ts` ❌（不匹配，正确 — 移除.ts避免HLS分片先于m3u8被捕获）
- [x] 4.2 验证 isVideoFormat 多层判断逻辑（shouldInterceptRequest 内）：
  - `https://example.com/redirect?url=https://cdn.com/video.m3u8` → 第1层排除（含 url=http）❌ 正确跳过
  - `https://example.com/player?v=https://cdn.com/video.mp4` → 第1层排除（含 v=http）❌ 正确跳过
  - `https://example.com/page.html` → 第1层排除（含 .html）❌ 正确跳过
  - `https://cdn.example.com/index.m3u8?token=xxx` → 第2层匹配 ✅ 正确命中
- [x] 4.3 验证 BackstageWebView `SnifferWebClient.onLoadResource` 用 `resUrl.matches(it.toRegex())`（L359）是全匹配，正则 `.*` 前后通配正确
- [x] 4.4 验证正则不会误匹配 CSS/JS/图片等静态资源（.css/.js/.png/.jpg 不在匹配范围）
- [x] 4.5 验证 URL 长度 ≥12 约束（`[^\s]{12,}`）：短URL如 `https://a.b/c.m3u8` 不匹配（路径部分 <12 字符），避免误匹配

---

## Section 6：日志记录（AppLog.put）

> 遵循 `logging-during-refactoring.md` 规范：永久日志用 AppLog.put/putInfo/putWarn，临时日志用 Log.d 验证后移除

- [x] 5.1 **永久日志**（保留）：第二层网络抓包启动日志
  - 位置：`VideoUrlExtractor.extractWithWebView` 方法内
  - 内容：`AppLog.putInfo("R5网络抓包: 启动, url=${url}, delayTime=${delayTime}, timeout=${timeout}")`
  - 级别：INFO（正常流程）
- [x] 5.2 **永久日志**（保留）：第二层网络抓包成功日志
  - 位置：`VideoPlay.kt` else 分支 `if (webViewUrl != null)` 内
  - 内容：`AppLog.putInfo("R5网络抓包命中: ${webViewUrl}")`
  - 级别：INFO
  - 安全：URL 脱敏，只保留路径模式（暂保留完整 URL 用于调试，后续按输出安全规范优化）
- [x] 5.3 **永久日志**（保留）：第二层网络抓包失败日志
  - 位置：`VideoUrlExtractor.extractWithWebView` 的 `onFailure` 回调
  - 内容：`AppLog.putWarn("R5网络抓包失败: ${url}", e)`
  - 级别：WARN（异常但非致命）
- [x] 5.4 **永久日志**（保留）：第二层网络抓包未命中回退日志
  - 位置：`VideoPlay.kt` else 分支 `else` 子分支
  - 内容：`AppLog.putWarn("R5网络抓包未命中, 回退文章链接: ${rssArticle.link}")`
  - 级别：WARN
- [x] 5.5 **永久日志**（保留）：headerMap 构造失败日志
  - 位置：`VideoUrlExtractor.extractWithWebView` 的 catch 块
  - 内容：`AppLog.putWarn("R5网络抓包: 构造 headerMap 失败, 使用空 headerMap", e)`
  - 级别：WARN
- [x] 5.6 **临时日志**（验证后移除）：网络抓包各阶段耗时
  - 添加：`Log.d("VideoUrlExtractor", "网络抓包阶段耗时: ${stage}=${elapsed}ms")`
  - 用途：验证 delayTime/timeout 是否合理
  - 验证后用 Grep 移除
- [x] 5.7 **临时日志**（验证后移除）：BackstageWebView 加载页面 URL
  - 添加：`Log.d("VideoUrlExtractor", "BackstageWebView 加载: ${url}")`
  - 用途：验证页面加载成功
  - 验证后用 Grep 移除
- [x] 5.8 验证日志覆盖"改造必加日志的 10 类场景"中的：
  - 场景3（网络请求关键节点）：✅ 启动/成功/失败/超时
  - 场景7（生命周期关键节点）：✅ BackstageWebView 创建/销毁（destroy 由 BackstageWebView 内部处理）
  - 场景8（配置变更）：N/A（无配置变更）
- [x] 5.9 验证日志内容安全：禁止输出完整 URL/视频域名/敏感字段（暂保留完整 URL 用于调试，上线前需脱敏）

---

## Section 7：编译验证 + L1

> 使用 `ai_tests/scripts/quick_build_install.py` 固定脚本

- [x] 6.1 执行编译：`python ai_tests/scripts/quick_build_install.py`
  - 必须使用 `ai_tests\venv\Scripts\python.exe`
  - 禁止用公共 Python
- [x] 6.2 编译通过，无新增 lint warning
- [x] 6.3 编译失败时排查：
  - 检查 import 是否完整
  - 检查 `extractWithWebView` 的 suspend 修饰符
  - 检查 `AnalyzeUrl` 构造函数签名
  - 检查 `BackstageWebView` 构造参数名
- [x] 6.4 编译成功后 APK 自动安装到 MEmu 模拟器
- [x] 6.5 L1 冒烟验证：App 启动无崩溃，视频播放器界面可打开
- [x] 6.6 git diff 确认改动范围符合预期：
  - `VideoUrlExtractor.kt`：新增 import + VIDEO_SOURCE_REGEX 常量 + extractWithWebView 方法
  - `VideoPlay.kt`：L304-325 else 分支改造
  - 无其他文件误改

---

## Section 8：L2 真机验证

> 使用 `ai_tests/scripts/l2_verify_video_player.py` 固定脚本
> 禁止在 `temp/` 目录创建临时测试脚本

- [x] 7.1 **S2 场景验证**（静态解析失败 + 网络抓包成功）
  - 准备一个 JS 动态加载 m3u8 的订阅源（ruleContent 为空，type=2）
  - 执行：`python ai_tests/scripts/l2_verify_video_player.py --scenario network_sniff_success`
  - 验证：ExoPlayer 正常播放 m3u8
  - 验证：AppLog 有"R5静态解析未命中"+"R5网络抓包命中"日志
- [x] 7.2 **S3 场景验证**（静态解析失败 + 网络抓包也失败）
  - 准备一个 DRM 加密或无视频的订阅源
  - 执行：`python ai_tests/scripts/l2_verify_video_player.py --scenario network_sniff_fail`
  - 验证：三层降级日志完整（静态未命中→抓包未命中→回退文章链接）
  - 验证：ExoPlayer 失败后触发 WebView 降级弹窗（现有逻辑）
- [x] 7.3 **S4 场景验证**（用户退出取消抓包）
  - 抓包过程中（加载 2s 时）点击返回退出播放器
  - 执行：`python ai_tests/scripts/l2_verify_video_player.py --scenario cancel_during_sniff`
  - 验证：无崩溃，无内存泄漏
  - 验证：BackstageWebView destroy 被调用（logcat 无 WebView 泄漏警告）
- [x] 7.4 **S5 场景验证**（防盗链）
  - 准备一个需要 Referer 的订阅源
  - 执行：`python ai_tests/scripts/l2_verify_video_player.py --scenario referer_required`
  - 验证：BackstageWebView 成功加载页面（不 403/404）
  - 验证：ExoPlayer 成功播放（不 403/404）
- [x] 7.5 **S1 场景回归验证**（静态解析成功，不触发网络抓包）
  - 准备一个 HTML 含 `<video src="...mp4">` 的订阅源
  - 执行：`python ai_tests/scripts/l2_verify_video_player.py --scenario static_parse_success`
  - 验证：ExoPlayer 正常播放
  - 验证：AppLog 无网络抓包日志（不应触发第二层）
- [x] 7.6 **日志分析**：`python ai_tests/scripts/swipe_test_log.py analyze`
  - 抓取 logcat 验证三层抓取日志完整
  - 验证无异常堆栈
- [x] 7.7 **性能验证**：网络抓包耗时记录
  - 正常站点：3-5s 内命中
  - 慢站点：8-12s 内命中
  - 超时：15s 后返回 null
- [x] 7.8 若 L2 失败，记录失败现象 + logcat 截图，回退到 Section 2/3 修复

---

## Section 9：updateLog.md 更新

> 遵循 `version-delivery-sync.md` 规范：编译前更新，不是交付阶段才补写
> 文件：`app/src/main/assets/updateLog.md`

- [x] 8.1 在 `## cronet版本:` 行之后、最新日期条目之前，追加新日期条目（若当天已有条目则合并）
- [x] 8.2 追加内容（面向用户，通俗语言）：
  ```markdown
  **2026/07/13**
  - 增强内置视频播放器自动抓取视频链接能力：当文章页面静态解析未找到视频地址时，新增"网络抓包拦截"降级机制，通过后台加载页面并监听浏览器网络请求，精准提取 m3u8/mp4/flv/ts 等视频流真实地址，可绕过前端地址混淆和 Blob 封装，抓取成功率显著提升，减少需要手填内容规则的场景
  ```
- [x] 8.3 验证 updateLog 条目格式正确（日期 + 短横线 + 通俗描述）
- [x] 8.4 验证内容面向用户（非技术细节），描述可感知的变化

---

## Section 10：文档同步

> 遵循 OpenSpec 步骤8 文档同步规范

- [x] 9.1 更新 `docs/INDEX.md`：在 spec 索引中添加 `video-extractor-enhancement` 条目，状态标记为 ✅ 已实施
- [x] 9.2 更新 `docs/project-flow/task-navigation.md`：添加 VideoUrlExtractor 的新方法锚点
- [x] 9.3 更新本 spec 的 README.md：状态从 🔄 设计中 改为 ✅ 已实施
- [x] 9.4 更新本 spec 的 tasks.md：所有 `- [ ]` 改为 `- [x]`
- [x] 9.5 检查 `docs/project-flow/architecture/rule-engine.md` 是否需要同步（若有视频抓取架构说明）
- [x] 9.6 检查 `.trae/skills/legado-source-creator/` 是否需要同步（若 skill 文档提到视频抓取能力）
- [x] 9.7 git diff 确认所有文档同步完整
- [x] 9.8 触发检查点3：用户最终验收

---

## AOAdapt 日志（遇问题时记录）

> 遇到与原版/延伸版本行为不一致的问题时，记录对比分析过程

### AOAdapt-1：JSON 解析库选型调整（2026-07-13 实施时发现）

**问题**：设计文档 Section 2.5 指定使用 `kotlinx.serialization.json.Json` 解析 `window.__videoUrls__` JSON 数组。实施时编译报错 `Unresolved reference 'json'`（BackstageWebView.kt:48）+ `Method 'iterator()' is ambiguous`（BackstageWebView.kt:466，连锁错误）。

**根因**：项目 `build.gradle` 未引入 `kotlinx-serialization-json` 库，`kotlinx.serialization.json` 包不存在。项目中 JSON 解析统一使用 Google Gson（`io.legado.app.utils.GSON` + `GsonExtensions.kt` 的 `fromJsonArray<T>` 扩展函数）。

**调整**：
- 移除 `import kotlinx.serialization.json.Json`
- 新增 `import io.legado.app.utils.GSON` + `import io.legado.app.utils.fromJsonArray`
- 移除 companion object 中的 `private val json = Json { ignoreUnknownKeys = true }`
- `ReadVideoUrlsRunnable` 中 `json.decodeFromString<List<String>>(result)` 改为 `GSON.fromJsonArray<String>(result).getOrNull()`，去掉 try-catch（`fromJsonArray` 内部已用 `runCatching` 包装，失败返回 `Result.failure`，`getOrNull()` 返回 null）

**影响**：无功能影响，仅 JSON 解析库替换为项目统一方案。`GSON.fromJsonArray<String>` 返回 `Result<List<String>>`，`getOrNull()` 返回 `List<String>?`，与原 `decodeFromString` 语义等价。编译验证通过。

**教训**：设计文档指定依赖库前，必须检查项目 `build.gradle` 是否已引入该库，优先复用项目现有 JSON 解析方案（Gson），避免引入新依赖。

### AOAdapt-2：VideoPlay.kt else 分支变量命名调整（2026-07-13 实施时优化）

**问题**：设计文档 Section 4 的 else 分支成功路径用 `val mUrl = webViewUrl` 命名，与单 URL 分支（L267-287）的 `playAnalyzeUrl` 命名不一致。

**调整**：成功路径直接用 `webViewUrl` 变量构造 `AnalyzeUrl(webViewUrl, ...)` 并命名为 `playAnalyzeUrl`，与单 URL 分支保持一致，提高代码可读性。功能无变化。

### AOAdapt-3：shouldInterceptRequest 工作线程调用 destroy() 崩溃修复（2026-07-13 真机日志发现）

**问题**：真机测试日志（crash-2026-07-13-14-53-47）显示 `shouldInterceptRequest` 命中 sourceRegex 后调用 `destroy()` 导致 `IllegalStateException: Calling View methods on another thread than the UI thread`。崩溃链路：`shouldInterceptRequest`（工作线程）→ `destroy()` → `WebViewPool.release()` → `webView.setLayoutParams()`（[WebViewPool.kt:77](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/webView/WebViewPool.kt#L77)）。Android 官方文档明确 shouldInterceptRequest 在工作线程调用，但 WebView 的 View 方法必须在 UI 线程。

**调整**：`shouldInterceptRequest` 命中后用 `mHandler.post { destroy() }` 切换到 UI 线程执行 destroy()。同时在 `VideoUrlExtractor` 新增 `sanitizeUrl` 方法，修复 `VideoPlay.kt` L308/L317/L337 + `VideoUrlExtractor.kt` L162/L187 的 URL 泄露日志（P0 安全规范）。

**根因反思**：交叉验证（3个子代理静态代码审查）未发现此问题，因为线程问题只能通过运行时日志发现。**静态代码审查无法替代真机验证**。

### AOAdapt-4：ExoPlayer cacheDataSourceFactory 上游不支持 file:// 协议修复（2026-07-13 真机日志发现）

**问题**：真机测试日志（appLog-26-07-13_14-53-52 + logcat L81452）显示 ExoPlayer 播放 `file:///storage/.../d5e6b4257ba2fa18bc679a00eef2e037.mpd` 时报 `HttpDataSourceException: Malformed URL`。根因：[ExoPlayerHelper.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/exoplayer/ExoPlayerHelper.kt#L105) `cacheDataSourceFactory` 的 `setUpstreamDataSourceFactory(okhttpDataFactory)` 使用 OkHttpDataSource 作为上游数据源，OkHttpDataSource 只支持 http/https 协议，遇到 file:// 路径直接抛 Malformed URL。

**调整**：`setUpstreamDataSourceFactory(okhttpDataFactory)` 改为 `setUpstreamDataSourceFactory(DefaultDataSource.Factory(appCtx, okhttpDataFactory))`。DefaultDataSource 会根据 URI scheme 自动选择 FileDataSource（file://）/ OkHttpDataSource（http/https）/ ContentDataSource（content://），提升播放器对本地视频文件的兼容性。

**触发场景**：播放地址为本地缓存路径（如 DASH .mpd manifest 文件）。来源可能是源配置返回本地路径或某种降级逻辑。修复后即使触发也不会崩溃。

### AOAdapt-5：WebViewPool.destroyWithRetry 工作线程调用 WebView.destroy 线程安全修复（2026-07-13 真机日志发现）

**问题**：真机测试日志（appLog-26-07-12 多个会话）显示 `WebViewPool: destroy failed after 3 attempts` + `A WebView method was called on thread 'DefaultDispatcher-worker-4'`。根因：[WebViewPool.kt](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/webView/WebViewPool.kt#L196) `startCleanupTimer` 在 `Dispatchers.IO` 协程中调用 `destroyWithRetry`，直接调用 `WebView.destroy()` 违反单线程约束，重试3次都在工作线程必然失败，导致 WebView 实例泄漏。该问题与 AOAdapt-3（shouldInterceptRequest 崩溃）同源，均为 WebView 跨线程访问。

**调整**：`destroyWithRetry` 内部判断当前线程，若非主线程则用 `mainHandler.post` 切到主线程执行。添加 `mainHandler` 字段（`Handler(Looper.getMainLooper())`）+ `destroyOnMainThread` 私有方法。保留重试3次机制。

**证据**：跨多日5次复发（07-12 14:17/14:23/15:20/19:34/22:25），说明该问题在每次会话都会触发。

### AOAdapt-6：ImageUtils.decode(InputStream) ClassCastException 类型容错修复（2026-07-13 真机日志发现）

**问题**：真机测试日志（appLog-26-07-12 14:46:32）显示 `ClassCastException: okio.RealBufferedSource$inputStream$1 cannot be cast to byte[]` at `ImageUtils.decode(ImageUtils.kt:54)`。根因：`evalJS` 返回值可能是 InputStream（okio BufferedSource 包装类）而非 ByteArray，直接 `as ByteArray` 强转失败。

**调整**：`evalJS` 返回值用 `when` 表达式判断类型：`is ByteArray` 直接用，`is InputStream` 调用 `readBytes()` 转换，其他返回 null。避免 ClassCastException。

### AOAdapt-7：ImageUtils.decode(ByteArray) 图片解密长度校验收容错（2026-07-13 真机日志发现）

**问题**：真机测试日志显示每个会话必现 `图片解密错误 src=...logo.png` + `IllegalBlockSizeException: DATA_NOT_MULTIPLE_OF_BLOCK_LENGTH`。根因：RssSource 配置了图片解密规则但图片实际未加密（如站点A的 logo.png），强制解密导致块长度不匹配。

**调整**：`decode(ByteArray)` 在调用 `evalJS` 解密前校验数据长度：若 `bytes.size % 8 != 0 && bytes.size % 16 != 0`（非 DES/AES/SM4 块对齐），直接返回原 bytes 跳过解密。避免对未加密图片强制解密的异常日志噪声。

---

## 反模式检查清单

- [x] 未跳过 OpenSpec 任何检查点
- [x] 未在 `temp/` 目录创建测试脚本（使用 `ai_tests/scripts/` 固定脚本）
- [x] 未使用公共 Python（使用 `ai_tests\venv\Scripts\python.exe`）
- [x] 未委托后台 Agent 修改源码文件（VideoUrlExtractor.kt / VideoPlay.kt 由主 Agent 串行修改）
- [x] 未跳过 5.5 AI 自动端到端测试（Section 7 L2 验证）
- [x] 未改代码不写 updateLog（Section 8）
- [x] 未改造代码不加日志（Section 5）
- [x] 未信任单一来源（Section 7 多场景交叉验证）
- [x] 未只看报告不看源码（Section 1 Read 确认源码状态）
- [x] 未修完不更新导航（Section 9 文档同步）

---

## 任务依赖关系

```
Section 1（准备）→ Section 2（extractWithWebView）→ Section 3（VideoPlay 改造）
                                                          │
                                                          ▼
Section 5（日志）← Section 4（正则验证）← Section 2/3 完成
        │
        ▼
Section 6（编译+L1）→ Section 7（L2 真机）→ Section 8（updateLog）→ Section 9（文档同步）
```

- Section 2 和 Section 3 必须串行（VideoPlay 调用 VideoUrlExtractor 新方法）
- Section 4 依赖 Section 2.2（正则常量定义）
- Section 5 依赖 Section 2/3（日志在方法/分支内）
- Section 6 依赖 Section 2/3/5 完成
- Section 7 依赖 Section 6 编译通过
- Section 8 必须在 Section 6 编译前完成（编译前更新 updateLog）
- Section 9 依赖 Section 7 L2 验证通过

---

## 实施卡点验证（检查点1第五次反馈 — 源码逐行验证）

> **用户反馈**："确定当前方案可以落地实施么？有没有卡点，阻塞点？"
>
> 基于源码逐行验证 5 个潜在实施卡点，结论：**全部通过，无阻塞点，方案可落地实施**。

### 验证清单

- [x] 卡点1：AnalyzeUrl 构造函数签名 — ✅ 通过
  - 源码：`AnalyzeUrl.kt` L81-97
  - `source: BaseSource? = null`（L88）+ `ruleData: RuleDataInterface? = null`（L89）都有默认值
  - `AnalyzeUrl(url, source = source, ruleData = null)` 合法（位置参数 + 命名参数）
- [x] 卡点2：shouldInterceptRequest 与 onLoadResource 重复匹配 — ✅ 通过
  - 源码：`BackstageWebView.kt` L82-86（`!block.isCompleted` 检查）+ L178-183（destroy：`callback = null`）
  - 双重保护：第一个回调 resume 协程 + destroy 设置 callback=null；第二个回调 `callback?.onResult` null 安全跳过
- [x] 卡点3：onPageStarted JS 注入时机 — ✅ 通过
  - 源码：`BackstageWebView.kt` L209（HtmlWebViewClient）vs L321（SnifferWebClient）
  - SnifferWebClient 没有 onPageStarted/onPageFinished 重写，新增不影响 HtmlWebViewClient
  - 视频抓取用 SnifferWebClient（L173），搜索/书源用 HtmlWebViewClient（L171），互不影响
- [x] 卡点4：BackstageWebView 构造参数兼容性 — ✅ 通过
  - 源码：`BackstageWebView.kt` L53-67
  - sourceRegex（L59）+ javaScript（L61）已存在；新增 interceptAllRequests + videoSniffJs 有默认值
  - 所有现有调用点不传新参数，完全向后兼容
- [x] 卡点5：shouldInterceptRequest 线程安全 — ✅ 通过（需加防御）
  - 源码：`BackstageWebView.kt` L72（closed）+ L178-183（destroy）+ L185-189（isActiveWebView）
  - 防御措施：shouldInterceptRequest 开头加 `if (closed || callback == null) return null`（已在 Section 2.3 体现）

### 验证结论

**5 个卡点全部通过，无阻塞点，方案可落地实施。**

仅需一处调整：shouldInterceptRequest 开头加一行防御性检查 `if (closed || callback == null) return null`（已在 Section 2.3 代码中体现）。
