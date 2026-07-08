# P1-B1 BackstageWebView runBlocking 修复 测试用例

> Task 19 / B1：修复 BackstageWebView.load() 主线程 runBlocking 阻塞，改为先读内存缓存，未命中再走数据库

## 功能概述

| 子功能 | 说明 |
|--------|------|
| BookSource 内存缓存 | `SourceHelp.bookSourceCache`：`android.util.LruCache<String, BookSource>(50)`，50 个常用书源，自动 LRU 淘汰 |
| 缓存读取 | `SourceHelp.getCachedBookSource(key)`：先读 LruCache，未命中返回 null |
| 缓存写入 | `SourceHelp.putBookSourceCache(key, source)`：写入 LruCache |
| 缓存删除 | `SourceHelp.removeBookSourceCache(key)`：删源时调用 |
| BackstageWebView 修复 | `BackstageWebView.load()`：先读缓存，未命中再 `runBlocking(IO)` 查数据库并 `.also` 写入缓存 |

**问题根因**：原 `BackstageWebView.kt:119` 在主线程（`runOnUI` 调用 `load()`）直接 `runBlocking(IO) { appDb.bookSourceDao.getBookSource(key) }`，每次书源调试/规则执行都阻塞主线程查询数据库，长跑下频繁调用影响 UI 流畅度。

**实现文件**：
- `app/src/main/java/io/legado/app/help/source/SourceHelp.kt`（新增 LruCache + 3 个方法 + insert/delete 同步维护）
- `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt`（修改 L118-125 先读缓存再走数据库）

**对比延伸版本**：所有延伸版本均直接 runBlocking 查数据库，本项目独立优化。

## 测试环境

- 设备：JVM 单元测试（Level 1，本任务无）+ Android 6.0+ 真机（Level 2/3）
- 构建版本：appDebug
- 测试框架：真机操作 + 日志观察

> **未新增单元测试的理由**：
> - `SourceHelp` 是 `object` 依赖 `appCtx`/`appDb`（Android 框架），纯 JVM 无法初始化
> - `BackstageWebView.load()` 依赖 `WebView`/`appDb`/`runOnUI`，纯 JVM 无法实例化
> - LruCache 使用模式与 Task 18（customIp）完全一致，已由 Task 18 的 5 个单元测试覆盖 LruCache 行为本身
> - 本任务核心价值在"主线程阻塞减少"，需真机 Level 2/3 验证

---

## 一、缓存读写一致性（Level 2 真机验证）

### TC-P1-B1-01：首次访问书源调试写入缓存（正常用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 导入一个书源（如"笔趣阁"）
- 书源未在 SourceHelp.bookSourceCache 中

**测试步骤**：
1. 进入书源调试页面
2. 触发规则执行（点击"测试"按钮，使用含 `{{bookSource}}` 的规则）
3. 观察 `DebugLog` 输出

**预期结果**：
- ✅ 首次访问：`SourceHelp.getCachedBookSource(key)` 返回 null
- ✅ 走 `runBlocking(IO) { appDb.bookSourceDao.getBookSource(key) }` 查数据库
- ✅ 查询结果通过 `.also { SourceHelp.putBookSourceCache(key, it) }` 写入缓存
- ✅ WebView 正常加载规则（行为与原实现一致）

### TC-P1-B1-02：二次访问命中缓存（正常用例）⏳ 待验证

**前置条件**：TC-P1-B1-01 已执行（缓存已写入）

**测试步骤**：
1. 再次触发同一书源的规则执行
2. 观察主线程阻塞情况

**预期结果**：
- ✅ `SourceHelp.getCachedBookSource(key)` 返回 BookSource（命中缓存）
- ✅ **不走** `runBlocking(IO)` 数据库查询
- ✅ 主线程阻塞显著减少（首次阻塞 ~10ms，二次 ~0ms）
- ✅ WebView 正常加载规则

### TC-P1-B1-03：insertBookSource 后缓存刷新（正常用例）⏳ 待验证

**前置条件**：
- 书源 A 已在缓存中
- 修改书源 A 的规则

**测试步骤**：
1. 通过 `SourceHelp.insertBookSource(modifiedSource)` 更新书源
2. 触发书源 A 的规则执行

