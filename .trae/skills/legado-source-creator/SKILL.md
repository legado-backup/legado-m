---
name: "legado-source-creator"
description: "为 Legado 阅读器生成优秀好用的书源/订阅源 JSON。当用户需要创建/优化书源或订阅源、RSS源、视频订阅源时调用。包含规则编写、必填字段校验、真机验证、自进化沉淀闭环。"
---

# Legado Source Creator Skill

> 帮助 AI 为 Legado 阅读器生成"优秀好用"的书源/订阅源 JSON。
> **核心目标**：必填字段强制校验 + 真机测试集成 + 自进化沉淀闭环。

## 核心原则

1. **源码验证优先**：写规则前先去 Legado 源码核实，不凭经验臆测
2. **必填字段强制**：所有源必须通过必填字段校验（CRITICAL/MANDATORY/RECOMMENDED 三级）
3. **JSON 输出合规**：所有 None 字段必须过滤为空字符串（AI 自己不写 None）
4. **真机验证为最终标准**：编译+安装+导入+真机测试+日志分析
5. **自动修复闭环**：生成 → 测试 → 失败 → 手动诊断 → 修复 → 重测
6. **输出安全防线**：思考/输出双闭口禁止违禁词。域名→站点代号、源名称→源[N]、URL→路径模式（/path/{id}）、cookie→***。Grep 只搜技术字段不搜业务字段
7. **导出目录规范**：所有新生成或优化的源 JSON 必须导出到 `output/ai_source/` 目录，按「源类型/域名」两级子目录存放（订阅源→`rss/{域名}/`，书源→`book/{域名}/`），文件命名 `{类型}_{描述}_{日期YYYYMMDD}.json`。域名取源 JSON 首个源的 `sourceUrl`/`bookSourceUrl` 的 host（小写、去 `www.` 前缀、去端口/路径；域名字符集 `[a-z0-9.-]` 在 Windows/Linux 天然合法可直接作目录名）。同域名的最终版 JSON 与同名分析报告 `.md` 同目录存放；被取代的迭代版本/备份移入 `{域名}/history/`；测试日志等非源产物放 `_logs/`（结构详见 `output/ai_source/README.md`）
8. **自进化沉淀**：发现新范式后按质量标准沉淀到 references/，实现 skill 越用越智能

## 快速入门

5 个快速了解入口：
1. **3分钟了解规则引擎**：[rule-syntax.md](./references/rule-syntax.md) + [rule-construction-guide/](./references/rule-construction-guide/_index.md)
2. **视频订阅源核心要求速查**（见下方章节）
3. **书源核心要求速查**：[booksource-schema.md](./references/booksource-schema.md)
4. **必填字段清单**（见下方章节）
5. **Top 10 陷阱速查**（见下方章节）

## 4 阶段闭环工作流

### Phase 0: 经验检索两源

**目标**：在分析新站点前，先检索已有经验避免重复分析。

1. **源1：references/知识库检索**
   - 用 Grep/SearchCodebase 工具搜索关键词
   - 关键词示例：动态域名 / Rhino类型转换 / MacCMS / Cloudflare / 平衡括号
2. **源2：output/ai_source/ 已生成源JSON检索**
   - 用 Glob 找同类源模板（`output/ai_source/rss/**/*.json` / `output/ai_source/book/**/*.json`，按域名子目录组织；`history/` 内为被取代的旧版迭代）
   - 读取同类源的规则字段作为参考
3. **检索时机**：Phase 1 分析前 + Phase 4 修复时
4. **检索输出**：在网站分析报告"规则映射建议"标注 `[经验来源:通用范式名]`（禁止用站点代号）

### Phase 1: 分析（必经 Playwright MCP）

**目标**：用 Playwright MCP 真实分析网站结构 + 输出网站分析报告。

> **🔴 铁律**：禁止仅凭 CMS 主题名或经验猜测字段值，必须用 Playwright MCP 真实访问目标站点。

1. **必经 Playwright 访问**：用 `playwright_navigate` 真实访问目标站点首页（headless=True, waitUntil=domcontentloaded）
2. **必经 JavaScript 提取**：用 `playwright_evaluate` 执行 IIFE 提取4字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）；并按报告模板 1.1 章逐项盘点列表项信息字段（发布/更新时间、类型标签、简介、集数/状态、作者、热度等，均为相对 `ruleArticles` 的子选择器，站点无该项填「无」禁止留空）
3. **必经播放页链路验证（视频源）**：点击列表项验证落地页是否直接含 `<video>` 或 m3u8 流；若落地页是详情页，分析"详情页→播放页"跳转规律（URL模式差异如 `/info/` → `/play/`）；优先用 `##` 操作符转换 URL
4. **必经网站恢复信息提取**：提取回家域名/邮箱/备用域名写入 sourceComment
5. **识别触发字段**：CF/登录/验证码 → 必须先源码验证再写规则
6. **输出网站分析报告**：与源 JSON 同目录同名（书源→`output/ai_source/book/{域名}/`，订阅源→`output/ai_source/rss/{域名}/`）

