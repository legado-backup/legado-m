# JS 扩展函数参考 — Cookie 与缓存

> 拆分自 js-extensions.md §五。Legado 书源 JS 环境中可调用的 Cookie 和缓存操作扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用 Cookie 函数，通过 `cache` 变量调用缓存函数。

---

## 五、Cookie 与缓存

### Cookie 操作

```javascript
var allCookies = java.getCookie("https://example.com");           // 获取指定域名所有 Cookie
var sid = java.getCookie("https://example.com", "sid");           // 获取指定域名+key 的 Cookie
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| getCookie | `getCookie(tag: String): String` | 指定域名所有 Cookie | 高 |
| getCookie | `getCookie(tag: String, key: String?): String` | 指定域名+key 的 Cookie | 高 |

---

### 缓存操作（CacheManager）

> 在 JS 中通过 `cache` 变量调用（非 `java.cache`），CacheManager 在 evalJS 的 bindings 中以 `cache` 名称注入。

```javascript
cache.put("key", "value");              // 写入缓存（永久）
cache.put("key", "value", 3600);        // 写入缓存（保存 3600 秒）
var val = cache.get("key");             // 读取缓存
var val = cache.get("key", true);       // 仅从磁盘读取（跳过内存缓存）
cache.putFile("key", "content");        // 文件缓存
cache.putFile("key", "content", 3600);  // 带时效文件缓存
var val = cache.getFile("key");         // 读取文件缓存
cache.delete("key");                    // 删除缓存
cache.putMemory("key", "value");        // 写入内存缓存（不持久化）
var val = cache.getFromMemory("key");   // 从内存读取
cache.deleteMemory("key");              // 删除内存缓存
```

| 函数 | 签名 | 频率 |
|------|------|------|
| put | `put(key: String, value: String, saveTime: Int = 0)` | 高 |
| get | `get(key: String): String?` | 高 |
| get | `get(key: String, onlyDisk: Boolean): String?` | 低 |
| putFile | `putFile(key: String, value: String, saveTime: Int = 0)` | 低 |
| getFile | `getFile(key: String): String?` | 低 |
| delete | `delete(key: String)` | 中 |
| putMemory | `putMemory(key: String, value: String)` | 中 |
| getFromMemory | `getFromMemory(key: String): String?` | 中 |
| deleteMemory | `deleteMemory(key: String)` | 低 |

---

### 变量存取（put / get）

> 在 JS 中通过 `java.put()` / `java.get()` 调用。变量存储优先级：章节变量 > 书籍变量 > 规则数据变量 > 源变量。

```javascript
java.put("lastPage", "3");          // 保存变量
var page = java.get("lastPage");    // 读取变量，返回 String
```

| 函数 | 签名 | 说明 | 频率 |
|------|------|------|------|
| put | `put(key: String, value: String): String` | 保存变量，返回 value | 极高 |
| get | `get(key: String): String` | 获取变量，不存在返回空字符串 | 极高 |

**特殊 key**：`bookName` 返回书名，`title` 返回章节标题（但这两个 key 的 put 值可能被覆盖，建议使用其他键名）。

## Cookie 双向共享机制

| 方向 | 机制 | 触发时机 |
|------|------|---------|
| WebView → OkHttp | CookieManager → CookieStore | onPageFinished 自动同步 |
| OkHttp → WebView | CookieStore → applyToWebView() | 需主动调用 |

### 源码依据
- BackstageWebView.kt L183-189: onPageFinished 中从 CookieManager 读取 Cookie 写入 CookieStore
- CookieStore.kt: OkHttp 的 Cookie 持久化存储

### CF 绕过场景
webView() 通过 CF JS Challenge 后，cf_clearance Cookie 自动从 WebView CookieManager 同步到 OkHttp CookieStore，后续请求自动携带。
