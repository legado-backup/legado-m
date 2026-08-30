# Spec: 源修复闭环优化

## Intent

基于对客户端1018行Python源码、JVM仿真服务端15个Kotlin文件、skill 6大参考目录、以及**真机vs仿真器3组文件对比**的深度分析，发现80+个真实痛点。本项目系统性修复这些痛点，使工具链从"假通过+手动修复"进化为"真通过+半自动修复+经验自积累"。

核心目标：
1. **仿真保真度**：JVM仿真器行为对齐真机（相对路径拼接、错误处理、singleUrl模式、getSubDomain、TextUtils）
2. **可观测性**：让问题可见（HTML结构分析、错误诊断、结构化输出）
3. **经验闭环**：通过JSON文件+MCP外层写入实现自动检索+写入（当前完全未集成，违反AGENTS.md）
4. **文档治理**：消除矛盾信息（陷阱编号断裂、mock数字过时、MVP命名混乱、版本锁不一致）

## Scope

### IN-SCOPE（16个方向）

**方向1：JVM仿真器相对路径拼接（P0）**
- 修复BookSourceDebugger搜索/详情阶段AnalyzeUrl未传baseUrl（BookSourceDebugger.kt:117-123,215-219）
- 修复RssSourceDebugger列表/内容/singleUrl阶段AnalyzeUrl未传baseUrl（RssSourceDebugger.kt:188-193,305-308,373-376）
- 修复RssSourceDebugger.debugSingleUrl未调用toAbsoluteUrl（RssSourceDebugger.kt:367-376）
- 修复AnalyzeRule.getString(isUrl=true)的redirectUrl未设置问题
- **注意**：RssSourceDebugger列表阶段第180行和内容阶段第303行已有toAbsoluteUrl预处理，传baseUrl的真正价值是让JS代码中能访问baseUrl变量（AnalyzeUrl.kt:362 `bindings["baseUrl"] = baseUrl`）

**方向2：JVM仿真器可观测性（P0）**
- 新增HtmlStructureAnalyzer：规则不匹配时自动输出class/id列表+建议选择器
- 修复ruleContent空时回退到html掩盖规则缺失（RssSourceDebugger.kt:333-339）
- 修复extractJsRule丢失HTML模板（RssSourceDebugger.kt:59-68）
- 修复sortUrl未匹配降级到第一个条目无警告（RssSourceDebugger.kt:161-166）
- **扩展触发条件**：不仅bookList.isEmpty()时触发，详情页name为空、目录页chapterList为空、正文页content为空时也触发

**方向3：Python客户端优化（P0/P2）**
- 新增--output report.json结构化输出（当前全靠stdout）
- 新增--timeout JVM调试超时控制+安全终止机制（当前可能永久阻塞）
- 修复JSON重复解析5次（第536,775,788,812,159行）
- 修复进化重验证丢失--import-cookie和--force参数（第977-985行）
- 修复batch_debug未传webview_handler（第646-651行）
- 统一STAGE_NAMES三套命名体系（数字键/字符串键/箭头分隔）

**方向4：经验闭环自动化（P1）**
- 新增experience_manager.py：测试前检索basic-memory + 测试后写入经验
- **basic-memory访问方式（AD-5修正）**：debug-source.py输出经验数据到JSON文件（`output/experience-pending.json`），由AI agent外层通过MCP工具（`mcp_basic-memory_write_note`）写入basic-memory。Python脚本不直接调用MCP或CLI。
- **原因**：basic-memory是MCP服务器（提供MCP工具），不是CLI命令行工具，Python脚本无法通过subprocess调用
- 降级路径：basic-memory不可用时，experience_manager.py用Python原生文件搜索（`pathlib.Path.rglob`，非grep命令，Windows兼容）
- **降级写入隔离**：写入references/troubleshooting/auto/（独立目录），添加`<!-- AUTO_GENERATED -->`标记，不污染权威文档
- 经验去重：写入前搜索basic-memory检查是否已存在相似经验

**方向5：错误诊断增强（P0）**
- 扩展错误类型从4种到5种（新增编码错误）
- 每种错误类型提供代码示例修复建议
- 规则不匹配时自动触发HTML结构分析（依赖方向2的2.1完成）
- 修复网络错误正则不精确（第326行'connect'匹配过宽，改为'connect timed out|ConnectException'）

**方向6：Skill文档治理（P1）**
- 统一陷阱编号：SKILL.md速查表与references/编号一致+建立映射表
- 更新mock数字：mock-unimplemented-functions.md与JsExtensionsStub.kt同步（当前说40实际132）
- 统一MVP命名：删除MVP1-4决策树，统一为legado-jvm
- 统一jar路径：3处文档统一为legado-jvm/build/libs/legado-jvm.jar
- 统一deep-verify.py状态：明确废弃
- 在SKILL.md参考文档索引中添加site-features/
- **版本锁同步**：jvm-infrastructure.md的okhttp/gson版本与build.gradle.kts一致
- **special-scenarios索引修复**：_index.md添加遗漏的rss-core-diff.md
- **脚本声明完整性**：为18个未声明脚本添加状态标注（active/deprecated/experimental）

