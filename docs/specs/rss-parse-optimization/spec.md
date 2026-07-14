# 需求规格：订阅源解析全流程性能优化

## Intent（意图）

优化订阅源（RSS源）解析全流程性能，针对网络请求层、规则引擎、图片加载、数据库、并发与内存五个维度，系统性消除已识别的 22 个性能瓶颈（5 个 P1 + 17 个 P2），达成以下用户可感知目标：

1. **列表加载提速**：Regex 模式源每项解析减少 0.5-2ms，含 JS 源每项减少 2-10ms，大列表源（>1000 条）减少 50-200ms
2. **降低 CPU/GC 开销**：消除 Pattern 重复编译、JS 重复编译、Map 重复分配，预计减少 30% GC 时间
3. **降低网络延迟**：HTTP 响应缓存命中时减少 200-2000ms，预连接减少首次内容页 300-1000ms
4. **适配设备性能**（可选）：Semaphore 限流根据 CPU 核心数动态适配，低端设备减少上下文切换（已降为可选，详见可选优化清单）

## Scope（范围）

### 涉及组件

| 组件 | 路径 | 变更范围 | 批次 |
|------|------|---------|------|
| AnalyzeByRegex | `model/analyzeRule/AnalyzeByRegex.kt` | 新增 Pattern LruCache | 第一批 |
| RssArticle | `data/entities/RssArticle.kt` | 新增 @Index 注解 | 第一批 |
| RssArticleDao | `data/dao/RssArticleDao.kt` | 配套 Migration | 第一批 |
| AnalyzeRule | `model/analyzeRule/AnalyzeRule.kt` | scriptCache/regexCache 提升为 companion | 第二批 |
| HttpHelper | `help/http/HttpHelper.kt` | OkHttp Cache 配置 | 第二批 |
| ImageUtils | `utils/ImageUtils.kt` | LruCache 扩容 | 第三批 |
| HttpHelper | `help/http/HttpHelper.kt` | 预连接逻辑 | 第三批 |
| RssParserByRule | `model/rss/RssParserByRule.kt` | Semaphore 动态适配（局部变量） | 可选 |
| AnalyzeRule | `model/analyzeRule/AnalyzeRule.kt` | getElement 走缓存 | 可选 |

### 22 个优化点清单

| 编号 | 优先级 | 优化点 | 批次 |
|------|--------|--------|------|
| 2.1 | P2 | AnalyzeByRegex Pattern 编译缓存（收益 10-40ms 不可感知，风险极低顺手做） | 第一批 |
| 4.1 | P1 | RssArticle 添加 (origin,sort) 复合索引（特定场景受益：>1000 条） | 第一批 |
| 2.2 | P1 | AnalyzeRule scriptCache/regexCache 全局共享 | 第二批 |
| 5.1 | P1 | AnalyzeRule 实例创建开销（结合 2.2） | 第二批 |
| 1.2 | P1 | HTTP 响应缓存（Cache 目录） | 第二批 |
| 3.1 | P2 | 解密缓存上限提升 | 第三批 |
| 1.4 | P2 | 预连接/DNS 预解析 | 第三批 |
| 5.5 | P2 | Semaphore 动态适配 CPU 核心数（局部变量改造，不移 companion） | 可选 |
| 2.5 | P2 | getElement/getElements 走缓存（含 isRegex 风险） | 可选 |
| 1.1 | P2 | AnalyzeUrl 实例复用 | 可选 |
| 1.3 | P2 | getClient() LRU 缓存 | 可选 |
| 2.3 | P2 | CSS 选择器编译缓存 | 可选 |
| 2.4 | P2 | XPath 编译缓存 | 可选 |
| 3.2 | P2 | decode(InputStream) 流式优化 | 可选 |
| 3.3 | P2 | 两层缓存 key 对齐 | 可选 |
| 4.2 | P2 | FTS 全文搜索 | 可选 |
| 4.3 | P2 | clearOld 事务包装 | 可选 |
| 4.4 | P2 | variableMap 解析优化 | 可选 |
| 5.2 | P2 | evalJS bindings 复用 | 可选 |
| 5.3 | P2 | evalJSCallCount 原子化 | 可选 |
| 5.4 | P2 | 大 body 避免 toString 序列化 | 可选 |
| 5.6 | P2 | Debug.log 并行开销 | 可选 |

### 不在范围内

