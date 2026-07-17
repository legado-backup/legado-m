---
name: legado-source-creator
description: 开源阅读(Legado)书源与订阅源智能创建。分析目标网站结构，自动生成符合Legado规则引擎的BookSource/RssSource JSON配置，覆盖CSS/XPath/JSONPath/Regex/JS五种解析方式，支持登录验证码加密图片视频等特殊场景。
---

# Legado 书源/订阅源智能创建器

> 为开源阅读（Legado）Android 应用创建 BookSource（书源）或 RssSource（订阅源）JSON 配置。

## 文件导航（AI agent 必读）

| 文件 | 定位 | 何时读取 |
|------|------|---------|
| **SKILL.md**（本文件） | L1 决策入口：流程+陷阱+L3操作+JVM测试+代码进化 | **必须首先读取** |
| AI_README.md | L1 补充：完整目录结构+数据文件说明+脚本详细用法 | 需要了解目录结构或脚本详细参数时 |
| references/ | L2 完整知识库：代码示例+详细解释+修复方案 | 按需查阅（本文件中有指针） |
| basic-memory | L3 经验索引：陷阱/模式/经验摘要+指针 | Phase 1 搜索 / Phase 5 反哺 |
| **统一 OpenSpec** | **整体优化设计文档**：三层协作架构（Skill+Python+JAR）+ 27 个方向任务清单 | 需要理解整体优化方案或查找具体修复任务时 |

> **统一 OpenSpec 位置**：`docs/specs/legado-skill-optimization/`（README.md / spec.md / design.md / tasks.md）
> **合并历史**：统一合并了 simulation-fidelity-95 + python-client-optimization + skill-core-capability-rebuild 三套旧 OpenSpec

## 触发条件

| 触发词 | 示例 |
|--------|------|
| 书源 | "创建书源" / "写个书源" / "书源规则" |
| 订阅源/RSS源 | "创建订阅源" / "RSS源" / "订阅规则" |
| 阅读/Legado | "阅读app书源" / "Legado规则" |
| 网站→JSON | "把这个网站做成书源" |
| 修复/优化 | "这个源用不了了" / "帮我修复书源" |

---

## 源类型快速决策

```
网站有"章节目录"结构？
  ├─ 有 → BookSource（bookSourceType: 0小说/1音频/2漫画/3文件）
  └─ 无 → RssSource（type: 0拼HTML渲染/1图片列表/2直接播放视频URL）
```

> **type 含义**：BookSource.bookSourceType 决定内容类型；RssSource.type 决定渲染方式（0=拼HTML显示, 1=图片列表, 2=视频直链播放）

| 维度 | BookSource | RssSource |
|------|-----------|-----------|
| 规则结构 | 5组嵌套（Search/BookInfo/Toc/Content/Explore） | **扁平独立字段**（ruleArticles/ruleTitle/ruleLink等） |
| 典型网站 | 笔趣阁、起点 | 视频站、图集站、新闻站 |

---

## 🔴 陷阱速查表（精选高频项，完整80条见 references/troubleshooting/）

### A. JS/Rhino（占错误70%+）

| # | 陷阱 | ✅ 正确做法 |
|---|------|-----------|
| 1 | ES5 only | `var`/`function(){}`/字符串拼接，禁止let/const/=>/模板字符串 |
| 2 | `java`遮蔽Java包 | `Packages.java.lang.String.xxx`（java是JsExtensions实例） |
| 5 | getElements返回类型 | `return arr`（非JSON.stringify） |
| 6 | NativeObject属性 | 纯属性名`vod_name`（非`$.vod_name`） |
| 9 | Java String→JS | `javaString+''`（非String()） |
| 11 | decryptStr vs decrypt | 二进制→`decrypt()`；文本→`decryptStr()` |
| 12 | loginCheckJs不返回result | 末尾加`;result`，否则NPE崩溃 |

### B. 源类型/字段

| # | 陷阱 | ✅ 正确做法 |
|---|------|-----------|
| 14 | RssSource字段扁平 | ruleArticles/ruleTitle等是独立String?，非嵌套对象 |
| 15 | type选择 | 拼HTML→type:0；纯视频URL→type:2 |
| 17 | enableJs≠webView | `{"webView":true}`才触发WebView加载 |

### C. URL/网络

| # | 陷阱 | ✅ 正确做法 |
|---|------|-----------|
| 19 | URL拼接缺`/` | 路径必须以`/`开头 |
| 37 | WebFetch丢标签 | 必须用curl/Playwright获取HTML |

### D. 高频陷阱补充

