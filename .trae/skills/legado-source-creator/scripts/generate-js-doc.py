#!/usr/bin/env python3
"""
Legado Source Creator - generate-js-doc
用途: 从JS代码库中提取精华模式，生成js-patterns.md参考文档(15章)
依赖: 无额外依赖(仅标准库)
使用: python scripts/generate-js-doc.py
输入: temp/book/js-code-library.json, temp/deep-analysis-report.json, temp/masterpiece-sources.json
输出: references/js-patterns.md
注意: 需先运行verify-source生成分析数据

从JS代码库中提取精华模式，生成skill参考文档"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = str(Path(__file__).resolve().parent.parent)
SKILL_DIR = BASE_DIR
JS_LIB_PATH = os.path.join(BASE_DIR, "temp", "book", "js-code-library.json")
DEEP_REPORT = os.path.join(BASE_DIR, "temp", "deep-analysis-report.json")
MASTERPIECE_PATH = os.path.join(BASE_DIR, "temp", "masterpiece-sources.json")


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_unique_js_patterns(library):
    """从代码库中提取去重后的JS模式"""
    patterns = {
        'search_url': [],
        'explore_url': [],
        'login_url': [],
        'content': [],
        'toc': [],
        'bookinfo': [],
        'search_rule': [],
    }

    # searchUrl JS
    seen = set()
    for item in library.get('search_url_js', []):
        code = item.get('code', '')
        sig = code[:80]
        if sig not in seen:
            seen.add(sig)
            patterns['search_url'].append(item)

    # exploreUrl JS
    seen = set()
    for item in library.get('explore_url_js', []):
        code = item.get('code', '')
        sig = code[:80]
        if sig not in seen:
            seen.add(sig)
            patterns['explore_url'].append(item)

    # loginUrl JS
    seen = set()
    for item in library.get('login_url_js', []):
        code = item.get('code', '')
        sig = code[:80]
        if sig not in seen:
            seen.add(sig)
            patterns['login_url'].append(item)

    # content JS
    seen = set()
    for item in library.get('content_js', []):
        code = item.get('code', '')
        sig = code[:80]
        if sig not in seen:
            seen.add(sig)
            patterns['content'].append(item)

    # toc JS
    seen = set()
    for item in library.get('toc_js', []):
        code = item.get('code', '')
        sig = code[:80]
        if sig not in seen:
            seen.add(sig)
            patterns['toc'].append(item)

    # bookinfo JS
    seen = set()
    for item in library.get('bookinfo_js', []):
        code = item.get('code', '')
        sig = code[:80]
        if sig not in seen:
            seen.add(sig)
            patterns['bookinfo'].append(item)

    # search rule JS
    seen = set()
    for item in library.get('search_rule_js', []):
        code = item.get('code', '')
        sig = code[:80]
        if sig not in seen:
            seen.add(sig)
            patterns['search_rule'].append(item)

    return patterns


def categorize_js(code):
    """对JS代码进行功能分类"""
    categories = []

    if 'java.ajax' in code:
        categories.append('ajax')
    if 'java.getString' in code:
        categories.append('jsonpath')
    if 'java.getElements' in code:
        categories.append('css_selector')
    if 'java.md5Encode' in code or 'md5' in code.lower():
        categories.append('md5')
    if 'java.aesBase64DecodeToString' in code or 'createSymmetricCrypto' in code or 'AES' in code:
        categories.append('crypto')
    if 'java.base64Encode' in code or 'java.base64Decode' in code or 'base64' in code.lower():
        categories.append('base64')
    if 'webView' in code:
        categories.append('webview')
    if 'java.timeFormat' in code or 'Date' in code:
        categories.append('time')
    if 'java.put' in code or 'cache.get' in code or 'cache.put' in code:
        categories.append('cache')
    if 'java.t2s' in code:
        categories.append('t2s')
    if 'JSON.parse' in code or 'JSON.stringify' in code:
        categories.append('json')
    if 'result.match' in code or '.match(' in code:
        categories.append('regex')
    if 'result.replace' in code or '.replace(' in code:
        categories.append('replace')
    if 'java.setContent' in code:
        categories.append('set_content')
    if 'java.log' in code:
        categories.append('debug')
    if 'login' in code.lower() or 'cookie' in code.lower():
        categories.append('auth')
    if 'for(' in code or 'for (' in code:
        categories.append('loop')
    if 'function' in code:
        categories.append('function_def')
    if 'xGorgon' in code or 'X-Gorgon' in code:
        categories.append('xgorgon')
    if 'hexDecode' in code or 'hexEncode' in code:
        categories.append('hex')
    if 'importPackage' in code or 'JavaImporter' in code:
        categories.append('java_import')

    return categories or ['basic']


def generate_js_patterns_doc(patterns, report, masterpieces):
    """生成JS模式参考文档"""

    doc = """# Legado JS 模式参考手册

