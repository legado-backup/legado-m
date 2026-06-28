# Design: Legado Skill 整体优化方案

> **统一技术设计**：合并 JAR 仿真服务端 + Python 客户端 + Skill 工作流
> **源码核实修正**：3 组子代理（27 个源文件）逐行核实，修正 18 个设计文档错误

---

## Technical Approach

### 总体架构：三层协作

```
┌─────────────────────────────────────────────────────────────────────┐
│              legado-source-creator Skill（编排层）                    │
│                                                                     │
│  5 阶段闭环工作流：                                                   │
│  Phase 1: 经验优先（basic-memory 检索）                              │
│  Phase 2: 构建规则 + 预校验（source_validator + rule_precheck）      │
│  Phase 3: 测试驱动（JAR 优先 + Python 降级）                         │
│  Phase 4: 源码深挖 + 工具辅助（source_navigation + auto_fixer）      │
│  Phase 5: 经验反哺 + 代码进化（半自动写入 basic-memory）             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼
┌───────────────────────┐    ┌──────────────────────────┐
│  Python 客户端（校验层）│    │  JAR 仿真服务端（执行引擎）│
│                        │    │                          │
│  预校验：source_validator│    │  规则引擎：AnalyzeRule     │
│  规则语法：rule_precheck │    │  JS 引擎：Rhino           │
│  调试流程：debug_runner  │◄──►│  HTTP 客户端：OkHttp       │
│  错误诊断：error_diagnoser│   │  调试器：BookSourceDebugger│
│  自动修复：auto_fixer    │    │          RssSourceDebugger│
│  经验管理：experience_mgr │    │  加密解密：hutool          │
│  用户交互：user_interaction│   │  委托路径：Selenium/环境变量│
└───────────────────────┘    └──────────────────────────┘
```

### 数据流

```
用户输入网站 URL
  ↓
AI 使用 Skill 生成 BookSource/RssSource JSON
  ↓
Phase 2: 构建规则 + 预校验（source_validator + rule_precheck）
  ↓ 预校验通过
Phase 3: 测试驱动（JAR 优先，降级 Python）
  ↓ JAR 调试
  ├→ 成功：confidence_evaluator 评估可信度
  └→ 失败：error_diagnoser 诊断
       ├→ 可自动修复：auto_fixer 修复 → 重试（最多 3 次）
       └→ 需用户介入：user_interaction 生成交互请求
  ↓
Phase 5: 经验反哺（半自动写入 basic-memory）
  ↓
输出最终源 + 测试报告 + 经验草稿
```

### 架构合理性审查（第十轮新增）

第十轮审查发现三层协作架构存在 4 个潜在问题，需在设计文档中明确解决方案：

| 问题 | 描述 | 解决方案 |
|------|------|---------|
| **经验管理职责重叠** | experience_manager 在 Python 层（提取/生成草稿），Phase 5 经验反哺在 Skill 层（审核/写入 basic-memory） | 明确分工：experience_manager 负责提取和生成草稿（数据层），Skill 负责审核和写入决策（编排层）。experience_manager.write_to_basic_memory() 返回 MCP 调用指令，由 AI agent 执行 |
| **用户交互职责重叠** | user_interaction 在 Python 层（生成标准化交互请求），用户介入决策在 Skill 层 | 明确分工：user_interaction 生成标准化交互请求模板（数据层），Skill 决定是否请求用户介入（编排层）。Python 层不直接请求用户介入，只生成请求模板 |
| **降级模式可信度有限** | Python 降级模式只支持搜索和详情，目录和正文不支持，结果标注"建议用 JAR 复验" | 明确定位：降级模式是"快速预检"而非"完整校验"，用于 JAR 不可用时的应急方案。降级模式结果可信度为 medium，AI 应优先修复 JAR 环境而非依赖降级模式 |
| **source_navigation 与"减少源码依赖"矛盾** | source_navigation 提供"自动映射到源码位置"，但"减少源码依赖"要求 AI 无需查阅源码 | 明确定位：source_navigation 提供源码位置作为**辅助参考**，主要价值是修复建议模板。AI 优先使用修复建议，源码位置仅在修复建议不足时作为深入分析的入口 |

---

## 一、JAR 仿真服务端修复方案

### 1.1 批量测试失败源根因分析

```
总源数: 100 | 成功: 0 | 失败: 100 | 成功率: 0%
失败分类: code 35 | network 33 | data 24 | other 7 | intervention 1
```

**关键结论**：100 个失败中，仿真端问题仅 2 个（2%），其余 98 个是源规则问题或网站问题。

### 1.2 低难度修复（12 个）

#### 1.2.1 属性 var→val 签名修正（6 个）

**真机源码**：`BaseSource.kt`（**源码核实修正：BaseSource 是 interface 不是 class**）中 concurrentRate/loginUrl/loginUi/header/enabledCookieJar/jsLib 均为 `var`

**修复方案**：改为 `var`，添加 setter

#### 1.2.2 dateFormat 格式对齐

**真机源码**（**源码核实修正：dateFormat 在 AppConst 不在 BaseSource**）：`AppConst.dateFormat` = `"yyyy/MM/dd HH:mm"`

**修复方案**：读取 `LEGADO_DATE_FORMAT` 环境变量，默认 `"yyyy/MM/dd HH:mm"`

#### 1.2.3 aesEncodeToString 对齐真机 bug

**真机源码**（**源码核实修正：aesEncodeToString 在 JsEncodeUtils 不在 JsExtensions**）：`JsEncodeUtils.kt` 中 `aesEncodeToString` 误用 `decryptStr`（**疑似源码 Bug，加密方法调用解密**）

**修复方案**：仿真端当前是正确的（用 encrypt），需反向引入真机 bug 以 100% 对齐

### 1.3 中难度修复（18 个）

#### 1.3.1 base64/AES flags 映射完善（6 个）

**真机源码**：`android.util.Base64`，flags 值：NO_WRAP=2, NO_PADDING=1, URL_SAFE=8

**源码核实修正**：`mapBase64Flags` 方法不存在，需新建映射逻辑

