# Rhino JS 语法陷阱

> Rhino JS引擎的语法限制和兼容性陷阱，创建书源时务必参考。

## 3.1 ES6+ 语法不可用

| 禁止 | 替代 |
|------|------|
| `let` / `const` | `var` |
| 箭头函数 `=>` | `function() {}` |
| 模板字符串 `` `Hello ${name}` `` | 字符串拼接 `'Hello ' + name` |
| 解构赋值 `const {a, b} = obj` | `var a = obj.a; var b = obj.b` |

## 3.2 Rhino 1.8.1 正则表达式兼容性（实测验证）

> ⚠️ **禁止用 Node.js 测试正则后直接用于 Legado！** 必须在 Rhino 1.8.1 环境中验证。

**测试环境**：Rhino 1.8.1 + `Context.VERSION_ES6`（与 Legado 配置一致）

| 正则特性 | ES 版本 | Rhino 1.8.1 | 说明 |
|----------|---------|-------------|------|
| 基本字符类 `[^']`、`\d`、`\w` | ES3 | ✅ 支持 | |
| 捕获组 `(...)` | ES3 | ✅ 支持 | |
| 非捕获组 `(?:...)` | ES3 | ✅ 支持 | |
| 正向前瞻 `(?=...)` | ES3 | ✅ 支持 | |
| 负向前瞻 `(?!...)` | ES3 | ✅ 支持 | |
| `String.match()` | ES3 | ✅ 支持 | |
| `String.replace(fn)` | ES3 | ✅ 支持 | 回调函数方式 |
| Sticky 标志 `/y` | ES6 | ⚠️ 部分支持 | 不报错但行为可能不一致 |
| dotAll 标志 `/s` | ES2018 | ⚠️ 部分支持 | 不报错但 `.` 可能不匹配换行 |
| **命名捕获组 `(?<name>...)`** | ES2018 | ❌ **SyntaxError** | 报"量词 ? 不正确" |
| **后行断言 `(?<=...)` / `(?<!...)`** | ES2018 | ❌ **SyntaxError** | 报"量词 ? 不正确" |
| **Unicode 属性 `\p{...}` + `/u` 标志** | ES2018 | ❌ **无效标志** | 报"标志 u 无效" |

**关键结论**：
- **ES3 基本正则完全兼容**，包括捕获组、非捕获组、前瞻断言
- **ES2018+ 正则特性全部不可用**：命名捕获组、后行断言、Unicode 属性转义
- `/s` 和 `/y` 标志不报错但行为不可靠，**避免使用**
- **测试正则时必须用 Rhino 1.8.1 环境**，Node.js/V8 支持更多特性

**Rhino 测试方法**：
```bash
# 下载 Rhino 1.8.1 JAR
curl -sL -o rhino.jar "https://repo1.maven.org/maven2/org/mozilla/rhino/1.8.1/rhino-1.8.1.jar"

# 运行测试（Windows）
java -cp "rhino.jar;." YourTestClass

# 或使用 jrunscript（注意：JDK 17+ 使用 Nashorn，不是 Rhino）
java -cp rhino.jar org.mozilla.javascript.tools.shell.Main -e "print('hello'.match(/l+/))"
```

| `for...of` | `for (var i = 0; i < arr.length; i++)` |
| `Promise` / `async/await` | 同步调用 |
| `Array.from()` | 手动遍历 |

## 3.3 byte 数组创建

```javascript
// ❌ 错误1：Rhino 不支持 Uint8Array
var arr = new Uint8Array(16);

// ❌ 错误2：Rhino 可能不支持 new byte[n] 语法（取决于版本）
var arr = new byte[16];

// ✅ 正确：使用 Java 反射创建 byte 数组（最安全）
var arr = java.lang.reflect.Array.newInstance(java.lang.Byte.TYPE, 16);
arr[0] = 0x41;  // 赋值
```

## 3.4 字符串转字节（⚠️ 高频陷阱）

```javascript
// ❌ 错误：JS 字符串没有 getBytes 方法！会报 TypeError: 找不到函数 getBytes
var bytes = 'hello'.getBytes('UTF-8');
var bytes = key.getBytes('UTF-8');

// ✅ 正确：必须先包装为 Java String 对象
var bytes = new java.lang.String('hello').getBytes('UTF-8');
var jKey = new java.lang.String(key);  // key 是搜索关键词（JS字符串）
var inputBytes = jKey.getBytes('UTF-8');
```

