# 搜索方法转换模式

## 适用场景
GET 搜索返回空结果或报错，需改为 POST 方法或调整 URL 参数格式。

## 修复源示例
- PO18

## 代码片段
```json
{
  "searchUrl": "https://www.po18.tw/search,{\"method\":\"POST\",\"body\":\"keyword={{key}}\",\"headers\":{\"Content-Type\":\"application/x-www-form-urlencoded\"}}"
}
```

## 注意事项
- OkHttp 自动编码 body 参数，但某些场景需手动处理特殊字符
- POST body 中 `{{key}}` 会被替换为搜索关键词，需确保编码正确
- Content-Type 必须与网站实际请求一致，否则后端可能拒绝
- 部分 POST 搜索需携带 Cookie 或 Referer，在 headers 中配置
- 如果 GET 搜索因参数顺序问题失败，尝试调整 URL 中参数顺序而非直接改 POST