**方向7：JVM仿真保真度对齐（P0）**
- 修复getSubDomain不剥离www前缀（NetworkUtilsStub.kt:183-194 vs NetworkUtils.kt:212-223）
- 修复TextUtils.isEmpty替换为isNullOrBlank（AnalyzeRule.kt:288,294,374）
- 修复AnalyzeUrl上下文中ajax走Jsoup.connect而非AnalyzeUrl（AnalyzeUrl通过JsExtensionsStub委托）
- 修复BaseSourceInterface.getHeaderMap不支持@js:头部规则
- **已知限制保留**：getGlideUrl/getMediaItem缺失（P3）、CookieStore无持久化（P3）、CacheManager无LRU（P3）

**方向8：已知修复模式参考目录（P1）**
- 在references/中新增`known-fix-patterns/`目录，系统化记录5个修复源+衍墨轩书（搜索阶段已知失效）的实际修复模式
- 记录8种已知修复模式：JS补全绝对路径、og:novel meta+@put/@get、nextContentUrl分页、replaceRegex净化、搜索方法转换、GBK编码、排行榜URL失效、音频解析
- 每种模式包含：适用场景、修复源示例、代码片段、注意事项
- 扩展HtmlStructureAnalyzer：新增meta标签提取（`<meta property="og:*">`）和标签名统计（Web Components自定义元素）
- 扩展ErrorDiagnoser：新增3种错误类型（搜索方法错误、GBK编码错误、功能失效vs网站不可达区分）
- 将basic-memory陷阱#46（||回退选择器）和#47（@CSS:前缀）纳入ErrorDiagnoser建议

**方向9：客户端-服务端命令兼容性+evalJS上下文（P0/P1）**
- 清理rule_engine_client.py中6个已弃用命令方法（eval_css/analyze_rule/analyze_elements/decrypt/encrypt/analyze_url），标注已弃用或删除
- 修复RuleEngineServer.kt evalJS命令上下文注入不完整（仅注入result，缺java/source/baseUrl/cookie/cache）
- 修复CacheManagerStub无LRU淘汰机制（添加软引用或手动清理，防止长时间运行OOM）
- 评估aesEncodeToString行为不一致的影响（Stub修复了真机bug但导致不一致），记录为已知限制或保持与真机一致
- 修复RuleEngineClient无超时处理（使用select.select或threading.Timer实现非阻塞读取）
- **注意**：basic-memory CLI工具不存在（是MCP服务器不是CLI），方向4改为方案A：debug-source.py输出经验数据到JSON文件，由AI agent外层通过MCP工具写入basic-memory

**方向10：AI工作流编排层（P0）**
- 设计多轮迭代修复闭环：测试→分析error_diagnosis→自动应用修复建议→重新测试→再分析，最多3轮迭代
- 设计建议选择器→规则字段自动转换：HtmlStructureAnalyzer输出建议后，AI自动拼装成完整的ruleSearch/ruleBookInfo
- 设计经验→自动复用桥接：experience_manager返回相似案例后，AI提取修复片段并注入当前源
- 设计代码进化流程：Phase 5新陷阱→JVM仿真器测试用例/Python验证脚本检查项转化
- 设计多模式组合应用：一个源同时需要多个修复模式时的优先级和依赖关系

**方向11：Phase 4源码导航工具（P1）**
- 建立"错误类型→真机源码文件/行号"映射索引（如"相对路径问题→NetworkUtils.kt:getAbsoluteURL"）
- 在references/source-analysis/中补充"错误诊断→源码定位"快速查找表
- 补充真机Debug.kt对比分析（仿真器BookSourceDebugger/RssSourceDebugger vs 真机Debug.kt）
- 设计保真度限制清单→Phase 4触发条件（如evalJS上下文不完整CRITICAL→JS错误直接进Phase 4）

**方向12：仿真器可信度评估（P1）**
- 设计测试结果可信度评分：根据规则类型（纯CSS=高可信、含JS=中可信、含加密=低可信）+保真度限制清单
- 设计可信度低→自动标记需真机验证的流程
- 设计假阳性/假阴性检测启发式规则
- 设计经验冲突解决：置信度评分+时效性+优先级规则
- 设计网站改版检测：ErrorDiagnoser新增网站改版错误类型（URL结构变化、选择器全部失效）