- 不重构 AnalyzeRule 整体架构（仅提升缓存层级）
- 不升级 jsoup 1.16.2 / rhino 1.8.1 / hutool 5.8.22（landmine 锁定）
- 不改造 Legado JS 引擎同步模型
- 不修改 RssParserByRule 已有的并行化框架（rss-image-decrypt-optimization 已完成）
- 不实施 FTS 全文搜索（4.2 收益有限，源数量通常 <1000）
- 不实施流式解密（3.2 改动大，需重构 evalJS 接口）

## Approach（方案）

### 分三批实施

```
第一批（低风险顺手做）   → 第二批（高收益中风险） → 第三批（中收益低风险）
2 项，立即受益            2 项，需线程安全评估     2 项，补充优化
```

#### 第一批：低风险顺手做（2 项）

| 编号 | 优化点 | 文件 | 改动量 | 预估收益 |
|------|--------|------|--------|---------|
| 2.1 | Pattern LruCache 缓存 | AnalyzeByRegex.kt | 新增 ~15 行 | Regex 源每项减少 0.5-2ms（10-40ms 不可感知，风险极低顺手做） |
| 4.1 | @Index(origin,sort) + Migration | RssArticle.kt + RssArticleDao.kt | 新增 ~10 行 | 特定场景受益：大列表（>1000 条）减少 50-200ms |

#### 第二批：高收益中风险（2 项）

| 编号 | 优化点 | 文件 | 改动量 | 预估收益 |
|------|--------|------|--------|---------|
| 2.2+5.1 | scriptCache/regexCache 提升为 companion object + ConcurrentHashMap | AnalyzeRule.kt | 改动 ~30 行 | 含 JS 源每项减少 2-10ms，减少 30% GC |
| 1.2 | OkHttp Cache 目录配置 + Cache-Control 策略 | HttpHelper.kt | 新增 ~20 行 | 命中缓存减少 200-2000ms |

#### 第三批：中收益低风险（2 项）

| 编号 | 优化点 | 文件 | 改动量 | 预估收益 |
|------|--------|------|--------|---------|
| 3.1 | LruCache 上限按 maxMemory/32 动态设置 | ImageUtils.kt | 改动 ~5 行 | 图片源减少 80% 解密调用 |
| 1.4 | 列表解析后预连接前 N 篇文章域名（async 并行） | HttpHelper.kt + Rss.kt | 新增 ~15 行 | 首次内容页减少 300-1000ms |

### 可选优化清单（按需评估实施）

> 以下优化点未列入三批实施方案，作为补充清单按需评估。实施前需单独评估收益与风险，并补充对应 spec/design 章节。

| 编号 | 优化点 | 文件 | 改动量 | 收益评估 | 风险点 |
|------|--------|------|--------|---------|--------|
| 5.5 | Semaphore 动态适配 CPU 核心数（保留为局部变量） | RssParserByRule.kt | 改动 1 行 | 低端设备减少上下文切换 | 改变多源并发行为；Semaphore 是 `parseXML` 方法内局部变量，**不移至 companion object**，改为 `Semaphore(Runtime.getRuntime().availableProcessors().coerceIn(2, 8))` |
| 2.5 | getElement/getElements 走 splitSourceRuleCacheString | AnalyzeRule.kt | 改动 ~10 行 | getElements 路径每项减少 0.1-0.3ms | **isRegex 风险**：splitSourceRuleCacheString 签名扩展 allInOne 参数后，需确认 isRegex 路径语义不被缓存 key 误命中；allInOne=true 与 false 需用复合 key 隔离 |
| 1.1 | AnalyzeUrl 实例复用 | AnalyzeUrl.kt | 改动 ~20 行 | 减少 URL 解析开销 | 实例状态污染 |
| 1.3 | getClient() LRU 缓存 | AnalyzeUrl.kt | 改动 ~15 行 | 减少 OkHttpClient 创建 | 缓存过期策略 |
| 2.3 | CSS 选择器编译缓存 | AnalyzeByJSoup.kt | 改动 ~20 行 | 每字段 0.1-0.5ms | jsoup#2017 风险（需验证 Evaluator 是否绑定 Document） |
| 2.4 | XPath 编译缓存 | AnalyzeByXPath.kt | 改动 ~15 行 | 每字段 0.1-0.3ms | XPath 实例线程安全性 |
| 3.2 | decode(InputStream) 流式优化 | ImageUtils.kt | 改动 ~50 行 | 减少内存峰值 | 需重构 evalJS 接口 |
| 3.3 | 两层缓存 key 对齐 | ImageUtils.kt + AnalyzeRule.kt | 改动 ~10 行 | 减少缓存冗余 | key 规范统一 |
| 4.2 | FTS 全文搜索 | RssSourceDao.kt | 改动 ~30 行 | 全文搜索提效 | 收益有限（源数量 <1000） |
| 4.3 | clearOld 事务包装 | RssArticleDao.kt | 改动 ~5 行 | 减少事务开销 | 事务死锁风险 |
| 4.4 | variableMap 解析优化 | AnalyzeRule.kt | 改动 ~15 行 | 减少 Map 分配 | 语义等价性验证 |
| 5.2 | evalJS bindings 复用 | AnalyzeRule.kt | 改动 ~20 行 | 单次 <0.1ms | 状态泄漏风险 |
| 5.3 | evalJSCallCount 原子化 | AnalyzeRule.kt | 改动 ~3 行 | 并发计数准确 | AtomicInteger 开销 |
| 5.4 | 大 body 避免 toString 序列化 | AnalyzeRule.kt | 改动 ~20 行 | 减少 GC 压力 | 接口改造大 |
| 5.6 | Debug.log 并行开销 | Debug.kt | 改动 ~10 行 | 减少 log 开销 | 日志可读性 |

