# spec.md — 日志规范全面审查与补全完善

## Intent

对 Legado 项目三层日志体系（AppLog / LogUtils / DebugLog）进行全面审查，系统性解决核心模块 catch 块异常被静默吞掉的问题，使 ai_tests 能在用户开启 recordLog 时通过文件日志可靠发现被捕获的异常，并固化日志规范防止未来再次出现日志缺失。

**核心约束**：所有补全的日志仅在 recordLog 开启时记录（使用 `AppLog.putDebug` / 新增 `putDebugWithTag`），recordLog 关闭时零开销，绝不影响用户功能使用。

具体目标：
1. 量化核心模块 catch 块的日志覆盖现状，识别静默吞异常的高风险点
2. 补全 WebBook / 规则引擎 / 网络层 / 数据层 等核心模块 catch 块的日志调用（**使用 putDebug/putDebugWithTag，仅在 recordLog 开启时记录**）
3. 定义统一的模块 Tag 命名规范，便于 ai_tests 按 tag 过滤文件日志
4. 新增 ai_tests 通用日志获取脚本，支持按模块 tag 过滤 + 获取 AppLog 文件日志
5. 更新日志规范文档（logging_rules.md + logging-during-refactoring.md），固化补全成果

## Scope

### In Scope（本次范围）

本次审查覆盖三个维度的日志缺失，不仅仅是 catch 块日志：

**维度1：catch 块日志（异常捕获）** — 所有 catch 块必须有日志调用
**维度2：关键操作成功/失败日志（操作流程）** — 搜索/详情/目录/正文等核心操作的开始/成功/失败
**维度3：关键参数日志（参数传递）** — URL构建/规则表达式/解析结果等关键参数

覆盖模块：

- **WebBook 模块**：深度分析发现 42 处缺失（10处catch + 22处成功/失败 + 10处参数），重点补全
  - WebBook.kt / BookInfo.kt / BookList.kt / BookContent.kt / BookChapterList.kt / SearchModel.kt
- **规则引擎模块**：5 个 catch 块 3 个 AppLog 调用（缺 2 个 catch），同时需补全 JS 执行/CSS/XPath/JSONPath/正则解析的成功/失败日志
  - AnalyzeRule.kt / AnalyzeByJSoup.kt / AnalyzeByXPath.kt / AnalyzeByJSonPath.kt / AnalyzeByRegex.kt / AnalyzeUrl.kt
- **网络请求模块**：34 个 catch 块 18 个 AppLog 调用（缺 16 个 catch），同时需补全 HTTP 请求/响应/重试/SSL 的成功/失败日志
  - SSLHelper.kt / OkHttpExceptionInterceptor.kt / BackstageWebView.kt（评估）
- **RSS 子模块**：5 个 catch 块 4 个 AppLog 调用（缺 1 个 catch），同时需补全 RSS 源请求/解析/文章获取的成功/失败日志
  - Rss.kt / RssParserByRule.kt / RssSearchModel.kt
- **内容处理模块**：7 个 catch 块 7 个 AppLog 调用（catch 覆盖充分），但需评估关键操作成功/失败日志
  - ContentProcessor.kt / BookHelp.kt
- **数据层**：8 个 catch 块 18 个 AppLog 调用（catch 覆盖充分），评估非 migration 部分是否需补全
- **模块 Tag 规范**：定义 WebBook / AnalyzeRule / HttpHelper / Rss / ContentProcess / Database 等模块 Tag
- **ai_tests 日志获取**：新增通用日志获取脚本，支持按模块 tag 过滤 + 拉取 AppLog 文件日志
- **规范文档更新**：logging_rules.md + logging-during-refactoring.md

### Out of Scope（不在本次范围）