> **这是 Rhino JS #1 常见错误**：所有 `.getBytes()` / `.toCharArray()` 等 Java String 方法，都必须先 `new java.lang.String(jsString)` 包装。

## 3.5 不要重复造轮子——优先使用 Legado 内置方法

> ⚠️ **这是 #1 最高频错误**：很多 AI 会写几百行 `javax.crypto.*` 手动加密代码，但 Legado 已经内置了完整工具链！

### 错误示范（❌ 绝对禁止）

```javascript
// ❌ 手动调 javax.crypto — 500+字符，且会报错！
var jKey = new java.lang.String(key);          // 报错：无法读取 undefined 的属性 "String"
var aesKey = new javax.crypto.spec.SecretKeySpec(jKeyStr.getBytes('UTF-8'), 'AES');
var cipher = javax.crypto.Cipher.getInstance('AES/CBC/NoPadding');
cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, aesKey, ivSpec);
var encrypted = cipher.doFinal(paddedInput);
var base64 = android.util.Base64.encodeToString(encrypted, android.util.Base64.NO_WRAP);
```

**问题清单**：
1. `java.lang.String` 在 Rhino 中是 `undefined` → TypeError
2. `new byte[n]` 在部分 Rhino 版本不支持
3. 代码量巨大，维护困难

### 正确做法（✅）

```javascript
// ✅ Legado 内置方法 — 1 行核心调用
var base64 = java.createSymmetricCrypto('AES/CBC/NoPadding', 'key', 'iv').encryptBase64(key);
```

### Legado 内置方法完整清单

通过 `java` 变量在 @js: 规则中直接调用：

**加密/解密**：
| 方法 | 说明 |
|------|------|
| `java.createSymmetricCrypto(algo, key, iv).encryptBase64(data)` | 对称加密→Base64 |
| `java.createSymmetricCrypto(algo, key, iv).decryptStr(data)` | 解密→字符串 |
| `java.aesEncrypt(data, key)` | AES 加速加密（如有） |
| `java.desEncrypt(data, key)` | DES 加速加密（如有） |

**编码/解码**：
| 方法 | 说明 |
|------|------|
| `java.md5Encode(str)` / `java.md5Encode16(str)` | MD5 哈希 |
| `java.base64Encode(str)` / `java.base64Decode(str)` | Base64 编解码 |
| `java.hexEncode(str)` / `java.hexDecode(str)` | Hex 编解码 |

**摘要/签名**：
| 方法 | 说明 |
|------|------|
| `java.digestHex(data, algorithm)` | SHA-1/SHA-256/SHA-512 等 |
| `java.HMacHex(data, algorithm, key)` | HMAC-SHA256 等签名 |

**网络/缓存**：
| 方法 | 说明 |
|------|------|
| `java.ajax(options)` | HTTP 请求 |
| `java.getCache(key)` / `java.putCache(key, value)` | 缓存读写 |
| `java.getCookie(sourceKey)` / `java.setCookie(sourceKey, cookie)` | Cookie 操作 |

### 视频获取专用方法

| 方法 | 说明 | 示例 |
|------|------|------|
| `java.webViewGetSource(null, url, null, regex)` | **获取 JS 渲染后的视频地址**（最佳方式） | `java.webViewGetSource(null, baseUrl, null, ".*\\.m3u8.*")` |
| `java.ajax(url)` | HTTP GET 请求（不执行 JS） | `java.ajax('https://example.com/play.html')` |

> **选择原则**：如果 m3u8 地址在静态 HTML 中 → `java.ajax()` + 正则；如果需要 JS 执行才能生成 → `java.webViewGetSource()`

### ruleContent 格式选择

| 格式 | 适用场景 | 说明 |
|------|----------|------|
| `@js:` | 只返回字符串（m3u8 URL） | 简单，但无法输出 HTML 播放页 |
| `<js>...</js>` + HTML | **输出完整 HTML 播放页** | JS 先执行设置 result，HTML 中用 `<js>result</js>` 插入 |

> **视频源必须用 `<js>` + HTML 格式**，因为需要 HLS.js 播放器和控制按钮。

> **原则：写任何加密/编码逻辑前，先查上面的表。如果 Legado 已有内置方法，坚决不自己实现。**

