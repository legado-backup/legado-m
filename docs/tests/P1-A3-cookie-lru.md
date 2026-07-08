# P1-A3 CookieStore LRU 淘汰 测试用例

> Task 14 / A3：修复 CookieStore 大 Cookie（>4096）随机删除导致登录态丢失问题，改为优先删除 tracking Cookie，其次按 key 长度降序

## 功能概述

| 子功能 | 说明 |
|--------|------|
| Tracking Cookie 识别 | 识别 _ga / _gid / _gat / _hjid（含前缀变体如 _ga_XYZ）+ Hm_lvt_xxx / Hm_lpvt_xxx（百度统计） |
| LRU 选择策略 | while 循环超 4096 时，优先删 tracking Cookie；无 tracking 时按 key 长度降序删除 |
| 数据库零迁移 | 不新增 lastAccessTime 字段，策略基于 key 名称 + key 长度 |

**问题根因**：原 `CookieStore.kt:85-90` 用 `cookieMap.keys.random()` 随机删除，可能误删 JSESSIONID / token / sid 等登录关键 Cookie，导致大 Cookie 站点登录态丢失。

**实现文件**：
- `app/src/main/java/io/legado/app/help/http/CookieStore.kt`（新增 top-level 纯函数 + 修改 getCookie while 循环）
- `app/src/test/java/io/legado/app/help/http/CookieStoreTest.kt`（新增 11 个单元测试）

**对比延伸版本**：蛋蛋Max / 阅读T / 阅读NG 均沿用原版 `random()` 策略，本项目独立优化。

## 测试环境

- 设备：JVM 单元测试（Level 1）+ Android 6.0+ 真机（Level 3）
- 构建版本：appDebug
- 测试框架：JUnit 4 + org.junit.Assert

---

## 一、Tracking Cookie 识别（isTrackingCookieKey）

### TC-P1-A3-01：通用 tracking Cookie 识别（正常用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：无

**测试步骤**：
1. 调用 `isTrackingCookieKey("_ga")`
2. 调用 `isTrackingCookieKey("_gid")`
3. 调用 `isTrackingCookieKey("_gat")`
4. 调用 `isTrackingCookieKey("_hjid")`

**预期结果**：
- ✅ 全部返回 true

**实际结果**：通过（`isTrackingCookieKey_recognizesCommonTrackingCookies`）

### TC-P1-A3-02：前缀变体识别（正常用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 调用 `isTrackingCookieKey("_ga_XYZ")`
2. 调用 `isTrackingCookieKey("_gat_UA-12345")`
3. 调用 `isTrackingCookieKey("_gid_abc")`

**预期结果**：
- ✅ 全部返回 true（前缀 + 下划线变体）

**实际结果**：通过（`isTrackingCookieKey_recognizesPrefixedVariants`）

### TC-P1-A3-03：百度统计 Hm_lvt_/Hm_lpvt_ 识别（正常用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 调用 `isTrackingCookieKey("Hm_lvt_123456")`
2. 调用 `isTrackingCookieKey("Hm_lpvt_abc")`

**预期结果**：
- ✅ 全部返回 true（正则 `^Hm_(lvt|lpvt)_.*` 匹配）

**实际结果**：通过（`isTrackingCookieKey_recognizesBaiduHmCookies`）

### TC-P1-A3-04：业务 Cookie 不误判（对照用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 调用 `isTrackingCookieKey("JSESSIONID")`
2. 调用 `isTrackingCookieKey("token")`
3. 调用 `isTrackingCookieKey("sid")`
4. 调用 `isTrackingCookieKey("PHPSESSID")`

**预期结果**：
- ✅ 全部返回 false（业务登录 Cookie 不应被识别为 tracking）

**实际结果**：通过（`isTrackingCookieKey_rejectsBusinessCookies`）

### TC-P1-A3-05：空白 key trim 处理（边界用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 调用 `isTrackingCookieKey("  _ga  ")`

**预期结果**：
- ✅ 返回 true（内部 trim 处理前后空白）

**实际结果**：通过（`isTrackingCookieKey_trimsWhitespace`）

---

## 二、LRU 选择策略（selectCookieKeyToRemove）

### TC-P1-A3-06：空 map 返回 null（边界用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 调用 `selectCookieKeyToRemove(emptyMap())`

**预期结果**：
- ✅ 返回 null

**实际结果**：通过（`selectCookieKeyToRemove_emptyMap_returnsNull`）

### TC-P1-A3-07：单元素 map 返回该 key（边界用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 调用 `selectCookieKeyToRemove(mapOf("JSESSIONID" to "abc123"))`

**预期结果**：
- ✅ 返回 "JSESSIONID"

**实际结果**：通过（`selectCookieKeyToRemove_singleEntry_returnsThatKey`）