### Alternatives Considered（备选方案）

#### 备选1：FTS 全文搜索（4.2）— 不推荐

- **方案**：引入 FTS4/FTS5 虚拟表替换 RssSourceDao 的 LIKE 搜索
- **拒绝原因**：
  - RSS 源数量通常 <1000，全表扫描延迟可接受（<50ms）
  - FTS 需建表迁移 + 触发器同步，改动较大
  - 收益有限，优先级低于三批优化项
- **结论**：不采用，列入可选优化清单

#### 备选2：流式解密（3.2）— 不推荐

- **方案**：重构 `ImageUtils.decode(InputStream)` 为流式解密，避免 `readBytes()` 全量读取
- **拒绝原因**：
  - 当前 evalJS 接口传 ByteArray，流式需重构 JS 引擎接口
  - 改动大、风险高，影响所有书源/订阅源的图片处理
  - 解密缓存扩容（3.1）已能覆盖大部分场景
- **结论**：不采用，列入可选优化清单

#### 备选3：CSS 选择器编译缓存（2.3）— 暂不实施

- **方案**：在 AnalyzeByJSoup 层缓存 jsoup 的 `Evaluator`（选择器编译结果）
- **拒绝原因**：
  - jsoup 1.16.2 锁定（landmine），`Evaluator` 是否绑定 Document 需验证
  - 风险中等，需确认不触发 jsoup#2017 破坏性变更
  - 收益相对较低（每字段 0.1-0.5ms）
- **结论**：暂不实施，待 jsoup 升级路径明确后再评估

#### 备选4：evalJS bindings 复用（5.2）— 暂不实施

- **方案**：复用 `ScriptBindings` 对象，clear + rebind 而非每次新建
- **拒绝原因**：
  - bindings 复用需确保上一次执行的状态不泄漏到下次
  - 单次节省 <0.1ms，累积效果取决于 JS 调用频率
  - 风险中等，需大量回归测试
- **结论**：暂不实施，列入可选优化清单

## Drawbacks（缺点）

### 实施风险

