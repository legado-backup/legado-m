# Legado Source Creator Skill v4

> 帮助 AI 为 Legado 阅读器生成"**优秀好用**"的书源/订阅源 JSON。
> **v4 核心目标**：必填字段强制校验 + 真机测试集成 + 自动修复循环。

## 核心原则（v4）

1. **源码验证优先**：写规则前先去 Legado 源码核实，不凭经验臆测
2. **必填字段强制**：所有源必须通过 `MandatoryFieldValidator` 校验
3. **JSON 输出合规**：所有 None 字段必须经 `sanitize_source_json` 过滤为空字符串
4. **真机验证为最终标准**：JVM 仿真仅覆盖规则引擎层，真机测试集成是验收门禁
5. **自动修复闭环**：生成 → 测试 → 失败 → 自动诊断 → 修复 → 重测
6. **输出安全防线（2026-07-25 强化）**：脚本可获取真实数据用于技术分析，但**思考链和输出内容双闭口禁止违禁词**。域名→站点代号（站点A/B/C）、源名称→源[N]、URL→路径模式（/path/{id}）、分类名→分类[N]、cookie/token→***。Grep只搜技术字段（id/type/ruleImage/函数名）不搜业务字段（sourceName/sourceUrl/title）。logcat只输出错误码/异常类型/调用栈，源名称/域名/URL全部代号化
7. **导出目录规范（2026-07-25 强化）**：所有新生成或优化的源 JSON **必须导出到 项目`output/ai_source/` 目录**，禁止散落在 temp/ 或其他目录。
   - **订阅源**：`output/ai_source/rss/`（如 `rssSource_video_fixed_20260725.json`）
   - **书源**：`output/ai_source/book/`
   - **命名规范**：`{类型}_{描述}_{日期YYYYMMDD}.json`（如 `rssSource_video_xxxsite_20260725.json`、`bookSource_novel_xxx_20260725.json`）
   - **唯一导出目录**：`output/ai_source/` 是 AI 生成/优化源的唯一交付目录，便于统一管理和后续导入

## 4 阶段闭环工作流（v4）

### Phase 1: 分析（v4 强化 - 必经 Playwright）

**目标**：用 Playwright MCP 真实分析网站结构 + 找同类经验。

> **🔴 铁律**（v4 强化，2026-07-18 反哺）：禁止仅凭 CMS 主题名或经验猜测字段值，**必须用 Playwright MCP 真实访问目标站点**提取4字段（sourceIcon/searchUrl/sortUrl/ruleNextPage）。
> 完整指南：[references/source-analysis/playwright-site-analysis.md](./references/source-analysis/playwright-site-analysis.md)

1. **必经 Playwright 访问**：用 `playwright_navigate` 真实访问目标站点首页（headless=True, waitUntil=domcontentloaded）
2. **必经 JavaScript 提取**：用 `playwright_evaluate` 执行 IIFE 提取4字段技术结构（favicon/searchForm/categoryLinks/pagination）
3. 搜索 `basic-memory`（project=legado）找同类经验
4. 识别触发字段：CF/登录/验证码 → 必须先源码验证再写规则
5. **必经播放页链路验证（视频源，2026-07-28 反哺）**：视频网站常见三层结构"列表页→详情页→播放页"，**必须用 Playwright 点击列表项验证落地页是否直接含视频**：(1)点击列表项，检查落地页是否含 `<video>` 标签或 m3u8 流；(2)若落地页是详情页（无视频），分析"详情页→播放页"跳转规律（URL模式差异如 `/info/` → `/play/`、按钮选择器、href 属性）；(3)优先用 `##` 操作符转换 URL（如 `a@href##info##play`），次选 JS 提取播放页 URL。**禁止**假设列表链接直接是播放页
6. 把提取结果记录到 `source_ref` metadata（`verified_against_source=true`）

```python
# Playwright 提取结果 → 源 JSON 字段映射（v4 反哺辅助函数）
def build_search_url(form_info):
    """从表单信息构建 searchUrl"""
    if not form_info:
        return None
    action = form_info['action'].rstrip('?')
    text_input = next((i for i in form_info['inputs'] if i['type'] in ('text', 'search')), None)
    if text_input:
        sep = '&' if '?' in action else '?'
        return f"{action}{sep}{text_input['name']}={{{{key}}}}"
    return None

def build_sort_url(category_links, hot_links, base_url):
    """从分类链接+排序参数构建 sortUrl"""
    items = []
    if hot_links:
        items.append(f"热门::{hot_links[0]}")
    if category_links:
        all_cat = next((l for l in category_links if '/categories/' in l['href']), None)
        if all_cat:
            items.append(f"全部分类::{all_cat['href']}")
    items.append(f"最新::{base_url}")
    return '\n'.join(items)

def extract_next_page_selector(pagination_html):
    """从分页HTML提取下一页CSS选择器"""
    if not pagination_html:
        return None
    if 'next page-link' in pagination_html:
        return '@CSS:a.next.page-link@href'
    if 'class="next"' in pagination_html:
        return '@CSS:a.next@href'
    if 'rel="next"' in pagination_html:
        return '@CSS:a[rel="next"]@href'
    return None
```

### Phase 2: 生成 + 必填校验（v4 强化）

**目标**：编写源 JSON + sanitize + 必填字段强制校验。

1. 按 [references/](./references/) 写源 JSON
2. **必经 sanitize**：所有 None 值会触发 Legado Rss.kt:64 ReferenceError
3. **必经 MandatoryFieldValidator 校验**（v4 新增）：

