# Spec: Skill 核心能力重建

## Intent

基于 4 个子代理对开源阅读源码、JAR 仿真服务端、Python 客户端、设计文档的深度分析，发现当前 skill 存在 7 大类核心问题：JAR 卡顿根因（4 个，经源码核实删除 2 个伪问题）、JAR 保真度不足（38 个 Stub）、Python 客户端无工程化（8 个）、4 个孤儿模块（代码完整但未被 import）、JAR 核心功能缺失（2 个，经源码核实删除 3 个已修复问题）、经验知识未闭环（4 个）、设计文档与代码不一致（6 项）。

核心目标：
1. **JAR=核心服务**：实现开源阅读核心服务功能（WebBook/Rss/Debug/CheckSource），保真度从 89% 提升到 95%+
2. **Python=客户端**：工程化重构，从 1236 行上帝脚本进化为包结构+虚拟环境+层级设计
3. **经验知识=大脑**：实现自动检索/写入/冲突解决，违反 AGENTS.md 强制规则的问题必须修复
4. **开源阅读源码=兜底**：仅在 JAR 无法覆盖时回查，目标是脱离源码独立工作

> **用户原话**：我期望的是最终你完全可以进化到脱离分析源码就能够通过当前 skill 中的 python 客户端和 jar 仿真服务端就能够完成整个书源订阅源的开发和优化

## Scope

### IN-SCOPE（7 个方向）

**方向 1：JAR 仿真服务端架构重构（P0）**

解决 4 大卡顿根因（原 6 大，经源码核实删除 2 个伪问题），让 JAR 从"同步阻塞"进化为"异步高性能"：

> **已删除伪问题**：~~runBlocking 阻塞~~（BookSourceDebugger.kt/RssSourceDebugger.kt 实际无 runBlocking）、~~30秒OkHttp超时~~（OkHttpUtils.kt 无超时配置，30秒在 JsExtensionsStub.ajax 中）

- **根因 1**：同步 execute 替代异步 enqueue（OkHttpUtils.kt:52）
  - 真机行为：OkHttp enqueue + 回调
  - 仿真器行为：OkHttp execute 同步阻塞
  - 修复：改为 enqueue + suspendCancellableCoroutine

- **根因 2**：JS 编译缓存上限 16（AnalyzeRule.kt:81/862 scriptCache）
  - 真机行为：scriptCache 上限 16（AnalyzeRule.kt:862 确认，真机也是16）
  - 仿真器行为：scriptCache 上限 16（与真机一致，但16偏小导致频繁编译）
  - 修复：提升到 64（优化提升，非对齐真机）

- **根因 3**：JsExtensionsStub 每次创建新实例（JsExtensionsStub.kt:48，仿真器中由 AnalyzeRule/AnalyzeUrl 内部创建；真机中 AnalyzeRule/AnalyzeUrl 直接 implements JsExtensions，无 Stub 层）
  - 真机行为：AnalyzeRule/AnalyzeUrl 直接 implements JsExtensions，无 Stub 层
  - 仿真器行为：JsExtensionsStub 是普通 class，每次 AnalyzeRule/AnalyzeUrl 初始化时创建新实例
  - 修复：单例化（class→object）

- **根因 4**：无 OkHttp 连接池复用
  - 真机行为：连接池保持 5 个连接
  - 仿真器行为：每次请求新建连接
  - 修复：配置连接池（5 个 keepAlive）

**方向 2：JAR 仿真服务端保真度提升（P0）**

补全 38 个 Stub 方法，保真度从 89% 提升到 95%+：

> **已删除伪问题**：~~getSubDomain 不剥离 www~~（NetworkUtilsStub.kt:192 已剥离 www 前缀）、~~TextUtils.isEmpty 替换为 isNullOrBlank~~（AnalyzeRule.kt 已使用 isNullOrEmpty）

