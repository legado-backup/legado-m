# P1-A6 proxyClientCache LRU 上限 测试用例

> Task 15 / A6：修复代理 OkHttpClient 缓存无限增长导致内存泄漏问题，改为 LRU 缓存（上限 20）

## 功能概述

| 子功能 | 说明 |
|--------|------|
| LRU 缓存 | `LinkedHashMap(accessOrder=true)` + `removeEldestEntry`，上限 20 个代理客户端 |
| 线程安全 | `synchronized(proxyClientLock)` 包装"读取-构造-写入"复合操作 |
| 自动淘汰 | 超过上限时自动淘汰最久未访问的代理客户端 |

**问题根因**：原 `HttpHelper.kt:25-27` 用 `ConcurrentHashMap` 无上限缓存代理 OkHttpClient。每个 OkHttpClient 含独立连接池/调度器，泄漏代价高。用户切换 50+ 个代理后，缓存永不释放，长跑导致内存泄漏。

**实现文件**：
- `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`（替换 proxyClientCache 定义 + getProxyClient 加 synchronized）
- `app/src/test/java/io/legado/app/help/http/ProxyClientCacheTest.kt`（新增 5 个单元测试）

**对比延伸版本**：所有 7 个延伸版本（蛋蛋Max/阅读T/阅读NG/LegadoTeam/refgd/Jingshiro/Rimchars）均用相同的 `ConcurrentHashMap` 无上限方案，蛋蛋Max 文档提到 LruCache 但实际未实施，本项目独立优化。

## 测试环境

- 设备：JVM 单元测试（Level 1）+ Android 6.0+ 真机（Level 2）
- 构建版本：appDebug
- 测试框架：JUnit 4 + org.junit.Assert

---

## 一、LRU 淘汰策略（LinkedHashMap 同模式）

### TC-P1-A6-01：上限内不淘汰（边界用例）✅ Level 1 已通过

**前置条件**：空 LRU cache（上限 20）

**测试步骤**：
1. 依次 put proxy1~proxy20 共 20 个 entry
2. 检查 cache.size
3. 查询 proxy1 和 proxy20

**预期结果**：
- ✅ size == 20
- ✅ proxy1 存在
- ✅ proxy20 存在

**实际结果**：通过（`lruCache_withinMaxSize_doesNotEvict`）

### TC-P1-A6-02：超限淘汰最老（正常用例）✅ Level 1 已通过

**测试步骤**：
1. 依次 put proxy1~proxy21 共 21 个 entry
2. 检查 size
3. 检查 proxy1 是否存在（最老）
4. 检查 proxy21 是否存在（最新）

**预期结果**：
- ✅ size == 20（自动淘汰 1 个）
- ✅ proxy1 已被淘汰
- ✅ proxy21 保留

**实际结果**：通过（`lruCache_exceedMaxSize_evictsOldest`）

### TC-P1-A6-03：accessOrder 刷新顺序（对照用例）✅ Level 1 已通过

**测试步骤**：
1. 依次 put proxy1~proxy20 共 20 个 entry
2. 访问 proxy1（使其成为最近访问）
3. put proxy21 触发淘汰
4. 检查 proxy1 是否保留
5. 检查 proxy2 是否被淘汰（最久未访问）

**预期结果**：
- ✅ size == 20
- ✅ proxy1 保留（被访问过）
- ✅ proxy2 被淘汰（最久未访问）

**实际结果**：通过（`lruCache_accessOrderRefreshesEvictionOrder`）

### TC-P1-A6-04：空 cache 查询返回 null（边界用例）✅ Level 1 已通过

**测试步骤**：
1. 不 put 任何 entry
2. 查询 "nonexistent"

**预期结果**：
- ✅ 返回 null

**实际结果**：通过（`lruCache_emptyCache_returnsNullForMissingKey`）

### TC-P1-A6-05：连续淘汰保留最近 20（综合用例）✅ Level 1 已通过

**测试步骤**：
1. 依次 put proxy1~proxy50 共 50 个 entry
2. 检查 size
3. 检查 proxy1~proxy30 是否被淘汰
4. 检查 proxy31~proxy50 是否保留

**预期结果**：
- ✅ size == 20
- ✅ proxy1~proxy30 全部被淘汰
- ✅ proxy31~proxy50 全部保留

**实际结果**：通过（`lruCache_multipleEvictions_keepsMostRecent20`）

---

## 二、端到端集成（待真机验证）

### TC-P1-A6-06：代理书源访问正常（Level 2 真机验证）⏳ 待验证

**前置条件**：
- 配置一个代理（http 或 socks5）
- 准备一个使用该代理的书源

**测试步骤**：
1. 在 app 中配置代理
2. 访问使用代理的书源
3. 检查书源能否正常加载内容

**预期结果**：
- ✅ 书源内容正常加载
- ✅ 代理客户端被缓存（下次访问同代理复用）
- ✅ 日志无 "Proxy authentication failed" 等错误

### TC-P1-A6-07：长跑后 cache 不超过 20 个条目（Level 2 真机验证）⏳ 待验证

**前置条件**：
- 准备 30+ 个不同的代理配置

**测试步骤**：
1. 依次切换 30 个不同代理访问书源
2. 触发内存分析（Android Profiler 或 dump 内存）
3. 检查 proxyClientCache 实际大小

**预期结果**：
- ✅ cache 始终保持 ≤ 20 个条目
- ✅ 最久未使用的代理被自动淘汰
- ✅ 内存占用稳定，不持续增长

### TC-P1-A6-08：代理复用不重复构造（Level 2 真机验证）⏳ 待验证

**测试步骤**：
1. 配置代理 A，访问书源
2. 切换到代理 B，访问书源
3. 切换回代理 A，访问书源
4. 检查代理 A 的 OkHttpClient 是否被复用（未重新构造）

**预期结果**：
- ✅ 第 1 次访问代理 A：构造新 OkHttpClient
- ✅ 第 2 次访问代理 A：从缓存复用（不构造）
- ✅ 切换代理 B 后再切回 A，A 仍在缓存中（未被淘汰）

---

## 测试统计

| 级别 | 用例数 | 通过 | 待验证 |
|------|--------|------|--------|
| Level 1（单元测试） | 5 | 5 ✅ | 0 |
| Level 2（真机验证） | 3 | 0 | 3 ⏳ |
| **合计** | **8** | **5** | **3** |

## 已知局限与升级路径

| 局限 | 说明 | 升级路径 |
|------|------|---------|
| 未直接测 getProxyClient | 依赖 okHttpClient（AppConfig/SSLHelper/Cronet 等 Android 框架），纯 JVM 无法实例化 | 引入 Robolectric + MockWebServer 测代理客户端构造与缓存联动 |
| 测试用 String 代替 OkHttpClient | LRU 策略逻辑与 value 类型无关，验证有效性 | 同上，引入 Android 测试框架后测真实 OkHttpClient |
| synchronized 粒度为整个 map | 代理书源访问频率不高，性能可接受 | 如需更高并发可改用 ConcurrentLinkedHashMap |