**修复方案**：新建 flags 映射函数

```kotlin
fun mapBase64Flags(flags: Int): Int {
    var result = 0
    if (flags and 1 != 0) result = result or Base64.NO_PADDING
    if (flags and 2 != 0) result = result or Base64.NO_WRAP
    if (flags and 8 != 0) result = result or Base64.URL_SAFE
    return result
}
```

#### 1.3.2 putConcurrent 实现

**真机源码**（**源码核实修正：ConcurrentRecord 定义在 AnalyzeUrl 中，非 ConcurrentRateLimiter**）

**修复方案**：实现 ConcurrentRateLimiter 更新，ConcurrentRecord 从 AnalyzeUrl 引用

### 1.4 高难度修复（8 个）

#### 1.4.1 getLoginInfoMap 实现 RowUi 解析

**真机源码**（**源码核实修正：getLoginInfoMap 在 BaseSource 不在 JsExtensions**）

**修复方案**：移植 RowUi 解析逻辑（剥离 Android UI 依赖）

### 1.5 委托路径实现

#### 1.5.1 WebView 渲染委托（9 个方法）

```
仿真端 webView()
  → 抛出 WebViewRequiredException(url, html, js, cacheFirst)
  → Python 客户端捕获异常
  → Selenium 执行 JS 渲染
  → 回传渲染结果
  → 仿真端继续处理
```

#### 1.5.2 硬件信息环境变量配置（4 个方法）

```kotlin
val androidId: String
    get() = System.getenv("LEGADO_ANDROID_ID") ?: "000000000000000"

val webViewUA: String
    get() = System.getenv("LEGADO_WEBVIEW_UA")
        ?: "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 ..."
```

### 1.6 第四轮深度排查修复（31 个）

#### 1.6.1 GAP-36: JsExtensions 委托模式并发覆盖（P0）

**真机源码**（`AnalyzeRule.kt:55-62`）：
```kotlin
class AnalyzeRule(...) : JsExtensions {
    // 每个实例持有自己的 source/ruleData
}
```

**修复方案**：将 JsExtensionsStub 从全局单例改为实例化模式

#### 1.6.2 GAP-37: ConcurrentRateLimiter 空实现（P0）

**真机源码**（**源码核实修正：ConcurrentRecord 定义在 AnalyzeUrl 中**）

**修复方案**：移植真机 ConcurrentRateLimiter 完整实现，ConcurrentRecord 从 AnalyzeUrl 引用

#### 1.6.3 GAP-44: AnalyzeUrl 新增 followRedirects（仿真端多余功能）

**源码核实修正**：AnalyzeUrl 无 followRedirects 字段，GAP-44 描述需修正为"仿真端新增的字段需移除"

**修复方案**：移除仿真端 AnalyzeUrl 中的 followRedirects 字段和逻辑

#### 1.6.4 GAP-54: Book 数据模型差异

**源码核实修正**：BookType.text=0b1000（8），非 0b1

**修复方案**：
- type 默认值改为 BookType.text(0b1000)
- origin 默认值改为 "loc_book"
- infoHtml/tocHtml 改为 @Ignore

### 1.7 第五轮深度排查修复（41 个）

#### 1.7.1 GAP-67a: loginCheckJs 完全缺失（P0）

**真机源码**（`WebBook.kt:70-78`/`Rss.kt:108-110`）：所有阶段执行 loginCheckJs

**修复方案**：在 BookSourceDebugger/RssSourceDebugger 所有阶段添加 loginCheckJs 检测逻辑

#### 1.7.2 GAP-67b: ruleNextPage=="PAGE" 特殊处理缺失（P0）

**源码核实修正**：ruleNextPage=="PAGE" 在 `model/rss/RssParserByRule.kt`（非 `rss/RssParserByRule.kt`，非 WebBook.kt）；使用 `uppercase(Locale.getDefault())` 转大写后比较，`"page"`/`"Page"`/`"PAGE"` 均可匹配

**修复方案**：在目录/正文分页逻辑中添加 `ruleNextPage.uppercase() == "PAGE"` 分支处理

#### 1.7.3 GAP-67c: init 规则执行方式不同（P0）

**源码核实修正**：init 规则在 BookInfo.kt 非 WebBook.kt

**修复方案**：将 init 规则执行方式改为 getElement

#### 1.7.4 GAP-67d: BookContent 正文格式化链完全缺失（P0）

**源码核实修正**：HtmlFormatter 方法名是 format/formatKeepImg（非 formatHtml）；文件路径是 `utils/HtmlFormatter.kt`（非 `help/book/HtmlFormatter.kt`，`BookInfo.kt:14` import 证实）

**修复方案**：移植完整正文格式化链

```kotlin
content = HtmlFormatter.formatKeepImg(content)
content = StringEscapeUtils.unescapeHtml4(content)
if (book.useHtmlMap) content = HtmlMap.format(content)
content = applyReplaceRegex(content, replaceRegex)
```

#### 1.7.5 GAP-70a: Rhino JS 引擎配置严重缺失（P0，重新设计）

**源码核实修正**：
- instructionObserverThreshold=10000（非 1000）
- maximumInterpreterStackDepth=1000
- WrapFactory 依赖 ClassShutter（wrapAsJavaObject 返回 null，wrapJavaClass 返回 NativeJavaPackage）

**重新设计方案**（AD-11）：
- 移植 WrapFactory（**修改移除对 ClassShutter 的调用**，让所有 Java 类都可见）
- 移植 NativeBaseSource
- 自定义 observeInstructionCount 实现（直接抛出 TimeoutException 中断死循环）
- 设置 instructionObserverThreshold=10000
- 设置 maximumInterpreterStackDepth=1000

#### 1.7.6 GAP-70b: 并发模型根本性差异（P0，重新设计）

**重新设计方案**（AD-12）：只添加 withTimeout 超时控制（HTTP 请求 + JS 执行）

### 1.8 第六轮深度排查修复（29 个）

#### 1.8.1 GAP-67: Room 数据库完全缺失（P0，重新设计）

