# 仿真端与真机差异追踪表

> 最后更新: 2026-06-23
> 仿真端版本: legado-jvm.jar (fatJar)
> 真机源码: app/src/main/java/io/legado/app/

## 已修复的 BUG

| BUG ID | 描述 | 状态 | 修复位置 |
|--------|------|------|---------|
| BUG-02 | 日志标签不一致 | ✅ 已修复 | Debug.kt / DebugLogger |
| BUG-03 | 编译冲突 (source/ruleData 命名) | ✅ 已修复 | JsExtensionsStub.kt |
| BUG-04 | IllegalStateException 异常类型 | ✅ 已修复 | JsExtensionsStub.kt (importScript) |
| BUG-05 | getSuffix 未对齐 analyzeUrl.type | ✅ 已修复 | JsExtensionsStub.kt (downloadFile) |
| BUG-06 | cookies 返回空 Map | ✅ 已修复 | JsoupResponseAdapter.cookies() |
| BUG-07 | aesEncodeToString 真机 bug 未对齐 | ✅ 已修复 | JsExtensionsStub.kt |

## 已处理的 GAP

| GAP ID | 描述 | 状态 | 处理方式 |
|--------|------|------|---------|
| GAP-05/06 | Rar/7z 解压不支持 | ✅ 降级处理 | 返回空/null + 降级日志，升级路径: commons-compress |
| GAP-07 | ajaxAll/ajaxTestAll 串行执行 | ✅ 并发优化 | CompletableFuture.supplyAsync + join |
| GAP-10 | replaceFont 多字节字符 | ✅ 降级处理 | toCharArray 简化实现，升级路径: 完整 Base64 解码 + 字体映射表 |
| GAP-22 | ruleDescription 逻辑对齐 | ✅ 已对齐 | RssSourceDebugger.kt 对齐真机 Debug.kt:155-171 |
| GAP-24 | 调试取消机制 | ✅ 已修复 | BookSourceDebugger.cancel() + checkCancelled() |
| GAP-25 | 校验模式 | ✅ 已修复 | validateRules() 静态规则校验 |
| GAP-36 | source/ruleData 并发覆盖 | ✅ 已修复 | ThreadLocal 隔离 |
| GAP-39 | RuleData 并发冲突 | ✅ 已修复 | 搜索/发现阶段独立 RuleData() |
| GAP-40 | 详情阶段 BookType 重置 | ✅ 已修复 | debugInfo 内联 removeAllBookType |
| GAP-44 | followRedirects | ✅ 正常工作 | URL 选项 followRedirects:false |
| GAP-67a | loginCheckJs 检测 | ✅ 已修复 | executeRequest() 成功/异常双路径检测 |
| GAP-67c | init 规则执行方式 | ✅ 已修复 | getElement + setContent(baseUrl) |
| GAP-67d | 正文格式化链 | ✅ 已修复 | HtmlFormatter.formatKeepImg + usehtml 占位符判断 |
| GAP-67e | 重定向检测 | ✅ 已修复 | checkRedirect() raw.priorResponse |

## 已知限制（仿真端无法实现，需真机或 Python 委托）

| 限制 | 描述 | 影响范围 | 升级路径 |
|------|------|---------|---------|
| WebView 渲染 | JVM 无法执行 WebView JS 渲染 | 需 JS 渲染的源 | Python 客户端 Selenium 委托 |
| UI 交互 | JVM 无法显示验证码/打开浏览器 | 需登录/验证码的源 | 用户在 Legado App 手动操作 |
| Rar/7z 解压 | JVM 未集成 commons-compress | 1-3% 源受影响 | 集成 commons-compress |
| replaceFont 多字节 | toStringArray 未抽取 | <1% 源受影响 | 完整 Base64 解码 + 字体映射表 |
| Cookie 持久化 | 内存存储，重启丢失 | 所有源 | 接入 SQLite 或文件系统 |
| openVideoPlayer | JVM 无视频播放能力 | 视频源 | 抛 UnsupportedOperationException |

## 依赖版本一致性

| 依赖 | 仿真端版本 | 真机版本 | 一致性 |
|------|-----------|---------|--------|
| okhttp | 5.3.2 | 5.3.2 | ✅ |
| rhino | 1.8.1 | 1.8.1 | ✅ |
| jsoup | 1.16.2 | 1.16.2 | ✅ |
| JsoupXpath | 2.5.3 | 2.5.3 | ✅ |
| json-path | 2.10.0 | 2.10.0 | ✅ |
| gson | 2.13.2 | 2.13.2 | ✅ |
| hutool-crypto | 5.8.22 | 5.8.22 | ✅ |
| commons-text | 1.13.1 | 1.13.1 | ✅ |
| quick-transfer-core | 0.2.17 | 0.2.17 | ✅ |
| kotlinx-coroutines | 1.10.2 | 1.10.2 | ✅ |

## 架构差异

| 项目 | 仿真端 | 真机 | 说明 |
|------|--------|------|------|
| 协程桥接 | runBlocking | launch/async | 7处 runBlocking 保留并添加注释（接口桥接/JS调用约束） |
| Base64 | java.util.Base64 | android.util.Base64 | mapBase64Flags 统一映射 flags |
| Cookie | CookieStoreStub (内存) | Room + CookieManager | 降级为内存存储 |
| 缓存 | CacheManagerStub (内存) | AppCacheManager (持久) | 降级为内存存储 |
| 日志 | DebugLogger (stdout JSON) | Debug + AppLog | 流式 JSON 协议 |
| 安卓依赖 | 完全剥离 | Android 框架 | 无 `import android.` 语句 |
