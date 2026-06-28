# Design: 源修复闭环优化

## 统一设计理念

### 理念1：仿真保真度优先
JVM仿真器首要目标是"行为与真机一致"。不保真的仿真器比没有更危险（debug()吞异常导致100%假通过率）。

### 理念2：可观测性优先
调试工具首要价值是"让问题可见"。AI看到问题后可以自己修复，但看不到问题就无法行动。

### 理念3：经验闭环自动化
经验从测试结果中自动提取，不依赖手动写入。

### 理念4：单一权威源
文档、代码、经验三层都有单一权威源，消除矛盾。冲突解决优先级：代码 > 文档 > 经验。

### 理念5：渐进式验证
修改JVM仿真器后必须确保不引入新bug。每次修改都遵循"修改→重建→回归测试"的闭环。修改前备份JAR，失败时可回滚。

### 理念6：降级路径一致性
降级时必须标记降级状态，降级写入必须隔离（独立目录+AUTO_GENERATED标记），降级数据必须可识别。

### 理念7：自顶向下与自底向上结合
设计文档不能只从仿真器源码自底向上分析（容易忽略规则语法和网站特性层面的实际问题），也不能只从修复经验自顶向下分析（容易忽略仿真器底层保真度问题）。必须两者结合。自底向上：JVM源码分析发现仿真保真度限制（方向1/2/7）；自顶向下：修复源实际经验发现规则语法和网站特性问题（方向8）。已知修复模式记录：JS补全绝对路径、og:novel meta+@put/@get、nextContentUrl分页、replaceRegex净化等模式必须系统化记录。

### 理念8：AI工作流编排优先
工具链改进的最终目的是让AI更好地使用skill生成/修复书源。工具改进与AI使用之间不能存在断层。多轮迭代修复闭环、建议→规则自动转换、经验→自动复用桥接是核心。

### 理念9：可信度分级
仿真器保真度89%意味着11%场景不可信。AI必须知道何时该信仿真器结果，何时需要标记"需真机验证"。测试结果可信度评分+假阳性/假阴性检测是核心。

## 架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                    debug-source.py (Python客户端)                       │
│                                                                        │
│  [Phase 0]经验检索 → [Phase 1]JVM调试 → [Phase 2]错误诊断 → [Phase 3]经验写入 │
│       ↑                    ↑              ↓              ↓            │
│  pathlib.Path.rglob    JVM仿真器      HTML结构分析    output/pending.json │
│  (文件搜索降级)         (Kotlin)       (新增模块)    (AI agent外层MCP写入) │
│                       + 保真度对齐                                      │
│                                                                        │
│  新增: --output report.json  --timeout  --export-html                  │
└──────────────────────────────────────────────────────────────────────┘
```

## 方向1：JVM仿真器相对路径拼接（P0）

### 1.1 问题根因（源码分析）

AnalyzeUrl构造时baseUrl参数默认为空字符串：
```kotlin
// AnalyzeUrl.kt:81 (仿真器版: tools/legado-jvm/src/main/kotlin/io/legado/app/model/analyzeRule/AnalyzeUrl.kt)
private var baseUrl: String = ""
```

NetworkUtilsStub.getAbsoluteURL在baseUrl为空时直接返回原URL：
```kotlin
// NetworkUtilsStub.kt:131
fun getAbsoluteURL(baseUrl: String?, href: String?): String {
    if (href.isNullOrEmpty()) return ""
    if (baseUrl.isNullOrEmpty()) return href  // ← baseUrl为空，不拼接
    // ...
}
```

BookSourceDebugger搜索/详情阶段构造AnalyzeUrl时未传baseUrl：
```kotlin
// BookSourceDebugger.kt:117-123 (搜索阶段)
val analyzeUrl = AnalyzeUrl(
    searchUrl,
    key = key,
    page = 1,
    source = source,
    ruleData = book
    // ← 缺少 baseUrl = source.bookSourceUrl
)

// BookSourceDebugger.kt:215-219 (详情阶段) — 同样缺少baseUrl
```

RssSourceDebugger同样的问题：
```kotlin
// RssSourceDebugger.kt:188-193 (列表阶段) — 缺少baseUrl
// RssSourceDebugger.kt:305-308 (内容阶段) — 缺少baseUrl
// RssSourceDebugger.kt:373-376 (singleUrl阶段) — 缺少baseUrl + 未调用toAbsoluteUrl
```

**注意**：RssSourceDebugger列表阶段第180行和内容阶段第303行已有toAbsoluteUrl预处理，但传baseUrl的真正价值是让JS代码中能访问baseUrl变量（AnalyzeUrl.kt:362 `bindings["baseUrl"] = baseUrl`）。

### 1.2 修复方案

在所有阶段构造AnalyzeUrl时传入baseUrl：

```kotlin
// BookSourceDebugger.kt 搜索阶段修复
val analyzeUrl = AnalyzeUrl(
    searchUrl,
    key = key,
    page = 1,
    source = source,
    ruleData = book,
    baseUrl = source.bookSourceUrl  // 新增
)

// BookSourceDebugger.kt 详情阶段修复
val analyzeUrl = AnalyzeUrl(
    bookUrl,
    source = source,
    ruleData = book,
    baseUrl = source.bookSourceUrl  // 新增
)

// RssSourceDebugger.kt 列表阶段修复
val analyzeUrl = AnalyzeUrl(
    sortUrl,
    source = source,
    baseUrl = source.sourceUrl  // 新增
)

// RssSourceDebugger.kt 内容阶段修复
val analyzeUrl = AnalyzeUrl(
    articleUrl,
    source = source,
    baseUrl = source.sourceUrl  // 新增
)

// RssSourceDebugger.kt singleUrl阶段修复
val searchUrl = toAbsoluteUrl(rssSource.sourceUrl, rssSource.sourceUrl)  // 新增toAbsoluteUrl调用
val analyzeUrl = AnalyzeUrl(
    searchUrl,
    source = source,
    baseUrl = source.sourceUrl  // 新增
)
```

同时修复AnalyzeRule的redirectUrl设置：在每阶段解析HTML前调用：
```kotlin
analyzeRule.setRedirectUrl(baseUrl)  // 确保getString(isUrl=true)能拼接相对路径
```

**注意**：setContent(html, response.url)已设置了baseUrl，setRedirectUrl是额外保障。两者不冲突——setContent设置content的baseUrl，setRedirectUrl设置URL拼接的baseUrl。

### 1.3 影响范围

| 文件 | 修改行号 | 修改内容 |
|------|---------|---------|
| BookSourceDebugger.kt | 117-123 | 搜索阶段加baseUrl |
| BookSourceDebugger.kt | 215-219 | 详情阶段加baseUrl |
| BookSourceDebugger.kt | 117后 | 搜索阶段加setRedirectUrl |
| BookSourceDebugger.kt | 215后 | 详情阶段加setRedirectUrl |
| RssSourceDebugger.kt | 188-193 | 列表阶段加baseUrl |
| RssSourceDebugger.kt | 305-308 | 内容阶段加baseUrl |
| RssSourceDebugger.kt | 367-376 | singleUrl阶段加baseUrl+toAbsoluteUrl |

## 方向2：JVM仿真器可观测性（P0）

### 2.1 HtmlStructureAnalyzer（新增）

```kotlin
// 新文件: HtmlStructureAnalyzer.kt
class HtmlStructureAnalyzer {
    fun analyze(html: String): String {
        // 大HTML截断前100KB避免性能问题
        val truncatedHtml = if (html.length > 102400) html.substring(0, 102400) else html
        val doc = Jsoup.parse(truncatedHtml)

        // 提取class+出现次数
        val classCounts = mutableMapOf<String, Int>()
        doc.getAllElements().forEach { el ->
            el.classNames().forEach { cls ->
                classCounts[cls] = classCounts.getOrDefault(cls, 0) + 1
            }
        }

        // 提取id+出现次数
        val ids = mutableMapOf<String, Int>()
        doc.select("[id]").forEach { el ->
            val id = el.id()
            ids[id] = ids.getOrDefault(id, 0) + 1
        }

        // 生成建议选择器
        val suggestions = generateSelectorSuggestions(classCounts)

        return formatResult(classCounts, ids, suggestions)
    }

    private fun generateSelectorSuggestions(classCounts: Map<String, Int>): List<String> {
        val suggestions = mutableListOf<String>()
        classCounts.filter { it.value > 1 }.forEach { (cls, count) ->
            when {
                cls.contains("book") || cls.contains("item") || cls.contains("card") ->
                    suggestions.add("书籍/文章列表: class.$cls ($count 次)")
                cls.contains("title") || cls.contains("name") ->
                    suggestions.add("标题: class.$cls ($count 次)")
                cls.contains("author") ->
                    suggestions.add("作者: class.$cls ($count 次)")
                cls.contains("content") || cls.contains("text") ->
                    suggestions.add("正文: class.$cls ($count 次)")
            }
        }
        return suggestions
    }
}
```

### 2.2 集成到调试器（扩展触发条件）

```kotlin
// BookSourceDebugger.kt 搜索阶段
if (bookList.isEmpty()) {
    val analysis = HtmlStructureAnalyzer().analyze(collectedHtml)
    logger.log(10, "[HTML结构分析]\n$analysis")
}

