# 搜索高级技巧

> 搜索规则（SearchRule）的高级写法，涵盖 Cookie 清理、重定向处理、编码转换、动态地址获取、分页和多列表等场景。
> 所有内容已通过 Legado 源码确认。

---

## 1. Cookie 清理解决搜索 30 秒超时

某些书源在搜索时会因旧 Cookie 导致服务端返回异常响应，触发 Legado 的 30 秒超时（SearchModel.kt L76-114）。解决方法是在搜索前清理该源的 Cookie。

### 方法一：在 loginCheckJs 中清理

```javascript
// loginCheckJs 字段
cookie.removeCookie(source.getKey());
```

`source.getKey()` 返回书源的 `bookSourceUrl`（即 BookSource.kt L34-35 定义的主键），作为 Cookie 存储的域名标识。

### 方法二：在搜索地址栏中清理

```
{{cookie.removeCookie(source.getKey())}}/search.html?searchkey={{key}}
```

模板引擎先执行 `cookie.removeCookie()`，清除旧 Cookie 后再发起搜索请求。`cookie` 变量是 JsExtensions 提供的 CookieManager 实例。

**适用场景**：搜索偶尔超时、搜索结果为空但手动浏览器可正常搜索。

---

## 2. 搜索重定向处理

部分网站搜索时会 302 重定向到结果页，直接 GET 可能拿不到正确内容。

### 用 java.post() 获取重定向地址

```javascript
// 获取 302 重定向的 Location 头
java.post('https://example.com/search', 'keyword=' + key + '&submit=', {}).header("Location")
```

### 模板写法

```
{{java.post('https://example.com/search','keyword='+key+'&submit=',{}).header("Location")}}
```

**原理**：`java.post()` 返回 Jsoup 的 `Connection.Response` 对象（不是 `StrResponse`），其 `.header("Location")` 方法可读取响应头中的重定向目标。Jsoup 的 `post()` 方法默认 `followRedirects=false`，因此可以直接拦截重定向获取 Location 头。

> **源码确认**：JsExtensions.kt L535，`fun post(urlStr: String, body: String, headers: Map<String, String>): Connection.Response`，返回类型是 Jsoup 的 `Connection.Response`，不是 `StrResponse`。

**适用场景**：搜索 URL 返回 302、搜索结果页 URL 与搜索 URL 不同。

---

## 3. 繁体字搜索编码处理

部分繁体网站（如台湾小说站）搜索关键词需转为繁体，且页面编码为 Big5。

### 简体转繁体

```javascript
key = java.s2t(key);
```

> **源码确认**：JsExtensions.kt L685，`s2t()` 方法调用 ChineseUtils.s2t() 实现简体转繁体。

### 指定 Big5 编码

```json
{
  "searchUrl": "/search.php?searchkey={{key}},{\"charset\":\"big5\"}"
}
```

> **注意**：`charset` 参数必须在 JSON 对象中，不能作为 URL 查询参数。详见 [encoding-guide.md](./encoding-guide.md)。

**完整示例**：

```
/search.php?searchkey={{java.s2t(key)}},{"charset":"big5"}
```

---

## 4. 搜索地址变动动态获取

部分网站的搜索表单 action 地址是动态生成的，不能硬编码。

### 用正则从首页提取

```
{{java.ajax(source.getKey()).match(/action="(.*?)"/)[1]}}?searchkey={{key}}
```

**流程**：
1. `java.ajax(source.getKey())` 获取书源首页 HTML
2. `.match(/action="(.*?)"/)[1]` 提取 form 标签的 action 属性值
3. 拼接搜索关键词参数

### 用 Jsoup 解析 form 标签

```javascript
var html = java.ajax(source.getKey());
var doc = org.jsoup.Jsoup.parse(html);
var action = doc.select("form").first().attr("action");
result = action + "?searchkey=" + key;
```

**适用场景**：搜索地址含动态 token、搜索表单 action 频繁变化。

---

## 5. 分页 URL 不同写法

搜索结果分页时，不同网站的 URL 规则各异。

