# P1-C3 连接池调优 测试用例

> Task 17 / C3：OkHttp 连接池扩容至 50 个空闲连接（默认 5），5 分钟保活，提升多书源并发访问的连接复用率

## 功能概述

| 子功能 | 说明 |
|--------|------|
| 连接池扩容 | `ConnectionPool(50, 5, TimeUnit.MINUTES)`：50 个空闲连接，5 分钟保活 |
| 派生客户端继承 | `okHttpClientManga` / `proxyClient` 通过 `newBuilder()` 自动继承连接池 |
| 性能提升 | 多书源并发访问时减少 TCP/TLS 握手开销 |

**问题根因**：原 okHttpClient 用 OkHttp 默认 `ConnectionPool(5, 5, TimeUnit.MINUTES)`（5 个空闲连接）。Legado 用户常同时访问多个书源域名，5 个连接不够用，导致频繁重建连接，增加 TCP/TLS 握手开销。

**实现文件**：
- `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`（okHttpClient builder 添加 `.connectionPool(...)`）

**对比延伸版本**：所有延伸版本均用 OkHttp 默认 ConnectionPool(5, 5, TimeUnit.MINUTES)，无连接池调优；蛋蛋Max 文档建议 maxIdleConnections=10，本项目采用 50（适合 Legado 多书源并发场景）。

## 测试环境

- 设备：JVM 代码审查（Level 1）+ Android 6.0+ 真机（Level 2）
- 构建版本：appDebug

---

## 一、配置正确性（代码审查）

### TC-P1-C3-01：连接池配置正确性（代码审查）✅ Level 1 已通过

**关联源码**：OkHttp.kt, ConnectionPool.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 读取 `HttpHelper.kt` okHttpClient builder 链
2. 检查 `.connectionPool(...)` 配置

**预期结果**：
- ✅ 存在 `.connectionPool(okhttp3.ConnectionPool(50, 5, TimeUnit.MINUTES))`
- ✅ maxIdleConnections = 50
- ✅ keepAliveDuration = 5 分钟
- ✅ 时间单位为 TimeUnit.MINUTES

**实际结果**：通过（L88 `.connectionPool(okhttp3.ConnectionPool(50, 5, TimeUnit.MINUTES))`）

### TC-P1-C3-02：派生客户端继承连接池（代码审查）✅ Level 1 已通过

**关联源码**：OkHttp.kt, ConnectionPool.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 读取 `okHttpClientManga` 定义（L129）
2. 读取 `getProxyClient` 函数（L169）
3. 检查是否通过 `okHttpClient.newBuilder()` 创建

**预期结果**：
- ✅ `okHttpClientManga = okHttpClient.newBuilder().run { ... }.build()`
- ✅ `getProxyClient` 中 `val builder = okHttpClient.newBuilder()`
- ✅ OkHttp 的 `newBuilder()` 实现为 `Builder(this)`，复制原 client 的 connectionPool
- ✅ 派生客户端自动继承 50 连接的连接池

**实际结果**：通过（L129 + L189 均用 `okHttpClient.newBuilder()`）

### TC-P1-C3-03：编译验证 ✅ Level 1 已通过

**关联源码**：OkHttp.kt, ConnectionPool.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 运行 `:app:assembleAppDebug`

**预期结果**：
- ✅ BUILD SUCCESSFUL

**实际结果**：通过（BUILD SUCCESSFUL in 1m 22s）

---

## 二、端到端集成（待真机验证）

### TC-P1-C3-04：多书源访问连接复用率提升（Level 2 真机验证）⏳ 待验证

**关联源码**：OkHttp.kt, ConnectionPool.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 准备 10+ 个不同域名的书源
- 网络抓包工具（如 Charles/Fiddler）或 OkHttp 日志

**测试步骤**：
1. 在 app 中依次访问 10 个不同书源
2. 等待 3 分钟
3. 再次访问相同的 10 个书源
4. 检查 OkHttp 连接复用情况（日志或抓包）

**预期结果**：
- ✅ 第 2 次访问时，连接被复用（无 TCP/TLS 握手）
- ✅ 连接池命中率显著提升（相比默认 5 连接）
- ✅ 整体加载时间减少

### TC-P1-C3-05：内存占用可接受（Level 2 真机验证）⏳ 待验证

**关联源码**：OkHttp.kt, ConnectionPool.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 启动 app，记录初始内存
2. 访问 50+ 个不同书源（填满连接池）
3. 检查内存占用

**预期结果**：
- ✅ 50 个连接约 2.5MB 内存（每连接 ~50KB）
- ✅ 内存增长在可接受范围内（< 5MB）
- ✅ 无 OOM 或内存告警

### TC-P1-C3-06：网络切换后连接池正确清理（Level 2 真机验证）⏳ 待验证

**关联源码**：OkHttp.kt, ConnectionPool.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. WiFi 网络下访问多个书源
2. 切换到移动数据
3. 再次访问相同书源

**预期结果**：
- ✅ 网络切换后旧连接被清理（避免连接失效）
- ✅ 新网络下连接正常建立
- ✅ 无 "Connection refused" 或 "Socket closed" 错误

### TC-P1-C3-07：代理客户端继承连接池（Level 2 真机验证）⏳ 待验证

**关联源码**：OkHttp.kt, ConnectionPool.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 配置代理访问书源
2. 检查代理 OkHttpClient 的连接池配置

**预期结果**：
- ✅ 代理客户端继承 50 连接的连接池
- ✅ 代理访问同样享受连接复用

---

## 测试统计

| 级别 | 用例数 | 通过 | 待验证 |
|------|--------|------|--------|
| Level 1（代码审查 + 编译验证） | 3 | 3 ✅ | 0 |
| Level 2（真机验证） | 4 | 0 | 4 ⏳ |
| **合计** | **7** | **3** | **4** |

## 已知局限与升级路径

| 局限 | 说明 | 升级路径 |
|------|------|---------|
| 未编写 JVM 单元测试 | okHttpClient 依赖 AppConfig/SSLHelper/Cronet 等 Android 框架，纯 JVM 无法实例化；连接池配置是声明式代码，测试价值有限 | 引入 Robolectric 测真实 OkHttpClient.connectionPool 配置 |
| 50 连接为经验值 | 适合 Legado 多书源并发场景，但未做精确容量规划 | 可结合用户实际书源数量调研，动态调整 maxIdleConnections |
| 真机验证未执行 | Level 2 用例待用户在真机上验证 | 见第 27 章节集成验证 |