// BookSourceDebugger.kt 详情阶段
if (name.isEmpty()) {
    val analysis = HtmlStructureAnalyzer().analyze(collectedHtml)
    logger.log(10, "[HTML结构分析-详情页]\n$analysis")
}

// BookSourceDebugger.kt 目录阶段
if (chapterList.isEmpty()) {
    val analysis = HtmlStructureAnalyzer().analyze(collectedHtml)
    logger.log(10, "[HTML结构分析-目录页]\n$analysis")
}

// BookSourceDebugger.kt 正文阶段
if (content.isEmpty()) {
    val analysis = HtmlStructureAnalyzer().analyze(collectedHtml)
    logger.log(10, "[HTML结构分析-正文页]\n$analysis")
}

// RssSourceDebugger.kt 列表阶段
if (articleList.isEmpty()) {
    val analysis = HtmlStructureAnalyzer().analyze(collectedHtml)
    logger.log(10, "[HTML结构分析]\n$analysis")
}
```

### 2.3 ruleContent回退修复

```kotlin
// RssSourceDebugger.kt:333-339 修复前
val content = if (ruleContentResult.isNotEmpty()) ruleContentResult
              else if (ruleDescriptionResult.isNotEmpty()) ruleDescriptionResult
              else html  // ← 掩盖问题

// 修复后
val content = if (ruleContentResult.isNotEmpty()) ruleContentResult
              else if (ruleDescriptionResult.isNotEmpty()) {
                  logger.log(40, "⚠️ ruleContent为空，回退到ruleDescription")
                  ruleDescriptionResult
              } else {
                  logger.log(40, "⚠️ ruleContent和ruleDescription均为空，回退到整个HTML（规则缺失）")
                  html
              }
```

### 2.4 extractJsRule修复

```kotlin
// RssSourceDebugger.kt:59-68 修复前
private fun extractJsRule(rule: String?): String? {
    val match = jsPattern.find(rule)
    return if (match != null) match.value  // ← 丢失HTML模板
    else rule
}

// 修复后
private fun extractJsRule(rule: String?): String? {
    val match = jsPattern.find(rule)
    return if (match != null) {
        // 保留JS + JS后的HTML模板
        rule.substring(match.range.first)
    } else rule
}
```

### 2.5 sortUrl未匹配警告

```kotlin
// RssSourceDebugger.kt:161-166 修复前
if (sortEntry == null && sortEntries.isNotEmpty()) {
    sortEntry = sortEntries[0]  // ← 静默降级
}

// 修复后
if (sortEntry == null && sortEntries.isNotEmpty()) {
    sortEntry = sortEntries[0]
    logger.log(10, "⚠️ sortUrl中未找到分类'$key'，降级到第一个分类'${sortEntry.first}'")
}
```

## 方向3：Python客户端优化（P0/P2）

### 3.1 结构化输出

```python
# debug-source.py 新增 --output 参数
parser.add_argument("--output", help="导出结构化结果到JSON文件")

# 调试完成后
if args.output:
    report = {
        "success": collector.result.get("success", False),
        "confidence": confidence,
        "stages": stages_passed,
        "html_sources": {k: len(v) for k, v in collector.html_sources.items()},
        "error_diagnosis": diagnosis if not success else None,
        "experience": {
            "searched": experience_searched,
            "written": experience_written
        }
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
```

### 3.2 超时控制+安全终止

```python
# debug-source.py 新增 --timeout 参数
parser.add_argument("--timeout", type=int, default=120, help="JVM调试超时（秒）")

# 传递给RuleEngineClient
client = RuleEngineClient(timeout=args.timeout)

# RuleEngineClient中超时处理（使用select.select实现非阻塞读取）
import select, threading

def _read_with_timeout(self, process, timeout):
    """非阻塞读取：使用select.select实现超时检测"""
    # Windows兼容：select对管道支持有限，使用threading.Timer兜底
    ready, _, _ = select.select([process.stdout], [], [], timeout)
    if ready:
        return process.stdout.readline()
    # 超时处理：先发shutdown命令，等待3秒，再强制destroy
    try:
        process.stdin.write("shutdown\n")
        process.stdin.flush()
    except Exception:
        pass
    process.wait(timeout=3)
    if process.poll() is None:
        process.kill()
    raise TimeoutError(f"JVM调试超时({timeout}秒)")

# Windows兼容方案：如果select.select对管道不工作，使用threading.Timer
def _read_with_timeout_windows(self, process, timeout):
    """Windows兼容：threading.Timer + 阻塞读取"""
    result = [None]
    def _read():
        result[0] = process.stdout.readline()
    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        # 超时：先发shutdown，等待3秒，再强制destroy
        try:
            process.stdin.write("shutdown\n")
            process.stdin.flush()
        except Exception:
            pass
        process.wait(timeout=3)
        if process.poll() is None:
            process.kill()
        raise TimeoutError(f"JVM调试超时({timeout}秒)")
    return result[0]
```

### 3.3 JSON去重

```python
# debug-source.py main() 入口解析一次
source_obj = json.loads(source_json)
if isinstance(source_obj, list):
    source_obj = source_obj[0]
    source_json = json.dumps(source_obj, ensure_ascii=False)

# 后续所有地方使用 source_obj，不再重复 json.loads(source_json)
```

### 3.4 进化重验证参数修复

```python
# debug-source.py:977-985 修复前
cmd = [sys.executable, __file__, "--source", args.source,
       "--key", args.key, "--stage", args.stage, "--no-reverify"]
if args.proxy:
    cmd += ["--proxy", args.proxy]
if args.ua:
    cmd += ["--ua", args.ua]
# ← 丢失 --import-cookie 和 --force

# 修复后
cmd = [sys.executable, __file__, "--source", args.source,
       "--key", args.key, "--stage", args.stage, "--no-reverify"]
if args.proxy:
    cmd += ["--proxy", args.proxy]
if args.ua:
    cmd += ["--ua", args.ua]
if args.import_cookie:
    cmd += ["--import-cookie", args.import_cookie]
if args.force:
    cmd += ["--force"]
```

### 3.5 batch_debug传webview_handler

```python
# debug-source.py:646-651 修复前
result = client.batch_debug(
    batch_data,
    source_type=st,
    on_progress=on_progress,
    on_complete=on_complete
    # ← 缺少 webview_handler
)

# 修复后
result = client.batch_debug(
    batch_data,
    source_type=st,
    on_progress=on_progress,
    on_complete=on_complete,
    webview_handler=webview_handler  # 新增
)
```

### 3.6 统一阶段命名

```python
# 统一为字符串键
STAGE_NAMES = {
    "search": "搜索页",
    "detail": "详情页",
    "toc": "目录页",
    "content": "正文页",
    "sort": "列表页"
}

# stages解析增加降级
for sep in ["→", "->", ","]:
    if sep in stages:
        stages_list = stages.split(sep)
        break
else:
    stages_list = [stages]
```

## 方向4：经验闭环自动化（P1）

### 4.1 experience_manager.py（新增）

> **AD-5决策（修正版）**：debug-source.py输出经验数据到JSON文件，由AI agent外层通过MCP工具写入basic-memory。basic-memory是MCP服务器（提供MCP工具如`mcp_basic-memory_write_note`），不是CLI命令行工具，Python脚本无法通过subprocess调用。

```python
# 新文件: scripts/experience_manager.py
import json
from pathlib import Path

class ExperienceManager:
    def __init__(self):
        self._references_dir = Path(__file__).parent.parent / "references" / "troubleshooting"
        self._auto_dir = self._references_dir / "auto"
        self._pending_file = Path(__file__).parent.parent.parent / "output" / "experience-pending.json"

    def search(self, source_url: str, source_name: str) -> str:
        """测试前检索：AI agent在外层通过MCP搜索，debug-source.py用文件搜索降级"""
        keyword = source_url or source_name
        matches = []
        for md_file in self._references_dir.rglob("*.md"):
            try:
                if keyword in md_file.read_text(encoding='utf-8'):
                    matches.append(str(md_file))
            except Exception:
                continue
        return f"找到相似案例:\n" + "\n".join(matches) if matches else "无相似案例"

    def write_pending(self, source: dict, fix_info: dict, test_result: dict):
        """测试后写入：输出到JSON文件，由AI agent外层通过MCP写入basic-memory"""
        if not test_result.get("success"):
            return
        experience = self._format_experience(source, fix_info, test_result)
        # 写入pending文件，等待AI agent通过MCP写入basic-memory
        self._pending_file.parent.mkdir(parents=True, exist_ok=True)
        pending_data = []
        if self._pending_file.exists():
            pending_data = json.loads(self._pending_file.read_text(encoding='utf-8'))
        pending_data.append({"content": experience, "tags": ["自动积累", fix_info.get('error_type', '')]})
        self._pending_file.write_text(json.dumps(pending_data, ensure_ascii=False, indent=2), encoding='utf-8')
        # 同时降级写入到auto目录
        self._write_references(experience, source)

    def _format_experience(self, source: dict, fix_info: dict, test_result: dict) -> str:
        """定义固定Markdown模板"""
        return f"""# 修复经验-{source.get('sourceName', 'unknown')}

- **错误类型**: {fix_info.get('error_type', 'unknown')}
- **源URL**: {source.get('bookSourceUrl', source.get('sourceUrl', ''))}
- **修复方案**: {fix_info.get('fix_description', '')}
- **测试结果**: {'通过' if test_result.get('success') else '失败'}
- **日期**: {test_result.get('date', '')}

## 详细修复
{fix_info.get('fix_details', '')}
"""

    def _write_references(self, content: str, source: dict):
        """降级路径：写入references/troubleshooting/auto/"""
        self._auto_dir.mkdir(parents=True, exist_ok=True)
        filename = f"auto-{source.get('sourceName', 'unknown')}-{source.get('sourceUrl', '')[:20]}.md"
        filepath = self._auto_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"<!-- AUTO_GENERATED -->\n{content}")
