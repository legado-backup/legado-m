# 源修复闭环优化：仿真保真度 + 可观测性 + 经验闭环 + 文档治理

> **状态**：🔄 设计中
> **前置项目**：[jvm-webview-and-test-fix](../jvm-webview-and-test-fix/)（已完成）
> **创建日期**：2026-06-20
> **分析方法**：基于源码深度分析（非拍脑袋），覆盖客户端1018行Python + 服务端15个Kotlin文件 + skill 6大参考目录 + 真机vs仿真器3组文件对比

---

## 功能概述

在修复20个失败书源/订阅源的过程中，暴露出工具链的**80+个真实痛点**（通过源码分析+修复经验对比+真机对比发现，非臆测）。这些痛点分布在7个层面：

| 层面 | 痛点数 | 核心问题 |
|------|--------|---------|
| **JVM仿真服务端** | 14个 | baseUrl普遍未传导致相对路径不拼接；HTML收集不分析；错误不够actionable；singleUrl多处bug |
| **JVM仿真保真度限制** | 14个 | getSubDomain不剥离www前缀；ajax委托走Jsoup；TextUtils.isEmpty替换为isNullOrBlank；Base64 flags简化 |
| **JVM仿真器深层问题** | 9个 | aesEncodeToString行为不一致；HTTP方法缺失5项功能；evalJS不注入完整上下文；CacheManagerStub无LRU可能OOM；客户端调用6个已弃用命令 |
| **Python客户端** | 15个 | JSON重复解析5次；无结构化输出；未集成basic-memory；JVM无超时；进化重验证丢参数 |
| **Skill文档体系** | 12个 | 陷阱编号断裂；mock数字过时；MVP命名混乱；deep-verify状态三重矛盾；okhttp/gson版本错误 |
| **跨层协作** | 8个 | 三套阶段命名不统一；jar路径不一致；经验闭环MCP访问方式未设计；降级写入污染文档 |
| **规则语法与网站特性** | 10个 | og:novel meta标签+@put/@get；nextContentUrl分页；replaceRegex正文净化；||回退选择器；@CSS:前缀；GBK编码；SSR反爬；音频解析；搜索方法转换；referer header |

本项目基于源码分析的真实发现，从16个方向系统性优化工具链，核心目的是**让AI使用skill更好地为用户生成/修复书源和订阅源**。

---

## 统一设计理念

### 理念1：仿真保真度优先

JVM仿真器的首要目标是"行为与真机一致"，而非"功能覆盖率高"。一个不保真的仿真器比没有仿真器更危险——因为它会产生错误的信任（如debug()吞异常导致100%假通过率）。

**落地原则**：
- 相对路径拼接必须对齐真机NetworkUtils.getAbsoluteURL
- 错误处理必须对齐真机（不吞异常、不降级到html掩盖规则缺失）
- JS执行环境必须对齐真机（Rhino限制、ES5语法约束）
- **Cookie域名计算必须对齐真机**（getSubDomain剥离www前缀）
- **规则空值判断必须对齐真机**（TextUtils.isEmpty ≠ isNullOrBlank）

### 理念2：可观测性优先

调试工具的首要价值是"让问题可见"，而非"自动解决问题"。AI看到问题后可以自己修复，但看不到问题就无法行动。

**落地原则**：
- HTML结构分析让选择器问题可见（当前只收集不分析是最大浪费）
- 错误诊断让根因可见（当前只报堆栈不给建议）
- 结构化输出让AI可读（当前全靠解析stdout文本）
- **可观测性边界**：输出调试信息而非原始数据（如输出class统计而非整个HTML），避免信息过载

### 理念3：经验闭环自动化

经验不应依赖手动写入，应从测试结果中自动提取。当前完全未集成basic-memory，违反AGENTS.md强制规则。

**落地原则**：
- 测试前自动检索相似案例（basic-memory不可用时降级Python原生文件搜索`pathlib.Path.rglob`）
- 测试后自动写入新经验（输出到`output/experience-pending.json`，由AI agent外层通过MCP工具写入basic-memory）
- 经验去重+质量评估（避免低质量经验污染）
- **经验质量标准**：测试通过才写入；包含错误类型+修复方案+测试结果三要素

