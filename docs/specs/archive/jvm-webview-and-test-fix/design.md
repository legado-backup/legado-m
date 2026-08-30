# Design: JVM 仿真服务端 WebView 支持 + 测试有效性修复 + 债务清理

> **源码参照原则**：所有行为与 Legado 真机源码一致，不臆测。

---

## 1. 问题根因分析

### 1.1 测试有效性缺陷（根因链）

```
debug() 吞掉异常
    ↓
RuleEngineServer batch: success = !抛异常 → 永远 true
    ↓
Python 测试脚本: success = batch_result["success"] → 永远 true
    ↓
"100% 通过率" 假象
```

**源码证据**：
- `RssSourceDebugger.debug()` (L77-97)：try-catch 捕获所有异常，只调 `logger.error()`，不重新抛出
- `BookSourceDebugger.debug()` (L55-78)：同样模式
- `RuleEngineServer` batch 处理 (L225-240)：`success = try { debugger.debug(); true } catch { false }`

### 1.2 WebView 不可用（根因链）

```
BackstageWebView.getStrResponse() 抛 UnsupportedOperationException
    ↓
AnalyzeUrl.executeStrRequest() 中 useWebView 分支直接异常
    ↓
AnalyzeRule.getWebJsResult() 中 @webjs: 规则直接异常
    ↓
debug() 捕获异常但不抛出 → 标记为 success=true（假象）
```

**源码证据**：
- `BackstageWebView.kt` (L19-21)：`throw UnsupportedOperationException("JVM 环境不支持 BackstageWebView")`
- `JsExtensionsStub.webView()` (L176-181)：降级为 `Jsoup.connect`（无法执行 JS）
- `JsExtensionsStub.startBrowserAwait()` (L249-251)：抛 `UnsupportedOperationException`

### 1.3 Legado 真机 WebView 实现方式（源码分析）

| 组件 | 真机实现 | 仿真现状 |
|------|---------|---------|
| `BackstageWebView` | Android WebView + WebViewClient + WebChromeClient | 抛异常 |
| `AnalyzeUrl.useWebView` | 检测 URL Option 中 `webView:true` → 走 BackstageWebView | 代码存在但 BackstageWebView 抛异常 |
| `AnalyzeRule @webjs:` | 检测 `@webjs:` 前缀 → 调 `getWebJsResult()` → BackstageWebView | 代码存在但 BackstageWebView 抛异常 |
| `JsExtensions.webView()` | `runBlocking { BackstageWebView(...).getStrResponse().body }` | 降级为 Jsoup.connect |
| `startBrowserAwait` | `SourceVerificationHelp` + `LockSupport.parkNanos` 阻塞等待 | 抛异常 |

---

## 2. 技术方案

### 2.1 方向 1：修复测试有效性校验

#### 2.1.1 DebugResult 数据结构

新增 `DebugResult.kt`：

```kotlin
package io.legado.ruleengine

import com.google.gson.JsonObject

data class DebugResult(
    val success: Boolean,
    val needsWebView: Boolean = false,
    val needsUserIntervention: Boolean = false,
    val summary: JsonObject = JsonObject(),
    val errorStage: String? = null,
    val errorMessage: String? = null,
    val webViewRequests: List<WebViewRequest> = emptyList()
)

data class WebViewRequest(
    val url: String?,
    val html: String?,
    val js: String?,
    val sourceRegex: String?,
    val type: String  // "load" | "sniff" | "overrideUrl" | "login"
)
```

#### 2.1.2 debug() 方法改造

**RssSourceDebugger.debug()** 改为返回 `DebugResult`：

```kotlin
fun debug(): DebugResult {
    return try {
        when {
            isAbsUrl(key) -> debugContent(key)
            singleUrl -> debugSingleUrl()
            else -> debugSort()
        }
    } catch (e: WebViewRequiredException) {
        // BackstageWebView 需求 → 不算失败，标记 needsWebView
        DebugResult(
            success = false,
            needsWebView = true,
            webViewRequests = e.requests,
            errorStage = e.stage,
            errorMessage = e.message
        )
    } catch (e: UserInterventionException) {
        // 登录/验证码 → 不算失败，标记 needsUserIntervention
        DebugResult(
            success = false,
            needsUserIntervention = true,
            errorStage = e.stage,
            errorMessage = e.message
        )
    } catch (e: Exception) {
        DebugResult(
            success = false,
            errorStage = "unknown",
            errorMessage = e.message
        )
    }
}
```

