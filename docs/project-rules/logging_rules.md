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
4. **禁止**直接使用 `android.util.Log`（release 构建会被 ProGuard 移除）
5. **禁止**使用 Timber（项目未引入）