```python
from legado_client.utils.file_utils import sanitize_source_json
from legado_client.validator import validate_source, format_validation_report

# 1. sanitize 清理 None
sanitized = sanitize_source_json(source_dict)

# 2. 必填字段强制校验（strict_recommended=True 用户"优秀好用"标准）
result = validate_source(sanitized, source_type='rss', strict_recommended=True)
if not result['passed']:
    print(format_validation_report(result))
    # CRITICAL 缺失（sourceUrl）→ 必须补全才能继续
    # MANDATORY 缺失（ruleArticles 等）→ 必须补全
    # RECOMMENDED 缺失（sourceIcon/searchUrl/sortUrl）→ 用户要求必填，必须补全
    raise ValueError("必填字段校验未通过")
```

### Phase 3: 真机验证（v4 集成）

**目标**：编译+安装+导入+真机测试+日志分析。

```python
from legado_client.runtime import validate_source_on_device

# 端到端真机验证（自动调用 ai_tests 脚本）
result = validate_source_on_device(
    source_obj=sanitized,
    source_type='rss',
    skip_build=False,  # True=跳过编译（APK 已装）
)
if not result['success']:
    for err in result['errors']:
        print(f"[{err['stage']}] {err['message']}")
```

或手动跑固定脚本（SOP: [fixed_test_workflow.md](../../ai_tests/docs/fixed_test_workflow.md)）：

```bash
ai_tests/venv/Scripts/python.exe ai_tests/scripts/quick_build_install.py
ai_tests/venv/Scripts/python.exe ai_tests/scripts/import_rss_source.py <json>
ai_tests/venv/Scripts/python.exe ai_tests/scripts/l2_verify_video_player.py --scenario error_patterns
```

### Phase 4: 自动修复循环（v4 新增）

**目标**：失败 → 自动诊断 → 修复 → 重测。

```python
from legado_client.runtime import auto_fixer_loop

# 一键自动修复循环
result = auto_fixer_loop(
    source_obj=source_dict,
    source_type='rss',
    max_attempts=3,
    skip_build=False,
    strict_recommended=True,
)
if result['success']:
    print(f"修复成功，最终源: {result['final_source']}")
else:
    print(f"修复失败，剩余错误: {result['remaining_errors']}")
    print(f"修复轨迹: {result['fix_history']}")
```

## v4 必填字段清单（基于源码深度分析）

> 完整分析：[docs/temp-analysis/legado_mandatory_fields.md](../../docs/temp-analysis/legado_mandatory_fields.md)

### RssSource 字段级别

| 级别 | 字段 | 不填后果 |
|------|------|----------|
| **CRITICAL** | `sourceUrl` | 导入时抛 NoStackTraceException("不是订阅源") |
| **MANDATORY** | `sourceName`/`ruleArticles`/`ruleTitle`/`ruleLink`/`ruleContent` | 核心功能失效（无名称/无列表/无标题/无链接/无正文） |
| **RECOMMENDED** | `sourceIcon`/`searchUrl`/`sortUrl`/`sourceGroup`/`sourceComment` | 用户要求必填（优秀好用标准） |
| **OPTIONAL** | `ruleRoutes`/`ruleEpisodes` | 仅 type=2 视频源使用，多线路多集按需采集（v3.26.072420+新增，详见"多线路多集按需采集标准写法"章节） |

#### 🔴 sourceComment 字段强制规范（2026-07-28 反哺）

> **sourceComment 不是写技术说明，而是写网站恢复信息！** 目的：网站丢失时能快速找到网站并修复完善。

**必须包含的信息**（用 Playwright 从目标站点获取）：
1. **回家域名/永久导航域名**：站点顶部横幅/页脚常含"回家域名:xxx.xyz"或"永久地址:xxx.com"，这是最重要的恢复信息
2. **联系邮箱**：页脚或"关于我们"页面的邮箱（如 `xxx@gmail.com`）
3. **当前域名**：sourceUrl 中的域名
4. **备用域名**（如有）：站点公告的镜像/备用域名
5. **发布页地址**（如有）：专门的发布页链接

**获取方式**（Phase 1 必经步骤）：
```javascript
// Playwright JS 提取网站恢复信息
(function(){
  var result = {domainHints:[], contactInfo:[]};
  // 1. 查找顶部横幅/页脚的"回家域名"/"永久地址"
  var bodyText = document.body.innerText || '';
  var keywords = ['回家域名','永久地址','官网地址','备用域名','发布页','联系站长'];
  for(var i=0;i<keywords.length;i++){
    var idx = bodyText.indexOf(keywords[i]);
    if(idx>=0) result.domainHints.push(bodyText.substring(idx, idx+50));
  }
  // 2. 查找邮箱
  var emailMatch = bodyText.match(/[\w.]+@[\w.]+\.\w+/);
  if(emailMatch) result.contactInfo.push('邮箱:'+emailMatch[0]);
  // 3. 查找 Telegram/微信/QQ 群
  var allLinks = document.querySelectorAll('a');
  for(var j=0;j<allLinks.length;j++){
    var h = allLinks[j].getAttribute('href')||'';
    if(h.indexOf('t.me')>=0) result.contactInfo.push('TG:'+h);
  }
  return JSON.stringify(result);
})()
```

**sourceComment 格式**：
```
[网站恢复]回家域名:xxx.xyz | 邮箱:xxx@gmail.com | 当前域名:xxx.buzz [技术]简短技术说明
```

**反模式**（禁止）：
- ❌ sourceComment 只写技术说明（如"列表页已验证;ruleLink用##操作符"）
- ❌ sourceComment 写空或写"无"
- ❌ 不获取网站恢复信息就随便写
- ❌ 技术说明过长淹没恢复信息

### BookSource 字段级别

| 级别 | 字段 | 不填后果 |
|------|------|----------|
| **CRITICAL** | `bookSourceUrl` | 导入时抛 NoStackTraceException("不是书源") |
| **MANDATORY** | `bookSourceName`/`searchUrl`/`ruleSearch.bookList`/`ruleBookInfo.name`/`ruleToc.chapterList`/`ruleContent.content` | 核心功能失效 |
| **RECOMMENDED** | `bookSourceGroup`/`bookSourceComment` | 优秀好用标准 |