- **Service 层**：23 个 catch 块，69 个 AppLog 调用，覆盖充分，不改动
- **重构三层日志体系**：不统一为一层日志体系，保留 AppLog / LogUtils / DebugLog 分层设计
- **AppLog.put 在 release 包输出到 logcat 的行为变更**：不修改 AppLog.put 的 logcat 输出条件（保持仅 BuildConfig.DEBUG 输出 Log.e），仅通过文件日志 + Tag 规范缓解
- **性能压测**：不评估补全日志后的性能影响（通过 @Synchronized 和截断保护已控制）
- **LogUtils 文件日志格式重构**：不修改 LogUtils 的日志文件格式和存储路径

## Approach

### Selected Approach：recordLog 守卫的日志补全 + 统一模块 Tag 规范 + AppLog 增强 + ai_tests 通用日志获取脚本

1. **对核心模块（WebBook / 规则引擎 / 网络层 / 数据层）的 catch 块补全日志调用**
   - 按"模块 → catch 块 → 是否有日志调用"逐点排查
   - 对无日志调用的 catch 块，补充 `AppLog.putDebugWithTag("模块Tag", "操作描述失败", e)` 调用
   - **关键：使用 putDebugWithTag 而非 put**，确保仅在 recordLog 开启时记录，recordLog 关闭时零开销
   - 优先补全 WebBook 模块（90% 缺失，影响最大），其次网络层（47% 缺失）、规则引擎（40% 缺失）、数据层（部分缺失）

2. **AppLog 新增 putDebugWithTag 方法**
   - 当前 putDebug 不支持自定义 tag（固定写入 "AppLog" tag 到文件）
   - 新增 `putDebugWithTag(tag, message, throwable)` 方法：recordLog 开启时写入文件（带 tag）+ 内存 + logcat(DEBUG)
   - recordLog 关闭时直接 return，零开销
   - 向后兼容：原有 put/putError/putWarn/putInfo/putDebug 方法不变

3. **定义统一的模块 Tag 命名规范**
   - 在 logging_rules.md 中新增"模块 Tag 命名规范"章节
   - 规定核心模块的 Tag 名称：WebBook / SearchModel / AnalyzeRule / AnalyzeUrl / HttpHelper / Concurrency / Database / SourceEdit 等
   - 要求 putDebugWithTag 调用的 tag 参数使用对应模块 Tag
   - 便于 ai_tests 通过文件日志按 Tag 过滤

4. **新增 ai_tests 通用日志获取脚本**
   - 新增 `ai_tests/scripts/collect_app_log.py`，支持：
     - 拉取 AppLog 文件日志（`externalCacheDir/logs/` 下的日志文件）
     - 按模块 Tag 过滤文件日志（`--tag WebBook`）
     - 按 CRASH_PATTERNS 提取异常（兼容现有 evidence_collector.py 的异常模式）
   - 与现有 evidence_collector.py（全量 logcat + CRASH_PATTERNS）和 swipe_test_log.py（按 tag 过滤 logcat）互补

5. **更新日志规范文档**
   - logging_rules.md：新增"模块 Tag 命名规范"章节 + "catch 块日志强制规则"章节（规定使用 putDebugWithTag）
   - logging-during-refactoring.md：新增"catch 块补全检查项"（重构时必须检查 catch 块是否有日志调用）

理由：
- 使用 putDebugWithTag 确保 recordLog 关闭时零开销，**绝不影响用户功能使用**
- recordLog 开启时写入文件日志（带模块 tag），ai_tests 可通过 adb pull + tag 过滤分析
- 统一 Tag 规范使 ai_tests 能精准过滤文件日志，避免噪音
- 更新规范文档防止未来再次出现日志缺失问题

### Alternatives Considered

| 替代方案 | 描述 | 否决理由 |
|---------|------|---------|
| 使用 AppLog.put 始终记录 | catch 块中使用 AppLog.put（始终写入文件+内存） | recordLog 关闭时仍有文件写入开销，影响用户功能性能 |
| 全局 AOP 日志注入 | 使用 Kotlin 编译器插件自动在所有 catch 块注入日志 | 过度工程化，项目未引入 AOP 框架，维护成本高 |
| 仅靠 LogUtils 文件日志 | 不改代码，仅通过 LogUtils 文件日志分析 | catch 块中没有日志调用，LogUtils 无内容可写 |
| 重构三层日志体系 | 统一为一层日志体系 | 影响范围过大，Service 层已覆盖充分不需改动 |
| 仅补全日志不改规范 | 只补日志不改规范文档 | 无法防止未来再次出现日志缺失问题 |