**重新设计方案**：使用内存存储（ConcurrentHashMap），不引入数据库

#### 1.8.2 GAP-80: HTTP 拦截器全部缺失（P0，重新设计）

**重新设计方案**：只添加 2 个影响测试校验的拦截器：
1. UA 注入拦截器（GAP-83）
2. CookieJar 网络拦截器（GAP-82）

### 1.9 砍掉的 75 个过度修复项

| 类别 | 数量 | 代表 GAP | 理由 |
|------|------|---------|------|
| 持久化类 | 14 | GAP-68/69/71/33/31 | 单次调试会话内存存储足够 |
| 安全沙箱类 | 5 | GAP-72c ClassShutter | 测试环境不需要安全限制 |
| 性能差异类 | 8 | GAP-71a/96/95/94 | 不影响结果 |
| UI 层类 | 6 | GAP-98/99/65/66/74/89 | 不影响调试 |
| 日志类 | 5 | GAP-77/78/79 + Toast | 不影响校验结果 |
| 模块移植类 | 9 | GAP-69a~i | 内联实现行为对齐即可 |
| 其他 | 28 | SourceHelp/ACache/WebCacheManager 等 | 非校验职责 |

---

## 二、Python 客户端优化设计

### 2.1 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│              debug_runner.run() 核心调试流程                         │
│                                                                     │
│  1. 解析 source_obj                                                 │
│  2. source_validator 校验字段完整性 ──→ 失败：返回错误               │
│  3. rule_precheck 校验规则语法 ──→ 失败：返回错误                   │
│  4. experience_manager 检索历史经验                                 │
│  5. RuleEngineClient 调用 JAR ──→ 失败：降级 Python 模式           │
│  6. error_diagnoser 诊断错误                                        │
│     ├→ 可自动修复：auto_fixer 修复后重试（最多 3 次）              │
│     └→ 需用户介入：user_interaction 生成交互请求                    │
│  7. confidence_evaluator 评估可信度                                 │
│  8. experience_manager 输出经验草稿到 pending/                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 source_validator 预校验模块

#### 2.2.1 BookSource 必填字段校验

**源码核实修正**：searchUrl/ruleSearch 实际可空，不应标记为必填

| 字段 | 校验规则 | 错误级别 |
|------|---------|---------|
| bookSourceName | 非空 | ERROR |
| bookSourceUrl | 非空 + URL 格式合法 | ERROR |
| bookSourceType | 0/1/2/3（文本/音频/图片/文件） | ERROR |
| searchUrl | 非空（**源码核实修正：实际可空，降级为 WARN**） | WARN |
| ruleSearch.bookList | 非空（**源码核实修正：实际可空，降级为 WARN**） | WARN |

#### 2.2.2 RssSource 必填字段校验

**源码核实修正**：字段名是 type 非 sourceType；ruleArticles 实际可空

| 字段 | 校验规则 | 错误级别 |
|------|---------|---------|
| sourceName | 非空 | ERROR |
| sourceUrl | 非空 + URL 格式合法 | ERROR |
| type（**源码核实修正：非 sourceType**） | 0/1（RSS/自定义） | ERROR |
| ruleArticles | 非空（**源码核实修正：实际可空，降级为 WARN**） | WARN |

### 2.3 rule_precheck 规则语法预检查

#### 2.3.1 规则类型识别

**源码核实修正**（第九轮再修正）：

| 前缀 | 类型 | Python 校验库 | 源码核实 |
|------|------|--------------|---------|
| `@CSS:` | CSS 选择器 | soupsieve | AnalyzeRule.kt `startsWith("@CSS:")` |
| `@XPath:` | XPath | lxml | AnalyzeRule.kt `startsWith("@XPath:")` |
| `@Json:` | JSONPath | jsonpath-ng | AnalyzeRule.kt `startsWith("@Json:", true)` 忽略大小写，`@json:` 也能匹配，但源码规范用大写 J |
| `<js>...</js>` | JavaScript | 括号匹配 + 关键字检查 | AnalyzeRule.kt 通过 `JS_PATTERN` 正则匹配（非前缀判断） |
| `@js:` | JavaScript（规则解析中） | 同上 | AnalyzeRule.kt 通过 `JS_PATTERN` 正则匹配（非前缀）；BaseSource.kt 中 `startsWith("@js:")` 是前缀使用，共 3 处但 ignoreCase 不一致：第 76 行（loginUrl）无、第 108 行（header）有、第 193 行（loginUi）无 |
| 无前缀 | 默认 CSS（jsoup 语法） | soupsieve | AnalyzeRule.kt 默认走 jsoup 解析 |

**源码核实修正**：`<regex>` 前缀不存在；`@js:` 在不同文件中用法不同（AnalyzeRule 中是正则匹配，BaseSource 中是前缀）

### 2.4 debug_runner 流程调整

```python
def run(source_path: str, key: str = None, **kwargs) -> DebugResult:
    """核心调试流程入口"""
    # 1. 解析 source_obj
    source_obj = _load_source(source_path)
    source_type = _detect_source_type(source_obj)

    # 2. 预校验：字段完整性（新增）
    validator = SourceValidator(source_obj, source_type)
    result = validator.validate()
    if not result["valid"]:
        return DebugResult(success=False, stage="prevalidate",
                          errors=result["errors"], warnings=result["warnings"])

    # 3. 预校验：规则语法（新增）
    prechecker = RulePrecheck(source_obj, source_type)
    result = prechecker.precheck()
    if not result["valid"]:
        return DebugResult(success=False, stage="precheck",
                          errors=result["errors"], warnings=result["warnings"])

    # 4. 检索历史经验
    experience = experience_manager.search(source_obj, source_type)

    # 5. 调用 JAR 执行调试
    try:
        jar_result = rule_engine_client.debug(source_obj, key)
    except JARUnavailableError:
        # 降级到 Python 模式
        jar_result = _python_fallback_debug(source_obj, key)
        jar_result.degraded = True

    # 6. 错误诊断 + 自动修复
    if not jar_result.success:
        diagnosis = error_diagnoser.diagnose(jar_result.error, source_obj, source_type)
        if diagnosis.auto_fixable:
            for attempt in range(3):
                fixed_source = auto_fixer.fix(source_obj, diagnosis)
                jar_result = rule_engine_client.debug(fixed_source, key)
                if jar_result.success:
                    break
                diagnosis = error_diagnoser.diagnose(jar_result.error, fixed_source, source_type)
        elif diagnosis.need_user:
            interaction = user_interaction.create_request(diagnosis)
            return DebugResult(success=False, stage="debug",
                              need_user=True, interaction=interaction)

    # 7. 可信度评估
    confidence = confidence_evaluator.evaluate(jar_result, source_type)

    # 8. 经验输出
    experience_manager.output_draft(source_obj, source_type, jar_result, confidence)

    return DebugResult(
        success=jar_result.success,
        stage="complete",
        confidence=confidence,
        degraded=jar_result.degraded
    )
```