## 3.6 RSS 订阅源 @js: 规则中 result 是 JSoup Element 对象

**现象**：在 RssSource 的 ruleImage 等子规则中使用 `@js:` 前缀时，调用 `result.match()` 报 `TypeError: 在对象 <article...>` 错误。

**原因**：在 RssSource 中，`ruleArticles` 用 CSS 选择器匹配到文章列表后，对每个文章元素执行子规则时，`result` 传入的是 JSoup Element 对象（Java 对象），而非 JS 字符串。JSoup Element 没有 `.match()` 方法，因此报 TypeError。

**源码依据**：`RssParserByRule.kt:74` 遍历 `getElements(ruleArticles)` 返回的 JSoup Element 列表，`RssParserByRule.kt:106` 调用 `analyzeRule.setContent(item)` 将 Element 设为当前内容，`AnalyzeRule.kt:835` 将其直接绑定为 JS 变量 `result`。

**错误示例**：
```javascript
// ❌ 错误：result 是 JSoup Element，没有 match 方法
@js:var m=result.match(/loadBannerDirect\('([^']+)'\)/);...

// ❌ 错误：String(result.html()) 在 Rhino 中不可靠转换 Java String → JS String
@js:var html=String(result.html());var m=html.match(/.../);...
```

**解决方案**：使用 JSoup 原生方法提取内容，再用 `+''` 拼接空字符串将 Java String 转为 JS String：
```javascript
// ✅ 方案1（推荐）：用 JSoup select + data() 精确提取 script 内容，+'' 转 JS String
@js:var url='';var scripts=result.select('script');for(var i=0;i<scripts.size();i++){var s=scripts.get(i).data()+'';var m=s.match(/loadBannerDirect\('([^']+)',/);if(m){url=m[1];break;}}...

// ✅ 方案2：用 outerHtml() + '' 获取完整 HTML 字符串
@js:var html=result.outerHtml()+'';var m=html.match(/loadBannerDirect\('([^']+)',/);...
```

**⚠️ 正则匹配陷阱**：从 JS 函数调用中提取参数时，注意参数之间的分隔符。
```javascript
// ❌ 错误：loadBannerDirect('URL', '') 中 URL 后是 ',' 不是 ')'
// 正则 loadBannerDirect\('([^']+)'\) 期望 URL 后紧跟 ')'
// 但实际格式是 loadBannerDirect('URL', '', ...)，URL 后是 ','
var m=s.match(/loadBannerDirect\('([^']+)'\)/);  // 匹配失败！

// ✅ 正确：用 ',' 匹配 URL 后的逗号分隔符
var m=s.match(/loadBannerDirect\('([^']+)',/);   // 匹配成功！
```

> **根因**：`loadBannerDirect('URL', '', ...)` 中 URL 后紧跟 `',`（单引号+逗号），不是 `')`（单引号+右括号）。正则 `'\)` 期望引号后紧跟右括号，但实际是逗号。

**关键要点**：
- `String(javaString)` 在 Rhino 中**不可靠**，不能保证将 Java String 转为 JS String
- `+''` 空字符串拼接是 Rhino 中最可靠的 Java String → JS String 转换方式
- `result.select('script')` 返回 JSoup Elements，`.get(i).data()` 返回 script 标签内的 JS 代码（Java String）
- `result.html()` 返回内部 HTML，`result.outerHtml()` 返回含外层标签的完整 HTML

**result 类型区分**（源码依据）：
| 规则 | result 类型 | 来源 | 是否需要转换 |
|------|------------|------|------------|
| RssSource ruleImage/ruleTitle/ruleLink/rulePubDate | JSoup Element | `getElements()` → `setContent(item)` | ✅ 需要 `+''` |
| RssSource ruleContent | JS String | `Rss.kt:137` `setContent(res.body)` | ❌ 直接用 `.match()` |
| BookSource ruleSearch 子规则 | JSoup Element | 同 RSS | ✅ 需要 `+''` |
| BookSource ruleContent | JS String | HTTP 响应体 | ❌ 直接用 `.match()` |

> **经验法则**：在 `@js:` 规则中，如果 `result` 来自 CSS 选择器匹配结果（JSoup Element），**必须用 `+''` 拼接空字符串**将 Java String 转为 JS String，**禁止用 `String()`**。如果 `result` 来自 HTTP 响应体（已经是 JS String），则直接使用。

