# JVM 测试基础设施详情

> 本文档从 SKILL.md 拆分，包含 JVM 仿真器的完整架构说明、API 速查、使用示例和降级路径。

---

## 核心问题

纯 Python 模拟覆盖率仅 35-40%，JS 规则验证 0%。JVM 仿真器将覆盖率提升到 85-90%。

---

## MVP 增量架构

| MVP | 能力 | 覆盖率 | JAR 文件 |
|-----|------|--------|----------|
| MVP1 | Rhino桥接 + JsExtensionsStub（ajax/put/get/base64/createSymmetricCrypto/md5Encode + log/webView(stub)/getWebViewUA/ajaxAll/hexDecode/encodeURI/cookie/hexDecodeToByteArray/decodeURI/getCache/startBrowserAwait(stub,抛异常)/connect(stub,抛异常)等辅助函数） | 55-65% | `legado-jvm/build/libs/legado-jvm.jar` |
| MVP2 | + jsoup CSS选择器验证（标准CSS，不含自定义索引语法） | 65-75% | `legado-jvm/build/libs/legado-jvm.jar` |
| MVP3 | + hutool加密验证（AES-CBC/ECB等） | 70-80% | `legado-jvm/build/libs/legado-jvm.jar` |
| legado-jvm | + 完整AnalyzeRule适配（自定义索引语法+&&/||/%%组合逻辑） | 85-90% | `legado-jvm/build/libs/legado-jvm.jar` |

**环境要求**：JDK 17+（`java -version` 验证）

**版本锁定**（不可升级，破坏性变更）：

| 库 | 版本 | 锁定原因 |
|----|------|---------|
| jsoup | 1.16.2 | 破坏性变更 jsoup#2017 |
| rhino | 1.8.1 | Android 6 以下缺少 Arrays.setAll |
| hutool | 5.8.22 | 书源加解密依赖 |
| okhttp | 5.3.2 | 网络请求引擎 |
| gson | 2.13.2 | JSON 序列化 |

---

## 架构说明

```
Python 编排层（debug-source.py / 固化脚本）
    ↓ subprocess 启动
RuleEngineServer（常驻JVM进程）
    ↓ stdin/stdout JSON 通信（流式协议：type=log/error/result）
    ↓ 支持命令：ping / evalJS / evalCSS / decrypt / encrypt / analyzeRule(legado-jvm) / analyzeElements(legado-jvm) / analyzeUrl / debugBookSource / debugRssSource / shutdown
    ↓ 模块检测：启动时输出可用模块列表
```

**端到端调试架构**（新增）：

```
debug-source.py（Python 编排层）
    ↓ RuleEngineClient.debug_book_source() / debug_rss_source()
    ↓ 流式 JSON 行协议（stdin 发送命令，stdout 逐行返回 log/error/result）
RuleEngineServer
    ↓ handleDebugBookSource / handleDebugRssSource
    ↓ 创建 BookSourceDebugger / RssSourceDebugger
BookSourceDebugger（端到端书源调试器）
    ├─ AnalyzeUrl（URL 解析三步流水线：analyzeJs → replaceKeyPageJs → analyzeUrl）
    │   ├─ MockCookieStore（二级域名 Cookie 存储，跨阶段持久化）
    │   ├─ MockCacheManager（内存缓存）
    │   └─ OkHttp 同步请求（GET/POST/HEAD，错误码 -1 到 -7）
    ├─ AnalyzeRule（规则解析，6 种模式 + 13 变量注入 + NativeObject 处理）
    │   └─ 变量层级存储（chapter → book → source，与真机一致）
    ├─ JsExtensionsStub（JS 扩展函数 50+，ajax/connect/加密等）
    ├─ 抽取后的 BookSource/RssSource / MockBook（内存版上下文）
    └─ DebugLogger（真机级日志输出，`[mm:ss.SSS] ︾︽⇒┌└≡◇` + state 状态码）
```

---

## Python 客户端

`tools/rule_engine_client.py`（RuleEngineClient 类）
- JDK 自动检测（JAVA_HOME → PATH）
- JAR 路径搜索（legado-jvm）
- 模块检测：启动时获取可用 MVP 模块
- 降级逻辑：JVM 不可用时自动降级到 Python 仿真

**共享工具模块**：`tools/jvm_helpers.py`
- `add_jvm_args(parser)` — 为 argparse 添加 --jvm 和 --jar-path 参数
- `init_jvm_client(jar_path)` — 统一 JVM 初始化+降级处理
- `assess_confidence(rule_type, jvm_available, rule_content)` — 可信度评估

---

## RuleEngineClient API 速查

（AI agent 可直接在 Python 中调用）