### 2.5 降级路径

当 JAR 不可用时，降级到 Python 模式：

| 阶段 | JAR 模式 | Python 降级模式 |
|------|---------|----------------|
| 搜索 | RuleEngineClient → JAR | requests + BeautifulSoup4 |
| 详情 | RuleEngineClient → JAR | requests + BeautifulSoup4 |
| 目录 | RuleEngineClient → JAR | 不支持（返回中可信度） |
| 正文 | RuleEngineClient → JAR | 不支持（返回中可信度） |

### 2.6 error_diagnoser 错误类型扩充

| 类别 | 错误类型 | 识别方式 | 修复建议 |
|------|---------|---------|---------|
| 预校验 | 字段缺失 | source_validator 输出 | 补充缺失字段 |
| 预校验 | 规则语法错误 | rule_precheck 输出 | 修正规则语法 |
| JAR 通信 | JAR 进程崩溃 | ConnectionRefusedError | 检查 JAR 是否启动 |
| JAR 通信 | JAR 超时 | TimeoutError | 检查网络或增加超时 |
| 规则执行 | CSS 选择器未匹配 | JAR 返回空结果 | 重新分析网站 HTML 结构 |
| 规则执行 | JS 执行错误 | JAR 返回 JS 异常 | 检查 JS 语法和变量 |
| 网络 | HTTP 403 | JAR 返回 403 | 网站反爬，需添加 Header |
| 网站 | 需要登录 | JAR 返回登录页面 | 需要用户提供登录信息 |
| 网站 | CF 防护 | JAR 返回 CF 挑战页面 | 需要用户破盾 |
| 仿真端 | 行为不一致 | 对比真机结果 | 检查 simulation-gap-report.md |

### 2.7 experience_manager 半自动经验写入

#### 2.7.1 经验要素自动提取

| 要素 | 提取来源 | 示例 |
|------|---------|------|
| 网站特征 | source_obj + URL | "使用 Nuxt.js SSR 框架" |
| 错误类型 | error_diagnoser 输出 | "CSS 选择器未匹配" |
| 修复方法 | auto_fixer 输出 | "改用首页 URL 替代/?page=路径" |
| 规则模式 | source_obj 中的规则 | "@CSS:.article-list .item" |
| 可信度 | confidence_evaluator 输出 | 0.92（高可信） |

#### 2.7.2 半自动写入流程

```
测试完成
  ├→ 1. experience_manager.extract() 提取经验要素
  ├→ 2. 生成 JSON 草稿到 experience/pending/
  ├→ 3. AI 审核草稿（可选，默认跳过）
  ├→ 4. 审核通过（或跳过审核）
  │    ├→ 4a. 写入 basic-memory（通过 MCP）
  │    └→ 4b. 写入 references/（通过文件写入，降级路径）
  └→ 5. conflict_resolver 检查冲突
       └→ 有冲突：按置信度+时效性+覆盖度评分选优
```

### 2.8 双客户端职责边界与整合方案

#### 2.8.1 现状分析（第九轮审查新增）

**当前架构**：
- `scripts/legado_client/`（16 个模块）：规范包结构，核心调试流程
- `tools/`（14 个模块）：扁平结构（无 `__init__.py`），可选辅助模块
- `scripts/` 独立脚本（10 个）：CLI 入口

**三个关键问题**：

1. **JVM 依赖断裂**：`tools/rule_engine_client.py` 已迁移到 `legado_client/client/`，但 5 个独立脚本（verify-source.py 等）仍引用旧路径，导致 JVM 验证功能全部失效（降级到纯 Python 模式）

2. **混合依赖**：debug_runner.py 同时导入两套模块：
   - 包内模块（直接 import）：rule_engine_client、error_diagnoser、confidence_evaluator 等
   - 外部 tools/ 模块（try-import 降级）：obstacle_resolver、crypto_analyzer、auto_fixer、interactive_guide

3. **职责割裂**：错误诊断在 `legado_client/analyzer/error_diagnoser.py`，但自动修复在 `tools/auto_fixer.py`；障碍解析在 `tools/obstacle_resolver.py`，但用户交互在 `legado_client/client/user_interaction.py`

#### 2.8.2 整合方案

**目标**：统一包结构，消除混合依赖，tools/ 仅保留独立工具。

**迁移清单**：

| tools/ 模块 | 迁移目标 | 理由 |
|------------|---------|------|
| auto_fixer.py | legado_client/analyzer/auto_fixer.py | 与 error_diagnoser 同属分析层 |
| obstacle_resolver.py | legado_client/client/obstacle_resolver.py | 与 user_interaction 同属客户端层 |
| crypto_analyzer.py | legado_client/analyzer/crypto_analyzer.py | 与 parse_strategy 同属分析层 |
| interactive_guide.py | legado_client/client/interactive_guide.py | 与 user_interaction 同属客户端层 |
| jvm_helpers.py | legado_client/utils/jvm_helpers.py | 与 config 同属工具层 |