## 3.7 RSS 订阅源 ruleArticles 需排除广告元素

**现象**：RSS 订阅源列表页中混入广告条目，广告文章与真实文章使用相同的 HTML 标签（如 `<article>`）。

**示例**（51cg 网站结构）：
```html
<!-- 真实文章 -->
<article itemscope itemtype="http://schema.org/BlogPosting" class="">
  <h2 class="post-card-title">文章标题</h2>
  ...
</article>

<!-- 广告 -->
<article class="ad-item">
  <a href="https://ad.example.com">广告</a>
</article>
```

**解决方案**：用属性选择器精确匹配，排除广告：
```json
// ❌ 匹配所有 article，包含广告
"ruleArticles": "article"

// ✅ 只匹配有 itemtype 属性的真实文章
"ruleArticles": "article[itemtype=\"http://schema.org/BlogPosting\"]"
```

**常见排除模式**：
| 网站 | 广告特征 | 选择器 |
|------|----------|--------|
| Typecho+Mirages 主题 | `<article class="ad-item">` | `article[itemtype="http://schema.org/BlogPosting"]` |
| WordPress 主题 | `<li class="sponsored">` | `li:not(.sponsored)` |
| 通用 | 广告无 `data-id` 属性 | `article[data-id]` |

## 3.8 加密图片在正文中的处理（data-xxx 属性模式）

**现象**：正文中的 `<img>` 标签 `src` 是占位图，真实加密 URL 在自定义 `data-xxx` 属性中。

**示例**（51cg 网站，Mirages 主题 + AES 加密）：
```html
<img src="/usr/plugins/tbxw/zw.png?v=1" data-xkrkllgl="https://pic.uoupfrl.cn/upload_01/xiao/20260528/img.jpeg">
```

**处理逻辑**：
1. 用 JSoup 选择器 `img[data-xkrkllgl]` 找到所有加密图片
2. 取 `data-xkrkllgl` 属性值作为真实 URL
3. 判断 URL 路径是否包含加密路径标识（如 `/xiao/`、`/upload_01/`）
4. 如果是加密图片：下载 → Base64 编码 → AES 解密 → 替换 src 为 data URI
5. 如果是非加密图片：直接替换 src

```javascript
var doc=org.jsoup.JSoup.parse(html);
var imgs=doc.select('img[data-xkrkllgl]');
for(var i=0;i<imgs.size();i++){
  var img=imgs.get(i);
  var src=img.attr('data-xkrkllgl');
  if(src.indexOf('/xiao/')>-1||src.indexOf('/upload_01/')>-1){
    try{
      var client=new Packages.okhttp3.OkHttpClient();
      var req=new Packages.okhttp3.Request.Builder().url(src).build();
      var resp=client.newCall(req).execute();
      var bytes=resp.body().bytes();resp.close();
      var b64=Packages.android.util.Base64.encodeToString(bytes,2);
      var decBytes=java.createSymmetricCrypto('AES/CBC/PKCS5Padding','key','iv').decrypt(b64);
      var d=Packages.android.util.Base64.encodeToString(decBytes,2);
      var ext=src.substring(src.lastIndexOf('.')+1);
      img.attr('src','data:image/'+ext+';base64,'+d);
    }catch(e){img.attr('src',src);}
  }else{img.attr('src',src);}
}
```

> **⚠️ 关键：`decryptStr` vs `decrypt`**：
> - `decryptStr(data)` — 返回 **String**，将解密后的 bytes 当文本解析。**仅适用于解密文本内容**（如 JSON、HTML）。
> - `decrypt(data)` — 返回 **ByteArray**，保留原始二进制数据。**解密图片/视频等二进制内容必须用此方法**。
> - 解密图片的正确流程：`加密bytes → Base64编码 → decrypt() → 解密bytes → Base64编码 → data URI`
> - 使用 `decryptStr` 解密图片会导致乱码（如 `data:image/jpeg;base64,����Exif`），因为 JPEG 的二进制头部 `FFD8FFE1` 被错误地当作 UTF-8 字符串。
> - 源码依据：`SymmetricCryptoAndroid.kt:38-45`，`decrypt()` 返回 `ByteArray`，`decryptStr()` 来自 hutool 父类将 bytes 转为 String。