| # | 陷阱 | ✅ 正确做法 |
|---|------|-----------|
| 42 | sourceIcon域名 | 必须与sourceUrl同域，或用data:image |
| 47 | CSS伪类冲突 | 含`:has()`等必须加`@CSS:`前缀 |
| 50 | PJAX空壳HTML | 用`java.webView()`获取渲染后内容 |
| 52 | ajax()返回String | 获取byte[]必须用`Packages.okhttp3.OkHttpClient()` |
| 53 | Mirages图片加密 | AES-CBC解密→详见`references/troubleshooting/crypto-traps.md` |
| 54 | CF JS Challenge | ⚠️ loginUrl **不能**用 `@js:java.webView()`！必须是普通 URL，用户手动点击登录后 WebView 自动通过 CF（源码锚定：`app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt` 的 loadUrl 不识别 @js: 形式） |
| 55 | loginCheckJs必须返回StrResponse | loginCheckJs返回值必须是StrResponse对象（非String），否则解析失败 |
| 56 | CF Cookie同步 | WebView→CookieStore自动同步（onPageFinished） |
| 57 | loginCheckJs无限循环 | loginCheckJs每次请求都执行，检测CF弹浏览器→通过→又检测→无限循环。CF站不要设loginCheckJs |
| 58 | ruleContent拆分`<js>`和HTML | `</js>`后HTML被当CSS选择器解析→SelectorParseException。整个ruleContent包裹在单个`<js>`标签内 |
| 59 | 多播放源优先选m3u8 | 第一个源可能是分享链接（非m3u8），必须遍历所有URL优先选择`.m3u8` |
| 60 | JS中result可能是Element | `org.jsoup.Jsoup.parse(result)`可能因类型失败。用`result+''`转String，或用正则代替Jsoup |
| 61 | java.ajax()空URL崩溃 | 必须检查URL非空且以http开头才调用java.ajax()，否则IllegalArgumentException |
| 62 | @CSS:前缀必须 | CSS选择器规则必须以`@CSS:`开头！否则走Legado自定义语法解析失败返回空。如`@CSS:span.xx a@text`而非`span.xx a@text` |
| 63 | ruleImage用result.select() | JS中result是Element对象，可直接调用`result.select('CSS')`和`result.attr('abs:href')`，无需Jsoup.parse |
| 64 | ruleArticles排除表头 | 用`:has(.class)`排除表头行，如`@CSS:.xing_vb ul li:has(.xing_vb4)` |
| 65 | Playwright无法破CF盾 | Playwright走CDP协议被CF检测，即使用户手动点验证也循环。用DrissionPage替代（不走CDP） |
| 66 | 应用层搜索验证码 | 搜索验证码独立于CF盾，基于PHPSESSID session。loginUrl组合处理CF+搜索验证码，enabledCookieJar:true传递Cookie |
| 67 | CF盾必须首页验证 | CF盾只能在首页人工干预解除，子页面无法独立破盾。cf_clearance Cookie有效期数小时到数天 |
| 68 | Rhino正则不能含单引号 | `replace(/'/g,"\\'")`中`/'/g`导致Rhino解析失败（`在语句前面缺少";"`）。改用`replace(new RegExp("'","g"),"\\'")`或避免在正则中使用单引号 |
| 69 | ruleContent不要嵌入HTML模板 | HTML+JS模板中的正则/转义在Rhino中极易出错。ruleContent只返回数据（如`名称$URL`列表），让Legado内置播放器处理 |
| 70 | loginCheckJs检测搜索验证码 | `if(result.indexOf('系统安全验证')!=-1){java.startBrowserAwait(...)}`检测验证码页面，弹出浏览器让用户输入。验证码基于session，通过后Cookie自动传递 |
| 71 | searchUrl用getVerificationCode处理验证码 | `java.getVerificationCode(imgUrl)`弹出验证码图片让用户输入，比startBrowserAwait更轻量。searchUrl的JS必须返回搜索URL，不能在JS中直接执行搜索 |
| 72 | searchUrl中<js>不能用{{key}} | AnalyzeUrl先执行`<js>`代码再替换`{{key}}`模板变量！`{{key}}`在JS执行时是`{{`语法，Rhino报"缺少分号"。必须用JS变量`key`（AnalyzeUrl.evalJS绑定了`bindings["key"]=key`） |
| 73 | searchUrl避免用<js>标签 | searchUrl中`<js>`标签极易触发Rhino语法错误（转义/编码/执行顺序问题）。优先用简单URL格式+loginCheckJs处理验证码，避免在searchUrl中写复杂JS代码 |
| 74 | loginCheckJs中result是StrResponse | RssSource的loginCheckJs在AnalyzeUrl.evalJS中执行，`result`绑定的是StrResponse对象（非HTML字符串）。必须用`result.body+''`获取HTML内容再检测关键词 |
| 75 | header @js:中{{baseUrl}}不替换 | `{{...}}`模板替换只在AnalyzeUrl.replaceKeyPageJs()中执行（仅处理ruleUrl/searchUrl），不处理header！header @js:中必须用`baseUrl`变量（BaseSource.evalJS作用域中可用，值为sourceUrl） |
| 76 | @CSS:前缀vs Legado自定义语法 | 不带@CSS:前缀走Legado自定义选择器解析（支持tag.class/tag@attr/tag[!n]），带@CSS:前缀走jsoup CSS选择器。两者都能工作，但Legado自定义语法更简洁（如`ul[!0]`vs`@CSS:.xing_vb ul li:has(.xing_vb4)`） |
| 77 | Legado URL拼接不用abs:href | Legado不用jsoup的`abs:href`，而是用`element.attr("href")`取原始值，再通过`NetworkUtils.getAbsoluteURL(redirectUrl, str)`拼接。ruleLink用redirectUrl（重定向后URL）作base，ruleImage用sourceUrl作base |
| 78 | searchUrl验证码用<js>+getVerificationCode | 搜索验证码用`<js>java.getVerificationCode(imgUrl)</js>`处理，JS代码必须用ES5（var/字符串拼接），禁止ES6模板字符串。JS返回后接搜索URL+POST选项 |
| 79 | NativeJavaObject toString输出哈希 | Rhino JS返回Java对象时`toString()`输出`NativeJavaObject@hash`而非实际内容。JAR仿真器已内置`unwrapRhinoResult()`自动处理6种Rhino特殊类型（NativeJavaObject/NativeArray/NativeObject/NativeJavaArray/Undefined/ConsString），真机无此问题 |
| 80 | 分类列表图片CF拦截-需Cookie预热 | searchUrl的`<js>`块会通过`java.ajax()`预热CF Cookie，但sortUrl是简单URL无预热。导致ruleImage中`java.ajax(href)`被CF拦截返回挑战页。修复：ruleImage中添加Cookie预热（`java.get/put`时间戳控制频率，每5分钟访问首页一次）+ CF拦截检测（`challenges.cloudflare.com`/`请稍候`关键词触发重试） |
| 81 | 内置播放器404防盗链 | type=2内置播放器(ExoPlayer)请求视频URL返回404但WebView模式正常。根因：CDN防盗链校验Referer，ExoPlayer默认不携带。修复已实现：系统自动注入Header（ruleContent不为空→AnalyzeUrl.headerMap；R5自动抓取→注入Referer=文章页面URL），通过ExoPlayerHelper.setDefaultHeaders注入okhttpDataFactory。singleUrl模式不注入Referer(YAGNI，URL本身就是视频地址)。详见`video-audio.md` 5.6节常见问题 |

> 完整81条陷阱+详细解释：`references/troubleshooting/_index.md`

---

## L3 经验引擎（basic-memory MCP）

> **核心定位**：basic-memory 是经验索引层（L3），存储陷阱/模式/经验的摘要+指针。完整内容在 L2（references/）。权威源规则：Skill文档 > references/ > basic-memory。

> **双写规范**：SKILL.md 陷阱速查表中的每条陷阱，basic-memory 中必须有对应的 trap 笔记。references/ 中的关键经验，basic-memory 中必须有对应的 experience/pattern 笔记。如果发现缺失，必须补写。

> **完整操作规范**（MCP工具调用、L3目录结构、笔记类型体系、搜索策略、反哺策略、双写一致性规则）：详见 [references/basic-memory-usage.md](./references/basic-memory-usage.md)

**关键操作速查**：
- 所有操作必须指定 `project="legado"`
- Phase 1 搜索：`search_notes(query, search_type="hybrid", project="legado")`
- Phase 5 反哺：先更新Skill文档 → 再写basic-memory → 标记sync_status
- 降级路径：basic-memory不可用 → Grep references/替代 → 标记待验证

**write_note 模板**（经验笔记+执行证据+双写一致性规则）：详见 [references/basic-memory-usage.md](./references/basic-memory-usage.md)

**执行证据必填 metadata 字段**：`source_name`/`phase`/`basic_memory_search`/`trap_check`（Phase 1）；`test_coverage`/`confidence_*`/`jvm_evolution_needed`/`phase4_triggered`（Phase 3）；`dual_write`/`sync_status`/`schema_validation`/`code_evolution_executed`（Phase 5）

---

## JVM 测试基础设施

> **定位**（v2 修正声明，2026-07-17）：JVM 服务端是**可选的测试工具，非必须依赖**。纯 Python 覆盖率 35-40%，JVM 提升**规则引擎层**到 85-90%（**❌ 不覆盖** WebView/Activity/Cookie同步）。JVM 不可用时自动降级到 verify-source.py，工作流不中断。完整详情（legado-jvm架构/API速查/使用示例/ajax差异/可信度标注/降级路径）：[references/jvm-infrastructure.md](./references/jvm-infrastructure.md)

**legado-jvm 覆盖能力**（v2 修正声明，2026-07-17）：legado-jvm 从 Legado 源码抽取完整规则引擎，**规则引擎层覆盖率 85-90%**（Rhino JS 引擎 + jsoup CSS + hutool 加密 + AnalyzeRule）。**❌ 不覆盖**：Android WebView 系统组件 / Activity 生命周期 / Cookie 自动同步 / 真机网络栈。涉及 WebView 字段（loginUrl/loginCheckJs/cookie）时**必须**走 Phase 0 源码验证 + 真机测试，不可依赖 JVM 仿真。
**降级**：JVM可用→debug-source.py(首选) → JVM不可用→verify-source.py+手动curl → 网站不可访问→标记需真机验证 → 涉及WebView字段→强制Phase 0+真机

---

## Phase 0 源码验证门禁（v2 新增，强制执行）

> **触发条件**（任一即触发）：涉及以下字段/方法时**必须**先执行源码验证，再写入 references/ 或 basic-memory：
> - `loginUrl` / `loginCheckJs` / `loginUi`
> - `webView` / `startBrowserAwait` / `startBrowser`
> - `cookie` / `CookieStore` / `CookieManager`
> - `ruleContent` 中涉及视频播放器配置
> - `header` 中 @js: 形式