| 缺点 | 影响 | 缓解措施 | 验证状态 |
|------|------|---------|---------|
| **scriptCache/regexCache 共享需线程安全** | AnalyzeRule.kt L81-85 当前 `hashMapOf` 非线程安全，共享后并发访问崩溃/数据错乱 | 改 `ConcurrentHashMap` 或 `LruCache`（自带同步），访问处加 `@Synchronized` | ⚠️ 待源码验证 |
| **HTTP 响应缓存时效性问题** | RSS 内容时效性要求高，缓存过期策略不当导致内容陈旧 | 仅缓存带 `Cache-Control` 头的响应；max-age 上限 5 分钟；缓存目录上限 50MB | ✅ 设计保证 |
| **缓存目录内存占用** | OkHttp Cache 目录占用磁盘空间，低端设备压力 | 设置 `maxSize` 上限（50MB），LRU 自动淘汰 | ✅ 设计保证 |
| **解密缓存扩容增加内存** | LruCache 从 2MB 提升至 8-16MB，低端设备内存压力 | 按 `Runtime.maxMemory()/32` 动态设置，最低 4MB 最高 16MB | ✅ 设计保证 |
| **Pattern LruCache 内存泄漏** | Pattern 对象持有编译后的 NFA/DFA 结构，缓存过多占用内存 | LruCache 上限 64 条（与 AnalyzeRule.regexCache 一致），LRU 自动淘汰 | ✅ 设计保证 |
| **Semaphore 动态值不稳定**（可选 5.5） | availableProcessors() 在不同设备返回不同值，行为不一致；改变多源并发行为 | `coerceIn(2,8)` 限定范围；保留为局部变量不移 companion | ✅ 设计保证（可选） |
| **预连接浪费流量** | 用户可能不点击预连接的文章，浪费 TCP/TLS 资源 | 仅预连接前 3 篇文章，连接池空闲超时 5 分钟自动回收 | ✅ 设计保证 |
| **RssArticle 索引增加写入开销** | 新增索引使 insert/update 变慢 | RSS 文章写入频率低（每次刷新），开销可接受 | ✅ 设计保证 |

### 已排除的风险

| 风险点 | 排除依据 |
|--------|---------|
| Rhino JS 引擎并发不安全 | RhinoScriptEngine Context.enter() 基于 ThreadLocal，每线程独立 Context（rss-image-decrypt-optimization 已验证） |
| AnalyzeRule 有共享静态状态 | companion object 只有 Pattern（不可变）+ 扩展函数 |
| OkHttpClient Cache 配置影响书源 | Cache 仅对带 Cache-Control 头的响应生效，书源请求不受影响 |
| RssArticle 索引迁移失败 | Room 自动迁移 + fallbackToDestructiveMigration 兜底 |

## Requirements（需求）

### R1：第一批 — Pattern 缓存（2.1）

- R1.1：在 `AnalyzeByRegex` object 内新增 `Pattern` LruCache，key=正则字符串，value=Pattern
- R1.2：LruCache 上限 64 条（与 AnalyzeRule.regexCache 一致）
- R1.3：`getElement`/`getElements` 调用时优先从缓存取 Pattern，未命中才 `Pattern.compile()`
- R1.4：Regex 模式源每项解析减少 0.5-2ms，20 项列表累积减少 10-40ms

### R2：第一批 — RssArticle 索引（4.1）

- R2.1：在 `RssArticle` 实体添加 `@Index(name = "idx_origin_sort", value = ["origin", "sort"])` 注解
- R2.2：编写 Room Migration（或在 AppDatabase 升级版本）创建索引
- R2.3：大文章量源（>1000 条）列表加载从 O(n) 降至 O(log n)
- R2.4：索引创建不破坏现有数据（fallbackToDestructiveMigration 兜底）

### R3：可选 — Semaphore 动态适配（5.5，已降为可选）

> ⚠️ 已从第一批移至可选清单。如实施，**保留为 `parseXML` 方法内局部变量**，不移至 companion object（避免改变多源并发行为）。

- R3.1：`RssParserByRule.parseXML` 内的 `Semaphore(6)`（局部变量）改为 `Semaphore(Runtime.getRuntime().availableProcessors().coerceIn(2, 8))`
- R3.2：低端设备（2-4 核）减少上下文切换，高端设备（8 核）提升吞吐
- R3.3：限流值每次 `parseXML` 调用时计算（`availableProcessors()` 本身是 native 缓存值，开销可忽略）；不移至 companion object 初始化，避免改变多源并发行为

### R4：第二批 — scriptCache/regexCache 全局共享（2.2 + 5.1）

- R4.1：将 `AnalyzeRule` 的 `scriptCache` 和 `regexCache` 从实例字段提升为 `companion object` 级别
- R4.2：`scriptCache` 改为 `LruCache<String, CompiledScript>`（上限 32 条，带同步）
- R4.3：`regexCache` 改为 `LruCache<String, Regex?>`（上限 64 条，带同步）
- R4.4：`stringRuleCache` 保持 per-instance（含 `putMap` 等实例状态）
- R4.5：含 JS 源每项解析减少 2-10ms，20 项列表累积减少 40-200ms
- R4.6：减少 AnalyzeRule 实例创建的 Map 分配开销，降低 30% GC 时间