> **关键发现**：Mirages 主题的加密图片路径标识为 `/xiao/`、`/upload_01/`、`/uploads/`、`/upload/upload/`，非加密路径（如 `/hc237/uploads/default/`）无需解密。

## 3.9 NativeJavaObject toString 输出哈希（⚠️ JAR 仿真器专属，真机无此问题）

**陷阱 #79** | 严重程度：🔴 高（导致 URL 和正文内容被哈希字符串污染）

**现象**：Rhino JS 引擎返回 Java 对象时，`toString()` 输出 `NativeJavaObject@e89439dc` 而非实际内容。

**影响范围**：
- URL 中嵌入哈希：`https://example.com/NativeJavaObject@e89439dc/page.html`
- 正文内容显示哈希：`NativeJavaObject@1a2b3c4d`
- 搜索结果书名/作者显示哈希

**根因**：Rhino 将 Java 对象包装为 6 种特殊类型，其 `toString()` 不返回实际值：

| 类型 | toString() 输出 | 实际值 |
|------|----------------|--------|
| `NativeJavaObject` | `NativeJavaObject@hash` | 被 unwrap 后的 Java 对象 |
| `NativeArray` | `NativeArray@hash` | JS 数组内容 |
| `NativeObject` | `[object Object]` | JS 对象属性 |
| `NativeJavaArray` | `NativeJavaArray@hash` | Java 数组内容 |
| `Undefined` | `undefined` | 空值 |
| `ConsString` | 正常但 `is String` 返回 false | 拼接字符串 |

**修复方案**：JAR 仿真器已内置 `AnalyzeRule.unwrapRhinoResult()` 自动处理：

```kotlin
// AnalyzeRule.kt companion object
fun unwrapRhinoResult(result: Any?): Any? {
    if (result == null) return null
    val className = result.javaClass.name
    return when {
        className.contains("NativeJavaObject") -> // 反射调用 unwrap()，递归解包
        className.contains("NativeArray") -> result.toArray()
        className.contains("NativeObject") -> result.toString()
        className.contains("NativeJavaArray") -> // 反射调用 unwrap()
        result is Undefined -> ""
        result is CharSequence && result !is String -> result.toString() // ConsString
        else -> result
    }
}
```

**修复覆盖点**（4 个 evalJS 入口 + 2 个 NativeObject key 访问）：
1. `AnalyzeRule.evalJS()` — 规则执行（核心入口）
2. `AnalyzeUrl.evalJS()` — URL 构建
3. `BaseSourceInterface.evalJS()` — 源接口
4. 规则引擎 evalJS — 通过 AnalyzeRule 执行
5. `AnalyzeRule.getString()` — NativeObject key 值访问
6. `AnalyzeRule.getStringList()` — NativeObject key 值访问

**验证结果**：20 个书源（10 个@js 规则 + 10 个起点相关）→ 0 个 NativeJavaObject/Undefined Bug。

**AI agent 行动指引**：
- JAR 仿真器已自动解包，无需手动处理
- 真机不存在此问题
- 如果在 JAR 测试中仍看到 `NativeJavaObject@hash`，说明 `unwrapRhinoResult()` 未覆盖到新的 evalJS 调用点，需检查源码

## 陷阱55: Rhino引擎类型转换陷阱（java.ajax返回Java String非JS String）

ruleContent JS中调用 `java.ajax(url)` 获取HTML后，直接对返回值使用 `.length` / `.charAt(i)` / `.indexOf()` 等 JS 字符串方法会得到错误结果，导致后续算法失效。

**现象**：
- `.length` 返回 `'function length() {/*'`（方法引用的字符串形式，非数字）
- `.charAt(i)` 返回 Java char 类型，字符 `===` 比较始终失败
- 平衡括号算法 `depth` 始终=0、`endIdx` 始终=-1，JSON 提取返回空

**根因**：`java.ajax()` 返回的是 `java.lang.String` 对象（Java 字符串），而非 JS 原生字符串。Rhino 引擎下 Java String 的 `.length` 是方法引用（不是属性，需 `.length()` 调用），`.charAt(i)` 返回 Java char 类型（不是 JS string），导致 `===` 严格比较失败（类型不同）。

**修复**：必须用 `String(java.ajax(url) || '')` 显式转换为 JS 原生字符串后再使用字符串方法。