**关键变化**：
- 不再用 `UnsupportedOperationException`，改为自定义 `WebViewRequiredException` 和 `UserInterventionException`
- `debugSort()`/`debugContent()` 等内部方法在遇到 webView 需求时抛 `WebViewRequiredException`
- `debug()` 捕获后返回 `DebugResult(needsWebView=true)`

#### 2.1.3 有效数据校验标准

```kotlin
// RssSourceDebugger 中
private fun validateResult(articleCount: Int, contentLength: Int): Boolean {
    return articleCount > 0 && contentLength > 0
}

// BookSourceDebugger 中
private fun validateResult(bookCount: Int, chapterCount: Int, contentLength: Int): Boolean {
    return bookCount > 0 && chapterCount > 0 && contentLength > 0
}
```

#### 2.1.4 RuleEngineServer batch 改造

```kotlin
// batch 处理中
val result = when (sourceType) {
    "book" -> BookSourceDebugger(sourceJson, key, batchLogger).debug()
    else -> RssSourceDebugger(sourceJson, key, batchLogger).debug()
}

val itemResult = JsonObject()
itemResult.addProperty("sourceName", sourceName)
itemResult.addProperty("success", result.success)
itemResult.addProperty("needsWebView", result.needsWebView)
itemResult.addProperty("needsUserIntervention", result.needsUserIntervention)
itemResult.add("summary", result.summary)
if (result.errorStage != null) {
    itemResult.addProperty("errorStage", result.errorStage)
    itemResult.addProperty("errorMessage", result.errorMessage ?: "")
}
if (result.webViewRequests.isNotEmpty()) {
    itemResult.add("webViewRequests", GSON.toJsonTree(result.webViewRequests))
}
results.add(itemResult)
```

### 2.2 方向 3：Python 客户端 + Selenium WebView 支持

#### 2.2.1 BackstageWebView 改造

不再抛异常，改为抛 `WebViewRequiredException`：

```kotlin
class BackstageWebView(
    val url: String? = null,
    val html: String? = null,
    // ... 其他参数不变
) {
    fun getStrResponse(): StrResponse {
        // 收集 webView 请求信息
        val request = WebViewRequest(
            url = url,
            html = html,
            js = javaScript,
            sourceRegex = sourceRegex,
            type = if (sourceRegex != null) "sniff" else "load"
        )
        throw WebViewRequiredException(
            stage = "unknown",
            requests = listOf(request),
            message = "需要 WebView 渲染: url=${url?.take(80)}, js=${javaScript?.take(50)}"
        )
    }
}
```

#### 2.2.2 JsExtensionsStub.webView() 改造

```kotlin
override fun webView(html: String?, url: String?, js: String?, cacheFirst: Boolean): String? {
    val targetUrl = url ?: return html
    // 不再降级为 Jsoup.connect，改为抛 WebViewRequiredException
    throw WebViewRequiredException(
        stage = "js_webView",
        requests = listOf(WebViewRequest(
            url = targetUrl,
            html = html,
            js = js,
            sourceRegex = null,
            type = "load"
        )),
        message = "JS 调用 webView() 需要渲染: url=$targetUrl"
    )
}
```

#### 2.2.3 startBrowserAwait 改造

```kotlin
override fun startBrowserAwait(url: String, title: String, refetchAfterSuccess: Boolean, html: String?): StrResponse {
    throw UserInterventionException(
        stage = "login",
        message = "源需要登录/人工验证: url=$url, title=$title\n建议：在 Legado App 中手动登录后导出 Cookie"
    )
}
```

#### 2.2.4 Python 客户端 Selenium 集成

新增 `webview_handler.py`：

```python
"""
WebView 委托处理器 - 使用 Selenium/Playwright 渲染页面
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import json

class WebViewHandler:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None

    def _ensure_driver(self):
        if self.driver is None:
            options = Options()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Chrome(options=options)

    def render_url(self, url, js=None, timeout=30):
        """加载 URL 并执行 JS，返回渲染后 HTML"""
        self._ensure_driver()
        self.driver.set_page_load_timeout(timeout)
        self.driver.get(url)
        if js:
            result = self.driver.execute_script(js)
            if result:
                return str(result)
        return self.driver.page_source

    def render_html(self, html, js=None, base_url="about:blank", timeout=30):
        """加载 HTML 并执行 JS，返回结果"""
        self._ensure_driver()
        self.driver.get(base_url)
        self.driver.execute_script(f"document.write(arguments[0]);", html)
        if js:
            result = self.driver.execute_script(js)
            if result:
                return str(result)
        return self.driver.page_source

    def sniff_resource(self, url, source_regex, js=None, timeout=30):
        """嗅探资源 URL（视频/音频）"""
        self._ensure_driver()
        # 监听网络请求
        urls = []
        self.driver.execute_cdp_cmd("Network.enable", {})
        # ... 性能日志监听资源请求
        self.driver.get(url)
        if js:
            self.driver.execute_script(js)
        time.sleep(timeout)
        # 从性能日志中匹配 source_regex
        logs = self.driver.get_log("performance")
        for entry in logs:
            # 解析网络请求 URL，匹配正则
            ...
        return matched_url

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
```

