# Spec: 测试基础设施升级 - 端到端真机级调试能力

> 状态：⚠️ 代码实现完成，测试验证缺失（2026-06-18）
> 创建日期：2026-06-18
> 优先级：P0

## 1. Intent（意图）

### 1.1 问题陈述

当前 `legado-source-creator` Skill 的测试基础设施存在系统性缺陷：AI 声称"测试通过"的书源/订阅源，用户导入手机开源阅读 App 后频繁报错，需要用户手动反馈调试信息才能定位问题。这违背了 Skill 的核心价值主张——"让 AI 自主创建可用的书源/订阅源"。

### 1.2 目标

让 AI 在使用 Skill 开发新书源/订阅源时，能够**完整跑通**生成的源配置，输出与真机一致的调试日志，达到"导入手机即可直接使用"的交付标准。

### 1.3 非目标

- ❌ 不实现 Android WebView 仿真（BackstageWebView 系列）
- ❌ 不实现 Android UI 交互（toast/openUrl 等）
- ❌ 不实现真机数据库持久化（CookieStore 用内存版即可）
- ❌ 不改变 Skill 的 5 阶段闭环工作流
- ❌ 不替换现有 MVP4 的核心解析器（AnalyzeRule/AnalyzeByJSoup/AnalyzeByXPath/RuleAnalyzer 已与真机一致）

## 2. Scope（范围）

### 2.1 涉及文件

#### 新增文件（JVM 服务端）

| 文件 | 职责 |
|------|------|
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/AnalyzeUrl.kt` | 从真机源码提取的 AnalyzeUrl，剥离 Android 依赖 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockCookieStore.kt` | 内存版 CookieStore，二级域名 Cookie 管理 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockCacheManager.kt` | 内存版 CacheManager |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockSource.kt` | 内存版 BookSource/RssSource 上下文 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/MockBook.kt` | 内存版 Book/BookChapter 上下文 |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/DebugLogger.kt` | 真机级调试日志输出器（`[mm:ss.SSS] ︾︽⇒┌└≡◇` 格式） |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/BookSourceDebugger.kt` | 端到端书源调试器（search→detail→toc→content） |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/RssSourceDebugger.kt` | 端到端订阅源调试器（sort→content） |
| `tools/mvp1-build/src/main/kotlin/io/legado/ruleengine/StrResponse.kt` | 真机 StrResponse 简化版（url + body + code） |

#### 修改文件（JVM 服务端）

| 文件 | 修改内容 |
|------|---------|
| `RuleEngineServer.kt` | 新增命令：`analyzeUrl` / `debugBookSource` / `debugRssSource`；支持流式日志输出 |
| `MinimalMockJsExtensions.kt` | 扩展 ajax（携带 cookie/header）、connect、getCookie/setCookie、md5Encode16、sha1/sha256、HMac 等 |
| `AnalyzeRule.kt` | 修复 NativeObject/LinkedTreeMap 处理；evalJS 注入 13 个变量；put/get 支持 book/source 层级 |

#### 新增文件（Python 客户端）

| 文件 | 职责 |
|------|------|
| `scripts/debug-source.py` | 端到端调试脚本（替代 deep-verify.py 的全链路验证） |

#### 修改文件（Python 客户端）

| 文件 | 修改内容 |
|------|---------|
| `tools/rule_engine_client.py` | 新增 `analyze_url` / `debug_book_source` / `debug_rss_source` 方法；支持流式日志回调 |
| `tools/jvm_helpers.py` | 可信度评估新增"端到端调试通过"判定 |
| `scripts/deep-verify.py` | 标记为 deprecated，全链路验证改调 `debug-source.py` |

#### 修改文件（Skill 文档）

| 文件 | 修改内容 |
|------|---------|
| `SKILL.md` | Phase 3 测试驱动章节新增端到端调试流程；JVM 测试基础设施章节更新 |
| `AI_README.md` | 脚本清单新增 `debug-source.py` |