> **根因**（2026-07-17 v2 修正）：原 cf-bypass.md 推荐 `loginUrl: @js:java.webView(null, source.sourceUrl, null, false);` 被源码证伪——[WebViewLoginFragment.loadUrl()](../../../app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt) 不识别 `@js:` 形式。错误经验一旦写入会反复强化，必须在写入前拦截。

### Phase 0 执行步骤（强制）

1. **Grep Legado 源码**定位字段实际使用位置：
   ```
   Grep "loginUrl" app/src/main/java/io/legado/app/ --type kotlin
   ```
2. **Read 关键源码文件**确认实现（不依赖记忆/经验）：
   - `loginUrl` → `app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt`
   - `loginCheckJs` → `app/src/main/java/io/legado/app/model/analyzeRule/AnalyzeUrl.kt`
   - `Cookie 同步` → `app/src/main/java/io/legado/app/help/http/BackstageWebView.kt`
3. **在 references/ 中带 `source_ref:` 字段**记录源码位置：
   ```
   source_ref: app/src/main/java/io/legado/app/ui/login/WebViewLoginFragment.kt#L123-L145
   ```
4. **写入 basic-memory 时带 `verified_against_source:` 字段**：
   ```
   metadata={"verified_against_source": "app/src/.../Xxx.kt#L123", "verified_date": "2026-07-17"}
   ```

### Phase 0 失败处理

- 无法找到源码依据时，**禁止**写入 references/ 和 basic-memory
- 记录为"Phase 0 未通过，需真机验证"
- 标记 `needsUserIntervention=true`，由用户手动测试验证

### Phase 0 通过条件

- ✅ 找到源码位置（带行号）
- ✅ references/ 中带 `source_ref:` 字段
- ✅ basic-memory 中带 `verified_against_source:` 字段

---

## 核心工作流（6阶段闭环，Phase 0-5）

> **MANDATORY流程！** Phase 0源码验证→经验优先→构建规则→测试驱动→源码深挖→经验反哺。涉及 WebView/loginUrl/loginCheckJs/cookie 字段时**必须**先执行 Phase 0。测试失败必须进Phase 4。

### Phase 1: 经验优先