### Drawbacks

- recordLog 关闭时 catch 块异常无日志记录（用户未开启 recordLog 时 ai_tests 无法获取日志）——接受理由：用户优先选择不被日志影响，开启 recordLog 是用户主动选择
- 统一 Tag 规范需要开发者遵守，无法强制约束（只能通过规范文档 + 代码审查软约束）
- 新增 putDebugWithTag 方法增加了 AppLog API 表面积，但方法简洁（仅 5 行），维护成本低
- ai_tests 通用日志获取脚本只能获取文件日志，无法获取内存中的 AppLog.logs（内存日志仅 App 内可通过 AppLogDialog 查看）

### Prior Art

- 项目已有 `docs/project-rules/logging_rules.md` 定义三层日志体系和使用规则，可作为规范更新基线
- 项目已有 `docs/project-rules/logging-during-refactoring.md` 定义改造过程日志记录规范，可补充 catch 块检查项
- ai_tests 已有 `evidence_collector.py`（全量 logcat + CRASH_PATTERNS）和 `swipe_test_log.py`（按 tag 过滤）作为日志获取参考

## Requirements

### R1：WebBook 模块 catch 块日志补全
- 对 WebBook 模块 20 个 catch 块逐个排查，对无日志调用的 18 个 catch 块补充 `AppLog.putDebugWithTag("WebBook", "操作描述失败", e)` 调用
- **使用 putDebugWithTag 而非 put**，确保 recordLog 关闭时零开销
- 覆盖搜索书籍、获取书籍信息、获取目录、获取正文等核心流程的异常捕获点
- 补全后 WebBook 模块 catch 块日志覆盖率从 10% 提升至 100%

### R2：规则引擎模块 catch 块日志补全
- 对规则引擎模块 5 个 catch 块逐个排查，对无日志调用的 2 个 catch 块补充 `AppLog.putDebugWithTag("AnalyzeRule", "操作描述失败", e)` 调用
- 覆盖 AnalyzeRule / AnalyzeUrl 等规则解析的异常捕获点
- 补全后规则引擎模块 catch 块日志覆盖率从 60% 提升至 100%

### R3：网络请求模块 catch 块日志补全
- 对网络请求模块 34 个 catch 块逐个排查，对无日志调用的 16 个 catch 块补充 `AppLog.putDebugWithTag("HttpHelper", "操作描述失败", e)` 调用
- 覆盖 HTTP 请求、响应解析、重试、Cookie 管理等流程的异常捕获点
- 补全后网络请求模块 catch 块日志覆盖率从 53% 提升至 100%

### R4：数据层 catch 块日志补全
- 对数据层 8 个 catch 块逐个排查，对非 migration 部分无日志调用的 catch 块补充 `AppLog.putDebugWithTag("Database", "操作描述失败", e)` 调用
- migration 中的 13 个 AppLog 调用保持不变（已是最佳实践）
- 补全后数据层 catch 块日志覆盖率达到 100%

### R5：模块 Tag 命名规范定义
- 在 logging_rules.md 中新增"模块 Tag 命名规范"章节
- 定义核心模块 Tag 名称：WebBook / SearchModel / AnalyzeRule / AnalyzeUrl / HttpHelper / Concurrency / Database / SourceEdit 等
- 规定 AppLog.put 调用的 message 前缀必须包含模块 Tag
- 规定 Tag 命名采用 PascalCase，长度不超过 20 字符