### 理念4：单一权威源

文档、代码、经验三个层面都应有单一权威源，当前存在多处矛盾。

**落地原则**：
- 陷阱编号在SKILL.md和references/之间统一（当前断裂）
- mock数字与实际代码同步（当前说40实际132）
- jar路径统一（当前3处文档不一致）
- **冲突解决优先级**：代码 > 文档 > 经验（代码是事实，文档是描述，经验是补充）
- **版本锁文档与代码同步**：okhttp/gson等依赖版本变更时必须同步更新文档

### 理念5：渐进式验证

修改JVM仿真器后必须确保不引入新bug。每次修改都遵循"修改→重建→回归测试"的闭环。

**落地原则**：
- 每次JVM修改后重建JAR并运行5个修复源回归测试+衍墨轩书搜索阶段已知失效（网站端问题）
- 修改前备份JAR（legado-jvm.jar.bak），失败时可回滚
- 回归测试不通过=修改无效，禁止进入下一方向

### 理念6：降级路径一致性

多个降级路径（basic-memory降级、JVM降级、HTML分析降级）需要统一的设计原则。

**落地原则**：
- 降级时必须标记降级状态（输出"⚠️ 降级到XXX"而非静默切换）
- 降级写入必须隔离（写入独立目录如`references/troubleshooting/auto/`，不污染权威文档）
- 降级数据必须可识别（添加`<!-- AUTO_GENERATED -->`标记，便于后续清理）

### 理念7：自顶向下与自底向上结合

设计文档不能只从仿真器源码自底向上分析（容易忽略规则语法和网站特性层面的实际问题），也不能只从修复经验自顶向下分析（容易忽略仿真器底层保真度问题）。必须两者结合。

**落地原则**：
- 自底向上：JVM源码分析发现仿真保真度限制（方向1/2/7）
- 自顶向下：修复源实际经验发现规则语法和网站特性问题（方向8新增）
- 交叉验证：修复源遇到的问题必须在设计文档中有对应方向（当前覆盖度仅30%，10个问题未覆盖）
- **已知修复模式记录**：JS补全绝对路径、og:novel meta+@put/@get、nextContentUrl分页、replaceRegex净化等模式必须系统化记录

### 理念8：AI工作流编排优先

工具链改进的最终目的是让AI更好地使用skill生成/修复书源。工具改进与AI使用之间不能存在断层——HtmlStructureAnalyzer输出建议选择器后，AI如何自动转化为规则？错误诊断输出代码示例后，AI如何自动应用？这些桥接设计是核心。

**落地原则**：
- **多轮迭代修复闭环**：测试→分析error_diagnosis→自动应用修复建议→重新测试→再分析，直到通过或达到最大迭代次数
- **建议→规则自动转换**：HtmlStructureAnalyzer输出的建议选择器，AI能自动拼装成完整的ruleSearch/ruleBookInfo字段
- **经验→自动复用桥接**：experience_manager返回相似案例后，AI能提取修复片段并注入当前源
- **工具改进必须设计AI使用方式**：每个工具改进方向都必须说明"AI如何利用这个改进提高生成成功率"

### 理念9：可信度分级

仿真器保真度89%意味着11%场景不可信。AI必须知道何时该信仿真器结果，何时需要标记"需真机验证"。

**落地原则**：
- **测试结果可信度评分**：根据规则类型（纯CSS=高可信、含JS=中可信、含加密=低可信）+保真度限制清单，输出可信度评分
- **可信度低→自动标记需真机验证**：AI不需要用户判断，系统自动标注
- **假阳性/假阴性检测**：仿真通过但涉及高保真度限制区域时，输出"⚠️ 此结果可信度中等，建议真机验证"

---

## 架构理念

### 分层解耦

```
协议层（stdin/stdout JSON）→ 服务层（JVM调试器）→ 分析层（HTML/错误诊断）→ 经验层（basic-memory）
    当前：完整                    当前：有bug          当前：缺失            当前：未集成
                                                       + 仿真保真度层（新增）  + 降级隔离（新增）
```

