# 动态域名陷阱

> 动态域名站点（入口域名固定但实际内容域名动态变化）的陷阱和解决方案。

## 陷阱44: Rhino ES5兼容性（padStart/模板字符串/箭头函数禁用）

Rhino 引擎不支持 ES6+ 语法，动态域名 JS 必须用 ES5 编写。

**禁用语法**：
- `padStart` → 用 `if(mm<10) mm='0'+mm` 手动补零
- 模板字符串 → 用字符串拼接 `+`
- 箭头函数 → 用 `function(){}`
- `let`/`const` → 用 `var`
- `includes` → 用 `indexOf > -1`

**完整替代写法**：见 [rhino-compat-cheatsheet.md](../js-extensions/rhino-compat-cheatsheet.md)

**经验来源**：`[经验来源:Rhino ES5兼容范式]`

## 陷阱45: searchUrl支持`<js>`标签JS执行（已纠正原错误结论）

**原结论错误**：曾认为 searchUrl 不支持 JS 执行。

**源码铁证**：`RssSearchModel.kt:163-169` 中 `search()` 方法把 `source.searchUrl` 当作 `sortUrl` 参数传给 `Rss.getArticlesAwait()`，内部通过 `AnalyzeUrl` 类处理，`initUrl()` → `analyzeJs()` 会执行 `<js>` 标签包裹的 JS 脚本（与 sortUrl 走完全相同的处理路径）。

**结论**：searchUrl 完全支持 `<js>` 标签 JS 执行，可以动态构造搜索 URL。

**适用场景**：
1. 动态域名站点的 searchUrl
2. 需要复杂搜索 URL 构造的场景

**注意**：searchUrl 的 JS 中可用变量 `key`（搜索关键词）、`cache`（CacheManager）、`java`（JsExtensions）

## 陷阱46: 多分类搜索实现（sortUrl中添加搜索分类项）

RSS源搜索只有一个 searchUrl，不支持多URL。但部分网站每分类独立搜索URL，无法用单一 searchUrl 覆盖。

**方案**：在 sortUrl 的分类列表末尾添加"搜索xxx"分类项，URL为 `baseUrl + '/search/{cat}/{{key}}.html'`。

**用户体验**：用户在分类列表中滑到末尾，选择"搜索x"等分类，输入关键词即可在该分类内搜索。

**关键**：sortUrl 的JS动态生成域名，所以搜索分类每天可用（不受 sourceUrl 硬编码影响）。

**注意**：ruleArticles 必须用CSS选择器（如 `div.cell_box`），不能用JS——因为 ruleArticles 的JS会在列表页和搜索页都执行，列表页没有搜索关键词，JS中的 ajaxAll 请求会失败（见陷阱47）

## 陷阱47: ruleArticles的JS会影响列表页（搜索与列表共用规则）

ruleArticles 用JS时，列表页和搜索页都会执行该JS。列表页没有搜索关键词 `{{key}}`，JS中的 ajaxAll 请求会因URL含空关键词而失败，导致列表页空白。

**解决方案**：ruleArticles 不用JS，改回CSS选择器（如 `div.cell_box`）。多分类搜索需求通过 sortUrl 的搜索分类实现（陷阱46），不需要在 ruleArticles 中处理

## 陷阱48: 导入脚本DELETE条件（用sourceName而非sourceUrl）

`import_rss_source.py` 默认按 `sourceUrl` 删除旧记录，但当源URL变更时（如从硬编码域名改为动态JS生成），旧记录的 sourceUrl 与新记录不同，DELETE 不命中，导致同名源在数据库中有多条记录。

**修复**：将 DELETE 条件从 `WHERE sourceUrl=?` 改为 `WHERE sourceName=?`，确保同名源只保留最新一条。

**适用场景**：
1. 源URL变更（硬编码→动态JS）
2. 域名切换（旧域名失效换新域名）
3. sortUrl 规则变更导致 sourceUrl 实际值变化

## 陷阱50: 入口域名+meta refresh跳转模式（区别于HTTP重定向）

部分站点入口域名访问返回 HTTP 200 + HTML 含 `<meta http-equiv="refresh" content="3;URL=https://实际域名/...">`，OkHttp 不跟随 HTML 层重定向（区别于 301/302 HTTP 重定向）。

