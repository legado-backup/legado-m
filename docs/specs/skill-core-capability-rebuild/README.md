# Skill 核心能力重建：Python 客户端工程化 + JAR 仿真服务端保真度提升

> **状态**：🔄 设计中
> **前置项目**：[source-repair-loop-optimization](../source-repair-loop-optimization/)（已完成，但存在孤儿模块问题）
> **创建日期**：2026-06-20
> **分析方法**：基于 4 个子代理深度分析（书源管理源码 / 订阅源+规则引擎源码 / JAR 仿真服务端真实状态 / Python 客户端+设计文档孤儿模块问题）

---

## 核心理念（用户原话）

> **经验知识是你的理解大脑，python 客户端是你的测试双手，jar 仿真服务端是你的核心能力底座，开源阅读源码是你最最最后的兜底保障**

### 四层架构理念

| 层级 | 比喻 | 对应开源阅读组件 | 当前状态 | 目标状态 |
|------|------|----------------|---------|---------|
| **经验知识层** | 理解大脑 | references/ + basic-memory | 有基础但未闭环 | 自动检索/写入/冲突解决 |
| **Python 客户端层** | 测试双手 | 开源阅读 Android 客户端 | 无工程化（1236 行上帝脚本） | 工程化包结构+虚拟环境+层级设计 |
| **JAR 仿真服务端层** | 核心能力底座 | 开源阅读核心服务（WebBook/Rss/Debug/CheckSource） | 89% 保真度+4 大卡顿根因 | 95%+ 保真度+异步高性能 |
| **开源阅读源码层** | 最后兜底 | app/src/main/java/io/legado/app/ | 作为参考源 | 仅在 JAR 无法覆盖时回查 |

### 终极目标

> **我期望的是最终你完全可以进化到脱离分析源码就能够通过当前 skill 中的 python 客户端和 jar 仿真服务端就能够完成整个书源订阅源的开发和优化**

落地原则：
- JAR 仿真服务端实现开源阅读核心服务功能（书源管理/订阅源管理/搜索发现/调试/校验）
- Python 客户端实现开源阅读客户端功能（调用 JAR + WebView 渲染 + 用户交互）
- 经验知识层实现自动检索/写入/冲突解决
- 开源阅读源码仅作为 JAR 无法覆盖场景的最后回查参考

---

## 功能概述

基于 4 个子代理的深度分析，发现当前 skill 存在 **7 大类核心问题**：

| 问题类别 | 问题数 | 核心问题 | 影响 |
|---------|--------|---------|------|
| **JAR 卡顿根因** | 4 个 | 同步 execute+JS 编译开销+Stub 每次创建+无连接池（原 6 个，经核实删除 2 个伪问题） | 命令响应卡特别长时间 |
| **JAR 保真度不足** | 38 个 | 86 完整/38 Stub/8 不可用；ajax 走 Jsoup；evalJS source=null, baseUrl="" | 仿真结果与真机不一致 |
| **Python 客户端无工程化** | 8 个 | 无虚拟环境+无包结构+1236 行上帝脚本+12 处 json.loads+无类型注解 | 不可维护不可扩展 |
| **4 个孤儿模块** | 4 个 | confidence_evaluator/user_interaction_handler/source_navigation/parse_strategy_selector 代码完整但未被 import | 虚假完成 |
| **JAR 核心功能缺失** | 2 个 | 无 CheckSource 校验流程（原 5 个，经核实删除 3 个已修复问题 + state码语义对齐已核实为伪问题） | 无法脱离源码独立工作 |
| **经验知识未闭环** | 4 个 | basic-memory 未集成+无自动检索+无自动写入+无冲突解决 | 违反 AGENTS.md 强制规则 |
| **设计文档与代码不一致** | 6 项 | 标记完成但实际未实现+mock 数字过时+MVP 命名混乱+版本锁不一致 | 误导实施 |

本项目从 **7 个方向** 系统性重建 skill 核心能力，目标是让 AI 脱离源码分析就能完成书源/订阅源开发和优化。

---

## 统一设计理念

### 理念 1：JAR=核心服务，Python=客户端（核心理念）

JAR 仿真服务端必须实现开源阅读核心服务功能，Python 客户端必须实现开源阅读客户端功能。两者协作完成书源/订阅源的全流程管理。

