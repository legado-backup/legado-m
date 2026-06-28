# og:novel meta+@put/@get模式

## 适用场景
详情页常规选择器失效，页面使用 `<meta property="og:novel:book_name">` 等 Open Graph 标签承载书籍元数据。需在 ruleBookInfo 中提取并跨阶段传递给 ruleToc/ruleContent 使用。

## 修复源示例
- 奇书塔
- 衍墨轩

## 代码片段
```json
{
  "ruleBookInfo": {
    "name": "@put:{novel:name}<js>result=String(result).replace(/,/g,\"，\")</js>meta[property=og:novel:book_name]@content",
    "author": "meta[property=og:novel:author]@content",
    "kind": "meta[property=og:novel:category]@content"
  },
  "ruleToc": {
    "chapterName": "tag.a@text",
    "chapterUrl": "tag.a@href"
  },
  "ruleContent": {
    "title": "@get:{novel:name}",
    "content": "class.content@text"
  }
}
```

## 注意事项
- @put/@get 用于跨阶段变量传递（ruleBookInfo → ruleToc → ruleContent）
- `String(result).replace(/,/g,"，")` 防止书名含半角逗号导致后续解析异常
- og:novel meta 标准字段：book_name/author/category/update_time/status/last_chapter
- 部分网站 og 标签可能缺失，需配合 fallback 选择器
