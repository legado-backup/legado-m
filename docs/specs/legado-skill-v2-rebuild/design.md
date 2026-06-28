# Design: Legado Skill V2 重建方案

> **状态**：设计中 | **创建日期**：2026-06-22 | **基于**：前置核查 + 全量实现差距分析 + 执行偏差复盘

---

## 1. 总体架构

### 1.1 四层协作架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  第一层：经验知识库（决策大脑）                            │
│                                                                         │
│  SKILL.md（5阶段闭环工作流）+ references/（6大目录）+ basic-memory       │
│  经验索引层（project=legado）                                            │
│                                                                         │
│  职责：决策指导、经验检索、陷阱预警、模式匹配                              │
│  5阶段：经验优先 → 构建规则+预校验 → 测试驱动 → 源码深挖 → 经验反哺       │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ 决策指令 + 经验上下文
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              第二层：Python 客户端（操作执行层）                           │
│                                                                         │
│  legado_client/（统一包，单入口 python -m legado_client）                 │
│  ├── analyzer/  （source_validator + rule_precheck + error_diagnoser     │
│  │               + auto_fixer + confidence_evaluator + crypto_analyzer） │
│  ├── client/    （rule_engine_client + debug_runner + batch_runner       │
│  │               + obstacle_resolver + user_interaction）                 │
│  ├── experience/（experience_manager + conflict_resolver）               │
│  └── utils/     （config + file_utils + jvm_helpers + logger）           │
│                                                                         │
│  职责：预校验、JVM通信、错误诊断、自动修复、经验提取、降级执行             │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ stdin/stdout JSON 协议
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            第三层：JAR 仿真服务端（核心能力底座）                         │
│                                                                         │
│  legado-jvm.jar（单 JAR，fatJar 构建）                                   │
│  ├── AnalyzeRule + AnalyzeUrl + Rhino 1.8.1 + jsoup 1.16.2             │
│  ├── BookSourceDebugger + RssSourceDebugger + CheckSourceDebugger       │
│  ├── JsExtensionsStub（86完整+38降级+8不可用）+ hutool 5.8.22           │
│  └── RuleEngineServer（stdin/stdout JSON 协议，suspend 协程）            │
│                                                                         │
│  职责：规则解析执行、网络请求、JS执行、调试输出、仿真验证                  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ 仿真失败时回退
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│          第四层：Legado 官方源码（兜底保障）                              │
│                                                                         │
│  开源阅读 Android 源码（app/src/main/java/io/legado/app/...）            │
│  逐行对比分析，验证仿真端行为一致性                                        │
│                                                                         │
│  职责：仿真端无法解决时，回源码分析根因；新功能实现前先核验源码逻辑         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 V1 → V2 架构变更

| # | 变更项 | V1 状态 | V2 目标 | 变更原因 |
|---|--------|---------|---------|---------|
| 1 | 架构层次 | 三层（Skill+Python+JAR） | **四层**（+源码兜底层） | 明确源码作为最终兜底，避免臆测 |
| 2 | JAR 数量 | 4 个 JAR | **1 个 JAR** | 简化部署，避免版本不一致 |
| 3 | OkHttp 版本 | 5.3.2 | **5.3.2（锁定验证）** | 与真机版本一致，无需变更，仅验证一致性 |
| 4 | 并发模型 | runBlocking 阻塞 | **suspend + withTimeout** | 避免阻塞和死锁 |
| 5 | Python 客户端 | 双客户端（tools/ + legado_client/） | **单客户端**（legado_client/） | 消除职责边界模糊 |
| 6 | auto_fixer 接入 | debug_runner 独立简化版 | **调用 auto_fixer.auto_fix_error()** | 完整修复能力（12种）接入主流程 |
| 7 | verify_fix | 仅 JVM ping | **执行实际规则验证** | 修复后验证不空转 |
| 8 | 经验闭环 | pending.json 无人消费 | **AI agent 消费 → basic-memory** | 闭环完整 |
| 9 | 诊断日志 | 硬编码 System.err | **环境变量 LEGADO_DEBUG 控制** | 生产环境不污染日志 |
| 10 | 测试验证 | 挑最简单源测试 | **50+书源 + 50+订阅源强制测试** | 端到端真实验证 |
| 11 | 懒原则边界 | 滥用（跳过必要实现） | **重定义边界，必做项不可简化** | 防止实施偏差 |
| 12 | 子代理输出 | 信任不验证 | **交叉验证强制化** | 防止空壳实现 |

---

## 2. 前置核查结论

### 2.1 核查一：JVM 仿真服务端 Bug 清单（源码逐行核实）

> **核实方法**：对 JVM 仿真端每个疑似 Bug 逐行阅读源码，与真机源码对比确认。

| Bug ID | 文件:行号 | 问题描述 | 源码核实结论 | 处理策略 |
|--------|----------|---------|------------|---------|
| ~~BUG-01~~ | ~~RuleEngineServer.kt:192~~ | ~~assessConfidence 正则 `\\blet\\b` 退格符问题~~ | **误判**：Kotlin 字符串中 `"\\blet\\b"` 经转义后为 `\blet\b`，是正确的正则单词边界写法，无需修复 | 移除 |
| BUG-02 | BookSourceDebugger.kt:444-449 | `debugExplore` 发现页日志误写为"搜索页" | **未修复**：源码第444行仍输出 `"[DIAG] 搜索页"`，但实际位于 `debugExplore()` 发现页方法内 | P0 修复 |
| ~~BUG-03~~ | ~~RssSourceDebugger.kt:313-378~~ | ~~debugSortWithEmptyKey 忽略 URL~~ | **已修复**：完整降级链 sortUrl→searchUrl→sourceUrl，`debugSingleUrl()` 已接受参数 | 移除 |
| ~~BUG-04~~ | ~~AnalyzeRule.kt:428-481~~ | ~~getElements NativeArray 转换~~ | **已修复**：`convertJsResultToList()` 三层防护（List/Array/反射兜底） | 移除 |
| ~~BUG-05~~ | ~~AnalyzeUrl.kt:124-149~~ | ~~ajax 防递归逻辑~~ | **已修复**：`ajaxRecursionGuard` 布尔标志位 + finally 重置，递归时回退到 JsExtensionsStub.ajax | 移除 |
| BUG-06 | JsExtensionsStub.kt:1148 | `JsoupResponseAdapter.cookies()` 始终返回空 Map | **确认存在**：`override fun cookies() = emptyMap()`，JS 通过 `java.post(...).cookies()` 获取 Cookie 失败 | P0 修复 |
| ~~BUG-07~~ | ~~BookSourceDebugger.kt:786-840~~ | ~~正文分页 nextChapterUrl 缺失~~ | **已修复**：toc 阶段末尾计算 nextChapterUrl 并传入 content 阶段（第786-788行计算，第840行设置） | 移除 |

