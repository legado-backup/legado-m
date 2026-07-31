# Tasks: Legado Source Creator Skill 优化

> **状态**: 🔄 设计中（v8 - 自进化沉淀闭环+经验质量标准+初始化经验审计+陷阱去站点化）
> **核心目标**: 让AI使用skill干活时越干越顺手（AI自驱视角）
> **v8 关键变化**: 在v7基础上新增 ①删除经验检索项目记忆源(AD-09改两源) ②自进化沉淀闭环(AD-14) ③经验沉淀质量标准(AD-15) ④初始化经验完整性审计(REQ-15) ⑤陷阱库去站点化重构(REQ-16) ⑥删除1.1备份任务(用户已备份)

## 1. Phase 1 - 删除全部孤岛

> **v8说明**：原1.1备份任务已删除（用户已自行备份skill目录）

### 1.2 删除JVM仿真器（REQ-01, AD-01）
- [ ] 1.2.1 删除 `tools/legado-jvm/` 整个目录
- [ ] 1.2.2 删除 `tools/rhino-1.8.1.jar`
- [ ] 1.2.3 删除 `references/jvm-infrastructure.md`
- [ ] 1.2.4 删除 `references/mock-unimplemented-functions.md`

### 1.3 删除Python Playwright脚本（REQ-02, AD-02）
- [ ] 1.3.1 删除 `scripts/legado_client/utils/fetch_html.py`
- [ ] 1.3.2 删除 `scripts/legado_client/utils/html_fetcher.py`
- [ ] 1.3.3 删除 `scripts/legado_client/tests/test_fetch_html.py`
- [ ] 1.3.4 删除 `scripts/legado_client/tests/test_html_fetcher.py`

### 1.4 删除legado_client整个Python客户端（REQ-03, AD-05）★v5新增
- [ ] 1.4.1 删除 `scripts/legado_client/` 整个目录（含 validator/runtime/analyzer/utils/experience/delegate/tests 等所有子模块）
- [ ] 1.4.2 Grep SKILL.md 确认无 `legado_client` import 残留引用
- [ ] 1.4.3 Grep references/ 确认无 `legado_client` 引用

### 1.5 删除过时缓存
- [ ] 1.5.1 删除 `tools/.fix-cache/`

### 1.6 审查 scripts/根目录脚本孤岛（REQ-09）
- [ ] 1.6.1 Grep SKILL.md 确认哪些 scripts/根目录脚本被引用
- [ ] 1.6.2 逐个审查未引用脚本（analyze_site.py / debug-source.py / deep-analyze-js.py / generate-js-doc.py / generate_tianlai_source.py / inspect_rss_schema.py / quick-verify.py / validate_tianlai_source.py / verify-decrypt.py / verify-image.py / verify-selector.py / verify-source.py）
- [ ] 1.6.3 删除确认孤岛脚本

### 1.7 审查 tools/根目录脚本孤岛（REQ-09）
- [ ] 1.7.1 Grep 确认哪些 tools/根目录脚本被 SKILL.md/scripts 引用
- [ ] 1.7.2 逐个审查未引用工具（cookie_manager.py / degradation_chain.py / error_translator.py / knowledge_matcher.py / smart_http_client.py / user_action_minimizer.py / workflow_timer.py）
- [ ] 1.7.3 删除确认孤岛工具

### 1.8 审查 test-data/ 和 templates/（REQ-09）
- [ ] 1.8.1 检查 test-data/ 是否被任何脚本引用
- [ ] 1.8.2 检查 templates/ 现有内容是否被SKILL.md引用（保留待新增报告模板）
- [ ] 1.8.3 删除未引用的

### 1.9 移除basic-memory引用（REQ-04, AD-08）★v5新增
- [ ] 1.9.1 Grep SKILL.md 查找 `basic-memory` 引用位置
- [ ] 1.9.2 Grep references/ 查找 `basic-memory` 引用位置
- [ ] 1.9.3 删除/替换basic-memory引用（项目记忆已迁移到 ai_memory_main.md）