```

### 4.2 集成到debug-source.py

```python
# Phase 0: 经验检索
exp_manager = ExperienceManager()
experience = exp_manager.search(source_url, source_name)
if experience:
    print(f"[经验检索] {experience}")

# Phase 3: 经验写入
if collector.result and collector.result.get("success"):
    exp_manager.write(source_obj, fix_info, collector.result)
```

## 方向5：错误诊断增强（P0）

> **AD-6决策**：新增独立模块error_diagnoser.py，替换debug-source.py中现有的_generate_error_suggestion函数。

### 5.1 ErrorDiagnoser（新增）

```python
# 新文件: scripts/error_diagnoser.py
class ErrorDiagnoser:
    ERROR_PATTERNS = {
        "relative_url": {
            "pattern": r"Expected URL scheme 'http' or 'https'",
            "category": "相对路径问题",
            "suggestion": "JVM仿真器未自动拼接相对路径。\n"
                         "修复方案：在URL规则中用JS补全绝对路径：\n"
                         "  rule<js>result.indexOf('http')===0?result:'https://域名'+result</js>",
            "trigger_html_analysis": False
        },
        "site_down": {
            "pattern": r"connect timed out|SocketTimeoutException|UnknownHostException|404|403|500|502|503",
            "category": "网站不可达",
            "suggestion": "网站可能已挂或域名变更。\n"
                         "修复方案：\n"
                         "  1. curl验证网站存活\n"
                         "  2. 检查域名301重定向\n"
                         "  3. 更新sourceUrl",
            "trigger_html_analysis": False
        },
        "rule_empty": {
            "pattern": r"列表大小:0|文章列表为空|本页文章数:0|搜索结果为空",
            "category": "规则不匹配",
            "suggestion": "选择器未匹配到HTML元素。\n"
                         "修复方案：\n"
                         "  1. 查看下方HTML结构分析\n"
                         "  2. 更新选择器\n"
                         "  3. 注意标签名vs class：class.xxx匹配class='xxx'，xxx匹配<xxx>",
            "trigger_html_analysis": True
        },
        "js_error": {
            "pattern": r"JavaScript Error|TypeError|ReferenceError|SyntaxError",
            "category": "JS执行错误",
            "suggestion": "JS执行出错。\n"
                         "修复方案：\n"
                         "  1. ES6改ES5：let→var、箭头函数→function\n"
                         "  2. 检查变量是否定义\n"
                         "  3. 检查java对象方法调用",
            "trigger_html_analysis": False
        },
        "encoding_error": {
            "pattern": r"400 Bad Request|Malformed URL",
            "category": "编码错误",
            "suggestion": "URL中的中文可能需要URL编码。\n"
                         "修复方案：\n"
                         "  OkHttp通常自动编码，但某些场景需手动编码：\n"
                         "  searchUrl中用{{key}}占位符（Legado自动编码）",
            "trigger_html_analysis": False
        }
    }
```

## 方向6：Skill文档治理（P1）

### 6.1 陷阱编号统一+映射表

在references/troubleshooting/的每个子文档中，为每个陷阱添加 `<!-- #编号 -->` 注释标记：
```markdown
## 4.1 RssSource 搜索功能 <!-- #14 -->
```

在SKILL.md速查表中添加精确指针：
```markdown
| #11 | decryptStr vs decrypt | 详见 troubleshooting/rhino-js-traps.md#11 |
```

在troubleshooting/_index.md中新增"陷阱编号映射表"：
```markdown
## 陷阱编号映射表

| SKILL.md编号 | troubleshooting/分类编号 | 文件 | 描述 |
|---|---|---|---|
| #1 | 1.1 | common-traps.md | xxx |
| #14 | 4.1 | rss-source-traps.md | RssSource搜索功能 |
...
```

### 6.2 mock数字更新

重新统计JsExtensionsStub.kt的override fun数量，更新mock-unimplemented-functions.md：
- 完整实现：86个 → 实际132个
- Stub降级：38个 → 重新统计
- 不可用：8个 → 重新统计

### 6.3 MVP命名统一

删除SKILL.md中的MVP1-4决策树，统一为：
```markdown
## JVM仿真器
使用 legado-jvm.jar（统一版本，不再区分MVP1-4）
路径：legado-jvm/build/libs/legado-jvm.jar
```

### 6.4 jar路径统一

3处文档统一为 `legado-jvm/build/libs/legado-jvm.jar`：
- SKILL.md
- jvm-infrastructure.md
- code-evolution.md（删除"复制到tools/"步骤）

### 6.5 版本锁同步

jvm-infrastructure.md更新：
- okhttp: 4.12.0 → 5.3.2（与build.gradle.kts一致）
- gson: "未使用" → 2.13.2（与build.gradle.kts一致）

### 6.6 deep-verify.py状态统一

明确为"已废弃，降级路径使用verify-source.py"，在SKILL.md和AI_README.md中统一。删除AI_README.md工作流程图中的deep-verify.py引用。

### 6.7 site-features索引

在SKILL.md参考文档索引中添加site-features/。修正site-features/_INDEX.md顶部数量为5。

### 6.8 special-scenarios索引修复

在special-scenarios/_index.md中添加遗漏的rss-core-diff.md。

### 6.9 脚本声明完整性

为18个未声明脚本添加状态标注（active/deprecated/experimental），在SKILL.md或AI_README.md中建立完整脚本清单。

## 方向7：JVM仿真保真度对齐（P0）

### 7.1 getSubDomain修复

```kotlin
// NetworkUtilsStub.kt:183-194 修复前
fun getSubDomain(url: String): String {
    val host = getHost(url)
    return host  // ← 不剥离www前缀
}

// 修复后（手动剥离www前缀，完整PublicSuffixDatabase为P3）
fun getSubDomain(url: String): String {
    val host = getHost(url)
    // 简化说明：手动剥离www前缀 | 已知上限：不处理多级TLD(.co.uk/.com.cn) | 升级路径：引入PublicSuffixDatabase
    return if (host.startsWith("www.")) host.substring(4) else host
}
```

### 7.2 TextUtils.isEmpty对齐

```kotlin
// AnalyzeRule.kt:288,294,374 修复前
if (ruleStr.isNullOrBlank())  // ← 比真机多检查纯空白字符串

// 修复后（与真机TextUtils.isEmpty行为一致）
if (ruleStr.isNullOrEmpty())
```

### 7.3 ajax委托修复

```kotlin
// AnalyzeUrl.kt 新增override
private var ajaxRecursionGuard = false  // 防递归检查

override fun ajax(urlStr: String): String? {
    if (ajaxRecursionGuard) {
        // 防递归：如果已经在ajax调用中，走JsExtensionsStub.ajax降级
        return super.ajax(urlStr)
    }
    // 委托AnalyzeUrl自身构造请求，而非走JsExtensionsStub.ajax(Jsoup.connect)
    return try {
        ajaxRecursionGuard = true
        // 注意：必须传递baseUrl（方向1修复的值），否则ajax请求中的相对路径仍不拼接
        val analyzeUrl = AnalyzeUrl(urlStr, source = source, ruleData = ruleData, baseUrl = this.baseUrl)
        analyzeUrl.getStrResponse(useWebView = false).body
    } catch (e: Exception) {
        null
    } finally {
        ajaxRecursionGuard = false
    }
}
```

### 7.4 getHeaderMap修复

```kotlin
// BaseSourceInterface.kt getHeaderMap 修复
fun getHeaderMap(): Map<String, String> {
    val headerMap = mutableMapOf<String, String>()
    header?.forEach { (key, value) ->
        if (value.startsWith("@js:") || value.contains("<js>")) {
            // 支持@js:头部规则，委托AnalyzeRule.evalJS执行
            val analyzeRule = AnalyzeRule(ruleData ?: RuleData())
            val result = analyzeRule.evalJS(value.substringAfter("@js:").removeSuffix("</js>"), null)
            headerMap[key] = result ?: ""
        } else {
            headerMap[key] = value
        }
    }
    return headerMap
}
```