### R6：catch 块日志强制规则
- 在 logging_rules.md 中新增"catch 块日志强制规则"章节
- 规定所有 catch 块必须有 `AppLog.putDebugWithTag` 调用（除明确声明"可忽略异常"并加注释外）
- **规定使用 putDebugWithTag 而非 put**，确保 recordLog 关闭时零开销，不影响用户功能
- 规定 catch 块日志必须包含模块 Tag + 操作描述 + 异常对象
- 规定禁止空 catch 块和仅 `e.printStackTrace()` 的 catch 块

### R7：ai_tests 通用日志获取脚本
- 新增 `ai_tests/scripts/collect_app_log.py`，支持拉取 AppLog 文件日志并按模块 Tag 过滤
- 支持拉取 AppLog 文件日志（`externalCacheDir/logs/` 下的日志文件）到本地
- 支持按模块 Tag 过滤文件日志（`--tag WebBook`）
- 支持按 CRASH_PATTERNS 提取异常（兼容现有 evidence_collector.py 的异常模式）
- 脚本使用 `ai_tests/venv/Scripts/python.exe` 运行，遵循 ai_tests 固定脚本规范
- 脚本需有 `--help` 说明和参数校验

### R8：logging_rules.md 规范文档更新
- 新增"模块 Tag 命名规范"章节（R5）
- 新增"catch 块日志强制规则"章节（R6）
- 补充"release 包日志可见性说明"章节（说明 AppLog.put 在 release 包不输出 logcat，需通过文件日志分析）
- 补充"ai_tests 日志获取脚本使用说明"章节

### R9：logging-during-refactoring.md 规范文档更新
- 新增"catch 块补全检查项"：重构时必须检查 catch 块是否有 AppLog 调用
- 新增"模块 Tag 规范遵守检查项"：新增 catch 块日志时必须使用正确的模块 Tag
- 补充"日志补全验证步骤"：重构完成后通过 collect_app_log.py 验证日志输出

### R10：Service 层不改动确认
- 确认 Service 层 23 个 catch 块、69 个 AppLog 调用覆盖充分，本次不改动
- 在规范文档中记录 Service 层作为"日志覆盖充分"的参考范例

### R11：release 包日志可见性缓解方案
- 分析 AppLog.put 在 release 包中不输出到 logcat 的影响（ai_tests 无法通过 logcat 发现 catch 异常）
- 缓解方案：ai_tests 测试时引导用户开启 recordLog 开关，通过文件日志分析
- 在 collect_app_log.py 中优先拉取文件日志，logcat 作为补充

### R12：关键操作成功/失败日志补全（维度2）
- 对核心模块的关键操作补全成功/失败日志，使用 `AppLog.putDebugWithTag`
- **WebBook 模块**：搜索开始/成功/失败、获取详情开始/成功/失败、获取目录开始/成功/失败、获取正文开始/成功/失败、发现页开始/成功/失败（约22处）
- **规则引擎模块**：JS 执行开始/成功/失败、CSS/XPath/JSONPath/正则解析开始/成功/失败
- **网络请求模块**：HTTP 请求发起/成功/失败、重试触发/成功/失败、SSL 握手成功/失败
- **RSS 子模块**：RSS 源请求开始/成功/失败、RSS 解析开始/成功/失败、文章获取开始/成功/失败
- **内容处理模块**：正文获取开始/成功/失败、图片解密开始/成功/失败
- 日志内容：模块 Tag + 操作名称 + 关键结果（如结果数量/响应码/耗时），过滤敏感信息

### R13：关键参数日志补全（维度3）
- 对核心模块的关键参数传递补全日志，使用 `AppLog.putDebugWithTag`
- **WebBook 模块**：URL 构建结果（路径模式化）、规则解析结果（类型+长度）、网络响应状态码（约10处）
- **规则引擎模块**：规则表达式（截断记录）、解析结果（类型+长度）、URL 模板变量替换结果
- **网络请求模块**：请求 URL（路径模式化）、响应状态码+长度、Cookie 操作类型+域名（代号化）
- **RSS 子模块**：RSS 源 URL（路径模式化）、解析结果（文章数）
- 日志内容：模块 Tag + 参数名 + 参数值（脱敏后），禁止输出完整 URL/cookie/token