- **2.1 evalJS 上下文注入修复**（RuleEngineServer.kt:134 方法定义，L137-145 上下文注入）
  - 真机：注入 java/source/baseUrl/cookie/cache（source 非空）
  - 仿真器：已注入 java/cookie/cache/baseUrl，但 source=null, baseUrl=""
  - 修复：传入真实 source 和 baseUrl

- **2.2 ajax 委托修复**（JsExtensionsStub.kt:64/67）
  - 真机：走 AnalyzeUrl 自身（支持 URL 模板/Cookie/请求体编码）
  - 仿真器：走 JsExtensionsStub.ajax（Jsoup.connect 简化请求）
  - 修复：AnalyzeUrl override ajax 方法

- **2.3 aesEncodeToString 评估**（JsExtensionsStub.kt:874）
  - 真机：调用 decryptStr（真机 bug）
  - 仿真器：调用 encrypt（修复了 bug）
  - 修复：评估影响并记录，保持与真机一致或记录为已知限制

- **2.4 HTTP 方法补全**（OkHttpUtils.kt）
  - 真机：cookieJarHeader/限流/SSL/ensureActive/AnalyzeUrl
  - 仿真器：全部走 Jsoup.connect
  - 修复：补全 HTTP 方法支持

- **2.5 BaseSource 方法补全**（BaseSource.kt，真机文件名非 BaseSourceInterface.kt）
  - 真机：`interface BaseSource : JsExtensions`（第33行），继承 JsExtensions+JsEncodeUtils 合计约 150+ 方法
  - 仿真器：仅 7 属性+3 方法
  - 修复：补全 source.login/evalJS 等高频方法

- **2.6 base64Decode flags 补全**（JsExtensionsStub.kt:512）
  - 真机：支持 URL_SAFE/CRLF/NO_PADDING/NO_WRAP
  - 仿真器：仅处理 flag 8
  - 修复：补全 flags 支持

- **2.7 CacheManagerStub LRU 修复**（CacheManagerStub.kt:18）
  - 真机：LruCache(50M)
  - 仿真器：无限 ConcurrentHashMap（已是 object 单例，只需添加 LRU）
  - 修复：添加软引用或手动清理

- **2.8 androidId 修复**（JsExtensionsStub.kt:748）
  - 真机：从 AppConst.androidId 读取
  - 仿真器：返回"000000000000000"
  - 修复：可配置的 androidId

- **2.9 高频 Stub 方法补全**（JsExtensionsStub.kt 38 个 Stub）
  - 优先补全：ajax/connect/get/post/base64Decode/Encode/strToBytes/bytesToStr/getCookie/cacheFile/importScript/queryTTF/replaceFont
  - 评估后补全：getGlideUrl/getMediaItem（图片/视频场景）

**方向 3：Python 客户端工程化重构（P0）**

从 1236 行上帝脚本进化为工程化包结构：

- **3.1 虚拟环境管理**
  - 创建 requirements.txt（声明所有依赖）
  - 创建 venv 激活脚本（Windows: activate.bat, Linux: activate.sh）
  - 创建 .gitignore（忽略 venv/）

- **3.2 包结构设计**
  ```
  .trae/skills/legado-source-creator/scripts/
  ├── legado_client/           # Python 包
  │   ├── __init__.py
  │   ├── client/              # 客户端层
  │   │   ├── __init__.py
  │   │   ├── rule_engine_client.py    # JAR 通信客户端
  │   │   ├── webview_handler.py       # WebView 渲染
  │   │   └── user_interaction.py      # 用户交互
  │   ├── analyzer/             # 分析层
  │   │   ├── __init__.py
  │   │   ├── error_diagnoser.py       # 错误诊断
  │   │   ├── html_structure.py        # HTML 结构分析
  │   │   ├── confidence_evaluator.py  # 可信度评估
  │   │   └── parse_strategy.py        # 解析策略选择
  │   ├── experience/           # 经验层
  │   │   ├── __init__.py
  │   │   ├── experience_manager.py    # 经验管理
  │   │   └── conflict_resolver.py     # 冲突解决
  │   └── utils/                # 工具层
  │       ├── __init__.py
  │       ├── config.py                # 配置管理
  │       ├── logger.py                # 日志
  │       └── file_utils.py            # 文件工具
  ├── debug-source.py          # 入口脚本（< 200 行）
  ├── requirements.txt
  └── setup_venv.bat           # 虚拟环境激活脚本
  ```