1. **过陷阱速查表**（上方表格，先检查通用项如 ES5/字段扁平，访问网站后再检查类型相关项）
2. **搜索basic-memory**（先用 URL 域名或网站名称搜索，访问网站后再用技术特征做增强搜索。按上方"L3搜索策略"执行，最小必执行1次 `search_notes`）
3. **查references/**：troubleshooting/（同类问题）→ js-patterns/（代码模式）→ source-analysis/（源码结论）
4. 找到经验→直接复用；未找到→记录为"skill未覆盖场景"

**完成检查清单**：
- [ ] 执行 search_notes 搜索 basic-memory（含CF绕过/CMS类型经验）
- [ ] 检查陷阱清单（至少检查与本网站类型相关的陷阱）
- [ ] 查cms-samples/目录（如检测到CMS类型）
- [ ] 输出 `[PHASE1_COMPLETE] basic-memory搜索:命中/未命中/降级, 陷阱检查:已检查/未检查`
- [ ] 写入 basic-memory 执行证据（按上方模板）

### Phase 2: 构建规则

**前置**：必须先完成Phase 1。

**0. 知识库强制查阅**（生成规则前必须执行，禁止跳过）：
   - 用 Grep 搜索 `references/` 目录中相关陷阱：`grep -rn "关键词" references/`（如 `CF\|cloudflare`、`AES\|加密`）
   - 或用 SearchCodebase 工具：`information_request="CF绕过方案"`, `target_directories=["references/"]`
   - **输出要求**：列出已查阅的陷阱清单（陷阱编号+标题），作为规则构建的依据
   - 如果搜索结果为空，记录"知识库未覆盖此场景"，进入 Phase 1 经验搜索

1. **分析网站**：curl获取HTML→判断类型（HTML/JSON/SPA/RSS）→检测特殊场景
   - 判断标准：HTML=完整HTML结构 / JSON=Content-Type:application/json / SPA=只有`<div id="app">`空壳 / RSS=XML格式含`<rss>`或`<feed>`标签
   - 详见：`references/rule-syntax.md` + `references/special-scenarios/_index.md`
   - 🔴 禁止WebFetch获取HTML（WebFetch会清理HTML标签，丢失关键结构信息），必须curl/Playwright
   - **HTML获取回退链**：curl获取失败（CF拦截/JS渲染）→ `python tools/html_fetcher.py --url URL --json` → 解析 FetchResult JSON（source/html/cms_type/log 字段）
   - 回退链顺序：curl → Wayback Machine → CMS样本库 → Google Cache → Playwright
2. **构建搜索规则**：
   - BookSource：searchUrl + ruleSearch（详见 `references/url-template.md` + `references/js-patterns/_index.md`）
   - RssSource：sourceUrl（列表页URL，详见"订阅源核心差异"章节）
   - 🔴 必须实际验证搜索可用，禁止猜测参数名
3. **构建详情+目录+正文规则**
   - 详见：`references/examples.md` + `references/special-scenarios/`
   - 🔴 decryptStr vs decrypt：二进制必须用`decrypt()`（陷阱#11）
   - **CMS样本选择器复用**：如果检测到CMS类型，优先使用 `references/cms-samples/{cms_type}/selectors.json` 中的选择器
     - 使用primary选择器构建规则字段
     - 如果primary验证失败，尝试fallbacks选择器
   - **BookSource 构建顺序**：searchUrl → ruleSearch → ruleBookInfo → ruleToc → ruleContent
   - **RssSource 构建顺序**：sourceUrl → ruleArticles → ruleTitle/ruleLink/ruleImage → ruleContent（详见"订阅源核心差异"章节 + `references/source-analysis/rss-source-entity.md`）
4. **处理特殊场景**：
   - CF反爬 → `references/special-scenarios/cf-bypass.md`（v2 已修正），使用三级策略：
     - JS Challenge → loginUrl 设为**普通首页 URL**（禁止用 `@js:java.webView(...)`，源码锚定：WebViewLoginFragment.loadUrl 不识别 @js: 形式）；用户手动点击"登录"按钮触发 WebView 加载
     - Turnstile → loginCheckJs 检测到 CF 时返回 `'CF_BLOCKED'` 标识字符串（禁止直接调 `java.startBrowserAwait()`，会触发陷阱#57 无限循环）；由用户手动触发登录
     - Interactive → 同 Turnstile 策略
   - 登录/验证码 → `references/special-scenarios/login.md` + `captcha.md`
   - 加密 → `references/special-scenarios/encryption.md` + `references/js-patterns/crypto-patterns.md`
   - 视频/图片 → `references/special-scenarios/video-audio.md`（**5.6节 type=2 内置播放器 ruleContent 编写指南：单URL/多行URL/JSON数组/嵌套JSON多线路四种格式**）+ `rss-advanced.md`（**7.10/7.11节 方案C type=2 内置播放器决策树**）+ `encrypted-images.md` + `templates/` 播放器模板

**完成检查清单**：
- [ ] 执行知识库查阅（Grep references/），输出"已查阅的陷阱清单"（陷阱编号+标题）
- [ ] 分析网站类型（HTML/JSON/SPA/RSS）
- [ ] 构建所有规则字段（search/detail/toc/content 或 articles/title/link/content）
- [ ] 处理特殊场景（CF/登录/加密/视频）
- [ ] **预校验**（新增）：用 source_validator + rule_precheck 校验字段完整性和规则语法
  - 字段完整性：必填字段非空、URL格式合法、字段冲突检测
  - 规则语法：CSS/XPath/JSONPath/Regex/JS 语法检查（不执行JS）
  - 预校验失败：返回 Phase 2 重新构建错误字段/规则
  - 预校验通过：进入 Phase 3
  - > **实现状态**：已实现（V2 重建阶段 6.1/6.2 完成）。source_validator.py 校验规则 BookSource 15 条 + RssSource 10 条；rule_precheck.py 支持 CSS/XPath/JSONPath/JS 语法检查 + Rhino 1.8.1 兼容性检测（ES6 关键字/箭头函数/模板字符串）。预校验失败时输出 `[PRECHECK_FAILED]` 结构化 JSON 并返回 Phase 2。

### Phase 3: 测试驱动

1. **静态陷阱扫描**：对照速查表检查所有JS规则
2. **运行测试脚本**（预校验通过后执行，JVM优先，降级Python）：

   > **预校验前置**（新增）：debug_runner.run() 入口先执行 source_validator + rule_precheck，预校验失败（字段缺失/规则语法错误）时不调用 JAR，直接返回错误。预计减少 20-30% 的无效 JAR 调用。
   >
   > **JVM 不可用时降级路径**（优化）：debug-source.py 启动时会自动检测 JVM 可用性（ping RuleEngineServer）。若 JVM 不可用（JDK 缺失/JAR 缺失/启动失败），脚本输出降级提示并退出码 3，**不中断工作流**。此时自动降级到 Python 模式（requests + BeautifulSoup4 执行简化调试，只支持搜索和详情阶段，不支持目录和正文），结果标注"Python降级模式，建议用JAR复验"，可信度降为 medium，工作流继续执行。
   > > **实现状态**：已实现（V2 重建阶段 6.3 完成）。debug_runner.py 在 FileNotFoundError（JAR 缺失）和 RuntimeError（Java 缺失/启动失败/ping 失败/启动超时）时自动降级到 Python 模式，输出 `[WARN] JAR 仿真服务端不可用，降级到 Python 模式` 并调用 `_run_python_fallback` 执行 verify-source.py 基本校验。
   >
   > **错误诊断闭环**（新增）：JAR 失败时自动调用 error_diagnoser 诊断错误类型，可自动修复的错误（CSS选择器未匹配/URL格式错误等）调用 auto_fixer 自动修复后重试（最多3次），需用户介入的错误（登录/验证码/CF破盾）调用 user_interaction 生成交互请求。
   > > **实现状态**：已实现（V2 重建阶段 5.1/5.2/7.9 完成；2026-07-17 v2 修正 cf-bypass 错误）。debug_runner.apply_auto_fix() 薄壳包装 auto_fixer.auto_fix_error()，接入 14 种自动修复（rule_parse/css/url_empty/network/rule_empty/relative_url/css_selector_empty/js_error/http_403/field_missing/syntax_error/cf_challenge/search_empty）+ 4 种需用户介入（need_login/jar_crash/jar_timeout/behavior_mismatch）。verify_fix() 调用 debug_book_source/debug_rss_source 执行端到端规则验证。阶段7.9新增并修复三处 BUG：①fix_cf_bypass（CF盾绕过：v2 修正后 loginUrl 设为**普通首页 URL**，禁止用 `@js:java.webView(null,...)` 形式——源码锚定 WebViewLoginFragment.loadUrl() 不识别 @js:；用户需手动点击"登录"按钮触发 WebView 加载；移除有 Rhino 1.8.1 语法错误的 `<js>java.ajax()</js>` 块；禁止设置 loginCheckJs 防止无限循环，陷阱#57；补全 UA/Accept/Referer headers）②fix_website_revamp（网站改版重分析：获取HTML→BeautifulSoup分析DOM→生成新CSS选择器；SSR/SPA降级 loginUrl 设为普通 URL，用户手动触发 WebView 渲染动态内容，Nuxt.js/Next.js/Vue SSR）③fix_css_selector（无HTML时不修改选择器，禁止破坏性驼峰转换/模糊匹配；有HTML时用BeautifulSoup验证选择器是否匹配）。

   **脚本选择决策树**：
   ```
   需要端到端调试（search→detail→toc→content）？
   ├─ 是 → debug-source.py（首选，真机级）
   └─ 否 → 需要验证什么？
           ├─ 源完整性 → verify-source.py
           ├─ CSS选择器 → verify-selector.py
           ├─ 加密解密 → verify-decrypt.py
           ├─ 图片解码 → verify-image.py
           ├─ 网站结构 → analyze_site.py
           └─ 浅层存活 → quick-verify.py
   ```

   - 执行优先级：`verify-source.py`（必选，源完整性）→ `debug-source.py`（**端到端调试，首选**）→ `verify-selector.py`（CSS验证）→ `verify-decrypt.py`（加密验证）→ `analyze_site.py`（网站分析）
   - **端到端调试（首选，真机级）**：`python scripts/debug-source.py --source {源JSON路径} --key {搜索关键词} --stage all`
     - 书源：search → detail → toc → content（含分页、变量持久化、Cookie 跨阶段、replaceRegex）
     - 订阅源：sort → content（含 ruleNextPage 分页、singleUrl 模式）
     - 日志与真机 Debug 一致（`[mm:ss.SSS] ︾︽⇒┌└≡◇` + state 10/20/30/40/-1/1000）
     - 退出码：0=成功，1=部分失败，2=严重错误
     - `--stage all|search|detail|toc|content`，key 格式：普通词(完整链路)/`http://...`(仅详情)/`++url`(仅目录)/`--url`(仅正文)
   - 其他脚本命令行详见下方"测试脚本"索引表

   **失败判定标准**（4 种失败条件，触发后进入 Phase 4）：
   | 失败类型 | 错误特征 | 处理方式 |
   |----------|---------|---------|
   | JVM缺函数 | `TypeError: java.xxx is not a function` | 标记 `jvm_evolution_needed=true`，Phase 5 补全 |
   | 网站反爬 | HTTP 403/503 或 CloudFlare 拦截 | 标记 `cf_detected=true`，需真机验证 |
   | 选择器返回空 | CSS/XPath/JSONPath 结果为空 | Phase 4 源码深挖规则语法 |
   | 解密失败 | decrypt 返回乱码或异常 | 检查 key/iv/mode/padding 参数 |

3. **可信度分层**（每个规则字段单独标注，最终汇总）：

| 可信度 | 适用 | 提示 |
|--------|------|------|
| 高 | CSS/纯逻辑JS/加密/AnalyzeRule + HTML直接获取验证通过 / Wayback(1年内)验证通过 | "已通过本地验证" |
| 中 | 依赖ajax()但无Cookie / Wayback(1年以上) / CMS样本库 / Google Cache | "Cookie差异可能影响" 或 "CMS样本验证通过" |
| 低 | 依赖ajax()+Cookie / 无HTML（猜测） | "需真机验证" |
| 不可验证 | WebView规则 | "必须在Legado中测试" |

**HTML来源可信度**：direct/playwright（不降级）> wayback 1年内（不降级）> wayback 1年以上/cms_sample/google_cache（降一级）> 无HTML（最低，需真机验证）

4. **输出**：JSON保存到 `output/book/`（书源）或 `output/rss/`（订阅源），必须`[...]`数组格式

**完成检查清单**：
- [ ] 执行测试验证（JVM仿真器或Python仿真）
- [ ] **执行端到端调试**（`debug-source.py`，首选）：4 阶段全部通过或精确定位失败阶段
- [ ] 输出可信度分层验证报告
- [ ] **识别代码进化需求**：JVM 测试报错 `TypeError: java.xxx is not a function` → 写入 basic-memory `(note_type=experience, tags=["jvm-evolution"])`，Phase 5 执行代码进化
- [ ] 输出 `[PHASE3_COMPLETE] 测试覆盖率:X%, 高可信:N, 中可信:N, 需真机:N`
- [ ] 写入 basic-memory 执行证据（按上方模板）

### Phase 4: 源码深挖（测试失败时必须执行）

**禁止猜测修复！** 必须读Legado源码定位根因。

**工具辅助**（新增，减少手动源码查阅）：
1. **source_navigation 自动导航**：根据错误类型自动映射到源码文件和行号（如 CSS选择器错误 → AnalyzeRule.kt CSS解析逻辑）
2. **error_diagnoser 修复建议**：每种错误类型对应修复建议模板，包含错误描述/可能原因/修复方法/参考文档链接
3. **auto_fixer 自动修复**：常见错误（CSS选择器重写/URL修正/规则语法修正）自动修复后重试，减少源码查阅需求

**手动源码深挖**（工具辅助不足时）：

| 核实场景 | 源码位置 |
|----------|----------|
| JS函数签名 | `app/.../help/JsExtensions.kt` |
| 字段定义 | `app/.../data/entities/BookSource.kt` / `RssSource.kt` |
| 规则引擎行为 | `app/.../analyzeRule/AnalyzeRule.kt` |
| RssSource解析 | `app/.../rss/RssParserByRule.kt` |
| 视频播放 | `app/.../model/VideoPlay.kt` |
| Rhino类限制 | `modules/rhino/.../RhinoClassShutter.kt` |
| CF JS Challenge 绕过 | JsExtensions.kt (webView方法) |
| Cookie 同步机制 | CookieStore.kt + BackstageWebView.kt |
| loginCheckJs 执行 | Rss.kt (L53-77) |
| loginUrl 执行 | `WebViewLoginFragment.kt` (loadUrl 方法，不识别 @js: 形式) + `SourceLoginDialog.kt` (仅 loginUi 非空时走 @js: 分支) |

> **源码访问**：本项目中 `app/src/main/java/` 下可直接读取，或从 GitHub [gedoor/legado](https://github.com/gedoor/legado) 获取最新版。

分析结果写入 `references/source-analysis/`（AI agent 可直接创建或追加文件），回到Phase 3重测。

**代码进化触发**：如果源码分析发现 Legado 有新函数/新行为是 JsExtensionsStub 未实现的，记录到 Phase 5 代码进化待办。

### Phase 5: 经验反哺 + 代码进化

1. **回顾**：新问题/新技巧/新规律？
2. **验证**：每条经验必须去Legado源码核实，未验证不写入
3. **文档反哺**（半自动，优化）：
   - **经验要素自动提取**（新增）：experience_manager 自动从调试结果中提取经验要素（网站特征/错误模式/修复方法/规则模式/可信度）
   - **经验草稿生成**（新增）：生成 JSON 草稿到 `experience/pending/` 目录
   - **AI 审核**（新增，可选，默认跳过）：AI 检查经验准确性和完整性，审核不通过标记为 rejected
   - **写入 basic-memory**（优化）：审核通过后自动写入 basic-memory（通过 MCP），降级路径写入 references/（通过文件写入）
   - **冲突解决**（新增）：conflict_resolver 检查同一网站特征的多条经验，按置信度0.5+时效性0.3+覆盖度0.2评分选优，过期经验（6个月未命中）自动降级
   - > **实现状态**：已实现（V2 重建阶段 5.3 完成）。experience_manager.extract() 自动从调试结果提取经验要素；write_pending() 写入 pending JSON；write_to_basic_memory() 输出 `[EXPERIENCE_PENDING]` MCP 指令到 stdout，AI agent 消费后通过 MCP `write_note` 写入 basic-memory。降级路径：MCP 不可用时经验保留在 pending JSON 待后续消费。
   - **经验消费规范**（AI agent 必须遵循）：
     - **触发条件**：debug_runner.py 主流程在调试完成后输出 `[EXPERIENCE_PENDING] {json}` 到 stdout
     - **消费步骤**：
       1. AI agent 解析 stdout 中的 `[EXPERIENCE_PENDING]` 标记，提取 JSON 指令
       2. 指令格式（由 experience_manager.write_to_basic_memory() 生成）：
          ```json
          {
            "tool": "mcp_basic-memory_write_note",
            "args": {
              "title": "经验: {website_feature}",
              "content": "# 经验: {website_feature}\n\n- **网站**: ...\n- **规则模式**: ...\n- **可信度**: ...\n- **源URL**: ...\n- **时间**: ...\n- **错误类型**: ...\n- **修复方法**: ...",
              "project": "legado",
              "note_type": "experience",
              "tags": ["auto-extracted"],
              "metadata": {经验草稿完整字段}
            }
          }
          ```
       3. AI agent 通过 `run_mcp` 工具调用 `mcp_basic-memory` 服务器的 `write_note` 工具，参数取自 args 字段
       4. 写入成功后，从 `output/experience-pending.json` 中移除已消费的记录（避免重复写入）
     - **降级路径**（MCP 不可用时）：
       1. AI agent 检测到 `mcp_basic-memory` 服务器不可用（run_mcp 调用失败）
       2. 经验保留在 `output/experience-pending.json`，不删除
       3. AI agent 在 `references/troubleshooting/auto/` 目录创建或追加 Markdown 文件，文件名格式 `{domain}-{error_type}.md`，内容含 `<!-- AUTO_GENERATED -->` 标记
       4. 后续 MCP 恢复时，AI agent 扫描 pending.json 并批量写入 basic-memory
     - **验证要求**：写入 basic-memory 后，AI agent 应执行 `search_notes(query="{website_feature}", project="legado")` 验证经验可被检索
   - 先更新Skill文档（权威源，references/ 下的文件，AI agent 可在任意子目录创建或追加文件）
   - 新经验写入 L2 时，参考 `references/_INDEX.md` 的"自进化指引"表格确定写入目标文件
   - 再写basic-memory（索引层），必须包含 source_doc + source_sync_date + sync_status
   - **新增写入目标**：
     - `references/special-scenarios/anti-crawl.md`：CF绕过方案
     - `references/cms-samples/{cms_type}/`：CMS样本和选择器
     - `references/troubleshooting/html-fetch-traps.md`：HTML获取方案
4. **权威源规则**：两处不一致时以Skill文档为准
5. **代码进化**：如果 JVM 仿真器或 Python 客户端有功能缺失，必须更新代码（见下方）
6. **进化成果沉淀**（代码进化后必须执行，确保可追溯）：
   - 写入 basic-memory（note_type=experience, tags=["evolution"]）：
     ```
     mcp_basic-memory_write_note(
         title="进化记录: {版本号} {简短描述}",
         content="## 变更内容\n{变更}\n\n## 触发原因\n{原因}\n\n## 验证结果\n{结果}",
         directory="experiences/",
         project="legado",
         note_type="experience",
         tags=["evolution", "jvm-evolution"],
         metadata={"version": "{版本号}", "change": "{变更}", "trigger_reason": "{原因}"}
     )
     ```
   - 更新未实现函数速查表（移除已补全函数）：`python scripts/evolution_log.py --update-table funcA,funcB`
   - 记录进化日志（版本号+变更+时间+触发原因）：`python scripts/evolution_log.py --log --version=v2.1 --change="补全XXX" --reason="TypeError"`
   - 重新计算精准度：`python scripts/precision_metrics.py --record --test-passed=N --test-total=M --real-passed=N --real-total=M`

**完成检查清单**：
- [ ] 更新 Skill 文档（权威源）
- [ ] 写入 basic-memory（索引层），记录 source_doc + sync_status
- [ ] 检查是否需要代码进化（JVM/Python）
- [ ] 输出 `[PHASE5_COMPLETE] 双写:完成/部分完成/失败, Schema验证:通过/未通过`

### 代码进化机制（JVM 仿真器 + Python 客户端）

> Phase 5 只反哺文档不够。新源需要 JsExtensionsStub 不支持的函数时，必须更新代码并重建 JAR。完整详情：[references/code-evolution.md](./references/code-evolution.md)

**进化触发**：Phase 3/4 识别 `TypeError: java.xxx is not a function` → 记录 basic-memory → Phase 5 执行
**进化流程**：记录需求 → 更新Kotlin源码 → 重建JAR → 更新Python客户端 → 重新验证
**未实现函数速查**：[references/mock-unimplemented-functions.md](./references/mock-unimplemented-functions.md)
**进化成果沉淀**：①写basic-memory(tags=["evolution"]) ②`evolution_log.py --update-table funcA,funcB` ③`evolution_log.py --log --version=v2.1 --change="..." --reason="..."` ④`precision_metrics.py --record --test-passed=N --test-total=M`
**精准度度量**：精准度 = 内置测试通过率 × 真机一致率（无真机数据时默认 1.0）。报告：`precision_metrics.py --report`
**规则层进化**：规则错误输出修正建议（不自动修改源JSON）：`rule_evolution.py --type=TYPE --rule=RULE --html=HTML`

### 任务后审计

任务完成后必须调用 `legado-workflow-auditor` Skill 审计。调用时机：Phase 5 完成后（若 Phase 4 触发则在 Phase 5 后调用）。

**上下文传递**：`source_name`/`source_type`/`phases_completed`/`execution_logs`（各 Phase basic-memory 执行证据 identifier）

**审计内容**：检查 basic-memory Phase 1/3/5 执行证据完整性（basic_memory_search/test_coverage/trap_check/dual_write 字段）→ 输出审计报告

---

## 与其他 Skill 的关系

> 本项目包含三个相互协作的 Skill，形成"审查 skill → 创建源 → 审计执行"的完整闭环。

| 维度 | legado-source-creator | legado-workflow-auditor | legado-skill-auditor |
|------|----------------------|------------------------|---------------------|
| 定位 | 书源/订阅源创建器 | 任务执行证据审计器 | Skill 质量审查器 |
| 触发时机 | 用户要求创建/修复/优化源 | source-creator 任务完成后（自动/手动） | 用户要求审查 skill 质量时 |
| 审查对象 | 网站规则 → JSON 配置 | Phase 1/3/5 执行证据 | Skill 本身（8维度42检查点） |
| 输出 | BookSource/RssSource JSON | 审计报告（通过/失败） | 审查报告 + 修复 + 健康度评分 |
| 修复能力 | 有（规则构建+测试） | 无（仅报告） | 有（精准修复+回归验证） |

**调用链路**：`legado-skill-auditor`（确保 skill 健康）→ `legado-source-creator`（创建/修复源）→ `legado-workflow-auditor`（审计执行证据）

**上下文传递**（source-creator → workflow-auditor）：`source_name`/`source_type`/`task_type`/`phases_completed`/`execution_logs`（详见上方"任务后审计"章节）

---

## 订阅源核心差异（vs 书源）

> **完整详情**：详见 [references/special-scenarios/rss-core-diff.md](./references/special-scenarios/rss-core-diff.md) + [rss-basic.md](./references/special-scenarios/rss-basic.md) + [rss-advanced.md](./references/special-scenarios/rss-advanced.md)

**核心要点**：
1. 字段扁平：ruleArticles/ruleTitle/ruleLink等都是独立String?字段
2. 搜索复用列表规则：searchUrl + 同一套ruleArticles/ruleTitle/ruleLink
3. ruleContent是扁平String?：直接写CSS/JS规则，非嵌套对象
4. 视频播放器：优先用 type=2 内置播放器（ruleContent 返回 JSON 数组即多集、嵌套 JSON 即多线路，详见 [references/special-scenarios/video-audio.md](references/special-scenarios/video-audio.md) 5.6 节）；需自定义播放器界面时用 `templates/` 模板 type=0

---

## 修复请求流程

> 修复流程是主工作流的简化版：跳过 Phase 2（规则已存在），直接从 Phase 1（查经验）开始。

Phase 1（查经验）→ 有经验→直接修复 → 无经验→Phase 4（源码深挖）→ Phase 3（测试）→ Phase 5（反哺）

| 类别 | 症状 | 方案 |
|------|------|------|
| 网站已挂 | sourceUrl不可访问 | 无法修复 |
| 选择器过时 | bookList匹配不到 | 重新curl+更新选择器 |
| 需Cookie/Header | 返回403 | CF标准配置（见`references/special-scenarios/anti-crawl.md`） |
| JS重度依赖 | 多字段含JS | 分析变量传递链+加密模式 |

---

## 输出目录

| 源类型 | 保存位置 | 格式要求 |
|--------|---------|---------|
| 书源 | `output/book/` | `[...]` 数组格式 JSON |
| 订阅源 | `output/rss/` | `[...]` 数组格式 JSON |

> 临时文件放 `temp/`，最终交付文件放 `output/`。首次使用时目录可能不存在，AI agent 应自动创建。

---

## 参考文档索引

| 文档 | 内容 | 何时读取 |
|------|------|----------|
| **[templates/](templates/)** | **视频播放器模板**（auto-video-player/hls-video-player/inject-video-player） | **视频站必用** |
| [rule-syntax.md](references/rule-syntax.md) | 五种规则语法+组合符号 | 编写规则时 |
| [url-template.md](references/url-template.md) | URL模板+UrlOption | 构建搜索URL时 |
| [booksource-schema.md](references/booksource-schema.md) | BookSource 完整字段定义 | 检查书源字段时 |
| [rss-source-entity.md](references/source-analysis/rss-source-entity.md) | RssSource 完整字段定义 | 检查订阅源字段时 |
| [examples.md](references/examples.md) | 完整JSON示例 | 需要参考时 |
| [special-scenarios/](references/special-scenarios/_index.md) | 登录/验证码/加密/图片/视频/RSS/搜索/正文/目录/编码（13子文档） | 遇特殊场景时 |
| [js-patterns/](references/js-patterns/_index.md) | JS模式参考（11子文档） | 编写JS规则时 |
| [js-extensions/](references/js-extensions/_index.md) | JS函数清单60+（11子文档） | 需要JS函数时 |
| [troubleshooting/](references/troubleshooting/_index.md) | 79条陷阱详解+修复方案（6子文档） | 遇到问题时 |
| [source-analysis/](references/source-analysis/_index.md) | 源码分析沉淀（6文档） | 写规则前先查 |
| [known-fix-patterns/](references/known-fix-patterns/_index.md) | 已知修复模式（8种：绝对路径/og meta/分页/净化/搜索方法/GBK/排行榜/音频） | 遇到已知问题时复用 |
| [site-features/](references/site-features/_INDEX.md) | 网站特征库（CF盾/高频问题/相对URL/特征→规则类型映射/WebView需求） | 分析网站特征时 |
| [cms-samples/](references/cms-samples/) | CMS样本库（选择器+HTML样本） | 检测到CMS类型时 |
| [tools/html_fetcher.py](tools/html_fetcher.py) | HTML获取回退链（curl→Wayback→CMS样本→Google Cache→Playwright） | curl获取HTML失败时 |
| [tools/fetch_html.py](tools/fetch_html.py) | Playwright HTML获取 | 需要JS渲染获取HTML时 |
| [mock-unimplemented-functions.md](references/mock-unimplemented-functions.md) | JsExtensionsStub 未实现函数速查表（96个，含影响级别+处理建议） | JVM测试报错 `TypeError: java.xxx is not a function` 时 |
| [basic-memory-usage.md](references/basic-memory-usage.md) | basic-memory 完整操作规范（MCP工具/L3目录/笔记类型/搜索策略/反哺策略/双写一致性） | Phase 1 搜索 / Phase 5 反哺时 |
| [jvm-infrastructure.md](references/jvm-infrastructure.md) | JVM 测试基础设施详情（legado-jvm架构/API速查/使用示例/可信度标注/降级路径） | 需要JVM测试详情时 |
| [code-evolution.md](references/code-evolution.md) | 代码进化机制详情（触发条件/进化流程/Kotlin源码结构/检查清单） | Phase 5 代码进化时 |
| [rss-core-diff.md](references/special-scenarios/rss-core-diff.md) | 订阅源核心差异详情（字段对比/构建顺序/相关陷阱） | 创建订阅源时 |

### 测试脚本

| 脚本 | 用途 | --jvm | --jar-path |
|------|------|-------|------------|
| `scripts/debug-source.py` | **端到端真机级调试（首选）**：书源 search→detail→toc→content / 订阅源 sort→content | ✅ | ✅ |
| `scripts/quick-verify.py` | 浅层验证（网站存活+HTTP） | ❌ | ❌ |
| `scripts/verify-source.py` | 深度链路验证（规则引擎模拟解析） | ✅ | ✅ |
| `scripts/verify-decrypt.py` | 解密验证（`--algo --key --iv --data`） | ✅ | ✅ |
| `scripts/verify-selector.py` | 选择器验证（`--url --selector`）；`--mode` 选择器模式(css/xpath/jsonpath) `--attr` 提取属性 `--header` 请求头 | ✅ | ✅ |
| `scripts/verify-image.py` | 图片验证（`--url --key --iv`） | ✅ | ✅ |
| `scripts/analyze_site.py` | 网站结构分析（`--url`） | ✅ | ✅ |
| `scripts/verify-source.py` | 源完整性验证（`--source-json`） | ✅ | ✅ |
| `scripts/generate-js-doc.py` | 提取JS模式生成文档 | ❌ | ❌ |
| `scripts/deep-analyze-js.py` | 深度JS分析（变量传递链/加密模式） | ❌ | ❌ |
| `scripts/check_health.py` | 三合一健康检查（死链+版本锁+文件债务） | ❌ | ❌ |
| `scripts/evolution_log.py` | 进化日志记录+速查表更新（`--log` / `--update-table` / `--history`） | ❌ | ❌ |
| `scripts/precision_metrics.py` | 精准度度量（`--record` / `--report`） | ❌ | ❌ |
| `scripts/rule_evolution.py` | 规则层进化修正建议（`--type` / `--rule` / `--html`） | ❌ | ❌ |
| `tools/html_fetcher.py` | HTML获取回退链（`--url URL --json` / `--cms-type TYPE` / `--output FILE`） | ❌ | ❌ |

### JVM 工具

| 文件 | 用途 |
|------|------|
| `legado-jvm/build/libs/legado-jvm.jar` | legado-jvm: 从 Legado 源码抽取的完整规则引擎（最高覆盖率） |
| `tools/rule_engine_client.py` | Python客户端（RuleEngineClient类，JDK检测+JAR多路径回退） |
| `tools/jvm_helpers.py` | 共享工具（add_jvm_args/init_jvm_client/assess_confidence） |
| `tools/rhino-1.8.1.jar` | Rhino 1.8.1 独立命令行（Legado使用的版本，快速测试JS片段：`java -jar tools/rhino-1.8.1.jar`） |
| `references/source-analysis/ajax-diff-analysis.md` | JsExtensionsStub ajax()差异分析 |

### 辅助工具（阶段七/八：减少用户手工操作 + 查漏补缺）

> **定位**：可选辅助模块，提升"检测到→尝试辅助→辅助失败再标记"的积极模式。未安装不影响 debug-source.py 基础功能。

| 工具 | 用途 |
|------|------|
| `tools/obstacle_resolver.py` | 障碍统一解析器（登录/CF/验证码表单分析+Cookie导入+持久化） |
| `tools/crypto_analyzer.py` | 加密自动分析（JS扫描+密钥提取+模式判断+解密代码生成） |
| `tools/auto_fixer.py` | 错误自动修复（CSS/URL/字段/语法修复+历史学习+循环验证） |
| `tools/interactive_guide.py` | 用户交互引导（登录/CF/验证码引导+规则确认+进度反馈） |
| `tools/cookie_manager.py` | Cookie/Session管理（文件持久化+跨网站复用+过期管理+导入导出） |
| `tools/smart_http_client.py` | 智能HTTP客户端（自适应重试+代理池+频率自适应+UA池+Referer） |
| `tools/knowledge_matcher.py` | 知识库匹配（网站特征提取+相似度计算+案例匹配+自动更新） |
| `tools/degradation_chain.py` | 统一降级链（自动求解→Cookie导入→手动引导→标记unverifiable） |
| `tools/workflow_timer.py` | 工作流耗时统计（5阶段耗时+瓶颈分析+优化建议） |
| `tools/error_translator.py` | 错误信息翻译（技术错误→用户友好描述+修复建议+分级） |
| `tools/user_action_minimizer.py` | 用户操作最小化（自动化尝试→手动降级，每个手工操作有自动化尝试记录） |

### Python 客户端 3.0 新功能（阶段六新增）

> Legado Client 3.0 新增数据库存储、Web 管理界面、真机测试链路、CLI 新命令。

#### 数据库查询模式

- MySQL 存储层（`storage/` 模块）：ORM 模型（Source/Collection/DebugResult/DeviceConfig）+ 异步 CRUD 仓储层
- 降级策略：MySQL 不可用时 `config.db_available=False`，所有 DB 操作静默降级，不抛异常
- 健康检测：`DatabaseHealthChecker` 每 30s 探测连接状态，自动恢复/降级
- CLI 的 `db` 子命令支持：init/migrate/reset/import-dir/stats/backup/restore
- Phase 3 测试阶段可通过 `--skip-db-lookup` 跳过数据库查询，`--db-only` 仅查库不测试

#### 真机测试链路

- `LegadoWebClient`：封装 Legado App 26 个 HTTP API + 3 个 WebSocket API
- 设备管理：`DeviceConfig` 表 + `/api/devices` CRUD + 连接测试
- 推送/拉取：`/api/devices/{id}/push` 和 `/api/devices/{id}/pull`
- Legado 代理：`/legado/{path}` HTTP 代理 + `/ws/legado/{path}` WebSocket 双向代理
- 对比测试：`/api/debug/compare` 同时在真机和 JAR 上测试，返回差异分析
- JAR 优化闭环：`/api/debug/jar-optimize` 真机通过但 JAR 失败时的修复建议

#### Web 管理界面

- FastAPI 应用（`server/app.py`）：统一 API 响应格式 `{ok, data, error}`
- 7 个路由模块：sources/stats/device/collections/import_export/legado_proxy/debug
- 中间件：CORS + 请求日志 + 数据库降级 + 请求体大小限制（10MB）
- Vue3 前端（`web/admin/`）：源列表/详情/调试/设备/导入/合集/统计页面
- 健康检查：`GET /api/health` 返回数据库+JVM 状态
- 静态文件挂载：SPA 回退（`web/dist/`）

#### 新增 CLI 命令

| 命令 | 说明 |
|------|------|
| `legado-client db init` | 建表 + 扫描 output/ 导入 |
| `legado-client db migrate` | Alembic 迁移 |
| `legado-client db reset` | 删除所有表并重建 |
| `legado-client db import-dir --dir PATH` | 导入目录下 JSON |
| `legado-client db stats` | 源数量统计 |
| `legado-client db backup --output PATH` | 备份数据库到 JSON |
| `legado-client db restore --input PATH` | 从 JSON 恢复 |
| `legado-client export --type book/rss --output PATH` | 导出源为 Legado 兼容 JSON |
| `legado-client serve --host 127.0.0.1 --port 8080` | 启动 Web 服务 |
| `legado-client debug --skip-db-lookup` | 跳过数据库查询 |
| `legado-client debug --db-only` | 仅查数据库不测试 |

---

### 不实现清单（Do-Not-Implement List）

| # | 不实现项 | 原因 |
|---|---------|------|
| 1 | BackstageWebView | 依赖 Android WebView 组件，JVM 环境无法模拟，标记为 unverifiable |
| 2 | importScript | 动态加载外部 JS 文件，涉及文件系统+网络+Rhino 上下文，复杂度高且影响 <5% 书源 |
| 3 | queryTTF | 字体文件解析（反爬字体替换），需要字体解析库，影响 <2% 书源 |
| 4 | 文件压缩包（zip/rar 解压） | 需要 Java 解压库，影响 <1% 书源，用户可手动解压 |
| 5 | createAsymmetricCrypto | RSA 非对称加密，影响 <3% 书源，hutool 支持但仿真复杂度高 |

> **覆盖率统计策略**：高频场景优先，不追求 100% 函数覆盖率，避免 scope creep。以"高频场景覆盖率"为准（只统计影响 >5% 书源的功能），目标 >90%。

---

## 能力边界（Capability Boundaries）

> **任何 AI agent 使用本 skill 前，必须阅读本章节，了解 skill 能做什么、不能做什么、以及何时需要用户介入。**

### Skill 能力矩阵

| 能力 | 支持度 | 说明 |
|------|--------|------|
| **创建书源** | ✅ 完整 | 5 种解析方式（CSS/XPath/JSONPath/Regex/JS）+ 登录+验证码+加密+视频 |
| **创建订阅源** | ✅ 完整 | 3 种类型（HTML/图片/视频）+ RSS基础+高级 |
| **修复/优化源** | ✅ 完整 | 80 条陷阱检查 + 自动修复建议 + 社区修复案例 |
| **JAR 仿真测试** | ✅ 完整 | 单源调试 + 批量测试 + 搜索→详情→目录→正文全链路 |
| **真机 WebSocket 调试** | ✅ 完整 | `/bookSourceDebug` + `/rssSourceDebug` + `/searchBook` |
| **真机 HTTP 管理** | ✅ 完整 | 源 CRUD + 推送/拉取 + 删除（通过 LegadoWebClient） |
| **批量校验** | ✅ 完整 | 连通性 + JAR仿真 + 真机调试，三种模式 |
| **死源清理** | ✅ 完整 | DNS检查→真机删除→数据库标记，一键操作 |
| **前端管理界面** | ✅ 完整 | Vue3 管理面板（源列表/详情/调试/设备/批量校验/一键清理） |
| **Python CLI** | ✅ 完整 | 数据库管理 + 调试 + 导入导出 + Web服务 |
| **对比测试** | ⚠️ 部分 | 真机vs JAR结果对比框架已有，但需真机 DNS 正常才可精确对比 |
| **JAR 自动优化** | ⚠️ 部分 | jar_optimizer.py 已实现，但需人工确认优化方案 |

### Skill 不能做什么（硬边界）

| 不能做 | 原因 | 替代方案 |
|--------|------|---------|
| **WebView 渲染** | 依赖 Android WebView 组件 | 标记 `needsWebView=true`，用户需在真机测试 |
| **CloudFlare JS Challenge** | 需要无头浏览器+JS执行 | 用 `webView()` 在真机通过，或 DrissionPage |
| **Android 原生 API** | Cronet/Glide/ReadBook 单例 | 标记为已知限制 |
| **字体反爬（queryTTF）** | 需要字体解析库 | 影响 <2% 书源，用户手动处理 |
| **importScript 动态加载** | 涉及文件系统+网络 | 影响 <5% 书源 |
| **登录 UI 交互** | 需要用户输入账号密码 | 标记 `needsUserIntervention=true`，引导用户手动登录 |
| **验证码图片识别** | 需要 OCR/用户输入 | `getVerificationCode()` 弹窗让用户输入 |

### JAR 仿真器 vs 真机差异

| 维度 | JAR 仿真器 | 真机 |
|------|-----------|------|
| JS 引擎 | Rhino on JVM | Rhino on Android |
| 网络栈 | OkHttp (JVM) | Cronet + OkHttp (Android) |
| DNS | PC DNS | Android DNS（可能不同） |
| UA | 伪装移动 Chrome | 真实 Android WebView |
| SSL | 信任所有证书 | 系统信任链 |
| Cookie | 内存 CookieStoreStub | CookieManager |
| WebView | ❌ 不支持 | ✅ 支持 |
| 一致率 | **86.7%** (13/15) | 100%（基准） |

### 真机测试前提条件

1. **真机 Legado App 必须开启 Web 服务**：设置 → 其他设置 → Web 服务 → 开启
2. **HTTP 端口（默认 1122）**：源 CRUD + 书架操作
3. **WebSocket 端口（默认 1123 = HTTP+1）**：实时调试
4. **网络可达**：PC 能 ping 通真机 IP
5. **DNS 配置**（模拟器场景）：模拟器 DNS 可能与宿主机不同，需手动配置

### 批量操作工具清单

| 工具 | 用途 | 调用方式 |
|------|------|---------|
| `deep_analysis.py` | 大规模闭环测试（分层采样+JAR/真机+差异分析） | `python deep_analysis.py --mode jar --sample-size 200` |
| `batch_clean_dead_sources.py` | 一键清理死源（DNS检查+真机删除+DB标记） | `python batch_clean_dead_sources.py --delete --mark-db` |
| `debug-source.py` | 端到端真机级调试（首选） | `python debug-source.py` |
| `quick-verify.py` | 浅层可用性验证 | `python quick-verify.py` |
| `verify-source.py` | 深度链路验证 | `python verify-source.py` |
| 前端"一键清理" | BatchValidatePage.vue 独立面板 | 选择设备→选择类型→一键清理 |
| 后端 API | `POST /api/devices/{id}/clean-dead` | `{source_type, dry_run, mark_db}` |

### 经验引擎（basic-memory project=legado）

AI agent 在新对话中可通过 basic-memory 快速获取历史经验：

```python
# Phase 1: 搜索经验
search_notes(query="网站特征关键词", search_type="hybrid", project="legado")

# 已沉淀的关键经验笔记：
# - websocket-debug/: WebSocket调试5大陷阱+3个有效路径+Python/JS连接示例
# - jar-optimization/: JAR优化经验（UA伪装+SSL兼容+DNS回退修复）
# - batch-validate/: 批量校验功能实现指南+一键清理功能指南
```

### 新增 WebSocket 调试 API 速查

| 路径 | 功能 | 请求 |
|------|------|------|
| `/bookSourceDebug` | 书源调试（搜索→详情→目录→正文） | `{"tag": "源URL", "key": "搜索关键字"}` |
| `/rssSourceDebug` | RSS源调试（文章列表） | `{"tag": "源URL", "key": "首页"}` |
| `/searchBook` | 全源搜索（⚠️搜全部书源，2万+源时极慢） | `{"key": "搜索关键字"}` |

> **WebSocket 陷阱**：真机调试日志是纯文本格式 `[MM:SS.mmm] msg`（非 JSON），需关键词匹配判定阶段；端口 1123 不响应 HTTP 请求（仅 WebSocket 升级握手）