## 方向8：已知修复模式参考目录（P1）

### 8.1 known-fix-patterns目录结构（新增）

```
references/known-fix-patterns/
├── _index.md              # 索引+8种模式概述
├── js-absolute-path.md    # JS补全绝对路径
├── og-novel-meta.md       # og:novel meta+@put/@get
├── next-content-url.md    # nextContentUrl分页
├── replace-regex.md       # replaceRegex净化
├── search-method.md       # 搜索方法转换
├── gbk-encoding.md        # GBK编码
├── ranking-url.md         # 排行榜URL失效
└── audio-parse.md         # 音频解析
```

每种模式包含：适用场景、修复源示例、代码片段、注意事项。

### 8.2 HtmlStructureAnalyzer meta标签扩展

```kotlin
// HtmlStructureAnalyzer.kt 扩展
fun analyze(html: String): String {
    // ... 原有class/id提取逻辑 ...

    // 新增：meta标签提取
    val metaTags = mutableMapOf<String, String>()
    doc.select("meta[property]").forEach { el ->
        val property = el.attr("property")
        val content = el.attr("content")
        if (property.startsWith("og:") || property.startsWith("novel:")) {
            metaTags[property] = content
        }
    }

    // 新增：标签名统计（Web Components自定义元素）
    val tagCounts = mutableMapOf<String, Int>()
    doc.getAllElements().forEach { el ->
        val tagName = el.tagName()
        if (tagName.contains("-")) {  // Web Components自定义元素包含连字符
            tagCounts[tagName] = tagCounts.getOrDefault(tagName, 0) + 1
        }
    }

    return formatResult(classCounts, ids, suggestions, metaTags, tagCounts)
}
```

### 8.3 ErrorDiagnoser 3种新错误类型

```python
# error_diagnoser.py 扩展
ERROR_PATTERNS = {
    # ... 原有5种错误类型 ...

    "search_method_error": {
        "pattern": r"搜索结果为空|搜索返回空|search.*empty",
        "category": "搜索方法错误",
        "suggestion": "GET搜索返回空，可能需要POST方法。\n"
                     "修复方案：\n"
                     "  searchUrl改为POST方法：\n"
                     "  \"searchUrl\": \"https://example.com/search,{\\\"method\\\":\\\"POST\\\",\\\"body\\\":\\\"key={{key}}\\\"}\"",
        "trigger_html_analysis": False
    },
    "gbk_encoding_error": {
        "pattern": r"乱码|GBK|GB2312|encoding.*error",
        "category": "GBK编码错误",
        "suggestion": "GBK网站搜索关键词可能需要指定编码。\n"
                     "修复方案：\n"
                     "  searchUrl中添加 \"charset\":\"gbk\"",
        "trigger_html_analysis": False
    },
    "function_disabled": {
        "pattern": r"找不到内容|功能已关闭|服务不可用",
        "category": "功能失效vs网站不可达",
        "suggestion": "网站功能可能已失效（非工具链问题）。\n"
                     "区分方法：\n"
                     "  1. curl验证网站是否可达\n"
                     "  2. 检查网站端搜索功能是否正常\n"
                     "  3. 如果网站端失效，保留规则待网站修复",
        "trigger_html_analysis": False
    }
}
```

## 方向9：客户端-服务端命令兼容性+evalJS上下文（P0/P1）

### 9.1 命令清理

```python
# rule_engine_client.py 修复
class RuleEngineClient:
    # 已弃用命令列表
    DEPRECATED_COMMANDS = {
        "eval_css": "已弃用，请使用debug_book_source或debug_rss_source",
        "analyze_rule": "已弃用，请使用debug_book_source或debug_rss_source",
        "analyze_elements": "已弃用，请使用debug_book_source或debug_rss_source",
        "decrypt": "已弃用，请使用debug_book_source或debug_rss_source",
        "encrypt": "已弃用，请使用debug_book_source或debug_rss_source",
        "analyze_url": "已弃用，请使用debug_book_source或debug_rss_source"
    }

    def _send_command(self, command: str, **kwargs):
        if command in self.DEPRECATED_COMMANDS:
            return {"success": False, "error": f"⚠️ {self.DEPRECATED_COMMANDS[command]}"}
        # ... 正常命令处理 ...
```

### 9.2 evalJS上下文注入

```kotlin
// RuleEngineServer.kt:128-129 修复
"evalJS" -> {
    val js = obj.getString("js")
    val result = obj.optString("result", "")
    // 修复：注入完整上下文
    val bindings = engine.createBindings()
    bindings["result"] = result
    bindings["java"] = JsExtensionsStub(source, ruleData)  // 新增
    bindings["source"] = source  // 新增
    bindings["baseUrl"] = baseUrl ?: ""  // 新增
    bindings["cookie"] = cookieStore?.getCookie(baseUrl) ?: ""  // 新增
    bindings["cache"] = cacheManager  // 新增
    val evalResult = engine.eval(js, bindings)
    output.put("result", evalResult?.toString() ?: "")
}
```

### 9.3 CacheManagerStub LRU

```kotlin
// CacheManagerStub.kt 修复
class CacheManagerStub : CacheManager {
    // 简化说明：使用LinkedHashMap+removeEldestEntry实现简易LRU | 已知上限：非线程安全 | 升级路径：使用ConcurrentLinkedHashMap
    private val cache = object : LinkedHashMap<String, String>(100, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, String>?): Boolean {
            return size > 500  // 最大500条缓存
        }
    }

    @Synchronized
    override fun get(key: String): String? = cache[key]

    @Synchronized
    override fun put(key: String, value: String) {
        cache[key] = value
    }
}
```

## 方向10：AI工作流编排层（P0）

> **核心理念**：工具改进的最终目的是让AI更好地使用skill生成/修复书源。工具改进与AI使用之间不能存在断层。

### 10.1 多轮迭代修复闭环

```python
# debug-source.py 新增 --max-iterations 参数
parser.add_argument("--max-iterations", type=int, default=3, help="最大迭代修复次数")

def iterative_repair_loop(source_obj, max_iterations=3):
    """AI多轮迭代修复闭环：测试→分析→修复→重测"""
    for iteration in range(max_iterations):
        # 1. 执行测试
        result = run_debug(source_obj)
        if result.get("success"):
            return result  # 通过，退出

        # 2. 分析错误诊断
        diagnosis = result.get("error_diagnosis", {})
        if not diagnosis:
            return result  # 无法诊断，退出

        # 3. 自动应用修复建议
        fixed = apply_auto_fix(source_obj, diagnosis, result.get("html_analysis"))
        if not fixed:
            return result  # 无法自动修复，退出

        # 4. 更新source_obj用于下一轮
        source_obj = fixed
        print(f"[迭代 {iteration+1}/{max_iterations}] 已应用修复，重新测试...")

    return result  # 达到最大迭代次数

def apply_auto_fix(source_obj, diagnosis, html_analysis):
    """根据错误诊断自动应用修复"""
    error_type = diagnosis.get("type")
    if error_type == "rule_empty" and html_analysis:
        # 建议→规则自动转换
        suggestions = html_analysis.get("suggestions", [])
        for s in suggestions:
            if "书籍列表" in s or "文章列表" in s:
                selector = extract_selector(s)  # 提取class.xxx
                source_obj["ruleSearch"]["bookList"] = f"{selector}@tag.li"
                return source_obj
    elif error_type == "relative_url":
        # 经验→自动复用：注入JS补全绝对路径
        source_obj["ruleSearch"]["bookUrl"] += "<js>result.indexOf('http')===0?result:'https://'+location.host+result</js>"
        return source_obj
    # ... 其他错误类型的自动修复 ...
    return None  # 无法自动修复
```

### 10.2 建议→规则自动转换

```python
# scripts/rule_builder.py（新增）
class RuleBuilder:
    """将HtmlStructureAnalyzer建议选择器自动转化为规则字段"""

    SUGGESTION_TO_RULE = {
        "书籍列表": ("ruleSearch", "bookList"),
        "文章列表": ("ruleSearch", "bookList"),
        "标题": ("ruleBookInfo", "name"),
        "作者": ("ruleBookInfo", "author"),
        "正文": ("ruleContent", "content"),
    }

    def build_from_suggestion(self, suggestion: str, html_analysis: dict) -> dict:
        """从建议选择器构建规则字段"""
        for keyword, (rule_section, field) in self.SUGGESTION_TO_RULE.items():
            if keyword in suggestion:
                selector = self._extract_selector(suggestion)
                # 自动拼装：class.xxx@tag.li（列表项）
                if "列表" in keyword:
                    return {rule_section: {field: f"{selector}@tag.li"}}
                else:
                    return {rule_section: {field: selector}}
        return {}

    def _extract_selector(self, suggestion: str) -> str:
        """从建议文本提取选择器（如"class.book-card (24 次)"→"class.book-card"）"""
        import re
        match = re.search(r'(class\.\S+|id\.\S+)', suggestion)
        return match.group(1) if match else ""
```