#### 2.2.5 Python 客户端 batch_debug 改造

```python
def batch_debug(self, sources, source_type="rss", on_progress=None, on_complete=None,
                webview_handler=None):
    """
    批量调试，支持 WebView 委托

    Args:
        webview_handler: WebViewHandler 实例，用于处理 needsWebView 的源
    """
    # ... 发送 batch 命令 ...

    # batch 完成后，处理 needsWebView 的源
    if webview_handler:
        for result in results:
            if result.get("needsWebView"):
                self._handle_webview_source(result, webview_handler, source_type)

    return final_result

def _handle_webview_source(self, result, webview_handler, source_type):
    """处理需要 WebView 的源"""
    requests = result.get("webViewRequests", [])
    for req in requests:
        if req["type"] == "load":
            # 加载 URL 并执行 JS
            html = webview_handler.render_url(req["url"], req.get("js"))
            # 用 JAR 的 analyzeRule 解析渲染后 HTML
            # ... 调用 self.analyze_rule(html, rule) ...
        elif req["type"] == "sniff":
            # 嗅探资源
            url = webview_handler.sniff_resource(req["url"], req.get("sourceRegex"))
            # ... 处理嗅探结果 ...
```

### 2.3 方向 2：临时文件清理

#### 2.3.1 nul 文件清理

5 个 `nul` 文件需用 `\\?\` 前缀路径删除：

```python
import os

nul_files = [
    r"f:\myself\github\WeAgentChat\temp\legado\nul",
    r"f:\myself\github\WeAgentChat\temp\legado\.trae\skills\legado-source-creator\scripts\nul",
    r"f:\myself\github\WeAgentChat\temp\legado\.trae\skills\legado-source-creator\tools\legado-jvm\nul",
    r"f:\myself\github\WeAgentChat\temp\legado\.trae\skills\legado-source-creator\tools\mvp1-build\nul",
    r"f:\myself\github\WeAgentChat\temp\legado\temp\tmp\1080zyk\nul",
]

for path in nul_files:
    # Windows 保留名文件需用 \\?\ 前缀
    long_path = "\\\\?\\" + path
    if os.path.exists(long_path):
        os.remove(long_path)
        print(f"Deleted: {path}")