**关键判断**：用 `curl -s -i` 看响应头，若 status=200 且无 Location header 但有 meta refresh，确认是 HTML 跳转模式。

**应对**：sortUrl 用 JS 调 `java.ajax(入口域名)` 获取响应 HTML，解析 meta refresh 提取实际域名。

## 陷阱51: punycode域名含日期+服务端随机数字

动态 punycode 域名格式 `xn--cdn{MMDD}-{1或2}jzy01cc-{punycode编码}.{主域名}`，其中日期部分对应当天日期，数字部分（1/2）服务端随机分配（可能用于负载均衡/多实例）。

**应对**：JS 中不必预测数字，直接通过入口域名 meta refresh 获取当次返回的实际域名即可（任一可用）。

## 陷阱52: sortUrl JS动态域名方案完整模板（meta refresh跳转类站点通用）

当站点入口域名固定但实际内容域名动态变化时，用 sortUrl JS 在运行时获取实际域名。

**完整模板**：
```javascript
<js>(function(){
  var cacheKey = 'siteX_real_domain_v1';
  var realDomain = cache.get(cacheKey);
  if (!realDomain) {
    var html = java.ajax('https://入口域名') || '';
    var idx = html.indexOf('URL=');
    if (idx < 0) idx = html.indexOf('url=');
    if (idx < 0) return '';
    var after = html.substring(idx + 4);
    var end = after.search(/["']/);
    var jumpUrl = end > 0 ? after.substring(0, end) : after;
    var p = jumpUrl.indexOf('://');
    if (p < 0) return '';
    var afterP = jumpUrl.substring(p + 3);
    var s = afterP.indexOf('/');
    realDomain = s > 0 ? afterP.substring(0, s) : afterP;
    cache.put(cacheKey, realDomain, 21600);  // 6小时过期
  }
  var base = 'https://' + realDomain;
  var cats = ['分类1', '分类2'];
  var paths = ['path1', 'path2'];
  var result = [];
  for (var i = 0; i < cats.length; i++) {
    result.push(cats[i] + '::' + base + '/list/' + paths[i] + '/index.html');
  }
  return result.join('\n');
})()</js>
```

**关键设计点**：
1. `sourceUrl` 用入口域名固定值（作为 cache key 和源标识）
2. `searchUrl` 支持 `<js>` 标签（见陷阱53）
3. `ruleLink` 等规则在 sortUrl 返回的实际域名 URL 上下文执行，相对路径基于实际域名拼接
4. **CacheManager 缓存 6 小时**避开日内 punycode 数字随机变化
5. **跨日域名变化时需用户手动清外层 cache**（RssSortActivity 右上角菜单"刷新分类"）

**已知限制**：`RssSourceExtensions.kt:36` 的 `aCache.put(sortUrlsKey, str)` 无 saveTime 参数永久缓存 sortUrl JS 返回值，JS 只执行一次。这是不改源码下的最佳折中方案。

**Rhino 兼容性**：避免正则的 JSON 转义麻烦，用 `indexOf` + `substring` 做字符串解析；不用 `padStart`/模板字符串/箭头函数（见陷阱44）。

**经验来源**：`[经验来源:动态域名解析范式]`

## 陷阱53: searchUrl和sortUrl共用cache key模式（动态域名站点搜索通用方案）

动态域名站点（meta refresh 跳转类）的 searchUrl 可以复用 sortUrl 的 cache key，避免重复 AJAX 请求获取实际域名。

**完整 searchUrl JS 模板**：
```javascript
<js>(function(){
  var cacheKey = 'siteX_real_domain_v1';  // 与 sortUrl 共用 cacheKey
  var realDomain = cache.get(cacheKey);
  if (!realDomain) {
    // 复用 sortUrl 的域名解析逻辑
    var html = java.ajax('https://入口域名') || '';
    var idx = html.indexOf('URL=');
    if (idx < 0) idx = html.indexOf('url=');
    if (idx < 0) return '';
    var after = html.substring(idx + 4);
    var end = after.search(/["']/);
    var jumpUrl = end > 0 ? after.substring(0, end) : after;
    var p = jumpUrl.indexOf('://');
    if (p < 0) return '';
    var afterP = jumpUrl.substring(p + 3);
    var s = afterP.indexOf('/');
    realDomain = s > 0 ? afterP.substring(0, s) : afterP;
    cache.put(cacheKey, realDomain, 21600);  // 6小时过期
  }
  var searchKey = encodeURIComponent(key || '');  // key 是搜索关键词变量
  if (!searchKey) return '';
  return 'https://' + realDomain + '/search/' + searchKey + '.html';
})()</js>
```