**预期结果**：
- ✅ `insertBookSource` 内部调用 `putBookSourceCache(source.bookSourceUrl, source)` 刷新缓存
- ✅ `getCachedBookSource` 返回修改后的 BookSource
- ✅ WebView 使用新规则

### TC-P1-B1-04：deleteBookSource 后缓存清除（边界用例）⏳ 待验证

**前置条件**：书源 A 已在缓存中

**测试步骤**：
1. 通过 `SourceHelp.deleteBookSource(key)` 删除书源
2. 触发书源 A 的规则执行（应失败/返回 null）

**预期结果**：
- ✅ `deleteBookSourceInternal` 内部调用 `removeBookSourceCache(key)` 删除缓存
- ✅ `getCachedBookSource(key)` 返回 null
- ✅ `runBlocking` 查数据库也返回 null（数据库已删除）
- ✅ WebView 不加载规则（bookSource 为 null）

---

## 二、LRU 淘汰策略（Level 2 真机验证）

### TC-P1-B1-05：超 50 个书源自动淘汰（边界用例）⏳ 待验证

**前置条件**：
- 导入 60 个不同书源

**测试步骤**：
1. 依次访问 60 个书源的规则执行（写入缓存）
2. 再次访问第 1 个书源

**预期结果**：
- ✅ 缓存上限 50，第 1 个书源已被 LRU 淘汰
- ✅ `getCachedBookSource` 返回 null（未命中）
- ✅ 走 `runBlocking` 查数据库并重新写入缓存
- ✅ 不影响功能正确性

---

## 三、端到端集成（Level 3 真机验证）

### TC-P1-B1-06：书源调试全流程（端到端用例）⏳ 待验证

**前置条件**：
- 安装新构建 APK
- 导入 3+ 个书源

**测试步骤**：
1. 进入书源列表
2. 选择书源 A，点击"调试"
3. 在调试页面执行搜索规则
4. 返回，再次进入书源 A 调试，执行搜索规则
5. 切换到书源 B 调试
6. 返回书源 A 调试

**预期结果**：
- ✅ 步骤 3：首次访问，走数据库查询，规则正常执行
- ✅ 步骤 4：二次访问，命中缓存，规则正常执行，主线程更流畅
- ✅ 步骤 5：书源 B 首次访问，走数据库查询
- ✅ 步骤 6：书源 A 命中缓存（未被淘汰，因为只缓存了 2 个）
- ✅ 全程无 ANR，UI 流畅度较原实现改善

### TC-P1-B1-07：长跑下主线程阻塞减少（性能验证）⏳ 待验证

**前置条件**：
- 导入 20+ 个书源
- 启用 Systrace 或 CPU Profiler

**测试步骤**：
1. 连续执行 50 次书源规则调试（每个书源循环 2-3 次）
2. 对比原实现与新实现的主线程阻塞情况

**预期结果**：
- ✅ 原实现：50 次 runBlocking 主线程阻塞，每次 ~5-15ms，累计 ~250-750ms
- ✅ 新实现：首次 20 次走数据库（~100-300ms），后续 30 次命中缓存（~0ms）
- ✅ 主线程阻塞减少约 60-80%

---

## 测试统计

| 级别 | 用例数 | 通过 | 待验证 |
|------|--------|------|--------|
| Level 1（单元测试） | 0 | 0 | 0 |
| Level 2（真机验证） | 5 | 0 | 5 ⏳ |
| Level 3（端到端验证） | 2 | 0 | 2 ⏳ |
| **合计** | **7** | **0** | **7** |

## 已知局限与升级路径

| 局限 | 说明 | 升级路径 |
|------|------|---------|
| 未直接测 SourceHelp.bookSourceCache | 依赖 `android.util.LruCache`（Android 框架）+ `appCtx`/`appDb`，纯 JVM 无法实例化 | 引入 Robolectric 测真实 LruCache 行为 |
| 未直接测 BackstageWebView.load() | 依赖 `WebView`/`runOnUI`/`appDb`，纯 JVM 无法实例化 | 引入 Robolectric 或 Instrumented Test |
| LruCache 行为本身 | 已由 Task 18（customIp）的 5 个单元测试覆盖同模式 LruCache 行为 | 复用 Task 18 测试结论 |
| 真机验证未执行 | Level 2/3 用例待用户在真机上验证 | 见第 27 章节集成验证 |
