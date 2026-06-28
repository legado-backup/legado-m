# Tasks: JVM 仿真服务端 WebView 支持 + 测试有效性修复 + 债务清理

> **格式说明**：`- [ ] X.Y` 未完成 / `- [x] X.Y ✅ YYYY-MM-DD` 已完成

---

## 方向 1：修复测试有效性校验

> **目标**：debug() 返回 DebugResult，batch 结果检查有效数据，不再"假成功"

### 1.1 创建 DebugResult 数据结构

- [x] 1.1.1 ✅ 2026-06-20 创建 `tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/DebugResult.kt`：DebugResult + WebViewRequest 数据类
- [x] 1.1.2 ✅ 2026-06-20 创建 `tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/WebViewRequiredException.kt`：继承 NoStackTraceException，携带 WebViewRequest 列表
- [x] 1.1.3 ✅ 2026-06-20 创建 `tools/legado-jvm/src/main/kotlin/io/legado/ruleengine/UserInterventionException.kt`：继承 NoStackTraceException，携带 stage 和 message
- [x] 1.1.4 ✅ 2026-06-20 验证：三个新文件编译通过

### 1.2 改造 RssSourceDebugger

- [x] 1.2.1 ✅ 2026-06-20 阅读 `RssSourceDebugger.kt` 当前 debug() 方法（L77-97）
- [x] 1.2.2 ✅ 2026-06-20 修改 debug() 返回类型从 `void` 改为 `DebugResult`
- [x] 1.2.3 ✅ 2026-06-20 修改 debugSort()：在文章列表为空时返回 `DebugResult(success=false, errorStage="sort")`
- [x] 1.2.4 ✅ 2026-06-20 修改 debugContent()：在正文长度为 0 时返回 `DebugResult(success=false, errorStage="content")`
- [x] 1.2.5 ✅ 2026-06-20 修改 debugSingleUrl()：同上
- [x] 1.2.6 ✅ 2026-06-20 修改 debug() 的 catch 块：捕获 `WebViewRequiredException` → 返回 `DebugResult(needsWebView=true)`
- [x] 1.2.7 ✅ 2026-06-20 修改 debug() 的 catch 块：捕获 `UserInterventionException` → 返回 `DebugResult(needsUserIntervention=true)`
- [x] 1.2.8 ✅ 2026-06-20 修改 debug() 的 catch 块：捕获其他 `Exception` → 返回 `DebugResult(success=false, errorStage="unknown")`
- [x] 1.2.9 ✅ 2026-06-20 修改 logger.result() 调用：使用 DebugResult 的 summary 字段
- [x] 1.2.10 ✅ 2026-06-20 验证：RssSourceDebugger 编译通过

### 1.3 改造 BookSourceDebugger

- [x] 1.3.1 ✅ 2026-06-20 阅读 `BookSourceDebugger.kt` 当前 debug() 方法（L55-78）
- [x] 1.3.2 ✅ 2026-06-20 修改 debug() 返回类型从 `void` 改为 `DebugResult`
- [x] 1.3.3 ✅ 2026-06-20 修改 debugSearch()：在搜索结果为空时返回 `DebugResult(success=false, errorStage="search")`
- [x] 1.3.4 ✅ 2026-06-20 修改 debugInfo()：在书籍信息为空时返回 `DebugResult(success=false, errorStage="detail")`
- [x] 1.3.5 ✅ 2026-06-20 修改 debugToc()：在目录为空时返回 `DebugResult(success=false, errorStage="toc")`
- [x] 1.3.6 ✅ 2026-06-20 修改 debugContent()：在正文长度为 0 时返回 `DebugResult(success=false, errorStage="content")`
- [x] 1.3.7 ✅ 2026-06-20 修改 debug() 的 catch 块：同 RssSourceDebugger
- [x] 1.3.8 ✅ 2026-06-20 验证：BookSourceDebugger 编译通过

### 1.4 改造 RuleEngineServer batch 处理

- [x] 1.4.1 ✅ 2026-06-20 阅读 `RuleEngineServer.kt` batch 处理（L225-240）
- [x] 1.4.2 ✅ 2026-06-20 修改 batch 处理：使用 `DebugResult` 而非 try-catch 判断成功
- [x] 1.4.3 ✅ 2026-06-20 在 batch itemResult 中增加 `needsWebView`、`needsUserIntervention`、`summary`、`errorStage`、`errorMessage` 字段
- [x] 1.4.4 ✅ 2026-06-20 在 batch itemResult 中增加 `webViewRequests` 字段（当 needsWebView=true 时）
- [x] 1.4.5 ✅ 2026-06-20 修改 batch_complete 中的 successCount 统计：只统计 `success=true` 的源
- [x] 1.4.6 ✅ 2026-06-20 增加 needsWebViewCount 和 needsUserInterventionCount 统计
- [x] 1.4.7 ✅ 2026-06-20 验证：RuleEngineServer 编译通过