### 1.10 统计
- [ ] 1.10.1 统计删除的文件/目录数量和体量

## 2. Phase 2 - SKILL.md重写 + 报告模板 + 经验检索+源码阅读

### 2.1 frontmatter + 瘦身（REQ-07）
- [ ] 2.1.1 添加YAML frontmatter（name + description，≤200字符）
- [ ] 2.1.2 验证 SKILL.md < 200行（v6因新增4章节可放宽到≤220行）

### 2.2 陷阱整理
- [ ] 2.2.1 陷阱分类映射：将陷阱1-57按问题类型分类，标记Top 10速查
- [ ] 2.2.2 陷阱迁移：非Top 10陷阱迁移至 references/troubleshooting/ 对应子文档
  - [ ] 2.2.2.1 新建 video-source-traps.md（视频订阅源专项）
  - [ ] 2.2.2.2 新建 dynamic-domain-traps.md（动态域名）
  - [ ] 2.2.2.3 更新 rhino-js-traps.md（追加Rhino类型转换）
  - [ ] 2.2.2.4 新建 import-verify-traps.md（导入验证）
  - [ ] 2.2.2.5 迁移批量源完善陷阱至 source-type-traps.md
- [ ] 2.2.3 消除重复陷阱（40+49 / 52+53 / 41+49）
- [ ] 2.2.4 修正陷阱45（删除错误原结论）

### 2.3 SKILL.md工作流重写为AI手动操作（REQ-05, AD-06）★v5核心
- [ ] 2.3.1 Phase 1重写：Playwright MCP分析 → 输出网站分析报告（无Python代码）
- [ ] 2.3.2 Phase 2重写：AI手动写JSON（Write工具）+ 对照必填字段清单校验 + sanitize（AI自己不写None）
- [ ] 2.3.3 Phase 3重写：ai_tests/scripts/脚本真机验证（RunCommand执行）
- [ ] 2.3.4 Phase 4重写：AI根据陷阱库手动修复 + 重测
- [ ] 2.3.5 移除所有Python代码块（sanitize_source_json / validate_source / auto_fixer_loop / validate_source_on_device 等）
- [ ] 2.3.6 Python代码块替换为：必填字段清单表格 + Playwright JS提取模板 + ai_tests脚本调用命令

### 2.4 移除过时引用
- [ ] 2.4.1 移除JVM仿真器相关内容（能力边界表 / 降级路径 / JVM引用）
- [ ] 2.4.2 移除Python Playwright脚本引用
- [ ] 2.4.3 移除legado_client所有引用（import / 函数调用 / 路径引用）★v5新增
- [ ] 2.4.4 移除basic-memory操作章节 ★v5新增

### 2.5 新增"网站分析报告"章节（REQ-06, AD-03, AD-07）
- [ ] 2.5.1 SKILL.md新增"网站分析报告"章节（Phase 1输出产物说明）
- [ ] 2.5.2 说明报告存放路径（书源→output/ai_source/book/，订阅源→output/ai_source/rss/，与源JSON同名）
- [ ] 2.5.3 说明报告核心章节为"规则映射建议"（直接映射源JSON字段）
- [ ] 2.5.4 说明报告为AI自驱工作笔记（防上下文压缩丢失数据）

### 2.6 新建报告模板（REQ-06, AD-07）★v5简化
- [ ] 2.6.1 新建 `templates/site-analysis-report.md`
- [ ] 2.6.2 章节结构（规则映射为核心）：
  - [ ] 2.6.2.1 **规则映射建议**（核心章节）：sourceUrl / searchUrl / sortUrl / ruleArticles / ruleTitle / ruleLink / ruleContent / ruleImage / ruleRoutes / ruleEpisodes 等字段建议值 + **经验来源标注字段**（v6新增）
  - [ ] 2.6.2.2 站点基本信息（代号/类型/CMS类型）
  - [ ] 2.6.2.3 域名分析（入口/实际域名/跳转方式/动态域名算法）
  - [ ] 2.6.2.4 页面结构（列表/详情/播放页URL模式）
  - [ ] 2.6.2.5 搜索功能（搜索URL/表单/结果选择器）
  - [ ] 2.6.2.6 分类功能（分类列表/URL模式）
  - [ ] 2.6.2.7 分页（下一页选择器）
  - [ ] 2.6.2.8 视频播放（视频源专用：播放页结构/视频地址提取方式）
  - [ ] 2.6.2.9 反爬分析（CF/Cookie/登录）
  - [ ] 2.6.2.10 验证清单（需真机验证项）