### 设计哲学

Legado 源码采用"**最小必填 + 渐进增强**"模式：
- 导入层面只校验 @PrimaryKey 非空（CRITICAL）
- 功能层面通过 `isNullOrBlank` 判断动态降级（MANDATORY 缺失时功能降级而非崩溃）
- v4 校验器在"功能必填"基础上加上用户要求的"优秀好用"标准（RECOMMENDED 强制）

## 核心陷阱速查（Top 39）

> 完整陷阱库见 [references/troubleshooting/](./references/troubleshooting/)

### JSON 输出陷阱

1. **None 序列化 bug**（v3 修复）：Python None → 字符串 "None" → Rss.kt:64 当 JS 执行 → ReferenceError。**修复**：用 `sanitize_source_json` 过滤
2. **loginUrl 禁用 `@js:java.webView()`**：WebViewLoginFragment.loadUrl() 不识别 @js: 形式
3. **loginCheckJs 陷阱**：每次请求执行，调 `java.startBrowserAwait()` 导致无限循环
4. **header 字段格式**：必须是 JSON 字符串（`json.dumps`），不是 dict

### 规则引擎陷阱

5. **@CSS vs class.**：`@CSS:.item` 与 `class.item` 等价但混用出错
6. **@XPath 转义**：属性值含 `"` 必须用 `'` 包裹
7. **@js 内联 vs `<js>` 标签**：前者追加在规则后，后者独立块
8. **put/get 变量**：跨规则传值必须用 `@put:{key:rule}` + `@get:{key}`
9. **列表规则返回 string**：必须用 `||` 分隔多结果
10. **正则 `{{}}` 陷阱**：`{{regex}}` 用于匹配，`{{regex|replace}}` 用于替换

### 网站类型陷阱

11. **CF 站点**：检查 `<title>Just a moment</title>` 或 `cf-challenge` cookie
12. **登录站点**：必须配置 loginUrl + 人工登录后才能爬取
13. **验证码站点**：无法自动绕过，标记 unverifiable
14. **图片加密**：先校验块对齐（DES=8, AES=16, SM4=16）
15. **JS 解密**：用 `crypto_analyzer.py` 扫描加密调用

### 真机验证陷阱

16. **Room WAL 模式**：导入前必须 `am force-stop` App，否则 WAL 覆盖
17. **Cookie 自动同步**：JVM 仿真不覆盖，必须真机验证
18. **WebView 生命周期**：destroy/setLayoutParams 必须在 UI 线程
19. **JS 引擎返回值**：类型不可信，必须类型容错（is ByteArray / is InputStream）
20. **ExoPlayer cacheDataSourceFactory**：上游 OkHttpDataSource 不支持 file://
21. **import_rss_source.py chown uid bug**：脚本硬编码 `u0_a0:u0_a0`，但不同包/不同实例 uid 不同（正式包实例0=10065, 实例1=10020, 测试包=10064）。导入后必须手动 `chown <实际uid>:<实际uid> /data/data/<pkg>/databases/legado.db` 修复权限，否则抛 SQLiteCantOpenDatabaseException + FATAL EXCEPTION arch_disk_io_0 崩溃。查 uid：`adb shell dumpsys package <pkg> | grep userId=`
22. **新模拟器实例DB迁移**：新装App首次启动前 rssSources 表只有48列（无 ruleRoutes/ruleEpisodes），导入含这两字段的源JSON报 "table rssSources has no column named ruleRoutes"。必须先 `am start` App 触发数据库迁移到49列，再 pull db 导入源
23. **模拟器多AI并发冲突**：同一模拟器上共存包(io.legado.app.debug)/测试包(io.legado.miss.app.debug)/正式包(io.legado.miss.app.release) 被不同AI操作会抢占前台。测试时必须用 `am start -W` 确认 ResumedActivity 是目标包；推荐用独立MEmu实例（`memuc start -i 1`，adb端口21513）
24. **新MEmu实例网络DNS问题**：新启动实例可能缺默认路由+DNS解析失败（ping IP通但ping域名报unknown host）。修复：`su -c 'ip route add default via 192.168.232.1 dev wlan0'` + `settings put global dns1 8.8.8.8`。若仍失败需重启实例
25. **ExoPlayer HLS MIME检测（动态URL）**：play.php 等动态URL不以 .m3u8 结尾时，DefaultMediaSourceFactory 的 URL 后缀检测失败，误用 ProgressiveMediaSource 报 UnrecognizedInputFormatException(3003)。修复：ruleContent 提取m3u8 URL后追加 `format=m3u8` 参数，ExoPlayerHelper.getMimeType 检测该参数返回 APPLICATION_M3U8，setMimeType 让 factory 正确创建 HlsMediaSource。**v3.26.0725+ 优化**：getMimeType 已新增支持 `m3u8=1` 参数和 `index.m3u8` 路径识别，这两种情况下无需追加 format=m3u8 也能自动识别；兼容旧版本仍建议追加
26. **ruleContent 提取 HLS URL 模式**：内联JS的 `hls.loadSource('xxx')` 提取模式：`@js:var m=result.match(/hls\\.loadSource\\(['"]([^'"]+)['"]\\)/);var u=m?m[1]:'';if(u){u+(u.indexOf('?')>=0?'&':'?')+'format=m3u8'}else{''}`。追加 format=m3u8 触发陷阱25的 MIME 检测。**v3.26.0725+ 简化版**：若 URL 已含 `m3u8=1` 或路径含 `index.m3u8`，可省略 format=m3u8 追加，直接返回视频地址即可
27. **违禁词安全防线（2026-07-25）**：Playwright分析/logcat调试/JSON字段输出时，禁止原样输出真实URL/源名称/分类名/cookie。脚本可获取真实数据用于技术分析（如选择器提取、JS执行），但AI思考链和最终输出必须用代号替代。**铁证**：summary原样引用站点完整URL和分类名，违反双闭口约束。**修复**：(1)Playwright evaluate结果在AI输出前先用脚本过滤为编号（源[1]/源[2]/分类[N]）；(2)logcat用Grep过滤技术关键词（Exception/Error/FATAL/自定义tag），head_limit≤20，原始日志行不输出；(3)JSON字段值在输出时只展示技术结构（选择器/JS模式），不展示业务值；(4)站点URL一律用站点A/B/C+路径模式，如 `/list/{分类}/index.html`

