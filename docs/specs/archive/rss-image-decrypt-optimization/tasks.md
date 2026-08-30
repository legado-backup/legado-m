# 任务清单：订阅源图片解密优化

## 1. 准备阶段

- [ ] 1.1 读取 RssParserByRule.kt 当前实现（确认 L44 单一analyzeRule实例 + L74 for循环 + L128 调试输出 + L43 articleList）
- [ ] 1.2 读取 Debug.kt 当前实现（确认 L41/L42/L56 log函数无截断）
- [ ] 1.3 读取 AppLog.kt putEntry 实现（确认 L79 后无截断）
- [ ] 1.4 确认 91 大事件源 ruleImage JS 当前实现（从DB提取）
- [ ] 1.5 确认 CacheManager 在 JS 引擎注入点（AnalyzeRule.kt L847 bindings["cache"]）
- [ ] 1.6 确认 RhinoScriptEngine L261-269 Context.enter() ThreadLocal（并行安全前提）

## 2. P0 调试输出截断（防崩溃）

- [ ] 2.1 **Debug.kt L41 后**：新增 `truncateSafely(msg, 2000)` 顶层函数，单点截断覆盖下游 Log.d(L42) + callback(L56)
  - UTF-8 安全截断：用 `offsetByCodePoints` 按代码点截断，避免切断中文字符
  - data URI 专项截断：`startsWith("data:image/")` 时截断为前80字符 + 长度提示
  - 通用截断：>2000字符截断为前2000字符 + 截断提示
- [ ] 2.2 **RssParserByRule.kt L128**：image 进入 Debug.log 前预截断（双重保险），原 image 值保留用于渲染
- [ ] 2.3 **AppLog.kt putEntry L79 后**：同步应用 truncateSafely（复用 Debug.kt 逻辑）
- [ ] 2.4 添加截断相关日志（改造过程日志记录规范）：截断触发时记录原长度
- [ ] 2.5 编译验证 P0 修改无语法错误

## 3. P1-1 列表并行化（提速）

### 🔴 硬性前提（违反必崩溃，代码审查重点验证）

- [ ] 3.0a **硬性前提1**：每item独立 AnalyzeRule 实例（在 async 块内 new，不复用循环外 L44 的）
  - 依据：AnalyzeRule.kt L859-870 evalJSCallCount++/topScopeRef/scriptCache(HashMap) 并发非线程安全
  - 验证：grep 确认 async 块内有 `AnalyzeRule(ruleData, rssSource)` 调用
- [ ] 3.0b **硬性前提2**：articleList 不在并行块内 add
  - 依据：RssParserByRule.kt L43 mutableListOf 非线程安全，并行 add 丢数据/崩溃
  - 方案：async 返回 RssArticle?，awaitAll().filterNotNull().toMutableList() 后批量收集
  - 验证：grep 确认并行块内无 `articleList.add` / `items.add` 调用

### 实施步骤

- [ ] 3.1 RssParserByRule.kt L74：for 循环改为 `rssRules.map { rule -> async(Dispatchers.IO) { semaphore.withPermit { ... } } }.awaitAll()`
- [ ] 3.2 新增 Semaphore(6) 限流字段（companion object 或函数内局部）
- [ ] 3.3 getItem 改为返回 RssArticle?（异常返回 null，单个失败不影响整体）
- [ ] 3.4 awaitAll 后 `filterNotNull().toMutableList()` 批量收集（禁止并行块内 add）
- [ ] 3.5 添加并行化相关日志（启动/完成/单item耗时/失败数）
- [ ] 3.6 编译验证 P1-1 修改无语法错误
- [ ] 3.7 **代码审查复核**：确认 3.0a + 3.0b 两个硬性前提已满足

## 4. P1-2 解密结果缓存（提速）

- [ ] 4.1 确认 CacheManager 在 JS 引擎中的全局变量名（cache）
- [ ] 4.2 91 源 JS ruleImage：新增 cacheKey 生成逻辑（基于图片 URL 去参数）
- [ ] 4.3 91 源 JS ruleImage：新增 cache.get(cacheKey) 命中检查
- [ ] 4.4 91 源 JS ruleImage：解密后 cache.put(cacheKey, dataUri)
- [ ] 4.5 添加缓存命中/未命中日志（JS 层）
- [ ] 4.6 验证 JS 语法正确

## 5. 验证阶段

- [ ] 5.1 编译 APK
- [ ] 5.2 安装到模拟器
- [ ] 5.3 测试场景 S1：调试 91 大事件源 → 不崩溃 + 日志可读
- [ ] 5.4 测试场景 S2：浏览 91 大事件列表 → 首屏 < 8 秒
- [ ] 5.5 测试场景 S3：普通订阅源 → 无回归
- [ ] 5.6 测试场景 S4：网络异常 → 单个失败不影响整体
- [ ] 5.7 性能对比：列表加载耗时（改造前 vs 改造后）
- [ ] 5.8 二次刷新验证缓存命中（加载 < 2 秒）

## 6. 文档同步

- [ ] 6.1 更新 `app/src/main/assets/updateLog.md`（顶部追加日期条目）
- [ ] 6.2 更新 `docs/INDEX.md`（spec 状态标记）
- [ ] 6.3 更新 AGENTS.md 相关章节（如有架构变更说明）
- [ ] 6.4 更新项目记忆 basic-memory（决策记录）

## AOAdapt 日志

> 遇到问题时记录于此，便于追溯。

- [ ] 2026-07-14 任务启动
- [ ] 待记录...