**通用规则**：在 Rhino JS 中调用任何返回 `java.lang.String` 的 Java 方法（`java.ajax` / `java.base64Decode` / `java.encodeDecode` 等）后，必须用 `String()` 显式转换为 JS 原生字符串，再使用 `.length` / `.charAt` / `.indexOf` / `.substring` / `.match` 等字符串方法或属性。

**反模式**：
- ❌ 直接对 `java.ajax()` 返回值用 `.length`（得到方法引用字符串）
- ❌ 用 `==` 而非 `===` 比较 char（掩盖类型问题）
- ❌ 假设 Rhino 自动转换 Java String 为 JS String（Rhino 对方法引用不会自动转换）

**经验来源**：`[经验来源:Rhino类型转换范式]`

## 陷阱56: player_data JSON提取的平衡括号算法（避免正则过度匹配）

maccms 视频站点播放页 HTML 中，`player_data` 变量存储视频 URL，格式为 `var player_data={"url":"...","encrypt":0,...};</script>` 或 `var player_data={...}</script>`（注意分号可选）。

**问题**：原正则 `/player_data\s*=\s*({.*?})\s*;\s*<\/script>/` 在格式为 `}</script>`（无分号）时会过度匹配——`.*?` 非贪婪也会匹配到下一个 `}`，可能匹配错误内容；若放宽为 `({.*})` 又会匹配不足（只到第一个 `}`）。

**修复**：用平衡括号算法精确提取 JSON：
1. 找到 `var player_data` 起始位置
2. 找到第一个 `{` 作为 JSON 起始
3. 遍历字符，遇到 `{` 则 `depth++`，遇到 `}` 则 `depth--`，`depth=0` 时找到 JSON 结束位置
4. `substring(start, end+1)` 提取后 `JSON.parse`

**完整代码模板**：
```javascript
<js>(function(){
  var html = String(java.ajax(url) || '');
  var key = 'var player_data';
  var start = html.indexOf(key);
  if (start < 0) return '';
  var braceStart = html.indexOf('{', start);
  if (braceStart < 0) return '';
  var depth = 0, endIdx = -1;
  for (var i = braceStart; i < html.length; i++) {
    var ch = html.charAt(i);
    if (ch === '{') depth++;
    else if (ch === '}') { depth--; if (depth === 0) { endIdx = i; break; } }
  }
  if (endIdx < 0) return '';
  var jsonStr = html.substring(braceStart, endIdx + 1);
  try { var pd = JSON.parse(jsonStr); return pd.url || ''; } catch(e) { return ''; }
})()</js>
```

**通用规则**：从 HTML 中提取嵌套 JSON 结构（player_data / config / playlist 等）时，优先用平衡括号算法而非正则，避免过度匹配或匹配不足。

**适用场景**：
1. maccms 播放页 player_data 提取
2. 任意 HTML 内联 JSON 变量提取
3. JSON 内含嵌套对象/数组导致正则 `.*?` 失效的场景

**前置依赖**：必须先应用陷阱55（`String()` 转换），否则 `.charAt(i)` 返回 Java char，`===` 比较失败，`depth` 始终=0

**经验来源**：`[经验来源:平衡括号算法范式]`

## 陷阱58: 协程IO线程死锁（含java.ajax()的JS不能在Dispatchers.IO执行）

Rhino JS引擎在Kotlin协程IO线程（`Dispatchers.IO`）执行含 `java.ajax()` 的JS代码时会导致死锁。JS等待网络请求完成，但IO线程被JS占用，网络请求无法执行。

**现象**：
- 订阅源分类列表加载完全无响应（loading 永不结束）
- 搜索功能无响应（输入关键词后无任何结果返回）
- Logcat 无异常堆栈，但功能卡死

**根因**：
- `java.ajax()` 内部通过 OkHttp 发起网络请求，OkHttp 默认使用 `Dispatchers.IO` 调度
- 当 JS 代码本身在 `Dispatchers.IO` 线程执行时，JS 持有 IO 线程等待 ajax 返回
- 但 ajax 需要的 IO 线程被 JS 占用，形成循环等待 → 死锁
- 协程 IO 线程池默认 64 个线程，多个源同时执行此类 JS 时会耗尽