### 2.7 新增经验检索两源机制（REQ-10, AD-09）★v6核心（v8修正删除项目记忆源）
- [ ] 2.7.1 SKILL.md Phase 1 前新增"Phase 0: 经验检索两源"步骤说明
- [ ] 2.7.2 写明源1：references/知识库检索（Grep/SearchCodebase 工具用法+关键词示例）
- [ ] 2.7.3 写明源2：output/ai_source/ 已生成源JSON检索（Glob 找同类源模板）
- [ ] 2.7.4 写明检索时机（Phase 1 分析前 + Phase 4 修复时）
- [ ] 2.7.5 写明检索输出格式（报告"规则映射建议"标注 `[经验来源:通用范式名]`，**v8禁止用站点代号**）
- [ ] 2.7.6 **v8删除**：原2.7.3 项目记忆源（ai_memory_main.md 内容与写源规则无关，无参考价值）

### 2.8 新增视频订阅源核心要求速查章节（REQ-11, AD-10）★v6核心（v7修正嗅探优先级）
- [ ] 2.8.1 SKILL.md "核心原则"之后新增"视频订阅源核心要求速查"章节
- [ ] 2.8.2 写明5大要求表格：
  - [ ] 2.8.2.1 搜索js：searchUrl 支持 `<js>` 标签（陷阱45/53引用）
  - [ ] 2.8.2.2 图片必填：ruleImage 必填 + articleStyle=2 网格布局（陷阱36引用）
  - [ ] 2.8.2.3 内置播放器嗅探能力（v7修正）：ruleContent="" 触发嗅探是**兜底方案而非首选**，视频地址提取优先级见 2.11 偏好优先级（陷阱41引用）
  - [ ] 2.8.2.4 多线路多集写js：ruleRoutes/ruleEpisodes MacCMS标准解析（陷阱31引用）+ 链接 multiline-on-demand-extraction.md
  - [ ] 2.8.2.5 适配开源阅读的js：Rhino兼容（陷阱44/55引用）
- [ ] 2.8.3 每项附陷阱编号+references链接

### 2.9 新增快速入门章节（REQ-12, AD-11）★v6新增
- [ ] 2.9.1 SKILL.md "核心原则"之后新增"快速入门"章节
- [ ] 2.9.2 写明5个快速了解入口：
  - [ ] 2.9.2.1 3分钟了解规则引擎（链接 references/rule-syntax.md + rule-construction-guide/）
  - [ ] 2.9.2.2 视频订阅源核心要求速查（引用 2.8 章节）
  - [ ] 2.9.2.3 书源核心要求速查（链接 references/booksource-schema.md）
  - [ ] 2.9.2.4 必填字段清单（已有，保留链接）
  - [ ] 2.9.2.5 Top 10 陷阱速查（已有，保留链接）

### 2.10 新增源码阅读步骤（REQ-13, AD-12）★v6核心
- [ ] 2.10.1 SKILL.md Phase 1 新增"源码验证"步骤说明（经验检索都不足时启用）
- [ ] 2.10.2 写明触发条件（经验检索两源都无同类经验 + 陷阱库无相关案例）
- [ ] 2.10.3 写明阅读范围（4类源码路径）：
  - [ ] 2.10.3.1 规则引擎源码路径（app/src/main/java/io/legado/app/model/analyzeRule/）
  - [ ] 2.10.3.2 RSS源码路径（RssSource.kt + model/rss/）
  - [ ] 2.10.3.3 书源源码路径（BookSource.kt + model/webBook/）
  - [ ] 2.10.3.4 JS扩展源码路径（JsExtensions.kt）