### 批量源完善陷阱（2026-07-25 rssSource 完善任务反哺）

28. **MacCMS searchUrl 接口混淆**：searchUrl 必须用 `ac=list`（搜索接口），不能用 `ac=detail`（详情接口）。**铁证**：批量源修复时发现大量源误用 `ac=detail` 导致搜索无结果或JSON解析错误，搜索通过率从 28/41 提升至 33/41。**区分**：`ac=list` 返回列表JSON用于搜索/分类；`ac=detail&ids={id}` 返回详情JSON用于ruleLink跳转后解析线路和集数。**修复**：批量将 searchUrl 中的 `ac=detail` 替换为 `ac=list`

29. **HTML搜索模式适配（API禁用时）**：部分MacCMS站点禁用API搜索接口，此时切换HTML搜索模式：`searchUrl=/index.php/vod/search/page/{{page}}/wd/{{key}}.html`。ruleArticles选择器按站点模板：模板A用 `ul.videoContent li` + `a.videoName@text`，模板B用 `div.xing_vb ul li:has(span.xing_vb4)` + `span.xing_vb4 a@text`。**关键**：`div.xing_vb ul li` 不加 `:has()` 过滤会包含分类标题li（无vod_id），导致ruleLink提取失败

30. **ruleLink JS拼接API详情URL模式**：HTML搜索结果li中只有 `/vod/detail/id/123.html` 形式的相对链接，但 ruleContent/ruleRoutes/ruleEpisodes 需要 MacCMS 详情JSON。**修复**：ruleLink 用 JS 从HTML提取 vod_id 后拼接 API URL：`<js>var m=result.match(/detail\/id\/(\d+)/);if(!m)return '';var id=m[1];var base=baseUrl||(source&&source.sourceUrl)||'';var api=base.split('?')[0];if(api.charAt(api.length-1)==='/')api=api.slice(0,-1);api+'?ac=detail&ids='+id;</js>`。**禁止**直接用相对链接作为link（会请求HTML页面而非JSON）

31. **ruleRoutes/ruleEpisodes MacCMS标准解析模式**：详情JSON通过 `vod_play_from` 解析线路（`$$$`分隔），`vod_play_url` 解析集数（`$$$`分隔线路 + `#`分隔集数 + `$`分隔标题和URL）。**铁证**：纯数字link（如 "123"）作为URL请求会失败，必须用JS拼接有效API URL。规则模板：ruleRoutes=`<js>(function(){var d=JSON.parse(result);var f=(d.list&&d.list[0]&&d.list[0].vod_play_from)||'';return f.split('$$$').filter(function(s){return s&&s.trim();}).map(function(n,i){return n||('线路'+(i+1));}).join('\\n');})()</js>`，ruleEpisodes=`<js>(function(){var ri={routeIndex};var d=JSON.parse(result);var u=(d.list&&d.list[0]&&d.list[0].vod_play_url)||'';var r=u.split('$$$');if(ri>=r.length)return JSON.stringify([]);var eps=[];r[ri].split('#').forEach(function(item,i){if(!item)return;var p=item.split('$');eps.push({title:p[0]||('第'+(i+1)+'集'),url:p[1]||p[0]});});return JSON.stringify(eps);})()</js>`

32. **站点失效判断标准与分层处理**：批量源完善时区分3类不可修复源：(1)**站点失效**（HTTP 500/超时/DNS解析失败）→ `enabled=false` 禁用；(2)**站点正常但搜索被禁用**（API返回"搜索功能已关闭"或空结果）→ 保留启用+`sourceComment='[注:站点搜索不可用]'`；(3)**Cloudflare挑战**（页面含 `Just a moment` 或 `cf-challenge` cookie）→ 标记 unverifiable + 启用。**判断流程**：先curl首页确认站点可达→再curl搜索接口确认搜索可用→最后Playwright验证DOM结构

33. **批量源修复启用/禁用/标注三层策略**：批量完善N个源时按3层处理：(1)**可修复层**（规则错误/字段缺失）→ 修复并启用；(2)**不可修复层**（站点失效）→ `enabled=false` 禁用避免用户看到错误；(3)**部分可用层**（站点正常但搜索/某功能不可用）→ 保留启用+`sourceComment` 标注已知问题。**铁证**：直接删除不可用源会丢失可能恢复的站点，禁用+标注是更优策略。每层处理完立即用 batch_test_all.py 验证通过率提升

34. **多参数搜索URL适配（u= / t= 等分类参数）**：部分站点搜索URL带分类参数（如 `?m=search&u=分类X&k={{key}}`），写死分类会限制搜索范围。**适配策略**：(1)优先验证无分类参数时是否全局搜索可用（如 `?m=search&k={{key}}`），可用则去掉分类参数实现全量搜索；(2)若必须带分类参数且分类固定，将搜索范围写入 sourceComment 说明；(3)若用户希望多分类搜索，可在 sortUrl 中按分类列出，每个分类作为独立搜索入口