- **3.3 拆分 debug-source.py**
  - 当前：1236 行上帝脚本，17 个 try/except ImportError 块，12 处 json.loads（已核实）
  - 目标：入口脚本 < 200 行，逻辑分散到 legado_client/ 包
  - 拆分原则：
    - debug-source.py：仅处理命令行参数解析+调用 legado_client
    - client/rule_engine_client.py：JAR 通信逻辑
    - analyzer/error_diagnoser.py：错误诊断逻辑
    - analyzer/html_structure.py：HTML 结构分析逻辑
    - experience/experience_manager.py：经验管理逻辑

- **3.4 类型注解**
  - 全量 type hints（Python 3.8+）
  - 使用 typing 模块（Optional, List, Dict, Any）
  - mypy 可选检查

- **3.5 JSON 去重**
  - 当前：12 处 json.loads(source_json) 重复解析（已核实）
  - 修复：main() 入口解析一次 source_obj，后续传递对象

**方向 4：4 个孤儿模块真正集成（P0）**

修复 4 个代码完整但未被 import 的"孤儿模块"（非"空架子"）：

> **核实结论**：这 4 个脚本不是"空架子"（有完整实现），而是"孤儿模块"（代码完整但未被任何代码 import）

- **4.1 confidence_evaluator.py 集成**
  - 当前状态：112行，完整实现可信度评分逻辑，但未被 debug-source.py import
  - 集成：在 debug-source.py 中 import 并调用

- **4.2 user_interaction_handler.py 集成**
  - 当前状态：140行，完整实现 4 种错误场景处理+自检代码，但未被 debug-source.py import
  - 集成：在 debug-source.py 中 import 并调用

- **4.3 source_navigation.py 集成**
  - 当前状态：84行，完整实现错误→源码映射+自检代码，但未被 debug-source.py import
  - 集成：在 debug-source.py 中 import 并调用

- **4.4 parse_strategy_selector.py 集成**
  - 当前状态：131行，完整实现解析策略选择+自检代码，但未被 debug-source.py import
  - 集成：在 debug-source.py 中 import 并调用

**方向 5：JAR 仿真服务端核心功能完善（P1）**

实现开源阅读核心服务功能，让 JAR 能脱离源码独立工作：

> **已删除伪问题**：~~state码未实现~~（已实现10/20/30/40）、~~singleUrl有bug~~（已修复）、~~baseUrl未传~~（已传）、~~相对路径未拼接~~（toAbsoluteUrl已调用）、~~HtmlStructureAnalyzer未集成~~（已集成）

- **5.1 CheckSource 校验流程**
  - 真机源码：CheckSource.kt（74行，已核实，配置管理入口，实际校验逻辑在 CheckSourceService 中）
  - 仿真器：无 CheckSource 对应实现，不支持批量校验和配置管理
  - 修复：新增 CheckSourceDebugger.kt，实现校验流程
  - 通过 addGroup/removeGroup 标记失效分组

- **5.2 state 码语义对齐**（已核实：伪问题，无需修改）
  - 真机源码：Debug.kt（382行）实际有 **7 个 state 码**（非 3 个）：1（默认）、-1（错误）、1000（完成）、10（列表页HTML，BookList.kt:54）、20（详情页HTML，BookInfo.kt:40）、30（目录页HTML，BookChapterList.kt:49）、40（正文页HTML，BookContent.kt:52）
  - 仿真器：已实现 state 码（BookSourceDebugger.kt:140/239/360/465），使用 10/20/30/40 **与真机一致**
  - ~~修复：统一为真机 state 码语义~~ **无需修复，仿真端已与真机一致**