### 10.3 代码进化流程

```python
# scripts/code_evolution.py（新增）
class CodeEvolution:
    """Phase 5新陷阱→JVM测试用例/Python检查项转化"""

    def trap_to_jvm_test(self, trap_description: str, trap_type: str) -> str:
        """将新陷阱转化为JVM测试用例模板"""
        return f"""// 自动生成测试用例：{trap_description}
// 陷阱类型：{trap_type}
// 生成日期：{datetime.now().strftime('%Y-%m-%d')}
@Test
fun test_{trap_type}_scenario() {{
    val source = BookSource(bookSourceUrl = "test_url")
    val result = BookSourceDebugger().debugSearch(source, "test_key")
    // TODO: 根据陷阱描述补充断言
    assertNotNull(result)
}}
"""

    def trap_to_python_check(self, trap_description: str, trap_type: str) -> str:
        """将新陷阱转化为Python验证脚本检查项"""
        return f"""# 自动生成检查项：{trap_description}
# 陷阱类型：{trap_type}
def check_{trap_type}(source, result):
    \"\"\"检查{trap_description}\"\"\"
    # TODO: 根据陷阱描述补充检查逻辑
    return True
"""
```

## 方向11：Phase 4源码导航工具（P1）

### 11.1 错误类型→源码映射索引

```python
# scripts/source_navigation.py（新增）
class SourceNavigation:
    """错误类型→真机源码文件/行号映射索引"""

    ERROR_TO_SOURCE = {
        "relative_url": {
            "simulator": "NetworkUtilsStub.kt:getAbsoluteURL 第131行",
            "real_device": "NetworkUtils.kt:getAbsoluteURL 第145行",
            "description": "baseUrl为空时不拼接相对路径"
        },
        "js_error": {
            "simulator": "RuleEngineServer.kt:evalJS 第128行",
            "real_device": "AnalyzeRule.kt:evalJS 第350行",
            "description": "evalJS上下文注入不完整"
        },
        "rule_empty": {
            "simulator": "BookSourceDebugger.kt:debugSearch 第130行",
            "real_device": "Debug.kt:debugSearch 第X行",
            "description": "规则不匹配时触发HTML分析"
        },
        "cookie_domain": {
            "simulator": "NetworkUtilsStub.kt:getSubDomain 第183行",
            "real_device": "NetworkUtils.kt:getSubDomain 第212行",
            "description": "getSubDomain不剥离www前缀"
        }
    }

    def navigate(self, error_type: str) -> dict:
        """根据错误类型返回源码定位"""
        return self.ERROR_TO_SOURCE.get(error_type, {
            "simulator": "未知",
            "real_device": "未知",
            "description": "未索引的错误类型，需手动查找"
        })
```

### 11.2 真机Debug.kt对比分析

在references/source-analysis/中新增`debug-kt-diff.md`：
- 仿真器BookSourceDebugger.kt vs 真机Debug.kt 逐方法对比
- 重点关注：真机Debug.kt是否在搜索阶段传baseUrl？setRedirectUrl何时调用？
- 记录差异点，补充到保真度限制清单

## 方向12：仿真器可信度评估（P1）

### 12.1 可信度评分算法

```python
# scripts/confidence_evaluator.py（新增）
class ConfidenceEvaluator:
    """测试结果可信度评分"""

    # 规则类型→基础可信度
    RULE_TYPE_CONFIDENCE = {
        "pure_css": 0.95,      # 纯CSS选择器，高可信
        "pure_xpath": 0.95,    # 纯XPath，高可信
        "contains_js": 0.75,   # 含JS，中可信
        "contains_encrypt": 0.50,  # 含加密，低可信
        "contains_ajax": 0.60,     # 含ajax，低可信
    }

    # 保真度限制区域→可信度扣减
    FIDELITY_PENALTY = {
        "getSubDomain": 0.10,      # Cookie域名问题
        "evalJS_context": 0.15,    # JS上下文不完整
        "ajax_delegate": 0.20,     # ajax走Jsoup
        "aes_encode": 0.10,        # 加密行为不一致
    }

    def evaluate(self, source: dict, test_result: dict) -> dict:
        """评估测试结果可信度"""
        rules = self._extract_rules(source)
        base_confidence = 1.0
        penalties = []

        for rule_type, confidence in self.RULE_TYPE_CONFIDENCE.items():
            if self._rule_matches_type(rules, rule_type):
                base_confidence = min(base_confidence, confidence)

        for area, penalty in self.FIDELITY_PENALTY.items():
            if self._rule_uses_fidelity_area(rules, area):
                base_confidence -= penalty
                penalties.append(area)

        if base_confidence >= 0.85:
            level = "高"
        elif base_confidence >= 0.65:
            level = "中"
        else:
            level = "低"

        return {
            "score": round(base_confidence, 2),
            "level": level,
            "penalties": penalties,
            "needs_real_device": level == "低",
            "warning": f"⚠️ 可信度: {level}（{base_confidence:.0%}）" if level != "高" else None
        }
```

### 12.2 经验冲突解决

```python
# experience_manager.py 扩展
class ExperienceManager:
    def resolve_conflict(self, experiences: list) -> dict:
        """经验冲突解决：置信度评分+时效性+优先级"""
        scored = []
        for exp in experiences:
            score = 0
            # 置信度评分（基于修复成功率）
            score += exp.get("success_rate", 0) * 0.5
            # 时效性（新经验优先，网站可能改版）
            days_old = (datetime.now() - exp.get("date")).days
            score += max(0, 1 - days_old / 90) * 0.3  # 90天后时效性为0
            # 测试覆盖度
            score += exp.get("test_coverage", 0) * 0.2
            scored.append((exp, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None
```

### 12.3 网站改版检测

```python
# error_diagnoser.py 扩展
ERROR_PATTERNS = {
    # ... 原有8种错误类型 ...

    "site_redesign": {
        "pattern": r"所有选择器.*空|全部规则.*失败|HTTP 301|HTTP 302.*永久重定向",
        "category": "网站改版",
        "suggestion": "网站可能已改版。\n"
                     "判断方法：\n"
                     "  1. 如果所有选择器都失效，可能是网站改版而非规则错误\n"
                     "  2. 检查网站URL结构是否变化\n"
                     "  3. 重新分析网站HTML结构\n"
                     "  4. 更新所有规则",
        "trigger_html_analysis": True
    }
}
```

### 方向13：大规模真实源测试验证

```python
# 13.1 测试集构建——场景覆盖矩阵
class TestSourceSelector:
    """从项目可用源中选取10+10测试源，覆盖15+种场景"""

    SCENE_MATRIX = {
        "pure_css":          {"difficulty": "简单", "min_count": 2},
        "contains_js":       {"difficulty": "中等", "min_count": 2},
        "contains_encrypt":  {"difficulty": "困难", "min_count": 1},
        "contains_ajax":     {"difficulty": "中等", "min_count": 1},
        "login_required":    {"difficulty": "困难", "min_count": 1},
        "captcha":           {"difficulty": "困难", "min_count": 1},
        "gbk_encoding":      {"difficulty": "中等", "min_count": 1},
        "audio_parse":       {"difficulty": "中等", "min_count": 1},
        "video_parse":       {"difficulty": "困难", "min_count": 1},
        "ssr_anti_crawl":    {"difficulty": "困难", "min_count": 1},
        "web_components":    {"difficulty": "中等", "min_count": 1},
        "next_content_url":  {"difficulty": "中等", "min_count": 1},
        "replace_regex":     {"difficulty": "简单", "min_count": 1},
        "og_novel_meta":     {"difficulty": "简单", "min_count": 1},
        "single_url_mode":   {"difficulty": "中等", "min_count": 1},
    }

    def select_test_sources(self, all_sources: list, source_type: str) -> list:
        """按场景覆盖矩阵选取测试源"""
        # 简化说明：按SCENE_MATRIX的min_count从all_sources中选取 | 已知上限：一个源可能覆盖多个场景 | 升级路径：自动场景检测
        # 实际筛选结果：从12,180个源中选取10+10个，覆盖15/15场景（100%）
        # 测试集清单见spec.md REQ-14，JSON文件：temp/test-book-sources.json + temp/test-rss-sources.json
        selected = []
        for scene, config in self.SCENE_MATRIX.items():
            candidates = self._find_sources_for_scene(all_sources, scene, source_type)
            selected.extend(candidates[:config["min_count"]])
        return selected[:10]  # 最多10个

# 13.2 基线采集
class BaselineCollector:
    """改进前用当前工具链跑20个测试源，记录基线数据"""

    def collect_baseline(self, test_sources: list) -> dict:
        results = []
        for source in test_sources:
            result = run_debug(source)  # 用当前工具链测试
            results.append({
                "source_name": source.get("bookSourceName", source.get("sourceName")),
                "source_type": "book" if "bookSourceName" in source else "rss",
                "pass": result.get("success", False),
                "error_type": result.get("error_diagnosis", {}).get("type"),
                "manual_intervention": self._count_manual_intervention(result),
                "duration_sec": result.get("duration", 0),
            })
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r["pass"]),
            "pass_rate": sum(1 for r in results if r["pass"]) / len(results),
            "error_distribution": self._count_errors(results),
            "manual_interventions": sum(r["manual_intervention"] for r in results),
            "avg_duration": sum(r["duration_sec"] for r in results) / len(results),
        }

# 13.3 改进后效果验证
class ImprovementValidator:
    """改进后用相同测试集跑一遍，输出对比报告"""

    def compare(self, baseline: dict, after: dict) -> dict:
        return {
            "pass_rate_improvement": after["pass_rate"] - baseline["pass_rate"],
            "manual_intervention_reduction": baseline["manual_interventions"] - after["manual_interventions"],
            "error_coverage": self._check_error_coverage(after),
            "iteration_success_rate": self._check_iteration_success(after),
        }
```