35. **正式包日志不可见陷阱（双重拦截）**：release 正式包中日志被双重机制拦截，logcat 几乎为空。**拦截层1**：`AppLog.kt` 所有日志方法（put/e/d/i/w）被 `if (BuildConfig.DEBUG)` 包裹，release 包 DEBUG=false → 业务日志不输出。**拦截层2**：`app/proguard-rules.pro` 配置 `-assumenosideeffects class android.util.Log` → ProGuard 移除所有 `Log.x()` 调用。**铁证**：2026-07-28 站点A任务，release 包运行时 `adb logcat -d` 只返回1行无关日志（`NetworkManagementSocketTagger`），AppLog.put 输出的规则解析/网络请求/播放器日志全部不可见。**调试策略**：(1)优先用 debug 包调试规则问题（AppLog 可见）；(2)若必须用正式包验证，只能看系统级日志（ActivityManager/ExoPlayer/AndroidRuntime 等 tag）；(3)ExoPlayer 播放问题看 `ExoPlayerImpl` / `MediaSource` / `OMX` 等系统 tag；(4)用后台持续 logcat（`adb logcat -v time > file`）捕获用户点击测试期间的系统日志；(5)logcat -d 缓冲区可能为空（App 运行时无系统级日志输出），需用持续监听模式

36. **RSS列表图片不显示（布局+加载失败双因素）**：RSS文章列表图片不显示有两个原因：(1)布局因素——默认列表样式（articleStyle=0）的 imageView 默认 GONE，只有 Glide 加载成功才 VISIBLE，加载失败则完全不可见；网格布局（articleStyle=2）有 placeholder 始终可见。(2)图片加载失败——CDN防盗链/Cloudflare拦截返回403。**解决方案**：(1)视频/图片类RSS源设置 `articleStyle=2`（网格布局），即使图片加载失败也有占位框；(2)配置 `header` 字段添加 User-Agent 和 Referer；(3)启用 `enabledCookieJar=true` 让cookie自动传递；(4)图片CDN有独立Cloudflare防护时，OkHttp请求可能被拦截，需用WebView模式或代理

37. **RSS源文章列表不加载（Cloudflare拦截OkHttp）**：站点有Cloudflare保护时，Legado的OkHttp直接请求会被拦截（返回503/403验证页），导致文章列表解析为空。**诊断方法**：(1)清空rssArticles表后重新进入源，如果文章数仍为0则确认是网络拦截；(2)旧文章数据是缓存，修改ruleImage后看不到效果是因为文章未重新加载。**解决方案**：(1)配置header伪装浏览器；(2)启用cookieJar传递验证cookie；(3)Cloudflare JS Challenge无法通过OkHttp绕过时，考虑用WebView模式（enableJs=true + loadWithBaseUrl=true）或等待IP被放行

38. **RSS文章image字段为null的调试方法**：调试ruleImage规则时，image字段为null有三种可能：(1)JS规则返回空字符串（提取失败）；(2)文章未重新加载（用了旧缓存，旧数据image本身为null）；(3)网络请求被拦截（文章列表为空）。**调试步骤**：(1)先用 `@js:result.tagName()` 验证JS执行环境和result对象类型；(2)用 `@js:var e=result.selectFirst('.css');e?'found':'not-found'` 验证选择器；(3)停止App后pull数据库（含WAL），用SQLite查看image字段实际值；(4)NetworkUtils.getAbsoluteURL会把非URL字符串转为绝对路径（如"div"→"https://domain/div"），可用于间接观察JS返回值

39. **数据库直接修改后App不生效（WAL+缓存）**：直接修改legado.db后push回模拟器，App可能不生效：(1)App运行时数据库被WAL锁定，push前必须force-stop；(2)需删除 `-wal` 和 `-shm` 文件避免WAL冲突；(3)文件权限必须设置 `chmod 660` + `chown u0_a20:u0_a20`（UID从dumpsys package获取）；(4)RSS文章有缓存机制，修改ruleImage后需切换分类或下拉刷新触发重新加载

### 视频订阅源专项陷阱（2026-07-28 站点A任务反哺）

40. **`##` 字符串替换操作符（视频源URL转换利器）**：Legado 规则引擎支持 `##` 操作符对提取的字符串进行替换，语法 `规则##旧字符串##新字符串`。**铁证**：站点A列表链接是 `/info/{id}.html`（详情页无视频），真正播放页是 `/play/{id}.html`，用 `ruleLink = "a@href##info##play"` 将 `/info/` 替换为 `/play/`，比 JS 方案（`@js:var m=result.match(...)）` 简单且正确。**适用场景**：(1)列表链接是详情页，需要转换为播放页URL模式；(2)URL 路径段替换（如 `/detail/` → `/play/`）；(3)去掉 URL 后缀（如 `##.html##` 去掉 .html）。**优势**：比 JS 方案更稳定（不依赖 Rhino 引擎），更简单（无需正则匹配），更正确（直接字符串替换）

41. **嗅探模式（ruleContent 为空）**：视频订阅源中 `ruleContent` 设为空字符串 `""` 时，Legado 内置播放器会自动嗅探播放页的视频地址（m3u8/mp4）。**铁证**：站点A用 `ruleContent = ""` + `ruleLink = "a@href##info##play"` 将列表链接转为播放页URL，内置播放器直接嗅探到 m3u8 成功播放。**适用场景**：(1)播放页是标准 HTML 含 `<video>` 或 m3u8 流；(2)视频地址通过 JS 动态加载（`playUrl = 'xxx.m3u8'`）。**不适用**：(1)视频地址需要复杂 JS 解密；(2)播放页需要登录或 cookie。**优先级**：视频源优先尝试嗅探模式，失败后再用 JS 提取

42. **播放页链路验证（列表链接≠播放页）**：视频网站常见三层结构"列表页→详情页→播放页"，列表链接往往指向详情页（无视频），需要点击触发才到播放页。**铁证**：站点A列表链接 `/info/{id}.html` 是详情页（含视频信息但无视频流），真正播放页 `/play/{id}.html` 需点击播放按钮才到达。**Phase 1 必经验证**：(1)用 Playwright 点击列表项，落地页是否直接含 `<video>` 或 m3u8 流；(2)若落地页是详情页，分析"详情页→播放页"跳转规律（URL模式差异/按钮选择器/href 属性）；(3)优先用 `##` 操作符转换 URL（如 `/info/` → `/play/`），次选 JS 提取播放页 URL。**禁止**：假设列表链接直接是播放页，必须验证