每层可独立测试和替换。分析层和经验层是本次新增的核心。仿真保真度层是对齐真机行为的基础保障。

### 渐进增强

| 优先级 | 方向 | 内容 |
|--------|------|------|
| P0 | 仿真保真度 | 相对路径拼接 + singleUrl bug修复 + ruleContent回退修复 |
| P0 | 仿真保真度对齐 | getSubDomain剥离www + TextUtils.isEmpty对齐 + ajax委托修复 |
| P0 | 可观测性 | HTML结构分析 + 错误诊断 + 结构化输出 |
| P1 | 经验闭环 | basic-memory集成（JSON文件+MCP外层写入） + 自动检索/写入 |
| P1 | 文档治理 | 陷阱编号统一 + mock数字更新 + MVP命名统一 + 版本锁同步 |
| P2 | 客户端优化 | JSON去重 + 超时控制 + 进化重验证参数修复 |
| P3 | 高级能力 | 自动修复 + 批量并行 + 经验去重 + 编码检测移植 |
| P0 | AI工作流编排 | 多轮迭代修复闭环 + 建议→规则自动转换 + 经验→自动复用 |
| P1 | Phase 4源码导航 | 错误类型→源码映射索引 + 真机Debug.kt对比 |
| P1 | 可信度评估 | 测试结果可信度评分 + 假阳性/假阴性检测 |
| P1 | 大规模真实源测试验证 | 10+10测试集 + 场景覆盖矩阵 + 改进前后基线对比 |
| P1 | Phase 2规则构建指导 | 解析方式决策树 + 网站类型策略 + 字段填写模板 + 方向→Phase映射 |
| P2 | 用户交互场景 | URL不可达/Cookie/登录/验证码交互 + 标准化失败报告 + 真机验证流程 |
| P2 | 性能优化与批量并行 | JVM常驻 + 多端口并行 + 性能预估 |

### 降级路径明确

| 层级 | 正常路径 | 降级路径 | 降级标记 |
|------|---------|---------|---------|
| JVM仿真器 | legado-jvm.jar | verify-source.py（覆盖率35-40%） | 输出"⚠️ JVM不可用，降级到Python仿真" |
| basic-memory | AI agent通过MCP搜索 | experience_manager.py用`pathlib.Path.rglob`搜索references/troubleshooting/ | 输出"⚠️ basic-memory不可用，降级到Python原生文件搜索" |
| basic-memory写入 | AI agent通过MCP写入 | 写入references/troubleshooting/auto/ | 添加`<!-- AUTO_GENERATED -->`标记 |
| HTML结构分析 | JVM端Jsoup解析 | Python端BeautifulSoup | 输出"⚠️ JVM端分析失败，降级到Python端" |
| WebView | Selenium委托 | 标记needsWebView + 用户介入 | 输出"⚠️ 需要WebView渲染，标记用户介入" |

---

## 源码分析方法论

> 本设计文档的所有结论均基于源码深度分析，非拍脑袋。以下是分析方法论，确保结论可追溯、可验证。

### 分析覆盖范围

| 文件 | 类型 | 行数 | 分析方法 |
|------|------|------|---------|
| debug-source.py | Python客户端 | 1018行 | 静态阅读 + 运行验证 |
| BookSourceDebugger.kt | JVM仿真器 | ~600行 | 静态阅读 + 行号验证 |
| RssSourceDebugger.kt | JVM仿真器 | ~400行 | 静态阅读 + 行号验证 |
| AnalyzeUrl.kt（仿真器） | JVM仿真器 | 960行 | 静态阅读 + 真机对比 |
| AnalyzeUrl.kt（真机） | 真机源码 | 978行 | 静态阅读 + 差异对比 |
| AnalyzeRule.kt（仿真器） | JVM仿真器 | 970行 | 静态阅读 + 真机对比 |
| AnalyzeRule.kt（真机） | 真机源码 | 973行 | 静态阅读 + 差异对比 |
| NetworkUtilsStub.kt | JVM仿真器 | 283行 | 静态阅读 + 真机对比 |
| NetworkUtils.kt（真机） | 真机源码 | 298行 | 静态阅读 + 差异对比 |
| SKILL.md | Skill文档 | ~494行 | 静态阅读 + 交叉验证 |
| AI_README.md | Skill文档 | ~220行 | 静态阅读 + 交叉验证 |
| references/6大目录 | Skill文档 | ~50个文件 | 静态阅读 + 索引验证 |

