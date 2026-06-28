# 反爬/Cloudflare 处理

> 反爬处理概览入口。详细 CF 绕过方案见 [cf-bypass.md](./cf-bypass.md)。

## 常见反爬类型

| 反爬类型 | 特征 | 绕过方案 |
|---------|------|---------|
| Cloudflare JS Challenge | 页面显示 "Just a moment..." | `webView:true` 自动通过 → 详见 [cf-bypass.md](./cf-bypass.md) |
| Cloudflare Turnstile | 需要用户交互（点击/滑块） | `java.startBrowserAwait()` 弹浏览器 → 详见 [cf-bypass.md](./cf-bypass.md) |
| Headers 验证 | 403/401 错误 | 伪装 User-Agent/Referer |
| Cookie 预置 | 需要特定 Cookie | `java.setCookie()` 预置 cf_clearance |
| PJAX 空壳 HTML | 获取的 HTML 无内容 | `webView:true` 获取渲染后内容 |

## WebView 绕过

```json
{
  "searchUrl": "/search?q={{key}},{\"webView\":true,\"webJs\":\"document.body.innerHTML\"}"
}
```

## Headers 伪装

```json
{
  "header": "{\"User-Agent\":\"Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36\",\"Referer\":\"https://www.example.com/\"}"
}
```

## Cookie 预置

```javascript
// 在 init 中
java.setCookie(source.getKey(), 'cf_clearance=xxx');
```

## 相关文档

- **CF 绕过完整方案**：[cf-bypass.md](./cf-bypass.md)（三种 CF 类型 + Cookie 机制 + 配置模板）
- 获取失败诊断：[troubleshooting/html-fetch-traps.md](../troubleshooting/html-fetch-traps.md)
- CF 标准修复配置：[troubleshooting/source-type-traps.md](../troubleshooting/source-type-traps.md)