**报告模板**：[templates/site-analysis-report.md](./templates/site-analysis-report.md)
**Playwright 完整指南**：[references/source-analysis/playwright-site-analysis.md](./references/source-analysis/playwright-site-analysis.md)

### Phase 1.5: 源码阅读（经验检索两源都不足时启用）

**目标**：经验检索两源都无同类经验 + 陷阱库无相关案例时，阅读 Legado 源码理解规则/字段行为。

**阅读范围**（只读不改，严禁修改项目源码）：
1. 规则引擎源码：`app/src/main/java/io/legado/app/model/analyzeRule/`
2. RSS源码：`RssSource.kt` + `model/rss/`
3. 书源源码：`BookSource.kt` + `model/webBook/`
4. JS扩展源码：`JsExtensions.kt`

**快捷入口**：优先阅读 `docs/project-flow/architecture/` 架构文档
**输出格式**：报告"规则映射建议"标注 `[源码验证:xxx]`
**自进化触发**：发现新范式后，按"自进化沉淀闭环"章节沉淀到 references/

### Phase 2: 生成 + 必填校验

**目标**：AI手动写源JSON（Write工具）+ 对照必填字段清单校验。

1. 按网站分析报告的"规则映射建议"写源 JSON
2. AI 自己不写 None（避免 None 序列化为 "None" 字符串触发 Rss.kt:64 ReferenceError）
3. 对照必填字段清单校验（CRITICAL/MANDATORY/RECOMMENDED）
4. 导出到 `output/ai_source/` 对应域名子目录（`book/{域名}/` 或 `rss/{域名}/`，结构见 `output/ai_source/README.md`）

### Phase 3: 真机验证

**目标**：导入+真机测试+日志分析。

```bash
# Step 1: 导入订阅源到正式包（Skill真机测试用正式包）
ai_tests/venv/Scripts/python.exe ai_tests/scripts/import_rss_source.py <json> --package io.legado.miss.app.release

# Step 2: 修复DB权限（import_rss_source.py chown bug）
# 检查正式包DB目录owner: adb shell "su -c 'ls -la /data/data/io.legado.miss.app.release/databases/'"
# 如果legado.db owner是root，需修复: adb shell "su -c 'chown u0_a73:u0_a73 /data/data/io.legado.miss.app.release/databases/legado.db'"

# Step 3: 启动App+验证（force-stop后启动避免WAL覆盖）
adb shell "am force-stop io.legado.miss.app.release"
adb shell "am start -n io.legado.miss.app.release/io.legado.app.ui.welcome.WelcomeActivity"
```

**SOP**：[ai_tests/docs/fixed_test_workflow.md](../../ai_tests/docs/fixed_test_workflow.md)
**包名规范**：Skill 真机测试用正式包 `io.legado.miss.app.release`；代码优化任务用测试包 `io.legado.miss.app.debug`

**订阅源验证流程**（Phase 3 详细步骤）：

| 步骤 | 操作 | 验证方法 |
|------|------|----------|
| 3.1 | 导入订阅源 | `import_rss_source.py --package io.legado.miss.app.release` |
| 3.2 | 修复DB权限 | `chown u0_a73:u0_a73 legado.db`（铁证：root权限导致SQLITE_CANTOPEN） |
| 3.3 | 启动App+进入订阅Tab | uiautomator2: `d(resourceId='{PKG}:id/menu_rss').click()` |
| 3.4 | 验证源列表加载 | 检查 `d(resourceId='{PKG}:id/tv_name')` 是否存在且count>0 |
| 3.5 | 点击源进入分类页 | 检查 Activity 是否为 RssSortActivity |
| 3.6 | 验证分类Tab加载 | 检查 TabLayout/分类文字是否可见 |
| 3.7 | 验证文章列表 | 检查 RecyclerView child count 或 tv_title 存在 |
| 3.8 | 验证搜索 | ADB直接启动: `am start -n {PKG}/.ui.rss.search.RssSearchActivity --es key HD --es searchScope '{sourceUrl}'` |
| 3.9 | 验证播放 | 点击文章检查 Activity 是否为 VideoPlayerActivity |
| 3.10 | 检查崩溃 | logcat grep `FATAL\|AndroidRuntime` |

