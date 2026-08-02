# 加密图片处理

> 封面图片解密（coverDecodeJs）、正文图片解密/替换、图片代理的完整处理方案。

## 4.1 封面图片解密（`coverDecodeJs`）

`coverDecodeJs` 是 BookSource 和 RssSource 的顶层字段，用于对封面图片原始字节进行解密。

### 参数说明

JS 执行时自动注入以下变量：

| 变量 | 类型 | 说明 |
|------|------|------|
| `result` | ByteArray | 封面图片的原始字节（必须返回解密后的 ByteArray） |
| `src` | String | 封面图片的 URL |
| `book` | Book? | 当前书籍对象（可能为 null） |

> **返回值**：必须返回解密后的 `ByteArray`，否则图片无法显示。

### 示例

**AES-CBC 解密封面（推荐，JavaImporter 直调 javax.crypto）**：

```json
{
  "coverDecodeJs": "(function(){\nvar aly = new JavaImporter(Packages.javax.crypto.Cipher, Packages.javax.crypto.spec.SecretKeySpec, Packages.javax.crypto.spec.IvParameterSpec);\nvar out;\nwith (aly) {\n  var key = new SecretKeySpec(Packages.java.lang.String('f5d965df75336270').getBytes('UTF-8'), 'AES');\n  var iv = new IvParameterSpec(Packages.java.lang.String('97b60394abc2fbe1').getBytes('UTF-8'));\n  var cipher = Cipher.getInstance('AES/CBC/PKCS5Padding');\n  cipher.init(Cipher.DECRYPT_MODE, key, iv);\n  out = cipher.doFinal(result);\n}\nreturn out;\n})()"
}
```

> **⚠️ 必须无 `@js:` 前缀**：调用链 `ImageUtils.decode` → `BaseSource.evalJS` → `AbstractScriptEngine.eval(script, scope)` → `RhinoScriptEngine.eval(reader, scope)` 全程无前缀剥离，`@js:` 会直接 JS 编译失败（2026-08-01 站点H封面解密验证）。
>
> **⚠️ 慎用 hutool `java.createSymmetricCrypto`**：hutool 5.8.22 `new SymmetricCrypto("AES/CBC/PKCS5Padding", key)` 在 JVM 抛 `InvalidKeyException: Wrong algorithm: AES or Rijndael required`（`KeyUtil.generateKey` 把完整 transformation 当算法名传给 `SecretKeySpec`）。Android Conscrypt 行为未验证，双保险用 `javax.crypto` 直调。
>
> **`result` 传参兼容**：`ScriptBindings.set` 经 `Context.javaToJS` 把 ByteArray 包装成 `NativeJavaArray`，`cipher.doFinal(result)` 可正常匹配 `doFinal(byte[])`（Rhino 1.8.1 端到端验证）。
>
> **加密端填充判定**：密文 16 对齐 + 解密尾部为 N 字节 `0x0N` 时，说明加密端用标准 PKCS7 填充，用 `AES/CBC/PKCS5Padding` 自动 unpad，无需手动截尾。

**AES-CBC 解密封面（旧写法，hutool）**：

```json
{
  "coverDecodeJs": "var key = '0123456789abcdef';\nvar iv = 'abcdef0123456789';\nvar crypto = java.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv);\ncrypto.decrypt(result)"
}
```

**简单异或解密**：

```json
{
  "coverDecodeJs": "var arr = result;\nfor (var i = 0; i < arr.length; i++) {\n  arr[i] = arr[i] ^ 0xFF;\n}\narr"
}
```

> **⚠️ base64 文本封面被"块对齐校验"静默拦截（2026-08-02 真机验证）**：当封面图片原始字节是 **base64 编码的文本**（如 `.dat` 后缀、首字节为 base64 ASCII `U`=0x55）而非二进制密文时，`ImageUtils.decode` 会先执行块对齐校验（旧源码 `bytes.size % 8 != 0 && bytes.size % 16 != 0` 则跳过解密）——base64 文本长度任意，极易非块对齐（如 95884%8=4、%16=12）→ **coverDecodeJs 完全不执行**，base64 文本原样返回给 Glide → skia 报 `Failed to create image decoder with message 'unimplemented'`，图片永远不显示。
>
> **诊断要点**：Logcat 大量 `skia ... 'unimplemented'` + 无「图片解密错误」AppLog + Glide 磁盘缓存（image_manager_disk_cache）里存的是 base64 文本（head `UklGR...`）而非 `RIFF`/WebP 头 → 基本可判定被此校验拦截。
>
> **修复**（已在 Legado 源码 `app/src/main/java/io/legado/app/utils/ImageUtils.kt` 修复）：
> 1. 移除块对齐校验块（`if (bytes.size % 8 != 0 && bytes.size % 16 != 0) return bytes`）——未加密图片保护由 `isKnownImageFormat` 文件头检测（PNG 89/JPG FF D8 FF/GIF 47 49 46 38/WebP 52 49 46 46）独立覆盖，块校验是冗余拦截，移除安全
> 2. evalJS 失败兜底由返回 null（→ onStreamReady(null) → failUrl 永久短路不再重试）改为 `?: bytes` 返回原始字节，允许后续重试
>
> 本项属于 Legado 引擎层修复，书源侧仅需保证：封面走 coverDecodeJs 时用 base64 解码（`Packages.java.util.Base64.getDecoder().decode(s)` 优先 + `Packages.android.util.Base64.decode(s,0)` 兜底 + 返回 result 最后兜底）。经验来源 `[经验来源:封面解密范式]`。

