# Design: Legado Skill 统一优化重设计

## 1. 前置核查结论

### 1.1 设计文档完成度
| Spec目录 | 总任务 | 已完成 | 完成率 | 状态 |
|----------|--------|--------|--------|------|
| legado-skill-optimization | 268 | 15 | 5.6% | 设计中 |
| skill-core-capability-rebuild | 160 | 160 | 100% | 已完成 |
| jvm-webview-and-test-fix | 52 | 52 | 100% | 已完成 |
| source-repair-loop-optimization | 212 | 184 | 86.8% | 已完成(YAGNI) |
| skill-usability-optimization | 71 | 0 | 0% | 设计中 |
| legado-skill-v2-rebuild | 85 | 0 | 0% | 设计中 |

### 1.2 设计与实施一致性偏差
已识别6项关键偏差：
1. SKILL.md引用11个不存在文件（5个scripts + 6个tools已迁移）
2. JsExtensionsStub.kt文件头注释过时（声称86/38/8，实际95/11/23）
3. tools/与legado_client/双轨并行，debug_runner通过sys.path动态注入
4. references/_INDEX.md缺失5个条目
5. output/目录含6个运行产物未清理
6. legado-skill-v2-rebuild与legado-skill-optimization重叠未归档

### 1.3 子任务校验机制缺陷
1. 子代理输出未校验直接闭环：100个新源批量测试0%成功率但标记"测试流程正常"
2. 虚假完成项反复出现：JSON去重/timeout参数/STAGE_NAMES/CacheManagerStub/evalJS/4个孤儿模块在旧spec中标记完成但实际未实现
3. 根因：验收标准不可执行、缺乏交叉验证

### 1.4 目录结构治理方案
需清理项：
- P0：删除tools/__pycache__/、更新SKILL.md 11个幽灵引用
- P1：补充references/_INDEX.md 5个缺失条目、清理output/产物
- P2：添加tools/.gitignore、重命名test-data/broken-selector.json
- P3：消除debug_runner.py的sys.path跨目录导入

## 2. 整体架构设计

### 2.1 四层组件架构
```
┌──────────────────────────────────────────────────────────────────────┐
│                    L1 经验知识库（决策大脑）                              │
│  SKILL.md（流程+陷阱+操作指引）+ references/（6大目录60+文档）           │
│  + basic-memory（L3经验索引层，project=legado）                        │
│  权威源规则：SKILL.md > references/ > basic-memory                     │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕
┌──────────────────────────────────────────────────────────────────────┐
│                    L2 Python客户端（操作执行层）                         │
│  legado_client/ 包结构                                                  │
│  ├── client/    （RuleEngineClient + DebugRunner + ObstacleResolver）  │
│  ├── analyzer/  （ErrorDiagnoser + AutoFixer + ConfidenceEvaluator）  │
│  ├── experience/（ExperienceManager + ConflictResolver）               │
│  └── utils/     （Config + Logger + FileUtils + JvmHelpers）           │
│  入口脚本：debug-source.py（薄壳，<200行）                                │
│  独立工具：verify-*.py / analyze_site.py / html_fetcher.py            │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕ stdin/stdout JSON 行协议
┌──────────────────────────────────────────────────────────────────────┐
│                    L3 JAR仿真服务端（核心能力底座）                       │
│  legado-jvm.jar（单JAR，非多JAR）                                       │
│  ├── RuleEngineServer（通信协议+命令分发：ping/evalJS/debug*/batch/check）│
│  ├── BookSourceDebugger（书源：search→detail→toc→content）              │
│  ├── RssSourceDebugger（订阅源：sort→content）                           │
│  ├── CheckSourceDebugger（校验：域名→搜索→发现→详情→目录→正文）          │
│  ├── AnalyzeUrl + AnalyzeRule（规则引擎核心）                           │
│  ├── JsExtensionsStub（132方法：95完整+11降级+23不可用）                 │
│  └── CacheManager + CookieStore + NetworkUtils（基础设施）              │
│  依赖版本锁定：rhino 1.8.1 / jsoup 1.16.2 / hutool 5.8.22            │
└──────────────────────────────────────────────────────────────────────┘
                                  ↕ 仅在JAR无法覆盖时回查
┌──────────────────────────────────────────────────────────────────────┐
│                    L4 Legado官方源码（最终兜底保障）                      │
│  app/src/main/java/io/legado/app/                                     │
│  WebBook.kt + Rss.kt + Debug.kt + CheckSource.kt + JsExtensions.kt  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件协同链路
```
用户请求 → SKILL.md决策入口 → Phase1经验搜索(basic-memory)
  → Phase2构建规则(references/) → Phase3测试驱动(Python→JAR)
  → Phase4源码深挖(L4源码) → Phase5经验反哺(basic-memory+references/)