**方向13：大规模真实源测试验证（P1）**
- 从项目可用源（13,166书源+974 RSS源）中选取10个书源+10个订阅源作为测试集
- 测试源选择标准：覆盖15+种场景（纯CSS/含JS/含加密/含ajax/登录/验证码/GBK编码/音频/视频/SSR反爬/Web Components/nextContentUrl分页/replaceRegex净化/og:novel meta/singleUrl模式）
- 改进前基线采集：用当前工具链跑20个测试源，记录通过率、失败原因分布、人工介入次数
- 改进后效果验证：用改进后工具链跑相同20个测试源，对比通过率提升、人工介入减少
- 新增能力效果验证：HtmlStructureAnalyzer建议选择器准确率、ErrorDiagnoser错误类型覆盖率、经验自动检索命中率、多轮迭代修复成功率
- 测试源维护机制：定期验证测试源可用性，网站改版时更新或替换

**方向14：Phase 2规则构建指导（P1）**
- 新增references/rule-construction-guide/目录，包含从零构建规则的模板和检查清单
- 五种解析方式选择决策树：CSS（简单结构）/JSONPath（API响应）/XPath（复杂XML/HTML）/正则（文本提取）/JS（动态渲染/加密）
- 不同网站类型规则构建策略：小说站/漫画站/音频站/视频站/论坛站
- 规则字段填写指南：ruleSearch/ruleBookInfo/ruleToc/ruleContent各字段的填写模板
- 方向→Phase映射表：明确每个方向属于哪个Phase的改进

**方向15：用户交互场景设计（P2）**
- URL不可达交互：AI向用户报告网站不可达，请求新URL或确认迁移
- Cookie请求交互：AI检测到需登录时，向用户请求Cookie并注入书源header
- 搜索关键词确认：AI推荐搜索关键词或向用户确认
- 登录场景交互：AI检测到登录页面时请求用户凭证或Cookie
- 验证码场景交互：AI检测到验证码时请求用户手动处理
- 失败报告格式：标准化失败报告（错误类型+已尝试修复+当前规则JSON+需用户提供的信息）

**方向16：性能优化与批量并行（P2）**
- JVM常驻模式：JVM进程常驻+stdin/stdout通信，避免每次测试重启JVM
- 多端口并行：多端口启动多个JVM实例+任务队列分配，支持批量并行测试
- 性能预估：单源测试耗时估算（JVM启动+各阶段调试+HTML分析）、20源串行/并行总耗时
- HTML分析性能决策：对风险18（截断丢失关键结构）做出最终决策

### OUT-OF-SCOPE

- WebView支持（已完成）
- 批量并行调试（P3，后续迭代）
- 自动修复（P3，后续迭代）
- CMS样本库扩充（P3，后续迭代）
- Cookie/Cache持久化（P3，后续迭代）
- 编码检测增强（EncodingDetect移植）（P3，后续迭代）
- getGlideUrl/getMediaItem JVM替代（P3，后续迭代）
- PublicSuffixDatabase完整移植（P3，本次仅手动剥离www前缀）

## Approach

### 方向1：相对路径拼接

**根因**：AnalyzeUrl构造时baseUrl参数默认为空字符串（AnalyzeUrl.kt:81），NetworkUtilsStub.getAbsoluteURL(baseUrl="", url)直接返回url不拼接（NetworkUtilsStub.kt:131）。

**方案**：在BookSourceDebugger和RssSourceDebugger的所有阶段构造AnalyzeUrl时传入baseUrl：
- 搜索阶段：baseUrl = source.bookSourceUrl / source.sourceUrl
- 详情阶段：baseUrl = source.bookSourceUrl / source.sourceUrl
- 目录阶段：已传book.bookUrl（正确）
- 正文阶段：已传book.bookUrl（正确）
- RSS列表阶段：baseUrl = source.sourceUrl（注意：第180行已有toAbsoluteUrl预处理，传baseUrl让JS可访问baseUrl变量）
- RSS内容阶段：baseUrl = source.sourceUrl（注意：第303行已有toAbsoluteUrl预处理）
- RSS singleUrl阶段：baseUrl = source.sourceUrl + 调用toAbsoluteUrl

同时修复AnalyzeRule的redirectUrl设置：调试器在每阶段开始前调用analyzeRule.setRedirectUrl(baseUrl)。

**注意**：setContent(html, response.url)已设置了baseUrl，setRedirectUrl是额外保障，确保getString(isUrl=true)能拼接相对路径。两者不冲突——setContent设置content的baseUrl，setRedirectUrl设置URL拼接的baseUrl。

### 方向2：可观测性

**HTML结构分析**：新增HtmlStructureAnalyzer.kt，用Jsoup解析HTML，提取class/id+出现次数，基于常见模式建议选择器。在BookSourceDebugger和RssSourceDebugger中，当bookList.isEmpty()/articleList.isEmpty()时自动触发。**扩展**：详情页name为空、目录页chapterList为空、正文页content为空时也触发。

**ruleContent回退修复**：RssSourceDebugger.kt:333-339回退到html时，标记"⚠️ ruleContent为空，回退到整个HTML（规则缺失）"而非静默通过。

