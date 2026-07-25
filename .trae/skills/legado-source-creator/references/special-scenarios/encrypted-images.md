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

**AES-CBC 解密封面**：

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