**关键设计点**：
1. searchUrl 的 JS 中可用变量 `key`（搜索关键词，由 RssSearchModel 传入）
2. `encodeURIComponent(key)` 编码搜索关键词
3. 与 sortUrl 共用 cacheKey，sortUrl 先执行缓存域名，searchUrl 直接读取
4. 跨日域名变化时清 sortUrl 缓存也会刷新搜索域名

**经验来源**：`[经验来源:动态域名搜索范式]`

## 陷阱54: Phase 3真机验证三步流程（导入后字段验证+禁用其他源+ExoPlayer系统日志）

Phase 3 真机验证需要系统化执行三步，避免遗漏。

**步骤1：导入后字段验证**（陷阱43）：用 Python sqlite3 查询 rssSources 表，确认 searchUrl/sortUrl 以 `<js>` 开头、含 cacheKey、ruleArticles/ruleLink 等字段值正确。

**步骤2：禁用其他源确保搜索准确**：用 Python UPDATE rssSources SET enabled=0 WHERE sourceUrl NOT LIKE '%目标站点%'，避免其他源干扰搜索结果。

**步骤3：ExoPlayer 系统日志验证播放**：正式包 AppLog 被双重拦截，但 ExoPlayer 系统日志可见，用 `adb logcat -d | findstr ExoPlayer` 查看 state=READY + first frame rendered 确认播放成功。

**经验来源**：`[经验来源:真机验证三步流程]`

## 陷阱57: JS动态域名解析算法（seededRandom方案，每日变化域名）

部分站点入口域名通过 JS redirect 跳转到动态实际域名，实际域名每日变化（基于日期种子生成随机词 + 域名后缀），不能写死域名。

**算法**：
1. `java.ajax` 获取入口域名 HTML
2. 正则匹配 `getRandomWord()` 函数附近的域名后缀（如 `'.xxx.xyz'` 模式）
3. 复刻站点的 `seededRandom` 函数：`var x = Math.sin(seed++) * 10000; return x - Math.floor(x);`
4. 用当前日期生成种子：`var seed = d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();`
5. 复刻 `generateWord` 函数用 `seededRandom` 从字母表生成随机词
6. 生成 2 个候选域名，用 `java.ajax` 测试每个域名可访问性（HTML 长度 > 1000 视为有效）
7. `sortUrl` 和 `searchUrl` 共用此域名解析逻辑（参考陷阱53的 cache key 共用模式）

**通用规则**：动态域名站点必须在 `sortUrl` 和 `searchUrl` 中用 JS 动态解析实际域名，不能写死域名；用日期种子 + `seededRandom` 复刻站点域名生成算法；测试候选域名可用性确保解析正确。

**Rhino 兼容性**：
1. 不用 `padStart`（用 `if(mm<10) mm='0'+mm` 手动补零，见陷阱44）
2. 不用模板字符串（用字符串拼接）
3. 不用箭头函数（用 `function(){}`）
4. `Math.sin` / `Math.floor` 在 Rhino 中可用

**注意事项**：
1. 候选域名测试时 `java.ajax` 超时建议设短（如 5 秒），避免两个候选都不可达时等待过久
2. 域名生成算法必须严格复刻站点 JS（包括种子计算公式、字母表、词长度），任何一处偏差都会生成错误域名
3. 跨日域名变化时需用户手动清 sortUrl 缓存（参考陷阱52的"刷新分类"操作）

**经验来源**：`[经验来源:seededRandom动态域名范式]`

## 陷阱D: 301重定向后HTML中不含punycode域名（java.ajax自动跟随重定向）

**现象**：sortUrl/searchUrl的JS中`java.ajax(url)`获取主页HTML，正则搜索`xn--`提取punycode域名，但301重定向后HTML中不含该字符串。

