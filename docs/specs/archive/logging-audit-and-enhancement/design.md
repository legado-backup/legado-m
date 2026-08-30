# Design: 日志规范全面审查与补全完善

## Technical Approach

本设计针对 Legado 三层日志体系（AppLog / LogUtils / DebugLog）在核心模块的覆盖缺失问题，采用"分层补全、统一 Tag、增强入口、配套测试"四位一体策略，确保异常可追溯、日志可过滤、规范可执行。

### 现状基线

三层日志体系职责明确但覆盖不均：

- **AppLog**（`constant/AppLog.kt`）：业务日志中枢。`put`/`putError`/`putWarn`/`putInfo` 始终写入内存 `mLogs`（上限 100 条）+ 文件（经 `LogUtils.d("AppLog", msg)`）+ logcat（仅 `BuildConfig.DEBUG` 时 `Log.e` 输出）；`putDebug` 仅 `AppConfig.recordLog` 开启时写入；`putNotSave` 仅写内存+logcat 不写文件。`truncateSafely` 提供 2000 字符截断保护（data URI 专项 80 字符），`@Synchronized` 保证线程安全。
- **LogUtils**（`utils/LogUtils.kt`）：文件日志存储层。日志写入 `externalCacheDir/logs/appLog-{date}.txt`，`Level.INFO`/`Level.OFF` 由 `AppConfig.recordLog` 控制，`AsyncFileHandler` 异步写入，7 天自动清理。`d(tag, msg)` 接受 tag 参数，但 AppLog 调用时固定传 `"AppLog"`。
- **DebugLog**（`utils/DebugLog.kt`）：纯 logcat 调试日志，仅 `BuildConfig.DEBUG` 时输出，不落盘。

覆盖缺失统计：WebBook 模块 20 个 catch 块仅 2 处 AppLog 调用（缺 18 处）；规则引擎 5 个 catch 块 3 处 AppLog（缺 2 处）；网络请求 34 个 catch 块 18 处 AppLog（缺 16 处，其中 ObsoleteUrlFactory 15 处为遗留代码低优先级）；数据层 8 个 catch 块 18 处 AppLog（需评估）。

### 补全策略（五步走）

**第一步：模块 Tag 常量定义**

在 `AppLog` 中定义模块 Tag 常量集合，统一命名规范，便于 ai_tests 按模块过滤。Tag 采用简洁大驼峰模块名：

| Tag 常量 | 值 | 覆盖模块 |
|---------|-----|---------|
| `TAG_WEB_BOOK` | `"WebBook"` | BookInfo / BookList / WebBook / BookContent / BookChapterList / SearchModel |
| `TAG_ANALYZE` | `"AnalyzeRule"` | AnalyzeByJSonPath / AnalyzeRule / AnalyzeUrl / AnalyzeByJSoup / AnalyzeByXPath / AnalyzeByRegex |
| `TAG_HTTP` | `"HttpHelper"` | HttpHelper / SSLHelper / OkHttpExceptionInterceptor / StrResponse / CookieStore |
| `TAG_WEB_VIEW` | `"BackstageWebView"` | BackstageWebView |
| `TAG_DATA` | `"DataLayer"` | data/ 下 DAO 及仓库类 |
| `TAG_RSS` | `"Rss"` | Rss / RssParserByRule / RssSearchModel / CheckRssSource |
| `TAG_CONTENT` | `"ContentProcess"` | ContentProcessor / BookHelp / BookContent |

**第二步：AppLog 增强 putEntryWithTag 方法**

当前 `putEntry` 写文件时 tag 固定为 `"AppLog"`（`LogUtils.d("AppLog", safeMsg)`），导致文件日志无法按模块区分。新增 `putEntryWithTag` 方法，将模块 tag 透传给 `LogUtils.d`，同时保留原有 `put`/`putError`/`putWarn`/`putInfo`/`putDebug` 不变（向后兼容）：

