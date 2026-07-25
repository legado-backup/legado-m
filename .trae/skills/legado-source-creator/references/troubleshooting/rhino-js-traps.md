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
4. `RuleEngineServer.evalJS()` — JAR 独立命令
5. `AnalyzeRule.getString()` — NativeObject key 值访问
6. `AnalyzeRule.getStringList()` — NativeObject key 值访问

**验证结果**：20 个书源（10 个@js 规则 + 10 个起点相关）→ 0 个 NativeJavaObject/Undefined Bug。

**AI agent 行动指引**：
- JAR 仿真器已自动解包，无需手动处理
- 真机不存在此问题
- 如果在 JAR 测试中仍看到 `NativeJavaObject@hash`，说明 `unwrapRhinoResult()` 未覆盖到新的 evalJS 调用点，需检查源码
