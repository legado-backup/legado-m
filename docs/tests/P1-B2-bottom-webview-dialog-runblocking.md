# P1-B2 BottomWebViewDialog runBlocking 优化 测试用例

> Task 20 / B2：优化 `BottomWebViewDialog.kt` 的 `getModifiedContentWithJs`，从 suspend 协程化调用改为同步 OkHttp 调用，省去协程调度开销

## 功能概述

| 子功能 | 说明 |
|--------|------|
| 同步执行优化 | `getModifiedContentWithJs` 从 `suspend` 改为普通同步函数，内部从 `okHttpClient.newCallResponse { ... }`（suspend）改为 `okHttpClient.newCall(request).execute()`（同步） |
| 307/308 兜底保留 | 与 `newCallResponse` 行为一致，OkHttp 自动重定向未跟随时手动保持 method+body 跟随 |
| runBlocking 保持不变 | `shouldInterceptRequest` 必须 synchronous（WebView API 限制），`runBlocking(IO) { ... }` 不可避免，但 `execute()` 直接在 IO 线程执行，省去协程调度 |
| Cookie 同步 | `Set-Cookie` 响应头正常保存到 `android.webkit.CookieManager` |
| JS 注入 | `preloadJs` 通过 `JS_URL` 注入到 `<head>` 标签后 |

**问题根因**：原 `BottomWebViewDialog.kt:819-821` 在 `shouldInterceptRequest`（WebView 主线程同步回调）中调用 `runBlocking(IO) { suspend getModifiedContentWithJs(...) }`，内部走 `okHttpClient.newCallResponse`（suspend 协程化封装：`suspendCancellableCoroutine + enqueue + Callback.resume`），引入不必要的协程调度开销（5 次线程切换/协程调度）。优化后仅 1 次线程切换（主线程 → IO 线程），减少主线程阻塞时间。

**实现文件**：
- `app/src/main/java/io/legado/app/ui/widget/dialog/BottomWebViewDialog.kt`（`getModifiedContentWithJs` 从 suspend 改为同步函数 + 移除 `newCallResponse` import）

**对比延伸版本**：所有延伸版本均用 suspend 协程化调用，本项目独立优化。

## 测试环境

- 设备：JVM 单元测试（Level 1，本任务无）+ Android 6.0+ 真机（Level 2/3）
- 构建版本：appDebug
- 测试框架：真机操作 + 日志观察

> **未新增单元测试的理由**：
> - `BottomWebViewDialog` 继承 `BottomSheetDialogFragment`，依赖 `FragmentManager`/`appCtx`（Android 框架），纯 JVM 无法实例化
> - `getModifiedContentWithJs` 依赖 `android.webkit.CookieManager`（Android 框架）+ `okHttpClient`（依赖 `AppConfig`/`Cronet` 初始化），纯 JVM 无法运行
> - 核心价值在"协程调度开销减少"，需真机 Level 2/3 验证 WebView 行为
> - 同步 `execute()` 与 suspend `await()` 的等价性已由 OkHttp 官方保证（`execute()` 是 `enqueue()` 的同步版本）

---

## 一、基本功能验证（Level 2 真机验证）

### TC-P1-B2-01：RSS 阅读正常加载（正常用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 导入一个订阅源（含 RSS 文章页）
- 订阅源 `ruleNextPage` 不为空（触发 `preloadJs` 注入流程）

**测试步骤**：
1. 进入订阅源列表
2. 选择订阅源，进入 RSS 文章列表
3. 点击一篇文章进入阅读

**预期结果**：
- ✅ RSS 文章列表正常加载
- ✅ 文章内容正常显示
- ✅ `shouldInterceptRequest` 拦截主资源请求，调用 `getModifiedContentWithJs`
- ✅ 同步 `execute()` 返回响应，`preloadJs` 注入到 `<head>` 后
- ✅ 全程无 ANR，WebView 正常渲染

### TC-P1-B2-02：源编辑预览正常加载（正常用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 导入一个书源

**测试步骤**：
1. 进入书源列表
2. 长按书源，选择"编辑"
3. 在编辑页面点击"预览"按钮（触发 `BottomWebViewDialog`）

**预期结果**：
- ✅ `BottomWebViewDialog` 正常弹出
- ✅ WebView 正常加载书源 URL
- ✅ `preloadJs` 注入成功
- ✅ 同步 `execute()` 返回响应，HTML 内容正常显示
- ✅ 全程无 ANR

### TC-P1-B2-03：POST 请求不拦截（边界用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 书源 URL 使用 POST 方法

**测试步骤**：
1. 触发 `BottomWebViewDialog` 加载 POST 请求 URL
2. 观察 `shouldInterceptRequest` 行为

**预期结果**：
- ✅ `request.method == "POST"` 时，`shouldInterceptRequest` 直接返回 `super.shouldInterceptRequest(view, request)`
- ✅ **不调用** `getModifiedContentWithJs`（原代码 L816 判断 `request.method == "POST"` 跳过）
- ✅ WebView 走默认加载流程

### TC-P1-B2-04：data: URL 不拦截（边界用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK

**测试步骤**：
1. 触发 `BottomWebViewDialog` 加载 `data:text/html;...` URL
2. 观察 `shouldInterceptRequest` 行为

**预期结果**：
- ✅ `url.startsWith("data:text/html;")` 时，直接返回 `super.shouldInterceptRequest(view, request)`
- ✅ **不调用** `getModifiedContentWithJs`（原代码 L816 判断跳过）
- ✅ WebView 走默认加载流程

---

