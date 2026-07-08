# P1-C5 customIp LRU 上限 测试用例

> Task 18 / C5：修复自定义 DNS IP 缓存无限增长导致内存泄漏问题，改为 LRU 缓存（上限 100）

## 功能概述

| 子功能 | 说明 |
|--------|------|
| LRU 缓存 | `android.util.LruCache<String, String>(100)`：100 个 DNS 映射，自动 LRU 淘汰 |
| 线程安全 | `android.util.LruCache` 内部 `synchronized` 包装，无需额外同步 |
| 使用模式 | `getClient()` 写入 → `CronetHelper.customHost()` 读取并 `remove`（一次性） |

**问题根因**：原 `AnalyzeUrl.kt:773` 用 `ConcurrentHashMap<String, String>()` 无上限缓存自定义 DNS IP。当用户切换大量带 dnsIp 的书源且未启用 Cronet 时，customIp 累积永不释放，长跑导致内存泄漏。

**实现文件**：
- `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt`（替换 customIp 定义 + L603 写入语法）
- `app/src/test/java/io/legado/app/model/analyzeRule/CustomIpCacheTest.kt`（新增 5 个单元测试）

**对比延伸版本**：所有延伸版本均用 `ConcurrentHashMap` 无上限方案，本项目独立优化。

## 测试环境

- 设备：JVM 单元测试（Level 1）+ Android 6.0+ 真机（Level 2）
- 构建版本：appDebug
- 测试框架：JUnit 4 + org.junit.Assert

---

## 一、LRU 策略与使用模式（LinkedHashMap 同模式）

### TC-P1-C5-01：put + remove 一次性使用模式（正常用例）✅ Level 1 已通过

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：空 LRU cache（上限 100）

**测试步骤**：
1. `cache.put("http://example.com/book", "192.168.1.1")`
2. `cache.remove("http://example.com/book")` 模拟 CronetHelper.customHost 读取

**预期结果**：
- ✅ remove 返回 "192.168.1.1"
- ✅ remove 后 entry 不存在

**实际结果**：通过（`customIp_putThenRemove_oneTimeUsagePattern`）

### TC-P1-C5-02：上限内不淘汰（边界用例）✅ Level 1 已通过

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 依次 put url1~url100 共 100 个 entry
2. 检查 cache.size

**预期结果**：
- ✅ size == 100

**实际结果**：通过（`customIp_withinMaxSize_doesNotEvict`）

### TC-P1-C5-03：超限淘汰最老（正常用例）✅ Level 1 已通过

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 依次 put url1~url101 共 101 个 entry
2. 检查 size、url1、url101

**预期结果**：
- ✅ size == 100（自动淘汰 1 个）
- ✅ url1 已被淘汰
- ✅ url101 保留

**实际结果**：通过（`customIp_exceedMaxSize_evictsOldest`）

### TC-P1-C5-04：空 cache remove 返回 null（边界用例）✅ Level 1 已通过

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 不 put 任何 entry
2. `cache.remove("nonexistent")`

**预期结果**：
- ✅ 返回 null（对应 CronetHelper.customHost 的 `urlIp == null` 分支）

**实际结果**：通过（`customIp_emptyCacheRemoveReturnsNull`）

### TC-P1-C5-05：连续淘汰保留最近 100（综合用例）✅ Level 1 已通过

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 依次 put url1~url250 共 250 个 entry
2. 检查 size
3. 检查 url1~url150 是否被淘汰
4. 检查 url151~url250 是否保留

**预期结果**：
- ✅ size == 100
- ✅ url1~url150 全部被淘汰
- ✅ url151~url250 全部保留

**实际结果**：通过（`customIp_multipleEvictions_keepsMostRecent100`）

---

## 二、端到端集成（待真机验证）

### TC-P1-C5-06：DNS 缓存场景正常（Level 2 真机验证）⏳ 待验证

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 启用 Cronet
- 配置一个带 dnsIp 的书源

**测试步骤**：
1. 访问带 dnsIp 的书源
2. 检查请求是否使用自定义 IP

**预期结果**：
- ✅ 请求使用自定义 IP（非系统 DNS 解析结果）
- ✅ customIp 缓存写入
- ✅ CronetHelper.customHost 读取并 remove 后缓存清空

### TC-P1-C5-07：长跑后 customIp 不超过 100 个条目（Level 2 真机验证）⏳ 待验证

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 准备 150+ 个带不同 dnsIp 的书源

**测试步骤**：
1. 依次访问 150 个不同书源（每个带不同 dnsIp）
2. 触发内存分析
3. 检查 customIp 实际大小

**预期结果**：
- ✅ customIp 始终保持 ≤ 100 个条目
- ✅ 最久未使用的 DNS 映射被自动淘汰
- ✅ 内存占用稳定，不持续增长

### TC-P1-C5-08：Cronet 未启用时 customIp 不累积（Level 2 真机验证）⏳ 待验证

**关联源码**：CustomIpCache.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：禁用 Cronet

**测试步骤**：
1. 访问带 dnsIp 的书源
2. 检查 customIp 是否被写入

**预期结果**：
- ✅ Cronet 未启用时 customIp 不被写入（L602 `if (AppConfig.isCronet && dnsIp != null)` 守卫）
- ✅ customIp 保持为空

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
| 未直接测 AnalyzeUrl.customIp | 依赖 `android.util.LruCache`（Android 框架），纯 JVM 无法实例化 | 引入 Robolectric 测真实 LruCache 行为 |
| 测试用 LinkedHashMap 模拟 LruCache | LRU 策略逻辑与实现无关，验证有效性 | 同上，引入 Android 测试框架后测真实 LruCache |
| 真机验证未执行 | Level 2 用例待用户在真机上验证 | 见第 27 章节集成验证 |