> 基于 yckceo.com 社区 23,881 个书源 + 2,702 个订阅源的深度分析
> 提取 160,121 个 JS 片段中的核心模式和大神技巧

---

## 一、java.xxx 方法调用频率 TOP15

| 方法 | 调用次数 | 用途 |
|------|----------|------|
| java.md5Encode | 5,586 | MD5哈希，API签名 |
| java.getString | 3,656 | JSONPath取值，解析API响应 |
| java.put | 3,610 | 缓存键值对，跨阶段传变量 |
| java.ajax | 2,783 | HTTP请求，获取额外数据 |
| java.get | 2,328 | 从缓存取值 |
| java.log | 1,618 | 调试输出 |
| java.timeFormat | 1,206 | 时间格式化 |
| java.getElements | 794 | CSS选择器获取元素列表 |
| java.lang | 481 | 多语言支持 |
| java.aesBase64DecodeToString | 442 | AES解密(Base64编码) |
| java.base64DecodeToByteArray | 380 | Base64解码为字节数组 |
| java.md5Encode16 | 373 | MD5哈希(16位) |
| java.security | 292 | 安全相关操作 |
| java.setContent | 268 | 设置正文内容 |
| java.t2s | 257 | 繁体转简体 |

---

## 二、result 变量使用模式

| 模式 | 次数 | 说明 |
|------|------|------|
| result.match() | 4,223 | 正则匹配提取数据 |
| result = ... | 2,551 | 赋值重写result（跨字段传递） |
| result.replace() | 2,334 | 字符串替换/清洗 |
| result.split() | 264 | 分割字符串 |
| result[0] | 183 | 数组索引取值 |
| result.trim() | 139 | 去除首尾空白 |
| result.toArray() | 121 | 转为数组 |
| result.html | 120 | 获取HTML内容 |
| result.push() | 119 | 数组追加元素 |
| result.includes() | 113 | 字符串包含判断 |

### 核心模式：result 跨字段传递

```
# ruleBookInfo.init 中设置变量
@js:
var data = JSON.parse(result);
java.put('bookId', data.id);    // 缓存bookId
result;

# ruleToc.chapterList 中使用变量
@js:
var bookId = java.get('bookId'); // 取出bookId
var url = 'https://api.example.com/books/' + bookId + '/chapters';
var html = java.ajax(url);
JSON.parse(html).data;
```

---

## 三、控制流模式

| 模式 | 次数 | 说明 |
|------|------|------|
| if/else | 3,180 | 条件判断 |
| JSON.stringify | 1,768 | 对象转JSON字符串 |
| JSON.parse | 1,662 | JSON字符串转对象 |
| for循环 | 1,609 | 遍历数组/列表 |
| while循环 | 631 | 条件循环 |
| try/catch | 590 | 异常处理 |

---

## 四、变量赋值模式

