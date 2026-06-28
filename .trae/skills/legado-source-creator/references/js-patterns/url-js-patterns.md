# searchUrl / exploreUrl / loginUrl JS 模式

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析

---

## 五、searchUrl JS 模式（1,500个示例）

### 模式1：API签名（最常见）

```javascript
@js:
sign_key='d3dGiJc651gSQ8w1'
headers={'app-version':'51110','platform':'android'}
body=JSON.stringify({'keyword':key})
sign=java.md5Encode(sign_key+body+sign_key)
headers['sign']=sign
JSON.stringify({body:body,headers:headers,method:'POST'})
```

**要点**：
- 用 `java.md5Encode()` 做签名
- 用 `JSON.stringify()` 构造请求体
- headers中放签名和版本信息
- 最后返回 `JSON.stringify({body, headers, method})` 格式

### 模式2：动态URL构造

```javascript
@js:
var url = 'https://api.example.com/search?keyword=' + encodeURI(key);
if (page > 1) {
  url += '&page=' + page;
}
url;
```

### 模式3：POST请求

```
https://api.example.com/search,{"method":"POST","body":"keyword={{key}}"}
```

**要点**：URL后直接跟JSON配置，`{{key}}`模板语法自动替换

---

## 六、exploreUrl JS 模式（1,259个示例）

### 模式1：分类列表生成

```javascript
@js:
li = [
  {"༺墨辰整合系列༻": ""},
  {"男生频道": "1"},
  {"女生频道": "2"},
  {"出版频道": "3"},
]
result = li.map(item => Object.keys(item)[0] + '::' + Object.values(item)[0]).join('\n');
```

**要点**：`名称::URL` 格式，用 `\n` 分隔

### 模式2：带缓存的分类

```javascript
<js>
if (cache.get("fx")=='female'){
  result=java.ajax('http://static.yesui.me/api/female.json');
} else {
  result=java.ajax('http://static.yesui.me/api/male.json');
}
result;
</js>
```

### 模式3：日期动态生成

```
今日更新::分类URL/{{new Date().toISOString().split('T')[0]}}
本周热门::分类URL/week
```

---

## 七、loginUrl JS 模式（2,260个示例）

### 模式1：简单登录函数

```javascript
function login() {
  var url = "https://www.example.com/login";
  var html = java.ajax(url);
  // 解析登录页面获取token
  var token = html.match(/name="_token" value="([^"]+)"/);
  if (token) {
    var body = "_token=" + token[1] + "&username=xxx&password=xxx";
    java.ajax(url + ",{method:'POST',body:'" + body + "'}");
  }
}
login();
```

### 模式2：浏览器登录

```javascript
function login(){}
function zc() {
  java.startBrowserAwait("https://api-x.example.com/login", "登录");
}
```

### 模式3：Cookie检查

```javascript
// 登录及登录检查
function login_(openBrowser, checkMode) {
  var cookie = java.getCookie("https://www.example.com");
  if (cookie && cookie.indexOf("session") > -1) {
    return; // 已登录
  }
  if (openBrowser) {
    java.startBrowserAwait("https://www.example.com/login", "登录成功");
  }
}
```

### 模式4：分页 URL 嵌入 JS 的处理（实战案例）

> 有些网站的下一页 URL 不是简单的 `<a href>` 链接，而是嵌入在 `<script>` 标签中。

**场景**：91短视频的下一页 URL 有两种格式：
1. `let url = "..."`
2. `<script name="cc">...</script>`

**ruleNextPage 规则**：
```javascript
script@all
<js>
// 一个正则匹配两种格式，直接取 uri
const reg = /let\s+url\s*=\s*"([^"]+)"|<script\s+name="cc">([^<]+)<\/script>/g;
let match;
while ((match = reg.exec(result)) !== null) {
  // 两种格式分别存在 match[1] 或 match[2]
  const uri = match[1] || match[2];
  result = uri;
}
</js>
```

**关键技巧**：
- 用 `script@all` 获取所有 script 标签内容
- 用正则匹配多种 URL 格式
- 使用 `match[1] || match[2]` 处理两种捕获组

**教训**：不要假设分页是简单的 `<a>` 链接，需要深入分析 HTML 结构。

## CF 绕过模式

### JS Challenge 自动通过
```javascript
@js:java.webView(null, source.sourceUrl, null, false);
```
适用：CF JS Challenge（5秒盾），webView() 自动执行验证 JS，Cookie 自动同步。

### Turnstile 手动通过（降级方案）
```javascript
@js:java.startBrowserAwait(source.sourceUrl, '通过Cloudflare验证');
```
适用：CF Turnstile/Interactive Challenge，需用户手动操作。
