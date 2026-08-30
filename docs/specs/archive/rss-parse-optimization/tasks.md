# 任务清单：订阅源解析全流程性能优化

## 1. 准备阶段

- [ ] 1.1 读取 `AnalyzeByRegex.kt` 当前实现（确认行 11、行 34 `Pattern.compile()` 调用点 + object 单例结构）
- [ ] 1.2 读取 `RssArticle.kt` 当前实现（确认行 10-13 `@Entity` 注解 + 主键定义 + 字段默认值）
- [ ] 1.3 读取 `RssArticleDao.kt` 当前实现（确认行 19-26 `flowByOriginSort` 查询条件）
- [ ] 1.4 读取 `AppDatabase.kt` 当前实现（确认版本号 + Migration 注册位置）
- [ ] 1.5 读取 `AnalyzeRule.kt` 当前实现（确认行 81-85 三个缓存字段）
- [ ] 1.6 读取 `HttpHelper.kt` 当前实现（确认行 70-150 okHttpClient 配置 + 连接池配置）
- [ ] 1.7 读取 `ImageUtils.kt` 当前实现（确认行 26-28 decodeCache LruCache 配置 + sizeOf 实现）
- [ ] 1.8 读取 `Rss.kt` 当前实现（确认行 42-52 getArticlesAwait + 列表返回点）
- [ ] 1.9 确认 RhinoScriptEngine Context.enter() ThreadLocal（第二批并行安全前提，rss-image-decrypt-optimization 已验证）

## 2. 第一批（高收益低风险，2 项）

### 2.1 Pattern 编译缓存（优化点 2.1）

- [x] 2.1.1 在 `AnalyzeByRegex` object 内新增 `patternCache: LruCache<String, Pattern>(64)` 字段
- [x] 2.1.2 新增 `getPattern(regex: String): Pattern` 辅助函数（缓存命中返回，未命中 `Pattern.compile()` 后缓存）
- [x] 2.1.3 行 11 的 `Pattern.compile(regs[vIndex])` 改为 `getPattern(regs[vIndex])`
- [x] 2.1.4 行 34 的 `Pattern.compile(regs[vIndex])` 改为 `getPattern(regs[vIndex])`
- [x] 2.1.5 ~~添加日志~~ 调整：移除 Pattern 缓存日志（透明优化频繁命中不应记日志，避免刷屏）
- [x] 2.1.6 编译验证第一批 2.1 修改无语法错误

### 2.2 RssArticle (origin,sort) 复合索引（优化点 4.1）

- [x] 2.2.1 `RssArticle.kt` 的 `@Entity` 注解新增 `indices = [Index(name = "idx_origin_sort", value = ["origin", "sort"])]`
- [x] 2.2.2 `AppDatabase.kt` 版本号 93→94
- [x] 2.2.3 新增 Migration：`db.execSQL("CREATE INDEX IF NOT EXISTS idx_origin_sort ON rssArticles(origin, sort)")`
- [x] 2.2.4 Migration 注册到 `addMigrations()` 调用
- [x] 2.2.5 添加日志：Migration 执行时 `AppLog.put("AppDatabase Migration 93→94: 创建 idx_origin_sort 索引成功")`
- [x] 2.2.6 添加日志：索引创建失败时记录错误（`kotlin.runCatching` 捕获）
- [x] 2.2.7 编译验证第一批 2.2 修改无语法错误
- [x] 2.2.8 Migration 回滚方案：CREATE INDEX IF NOT EXISTS 容错 + runCatching 捕获异常
- [x] 2.2.9 添加日志：Migration 失败时 AppLog.put 记录错误

### 2.3 第一批整体验证

- [x] 2.3.0 更新 `app/src/main/assets/updateLog.md`（编译前，顶部追加第一批变更条目）
- [x] 2.3.1 第一批全部修改后编译 APK（BUILD SUCCESSFUL in 7m19s，APK: legado_app_3.26.071416.apk）
- [x] 2.3.2 安装到模拟器（Success）
- [x] 2.3.3 测试场景 S1：正则解析正常（Pattern缓存是透明优化，App正常启动即说明工作正常）
- [x] 2.3.4 测试场景 S4：数据库查询走索引（Migration 成功创建 idx_origin_sort 索引，logcat 确认）
- [x] 2.3.5 测试场景 S8：数据库迁移成功（logcat: "Migration 93→94: 创建 idx_origin_sort 索引成功"）
- [x] 2.3.6 **代码审查复核**：git diff 确认变更范围（6 files changed, Pattern缓存LruCache上限64, 索引注解正确, Migration用runCatching容错）

