# Spec: JVM 仿真服务端 WebView 支持 + 测试有效性修复 + 债务清理

---

## Intent（意图）

修复 jvm-extract-refactor 项目中三个被"表面完成"掩盖的严重问题，使仿真工具链真正可用于 Skill 的端到端书源/订阅源验证。核心目标：**测试不是为了看通过率数字，而是为了发现问题和优化工具链**。

---

## Scope（范围）

### 三个改进方向（并行处理）

#### 方向 1：修复测试有效性校验

**问题根因**：
- `RssSourceDebugger.debug()` 和 `BookSourceDebugger.debug()` 用 try-catch 吞掉所有异常（包括 `UnsupportedOperationException`），只是记录到 logger，不重新抛出
- `RuleEngineServer` batch 处理中 `success = !抛异常`，由于 debug() 不抛异常，所有源都被标记为 `success=true`
- 测试脚本只检查"是否抛异常"，不检查"是否获取到有效数据"

**修复范围**：
- `debug()` 方法改为返回 `DebugResult` 对象（含 success/summary/needsWebView/errorStage 字段），不再吞掉异常
- `RuleEngineServer` batch 处理使用 `DebugResult` 判断成功/失败
- batch 结果中增加 `articleCount`、`contentLength`、`needsWebView` 字段
- Python 客户端和测试脚本检查有效数据指标

#### 方向 2：清理临时文件和代码债务

**清理清单**：
- 5 个 `nul` 文件（Windows 保留名，需用 `\\?\` 前缀路径删除）
- 10+ 临时测试脚本（评估保留/归档/删除）
- 24 个 `docs/temp-analysis/` 临时文档（评估保留/删除）
- 3 个临时 Java 文件（删除）
- 旧 `mvp1-build/` 目录（标记 deprecated 或删除）

#### 方向 3：实现 Python 客户端 + Selenium 的 WebView 支持

**架构设计**：
- JAR 中 `BackstageWebView` 不再抛异常，返回标记 `StrResponse(body="__WEBVIEW_REQUIRED__")`
- `AnalyzeUrl`/`AnalyzeRule` 检测到标记后，在 `DebugResult` 中设置 `needsWebView=true`
- Python 客户端检测到 `needsWebView` 后，用 Selenium/Playwright 加载页面、执行 JS、获取渲染后 HTML
- Python 客户端将渲染后 HTML 传回 JAR，用 `analyzeRule` 命令继续解析
- 登录/验证码场景标记为"需用户介入"，输出诊断信息和操作建议

---

## Approach（方法）

### WebView 委托协议（核心设计）

```
JAR (RuleEngineServer)              Python 客户端
    │                                     │
    │  1. batch_debug(sources)            │
    │ ─────────────────────────────────→  │
    │                                     │
    │  2. batch_progress(source1)        │
    │ ←─────────────────────────────────  │
    │  (needsWebView=true)               │
    │                                     │
    │                          3. Selenium加载URL/执行JS
    │                          4. 获取渲染后HTML
    │                                     │
    │  5. analyzeRule(html, rule)        │
    │ ─────────────────────────────────→  │
    │                                     │
    │  6. 解析结果                       │
    │ ←─────────────────────────────────  │
    │                                     │
    │  7. batch_complete                 │
    │ ←─────────────────────────────────  │
```

**关键决策**：JAR 不在 batch 处理中同步等待 WebView 渲染，而是：
1. batch 处理中遇到 webView 需求时标记 `needsWebView=true`，跳过该阶段
2. Python 客户端在 batch 完成后，对 `needsWebView=true` 的源用 Selenium 重新测试
3. Selenium 测试流程：加载 URL → 获取渲染后 HTML → 用 JAR 的 `analyzeRule` 命令解析

### 测试有效性校验标准

| 源类型 | 阶段 | 有效数据标准 |
|--------|------|-------------|
| RSS | sort | `articleCount > 0`（文章列表非空） |
| RSS | content | `contentLength > 0`（正文长度 > 0） |
| Book | search | `bookCount > 0`（搜索结果非空） |
| Book | detail | `bookInfo != null`（书籍信息存在） |
| Book | toc | `chapterCount > 0`（目录非空） |
| Book | content | `contentLength > 0`（正文长度 > 0） |

### DebugResult 数据结构

```kotlin
data class DebugResult(
    val success: Boolean,          // 是否成功（必须满足有效数据标准）
    val needsWebView: Boolean,     // 是否需要 WebView 渲染
    val needsUserIntervention: Boolean,  // 是否需要用户介入（登录/验证码）
    val summary: JsonObject,       // 数据指标（articleCount/contentLength 等）
    val errorStage: String?,      // 失败阶段（sort/content/search/detail/toc）
    val errorMessage: String?,     // 错误信息
    val webViewRequests: List<WebViewRequest>  // WebView 请求详情
)