43. **导入源后必须验证写入（DELETE+INSERT 不可靠）**：`import_rss_source.py` 用 DELETE + INSERT 方式更新源，但 WAL 模式下可能被旧 WAL 覆盖导致更新失败。**铁证**：2026-07-28 站点A任务，脚本执行后数据库中仍是旧版源（ruleLink 是 `@js:...` 而非 `a@href##info##play`），用户测试失败。**强制验证流程**：(1)导入后用 `SELECT ruleLink, ruleContent FROM rssSources WHERE sourceUrl = ?` 确认字段值是最新版；(2)若仍是旧版，直接用 Python sqlite3 操作：DELETE + INSERT OR REPLACE + COMMIT + PRAGMA wal_checkpoint(TRUNCATE)；(3)push 回设备前必须 force-stop App + 删除设备端 WAL/SHM；(4)push 后必须 `chown <uid>:<uid>` + `chmod 660`（uid 从 `adb shell dumpsys package <pkg> | grep userId=` 获取）。**反模式**：信任脚本返回的"导入成功"而不验证实际字段值

## 工具脚本

### v4 核心模块（legado_client）

| 模块 | 用途 |
|------|------|
| `legado_client.validator.MandatoryFieldValidator` | 必填字段强制校验（CRITICAL/MANDATORY/RECOMMENDED 三级） |
| `legado_client.runtime.RuntimeValidator` | 真机测试集成验证器（编译+安装+导入+L2+logcat） |
| `legado_client.runtime.auto_fixer_loop` | 自动修复循环（生成→测试→诊断→修复→重测） |
| `legado_client.utils.sanitize_source_json` | None 序列化 bug 修复 |
| `legado_client.analyzer.auto_fix_error` | 错误自动修复（12 种自动 + 5 种需用户介入） |

### 调试脚本（scripts/）

| 脚本 | 用途 |
|------|------|
| `scripts/debug-source.py --source PATH --key KEY --stage all` | 端到端调试（首选） |
| `scripts/quick-verify.py` | 静态可用性检查 |

### 真机测试脚本（ai_tests/scripts/）

| 脚本 | 用途 |
|------|------|
| `ai_tests/scripts/quick_build_install.py` | 编译+安装+L1 验证 |
| `ai_tests/scripts/import_rss_source.py <json>` | 导入订阅源到 legado.db（含 WAL 处理） |
| `ai_tests/scripts/l2_verify_video_player.py --scenario error_patterns` | L2 视频播放器验证 |
| `ai_tests/scripts/skill_e2e_test.py` | Skill v4 E2E 测试（14 用例） |
| `ai_tests/scripts/export_rss_sources.py` | 从模拟器反向导出订阅源到 JSON（批量优化起点） |
| `ai_tests/scripts/batch_optimize_sources.py` | Playwright 批量分析站点补全4字段 |
| `ai_tests/scripts/fix_rule_next_page.py` | 修复批量脚本导致的字段错误值（'page'/'None'等） |
| `ai_tests/scripts/verify_rss_scenarios.py` | 4场景真机验证（列表/搜索/分类/下一页） |
| `ai_tests/scripts/analyze_rule_prefix.py` | 字段前缀分布分析（用于诊断） |

## JVM 仿真器能力边界

> **v3 修正声明**（2026-07-17）：JVM 仿真覆盖规则引擎层 85-90%，**不覆盖** WebView/Activity/Cookie/真机网络栈。

| 能力 | 覆盖率 | 说明 |
|------|--------|------|
| Rhino JS 执行 | ✅ 85-90% | 规则引擎层 |
| jsoup CSS 选择器 | ✅ 100% | 完整支持 |
| hutool 加密 | ✅ 100% | AES/DES/SM4 |
| AnalyzeRule | ✅ 100% | 规则解析器 |
| WebView | ❌ 0% | 必须真机 |
| Activity 生命周期 | ❌ 0% | 必须真机 |
| Cookie 自动同步 | ❌ 0% | 必须真机 |
| 真机网络栈 | ❌ 0% | 必须真机 |

**降级路径**：JVM 可用 → RuleEngineServer → JDK 不可用 → Python 仿真 → 标记"未验证"

## basic-memory 操作（project=legado）

| 操作 | MCP 工具 |
|------|---------|
| 搜索经验 | `search_notes(query="{关键词}", search_type="hybrid", project="legado")` |
| 读取笔记 | `read_note(identifier="{标题}", project="legado")` |
| 写入笔记 | `write_note(title, content, directory, project="legado")` |
| 编辑笔记 | `edit_note(identifier, operation, content, project="legado")` |

**L3 目录结构**：traps/ | patterns/ | experiences/ | verifications/ | cases/

## v4 重构变更（2026-07-18）

### 新增（v4）

- `legado_client/validator/`：必填字段校验器包
  - `mandatory_fields.py`：三级字段清单（CRITICAL/MANDATORY/RECOMMENDED）
  - `MandatoryFieldValidator` 类 + `validate_source()` 便捷函数
- `legado_client/runtime/`：真机测试集成包
  - `runtime_validator.py`：复用 ai_tests 10 lib 模块 + 7 固定脚本
  - `auto_fixer_loop.py`：生成→测试→诊断→修复→重测闭环
- `auto_fix_error()` 入口集成 `MandatoryFieldValidator`：
  - CRITICAL 缺失 → 直接返回失败，不进入修复流程
  - MANDATORY/RECOMMENDED 缺失 → 加入 `missing_fields` 清单

### v3 保留

