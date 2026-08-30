# 日志规范

> 基于 Legado 项目源码深度分析提取的项目特有日志约定。

---

## 三层日志体系

### 第一层：AppLog（核心日志，面向用户/调试）

- 文件：`constant/AppLog.kt`
- 单例对象，维护内存日志列表（最多 100 条）
- 方法：
  - `put(message, throwable?, toast?)` — 记录日志 + 写文件 + Debug Logcat
  - `putNotSave(message, throwable?)` — 仅内存 + Logcat
  - `putDebug(message, throwable?)` — 仅 `AppConfig.recordLog` 开启时记录
- `toast = true` 时直接 Toast 提示用户
- 日志可在 App 内通过 `AppLogDialog` 查看

```kotlin
AppLog.put("执行preUpdateJs规则失败 书源:${bookSource.bookSourceName}", it)
AppLog.put("保存成功", toast = true)
```

### 第二层：LogUtils（文件日志，面向开发）

- 文件：`utils/LogUtils.kt`
- 基于 `java.util.logging.Logger`，Logger 名 `"Legado"`
- 使用自定义 `AsyncFileHandler`（异步写入，避免 IO 阻塞）
- 日志文件存储在 `externalCacheDir/logs/`，自动清理 7 天前
- 日志级别由 `AppConfig.recordLog` 控制

### 第三层：DebugLog（纯 Logcat 调试日志）

- 文件：`utils/DebugLog.kt`
- 仅在 `BuildConfig.DEBUG` 时输出到 Logcat
- 提供 e/d/i/w 四个级别

## 辅助工具

- `printOnDebug()` 扩展函数（`LogUtils.kt`）：Throwable 扩展，仅 Debug 模式打印堆栈
- `Debug` 对象（`model/Debug.kt`）：书源调试专用日志，带时间戳，支持 UI 回调显示

## 日志标签约定

| 组件 | 标签 |
|------|------|
| AppLog 写入 LogUtils | `"AppLog"` |
| Debug 模式 Logcat | 调用类名 `stackTrace[3].className` |
| Debug 对象 | `"sourceDebug"` |
| LogUtils 文件日志 | `"Legado"` |

## 使用规则

1. **业务错误**：使用 `AppLog.put()`，重要错误加 `toast = true`
2. **调试信息**：使用 `AppLog.putDebug()` 或 `DebugLog`
3. **书源调试**：使用 `Debug.log()` 对象
4. **禁止**直接使用 `android.util.Log`（release 构建会被 ProGuard 移除）。例外：改造验证期允许临时使用 Log.d/Log.e 打验证日志（统一自定义 tag），验证通过后必须 Grep 确认 0 残留并移除（见 logging-during-refactoring.md 双轨制）
5. **禁止**使用 Timber（项目未引入）

## 模块 Tag 规范

为便于 ai_tests 按模块过滤日志，AppLog 定义了 7 个模块 Tag 常量：

| Tag 常量 | 值 | 覆盖模块 |
|---------|-----|---------|
| `TAG_WEB_BOOK` | `"WebBook"` | BookInfo / BookList / WebBook / BookContent / BookChapterList / SearchModel |
| `TAG_ANALYZE` | `"AnalyzeRule"` | AnalyzeByJSonPath / AnalyzeRule / AnalyzeUrl / AnalyzeByJSoup / AnalyzeByXPath / AnalyzeByRegex |
| `TAG_HTTP` | `"HttpHelper"` | HttpHelper / SSLHelper / OkHttpExceptionInterceptor / StrResponse / CookieStore |
| `TAG_WEB_VIEW` | `"BackstageWebView"` | BackstageWebView |
| `TAG_DATA` | `"DataLayer"` | data/ 下 DAO 及仓库类 |
| `TAG_RSS` | `"Rss"` | Rss / RssParserByRule / RssSearchModel / CheckRssSource |
| `TAG_CONTENT` | `"ContentProcess"` | ContentProcessor / BookHelp / BookContent |

ai_tests 可通过 `adb logcat -s WebBook:E AnalyzeRule:E` 精确过滤模块日志；文件日志可按 Tag grep 定位模块。

## putDebugWithTag 使用指南

`putDebugWithTag(tag, message, throwable?, level?)` 方法用于带模块 Tag 的调试日志：

- **recordLog 守卫**：仅在 `AppConfig.recordLog` 开启时记录，关闭时直接 return 零开销，不影响用户功能
- **tag 透传**：tag 透传给 `LogUtils.d` 和 `Log.e`，实现模块级过滤
- **写入文件 + 内存 + logcat(DEBUG)**：recordLog 开启时写入文件日志（带 tag）+ 内存 mLogs + logcat（仅 DEBUG）

### 何时用 putDebugWithTag vs put

| 场景 | 使用方法 | 理由 |
|------|---------|------|
| catch 块异常补全 | `putDebugWithTag` | recordLog 关闭时零开销 |
| 关键操作成功/失败日志 | `putDebugWithTag` (level=INFO/WARN) | recordLog 关闭时零开销 |
| 关键参数日志 | `putDebugWithTag` (level=INFO) | recordLog 关闭时零开销 |
| 用户可感知的错误 | `put` (toast=true) | 始终记录 + Toast 提示 |
| 重要业务错误 | `putError` | 始终记录 |

### 使用示例

```kotlin
// catch 块异常补全
} catch (e: Exception) {
    AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, "搜索失败: ${e.localizedMessage}", e)
}

// 关键操作成功日志
AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, "搜索开始 page=$page", level = AppLog.Level.INFO)

// 关键参数日志
AppLog.putDebugWithTag(AppLog.TAG_HTTP, "请求路径=/path/{id} code=${response.code()}", level = AppLog.Level.INFO)
```

## 三维度日志覆盖要求

核心模块日志覆盖需满足三个维度：

### 维度1：catch 块日志（异常捕获）

- 所有 catch 块必须有 `AppLog.putDebugWithTag` 调用
- **例外**：CancellationException 重新抛出的 catch 块不需要（异常会重新抛出由上层处理）
- **不重复记录**：已有 AppLog.put/putError/putWarn 调用的 catch 块不重复添加
- 日志内容：模块 Tag + 操作描述 + 异常对象

### 维度2：关键操作成功/失败日志（操作流程）

- 在关键操作的方法入口/成功出口/失败分支添加 `putDebugWithTag`（level=INFO/WARN）
- 覆盖操作：搜索/详情/目录/正文/发现页/规则解析/HTTP请求/RSS请求/内容处理
- 日志内容：模块 Tag + 操作名称 + 关键结果（结果数量/响应码/耗时）

### 维度3：关键参数日志（参数传递）

- 在关键参数传递点添加 `putDebugWithTag`（level=INFO）
- 覆盖参数：URL构建结果/规则解析结果/网络响应状态码/RSS源URL/解析结果
- 日志内容：模块 Tag + 参数名 + 参数值（脱敏后）

### 脱敏原则（铁律）

- URL 只保留路径模式（`/path/{id}`），禁止输出完整 URL
- cookie/token/key/secret 隐藏为 `***`
- 源名称不记录，只记源 ID 编号
- 日志消息格式：操作描述 + 关键参数（脱敏后）
