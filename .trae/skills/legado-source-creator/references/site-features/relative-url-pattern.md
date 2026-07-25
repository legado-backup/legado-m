# 相对 URL 拼接模式

> 影响范围：3/7 真实源（51cg/acgfta/mjv006）

## 模式特征

RSS 源的 sortUrl 或文章列表 URL 为相对路径，需要用 bookSourceUrl 拼接为完整 URL。

## 典型场景

### 场景 1：sortUrl 为相对路径
```json
{
  "sourceUrl": "https://www.51cg.net",
  "ruleSortUrl": "/list/1.html::最新\n/list/2.html::热门"
}
```
**问题**：sortUrl 解析为 `/list/1.html`，未拼接 `https://www.51cg.net`

### 场景 2：文章 URL 为相对路径
```json
{
  "sourceUrl": "https://www.acgfta.com",
  "ruleArticles": "class.article-list@tag.a@href"
}
```
**问题**：提取的 href 为 `/article/123.html`，未拼接 baseUrl

## 修复方案

在 RssSourceDebugger.kt 的 debugSort 方法中，创建 AnalyzeUrl 前拼接：
```kotlin
if (!currentUrl.startsWith("http", ignoreCase = true) && mockSource.bookSourceUrl.isNotBlank()) {
    val base = mockSource.bookSourceUrl.trimEnd('/')
    currentUrl = when {
        currentUrl.startsWith("/") -> base + currentUrl
        else -> "$base/$currentUrl"
    }
}
```

## 验证结果

| 源 | 修复前 | 修复后 |
|----|--------|--------|
| 51cg | sort 失败 | ✅ sort→content 通过 |
| acgfta | sort 失败 | ✅ sort→content 通过 |
| mjv006 | sort 失败 | 🟡 URL 拼接成功，列表规则需优化 |