### 方向14：Phase 2规则构建指导

```python
# 14.1 解析方式选择决策树
class ParseStrategySelector:
    """根据网站分析结果选择最佳解析方式"""

    DECISION_TREE = {
        # 简化说明：决策树基于网站特征自动选择 | 已知上限：复杂网站可能需要多种方式组合 | 升级路径：ML自动选择
        "api_response": "jsonpath",      # API响应用JSONPath
        "simple_html": "css",            # 简单HTML结构用CSS
        "complex_html": "xpath",         # 复杂HTML/XHTML用XPath
        "text_extract": "regex",         # 纯文本提取用正则
        "dynamic_render": "js",          # 动态渲染/加密用JS
        "encrypted_content": "js+encrypt", # 加密内容用JS+加密函数
    }

    def select(self, site_analysis: dict) -> str:
        if site_analysis.get("is_api"): return "jsonpath"
        if site_analysis.get("has_encryption"): return "js+encrypt"
        if site_analysis.get("is_dynamic"): return "js"
        if site_analysis.get("html_complexity") == "high": return "xpath"
        if site_analysis.get("is_text_only"): return "regex"
        return "css"  # 默认CSS

# 14.2 方向→Phase映射表
DIRECTION_TO_PHASE = {
    1: "Phase 3",    # JVM仿真器修复→测试驱动
    2: "Phase 3",    # 可观测性→测试驱动
    3: "Phase 3",    # 客户端优化→测试驱动
    4: "Phase 1+5",  # 经验闭环→经验优先+经验反哺
    5: "Phase 3",    # 错误诊断→测试驱动
    6: "ALL",        # 文档治理→全Phase
    7: "Phase 3",    # 保真度对齐→测试驱动
    8: "Phase 1",    # 已知修复模式→经验优先
    9: "Phase 3",    # 命令兼容性→测试驱动
    10: "Phase 2+3", # AI工作流编排→构建规则+测试驱动
    11: "Phase 4",  # 源码导航→源码深挖
    12: "Phase 3",  # 可信度评估→测试驱动
    13: "ALL",      # 大规模测试→全Phase验证
    14: "Phase 2",  # 规则构建指导→构建规则
    15: "Phase 2+3", # 用户交互→构建规则+测试驱动
    16: "Phase 3",  # 性能优化→测试驱动
}
```

### 方向15：用户交互场景设计

```python
# 15.1 用户交互处理器
class UserInteractionHandler:
    """处理AI使用skill时的用户交互场景"""

    def handle_url_unreachable(self, source, error):
        """URL不可达：向用户报告并请求新URL"""
        return {
            "type": "url_unreachable",
            "message": f"网站 {source['bookSourceUrl']} 不可达",
            "suggestion": "请确认网站是否已迁移，或提供新的URL",
            "current_url": source["bookSourceUrl"],
            "needs_user_input": "new_url",
        }

    def handle_login_required(self, source, html_analysis):
        """需登录：向用户请求Cookie"""
        return {
            "type": "login_required",
            "message": f"网站 {source['bookSourceUrl']} 需要登录",
            "suggestion": "请在浏览器中登录该网站，然后提供Cookie值",
            "cookie_guide": "F12→Network→任意请求→Request Headers→Cookie",
            "needs_user_input": "cookie",
        }

    def handle_captcha(self, source, html_analysis):
        """验证码：请求用户手动处理"""
        return {
            "type": "captcha_detected",
            "message": f"网站 {source['bookSourceUrl']} 需要验证码",
            "suggestion": "请在浏览器中手动访问该网站并完成验证码",
            "needs_user_input": "manual_captcha_resolution",
        }

# 15.2 标准化失败报告
class FailureReporter:
    """3轮迭代修复失败后输出标准化报告"""

    def generate_report(self, source, iterations_log):
        return {
            "source_name": source.get("bookSourceName"),
            "source_url": source.get("bookSourceUrl"),
            "error_type": iterations_log[-1].get("error_type"),
            "error_detail": iterations_log[-1].get("error_detail"),
            "attempted_fixes": [it.get("fix_applied") for it in iterations_log],
            "current_rule_json": source,
            "needs_user_input": self._suggest_user_action(iterations_log[-1]),
            "real_device_verification": self._gen_real_device_steps(source),
        }

    def _gen_real_device_steps(self, source):
        """生成真机验证步骤"""
        return [
            "1. 在Legado App中导入此书源",
            "2. 搜索关键词测试搜索阶段",
            "3. 点击搜索结果测试详情阶段",
            "4. 进入目录测试目录阶段",
            "5. 点击章节测试正文阶段",
            "6. 反馈每个阶段的成功/失败及错误信息",
        ]
```

### 方向16：性能优化与批量并行

```python
# 16.1 JVM常驻模式
class JvmPersistentServer:
    """JVM进程常驻+stdin/stdout通信，避免每次测试重启JVM"""

    def __init__(self, jar_path, port=9999):
        self.process = None
        self.jar_path = jar_path
        self.port = port

    def start(self):
        """启动JVM常驻进程"""
        # 简化说明：JVM启动后保持运行，通过stdin发送命令 | 已知上限：进程崩溃需重启 | 升级路径：健康检查+自动重启
        self.process = subprocess.Popen(
            ["java", "-jar", self.jar_path, "--port", str(self.port), "--mode", "persistent"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def send_command(self, command_json: str) -> dict:
        """发送命令并读取响应"""
        self.process.stdin.write((command_json + "\n").encode())
        self.process.stdin.flush()
        response = self.process.stdout.readline().decode()
        return json.loads(response)

    def stop(self):
        self.send_command('{"action": "shutdown"}')
        self.process.wait(timeout=5)

# 16.2 多端口并行测试
class ParallelTestRunner:
    """多端口启动多个JVM实例+任务队列分配"""

    def __init__(self, jar_path, max_workers=4):
        self.jar_path = jar_path
        self.max_workers = max_workers
        self.servers = []

    def run_batch(self, sources: list) -> list:
        """并行测试多个源"""
        # 简化说明：每个worker一个JVM实例，端口9999+i | 已知上限：端口冲突 | 升级路径：动态端口分配
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._test_one, source, i): source
                       for i, source in enumerate(sources)}
            for future in as_completed(futures):
                results.append(future.result())
        return results

    def _test_one(self, source, worker_id):
        port = 9999 + (worker_id % self.max_workers)
        server = JvmPersistentServer(self.jar_path, port)
        server.start()
        try:
            return server.send_command(json.dumps(source))
        finally:
            server.stop()
```

## Architecture Decisions

### AD-1：相对路径拼接放在AnalyzeUrl构造时还是AnalyzeRule解析时？

**决策**：两者都做。

**理由**：
- AnalyzeUrl构造时传baseUrl → 解决URL模板中的相对路径
- AnalyzeRule设置redirectUrl → 解决规则解析出的相对路径
- 真机两者都做，JVM仿真器应对齐
- setContent(html, response.url)已设置baseUrl，setRedirectUrl是额外保障，两者不冲突

### AD-2：HTML结构分析放在JVM端还是Python端？

**决策**：JVM端。

**理由**：
- JVM端已有Jsoup库
- JVM端在收集HTML时就能分析
- 减少数据传输量（只传分析结果，不传整个HTML）
- **大HTML截断**：超过100KB截断前100KB，避免性能问题

### AD-3：经验写入是自动还是半自动？

**决策**：自动写入（测试通过才写入），可配置关闭。

**理由**：
- 测试通过才写入保证质量
- 自动写入减少手动操作
- --no-experience参数可关闭
- **经验去重**：写入前搜索basic-memory检查是否已存在相似经验

### AD-4：结构化输出格式

**决策**：JSON格式，包含success/stages/html_sources/error_diagnosis/experience。