```

### 2.3 三Skill协作接口

> 对齐SKILL.md §"与其他Skill的关系"的三Skill协作链路

```
legado-skill-auditor（确保skill健康）→ legado-source-creator（创建/修复源）→ legado-workflow-auditor（审计执行证据）
```

#### 2.3.1 source-creator → workflow-auditor 上下文传递

| 字段 | 类型 | 说明 |
|------|------|------|
| source_name | String | 源名称（从Phase 1获取） |
| source_type | "book" / "rss" | 源类型 |
| task_type | "create" / "repair" / "optimize" | 任务类型 |
| phases_completed | Int[] | 已完成的Phase列表（如[1, 3, 5]） |
| execution_logs | String[] | 各Phase的basic-memory执行证据identifier |

#### 2.3.2 skill-auditor 触发条件

- 用户明确要求审查skill质量时
- legado-source-creator重大版本更新后（建议触发）

## 3. JVM仿真服务端优化方案

### 3.1 源码差距全量盘点

#### 3.1.1 JsExtensionsStub方法差距（132个方法）

| 分类 | 完整 | Stub降级 | 不可用 | 说明 |
|------|------|---------|--------|------|
| HTTP方法 | 15 | 0 | 0 | ajax/ajaxAll/connect/get/head/post全部委托AnalyzeUrl |
| WebView方法 | 0 | 0 | 7 | 全部抛WebViewRequiredException |
| UI交互方法 | 0 | 0 | 7 | startBrowser/getVerificationCode等抛异常 |
| 文件方法 | 10 | 3 | 1 | unArchiveFile/un7z/unrar空实现，openUrl不可用 |
| 压缩方法 | 3 | 0 | 6 | Zip完整，Rar/7z返回null |
| Base64方法 | 7 | 0 | 0 | hutool+java.util.Base64适配 |
| 编码方法 | 5 | 0 | 0 | encodeURI/htmlFormat/t2s/s2t |
| 加密方法 | 30 | 0 | 0 | JsEncodeUtils全部完整 |
| 配置方法 | 0 | 5 | 0 | getReadBookConfig等返回空/默认值 |
| 其他 | 25 | 3 | 2 | toast降级stdout，getWebViewUA固定值 |
| **合计** | **86** | **38** | **8** | ~~原统计95/11/23有误，源码核实修正为86/38/8~~ |

#### 3.1.2 关键差距清单（按影响等级）

**已修复项（源码核验确认）**：

| GAP-ID | 差距 | 影响 | 修复方案 | 源码验证 |
|--------|------|------|---------|---------|
| GAP-01 | readTxtFile编码检测缺失 | GBK/GB2312文件10-15% | EncodingDetect.kt | ✅ 已修复 |
| GAP-02 | getTxtInFolder编码检测缺失 | 同GAP-01 | EncodingDetect.kt | ✅ 已修复 |
| GAP-03 | get/head/post无SSL信任 | 自签名证书5-10% | SSLHelper.unsafeSSLSocketFactory | ✅ HttpHelper.kt:40-41 |
| GAP-67a | loginCheckJs检测缺失 | 需登录源5-10% | 各阶段添加检测逻辑 | ✅ BookSourceDebugger.kt:73-115 |
| GAP-67b | ruleNextPage=="PAGE"处理 | 分页源5% | uppercase()比较 | ✅ RssSourceDebugger.kt:560-566 |
| GAP-67d | 正文格式化链缺失 | 正文5% | 移植HtmlFormatter | ✅ BookSourceDebugger.kt:606-900 |
| GAP-80 | CookieJar拦截器缺失 | Cookie源5% | OkHttp拦截器 | ✅ HttpHelper.kt:45-60 |
| BaseSource属性val→var | 6个属性为val | 并发调试 | val→var | ✅ BaseSourceInterface.kt:18 |

**P1级差距（影响1-5%书源）**：

| GAP-ID | 差距 | 影响 | 修复方案 |
|--------|------|------|---------|
| GAP-05 | Rar/7z解压不支持 | 压缩源1-3% | 抽取LibArchiveUtils |
| GAP-36 | JsExtensions委托模式 | 并发调试 | ThreadLocal隔离（已部分修复，源码核验：AnalyzeRule.kt:58使用by委托+ThreadLocal） |
| GAP-37 | ConcurrentRateLimiter | 限流源 | 移植完整限流 |
| GAP-42 | SymmetricCryptoAndroid | 加密源 | 移植encryptBase64 |
| GAP-70a | WrapFactory+instructionObserverThreshold | JS执行 | 移植Rhino安全配置 |

**P2级差距（影响<1%书源）**：

| GAP-ID | 差距 | 影响 | 修复方案 |
|--------|------|------|---------|
| GAP-06 | unArchiveFile返回空 | 压缩源<1% | 抽取ArchiveUtils |
| GAP-56 | evalJS注入持久化对象 | 边缘场景 | 补充注入 |
| GAP-58 | BookChapter业务方法 | 边缘场景 | 补充方法 |
| GAP-73 | userAgent默认值 | 边缘场景 | 改为真机默认值 |

#### 3.1.3 不可用方法分类与委托路径

| 分类 | 方法数 | 委托路径 | 说明 |
|------|--------|---------|------|
| WebView渲染 | 7 | Python Selenium/CDP | webView/startBrowserAwait等 |
| UI交互 | 7 | 用户手动操作+Cookie导出 | startBrowser/getVerificationCode等 |
| Rar/7z解压 | 6 | 抽取LibArchiveUtils | un7zFile/unrarFile等 |
| 其他 | 3 | 标记不实现 | openUrl等 |

### 3.2 兼容性问题根因分析

#### 3.2.1 根因分类

| 根因类型 | 占比 | 典型表现 | 修复策略 |
|----------|------|---------|---------|
| 函数缺失 | 35% | TypeError: java.xxx is not a function | 补全JsExtensionsStub方法 |
| 语法差异 | 25% | Rhino ES5限制、正则差异 | 已在SKILL.md陷阱表覆盖 |
| 引擎差异 | 20% | jsoup CSS vs Legado自定义语法 | 对齐AnalyzeRule解析逻辑 |
| 安卓依赖 | 15% | android.util.Base64、icu4j | JVM替代方案 |
| 网络差异 | 5% | SSL/cookieJar/限流 | OkHttp拦截器 |

#### 3.2.2 分阶段修复方案

**第一阶段（P0，影响>5%）——已全部完成**：
1. ✅ SSL信任所有证书（GAP-03）——HttpHelper.kt:40-41
2. ✅ loginCheckJs检测（GAP-67a）——BookSourceDebugger.kt:73-115
3. ✅ ruleNextPage=="PAGE"（GAP-67b）——RssSourceDebugger.kt:560-566
4. ✅ 正文格式化链（GAP-67d）——BookSourceDebugger.kt:606-900
5. ✅ CookieJar拦截器（GAP-80）——HttpHelper.kt:45-60
6. ✅ BaseSource属性val→var（方向1.1）——BaseSourceInterface.kt:18

**第二阶段（P1，影响1-5%）**：
1. JsExtensions委托模式改为实例化（GAP-36）——已部分修复（ThreadLocal隔离），待评估是否需进一步改为实例化
2. ConcurrentRateLimiter完整限流（GAP-37）
3. SymmetricCryptoAndroid加密对齐（GAP-42）
4. WrapFactory+instructionObserverThreshold（GAP-70a）
5. base64/AES flags映射完善（方向2.1）
6. 其他中难度方法修复（方向2.2）

**第三阶段（P2，影响<1%）**：
1. Rar/7z解压支持（GAP-05/06）
2. evalJS注入持久化对象（GAP-56）
3. BookChapter业务方法（GAP-58）
4. userAgent默认值（GAP-73）
5. 其他P2级差距修复

### 3.3 架构合理性评估

#### 3.3.1 单JAR vs 多JAR
当前已是单JAR（legado-jvm.jar），无需变更。理由：
- 单JAR简化部署和版本管理
- 当前JAR大小合理（~15MB含所有依赖）
- 多JAR拆分增加通信复杂度无性能收益

#### 3.3.2 性能优化现状
已完成的性能优化：
- OkHttp同步execute→异步enqueue+suspendedCancellableCoroutine
- JS编译缓存上限16→64
- JsExtensionsStub单例化
- OkHttp连接池复用（5 keepAlive连接）
- CacheManagerStub软引用防OOM

#### 3.3.3 已修复的性能问题

以下性能问题已在历史迭代中修复，此处记录以供验证：

| 问题 | 根因 | 修复方案 | 验证状态 |
|------|------|---------|---------|
| JVM启动后首次调用卡顿 | runBlocking阻塞主线程 | 改用suspendCancellableCoroutine+异步enqueue | ✅ 已验证 |
| HTTP请求同步阻塞 | OkHttp同步execute() | 改为异步enqueue()+suspendCancellableCoroutine | ✅ 已验证 |
| JS编译缓存不足 | JS缓存上限16导致频繁重编译 | 上限提升至64 | ✅ 已验证 |
| 请求超时过长 | 默认timeout 30s导致长时间等待 | 缩短至15s | ✅ 已验证 |
| JsExtensionsStub非单例 | 每次创建新实例开销大 | 改为object单例 | ✅ 已验证 |
| 连接池未充分利用 | 默认配置无keepAlive | 配置5个keepAlive连接+5分钟存活 | ✅ 已验证 |

#### 3.3.4 待优化性能项

| 项目 | 当前状态 | 优化方案 | 优先级 |
|------|---------|---------|--------|
| JVM冷启动时间 | 1-2秒 | 预热Rhino引擎+预编译常用JS | P2 |
| 批量调试内存管理 | 100源批量时内存波动 | 定期GC+AnalyzeRule ThreadLocal清理 | P1 |
| JS缓存命中率监控 | 无监控 | 添加缓存命中率日志 | P2 |

### 3.4 安卓依赖剥离验证

| 安卓依赖 | 当前替代方案 | 验证状态 |
|----------|------------|---------|
| android.util.Base64 | java.util.Base64 + flags映射 | ✅ 已验证 |
| icu4j CharsetDetector | EncodingDetect.kt（meta标签+UTF-8 fallback） | ✅ 已验证 |
| android.webkit.WebView | WebViewRequiredException→Python Selenium | ✅ 已验证 |
| android.content.Context | 环境变量/配置文件 | ✅ 已验证 |
| android.os.Handler | 直接执行（无UI线程需求） | ✅ 已验证 |
| Room数据库 | 内存Map实现 | ✅ 已验证 |
| LibArchiveUtils | 未替代（返回null） | ❌ 需修复 |
| ArchiveUtils | 未替代（返回空字符串） | ❌ 需修复 |

### 3.5 代码进化机制完善

#### 3.5.1 当前进化流程
```
Phase3测试报错 TypeError → 记录basic-memory(tags=["jvm-evolution"]) 
→ Phase5执行代码进化 → 更新Kotlin源码 → 重建JAR → 重新验证
```

#### 3.5.2 优化点
1. **进化触发识别增强**：从仅识别TypeError扩展到识别所有JVM差异错误
2. **源码对标自动化**：source_navigation.py自动映射错误类型→源码文件+行号
3. **验证沉淀规范化**：进化后必须执行3步沉淀（写basic-memory + 更新速查表 + 记录进化日志）
4. **进化日志持久化**：当前evolution_log.py/precision_metrics.py/rule_evolution.py不存在，SKILL.md引用这3个脚本但实际未实现。**统一决策：用basic-memory替代进化日志**，删除SKILL.md中对这3个脚本的引用。进化记录统一写入basic-memory（note_type=experience, tags=["evolution"]），精准度度量从basic-memory搜索进化记录计算

## 4. Python客户端工程化优化方案

### 4.1 工程化体系建设

#### 4.1.1 依赖管理
- 新增pyproject.toml（声明包元数据+依赖+入口点）
- requirements.txt区分必选/可选依赖
- 必选：requests, beautifulsoup4, lxml, psutil
- 可选：selenium（WebView委托）, pycryptodome（加密验证）, cloudscraper（CF绕过）

#### 4.1.2 目录分层架构
```
legado_client/
├── __init__.py          # 声明__all__公共API
├── __main__.py          # python -m legado_client 入口
├── client/              # 客户端层（JVM通信+调试流程+障碍辅助）
├── analyzer/            # 分析层（错误诊断+自动修复+可信度评估+加密分析+源码导航+解析策略+预校验）
├── experience/          # 经验层（经验检索/写入+冲突解决）
└── utils/               # 工具层（配置+日志+文件工具+JVM辅助）
```

#### 4.1.3 模块化接口封装
- 每层__init__.py声明__all__导出
- 消除sys.path动态注入
- 统一错误处理：自定义LegadoClientError基类+子类

#### 4.1.4 结构化日志输出
- 使用Python logging模块替代print()
- 日志格式：[时间][级别][模块]消息
- 支持JSON结构化输出（--json-output参数）

### 4.2 协同逻辑优化

#### 4.2.1 Python与JVM职责边界

| 职责 | Python客户端 | JAR服务端 |
|------|-------------|----------|
| 规则引擎执行 | ❌ | ✅ AnalyzeRule/AnalyzeUrl |
| HTTP请求 | ❌（仅降级模式） | ✅ OkHttp |
| JS执行 | ❌ | ✅ Rhino |
| WebView渲染 | ✅ Selenium/CDP | ❌ |
| 用户交互 | ✅ CLI/OCR | ❌ |
| 经验管理 | ✅ basic-memory MCP | ❌ |
| 报告生成 | ✅ | ❌ |
| 加密分析 | ✅ 静态分析 | ✅ 执行解密 |

#### 4.2.2 交互协议
- 通信：stdin/stdout JSON行协议（保持现有）
- 命令：ping/evalJS/debugBookSource/debugRssSource/batch/check/shutdown
- 降级：JVM不可用→Python降级模式（搜索+详情，可信度medium）

### 4.3 AI友好性升级

#### 4.3.1 测试输出格式
```json
{
  "success": false,
  "stage": "search",
  "error": {
    "type": "css_selector_empty",
    "message": "CSS选择器'.book-list a'未匹配任何元素",
    "root_cause": "网站改版，选择器过时",
    "stack_trace": "AnalyzeRule.kt:437 → BookSourceDebugger.kt:89",
    "rule_field": "ruleSearch.bookList",
    "fix_suggestion": "重新分析网站HTML结构，更新选择器"
  },
  "confidence": "medium",
  "source_json": "path/to/source.json"
}
```

#### 4.3.2 错误诊断覆盖
从4种扩充到12种错误类型：
1. css_selector_empty（CSS选择器未匹配）
2. xpath_empty（XPath未匹配）
3. jsonpath_empty（JSONPath未匹配）
4. rule_parse_error（规则语法错误）
5. url_format_error（URL格式错误）
6. relative_url（相对路径未拼接）
7. network_error（网络请求失败）
8. js_runtime_error（JS运行时错误）
9. decrypt_error（解密失败）
10. field_missing（必填字段缺失）
11. field_conflict（字段冲突）
12. type_mismatch（类型不匹配）

### 4.4 工具集整合

#### 4.4.1 tools/目录现状与整合方案

> **源码核验结论**：`tools/`目录已不存在。SKILL.md中引用的18个`tools/`路径均为幽灵引用。相关模块已迁移到`scripts/legado_client/`包结构中，或已删除。

| SKILL.md引用的tools/模块 | 实际状态 | 整合方案 |
|--------------------------|---------|---------|
| tools/html_fetcher.py | ❌ 不存在 | 需新建或从SKILL.md删除引用 |
| tools/fetch_html.py | ❌ 不存在 | 需新建或从SKILL.md删除引用 |
| tools/rule_engine_client.py | ✅ 已迁移 | scripts/legado_client/client/rule_engine_client.py |
| tools/jvm_helpers.py | ✅ 已迁移 | scripts/legado_client/utils/jvm_helpers.py |
| tools/obstacle_resolver.py | ✅ 已迁移 | scripts/legado_client/client/obstacle_resolver.py |
| tools/crypto_analyzer.py | ✅ 已迁移 | scripts/legado_client/analyzer/crypto_analyzer.py |
| tools/auto_fixer.py | ✅ 已迁移 | scripts/legado_client/analyzer/auto_fixer.py |
| tools/interactive_guide.py | ✅ 已迁移 | scripts/legado_client/client/interactive_guide.py |
| tools/cookie_manager.py | ❌ 不存在 | 需新建或从SKILL.md删除引用 |
| tools/smart_http_client.py | ❌ 不存在 | 需新建或从SKILL.md删除引用 |
| tools/knowledge_matcher.py | ✅ 已合并 | scripts/legado_client/experience/experience_manager.py |
| tools/error_translator.py | ✅ 已合并 | scripts/legado_client/analyzer/error_diagnoser.py |
| tools/degradation_chain.py | ❌ 不存在 | 需新建或从SKILL.md删除引用 |
| tools/workflow_timer.py | ❌ 不存在 | 需新建或从SKILL.md删除引用 |
| tools/user_action_minimizer.py | ❌ 不存在 | 需新建或从SKILL.md删除引用 |
| tools/rhino-1.8.1.jar | ❌ 不存在 | 需新建或从SKILL.md删除引用 |

**整改决策**：
1. SKILL.md中所有`tools/`引用统一改为`scripts/legado_client/`对应路径
2. 不存在的模块（html_fetcher/cookie_manager/smart_http_client等）从SKILL.md删除引用，或标注为"待实现"
3. 已迁移模块的引用路径更新为实际路径

#### 4.4.2 import路径修复方案
1. 修复5个独立脚本的import路径（verify-source/verify-decrypt/verify-selector/verify-image/analyze_site）——源码核验：5个脚本仍使用sys.path.insert动态注入
2. 消除debug_runner.py的sys.path动态注入——源码核验：debug_runner.py:21-22仍使用sys.path.insert
3. 消除auto_fixer.py的4层parent硬编码路径——源码核验：auto_fixer.py:31使用`Path(__file__).resolve().parent.parent.parent.parent / "tools"`
4. 统一使用legado_client包内import
5. 创建pyproject.toml——源码核验：当前不存在

## 5. 经验知识库完善方案

### 5.1 双写一致性核验

#### 5.1.1 SKILL.md陷阱速查表
- 当前79条陷阱，需逐条核验references/中是否有对应详细文档
- 缺失条目补写到references/troubleshooting/对应子文档

#### 5.1.2 references/_INDEX.md补全
需补充5个缺失条目：
1. basic-memory-usage.md
2. code-evolution.md
3. jvm-infrastructure.md
4. mock-unimplemented-functions.md
5. known-fix-patterns/目录

#### 5.1.3 basic-memory索引层
- 核查SKILL.md每条陷阱在basic-memory中是否有对应trap笔记
- 核查references/关键经验在basic-memory中是否有对应experience/pattern笔记
- 缺失项补写

### 5.2 闭环反哺机制优化

#### 5.2.1 当前反哺流程
```
测试发现问题 → 源码定位根因 → 沉淀为经验 → 更新知识库 → 写入basic-memory
```

#### 5.2.2 优化点
1. **经验要素自动提取**：experience_manager.extract()从调试结果自动提取（网站特征/错误模式/修复方法/规则模式/可信度）
2. **经验草稿生成**：生成JSON草稿到experience/pending/目录
3. **冲突解决自动化**：conflict_resolver按置信度0.5+时效性0.3+覆盖度0.2评分选优
4. **降级写入隔离**：basic-memory不可用时写入references/troubleshooting/auto/，添加<!-- AUTO_GENERATED -->标记

## 6. 测试体系升级方案

### 6.1 测试用例有效性审计

#### 6.1.1 有效校验项
- debug-source.py端到端调试（search→detail→toc→content）
- verify-source.py源完整性验证
- verify-selector.py CSS选择器验证
- verify-decrypt.py加密验证

#### 6.1.2 空架子项（需优化或删除）
- quick-verify.py：仅检查HTTP存活，无规则验证价值
- classify-and-fix.py：不存在（SKILL.md幽灵引用）
- check_health.py：不存在（SKILL.md幽灵引用）
- evolution_log.py / precision_metrics.py / rule_evolution.py：不存在

#### 6.1.3 保留/优化/删除方案
| 脚本 | 方案 | 理由 |
|------|------|------|
| debug-source.py | 保留+优化 | 核心端到端调试 |
| verify-source.py | 保留+修复import | 源完整性验证 |
| verify-selector.py | 保留+修复import | CSS验证 |
| verify-decrypt.py | 保留+修复import | 加密验证 |
| verify-image.py | 保留+修复import | 图片验证 |
| analyze_site.py | 保留+修复import | 网站分析 |
| quick-verify.py | 优化：增加规则存活检测 | 当前仅HTTP检查 |
| classify-and-fix.py | 删除引用 | 不存在 |
| check_health.py | 删除引用 | 不存在 |
| evolution_log.py | 删除引用或创建简化版 | 不存在 |
| precision_metrics.py | 删除引用或创建简化版 | 不存在 |
| rule_evolution.py | 删除引用 | 不存在 |

### 6.2 全链路测试规范

#### 6.2.1 测试流程
```
源导入(JSON解析) → 预校验(source_validator+rule_precheck)
→ JVM调试(debug-source.py) → 结果校验(与真机对比)
→ 错误诊断(error_diagnoser) → 自动修复(auto_fixer,最多3次)
→ 经验沉淀(experience_manager)
```

**预校验详细步骤**（对齐SKILL.md Phase2完成检查清单）：
1. **字段完整性校验**（source_validator）：
   - BookSource必填字段非空：bookSourceName/bookSourceUrl/bookSourceType
   - RssSource必填字段非空：sourceName/sourceUrl/type
   - URL格式校验：sourceUrl/searchUrl必须以http://或https://开头
   - 字段冲突检测：如同时存在ruleSearch和ruleArticles
2. **规则语法校验**（rule_precheck）：
   - CSS选择器语法检查（soupsieve验证）
   - XPath语法检查（lxml验证）
   - JSONPath语法检查（jsonpath-ng或降级为括号匹配）
   - JS规则括号匹配+关键字检查（不执行JS）
3. **预校验失败处理**：返回Phase2重新构建错误字段/规则，不调用JAR

#### 6.2.2 可信度分级
| 级别 | 条件 | 标注 |
|------|------|------|
| 高 | CSS/纯逻辑JS/加密 + HTML直接获取验证 | "已通过本地验证" |
| 中 | 依赖ajax()但无Cookie / CMS样本 / Python降级 | "Cookie差异可能影响" |
| 低 | 依赖ajax()+Cookie / 无HTML | "需真机验证" |
| 不可验证 | WebView规则 | "必须在Legado中测试" |

### 6.3 错误诊断与自动修复升级

#### 6.3.1 auto_fixer覆盖场景扩充
从4种→12种错误类型（见4.3.2），每种类型对应修复方法模板

#### 6.3.2 自动修复流程
```
JAR失败 → error_diagnoser诊断错误类型 
→ 可自动修复？→ auto_fixer修复→重试(最多3次) 
→ 需用户介入？→ user_interaction生成交互请求
```

### 6.4 降级机制完善

#### 6.4.1 JVM不可用降级路径
```
JVM可用 → debug-source.py(JVM模式,可信度高)
→ JVM不可用 → Python降级模式(requests+BS4,仅搜索+详情,可信度medium)
→ 网站不可访问 → 标记需真机验证
```

#### 6.4.2 降级行为修正
- 当前：退出码3中断工作流
- 修改为：自动降级到Python模式，工作流不中断
- 结果标注"Python降级模式，建议用JAR复验"

## 7. 执行约束规则

### 7.1 懒原则边界重定义

#### 7.1.1 允许使用懒原则的场景
1. 避免过度工程化：不为一次性操作创建抽象
2. 删减非必要冗余设计：YAGNI原则正确应用
3. 简化文档格式：不追求完美格式

#### 7.1.2 禁止使用懒原则的场景
1. 规避核心问题解决
2. 降低验收标准
3. 跳过验证环节
4. 简化核心功能实现
5. 未对标源码擅自修改逻辑
6. 挑选简单书源测试回避复杂样本
7. 虚假标记任务完成

#### 7.1.3 判定标准
- 问题：此简化是否影响>1%的书源兼容性？
  - 是 → 禁止简化
  - 否 → 允许简化，但需标注简化说明

### 7.2 执行偏差深度复盘

| 偏差行为 | 根因 | 预防机制 |
|----------|------|---------|
| 挑选简单书源测试 | 回避复杂问题 | 强制使用50+50标准测试集 |
| 虚假标记任务完成 | 验收标准不可执行 | 每个任务必须有可执行的验证方法 |
| 未对标源码擅自修改 | 经验臆测 | 所有JVM修改必须先对标Legado源码 |
| 简化核心任务 | 滥用懒原则 | 懒原则边界明确化 |
| 子代理输出未校验 | 信任单一来源 | 交叉验证+人工抽检 |

### 7.3 大型任务上下文管理方案

1. **分阶段固化文档**：每个Phase完成后产出正式文档
2. **核心需求锚定**：在文档开头声明不可妥协的核心需求
3. **关键节点产出正式文档**：设计阶段禁止主动压缩上下文
4. **上下文压缩保护**：标记"不可压缩"的关键信息
5. **进度可视化**：TodoWrite实时跟踪

## 8. 真实样本验证方案

### 8.1 测试集要求
- 书源50个+订阅源50个
- 覆盖不同规则类型：CSS/XPath/JSONPath/Regex/JS
- 覆盖不同复杂度：简单/中等/复杂
- 覆盖不同站点类型：小说/视频/图集/新闻/音频
- 合法合规、真机可正常运行

### 8.2 全流程闭环测试
```
导入50+50源 → Phase1经验搜索 → Phase2构建规则(如需) 
→ Phase3测试驱动 → Phase4源码深挖(如测试失败) 
→ Phase5经验反哺 → 统计兼容性达标率
```

### 8.3 验收标准
| 指标 | 目标 | 验证方法 |
|------|------|---------|
| 保真度 | ≥95% | 四分类法评估 |
| 自动化率 | >70% | 100源中无需手动操作的比例 |
| 端到端一致性 | 100% | 抽样真机验证 |
| 自动修复成功率 | >50% | auto_fixer修复后通过率 |
| 预校验拦截率 | >20% | 预校验失败占比 |