**保留在 tools/ 的模块**（无包依赖的独立工具）：
- html_fetcher.py、fetch_html.py（HTML 获取回退链）
- cookie_manager.py、smart_http_client.py（HTTP 工具）
- knowledge_matcher.py、degradation_chain.py（辅助工具）
- error_translator.py、user_action_minimizer.py、workflow_timer.py

**依赖断裂修复**：
- 5 个独立脚本的 import 路径从 `from rule_engine_client import RuleEngineClient` 改为 `from legado_client.client.rule_engine_client import RuleEngineClient`
- 或通过 `legado_client/utils/jvm_helpers.py` 统一封装 JVM 客户端初始化

#### 2.8.3 整合后职责边界

| 模块 | 归属 | 职责 | 调用方式 |
|------|------|------|---------|
| source_validator | legado_client/analyzer/ | 源字段完整性校验 | debug_runner 内部调用 |
| rule_precheck | legado_client/analyzer/ | 规则语法校验 | debug_runner 内部调用 |
| debug_runner | legado_client/client/ | 核心调试流程 | debug-source.py CLI 入口 |
| error_diagnoser | legado_client/analyzer/ | 错误诊断 | debug_runner 内部调用 |
| auto_fixer | legado_client/analyzer/ | 自动修复 | debug_runner 内部调用（整合后） |
| experience_manager | legado_client/experience/ | 经验管理 | debug_runner 内部调用 |
| obstacle_resolver | legado_client/client/ | 障碍解析 | debug_runner 内部调用（整合后） |
| user_interaction | legado_client/client/ | 用户交互 | debug_runner 内部调用 |
| crypto_analyzer | legado_client/analyzer/ | 加密分析 | debug_runner 内部调用（整合后） |
| interactive_guide | legado_client/client/ | 交互引导 | debug_runner 内部调用（整合后） |

---

## 三、Skill 工作流优化

### 3.1 Phase 2 预校验（新增）

```
Phase 2: 构建规则
  ├→ 知识库查阅
  ├→ 分析网站类型
  ├→ 构建搜索/详情/目录/正文规则
  ├→ 处理特殊场景
  └→ 【新增】预校验
       ├→ source_validator 校验字段完整性
       └→ rule_precheck 校验规则语法
            └→ 失败：返回 Phase 2 重新构建
```

### 3.2 Phase 3 降级路径（优化）

```
Phase 3: 测试驱动
  ├→ 静态陷阱扫描
  ├→ 运行测试脚本
  │    ├→ JVM 优先（RuleEngineClient → JAR）
  │    └→ 【优化】JVM 不可用时降级到 Python 模式
  │         ├→ requests + BeautifulSoup4 执行简化调试
  │         └→ 标注"Python 降级模式，建议用 JAR 复验"
  ├→ 错误诊断
  │    ├→ 【优化】扩充错误类型（预校验/JAR 通信/仿真端差异）
  │    └→ 可自动修复：auto_fixer 修复后重试（最多 3 次）
  └→ 可信度分层
       ├→ 高可信：JAR 通过
       ├→ 中可信：JAR 失败但 Python 降级通过
       └→ 需真机：JAR 和 Python 都失败
```

### 3.3 Phase 4 工具辅助（优化）

```
Phase 4: 源码深挖（测试失败时）
  ├→ 【优化】source_navigation 自动导航到源码位置
  │    └→ 错误类型 → 源码文件和行号映射
  ├→ 【优化】error_diagnoser 提供修复建议
  │    └→ 不再需要 AI 手动查阅源码
  ├→ 【优化】auto_fixer 自动修复常见错误
  │    └→ CSS 选择器重写 / URL 修正 / 规则语法修正
  └→ 回到 Phase 3 重测
```

### 3.4 Phase 5 半自动经验写入（优化）

```
Phase 5: 经验反哺 + 代码进化
  ├→ 回顾新问题
  ├→ 验证（每条经验必须去源码核实）
  ├→ 【优化】文档反哺（半自动）
  │    ├→ experience_manager 自动提取经验要素
  │    ├→ 生成草稿到 pending/
  │    ├→ AI 审核（可选）
  │    └→ 写入 basic-memory / references/
  └→ 代码进化
       └→ Phase 3/4 识别仿真端差异 → 更新 simulation-gap-report.md
```

### 3.5 Phase 3 JVM 降级路径行为修正（第九轮审查新增）

**问题**：SKILL.md 描述"JVM 不可用时自动降级到 Python 模式，工作流继续执行"，但 debug_runner.py 实际实现是退出码 3 中断。

**修复方案**：

```python
# debug_runner.py 修改前（第 754-766 行）：
try:
    jar_result = rule_engine_client.debug(source_obj, key)
except JARUnavailableError:
    print("JAR 不可用，请使用 verify-source.py")
    sys.exit(3)  # ❌ 中断工作流

# 修改后：
try:
    jar_result = rule_engine_client.debug(source_obj, key)
except JARUnavailableError:
    # ✅ 自动降级到 Python 模式继续执行
    jar_result = _python_fallback_debug(source_obj, key)
    jar_result.degraded = True
    jar_result.confidence = "medium"  # 降级为中可信度
    jar_result.note = "Python 降级模式，建议用 JAR 复验"
```

**Python 降级模式实现**：
- 搜索阶段：requests + BeautifulSoup4 执行搜索（支持 CSS 选择器）
- 详情阶段：requests + BeautifulSoup4 执行详情解析
- 目录阶段：不支持（返回中可信度，标注"需 JAR 复验"）
- 正文阶段：不支持（返回中可信度，标注"需 JAR 复验"）

### 3.6 Phase 3 错误诊断覆盖扩充（第九轮审查新增，第十轮修正）

**问题**：auto_fixer 当前实际处理 4 种错误类型（`rule_parse`/`css`/`url_empty`/`network`，见 `tools/auto_fixer.py:471-476` fix_map），但 SKILL.md 描述"最多 3 次自动修复"，且 4 种覆盖不足——`TypeError` 和 `unknown` 走默认全量修复路径，无专门逻辑。

**修复方案**：扩充 auto_fixer 错误类型覆盖到 12 种：

