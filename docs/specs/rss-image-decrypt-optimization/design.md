# 技术设计：订阅源图片解密优化

## Technical Approach（技术方案）

### 三阶段修复

```
阶段1（P0）→ 阶段2（P1-1）→ 阶段3（P1-2）
调试截断    列表并行化      解密缓存
防崩溃      提速50%+        二次刷新提速
```

### 阶段1：P0 调试输出截断

**源码验证结论**（子代理深度验证）：
- `Debug.kt` L42 `Log.d("sourceDebug", msg)` 输出超长 msg 浪费 logcat 缓冲区
- `Debug.kt` L56 `it.printLog(state, printMsg)` callback 跨进程传输可能触发 `TransactionTooLargeException`（Binder 上限1MB）
- `RssParserByRule.kt` L128 `Debug.log(sourceUrl, "└${rssArticle.image ?: ""}", log)` 的 image 可能是 MB 级 base64 data URI

**修改点**（单点截断覆盖所有下游）：

1. **Debug.kt L41 后**（`var printMsg = msg` 之前）— 全局截断保护，单点覆盖 Log.d + callback
   ```kotlin
   // 伪代码（UTF-8 安全截断，避免切断中文字符）
   fun log(sourceUrl: String, msg: String, state: Int = 1) {
       // L41 后插入：单点截断（覆盖下游 Log.d L42 + callback L56）
       val safeMsg = truncateSafely(msg, 2000)
       // 原有逻辑使用 safeMsg 替代 msg
   }
   
   private fun truncateSafely(msg: String, maxLen: Int): String {
       if (msg.length <= maxLen) return msg
       // data URI 专项截断（前80字符 + 长度提示，避免 base64 撑爆）
       if (msg.startsWith("data:image/")) {
           return "${msg.substring(0, minOf(80, msg.length))}...(data URI 共${msg.length}字符，已截断)"
       }
       // 通用截断：按代码点截断，避免切断多字节中文字符
       val end = msg.offsetByCodePoints(0, minOf(maxLen, msg.codePointCount(0, msg.length)))
       return "${msg.substring(0, end)}...(已截断，总长${msg.length}字符)"
   }
   ```

2. **RssParserByRule.kt L128 区域** — data URI 在进入 Debug.log 前预截断（双重保险）
   ```kotlin
   // 伪代码
   val imageValue = rssArticle.image ?: ""
   val debugImage = if (imageValue.startsWith("data:image/")) {
       "${imageValue.substring(0, minOf(80, imageValue.length))}...(共${imageValue.length}字符)"
   } else {
       imageValue
   }
   Debug.log(sourceUrl, "└$debugImage", log)
   // 注意：rssArticle.image 原值保留用于实际渲染，不修改
   ```

3. **AppLog.kt putEntry L79 后**（`message?:return` 之后）— 同步应用截断（与 Debug.log 一致策略）
   - 风险低于 Debug（mLogs 是同进程内存 List，不跨 Binder），但为一致性也截断
   - 复用 `truncateSafely` 逻辑（提取为 Debug.kt 顶层函数或 AppLog companion）

### 阶段2：P1-1 列表并行化

**源码验证结论**（子代理深度验证，关键风险点）：
- `RssParserByRule.kt` L44: `val analyzeRule = AnalyzeRule(ruleData, rssSource)` — for循环外创建**单一实例**
- L105-106（getItem内）: `analyzeRule.setRuleData(rssArticle); analyzeRule.setContent(item)` — **并发修改同一实例状态会数据错乱**
- L43: `val articleList = mutableListOf<RssArticle>()` — **共享可变List，并行 add 非线程安全**
- `AnalyzeRule.kt` L859-870 evalJS: `evalJSCallCount++`（非原子）/ `topScopeRef`（互相覆盖）/ `scriptCache`(HashMap 非线程安全) — 复用同一实例并发 evalJS **必然崩溃/数据错乱**
- `RhinoScriptEngine.kt` L261-269: `Context.enter()` 基于 ThreadLocal，每线程独立 Context — **Rhino 引擎本身并行安全**，前提是独立 AnalyzeRule 实例

**修改点**：RssParserByRule.kt L74 for 循环改为并行（两个硬性前提）

**🔴 硬性前提1：每item独立 AnalyzeRule 实例**（非可选，违反必崩溃）
```kotlin
// 伪代码
val semaphore = Semaphore(6)  // 限流

// 关键改造：原 L44 单一 analyzeRule 实例废弃，改为每item内部创建
val deferredItems = rssRules.map { rule ->
    async(Dispatchers.IO) {
        semaphore.withPermit {
            // 硬性前提：每item独立 AnalyzeRule 实例（不复用循环外的）
            val analyzeRule = AnalyzeRule(ruleData, rssSource)
            try {
                getItem(sourceUrl, rule, analyzeRule, ...)  // 内部 setRuleData/setContent 修改独立实例
            } catch (e: Exception) {
                AppLog.put("RSS解析失败", e)
                null  // 单个失败不影响整体
            }
        }
    }
}
// 硬性前提2：awaitAll 后批量收集（不用并行 add，避免 articleList 并发崩溃）
val articleList = deferredItems.awaitAll().filterNotNull().toMutableList()
```