### Phase 4: 自动修复循环

**目标**：失败 → AI查陷阱库 → 手动诊断 → 修复 → 重测。

1. 失败时查陷阱库（Top 10 速查 + [references/troubleshooting/](./references/troubleshooting/_index.md)）
2. AI 根据陷阱条目手动修复源 JSON
3. 重新导入+测试
4. **自进化沉淀**：修复新问题后，将修复方案沉淀为陷阱条目（见"自进化沉淀闭环"章节）

## 必填字段清单

### RssSource 字段级别

| 级别 | 字段 | 不填后果 |
|------|------|----------|
| **CRITICAL** | `sourceUrl` | 导入时抛 NoStackTraceException("不是订阅源") |
| **MANDATORY** | `sourceName`/`ruleArticles`/`ruleTitle`/`ruleLink`/`ruleContent` | 核心功能失效（无名称/无列表/无标题/无链接/无正文） |
| **MANDATORY**（站点具备该信息时） | `rulePubDate`/`ruleDescription` | 列表时间行空白/内容项描述信息缺失（类型标签/集数等无独立字段的信息须按模板1.1章合并进 `ruleDescription`） |
| **RECOMMENDED** | `sourceIcon`/`searchUrl`/`sortUrl`/`sourceGroup`/`sourceComment` | 优秀好用标准 |
| **OPTIONAL** | `ruleRoutes`/`ruleEpisodes` | 仅 type=2 视频源使用（多线路多集按需采集，详见下方章节） |

### BookSource 字段级别

| 级别 | 字段 | 不填后果 |
|------|------|----------|
| **CRITICAL** | `bookSourceUrl` | 导入时抛 NoStackTraceException("不是书源") |
| **MANDATORY** | `bookSourceName`/`searchUrl`/`ruleSearch.bookList`/`ruleBookInfo.name`/`ruleToc.chapterList`/`ruleContent.content` | 核心功能失效 |
| **RECOMMENDED** | `bookSourceGroup`/`bookSourceComment` | 优秀好用标准 |

### sourceComment 字段强制规范

必须包含网站恢复信息（回家域名/邮箱/当前域名/备用域名），用于网站丢失时快速恢复。
格式：`[网站恢复]回家域名:xxx.xyz | 邮箱:xxx@gmail.com [技术]简短技术说明`

## 视频订阅源核心要求速查

| 要求 | 说明 | 陷阱引用 |
|------|------|----------|
| 搜索js | searchUrl 支持 `<js>` 标签 JS 执行（动态域名站点必需） | 见陷阱库 |
| 图片必填 | ruleImage 必填 + articleStyle=2 网格布局（避免加载失败时图片不可见） | 见陷阱库 |
| 嗅探兜底 | ruleContent="" 触发嗅探是**兜底方案而非首选**（见偏好优先级） | 见陷阱库 |
| 多线路多集js | ruleRoutes/ruleEpisodes MacCMS标准解析 + `{routeIndex}` 占位符 | 见陷阱库 |
| Rhino兼容 | 避免ES6+语法（let/const/箭头函数/模板字符串/padStart/includes/Promise），用ES5替代写法 | 见 [rhino-compat-cheatsheet.md](./references/js-extensions/rhino-compat-cheatsheet.md) |

**多线路多集按需采集**：[references/source-analysis/multiline-on-demand-extraction.md](./references/source-analysis/multiline-on-demand-extraction.md)
**JS执行环境差异**：[references/js-extensions/js-env-diff.md](./references/js-extensions/js-env-diff.md)

## 用户偏好/AI进化偏好优先级

> AI在Phase 2写规则时按优先级递进尝试，高优先级失败才降级，遵循"简单优先/主流优先/兜底最后"原则。

| 规则类型 | P1（首选） | P2（次选） | P3（备选） | P4（兜底） |
|---------|-----------|-----------|-----------|-----------|
| 视频地址提取 | CMS API（ac=detail&ids） | JS提取（player_data平衡括号） | XPath/CSS选择器 | 嗅探（ruleContent=""） |
| 搜索URL | API搜索（ac=list） | HTML搜索（`/search/wd/{{key}}.html`） | — | — |
| 图片提取 | CSS选择器 | JS提取 | 正则 | — |
| URL转换 | `##`操作符（`a@href##info##play`） | JS提取（`result.match(...)`） | — | — |
| 域名处理 | 固定域名 | 动态域名JS（meta refresh/seededRandom） | — | — |
| 规则解析 | CSS选择器 | JSONPath | XPath | JS（Rhino） |

**报告标注**：在网站分析报告"规则映射建议"标注 `[偏好优先级:视频地址提取P1-CMS API]`