## 二、307/308 重定向兜底（Level 2 真机验证）

### TC-P1-B2-05：307 重定向跟随（正常用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 找一个会返回 307 重定向的 URL（如某些 API 端点）

**测试步骤**：
1. 触发 `BottomWebViewDialog` 加载该 URL
2. 观察重定向行为

**预期结果**：
- ✅ 同步 `execute()` 返回 307 响应
- ✅ 检测 `res.code == 307`，读取 `Location` header
- ✅ 构建重定向请求（保持 method+headers），再次 `execute()`
- ✅ 最终返回重定向后的响应内容
- ✅ WebView 正常渲染

### TC-P1-B2-06：308 重定向跟随（正常用例）⏳ 待验证

**前置条件**：同 TC-P1-B2-05，但 URL 返回 308

**测试步骤**：同 TC-P1-B2-05

**预期结果**：
- ✅ 同步 `execute()` 返回 308 响应
- ✅ 检测 `res.code == 308`，读取 `Location` header
- ✅ 构建重定向请求，再次 `execute()`
- ✅ 最终返回重定向后的响应内容

---

## 三、Cookie 同步与异常处理（Level 2 真机验证）

### TC-P1-B2-07：Set-Cookie 正确保存（正常用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 订阅源 URL 响应包含 `Set-Cookie` 头

**测试步骤**：
1. 触发 `BottomWebViewDialog` 加载该 URL
2. 观察响应头处理

**预期结果**：
- ✅ 同步 `execute()` 返回响应
- ✅ `res.headers("Set-Cookie")` 遍历每个 `setCookie`
- ✅ 调用 `webCookieManager.setCookie(url, setCookie)` 保存到 `android.webkit.CookieManager`
- ✅ 后续 WebView 请求自动携带 Cookie

### TC-P1-B2-08：请求异常返回 null（异常用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 模拟网络异常（如断网或 URL 不可达）

**测试步骤**：
1. 断开网络
2. 触发 `BottomWebViewDialog` 加载一个不可达 URL
3. 观察 `getModifiedContentWithJs` 行为

**预期结果**：
- ✅ 同步 `execute()` 抛出 `IOException`
- ✅ `catch (_: Exception)` 捕获异常，返回 `null`
- ✅ `runBlocking(IO) { getModifiedContentWithJs(...) ?: super.shouldInterceptRequest(view, request) }` 走 `super` 分支
- ✅ WebView 走默认加载流程（显示错误页或空白页）
- ✅ **不崩溃**

---

## 四、端到端集成（Level 3 真机验证）

### TC-P1-B2-09：RSS 阅读 + 源编辑预览全流程（端到端用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 导入 3+ 个订阅源 + 3+ 个书源

**测试步骤**：
1. 进入订阅源 A，浏览文章列表，点击文章阅读
2. 返回，切换订阅源 B，浏览文章
3. 进入书源 A 编辑页面，点击预览
4. 返回，切换书源 B 编辑页面，点击预览
5. 再次进入订阅源 A 浏览文章

**预期结果**：
- ✅ 步骤 1-2：RSS 文章正常加载，`preloadJs` 注入成功
- ✅ 步骤 3-4：书源预览正常加载
- ✅ 步骤 5：再次加载订阅源 A，行为一致
- ✅ 全程无 ANR，UI 流畅度较原实现改善
- ✅ 无内存泄漏（多次打开/关闭 `BottomWebViewDialog`）

### TC-P1-B2-10：协程调度开销减少（性能验证）⏳ 待验证

**前置条件**：
- 启用 Systrace 或 CPU Profiler
- 导入一个响应较慢的订阅源（如海外站点）

**测试步骤**：
1. 连续触发 20 次 `BottomWebViewDialog` 加载（如快速切换文章）
2. 对比原实现与新实现的主线程阻塞情况

**预期结果**：
- ✅ 原实现：每次加载走 `suspendCancellableCoroutine + enqueue + Callback.resume`，5 次线程切换/协程调度，主线程阻塞 ~20-50ms/次
- ✅ 新实现：每次加载走同步 `execute()`，1 次线程切换（主线程 → IO 线程），主线程阻塞 ~10-30ms/次
- ✅ 主线程阻塞减少约 30-50%（协程调度开销省去）
- ✅ WebView 加载流畅度提升

---

## 测试统计

| 级别 | 用例数 | 通过 | 待验证 |
|------|--------|------|--------|
| Level 1（单元测试） | 0 | 0 | 0 |
| Level 2（真机验证） | 8 | 0 | 8 ⏳ |
| Level 3（端到端验证） | 2 | 0 | 2 ⏳ |
| **合计** | **10** | **0** | **10** |

## 已知局限与升级路径

| 局限 | 说明 | 升级路径 |
|------|------|---------|
| 未直接测 BottomWebViewDialog | 继承 `BottomSheetDialogFragment`，依赖 `FragmentManager`/`appCtx`，纯 JVM 无法实例化 | 引入 Robolectric 或 Instrumented Test |
| 未直接测 getModifiedContentWithJs | 依赖 `android.webkit.CookieManager`（Android 框架）+ `okHttpClient`（依赖 `AppConfig`/`Cronet` 初始化），纯 JVM 无法运行 | 引入 Robolectric 测真实 CookieManager 行为 |
| 307/308 重定向测试依赖真实环境 | 需要真实返回 307/308 的 URL，测试环境搭建困难 | 使用 MockWebServer 模拟 307/308 响应 |
| 真机验证未执行 | Level 2/3 用例待用户在真机上验证 | 见第 27 章节集成验证 |
