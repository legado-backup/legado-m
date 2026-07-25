# nextContentUrl分页模式

## 适用场景
正文分页（多页正文），一篇文章分布在多个页面，需通过"下一页"链接自动拼接完整内容。

## 修复源示例
- PO18
- 衍墨轩

## 代码片段
```json
{
  "ruleContent": {
    "content": "div.content@html",
    "nextContentUrl": "a.next-page@href",
    "replaceRegex": "##<div class=\"content\">|</div>##"
  }
}
```

## 注意事项
- 注意无限循环：必须设置最大页数限制，或确保最后一页的 nextContentUrl 选择器匹配为空
- nextContentUrl 提取的 URL 必须是绝对路径或可拼接的相对路径
- 配合 replaceRegex 去除每页重复的容器标签，避免拼接后 HTML 结构错乱
- 部分网站"下一页"按钮文字可能是图片或图标，需用属性选择器而非文本匹配
