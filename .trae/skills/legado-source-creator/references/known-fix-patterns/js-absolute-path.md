# JS补全绝对路径模式

## 适用场景
Web Components自定义元素（如 `<a href="/book/123">`）的 href 属性返回相对路径，导致 Legado 解析出的 URL 无法直接访问，需要在 JS 规则中补全为绝对路径。

## 修复源示例
- 奇书塔
- 中国古典
- 衍墨轩

## 代码片段
```json
{
  "ruleBookInfo": {
    "intro": "class.book-info@text"
  },
  "ruleToc": {
    "chapterList": "class.chapter-item",
    "chapterName": "tag.a@text",
    "chapterUrl": "tag.a@href<js>result.indexOf('http')===0?result:'https://www.qishuta.com'+result</js>"
  }
}
```

## 注意事项
- 注意：JS 中拼接 baseUrl 仍需手动处理
- 域名需硬编码在 JS 中，网站换域名时需同步更新
- `result.indexOf('http')===0` 判断比 `result.startsWith('http')` 更兼容（Rhino ES5）
- 若网站协议不一致（http/https混用），建议统一拼接为 https
