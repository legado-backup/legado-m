# Spec: Legado Source Creator Skill 优化

> **状态**: 🔄 设计中（v8 - 自进化沉淀闭环+经验质量标准+初始化经验审计+陷阱去站点化）

## Intent

legado-source-creator skill 经多轮反哺积累，存在大量孤岛。本次优化**更彻底地删除孤岛**：删除JVM仿真器、删除Python Playwright脚本、**删除整个legado_client Python客户端**（AI不使用Python库）、移除basic-memory引用。SKILL.md重写为"AI手动操作"工作流。新增网站分析报告作为AI工作笔记。**新增经验检索机制和源码阅读步骤**确保AI在经验不足时能主动查找经验或阅读开源阅读源码。核心目标：**让AI使用skill干活时越干越顺手**。

## Scope

### 本次实现

1. **删除孤岛**：JVM仿真器 + Python Playwright脚本 + **legado_client整个Python客户端** + 过时缓存 + 冗余脚本 + basic-memory引用
2. **SKILL.md重写**：frontmatter + Phase 2-4从"Python脚本"改为"AI手动操作+ai_tests脚本" + 陷阱迁移 + 瘦身<200行
3. **新增网站分析报告**：AI自驱工作笔记，聚焦"规则映射建议"，按源类型分目录存放
4. **references整理**：删JVM文档 + 合并重叠 + ≤25文档
5. **新增经验检索机制**：AI在Phase 1主动检索两源（references知识库 + output/ai_source/已生成源JSON）。**v8修正**：删除"ai_memory_main.md项目记忆"作为经验源——项目记忆内容是项目代码任务状态/用户反馈，与写源规则无关，无参考价值
6. **新增视频订阅源核心要求指引**：搜索js/图片必填/内置播放器嗅探/多线路多集js的快速了解入口
7. **新增源码阅读步骤**：经验都不足时AI按指引阅读开源阅读源码（只读不改）
8. **★新增自进化沉淀闭环**（v8）：AI从源码阅读/陷阱修复/Playwright分析中发现新范式，反哺到 references/ 对应文档，实现 skill 越用越智能
9. **★新增经验沉淀质量标准**（v8）：经验必须按通用范式抽象（如"动态域名解析"），禁止按站点分类（如"站点A经验"），避免经验膨胀爆炸
10. **★初始化经验完整性审计**（v8）：审计 JsExtensions.kt 全方法覆盖率 + Rhino 兼容性速查表 + JS 执行环境差异集中化（Rhino vs WebView）
11. **★陷阱库去站点化重构**（v8）：陷阱40-57标题改按问题类型分类，"铁证"部分脱敏（站点代号→通用描述，具体URL→路径模式）

### 不在本次实现

- **🔴 禁止修改项目源码**：本次优化只修改 `.trae/skills/legado-source-creator/` 目录内文件，**严禁修改项目源码**（app/ 模块下的 Kotlin/Java/XML 等代码）。源码仅用于阅读理解规则引擎行为
- 不修改ai_tests/脚本（测试手段已成熟）

## Approach

### Selected Approach

**更彻底地删 + SKILL.md重写为AI手动操作 + 经验检索+源码阅读闭环**：
1. 删除全部孤岛（JVM仿真器/Python Playwright/legado_client/basic-memory引用/冗余脚本）
2. SKILL.md重写：Phase 1=Playwright MCP分析+经验检索→输出报告；Phase 2=AI手动写JSON+对照必填清单；Phase 3=ai_tests脚本真机验证；Phase 4=AI根据陷阱库手动修复
3. 报告模板聚焦"规则映射建议"（直接映射源JSON字段）
4. references整理
5. **经验检索两源机制**（v8修正）：Phase 1 主动检索 references/知识库 + output/ai_source/ 已生成源JSON。**删除 ai_memory_main.md 项目记忆作为经验源**（项目记忆内容与写源规则无关）
6. **视频订阅源核心要求快速了解入口**：SKILL.md新增"视频订阅源核心要求速查"章节
7. **源码阅读步骤**：SKILL.md新增"源码验证"步骤（经验都不足时按指引阅读开源阅读源码，只读不改）
8. **★自进化沉淀闭环**（v8新增）：发现新范式→更新 references/ 对应文档→下次检索命中。新范式来源：源码阅读/陷阱修复/Playwright分析
9. **★经验沉淀质量标准**（v8新增）：通用范式抽象 + 脱敏案例，禁止按站点分类
10. **★初始化经验完整性审计**（v8新增）：JsExtensions.kt 全方法 + Rhino 兼容性速查表 + JS 执行环境差异集中化
11. **★陷阱库去站点化重构**（v8新增）：陷阱40-57标题改按问题类型分类，"铁证"部分脱敏