**根因**：`java.ajax()`内部OkHttp自动跟随301/302重定向，返回重定向后页面的HTML内容。punycode域名只在Location头中出现，不在HTML内容中。

**影响**：动态域名提取失败，sortUrl/searchUrl返回空字符串，分类列表为空，搜索退化为请求主页URL。

**解决方案**：
1. 在请求URL中添加`&mod=jump`参数绕过安全检测，直接获取正常页面
2. 或用`java.connect(url)`获取StrResponse，从`resp.raw.request.url`获取重定向后的URL
3. 缓存punycode域名（6小时有效），减少动态域名提取次数

**验证方法**：logcat中搜索`xn--`字符串，如果在sourceDebug日志中找到，说明HTML中包含punycode域名；如果只在"重定向后地址"日志中找到，说明HTML中不含，需要改用方案2。

## 陷阱E: 动态域名缓存过期导致功能间歇性失效

**现象**：源在首次导入时测试通过（分类加载+搜索正常），但几小时后功能失效（分类为空、搜索无结果）。

**根因**：动态域名缓存时间设置过短（如300秒=5分钟），或缓存key冲突。当缓存过期后，JS重新获取动态域名时可能遇到301重定向问题（见陷阱D）。

**解决方案**：
1. 缓存时间设置为6小时（21600秒）：`cache.put(ck, d, 21600)`
2. 缓存key用源唯一标识（如`tianlai_v5`），避免多源冲突
3. 测试时需清除App缓存后再测，确保动态域名提取逻辑正确（不是依赖缓存）

**铁证**：7个订阅源首次测试通过（缓存了动态域名6小时），6小时后缓存过期，动态域名提取失败（301重定向HTML中不含punycode），功能失效。

## 陷阱F: HTML属性值带引号导致marker字符串匹配失败

**现象**：sortUrl的JS中用`html.indexOf('href=https://xn--')`搜索punycode域名，永远返回-1。但用浏览器查看HTML源码，明显能看到`href="https://xn--..."`。

**根因**：HTML属性值通常用双引号包裹（`href="URL"`），JS字符串`'href=URL'`（无引号）与HTML实际内容不匹配。`indexOf`严格匹配字符序列，差一个引号都失败。

**解决方案**：marker字符串只搜索属性值本身（含唯一特征），不要带属性名和等号：
```javascript
// ❌ 错误：marker带属性名和等号，与HTML中href="..."不匹配
var marker='href=https://xn--';
var pos=html.indexOf(marker);

// ✅ 正确：只搜索特征字符串（punycode前缀就是唯一特征）
var marker='xn--';  // 或 'https://xn--'（含协议更精确）
var pos=html.indexOf(marker);

// 提取完整URL：从marker位置向前找'href='或'src='，向后找引号或空格
if(pos>=0){
    var urlStart=html.lastIndexOf('href=',pos);
    if(urlStart<0)urlStart=html.lastIndexOf('src=',pos);
    if(urlStart>=0){
        var eqPos=html.indexOf('=',urlStart);
        var ch=html.charAt(eqPos+1);  // 引号字符
        var valStart=eqPos+1;
        if(ch=='"'||ch=='\'')valStart=eqPos+2;
        var valEnd=html.indexOf(ch=='"'?'"':(ch=='\''?'\'':' '),valStart);
        if(valEnd<0)valEnd=html.indexOf(' ',valStart);
        if(valEnd<0)valEnd=html.length;
        var url=html.substring(valStart,valEnd);
    }
}
```

**通用规则**：在HTML中搜索特征字符串时，不要带HTML属性名和等号（`href=`/`src=`），只搜索值本身的特征部分（如`xn--`、`/upload/`、`data-`等）。

**铁证**：7源v2版marker用`href=https://xn--`，7个源分类列表全部为空（HTML中是`href="https://xn--"`带引号）；改为`https://xn--`后7/7源列表加载成功。

**经验来源**：`[经验来源:HTML属性值marker匹配范式]`

## 陷阱G: 地址发布页 document.write 编码 + gotoPath 域名轮换（2026-08-02 欢乐谷实战）

**适用站点特征**：入口是「地址发布页」（HTML 整体被 `<script>document.write(decodeURIComponent("<URL编码HTML>"))</script>` 包裹），内含「点击进入网站」按钮 + 「最新地址1/2/3」列表，每次刷新 gotoPath 域名不同（多域名轮换），永久域名已失效。