### 分析方法

1. **静态阅读**：逐行阅读源码，记录关键逻辑和行号
2. **真机对比**：仿真器源码 vs 真机源码逐方法对比，记录行为差异
3. **行号验证**：设计文档中引用的行号必须与实际源码对应（已验证全部准确，除1处：debug-source.py第318行应为第326行）
4. **交叉验证**：多文档间交叉验证（如SKILL.md说79条陷阱，troubleshooting/用分类编号，两者对比发现断裂）

### 分析局限性

- **静态分析为主**：大部分结论基于静态代码阅读，未通过运行时测试验证
- **仿真器与真机差异**：仿真器代码与真机代码存在38个差异点，部分分析结论可能受差异影响
- **未覆盖的文件**：真机Debug.kt未对比分析（仿真器BookSourceDebugger/RssSourceDebugger对应真机Debug.kt，但未做对比）
- **置信度评估**：方向1（相对路径）置信度95%（源码行号已验证）；方向7（保真度对齐）置信度85%（基于静态对比，未运行时验证）

---

## 仿真保真度限制清单

> 通过真机vs仿真器3组文件对比发现。这些限制影响仿真结果的准确性，需在设计中明确记录。

### AnalyzeUrl 保真度限制（90%）

| 严重度 | 限制 | 真机行为 | 仿真器行为 | 影响 |
|--------|------|---------|-----------|------|
| CRITICAL | JS上下文中java.ajax() | 走AnalyzeUrl自身（支持URL模板/Cookie/请求体编码） | 走JsExtensionsStub.ajax（Jsoup.connect简化请求） | AnalyzeUrl.evalJS中的ajax请求能力降级 |
| HIGH | getGlideUrl()/getMediaItem() | 支持 | 完全缺失 | 图片/视频无法仿真 |
| MEDIUM | Base64解码flags参数 | 支持URL_SAFE等flags | 简化为`flags and 8`检查 | URL_SAFE编码的Base64可能解码失败 |

### AnalyzeRule 保真度限制（92%）

| 严重度 | 限制 | 真机行为 | 仿真器行为 | 影响 |
|--------|------|---------|-----------|------|
| MEDIUM | TextUtils.isEmpty vs isNullOrBlank | isEmpty只检查null和空字符串 | isNullOrBlank还检查纯空白字符串 | 纯空白规则字符串（如"   "）处理不一致 |
| LOW | getWebJsResult线程检查 | 主线程调用抛异常 | 硬编码为false，永不抛异常 | 无法检测主线程调用WebJs的错误 |
| LOW | ajax onFailure日志 | printOnDebug() | printStackTrace() | 日志输出方式不同 |

### NetworkUtils 保真度限制（85%）

| 严重度 | 限制 | 真机行为 | 仿真器行为 | 影响 |
|--------|------|---------|-----------|------|
| CRITICAL | getSubDomain | PublicSuffixDatabase剥离www前缀+处理多级TLD | 直接返回host，不剥离www | Cookie在子域名间不共享 |
| LOW | isAvailable | ConnectivityManager检测真实网络 | 固定返回true | 无法检测网络不可用 |

### 间接差异（通过Stub依赖引入）

| 严重度 | 差异 | 影响 |
|--------|------|------|
| HIGH | BaseSourceInterface.getHeaderMap不支持@js:头部规则 | 书源header含JS时请求头不正确 |
| MEDIUM | CookieStore无持久化 | JVM重启后Cookie丢失 |
| MEDIUM | CacheManager无LRU淘汰 | 内存可能溢出 |

### 综合保真度：~89%

---

## 核心能力