理由：AI实际工作流程中从不import legado_client——AI用Write工具手动写JSON，对照SKILL.md必填字段清单手动校验，用ai_tests/scripts/脚本（RunCommand）真机验证。legado_client Python库是误导性孤岛。同时AI需要经验检索和源码阅读能力来应对未知问题。

### Alternatives Considered

| 方案 | 描述 | 否决理由 |
|------|------|----------|
| v4方案（保留legado_client） | 仅删JVM/Python Playwright | legado_client也是孤岛，AI不使用Python库 |
| 全量重写 | 从零重建 | 丢失57+陷阱经验 |
| 仅删孤岛不重写工作流 | 只删不改SKILL.md工作流 | SKILL.md仍引用Python代码，误导AI |
| 仅删孤岛不增经验检索 | 只删不改工作流+不增检索 | AI失去basic-memory后无经验检索能力，遇未知问题无法应对 |
| 不增源码阅读步骤 | 只靠经验检索 | 经验都不足时AI无应对路径，无法理解新规则 |
| 保留项目记忆作为经验源（v8否决） | 将 ai_memory_main.md 作为经验检索源 | 项目记忆内容是项目代码任务状态/用户反馈，与写源规则无关，无参考价值。且会误导AI关注项目代码任务而非写源规则 |
| 不增自进化沉淀闭环（v8否决） | 只读不写，经验无反哺机制 | AI从源码阅读/陷阱修复发现的新范式无法沉淀，下次遇到同类问题需重新分析，skill无法越用越智能 |
| 经验按站点分类（v8否决） | 陷阱按"站点A/B/C/D经验沉淀"分类 | 经验膨胀爆炸（每新增站点新增条目），AI检索路径不匹配（AI按问题类型检索而非按站点检索），且铁证引用具体站点代号违反输出安全规范 |
| 不审计初始化经验完整性（v8否决） | 保留现状，JS支持语法/JsjExtensions方法覆盖不审计 | AI写JS规则时可能使用Rhino不支持的语法或未文档化的方法，导致运行时错误；JS执行环境差异（Rhino vs WebView）分散在多文档，AI易混淆 |

### Drawbacks

1. **失去Python自动校验/修复能力**：legado_client的validator/auto_fixer被删。接受理由：AI手动校验（对照清单）+ 手动修复（根据陷阱库）实际更灵活，且AI从未使用过Python校验器
2. **报告模板简化后信息可能不足**：聚焦规则映射可能遗漏关键上下文。接受理由：规则映射是核心，其他信息AI可在Playwright分析过程中直接获取
3. **源码阅读步骤可能耗时**：阅读开源阅读源码需时间。接受理由：仅在经验都不足时才走此路径，且AI可通过 docs/project-flow/architecture/ 已有架构文档快速定位源码

## Requirements

### REQ-01: 删除JVM仿真器
删除 tools/legado-jvm/ + rhino-1.8.1.jar + references/jvm-infrastructure.md + mock-unimplemented-functions.md。

### REQ-02: 删除Python Playwright脚本
删除 fetch_html.py + html_fetcher.py + 对应测试。网站分析统一用Playwright MCP。

### REQ-03: 删除legado_client整个Python客户端
删除 scripts/legado_client/ 整个目录。AI不使用Python库——Phase 2 AI用Write手动写JSON+对照必填清单，Phase 3用ai_tests/scripts/，Phase 4 AI根据陷阱库手动修复。SKILL.md移除所有legado_client引用。

### REQ-04: 移除basic-memory引用
SKILL.md移除basic-memory操作章节。项目记忆已迁移到ai_memory_main.md。

### REQ-05: SKILL.md重写为AI手动操作工作流
- Phase 1: Playwright MCP分析 + **经验检索两源** → 输出网站分析报告
- Phase 2: AI手动写JSON（Write工具）+ 对照必填字段清单校验 + sanitize（AI自己不写None）
- Phase 3: ai_tests/scripts/脚本真机验证（RunCommand）
- Phase 4: AI根据陷阱库手动修复+重测
- 移除所有Python代码块（sanitize_source_json/validate_source/auto_fixer_loop等）

