# 编码处理完整指南

> 书源开发中常见的编码问题及解决方案，涵盖编码判断、charset 参数、URL 编码、繁简转换等。
> 所有内容已通过 Legado 源码确认。

---

## 1. 编码判断三步法

遇到乱码时，按以下顺序排查编码问题。

### 第一步：检查 HTTP 响应头

```
Content-Type: text/html; charset=gbk
```

- HTTP 响应头中的 `charset` 是最权威的编码声明
- OkHttp 会根据此值解码响应体
- 如果 Legado 未正确识别，需手动指定

### 第二步：检查 HTML meta 标签

```html
<meta charset="gbk">
<!-- 或 -->
<meta http-equiv="Content-Type" content="text/html; charset=gbk">
```

- 部分网站 HTTP 头不声明 charset，但在 HTML 中声明
- Legado 的 EncodingDetect.kt L18-50 会检测 meta 标签

### 第三步：根据乱码特征判断

| 乱码特征 | 实际编码 | 说明 |
|----------|----------|------|
| `ÎÒ°®ãá` | GBK | UTF-8 解码 GBK 内容 |
| `ÿþ` 开头 | UTF-16 LE | BOM 头标识 |
| `þÿ` 开头 | UTF-16 BE | BOM 头标识 |
| `ï»¿` 开头 | UTF-8 BOM | BOM 头标识 |
| 中文显示为 `问号` 或 `方块` | 缺少字体 | 非编码问题 |

---

## 2. charset 参数位置规则

### 正确写法：在 JSON 对象中

```
/search.php,{"charset":"gbk"}
```

- 逗号分隔 URL 和 JSON 参数对象
- `charset` 是 JSON 对象的键，值为编码名称
- Legado 的 AnalyzeUrl.kt 会解析此 JSON 对象

### 错误写法：作为 URL 参数

```
/search.php?charset=gbk
```

- 这是向服务端传递参数，不是告诉 Legado 用什么编码
- 服务端通常不处理此参数
- 仍然会出现乱码

### 完整示例

```json
{
  "searchUrl": "/search.php?searchkey={{key}},{\"charset\":\"gbk\",\"method\":\"POST\"}"
}
```

- `charset` 和 `method` 等参数都在同一个 JSON 对象中
- JSON 对象整体作为 URL 的第二部分

---

## 3. java.encodeURI() 使用

搜索关键词含中文时，需要正确编码才能放入 URL。

### 基本用法

```javascript
java.encodeURI(key, 'GBK')
```

> **源码确认**：JsExtensions.kt L657/L666，`encodeURI()` 方法支持指定编码进行 URL 编码。

### 在搜索 URL 中使用

```
/search.php?keyword={{java.encodeURI(key,'GBK')}}
```

### 与 charset 配合

```
/search.php?keyword={{java.encodeURI(key,'GBK')}},{"charset":"gbk"}
```

- 请求时用 GBK 编码关键词
- 响应时用 GBK 解码内容

**适用场景**：GBK/Big5 网站的搜索关键词编码、URL 中包含中文。

---

## 4. java.s2t() / java.t2s() 繁简转换

### 简体转繁体

```javascript
key = java.s2t(key);
```

> **源码确认**：JsExtensions.kt L685，`s2t()` 方法调用 `ChineseUtils.s2t()` 实现简体转繁体。

### 繁体转简体

```javascript
key = java.t2s(key);
```

> **源码确认**：JsExtensions.kt L680，`t2s()` 方法调用 `ChineseUtils.t2s()` 实现繁体转简体。

### 实际应用

```
/search?key={{java.s2t(key)}},{"charset":"big5"}
```

- 搜索台湾/香港网站时，关键词需转为繁体
- 配合 `charset: big5` 处理 Big5 编码的响应

### 正文繁简转换

```javascript
// 在正文规则中将繁体内容转为简体
result = java.t2s(result);
```

**适用场景**：繁体网站搜索、正文繁简转换、标题繁简转换。

---

## 5. GBK 兼容性说明

### GBK 是 GB2312 的超集

| 编码 | 字符数 | 说明 |
|------|--------|------|
| GB2312 | 6,763 汉字 | 基本简体中文 |
| GBK | 21,886 汉字 | GB2312 超集，含繁体字 |
| GB18030 | 70,244 汉字 | GBK 超集，含少数民族文字 |

### 实际建议

- **遇到 GB2312 网站**：指定 `"charset":"gbk"`，GBK 完全兼容 GB2312
- **遇到 GBK 网站**：指定 `"charset":"gbk"`
- **遇到 GB18030 网站**：指定 `"charset":"gbk"` 通常也够用，因为常用汉字都在 GBK 范围内

### 为什么不直接用 GB18030

- Legado 内部使用 Java 的 `Charset.forName()` 解码
- Java 的 GBK 解码器覆盖了绝大多数中文网站的需求
- 只有极少数含生僻字或少数民族文字的网站才需要 GB18030
- 如果确实需要，可以指定 `"charset":"gb18030"`

**适用场景**：中文网站编码选择、乱码修复、编码兼容性判断。