- [ ] 2.10.4 写明快捷入口（优先阅读 docs/project-flow/architecture/ 架构文档）
- [ ] 2.10.5 写明输出格式（报告"规则映射建议"标注 `[源码验证:xxx]`）
- [ ] 2.10.6 写明🔴硬约束：只读不改，严禁修改项目源码

### 2.11 新增用户偏好/AI进化偏好优先级章节（REQ-14, AD-13）★v7核心
- [ ] 2.11.1 SKILL.md "视频订阅源核心要求速查"之后新增"用户偏好/AI进化偏好优先级"章节
- [ ] 2.11.2 写明6类规则优先级表格：
  - [ ] 2.11.2.1 视频地址提取优先级：CMS API(P1) > JS提取(P2) > XPath/CSS(P3) > 嗅探兜底(P4)（陷阱28/30/31/56/41引用）
  - [ ] 2.11.2.2 搜索URL优先级：API搜索(P1) > HTML搜索(P2)（陷阱28/29引用）
  - [ ] 2.11.2.3 图片提取优先级：CSS选择器(P1) > JS提取(P2) > 正则(P3)
  - [ ] 2.11.2.4 列表提取优先级：CSS选择器(P1) > XPath(P2) > JS(P3)（陷阱47引用）
  - [ ] 2.11.2.5 域名处理优先级：固定域名(P1) > meta refresh(P2) > JS redirect(P3)（陷阱50/52/57引用）
  - [ ] 2.11.2.6 详情页→播放页URL转换优先级：`##`操作符(P1) > JS提取(P2)（陷阱40/49引用）
- [ ] 2.11.3 写明AI使用方式：Phase 2写规则时按优先级递进尝试，高优先级失败才降级
- [ ] 2.11.4 写明输出格式：报告"规则映射建议"标注 `[偏好优先级:视频地址提取P1-CMS API]`

### 2.12 初始化经验完整性审计（REQ-15, AD-14支持）★v8核心
- [ ] 2.12.1 JsExtensions.kt 全方法覆盖率审计
  - [ ] 2.12.1.1 读取 `app/src/main/java/io/legado/app/help/JsExtensions.kt`，提取所有 `@JavascriptInterface` 注解方法
  - [ ] 2.12.1.2 对照 `references/js-extensions/` 现有文档，标记缺失方法
  - [ ] 2.12.1.3 补齐缺失方法的文档（函数签名+参数+返回值+示例+Rhino兼容性）
- [ ] 2.12.2 新建 Rhino 兼容性速查表 `references/js-extensions/rhino-compat-cheatsheet.md`
  - [ ] 2.12.2.1 ES5 支持的语法清单（var/function/正则字面量/基本运算）
  - [ ] 2.12.2.2 ES6+ 不支持的语法清单（let/const/箭头函数/模板字符串/padStart/includes/Promise/async-await/解构/扩展运算符）
  - [ ] 2.12.2.3 替代写法对照表（includes→indexOf>-1 / padStart→手动补零 / 模板字符串→字符串拼接）
  - [ ] 2.12.2.4 类型转换陷阱（java.ajax()返回值必须String()显式转换 / NativeArray实现List / NativeObject属性访问）
- [ ] 2.12.3 新建 JS 执行环境差异集中化文档 `references/js-extensions/js-env-diff.md`
  - [ ] 2.12.3.1 集中化现有分散的执行环境差异文档（shouldOverrideUrlLoading/injectJs/loginCheckJs/ruleArticles JS/evalJS）
  - [ ] 2.12.3.2 表格对比：Rhino vs WebView 的 API 可用性（document/window/localStorage/cookie/cache/java/result/source）
  - [ ] 2.12.3.3 绑定变量清单（各执行环境绑定的变量列表）
  - [ ] 2.12.3.4 返回值类型约束（loginCheckJs必须返回StrResponse / ruleArticles JS必须返回NativeArray）