### REQ-06: 新增网站分析报告（AI工作笔记）
- 存放：书源→output/ai_source/book/，订阅源→output/ai_source/rss/，与源JSON同名
- **核心章节：规则映射建议**（sourceUrl/searchUrl/sortUrl/ruleArticles/ruleTitle/ruleLink/ruleContent/ruleImage等字段建议值）
- 辅助章节：站点信息/域名分析/页面结构/搜索/分类/分页/视频播放/反爬/验证清单
- 目的：防上下文压缩丢失数据；AI自驱使用；AI基于报告快速生成源JSON

### REQ-07: SKILL.md frontmatter + 瘦身<200行
含name+description frontmatter。保留：核心原则、4阶段工作流（AI手动操作）、必填字段清单、Top 10速查、工具索引。57+陷阱迁移至references/troubleshooting/。

### REQ-08: references整理
删JVM文档 + 合并重叠 + 统一索引命名 + ≤25文档 + 自进化去重。

### REQ-09: 识别并删除其他孤岛
审查scripts/根目录脚本、tools/根目录脚本、test-data/、templates/，删除孤岛。

### REQ-10: 新增经验检索两源机制（v6新增，v8修正删除项目记忆源）★核心
SKILL.md Phase 1 新增"经验检索两源"步骤，AI在Playwright分析前/中主动检索：
1. **源1：references/知识库**：用 Grep/SearchCodebase 搜索 references/ 目录下85+文档（陷阱库/JS模式/特殊场景/已知修复模式/规则构建指南）
2. **源2：output/ai_source/ 已生成源JSON**：Glob output/ai_source/{book,rss}/ 找同类已生成源JSON作为参考模板

**v8删除源**：~~ai_memory_main.md 项目记忆~~（项目记忆内容是项目代码任务状态/用户反馈，与写源规则无关，无参考价值）

**检索时机**：
- Phase 1 Playwright分析前：先检索是否有同类站点经验
- Phase 4 修复时：失败后检索同类失败案例的修复方案

**检索输出**：在网站分析报告的"规则映射建议"章节标注经验来源（如 `[经验来源:陷阱41嗅探模式]`、`[经验来源:动态域名修复范式]`）。**v8要求**：经验来源标注必须用通用范式名（如"动态域名修复""平衡括号算法"），禁止用站点代号

### REQ-11: 新增视频订阅源核心要求快速了解入口（v6新增，v7修正嗅探优先级）★核心
SKILL.md 新增"视频订阅源核心要求速查"章节（位于"核心原则"之后），让AI快速了解视频订阅源的关键规则要求：

1. **搜索js**：searchUrl 支持 `<js>` 标签JS执行（陷阱45/53），动态域名站点必须用JS解析实际域名
2. **图片必填**：ruleImage 必填（用户"优秀好用"标准），视频/图片类RSS源设置 articleStyle=2 网格布局避免图片加载失败白屏（陷阱36）
3. **内置播放器嗅探能力**（v7修正优先级）：ruleContent 设为空字符串 `""` 时，Legado 内置播放器自动嗅探播放页视频地址（陷阱41）。**嗅探是兜底方案而非首选**，视频地址提取优先级见 REQ-14：CMS API > JS提取 > XPath/CSS > 嗅探兜底
4. **多线路多集写js**：ruleRoutes/ruleEpisodes 用 MacCMS 标准解析模式（陷阱31），vod_play_from 解析线路（`$$$`分隔），vod_play_url 解析集数（`$$$`分隔线路+`#`分隔集数+`$`分隔标题和URL）。多线路多集按需采集架构详见 references/source-analysis/multiline-on-demand-extraction.md
5. **适配开源阅读的js**：所有JS必须Rhino兼容（陷阱44/55）：不用 padStart/模板字符串/箭头函数，java.ajax()返回值必须 String() 显式转换

**章节形式**：表格 + 关键陷阱编号引用 + 链接到 references/ 对应文档

### REQ-12: 新增AI快速了解规则入口（v6新增）
SKILL.md 在"核心原则"之后新增"快速入门"章节，让AI首次使用skill时快速了解全貌：
1. **3分钟了解规则引擎**：链接到 references/rule-syntax.md + references/rule-construction-guide/
2. **视频订阅源核心要求速查**（REQ-11）
3. **书源核心要求速查**：链接到 references/booksource-schema.md
4. **必填字段清单**：CRITICAL/MANDATORY/RECOMMENDED 三级（已有，保留）
5. **Top 10 陷阱速查**：已有，保留