| 能力 | 当前状态 | 源码依据 | 目标状态 |
|------|---------|---------|---------|
| JVM相对路径拼接 | ❌ baseUrl未传 | BookSourceDebugger.kt:117-123,215-219; RssSourceDebugger.kt:188-193,305-308,373-376 | ✅ 所有阶段传baseUrl |
| getSubDomain保真度 | ❌ 不剥离www | NetworkUtilsStub.kt:183-194 vs NetworkUtils.kt:212-223 | ✅ 剥离www前缀 |
| TextUtils保真度 | ❌ isNullOrBlank | AnalyzeRule.kt:288,294,374 vs 真机TextUtils.isEmpty | ✅ 改回isNullOrEmpty |
| ajax委托保真度 | ❌ 走Jsoup.connect | AnalyzeUrl通过JsExtensionsStub委托 | ✅ AnalyzeUrl override ajax |
| HTML结构分析 | ❌ 只收集不分析 | DebugCollector收集了HTML但generate_report只打印字符数 | ✅ 自动输出class/id+建议选择器 |
| 错误诊断 | ❌ 纯描述性 | _generate_error_suggestion只有4类且不精确 | ✅ 5类+代码示例+触发HTML分析 |
| 结构化输出 | ❌ 全靠stdout | 无--output参数 | ✅ --output report.json |
| 经验检索 | ❌ 未集成 | 无basic-memory代码 | ✅ experience_manager.py用`pathlib.Path.rglob`搜索references/ |
| 经验写入 | ❌ 未集成 | _settle_evolution只写本地文件 | ✅ 输出pending JSON文件，由AI agent外层通过MCP写入basic-memory |
| singleUrl模式 | ❌ 多处bug | RssSourceDebugger.kt:367-376未传baseUrl+未调toAbsoluteUrl | ✅ 修复所有bug |
| ruleContent回退 | ❌ 掩盖问题 | RssSourceDebugger.kt:333-339回退到html | ✅ 回退时标记"规则缺失" |
| 陷阱编号 | ❌ 断裂 | SKILL.md用#1-79，references/用章节编号 | ✅ 统一编号体系+映射表 |
| mock数字 | ❌ 过时 | 说~40个已实现，实际132个 | ✅ 与代码同步 |
| MVP命名 | ❌ 混乱 | SKILL.md说MVP4，实际无mvp4.jar | ✅ 统一为legado-jvm |
| 版本锁文档 | ❌ 不一致 | jvm-infrastructure.md说okhttp4.12.0，build.gradle.kts用5.3.2 | ✅ 文档与代码同步 |
| deep-verify状态 | ❌ 三重矛盾 | SKILL.md说可用，AI_README.md说废弃但工作流还在用 | ✅ 统一为废弃 |
| site-features索引 | ❌ 未索引 | SKILL.md参考文档索引遗漏site-features/ | ✅ 添加索引 |
| og:novel meta标签 | ❌ 未覆盖 | 修复源用og:novel meta+@put/@get但设计文档未提及 | ✅ HtmlStructureAnalyzer提取meta标签 |
| nextContentUrl分页 | ❌ 未覆盖 | PO18/衍墨轩用nextContentUrl分页但调试器未循环抓取 | ✅ BookSourceDebugger正文阶段循环抓取 |
| replaceRegex净化 | ❌ 未覆盖 | 奇书塔/PO18用replaceRegex净化正文但未验证 | ✅ 调试器验证replaceRegex效果 |
| 客户端-服务端命令 | ❌ 6个已弃用 | rule_engine_client.py调用6个已弃用命令 | ✅ 清理或标注已弃用 |
| evalJS上下文注入 | ❌ 不完整 | 仅注入result，缺java/source/baseUrl/cookie/cache | ✅ 注入完整上下文 |
| CacheManagerStub | ❌ 无LRU | 无限ConcurrentHashMap可能OOM | ✅ 添加软引用或手动清理 |
| aesEncodeToString | ❌ 行为不一致 | Stub修复了真机bug但导致不一致 | ✅ 评估影响并记录 |
| AI多轮迭代修复 | ❌ 单次测试 | 测试→看结果→人工判断如何修 | ✅ 测试→分析诊断→自动应用修复→重新测试闭环 |
| 建议→规则自动转换 | ❌ 仅参考 | HtmlStructureAnalyzer输出建议但AI需手动拼装 | ✅ 建议选择器自动转化为ruleSearch/ruleBookInfo字段 |
| 经验→自动复用 | ❌ 仅提示 | 返回相似案例但AI需人工判断如何应用 | ✅ 提取修复片段并注入当前源 |
| Phase 4源码导航 | ❌ 无导航 | AI在近千行源码中手动找根因 | ✅ 错误类型→源码文件/行号映射索引 |
| 测试可信度评分 | ❌ 无评分 | AI不知道何时该信仿真器结果 | ✅ 根据规则类型+保真度限制输出可信度评分 |
| 代码进化 | ❌ 仅写经验 | Phase 5只写basic-memory，不更新测试用例 | ✅ 新陷阱→JVM测试用例/Python检查项转化 |
| 多模式组合 | ❌ 单模式 | 8种修复模式都是单独记录 | ✅ 组合场景+优先级+依赖关系 |
| 网站改版检测 | ❌ 无检测 | 无法区分规则错误vs网站改版 | ✅ ErrorDiagnoser新增网站改版错误类型 |
| 经验冲突解决 | ❌ 无机制 | 两条经验冲突时AI不知如何选择 | ✅ 置信度评分+时效性+优先级规则 |

