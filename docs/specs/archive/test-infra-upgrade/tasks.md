# Tasks: 测试基础设施升级 - 端到端真机级调试能力

> 状态：⚠️ 代码实现完成，测试验证缺失（2026-06-18）
> 创建日期：2026-06-18
> 优先级：P0
> 详见：[design.md 第 7 章 实施差异与后续优化](./design.md#7-实施差异与后续优化2026-06-18-实施后补充)

## 完成总结

### P0 代码实现已完成（2026-06-18）

| 分组 | 状态 | 说明 |
|------|------|------|
| 1. AnalyzeUrl 移植 | ✅ 代码完成 | 从真机 957 行源码提取，剥离 Android 依赖（单元测试未编写） |
| 2. Mock 层实现 | ✅ 代码完成 | MockCookieStore/MockCacheManager/MockSource/MockBook/StrResponse（单元测试未编写） |
| 3. AnalyzeRule 修复 | ✅ 代码完成 | evalJS 注入 13 变量 + NativeObject 处理 + put/get 层级（单元测试未编写） |
| 4. MockJsExtensions 扩展 | ✅ 代码完成 | ajax/connect/getCookie/加密函数 50+ 个（createAsymmetricCrypto 未实施，单元测试未编写） |
| 5. DebugLogger 实现 | ✅ 代码完成 | 真机级日志格式（︾︽⇒┌└≡◇ + state 状态码）（单元测试未编写） |
| 6. BookSourceDebugger | ✅ 代码完成 | search→detail→toc→content 端到端链路（debugExplore 未实施，集成测试未编写） |
| 7. RssSourceDebugger | ✅ 代码完成 | sort→content 端到端链路（集成测试未编写） |
| 8. RuleEngineServer | ✅ 代码完成 | analyzeUrl/debugBookSource/debugRssSource 命令路由（集成测试未编写） |
| 9. Python 客户端 | ✅ 代码完成 | analyze_url/debug_book_source/debug_rss_source + 流式读取（jvm_helpers.py 未修改，集成测试未编写） |
| 11. 构建与打包 | ✅ 完成 | JAR 构建成功，启动验证通过 |
| 12. 回测验证 | ❌ 未执行 | 仅基础运行验证，未用真实书源/订阅源回测 |

### P1 文档更新已完成（2026-06-18）

| 分组 | 状态 | 说明 |
|------|------|------|
| 10. SKILL.md 文档更新 | ✅ 完成 | Phase 3 章节、JVM 架构、API 速查表、检查清单、降级路径 |
| 13. basic-memory 经验反哺 | ✅ 完成 | 3条经验笔记 + 1条执行证据 |

### 后续待完成（P2）

| 分组 | 状态 | 说明 |
|------|------|------|
| 单元测试 | ✅ 已完成 | 已在 skill-deep-optimization-v2 阶段三完成（AnalyzeUrl 12用例/MockCookieStore 8用例/AnalyzeRule 15用例/MinimalMockJsExtensions 10用例） |
| 集成测试 | ✅ 已完成 | 已在 skill-deep-optimization-v2 阶段三完成（简单书源/加密书源/失败定位/变量链/订阅源 5场景） |
| 回测验证 | ✅ 已完成 | 已在 skill-deep-optimization-v2 阶段三完成（3真实书源+2真实订阅源回测） |
| jvm_helpers.py 修改 | ❌ 未执行 | task 9.12（可信度评估新增"端到端调试通过"判定） |
| debugExplore 实现 | ❌ 未执行 | 发现页调试功能 |
| createAsymmetricCrypto 实现 | ❌ 未执行 | RSA 加解密支持（已列入 SKILL.md 不实现清单） |
| 非功能验收 | ❌ 未执行 | 启动时间/执行时间/日志延迟/内存占用 |

## 任务清单

### 1. AnalyzeUrl 移植（P0）

- [ ] 1.1 从真机 `app/.../model/analyzeRule/AnalyzeUrl.kt` 提取核心逻辑，创建 `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/AnalyzeUrl.kt`
- [ ] 1.2 实现 `initUrl()` 三步流水线（analyzeJs → replaceKeyPageJs → analyzeUrl）
- [ ] 1.3 实现 `analyzeJs()` - `@js:`/`<js>` 标签求值，支持 `@result` 占位符
- [ ] 1.4 实现 `replaceKeyPageJs()` - `{{js}}` 内嵌 JS 替换 + `<page,page>` 页数列表
- [ ] 1.5 实现 `analyzeUrl()` - URL + JSON 选项解析（UrlOption 14 字段）
- [ ] 1.6 实现 `setCookie()` - 合并 MockCookieStore + header Cookie
- [ ] 1.7 实现 `executeStrRequest()` - GET/POST/HEAD 请求执行
- [ ] 1.8 实现 POST body 处理（form 编码 / json body / 原始 body）
- [ ] 1.9 实现 charset 编码处理（UTF-8/GBK/escape）
- [ ] 1.10 实现错误码映射（-1 到 -7）
- [ ] 1.11 实现 `evalJS()` 注入变量（java/cookie/cache/source/book/page/key/result 等）
- [ ] 1.12 剥离 Android 依赖（CookieStore→MockCookieStore、BackstageWebView→抛异常、Coroutine→同步）
- [ ] 1.13 单元测试：AnalyzeUrl 三步流水线
- [ ] 1.14 单元测试：UrlOption 字段解析
- [ ] 1.15 单元测试：错误码映射

### 2. Mock 层实现（P0）

- [ ] 2.1 创建 `MockCookieStore.kt` - 二级域名 Cookie 存储（getCookie/setCookie/removeCookie/getCookieByKey）
- [ ] 2.2 创建 `MockCacheManager.kt` - 内存缓存（get/put/delete，支持过期时间）
- [ ] 2.3 创建 `MockSource.kt` - BookSource/RssSource 上下文（fromJson、getHeaderMap、enabledCookieJar、variableMap）
- [ ] 2.4 创建 `MockBook.kt` - Book/BookChapter 上下文（name/author/bookUrl/tocUrl/variableMap/chapters）
- [ ] 2.5 创建 `StrResponse.kt` - 真机 StrResponse 简化版（url + body + code + callTime）
- [ ] 2.6 单元测试：MockCookieStore 二级域名提取
- [ ] 2.7 单元测试：MockSource JSON 解析

### 3. AnalyzeRule 修复（P0）

- [ ] 3.1 修改 `AnalyzeRule.kt` 构造函数，接收 MockSource/MockBook/MockBookChapter 上下文
- [ ] 3.2 修复 `evalJS()` 注入 13 个变量（java/cookie/cache/source/book/chapter/title/src/result/baseUrl/nextChapterUrl/rssArticle/fromBookInfo）
- [ ] 3.3 修复 `getStringList()`/`getString()` 处理 Rhino NativeObject（键值访问）
- [ ] 3.4 修复 `getStringList()`/`getString()` 处理 gson LinkedTreeMap（键值访问）
- [ ] 3.5 修复 `put(key, value)` 层级存储（chapter → book → source）
- [ ] 3.6 修复 `get(key)` 层级查找（chapter → book → source）+ 特殊键 bookName/title
- [ ] 3.7 单元测试：evalJS 变量注入完整性
- [ ] 3.8 单元测试：NativeObject/LinkedTreeMap 键值访问
- [ ] 3.9 单元测试：put/get 层级存储

### 4. MockJsExtensions 扩展（P0/P1）

- [ ] 4.1 修改 `ajax(url)` - 携带 MockCookieStore Cookie + MockSource header
- [ ] 4.2 修改 `ajax(url)` - 支持 POST body（通过 AnalyzeUrl 解析 URL 选项）
- [ ] 4.3 实现 `ajaxAll(urls)` - 串行执行（替代返回空数组）
- [ ] 4.4 实现 `connect(url)` - 返回 StrResponse（替代抛异常）
- [ ] 4.5 实现 `connect(url, header)` - 带 header
- [ ] 4.6 实现 `get(url, headers)` / `head(url, headers)` / `post(url, body, headers)` - jsoup Connection.Response
- [ ] 4.7 实现 `getCookie(tag)` - 从 MockCookieStore 获取
- [ ] 4.8 实现 `getCookie(tag, key)` - 获取单个 key
- [ ] 4.9 实现 `cacheFile(url)` / `cacheFile(url, saveTime)` - 缓存到 MockCacheManager
- [ ] 4.10 实现 `md5Encode16(str)` - 16 位 MD5
- [ ] 4.11 实现 `sha1Encode(str)` / `sha256Encode(str)`
- [ ] 4.12 实现 `hmacSHA1(data, key)` / `hmacSHA256(data, key)`
- [ ] 4.13 实现 `digestHex(data, algorithm)` / `digestBase64Str(data, algorithm)`
- [ ] 4.14 实现 `base64Decode(str, charset)` / `base64DecodeToByteArray(str)` / `base64Encode(str, flags)`
- [ ] 4.15 实现 `hexEncodeToString(utf8)` / `strToBytes(str, charset)` / `bytesToStr(bytes, charset)`
- [ ] 4.16 单元测试：ajax 携带 Cookie/Header
- [ ] 4.17 单元测试：connect 返回 StrResponse
- [ ] 4.18 单元测试：加密函数（md5Encode16/sha1/sha256/hmac）

### 5. DebugLogger 实现（P0）

- [ ] 5.1 创建 `DebugLogger.kt` - 真机级调试日志输出器
- [ ] 5.2 实现 `log(msg, state, html, showTime)` - 输出 `[mm:ss.SSS] {msg}` 格式
- [ ] 5.3 实现特殊符号输出（`︾` 开始解析、`︽` 解析完成、`⇒` 提示、`┌` 获取字段开始、`└` 获取字段结果、`≡` 状态信息、`◇` 统计信息）
- [ ] 5.4 实现 state 状态码（1/10/20/30/40/-1/1000）
- [ ] 5.5 实现 HTML 源码输出（state=10/20/30/40 时附带 html 字段）
- [ ] 5.6 实现 `error(msg, stackTrace, failedStage)` - 错误日志（state=-1）
- [ ] 5.7 实现 `result(success, summary)` - 完成日志（state=1000）
- [ ] 5.8 实现流式输出（每行 `println` + `System.out.flush()`）
- [ ] 5.9 单元测试：日志格式与真机一致
- [ ] 5.10 单元测试：时间戳计算

### 6. BookSourceDebugger 实现（P0）

- [ ] 6.1 创建 `BookSourceDebugger.kt` - 端到端书源调试器
- [ ] 6.2 实现 `debug()` 入口 - 根据 key 格式分发（isAbsUrl→详情、`::`→发现、`++`→目录、`--`→正文、else→搜索）
- [ ] 6.3 实现 `debugSearch()` - 搜索阶段（AnalyzeUrl + AnalyzeRule + 字段提取日志）
- [ ] 6.4 实现 `debugInfo(bookUrl)` - 详情阶段（含 ruleBookInfo.init 执行 + 变量持久化）
- [ ] 6.5 实现 `debugToc(tocUrl)` - 目录阶段（含 nextTocUrl 分页循环，最大 100 页）
- [ ] 6.6 实现 `debugContent(chapterUrl)` - 正文阶段（含 nextContentUrl 分页 + replaceRegex）
- [ ] 6.7 实现字段提取日志（`┌获取书名`/`└{name}` 等，与真机一致）
- [ ] 6.8 实现统计日志（`◇书籍总数:N`/`◇目录总数:N`）
- [ ] 6.9 实现错误处理（异常捕获 + `logger.error` + state=-1）
- [ ] 6.10 实现变量跨阶段持久化（MockBook.variableMap）
- [ ] 6.11 实现 Cookie 跨阶段持久化（MockCookieStore）
- [ ] 6.12 集成测试：简单书源端到端（场景 1）
- [ ] 6.13 集成测试：含加密的书源（场景 4）
- [ ] 6.14 集成测试：失败阶段定位（场景 7）
- [ ] 6.15 集成测试：变量链传递（场景 8）

### 7. RssSourceDebugger 实现（P0）

- [ ] 7.1 创建 `RssSourceDebugger.kt` - 端到端订阅源调试器
- [ ] 7.2 实现 `debug()` 入口 - 根据 key 格式分发（`::`→分类、isAbsUrl→内容、else→搜索）
- [ ] 7.3 实现 `debugSort()` - 列表阶段（AnalyzeUrl + RssParserByRule 逻辑 + 字段提取日志）
- [ ] 7.4 实现 `debugContent(articleUrl)` - 内容阶段
- [ ] 7.5 实现 ruleNextPage 分页支持
- [ ] 7.6 实现字段提取日志（`┌获取标题/时间/描述/图片url/文章链接`）
- [ ] 7.7 实现错误处理
- [ ] 7.8 集成测试：订阅源端到端（场景 5）

### 8. RuleEngineServer 命令路由（P0）

- [ ] 8.1 修改 `RuleEngineServer.kt` - 新增 `analyzeUrl` 命令路由
- [ ] 8.2 新增 `debugBookSource` 命令路由（接收 sourceJson + key，调用 BookSourceDebugger）
- [ ] 8.3 新增 `debugRssSource` 命令路由（接收 sourceJson + key，调用 RssSourceDebugger）
- [ ] 8.4 实现流式响应输出（端到端命令期间，每条日志立即输出）
- [ ] 8.5 实现命令结束标志（type=result 或 type=error）
- [ ] 8.6 集成测试：analyzeUrl 命令
- [ ] 8.7 集成测试：debugBookSource 命令流式输出
- [ ] 8.8 集成测试：debugRssSource 命令流式输出

### 9. Python 客户端升级（P0）

- [ ] 9.1 修改 `tools/rule_engine_client.py` - 新增 `analyze_url(url, key, page, source_json)` 方法
- [ ] 9.2 新增 `debug_book_source(source_json, key, callback)` 方法 - 支持流式日志回调
- [ ] 9.3 新增 `debug_rss_source(source_json, key, callback)` 方法 - 支持流式日志回调
- [ ] 9.4 实现流式读取（逐行读取 stdout，解析 JSON，调用 callback）
- [ ] 9.5 实现 callback 接口（on_log/on_error/on_result）
- [ ] 9.6 创建 `scripts/debug-source.py` - 端到端调试脚本
- [ ] 9.7 实现 `--source`/`--key`/`--stage` 参数解析
- [ ] 9.8 实现实时日志打印（与真机格式一致）
- [ ] 9.9 实现 HTML 源码收集（state=10/20/30/40）
- [ ] 9.10 实现验证报告输出（4 阶段通过情况 + 失败阶段 + 不可仿真项 + 可信度评估）
- [ ] 9.11 实现退出码（0=成功，1=部分失败，2=严重错误）
- [ ] 9.12 修改 `tools/jvm_helpers.py` - 可信度评估新增"端到端调试通过"判定
- [ ] 9.13 标记 `scripts/deep-verify.py` 为 deprecated（文件头部添加警告）
- [ ] 9.14 集成测试：debug-source.py 端到端

### 10. SKILL.md 文档更新（P1）

- [x] 10.1 更新 `SKILL.md` Phase 3 测试驱动章节 - 新增端到端调试流程 ✅ 2026-06-18
- [x] 10.2 更新 `SKILL.md` JVM 测试基础设施章节 - 新增 AnalyzeUrl/BookSourceDebugger/RssSourceDebugger 说明 ✅ 2026-06-18
- [x] 10.3 更新 `SKILL.md` RuleEngineClient API 速查表 - 新增 analyze_url/debug_book_source/debug_rss_source ✅ 2026-06-18
- [x] 10.4 更新 `SKILL.md` Phase 3 完成检查清单 - 新增端到端调试项 ✅ 2026-06-18
- [x] 10.5 更新 `AI_README.md` 脚本清单 - 新增 debug-source.py ✅ 2026-06-18
- [x] 10.6 更新 `SKILL.md` 降级路径 - JVM 不可用时降级说明 ✅ 2026-06-18

### 11. 构建与打包（P0）

- [ ] 11.1 更新 `tools/mvp1-build/build.gradle.kts` - 确认依赖（OkHttp/jsoup/hutool/rhino/json-path/JsoupXpath）
- [ ] 11.2 构建新版 JAR（`tools/legado-rule-engine-mvp4.jar` 替换）
- [ ] 11.3 验证 JAR 启动正常（`java -jar legado-rule-engine-mvp4.jar` ping 命令）
- [ ] 11.4 验证新命令可用（analyzeUrl/debugBookSource/debugRssSource）

### 12. 回测验证（P0）

- [ ] 12.1 回测：已知正常书源端到端调试（4 阶段全部通过）
- [ ] 12.2 回测：已知问题书源端到端调试（精确定位失败阶段）
- [ ] 12.3 回测：订阅源端到端调试
- [ ] 12.4 回测：含加密的书源端到端调试
- [ ] 12.5 回测：需登录的书源（输出警告 + 标记 unverifiable）
- [ ] 12.6 回测：含 CF 盾的书源（输出警告 + 标记 unverifiable）
- [ ] 12.7 日志格式对比：与真机 Debug 日志对比（时间戳/符号/state 一致）
- [ ] 12.8 用户真机导入验证：生成的书源导入手机无报错

### 13. basic-memory 经验反哺（P1）

- [x] 13.1 将 AnalyzeUrl 移植经验写入 basic-memory（note_type=experience, tags=["jvm-evolution","analyzeurl"]） ✅ 2026-06-18
- [x] 13.2 将端到端调试器设计经验写入 basic-memory（note_type=pattern, tags=["debugger","e2e"]） ✅ 2026-06-18
- [x] 13.3 将 MockJsExtensions 扩展经验写入 basic-memory（note_type=experience, tags=["mock","jsextensions"]） ✅ 2026-06-18
- [x] 13.4 更新 SKILL.md 陷阱速查表（如有新发现的陷阱） ✅ 2026-06-18（本轮无新陷阱发现）

## 任务依赖关系

```
1. AnalyzeUrl 移植 ─┬─→ 6. BookSourceDebugger ─┬─→ 8. RuleEngineServer ─┬─→ 9. Python 客户端 ─┬─→ 12. 回测验证
                    │                          │                       │                    │
2. Mock 层 ─────────┘                          │                       │                    │
                                              │                       │                    │
3. AnalyzeRule 修复 ──────────────────────────┤                       │                    │
                                              │                       │                    │
4. MockJsExtensions 扩展 ─────────────────────┤                       │                    │
                                              │                       │                    │
5. DebugLogger ───────────────────────────────┘                       │                    │
                                                                      │                    │
7. RssSourceDebugger ─────────────────────────────────────────────────┘                    │
                                                                                           │
10. SKILL.md 文档更新 ─────────────────────────────────────────────────────────────────────┤
                                                                                           │
11. 构建与打包 ────────────────────────────────────────────────────────────────────────────┤
                                                                                           │
13. basic-memory 经验反哺 ─────────────────────────────────────────────────────────────────┘
```

## 优先级分组

### P0（必须完成，阻塞回测验证）

- 1. AnalyzeUrl 移植（1.1-1.15）
- 2. Mock 层实现（2.1-2.7）
- 3. AnalyzeRule 修复（3.1-3.9）
- 4. MockJsExtensions 扩展 - 网络类（4.1-4.6, 4.7-4.9）
- 5. DebugLogger 实现（5.1-5.10）
- 6. BookSourceDebugger 实现（6.1-6.15）
- 7. RssSourceDebugger 实现（7.1-7.8）
- 8. RuleEngineServer 命令路由（8.1-8.8）
- 9. Python 客户端升级（9.1-9.14）
- 11. 构建与打包（11.1-11.4）
- 12. 回测验证（12.1-12.8）

### P1（重要，不阻塞核心功能）

- 4. MockJsExtensions 扩展 - 加密/编码类（4.10-4.18）
- 10. SKILL.md 文档更新（10.1-10.6）
- 13. basic-memory 经验反哺（13.1-13.4）

## 验收检查清单

### 功能验收

- [ ] AnalyzeUrl 单元测试通过（1.13-1.15）
- [ ] Mock 层单元测试通过（2.6-2.7）
- [ ] AnalyzeRule 修复单元测试通过（3.7-3.9）
- [ ] MockJsExtensions 扩展单元测试通过（4.16-4.18）
- [ ] DebugLogger 单元测试通过（5.9-5.10）
- [ ] BookSourceDebugger 集成测试通过（6.12-6.15）
- [ ] RssSourceDebugger 集成测试通过（7.8）
- [ ] RuleEngineServer 命令路由集成测试通过（8.6-8.8）
- [ ] Python 客户端集成测试通过（9.14）

### 场景验收

- [ ] 场景 1: 简单书源端到端调试（无登录、无加密）
- [ ] 场景 2: 需登录的书源调试（输出警告 + 标记 unverifiable）
- [ ] 场景 3: 含 CF 盾的书源调试（输出警告 + 标记 unverifiable）
- [ ] 场景 4: 含加密的书源调试（解密成功）
- [ ] 场景 5: 订阅源端到端调试
- [ ] 场景 6: 单阶段调试（只验证搜索）
- [ ] 场景 7: 失败阶段定位
- [ ] 场景 8: 变量链传递

### 回测验收

- [ ] 已知正常书源回测：4 阶段全部通过
- [ ] 已知问题书源回测：精确定位失败阶段
- [ ] 用户真机导入验证：无报错，可直接使用

### 非功能验收

- [ ] JVM 服务端启动时间 ≤ 3 秒
- [ ] 端到端调试单次执行时间 ≤ 30 秒
- [ ] 日志输出实时性（每条日志延迟 ≤ 100ms）
- [ ] 内存占用 ≤ 200MB

## 完成标志

所有 P0 任务完成后，执行以下验证：

```bash
# 1. 启动 JVM 服务端
java -jar .trae/skills/legado-source-creator/tools/legado-rule-engine-mvp4.jar

# 2. 端到端书源调试
python .trae/skills/legado-source-creator/scripts/debug-source.py \
  --source output/book/test.json \
  --key "斗破苍穹" \
  --stage all

# 3. 端到端订阅源调试
python .trae/skills/legado-source-creator/scripts/debug-source.py \
  --source output/rss/test.json \
  --stage all

# 4. 验证日志格式与真机一致
# 5. 用户真机导入测试
```

全部通过后，本任务清单标记为 ✅ 完成。