**extractJsRule修复**：保留JS执行结果与后续HTML模板的串联，而非截断。

### 方向3：客户端优化

**结构化输出**：新增--output参数，将调试结果导出为JSON（包含success/stages/html_sources/error_diagnosis/experience）。

**超时控制**：新增--timeout参数，传递给RuleEngineClient的readline调用，超时后安全终止JVM进程（先发shutdown命令，等待3秒，再强制destroy）。

**JSON去重**：在main()入口解析一次source_json为source_obj，后续所有地方使用source_obj。

### 方向4：经验闭环

**basic-memory访问方式**（AD-5决策修正版）：debug-source.py输出经验数据到JSON文件（`output/experience-pending.json`），由AI agent外层通过MCP工具（`mcp_basic-memory_write_note`）写入basic-memory。Python脚本不直接调用MCP或CLI。

**测试前检索**：experience_manager.py用`pathlib.Path.rglob`搜索references/troubleshooting/中的相似案例（Windows兼容，非grep命令）。

**测试后写入**：测试通过后提取修复模式（错误类型→修复方案→测试结果），输出到`output/experience-pending.json`，由AI agent外层通过MCP工具写入basic-memory。

**降级路径**：basic-memory不可用时，experience_manager.py用Python原生文件搜索（`pathlib.Path.rglob`，非grep命令，Windows兼容）。

**降级写入隔离**：写入references/troubleshooting/auto/目录，添加`<!-- AUTO_GENERATED -->`标记。

### 方向5：错误诊断

**9种错误类型**：相对路径、网站不可达、规则不匹配、JS执行错误、编码错误、搜索方法错误、GBK编码错误、功能失效vs网站不可达区分、网站改版。

**触发HTML分析**：规则不匹配时自动触发HtmlStructureAnalyzer（依赖方向2的2.1完成）。

### 方向6：文档治理

**陷阱编号统一**：在references/troubleshooting/的每个子文档中添加"#编号"标记，与SKILL.md速查表对应。建立映射表（SKILL.md #1-79 ↔ troubleshooting/ 分类编号1.1-5.6）。

**mock数字更新**：重新统计JsExtensionsStub.kt的override fun数量，更新mock-unimplemented-functions.md。

**版本锁同步**：jvm-infrastructure.md的okhttp版本从4.12.0更新为5.3.2，gson从"未使用"更新为2.13.2。

### 方向7：仿真保真度对齐

**getSubDomain修复**：在NetworkUtilsStub.getSubDomain中手动剥离www前缀（`if (host.startsWith("www.")) host.substring(4) else host`）。完整PublicSuffixDatabase移植为P3。

**TextUtils.isEmpty对齐**：将AnalyzeRule.kt中的isNullOrBlank改回isNullOrEmpty（3处：第288,294,374行），与真机TextUtils.isEmpty行为一致。

**ajax委托修复**：在AnalyzeUrl中override ajax方法，委托AnalyzeUrl自身构造请求而非走JsExtensionsStub.ajax。

**getHeaderMap修复**：BaseSourceInterface.getHeaderMap支持@js:头部规则，委托AnalyzeRule.evalJS执行。

## Requirements

### REQ-1：相对路径拼接正确性
- 所有阶段AnalyzeUrl构造时传baseUrl
- 移除JS补全后，5个修复源仍通过测试+衍墨轩书搜索阶段已知失效（网站端问题）
- AnalyzeRule.getString(isUrl=true)的redirectUrl正确设置

### REQ-2：HTML结构分析准确性
- 正确提取HTML中的所有class和id
- 统计出现次数
- 建议选择器准确率≥80%
- 所有阶段（搜索/详情/目录/正文/列表/内容）规则不匹配时都触发

### REQ-3：结构化输出完整性
- --output report.json包含：success/stages/html_sources/error_diagnosis/experience
- AI可直接解析JSON获取结果，不依赖stdout文本

### REQ-4：经验闭环自动化
- 测试前通过experience_manager.py用`pathlib.Path.rglob`搜索references/troubleshooting/（≤2秒响应）
- 测试通过后输出到`output/experience-pending.json`（≤5秒写入），由AI agent外层通过MCP写入basic-memory
- basic-memory不可用时降级到Python原生文件搜索（`pathlib.Path.rglob`，Windows兼容）
- 降级写入到references/troubleshooting/auto/，不污染权威文档

### REQ-5：错误诊断覆盖率
- 9种错误类型识别（原5种+方向8新增3种：搜索方法错误/GBK编码错误/功能失效vs网站不可达+方向12新增1种：网站改版）
- 每种类型有代码示例修复建议
- 规则不匹配时自动触发HTML结构分析（依赖方向2完成）