### R5：第二批 — HTTP 响应缓存（1.2）

- R5.1：在 `HttpHelper.okHttpClient` 配置 `Cache(directory, maxSize)`，maxSize=50MB
- R5.2：缓存目录位于应用缓存目录下 `okhttp_cache/`
- R5.3：仅缓存带 `Cache-Control` 或 `ETag` 头的响应
- R5.4：RSS 源列表刷新命中缓存时减少 200-2000ms
- R5.5：缓存目录大小超限时 LRU 自动淘汰

### R6：第三批 — 解密缓存扩容（3.1）

- R6.1：`ImageUtils.decodeCache` 上限从 2MB 改为 `Runtime.maxMemory()/32`（最低 4MB，最高 16MB）
- R6.2：图片类源列表滚动减少 80% 解密调用
- R6.3：低端设备内存压力可控（maxMemory 小则缓存小）

### R7：可选 — getElement 走缓存（2.5，已降为可选）

> ⚠️ 已从第三批移至可选清单。如实施，需重点验证 isRegex 路径语义与 allInOne 缓存 key 隔离。

- R7.1：`AnalyzeRule.getElement`/`getElements` 改用 `splitSourceRuleCacheString`（带 LruCache 缓存版本）
- R7.2：扩展 `splitSourceRuleCacheString` 签名添加 `allInOne` 参数，缓存 key 用 `"allInOne=$allInOne|$ruleStr"` 复合形式区分语义
- R7.3：确认 `allInOne` 参数的语义差异不影响正确性，**特别是 isRegex 路径不被缓存 key 误命中**
- R7.4：getElements 路径每项减少 0.1-0.3ms

### R8：第三批 — 预连接（1.4）

- R8.1：列表解析完成后，对前 3 篇文章的 link 域名做 `okHttpClient` 预连接
- R8.2：预连接使用 `async{}.awaitAll()` **并行执行**（3 个 HEAD 请求并行，避免 forEach 串行累积 300-1500ms 延迟）
- R8.3：预连接使用 `ConnectionPool` 预热，HEAD 请求不下载 body
- R8.4：连接池空闲超时 5 分钟自动回收
- R8.5：首次内容页加载减少 300-1000ms（DNS+TCP+TLS）

### R9：通用要求

- R9.1：每批实施后编译验证无语法错误
- R9.2：每批实施后安装到模拟器回归测试
- R9.3：每批实施后更新 `updateLog.md`
- R9.4：改造过程添加日志（AppLog.put 记录缓存命中/未命中、限流值、预连接触发等关键节点）
- R9.5：异常处理用 `kotlin.runCatching`，错误用 `Coroutine.onError`，日志用 `AppLog.put()`

## Scenarios（场景）

### S1：Regex 模式源列表加载

- **前置**：用户导入一个使用 Regex 解析规则的 RSS 源，列表含 20 项
- **动作**：打开列表浏览
- **期望**：
  - 首屏加载时间比优化前减少 10-40ms
  - Pattern 编译只发生一次（首次解析），后续命中缓存
  - 6 并发协程共享 Pattern 缓存
  - 无回归问题

### S2：JS 模式源列表加载

- **前置**：用户导入一个 ruleImage/ruleTitle 含 `<js>...</js>` 的 RSS 源，列表含 20 项
- **动作**：打开列表浏览
- **期望**：
  - 首屏加载时间比优化前减少 40-200ms
  - Rhino JS 编译只发生一次（首次解析），后续命中 scriptCache
  - 6 并发协程共享 scriptCache，无 JS 重复编译
  - AnalyzeRule 实例创建开销降低（Map 分配减少）

### S3：图片源列表滚动

- **前置**：用户浏览一个图片类 RSS 源，列表含 50+ 张图片
- **动作**：快速上下滚动列表
- **期望**：
  - 解密缓存命中率 >80%（扩容后）
  - 滚动不卡顿
  - 内存占用不超过 maxMemory/32
  - 重复解密次数显著减少

### S4：大列表源数据库查询

- **前置**：某 RSS 源已积累 2000+ 篇文章
- **动作**：打开该源列表
- **期望**：
  - 列表加载时间比优化前减少 50-200ms
  - 数据库查询走 (origin, sort) 复合索引
  - 查询效率从 O(n) 降至 O(log n)
  - 不破坏现有数据