### 2.13 陷阱库去站点化重构（REQ-16, AD-15）★v8核心
- [ ] 2.13.1 陷阱40-57标题重构
  - [ ] 2.13.1.1 现状：陷阱标题按"站点A经验沉淀""站点B经验沉淀"分类
  - [ ] 2.13.1.2 目标：改为按问题类型分类（如"动态域名解析""平衡括号算法""Rhino类型转换""##操作符URL替换"）
  - [ ] 2.13.1.3 保留陷阱编号不变，仅改标题和分类
- [ ] 2.13.2 "铁证"部分脱敏
  - [ ] 2.13.2.1 站点代号→通用描述（站点A→"某聚合视频站点"）
  - [ ] 2.13.2.2 具体URL→路径模式（`/path/{id}`）
  - [ ] 2.13.2.3 保留技术结论（错误码/异常类型/调用栈/DOM选择器），删除业务数据
- [ ] 2.13.3 经验来源标注通用化（配合 REQ-10/2.7）
  - [ ] 2.13.3.1 现状：`[经验来源:站点D修复v4]`
  - [ ] 2.13.3.2 目标：`[经验来源:动态域名修复范式]` 或 `[经验来源:平衡括号算法]`

### 2.14 新增自进化沉淀闭环（AD-14, AD-15）★v8核心
- [ ] 2.14.1 SKILL.md 新增"自进化沉淀"章节（位于源码阅读步骤之后）
- [ ] 2.14.2 写明沉淀触发条件：源码阅读/陷阱修复/Playwright分析中发现新范式
- [ ] 2.14.3 写明沉淀流程：发现新范式 → 按AD-15质量标准抽象 → 更新references/对应文档 → 在_INDEX.md自进化指引登记
- [ ] 2.14.4 写明沉淀质量标准（引用AD-15）：通用范式抽象 + 脱敏案例 + 保留技术结论 + 删除业务数据
- [ ] 2.14.5 写明沉淀效果：下次经验检索两源命中该经验，无需重新分析

### 2.15 验证SKILL.md
- [ ] 2.15.1 验证 SKILL.md 行数（v8因新增6章节可放宽到≤260行）
- [ ] 2.15.2 验证 frontmatter 格式符合 skill-creator 规范
- [ ] 2.15.3 Grep 确认无 JVM / fetch_html / html_fetcher / legado_client / basic-memory 引用
- [ ] 2.15.4 Grep 确认无 Python import / Python 函数调用代码块
- [ ] 2.15.5 Grep 确认含 经验检索两源 / 视频源核心要求速查 / 快速入门 / 源码阅读步骤 / 偏好优先级 / 自进化沉淀 6大新增章节（v8新增自进化沉淀）
- [ ] 2.15.6 Grep 确认经验来源标注无站点代号（v8新增，配合REQ-16去站点化）

## 3. Phase 3 - references整理

### 3.1 删除JVM相关文档（REQ-01）
- [ ] 3.1.1 删除 `references/jvm-infrastructure.md`（如Phase 1未删）
- [ ] 3.1.2 删除 `references/mock-unimplemented-functions.md`（如Phase 1未删）

### 3.2 合并重叠目录
- [ ] 3.2.1 统一索引命名：site-features/_INDEX.md → _index.md
- [ ] 3.2.2 合并 troubleshooting/ + known-fix-patterns/
  - [ ] 3.2.2.1 分析两目录内容重叠
  - [ ] 3.2.2.2 合并 known-fix-patterns/ 内容到 troubleshooting/
  - [ ] 3.2.2.3 删除 known-fix-patterns/ 目录
- [ ] 3.2.3 合并 js-patterns/ + js-extensions/ → js-reference/
- [ ] 3.2.4 评估 special-scenarios/ + site-features/ 合并可行性

### 3.3 新建/补充多线路多集按需采集文档（AD-10引用）
- [ ] 3.3.1 新建 `references/source-analysis/multiline-on-demand-extraction.md`（或链接到 docs/specs/multiline-on-demand-extraction/）
- [ ] 3.3.2 内容含：按需采集架构 + ruleRoutes/ruleEpisodes 标准写法 + JS模板