### 三元表达式

```
https://example.com/search/{{page==1?"":page+".html"}}?key={{key}}
```

- 第一页：`https://example.com/search/?key=关键词`
- 第二页：`https://example.com/search/2.html?key=关键词`

### Legado 内置分页语法

```
https://example.com/search/<,/{{page}}.html>?key={{key}}
```

- `<,/{{page}}.html>` 是 Legado 的内置分页语法
- 逗号前为第一页（空），逗号后为后续页模板
- `{{page}}` 从 1 开始递增

### 第一页无页数

```
https://example.com/gudai/{{page==1?'':'index_'+page+'.html'}}
```

- 第一页：`https://example.com/gudai/`
- 第二页：`https://example.com/gudai/index_2.html`

---

## 6. 多个搜索列表处理

部分网站搜索结果页包含多个不同结构的列表区域（如热门推荐 + 搜索结果），需要精准提取。

### 用共通 class 名取交集

```
div.hot_sale
```

如果多个列表区域都使用 `hot_sale` 这个 class，CSS 选择器会自动合并所有匹配结果。

### 用 XPath 排除干扰区域

```
//div[@id="searchmain"]//div[not(@class="searchResult")]
```

- `not(@class="searchResult")` 排除 class 为 searchResult 的干扰 div
- XPath 的 `not()` 谓词比 CSS 的 `:not()` 更灵活，支持属性值匹配

### 用 JS 过滤合并

```javascript
var list1 = JSON.parse(java.ajax(url1));
var list2 = JSON.parse(java.ajax(url2));
result = list1.concat(list2);
```

**适用场景**：搜索结果分散在多个 div 区域、页面包含推荐内容干扰搜索结果。

---

## 7. AJAX动态加载页面改用JSON API

部分站点的搜索结果页面通过AJAX动态加载（前端JS发起XHR请求获取数据后渲染DOM）。Legado的`java.ajax()`只获取初始HTML（不含动态加载的搜索结果），导致CSS选择器（如`.video-card`）匹配不到任何元素，列表大小为0。

### 诊断方法（Playwright Performance API）

用Playwright MCP访问搜索结果页面，执行`performance.getEntriesByType('resource')`监控网络请求，找到数据API的URL模式。

**操作步骤**：
1. 用 `playwright_navigate` 访问搜索结果页面 URL（如 `/search?k={keyword}`）
2. 用 `playwright_evaluate` 执行 `JSON.stringify(performance.getEntriesByType('resource').map(e => e.name))`
3. 从返回的网络请求列表中筛选出数据 API 端点（通常返回 JSON，URL 含 `api`/`search`/`async` 等关键词）
4. 识别 URL 模式（如 `/?m=searchall_async&api={code}&k={keyword}&p={page}`）

### 解决方案（改用JSON API + JSONPath）

将 `searchUrl` 改为直接请求数据 API（返回JSON），用 JSONPath 替代 CSS 选择器解析。

**字段改写映射**：

| 字段 | 原方案（CSS解析HTML） | 新方案（JSONPath解析JSON） |
|------|---------------------|--------------------------|
| `searchUrl` | `/search?k={keyword}`（返回HTML） | `/?m=searchall_async&api={code}&k={keyword}&p={page}`（返回JSON） |
| `ruleArticles` | `.video-card`（CSS选择器） | `$.list`（JSONPath） |
| `ruleTitle` | `.title@text` | `$.title` |
| `ruleImage` | `img@src` | `$.img` |
| `rulePubDate` | `.time@text` | `$.time` |
| `ruleLink` | `a@href` | `@js:var id=result.id; '/detail/'+id+'.html'`（JS构造详情页URL） |

**关键要点**：
- `searchUrl` 直接请求返回 JSON 的数据 API，跳过 HTML 渲染层
- `ruleArticles` 改用 JSONPath（如 `$.list`）从 JSON 中提取列表
- 各字段规则改用对应 JSONPath（如 `$.title`/`$.img`/`$.time`）
- `ruleLink` 用 `@js:` 构造详情页 URL（因为 JSON 中通常只有 ID，需拼接成完整路径）

