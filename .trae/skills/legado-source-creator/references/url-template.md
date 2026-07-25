# URL 模板语法与 UrlOption

> 搜索/发现 URL 的模板变量语法、UrlOption 完整参数表、POST 请求配置。

## 一、URL 模板变量

### 内置变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{key}}` | 搜索关键词 | `/search?q={{key}}` → `/search?q=斗破苍穹` |
| `{{page}}` | 当前页码 | `/list?p={{page}}` → `/list?p=1` |
| `{{host}}` | bookSourceUrl 的 scheme+host | `https://www.example.com` |
| `{{baseUrl}}` | bookSourceUrl 完整值 | `https://www.example.com/` |

### 变量运算（`{{}}` 内支持 JS 表达式）

| 表达式 | 说明 | 示例 |
|--------|------|------|
| `{{page-1}}` | 页码减1（第1页=0） | `/list?p={{page-1}}` |
| `{{page*10}}` | 页码乘10 | `/list?offset={{page*10}}` |
| `{{page+1}}` | 页码加1 | `/list/{{page+1}}` |
| `{{java.md5Encode(key)}}` | MD5加密关键词 | 签名计算 |
| `{{encodeURI(key)}}` | URL编码关键词 | 中文搜索 |

### UrlOption（URL 后缀 JSON）

URL 规则后面可用 `,{JSON}` 附加 UrlOption：

```
/search?q={{key}}&page={{page}},{"method":"POST","body":"keyword={{key}}","charset":"gbk"}
```

## 二、UrlOption 完整参数表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `method` | String | `"GET"` | GET/POST |
| `charset` | String | `"UTF-8"` | 请求/响应编码 |
| `headers` | String(JSON) | `null` | 本次请求的自定义头 |
| `body` | String | `null` | POST 请求体 |
| `origin` | String | `null` | 替代 bookSourceUrl 作为 Origin |
| `retry` | Int | `0` | 请求失败重试次数 |
| `type` | String | `null` | `"form"` / `"json"` / `"multipart"` |
| `webView` | Boolean | `false` | 使用 WebView 加载 |
| `webJs` | String | `null` | WebView 加载完后执行的 JS |
| `dnsIp` | String | `null` | 自定义 DNS IP |
| `delayTime` | Long | `0` | 请求延迟执行(毫秒) |
| `cacheFirst` | Boolean | `false` | 优先从缓存读取 |

### POST 请求示例

**普通 POST（form）**：
```
/search.php,{"method":"POST","body":"searchkey={{key}}&searchtype=articlename","charset":"gbk"}
```

**JSON POST**：
```
/api/search,{"method":"POST","body":"{\"keyword\":\"{{key}}\"}","type":"json","headers":"{\"Content-Type\":\"application/json\"}"}
```

**Multipart POST**：
```
/upload,{"method":"POST","type":"multipart","body":"file=@/path/to/file"}
```

## 三、常见 URL 模式

### 搜索 URL

```
# 简单 GET 搜索
/search.html?keyword={{key}}

# POST 搜索（GBK编码）
/search.php,{"method":"POST","body":"searchkey={{key}}","charset":"gbk"}

# 有签名的搜索
@js:'/api/search?q='+encodeURI(key)+'&sign='+java.md5Encode(key+'salt')+'&t='+new Date().getTime()

# JSON API 搜索
/api/v1/search?keyword={{key}},{"headers":"{\"Authorization\":\"Bearer token123\"}"}
```

### 分页 URL

```
# 从第1页开始
/list/{{page}}

# 从第0页开始（offset模式）
/list?offset={{page-1}}

# 每页20条
/list?p={{page}}&size=20

# 从第2页开始
/b/{{page+1}}
```

### 发现页 URL

```
# 分类浏览
/category/{{type}}/{{page}}

# JSON API 发现
/api/rank?type={{type}}&page={{page}}

# 带签名的发现
@js:'/api/v2/rank?type='+type+'&sign='+java.md5Encode(type+'secret')+'&page='+page
```

## 四、WebView 模式 URL

当网站依赖 JS 渲染内容时：

```
/search?q={{key}},{"webView":true}
```

或指定 WebView 中执行的 JS：

```
/search?q={{key}},{"webView":true,"webJs":"document.querySelector('.result-list').outerHTML"}
```

### WebView 获取内容的时机

```javascript
// webJs 中
// 等待动态内容加载完成
function waitFor(selector, timeout) {
    var start = Date.now();
    while (Date.now() - start < timeout) {
        var el = document.querySelector(selector);
        if (el) return el.outerHTML;
        java.lang.Thread.sleep(500);
    }
    return document.body.innerHTML;
}
result = waitFor('.search-result', 5000);
```

## 五、编码处理

### 常用编码值

| charset | 语言/地区 |
|---------|----------|
| `utf-8` | 通用（默认） |
| `gbk` | 中国大陆简体 |
| `gb2312` | 中国大陆简体（旧） |
| `big5` | 台湾繁体 |
| `euc-kr` | 韩文 |
| `shift_jis` | 日文 |