**理由**：
- AI可直接json.loads解析
- 包含所有调试信息，无需解析stdout
- 可扩展（未来可添加更多字段）

### AD-5：basic-memory访问方式（修正版）

**决策**：debug-source.py输出经验数据到JSON文件，由AI agent外层通过MCP工具写入basic-memory。

**理由**：
- basic-memory是MCP服务器（提供MCP工具如`mcp_basic-memory_search_notes`/`mcp_basic-memory_write_note`），不是CLI命令行工具
- Python脚本无法通过subprocess调用MCP工具（run_mcp是AI agent的能力）
- **方案A（推荐）**：debug-source.py输出`output/experience-pending.json`，AI agent执行完debug-source.py后读取该文件，通过MCP工具写入basic-memory
- **降级路径**：experience_manager.py用Python原生文件搜索（`pathlib.Path.rglob`，非grep命令，Windows兼容）
- **降级写入**：写入references/troubleshooting/auto/目录，添加AUTO_GENERATED标记

**experience_manager.py修正**：
```python
class ExperienceManager:
    def __init__(self):
        self._references_dir = Path(__file__).parent.parent / "references" / "troubleshooting"
        self._auto_dir = self._references_dir / "auto"
        self._pending_file = Path(__file__).parent.parent.parent / "output" / "experience-pending.json"

    def search(self, source_url: str, source_name: str) -> str:
        """测试前检索：AI agent在外层通过MCP搜索，debug-source.py用文件搜索降级"""
        keyword = source_url or source_name
        matches = []
        for md_file in self._references_dir.rglob("*.md"):
            try:
                if keyword in md_file.read_text(encoding='utf-8'):
                    matches.append(str(md_file))
            except Exception:
                continue
        return f"找到相似案例:\n" + "\n".join(matches) if matches else "无相似案例"

    def write_pending(self, source: dict, fix_info: dict, test_result: dict):
        """测试后写入：输出到JSON文件，由AI agent外层通过MCP写入basic-memory"""
        if not test_result.get("success"):
            return
        experience = self._format_experience(source, fix_info, test_result)
        # 写入pending文件，等待AI agent通过MCP写入basic-memory
        self._pending_file.parent.mkdir(parents=True, exist_ok=True)
        pending_data = []
        if self._pending_file.exists():
            pending_data = json.loads(self._pending_file.read_text(encoding='utf-8'))
        pending_data.append({"content": experience, "tags": ["自动积累", fix_info.get('error_type', '')]})
        self._pending_file.write_text(json.dumps(pending_data, ensure_ascii=False, indent=2), encoding='utf-8')
        # 同时降级写入到auto目录
        self._write_references(experience, source)
```

### AD-6：ErrorDiagnoser替换还是新增？（新增）

**决策**：新增独立模块error_diagnoser.py，替换debug-source.py中现有的_generate_error_suggestion函数。

**理由**：
- 独立模块便于测试和扩展
- 替换现有函数避免代码重复
- 现有函数只有4类且不精确，新模块有5类+代码示例

### AD-7：HtmlStructureAnalyzer触发条件（新增）

**决策**：扩展到所有阶段的规则不匹配。

**理由**：
- 不仅bookList.isEmpty()时触发
- 详情页name为空、目录页chapterList为空、正文页content为空时也触发
- 确保所有阶段的规则不匹配都能被诊断

### AD-8：经验去重实现（新增）

**决策**：写入前搜索basic-memory检查是否已存在相似经验。

**理由**：
- 相同错误类型+相同修复方案视为重复
- 写入前搜索避免重复
- 如果basic-memory不可用，降级写入时检查auto/目录是否已有同名文件

### AD-9：known-fix-patterns目录位置（方向8新增）

**决策**：放在references/known-fix-patterns/，作为references/的第7大目录。

**理由**：
- 与现有6大目录（规则语法/URL模板/实体字段/示例源/troubleshooting/js-extensions等）平级
- AI在Phase 1经验搜索时可自动检索
- 每种模式独立文件，便于扩展和维护

### AD-10：evalJS上下文注入策略（方向9新增）

**决策**：注入完整上下文（java/source/baseUrl/cookie/cache），与真机对齐。

**理由**：
- 真机evalJS注入了完整上下文，JS可调用java.ajax等
- 当前仅注入result，导致JS规则无法调用java对象
- 注入java/source/baseUrl/cookie/cache后，JS规则能力与真机一致
- **风险**：注入source对象可能暴露敏感信息，但仿真器环境无真实用户数据

### AD-11：CacheManagerStub LRU策略（方向9新增）

**决策**：使用LinkedHashMap+removeEldestEntry实现简易LRU，最大500条。

**理由**：
- LinkedHashMap+accessOrder=true+removeEldestEntry是最简实现（标准库）
- 最大500条避免OOM
- @Synchronized保证线程安全
- **已知上限**：非线程安全的ConcurrentHashMap替代方案 | **升级路径**：ConcurrentLinkedHashMap

### AD-12：AI工作流编排策略（方向10新增）

**决策**：在debug-source.py中实现多轮迭代修复闭环，最大3轮迭代，每轮包含"测试→诊断→自动修复→重测"。

**理由**：
- 当前AI使用skill的流程是"测试→看结果→人工判断→手动修复→重新测试"，断层在"人工判断"和"手动修复"
- 多轮迭代闭环让AI自动完成"判断+修复"环节，减少人工介入
- 最大3轮是经验值：第1轮修复常见问题（选择器/路径），第2轮修复复杂问题（JS/编码），第3轮仍失败则标记需人工介入
- **建议→规则自动转换**用RuleBuilder类实现，而非让AI每次手动拼装选择器
- **经验→自动复用**用experience_manager返回相似案例后，AI提取修复片段注入当前源
- **代码进化**用CodeEvolution类将Phase 5新陷阱转化为JVM测试用例/Python检查项
- **风险**：自动修复可能引入新错误，每轮修复后必须重新测试验证

### AD-13：源码导航索引位置（方向11新增）

**决策**：错误类型→源码映射索引放在scripts/source_navigation.py（Python脚本），真机Debug.kt对比分析放在references/source-analysis/debug-kt-diff.md（Markdown文档）。

**理由**：
- 映射索引是代码（可被debug-source.py调用），放scripts/目录与其他Python脚本平级
- 对比分析是文档（供AI阅读参考），放references/source-analysis/与现有源码分析文档平级
- 两者配合：source_navigation.py返回源码定位，AI再查阅debug-kt-diff.md了解差异详情
- **已知上限**：映射索引需手动维护，源码行号可能因版本更新而偏移 | **升级路径**：从源码自动提取行号

### AD-14：可信度评分算法选择（方向12新增）

**决策**：采用"规则类型基础分+保真度限制扣减"的加权方案，阈值0.85/0.65划分高/中/低三级。

**理由**：
- 规则类型决定基础可信度（纯CSS=0.95高可信，含JS=0.75中可信，含加密=0.50低可信）
- 保真度限制区域决定扣减（getSubDomain扣0.10，evalJS上下文扣0.15，ajax委托扣0.20）
- 两者叠加：如"含JS+evalJS上下文不完整"→0.75-0.15=0.60→低可信→标记需真机验证
- 阈值0.85/0.65：0.85以上高可信（可直接信任），0.65-0.85中可信（建议验证），0.65以下低可信（必须真机验证）
- **已知上限**：扣减值是经验估算，非精确测量 | **升级路径**：基于大量测试数据回归校准扣减值

### AD-15：大规模测试验证策略（方向13新增）

**决策**：采用"改进前基线→改进后对比"的前后对比策略，测试集固定20个源（10书源+10订阅源），覆盖15+种场景。

**理由**：
- 5+1回归测试源只能验证"没退步"，无法验证"更好用"
- 20个源覆盖15+种场景，足以验证新增能力（HtmlStructureAnalyzer/ErrorDiagnoser/经验检索/多轮迭代）在未知源上的效果
- 前后对比能量化改进效果（通过率提升X%、人工介入减少Y%）
- 测试源从项目可用源（13,166书源+974 RSS源）中按场景覆盖矩阵选取
- **已知上限**：20个源可能不覆盖所有边缘场景 | **升级路径**：扩展到50+源

### AD-16：Phase 2规则构建指导位置（方向14新增）

**决策**：新增references/rule-construction-guide/目录，包含解析方式决策树、网站类型策略、字段填写模板。

**理由**：
- Phase 2（构建规则）是skill 5阶段闭环中唯一没有专门改进方向的Phase
- 从零创建书源是AI使用skill的核心场景之一（不只是修复）
- 决策树帮助AI快速选择解析方式，减少试错
- 字段填写模板降低AI生成规则的错误率
- 方向→Phase映射表帮助AI将工具改进映射到Phase工作流
- **已知上限**：决策树可能不覆盖所有网站类型 | **升级路径**：基于测试结果持续扩充

### AD-17：用户交互场景设计策略（方向15新增）

**决策**：在debug-source.py中集成UserInteractionHandler，AI遇到需用户介入场景时输出标准化交互请求。