### 2.2 不涉及文件

- ❌ 不修改 Legado 真机源码（`app/src/main/java/io/legado/app/`）
- ❌ 不修改 Legado 真机构建配置（`app/build.gradle`）
- ❌ 不修改 Skill 的 references/ 目录（知识库不变）
- ❌ 不修改 Skill 的 templates/ 目录（播放器模板不变）

## 3. Approach（方法）

### 3.1 总体策略

**从真机源码提取核心逻辑，剥离 Android 依赖，移植到 JVM 仿真器**。

具体路径：
1. **AnalyzeUrl 移植**：从 `app/.../model/analyzeRule/AnalyzeUrl.kt` 提取 URL 解析三步流水线（analyzeJs → replaceKeyPageJs → analyzeUrl），剥离 CookieStore/CacheManager/BackstageWebView 依赖，替换为 Mock 实现
2. **端到端调试器**：参考 `app/.../model/Debug.kt` 的 searchDebug→infoDebug→tocDebug→contentDebug 链路，实现 BookSourceDebugger/RssSourceDebugger
3. **日志格式对齐**：参考 `Debug.kt:33` 的 log 方法，实现 DebugLogger，输出 `[mm:ss.SSS] ︾︽⇒┌└≡◇` 格式 + state 状态码
4. **Mock 扩展**：参考 `JsExtensions.kt` 完整 API，补齐关键函数

### 3.2 通信协议升级

当前：stdin/stdout JSON 行协议（请求-响应模式）
升级后：支持**流式输出**（一个请求，多个响应行）

```
客户端发送：{"cmd": "debugBookSource", "sourceJson": "{...}", "key": "斗破"}
服务端流式返回（每行一个 JSON）：
  {"type": "log", "state": 1, "msg": "[00:00.001] ︾开始解析搜索页", "ts": "..."}
  {"type": "log", "state": 10, "msg": "...", "html": "...", "ts": "..."}
  {"type": "log", "state": 1, "msg": "[00:00.005] ┌获取书名", "ts": "..."}
  {"type": "log", "state": 1, "msg": "[00:00.006] └斗破苍穹", "ts": "..."}
  ...
  {"type": "result", "state": 1000, "success": true, "summary": {...}}
  或
  {"type": "error", "state": -1, "msg": "...", "stackTrace": "..."}
```

### 3.3 变量持久化机制

端到端调试期间，变量需跨步骤持久化：

| 变量类型 | 存储位置 | 生命周期 |
|---------|---------|---------|
| `@put/@get` 变量 | MockSource.variableMap | 整个调试会话 |
| `java.put/get` 变量 | MockBook.variableMap | 整个调试会话 |
| Cookie | MockCookieStore | 整个调试会话 |
| Cache | MockCacheManager | 整个调试会话 |
| Book 字段 | MockBook | 详情页解析后填充 |
| Chapter 字段 | MockBookChapter | 目录页解析后填充 |

## 4. Requirements（需求）

### L0: AnalyzeUrl 完整移植

#### REQ-L0-1: URL 解析三步流水线

**需求**：实现 `analyzeJs() → replaceKeyPageJs() → analyzeUrl()` 三步流水线

**验收标准**：
- 支持 `@js:code` 和 `<js>code</js>` 标签的 URL 求值
- 支持 `{{js}}` 内嵌 JS 替换
- 支持 `{{key}}` 搜索关键字替换
- 支持 `{{page}}` 页码替换
- 支持 `<page,page,...>` 页数列表
- 支持 `@result` 占位符引用前段 JS 结果

#### REQ-L0-2: UrlOption 字段解析

**需求**：解析 URL 后的 JSON 选项