**落地原则**：
- JAR 实现：WebBook（书源管理）+ Rss（订阅源管理）+ Debug（调试）+ CheckSource（校验）
- Python 实现：调用 JAR + WebView 渲染 + 用户交互 + 经验管理 + 报告生成
- 通信协议：stdin/stdout JSON 行协议（保持现有）
- **禁止 Python 重复实现 JAR 已有能力**（如规则解析、JS 执行）

### 理念 2：异步高性能（解决卡顿根因）

JAR 仿真服务端必须从"同步阻塞"进化为"异步高性能"，解决 4 大卡顿根因（原 6 大，经源码核实删除 2 个伪问题）。

**落地原则**（基于源码核实，2026-06-20）：
- 同步 execute → 异步 enqueue + suspendCancellableCoroutine
- JS 编译缓存优化（AnalyzeRule.kt:862，scriptCache 上限从 16 提升到 64，真机也是16，提升到64是优化）
- JsExtensionsStub 单例化（class→object，仿真器中由 AnalyzeRule/AnalyzeUrl 内部创建；真机中 AnalyzeRule/AnalyzeUrl 直接 implements JsExtensions，无 Stub 层）
- OkHttp 连接池复用（5 个连接保持活跃）

**已核实不存在的伪问题**（设计文档原描述错误，已删除）：
- ~~runBlocking 阻塞~~：BookSourceDebugger.kt/RssSourceDebugger.kt 实际无 runBlocking
- ~~30 秒 OkHttp 超时~~：OkHttpUtils.kt 无超时配置，30 秒在 JsExtensionsStub.ajax 中

### 理念 3：保真度优先（补全 38 个 Stub）

JAR 仿真服务端保真度从 89% 提升到 95%+，补全 38 个 Stub 方法。

**落地原则**（基于源码核实，2026-06-20）：
- 优先补全高频方法（ajax/connect/get/post/base64Decode/Encode/strToBytes/bytesToStr/getCookie/cacheFile/importScript/queryTTF/replaceFont）
- 修复 ajax 委托走 Jsoup.connect
- 修复 evalJS 上下文注入不完整（source=null, baseUrl=""）
- 修复 CacheManagerStub 无 LRU（添加软引用）
- 补全 base64Decode flags 支持

**已核实不存在的伪问题**（设计文档原描述错误，已删除）：
- ~~getSubDomain 不剥离 www~~：NetworkUtilsStub.kt:192 已剥离 www 前缀
- ~~TextUtils.isEmpty 替换为 isNullOrBlank~~：AnalyzeRule.kt 已使用 isNullOrEmpty

### 理念 4：Python 客户端工程化

Python 客户端从"1236 行上帝脚本"进化为"工程化包结构"。

**落地原则**：
- 虚拟环境管理：requirements.txt + venv 激活脚本
- 包结构：legado_client/ 包 + __init__.py + 模块化
- 层级设计：客户端层 / 分析层 / 经验层 / 工具层
- 类型注解：全量 type hints
- 拆分 debug-source.py：1236 行 → 多个模块（每个 < 300 行）

### 理念 5：孤儿模块真正集成

4 个代码完整但未被 import 的"孤儿模块"必须真正集成到 debug-source.py。

**落地原则**（基于源码核实，2026-06-20）：
- confidence_evaluator.py（112行）：完整实现可信度评分逻辑，只需 import+调用
- user_interaction_handler.py（140行）：完整实现 4 种错误场景处理+自检代码，只需 import+调用
- source_navigation.py（84行）：完整实现错误→源码映射+自检代码，只需 import+调用
- parse_strategy_selector.py（131行）：完整实现解析策略选择+自检代码，只需 import+调用
- **核实结论**：这 4 个脚本不是"空架子"（有完整实现），而是"孤儿模块"（代码完整但未被任何代码 import）

### 理念 6：经验知识闭环

经验知识层必须实现自动检索/写入/冲突解决，违反 AGENTS.md 强制规则的问题必须修复。

**落地原则**：
- 测试前自动检索相似案例（basic-memory 不可用时降级 pathlib.Path.rglob）
- 测试后自动写入新经验（输出 pending JSON，AI agent 外层 MCP 写入）
- 经验去重+质量评估（避免低质量经验污染）
- 经验冲突解决（置信度评分+时效性+优先级规则）

### 理念 7：禁止懒原则（用户强制要求）