**理由**：
- AI使用skill时遇到URL不可达/需登录/验证码等场景会"卡住"，没有标准化的交互流程
- UserInteractionHandler输出结构化交互请求（类型+消息+建议+需用户提供的信息）
- FailureReporter定义3轮迭代失败后的标准化报告格式
- 真机验证流程：可信度"低"时输出真机验证步骤，用户反馈后AI更新经验库
- **已知上限**：交互请求需要AI外层解析并转发给用户 | **升级路径**：集成到skill工作流自动处理

### AD-18：JVM常驻+多端口并行策略（方向16新增）

**决策**：采用JVM进程常驻+stdin/stdout通信+多端口并行（默认4个worker）。

**理由**：
- 当前每次测试都启动JVM进程，启动开销可能占单源测试时间的50%+
- JVM常驻模式避免重复启动，通过stdin发送命令+stdout读取响应
- 多端口并行：每个worker一个JVM实例（端口9999+i），ThreadPoolExecutor分配任务
- 20源并行（4 worker）总耗时约为串行的1/3
- HTML分析性能决策：对风险18采用"只分析body直接子元素"方案（正文页关键class通常在body直接子元素中）
- **已知上限**：JVM进程崩溃需重启 | **升级路径**：健康检查+自动重启

## File Changes

### 修改文件

| 文件 | 修改内容 | 源码行号 |
|------|---------|---------|
| BookSourceDebugger.kt | 搜索/详情阶段加baseUrl+setRedirectUrl | 117-123, 215-219 |
| BookSourceDebugger.kt | 详情/目录/正文阶段加HtmlStructureAnalyzer触发 | 255, 367, 529 |
| RssSourceDebugger.kt | 列表/内容/singleUrl阶段加baseUrl+toAbsoluteUrl | 188-193, 305-308, 367-376 |
| RssSourceDebugger.kt | ruleContent回退标记 | 333-339 |
| RssSourceDebugger.kt | extractJsRule保留HTML模板 | 59-68 |
| RssSourceDebugger.kt | sortUrl未匹配警告 | 161-166 |
| RssSourceDebugger.kt | 列表阶段加HtmlStructureAnalyzer触发 | 188后 |
| AnalyzeUrl.kt（仿真器） | override ajax方法 | 新增方法 |
| AnalyzeRule.kt（仿真器） | isNullOrBlank改回isNullOrEmpty | 288, 294, 374 |
| NetworkUtilsStub.kt | getSubDomain剥离www前缀 | 183-194 |
| BaseSourceInterface.kt | getHeaderMap支持@js:头部规则 | getHeaderMap方法 |
| debug-source.py | 新增--output/--timeout参数 | argparse区域 |
| debug-source.py | JSON去重 | 536,775,788,812,159 |
| debug-source.py | 进化重验证参数修复 | 977-985 |
| debug-source.py | batch_debug传webview_handler | 646-651 |
| debug-source.py | 统一阶段命名 | 370-375, 453, 433 |
| debug-source.py | 网络错误正则修复 | 326 |
| SKILL.md | 陷阱编号统一+MVP命名统一+jar路径统一+site-features索引 | 多处 |
| mock-unimplemented-functions.md | mock数字更新 | 第5,7行 |
| AI_README.md | deep-verify.py状态统一+删除工作流中的deep-verify引用 | 93, 122-124 |
| jvm-infrastructure.md | okhttp/gson版本同步 | 31, 32 |
| special-scenarios/_index.md | 添加rss-core-diff.md | 索引区域 |
| site-features/_INDEX.md | 顶部数量修正为5 | 第24行 |
| HtmlStructureAnalyzer.kt | meta标签提取+标签名统计扩展 | analyze方法 |
| error_diagnoser.py | 新增3种错误类型（搜索方法/GBK编码/功能失效） | ERROR_PATTERNS |
| rule_engine_client.py | 6个已弃用命令清理+标注 | DEPRECATED_COMMANDS |
| RuleEngineServer.kt | evalJS注入完整上下文 | 128-129 |
| CacheManagerStub.kt | LRU淘汰机制 | 新增实现 |
| SKILL.md | 参考文档索引添加known-fix-patterns/ | 索引区域 |
| debug-source.py | 新增--max-iterations参数+iterative_repair_loop函数（方向10） | argparse区域+main() |
| debug-source.py | 新增apply_auto_fix函数（方向10，建议→规则自动修复） | 新增函数 |
| error_diagnoser.py | 新增site_redesign错误类型（方向12，网站改版检测） | ERROR_PATTERNS |
| experience_manager.py | 新增resolve_conflict方法（方向12，经验冲突解决） | ExperienceManager类 |
| debug-source.py | 新增--batch参数+集成UserInteractionHandler（方向15） | argparse区域 |
| debug-source.py | 新增--persistent参数启用JVM常驻模式（方向16） | argparse区域 |

### 新增文件

| 文件 | 内容 |
|------|------|
| HtmlStructureAnalyzer.kt | HTML结构分析模块（含meta标签提取+标签名统计） |
| scripts/error_diagnoser.py | 错误诊断模块（9种错误类型：原8种+网站改版） |
| scripts/experience_manager.py | 经验管理模块（JSON文件+MCP外层写入+经验冲突解决） |
| references/troubleshooting/auto/ | 降级写入隔离目录 |
| references/known-fix-patterns/ | 已知修复模式参考目录（8种模式） |
| scripts/rule_builder.py | 建议→规则自动转换模块（方向10，RuleBuilder类） |
| scripts/code_evolution.py | 代码进化模块（方向10，Phase 5新陷阱→JVM测试用例/Python检查项） |
| scripts/source_navigation.py | Phase 4源码导航模块（方向11，错误类型→源码映射索引） |
| scripts/confidence_evaluator.py | 可信度评估模块（方向12，ConfidenceEvaluator类） |
| references/source-analysis/debug-kt-diff.md | 真机Debug.kt对比分析文档（方向11） |
| scripts/test_source_selector.py | 测试源选择器（方向13，场景覆盖矩阵+测试集构建） |
| scripts/baseline_collector.py | 基线采集器（方向13，改进前基线数据采集） |
| scripts/improvement_validator.py | 改进效果验证器（方向13，前后对比报告） |
| references/rule-construction-guide/ | Phase 2规则构建指导目录（方向14，决策树+策略+模板） |
| scripts/user_interaction_handler.py | 用户交互处理器（方向15，URL不可达/Cookie/登录/验证码交互） |
| scripts/failure_reporter.py | 标准化失败报告生成器（方向15，3轮失败后报告+真机验证步骤） |
| scripts/jvm_persistent_server.py | JVM常驻服务器（方向16，stdin/stdout通信） |
| scripts/parallel_test_runner.py | 多端口并行测试运行器（方向16，ThreadPoolExecutor+多端口JVM） |

## 风险预测与应对

### 风险1：修改JVM仿真器引入新bug
- **应对**：修改后运行5个修复源回归测试+衍墨轩书搜索阶段已知失效（网站端问题）
- **回滚**：保留修改前的JAR备份（legado-jvm.jar.bak）

### 风险2：经验库膨胀
- **应对**：经验去重（写入前搜索basic-memory检查是否已存在）+ 质量评估（测试通过才写入）

### 风险3：HTML结构分析不准确
- **应对**：建议选择器标注"建议"而非"确定"
- **AI仍需验证**：建议只是辅助

### 风险4：basic-memory不可用
- **应对**：降级到Python原生文件搜索（`pathlib.Path.rglob`，Windows兼容）
- **降级写入**：写入references/troubleshooting/auto/目录，添加AUTO_GENERATED标记

### 风险5：JVM与真机编码差异
- **已知限制**：GBK/GB2312网站可能乱码
- **后续迭代**：P3移植EncodingDetect

### 风险6：并发调试冲突
- **已知限制**：多个debug-source.py同时运行可能冲突
- **后续迭代**：P3增加端口管理

### 风险7：降级写入污染skill文档（新增）
- **应对**：降级写入到独立目录references/troubleshooting/auto/
- **标记**：添加`<!-- AUTO_GENERATED -->`标记，便于后续清理
- **质量控制**：不与6.2任务（添加编号标记）冲突

### 风险8：--timeout与JVM进程管理交互（新增）
- **应对**：先发shutdown命令，等待3秒，再强制destroy
- **端口检查**：超时后检查端口是否释放

### 风险9：大HTML性能影响（新增）
- **应对**：限制HTML分析只在规则不匹配时触发
- **截断**：大HTML截断前100KB

### 风险10：经验写入格式未定义（新增）
- **应对**：定义固定Markdown模板（错误类型/修复方案/测试结果/源URL/日期）

### 风险11：Cookie跨阶段持久化（新增）
- **应对**：验证baseUrl修复后Cookie跨阶段传递是否正确

### 风险12：真机Debug.kt对比分析缺失（新增）
- **应对**：本次记录为已知限制，后续迭代补充真机Debug.kt对比分析
