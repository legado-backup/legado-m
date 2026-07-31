# 代码进化机制详情

> 本文档从 SKILL.md 拆分，包含代码进化机制完整说明。

---

## 核心问题

Phase 5 只反哺文档是不够的。当新源需要 JsExtensionsStub 不支持的函数，或 AnalyzeRule 解析结果与 Legado 不一致时，必须更新代码并重建 JAR。

---

## 进化触发条件

（在 Phase 3/4 中识别）

| 触发场景 | 识别方式 | 示例 |
|---------|---------|------|
| 新命令需求 | Phase 4 源码分析发现新处理流程 | 需要 `analyzeUrl` 命令 |
| Python 客户端缺失方法 | 新 JAR 命令没有对应 Python 方法 | JAR 新增 `handleRedirect` 但客户端无此方法 |

---

## 进化流程

```
1. 记录进化需求 → references/ 对应文档
2. 更新 Kotlin 源码 → tools/legado-jvm/src/main/kotlin/io/legado/
3. 重建 JAR → cd tools/legado-jvm && gradlew.bat fatJar（前置条件：JDK 17+ 已安装，Gradle wrapper 已配置）
4. JAR 输出位置 → legado-jvm/build/libs/legado-jvm.jar
5. 更新 Python 客户端 → tools/rule_engine_client.py
6. 更新共享模块 → tools/jvm_helpers.py（如需新评估逻辑）
7. 重新验证失败的源
```

---

## Kotlin 源码结构

| 文件 | 职责 | 何时更新 |
|------|------|---------|
| `JsExtensionsStub.kt` | JS 扩展函数模拟 | 遇到不支持的 `java.xxx()` 函数时 |
| `AnalyzeRule.kt` | 规则解析引擎 | 规则解析结果与 Legado 不一致时 |
| `AnalyzeByJSoup.kt` | JSoup CSS 解析 | CSS 选择器行为与 Legado 不一致时 |
| `RuleAnalyzer.kt` | 规则组合逻辑（&&/\|\|/%%） | 组合逻辑解析与 Legado 不一致时 |
| `AnalyzeUrl.kt` | URL 解析三步流水线（analyzeJs→replaceKeyPageJs→analyzeUrl） | URL 解析行为与 Legado 不一致时 |
| `BookSourceDebugger.kt` | 端到端书源调试器（search→detail→toc→content） | 书源调试链路行为与 Legado 不一致时 |
| `RssSourceDebugger.kt` | 端到端订阅源调试器（sort→content） | 订阅源调试链路行为与 Legado 不一致时 |
| `DebugLogger.kt` | 真机级调试日志输出器 | 日志格式与真机不一致时 |
| `BookSource.kt` / `RssSource.kt` | 抽取后的 BookSource/RssSource 上下文 | 源字段解析与 Legado 不一致时 |
| `MockBook.kt` | 内存版 Book/BookChapter 上下文 | 书籍上下文行为与 Legado 不一致时 |
| `MockCookieStore.kt` | 内存版 CookieStore（二级域名） | Cookie 管理行为与 Legado 不一致时 |
| `MockCacheManager.kt` | 内存版 CacheManager | 缓存行为与 Legado 不一致时 |
| `StrResponse.kt` | 真机 StrResponse 简化版 | 响应体处理与 Legado 不一致时 |

---

## JsExtensionsStub 扩展检查清单

（更新时必检）

- [ ] 新函数是否在 Legado `JsExtensions.kt` 中有对应实现？
- [ ] 新函数的参数签名是否与 Legado 一致？
- [ ] 新函数的返回值类型是否与 Legado 一致？
- [ ] 新函数是否需要网络请求（ajax）？如是，Cookie/Header 差异是否已标注？
- [ ] 新函数是否需要 Android API？如是，标记需真机验证。

