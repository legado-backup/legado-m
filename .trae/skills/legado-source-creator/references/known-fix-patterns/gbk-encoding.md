# GBK编码模式

## 适用场景
GBK 编码网站的搜索关键词传输，OkHttp 默认 UTF-8 编码会导致关键词乱码。

## 修复源示例
- PO18

## 代码片段
```json
{
  "searchUrl": "https://www.po18.tw/search?q={{key}},{\"charset\":\"GBK\"}"
}
```

或通过 JS 编码：
```json
{
  "searchUrl": "<js>\nvar kw = java.encodeURI(java.urlEncode(String(result), 'GBK'));\n'https://www.po18.tw/search?q=' + kw;\n</js>"
}
```

## 注意事项
- OkHttp 默认 UTF-8，GBK 网站需在 UrlOption 中指定 `charset` 参数
- `java.urlEncode(str, charset)` 可手动指定编码，避免依赖框架默认行为
- GBK 编码下中文关键词占 2 字节，URL 编码后长度翻倍，注意 URL 长度限制
- 部分网站搜索结果页也是 GBK 编码，Legado 会自动检测响应编码，通常无需额外处理