**验收标准**：支持以下字段
- `method`: GET/POST/HEAD
- `charset`: 编码（UTF-8/GBK/escape）
- `headers`: Map 或 JSON String
- `body`: String/JsonObject/JsonArray
- `type`: 文件类型（图片/字体）
- `retry`: 重试次数
- `webView`: 是否用 WebView（标记 unverifiable）
- `webJs`: WebView JS（标记 unverifiable）
- `js`: URL 参数解析后 JS
- `bodyJs`: 响应 body 后 JS
- `charset`: 编码

#### REQ-L0-3: 网络请求执行

**需求**：执行 HTTP 请求

**验收标准**：
- GET/POST/HEAD 三种方法
- POST 支持 form 编码、json body、原始 body
- 自动携带 CookieStore 中的 Cookie
- 自动合并 source.header
- 支持 charset 编码处理
- 返回 StrResponse（url + body + code）
- 错误码与真机一致（-1 到 -7）

### L1: 端到端 debugBookSource 命令

#### REQ-L1-1: 调试链路

**需求**：实现 search→detail→toc→content 完整链路

**验收标准**：
- 接收 BookSource JSON + 搜索关键词
- 按 searchDebug→infoDebug→tocDebug→contentDebug 顺序执行
- 每阶段使用 AnalyzeUrl 构造请求 + AnalyzeRule 解析响应
- 变量跨阶段持久化（@put/@get、java.put/get）
- Cookie 跨阶段持久化
- 支持单阶段调试（key 格式：`isAbsUrl`→详情、`++url`→目录、`--url`→正文）

#### REQ-L1-2: 增量日志输出

**需求**：流式输出调试日志

**验收标准**：
- 日志格式：`[mm:ss.SSS] {msg}`
- 特殊符号：`︾` 开始解析、`︽` 解析完成、`⇒` 提示、`┌` 获取字段开始、`└` 获取字段结果、`≡` 状态信息、`◇` 统计信息
- state 状态码：1=普通日志、10=搜索页HTML、20=详情页HTML、30=目录页HTML、40=正文页HTML、-1=错误、1000=完成
- 每阶段输出 HTML 源码（state=10/20/30/40）
- 错误时输出完整堆栈（state=-1）

#### REQ-L1-3: 字段提取日志

**需求**：每个字段提取输出日志

**验收标准**：
- 搜索阶段：`┌获取书名` / `└{name}` / `┌获取作者` / `└{author}` / `┌获取详情页链接` / `└{bookUrl}` 等
- 详情阶段：`┌获取书名/作者/分类/字数/最新章节/简介/封面链接/目录链接`
- 目录阶段：`┌获取目录列表` / `└列表大小:N` / `┌获取目录下一页列表` / `◇目录总数:N`
- 正文阶段：`┌获取章节名称` / `└{title}` / `┌获取正文内容` / `└\n{content}`

#### REQ-L1-4: 分页支持

**需求**：支持 nextTocUrl / nextContentUrl 分页

**验收标准**：
- 目录页分页：循环获取所有章节，输出 `◇目录总页数:N`
- 正文页分页：串行/并发获取下一页，合并正文
- 防止无限循环（最大页数限制：100）

#### REQ-L1-5: replaceRegex 支持

**需求**：支持 ruleContent.replaceRegex

**验收标准**：
- 支持 `##正则##替换` 语法
- 支持 `##正则##替换##extra`（replaceFirst）
- 在正文提取后应用替换

### L2: 端到端 debugRssSource 命令

#### REQ-L2-1: 调试链路

**需求**：实现 sort→content 完整链路

**验收标准**：
- 接收 RssSource JSON
- 按 sortDebug→rssContentDebug 顺序执行
- 支持 key 格式：`name::url`（分类页）、`isAbsUrl`（内容页直接调试）
- 变量跨阶段持久化
- Cookie 跨阶段持久化

#### REQ-L2-2: 字段提取日志

**验收标准**：
- 列表阶段：`┌获取列表` / `└列表大小:N` / `┌获取标题/时间/描述/图片url/文章链接`
- 内容阶段：`┌获取正文内容` / `└{content}`