### 源码位置

- 字段定义：`BookSource.coverDecodeJs` / `RssSource.coverDecodeJs`
- 解密逻辑：`ImageUtils.decode()` → `source.evalJS(ruleJs)` 注入 result/src/book 变量

---

## 4.2 正文图片解密（`imageDecode`）

`imageDecode` 是 `ContentRule` 的字段，用于对正文中的图片字节进行二次解密。用法与 `coverDecodeJs` 完全一致。

### 参数说明

| 变量 | 类型 | 说明 |
|------|------|------|
| `result` | ByteArray | 正文图片的原始字节 |
| `src` | String | 图片 URL |
| `book` | Book? | 当前书籍对象 |

### 示例

```json
{
  "ruleContent": {
    "content": "class.read-content@html",
    "imageDecode": "var key = 'mykey1234567890';\nvar iv = 'myiv12345678901';\njava.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv).decrypt(result)"
  }
}
```

### coverDecodeJs vs imageDecode 区别

| 维度 | coverDecodeJs | imageDecode |
|------|--------------|-------------|
| 位置 | BookSource/RssSource 顶层字段 | ContentRule 子字段 |
| 作用对象 | 封面图片 | 正文中的图片 |
| 触发时机 | Glide 加载封面时 | 加载正文图片时 |
| RssSource 支持 | ✅ | ❌（RssSource 无 ContentRule） |

---

## 4.3 正文图片替换（`replaceRegex`）

`replaceRegex` 是 `ContentRule` 的字段，用于对正文 HTML 进行正则替换。常用于将加密图片 URL 替换为解密后的 URL，或注入 JS 解密逻辑。

### 参数格式

```
##正则表达式##替换内容
```

- 正则表达式：Java 正则语法
- 替换内容：纯文本或 `@js:` 前缀的 JS 代码

### 替换内容支持 `@js:` 前缀

当替换内容以 `@js:` 开头时，每个匹配项会执行 JS 代码，JS 中可用变量：

| 变量 | 类型 | 说明 |
|------|------|------|
| `result` | String | 当前匹配到的文本 |
| `chapter` | BookChapter? | 当前章节对象 |
| `book` | ReplaceBook? | 当前书籍摘要 |

### 示例

**替换加密图片 URL 为解密 URL**：

```json
{
  "ruleContent": {
    "replaceRegex": "##<img src=\"([^\"]+)\"##<img src=\"@js:java.decodeImageUrl('$1')\""
  }
}
```

**移除广告 HTML**：

```json
{
  "ruleContent": {
    "replaceRegex": "##<div class=\"ad-[^\"]*\">[\\s\\S]*?</div>##"
  }
}
```

**使用 JS 替换函数**：

```json
{
  "ruleContent": {
    "replaceRegex": "##<img data-src=\"([^\"]+)\"[^>]*>##<img src=\"@js:'$1'\">"
  }
}
```

### 源码位置

- 字段定义：`ContentRule.replaceRegex`
- 执行逻辑：`BookContent.getContentStr()` → `analyzeRule.getString(replaceRegex, contentStr)`
- JS 替换：`RegexExtensions.replace()` → `@js:` 前缀检测 → `RhinoScriptEngine.run()`

---

## 4.4 图片显示样式（`imageStyle`）

`imageStyle` 控制 Legado 阅读界面中正文图片的显示方式。有两种设置位置：

1. **ContentRule.imageStyle**：书源级别，所有使用该源的书都生效
2. **Book.ReadConfig.imageStyle**：书籍级别，用户可单独覆盖

### 支持的值

| 值 | 说明 | 效果 |
|-----|------|------|
| `DEFAULT` 或空 | 默认模式 | 图片居中显示，按原始大小渲染，不超过屏幕宽度 |
| `FULL` | 全宽模式 | 图片宽度撑满屏幕宽度，适合漫画/图集类书源 |
| `TEXT` | 文本模式 | 图片作为行内元素，与文字同行显示 |
| `SINGLE` | 单图模式 | 每页只显示一张图片，左右翻页浏览，适合漫画 |

> **注意**：源码中未定义 `WIDE`、`CENTER`、`CUSTOM` 值，这些不是 Legado 原生支持的 imageStyle 选项。

### 示例

**漫画书源（全宽显示）**：