### R14：RSS 子模块日志补全
- 对 RSS 子模块 5 个 catch 块中无日志的 1 个 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_RSS, ...)` 调用
- 同时补全 RSS 源请求/解析/文章获取的成功/失败日志（R12）
- 覆盖 Rss.kt / RssParserByRule.kt / RssSearchModel.kt

### R15：内容处理模块日志评估
- 评估 ContentProcessor.kt 和 BookHelp.kt 的关键操作成功/失败日志覆盖
- 评估正文获取/处理/图片解密的成功/失败日志是否缺失
- 评估替换规则/简繁转换/分段处理的关键节点日志
- catch 块已覆盖充分（7/7），重点评估维度2和维度3

## Scenarios

### S1：WebBook 搜索书籍异常被静默吞掉
- **Given** 用户通过书源搜索书籍，书源返回异常数据导致解析失败
- **When** WebBook 搜索流程的 catch 块捕获异常但无日志调用
- **Then** 异常被静默吞掉，用户无法知道失败原因
- **补全后** catch 块补充 `AppLog.putDebugWithTag("WebBook", "搜索书籍失败: ${e.message}", e)`，recordLog 开启时可通过文件日志按 Tag 过滤发现异常

### S2：规则引擎解析异常无日志
- **Given** 书源规则解析时发生 CSS/JSONPath/XPath 解析异常
- **When** AnalyzeRule 的 catch 块捕获异常但无日志调用
- **Then** 解析失败但无日志记录，难以定位是哪条规则出错
- **补全后** catch 块补充 `AppLog.putDebugWithTag("AnalyzeRule", "规则解析失败: ${e.message}", e)`，可定位具体规则

### S3：网络请求重试异常无日志
- **Given** 网络请求模块发起 HTTP 请求，发生 IOException 触发重试
- **When** 重试逻辑的 catch 块捕获异常但无日志调用
- **Then** 重试失败原因无记录，难以判断是网络问题还是服务端问题
- **补全后** catch 块补充 `AppLog.putDebugWithTag("HttpHelper", "请求重试失败: ${e.message}", e)`，可分析失败原因

### S4：recordLog 关闭时零开销验证
- **Given** 用户未开启 recordLog，核心模块 catch 块已补全 putDebugWithTag
- **When** catch 块捕获异常，调用 `AppLog.putDebugWithTag`
- **Then** putDebugWithTag 检测到 recordLog=false 后直接 return，无文件写入、无内存操作、零开销，不影响用户功能
- **对比** 若使用 AppLog.put 则即使 recordLog 关闭也会写入文件+内存，影响性能

### S5：recordLog 开启时 ai_tests 按模块 Tag 过滤日志
- **Given** 用户开启 recordLog，核心模块 catch 块已补全 putDebugWithTag 并使用统一模块 Tag
- **When** ai_tests 执行测试后通过 collect_app_log.py 拉取文件日志并按模块 Tag 过滤
- **Then** 可精准获取目标模块的异常日志，避免全量噪音，提升问题定位效率

### S6：数据库 migration 外的 catch 块日志缺失
- **Given** 数据层 8 个 catch 块中 13 个 AppLog 调用在 migrations 内，非 migration 部分日志缺失
- **When** 数据库操作（非 migration）发生异常被 catch 块捕获但无日志调用
- **Then** 数据操作失败无日志记录，难以排查数据问题
- **补全后** 非 migration 部分的 catch 块补充 `AppLog.putDebugWithTag("Database", "操作描述失败", e)`，覆盖所有数据操作异常

### S7：规范文档防止未来日志缺失
- **Given** 本次补全完成后，开发者后续新增 catch 块
- **When** 开发者查阅 logging_rules.md 的"catch 块日志强制规则"
- **Then** 开发者按规范在新增 catch 块中添加 putDebugWithTag 调用并使用正确模块 Tag，防止再次出现日志缺失