**🔴 硬性前提2：articleList 不在并行块内 add**（非可选，违反必丢数据/崩溃）
- ❌ 错误：`synchronized(items) { items.add(item) }` — 锁竞争 + 忘记加锁就崩溃
- ✅ 正确：`async` 返回 `RssArticle?`，`awaitAll().filterNotNull()` 后一次性 `toMutableList()`

### 阶段3：P1-2 解密结果缓存

**源码验证结论**（子代理深度验证）：
- `AnalyzeRule.kt` L847: `bindings["cache"] = CacheManager` — **JS 内 `cache.get/put` 直接可用**
- `CacheManager.kt` L19 `memoryLruCache` 是 `LruCache<String, Any>(50MB)` — **LruCache 内部线程安全**
- ⚠️ `CacheManager.kt` L69 `runBlocking(IO) { appDb.cacheDao.insert(cache) }` / L91 `runBlocking(IO) { appDb.cacheDao.get(key) }` — **runBlocking 阻塞调用线程**
  - 并行6个item同时 cache.get 会同时 runBlocking，6个线程被阻塞
  - IO调度器默认64线程，6个并行**不会死锁**，但浪费线程
  - 缓存命中时跳过网络+解密，即使 runBlocking 开销也远小于原方案

**修改点**：91 源 JS 的 ruleImage 字段

```javascript
// 伪代码（JS）
// legado JS 引擎已注入 cache 全局变量（CacheManager，AnalyzeRule.kt L847 确认）
function decryptImage(url) {
    var cacheKey = "91_img_" + url;  // 加源标识前缀，避免与其他源缓存冲突
    var cached = cache.get(cacheKey);
    if (cached) return cached;
    
    // 原 OkHttp 同步请求 + AES 解密逻辑
    var bytes = okhttp.newCall(req).execute().body().bytes();
    var decrypted = aesDecrypt(bytes, key, iv);  // key=密钥K
    var dataUri = "data:image/jpeg;base64," + base64Encode(decrypted);
    
    cache.put(cacheKey, dataUri, 3600);  // saveTime=3600秒（1小时），可按需调整
    return dataUri;
}
```

**注意事项**：
- cache.put 第三个参数 saveTime（秒），0=永久。建议设 3600~86400（1小时~1天），避免缓存陈旧
- cacheKey 加源标识前缀（`91_img_`），避免与其他源 URL 碰撞
- 密钥等敏感字段用代号（密钥K）替代，不写入文档

## Architecture Decisions（架构决策）

### ADR1：截断阈值 2000 字符

- **Context（上下文）**：
  - Android Binder 事务上限 1MB
  - TextView 显示超长字符串性能急剧下降
  - 调试信息需保留可读性（类型 + 前缀）
- **Decision（决策）**：全局截断阈值 2000 字符
- **Consequences（后果）**：
  - ✅ 防止 OOM/ANR/TransactionTooLargeException
  - ✅ 保留调试信息可读性
  - ⚠️ 超长文本被截断（可接受，调试只需看前缀）

### ADR2：并行限流 Semaphore(6)

- **Context（上下文）**：
  - AnalyzeRule 非线程安全，并发使用共享实例会数据错乱
  - 无限并发导致网络压力过大，可能触发目标站点限流
  - CPU 密集型（JS 执行）+ IO 密集型（网络）混合
- **Decision（决策）**：Semaphore(6) 限流，每个 item 独立 AnalyzeRule 实例
- **Consequences（后果）**：
  - ✅ 平衡并行速度与稳定性
  - ✅ 避免 AnalyzeRule 线程安全问题
  - ⚠️ 极端场景（网络极好）无法满速（可接受）

### ADR3：JS 内 CacheManager 缓存

- **Context（上下文）**：
  - data URI 无法被 Glide 磁盘缓存（ Glide 不识别 data URI）
  - 列表刷新会重新执行 JS → 重新网络请求 + AES 解密
  - Legado JS 引擎已注入 `cache` 全局变量（CacheManager）
- **Decision（决策）**：JS 内使用 `cache.get/put` 缓存解密结果
- **Consequences（后果）**：
  - ✅ 跨会话复用，二次刷新秒级加载
  - ✅ 无需改造 Glide 缓存机制
  - ⚠️ 内存占用略增（可接受，单张图片 ~70KB）