**影响范围**：
- 订阅源 `sortUrl` 字段如果是 JS 代码且包含 `java.ajax()`（如动态获取域名）
- 订阅源 `searchUrl` 字段如果是 JS 代码且包含 `java.ajax()`（如动态获取搜索接口）
- 上述场景在协程 IO 线程执行会死锁，导致分类加载和搜索功能完全无响应

**解决方案**：使用独立线程执行器（`Executors.newSingleThreadExecutor`）执行含网络请求的 JS 代码，避免在协程 IO 线程执行 `runScriptWithContext`。

**参考实现**：`RssSourceExtensions.kt` 中的 `sortUrlJsExecutor` 和 `getSearchUrl()` 方法：
- 定义单线程执行器：`private val sortUrlJsExecutor = Executors.newSingleThreadExecutor()`
- 提交 JS 执行任务到独立线程：`Future { runScriptWithContext(jsCode) }`
- 通过 `Future.get()` 获取结果，阻塞当前协程但不占用 IO 线程

**通用范式**：
- 任何在协程中执行含 `java.ajax()` / `java.ajaxAll()` 的 JS 代码，都必须用独立线程执行器
- 不能直接在 `Dispatchers.IO` 中执行 `runScriptWithContext`
- 单线程执行器确保 JS 执行和网络请求不会争抢同一线程池

**反模式**：
- ❌ 在 `withContext(Dispatchers.IO) { runScriptWithContext(jsWithAjax) }` 中直接执行含 `java.ajax()` 的 JS
- ❌ 假设协程 IO 线程池足够大（64线程）不会死锁（多个源并发时会耗尽）
- ❌ 用 `runBlocking` 替代独立线程执行器（仍可能占用协程线程）

**经验来源**：`[经验来源:协程IO线程死锁范式]`

## 陷阱59: Rhino中Java String的length是属性不是方法（length vs length()）

Rhino引擎中，Java String的`length`是属性（通过`getString().length()`的getter暴露），不是JS的`string.length`。在JS代码中调用`str.length()`会触发`EvaluatorException: 无法将function length()转换为java.lang.Integer`。

**现象**：
- ruleArticles/ruleNextPage的@js规则中用`str.length()`获取字符串长度，解析失败
- logcat显示"RSS使用默认规则解析"（规则执行异常后退化）
- Exception中含`NoSuchMethodException`（但非根因，是rebase方法）

**根因**：
- Rhino中Java String通过`java.lang.String`代理，`length`被解析为`String.length()`方法（函数对象）
- JS中`str.length()`调用该方法返回的是函数对象，不是数字
- 用`parseInt()`或数学运算时，函数对象无法转换为Integer

**解决方案**：
- JS中获取Java String长度用`str.length`（属性访问，非方法调用）
- 或用`new String(str).length`（先转为JS String）

**铁证**：7个订阅源ruleNextPage中`u.length()`导致分页规则执行异常，改为`u.length`后分页正常（p=2/3/4参数出现）

## 陷阱60: Rhino中java.ajax(url, timeout)的Long参数类型转换失败

Rhino引擎中调用`java.ajax(url, callTimeout)`时，JavaScript数字无法自动转换为Java的`Long?`类型，导致`NoSuchMethodException`（找不到匹配的方法签名）。

**现象**：
- searchUrl的JS中调用`java.ajax(u, 3000)`设置3秒超时，JS静默失败（try/catch捕获）
- 12个子源的串行请求全部跳过，没有HTTP请求日志
- logcat中无EvaluatorException（异常被try/catch静默吞掉）

**根因**：
- `JsExtensions.kt`中`fun ajax(url: Any, callTimeout: Long?): String?`，第二个参数是`Long?`
- Rhino中JavaScript数字默认是double，无法自动转换为Java的`Long`类型
- Rhino查找方法签名时，`ajax(String, double)`不匹配`ajax(Any, Long?)`
- try/catch捕获异常后继续执行，导致所有请求跳过

**解决方案**：
- 用单参数版本`java.ajax(url)`（使用默认超时）
- 或用`new java.lang.Long(3000)`显式创建Long对象（代码复杂，不推荐）
- 最佳实践：不在JS中设置超时，依赖App默认超时（9秒）

**铁证**：7个订阅源searchUrl中`java.ajax(u, 3000)`导致12子源串行请求全部跳过，改为`java.ajax(u)`后请求正常执行

