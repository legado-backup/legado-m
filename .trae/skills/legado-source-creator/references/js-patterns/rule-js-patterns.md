# ruleContent / ruleToc / ruleBookInfo JS 模式

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析

---

## 八、ruleContent JS 模式（3,370个示例）

### 模式1：API响应解析

```javascript
<js>
var data = JSON.parse(result);
var content = data.data.content;
// 清洗HTML标签
content = content.replace(/<script[^>]*>[\s\S]*?<\/script>/g, '');
content = content.replace(/<div class="ad[^"]*">[\s\S]*?<\/div>/g, '');
content;
</js>
```

### 模式2：加密内容解密

```javascript
<js>
var data = JSON.parse(result);
var encrypted = data.data.content;
var key = '2d4ebb7cb767dab1';
var iv = '7563ca4af41bd0fb';
var crypto = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv);
var decrypted = crypto.decryptBase64ToString(encrypted);
decrypted;
</js>
```

### 模式3：多页正文拼接

```javascript
<js>
var pages = [result];
var nextUrl = result.match(/nextPage['"]\s*:\s*['"]([^'"]+)/);
if (nextUrl) {
  var nextHtml = java.ajax(nextUrl[1]);
  pages.push(nextHtml);
}
pages.join('\n');
</js>
```

### 模式4：WebView获取JS渲染内容

```javascript
@js:
var html = java.webViewGetSource(null, url, null, '正文内容');
html;
```

### 模式5：hex解码+API请求

```javascript
<js>
bid=JSON.parse(java.hexDecodeToString(result)).bookId
cid=JSON.parse(java.hexDecodeToString(result)).chapterId
url='https://api-x.example.com/chapter/'+bid+'/'+cid
java.ajax(url)
</js>
```

---

## 九、ruleToc JS 模式（5,323个示例）

### 模式1：API目录解析

```javascript
@js:
var data = JSON.parse(result);
var chapters = data.data.chapterList;
chapters.map(ch => ch.title + '@@' + ch.url).join('\n');
```

### 模式2：繁简转换

```javascript
<js>
result=java.t2s(tzs(result))
</js>
@js:result.replace("••","")
```

### 模式3：分页目录

```javascript
@js:
var list = [];
var html = result;
var nextUrl = html.match(/nextPage['"]\s*:\s*['"]([^'"]+)/);
while (nextUrl && list.length < 500) {
  var chapters = html.match(/<a[^>]*href="([^"]*)"[^>]*>([^<]*)<\/a>/g);
  list = list.concat(chapters || []);
  html = java.ajax(nextUrl[1]);
  nextUrl = html.match(/nextPage['"]\s*:\s*['"]([^'"]+)/);
}
list.join('\n');
```

---

## 十、ruleBookInfo JS 模式（4,821个示例）

### 模式1：Base64编码传递bookId

```javascript
// ruleBookInfo.init
.BaseBookInfo.BookId
<js>java.base64Encode(result)</js>

// ruleToc.chapterList
data:bookId;base64,{{result}}
```

**要点**：用base64编码在字段间传递复杂ID

### 模式2：JSONPath + 条件判断

```
{{java.getString("$..IsInBlackList")==1?"非限免":"限免"}}|{{$.BaseBookInfo.BookStatus##1##连载##2##完结}}
```

### 模式3：多字段组合

```javascript
@js:
var data = JSON.parse(result);
var info = data.data;
java.put('bookId', info.id);
result = info.name + '\n' + info.author + '\n' + info.intro;
```

## CF 检测模式

```javascript
var s=result.body();if(s.indexOf('Just a moment')!=-1){java.startBrowserAwait(source.sourceUrl,'通过Cloudflare验证');}result;
```

### 要点
1. 检测 CF 特征："Just a moment" 是 CF JS Challenge 的标题
2. 检测到 CF → 弹浏览器让用户手动通过（Turnstile/Interactive 的降级方案）
3. **必须返回 result**：loginCheckJs 必须返回 StrResponse 对象，末尾加 `result;`
4. 不能返回 String：`java.ajax()` 返回 String，不能直接作为 loginCheckJs 的返回值