| 错误类型 | 识别方式 | 自动修复方法 |
|---------|---------|-------------|
| rule_empty | JAR 返回空结果 | 重新分析网站 HTML，重写选择器 |
| relative_url | URL 拼接错误 | 补全为绝对路径 |
| css_selector_empty | CSS 选择器未匹配 | 尝试 fallback 选择器 |
| js_error | JS 执行异常 | 检查 ES5 语法，移除 ES6 特性 |
| http_403 | HTTP 403 | 添加 Header / Cookie |
| need_login | 返回登录页面 | 标记需用户介入 |
| cf_challenge | CF 挑战页面 | 标记需用户破盾 |
| field_missing | 字段缺失 | source_validator 预校验拦截 |
| syntax_error | 规则语法错误 | rule_precheck 预校验拦截 |
| jar_crash | JAR 进程崩溃 | 重启 JAR 进程 |
| jar_timeout | JAR 超时 | 增加超时时间 |
| behavior_mismatch | 行为不一致 | 标记需源码核实 |

### 3.7 Phase 5 经验写入自动化提升（第九轮审查新增，第十轮修正）

**问题**：experience_manager 当前实际方法为 `search()`/`search_experience()`（检索）和 `write_pending()`/`write_experience()`（输出到 `output/experience-pending.json`），**不存在** `extract()` 和 `write_to_basic_memory()` 方法。文件头注释明确说明："basic-memory是MCP服务器，不是CLI工具，Python脚本无法通过subprocess调用。debug-source.py输出经验数据到JSON文件，由AI agent外层通过MCP写入basic-memory。"

**修复方案**：增强 experience_manager，新增 `extract()` 和 `write_to_basic_memory()` 方法：

```python
# experience_manager.py 增强（新增方法，保留现有 search()/write_pending()）
class ExperienceManager:
    # 现有方法保留：search()、search_experience()、write_pending()、write_experience()、
    #              write_experience_fallback()、resolve_conflict()、_format_experience()

    def extract(self, source_obj, debug_result, confidence):
        """自动提取经验要素（新增方法）"""
        return {
            "website_feature": self._extract_website_feature(source_obj),
            "error_type": debug_result.error_type if not debug_result.success else None,
            "fix_method": debug_result.fix_method if debug_result.fix_applied else None,
            "rule_pattern": self._extract_rule_pattern(source_obj),
            "confidence": confidence,
            "source_url": source_obj.get("bookSourceUrl") or source_obj.get("sourceUrl"),
            "timestamp": datetime.now().isoformat()
        }

    def write_to_basic_memory(self, experience_draft):
        """通过 MCP 写入 basic-memory（新增方法，返回 MCP 调用指令由 AI agent 执行）"""
        # 返回 MCP 调用指令，由 AI agent 执行
        return {
            "tool": "mcp_basic-memory_write_note",
            "args": {
                "title": f"经验: {experience_draft['website_feature']}",
                "content": self._format_content(experience_draft),
                "project": "legado",
                "note_type": "experience",
                "tags": ["auto-extracted"],
                "metadata": experience_draft
            }
        }
```

**自动化流程**：
1. experience_manager.extract() 自动提取经验要素
2. 生成 JSON 草稿到 `experience/pending/`
3. AI 确认草稿（可选审核）
4. experience_manager.write_to_basic_memory() 返回 MCP 调用指令
5. AI agent 执行 MCP 调用写入 basic-memory
6. 降级路径：MCP 不可用时写入 references/

---

## 四、源码核实修正说明

### 4.1 核实方法

3 组子代理（共 27 个源文件）逐行对比仿真端 vs 真机源码：

- **组 1**：Rhino 引擎 + HTTP（10 个文件）
- **组 2**：核心业务 + 调试（9 个文件）
- **组 3**：规则引擎 + JS 扩展（8 个文件）

**第十轮补充核实**：逐行读取 12 个关键源码文件，对 18 个修正点逐一验证，确认 17 个完全正确、修正 10 需精确化表述。同时核实 Python 客户端实际代码结构，发现 7 个新问题（见 4.3 和 4.4 节）。

### 4.2 修正的 18 个错误

| 序号 | 错误 | 修正 | 影响范围 |
|------|------|------|---------|
| 1 | BookType.text=0b1 | BookType.text=0b1000（8） | REQ-15 GAP-54 |
| 2 | RssSource 字段名 sourceType | 实际为 type | Python source_validator |
| 3 | BookChapter 有 chapterUrl/level 字段 | 实际为 url，无 level | REQ-17 GAP-68c |
| 4 | init 规则在 WebBook.kt | 实际在 BookInfo.kt | REQ-17 GAP-67c |
| 5 | ruleNextPage=="PAGE" 在 WebBook.kt | 实际在 RssParserByRule.kt | REQ-17 GAP-67b |
| 6 | ConcurrentRecord 在 ConcurrentRateLimiter | 实际在 AnalyzeUrl | REQ-14 GAP-37 |
| 7 | BookSource 的 searchUrl/ruleSearch 必填 | 实际可空 | Python source_validator |
| 8 | RssSource 的 ruleArticles 必填 | 实际可空 | Python source_validator |
| 9 | 规则前缀 @json: | 源码书写为 `@Json:`（大写 J），但 `startsWith("@Json:", true)` 忽略大小写，`@json:` 也能匹配 | Python rule_precheck |
| 10 | @js: 和 `<regex>` 前缀存在 | **第十轮再修正（精确化）**：① `AnalyzeRule.kt` 中 `@js:` 和 `<js></js>` 均通过 `JS_PATTERN` 正则匹配（`AppPattern.kt:7-8` 定义为 `<js>([\\w\\W]*?)</js>|@js:([\\w\\W]*)`，CASE_INSENSITIVE），非 startsWith 前缀；且不在 `SourceRule.init` 规则类型识别分支中。② `BaseSource.kt` 中 `@js:` 是 startsWith 前缀匹配，共 3 处但 ignoreCase 不一致：`BaseSource.kt:76`（loginUrl）无 ignoreCase、`BaseSource.kt:108`（header）有 ignoreCase=true、`BaseSource.kt:193`（loginUi）无 ignoreCase。③ `<regex>` 前缀在源码中完全不存在（Grep 全局无匹配） | Python rule_precheck |
| 11 | BaseSource 是 class | 实际是 interface | REQ-16 GAP-59 |
| 12 | dateFormat 在 BaseSource | 实际在 AppConst | REQ-01 |
| 13 | HtmlFormatter 方法名是 formatHtml | 实际是 format/formatKeepImg | REQ-17 GAP-67d |
| 14 | mapBase64Flags 方法存在 | 实际不存在，需新建 | REQ-02 |
| 15 | aesEncodeToString 在 JsExtensions | 实际在 JsEncodeUtils | REQ-01 |
| 16 | cookie()/getBook() 方法存在 | 实际不存在 | 方法列表 |
| 17 | AnalyzeUrl 有 followRedirects 字段 | 实际无此字段 | REQ-15 GAP-44 |
| 18 | aesEncodeToString 实现正确 | 疑似源码 Bug | REQ-01 |