---

## 已知修复模式参考目录（新增）

> 基于5个修复源+衍墨轩书（搜索阶段已知失效）的实际修复经验，系统化记录常见修复模式。这些模式应在references/中新增`known-fix-patterns/`目录。

| 模式 | 适用场景 | 修复源 | 示例 |
|------|---------|--------|------|
| JS补全绝对路径 | Web Components自定义元素href；baseUrl传递修复前的兜底 | 奇书塔/中国古典/衍墨轩 | `result.indexOf('http')===0?result:'https://域名'+result` |
| og:novel meta+@put/@get | 详情页选择器失效，改用meta标签 | 奇书塔/衍墨轩 | `@put:{n:meta[property$=book_name]@content}` + `@get:{n}` |
| nextContentUrl分页 | 正文分页 | PO18/衍墨轩 | `nextContentUrl: "text.下一页@href"` |
| replaceRegex净化 | 去广告/章节标题重复 | 奇书塔/PO18 | `replaceRegex: "##（本章未完.*）"` |
| 搜索方法转换 | GET搜索返回空 | PO18 | searchUrl改为POST方法 |
| GBK编码 | GBK网站搜索关键词 | PO18 | `"charset":"gbk"` |
| 排行榜URL失效 | 网站改版导致URL变化 | 放屁音乐 | sortUrl改为搜索结果页格式 |
| 音频解析 | 音频订阅源 | 放屁音乐 | JS提取token+POST获取音频URL |

---

## 客户端-服务端命令兼容性矩阵（新增）

> rule_engine_client.py定义的方法 vs RuleEngineServer.kt支持的命令

| 客户端方法 | 服务端命令 | 状态 | 备注 |
|-----------|-----------|------|------|
| ping | ping | ✅ 可用 | |
| eval_js | evalJS | ⚠️ 可用但不完整 | 仅注入result，缺java/source/baseUrl/cookie/cache |
| eval_css | evalCSS | ❌ 已弃用 | 服务端返回错误 |
| analyze_rule | analyzeRule | ❌ 已弃用 | 服务端返回错误 |
| analyze_elements | analyzeElements | ❌ 已弃用 | 服务端返回错误 |
| decrypt | decrypt | ❌ 已弃用 | 服务端返回错误 |
| encrypt | encrypt | ❌ 已弃用 | 服务端返回错误 |
| analyze_url | analyzeUrl | ❌ 已弃用 | 服务端返回错误 |
| debug_book_source | debugBookSource | ✅ 可用 | |
| debug_rss_source | debugRssSource | ✅ 可用 | |
| batch_debug | batch | ✅ 可用 | |

---

## 行为不一致风险清单（新增）

> 仿真器与真机行为不一致的关键点，按风险等级排序