### REQ-13: 新增源码阅读步骤（v6新增）★核心
SKILL.md Phase 1 新增"源码验证"步骤（经验检索两源都不足时启用）：
1. **触发条件**：经验检索两源都无同类经验 + 陷阱库无相关案例
2. **阅读范围**（只读不改）：
   - 规则引擎源码：`app/src/main/java/io/legado/app/model/analyzeRule/` （AnalyzeRule/AnalyzeUrl/RuleAnalyzer）
   - RSS源码：`app/src/main/java/io/legado/app/data/entities/RssSource.kt` + `app/src/main/java/io/legado/app/model/rss/` （Rss/RssParserByRule/RssSearchModel）
   - 书源源码：`app/src/main/java/io/legado/app/data/entities/BookSource.kt` + `app/src/main/java/io/legado/app/model/webBook/`
   - JS扩展：`app/src/main/java/io/legado/app/help/JsExtensions.kt`
3. **快捷入口**：优先阅读 docs/project-flow/architecture/ 已有架构文档（rule-engine.md/rule-engine-algorithms.md/rule-engine-js-env.md/rss-subsystem.md）
4. **输出**：在网站分析报告的"规则映射建议"章节标注 `[源码验证:RssSource.kt#ruleRoutes字段]`
5. **🔴 禁止修改源码**：只读不写，所有规则适配通过源JSON字段实现，不通过修改项目源码实现

### REQ-14: 新增用户偏好/AI进化偏好优先级机制（v7新增）★核心
SKILL.md 新增"用户偏好/AI进化偏好优先级"章节（位于"视频订阅源核心要求速查"之后），明确各种规则的优先级顺序，AI按优先级递进尝试，高优先级失败才降级到低优先级：

1. **视频地址提取优先级**（修正REQ-11嗅探描述）：
   - 优先级1：CMS API（MacCMS等标准API `ac=detail&ids={id}` 返回JSON含视频地址，陷阱28/30/31）
   - 优先级2：JS提取（API不可用时，用JS从HTML提取 player_data/player_aaaa 等变量，陷阱56平衡括号算法）
   - 优先级3：XPath/CSS（从HTML标签直接提取 `<video>` 标签的 src）
   - 优先级4：嗅探兜底（ruleContent="" 让内置播放器自动嗅探，适用于无法用规则提取的复杂场景，陷阱41）

2. **搜索URL优先级**：
   - 优先级1：API搜索（MacCMS `ac=list&wd={{key}}` 标准接口，陷阱28）
   - 优先级2：HTML搜索（API禁用时切换 `/search/{{key}}.html` 模式，陷阱29）

3. **图片提取优先级**（ruleImage）：
   - 优先级1：CSS选择器（`img@src` 或 `img@data-original`）
   - 优先级2：JS提取（CSS失败时用JS从 lazy-load 属性提取）
   - 优先级3：正则（最后兜底）

4. **列表提取优先级**（ruleArticles/ruleBookList）：
   - 优先级1：CSS选择器（最稳定，如 `div.cell_box`）
   - 优先级2：XPath（CSS不支持时）
   - 优先级3：JS（最后兜底，注意陷阱47 ruleArticles JS会影响列表页）

5. **域名处理优先级**：
   - 优先级1：固定域名（sourceUrl 直接用固定域名）
   - 优先级2：meta refresh 跳转（入口域名返回HTML含 meta refresh，陷阱50/52）
   - 优先级3：JS redirect（入口域名JS生成实际域名，陷阱57 seededRandom方案）

6. **详情页→播放页URL转换优先级**：
   - 优先级1：`##` 操作符字符串替换（`a@href##info##play`，陷阱40/49）
   - 优先级2：JS提取（`##` 无法处理时用JS正则提取）

**章节形式**：6个优先级表格 + 优先级编号 + 陷阱编号引用 + 链接到 references/ 对应文档
**AI使用方式**：AI在Phase 2写规则时按优先级递进尝试，高优先级失败才降级，并在报告"规则映射建议"标注 `[偏好优先级:视频地址提取P1-CMS API]`

### REQ-15: 初始化经验完整性审计（v8新增）★核心
**审计目标**：确保 skill 初始化经验齐全，AI首次使用时即可获得完整的 JS 规则编写参考。审计范围：

1. **JsExtensions.kt 全方法覆盖率审计**：
   - 读取 `app/src/main/java/io/legado/app/help/JsExtensions.kt`，提取所有 `@JavascriptInterface` 注解方法
   - 对照 `references/js-extensions/` 现有文档，标记缺失方法
   - 补齐缺失方法的文档（函数签名+参数+返回值+示例+Rhino兼容性）