**核实后实际需修复的 Bug 仅 2 个**：BUG-02（日志标签错误）和 BUG-06（cookies 返回空 Map）。

### 2.2 核查二：JVM 仿真服务端 5 个未修复 GAP

| GAP ID | 问题描述 | 影响范围 | 处理策略 |
|--------|---------|---------|---------|
| GAP-05/06 | Rar/7z 解压不支持，`extractZipFile` 仅支持 zip | 影响 1-3% 源（压缩包源） | 降级：返回空 + 文档化；升级路径：集成 commons-compress |
| GAP-10 | `replaceFont` 多字节字符简化处理，未完整实现 Base64 字体替换 | 影响 <1% 源（自定义字体源） | 降级：跳过 + 文档化；升级路径：完整 Base64 解码 |
| GAP-07 | `ajaxAll`/`ajaxTestAll` 无并发，串行执行所有 ajax 请求 | 性能差但功能正确 | 优化：引入协程并发（非阻塞性 GAP） |
| GAP-22 | `ruleDescription` 逻辑与真机有差异，调试输出格式不一致 | 调试信息可读性差异 | 对齐：参照真机源码修正输出格式 |
| GAP-44 | ~~followRedirects 字段未移除~~ | ~~代码冗余~~ | **保留**：源码核实确认 `followRedirects` 在 AnalyzeUrl.kt 中完整实现（声明第114行、赋值第303行、使用第642行），与真机行为一致，不应移除 |

### 2.3 核查三：Python 客户端 9 项重大偏差

| # | 偏差描述 | 当前状态 | 根因 | 影响 |
|---|---------|---------|------|------|
| PY-01 | SKILL.md 4 处"实现状态"标注过时 | 标注为"已实现"但实际未实现或部分实现 | 实施后未同步更新文档 | AI agent 被误导，依赖不存在的功能 |
| PY-02 | `apply_auto_fix()` 仅处理 relative_url | `auto_fixer.py` 的 `auto_fix_error()` 已支持 12 种自动修复 + 5 种需用户介入类型（源码核实确认），但 `debug_runner.py` 的 `apply_auto_fix()` 未调用 `auto_fix_error()`，仅自行处理 relative_url | 懒原则：独立简化版替代完整实现 | 修复能力严重不足，大部分错误无法自动修复 |
| PY-03 | `verify_fix()` 仅 ping JVM | 不验证修复效果，只检查 JVM 是否存活 | 懒原则：用最简单的检查替代实际验证 | 修复后验证空转，无法确认修复有效性 |
| PY-04 | `experience_manager.extract()`/`write_to_basic_memory()` 已实现但未接入主流程 | 经验提取和写入功能存在但从未被调用 | 主流程未集成经验管理步骤 | 经验闭环断裂，无法反哺 |
| PY-05 | AD-04/05/06/07/09 五个决策编号缺失 | 实施时做出决策但未记录编号 | 实施决策未同步文档 | 决策追溯困难，无法审计 |
| PY-06 | 6 个新增模块未在设计文档中记录 | webview_delegate/crypto_analyzer 等模块已存在但设计文档无记录 | 实施时新增模块未更新设计 | 设计文档与实现脱节 |
| PY-07 | 预校验失败 `sys.exit(1)` | 直接退出而非返回 Phase 2 重新构建 | 错误处理粗暴，未考虑工作流回退 | 预校验失败后无法恢复，需重新启动 |
| PY-08 | `webview_delegate.py` 路径偏差 | 导入路径与实际文件位置不一致 | 文件移动后未更新导入 | 模块导入失败 |
| PY-09 | `ocr_delegate.py` 未实现 | 文件存在但内容为空或仅有占位符 | 懒原则：创建文件但不实现 | OCR 功能不可用 |

### 2.4 核查四：目录结构问题与执行偏差

#### 2.4.1 目录结构问题

| 问题类型 | 数量 | 详情 |
|---------|------|------|
| 需清理的问题文件 | 130+ | __pycache__、build 产物、临时文件、孤立 JSON |
| 需删除的废弃脚本 | 6 个 | tools/ 下已废弃的独立脚本 |
| 需整合的 tools/ 文件 | 9 个 | tools/ 下 Python 文件需整合到 legado_client/ |

#### 2.4.2 执行偏差复盘

| 偏差类型 | 具体表现 | 根因 | 后果 |
|---------|---------|------|------|
| 懒原则滥用 | 将"减少过度工程"曲解为"跳过必要实现" | 对 YAGNI 原则理解偏差 | 12 个 Bug 仅修复 5 个，auto_fixer 仅接入 1/12 能力 |
| 回避真实测试 | 挑最简单的源测试，回避复杂源 | 简单源容易通过，复杂源可能暴露问题 | JAR 仿真端无法支持真机可运行的源 |
| 未校验子代理输出 | 信任子代理返回结果，不交叉验证 | 缺乏验证机制 | 错误/空壳实现被标记为"已完成" |
| 实施决策未同步文档 | AD-01~AD-12 决策未全部记录 | 实施时未同步更新设计文档 | 文档失去参考价值，无法审计决策 |

---

## 3. JVM 仿真服务端优化方案

### 3.1 Bug 修复方案（源码核实后仅 2 个需修复）

> **源码核实结论**：原 7 个 Bug 中，BUG-01 为误判（正则写法正确），BUG-03/04/05/07 已修复，仅 BUG-02 和 BUG-06 需修复。

#### ~~BUG-01: assessConfidence 正则错误~~（误判，无需修复）

> **源码核实**：Kotlin 字符串 `"\\blet\\b"` 经转义后为 `\blet\b`，是正确的正则单词边界写法。`\\b` 在 Kotlin 普通字符串中不是退格符（退格符需 `"\u0008"`），而是转义序列 `\b`（正则单词边界）。此 Bug 不存在，无需修复。

#### BUG-02: debugExplore 日志误写（P0，需修复）

**文件**：`tools/legado-jvm/src/.../BookSourceDebugger.kt:444-449`

**问题**：发现页（Explore）调试日志输出为"[DIAG] 搜索页"，日志内容与实际调试阶段不符。

**修复方案**：
```kotlin
// 修复前（第444行）
System.err.println("[DIAG] 搜索页 bookListRule=$bookListRule")

// 修复后
System.err.println("[DIAG] 发现页 bookListRule=$bookListRule")
```

