# 5种解析方式选择决策树

> 给定网站分析结果，决定使用哪种（或哪几种组合）解析方式。
> 语法细节参见 [../rule-syntax.md](../rule-syntax.md)，网站特征映射参见 [../site-features/site-feature-to-rule-type.md](../site-features/site-feature-to-rule-type.md)。

## 一、决策流程图

```
输入：网站分析结果
  is_api          : 响应是否为 JSON API
  has_encryption  : 是否存在加密/签名
  is_dynamic      : 是否需要 JS 渲染才能获取内容
  html_complexity : HTML 复杂度 (low/medium/high)
  is_text_only    : 是否纯文本内容（无富媒体）

┌─ is_api == true ?
│   ├─ YES → 主解析方式 = JSONPath
│   │        └─ has_encryption == true ? → 组合 JS（先解密再解析）
│   └─ NO ↓
│
├─ is_dynamic == true ?
│   ├─ YES → 主解析方式 = WebView JS (@webjs:)
│   │        └─ 内容在渲染后 DOM 中 → 组合 CSS 提取
│   └─ NO ↓
│
├─ html_complexity == low ?
│   ├─ YES → 主解析方式 = CSS（Default 简写）
│   └─ NO ↓
│
├─ html_complexity == high ?
│   ├─ YES → 主解析方式 = XPath（层级穿透能力强）
│   │        或 CSS + 正则（先提取再清洗）
│   └─ NO ↓
│
└─ 默认 → 主解析方式 = CSS（最稳定，jsoup 引擎）
         └─ is_text_only == true ? → 可加正则清洗广告
```

## 二、每种解析方式适用场景和限制

| 解析方式 | 适用场景 | 限制 | 引擎 |
|----------|----------|------|------|
| **CSS（Default）** | 静态 HTML、结构固定、传统小说站 | 不支持复杂层级过滤、无算术运算 | jsoup 1.16.2 |
| **JSONPath** | REST API、JSON 响应、现代视频/图片站 | 仅适用于 JSON 数据，HTML 无效 | json-path |
| **XPath** | 复杂 HTML 层级、需条件过滤（position()>1） | 性能略低于 CSS、语法较复杂 | JsoupXpath |
| **正则** | 文本清洗、提取片段（数字/URL）、广告去除 | 不适合结构化解析、易误匹配 | Java Regex |
| **JS（@js:/`<js>`）** | 加密解密、动态计算、跨规则传值、复杂逻辑 | Rhino 1.8.1 仅 ES5、无 DOM | Rhino |
| **WebView JS（@webjs:）** | 需 JS 渲染、视频嗅探、动态加载 | 性能慢、需启动 WebView、代码≥5字符 | Android WebView |

## 三、组合使用场景

| 组合 | 场景 | 示例写法 |
|------|------|----------|
| **CSS + 正则** | 提取 HTML 后清洗广告/提取数字 | `div.content@html##<script[\\s\\S]*?</script>` |
| **CSS + JS** | 提取后需二次处理（拼接、解密） | `div.token@text<js>java.decrypt(result)</js>` |
| **JSONPath + JS** | API 响应需解密后再解析 | `$.data<js>JSON.parse(java.decrypt(result))</js>` |
| **JS + CSS** | JS 解密后返回 HTML，再用 CSS 提取 | `<js>java.decrypt(result)</js>div.content@html` |
| **`||` 多规则回退** | 页面结构不固定，多种选择器尝试 | `span.author@text\|\|p.author@text\|\|div.writer@text` |
| **`&&` 合并去重** | 信息分散在多处需合并 | `div.intro@text&&div.summary@text` |
| **`%%` 交错合并** | 书名和 URL 配对提取 | `div.item a@text%%div.item a@href` |

> 组合符 `&&`/`||`/`%%` 详见 [../rule-syntax.md](../rule-syntax.md) 第六节。

## 四、决策表示例

| 输入特征 | 输出主解析方式 | 组合 | 说明 |
|----------|---------------|------|------|
| is_api=true, has_encryption=false | JSONPath | — | 标准 REST API |
| is_api=true, has_encryption=true | JSONPath | + JS | 先 JS 解密，再 JSONPath 解析 |
| is_api=false, is_dynamic=false, html_complexity=low | CSS | — | 传统小说站 |
| is_api=false, is_dynamic=false, html_complexity=high | XPath | 或 CSS+正则 | 复杂嵌套 HTML |
| is_api=false, is_dynamic=true | WebView JS | + CSS | JS 渲染后用 CSS 提取 |
| is_api=false, is_dynamic=true, is_text_only=true | WebView JS | + 正则 | 渲染后正则清洗 |
| is_api=false, has_encryption=true, is_dynamic=false | CSS | + JS | HTML 中加密内容需 JS 解密 |

## 五、选择优先级（冲突时）

1. **能 JSONPath 不用 CSS**：API 响应比 HTML 更稳定高效
2. **能 CSS 不用 XPath**：jsoup 性能优于 JsoupXpath，且语法更简洁
3. **能 CSS/JSONPath 不用 JS**：原生解析比 Rhino 执行快且不易出错
4. **能 JS 不用 WebView JS**：Rhino 比 WebView 启动快得多
5. **正则只做清洗不做提取**：正则用于 `##` 后处理，不作为主解析方式