### REQ-6：文档一致性
- SKILL.md速查表编号与references/一致+映射表
- mock数字与JsExtensionsStub.kt代码同步
- jar路径3处文档统一
- jvm-infrastructure.md版本号与build.gradle.kts一致
- deep-verify.py状态在SKILL.md和AI_README.md统一
- site-features/在SKILL.md参考文档索引中列出
- special-scenarios/_index.md包含rss-core-diff.md

### REQ-7：仿真保真度对齐
- getSubDomain剥离www前缀
- TextUtils.isEmpty行为与真机一致（isNullOrEmpty）
- AnalyzeUrl上下文中ajax走AnalyzeUrl而非Jsoup.connect
- BaseSourceInterface.getHeaderMap支持@js:头部规则

### REQ-8：已知修复模式参考目录（方向8）
- references/known-fix-patterns/目录包含8种修复模式文档
- HtmlStructureAnalyzer提取`<meta property="og:*">`标签
- HtmlStructureAnalyzer统计Web Components自定义元素（如mdui-list-item）
- ErrorDiagnoser新增3种错误类型（搜索方法错误/GBK编码错误/功能失效vs网站不可达）
- basic-memory陷阱#46（||回退选择器）和#47（@CSS:前缀）纳入ErrorDiagnoser建议
- SKILL.md参考文档索引包含known-fix-patterns/

### REQ-9：客户端-服务端命令兼容性（方向9）
- rule_engine_client.py中6个已弃用命令已清理或标注（eval_css/analyze_rule/analyze_elements/decrypt/encrypt/analyze_url）
- evalJS命令注入完整上下文（java/source/baseUrl/cookie/cache）
- CacheManagerStub添加软引用或手动清理机制（防止OOM）
- aesEncodeToString行为不一致影响已评估并记录

### REQ-10：超时控制Windows兼容性（方向9）
- RuleEngineClient使用select.select或threading.Timer实现非阻塞读取（Windows兼容）
- 超时后先发shutdown命令，等待3秒，再强制destroy

### REQ-11：AI多轮迭代修复闭环（方向10）
- 测试→分析error_diagnosis→自动应用修复建议→重新测试，最多3轮迭代
- HtmlStructureAnalyzer建议选择器可自动转化为ruleSearch/ruleBookInfo字段
- experience_manager返回相似案例后，AI可提取修复片段注入当前源
- Phase 5新陷阱可转化为JVM测试用例或Python检查项

### REQ-12：Phase 4源码导航（方向11）
- 错误类型→真机源码文件/行号映射索引建立
- 真机Debug.kt对比分析完成
- 保真度限制清单→Phase 4触发条件明确

### REQ-13：仿真器可信度评估（方向12）
- 测试结果输出可信度评分（高/中/低）
- 仿真通过但涉及高保真度限制区域时输出假阳性警告
- 经验笔记包含置信度评分+时效性+优先级规则
- ErrorDiagnoser新增网站改版错误类型

### REQ-14：大规模真实源测试验证（方向13）
- 选取10个书源+10个订阅源作为测试集，覆盖15+种场景
- 改进前基线采集：记录通过率、失败原因分布、人工介入次数
- 改进后效果验证：通过率提升≥20%、人工介入减少≥50%
- HtmlStructureAnalyzer建议选择器准确率≥80%
- ErrorDiagnoser错误类型覆盖率≥90%（20个源的错误都能被9种类型识别）
- 多轮迭代修复成功率≥60%（20个源中≥12个能在3轮内自动修复通过）

**测试集清单（从项目12,180个源中筛选，15/15场景全覆盖）**：

| # | 类型 | 源名称 | 覆盖场景 | 难度 |
|---|------|--------|---------|------|
| 1 | 书源 | PO18文学 | gbk_encoding, next_content_url, replace_regex | 中等 |
| 2 | 书源 | 全英文学（英） | contains_encrypt, ssr_anti_crawl | 困难 |
| 3 | 书源 | 狸猫故事（优+） | contains_js, contains_encrypt, login_required, audio_parse, replace_regex, og_novel_meta | 困难 |
| 4 | 书源 | 三月天吧 | pure_css, web_components, next_content_url, og_novel_meta | 中等 |
| 5 | 书源 | 追书网吧 | contains_js, contains_encrypt, contains_ajax, login_required, captcha, next_content_url, replace_regex, og_novel_meta | 困难 |
| 6 | 书源 | 奇书塔 | web_components, contains_js, og_novel_meta, replace_regex | 中等 |
| 7 | 书源 | 乐乎文章（优） | contains_js, contains_encrypt, contains_ajax, login_required, video_parse, next_content_url, replace_regex | 困难 |
| 8 | 书源 | 中国古典 | pure_css | 简单 |
| 9 | 书源 | 哔哩轻小说（优） | contains_js, contains_encrypt, contains_ajax, login_required, next_content_url, replace_regex, og_novel_meta | 困难 |
| 10 | 书源 | 衍墨轩书 | replace_regex, next_content_url | 中等 |
| 11 | RSS | 日式jk | contains_encrypt, contains_ajax, captcha | 困难 |
| 12 | RSS | ©集芳阁® | pure_css, single_url_mode | 中等 |
| 13 | RSS | ©HylTV | contains_encrypt, contains_ajax, login_required, audio_parse, video_parse | 困难 |
| 14 | RSS | Hanime1 | contains_js, contains_encrypt, contains_ajax, login_required, video_parse | 困难 |
| 15 | RSS | 喵公子 | single_url_mode | 中等 |
| 16 | RSS | 放屁音乐 | audio_parse, contains_js | 中等 |
| 17 | RSS | 微博博主 | contains_js, contains_encrypt, contains_ajax, login_required, video_parse | 困难 |
| 18 | RSS | 微博搜索 | contains_js, contains_encrypt, contains_ajax, login_required, video_parse | 困难 |
| 19-20 | RSS | (从社区源中补充2个覆盖缺失场景的源) | 待定 | 待定 |

