# JS 扩展函数参考 — 字体解析（反反爬）

> 拆分自 js-extensions.md §七。Legado 书源 JS 环境中可调用的字体反反爬解析扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用，如 `java.queryTTF(data)`。

---

## 七、字体解析（反反爬）

### queryTTF(data) / queryTTF(data, useCache) — 获取字体解析类

```javascript
// 支持传入 URL、本地文件路径、Base64 字符串、ByteArray，自动判断
var font = java.queryTTF("https://example.com/font.ttf");
var font = java.queryTTF(base64FontData);
var font = java.queryTTF("https://example.com/font.ttf", false); // 禁用缓存
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data | Any? | 是 | URL / 本地路径 / Base64 / ByteArray |
| useCache | Boolean | 否 | 是否使用缓存，默认 true |

**使用频率**：中

---

### replaceFont(text, errorQueryTTF, correctQueryTTF) / replaceFont(text, errorQueryTTF, correctQueryTTF, filter) — 替换字体映射

```javascript
var correctFont = java.queryTTF("https://example.com/correct_font.ttf");
var errorFont = java.queryTTF("https://example.com/error_font.ttf");
var fixedText = java.replaceFont(garbledText, errorFont, correctFont);
var fixedText = java.replaceFont(garbledText, errorFont, correctFont, true); // filter=true 删除无轮廓字符
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | String | 是 | 包含错误字体的内容 |
| errorQueryTTF | QueryTTF? | 是 | 错误字体 |
| correctQueryTTF | QueryTTF? | 是 | 正确字体 |
| filter | Boolean | 否 | 删除错误字体中不存在的字符，默认 false |

**使用频率**：中

---

### queryBase64TTF(data) — @Deprecated

```javascript
// 已废弃，请使用 queryTTF(data) 替代
var font = java.queryBase64TTF(base64Data); // @Deprecated
```
