# Default 语法源码确认结果

> 基于 Legado 源码分析，确认 Default 模式（无前缀 / `@@` 前缀）的完整语法行为。
> 验证日期：2026-06-03

## 规则前缀解析（AnalyzeRule.kt L600-634）

| 前缀 | 解析模式 | 行为 |
|------|----------|------|
| `@CSS:` | Mode.Default | 保留完整字符串（`@CSS:` 前缀由 AnalyzeByJSoup 内部剥离） |
| `@@` | Mode.Default | 剥离 `@@` 前缀后作为 Default 规则处理 |
| `@XPath:` | Mode.XPath | 切换到 XPath 解析 |
| `@Json:` | Mode.Json | 切换到 JSONPath 解析 |
| `@js:` / `<js></js>` | JS 模式 | 通过正则匹配（AppPattern.kt L7-10），在 `splitSourceRule()` 方法中识别（AnalyzeRule.kt L545-555），不在 SourceRule.init 块中 |
| 无前缀 | Mode.Default | 默认走 Default 解析 |

**关键说明**：`@CSS:` 前缀在 AnalyzeRule 中被保留不剥离，传入 AnalyzeByJSoup 后由其内部处理。AnalyzeRule.SourceRule 保留完整字符串。源码依据：AnalyzeRule.kt L601-631。

---

## Default 语法关键字前缀（AnalyzeByJSoup.kt L310-321）

| 前缀 | 解析方法 | 等价 CSS | 源码行号 |
|------|---------|---------|----------|
| `class.名称` | `getElementsByClass("名称")` | `.名称` | L311-313 |
| `tag.名称` | `getElementsByTag("名称")` | `名称` | L314-316 |
| `id.名称` | `Collector.collect(Evaluator.Id("名称"))` | `#名称` | L317-319 |
| `text.文本` | `getElementsContainingOwnText("文本")` | `:containsOwn(文本)` | L320 |
| `children` | `temp.children()` | `> *` | L321 |
| 其他 | `temp.select(beforeRule)` | CSS 选择器兜底 | L322+ |

**说明**：Default 语法先检查是否匹配上述关键字前缀，不匹配则通过 `temp.select()` 作为标准 CSS 选择器执行。因此 Default 语法兼容所有 CSS 选择器。

---

## 索引语法

### 旧式索引（AnalyzeByJSoup.kt L482-506）

- `.0` — 取第 0 个元素
- `.1` — 取第 1 个元素
- `.-1` — 取倒数第 1 个元素

### 新式索引（AnalyzeByJSoup.kt L418-481）

| 语法 | 含义 | 示例 |
|------|------|------|
| `[0:10]` | 取索引 0 到 9（不含 10） | 前 10 个元素 |
| `[-1:0]` | 从倒数第 1 个到开头（逆序） | 倒序所有元素 |
| `[!0:-1]` | 排除第 0 个，取到倒数第 1 个 | 跳过首个元素 |

### 排除语法

- `!0` — 排除第 0 个元素
- 排除语法在新式索引和旧式索引中**均可用**（源码：AnalyzeByJSoup.kt L491 处理旧式索引中的 `!` 分隔符）

---

## 提取类型

| 提取后缀 | 含义 | 源码依据 |
|----------|------|----------|
| `@text` | `element.text()` — 含子元素文本 | AnalyzeByJSoup.kt |
| `@ownText` | `element.ownText()` — 仅自身直接文本 | AnalyzeByJSoup.kt |
| `@textNodes` | `element.textNodes()` — 直接文本节点，过滤空白，换行连接 | AnalyzeByJSoup.kt L239-251 |
| `@html` | `element.html()` | AnalyzeByJSoup.kt |
| `@属性名` | `element.attr("属性名")` | AnalyzeByJSoup.kt |

**`@text` vs `@ownText` vs `@textNodes` 区别**：
- `@text`：返回元素及其所有子元素的文本内容（递归拼接）
- `@ownText`：仅返回元素自身的直接文本，不含子元素文本
- `@textNodes`：返回直接文本节点列表，过滤纯空白节点，用换行符连接。适合提取混合标签中的多段文本

---

## 选择器兼容性

| 选择器 | Default 模式 | `@CSS:` 模式 | 说明 |
|--------|-------------|-------------|------|
| `:first-child` | ✅ | ✅ | 标准 CSS 伪类 |
| `:last-child` | ✅ | ✅ | 标准 CSS 伪类 |
| `:nth-child()` | ✅ | ✅ | 标准 CSS 伪类 |
| `:contains()` | ✅ | ✅ | jsoup 扩展伪类 |
| `class.名称` | ✅ | ❌ | Default 语法糖，`@CSS:` 下用 `.名称` |
| `tag.名称` | ✅ | ❌ | Default 语法糖，`@CSS:` 下用 `名称` |
| `id.名称` | ✅ | ❌ | Default 语法糖，`@CSS:` 下用 `#名称` |
| `text.文本` | ✅ | ❌ | Default 语法糖，`@CSS:` 下用 `:containsOwn(文本)` |
| `children` | ✅ | ❌ | Default 语法糖，`@CSS:` 下用 `> *` |

**关键结论**：Default 语法通过 `temp.select()` 兜底，支持所有 CSS 选择器。`@CSS:` 模式同样走 jsoup 的 `select()`，但不识别 Default 语法糖。

---

## 已知限制

- **纯 `[` 开头的 CSS 属性选择器**作为首段规则时，可能被索引解析器误读为新式索引语法 `[0:10]`，导致解析错误。建议在属性选择器前添加元素限定，如用 `div[data-xx]` 替代 `[data-xx]`
- **CSS 伪类选择器中的 `:` 与 Default 语法索引分隔符冲突**（源码依据：AnalyzeByJSoup.kt L491）。Default 语法逆向遍历规则字符串时，将 `:` 视为索引分隔符（与 `.` 和 `!` 同级），导致含 `:has()`、`:not()`、`:first-child` 等伪类选择器的规则被错误解析。**必须使用 `@CSS:` 前缀**来避免此冲突，例如：`@CSS:article:has(h2.title)` 而非 `article:has(h2.title)`。注意：`ruleArticles`（getElements）和 `ruleXxx`（getString）均受此影响