**方向 6：经验知识体系完善（P1）**

实现经验知识自动检索/写入/冲突解决：

- **6.1 basic-memory 集成**
  - 当前：完全未集成，违反 AGENTS.md 强制规则
  - 修复：experience_manager.py 输出经验数据到 JSON 文件，AI agent 外层通过 MCP 写入
  - 降级：basic-memory 不可用时用 pathlib.Path.rglob 搜索 references/troubleshooting/

- **6.2 经验自动检索**
  - 当前：无自动检索
  - 修复：测试前用 pathlib.Path.rglob 搜索相似案例（≤2 秒响应）

- **6.3 经验自动写入**
  - 当前：_settle_evolution 只写本地文件
  - 修复：测试通过后输出到 output/experience-pending.json，由 AI agent 外层通过 MCP 写入

- **6.4 经验冲突解决**
  - 当前：无冲突解决机制
  - 修复：置信度评分+时效性+优先级规则（resolve_conflict 方法）

**方向 7：设计文档与实际代码一致性（P1）**

修复 6 项"已完成但实际未实现"的虚假完成项：

- **7.1 修复 JSON 去重虚假完成**
  - 当前：tasks.md 标记完成但实际 12 处 json.loads（已核实）
  - 修复：真正实现 JSON 去重（main() 入口解析一次）

- **7.2 修复 --timeout 参数虚假完成**
  - 当前：tasks.md 标记完成但实际不存在
  - 修复：真正实现 --timeout 参数

- **7.3 修复 STAGE_NAMES 虚假完成**
  - 当前：tasks.md 标记完成但仍用整数键
  - 修复：统一为字符串键

- **7.4 修复 CacheManagerStub 虚假完成**
  - 当前：tasks.md 标记完成但无 LRU
  - 修复：添加软引用或手动清理

- **7.5 修复 evalJS 虚假完成**
  - 当前：tasks.md 标记完成但 source 上下文缺失
  - 修复：注入完整上下文

- **7.6 修复 4 个孤儿模块虚假完成**
  - 当前：tasks.md 标记"已集成"但实际未 import
  - 修复：真正 import 并调用（方向 4）

- **7.7 mock 数字更新**
  - 当前：说~40 个已实现，实际 132 个
  - 修复：与 JsExtensionsStub.kt 实际代码同步

- **7.8 MVP 命名统一**
  - 当前：SKILL.md 说 MVP4，实际无 mvp4.jar
  - 修复：统一为 legado-jvm

- **7.9 版本锁同步**
  - 当前：jvm-infrastructure.md 说 okhttp4.12.0，build.gradle.kts 用 5.3.2
  - 修复：文档与代码同步

### OUT-OF-SCOPE

- PublicSuffixDatabase 完整移植（P3，本次仅手动剥离 www 前缀）
- Cookie/Cache 持久化（P3，CookieStoreStub 保持内存实现）
- 编码检测增强（EncodingDetect 移植）（P3）
- getGlideUrl/getMediaItem JVM 替代（P3，本次仅评估影响）
- 批量并行调试（P3，后续迭代）
- 自动修复（P3，后续迭代）

## Approach

### 方向 1：JAR 架构重构

**根因分析**（基于源码深度分析，2026-06-20 核实）：

> **已删除伪问题**：~~runBlocking 阻塞~~（BookSourceDebugger.kt/RssSourceDebugger.kt 实际无 runBlocking）、~~30秒OkHttp超时~~（OkHttpUtils.kt 无超时配置，30秒在 JsExtensionsStub.ajax 中）

1. **同步 execute**（OkHttpUtils.kt:52）
   - 真机 OkHttp enqueue + 回调
   - 仿真器 OkHttp execute 同步阻塞
   - 修复：改为 enqueue + suspendCancellableCoroutine