- `sanitize_source_json()` 函数：None 序列化 bug 修复
- `ai_tests/scripts/skill_e2e_test.py`：端到端测试（v4 升级到 14 用例）
- 6 大核心脚本（debug/quick-verify/verify-selector/verify-decrypt/verify-image/analyze-site）
- `legado_client/` 包内核心模块（analyzer/client/delegate/experience/utils）
- `references/` 知识库（85 文档，T6 待合并到 ≤25）


## 完整参考

- [references/](./references/) - 规则语法、JS 模式、特殊场景、故障排除完整知识库
- [docs/specs/legado-skill-v4-rebuild/](../../docs/specs/legado-skill-v4-rebuild/) - v4 重构设计文档
- [docs/temp-analysis/legado_mandatory_fields.md](../../docs/temp-analysis/legado_mandatory_fields.md) - 必填字段源码分析
- [docs/temp-analysis/ai_test_reuse_for_skill.md](../../docs/temp-analysis/ai_test_reuse_for_skill.md) - ai_test 复用分析
- [ai_tests/docs/fixed_test_workflow.md](../../ai_tests/docs/fixed_test_workflow.md) - 真机测试 SOP
- [references/source-analysis/playwright-site-analysis.md](./references/source-analysis/playwright-site-analysis.md) - Playwright 网站真实分析指南
- [references/source-analysis/batch-optimization-patterns.md](./references/source-analysis/batch-optimization-patterns.md) - 批量优化模式与陷阱

## 批量优化工作流（v4 反哺 2026-07-18）

> 65 个订阅源批量优化的实战经验反哺。

### 5 步闭环

```
1. export_rss_sources.py      从模拟器导出 N 个源
2. batch_optimize_sources.py  Playwright 逐个分析补全4字段
3. fix_rule_next_page.py      修复批量脚本导致的字段错误值
4. import_rss_source.py       导入回模拟器（含 WAL 处理）
5. verify_rss_scenarios.py    4 场景真机验证
```

### 24 大陷阱（详见 batch-optimization-patterns.md）

> v5反哺新增陷阱16-24（2026-07-18 222源批量优化实战）

**陷阱1-15（v4反哺，65源优化）**：
1. **批量脚本字段填充错误值**（最高风险）：50/65 个 ruleNextPage 被错填为 "page"。**必修**：写入前合法性校验
2. **成功率陷阱**：脚本判定"成功"未校验提取值合法性。**必修**：后置校验+自动清空
3. **Playwright 站点可达性差异**：41/65 失败（模板 URL/IP失效/CF防护）。**应对**：失败不中断+保持原值
4. **校验器字段级别动态调整**：ruleContent/ruleDescription 对视频源是 OPTIONAL。**已落实**：mandatory_fields.py
5. **4 场景真机验证误判**：`.stui-page@li@href` 被判无效。**修复**：识别无前缀 CSS 选择器
6. **Python None 序列化污染**：str(None)="None" 污染字段。**必修**：sanitize_source_json 过滤
7-15. 详见 batch-optimization-patterns.md（诊断脚本脱敏/批量脚本修复/域名迁移/导入残留/subprocess传参/Playwright异常脱敏/失败源7种重试/反爬loginUrl/模拟器DNS/JSON boolean类型）

**陷阱16-24（v5反哺，222源优化）**：
16. **占位符源多字段交叉恢复**：sourceUrl长度<20的占位符源，通过 sourceIcon/injectJs/header 等多字段交叉提取 host，恢复率85.7%
17. **Wayback Machine 是最有效的失败恢复手段**：56个失败源深度重试，Wayback 直接访问恢复24个（66.7%），远超其他策略。**必修**：Wayback 优先策略
18. **Cloudflare 防护普遍存在**：26/33 源命中 CF 防护（79%命中率）。**应对**：反爬 jsRule 配置（页面就绪检测+弹框关闭）+ loginUrl + CookieJar
19. **searchUrl 和 jsRule 是最大字段缺口**：searchUrl 仅30.6%覆盖率，jsRule 0%覆盖率。**必修**：双策略自动补全（GET/POST表单探测+弹框关闭JS）
20. **图片源 ruleContent 4 模板选择**：已有参考源原样保留（模板C，47.4%），新设计用模板A（详情页主图，52.6%）。ruleContent 必须适配 PhotoDialog 调用链
21. **视频源 ruleContent 优先嗅探器策略**：V1优先（script正则提取m3u8/mp4，66.7%）→ V3次选（iframe src）→ V2备用（sniffer留空）
22. **子代理模式比批量脚本模式效果更好**：8个子代理并行处理222源，字段补全率70-90%（vs 批量脚本30-50%）。**必修**：子代理模式批量优化工作流
23. **真机测试脚本校验过严误报**：verify_rss_scenarios.py scenario_4 仅校验3种前缀导致0%通过率。**已修复**：支持7种 legado 原生语法（class./text./page./标签./CSS选择器/属性提取/IIFE/正则兜底），通过率从0%→62.5%
24. **Cronet 库缺失导致 HTTPS 源加载失败**：libcronet.so FileNotFoundException。**必修**：真机测试前启动App等待60秒自动下载 Cronet 库

**陷阱25-28（v6反哺，订阅源年龄验证自动破除实战）**：
25. **Accept-Encoding 头导致 OkHttp 响应乱码**：手动设置 `Accept-Encoding: gzip, deflate, br` 后 OkHttp 无法解码 brotli。**必修**：永远不在 header 中设置 Accept-Encoding/Connection/Upgrade-Insecure-Requests
26. **CookieStore 过期值覆盖 header Cookie**：mergeCookies() 中 CookieStore > header，导致"时好时不好"。**必修**：loginCheckJs 中先 `cookie.removeCookie(baseUrl)` 再 `cookie.setCookie()`
27. **shouldOverrideUrlLoading 仅绑定 java 和 url**：没有 cookie/baseUrl/source/result，`{{}}` 模板也不处理。**必修**：仅使用 java 和 url 变量
28. **服务端 Cookie 年龄验证三层自动破除**：Layer1 header预置Cookie + Layer2 loginCheckJs检测+清除+重设 + Layer3 injectJs WebView自动点击。**必修**：三层防护配置