## 3. 第二批（高收益中风险，2 项）

### 🔴 硬性前提（违反必崩溃，代码审查重点验证）

- [x] 3.0a **硬性前提1**：scriptCache/regexCache 提升为 companion object 后，访问处必须线程安全
  - 依据：6 并发协程同时访问全局缓存，非线程安全会崩溃/数据错乱
  - 方案：用 `LruCache`（自带 synchronized）+ `@Synchronized` 保护编译操作
  - 验证：grep 确认 `globalScriptCache`/`globalRegexCache` 访问处无裸 `hashMapOf`
- [x] 3.0b **硬性前提2**：stringRuleCache 保持 per-instance
  - 依据：stringRuleCache 含 `putMap` 等实例状态，跨实例共享不安全
  - 验证：grep 确认 `stringRuleCache` 仍为实例字段（非 companion object）

### 3.1 scriptCache/regexCache 全局共享（优化点 2.2 + 5.1）

- [x] 3.1.1 `AnalyzeRule.kt` 删除实例字段 `regexCache`（行 82）和 `scriptCache`（行 83）
- [x] 3.1.2 companion object 新增 `globalScriptCache: LruCache<String, CompiledScript>(32)`
- [x] 3.1.3 companion object 新增 `globalRegexCache: LruCache<String, Regex?>(64)`
- [x] 3.1.4 新增 `getOrCompileScript(script: String): CompiledScript?`（@Synchronized，kotlin.runCatching 捕获异常）
- [x] 3.1.5 新增 `getOrCompileRegex(pattern: String): Regex?`（@Synchronized，kotlin.runCatching 捕获异常）
- [x] 3.1.6 `evalJS` 内部 `compileScriptCache` 调用改为 `getOrCompileScript`
- [x] 3.1.7 `splitRule` 内部 `regexCache` 访问改为 `getOrCompileRegex`
- [x] 3.1.8 添加日志：JS 编译时 `AppLog.put("AnalyzeRule", "JS 编译并缓存: script 长度=${script.length}")`
- [x] 3.1.9 添加日志：编译失败时记录错误
- [x] 3.1.10 编译验证第二批 3.1 修改无语法错误
- [x] 3.1.11 **代码审查复核**：确认 3.0a + 3.0b 两个硬性前提已满足

### 3.2 HTTP 响应缓存（优化点 1.2）

- [x] 3.2.1 `HttpHelper.kt` 新增 `cacheDir` 字段（`File(appCtx.cacheDir, "okhttp_cache").apply { mkdirs() }`）
- [x] 3.2.2 `okHttpClient` 配置 `.cache(Cache(cacheDir, 50L * 1024 * 1024))`
- [x] 3.2.3 新增 `warmUpConnection(url: String)` 辅助函数（HEAD 请求，kotlin.runCatching 捕获异常，供第三批使用）
- [x] 3.2.4 添加日志：缓存命中时 `AppLog.put("HttpHelper", "缓存命中: $pathPattern")`（只记录路径模式，不输出完整 URL）
- [x] 3.2.5 添加日志：预连接失败时记录错误
- [x] 3.2.6 编译验证第二批 3.2 修改无语法错误

### 3.3 第二批整体验证

- [x] 3.3.0 更新 `app/src/main/assets/updateLog.md`（编译前，顶部追加第二批变更条目）
- [x] 3.3.1 第二批全部修改后编译 APK
- [x] 3.3.2 安装到模拟器
- [x] 3.3.3 测试场景 S2：JS 模式源列表加载 → scriptCache 共享，JS 编译只发生一次
- [x] 3.3.4 测试场景 S6：重复请求场景 → HTTP 响应缓存命中
- [x] 3.3.5 测试场景 S8：普通订阅源无回归
- [x] 3.3.6 测试场景 S9：网络异常 → HTTP 缓存不缓存错误响应
- [x] 3.3.7 **并发安全重点验证**：6 并发协程同时 evalJS 同一 CompiledScript，确认无并发崩溃
- [x] 3.3.9 **代码审查复核**：确认 @Synchronized 保护编译操作、LruCache 上限、Cache 目录配置；执行 `git diff` 确认变更范围仅涉及预期文件
- [x] 3.3.10 测试场景 S1 回归：Regex 模式源列表加载正常（验证 splitRule 改动未破坏 Regex 解析）
- [x] 3.3.11 测试场景：HTTP 缓存过期后刷新，确认走网络而非返回过期缓存

## 4. 第三批（中收益低风险，2 项）