## 陷阱61: java.ajax()自动跟随301重定向导致动态域名提取失败

`java.ajax()`会自动跟随HTTP 301/302重定向，返回重定向后的页面内容。如果JS代码在HTML内容中搜索punycode域名（`xn--`前缀），但重定向后的页面内容中不包含该字符串，动态域名提取失败。

**现象**：
- sortUrl/searchUrl的JS中`java.ajax(url)`获取主页HTML，正则搜索`xn--`提取punycode域名
- 主页301重定向到punycode域名的页面，返回的HTML中不含`xn--`字符串
- 动态域名提取失败，sortUrl/searchUrl返回空字符串
- 分类列表为空，搜索退化为请求主页URL（返回主页视频列表，非按关键词搜索）

**根因**：
- `java.ajax()`内部通过OkHttp请求，OkHttp默认跟随重定向
- 301重定向后，OkHttp请求重定向后的URL，返回重定向后页面的HTML内容
- 重定向后的页面是正常页面（不含`xn--`字符串），JS正则提取失败
- `xn--`字符串只在重定向过程中的Location头中出现，不在HTML内容中

**影响范围**：
- 使用punycode动态域名的站点（域名按日期变化，如含日期后缀）
- sortUrl/searchUrl的JS通过`java.ajax()`获取主页HTML+正则提取`xn--`域名的方案

**解决方案**：
- 方案1（推荐）：用`java.connect(url)`获取StrResponse，从`resp.raw.request.url`获取重定向后的URL
- 方案2：在请求URL中添加`&mod=jump`参数绕过安全检测页面，直接获取正常页面
- 方案3：缓存punycode域名（cache.put，6小时有效），减少动态域名提取次数

**铁证**：7个订阅源sortUrl的JS中`java.ajax()`获取主页，301重定向后HTML中不含`xn--`，动态域名提取失败。之前测试成功是因为缓存了动态域名（6小时有效），缓存过期后失败。添加`&mod=jump`参数后正常。

## 陷阱65: JSON中`\\n`被双重转义为字面量字符串（sortUrl分类分隔符失效）

**现象**：sortUrl的JS中用`r.join('\\n')`拼接分类列表，Legado解析后分类标签消失或合并为一个长字符串。日志显示返回值含字面量`\n`字符（反斜杠+n），而非换行符。

**根因**：JSON字符串中`\\n`在JSON解析时被还原为`\n`（两字符：反斜杠+n），而非JS的换行符（LF, 0x0A）。当JS代码`r.join('\\n')`写入JSON文件时，经过JSON.dump自动转义，`\\n`变为`\\\\n`，JS运行时收到的是`\\n`（字面量两字符），作为分隔符无法分割。

**JSON转义链路**：
```
源代码意图: r.join('\n')           → JS中得到换行符
JSON.dump后: "r.join('\\n')"       → JSON字符串中是\\n
JSON.parse后: r.join('\n')         → JS中得到\n（两字符字面量，非换行符）
```

**解决方案**：用`String.fromCharCode(10)`显式生成换行符，避免JSON转义链路破坏：
```javascript
// ❌ 错误：JSON中\\n被解析为字面量\n（反斜杠+n），无法分割
var result=r.join('\\n');

// ✅ 正确：用String.fromCharCode(10)生成真正的换行符
var LF=String.fromCharCode(10);
var result=r.join(LF);

// ✅ 也可用String.fromCharCode(10)+String.fromCharCode(10)生成空行
```

**通用规则**：JS中需要换行符（LF, 0x0A）、回车符（CR, 0x0D）、制表符（Tab, 0x09）等控制字符时，如果JS代码经过JSON序列化（如订阅源JSON文件），必须用`String.fromCharCode(code)`显式生成，禁止用`'\n'`/`'\r'`/`'\t'`字面量。

**适用场景**：
- sortUrl的JS返回分类列表（用`\n`分隔分类项）
- 任何JS返回多行文本的场景
- ruleContent的JS返回多段内容

**铁证**：7源sortUrl的JS用`r.join('\\n')`拼接12个分类，Legado解析后分类标签消失（实际是合并为一个含`\n`字面量的字符串）。改为`r.join(String.fromCharCode(10))`后12个分类正常显示。

**经验来源**：`[经验来源:JSON双重转义换行符范式]`