| 风险等级 | 不一致点 | 真机行为 | 仿真器行为 | 影响 |
|---------|---------|---------|-----------|------|
| CRITICAL | getSubDomain域名匹配 | PublicSuffixDatabase剥离www+多级TLD | 直接返回host不剥离 | Cookie跨阶段传递失败 |
| CRITICAL | evalJS上下文注入 | 注入java/source/baseUrl/cookie/cache | 仅注入result | JS无法调用java.ajax等 |
| HIGH | aesEncodeToString | 调用decryptStr（真机bug） | 调用encrypt（修复了bug） | 加密结果不一致 |
| HIGH | HTTP方法缺失功能 | cookieJarHeader/限流/SSL/ensureActive/AnalyzeUrl | 全部走Jsoup.connect | 复杂请求场景失败 |
| HIGH | BaseSourceInterface方法缺失 | 继承JsExtensions有77+方法 | 仅7属性+3方法 | source.login/evalJS等无法调用 |
| MEDIUM | base64Decode flags | 支持URL_SAFE/CRLF/NO_PADDING/NO_WRAP | 仅处理flag 8 | 其他flags解码失败 |
| MEDIUM | CacheManagerStub无LRU | LruCache(50M) | 无限ConcurrentHashMap | 长时间运行OOM |
| MEDIUM | androidId固定值 | 从AppConst.androidId读取 | 返回"000000000000000" | getLoginInfo AES加密key不同 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios（基于源码分析+修复经验对比，16个方向） |
| [design.md](./design.md) | 技术方案：16个方向 + 9个统一设计理念 + 18个架构决策 + 仿真保真度限制清单 + 风险预测 |
| [tasks.md](./tasks.md) | 任务清单（16个方向，150+个任务，每个有源码行号引用） |

---

## 验收标准

### P0 验收（仿真保真度 + 可观测性）

1. **相对路径拼接**：所有阶段AnalyzeUrl构造时传baseUrl，移除JS补全后5个修复源仍通过+衍墨轩书搜索阶段已知失效（网站端问题）
2. **singleUrl修复**：RssSourceDebugger.debugSingleUrl传baseUrl+调toAbsoluteUrl
3. **ruleContent回退**：回退到html时标记"规则缺失"而非掩盖
4. **HTML结构分析**：规则不匹配时输出class/id列表+建议选择器+meta标签
5. **错误诊断**：9种错误类型识别+代码示例修复建议（原5种+方向8新增3种：搜索方法错误/GBK编码错误/功能失效vs网站不可达+方向12新增1种：网站改版）
6. **结构化输出**：--output report.json导出机器可读结果
7. **getSubDomain保真度**：剥离www前缀，Cookie在子域名间共享
8. **TextUtils保真度**：isNullOrBlank改回isNullOrEmpty，与真机一致
9. **extractJsRule修复**：JS后的HTML模板被保留
10. **sortUrl警告**：未匹配时输出降级警告

### P1 验收（经验闭环 + 文档治理）

11. **经验检索**：experience_manager.py用`pathlib.Path.rglob`搜索references/troubleshooting/（≤2秒响应）
12. **经验写入**：测试通过后输出到`output/experience-pending.json`（≤5秒写入），AI agent外层通过MCP写入basic-memory
13. **降级写入隔离**：basic-memory不可用时写入references/troubleshooting/auto/，不污染权威文档
14. **陷阱编号统一**：SKILL.md速查表与references/编号一致+映射表
15. **mock数字更新**：与JsExtensionsStub.kt实际代码同步
16. **MVP命名统一**：删除MVP1-4决策树，统一为legado-jvm
17. **版本锁同步**：jvm-infrastructure.md与build.gradle.kts版本号一致
18. **deep-verify统一**：SKILL.md和AI_README.md统一为废弃
19. **site-features索引**：SKILL.md参考文档索引添加site-features/

### P2 验收（客户端优化）

20. **JSON去重**：source_json只解析1次（当前5次）
21. **超时控制**：--timeout参数控制JVM调试超时+安全终止机制
22. **进化重验证**：完整传递--import-cookie和--force参数
23. **batch_debug传参**：完整传递webview_handler参数
24. **阶段命名统一**：STAGE_NAMES统一为字符串键
25. **stages解析降级**：支持→/->/, 三种分隔符

