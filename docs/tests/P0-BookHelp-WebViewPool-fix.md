# P0 BookHelp 互斥失效 + WebViewPool 池化修复 测试用例

> P0 阶段稳定性修复续篇：BookHelp saveImage finally 块顺序修复 + BackstageWebView isActiveWebView 引用相等检查修复

## 功能概述

| 任务 | 优化点 | 修改文件 |
|------|--------|---------|
| P0-9 | BookHelp 互斥失效修复（finally 块顺序：先 unlock 后 remove） | BookHelp.kt |
| P0-10 | WebViewPool 池化修复（isActiveWebView 引用相等检查 `===`） | BackstageWebView.kt |

### P0-9 BookHelp 互斥失效修复

**问题根因**：原 `BookHelp.saveImage` 的 finally 块若先 `downloadImages.remove(src)` 再 `mutex.unlock()`，会引入竞态窗口——另一线程在 remove 之后、unlock 之前进入 `synchronized(this) { downloadImages.getOrPut(src) { Mutex() } }`，发现 map 中无 src，新建一个新 Mutex 并立即获取，与当前仍持锁的旧 Mutex 形成"两个 Mutex 同时持锁"的假象，导致同一图片被并发下载两次（互斥失效）。

**修复方案**：调整 finally 块顺序为 `mutex.unlock()` → `downloadImages.remove(src)`，确保 unlock 后再 remove，让后续线程在 getOrPut 时仍能拿到同一把 Mutex（互斥正确）。

**实现位置**：`app/src/main/java/io/legado/app/help/book/BookHelp.kt:260-263`

```kotlin
} finally {
    mutex.unlock()
    downloadImages.remove(src)
}
```

### P0-10 WebViewPool 池化修复（isActiveWebView 引用相等）

**问题根因**：原 `BackstageWebView` 在 `EvalJsRunnable.run()` 中收到 evaluateJavascript 回调后，未校验当前 WebView 是否仍是活跃实例。当 WebView 被 WebViewPool 回收并复用给其他业务后，旧业务的回调可能误用新业务的 WebView 实例，导致 JS 结果串扰。

**修复方案**：新增 `isActiveWebView(webView)` 方法，使用 `===`（引用相等）校验回调中的 WebView 与当前 `pooledWebView.realWebView` 是否同一实例；同时引入 `closed` 标志位，destroy 后立即拒绝所有回调。

**实现位置**：`app/src/main/java/io/legado/app/help/http/BackstageWebView.kt:178-189`

```kotlin
private fun destroy() {
    closed = true
    callback = null
    pooledWebView?.let { WebViewPool.release(it) }
    pooledWebView = null
}

private fun isActiveWebView(webView: WebView? = null): Boolean {
    if (closed) return false
    val pooled = pooledWebView ?: return false
    return webView == null || pooled.realWebView === webView
}
```

**对比延伸版本**：阅读Archive 提供 `closed` 标志 + `isActiveWebView` 范式；本项目在此基础上强化为 `===` 引用相等检查，更严格。

## 测试环境

- 设备：JVM 单元测试（Level 1，本任务无）+ Android 6.0+ 真机（Level 2/3）
- 构建版本：appDebug
- 测试框架：真机操作 + 日志观察 + 内存分析

> **未新增单元测试的理由**：
> - `BookHelp` 是 `object` 依赖 `appCtx`/`appDb`/`Mutex`，纯 JVM 无法实例化
> - `BackstageWebView` 依赖 `WebView`/`Handler`/`Coroutine`，纯 JVM 无法实例化
> - finally 块顺序的正确性属于"顺序敏感"代码，需通过真机并发场景验证
> - `===` 引用相等的正确性属于 Kotlin 语言保证，代码审查 + 真机端到端验证更直接

---

## 一、BookHelp finally 块顺序（Level 2 真机验证）

### TC-P0-9-01：单图片下载正常完成（正常用例）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 导入一本含图片章节的书籍（漫画/插画小说）