```

#### 2.3.2 临时测试脚本评估

| 文件 | 评估 | 处理 |
|------|------|------|
| `scripts/large-scale-test.py` | 有用（大规模测试） | 保留，适配新协议 |
| `scripts/test_all_sources.py` | 有用（全量测试） | 保留，适配新协议 |
| `scripts/debug-source.py` | 有用（端到端调试） | 保留，适配新协议 |
| `scripts/test_sorturl_js.py` | 临时（sortUrl JS 测试） | 删除 |
| `scripts/debug_mjv006.py` | 临时（单源调试） | 删除 |
| `tools/test_debug_rss.py` | 临时（RSS 调试） | 删除 |
| `temp/tmp/1080zyk/*.py` (4个) | 临时（1080zyk 专用） | 删除 |
| `temp/TestJsoupSelector.java` | 临时（选择器测试） | 删除 |
| `temp/tmp/1080zyk/RhinoTest*.java` (2个) | 临时（Rhino 测试） | 删除 |

#### 2.3.3 docs/temp-analysis/ 评估

24 个文档是多代理分析流水线的产出物。评估：
- 如果 `docs/INDEX.md` 或其他文档引用了它们 → 保留
- 如果无引用 → 归档到 `docs/archive/temp-analysis/` 或删除

#### 2.3.4 旧 mvp1-build 目录

```bash
# 检查是否有文档引用 mvp1-build
grep -r "mvp1-build" --include="*.md" .
# 如果无引用（jvm-extract-refactor 已替换为 legado-jvm）→ 删除
```

### 2.4 经验教训提取方法

#### 2.4.1 测试结果分析维度

```python
def extract_lessons(test_results):
    """从测试结果中提取经验教训"""
    lessons = {
        # 维度 1：网站特征 → 规则类型
        "site_features": {},
        # 维度 2：规则类型 → 成功率
        "rule_type_stats": {},
        # 维度 3：失败原因分类
        "failure_patterns": {},
        # 维度 4：WebView 需求模式
        "webview_patterns": {},
        # 维度 5：登录/验证码模式
        "login_patterns": {},
    }

    for result in test_results:
        # 分析网站特征（域名、页面结构）
        # 分析规则类型（CSS/XPath/JSONPath/JS/Regex）
        # 分析失败原因
        # 分析 WebView 需求
        ...

    return lessons
```

#### 2.4.2 经验写入格式

```markdown
## 网站特征 → 规则类型映射

| 网站特征 | 推荐规则类型 | 成功率 | 注意事项 |
|---------|-------------|--------|---------|
| 静态 HTML 列表 | CSS 选择器 | 95% | 注意相对 URL 拼接 |
| JSON API 响应 | JSONPath | 90% | 注意分页参数 |
| JS 动态渲染 | 需 WebView | N/A | 标记 needsWebView |
| Cloudflare 防护 | 需 WebView | N/A | 标记 needsUserIntervention |

## 高频陷阱模式

| 陷阱 | 影响范围 | 修复方案 |
|------|---------|---------|
| 相对 URL 未拼接 | 3/7 | RssSourceDebugger 自动拼接 |
| sortUrl 格式错误 | 1/7 | 检查 `分类名::URL` 格式 |
| webView:true 但无 webJs | 2/300 | 检查 URL 配置完整性 |
```

---

## 3. 文件变更清单

### 3.1 新增文件

| 文件 | 用途 |
|------|------|
| `tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/DebugResult.kt` | DebugResult + WebViewRequest 数据结构 |
| `tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/WebViewRequiredException.kt` | WebView 需求异常 |
| `tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/UserInterventionException.kt` | 用户介入需求异常 |
| `tools/webview_handler.py` | Python Selenium WebView 处理器 |

### 3.2 修改文件

| 文件 | 变更内容 |
|------|---------|
| `tools/legado-jvm/.../RssSourceDebugger.kt` | debug() 返回 DebugResult，内部方法抛 WebViewRequiredException |
| `tools/legado-jvm/.../BookSourceDebugger.kt` | 同上 |
| `tools/legado-jvm/.../RuleEngineServer.kt` | batch 处理使用 DebugResult |
| `tools/legado-jvm/.../BackstageWebView.kt` | 抛 WebViewRequiredException 而非 UnsupportedOperationException |
| `tools/legado-jvm/.../JsExtensionsStub.kt` | webView 方法抛 WebViewRequiredException，startBrowserAwait 抛 UserInterventionException |
| `tools/rule_engine_client.py` | batch_debug 增加 webview_handler 参数 |
| `scripts/large-scale-test.py` | 适配新协议，检查有效数据 |
| `scripts/debug-source.py` | 适配新协议 |

### 3.3 删除文件

| 文件 | 原因 |
|------|------|
| 5 个 `nul` 文件 | Windows 保留名文件 |
| `scripts/test_sorturl_js.py` | 临时测试脚本 |
| `scripts/debug_mjv006.py` | 临时测试脚本 |
| `tools/test_debug_rss.py` | 临时测试脚本 |
| `temp/tmp/1080zyk/*.py` (4个) | 临时测试脚本 |
| `temp/TestJsoupSelector.java` | 临时 Java 文件 |
| `temp/tmp/1080zyk/RhinoTest*.java` (2个) | 临时 Java 文件 |
| `tools/mvp1-build/` (整个目录) | 旧仿真端，已被 legado-jvm 替换 |

---

## 4. 依赖变更

### 4.1 Python 依赖

```txt
# requirements.txt 新增
selenium>=4.15.0
```

### 4.2 系统依赖

- Chrome 浏览器（Selenium WebDriver）
- 或 Firefox + geckodriver

---

## 5. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| Selenium 依赖 Chrome 浏览器 | 检测 Chrome 是否安装，未安装时降级为"标记 needsWebView 不渲染" |
| Selenium 渲染速度慢 | 设置超时（30s），超时标记为失败 |
| debug() 改造影响现有测试 | 保留旧 debug() 签名作为 deprecated，新增返回 DebugResult 的版本 |
| 临时文件删除误删 | 删除前检查是否有文档引用 |

---

## 6. 验收标准

| 标准 | 验证方法 |
|------|---------|
| debug() 返回 DebugResult | 单元测试 |
| batch 结果包含 needsWebView | 用 evalJS 命令测试 |
| success=true 的源有有效数据 | 大规模测试验证 |
| WebView 源能通过 Selenium 测试 | 端到端测试 |
| 0 个 nul 文件 | 文件系统检查 |
| 经验教训写入 basic-memory | basic-memory 查询 |