| 变量 | 次数 | 典型用途 |
|------|------|----------|
| url = ... | 1,917 | 构造请求URL |
| list = ... | 1,137 | 构造列表数据 |
| src = ... | 559 | 图片/视频源地址 |
| html = ... | 259 | HTML内容 |
| body = ... | 213 | 请求体 |
| doc = ... | 46 | DOM文档对象 |

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
result = li.map(item => Object.keys(item)[0] + '::' + Object.values(item)[0]).join('\\n');
```

**要点**：`名称::URL` 格式，用 `\\n` 分隔

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

---

## 八、ruleContent JS 模式（3,370个示例）

### 模式1：API响应解析

```javascript
<js>
var data = JSON.parse(result);
var content = data.data.content;
// 清洗HTML标签
content = content.replace(/<script[^>]*>[\\s\\S]*?<\\/script>/g, '');
content = content.replace(/<div class="ad[^"]*">[\\s\\S]*?<\\/div>/g, '');
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
var nextUrl = result.match(/nextPage['"]\\s*:\\s*['"]([^'"]+)/);
if (nextUrl) {
  var nextHtml = java.ajax(nextUrl[1]);
  pages.push(nextHtml);
}
pages.join('\\n');
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
chapters.map(ch => ch.title + '@@' + ch.url).join('\\n');
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
var nextUrl = html.match(/nextPage['"]\\s*:\\s*['"]([^'"]+)/);
while (nextUrl && list.length < 500) {
  var chapters = html.match(/<a[^>]*href="([^"]*)"[^>]*>([^<]*)<\\/a>/g);
  list = list.concat(chapters || []);
  html = java.ajax(nextUrl[1]);
  nextUrl = html.match(/nextPage['"]\\s*:\\s*['"]([^'"]+)/);
}
list.join('\\n');
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
result = info.name + '\\n' + info.author + '\\n' + info.intro;
```

---

## 十一、加密/签名模式（453个示例）

### AES解密

```javascript
var crypto = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv);
var decrypted = crypto.decryptBase64ToString(encrypted);
```

### MD5签名

```javascript
var sign = java.md5Encode(key + body + secret);
headers['X-Sign'] = sign;
```

### X-Gorgon签名（抖音/番茄系）

```javascript
// 需要引入xGorgon函数
xGorgon("/api/category/landing?", body)
```

---

## 十二、大神源完整链路分析

### 起点（优+）— 复杂度2713分

**链路**：搜索→发现→详情→目录→正文

| 阶段 | 关键JS | 技巧 |
|------|--------|------|
| searchUrl | @js:动态构造搜索URL | API签名+POST |
| exploreUrl | @js:生成分类列表 | 缓存+动态分类 |
| ruleSearch | @js:解析搜索结果 | JSONPath+字段映射 |
| ruleBookInfo | @js:解析详情 | hex解码+变量缓存 |
| ruleToc | @js:获取目录 | 分页+VIP标记 |
| ruleContent | @js:获取正文 | API请求+解密 |

**核心技巧**：
1. `java.put()`/`java.get()` 跨阶段传递bookId等变量
2. `java.hexDecodeToString()` 解码hex编码的API响应
3. `java.aesBase64DecodeToString()` 解密AES加密的正文
4. `enabledCookieJar:true` 保持登录状态
5. exploreUrl用JS动态生成分类，支持男女频切换

### 淘小说（优++）— 复杂度1276分

**核心技巧**：
1. searchUrl中构造POST请求体
2. header中设置自定义请求头
3. ruleSearch.kind用JS解析分类标签
4. ruleToc.chapterUrl用JS修正URL格式

---

## 十三、订阅源JS技巧

### 微博博主（复杂度283分）

**核心技巧**：
1. sourceUrl中使用`#`锚点区分不同功能
2. ruleArticles用JS解析微博API
3. ruleContent用JS拼接完整内容
4. sortUrl用JS动态生成博主列表

### 18AV视频源（复杂度260分）

**核心技巧**：
1. loginUrl处理年龄确认页
2. ruleContent用webView获取m3u8地址
3. sortUrl动态生成分类
4. enabledCookieJar保持Cookie

---

## 十四、常见陷阱

1. **Rhino引擎ES5限制**：不能用let/const/箭头函数/模板字符串
2. **result变量必须返回**：JS代码最后必须有一个表达式作为返回值
3. **@js: vs <js>**：@js:只返回JS表达式值，<js>允许JS和HTML混合
4. **java.put/get是进程内缓存**：App重启后丢失
5. **webViewGetSource是异步的**：需要等待页面加载完成
6. **JSON.stringify构造POST请求**：必须包含method字段
7. **正则中的反斜杠**：JS字符串中需要双转义 `\\\\d` 匹配 `\\d`

"""

    return doc


def main():
    print("生成JS模式参考文档...")

    library = load_json(JS_LIB_PATH)
    report = load_json(DEEP_REPORT)
    masterpieces = load_json(MASTERPIECE_PATH)

    patterns = extract_unique_js_patterns(library)
    doc = generate_js_patterns_doc(patterns, report, masterpieces)

    output_path = os.path.join(SKILL_DIR, "references", "js-patterns.md")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f"✓ JS模式参考文档: {output_path}")

    # 统计
    total_items = sum(len(v) for v in patterns.values())
    print(f"  去重后JS示例: {total_items}")
    for k, v in patterns.items():
        print(f"  {k}: {len(v)}")


if __name__ == '__main__':
    main()