**验证标准**：调试发现页时日志输出"[DIAG] 发现页"，调试搜索页时输出"[DIAG] 搜索页"。

#### ~~BUG-03: debugSortWithEmptyKey 忽略解析 URL~~（已修复）

> **源码核实**：`RssSourceDebugger.kt:313-378` 已实现完整降级链（sortUrl→searchUrl→sourceUrl），`debugSingleUrl()` 已接受参数。无需修复。

#### ~~BUG-04: getElements NativeArray 转换不完整~~（已修复）

> **源码核实**：`AnalyzeRule.kt:428-481` 已实现 `convertJsResultToList()` 方法，三层防护（List 直接转换 / Array 转换 / 反射兜底）。无需修复。

#### ~~BUG-05: ajax 防递归逻辑可能无限递归~~（已修复）

> **源码核实**：`AnalyzeUrl.kt:124-149` 已实现 `ajaxRecursionGuard` 布尔标志位 + finally 重置，递归时回退到 `JsExtensionsStub.ajax`。无需修复。

#### BUG-06: JsoupResponseAdapter.cookies() 返回空 Map（P0，需修复）

**文件**：`tools/legado-jvm/src/.../JsExtensionsStub.kt:1148`

**问题**：`JsoupResponseAdapter.cookies()` 始终返回空 Map，JS 通过 `java.post(...).cookies()` 获取 Cookie 失败，影响需要维持登录态的源。

**修复方案**：从 OkHttp Response 的 headers 中解析 Set-Cookie：
```kotlin
override fun cookies(): Map<String, String> {
    val cookies = mutableMapOf<String, String>()
    response.headers("Set-Cookie").forEach { setCookie ->
        // 解析 Set-Cookie: name=value; Path=/; ...
        val parts = setCookie.split(";")
        if (parts.isNotEmpty()) {
            val nameValue = parts[0].trim().split("=", limit = 2)
            if (nameValue.size == 2) {
                cookies[nameValue[0].trim()] = nameValue[1].trim()
            }
        }
    }
    return cookies
}
```

**验证标准**：
- 发送 POST 请求后，`response.cookies()` 返回响应中的 Cookie
- 无 Cookie 时返回空 Map（行为不变）
- Cookie 解析与浏览器行为一致

#### ~~BUG-07: 正文分页 nextChapterUrl 缺失~~（已修复）

> **源码核实**：`BookSourceDebugger.kt:786-840` 已实现 nextChapterUrl 完整传递链路（toc 阶段末尾计算→content 阶段设置）。无需修复。

### 3.2 GAP 修复方案（4 个，GAP-44 已确认正常无需修复）

#### GAP-05/06: Rar/7z 解压不支持

**问题**：`JsExtensionsStub` 的 `extractZipFile` 仅支持 zip 格式，Rar/7z 压缩包返回空。

**修复方案**（降级+文档化）：
```kotlin
// 简化说明：Rar/7z 解压暂不支持 | 已知上限：1-3% 源受影响 | 升级路径：集成 commons-compress 5.x
fun extractArchive(filePath: String, format: String): List<String> {
    return when (format) {
        "zip" -> extractZipFile(filePath)
        "rar", "7z" -> {
            debugLog("不支持的压缩格式: $format，返回空列表")
            emptyList()
        }
        else -> emptyList()
    }
}
```

**验证标准**：zip 解压正常；rar/7z 返回空列表并输出降级日志；文档中记录已知限制。

#### GAP-10: replaceFont 多字节字符简化

**问题**：`replaceFont` 对 Base64 编码的自定义字体替换处理不完整，多字节字符未正确解码。

**修复方案**（降级+文档化）：
```kotlin
// 简化说明：replaceFont 多字节字符未完整实现 | 已知上限：<1% 源受影响 | 升级路径：完整 Base64 解码 + 字体映射表
fun replaceFont(html: String, fontRule: String): String {
    // 当前：仅处理单字节字符替换
    // 降级：跳过多字节字符的字体替换
    return html.replaceRegex(fontRule.toRegex())
}
```

**验证标准**：单字节字体替换正常；多字节字符跳过并输出降级日志；文档记录限制。

#### GAP-07: ajaxAll/ajaxTestAll 无并发

**问题**：`ajaxAll`/`ajaxTestAll` 串行执行所有 ajax 请求，性能差但功能正确。

**修复方案**（性能优化）：
```kotlin
suspend fun ajaxAll(urls: List<String>): List<String> = coroutineScope {
    urls.map { url ->
        async { executeAjax(url) }
    }.awaitAll()
}
```

**验证标准**：并发执行后总耗时显著降低；返回结果顺序与输入一致；功能正确性不变。

#### GAP-22: ruleDescription 逻辑差异

**问题**：`ruleDescription` 调试输出格式与真机不一致。

**修复方案**：参照真机源码 `BookSourceDebugger.kt` 中的 `ruleDescription` 实现，对齐输出格式。

**验证标准**：调试输出格式与真机一致；字段名称、顺序、分隔符完全对齐。

#### ~~GAP-44: followRedirects 字段未移除~~（源码核实确认正常，无需修复）

> **源码核实**：`AnalyzeUrl.kt` 中 `followRedirects` 字段完整实现（声明第114行、赋值第303行、OkHttpClient 配置第642行），与真机行为一致。此字段不是"已废弃"，而是正常的 URL 选项配置。不应移除。

### 3.3 架构优化

#### 3.3.1 runBlocking 消除

**涉及文件**：AnalyzeUrl.kt（4 处）、AnalyzeRule.kt（3 处）、RuleEngineServer.kt（main 入口）

**策略**：
1. `RuleEngineServer` 的命令处理改为 `suspend` 函数
2. 使用 `withTimeout(15.seconds)` 替代 `runBlocking` 超时控制
3. `runBlocking` 仅保留在 `main()` 入口，内部全部 `suspend`

```kotlin
// main 入口（唯一保留 runBlocking 的位置）
fun main() = runBlocking {
    while (true) {
        val line = readLine() ?: break
        processCommand(line)  // suspend 函数
    }
}

suspend fun processCommand(cmd: String) {
    withTimeout(15.seconds) {
        // 原有逻辑，全部 suspend
    }
}
```

#### 3.3.2 单 JAR 构建