### 3.4 新建初始化经验完整性文档（REQ-15）★v8新增
- [ ] 3.4.1 新建 `references/js-extensions/rhino-compat-cheatsheet.md`（Rhino兼容性速查表）
  - [ ] 3.4.1.1 ES5支持语法清单
  - [ ] 3.4.1.2 ES6+不支持语法清单+替代写法对照表
  - [ ] 3.4.1.3 类型转换陷阱
- [ ] 3.4.2 新建 `references/js-extensions/js-env-diff.md`（JS执行环境差异集中化）
  - [ ] 3.4.2.1 Rhino vs WebView API可用性对比表
  - [ ] 3.4.2.2 各执行环境绑定变量清单
  - [ ] 3.4.2.3 返回值类型约束
- [ ] 3.4.3 JsExtensions.kt 全方法覆盖率审计补齐（对照2.12.1审计结果补齐缺失方法文档）

### 3.5 陷阱库去站点化重构（REQ-16）★v8新增
- [ ] 3.5.1 陷阱40-57标题重构（按问题类型分类，保留编号）
- [ ] 3.5.2 "铁证"部分脱敏（站点代号→通用描述，URL→路径模式）
- [ ] 3.5.3 经验来源标注通用化（站点代号→通用范式名）

### 3.6 更新索引
- [ ] 3.6.1 更新 `references/_INDEX.md`（合并后完整索引，含v8新增文档）
- [ ] 3.6.2 自进化指引增加去重检查流程 + v8自进化沉淀登记（AD-14）

### 3.7 统计
- [ ] 3.7.1 统计合并后文档总数，确认 ≤25（v8新增3文档后可适当放宽）

## 4. 验证

### 4.1 体量验证
- [ ] 4.1.1 统计 SKILL.md 行数（确认 ≤220行，v6放宽）
- [ ] 4.1.2 统计 references/ 文档数量（确认 ≤25）
- [ ] 4.1.3 确认 scripts/legado_client/ 目录已完全删除（无残留）★v5新增

### 4.2 内容验证
- [ ] 4.2.1 Grep 确认 SKILL.md 无 JVM / fetch_html / html_fetcher / legado_client / basic-memory 引用
- [ ] 4.2.2 Grep 确认 SKILL.md 无 Python import / 函数调用代码块
- [ ] 4.2.3 Grep 确认无重复陷阱内容
- [ ] 4.2.4 验证 frontmatter 格式符合 skill-creator 规范
- [ ] 4.2.5 验证网站分析报告模板完整性（10个章节齐全，规则映射为核心，含经验来源标注字段，v8要求通用范式名标注）
- [ ] 4.2.6 验证 SKILL.md 含 经验检索两源 / 视频源核心要求速查 / 快速入门 / 源码阅读步骤 / 偏好优先级 / 自进化沉淀 6大新增章节（v8新增自进化沉淀）
- [ ] 4.2.7 验证源码阅读步骤含🔴硬约束"只读不改"
- [ ] 4.2.8 验证 SKILL.md 经验来源标注无站点代号（v8新增，配合REQ-16）
- [ ] 4.2.9 验证 `references/js-extensions/rhino-compat-cheatsheet.md` 完整性（ES5支持/ES6+不支持/替代写法/类型转换陷阱）（v8新增）
- [ ] 4.2.10 验证 `references/js-extensions/js-env-diff.md` 完整性（Rhino vs WebView对比/绑定变量/返回值约束）（v8新增）
- [ ] 4.2.11 验证陷阱40-57标题已按问题类型分类（非站点分类），铁证已脱敏（v8新增）

### 4.3 功能验证
- [ ] 4.3.1 确认源制作任务可正常使用skill（重构未破坏核心功能）
- [ ] 4.3.2 模拟AI使用优化后的skill走一遍4阶段工作流（不实际生成源，仅验证流程通畅）
- [ ] 4.3.3 模拟AI遇未知问题时走经验检索两源→源码阅读路径（v6新增）

## AOAdapt 日志

> 实施过程中遇到问题时记录于此

（待实施时填充）