**两处 document.write 编码**：
1. **发布页本身**：需解码才能看到 gotoPath 域名
2. **主站所有页面（列表/分类/搜索/播放）也编码**：HTML 整体被 document.write 包裹，所有规则（ruleArticles/ruleContent/ruleNextPage）的 JS 必须**先解码再解析**

**解码算法（Rhino ES5 兼容）**：
```javascript
function decodeDoc(html){
  var st = html.indexOf('document.write(decodeURIComponent("');
  if (st < 0) return html;          // 非编码页原样返回
  st += 'document.write(decodeURIComponent("'.length;
  var en = html.indexOf('");', st);
  if (en < 0) en = html.indexOf('")', st);
  var s = html.substring(st, en);
  try { return decodeURIComponent(s); } catch(e) { return html; }  // 防 URIError（孤立%）
}
```

**gotoPath 域名提取 + 逐域名验证（核心范式）**：gotoPath 域名每次刷新随机，且**个别域名可能被污染/劫持（跳转异站）**，必须逐个验证内容特征：
```javascript
function resolveDomain(){
  var ck = 'siteX_dom_v1';
  var d = cache.get(ck);
  if (d) {   // 缓存命中也要先验证（陷阱E 增强）
    try {
      var h = decodeDoc(String(java.ajax('https://' + d + '/')));
      if (h.indexOf('vod-item') >= 0) return d;   // 特征标记：真实主站
    } catch(e) {}
    d = null;   // 失效则重新解析
  }
  var pub = decodeDoc(String(java.ajax('https://固定发布页入口')));
  var doms = []; var pos = 0;
  for (var k = 0; k < 10; k++) {      // 提取全部 gotoPath('https://xxx') 域名
    var gp = pub.indexOf("gotoPath('https://", pos);
    if (gp < 0) break;
    gp += "gotoPath('https://".length;
    var ge = pub.indexOf("'", gp);
    var cand = pub.substring(gp, ge);
    if (doms.indexOf(cand) < 0) doms.push(cand);   // 去重
    pos = ge + 1;
  }
  for (var i = 0; i < doms.length; i++) {          // 逐个验证可用性
    try {
      var h2 = decodeDoc(String(java.ajax('https://' + doms[i] + '/')));
      if (h2.indexOf('vod-item') >= 0) { d = doms[i]; break; }
    } catch(e) {}
  }
  if (d) cache.put(ck, d, 21600);                  // 6小时
  return d || '兜底域名:8888';
}
```

**关键设计点**：
1. **缓存命中后必须验证**（本范式相对陷阱52/53/57 的关键升级）：缓存里是失效域名时，直接复用会重演"昨天能用今天不能用"（404 兜底 → 分类请求返回发布页 HTML → 解析 0 文章）。`java.ajax` 探测 + 内容特征检查，失效才重新解析
2. **gotoPath 域名逐个验证**：发布页给出的域名不保证全部有效（实测部分被劫持跳转异站），用 `java.ajax` 抓取后检查主站特征内容（如 `vod-item`/`vod-img`），第一个命中的采用
3. **所有页面都要 decodeDoc**：ruleArticles/ruleContent/ruleNextPage 的 JS 对 `result`（HTML）先 `decodeDoc(result)` 再 Jsoup/正则解析
4. **视频地址提取**：播放页解码后正则 `/var url = "([^"]+)"/` 提取 m3u8（见 video-source-traps.md 陷阱41b）
5. **sourceComment 必须记录**：回家域名（永久地址）+ 备用域名段 + 邮箱 + 当前发布页入口 + 「动态域名:发布页gotoPath提取+逐域名验证」

**常见坑**：
- `java.ajax()` 返回的是 Java String，第一步必须 `String(...)` 包装（Rhino 陷阱4.1）
- decodeURIComponent 遇孤立 `%` 抛 URIError，必须 try-catch
- 反斜杠/引号在 JSON 双重转义易错，建议 marker 用 `indexOf+substring` 而非正则
- 兜底域名不能写死已过期域名，需定期更新为当前可用域名

**经验来源**：`[经验来源:发布页gotoPath动态域名范式]`