data class WebViewRequest(
    val url: String?,              // 目标 URL
    val html: String?,            // 当前 HTML（用于二次解析）
    val js: String?,              // 需执行的 JS
    val sourceRegex: String?,     // 资源嗅探正则
    val type: String              // "load" | "sniff" | "overrideUrl" | "login"
)
```

---

## Requirements（需求）

### R1：测试有效性（方向 1）

- **R1.1**：`debug()` 方法返回 `DebugResult`，不再吞掉异常
- **R1.2**：batch 结果中 `success=true` 必须满足有效数据标准
- **R1.3**：batch 结果中包含 `articleCount`、`contentLength`、`needsWebView` 字段
- **R1.4**：Python 客户端和测试脚本检查有效数据指标
- **R1.5**：`needsWebView=true` 的源不算失败，标记为"需 WebView 渲染"

### R2：WebView 支持（方向 3）

- **R2.1**：`BackstageWebView` 返回标记而非抛异常
- **R2.2**：`AnalyzeUrl` 检测到 `webView:true` 配置时设置 `needsWebView=true`
- **R2.3**：`AnalyzeRule` 检测到 `@webjs:` 规则时设置 `needsWebView=true`
- **R2.4**：Python 客户端集成 Selenium/Playwright
- **R2.5**：Python 客户端对 `needsWebView=true` 的源用 Selenium 重新测试
- **R2.6**：Selenium 渲染后 HTML 传回 JAR 用 `analyzeRule` 解析
- **R2.7**：登录/验证码场景标记为"需用户介入"，输出诊断信息

### R3：债务清理（方向 2）

- **R3.1**：删除 5 个 `nul` 文件
- **R3.2**：临时测试脚本评估保留/归档/删除
- **R3.3**：`docs/temp-analysis/` 24 个文档评估保留/删除
- **R3.4**：删除 3 个临时 Java 文件
- **R3.5**：旧 `mvp1-build/` 目录标记 deprecated 或删除

### R4：经验教训提取

- **R4.1**：从测试中提取网站特征→规则类型→常见陷阱的映射模式
- **R4.2**：将经验写入 basic-memory 和 references/site-features/
- **R4.3**：经验必须可指导后续书源创建（如"遇到 XX 特征的网站，应该用 YY 规则类型"）

---

## Scenarios（场景）

### 场景 1：普通 RSS 源测试（无 WebView）

```
输入：rss_source.json（普通 HTTP 请求 + CSS 选择器规则）
流程：JAR batch_debug → debug() 返回 DebugResult(success=true, articleCount=10, contentLength=500)
输出：success=true（有效数据验证通过）
```

### 场景 2：需要 WebView 的 RSS 源

```
输入：rss_source.json（URL 配置 webView:true + webJs:"document.querySelector('.content').innerHTML"）
流程：
  1. JAR batch_debug → debug() 检测到 webView:true → 返回 DebugResult(needsWebView=true)
  2. Python 客户端检测到 needsWebView=true
  3. Selenium 加载 URL → 执行 webJs → 获取渲染后 HTML
  4. Python 客户端用 JAR analyzeRule 解析渲染后 HTML
  5. 解析结果返回 success=true, contentLength=500
输出：success=true（通过 Selenium 委托完成）
```

### 场景 3：需要登录的源

```
输入：book_source.json（搜索需要 Cookie 登录）
流程：
  1. JAR batch_debug → debug() 检测到登录需求 → 返回 DebugResult(needsUserIntervention=true)
  2. Python 客户端输出诊断信息："该源需要登录，请在 Legado App 中手动登录后导出 Cookie"
  3. 用户导入 Cookie 后重新测试
输出：needsUserIntervention=true（不算失败，标记为需用户介入）
```

### 场景 4：`@webjs:` 规则二次解析

```
输入：rss_source.json（正文规则包含 @webjs:document.querySelector('.article-content').innerText）
流程：
  1. JAR batch_debug → debug() 获取到 HTML → AnalyzeRule 检测到 @webjs: → 返回 DebugResult(needsWebView=true, webViewRequests=[{html: "...", js: "...", type: "load"}])
  2. Python 客户端检测到 needsWebView=true
  3. Selenium 加载 HTML → 执行 JS → 获取结果
  4. 结果传回 JAR 继续解析
输出：success=true（通过 Selenium 委托完成）
```

### 场景 5：大规模测试经验提取

```
输入：300 个源测试结果
流程：
  1. 测试完成后分析结果：哪些源 needsWebView、哪些 needsUserIntervention、哪些失败
  2. 提取模式：网站特征（域名/页面结构）→ 规则类型（CSS/XPath/JS）→ 常见陷阱
  3. 写入 basic-memory 和 references/site-features/
输出：可指导后续书源创建的经验模式
```