## Data Flow（数据流）

### 调试场景数据流

```
用户点击调试
    ↓
RssParserByRule.getItemList()
    ↓
analyzeRule.getString(ruleImage)  → 执行 JS → 返回 data URI
    ↓
判断 startsWith("data:image/")
    ↓ 是
截断为前 80 字符 + 长度提示
    ↓
Debug.log(截断后内容)
    ↓
AppLog.putEntry（同步截断）
    ↓
UI 显示（安全）
```

### 列表场景数据流

```
用户打开列表
    ↓
RssParserByRule.getItemList()
    ↓
rssRules.map { rule → async { ... } }  ← 并行启动
    ↓
Semaphore(6).withPermit { ... }  ← 限流
    ↓
新建 AnalyzeRule 实例
    ↓
analyzeRule.getString(ruleImage)
    ↓
JS 执行：cache.get(key) 命中？ → 直接返回
    ↓ 未命中
OkHttp 请求 + AES 解密 → cache.put(key, dataUri) → 返回
    ↓
awaitAll() 汇总结果
    ↓
返回 List<RssItem>
```

## File Changes（文件变更）

### 1. RssParserByRule.kt

- **L74 区域**：for 循环改 `map{async{}}.awaitAll()`
- **L128 区域**：调试输出前判断 data URI 并截断
- **新增**：Semaphore 限流字段（companion object）
- **新增**：独立 AnalyzeRule 实例创建逻辑

### 2. Debug.kt

- **L33 log 函数**：入口加截断保护（>2000 字符）
- **影响**：所有调用 log 的地方自动受益

### 3. AppLog.kt

- **putEntry 函数**：同步应用截断逻辑
- **影响**：日志写入前自动截断

### 4. 91 大事件源 JS（ruleImage）

- **新增**：cache.get/put 缓存逻辑
- **保留**：原有 OkHttp 请求 + AES 解密逻辑
- **注意**：密钥等敏感字段用代号（密钥K）替代，不写入文档

## 风险评估

### 源码验证后的真实风险（按严重度排序）

| 风险 | 概率 | 影响 | 缓解措施 | 验证状态 |
|------|------|------|---------|---------|
| **并行化忘记独立 AnalyzeRule 实例** | 高（若不强制） | 致命（数据错乱/崩溃） | 🔴 硬性前提1：tasks.md 明确列为前置条件 + 代码审查重点验证 | ✅ 源码确认 L44/L105-106/L859-870 |
| **并行化忘记保护 articleList** | 高（若不强制） | 致命（丢数据/崩溃） | 🔴 硬性前提2：awaitAll 后批量收集，禁止并行块内 add | ✅ 源码确认 L43 mutableListOf |
| **data URI 未截断触发 TransactionTooLargeException** | 高（91源） | 致命（Binder 崩溃） | P0 截断：Debug.kt L41 单点截断 + L128 预截断 | ✅ 源码确认 L128 image 可能 MB 级 |
| UTF-8 截断切断中文字符 | 中 | 低（乱码） | 用 offsetByCodePoints 按代码点截断 | ✅ 子代理建议 |
| CacheManager runBlocking 阻塞线程 | 中 | 低（线程浪费） | 缓存命中跳过网络+解密，净收益正；IO调度器64线程不死锁 | ✅ 源码确认 L69/L91 |
| Semaphore 限流值不当 | 低 | 中 | 6 可配置，验证阶段调整；OkHttp 连接池50空闲 | ✅ 源码确认 HttpHelper L91 |
| 截断误伤正常日志 | 低 | 低 | 仅 >2000 字符才截断，data URI 专项处理 | ✅ 设计保证 |
| CacheManager 内存溢出 | 低 | 中 | LruCache 50MB 上限，自动 LRU 淘汰 | ✅ 源码确认 CacheManager L19 |

### 已排除的风险（源码验证后确认安全）

| 风险点 | 排除依据 |
|--------|---------|
| Rhino JS 引擎并发不安全 | `RhinoScriptEngine.kt` L261-269 Context.enter() 基于 ThreadLocal，每线程独立 Context |
| AnalyzeRule 有共享静态状态 | `AnalyzeRule.kt` L960-986 companion object 只有 Pattern（不可变）+ 扩展函数 |
| OkHttpClient 每次 new 爆炸 | 短生命周期 GC 可回收，6个约15MB，不会爆炸（可后续优化为共享实例） |
| item 之间有状态依赖 | `RssParserByRule.kt` L73 variable 是 String? 不可变，L76 index==0 仅控制 log 开关 |

## 测试策略

- **单元测试**：截断函数边界用例（1999/2000/2001 字符）
- **集成测试**：91 源调试不崩溃 + 列表加载提速
- **回归测试**：普通源不受影响