```kotlin
// build.gradle.kts
tasks.register<Jar>("fatJar") {
    archiveClassifier.set("all")
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    from(configurations.runtimeClasspath.get().map {
        if (it.isDirectory) it else zipTree(it)
    })
    with(tasks.jar.get())
    manifest {
        attributes["Main-Class"] = "io.legado.app.ruleengine.RuleEngineServerKt"
    }
}
```

#### 3.3.3 OkHttp 版本对齐

```kotlin
// 验证前（当前状态，与真机一致）
implementation("com.squareup.okhttp3:okhttp:5.3.2")
// 验证后（维持不变，无需降级）
implementation("com.squareup.okhttp3:okhttp:5.3.2")
```

**版本一致性验证**：
- 确认 `build.gradle.kts` 中 `okhttp:5.3.2` 与真机 `libs.versions.toml` 中 `okhttp = "5.3.2"` 一致
- OkHttp 5.x API 与 4.x 无需适配（当前代码已使用 5.x API）
- `Response.body` 在 5.x 中是属性（无需 `body()` 调用）

### 3.4 性能优化

| 优化项 | 当前 | 目标 | 方案 |
|--------|------|------|------|
| scriptCache 无限制 | HashMap 无限增长 | LRU 64 项 | 替换为 `LinkedHashMap` + `removeEldestEntry` |
| ajax 串行 | 串行执行 | 并发执行 | `async` + `awaitAll` |
| JVM 启动 | 无预热 | 预加载规则引擎 | 启动时预初始化 AnalyzeRule/AnalyzeUrl |
| 诊断日志 | 始终输出 | 条件输出 | `LEGADO_DEBUG` 环境变量控制 |

### 3.5 安卓依赖剥离验证

**目标**：确保 JAR 仿真端不依赖任何 Android 平台 API。

**验证清单**：

| 安卓 API | 仿真端替代 | 验证方式 |
|---------|----------|---------|
| `android.util.Base64` | `java.util.Base64` + `mapBase64Flags` | 单元测试：编码/解码一致性 |
| `android.util.Log` | `System.err.println` | 日志输出验证 |
| `android.webkit.WebView` | 抛 `WebViewRequiredException` | 异常抛出验证 |
| `androidx.room.*` | 内存 Map | 数据存取验证 |
| `SymmetricCryptoAndroid` | hutool `SymmetricCrypto` | 加密/解密一致性验证 |
| `androidId` | 固定值 `"simulation"` | 返回值验证 |
| `Toast` | `System.err.println` | 输出验证 |
| `Intent` | `UnsupportedOperationException` | 异常抛出验证 |

**验证方法**：在 JAR 中执行 `grep -r "android\." src/`，确认无 Android 框架导入（除 `android.util.Base64` 映射层）。

### 3.6 代码进化机制完善

**目标**：建立仿真端代码与真机源码的持续对齐机制。

**机制设计**：

1. **源码版本锚定**：在 `legado-jvm/` 目录下记录对应的 Legado 源码 commit hash
2. **差异追踪表**：维护 `simulation-vs-real-diff.md`，记录所有已知差异
3. **定期对齐**：每次 Legado 源码更新后，执行差异对比，更新仿真端
4. **回归测试**：每次仿真端修改后，执行 50+ 真实源回归测试

```kotlin
// legado-jvm/SOURCE_VERSION
legado_commit: abc123def456...
last_aligned: 2026-06-22
known_diffs: 12  // 见 simulation-vs-real-diff.md
```

---

## 4. Python 客户端工程化优化方案

### 4.1 工程化体系

#### 4.1.1 目录结构（V2）

```
scripts/
├── requirements.txt          # 依赖声明
├── setup.py                  # 包安装配置
├── setup_venv.bat            # Windows 虚拟环境初始化
├── setup_venv.sh             # Linux/Mac 虚拟环境初始化
├── legado_client/            # 统一包
│   ├── __init__.py
│   ├── __main__.py           # CLI 入口：python -m legado_client
│   ├── cli.py                # CLI 参数解析
│   ├── analyzer/             # 分析器
│   │   ├── source_validator.py    # 字段完整性校验（15条规则）
│   │   ├── rule_precheck.py       # 规则语法预检（Rhino兼容性）
│   │   ├── error_diagnoser.py     # 错误诊断（12种错误类型）
│   │   ├── auto_fixer.py          # 自动修复（12种修复能力）
│   │   ├── confidence_evaluator.py # 可信度评估
│   │   ├── crypto_analyzer.py     # 加密分析
│   │   ├── parse_strategy.py      # 解析策略
│   │   └── source_navigation.py   # 源码导航
│   ├── client/               # 客户端
│   │   ├── rule_engine_client.py  # JAR 通信客户端（带超时保护）
│   │   ├── debug_runner.py        # 调试运行器（auto_fixer接入）
│   │   ├── batch_runner.py        # 批量运行器
│   │   ├── obstacle_resolver.py   # 障碍解决器
│   │   └── user_interaction.py    # 用户交互
│   ├── experience/            # 经验管理
│   │   ├── experience_manager.py  # 经验管理器（接入主流程）
│   │   └── conflict_resolver.py   # 冲突解决器
│   ├── delegate/             # 委托层
│   │   ├── webview_delegate.py     # WebView 委托（Playwright）
│   │   └── ocr_delegate.py         # OCR 委托（实现）
│   ├── utils/                # 工具
│   │   ├── config.py              # 配置管理
│   │   ├── file_utils.py          # 文件工具
│   │   ├── jvm_helpers.py         # JVM 辅助
│   │   └── logger.py              # 日志
│   └── tests/                # 测试
│       ├── test_source_validator.py
│       ├── test_rule_precheck.py
│       ├── test_error_diagnoser.py
│       ├── test_auto_fixer.py
│       ├── test_rule_engine_client.py
│       └── test_debug_runner.py
└── tools/                    # JAR 仿真服务端（仅保留 Kotlin 项目）
    ├── legado-jvm/           # Kotlin 项目
    ├── rhino-1.8.1.jar       # Rhino 引擎
    └── degradation_config.json # 降级配置
```

#### 4.1.2 虚拟环境管理

**requirements.txt**：
```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
jsonpath-ng>=1.6.0
pyyaml>=6.0
```

**setup.py**：
```python
from setuptools import setup, find_packages
setup(
    name="legado-client",
    version="2.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "legado-client=legado_client.cli:main",
        ],
    },
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
    ],
)
```

**setup_venv.bat**：
```bat
@echo off
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -e .
pip install pytest pytest-cov
echo Virtual environment setup complete.
echo Run: .venv\Scripts\activate.bat
```

### 4.2 协同逻辑

#### 4.2.1 auto_fixer 接入主流程