### 实战数据（65 源）

| 指标 | 数据 |
|------|------|
| Playwright 分析成功 | 24/65（37%） |
| ruleNextPage 修复后合法值 | 14/65（22%，51 个无效值已清空） |
| strict 校验通过 | 30/65（46%） |
| 列表加载通过（抽样） | 6/8（75%） |

## 多线路多集按需采集标准写法（v4.1+ 新增）

> **背景**：Legado 阅读M v3.26.072420+ 新增 `ruleRoutes` 和 `ruleEpisodes` 两个字段，用于 RSS 视频源（type=2）的多线路多集按需采集。
> **设计文档**：`docs/specs/multiline-on-demand-extraction/`
> **核心原则**：分离线路采集和集数采集，用户切换线路/集数时才采集视频地址（按需采集），替代 ruleContent JS 全量采集模式。

### 字段说明

| 字段 | 作用 | 支持规则 | 适用场景 |
|------|------|---------|---------|
| `ruleRoutes` | 从详情页采集线路列表（线路名） | CSS/JSONPath/XPath/JS | type=2 视频源，有多线路切换需求 |
| `ruleEpisodes` | 从详情页采集集数列表（集数标题+播放页URL） | CSS/JSONPath/XPath/JS | type=2 视频源，支持 `{routeIndex}`/`{routeIndex+1}` 占位符 |

### MacCMS HTML 模板标准写法（CSS 选择器）

MacCMS HTML 模板站点通常用 `.module-player-list` 结构组织线路和集数：

```json
{
  "ruleRoutes": ".module-player-list .module-player-tab-name@text",
  "ruleEpisodes": ".module-player-list .module-player-list-content:eq({routeIndex}) a@text&&href"
}
```

**说明**：
- `ruleRoutes`：用 CSS 选择器采集所有线路名（`.module-player-tab-name` 的文本）
- `ruleEpisodes`：用 `{routeIndex}` 占位符匹配当前线路索引，采集集数标题（`@text`）和播放页 URL（`href`）

### MacCMS JSON API 模板标准写法（vod_play_from / vod_play_url）

MacCMS JSON API 站点通常返回 `vod_play_from` 和 `vod_play_url` 字段：

```json
{
  "ruleRoutes": "@js:<JSON.parse(result).vod_play_from.split('$$$').map(function(name, i){return name||'线路'+(i+1)}).join('\\n')",
  "ruleEpisodes": "@js:var d=JSON.parse(result).vod_play_url.split('$$$')[{routeIndex}];d.split('#').map(function(item){var p=item.split('$');return p[0]+'$'+p[1]}).join('\\n')"
}
```

**vod_play_from 结构**：`线路1$$$线路2$$$线路3`（用 `$$$` 分隔线路）
**vod_play_url 结构**：`第1集$url1#第2集$url2$$$第1集$url1#第2集$url2`（用 `$$$` 分隔线路，`#` 分隔集数，`$` 分隔标题和URL）

**JS 规则解析**：
- `ruleRoutes` JS：解析 `vod_play_from`，用 `$$$` 分割得到线路名数组，空名用"线路N"替代
- `ruleEpisodes` JS：用 `{routeIndex}` 占位符选择当前线路的集数段，用 `#` 分割得到集数数组，每集用 `$` 分割标题和URL

### 占位符说明

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{routeIndex}` | 当前线路索引（0-based） | 用户选择"线路1"时，routeIndex=0 |
| `{routeIndex+1}` | 当前线路索引（1-based） | 用户选择"线路1"时，routeIndex+1=1 |

### 使用规范

1. **仅 type=2 视频源使用**：`ruleRoutes`/`ruleEpisodes` 仅对 type=2（视频源）生效，其他类型源忽略
2. **ruleContent 回归单集视频 URL**：使用新字段后，`ruleContent` 不再支持返回多线路多集嵌套 JSON，仅支持单集视频 URL
3. **按需采集**：用户切换线路时，App 调用 `Rss.getEpisodesAwait(rssArticle, ruleEpisodes, routeIndex, source)` 重新采集新线路集数
4. **视频地址由统一入口采集**：`VideoUrlExtractor.extractVideoUrlForEpisode` 按 MacCMS 播放页解析 → DOM 解析 → WebView 抓包三层降级采集视频流地址
5. **老源兼容**：未配置 `ruleRoutes`/`ruleEpisodes` 的源仍使用 `ruleContent` JS 模式（兼容老版本）

### 反模式（禁止）

- ❌ 在 `ruleContent` JS 中一次性采集所有线路所有集的播放页 URL
- ❌ 在 `ruleContent` JS 中逐集请求播放页 HTML 提取 m3u8
- ❌ 在 `ruleEpisodes` 中直接采集视频流地址（m3u8/mp4），应只采集播放页 URL
- ❌ 硬编码镜像站 URL 列表（应由 `ruleRoutes` 动态采集）

## 任务完成标准

任务完成前必须逐项核对：

- [ ] 已用 Playwright MCP 真实访问目标站点首页（非 WebFetch/猜测）
- [ ] 4个 RECOMMENDED 字段值来自真实 DOM 提取（sourceIcon/searchUrl/sortUrl/ruleNextPage）
- [ ] 源 JSON 经 `sanitize_source_json` 过滤
- [ ] `MandatoryFieldValidator` 校验通过（strict_recommended=True）
- [ ] `skill_e2e_test.py` 14/14 通过
- [ ] 真机导入后源可正常加载（通过 `RuntimeValidator`）
- [ ] 无 ImportError / NameError 残留
- [ ] 批量优化任务：字段值经 `is_valid_*` 校验（非 INVALID_VALUES）
- [ ] 用 AskUserQuestion 向用户确认