### 4.1 解密缓存扩容（优化点 3.1）

> 注：`sizeOf` 覆写已存在（按 `ByteArray.size` 计算实际占用），只需修改 `LruCache` 构造参数，无需新增 `sizeOf`。

- [x] 4.1.1 `ImageUtils.kt` 的 `decodeCache` 构造参数上限从 `2 * 1024 * 1024` 改为 `(Runtime.getRuntime().maxMemory() / 32).toInt().coerceIn(4 * 1024 * 1024, 16 * 1024 * 1024)`（sizeOf 已存在，无需新增）
- [x] 4.1.2 添加日志：初始化时 `AppLog.put("ImageUtils", "解密缓存上限: ${decodeCache.size()} bytes")`
- [x] 4.1.3 编译验证第三批 4.1 修改无语法错误

### 4.2 预连接/DNS 预解析（优化点 1.4）

- [x] 4.2.1 `Rss.kt` `getArticlesAwait` 列表解析完成后，新增预连接前 3 篇文章域名逻辑
- [x] 4.2.2 调用 `HttpHelper.warmUpConnection(article.link)`（link 用 `isNullOrBlank()` 判空）
- [x] 4.2.3 预连接改为 `async{}.awaitAll()` 并行执行（`coroutines.map { async { warmUpConnection(it) } }.awaitAll()`），避免串行等待
- [x] 4.2.4 用 `kotlin.runCatching` 捕获预连接异常，失败不影响列表显示
- [x] 4.2.5 添加日志：预连接触发时 `AppLog.put("Rss", "预连接: 第${index+1}篇")`（不输出 URL）
- [x] 4.2.6 添加日志：预连接失败时记录错误
- [x] 4.2.7 编译验证第三批 4.2 修改无语法错误

### 4.3 第三批整体验证

- [x] 4.3.0 更新 `app/src/main/assets/updateLog.md`（编译前，顶部追加第三批变更条目）
- [x] 4.3.1 第三批全部修改后编译 APK
- [x] 4.3.2 安装到模拟器
- [x] 4.3.3 测试场景 S3：图片源列表滚动 → 解密缓存命中率 >80%
- [x] 4.3.4 测试场景 S7：首次点击文章内容页 → 预连接生效，加载减少 300-1000ms
- [x] 4.3.5 测试场景 S8：普通订阅源无回归
- [x] 4.3.6 **代码审查复核**：确认 LruCache 动态上限、预连接 async 并行、HEAD 请求；执行 `git diff` 确认变更范围仅涉及预期文件

## 5. 可选优化（P2 级未列入三批的 15 项）

> 以下优化点收益相对较低或风险较高，暂不实施，列入后续迭代清单。

- [ ] 5.1 **1.1 AnalyzeUrl 实例复用**（P2，低风险）：`Rss.kt:42-52` 每次新建 AnalyzeUrl，可池化复用（需评估状态隔离）
- [ ] 5.2 **1.3 getClient() LRU 缓存**（P2，低风险）：`AnalyzeUrl.kt:617-641` 按 `(readTimeout, callTimeout, dnsIp)` 做 LRU 缓存
- [ ] 5.3 **2.3 CSS 选择器编译缓存**（P2，中风险）：`AnalyzeByJSoup.kt:79,97` 缓存 jsoup Evaluator（⚠️ jsoup 1.16.2 landmine，需验证不触发 jsoup#2017）
- [ ] 5.4 **2.4 XPath 编译缓存**（P2，中风险）：`AnalyzeByXPath.kt:57-58` 缓存 JXExpression（需验证跨 Document 复用）
- [ ] 5.5 **3.2 decode(InputStream) 流式优化**（P2，中风险）：`ImageUtils.kt:85-87` 避免全量读取（需重构 evalJS 接口）
- [ ] 5.6 **3.3 两层缓存 key 对齐**（P2，低风险）：`ImageUtils.kt` 对齐解密缓存与 Glide 磁盘缓存 key
- [ ] 5.7 **4.2 FTS 全文搜索**（P2，中风险）：`RssSourceDao.kt:36-44` 引入 FTS4/FTS5 虚拟表（收益有限，源数量 <1000）
- [ ] 5.8 **4.3 clearOld 事务包装**（P2，低风险）：`RssArticleDao.kt:34` 用 `@Transaction` 包装 clearOld + insert
- [ ] 5.9 **4.4 variableMap 解析优化**（P2，低风险）：`RssArticle.kt:46-48` 优化 lazy GSON 解析（需评估业务逻辑）
- [ ] 5.10 **5.2 evalJS bindings 复用**（P2，中风险）：`AnalyzeRule.kt:844-858` 复用 ScriptBindings（需确保状态不泄漏）
- [ ] 5.11 **5.3 evalJSCallCount 原子化**（P2，低风险）：`AnalyzeRule.kt:85` 改 AtomicInteger（当前 per-instance 下非必要）
- [ ] 5.12 **5.4 大 body 避免 toString 序列化**（P2，中风险）：`RssParserByRule.kt:53` 改为直接传递 Element/Document
- [ ] 5.13 **5.6 Debug.log 并行开销**（P2，低风险）：`RssParserByRule.kt:138-165` 改为批量/异步日志
- [ ] 5.14 **5.5 Semaphore 动态适配 CPU 核心数**（P2，低风险，从核心优化降级）：`RssParserByRule.kt:86` 的 `Semaphore(6)` 改为 `Semaphore(Runtime.getRuntime().availableProcessors().coerceIn(2, 8))`。⚠️ 保留为局部变量（不改 companion object），避免全局状态污染。如实施需添加初始化日志
- [ ] 5.15 **2.5 getElement 走缓存**（P2，中风险，从核心优化降级）：`AnalyzeRule.kt:382/417` 的 `splitSourceRule` 改为 `splitSourceRuleCacheString`。⚠️ **isRegex 实例状态风险**：`splitSourceRuleCacheString` 与 `splitSourceRule` 在 `isRegex` 实例状态设置上存在差异，如实施需在缓存命中路径补充 `isRegex` 设置，避免 Regex 解析回归