**测试步骤**：
1. 打开书籍，进入含图片的章节
2. 观察图片正常加载
3. 检查日志无异常

**预期结果**：
- ✅ 图片正常显示
- ✅ `saveImage` 正常完成：`mutex.lock()` → 下载 → `mutex.unlock()` → `downloadImages.remove(src)`
- ✅ 无 `IllegalMonitorStateException`（unlock 未持锁）
- ✅ 无图片损坏

### TC-P0-9-02：并发下载同 src 图片（核心场景）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 一本漫画书，预下载开启，多章节含同一封面图

**测试步骤**：
1. 开启预下载（设置 → 预下载 5 章）
2. 翻到含共享封面图的章节
3. 观察预下载过程
4. 检查同一 src 是否被下载多次

**预期结果**：
- ✅ 同一 src 的图片仅下载一次（互斥正确）
- ✅ 第二个线程在 `getOrPut` 时拿到同一 Mutex，阻塞等待
- ✅ 第一个线程 unlock 后第二个线程进入临界区，但 `isImageExist` 已为 true，立即返回
- ✅ 无重复下载日志

### TC-P0-9-03：图片下载异常时互斥正确（异常用例）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 配置一个图片 URL 不可达的书源

**测试步骤**：
1. 阅读含失败图片的章节
2. 触发图片下载失败
3. 立即再次进入该章节（触发重试）
4. 观察互斥行为

**预期结果**：
- ✅ 第一次下载抛异常，进入 catch 块记录日志
- ✅ finally 块执行：先 `mutex.unlock()`，后 `downloadImages.remove(src)`
- ✅ 第二次进入时 `getOrPut` 返回新 Mutex（已被 remove），正常获取锁
- ✅ 无死锁、无 `IllegalMonitorStateException`

### TC-P0-9-04：快速切换章节时互斥不失效（边界用例）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 一本漫画书，多章节含图片

**测试步骤**：
1. 快速连续切换 5 个含图片的章节
2. 观察图片加载行为

**预期结果**：
- ✅ 每个章节的图片正确加载，无串图
- ✅ 同一 src 的并发请求被互斥保护
- ✅ 无 `ConcurrentModificationException`

---

## 二、isActiveWebView 引用相等检查（Level 2 真机验证）

### TC-P0-10-01：单次 JS 执行回调正常（正常用例）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 配置一个使用 WebView 加载的书源（含 JS 规则）

**测试步骤**：
1. 搜索该书源
2. 触发 WebView 加载 + JS 执行
3. 观察 JS 结果回调

**预期结果**：
- ✅ `EvalJsRunnable.run()` 中 `mWebView.get()` 返回当前 WebView
- ✅ `isActiveWebView(mWebView.get())` 返回 true（`pooledWebView.realWebView === webView`）
- ✅ `handleResult(it)` 正常处理结果
- ✅ 搜索结果正确返回

### TC-P0-10-02：destroy 后旧回调被拒绝（核心修复点）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 一个 WebView 加载较慢的书源（JS 执行需 2+ 秒）

**测试步骤**：
1. 触发书源搜索（启动 WebView + JS）
2. 在 JS 执行过程中快速返回（触发 `destroy()`）
3. 等待 JS 回调到达
4. 观察回调处理行为

**预期结果**：
- ✅ `destroy()` 设置 `closed = true`，`pooledWebView = null`
- ✅ JS 回调到达时 `isActiveWebView` 检查 `closed` 为 true，立即返回 false
- ✅ **不调用** `handleResult`，旧结果被丢弃
- ✅ 无 NPE、无 IllegalStateException
- ✅ 无"已销毁的 WebView 接收回调"日志

### TC-P0-10-03：WebView 复用后旧回调不串扰（核心修复点）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 两个都使用 WebView 的书源 A 和 B

**测试步骤**：
1. 触发书源 A 搜索（WebView 实例 #1）
2. 立即取消并触发书源 B 搜索（WebViewPool 可能复用实例 #1）
3. 等待两个 JS 回调都到达
4. 观察回调路由