### P2 验收（方向8：已知修复模式 + 方向9：命令兼容性）

26. **known-fix-patterns目录**：references/known-fix-patterns/包含8种修复模式文档
27. **meta标签提取**：HtmlStructureAnalyzer提取`<meta property="og:*">`标签
28. **标签名统计**：HtmlStructureAnalyzer统计Web Components自定义元素（如mdui-list-item）
29. **ErrorDiagnoser扩展**：新增3种错误类型（搜索方法错误/GBK编码错误/功能失效vs网站不可达）
30. **basic-memory陷阱纳入**：#46（||回退选择器）和#47（@CSS:前缀）纳入ErrorDiagnoser建议
31. **known-fix-patterns索引**：SKILL.md参考文档索引包含known-fix-patterns/
32. **命令清理**：rule_engine_client.py中6个已弃用命令已清理或标注
33. **evalJS上下文注入**：注入java/source/baseUrl/cookie/cache，JS可调用java.ajax
34. **CacheManagerStub LRU**：添加软引用或手动清理，长时间运行不OOM
35. **aesEncodeToString评估**：行为不一致影响已评估并记录

### P0 验收（方向10：AI工作流编排）

36. **多轮迭代修复闭环**：测试→分析诊断→自动应用修复→重新测试，最多3轮迭代
37. **建议→规则自动转换**：HtmlStructureAnalyzer建议选择器可自动转化为ruleSearch/ruleBookInfo字段
38. **经验→自动复用**：experience_manager返回相似案例后，AI可提取修复片段注入当前源
39. **代码进化**：Phase 5新陷阱可转化为JVM测试用例或Python检查项

### P1 验收（方向11：Phase 4源码导航 + 方向12：可信度评估）

40. **源码导航索引**：错误类型→真机源码文件/行号映射索引建立
41. **真机Debug.kt对比**：仿真器Debug流程与真机Debug.kt差异分析完成
42. **可信度评分**：测试结果输出可信度评分（高/中/低）
43. **假阳性检测**：仿真通过但涉及高保真度限制区域时输出警告
44. **多模式组合**：known-fix-patterns/包含组合场景+优先级+依赖关系
45. **网站改版检测**：ErrorDiagnoser新增网站改版错误类型
46. **经验冲突解决**：经验笔记包含置信度评分+时效性+优先级规则

### P1 验收（方向13：大规模真实源测试验证）

47. **测试集构建**：10个书源+10个订阅源覆盖15+种场景（纯CSS/含JS/含加密/含ajax/登录/验证码/GBK/音频/视频/SSR反爬/Web Components/nextContentUrl/replaceRegex/og:novel/singleUrl）
48. **基线采集**：改进前20个测试源跑完，输出基线报告（通过率、失败原因分布、人工介入次数）
49. **改进后效果验证**：通过率提升≥20%、人工介入减少≥50%
50. **建议选择器准确率**：HtmlStructureAnalyzer输出的建议选择器≥80%可直接采用
51. **错误类型覆盖率**：20个源的错误≥90%能被9种类型识别
52. **多轮迭代修复成功率**：20个源中≥12个能在3轮内自动修复通过

### P1 验收（方向14：Phase 2规则构建指导）

53. **解析方式决策树**：给定网站分析结果，ParseStrategySelector返回正确解析方式
54. **规则字段模板**：模板覆盖ruleSearch/ruleBookInfo/ruleToc/ruleContent所有字段
55. **方向→Phase映射表**：16个方向全部映射到正确的Phase

### P2 验收（方向15：用户交互 + 方向16：性能）

56. **URL不可达交互**：网站不可达时输出标准化交互请求（类型+消息+建议+需用户提供的信息）
57. **Cookie请求交互**：检测到需登录时输出Cookie请求+获取指南
58. **失败报告**：3轮迭代失败后输出标准化报告（错误类型+已尝试修复+当前规则JSON+真机验证步骤）
59. **JVM常驻模式**：--persistent参数启用后，JVM进程常驻，多次测试不重启
60. **多端口并行**：20源并行（4 worker）总耗时≤串行的1/3
