# 高频问题模式与修复方案

> 基于 7 个真实源端到端验证 + 300 个源大规模抽样测试积累的高频问题模式。

## 问题 1：相对 URL 未拼接 baseUrl

**影响范围**：3/7 源（51cg/acgfta/mjv006）
**严重级别**：P0（导致 sort/content 阶段全部失败）
**根因**：RSS 源的 sortUrl 或文章 URL 为相对路径（如 `/list/1.html`），JVM 仿真端未自动拼接 bookSourceUrl

**特征识别**：
- 错误信息包含 `UnknownHostException` 或 `scheme` 或 `URL缺`
- 源 JSON 中 sortUrl 字段以 `/` 开头（非 `http`）

**修复方案**（已在 RssSourceDebugger.kt 修复）：
```kotlin
// 9.4.1: 相对URL自动拼接baseUrl
if (!currentUrl.startsWith("http", ignoreCase = true) && mockSource.bookSourceUrl.isNotBlank()) {
    val base = mockSource.bookSourceUrl.trimEnd('/')
    currentUrl = when {
        currentUrl.startsWith("/") -> base + currentUrl
        else -> "$base/$currentUrl"
    }
}
```

**验证结果**：3 个源全部修复成功

---

## 问题 2：String→List 类型兼容

**影响范围**：1/7 源（611371056 小黄书视频）
**严重级别**：P0（导致 content 阶段 ClassCastException）
**根因**：AnalyzeRule.getElements 期望 List 返回值，但规则返回 String

**特征识别**：
- 错误信息包含 `ClassCastException` 或 `String cannot be cast to List`
- 规则返回单个元素而非数组

**修复方案**（已在 AnalyzeRule.kt 修复）：
```kotlin
// 9.4.1: 类型兼容处理 — 如果规则返回String而非List，包装为单元素List
return when (it) {
    is List<*> -> it.filterNotNull() as List<Any>
    is String -> if (it.isNotBlank()) listOf(it) else ArrayList()
    else -> listOf(it)
}
```

**验证结果**：1 个源修复成功

---

## 问题 3：CF 盾 JS 挑战拦截

**影响范围**：1/7 源（1080zyk 优质资源）
**严重级别**：预期不可绕过（JVM 无法执行 JS challenge）
**根因**：Cloudflare 返回 JS challenge 页面，JVM 仿真端无法执行 JS

**特征识别**：
- HTTP 响应包含 `challenge` 或 `cf-` 或 `__cf_bm`
- 响应状态码 403/503

**处理方案**：标记为 `unverifiable`，输出用户操作建议：
```
[需用户介入] CF 盾检测到，JVM 无法模拟 JS challenge
建议：在手机端 Legado App 中使用 webView 验证，或手动获取 Cookie 后导入
```

**验证结果**：符合预期，标记为需用户介入

---

## 问题 4：sortUrl 规则解析为 null

**影响范围**：1/7 源（jfg 机房哥视频）
**严重级别**：P1（规则本身缺陷，非仿真端问题）
**根因**：源 JSON 中 sortUrl 字段格式错误或规则未正确生成 URL

**特征识别**：
- sort 阶段返回空列表
- sortUrl 字段为空或格式不符合 `分类名::URL\n分类名2::URL2`

**处理方案**：通过 `debug-source.py` 修正规则：
- 检查 sortUrl 格式是否正确
- 确保 URL 模板中的 `{{key}}` 占位符有对应映射

**验证结果**：未改善（规则需重写，非仿真端问题）

---

## 问题 5：网站不可访问/超时

**影响范围**：1/7 源（test-debug 书源）
**严重级别**：环境问题（非代码问题）
**根因**：目标网站已关闭或网络不可达

**特征识别**：
- 错误信息包含 `timeout` 或 `404` 或 `不可访问`
- HTTP 状态码 404 或连接超时

**处理方案**：标记为 `unverifiable`，建议用户更换源或检查网络

**验证结果**：符合预期，环境问题

---

## 修复优先级矩阵

| 问题类型 | 影响范围 | 修复成本 | 优先级 |
|---------|---------|---------|--------|
| 相对 URL 拼接 | 3/7 | 低（已修复）| ✅ 已完成 |
| String→List 兼容 | 1/7 | 低（已修复）| ✅ 已完成 |
| CF 盾拦截 | 1/7 | 高（需 webView）| 🟡 需用户介入 |
| sortUrl 规则缺陷 | 1/7 | 中（需重写规则）| 📝 待修复 |
| 网站不可访问 | 1/7 | N/A | ⚠️ 环境问题 |
| OkHttp 系统代理超时 | 阶段五 | 低（已修复）| ✅ 已完成 |
| extractJsRule 丢失 JS 标签 | 阶段五 | 低（已修复）| ✅ 已完成 |