```kotlin
@Synchronized
fun putDebugWithTag(
    tag: String,
    message: String?,
    throwable: Throwable? = null,
    level: Level = Level.ERROR
) {
    // recordLog 守卫：关闭时直接 return，零开销，不影响用户功能
    if (!AppConfig.recordLog) return
    message ?: return
    val safeMsg = truncateSafely(message)
    val fileMsg = if (throwable == null) safeMsg
    else "$safeMsg\n${throwable.stackTraceToString()}"
    LogUtils.d(tag, fileMsg)
    if (mLogs.size > 100) mLogs.removeLastOrNull()
    mLogs.add(0, LogEntry(System.currentTimeMillis(), safeMsg, throwable, level))
    if (BuildConfig.DEBUG) {
        Log.e(tag, safeMsg, throwable)
    }
}
```

此方法使 logcat（DEBUG 模式）和文件日志均携带模块 tag，ai_tests 可通过 `adb logcat -s WebBook:E` 或 grep 文件日志按模块过滤。

**第三步：catch 块日志补全**

对核心模块 catch 块补全 `AppLog.putDebugWithTag(TAG_XXX, ...)` 调用，遵循以下原则：

- **记录内容**：异常类型简称 + 关键参数（如书源 ID/URL 路径模式化、规则索引、HTTP 状态码）+ 调用栈（throwable 自动展开）
- **脱敏原则**：URL 仅保留路径模式（`/path/{id}`），cookie/token/key 等敏感字段隐藏为 `***`，源名称不记录（仅记源 ID 编号）
- **级别选择**：影响主流程的异常用 `Level.ERROR`（默认），可降级处理的异常用 `Level.WARN`，调试信息用 `putDebug`
- **不重复记录**：catch 块内若已有 AppLog 调用则不重复添加；仅向上抛出的异常在最外层 catch 记录一次

**第四步：ai_tests 日志获取脚本增强**

现有 `evidence_collector.py`（`ai_tests/lib/`）用 `adb logcat -d -v time` 获取全量 logcat 并提取 FATAL/ANR/CRASH；`swipe_test_log.py`（`ai_tests/scripts/`）用 `adb logcat -d -s SwipeTest:D VideoGesture:D` 获取特定 tag。缺失：按模块 tag 过滤的通用脚本、获取 AppLog 文件日志的脚本。

新增 `ai_tests/scripts/collect_app_log.py`，支持三种模式：

- `--tag WebBook`：按模块 tag 过滤 logcat（`adb logcat -d -s WebBook:*`）
- `--file`：`adb pull` 拉取设备 `externalCacheDir/logs/` 下当日 appLog 文件
- `--all`：同时获取 logcat 全量 + 文件日志，按 tag 分类输出摘要

**第五步：规范文档同步更新**

更新 `logging_rules.md`（补充模块 Tag 规范、putDebugWithTag 使用指南）和 `logging-during-refactoring.md`（补充 catch 块日志补全检查项）。

## Architecture Decisions

### AD-01: 日志补全策略选择（AppLog.putDebugWithTag vs AppLog.put vs LogUtils.d vs DebugLog）

- **Context**: 三层日志体系各有适用场景。AppLog.put 始终写内存+文件（不受 recordLog 控制），AppLog.putDebug 仅 recordLog 开启时写入，LogUtils.d 仅写文件，DebugLog 仅 logcat 且不落盘。用户要求：日志仅在 recordLog 开启时记录，recordLog 关闭时零开销，绝不影响用户功能使用。
- **Concern**: catch 块异常需同时满足：(1) recordLog 关闭时零开销（用户核心诉求）；(2) recordLog 开启时可追溯（ai_tests 能获取）；(3) 可按模块过滤。AppLog.put 始终写入文件+内存，recordLog 关闭时仍有开销，不满足诉求。LogUtils.d 绕过内存 mLogs，DebugLog release 无记录。
- **Decision**: catch 块统一使用新增的 `AppLog.putDebugWithTag(tag, message, throwable)`。该方法**仅在 recordLog 开启时**写入内存 mLogs + 文件（带 tag）+ logcat（仅 DEBUG），recordLog 关闭时直接 return 零开销。tag 透传给 LogUtils.d 实现模块级过滤。原有 `put`/`putError` 等方法保持不变。
- **Goal**: catch 块异常在 recordLog 开启时可追溯，recordLog 关闭时零开销不影响用户功能，ai_tests 能按模块 tag 过滤文件日志。
- **Tradeoff**: recordLog 关闭时 catch 块异常无日志记录（ai_tests 无法获取）——接受理由：用户主动选择不被日志影响，开启 recordLog 是用户主动选择；新增方法增加 API 表面，但方法简洁（5 行），维护成本低。
- **Status**: Proposed