**当前偏差**：`debug_runner.apply_auto_fix()` 仅处理 `relative_url` 一种错误类型，`auto_fixer.py` 的 12 种修复能力未被调用。

**修复方案**：
```python
# debug_runner.py
from legado_client.analyzer.auto_fixer import auto_fix_error

# 替换 apply_auto_fix() 调用
# 修复前
result = apply_auto_fix(error_type, source_obj, ...)  # 仅处理 relative_url

# 修复后：调用完整修复能力
result = auto_fix_error(source_obj, error_info, ...)  # 12 种修复能力
```

**auto_fixer.py 的 12 种修复能力**：
1. `relative_url` - 相对 URL 修复
2. `missing_protocol` - 缺失协议修复
3. `json_path_error` - JSONPath 语法修复
4. `css_selector_error` - CSS 选择器修复
5. `xpath_error` - XPath 语法修复
6. `regex_error` - 正则表达式修复
7. `js_syntax_error` - JS 语法修复
8. `encoding_error` - 编码问题修复
9. `url_template_error` - URL 模板修复
10. `field_mapping_error` - 字段映射修复
11. `rule_type_error` - 规则类型修复
12. `book_list_error` - 书单列表修复

#### 4.2.2 verify_fix 真正验证

**当前偏差**：`verify_fix()` 仅 ping JVM，不执行实际规则验证。

**修复方案**：
```python
def verify_fix(source_obj: dict, source_type: str, client: RuleEngineClient) -> dict:
    """修复后验证：执行实际规则验证"""
    if source_type == "book":
        result = client.debug_book_source(source_obj, validate_mode=True)
    else:
        result = client.debug_rss_source(source_obj, validate_mode=True)
    return {
        "passed": result.get("success", False),
        "details": result
    }
```

#### 4.2.3 经验闭环接入主流程

**当前偏差**：`experience_manager.extract()`/`write_to_basic_memory()` 已实现但未被调用。

**修复方案**：在 `debug_runner.py` 主流程中集成经验管理：
```python
# debug_runner.py 主流程
def run(source_path, source_type, ...):
    # ... 预校验 → JVM 调试 → 错误诊断 → 自动修复 → 验证 ...

    # 经验提取与写入（新增）
    if debug_result.get("errors") or fix_result.get("applied"):
        experience = experience_manager.extract(
            source_obj, debug_result, fix_result
        )
        experience_manager.write_pending(experience)
        # 输出 MCP 指令供 AI agent 消费
```

#### 4.2.4 预校验失败返回 Phase 2

**当前偏差**：预校验失败时 `sys.exit(1)` 直接退出。

**修复方案**：
```python
# 修复前
if not validation_result["valid"]:
    sys.exit(1)

# 修复后：返回错误信息，由调用方决定是否回退到 Phase 2
if not validation_result["valid"]:
    return {
        "success": False,
        "stage": "precheck",
        "errors": validation_result["errors"],
        "suggestion": "返回 Phase 2 修复规则后重试"
    }
```

### 4.3 AI 友好性

#### 4.3.1 结构化输出

所有 Python 客户端输出采用结构化 JSON，便于 AI agent 解析：
```python
{
    "stage": "debug",
    "success": true/false,
    "source_name": "...",
    "details": {...},
    "errors": [...],
    "fixes_applied": [...],
    "experience_pending": "...",  # MCP 指令
    "next_action": "..."  # 建议的下一步操作
}
```

#### 4.3.2 经验 MCP 指令输出

```python
def write_pending(self, experience: dict) -> str:
    """写入 pending 经验，返回 MCP 指令"""
    pending_path = self._write_pending_json(experience)
    mcp_instruction = {
        "tool": "run_mcp",
        "server": "mcp_basic-memory",
        "method": "write_note",
        "args": {
            "project": "legado",
            "title": experience["title"],
            "content": experience["content"],
            "tags": experience["tags"]
        }
    }
    print(f"[EXPERIENCE_PENDING] {json.dumps(mcp_instruction)}")
    return pending_path
```

### 4.4 工具集整合

#### 4.4.1 14 个独立脚本整合为统一 CLI

```python
# legado_client/cli.py
import argparse

def main():
    parser = argparse.ArgumentParser(prog="legado-client")
    subparsers = parser.add_subparsers(dest="command")

    # debug 命令（替代 debug-source.py）
    debug_parser = subparsers.add_parser("debug")
    debug_parser.add_argument("--source", required=True)
    debug_parser.add_argument("--type", choices=["book", "rss"], default="book")

    # verify 命令（替代 quick-verify.py）
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--source", required=True)

    # batch 命令（替代 run-full-regression.py）
    batch_parser = subparsers.add_parser("batch")
    batch_parser.add_argument("--dir", required=True)

    args = parser.parse_args()
    # 分发到对应处理函数
```

#### 4.4.2 tools/ 目录整合

| tools/ 文件 | 处理方式 | 目标位置 |
|------------|---------|---------|
| `degradation_chain.py` | 保留（被 legado_client/ 引用） | 原地保留 |
| `error_translator.py` | 保留（被 legado_client/ 引用） | 原地保留 |
| `workflow_timer.py` | 保留（被 legado_client/ 引用） | 原地保留 |
| `cookie_manager.py` | 移除（不存在模块） | 删除 |
| `smart_http_client.py` | 移除（不存在模块） | 删除 |
| `knowledge_matcher.py` | 移除（不存在模块） | 删除 |
| `fetch_html.py` | 移动 | `legado_client/utils/` |
| `html_fetcher.py` | 移动 | `legado_client/utils/` |
| `debug-source.py` | 整合 | CLI `debug` 命令 |

#### 4.4.3 webview_delegate.py 路径修复

**当前偏差**：导入路径与实际文件位置不一致。

**修复方案**：修正 `delegate/webview_delegate.py` 的导入路径，确保 `from legado_client.delegate.webview_delegate import ...` 可正常导入。

#### 4.4.4 ocr_delegate.py 实现

**当前偏差**：文件存在但内容为空。

**修复方案**：实现基础 OCR 委托：
```python
# 简化说明：OCR 委托为占位实现 | 已知上限：验证码源无法自动识别 | 升级路径：集成 Tesseract/PaddleOCR
class OcrDelegate:
    def recognize(self, image_path: str) -> str:
        """OCR 识别（当前为占位实现）"""
        raise NotImplementedError(
            "OCR 功能未实现，请手动输入验证码。"
            "升级路径：集成 Tesseract 或 PaddleOCR"
        )
```

---

## 5. 经验知识库完善方案