2. **Rhino 兼容性速查表**（新建 `references/js-extensions/rhino-compat-cheatsheet.md`）：
   - ES5 支持的语法（var/function/正则字面量/基本运算）
   - ES6+ 不支持的语法（let/const/箭头函数/模板字符串/padStart/includes/Promise/async-await/解构/扩展运算符）
   - 替代写法对照表（`includes` → `indexOf>-1` / `padStart` → 手动补零 / 模板字符串 → 字符串拼接）
   - 类型转换陷阱（java.ajax() 返回值必须 String() 显式转换 / NativeArray 实现 List / NativeObject 属性访问）

3. **JS 执行环境差异集中化**（新建 `references/js-extensions/js-env-diff.md`）：
   - 集中化现有分散的执行环境差异文档（shouldOverrideUrlLoading/injectJs/loginCheckJs/ruleArticles JS/evalJS）
   - 表格对比：Rhino vs WebView 的 API 可用性（document/window/localStorage/cookie/cache/java/result/source）
   - 绑定变量清单（各执行环境绑定的变量列表）
   - 返回值类型约束（loginCheckJs 必须返回 StrResponse / ruleArticles JS 必须返回 NativeArray）

### REQ-16: 陷阱库去站点化重构（v8新增）★核心
**重构目标**：消除陷阱库按站点分类导致的经验膨胀，改为按问题类型分类，符合 AI 按问题检索的路径。重构范围：

1. **陷阱40-57标题重构**：
   - 现状：陷阱标题按"站点A经验沉淀""站点B经验沉淀"分类
   - 目标：改为按问题类型分类（如"动态域名解析""平衡括号算法""Rhino类型转换""##操作符URL替换"）
   - 保留陷阱编号不变，仅改标题和分类

2. **"铁证"部分脱敏**：
   - 现状：铁证引用具体站点代号（站点A/B/C/D/E）和具体URL路径
   - 目标：站点代号→通用描述（"某聚合视频站点"），具体URL→路径模式（`/path/{id}`）
   - 保留技术结论（错误码/异常类型/调用栈/DOM选择器），删除业务数据

3. **经验来源标注通用化**（配合 REQ-10）：
   - 现状：`[经验来源:站点D修复v4]`
   - 目标：`[经验来源:动态域名修复范式]` 或 `[经验来源:平衡括号算法]`

## Scenarios

### SCN-01: AI使用优化后的skill干活
- Phase 1: Playwright MCP分析网站 + 经验检索两源 → 输出报告到output/ai_source/
- Phase 2: AI读取报告→手动写源JSON（Write工具）→对照必填清单校验
- Phase 3: RunCommand执行ai_tests/scripts/真机验证
- Phase 4: 失败→AI查陷阱库→手动修复→重测
- 全程无Python代码，AI自驱完成

### SCN-02: 上下文压缩后恢复
- 压缩后AI读取output/ai_source/下的分析报告→恢复全部分析数据→继续生成源JSON

### SCN-03: 删除孤岛后体量
- SKILL.md 498行→<200行；references 85文档→≤25；scripts删除legado_client；tools删除JVM

### SCN-04: AI遇到未知问题查源码（v6新增）
- Phase 1 经验检索两源都无同类经验 → 触发源码阅读步骤
- AI阅读 docs/project-flow/architecture/rule-engine.md 了解规则引擎行为
- AI阅读 RssSource.kt/Rss.kt 源码理解字段含义（只读不改）
- AI基于源码理解在报告"规则映射建议"标注 `[源码验证:xxx]`
- AI基于源码理解生成源JSON
- **v8闭环**：发现新范式后，AI主动更新 references/ 对应文档（自进化沉淀）

### SCN-05: AI制作视频订阅源（v6新增）
- AI读取"视频订阅源核心要求速查"快速了解5大要求（搜索js/图片必填/嗅探/多线路多集js/Rhino兼容）
- AI按REQ-11指引写规则：ruleContent="" 嗅探 + ruleRoutes/ruleEpisodes MacCMS标准解析 + searchUrl `<js>` 动态域名
- 失败时查陷阱41/45/53/55/56/57等视频源专项陷阱

### SCN-06: AI自进化沉淀新范式（v8新增）★核心
- 场景：AI在源码阅读/陷阱修复/Playwright分析中发现新范式（如新的动态域名解析算法/新的反爬绕过方案）
- AI按经验沉淀质量标准（REQ-15/AD-15）抽象为通用范式（禁止按站点分类）
- AI更新 references/ 对应文档（troubleshooting/ 或 special-scenarios/ 或 js-patterns/）
- AI在 references/_INDEX.md 的"自进化指引"章节登记新经验
- 下次遇到同类问题时，AI通过经验检索两源命中该经验，无需重新分析
- **效果**：skill 越用越智能，新范式持续沉淀