2. **JS 编译缓存**（AnalyzeRule.kt:81/862 scriptCache）
   - 真机 scriptCache 上限 16（AnalyzeRule.kt:862 确认，真机也是16）
   - 仿真器 scriptCache 上限 16（与真机一致，但16偏小导致频繁编译）
   - 修复：提升到 64（优化提升，非对齐真机）

3. **JsExtensionsStub 实例化**（JsExtensionsStub.kt:48，仿真器中由 AnalyzeRule/AnalyzeUrl 内部创建；真机无 Stub 层）
   - 真机 AnalyzeRule/AnalyzeUrl 直接 implements JsExtensions，无 Stub 层
   - 仿真器 JsExtensionsStub 是普通 class，每次 AnalyzeRule/AnalyzeUrl 初始化时创建新实例
   - 修复：单例化（class→object）

4. **连接池**（OkHttpUtils.kt）
   - 真机连接池保持 5 个连接
   - 仿真器每次新建连接
   - 修复：配置连接池

### 方向 2：保真度提升

**38 个 Stub 方法补全优先级**：

| 优先级 | 方法 | 真机行为 | 仿真器当前 | 修复方案 |
|--------|------|---------|-----------|---------|
| P0 | ajax | AnalyzeUrl 自身 | Jsoup.connect | AnalyzeUrl override |
| P0 | connect | AnalyzeUrl 自身 | Jsoup.connect | AnalyzeUrl override |
| P0 | get/post | OkHttp 完整 | Jsoup.connect | OkHttp 补全 |
| P0 | base64Decode/Encode | 完整 flags | 仅 flag 8 | 补全 flags |
| P0 | strToBytes/bytesToStr | 完整 | Stub | 实现 |
| P0 | getCookie | CookieStore | 固定返回 | CookieStore 集成 |
| P0 | cacheFile | CacheManager | Stub | CacheManager 集成 |
| P0 | importScript | 文件读取 | Stub | 文件读取实现 |
| P0 | queryTTF | TTF 解析 | Stub | TTF 解析实现 |
| P0 | replaceFont | 字体替换 | Stub | 字体替换实现 |
| P1 | getGlideUrl | 图片 URL | 缺失 | 评估后补全 |
| P1 | getMediaItem | 媒体 URL | 缺失 | 评估后补全 |

### 方向 3：Python 工程化

**拆分原则**：
- debug-source.py：仅处理命令行参数解析+调用 legado_client（< 200 行）
- client/：JAR 通信+WebView 渲染+用户交互
- analyzer/：错误诊断+HTML 结构分析+可信度评估+解析策略
- experience/：经验管理+冲突解决
- utils/：配置+日志+文件工具

**虚拟环境管理**：
- requirements.txt：声明所有依赖（requests, selenium, beautifulsoup4 等）
- setup_venv.bat：Windows 虚拟环境激活脚本
- .gitignore：忽略 venv/

### 方向 4：孤儿模块真正集成

**4 个脚本的集成方案**（代码已完整，只需 import+调用）：

> **核实结论**：这 4 个脚本不是"空架子"（有完整实现），而是"孤儿模块"（代码完整但未被任何代码 import）

1. **confidence_evaluator.py**（112行，完整实现）：
   - 已实现 evaluate_confidence 方法
   - 已有类常量 RULE_TYPE_CONFIDENCE 和 FIDELITY_PENALTY
   - 集成：在 debug-source.py 中 import 并调用

2. **user_interaction_handler.py**（140行，完整实现+自检）：
   - 已实现 4 种错误场景处理（url_unreachable/login_required/captcha/cf_protection）
   - 集成：在 debug-source.py 中 import 并调用

3. **source_navigation.py**（84行，完整实现+自检）：
   - 已实现错误→源码映射（6种错误类型）
   - 集成：在 debug-source.py 中 import 并调用

4. **parse_strategy_selector.py**（131行，完整实现+自检）：
   - 已实现解析策略选择（决策树+HTML推断）
   - 集成：在 debug-source.py 中 import 并调用

### 方向 5：JAR 核心功能完善