### 4.3 第十轮审查新发现（补充修正）

第十轮逐行源码核实发现以下 4 个额外问题，需在设计文档中补充记录：

| 序号 | 问题 | 源码证据 | 影响范围 | 处理方式 |
|------|------|---------|---------|---------|
| 19 | 文件路径错误：`rss/RssParserByRule.kt` | 实际路径为 `model/rss/RssParserByRule.kt` | tasks.md 方向 15.1.2 | 修正路径 |
| 20 | 文件路径错误：`help/book/HtmlFormatter.kt` | 实际路径为 `utils/HtmlFormatter.kt`（`BookInfo.kt:14` import 证实） | tasks.md 方向 15.1.4 | 修正路径 |
| 21 | ruleNextPage 比较方式：非精确匹配 `"PAGE"` | `RssParserByRule.kt:58` 使用 `uppercase(Locale.getDefault())` 转大写后比较，`"page"`/`"Page"`/`"PAGE"` 均可匹配 | REQ-17 GAP-67b | 修正描述 |
| 22 | BaseSource 中 `@js:` 的 ignoreCase 不一致 | 3 处 `startsWith("@js:")`：`BaseSource.kt:76`（loginUrl）无 ignoreCase、`BaseSource.kt:108`（header）有 ignoreCase=true、`BaseSource.kt:193`（loginUi）无 ignoreCase | Python rule_precheck | 预校验需区分场景 |
| 23 | aesEncodeToString 的 `@Deprecated` ReplaceWith 也错误 | `JsEncodeUtils.kt:220` 的 `ReplaceWith("createSymmetricCrypto(...).decryptStr(data)")` 也指向解密方法，应指向加密方法 | REQ-01 | 仿真端对齐 bug 时需同时对齐 ReplaceWith |

### 4.4 Python 客户端代码核实修正（第十轮新增）

第十轮核实 Python 客户端实际代码，发现 2 个描述需修正：

| 序号 | 问题 | 实际代码证据 | 修正 |
|------|------|-------------|------|
| 24 | REQ-S06 描述"仅处理 rule_empty 和 relative_url 两种错误类型" | `tools/auto_fixer.py:471-476` fix_map 实际处理 4 种：`rule_parse`/`css`/`url_empty`/`network`；`TypeError` 和 `unknown` 走默认全量修复路径 | 修正为"实际处理 4 种错误类型" |
| 25 | REQ-S07 描述"extract() 和 write_to_basic_memory()" | `legado_client/experience/experience_manager.py` 实际方法为 `search()`/`search_experience()`/`write_pending()`/`write_experience()`，不存在 extract() 和 write_to_basic_memory()；文件头注释说明"basic-memory是MCP服务器，Python脚本无法通过subprocess调用" | 修正为"新增 extract() 和 write_to_basic_memory() 方法" |

---

## 五、实施决策记录

### AD-01: type 位运算替代 isWebFile 字段

**决策**：用 `book.type and 0b10000000 != 0` 判断 isWebFile

**合理性**：✅ 合理。Book.kt 中 isWebFile 是计算属性，底层就是 type 位运算。

### AD-02: hutool AES 替代 SymmetricCryptoAndroid

**决策**：用 `hutool AES(key).encryptBase64` 替代 `SymmetricCryptoAndroid`

**合理性**：✅ 合理。算法一致，结果相同。

### AD-03: System.getenv 替代 AppConst.androidId

**决策**：用 `System.getenv("LEGADO_ANDROID_ID")` 替代 `AppConst.androidId`

**合理性**：⚠️ 行为不一致。需通过环境变量传入真机 androidId 才能完全对齐。

### AD-08: 真机 bug 也需对齐

**决策**：仿真端需对齐真机 bug（如 aesEncodeToString 误用 decryptStr）

**理由**：100% 测试校验准确性要求行为对齐（**源码核实修正：aesEncodeToString 疑似源码 Bug**）

**第十轮补充**：不仅方法体调用了 `decryptStr(data)`（`JsEncodeUtils.kt:226`），连 `@Deprecated` 注解的 `ReplaceWith("createSymmetricCrypto(...).decryptStr(data)")`（`JsEncodeUtils.kt:220`）也错误地指向了解密方法。仿真端对齐 bug 时需同时对齐 ReplaceWith。

### AD-10: 保持内联实现，只修复 P0 级差异

**决策**：保持 BookSourceDebugger/RssSourceDebugger 中的内联实现，只修复 P0 级 5 个差异

**理由**：移植整个 WebBook/Rss 模块工作量巨大，且可能引入大量 Android 依赖。内联实现行为对齐即可。

### AD-11: 只移植 WrapFactory + instructionObserverThreshold

**决策**：不引入完整 modules/rhino 模块，只移植影响测试校验的关键组件

**源码核实修正**：
- WrapFactory 依赖 ClassShutter（wrapAsJavaObject 返回 null，wrapJavaClass 返回 NativeJavaPackage）
- instructionObserverThreshold=10000（非 1000）
- maximumInterpreterStackDepth=1000
- ContextFactory.observeInstructionCount 覆写方法内部调用 RhinoContext.ensureActive()