### S5：低端设备适配（Semaphore 部分依赖可选优化 5.5）

- **前置**：在 2 核低端设备上使用
- **动作**：打开 RSS 源列表
- **期望**：
  - **若实施可选优化 5.5**：Semaphore 限流值为 2（coerceIn(2,8) 下限），减少上下文切换开销，不出现过度并发导致的卡顿
  - **未实施 5.5 时**：维持原 `Semaphore(6)` 行为，依赖 RSS 源数量本身限制并发
  - 解密缓存上限自动调整为 maxMemory/32（较低值）（第三批 3.1 始终生效）

### S6：重复请求场景

- **前置**：用户下拉刷新 RSS 源列表，5 秒内再次刷新同一源
- **动作**：连续下拉刷新
- **期望**：
  - 第二次刷新命中 HTTP 响应缓存
  - 加载时间减少 200-2000ms（取决于网络延迟）
  - 缓存过期后自动重新请求（max-age 上限 5 分钟）
  - **可达成性前提**：RSS 源请求需使用不带 `Cache-Control: no-cache` 请求头的 OkHttpClient（详见 design.md 1.2 "no-cache 请求头处理"章节），否则 OkHttp Cache 因 no-cache 指令跳过缓存命中
  - 隔离影响：仅 RSS 源请求使用专用客户端，书源请求不受影响（仍用原 okHttpClient 带 no-cache）

### S7：首次点击文章内容页

- **前置**：用户在 RSS 源列表中浏览，列表已加载完成
- **动作**：点击列表前 3 篇文章中的任意一篇
- **期望**：
  - 内容页加载时间减少 300-1000ms（DNS+TCP+TLS 已预连接）
  - 预连接未点击的文章连接池 5 分钟后自动回收
  - 不浪费流量（仅 TCP/TLS 预连接，不发起实际请求）

### S8：普通订阅源无回归

- **前置**：用户使用普通 RssSource（无 JS/Regex/图片解密）
- **动作**：调试 + 列表浏览
- **期望**：
  - 列表加载速度与改造前一致或更优
  - 调试功能正常
  - 无回归问题

### S9：网络异常场景

- **前置**：部分 RSS 源 URL 不可达
- **动作**：列表加载
- **期望**：
  - 单个源失败不影响其他源
  - 失败源显示错误提示
  - HTTP 缓存不缓存错误响应
  - 预连接失败不影响列表显示

### S10：JS 源并发解析无崩溃

- **前置**：用户导入一个 ruleImage/ruleTitle 含 `<js>...</js>` 的 RSS 源，列表含 20 项，6 并发协程同时解析同一源
- **动作**：打开列表浏览，触发 6 并发协程同时 evalJS 同一 CompiledScript
- **期望**：
  - 无并发崩溃、无 ConcurrentModificationException
  - 无数据错乱（每项解析结果与串行一致）
  - globalScriptCache 全局共享，JS 编译只发生一次
  - RhinoScriptEngine Context.enter() 基于 ThreadLocal，每线程独立 Context
  - topScopeRef/evalJSCallCount 保持 per-instance，不跨实例污染

### S11：JS/Regex 编译 @Synchronized 互斥验证

- **前置**：6 并发协程同时首次编译相同 JS 脚本和相同 Regex 字符串（缓存未命中场景）
- **动作**：并发触发 getOrCompileScript / getOrCompileRegex
- **期望**：
  - @Synchronized 注解保证编译操作原子性，同一时刻仅一个线程执行 compile()
  - 编译结果仅写入 globalScriptCache/globalRegexCache 一次（非 6 次）
  - 其余 5 个线程阻塞等待，命中缓存后直接返回
  - 无重复编译、无缓存覆盖竞态
  - LruCache 自带 synchronized 保护 get/put 操作

### S12：LruCache LRU 淘汰行为验证

- **前置**：向 globalScriptCache（上限 32 条）/globalRegexCache（上限 64 条）/patternCache（上限 64 条）注入超过上限数量的规则
- **动作**：循环注入 N+1 条规则（N 为上限）
- **期望**：
  - 最久未使用的规则被淘汰（LRU 策略）
  - 缓存 size() 不超过上限
  - 被淘汰的规则再次访问时重新编译（缓存未命中）
  - 热点规则不被淘汰（最近访问的保留）
  - 无内存泄漏（Pattern/CompiledScript 被 GC 回收）