### 5.1 双写一致性

**问题**：Skill 文档（references/）与 basic-memory 经验索引可能不一致。

**双写规则**：

| 写入时机 | Skill 文档（权威源） | basic-memory（索引层） |
|---------|---------------------|----------------------|
| Phase 5 经验反哺 | **先写**：完整内容写入 references/ | **后写**：摘要 + 指针写入 basic-memory |
| 日常维护 | 直接编辑 | 通过 `write_note` 同步 |
| 冲突时 | **以 Skill 文档为准** | basic-memory 自动更新对齐 |

**一致性校验**：
```python
# experience_manager.py
def verify_consistency(self) -> dict:
    """校验 Skill 文档与 basic-memory 的一致性"""
    skill_experiences = self._scan_skill_references()
    memory_experiences = self._search_basic_memory("all")
    # 对比标题和标签，报告不一致项
    return {
        "skill_only": [...],  # 仅 Skill 有
        "memory_only": [...],  # 仅 basic-memory 有
        "consistent": [...]  # 一致
    }
```

### 5.2 闭环反哺机制

```
Phase 3 测试驱动
    │
    ├── 调试成功 → 无需经验反哺
    │
    └── 调试失败
         │
         ├── error_diagnoser 诊断错误
         ├── auto_fixer 尝试修复
         ├── verify_fix 验证修复
         │
         └── experience_manager.extract()
              │
              ├── 写入 references/（权威源，完整内容）
              ├── 写入 basic-memory（索引层，摘要+指针）
              └── 输出 MCP 指令到 stdout
                   │
                   └── AI agent 消费 MCP 指令
                        │
                        └── 下次 Phase 1 可检索到新经验
```

**降级路径**：如果 AI agent 未消费 MCP 指令，经验仍保存在 `pending.json` 中，下次 Phase 1 可通过 `rglob` 搜索 `pending.json` 获取。

---

## 6. 测试体系升级方案

### 6.1 测试有效性审计

**问题**：V1 中存在"空壳测试"——测试用例过于简单，无法覆盖真实场景。

**审计标准**：

| 审计维度 | 标准 | V1 状态 | V2 要求 |
|---------|------|---------|---------|
| 测试源真实性 | 必须使用真实网站源 | 仅用本地构造的简单源 | 50+ 真实源 |
| 测试覆盖度 | 覆盖 5 种解析方式 | 仅 CSS/JSONPath | CSS/XPath/JSONPath/JS/Regex 全覆盖 |
| 测试深度 | 搜索→详情→目录→正文全链路 | 仅搜索 | 全链路 |
| 复杂源覆盖 | 含加密/分页/重定向 | 无 | ≥ 30% 复杂源 |
| 修复验证 | verify_fix 执行实际验证 | 仅 ping | 实际规则验证 |
| 经验反哺 | 测试失败触发经验写入 | 无 | 强制写入 |

### 6.2 全链路测试

**书源全链路**：
```
搜索（searchUrl）→ 详情（ruleBookInfo）→ 目录（ruleToc）→ 正文（ruleContent）→ 分页（nextContentUrl）
```

**订阅源全链路**：
```
分类（ruleArticles）→ 列表（ruleArticles）→ 正文（ruleContent）→ 分页（nextContentUrl）
```

### 6.3 诊断修复

**诊断流程**：
```
调试失败 → error_diagnoser.diagnose() → 错误分类（12种）
    │
    ├── 可自动修复 → auto_fixer.auto_fix_error() → verify_fix() → 验证通过？
    │                                                      ├── 是 → 经验反哺
    │                                                      └── 否 → 人工介入
    │
    └── 不可自动修复 → 输出修复建议 → 人工介入
```

### 6.4 降级机制

**降级路径**：

| 场景 | 降级方式 | 触发条件 |
|------|---------|---------|
| JAR 不可用 | Python `verify-source.py` 基本校验 | JVM 启动失败/超时 |
| JAR 超时 | kill JVM + 返回超时错误 | 30s 无响应 |
| WebView 需要 | Python Playwright 委托 | `WebViewRequiredException` |
| 登录需要 | 用户导入 Cookie | `UserInterventionException` |
| 验证码需要 | 用户手动输入 | `UserInterventionException` |
| CF 防护 | Python cloudscraper | 检测到 CF Challenge |

```python
# debug_runner.py 降级逻辑
def run(source_path: str, source_type: str, ...):
    try:
        client = init_jvm_client(args)
    except (FileNotFoundError, RuntimeError):
        print("[WARN] JAR 仿真服务端不可用，降级到 Python 模式")
        return _run_python_fallback(source_path, source_type)
```

---

## 7. 执行偏差复盘与机制修正

### 7.1 懒原则边界重定义

**问题**：V1 中将"减少过度工程"曲解为"跳过必要实现"。

**重定义边界**：

| 类别 | 定义 | 示例 | 处理方式 |
|------|------|------|---------|
| **必做项（不可简化）** | 与主功能强绑定的配套工程逻辑 | 入参校验、异常处理、资源释放、错误反馈 | **必须完整实现** |
| **增值项（可裁剪）** | 用户未提及、与主功能无绑定、后期补充成本低 | 额外的配置选项、未要求的扩展接口 | 可不实现（YAGNI） |
| **过度工程（应避免）** | 为不可能场景做错误处理、为一次性操作创建抽象 | 单次使用的工厂模式、不可能触发的异常处理 | 不实现 |

**判定流程**：
```
每个功能点 → 是否用户明确要求？
    ├── 是 → 必做项，不可简化
    └── 否 → 是否与主功能强绑定？
              ├── 是 → 必做项，不可简化
              └── 否 → 增值项，可裁剪
```

### 7.2 偏差深度复盘

| # | 偏差 | 当初理由 | 实际后果 | 根因 | 修正措施 |
|---|------|---------|---------|------|---------|
| 1 | 12 个 Bug 仅修复 5 个 | "懒原则，优先级" | 7 个高风险 Bug 遗留，真实源运行失败 | 懒原则滥用 | **全部修复，不可跳过** |
| 2 | auto_fixer 仅接入 1/12 能力 | "简化说明" | 修复能力严重不足 | 懒原则：简化版替代完整实现 | **接入完整 auto_fixer** |
| 3 | verify_fix 仅 ping JVM | "简化说明" | 修复验证空转 | 懒原则：最简检查替代实际验证 | **执行实际规则验证** |
| 4 | 经验闭环未接入主流程 | "后续接入" | 经验无法反哺 | 延迟接入导致遗忘 | **本次必须接入** |
| 5 | 回避复杂书源测试 | "找最简单的源" | 仿真端无法支持真机源 | 回避困难 | **50+ 真实源强制测试** |
| 6 | 未校验子代理输出 | "信任子代理" | 空壳实现被标记已完成 | 缺乏验证机制 | **交叉验证强制化** |
| 7 | 实施决策未同步文档 | "后续更新" | 文档失去参考价值 | 延迟更新导致遗忘 | **决策即记录** |
| 8 | 3 个不存在模块不处理 | "try/except 降级" | 永远不可用的代码路径 | 回避问题 | **移除或实现** |