### 通用范式

当HTML页面内容是AJAX动态加载时，**不要用CSS选择器解析HTML**，而要找到数据API直接请求JSON，用JSONPath解析。

**判断标志**：
- `java.ajax()` 获取的 HTML 中，列表容器为空（如 `<div class="list"></div>` 无子元素）
- 浏览器中查看页面有内容，但 `java.ajax()` 返回的 HTML 无内容
- 页面源码中能找到 AJAX 请求的 JS 代码（如 `$.get('/api/...')`）

**工具链**：
- 诊断：Playwright MCP + `performance.getEntriesByType('resource')` 发现数据 API 端点
- 解析：JSONPath 替代 CSS 选择器（`$.list` / `$.title` / `$.img` 等）
- 构造：`@js:` 规则用于拼接详情页 URL

**经验来源**：`[经验来源:AJAX动态加载改用JSON API范式]`

## 第8节: 多API搜索（合并多个子源搜索结果）

### 场景
聚合站点有多个子源（如13个子站），每个子源有独立的搜索API。用户要求搜索全部子源并合并结果。

### 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| java.ajaxAll并发 | 响应快 | 对JS重定向页面无效，8/12连接失败 | 不适用于安全检测站点 |
| java.ajax串行 | 可靠 | 响应慢（12*9秒=108秒最坏） | 适用于需合并结果的场景 |
| 仅主源搜索 | 最快 | 只搜1个子源 | 只需主源结果的场景 |

### 推荐方案：仅主源搜索 + 串行补充

1. searchUrl的JS返回主源搜索URL（api=sh），立即显示主源结果
2. 如需合并子源结果，用串行请求（不用ajaxAll）
3. 串行请求用`java.ajax(u)`单参数版本（避免Long参数陷阱，见陷阱60）
4. 失败请求try/catch跳过，不影响其他

### ajaxAll失效根因

`java.ajaxAll()`内部使用`mapAsync(searchThreadCount)`并发请求，但：
1. 对JS重定向/安全检测页面无效（铁证：v3版ajaxAll全部失败）
2. 并发请求可能触发反爬机制（8/12连接失败）
3. 速率限制（skipRateLimit=false时）可能限制并发数

### 多API搜索JS模板

```javascript
// searchUrl的JS（串行请求版）
var apis=['api1','api2',...];
var allList=[];
for(var i=0;i<apis.length;i++){
    try{
        var u=b+'/?m=searchall_async&api='+apis[i]+'&p=1&k='+kw+'&mod=jump';
        var body=java.ajax(u);  // 注意：用单参数版本，不用java.ajax(u,3000)
        if(body){
            var data=JSON.parse(body);
            if(data.list)allList=allList.concat(data.list);
        }
    }catch(e){}
}
cache.put('multi_search_others_'+kw,JSON.stringify(allList),300);
return b+'/?m=searchall_async&api=sh&p=1&k='+kw+'&mod=jump';  // 主源URL
```

```javascript
// ruleArticles的JS（合并主源+缓存结果）
var c=result;
try{
    var j=JSON.parse(c);
    if(j&&j.list){
        var allList=j.list.slice();  // 主源结果
        // 从缓存合并其他子源结果
        var kPos=baseUrl.indexOf('k=');
        var k='';
        if(kPos>=0){
            var kEnd=baseUrl.indexOf('&',kPos+2);
            k=kEnd>0?baseUrl.substring(kPos+2,kEnd):baseUrl.substring(kPos+2);
        }
        var cached=cache.get('multi_search_others_'+k);
        if(cached){
            try{
                var others=JSON.parse(cached);
                if(Array.isArray(others))allList=allList.concat(others);
            }catch(e){}
        }
        return allList.map(function(item){return JSON.stringify(item);});
    }
}catch(e){}
// HTML回退：用Jsoup解析
var d=org.jsoup.Jsoup.parse(c);
var cards=d.select('.video-card, .dr-card');  // 多模板适配
// ... 解析卡片 ...
```