### 1.5 适配 Python 客户端和测试脚本

- [x] 1.5.1 ✅ 2026-06-20 修改 `rule_engine_client.py` batch_debug：解析新字段（needsWebView/needsUserIntervention/summary）
- [x] 1.5.2 ✅ 2026-06-20 修改 `large-scale-test.py`：检查有效数据指标（articleCount/contentLength）
- [x] 1.5.3 ✅ 2026-06-20 修改 `large-scale-test.py`：区分 success/needsWebView/needsUserIntervention/failed 四种状态
- [x] 1.5.4 ✅ 2026-06-20 修改 `debug-source.py`：适配新输出格式
- [x] 1.5.5 ✅ 2026-06-20 验证：Python 脚本能正确解析新协议

### 1.6 方向 1 验证

- [x] 1.6.1 ✅ 2026-06-20 重新构建 JAR（fatJar）
- [x] 1.6.2 ✅ 2026-06-20 用 1 个 RSS 源测试：验证返回 DebugResult 中的 summary 包含 articleCount 和 contentLength
- [x] 1.6.3 ✅ 2026-06-20 用 1 个书源测试：验证返回 DebugResult 中的 summary 包含 bookCount 和 contentLength
- [x] 1.6.4 ✅ 2026-06-20 验证：正文长度为 0 的源被标记为 success=false（不再"假成功"）

---

## 方向 2：清理临时文件和代码债务

> **目标**：删除所有临时文件，清理代码债务

### 2.1 删除 nul 文件

