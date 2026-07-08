# P0-1~P0-8 网络层与稳定性优化 测试用例

> 涵盖 8 项 P0 阶段优化：协程错误处理、WebBook 并发安全、Flow 扩展、HTTP 异常拦截、书源扩展、MainViewModel 缓存、CacheBook 同步锁、BookHelp 死锁修复

## 功能概述

| 任务 | 优化点 | 修改文件 |
|------|--------|---------|
| P0-1 | 协程错误处理（CancellationException 反模式修复） | Coroutine.kt |
| P0-2 | WebBook 并发安全（书源互斥锁线程安全） | WebBook.kt |
| P0-3 | Flow 扩展优化（flowWithIO + flowOnIO 合并） | FlowExtensions.kt |
| P0-4 | HTTP 异常拦截器（OkHttpExceptionInterceptor 完善） | OkHttpExceptionInterceptor.kt |
| P0-5 | 书源扩展优化（BookSourceExtensions） | BookSourceExtensions.kt |
| P0-6 | MainViewModel 缓存（刷新队列线程安全） | MainViewModel.kt |
| P0-7 | CacheBook 同步锁（close 方法加锁） | CacheBook.kt / BookHelp.kt |
| P0-8 | SSL/TLS 安全升级 + 307/308 重定向兜底 | SSLHelper.kt / OkHttpUtils.kt / BackstageWebView.kt |

## 测试环境

- 设备：Android 6.0+ 真机
- 构建版本：appDebug
- 依赖：Kotlin 2.3.10, KSP 2.3.4, Room 2.7.1, OkHttp 4.12.0

---

## P0-1 协程错误处理

### TC-P0-1-01：协程正常取消不触发错误回调（正常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：书架正在刷新书籍

**测试步骤**：
1. 打看书架页面，触发书架刷新
2. 在刷新过程中快速按下返回键退出页面
3. 观察是否出现 ANR 或异常弹窗

**预期结果**：
- ✅ 无 ANR 弹窗
- ✅ 无 "Job was cancelled" 异常弹窗
- ✅ 协程正常取消，不触发 onError 回调

### TC-P0-1-02：协程异常触发错误回调（异常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：配置一个无效书源（URL 不可达）

**测试步骤**：
1. 使用无效书源搜索书籍
2. 观察错误处理行为

**预期结果**：
- ✅ 显示错误提示"网络请求失败"或类似信息
- ✅ 不崩溃，不 ANR
- ✅ 错误信息通过 onError 回调传递

### TC-P0-1-03：单元测试验证（Level 1）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
```bash
./gradlew.bat :app:testAppDebugUnitTest --tests "*.CoroutineTest"
```

**预期结果**：
- ✅ 3 个测试用例全部通过
- ✅ BUILD SUCCESSFUL

---

## P0-2 WebBook 并发安全

### TC-P0-2-01：多线程并发访问书源（正常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：书架有 10+ 本书，配多个书源

**测试步骤**：
1. 打看书架，触发"更新所有书籍"
2. 观察刷新过程是否稳定

**预期结果**：
- ✅ 所有书籍更新完成，无崩溃
- ✅ 书源互斥锁正常工作，无 ConcurrentModificationException

### TC-P0-2-02：快速重复触发刷新（边界用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 连续快速点击"刷新"按钮 5 次
2. 观察行为

**预期结果**：
- ✅ 不崩溃
- ✅ 刷新操作正确排队或去重

---

## P0-6 MainViewModel 缓存（刷新队列线程安全）

### TC-P0-6-01：刷新队列并发访问（正常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 书架刷新过程中，同时触发搜索操作
2. 观察是否崩溃

**预期结果**：
- ✅ 无 ConcurrentModificationException
- ✅ 刷新队列正常工作

---

## P0-7 CacheBook 同步锁

### TC-P0-7-01：缓存书籍关闭时数据一致性（正常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：打开一本缓存书籍阅读

**测试步骤**：
1. 打开缓存书籍阅读
2. 在阅读过程中快速切换到另一本书
3. 再切回原书

**预期结果**：
- ✅ 阅读进度正确保存
- ✅ 无数据错乱
- ✅ close 方法同步锁正常工作

### TC-P0-7-02：快速切换书籍（边界用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 快速连续打开 3 本不同的缓存书籍
2. 每本阅读几秒后立即切换

**预期结果**：
- ✅ 每本书的进度独立保存
- ✅ 无数据串错

---

## P0-8 SSL/TLS 安全升级 + 307/308 重定向

### TC-P0-8-01：HTTPS 网站正常访问（正常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 使用 HTTPS 书源搜索书籍
2. 观察是否能正常获取结果

**预期结果**：
- ✅ HTTPS 请求正常
- ✅ TLS 协议生效

### TC-P0-8-02：307/308 重定向网站访问（正常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：找一个支持 307/308 重定向的网站书源

**测试步骤**：
1. 使用该书源搜索书籍
2. 观察是否能正常获取结果

**预期结果**：
- ✅ 307/308 重定向正常处理
- ✅ 不出现"重定向过多"错误

### TC-P0-8-03：SSL 证书错误网站（异常用例）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 使用 SSL 证书过期或无效的书源
2. 观察错误处理

**预期结果**：
- ✅ 显示明确的 SSL 错误信息
- ✅ 不崩溃

---

## 集成验证

### TC-P0-13-01：全量单元测试（Level 1）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
```bash
./gradlew.bat :app:testAppDebugUnitTest
```

**预期结果**：
- ✅ BUILD SUCCESSFUL
- ✅ CoroutineTest 3 个测试用例全部通过

### TC-P0-13-02：APK 编译通过（Level 2）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
```bash
./gradlew.bat :app:assembleAppDebug
```

**预期结果**：
- ✅ BUILD SUCCESSFUL
- ✅ 仅有 deprecation 警告（已有代码，非本次新增）

### TC-P0-13-03：真机功能回归（Level 3）

**关联源码**：ConcurrentRateLimiter.kt, OkHttp.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 安装 APK 到真机
2. 验证书源搜索、RSS 源加载、图片加载、翻页等功能正常

**预期结果**：
- ✅ 所有核心功能正常
- ✅ 无崩溃、无 ANR