### AD-02: 模块 Tag 命名规范

- **Context**: 现有 AppLog 写文件 tag 固定 "AppLog"，logcat tag 为 `stackTrace[3].className`（全限定类名，过长且不可预测）。ai_tests 需按模块过滤日志，但无统一 tag 规范。
- **Concern**: tag 不统一导致：(1) ai_tests 无法按模块过滤 logcat；(2) 文件日志无法区分来源模块；(3) 全限定类名作 tag 过长且因调用栈深度变化而不可靠。
- **Decision**: 定义 5 个模块 Tag 常量（`TAG_WEB_BOOK`="WebBook" / `TAG_ANALYZE`="AnalyzeRule" / `TAG_HTTP`="HttpHelper" / `TAG_WEB_VIEW`="BackstageWebView" / `TAG_DATA`="DataLayer"），存放于 AppLog companion。Tag 采用简洁大驼峰模块名，非全限定类名。catch 块调用 `putDebugWithTag` 时传入对应常量。
- **Goal**: ai_tests 可通过 `adb logcat -s WebBook:E AnalyzeRule:E` 精确过滤模块日志；文件日志可按 tag grep 定位模块。
- **Tradeoff**: 同一模块多个文件共用一个 tag（如 WebBook 模块 6 个文件都用 "WebBook"），无法区分具体文件；但 catch 块 message 中会包含类名/方法名上下文，且模块级过滤已满足定位需求，粒度过细反而不便过滤。
- **Status**: Proposed

### AD-03: ai_tests 日志获取方式

- **Context**: 现有 `evidence_collector.py` 获取全量 logcat 提取 CRASH，`swipe_test_log.py` 按 SwipeTest/VideoGesture tag 过滤。缺失按业务模块 tag 过滤的通用脚本，且无获取 AppLog 文件日志（`externalCacheDir/logs/appLog-*.txt`）的能力。
- **Concern**: 日志补全后需验证各模块 catch 日志是否正确输出；全量 logcat 噪声大难以定位；文件日志是用户反馈的主要载体却无脚本获取。
- **Decision**: 新增 `ai_tests/scripts/collect_app_log.py`，支持三种模式：(1) `--tag <Tag>` 按模块 tag 过滤 logcat（`adb logcat -d -s <Tag>:*`）；(2) `--file` 通过 `adb shell run-as io.legado.app cat externalCacheDir/logs/appLog-*.txt` 或 `adb pull` 拉取文件日志；(3) `--all` 同时获取并按 tag 分类输出摘要。脚本输出仅技术信息（异常类型/错误码/调用栈/数量统计），过滤敏感内容。
- **Goal**: ai_tests 可按模块验证日志补全效果；用户反馈问题时可一键拉取文件日志辅助定位。
- **Tradeoff**: `--file` 模式在 release 构建中需 `run-as` 权限（debuggable=false 时可能受限）；可接受，因测试环境通常用 debug 构建，release 用户反馈时可通过分享日志功能导出。
- **Status**: Proposed

### AD-04: recordLog 开关控制范围（putDebugWithTag 的 recordLog 守卫）

- **Context**: 当前 `recordLog`（`AppConfig.recordLog`）控制：(1) `LogUtils` 文件 handler 的 `Level.INFO`/`Level.OFF`；(2) `AppLog.putDebug` 是否写入。`put`/`putError`/`putWarn`/`putInfo` 始终写入内存+文件+logcat，不受 recordLog 控制。用户要求：补全的 catch 块日志必须在 recordLog 关闭时零开销。
- **Concern**: 若 catch 块使用 AppLog.put，recordLog 关闭时仍会写入内存+调用 LogUtils.d（虽然 LogUtils level=OFF 不实际写入文件，但仍有方法调用+内存操作开销）。用户明确要求"不能影响用户功能使用"。
- **Decision**: `putDebugWithTag` 方法开头检查 `AppConfig.recordLog`，若为 false 则直接 return，不执行任何内存/文件/logcat 操作。即 recordLog 关闭时**完全零开销**——无方法调用链、无内存分配、无 IO 操作。这与 `putDebug` 的行为一致，但增加了 tag 支持。
- **Goal**: recordLog 关闭时 catch 块日志调用零开销，绝不影响用户功能性能。
- **Tradeoff**: recordLog 关闭时 catch 块异常无任何记录（连内存都没有）；可接受，因用户主动选择关闭日志，开启 recordLog 是用户主动选择，ai_tests 测试时引导用户开启即可。
- **Status**: Proposed