#### REQ-L2-3: 分页支持

**验收标准**：支持 ruleNextPage 分页

### L3: 增量日志输出（与真机一致）

#### REQ-L3-1: 日志格式

**验收标准**：
- 时间戳：`[mm:ss.SSS]`（从调试开始计时）
- 特殊符号：`︾︽⇒┌└≡◇`（与真机完全一致）
- state 状态码：1/10/20/30/40/-1/1000

#### REQ-L3-2: HTML 源码输出

**验收标准**：
- state=10：搜索页/列表页 HTML 源码
- state=20：详情页/内容页 HTML 源码
- state=30：目录页 HTML 源码
- state=40：正文页 HTML 源码
- HTML 单独存储在响应的 `html` 字段

#### REQ-L3-3: 错误日志

**验收标准**：
- state=-1：错误日志
- 输出完整堆栈（stackTraceStr）
- 触发客户端停止等待

### L4: CookieStore 内存实现

#### REQ-L4-1: Cookie 存储

**验收标准**：
- 按二级域名存储 Cookie
- `getCookie(url)`：获取二级域名的所有 Cookie
- `setCookie(url, cookie)`：保存 Cookie
- `removeCookie(url)`：删除 Cookie
- `getCookie(url, key)`：获取单个 key 的 Cookie

#### REQ-L4-2: Cookie 自动携带

**验收标准**：
- ajax/connect 请求自动携带 CookieStore 中的 Cookie
- 合并 CookieStore Cookie + header Cookie
- 支持 enabledCookieJar 模式

### L5: MockJsExtensions 扩展

#### REQ-L5-1: 网络类函数

**验收标准**：
- `ajax(url)`：携带 Cookie + source.header，支持 POST body
- `ajaxAll(urls)`：并发请求（替代返回空数组）
- `connect(url)`：返回 StrResponse（替代抛异常）
- `connect(url, header)`：带 header
- `get/head/post`：jsoup Connection.Response

#### REQ-L5-2: Cookie/缓存类函数

**验收标准**：
- `getCookie(tag)`：从 MockCookieStore 获取
- `getCookie(tag, key)`：获取单个 key
- `cacheFile(url)`：缓存到 MockCacheManager
- `cacheFile(url, saveTime)`：带过期时间

#### REQ-L5-3: 加密类函数

**验收标准**：
- `md5Encode16(str)`：16 位 MD5
- `sha1Encode(str)` / `sha256Encode(str)`
- `hmacSHA1(data, key)` / `hmacSHA256(data, key)`
- `digestHex(data, algorithm)` / `digestBase64Str(data, algorithm)`
- `createAsymmetricCrypto(transformation)`：RSA（基础实现）

#### REQ-L5-4: 编码类函数

**验收标准**：
- `base64Decode(str, charset)`：指定编码
- `base64DecodeToByteArray(str)`
- `base64Encode(str, flags)`
- `hexEncodeToString(utf8)`
- `strToBytes(str, charset)` / `bytesToStr(bytes, charset)`

### L6: Book/BookSource 上下文注入

#### REQ-L6-1: AnalyzeRule 上下文

**验收标准**：
- 接收 MockSource（含 header/cookie/loginUrl 配置）
- 接收 MockBook（含 name/author/variableMap）
- 接收 MockBookChapter（含 title/url）
- evalJS 注入 13 个变量：java/cookie/cache/source/book/chapter/title/src/result/baseUrl/nextChapterUrl/rssArticle/fromBookInfo

#### REQ-L6-2: put/get 变量层级

**验收标准**：
- `put(key, value)`：chapter → book → source 层级存储
- `get(key)`：chapter → book → source 层级查找
- 特殊键 `bookName`/`title` 返回 book.name/chapter.title

#### REQ-L6-3: NativeObject/LinkedTreeMap 处理