### 7.3 大型任务上下文管理方案

**问题**：V1 中 170+ 子任务因上下文不足导致大量未完成。

**管理方案**：

1. **分批执行**：将大型任务拆分为 ≤ 12 个源文件/批，每批独立执行
2. **检查点机制**：每批完成后输出 `[BATCH_COMPLETE]` 标志，记录完成状态
3. **上下文传递**：批次间通过临时文档（`docs/temp-analysis/`）传递上下文
4. **进度追踪**：使用 `tasks.md` 实时更新任务状态
5. **交叉验证**：每批结果由独立子代理验证，不信任单一来源

```
大型任务 → 拆分为 N 批（≤ 12 文件/批）
    │
    ├── 批次1 → [BATCH1_COMPLETE] → 临时文档1
    ├── 批次2 → [BATCH2_COMPLETE] → 临时文档2
    │   ...
    └── 批次N → [BATCHN_COMPLETE] → 临时文档N
         │
         └── 交叉验证子代理 → 验证报告 → 修复
```

---

## 8. 真实样本验证方案

### 8.1 测试集构建

| 类型 | 数量 | 来源 | 覆盖场景 |
|------|------|------|---------|
| 书源 | 50+ | 开源阅读社区、用户提供的源 | CSS/XPath/JSONPath/JS/Regex 五种解析 |
| 订阅源 | 50+ | 开源阅读社区、用户提供的源 | singleUrl/multiUrl/JS规则/分页 |

### 8.2 测试分类

| 类别 | 书源数量 | 订阅源数量 | 覆盖场景 | 说明 |
|------|---------|----------|---------|------|
| 简单（纯 CSS/JSONPath） | 10 | 10 | 基线验证 | 无 JS、无加密、无分页 |
| 中等（含 JS 规则） | 15 | 15 | JS 执行验证 | 含 `<js>` 规则、@js: 前缀 |
| 复杂（加密/分页/重定向） | 15 | 15 | 核心能力验证 | 含 AES/Base64 加密、分页、重定向 |
| 特殊（WebView/登录/CF） | 10 | 10 | 降级路径验证 | 需 WebView/登录/CF 防护 |

### 8.3 验收标准

| 指标 | 目标 | 最低可接受 |
|------|------|----------|
| 总通过率 | ≥ 95% | ≥ 90% |
| 简单源通过率 | 100% | ≥ 95% |
| 中等源通过率 | ≥ 95% | ≥ 90% |
| 复杂源通过率 | ≥ 90% | ≥ 80% |
| 特殊源通过率 | ≥ 80% | ≥ 60%（降级路径验证通过即可） |
| 单源调试耗时 | ≤ 30s | ≤ 60s |
| 50 源批量耗时 | ≤ 5min | ≤ 10min |

### 8.4 闭环流程

```
1. 收集 50+ 书源 + 50+ 订阅源 JSON
2. 对每个源执行：
   a. source_validator.validate() → 预校验
   b. rule_precheck.precheck() → 语法预检
   c. RuleEngineClient.debug_book_source/debug_rss_source() → JVM 调试
   d. 收集调试结果（成功/失败/失败原因）
   e. 失败时：error_diagnoser.diagnose() → auto_fixer.auto_fix_error() → verify_fix()
   f. experience_manager.extract() → write_pending() → 经验记录
3. 生成汇总报告：
   - 通过率（目标 ≥ 95%）
   - 失败原因分类
   - 需要用户介入的源列表
   - 新增经验记录
4. 经验反哺：AI agent 消费 MCP 指令 → basic-memory
5. 回归测试：修复后重新执行失败源测试
```

### 8.5 测试结果报告格式

```json
{
  "summary": {
    "total": 50,
    "passed": 47,
    "failed": 3,
    "pass_rate": "94%",
    "categories": {
      "simple": {"total": 10, "passed": 10},
      "medium": {"total": 15, "passed": 14},
      "complex": {"total": 15, "passed": 13},
      "special": {"total": 10, "passed": 10}
    }
  },
  "failures": [
    {
      "source_name": "xxx",
      "source_url": "https://...",
      "stage": "search",
      "error_type": "js_error",
      "error_message": "Rhino: ReferenceError: \"fetch\" is not defined",
      "fix_attempted": true,
      "fix_result": "failed",
      "fix_reason": "ES6 fetch API not supported by Rhino",
      "user_action_needed": "Replace fetch with ajax()",
      "experience_recorded": true
    }
  ],
  "new_experiences": [
    {
      "title": "ES6 fetch API not supported by Rhino",
      "tags": ["js", "rhino", "es6", "fetch"],
      "content": "Rhino 1.8.1 不支持 ES6 fetch API，需替换为 ajax()"
    }
  ]
}
```

---

## 9. 实施决策记录

| ID | 决策 | 理由 | 风险 | 缓解 |
|----|------|------|------|------|
| V2-AD01 | 确立四层架构（经验知识库+Python客户端+JAR仿真+源码兜底） | 明确各层职责，源码作为最终兜底避免臆测 | 层间通信开销 | 协议标准化（stdin/stdout JSON） |
| V2-AD02 | 源码核实后仅 2 个 Bug 需修复（BUG-02/06），其余 5 个已修复或误判 | 源码逐行核实确认真实状态，避免无效工作 | 误判可能遗漏真实 Bug | 每个修复配套验证用例 + 50+ 源回归测试 |
| V2-AD03 | 4 个 GAP 分类处理（修复/降级/文档化），GAP-44 源码核实确认正常无需处理 | 根据影响范围和实现成本分类，GAP-44 经核实无需移除 | 降级项可能影响部分源 | 文档化已知限制 + 升级路径 |
| V2-AD04 | Python 客户端 9 项偏差系统性修复 | 偏差相互关联，需系统性修复 | 修复范围大 | 分阶段实施 + 测试覆盖 |
| V2-AD05 | 懒原则边界重定义，明确必做项不可简化 | 防止 V1 偏差重演 | 边界判定主观 | 判定流程标准化 |
| V2-AD06 | 50+ 真实源端到端测试强制执行 | V1 回避测试导致问题遗留 | 部分源可能网站失效 | 更新失效源，保持 50+ 有效源 |
| V2-AD07 | 经验双写一致性（Skill 文档 + basic-memory） | 防止经验索引与权威源不一致 | 双写可能不同步 | 一致性校验 + Skill 文档为准 |
| V2-AD08 | 测试有效性审计机制 | 防止空壳测试 | 审计标准可能不够全面 | 6 维度审计标准 |
| V2-AD09 | 大型任务上下文管理（分批+检查点） | 防止上下文不足导致任务未完成 | 分批可能遗漏关联 | 交叉验证 + 临时文档传递 |
| V2-AD10 | 子代理输出交叉验证强制化 | 防止空壳实现被标记已完成 | 验证增加工作量 | 独立验证子代理 |