**CheckSource 校验流程**（基于 CheckSource.kt，74行，配置管理入口，实际校验逻辑在 CheckSourceService.kt，294行）：

> **第三轮深度核实更正**（2026-06-20）：实际流程**非线性**，搜索和发现各自独立触发详情→目录→正文。

```
域名检查（Socket连接检测）
    ↓
搜索检查（WebBook.searchBookAwait）
    ↓ 成功则
    checkBook → 详情检查 → 目录检查 → 正文检查（第1次）
    ↓
发现检查（WebBook.exploreBookAwait）
    ↓ 成功则
    checkBook → 详情检查 → 目录检查 → 正文检查（第2次）
```

**关键细节**（设计文档原遗漏）：
- 详情→目录→正文会被执行**两次**（搜索成功一次、发现成功一次）
- checkBook 的详情检测有跳过逻辑：若 `book.tocUrl` 不为空则跳过详情页
- checkBook 的目录检测有跳过逻辑：若 `!checkCategory || source.bookSourceType == BookTokenType.file` 则跳过
- 整个校验有 `withTimeout(CheckSource.timeout)` 超时控制（默认 180000ms）
- 校验失败的书源按异常类型分组（超时/js失效/网站失效）
- `wSourceComment` 控制是否将错误信息写入书源的 errorComment 字段

**state 码语义对齐**（基于 Debug.kt，382行，第三轮深度核实）：
```
真机 Debug.kt 实际有 7 个 state 值（非 3 个）：
state=1: 默认日志
state=-1: 错误
state=1000: 完成
state=10: 列表页HTML（BookList.kt:54, RssParserByRule.kt:37）
state=20: 详情页HTML（BookInfo.kt:40, Rss.kt:135）
state=30: 目录页HTML（BookChapterList.kt:49）
state=40: 正文页HTML（BookContent.kt:52）

仿真端使用 10/20/30/40 与真机一致，无需修改。
```

### 方向 6：经验知识闭环

**basic-memory 访问方式**（AD-5 决策修正版）：
- debug-source.py 输出经验数据到 JSON 文件（output/experience-pending.json）
- AI agent 外层通过 MCP 工具（mcp_basic-memory_write_note）写入 basic-memory
- Python 脚本不直接调用 MCP 或 CLI

**降级路径**：
- basic-memory 不可用时，experience_manager.py 用 pathlib.Path.rglob 搜索 references/troubleshooting/
- 降级写入到 references/troubleshooting/auto/，添加 <!-- AUTO_GENERATED --> 标记

### 方向 7：设计文档一致性

**6 项虚假完成项修复**：
- JSON 去重：真正实现 main() 入口解析一次
- --timeout：真正实现参数
- STAGE_NAMES：统一为字符串键
- CacheManagerStub：添加软引用
- evalJS：注入完整上下文
- 4 个孤儿模块：真正 import 并调用

## Requirements

### REQ-1：JAR 异步高性能
- 单源调试响应时间 < 10 秒（当前 30 秒+）
- 同步 execute 改为异步 enqueue + suspendCancellableCoroutine
- JS 编译缓存上限从 16 提升到 64（AnalyzeRule.kt:862，真机也是16，提升到64是优化）
- JsExtensionsStub 单例化（class→object，仿真器中由 AnalyzeRule/AnalyzeUrl 内部创建；真机无 Stub 层）
- OkHttp 连接池复用（5 个 keepAlive）

### REQ-2：JAR 保真度 95%+
- evalJS 注入真实 source 和 baseUrl（非 null 和非空）
- ajax 走 AnalyzeUrl 而非 Jsoup.connect
- CacheManagerStub 添加软引用或手动清理
- 38 个 Stub 中高频方法全部补全
- base64Decode 支持完整 flags

### REQ-3：Python 客户端工程化
- 创建 requirements.txt 声明所有依赖
- 创建 venv 激活脚本
- 创建 legado_client/ 包结构（__init__.py + 模块化）
- 拆分 debug-source.py（1236 行 → 入口 < 200 行 + 包模块）
- 全量 type hints
- JSON 去重（main() 入口解析一次）