> 测试集JSON文件：`temp/test-book-sources.json` + `temp/test-rss-sources.json`
> 筛选脚本：`temp/select-test-sources.py`（从12,180个源中按场景覆盖矩阵贪心选取）

### REQ-15：Phase 2规则构建指导（方向14）
- references/rule-construction-guide/目录包含5种解析方式决策树
- 包含5种网站类型规则构建策略
- 包含ruleSearch/ruleBookInfo/ruleToc/ruleContent字段填写模板
- 方向→Phase映射表明确每个方向属于哪个Phase

### REQ-16：用户交互场景设计（方向15）
- URL不可达时AI向用户报告并请求新URL
- 需登录时AI向用户请求Cookie并注入书源header
- 失败报告包含错误类型+已尝试修复+当前规则JSON+需用户提供的信息
- 真机验证流程：可信度"低"时输出真机验证步骤报告

### REQ-17：性能优化与批量并行（方向16）
- JVM常驻模式：避免每次测试重启JVM
- 多端口并行：支持批量并行测试（20源并行总耗时≤串行的1/3）
- 性能预估：单源测试耗时估算+20源串行/并行总耗时
- HTML分析性能决策：对风险18做出最终决策（建议"只分析body直接子元素"）

## Scenarios

### Scenario 1：相对路径自动拼接
```
Given: 书源bookUrl规则是 a@href，网站返回 /honglou.html
When: JVM仿真器调试搜索阶段（BookSourceDebugger.kt:117-123）
Then: AnalyzeUrl构造时传入baseUrl=source.bookSourceUrl，自动拼接为绝对URL
```

### Scenario 2：HTML结构分析
```
Given: 测试失败，文章列表为空（bookList.isEmpty()）
When: JVM仿真器触发HtmlStructureAnalyzer
Then: 输出 "class列表: book-card(24次)、author(24次)、title(24次) + 建议选择器: 书籍列表→class.book-card"
```

### Scenario 3：结构化输出
```
Given: AI执行 python debug-source.py --source xxx.json --output report.json
When: 调试完成
Then: report.json包含 {success: true, stages: ["search","detail","toc","content"], html_sources: {...}, error_diagnosis: null}
```

### Scenario 4：经验自动检索
```
Given: 测试中国古典书源前
When: experience_manager.py用pathlib.Path.rglob搜索references/troubleshooting/
Then: 返回 "相似案例：奇书塔（相对路径问题，JS补全绝对路径修复）"
```

### Scenario 5：经验自动写入
```
Given: 中国古典书源修复后测试通过
When: debug-source.py输出经验数据到output/experience-pending.json
Then: AI agent外层通过MCP工具写入basic-memory，包含错误类型+修复方案+测试结果
```

### Scenario 6：错误诊断+修复建议
```
Given: 测试失败，错误信息是 "Expected URL scheme 'http'"
When: ErrorDiagnoser分析错误
Then: 输出 "错误类型：相对路径问题。修复建议：在bookUrl中用JS补全绝对路径 [代码示例]"
```

### Scenario 7：singleUrl模式修复
```
Given: 喵公子订阅源singleUrl=true
When: JVM仿真器调试singleUrl模式
Then: AnalyzeUrl构造时传baseUrl=source.sourceUrl，调用toAbsoluteUrl，不报"订阅源URL为空"
```

### Scenario 8：ruleContent回退标记
```
Given: 订阅源ruleContent为空
When: JVM仿真器回退到html
Then: 输出 "⚠️ ruleContent为空，回退到整个HTML（规则缺失）"，而非静默通过
```

### Scenario 9：getSubDomain保真度
```
Given: 书源sourceUrl是 https://www.example.com，Cookie设置在 www.example.com
When: JVM仿真器请求 m.example.com 子域名
Then: getSubDomain剥离www前缀返回 example.com，Cookie在子域名间共享
```