> **禁止懒原则，我需要你深度分析全面审查当前设计文档是否全部已经优化完成！因为我明确看到你在实施过程中大量通过懒原则简化设计文档中的任务，让其看起来都是完成了，但是其实全是空架子！**

**落地原则**：
- 所有任务必须真正实现，禁止 YAGNI 跳过核心功能
- 每个任务必须有源码行号引用+验证方法
- 验收标准必须可执行（非"已实现"描述性验收）
- 修复 6 项"已完成但实际未实现"的虚假完成项

---

## 架构理念

### 分层解耦

```
┌──────────────────────────────────────────────────────────────────────┐
│                    经验知识层（理解大脑）                                │
│  references/ + basic-memory + experience_manager.py                    │
│  自动检索 → 自动写入 → 冲突解决 → 质量评估                               │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕
┌──────────────────────────────────────────────────────────────────────┐
│                    Python 客户端层（测试双手）                            │
│  legado_client/ 包结构                                                  │
│  ├── client/    （RuleEngineClient + WebViewHandler + UserInteraction） │
│  ├── analyzer/  （ErrorDiagnoser + HtmlStructureAnalyzer + Confidence）  │
│  ├── experience/（ExperienceManager + ConflictResolver）                │
│  └── utils/     （Config + Logger + FileUtils）                          │
│  debug-source.py（入口脚本，< 200 行）                                    │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕ stdin/stdout JSON
┌──────────────────────────────────────────────────────────────────────┐
│                    JAR 仿真服务端层（核心能力底座）                        │
│  legado-jvm.jar（单 JAR，非 4 个）                                       │
│  ├── RuleEngineServer（通信协议+命令分发）                                │
│  ├── WebBookDebugger（书源管理：搜索/发现/详情/目录/正文）                  │
│  ├── RssSourceDebugger（订阅源管理：列表/内容/singleUrl）                  │
│  ├── CheckSource（校验：域名→搜索→发现→详情→目录→正文）                    │
│  ├── AnalyzeUrl + AnalyzeRule（规则引擎核心）                             │
│  ├── JsExtensionsStub（JS 扩展函数，86 完整+38 补全）                      │
│  └── CacheManager + CookieStore + NetworkUtils（基础设施）               │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕ 仅在 JAR 无法覆盖时回查
┌──────────────────────────────────────────────────────────────────────┐
│                    开源阅读源码层（最后兜底保障）                           │
│  app/src/main/java/io/legado/app/                                       │
│  WebBook.kt + Rss.kt + Debug.kt + CheckSource.kt + JsExtensions.kt     │
└──────────────────────────────────────────────────────────────────────┘
```

### 渐进增强

| 优先级 | 方向 | 内容 |
|--------|------|------|
| P0 | JAR 架构重构 | 同步 execute→异步 enqueue + JS 编译缓存 + Stub 单例 + 连接池（原 6 大根因，经核实删除 2 个伪问题） |
| P0 | JAR 保真度提升 | 补全 38 个 Stub + 修复 ajax 委托 + 修复 evalJS 上下文 + 修复 CacheManagerStub LRU（原含 getSubDomain 和 TextUtils，经核实已修复） |
| P0 | Python 工程化 | 虚拟环境 + 包结构 + 层级设计 + 拆分上帝脚本 + 类型注解 |
| P0 | 孤儿模块真正集成 | 4 个脚本真正 import + 调用（代码已完整，只需集成） |
| P1 | JAR 核心功能完善 | CheckSource 校验（原 5 个，经核实删除 3 个已修复问题 + state码语义对齐已核实为伪问题） |
| P1 | 经验知识闭环 | basic-memory 集成 + 自动检索/写入 + 冲突解决 |
| P1 | 设计文档一致性 | 修复 6 项虚假完成 + 修复 mock 数字 + 修复 MVP 命名 + 修复版本锁 |

### 降级路径明确