### REQ-4：孤儿模块真正集成
- confidence_evaluator.py import 到 debug-source.py 并调用
- user_interaction_handler.py import 到 debug-source.py 并调用
- source_navigation.py import 到 debug-source.py 并调用
- parse_strategy_selector.py import 到 debug-source.py 并调用

### REQ-5：JAR 核心功能完善
- CheckSource 校验流程（域名→搜索→发现→详情→目录→正文）
- ~~state 码语义对齐~~ **已核实：伪问题，仿真端 10/20/30/40 与真机一致（真机 BookList/BookInfo/BookChapterList/BookContent 也使用 10/20/30/40）**

### REQ-6：经验知识闭环
- 测试前用 pathlib.Path.rglob 搜索相似案例（≤2 秒响应）
- 测试后输出到 output/experience-pending.json（≤5 秒写入）
- basic-memory 不可用时降级到 Python 原生文件搜索
- 降级写入到 references/troubleshooting/auto/，添加 <!-- AUTO_GENERATED --> 标记
- 经验冲突解决（置信度评分+时效性+优先级规则）

### REQ-7：设计文档一致性
- JSON 去重真正实现（12 处 → 1 处）
- --timeout 参数真正实现
- STAGE_NAMES 统一为字符串键
- CacheManagerStub 添加软引用
- evalJS 注入真实 source 和 baseUrl
- 4 个孤儿模块真正 import 并调用
- mock 数字与 JsExtensionsStub.kt 代码同步
- MVP 命名统一为 legado-jvm
- jvm-infrastructure.md 版本号与 build.gradle.kts 一致

## Scenarios

### Scenario 1：JAR 异步高性能
```
Given: AI 执行 python debug-source.py --source xxx.json
When: JAR 仿真服务端调试书源
Then: 单源调试响应时间 < 10 秒（当前 30 秒+），不卡顿
```

### Scenario 2：ajax 委托修复
```
Given: 书源 JS 规则调用 java.ajax("https://api.example.com/data")
When: JAR 仿真器执行 ajax 请求
Then: 走 AnalyzeUrl 而非 Jsoup.connect，支持 URL 模板/Cookie/请求体编码
```

### Scenario 3：evalJS 上下文注入
```
Given: 书源 JS 规则调用 java.ajax("https://api.example.com/data")
When: RuleEngineServer.kt 执行 evalJS 命令
Then: 注入真实 source 和 baseUrl（非 null 和非空），java.ajax 可正常执行
```

### Scenario 4：Python 工程化
```
Given: AI 执行 python debug-source.py --source xxx.json
When: debug-source.py 调用 legado_client 包
Then: 入口脚本 < 200 行，逻辑分散到 client/analyzer/experience/utils 模块
```

### Scenario 5：孤儿模块真正集成
```
Given: AI 执行 python debug-source.py --source xxx.json --output report.json
When: 调试完成后生成报告
Then: confidence_evaluator 评估可信度+user_interaction_handler 处理错误+source_navigation 导航源码+parse_strategy_selector 推荐解析策略
```

### Scenario 6：CheckSource 校验
```
Given: AI 执行 python debug-source.py --source xxx.json --check
When: JAR 仿真服务端执行 CheckSource 校验
Then: 输出域名→搜索→发现→详情→目录→正文全流程校验结果，标记失效分组
```

### Scenario 7：state 码语义对齐（已核实：伪问题）
```
Given: AI 执行 python debug-source.py --source xxx.json --debug
When: JAR 仿真服务端执行调试
Then: 输出 state 码与真机一致（10=列表页HTML, 20=详情页HTML, 30=目录页HTML, 40=正文页HTML, 1=默认日志, -1=错误, 1000=完成）
注：经第三轮深度核实，真机 Debug.kt 也使用 10/20/30/40（在 BookList/BookInfo/BookChapterList/BookContent 中），仿真端已与真机一致，无需修改。
```