```json
{
  "bookSourceType": 2,
  "ruleContent": {
    "content": "class.comic-page@img@src",
    "imageStyle": "FULL"
  }
}
```

**漫画书源（单图翻页）**：

```json
{
  "bookSourceType": 2,
  "ruleContent": {
    "content": "class.comic-page@img@src",
    "imageStyle": "SINGLE"
  }
}
```

### 源码位置

- 字段定义：`ContentRule.imageStyle` / `Book.ReadConfig.imageStyle`
- 常量定义：`Book.imgStyleDefault` / `Book.imgStyleFull` / `Book.imgStyleText` / `Book.imgStyleSingle`

---

## 4.5 图片代理

部分网站对图片做了防盗链处理（Referer 检查），需要通过 Legado 的图片代理加载。

### 方案1：使用 `@js:` 规则获取图片

在 `ruleContent` 中使用 JS 规则获取图片 URL，Legado 内置的图片加载会自动处理：

```json
{
  "ruleContent": {
    "content": "<js>var imgs = java.getElements('class.read-content img');\nvar result = '';\nfor (var i = 0; i < imgs.length; i++) {\n  result += '<img src=\"' + imgs[i].attr('src') + '\">';\n}\nresult</js>"
  }
}
```

### 方案2：使用 header 字段

在书源顶层 `header` 字段中设置 Referer，图片请求会自动携带：

```json
{
  "header": "{\"Referer\":\"https://example.com\"}"
}
```

---

## 4.6 常见加密图片场景

### key/iv 逆向获取（站点 JS 下划线十进制 ASCII）

部分站点的加密 key/iv 不直接明文暴露，而是以 `media_key`/`media_iv` 形式存于 `app.config.js` 等配置文件，值为下划线分隔的十进制 ASCII：

```js
// 站点 app.config.js
media_key: "102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48",
media_iv: "57_55_98_54_48_51_57_52_97_98_99_50_102_98_101_49"
```

还原方式（站点 JS 用 `String.fromCharCode(...)`，实现直接写死十进制值）：

```js
// key = 'f5d965df75336270'  iv = '97b60394abc2fbe1'
var key = Packages.java.lang.String('102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48'.split('_').map(function(n){return String.fromCharCode(parseInt(n,10));}).join(''));
```

> 逆向步骤：Playwright/curl 抓 `app.config.js` → 定位 `media_key`/`media_iv` → 下划线十进制 ASCII → 16 字节 AES-128 key/iv。经验标注 `[经验来源:封面解密范式]`。

### 站点JT实例（2026-08-02，与站点H同密钥组）

> 站点JT（视频订阅源）封面图片字节为 AES-CBC 密文（头 `093de3b1`/`1e37f55c`/`3eaa708e` 非图片魔数，Content-Type `binary/octet-stream`），密钥与 API 响应密钥（http.js）**不同**，藏于打包 bundle `crypto-worker.js`：
>
> ```js
> media_key: "102_53_100_57_54_53_100_102_55_53_51_51_54_50_55_48",  // key = f5d965df75336270
> media_iv:  "57_55_98_54_48_51_57_52_97_98_99_50_102_98_101_49",  // iv  = 97b60394abc2fbe1
> ```
>
> 解密后为 JPEG(`ffd8ffe0`)/PNG(`89504e47`)。coverDecodeJs 用 JavaImporter javax.crypto AES-CBC-PKCS5，`cipher.doFinal(result)` 返回解密后 ByteArray（.png 解密后仍 PNG，.jpeg 解密后仍 JPEG，格式正确）。

**⚠️ Glide 磁盘缓存残留旧密文陷阱（2026-08-02 真机验证）**：当封面从"未加密"状态改为"新增 coverDecodeJs"后，`image_manager_disk_cache` 中已缓存的同 URL 密文不会重新走解密（Glide 命中缓存直接返回旧字节）→ 该图继续白屏。**修复**：`am force-stop` 后删除 `/data/data/{pkg}/cache/image_manager_disk_cache`（与 `okhttp_cache`）再重启。经验标注 `[经验来源:封面解密范式]`。

### Mirages 图片加密

部分网站使用 Mirages 插件对图片进行 AES-CBC 加密，需要解密后才能显示：

```json
{
  "ruleContent": {
    "content": "class.article-content@html",
    "imageDecode": "var key = java.base64Decode('base64编码的key');\nvar iv = java.base64Decode('base64编码的iv');\njava.createSymmetricCrypto('AES/CBC/PKCS5Padding', key, iv).decrypt(result)"
  }
}
```

> 详见 `references/troubleshooting/crypto-traps.md`

### Canvas 渲染图片

部分网站使用 Canvas 动态渲染图片，无法直接提取 URL，需要使用 WebView：

```json
{
  "ruleContent": {
    "content": "class.article-content@html",
    "webJs": "document.querySelector('canvas').toDataURL()"
  }
}
```