### Scenario 10：TextUtils保真度
```
Given: 书源规则字符串是 "   "（纯空格）
When: JVM仿真器解析规则
Then: isNullOrEmpty与真机TextUtils.isEmpty行为一致（返回true，不继续解析）
```

### Scenario 11：降级写入隔离
```
Given: basic-memory不可用，测试通过需要写入经验
When: experience_manager降级写入
Then: 写入references/troubleshooting/auto/目录，添加<!-- AUTO_GENERATED -->标记，不污染权威文档
```

### Scenario 12：版本锁同步
```
Given: AI需要重建legado-jvm.jar
When: AI查阅jvm-infrastructure.md获取依赖版本
Then: okhttp版本为5.3.2（与build.gradle.kts一致），gson版本为2.13.2（与build.gradle.kts一致）
```

### Scenario 13：已知修复模式检索（方向8）
```
Given: AI遇到Web Components自定义元素（如mdui-list-item）href为相对路径
When: AI查阅references/known-fix-patterns/
Then: 找到"JS补全绝对路径"模式，包含适用场景、修复源示例（奇书塔/中国古典/衍墨轩）、代码片段
```

### Scenario 14：meta标签提取（方向8）
```
Given: 书源详情页选择器失效，网站使用og:novel meta标签
When: HtmlStructureAnalyzer分析HTML
Then: 输出 "meta标签: og:novel:book_name(1次)、og:novel:author(1次) + 建议使用@put/@get模式"
```

### Scenario 15：命令兼容性清理（方向9）
```
Given: rule_engine_client.py调用eval_css命令
When: AI执行debug-source.py
Then: 输出 "⚠️ eval_css已弃用，请使用debug_book_source或debug_rss_source"，而非服务端返回错误
```

### Scenario 16：evalJS上下文注入（方向9）
```
Given: 书源JS规则调用java.ajax("https://api.example.com/data")
When: RuleEngineServer.kt执行evalJS命令
Then: 注入完整上下文（java/source/baseUrl/cookie/cache），java.ajax可正常执行
```

### Scenario 17：AI多轮迭代修复（方向10）
```
Given: AI生成书源后测试失败，error_diagnosis输出"规则不匹配+建议选择器class.book-card"
When: AI自动应用建议选择器修改ruleSearch，重新测试
Then: 第2轮测试通过，无需人工介入
```

### Scenario 18：建议→规则自动转换（方向10）
```
Given: HtmlStructureAnalyzer输出"建议选择器: 书籍列表→class.book-card(24次)"
When: AI自动转换建议为规则字段
Then: ruleSearch.bookList = "class.book-card@tag.li" 自动生成，AI只需验证
```

### Scenario 19：Phase 4源码导航（方向11）
```
Given: AI遇到JS执行错误，需要深入源码找根因
When: AI查阅"错误类型→源码映射索引"
Then: 返回"JS执行错误→RuleEngineServer.kt:evalJS 第128行 + 真机AnalyzeRule.kt:evalJS 第X行"，快速定位
```

### Scenario 20：可信度评估（方向12）
```
Given: 书源规则包含JS+加密，仿真器测试通过
When: 可信度评估引擎计算评分
Then: 输出"可信度: 低（含JS+加密，保真度限制区域）→ ⚠️ 建议真机验证"
```

### Scenario 21：大规模测试基线对比（方向13）
```
Given: 选取10个书源+10个订阅源，覆盖15+种场景
When: 改进前用当前工具链跑20个测试源
Then: 记录基线数据（通过率X%、失败原因分布、人工介入N次），作为改进后对比基准
```

### Scenario 22：改进后效果验证（方向13）
```
Given: 方向1-12改进完成后
When: 用改进后工具链跑相同20个测试源
Then: 通过率提升≥20%、人工介入减少≥50%、多轮迭代修复成功率≥60%
```

### Scenario 23：用户交互-Cookie请求（方向15）
```
Given: AI检测到网站需要登录（返回登录页面）
When: AI向用户请求Cookie
Then: 用户提供Cookie后，AI注入到书源header，重新测试通过
```

### Scenario 24：失败报告+用户介入（方向15）
```
Given: 3轮迭代修复失败
When: AI输出标准化失败报告
Then: 报告包含错误类型+已尝试修复列表+当前规则JSON+需用户提供的信息，用户介入后从第1轮重新开始
```

## 风险预测

### 风险1：JVM与真机编码处理差异
- **问题**：JVM用OkHttp默认编码检测，真机用EncodingDetect。GBK/GB2312网站可能乱码
- **影响**：中编码网站测试结果与真机不一致
- **应对**：本次不在scope内（P3），但记录为已知限制

### 风险2：Cookie持久化缺失
- **问题**：JVM重启后Cookie丢失，需要登录的网站每次都要重新登录
- **影响**：登录场景测试不可重复
- **应对**：本次不在scope内（P3），CookieStoreStub保持内存实现