### AD-05: 日志规范文档更新范围

- **Context**: 现有 `logging_rules.md` 定义三层日志体系和使用规范，`logging-during-refactoring.md` 定义改造过程日志记录规范。本次新增 putDebugWithTag 方法和模块 Tag 规范，需同步更新文档。
- **Concern**: 文档若不同步，后续开发者不知晓 putDebugWithTag 和 Tag 规范，catch 块日志补全无法持续执行。
- **Decision**: 更新范围限定为：(1) `logging_rules.md` 新增"模块 Tag 规范"章节（5 个 Tag 常量定义+使用场景）和"putDebugWithTag 使用指南"（何时用 putDebugWithTag vs put）；(2) `logging-during-refactoring.md` 新增"catch 块日志补全检查项"（改造时 catch 块必须有 AppLog 调用、记录异常类型+关键参数、脱敏原则）。不改动文档其他章节。
- **Goal**: 规范可执行、可检查，后续改造有据可依。
- **Tradeoff**: 文档更新范围保守（仅新增章节不改原有内容），可能存在规范重叠；可接受，避免大面积改动引入不一致。
- **Status**: Proposed

## Data Flow

日志数据流分为写入流和获取流两条路径。

### 日志写入流

业务代码 catch 块捕获异常后调用 `AppLog.putDebugWithTag(tag, message, throwable, level)`，数据流经以下阶段：

1. **recordLog 守卫**：`putDebugWithTag` 首先检查 `AppConfig.recordLog`，若为 false 则直接 return，**零开销**——无内存分配、无 IO 操作、无方法调用链。这是用户核心诉求："不能影响用户功能使用"。
2. **入口校验**：recordLog 开启时，检查 message 是否为空，为空则返回（`message ?: return`）。
3. **截断保护**：调用 `truncateSafely(message)` 处理。若 message 长度 ≤2000 字符则原样返回；若以 "data:image/" 开头则截断为前 80 字符并附加长度提示；否则按 Unicode 代码点截断至 2000 字符并附加长度提示。此步骤防止 MB 级 base64 图片或超长文本撑爆 logcat 和 Binder 导致 OOM/ANR/TransactionTooLargeException。
4. **线程安全写入**：`@Synchronized` 保证同一时刻仅一个线程操作 `mLogs`。先检查 `mLogs.size > 100` 则移除最旧条目（`removeLastOrNull`，因新条目插入头部），再将 `LogEntry(time, safeMsg, throwable, level)` 插入头部。
5. **文件写入**：调用 `LogUtils.d(tag, fileMsg)`，其中 fileMsg 为 safeMsg 或 safeMsg+堆栈字符串。LogUtils 通过 Logger 输出 `Level.INFO` 日志，AsyncFileHandler 异步写入 `externalCacheDir/logs/appLog-{date}.txt`。recordLog 开启时 fileHandler level 为 `Level.INFO`，正常写入。
6. **logcat 输出**：仅当 `BuildConfig.DEBUG` 为 true 时，调用 `Log.e(tag, safeMsg, throwable)` 输出到 logcat。release 构建不执行此步，无性能影响。

### 日志获取流

ai_tests 获取日志有两条路径：