### TC-P1-A3-08：tracking Cookie 优先于业务 Cookie（正常用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：map 含业务 Cookie + tracking Cookie

**测试步骤**：
1. 构造 `linkedMapOf("JSESSIONID" to "abc123", "_ga" to "GA1.2.xxx", "token" to "bearer-yyy")`
2. 调用 `selectCookieKeyToRemove(map)`

**预期结果**：
- ✅ 返回 "_ga"（tracking 优先于业务 Cookie，即使 JSESSIONID 更长）

**实际结果**：通过（`selectCookieKeyToRemove_prefersTrackingCookieOverBusinessCookie`）

### TC-P1-A3-09：多 tracking 取最长 key（正常用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 构造 `linkedMapOf("_ga" to "...", "_gid" to "...", "Hm_lvt_1234567890" to "...")`
2. 调用 `selectCookieKeyToRemove(map)`

**预期结果**：
- ✅ 返回 "Hm_lvt_1234567890"（多个 tracking 时取最长 key 最大化释放空间）

**实际结果**：通过（`selectCookieKeyToRemove_prefersLongestTrackingCookie`）

### TC-P1-A3-10：无 tracking 时按 key 长度降序（对照用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 构造 `linkedMapOf("sid" to "s1", "JSESSIONID" to "j1", "token" to "t1")`
2. 调用 `selectCookieKeyToRemove(map)`

**预期结果**：
- ✅ 返回 "JSESSIONID"（无 tracking 时取最长业务 key）

**实际结果**：通过（`selectCookieKeyToRemove_noTrackingCookie_fallsBackToLongestKey`）

### TC-P1-A3-11：混合场景 tracking 优先（综合用例）✅ Level 1 已通过

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**测试步骤**：
1. 构造 `linkedMapOf("PHPSESSID" to "p1", "_gat_UA-12345-1" to "g1", "a" to "x")`
2. 调用 `selectCookieKeyToRemove(map)`

**预期结果**：
- ✅ 返回 "_gat_UA-12345-1"（即使 PHPSESSID 是业务 Cookie 且较长，仍优先删 tracking）

**实际结果**：通过（`selectCookieKeyToRemove_mixedTrackingAndBusiness_prefersTracking`）

---

## 三、端到端集成（待真机验证）

### TC-P1-A3-12：大 Cookie 站点登录态保持（Level 3 真机验证）⏳ 待验证

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：
- 准备一个 Cookie 总长度 > 4096 的书源站点（含 _ga / JSESSIONID 等混合 Cookie）
- 已登录该站点

**测试步骤**：
1. 在 app 中访问该书源
2. 触发多次请求（使 Cookie 累积）
3. 检查请求是否携带 JSESSIONID / token 等登录态 Cookie
4. 检查 _ga 等 tracking Cookie 是否被优先删除

**预期结果**：
- ✅ 登录态保持（JSESSIONID / token 等业务 Cookie 未被删除）
- ✅ tracking Cookie（_ga / _gid 等）优先被删除
- ✅ Cookie 总长度被截断到 ≤ 4096
- ✅ 后续请求正常返回业务数据（非 401/403）

### TC-P1-A3-13：4096 截断链路端到端验证（Level 3 真机验证）⏳ 待验证

**关联源码**：CookieStore.kt
**关联 Activity**：无（纯 Service/工具类）

**前置条件**：构造一个仅含业务 Cookie 但总长度 > 4096 的极端场景

**测试步骤**：
1. 在 app 中访问该书源
2. 观察日志中 Cookie 截断行为
3. 检查截断后保留的 Cookie 顺序

**预期结果**：
- ✅ 按 key 长度降序逐个删除，直到 ≤ 4096
- ✅ 删除顺序可预测（最长 key 先删）
- ✅ 不会出现"删除一个 key 后长度反而增加"的异常

---

## 测试统计

| 级别 | 用例数 | 通过 | 待验证 |
|------|--------|------|--------|
| Level 1（单元测试） | 11 | 11 ✅ | 0 |
| Level 3（真机验证） | 2 | 0 | 2 ⏳ |
| **合计** | **13** | **11** | **2** |

## 已知局限与升级路径

| 局限 | 说明 | 升级路径 |
|------|------|---------|
| 未覆盖 getCookie 完整流程 | CookieStore object 依赖 appDb / CacheManager / android.webkit.CookieManager，纯 JVM 无法实例化 | 引入 Robolectric 测整体 4096 截断链路 |
| tracking Cookie 列表为硬编码 | 仅覆盖 _ga / _gid / _gat / _hjid / Hm_lvt_* / Hm_lpvt_* 常见 tracking | 后续可考虑配置化或从 Cookie 属性（如 SameSite/Expires）推断 |
| 真机验证未执行 | Level 3 用例待用户在真机上验证 | 见第 27 章节集成验证 |