### 风险3：并发调试冲突
- **问题**：多个debug-source.py同时运行可能JVM端口冲突
- **影响**：批量测试时无法并行
- **应对**：本次不在scope内（P3），保持串行

### 风险4：经验库膨胀
- **问题**：自动写入经验可能导致低质量经验污染
- **影响**：经验检索结果变差
- **应对**：经验去重（写入前搜索basic-memory检查是否已存在）+ 质量评估（测试通过才写入）

### 风险5：HTML结构分析准确性
- **问题**：基于常见模式的选择器建议可能不准确
- **影响**：AI根据错误建议修改后仍可能不通过
- **应对**：建议选择器只是辅助，AI仍需验证；标注"建议"而非"确定"

### 风险6：修改JVM仿真器可能引入新bug
- **问题**：修改AnalyzeUrl构造参数可能影响已有功能
- **影响**：回归测试不通过
- **应对**：修改后运行5个修复源回归测试+衍墨轩书搜索阶段已知失效（网站端问题），确保不引入新问题；修改前备份JAR

### 风险7：降级写入污染skill文档
- **问题**：basic-memory不可用时降级写入references/troubleshooting/会污染权威文档
- **影响**：文档质量下降，与6.2任务（添加编号标记）冲突
- **应对**：降级写入到独立目录references/troubleshooting/auto/，添加`<!-- AUTO_GENERATED -->`标记

### 风险8：--timeout与JVM进程管理交互
- **问题**：超时后强制终止JVM进程可能导致资源泄漏（网络连接未关闭）
- **影响**：JVM进程残留或端口占用
- **应对**：先发shutdown命令，等待3秒，再强制destroy；超时后检查端口是否释放

### 风险9：大HTML性能影响
- **问题**：正文页HTML可能几十KB到几百KB，Jsoup.parse()性能需评估
- **影响**：调试变慢
- **应对**：限制HTML分析只在规则不匹配时触发（非每次都解析）；大HTML截断前100KB

### 风险10：经验写入格式未定义
- **问题**：没有定义经验笔记的结构化格式
- **影响**：检索困难，basic-memory全文搜索可能返回不相关结果
- **应对**：定义固定Markdown模板（错误类型/修复方案/测试结果/源URL/日期）

### 风险11：Cookie跨阶段持久化
- **问题**：baseUrl修复后Cookie的domain可能变化（从www.xxx.com变为xxx.com）
- **影响**：搜索阶段获取的Cookie在详情阶段可能不匹配
- **应对**：验证baseUrl修复后Cookie跨阶段传递是否正确

### 风险12：真机Debug.kt对比分析缺失
- **问题**：设计文档未对比仿真器代码与真机Debug.kt的差异
- **影响**：仿真器Debug流程可能与真机不一致（如真机Debug.kt是否在搜索阶段传baseUrl？setRedirectUrl何时调用？）
- **应对**：本次记录为已知限制，后续迭代补充真机Debug.kt对比分析

### 风险13：SSR网站反爬（新增）
- **问题**：Nuxt.js/Next.js等SSR网站的`/?page=`路径可能有反爬（403+JS重定向）
- **影响**：AI遇到SSR反爬时不知道改用首页URL或API端点
- **应对**：在known-fix-patterns/中记录SSR反爬模式；ErrorDiagnoser新增"SSR反爬"检测

### 风险14：音频解析场景（新增）
- **问题**：音频订阅源的ruleContent用JS提取token+POST请求获取音频URL
- **影响**：音频订阅源无法完整验证（java.ajax POST能力需验证）
- **应对**：在known-fix-patterns/中记录音频解析模式；验证ajax委托修复后POST能力

### 风险15：CacheManagerStub内存溢出（新增）
- **问题**：CacheManagerStub使用无限ConcurrentHashMap，无LRU淘汰
- **影响**：长时间批量调试可能OOM
- **应对**：方向9添加软引用或手动清理机制

### 风险16：ajax override递归调用（新增）
- **问题**：方向7.3在AnalyzeUrl中override ajax方法，内部构造新AnalyzeUrl可能触发递归
- **影响**：StackOverflowError
- **应对**：在override ajax中添加防递归检查，或确保新构造的AnalyzeUrl不触发ajax override

### 风险17：回归测试标准不现实（新增）
- **问题**：修复源中衍墨轩书搜索功能已失效（网站端问题，POST/GET均返回"找不到内容"）
- **影响**：回归测试"全部通过"标准不可能达到
- **应对**：回归测试标准改为"5个源通过+衍墨轩书搜索阶段已知失效（网站端问题，非工具链问题）"

### 风险18：HtmlStructureAnalyzer大HTML截断丢失关键结构（新增）
- **问题**：截断前100KB可能丢失正文区域的class/id（正文页HTML可能几百KB）
- **影响**：建议选择器不准确
- **应对**：改为"截断后保留头部+尾部各50KB"或"只分析body直接子元素"