**解决方案**：
- 修改 WrapFactory 移除对 ClassShutter 的调用
- 自定义 observeInstructionCount 实现，直接抛出 TimeoutException

### AD-12: 只添加 withTimeout 超时控制

**决策**：不将 runBlocking 替换为 Coroutine 链式封装，只在关键位置添加 withTimeout 超时控制

**理由**：runBlocking vs Coroutine 是性能差异，不影响测试校验结果。

---

## 六、File Changes

### 新增文件

| 文件 | 来源 | 说明 | 优先级 |
|------|------|------|--------|
| `scripts/legado_client/analyzer/source_validator.py` | 新建 | 源字段完整性预校验 | P0 |
| `scripts/legado_client/analyzer/rule_precheck.py` | 新建 | 规则语法预检查 | P0 |
| `utils/SharedJsScope.kt` | 真机移植 | JS Scope 管理 | P1 |
| `utils/RowUiParser.kt` | 真机移植 | loginUi 解析 | P1 |
| `python/webview_delegate.py` | 新建 | WebView Selenium 委托 | P1 |
| `python/ocr_delegate.py` | 新建 | 验证码 OCR 委托 | P2 |
| `rhino/RhinoWrapFactory.kt` | 真机移植 | Java 对象包装（AD-11） | P0 |
| `rhino/NativeBaseSource.kt` | 真机移植 | source 对象包装（AD-11） | P0 |
| `scripts/legado_client/analyzer/auto_fixer.py` | 从 tools/ 迁移 | 自动修复（整合后） | P0 |
| `scripts/legado_client/client/obstacle_resolver.py` | 从 tools/ 迁移 | 障碍解析（整合后） | P1 |
| `scripts/legado_client/analyzer/crypto_analyzer.py` | 从 tools/ 迁移 | 加密分析（整合后） | P1 |
| `scripts/legado_client/client/interactive_guide.py` | 从 tools/ 迁移 | 交互引导（整合后） | P1 |
| `scripts/legado_client/utils/jvm_helpers.py` | 从 tools/ 迁移 | JVM 共享工具（整合后） | P0 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `JsExtensionsStub.kt` | 46 个方法修复 + GAP-36 改实例化 + GAP-42/43 |
| `BaseSourceInterface.kt` | 6 个属性 var + 3 个空实现 |
| `BookSourceDebugger.kt` | GAP-39/40/47/48/49/50/51 + 第五轮 P0 |
| `RssSourceDebugger.kt` | GAP-22/23/24/25/26/41/52/53/60/61/62/63 |
| `OkHttpUtils.kt` | SSLHelper + DNS + GAP-1/2/3 |
| `HttpHelper.kt` | UA 注入 + CookieJar（AD-12） |
| `CookieManagerStub.kt` | GAP-32 saveResponse/loadRequest（内存 Map） |
| `Debug.kt` | 状态管理 + CheckSource |
| `AnalyzeRule.kt` | GAP-36 + GAP-56 + instructionObserverThreshold |
| `AnalyzeUrl.kt` | GAP-44/45/46 移除多余功能 |
| `ConcurrentRateLimiter.kt` | GAP-37 + withTimeout |
| `NetworkUtilsStub.kt` | GAP-38 + customHosts |
| `Book.kt` | GAP-54（**源码核实修正：BookType.text=0b1000**） |
| `BookChapter.kt` | GAP-58（**源码核实修正：无 chapterUrl/level，实际为 url**） |
| `BookSource.kt` | GAP-59（**源码核实修正：BaseSource 是 interface**） |
| `RssSource.kt` | GAP-59 |
| `SSLHelper.kt` | GAP-64 |
| `AppConfig.kt` | userAgent + customHosts |
| `AppConst.kt` | MAX_THREAD + charsets |
| `RhinoScriptEngine.kt` | WrapFactory + instructionObserverThreshold |
| `scripts/legado_client/client/debug_runner.py` | 预校验 + 降级路径 + JVM 降级行为修正（REQ-S05） |
| `scripts/legado_client/analyzer/error_diagnoser.py` | 错误类型扩充 |
| `scripts/legado_client/experience/experience_manager.py` | 半自动写入 + 自动提取增强（REQ-S07） |
| `scripts/verify-source.py` | import 路径修正（REQ-P07） |
| `scripts/analyze_site.py` | import 路径修正（REQ-P07） |
| `scripts/verify-selector.py` | import 路径修正（REQ-P07） |
| `scripts/verify-decrypt.py` | import 路径修正（REQ-P07） |
| `scripts/verify-image.py` | import 路径修正（REQ-P07） |
| `.trae/skills/legado-source-creator/SKILL.md` | 5 阶段工作流调整 + 统一 OpenSpec 引用 |

---

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| SharedJsScope 移植复杂 | 高 | 高 | 分阶段实现，先实现基础 Scope 管理 |
| Selenium 委托延迟 | 高 | 中 | 设置超时 + 异步执行 |
| 环境变量未配置 | 中 | 中 | 提供默认值 + 启动时检查 |
| GAP-22 ruleDescription 修正引入回归 | 中 | 高 | 修正后用真实 RSS 源验证 |
| GAP-36 委托模式改实例化引入回归 | 高 | 高 | 修改后全量回归测试 |
| WrapFactory 移植不完整 | 中 | 高 | 参照真机 RhinoWrapFactory.kt 逐行移植 |
| instructionObserverThreshold 设置不当 | 低 | 高 | 设置合理阈值（默认 10000） |
| soupsieve 不支持 jsoup 扩展语法 | 中 | 中 | 预校验只检查标准 CSS 语法 |
| 预校验误报 | 中 | 高 | 预校验只检查明确错误的语法 |
| auto_fixer 修复成功率低 | 中 | 中 | 修复失败后降级到用户交互 |
| 降级模式结果不准确 | 中 | 高 | 降级模式结果标注"建议用 JAR 复验" |
