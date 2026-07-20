# Cookie 管理链路修复

> 修复 Legado Cookie 管理中"登录获取 Cookie 时好时不好"的根因问题

## 状态

✅ 设计完成

## 核心问题

订阅源/书源用户登录后获取的 Cookie，在后续 OkHttp 请求中"时好时不好"——有时正常携带，有时丢失。根因是 Cookie 在 WebView ↔ CookieStore ↔ OkHttp 三方之间的同步链路存在断裂。

## 关键发现

| # | 问题 | 优先级 | 影响 |
|---|------|--------|------|
| P0 | ReadRssActivity WebView Cookie 不回写 CookieStore | 最高 | 用户登录后 Cookie 丢失 |
| P1 | CookieStore 无过期清理机制 | 高 | 过期 Cookie 覆盖正确值 |
| P2 | applyToWebView() 全局清空会话 Cookie | 高 | 多源切换时互相清除 |
| P3 | AnalyzeUrl.saveCookie() 死代码 | 中 | 潜在功能缺失 |
| P4 | BackstageWebView 用 source.getKey() 而非请求 URL 域名 | 中 | Cookie 域名不匹配 |
| P5 | mergeCookiesToMap() 合并顺序不一致 | 低 | 理论上可能覆盖异常 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 需求文档：Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | 技术方案：Architecture Decisions/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单：分阶段实施计划 |

## 关联文档

- [rss-age-verify-autobypass](../rss-age-verify-autobypass/README.md) — 订阅源年龄验证自动破除（触发本次分析的上游任务）