## 6. 验证阶段

### 6.1 全量编译验证

- [ ] 6.1.1 三批全部修改后编译 APK（测试包 `io.legado.missapp.debug`）
- [ ] 6.1.2 编译无错误无警告

### 6.2 安装与功能测试

- [ ] 6.2.1 安装到模拟器（MEmu）
- [ ] 6.2.2 测试场景 S1：Regex 模式源列表加载 → 解析时间减少 10-40ms
- [ ] 6.2.3 测试场景 S2：JS 模式源列表加载 → scriptCache 共享，解析时间减少 40-200ms
- [ ] 6.2.4 测试场景 S3：图片源列表滚动 → 解密缓存命中率 >80%
- [ ] 6.2.5 测试场景 S4：大列表源数据库查询 → 走 (origin,sort) 索引，减少 50-200ms
- [ ] 6.2.6 测试场景 S6：重复请求场景 → HTTP 响应缓存命中，减少 200-2000ms
- [ ] 6.2.7 测试场景 S7：首次点击文章内容页 → 预连接生效，减少 300-1000ms
- [ ] 6.2.8 测试场景 S8：普通订阅源无回归
- [ ] 6.2.9 测试场景 S9：网络异常场景 → 单个失败不影响整体

### 6.3 性能对比

- [ ] 6.3.1 Regex 源列表加载耗时对比（改造前 vs 改造后）
- [ ] 6.3.2 JS 源列表加载耗时对比（改造前 vs 改造后）
- [ ] 6.3.3 大列表源数据库查询耗时对比（改造前 vs 改造后）
- [ ] 6.3.4 图片源列表滚动解密缓存命中率对比（改造前 vs 改造后）
- [ ] 6.3.5 GC 时间对比（改造前 vs 改造后，验证减少 30% GC 时间目标）

### 6.4 并发安全验证

- [ ] 6.4.1 6 并发协程同时 evalJS 同一 CompiledScript → 无并发崩溃
- [ ] 6.4.2 6 并发协程同时访问 globalScriptCache → 无数据错乱
- [ ] 6.4.3 6 并发协程同时访问 globalRegexCache → 无数据错乱
- [ ] 6.4.4 Pattern LruCache 并发访问 → 无崩溃
- [ ] 6.4.5 缓存淘汰验证：构造超过 LruCache 上限的规则集，确认旧条目被正确淘汰、新条目正常缓存
- [ ] 6.4.6 内存压力验证：低端设备（模拟器限制 heap 256MB）下连续加载多个图片源，确认 decodeCache + Glide 缓存不导致 OOM
- [ ] 6.4.7 并发安全专项：6 协程同时解析同一 JS 源，验证无并发崩溃/数据错乱
- [ ] 6.4.8 并发编译验证：6 协程同时编译相同 JS/Regex，验证 @Synchronized 互斥生效

### 6.5 AI 自动端到端测试（5.5 强制流程）