## 自进化沉淀闭环

> **触发条件**：在源码阅读/陷阱修复/Playwright分析中发现新范式时触发（如新的动态域名解析算法/新的反爬绕过方案/新的Rhino兼容性陷阱）。

**沉淀流程**：
1. **发现新范式**：源码阅读理解新规则行为 / 陷阱修复找到新方案 / Playwright分析发现新页面结构
2. **按质量标准抽象**（AD-15）：
   - 通用范式抽象：标题按问题类型命名（如"动态域名解析""平衡括号算法""Rhino类型转换"），禁止按站点命名
   - 脱敏案例：站点代号→通用描述（"某聚合视频站点"），具体URL→路径模式（`/path/{id}`）
   - 保留技术结论：错误码/异常类型/调用栈/DOM选择器/字段名/函数名
   - 删除业务数据：源名称/域名/URL/cookie内容/分类名称
   - 经验来源标注通用化：`[经验来源:动态域名修复范式]` 而非 `[经验来源:站点D修复v4]`
3. **更新 references/ 对应文档**：
   - 陷阱类（导致错误/报错的用法）→ `references/troubleshooting/` 对应子文档
   - 方案类（成功的实现方案）→ `references/special-scenarios/` 对应子文档
   - JS技巧 → `references/js-patterns/` 对应子文档
   - JS函数用法 → `references/js-extensions/` 对应子文档
4. **在 `references/_INDEX.md` 的"自进化指引"章节登记新经验**
5. **下次遇到同类问题时，经验检索两源命中该经验，无需重新分析**

**🔴 硬约束**：沉淀必须遵循质量标准，禁止按站点分类导致经验膨胀爆炸

## Top 10 陷阱速查

> 完整陷阱库见 [references/troubleshooting/](./references/troubleshooting/_index.md)（陷阱库已去站点化重构，按问题类型分类）

### JSON 输出陷阱

1. **None 序列化 bug**：None → "None" 字符串 → Rss.kt:64 ReferenceError。**修复**：AI不写None
2. **loginUrl 禁用 `@js:java.webView()`**：WebViewLoginFragment.loadUrl() 不识别 @js: 形式
3. **loginCheckJs 陷阱**：每次请求执行，调 `java.startBrowserAwait()` 导致无限循环
4. **header 字段格式**：必须是 JSON 字符串，不是 dict

### 规则引擎陷阱

5. **@CSS vs class.**：`@CSS:.item` 与 `class.item` 等价但混用出错
6. **@XPath 转义**：属性值含 `"` 必须用 `'` 包裹
7. **@js 内联 vs `<js>` 标签**：前者追加在规则后，后者独立块
8. **put/get 变量**：跨规则传值必须用 `@put:{key:rule}` + `@get:{key}`

### 真机验证陷阱

9. **Room WAL 模式**：导入前必须 `am force-stop` App，否则 WAL 覆盖
10. **import_rss_source.py chown uid bug**：脚本硬编码 uid，不同包/实例 uid 不同，导入后必须手动 `chown <实际uid>:<实际uid>` 修复权限