---

## 问题 6：OkHttp 系统代理导致 Connect timed out

**影响范围**：阶段五真实源测试（所有 HTTP 请求均受影响）
**严重级别**：P0（导致所有网络请求 31 秒超时）
**根因**：OkHttp 默认使用 `ProxySelector.getDefault()` 读取 Windows 系统代理设置。当 Windows 系统代理配置了不可用的代理服务器（如 `127.0.0.1:31181`）时，所有请求尝试通过不可用代理连接导致超时。

**特征识别**：
- 错误信息包含 `Connect timed out` 或 `connect timed out`
- 独立 Java OkHttp 测试能成功连接，但 RuleEngineServer 中的 OkHttp 失败
- Java 系统代理属性（`http.proxyHost` 等）全部为 null
- Windows 注册表 `ProxyEnable=1, ProxyServer=https=http://127.0.0.1:PORT`

**修复方案**（已在 HttpHelper.kt 修复）：
```kotlin
// 禁用系统代理，直接连接
OkHttpClient.Builder()
    .dns(ipv4PreferredDns)
    .proxySelector(java.net.ProxySelector.of(null))  // 关键修复
    .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
    // ...
```

**验证结果**：acgfta 源从 31.20s 超时变为 6.80s 成功

---

## 问题 7：extractJsRule 丢失 `<js></js>` 标签导致正文为空

**影响范围**：阶段五 acgfta 源（正文长度从 0 到 2396 字符）
**严重级别**：P0（导致正文解析返回空字符串）
**根因**：`extractJsRule` 方法提取了 JS 代码但去掉了 `<js></js>` 标签。`AnalyzeRule.getString` 方法需要 `<js></js>` 标签来识别 JS 规则，去掉标签后 HTML 模板被当作 CSS 选择器解析，导致 `SelectorParseException`。

**特征识别**：
- 列表页获取成功，正文页 HTML 获取成功，但正文长度为 0
- 日志中出现 `SelectorParseException`（HTML 模板被当作 CSS 选择器）
- ruleContent 包含 `<js>...</js>` 标签 + HTML 模板

**修复方案**（已在 RssSourceDebugger.kt 修复）：
```kotlin
// 保留 <js></js> 标签，让 getString 能识别为 JS 规则
private fun extractJsRule(rule: String?): String? {
    if (rule.isNullOrBlank()) return rule
    val jsPattern = Regex("<js>([\\s\\S]*?)</js>", RegexOption.IGNORE_CASE)
    val match = jsPattern.find(rule)
    return if (match != null) {
        match.value  // 保留 <js></js> 标签（之前是 match.groupValues[1] 丢失了标签）
    } else {
        rule
    }
}
```

**验证结果**：acgfta 正文长度从 0 提升到 2396 字符

---

## ~~大规模测试统计（阶段七）~~ [已废弃 - 假成功]

> **⚠️ 以下数据已废弃**：阶段七的"100%通过率"是假象，根因是 debug() 方法用 try-catch 吞掉所有异常，batch 模式 `success = !抛异常` 永远为 true。修复后（2026-06-20）重新测试，真实通过率为 0%。

~~**抽样规模**：26,583 个源中随机抽样 300 个（200 书源 + 100 订阅源）~~
~~**测试结果**：288/300 源完成测试，全部成功~~
~~- 书源通过率：200/200 = 100%（> 70% 验收标准 ✅）~~
~~- 订阅源通过率：88/88 = 100%（> 75% 验收标准 ✅）~~
~~- 12 个订阅源因超时未完成（不影响验收）~~

---

## 修复后真实测试统计（2026-06-20）

> **修复内容**：debug() 返回 DebugResult，batch 使用 DebugResult 判断成功/失败，不再"假成功"

**抽样规模**：20 个源（10 书源 + 10 订阅源）
**测试结果**：0/20 成功（0% 通过率）
- 书源通过率：0/10 = 0%
- 订阅源通过率：0/10 = 0%
- 耗时：7.2 秒（平均 0.36 秒/源，网络请求快速失败）

**失败原因分类**：

| errorStage | 数量 | 占比 | 说明 |
|-----------|------|------|------|
| unknown | 10 | 50% | 网络连接失败（网站已失效） |
| search/sort | 8 | 40% | 搜索/发现阶段失败（规则不匹配或源格式不标准） |
| content | 1 | 5% | 内容阶段失败（套娃源 legado://import） |
| sort | 1 | 5% | 源格式不标准（元数据非标准源 JSON） |

**关键发现**：
1. 修复前 100% 通过率是假象，修复后 0% 通过率是真实结果
2. 社区旧源失效率高（50% 网络连接失败）
3. errorStage 字段能有效区分失败阶段
4. needsWebView/needsUserIntervention 未检测到（因网络先失败）
