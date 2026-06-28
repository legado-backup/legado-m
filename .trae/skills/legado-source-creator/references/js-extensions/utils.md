# JS 扩展函数参考 — 工具方法

> 拆分自 js-extensions.md §九。Legado 书源 JS 环境中可调用的工具方法扩展函数。
> 引擎为 Rhino 1.8.1（ES5），禁止使用 ES6+ 语法。
> 在 JS 中通过 `java` 变量调用，如 `java.log(msg)`。

---

## 九、工具方法

### log(msg) — 输出调试日志

```javascript
var result = java.log("调试信息"); // 输出到调试日志，返回 msg 本身
java.logType(someVar);             // 输出对象类型
```

| 函数 | 签名 | 返回值 | 频率 |
|------|------|--------|------|
| log | `log(msg: Any?): Any?` | 返回 msg 本身 | 高 |
| logType | `logType(any: Any?)` | 无返回值 | 低 |

---

### timeFormat(time) — 时间格式化

```javascript
var formatted = java.timeFormat(1700000000000);
// 返回: String（使用 AppConst.dateFormat 格式化）
```

**使用频率**：中

---

### timeFormatUTC(time, format, sh) — UTC 时间格式化

```javascript
var formatted = java.timeFormatUTC(1700000000000, "yyyy-MM-dd HH:mm:ss", 8);
// 返回: String（UTC+8 格式化）
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| time | Long | 是 | 时间戳（毫秒） |
| format | String | 是 | 格式化模板 |
| sh | Int | 是 | 时区偏移（小时） |

**使用频率**：低

---

### randomUUID() — 生成 UUID

```javascript
var uuid = java.randomUUID();
// 返回: String（如 "550e8400-e29b-41d4-a716-446655440000"）
```

**使用频率**：中

---

### androidId() — 获取设备 Android ID

```javascript
var id = java.androidId();
// 返回: String
```

**使用频率**：低

---

### getWebViewUA() — 获取 WebView 默认 User-Agent

```javascript
var ua = java.getWebViewUA();
// 返回: String
```

**使用频率**：高

---

### htmlFormat(str) — HTML 格式化（保留图片）

```javascript
var clean = java.htmlFormat("<p>文本<br><img src='x.jpg'></p>");
// 返回: 格式化后的 HTML，保留 img 标签
```

**使用频率**：中

---

### t2s(text) / s2t(text) — 繁简转换

```javascript
var simplified = java.t2s("繁體字");   // 繁体转简体
var traditional = java.s2t("简体字");  // 简体转繁体
```

**使用频率**：中

---

### toNumChapter(s) — 章节数字转换

```javascript
var result = java.toNumChapter("第十二章 标题");
// 将中文数字转为阿拉伯数字
```

**使用频率**：低

---

### toURL(urlStr) / toURL(url, baseUrl) — 构造 URL 对象

```javascript
var urlObj = java.toURL("page.html", "https://example.com/");
// 返回: JsURL 对象
```

**使用频率**：低

---

### encodeURI(str) / encodeURI(str, enc) — URI 编码

> 详见加密与编码章节。

---

### getReadBookConfig() — 获取阅读配置

```javascript
var config = java.getReadBookConfig();
// 返回: String（JSON 格式的阅读配置）
```

**使用频率**：低

---

### getThemeMode() — 获取主题模式

```javascript
var mode = java.getThemeMode();
// 返回: String（"0" 跟随系统 / "1" 浅色 / "2" 深色）
```

**使用频率**：低

---

### getThemeConfig() — 获取主题配置

```javascript
var config = java.getThemeConfig();
// 返回: String（JSON 格式的主题配置）
```

**使用频率**：低