**验收标准**：
- `getStringList`/`getString` 处理 Rhino NativeObject（键值访问）
- `getStringList`/`getString` 处理 gson LinkedTreeMap（键值访问）

### L7: deep-verify.py 改用 JVM

#### REQ-L7-1: 废弃 Python 仿真

**验收标准**：
- `deep-verify.py` 标记为 deprecated
- 全链路验证改调 `debug-source.py`
- `debug-source.py` 调用 JVM `debugBookSource`/`debugRssSource` 命令

#### REQ-L7-2: debug-source.py 接口

**验收标准**：
- 输入：`--source {json路径} --key {搜索关键词} --stage {search|detail|toc|content|all}`
- 输出：流式日志（与真机格式一致）+ 最终验证报告
- 退出码：0=成功，1=部分失败，2=严重错误

## 5. Scenarios（场景）

### 场景 1: 简单书源端到端调试（无登录、无加密）

**输入**：笔趣阁风格书源 JSON + 搜索关键词"斗破苍穹"

**预期流程**：
1. 解析 searchUrl（`/search.php?q={{key}}`）
2. 发起 GET 请求，获取搜索页 HTML
3. 用 ruleSearch.bookList 解析书籍列表
4. 提取第一本书的 bookUrl
5. 访问详情页，用 ruleBookInfo 解析
6. 访问目录页，用 ruleToc 解析章节列表
7. 访问第一章正文页，用 ruleContent 解析正文

**预期输出**：
```
[00:00.000] ⇒开始搜索关键字:斗破苍穹
[00:00.001] ︾开始解析搜索页
[00:00.002] ≡获取成功:https://www.biquge.com/search.php?q=斗破苍穹
[00:00.003] ┌获取书籍列表
[00:00.004] └列表大小:20
[00:00.005] ┌获取书名
[00:00.006] └斗破苍穹
...
[00:00.012] ︽搜索页解析完成
[00:00.013]
[00:00.014] ⇒开始访问详情页:https://...
...
[00:00.070] ︽正文页解析完成
```

**验收**：日志格式与真机一致，4 阶段全部完成，无错误。

### 场景 2: 需登录的书源调试

**输入**：需登录的书源 JSON（含 loginUrl + loginUi + loginCheckJs）

**预期流程**：
1. 检测到 loginUrl 配置
2. 输出警告："本源需登录，JVM 仿真器无法执行 loginUi/loginCheckJs，Cookie 将为空"
3. 尝试执行搜索请求（无 Cookie）
4. 如果返回登录页，输出"检测到未登录响应"
5. 标记为"需真机验证登录流程"

**验收**：不崩溃，明确输出警告，标记 unverifiable。

### 场景 3: 含 CF 盾的书源调试

**输入**：CF 保护的网站书源（含 `webView()` loginUrl）

**预期流程**：
1. 检测到 loginUrl 含 `webView()`
2. 输出警告："CF 盾需 WebView，JVM 仿真器无法执行，标记 unverifiable"
3. 尝试直接请求（无 CF Cookie）
4. 如果返回 CF 挑战页，输出"检测到 CF 挑战"
5. 标记为"需真机验证 CF 绕过"

**验收**：不崩溃，明确输出警告，标记 unverifiable。

### 场景 4: 含加密的书源调试

**输入**：正文加密的书源（ruleContent 含 `createSymmetricCrypto`）

**预期流程**：
1. 正常执行搜索→详情→目录
2. 正文阶段：获取加密的正文内容
3. 执行 ruleContent JS（含 `java.createSymmetricCrypto(...).decryptStr(...)`）
4. MockJsExtensions 的 createSymmetricCrypto 真实执行解密
5. 输出解密后的正文

**验收**：解密成功，正文可读，无错误。

### 场景 5: 订阅源端到端调试

**输入**：视频站订阅源 JSON

**预期流程**：
1. 解析 sourceUrl
2. 发起请求，获取列表页 HTML
3. 用 ruleArticles 解析文章列表
4. 提取第一篇文章的 link
5. 访问内容页，用 ruleContent 解析
6. 输出 2 阶段日志（state=10/20）