| 层级 | 正常路径 | 降级路径 | 降级标记 |
|------|---------|---------|---------|
| JAR 仿真器 | legado-jvm.jar | verify-source.py（覆盖率 35-40%） | 输出"⚠️ JVM 不可用，降级到 Python 仿真" |
| basic-memory | AI agent 通过 MCP 搜索 | experience_manager.py 用 pathlib.Path.rglob 搜索 references/troubleshooting/ | 输出"⚠️ basic-memory 不可用，降级到 Python 原生文件搜索" |
| basic-memory 写入 | AI agent 通过 MCP 写入 | 写入 references/troubleshooting/auto/ | 添加 <!-- AUTO_GENERATED --> 标记 |
| WebView | Selenium 委托 | 标记 needsWebView + 用户介入 | 输出"⚠️ 需要 WebView 渲染，标记用户介入" |
| 开源阅读源码 | JAR 仿真覆盖 | 回查 app/src/main/java/ | 输出"⚠️ JAR 无法覆盖，回查开源阅读源码" |

---

## 源码分析方法论

> 本设计文档的所有结论均基于 4 个子代理的深度分析，非拍脑袋。

### 分析覆盖范围

| 子代理 | 分析范围 | 文件数 | 核心发现 |
|--------|---------|--------|---------|
| 子代理 1（书源管理） | WebBook/BookList/BookInfo/BookChapterList/BookContent/Debug.kt | 12 个 | WebBook 核心解析逻辑 90% 可移植，主要 Android 依赖是 appCtx/R.string/AppConfig/appDb |
| 子代理 2（订阅源+规则引擎） | Rss/RssParserByRule/AnalyzeRule/AnalyzeUrl/JsExtensions/CheckSource | 12 个 | 规则引擎 6 个解析器（CSS/XPath/JSONPath/Regex/JS/WebJs）可几乎无损移植，AnalyzeUrl 是最大移植风险 |
| 子代理 3（JAR 仿真服务端） | RuleEngineServer/BookSourceDebugger/RssSourceDebugger/JsExtensionsStub/CacheManagerStub/OkHttpUtils | 12 个 | 只有 1 个 JAR（非 4 个），同步 execute 是最大卡顿瓶颈（原分析含 runBlocking 伪问题，经核实已删除） |
| 子代理 4（Python 客户端+设计文档） | debug-source.py/confidence_evaluator/user_interaction_handler/source_navigation/parse_strategy_selector/4 个设计文档 | 10 个 | 4 个孤儿模块（代码完整但未被 import）+6 项虚假完成+Python 完全无工程化 |

### 分析方法

1. **源码深度阅读**：逐行阅读开源阅读源码，记录关键逻辑和行号
2. **真机对比**：仿真器源码 vs 真机源码逐方法对比，记录行为差异
3. **运行时验证**：通过 JAR 启动+命令响应验证卡顿根因
4. **交叉验证**：设计文档 vs 实际代码交叉验证，发现孤儿模块问题

---

## 仿真保真度限制清单

> 通过真机 vs 仿真器对比发现。这些限制影响仿真结果的准确性，本次设计将系统性修复。

### 当前保真度：~89%（86 完整 / 38 Stub / 8 不可用）

> **已删除伪问题**：~~getSubDomain 不剥离 www~~（NetworkUtilsStub.kt:192 已剥离 www 前缀）、~~TextUtils.isEmpty 替换为 isNullOrBlank~~（AnalyzeRule.kt 已使用 isNullOrEmpty）

| 严重度 | 限制 | 真机行为 | 仿真器行为 | 影响 | 修复方向 |
|--------|------|---------|-----------|------|---------|
| CRITICAL | evalJS 上下文注入 | 注入 java/source/baseUrl/cookie/cache（source 非空） | 已注入 java/cookie/cache/baseUrl，但 source=null, baseUrl="" | JS 无法调用 java.ajax | 方向 2.1 |
| CRITICAL | ajax 委托 | 走 AnalyzeUrl 自身 | 走 JsExtensionsStub.ajax（Jsoup.connect） | AnalyzeUrl.evalJS 中的 ajax 请求能力降级 | 方向 2.2 |
| HIGH | aesEncodeToString | 调用 decryptStr（真机 bug） | 调用 encrypt（修复了 bug） | 加密结果不一致 | 方向 2.3 |
| HIGH | HTTP 方法缺失 | cookieJarHeader/限流/SSL/ensureActive/AnalyzeUrl | 全部走 Jsoup.connect | 复杂请求场景失败 | 方向 2.4 |
| HIGH | BaseSource 方法缺失 | 继承 JsExtensions+JsEncodeUtils 约 150+ 方法 | 仅 7 属性+3 方法 | source.login/evalJS 无法调用 | 方向 2.5 |
| MEDIUM | base64Decode flags | 支持 URL_SAFE/CRLF/NO_PADDING/NO_WRAP | 仅处理 flag 8 | 其他 flags 解码失败 | 方向 2.6 |
| MEDIUM | CacheManagerStub 无 LRU | LruCache(50M) | 无限 ConcurrentHashMap（已是 object 单例） | 长时间运行 OOM | 方向 2.7 |
| MEDIUM | androidId 固定值 | 从 AppConst.androidId 读取 | 返回"000000000000000" | getLoginInfo AES 加密 key 不同 | 方向 2.8 |