**预期结果**：
- ✅ 实例 #1 在 A 业务 destroy 后被 release 回池
- ✅ B 业务 acquire 时复用实例 #1（`pooledWebView.realWebView` 是同一对象）
- ✅ A 的旧回调到达时，`isActiveWebView` 中 `pooledWebView.realWebView === webView` 仍为 true（因为是同一对象）
- ✅ 但 `pooledWebView` 此时已是 B 业务的包装对象，A 的 callback 已被置 null
- ✅ A 的旧 callback 为 null，不执行 handleResult
- ✅ B 的回调正常路由到 B 的 callback
- ✅ 无结果串扰

### TC-P0-10-04：closed 标志位优先级（边界用例）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：同 TC-P0-10-02

**测试步骤**：
1. 触发书源搜索
2. destroy() 后，再次触发新搜索（同一 BackstageWebView 实例）
3. 观察新搜索的回调

**预期结果**：
- ✅ `closed` 标志在 destroy 时置 true
- ✅ 新搜索前会重置 `closed`（或新建 BackstageWebView 实例）
- ✅ 新搜索的回调正常处理
- ✅ 旧搜索的回调被 closed 拒绝

---

## 三、端到端集成（Level 3 真机验证）

### TC-P0-9-10-05：漫画书长跑阅读（端到端）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 导入一本 50+ 章的漫画书

**测试步骤**：
1. 阅读漫画书 30 分钟，频繁切换章节
2. 开启预下载 5 章
3. 检查图片加载正确性、内存占用、是否崩溃

**预期结果**：
- ✅ 所有图片正确加载，无串图、无重复下载
- ✅ `downloadImages` map 大小稳定（finally remove 生效）
- ✅ 无内存泄漏（图片下载 Mutex 不累积）
- ✅ 无 ANR、无崩溃

### TC-P0-9-10-06：多书源并发搜索（端到端）⏳ 待验证

**关联源码**：WebViewPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 安装新构建 APK
- 导入 10+ 个使用 WebView 的书源

**测试步骤**：
1. 执行多书源并发搜索
2. 在搜索过程中快速返回
3. 重新触发搜索
4. 观察结果正确性

**预期结果**：
- ✅ 每次搜索的 JS 结果正确路由到对应 callback
- ✅ 旧搜索的回调被 `isActiveWebView` 拒绝
- ✅ 无结果串扰、无 NPE
- ✅ WebViewPool 正常复用，无内存泄漏

---

## 测试统计

| 级别 | 用例数 | 通过 | 待验证 |
|------|--------|------|--------|
| Level 2（真机验证 - BookHelp） | 4 | 0 | 4 ⏳ |
| Level 2（真机验证 - WebViewPool） | 4 | 0 | 4 ⏳ |
| Level 3（端到端验证） | 2 | 0 | 2 ⏳ |
| **合计** | **10** | **0** | **10** |

## 已知局限与升级路径

| 局限 | 说明 | 升级路径 |
|------|------|---------|
| 未直接测 BookHelp.saveImage | 依赖 `appCtx`/`appDb`/`Mutex`，纯 JVM 无法实例化 | 引入 Robolectric 测真实 Mutex + finally 顺序 |
| 未直接测 BackstageWebView.isActiveWebView | 依赖 `WebView`/`Handler`/`Coroutine`，纯 JVM 无法实例化 | 引入 Robolectric 测真实 WebView 引用相等 |
| finally 顺序正确性需真机验证 | 顺序敏感代码，需并发场景触发 | 真机 Level 2/3 验证（TC-P0-9-02 核心场景） |
| `===` 引用相等由 Kotlin 语言保证 | 代码审查已确认 | 真机端到端验证（TC-P0-10-03 核心修复点） |
| 真机验证未执行 | Level 2/3 用例待用户在真机上验证 | 见端到端集成章节 |