1. **logcat 获取**：`collect_app_log.py --tag WebBook` 执行 `adb logcat -d -s WebBook:*`，获取指定模块 tag 的 logcat 输出。此路径仅 DEBUG 构建有效（release 无 logcat 输出）。脚本对输出过滤敏感内容（URL 路径模式化、cookie/token 隐藏），仅输出技术信息（异常类型、错误码、调用栈、数量统计）。
2. **文件日志获取**：`collect_app_log.py --file` 通过 `adb shell run-as io.legado.app` 进入应用沙箱，`cat externalCacheDir/logs/appLog-*.txt` 读取当日文件日志，或 `adb pull` 拉取到本地。此路径在 recordLog 开启时有效，release/debug 构建均可（需 run-as 权限）。
3. **全量获取**：`collect_app_log.py --all` 同时执行上述两条路径，按 tag 分类输出摘要，配合 `evidence_collector.py` 的 CRASH 提取能力，形成完整日志画像。

## File Changes

### 源码修改（AppLog 增强 + catch 块补全）

| 文件路径 | 修改内容 | 补全数量 |
|---------|---------|---------|
| `app/src/main/java/io/legado/app/constant/AppLog.kt` | 新增 7 个模块 Tag 常量（TAG_WEB_BOOK/TAG_ANALYZE/TAG_HTTP/TAG_WEB_VIEW/TAG_DATA/TAG_RSS/TAG_CONTENT）；新增 `putDebugWithTag(tag, message, throwable, level)` 方法，recordLog 守卫（关闭时直接 return 零开销），tag 透传给 LogUtils.d 和 Log.e | 新增方法+常量 |
| `app/src/main/java/io/legado/app/model/webBook/BookInfo.kt` | 5 个 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, ...)`，记录书源 ID+操作类型+异常 | +5 处 |
| `app/src/main/java/io/legado/app/model/webBook/BookList.kt` | 5 个 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, ...)`，记录书源 ID+页码+异常 | +5 处 |
| `app/src/main/java/io/legado/app/model/webBook/WebBook.kt` | 8 个无 AppLog 的 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_WEB_BOOK, ...)`（现有 2 处保留） | +8 处 |
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeByJSonPath.kt` | 3 个 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_ANALYZE, ...)`，记录规则类型 JSONPath+表达式+异常 | +3 处 |
| `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt` | 1 个 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_ANALYZE, ...)`，记录 URL 路径模式+异常 | +1 处 |
| `app/src/main/java/io/legado/app/help/http/SSLHelper.kt` | 5 个 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_HTTP, ...)`，记录 SSL 操作类型+异常 | +5 处 |
| `app/src/main/java/io/legado/app/help/http/OkHttpExceptionInterceptor.kt` | 2 个无 AppLog 的 catch 块补全 `AppLog.putDebugWithTag(AppLog.TAG_HTTP, ...)`（现有 1 处保留），记录 HTTP 状态码+URL 路径模式+异常 | +2 处 |
| `app/src/main/java/io/legado/app/data/entities/Rss.kt` | 补全 RSS 源请求/解析/文章获取的关键操作成功/失败日志 + 1 处 catch 块日志（使用 TAG_RSS），记录 RSS 源 ID+操作阶段+结果数量 | +1 catch + 成功/失败日志 |
| `app/src/main/java/io/legado/app/model/rss/RssParserByRule.kt` | 补全 RSS 规则解析的关键操作成功/失败日志（开始解析/解析成功文章数/解析失败） | 成功/失败日志 |
| `app/src/main/java/io/legado/app/model/rss/RssSearchModel.kt` | 补全 RSS 搜索的关键操作成功/失败日志（搜索开始/成功结果数/失败原因） | 成功/失败日志 |
| `app/src/main/java/io/legado/app/model/ContentProcessor.kt` | 评估并补全正文获取/替换/简繁/分段/图片解密的关键操作成功/失败日志（使用 TAG_CONTENT），catch 块已覆盖（7/7）保持不变 | 成功/失败日志（评估） |
| `app/src/main/java/io/legado/app/help/book/BookHelp.kt` | 评估并补全书籍内容处理的关键操作成功/失败日志 | 成功/失败日志（评估） |

### 维度2/维度3 补全说明

维度2（关键操作成功/失败日志）和维度3（关键参数日志）通过在现有 catch 块补全之外，**在关键操作节点（方法入口/成功出口/失败分支）增加 putDebugWithTag 调用**实现。具体清单：
- WebBook 模块：约 22 处成功/失败日志 + 约 10 处参数日志（搜索/详情/目录/正文/发现页各阶段）
- 规则引擎模块：JS 执行/CSS/XPath/JSONPath/正则解析的成功/失败日志
- 网络请求模块：HTTP 请求/响应/重试/SSL 的成功/失败日志
- RSS 子模块：RSS 源请求/解析/文章获取的成功/失败日志
- 内容处理模块：正文获取/图片解密的成功/失败日志

所有维度2/维度3 日志均使用 `putDebugWithTag`，recordLog 关闭时零开销，不影响用户功能。

### 规范文档更新

| 文件路径 | 修改内容 |
|---------|---------|
| `docs/project-rules/logging_rules.md` | 新增"模块 Tag 规范"章节（7 个 Tag 常量定义表+使用场景说明）；新增"putDebugWithTag 使用指南"小节（何时用 putDebugWithTag vs put，catch 块补全原则）；新增"三维度日志覆盖要求"章节（catch 块 + 关键操作成功/失败 + 关键参数） |
| `docs/project-rules/logging-during-refactoring.md` | 新增"catch 块日志补全检查项"章节（改造时 catch 块必须有 AppLog 调用、记录异常类型+关键参数、URL 路径模式化脱敏、敏感字段隐藏为 \*\*\*、不重复记录原则） |

### 测试脚本新增

| 文件路径 | 修改内容 |
|---------|---------|
| `ai_tests/scripts/collect_app_log.py` | 新增通用日志获取脚本。支持 `--tag <Tag>` 按模块 tag 过滤 logcat、`--file` 拉取 AppLog 文件日志、`--all` 全量获取按 tag 分类输出。输出仅技术信息（异常类型/错误码/调用栈/数量统计），过滤敏感内容（URL 路径模式化、cookie/token 隐藏）。使用 `ai_tests/venv/Scripts/python.exe` 运行 |

### 不修改的文件（明确排除）

- `app/src/main/java/io/legado/app/utils/LogUtils.kt`：不修改，putDebugWithTag 通过调用现有 `LogUtils.d(tag, msg)` 实现文件写入，无需改动 LogUtils。
- `app/src/main/java/io/legado/app/utils/DebugLog.kt`：不修改，DebugLog 职责不变。
- `app/src/main/java/io/legado/app/help/http/ObsoleteUrlFactory.kt`：15 个 catch 块为遗留代码（Apache HTTP 兼容层），低优先级，本次不补全，避免改动遗留代码引入风险。
- `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt`：已有 5 处 AppLog 调用（6 个 catch 块），覆盖率较高，本次不补全。
- `app/src/main/java/io/legado/app/help/http/CookieStore.kt`：已有 3 处 AppLog 调用（2 个 catch 块），已覆盖，本次不补全。
- `app/src/main/java/io/legado/app/help/http/HttpHelper.kt`：已有 7 处 AppLog 调用（1 个 catch 块），已覆盖，本次不补全。
- `app/src/main/java/io/legado/app/help/http/StrResponse.kt`：1 个 catch 块 0 处 AppLog，但为简单响应包装类，异常影响小，本次不补全。
- `data/` 下各文件：已有 18 处 AppLog 调用（8 个 catch 块），覆盖率较高，本次不补全，后续视情况评估。

### 补全统计汇总

| 模块 | 文件数 | 维度1 catch 块 | 维度2 成功/失败 | 维度3 参数 | 涉及 Tag |
|------|-------|---------------|----------------|-----------|---------|
| WebBook | 3 | 18 | 约22处 | 约10处 | TAG_WEB_BOOK |
| 规则引擎 | 2 | 4 | JS/CSS/XPath/JSONPath/正则各阶段 | 规则表达式+解析结果 | TAG_ANALYZE |
| 网络请求 | 2 | 7 | HTTP 请求/响应/重试/SSL | 请求URL路径+响应码 | TAG_HTTP |
| RSS | 3 | 1 | 请求/解析/文章获取各阶段 | 源URL路径+文章数 | TAG_RSS |
| 内容处理 | 2 | 0（已覆盖7/7） | 正文获取/替换/简繁/分段/图片解密 | 处理参数+结果长度 | TAG_CONTENT |
| **合计** | **12** | **30** | 全流程覆盖 | 关键参数覆盖 | 5 个 Tag |