| 方法 | 用途 | 关键参数 |
|------|------|---------|
| `eval_js(code, context="")` | 执行 JS 代码 | code=JS代码字符串, context=上下文变量(JSON字符串，注入到JS执行环境) |
| `eval_css(html, selector)` | CSS 选择器查询 | html=HTML字符串, selector=CSS选择器 |
| `analyze_rule(content, rule, base_url="")` | 完整规则解析（legado-jvm） | content=HTML/JSON, rule=Legado规则（支持自定义索引+组合逻辑）, base_url=基础URL（用于相对链接解析） |
| `analyze_elements(content, rule, base_url="")` | 获取元素列表（legado-jvm） | 同上，返回元素详情（text/html/attributes）, base_url=基础URL |
| `decrypt(algo, key, data, iv, key_encoding="utf-8", iv_encoding="utf-8", data_encoding="base64")` | hutool 解密 | algo="AES/CBC/PKCS5Padding", data默认base64, key_encoding=密钥编码, iv_encoding=IV编码, data_encoding=数据编码 |
| `encrypt(algo, key, data, iv, key_encoding="utf-8", iv_encoding="utf-8", data_encoding="utf-8")` | hutool 加密 | 同上, data_encoding默认utf-8(加密输入) |
| `analyze_url(url, key=None, page=None, source_json=None, base_url="")` | URL 解析（AnalyzeUrl 移植版） | url=URL规则字符串, key=搜索关键词, page=页码, source_json=BookSource JSON, base_url=基础URL。返回 url/method/headerMap/responseUrl/responseCode/responseBody/callTime |
| `debug_book_source(source_json, key, on_log=None, on_error=None, on_result=None)` | 书源端到端调试（流式） | source_json=BookSource JSON, key=搜索词或阶段标识（`http://`详情/`++`目录/`--`正文）, on_log/on_error/on_result=回调函数。调试链路: search→detail→toc→content |
| `debug_rss_source(source_json, key, on_log=None, on_error=None, on_result=None)` | 订阅源端到端调试（流式） | source_json=RssSource JSON, key=搜索词或URL, on_log/on_error/on_result=回调函数。调试链路: sort→content |
| `ping()` | 检查服务器存活 | 无 |
| `shutdown()` | 关闭服务器 | 无（内部管理命令） |

---

## 使用示例

```python
# 注意：路径相对于 skill 根目录（.trae/skills/legado-source-creator/）
import sys, os
skill_dir = os.path.dirname(os.path.abspath(__file__))  # 或手动指定 skill 根目录
sys.path.insert(0, os.path.join(skill_dir, "tools"))
from rule_engine_client import RuleEngineClient
with RuleEngineClient() as client:
    result = client.analyze_rule(html, "tag.div.0@text")  # legado-jvm 完整规则解析
    result = client.eval_css(html, "div.article p")       # CSS 选择器
    result = client.decrypt("AES/CBC/PKCS5Padding", key, data, iv)  # 解密

    # 端到端书源调试（流式日志）
    def on_log(state, msg, html):
        print(f"[{state}] {msg}")
    def on_error(msg, stack_trace, failed_stage):
        print(f"ERROR: {failed_stage} - {msg}")
    def on_result(success, summary):
        print(f"{'✅' if success else '❌'} {summary}")

    result = client.debug_book_source(
        source_json=book_source_json_str,
        key="斗破苍穹",
        on_log=on_log, on_error=on_error, on_result=on_result
    )

    # 端到端订阅源调试
    result = client.debug_rss_source(
        source_json=rss_source_json_str,
        key="",  # 订阅源通常不需要搜索词
        on_log=on_log, on_error=on_error, on_result=on_result
    )
```

---

## JsExtensionsStub ajax() 差异

> 详见 `tools/ajax-diff-analysis.md`

| 行为 | Legado ajax() | JsExtensionsStub | 影响 |
|------|-------------|-----------------|------|
| Cookie自动携带 | CookieStore自动携带 | OkHttp默认不携带 | **高**——登录后请求可能失败 |
| Header自动携带 | source.header自动携带 | 不携带 | **高**——需Header的请求可能失败 |
| 编码 | 根据charset参数 | OkHttp默认UTF-8 | 中——GBK站可能乱码 |

---

## 可信度标注规则

（由 `_assess_confidence()` 自动判断）

**evalJS 场景**：

| 规则特征 | 可信度 | 理由 |
|---------|--------|------|
| 不含 ajax/ES6 的纯逻辑 JS | 高 | 不依赖网络请求差异 |
| 含 ES6 语法（let/const/=>/模板字符串） | 低 | Legado 真机不支持 ES6，Rhino 1.8.1 仅支持 ES5 |
| 含 java.ajax() 但不含 Cookie/Header 依赖 | 中 | ajax() 基本行为一致，但编码可能有差异 |
| 含 java.ajax() 且依赖 Cookie/Header | 低 | Cookie/Header 不自动携带 |
| 含 java.webView() | 不可验证 | 无法模拟 WebView |

**analyzeRule 场景**（legado-jvm AnalyzeRule 完整规则解析）：

| 规则特征 | 可信度 | 理由 |
|---------|--------|------|
| 纯 CSS/XPath/JSONPath/Default+Combo | 高 | JVM 中通过 JsoupXpath/JSON/AnalyzeByJSoup 验证 |
| 含 `<js>` 或 `@js:` 标签 | 中 | JS 部分依赖 JsExtensionsStub，行为可能与真机不同 |
| 含 webView/webJs | 不可验证 | 无法模拟 WebView |

---

## 降级路径

```
JVM 可用（JDK 17+）→ 使用 RuleEngineServer（legado-jvm）
    ↓ 端到端调试可用：debug-source.py（首选，真机级日志）
    ↓ 单项验证可用：verify-selector.py / verify-decrypt.py / verify-image.py
    ↓ JDK 不可用 / JAR 启动失败
Python 仿真（verify-source.py 仍可运行，但无 JS 规则验证能力）
    ↓ 覆盖率仅 35-40%，JS 规则 0%
所有 JS 规则标记为"未验证"，提示用户需真机测试
    ↓ 端到端调试不可用时
降级到 verify-source.py（源完整性验证）+ 手动 curl 验证
```

**端到端调试降级**：
- JVM 可用 → `debug-source.py`（首选，4 阶段真机级日志）
- JVM 不可用 → `verify-source.py`（仅源完整性，无链路验证）+ 手动 curl 验证关键页面
- 网站不可访问 → 标记"需真机验证"，提示用户在 Legado App 中导入测试