**验收**：2 阶段全部完成，无错误。

### 场景 6: 单阶段调试（只验证搜索）

**输入**：书源 JSON + key="搜索关键词"

**预期流程**：
1. 只执行 searchDebug 阶段
2. 输出搜索页日志（state=10）
3. 不继续执行详情/目录/正文

**验收**：只输出搜索阶段日志，快速验证搜索规则。

### 场景 7: 失败阶段定位

**输入**：故意写错 ruleToc 的书源 JSON

**预期流程**：
1. 搜索阶段成功（state=10）
2. 详情阶段成功（state=20）
3. 目录阶段失败（ruleToc 匹配不到章节）
4. 输出错误日志：`[00:00.050] ┌获取目录列表` / `[00:00.051] └列表大小:0` / `[00:00.052] 错误:目录为空`
5. state=-1，停止后续阶段

**验收**：精确定位到"目录阶段失败"，输出明确错误信息。

### 场景 8: 变量链传递

**输入**：ruleBookInfo.init 含 `java.put("tocUrl", "...")`，ruleToc.tocUrl 含 `@get:{tocUrl}`

**预期流程**：
1. 详情阶段执行 ruleBookInfo.init
2. `java.put("tocUrl", "...")` 存入 MockBook.variableMap
3. 目录阶段执行 ruleToc.tocUrl
4. `@get:{tocUrl}` 从 MockBook.variableMap 读取
5. 正确构造目录页 URL

**验收**：变量跨阶段传递成功，目录页 URL 正确。

## 6. 验收标准（整体）

> 更新日期：2026-06-18（实施后更新）
> 状态说明：✅ 已通过 / ⚠️ 代码已实现但未测试 / ❌ 未实施

### 6.1 功能验收

- ⚠️ AnalyzeUrl 单元测试通过（REQ-L0-1/2/3）— 代码已实现，单元测试未编写
- ⚠️ debugBookSource 命令可用（REQ-L1-1/2/3/4/5）— 代码已实现，基础运行验证通过，集成测试未编写
- ⚠️ debugRssSource 命令可用（REQ-L2-1/2/3）— 代码已实现，基础运行验证通过，集成测试未编写
- ⚠️ 日志格式与真机一致（REQ-L3-1/2/3）— 代码已实现，格式验证通过，场景测试未执行
- ⚠️ CookieStore 内存实现可用（REQ-L4-1/2）— 代码已实现，单元测试未编写
- ⚠️ MockJsExtensions 扩展完成（REQ-L5-1/2/3/4）— 大部分已实现，createAsymmetricCrypto(RSA) 未实施
- ⚠️ Book/BookSource 上下文注入（REQ-L6-1/2/3）— 代码已实现，单元测试未编写
- ✅ debug-source.py 替代 deep-verify.py（REQ-L7-1/2）— 已实施，deep-verify.py 已标记 deprecated

### 6.2 场景验收

- ❌ 场景 1-8 全部未执行（代码已实现，但未用真实书源/订阅源进行场景测试）

### 6.3 回测验收

- ❌ 用一个已知能正常工作的书源回测：未执行
- ❌ 用一个已知有问题的书源回测：未执行
- ❌ 用户真机导入测试：未执行

### 6.4 非功能验收

- ❌ JVM 服务端启动时间 ≤ 3 秒 — 未测量
- ❌ 端到端调试单次执行时间 ≤ 30 秒（含网络请求）— 未测量
- ❌ 日志输出实时性（每条日志延迟 ≤ 100ms）— 未测量
- ❌ 内存占用 ≤ 200MB — 未测量

### 6.5 验收总结

**当前状态**：代码实现部分完成，测试验证完全缺失。详见 [design.md 第 7 章](./design.md#7-实施差异与后续优化2026-06-18-实施后补充)。