### Scenario 8：经验自动检索
```
Given: 测试中国古典书源前
When: experience_manager.py 用 pathlib.Path.rglob 搜索 references/troubleshooting/
Then: 返回 "相似案例：奇书塔（相对路径问题，JS 补全绝对路径修复）"
```

### Scenario 9：经验自动写入
```
Given: 中国古典书源修复后测试通过
When: debug-source.py 输出经验数据到 output/experience-pending.json
Then: AI agent 外层通过 MCP 工具写入 basic-memory，包含错误类型+修复方案+测试结果
```

### Scenario 10：设计文档一致性
```
Given: AI 查阅 tasks.md 发现"JSON 去重"标记完成
When: AI 验证实际代码
Then: debug-source.py 中 main() 入口解析一次 source_obj，后续传递对象（非 12 处 json.loads）
```

### Scenario 11：相对路径自动拼接（已核实已修复）
```
Given: 书源 bookUrl 规则是 a@href，网站返回 /honglou.html
When: JVM 仿真器调试搜索阶段
Then: baseUrl 已传递（第121行），toAbsoluteUrl 已调用（第181行），自动拼接为绝对 URL
```

### Scenario 12：CacheManagerStub LRU
```
Given: 长时间批量调试 20 个源
When: CacheManagerStub 缓存数据
Then: 添加软引用或手动清理，长时间运行不 OOM
```

### Scenario 13：虚拟环境管理
```
Given: AI 首次使用 skill
When: AI 执行 setup_venv.bat
Then: 创建 venv 虚拟环境+安装 requirements.txt 依赖，后续脚本在虚拟环境中运行
```

### Scenario 14：可信度评估
```
Given: 书源规则包含 JS+加密，仿真器测试通过
When: confidence_evaluator 评估可信度
Then: 输出"可信度: 低（含 JS+加密，保真度限制区域）→ ⚠️ 建议真机验证"
```

### Scenario 15：用户交互-Cookie 请求
```
Given: AI 检测到网站需要登录（返回登录页面）
When: user_interaction_handler 处理错误
Then: 输出标准化交互请求（类型: Cookie 请求+消息+建议+需用户提供的信息）
```

## 风险预测

### 风险 1：JAR 异步改造可能引入死锁
- **问题**：协程 async/await 改造可能引入死锁
- **影响**：JAR 完全无响应
- **应对**：使用 suspendCancellableCoroutine + enqueue 模式，避免嵌套 suspend；改造后回归测试

### 风险 2：Stub 方法补全可能引入新 bug
- **问题**：补全 38 个 Stub 方法可能引入新 bug
- **影响**：仿真结果与真机不一致
- **应对**：每个 Stub 补全后单独测试+回归测试

### 风险 3：Python 包结构重构可能破坏现有功能
- **问题**：拆分 debug-source.py 可能破坏现有功能
- **影响**：脚本无法运行
- **应对**：重构后运行 20 个测试源回归测试

### 风险 4：basic-memory MCP 写入失败
- **问题**：AI agent 外层 MCP 写入 basic-memory 可能失败
- **影响**：经验无法持久化
- **应对**：降级写入到 references/troubleshooting/auto/，添加 <!-- AUTO_GENERATED --> 标记

### 风险 5：CheckSource 校验流程复杂
- **问题**：CheckSource 涉及多个阶段，实现复杂
- **影响**：开发周期长
- **应对**：分阶段实现，先实现域名+搜索校验，再逐步补全

### 风险 6：虚拟环境兼容性
- **问题**：Windows/Linux 虚拟环境激活方式不同
- **影响**：跨平台兼容性
- **应对**：提供 activate.bat（Windows）和 activate.sh（Linux）

### 风险 7：设计文档修复可能遗漏
- **问题**：6 项虚假完成项可能修复不彻底
- **影响**：设计文档仍不一致
- **应对**：每项修复后验证实际代码，禁止描述性验收