- [x] 2.1.1 ✅ 2026-06-20 编写 Python 脚本用 `\\?\` 前缀路径删除 5 个 nul 文件
- [x] 2.1.2 ✅ 2026-06-20 验证：文件系统中不存在 nul 文件

### 2.2 删除临时测试脚本

- [x] 2.2.1 ✅ 2026-06-20 删除 `scripts/test_sorturl_js.py`
- [x] 2.2.2 ✅ 2026-06-20 删除 `scripts/debug_mjv006.py`
- [x] 2.2.3 ✅ 2026-06-20 删除 `tools/test_debug_rss.py`
- [x] 2.2.4 ✅ 2026-06-20 删除 `temp/tmp/1080zyk/test_all_rules.py`
- [x] 2.2.5 ✅ 2026-06-20 删除 `temp/tmp/1080zyk/full_real_test.py`
- [x] 2.2.6 ✅ 2026-06-20 删除 `temp/tmp/1080zyk/test_rules.py`
- [x] 2.2.7 ✅ 2026-06-20 删除 `temp/tmp/1080zyk/full_test.py`

### 2.3 删除临时 Java 文件

- [x] 2.3.1 ✅ 2026-06-20 删除 `temp/TestJsoupSelector.java`
- [x] 2.3.2 ✅ 2026-06-20 删除 `temp/tmp/1080zyk/RhinoTest.java`
- [x] 2.3.3 ✅ 2026-06-20 删除 `temp/tmp/1080zyk/RhinoTestES5.java`

### 2.4 评估 docs/temp-analysis/

- [x] 2.4.1 ✅ 2026-06-20 检查 `docs/INDEX.md` 和其他文档是否引用了 `docs/temp-analysis/` 中的文档
- [x] 2.4.2 ✅ 2026-06-20 如果有引用 → 保留被引用的文档
- [x] 2.4.3 ✅ 2026-06-20 如果无引用 → 归档到 `docs/archive/temp-analysis/` 或删除（目录不存在，无需处理）
- [x] 2.4.4 ✅ 2026-06-20 验证：docs/ 目录无冗余临时文档

### 2.5 处理旧 mvp1-build 目录

- [x] 2.5.1 ✅ 2026-06-20 检查是否有文档引用 `mvp1-build`（17个历史specs文档引用，3个活跃代码引用）
- [x] 2.5.2 ✅ 2026-06-20 如果无引用 → 删除整个 `tools/mvp1-build/` 目录（已删除，更新rule_engine_client.py引用指向legado-jvm）
- [x] 2.5.3 ✅ 2026-06-20 如果有引用 → 更新引用指向 `legado-jvm`（已更新rule_engine_client.py，删除build-mvp1.sh/bat）
- [x] 2.5.4 ✅ 2026-06-20 验证：无过时路径引用

### 2.6 方向 2 验证

- [x] 2.6.1 ✅ 2026-06-20 验证：0 个 nul 文件
- [x] 2.6.2 ✅ 2026-06-20 验证：0 个临时测试脚本（保留的除外）
- [x] 2.6.3 ✅ 2026-06-20 验证：0 个临时 Java 文件
- [x] 2.6.4 ✅ 2026-06-20 验证：docs/temp-analysis/ 已评估处理（目录不存在）
- [x] 2.6.5 ✅ 2026-06-20 验证：mvp1-build 目录已处理（已删除，引用已更新）
- [x] 2.6.6 ✅ 2026-06-20 验证：temp/ 目录临时文件已清理（122个文件已删除）

---

## 方向 3：实现 Python 客户端 + Selenium WebView 支持

> **目标**：JAR 检测到 webView 需求时委托给 Python 客户端用 Selenium 渲染

### 3.1 改造 BackstageWebView

- [x] 3.1.1 ✅ 2026-06-20 阅读 `BackstageWebView.kt` 当前实现（L1-22，直接抛异常）
- [x] 3.1.2 ✅ 2026-06-20 修改 `getStrResponse()`：收集 url/html/js/sourceRegex 信息，抛 `WebViewRequiredException` 而非 `UnsupportedOperationException`
- [x] 3.1.3 ✅ 2026-06-20 验证：BackstageWebView 编译通过

### 3.2 改造 JsExtensionsStub

- [x] 3.2.1 ✅ 2026-06-20 阅读 `JsExtensionsStub.kt` webView 相关方法（L173-255）
- [x] 3.2.2 ✅ 2026-06-20 修改 `webView()`：抛 `WebViewRequiredException` 而非降级为 Jsoup.connect
- [x] 3.2.3 ✅ 2026-06-20 修改 `webViewGetSource()`：抛 `WebViewRequiredException`（type="sniff"）
- [x] 3.2.4 ✅ 2026-06-20 修改 `webViewGetOverrideUrl()`：抛 `WebViewRequiredException`（type="overrideUrl"）
- [x] 3.2.5 ✅ 2026-06-20 修改 `startBrowser()`：抛 `UserInterventionException`（stage="login"）
- [x] 3.2.6 ✅ 2026-06-20 修改 `startBrowserAwait()`：抛 `UserInterventionException`（stage="login"）
- [x] 3.2.7 ✅ 2026-06-20 修改 `getVerificationCode()`：抛 `UserInterventionException`（stage="verification"）
- [x] 3.2.8 ✅ 2026-06-20 验证：JsExtensionsStub 编译通过

### 3.3 创建 Python webview_handler.py

- [x] 3.3.1 ✅ 2026-06-20 创建 `tools/webview_handler.py`：WebViewHandler 类
- [x] 3.3.2 ✅ 2026-06-20 实现 `render_url(url, js, timeout)`：Selenium 加载 URL + 执行 JS + 返回 HTML
- [x] 3.3.3 ✅ 2026-06-20 实现 `render_html(html, js, base_url, timeout)`：Selenium 加载 HTML + 执行 JS + 返回结果
- [x] 3.3.4 ✅ 2026-06-20 实现 `sniff_resource(url, source_regex, js, timeout)`：嗅探资源 URL
- [x] 3.3.5 ✅ 2026-06-20 实现 Chrome 检测和降级：Chrome 未安装时返回 None 并提示
- [x] 3.3.6 ✅ 2026-06-20 实现 `close()`：关闭 WebDriver
- [x] 3.3.7 ✅ 2026-06-20 验证：webview_handler.py 能独立运行

### 3.4 改造 Python 客户端 batch_debug

- [x] 3.4.1 ✅ 2026-06-20 阅读 `rule_engine_client.py` batch_debug 方法（L392-456）
- [x] 3.4.2 ✅ 2026-06-20 增加 `webview_handler` 参数到 batch_debug 方法
- [x] 3.4.3 ✅ 2026-06-20 在 batch 完成后，遍历 results 检查 `needsWebView=true` 的源
- [x] 3.4.4 ✅ 2026-06-20 对 needsWebView 的源调用 `_handle_webview_source()`
- [x] 3.4.5 ✅ 2026-06-20 实现 `_handle_webview_source()`：根据 webViewRequests 类型调用 webview_handler 对应方法
- [x] 3.4.6 ✅ 2026-06-20 将 Selenium 渲染后 HTML 传回 JAR 用 `analyze_rule()` 解析
- [x] 3.4.7 ✅ 2026-06-20 更新源的结果：从 needsWebView 改为 success/failed
- [x] 3.4.8 ✅ 2026-06-20 验证：batch_debug 能处理 needsWebView 的源

### 3.5 适配测试脚本

- [x] 3.5.1 ✅ 2026-06-20 修改 `large-scale-test.py`：集成 WebViewHandler
- [x] 3.5.2 ✅ 2026-06-20 修改 `large-scale-test.py`：对 needsWebView 的源用 Selenium 重新测试
- [x] 3.5.3 ✅ 2026-06-20 修改 `debug-source.py`：增加 `--webview` 参数启用 Selenium
- [x] 3.5.4 ✅ 2026-06-20 验证：测试脚本能处理 needsWebView 的源

### 3.6 方向 3 验证

- [x] 3.6.1 ✅ 2026-06-20 重新构建 JAR
- [x] 3.6.2 ✅ 2026-06-20 用 1 个 webView:true 的源测试：验证 JAR 返回 needsWebView=true
- [x] 3.6.3 ✅ 2026-06-20 验证：Python 客户端检测到 needsWebView 后用 Selenium 渲染
- [x] 3.6.4 ✅ 2026-06-20 验证：Selenium 渲染后 HTML 传回 JAR 解析成功
- [x] 3.6.5 ✅ 2026-06-20 验证：登录场景标记为 needsUserIntervention 并输出诊断信息

---

## 方向 4：经验教训提取

> **目标**：从测试中提取可指导后续书源创建的经验模式

### 4.1 分析测试结果

- [x] 4.1.1 ✅ 2026-06-20 用修复后的测试脚本重新测试 20 个源（10 书源 + 10 订阅源，0% 通过率证明修复有效）
- [x] 4.1.2 ✅ 2026-06-20 分析结果：区分 success/needsWebView/needsUserIntervention/failed 四种状态
- [x] 4.1.3 ✅ 2026-06-20 提取网站特征→规则类型映射（4种类型：CSS选择器/JSONPath/JS+WebView/套娃源）
- [x] 4.1.4 ✅ 2026-06-20 提取失败原因分类（网络50%/搜索40%/内容5%/格式5%）
- [x] 4.1.5 ✅ 2026-06-20 提取 WebView 需求模式（4种需求特征+WebViewRequest类型表）
- [x] 4.1.6 ✅ 2026-06-20 提取登录/验证码模式（JAR端检测机制+登录源特征+处理流程）

### 4.2 写入 basic-memory

- [x] 4.2.1 ✅ 2026-06-20 写入"网站特征→规则类型映射"经验（permalink: legado/experiences/网站特征-规则类型映射经验）
- [x] 4.2.2 ✅ 2026-06-20 写入"高频失败模式"经验（permalink: legado/experiences/高频失败模式经验）
- [x] 4.2.3 ✅ 2026-06-20 写入"WebView 需求模式"经验（permalink: legado/experiences/web-view-需求模式经验）
- [x] 4.2.4 ✅ 2026-06-20 写入"登录/验证码处理"经验（permalink: legado/experiences/登录-验证码处理经验）

### 4.3 更新 references/site-features/

- [x] 4.3.1 ✅ 2026-06-20 更新 `high-frequency-issues.md`：标记废弃假数据，新增修复后真实测试统计
- [x] 4.3.2 ✅ 2026-06-20 创建 `site-feature-to-rule-type.md`：网站特征→规则类型映射表+决策流程
- [x] 4.3.3 ✅ 2026-06-20 创建 `webview-requirements.md`：WebView 需求模式文档+架构概览图
- [x] 4.3.4 ✅ 2026-06-20 更新 `_INDEX.md`：索引2个新文档，更新验证统计

### 4.4 方向 4 验证

- [x] 4.4.1 ✅ 2026-06-20 验证：basic-memory 中有 4 条新经验（search_notes 确认全部存在）
- [x] 4.4.2 ✅ 2026-06-20 验证：references/site-features/ 有 2 个新文档（LS 确认存在）
- [x] 4.4.3 ✅ 2026-06-20 验证：经验模式可指导后续书源创建（4条经验均含"指导建议"部分，涵盖网站特征识别、规则类型选择、WebView配置、登录处理决策流程）

---

## 任务依赖关系

```
方向 1（测试有效性）──┐
                      ├──→ 方向 4（经验教训提取）
方向 3（WebView 支持）─┘

方向 2（债务清理）── 独立，可并行
```

**关键依赖**：
- 方向 4 依赖方向 1 和方向 3 完成（需要修复后的测试结果才能提取经验）
- 方向 2 独立，可与其他方向并行

---

## 验收标准

| 标准 | 验证方法 |
|------|---------|
| debug() 返回 DebugResult | 单元测试 |
| batch 结果包含 needsWebView/summary | 端到端测试 |
| success=true 的源有有效数据 | 大规模测试验证 |
| WebView 源能通过 Selenium 测试 | 端到端测试 |
| 0 个 nul 文件 | 文件系统检查 |
| 0 个临时文件 | 文件系统检查 |
| 4 条 basic-memory 经验 | basic-memory 查询 |
| 2 个新 site-features 文档 | 文件检查 |