> 陷阱11-57（含动态域名解析/Rhino类型转换/平衡括号算法/##操作符URL替换/MacCMS解析/CF防护等）已迁移至 references/troubleshooting/ 对应子文档
>
> 新增陷阱（按类别索引，全部来自7源聚合站点实战）：
>
> **Rhino JS引擎陷阱**（见 references/troubleshooting/rhino-js-traps.md）：
> - **陷阱58 协程IO线程死锁**：含`java.ajax()`的JS不能在`Dispatchers.IO`执行，须用独立线程执行器
> - **陷阱59 length vs length()**：Java String的`length`是属性不是方法，`str.length()`触发EvaluatorException
> - **陷阱60 Long参数类型转换失败**：`java.ajax(url, 3000)`中JS数字无法转Long?，须用单参数版本`java.ajax(url)`
> - **陷阱61 ajax自动跟随301重定向**：`java.ajax()`自动跟随重定向，HTML中不含Location头的域名
> - **陷阱65 JSON中`\\n`双重转义**：sortUrl分类分隔符失效，用`String.fromCharCode(10)`替代`'\\n'`
>
> **动态域名陷阱**（见 references/troubleshooting/dynamic-domain-traps.md）：
> - **陷阱D 301重定向后HTML不含punycode域名**：java.ajax自动跟随重定向，HTML中无`xn--`
> - **陷阱E 动态域名缓存过期**：缓存时间过短导致间歇性失效，须6小时(21600秒)
> - **陷阱F HTML属性值带引号导致marker匹配失败**：HTML中`href="URL"`带引号，marker不能带`href=`
>
> **聚合站点多子源列表解析陷阱**（见 references/special-scenarios/rss-advanced.md 7.12节）：
> - **陷阱62 多HTML模板适配**：聚合站点多子源class名不同，须用CSS多选择器`.a, .b, .c`
> - **陷阱63 卡片本身是`<a>`标签**：不能用`card.find('a')`，须用`card.attr('href')`或"先查子元素再取卡片本身"
> - **陷阱64 JSON vs HTML动态判断ruleArticles**：用`@js:`动态分支，先JSON.parse失败再Jsoup解析
>
> **多API搜索**（见 references/special-scenarios/search-advanced.md 第8节）：
> - **多API搜索方案对比**：ajaxAll并发 vs ajax串行 vs 仅主源搜索
> - **推荐方案**：仅主源搜索 + 串行补充（用`java.ajax(u)`单参数版本，避免陷阱60）
> - **ruleArticles合并模板**：主源结果+缓存子源结果合并，HTML回退用Jsoup多模板适配
>
> **封面解密**（见 references/special-scenarios/encrypted-images.md）：
> - **陷阱66 coverDecodeJs 不能带 `@js:` 前缀**：ImageUtils.decode→BaseSource.evalJS→AbstractScriptEngine.eval 全程无前缀剥离，`@js:` 直接 JS 编译失败
> - **陷阱67 hutool createSymmetricCrypto 的 transformation 坑**：hutool 5.8.22 `new SymmetricCrypto("AES/CBC/PKCS5Padding", key)` 在 JVM 抛 InvalidKeyException（KeyUtil.generateKey 把完整 transformation 当算法名），用 JavaImporter 直调 javax.crypto 兜底
> - **陷阱68 key/iv 下划线十进制 ASCII**：站点 media_key/media_iv 常为下划线分隔十进制 ASCII，需还原为 16 字节字节串（`String.fromCharCode(...)`）
> - **陷阱69 NativeJavaArray 兼容**：ScriptBindings.set 经 Context.javaToJS 包装 ByteArray 为 NativeJavaArray，`cipher.doFinal(result)` 可正常匹配 `doFinal(byte[])`

## 真机测试脚本

### 通用脚本

| 脚本 | 用途 |
|------|------|
| `ai_tests/scripts/quick_build_install.py` | 编译+安装+L1验证（代码优化任务用，Skill测试不需要） |
| `ai_tests/scripts/import_rss_source.py <json> --package io.legado.miss.app.release` | 导入订阅源（含WAL处理+chown修复） |
| `ai_tests/scripts/l2_verify_video_player.py` | L2视频播放器验证 |
| `ai_tests/scripts/l2_verify_rss_search.py [--keyword 关键词]` | L2订阅源搜索验证（需修改PACKAGE为正式包） |
| `ai_tests/scripts/swipe_test_log.py` | 日志分析（clear/capture/analyze） |

### Skill 专用验证脚本（创建于本次任务）

| 脚本 | 用途 |
|------|------|
| `ai_tests/scripts/e2e_verify_rss_v3.py` | 订阅源端到端验证（源列表→分类→文章→搜索→播放） |
| `ai_tests/scripts/quick_check.py` | 快速检查当前Activity+UI状态 |
| `ai_tests/scripts/verify_articles_play.py` | 验证文章列表+翻页+播放 |

## 任务完成标准

- [ ] 已用 Playwright MCP 真实访问目标站点首页（非猜测）
- [ ] 4个 RECOMMENDED 字段值来自真实 DOM 提取（sourceIcon/searchUrl/sortUrl/ruleNextPage）
- [ ] 源 JSON 无 None 字段
- [ ] 必填字段清单校验通过（CRITICAL/MANDATORY/RECOMMENDED）
- [ ] 真机导入后源可正常加载（列表/搜索/分类/播放）
- [ ] 发现新范式已沉淀到 references/（按质量标准抽象+脱敏）
- [ ] 用 AskUserQuestion 向用户确认

## 完整参考

- [references/_INDEX.md](./references/_INDEX.md) - 知识库索引（规则语法/JS扩展/陷阱/特殊场景/源码分析/站点特性/CMS样本）
- [templates/site-analysis-report.md](./templates/site-analysis-report.md) - 网站分析报告模板
- [ai_tests/docs/fixed_test_workflow.md](../../ai_tests/docs/fixed_test_workflow.md) - 真机测试SOP
- [references/source-analysis/playwright-site-analysis.md](./references/source-analysis/playwright-site-analysis.md) - Playwright网站真实分析指南