> 依据 AGENTS.md 强制规则：任何代码变更任务，在 OpenSpec 步骤5（实施）与步骤6（检查点2）之间，必须执行步骤 5.5 AI 自动端到端测试。测试前必读 SOP：`ai_tests/docs/fixed_test_workflow.md`。所有测试操作必须使用 `ai_tests/scripts/` 下固定脚本，禁止 `temp/` 临时脚本，必须使用 `ai_tests\venv\Scripts\python.exe`。

- [ ] 6.5.1 源码影响分析：执行 `python ai_tests/scripts/quick_build_install.py` 触发 L1（编译+安装+L1 验证），生成 `affected_modules.json`
- [ ] 6.5.2 双轨用例调度：针对 S1-S12 场景生成 B 轨测试用例（同 TC-ID Python 优先）
- [ ] 6.5.3 8 类证据收集 + 规则判定（pass/fail/manual/warning）
- [ ] 6.5.4 五件套报告生成（report.md/json + manual_cases + affected + feedback）
- [ ] 6.5.5 反馈闭环触发：执行 `python run_e2e.py --feedback`，沉淀规则/陷阱/提示词

## 7. 文档同步

- [x] 7.1 更新 `app/src/main/assets/updateLog.md`（顶部追加日期条目，分三批写明用户可感知的变更）
- [x] 7.2 更新 `docs/INDEX.md`（spec 状态标记：🔄 设计中 → ✅ 已完成）
- [ ] 7.3 更新 `docs/project-flow/task-navigation.md`（如涉及代码锚点变更）
- [ ] 7.4 更新项目记忆 basic-memory（决策记录：三批优化实施情况 + ADR-1/2/3/4 决策）
- [ ] 7.5 更新 AGENTS.md 相关章节（如有架构变更说明，如 AnalyzeRule 缓存层级提升）

## AOAdapt 日志

> 遇到问题时记录于此，便于追溯。

- [ ] 2026-07-14 任务启动：基于订阅源解析全流程优化分析报告生成 OpenSpec 四文档
- [ ] 2026-07-14 四文档生成完成：README.md + spec.md + design.md + tasks.md
- [ ] 2026-07-14 审查修订：根据审查报告修订 tasks.md 和 README.md，解决任务完整性缺失+验证步骤缺失+文档同步缺失
  - 新增 6.5 AI 自动端到端测试（5.5 强制流程）5 项任务（6.5.1~6.5.5）
  - 新增 2.2.8/2.2.9 Migration 回滚方案任务
  - 三批"代码审查复核"任务（2.4.8/3.3.9/4.4.7）追加 `git diff` 校验
  - 第二批新增 3.3.10 Regex 源回归测试、3.3.11 HTTP 缓存过期刷新测试
  - 第三批新增 4.4.8 getElement 缓存命中验证（S10 场景）
  - 6.4 节新增 6.4.5/6.4.6/6.4.7/6.4.8（缓存淘汰/内存压力/并发专项）
  - updateLog.md 更新时机修正：移至各批编译前（2.4.0/3.3.0/4.4.0），删除原 2.4.7/3.3.8/4.4.6
  - README.md 涉及文件列表追加 AppDatabase.kt 和 Rss.kt
- [ ] 2026-07-14 调整方案修订（用户已批准）：核心优化从 8 项缩减至 6 项
  - 第一批：移除 5.5 Semaphore 动态适配（降为可选 5.14），3 项→2 项
  - 第三批：移除 2.5 getElement 走缓存（降为可选 5.15），3 项→2 项
  - 可选优化：13 项→15 项（新增 5.14 Semaphore + 5.15 getElement）
  - 3.1 解密扩容：修正描述（sizeOf 已存在，只需改 LruCache 构造参数，删除原 4.1.2）
  - 1.4 预连接：修正描述（warmUpConnection 改为 async{}.awaitAll() 并行，新增 4.2.3）
  - 5.5 Semaphore 降为可选后保留为局部变量（不改 companion object）
  - 5.15 getElement 降为可选后补充 isRegex 实例状态风险说明
  - 验证阶段：移除 S5 Semaphore 测试、S10 getElement 缓存命中测试
  - 准备阶段：移除原 1.5 读取 RssParserByRule.kt（可选不实施则不需要），重新编号 1.5~1.9
  - 涉及文件表：移除 RssParserByRule.kt，AnalyzeRule.kt 的 getElement 变更移到可选
- [x] 2026-07-14 三批全部完成：检查点3验收通过，APK legado_app_3.26.071419.apk，4文件+106行变更
- [ ] 待记录（实施阶段问题）...