### 目标保真度：95%+（补全 38 个 Stub 中的高频方法）

---

## 核心能力

| 能力 | 当前状态 | 源码依据 | 目标状态 |
|------|---------|---------|---------|
| JAR 异步高性能 | ❌ 同步 execute 阻塞 | OkHttpUtils.kt:52 | ✅ 异步 enqueue + suspendCancellableCoroutine |
| JAR 保真度 95%+ | ❌ 89%（38 Stub） | JsExtensionsStub.kt | ✅ 95%+（补全高频 Stub） |
| Python 工程化 | ❌ 1236 行上帝脚本 | debug-source.py | ✅ 包结构+虚拟环境+层级设计 |
| 孤儿模块真正集成 | ❌ 4 个未 import | confidence_evaluator.py 等 | ✅ 真正 import+调用 |
| JAR CheckSource 校验 | ❌ 无 | CheckSource.kt（74行） | ✅ 域名→搜索→发现→详情→目录→正文 |
| ~~state 码语义对齐~~ | ~~❌ 10/20/30/40 语义~~ | ~~Debug.kt（382行，只用1/-1/1000）~~ | **✅ 已核实：伪问题，真机也用10/20/30/40（BookList/BookInfo/BookChapterList/BookContent）** |
| 经验知识闭环 | ❌ 未集成 | experience_manager.py | ✅ 自动检索/写入/冲突解决 |
| 设计文档一致性 | ❌ 6 项虚假完成 | tasks.md | ✅ 修复所有虚假完成项 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios（7 个方向） |
| [design.md](./design.md) | 技术方案：7 个方向 + 7 个统一设计理念 + 架构决策 + JAR 卡顿 6 大根因解决方案 + 38 个 Stub 补全方案 + Python 工程化方案 |
| [tasks.md](./tasks.md) | 任务清单（7 个方向，100+ 个任务，每个有源码行号引用，禁止懒原则） |

---

## 验收标准

### P0 验收（JAR 架构重构 + 保真度提升 + Python 工程化 + 孤儿模块集成）

1. **JAR 异步高性能**：单源调试响应时间 < 10 秒（当前 30 秒+）
2. **JAR 保真度 95%+**：38 个 Stub 中高频方法全部补全
3. **Python 工程化**：包结构+虚拟环境+层级设计+类型注解
4. **孤儿模块真正集成**：4 个脚本真正 import+调用
5. **evalJS 上下文注入**：注入真实 source 和 baseUrl（非 null 和非空）
6. **ajax 委托修复**：走 AnalyzeUrl 而非 Jsoup.connect
7. **CacheManagerStub LRU**：添加软引用，长时间运行不 OOM
8. **JSON 去重**：12 处 → 1 处

### P1 验收（JAR 核心功能完善 + 经验知识闭环 + 设计文档一致性）

9. **CheckSource 校验**：域名→搜索→发现→详情→目录→正文全流程
10. **~~state 码语义对齐~~**：**已核实伪问题**，真机 Debug.kt 也使用 10/20/30/40（在 BookList.kt:54/BookInfo.kt:40/BookChapterList.kt:49/BookContent.kt:52 中），仿真端已与真机一致
11. **经验自动检索**：experience_manager.py 用 pathlib.Path.rglob 搜索（≤2 秒响应）
12. **经验自动写入**：测试通过后输出到 output/experience-pending.json
13. **设计文档一致性**：6 项虚假完成项全部修复
14. **mock 数字更新**：与 JsExtensionsStub.kt 实际代码同步（132个方法）
15. **MVP 命名统一**：删除 MVP1-4 决策树，统一为 legado-jvm
16. **版本锁同步**：jvm-infrastructure.md 与 build.gradle.kts 版本号一致