---

## 10. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 7 个 Bug 修复引入新问题 | 中 | 高 | 每个修复配套验证用例 + 50+ 源回归测试 |
| OkHttp 版本一致性验证 | 低 | 低 | build.gradle.kts 已使用 5.3.2，与真机一致，无需变更 |
| runBlocking 消除引入死锁 | 低 | 高 | 仅 main 入口用 runBlocking，内部全部 suspend |
| 50+ 真实源网站失效 | 高 | 低 | 更新失效源，保持 50+ 有效源 |
| auto_fixer 修复引入新问题 | 中 | 中 | verify_fix 真正验证修复效果 |
| fatJar 构建冲突 | 低 | 中 | duplicatesStrategy EXCLUDE |
| Python 客户端整合破坏现有功能 | 中 | 中 | 逐步整合 + 测试覆盖 |
| 经验双写不一致 | 中 | 中 | 一致性校验 + Skill 文档为准 |
| 大型任务上下文不足 | 中 | 中 | 分批执行 + 检查点 + 临时文档 |
| GAP 降级项影响真实源 | 低 | 低 | 文档化已知限制 + 升级路径 |

---

## 11. File Changes

### 11.1 新增文件

| 文件 | 说明 |
|------|------|
| `scripts/setup.py` | Python 包安装配置 |
| `scripts/setup_venv.bat` | Windows 虚拟环境初始化 |
| `scripts/setup_venv.sh` | Linux/Mac 虚拟环境初始化 |
| `scripts/legado_client/__main__.py` | CLI 入口 |
| `scripts/legado_client/cli.py` | CLI 参数解析 |
| `scripts/legado_client/delegate/ocr_delegate.py` | OCR 委托实现（占位） |
| `scripts/legado_client/tests/test_source_validator.py` | source_validator 测试 |
| `scripts/legado_client/tests/test_rule_precheck.py` | rule_precheck 测试 |
| `scripts/legado_client/tests/test_error_diagnoser.py` | error_diagnoser 测试 |
| `scripts/legado_client/tests/test_auto_fixer.py` | auto_fixer 测试 |
| `scripts/legado_client/tests/test_rule_engine_client.py` | rule_engine_client 测试 |
| `scripts/legado_client/tests/test_debug_runner.py` | debug_runner 测试 |
| `tools/legado-jvm/SOURCE_VERSION` | 源码版本锚定 |
| `tools/legado-jvm/simulation-vs-real-diff.md` | 仿真端与真机差异追踪表 |

### 11.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `tools/legado-jvm/build.gradle.kts` | fatJar 配置（OkHttp 维持 5.3.2，仅验证一致性） |
| `tools/legado-jvm/src/.../RuleEngineServer.kt` | ~~BUG-01 修复（误判，无需修复）~~ + suspend 改造 + 诊断日志条件化 |
| `tools/legado-jvm/src/.../BookSourceDebugger.kt` | BUG-02 修复（日志标签"搜索页"→"发现页"）+ ~~BUG-07（已修复）~~ |
| `tools/legado-jvm/src/.../RssSourceDebugger.kt` | ~~BUG-03（已修复）~~ + GAP-22 对齐 |
| `tools/legado-jvm/src/.../AnalyzeRule.kt` | ~~BUG-04（已修复）~~ + scriptCache LRU + runBlocking 消除 |
| `tools/legado-jvm/src/.../AnalyzeUrl.kt` | ~~BUG-05（已修复）~~ + ~~GAP-44 清理（正常工作，不应移除）~~ + runBlocking 消除 + 诊断日志条件化 |
| `tools/legado-jvm/src/.../JsExtensionsStub.kt` | BUG-06 修复 + GAP-05/06 降级 + GAP-10 降级 + GAP-07 并发 |
| `scripts/legado_client/client/debug_runner.py` | auto_fixer 接入 + 经验闭环接入 + 降级路径 + 预校验返回 |
| `scripts/legado_client/client/rule_engine_client.py` | 超时保护 + 弃用方法清理 |
| `scripts/legado_client/analyzer/auto_fixer.py` | verify_fix 真正验证 |
| `scripts/legado_client/analyzer/source_validator.py` | 校验规则扩展（5→15 条） |
| `scripts/legado_client/analyzer/rule_precheck.py` | Rhino 兼容性检测 |
| `scripts/legado_client/experience/experience_manager.py` | 经验闭环修复 + 双写一致性 |
| `scripts/legado_client/delegate/webview_delegate.py` | 导入路径修复 |
| `scripts/requirements.txt` | 依赖声明 |
| `.gitignore` | 补充忽略规则 |
| `.trae/skills/legado-source-creator/SKILL.md` | 4 处"实现状态"标注更新 + Phase 5 经验消费规范 |
| `.trae/skills/legado-source-creator/AI_README.md` | V2 变更同步 |
| `docs/AGENTS.md` | V2 变更同步 |

### 11.3 删除文件

| 文件 | 原因 |
|------|------|
| `tools/__pycache__/` | Python 缓存 |
| `tools/legado-jvm/build/` | Gradle 构建产物 |
| `tools/cookie_manager.py` | 不存在模块，被 try/except 引用 |
| `tools/smart_http_client.py` | 不存在模块 |
| `tools/knowledge_matcher.py` | 不存在模块 |
| `.trae/skills/output/experience-pending.json` | 孤立文件（移入 legado-source-creator/output/） |
| `tools/debug-source.py` | 整合为 CLI `debug` 命令 |
| `tools/quick-verify.py` | 整合为 CLI `verify` 命令 |
| `tools/run-full-regression.py` | 整合为 CLI `batch` 命令 |
