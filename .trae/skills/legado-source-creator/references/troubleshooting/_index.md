# 常见陷阱与故障排除 — 速查索引

> 本目录是 troubleshooting.md 的拆分版。按关键词定位子文档，避免读取全量内容。

## ⚠️ 创建新子文档前必须检查

1. 新内容是否可以归入已有子文档？→ 优先追加到已有子文档
2. 新内容与已有子文档的边界是否清晰？→ 如果重叠，应该扩展已有子文档的覆盖范围
3. 新子文档的预估内容是否 > 100行？→ 太小的内容不值得独立成文档
4. 创建后是否需要更新本索引的边界规则？→ 是则必须同步更新

## 速查表

### html-fetch-traps.md
> **一句话描述**：网站HTML获取失败的各种原因和解决方案

- ✅ 包含：WebFetch限制、curl失败、HTTP/2协议错误、CDN白名单拦截、SPA站点获取、手机UA策略
- ❌ 不包含：JS语法错误（→ rhino-js-traps.md）、加密解密失败（→ crypto-traps.md）
- **触发关键词**：WebFetch, curl, HTTP/2, CDN, 白名单, SPA, Vue, 获取HTML, 无法访问, 连接失败, 手机UA
- **自进化写入规则**：当发现新的网站获取方式或反爬绕过方法时追加

### crypto-traps.md
> **一句话描述**：加密/解密/编码在Legado JS环境中的常见陷阱

- ✅ 包含：CryptoJS不可用、ZeroPadding不支持、Base64兼容性、JS混淆分析
- ❌ 不包含：JS语法错误（→ rhino-js-traps.md）、加密认证方案设计（→ ../special-scenarios/encryption.md）
- **触发关键词**：CryptoJS, AES, DES, Base64, ZeroPadding, 加密, 解密, 混淆, sojson
- **自进化写入规则**：当发现新的加密/解密陷阱或编码兼容性问题时追加

### rhino-js-traps.md
> **一句话描述**：Rhino JS引擎的语法限制和兼容性陷阱

- ✅ 包含：ES6不可用、正则兼容性、byte数组、字符串转字节、内置方法优先、RSS @js result对象、广告排除、加密图片处理、**NativeJavaObject toString哈希（#79）**、**unwrapRhinoResult 6种类型解包**
- ❌ 不包含：源类型选择问题（→ source-type-traps.md）、JS技巧模式（→ ../js-patterns/）
- **触发关键词**：Rhino, ES6, let, const, 箭头函数, 正则, byte, 字节, result, Element, 广告排除, NativeJavaObject, unwrap, 仿真器哈希
- **自进化写入规则**：当发现新的Rhino语法限制或JS兼容性问题时追加

### source-type-traps.md
> **一句话描述**：书源/订阅源类型选择和配置字段导致的运行时错误

- ✅ 包含：RssSource搜索、type字段选择、视频源、loginCheckJs NPE、webView强制加载、搜索功能配置
- ❌ 不包含：JS语法错误（→ rhino-js-traps.md）、网站分析流程（→ analysis-best-practices.md）
- **触发关键词**：type, loginCheckJs, NPE, StrResponse, webView, enableJs, 搜索, searchUrl, RssSource, BookSource
- **自进化写入规则**：当发现新的源类型配置陷阱或运行时错误时追加

### analysis-best-practices.md
> **一句话描述**：分析网站结构和编写规则的最佳实践流程

- ✅ 包含：分析顺序、字段完善清单、curl提取技巧、年龄确认处理、加密验证
- ❌ 不包含：具体修复案例（→ community-fix-experience.md）、源类型选择（→ source-type-traps.md）
- **触发关键词**：分析, curl, 字段完善, sourceIcon, sourceComment, ruleNextPage, rulePubDate, 年龄确认
- **自进化写入规则**：当总结出新的网站分析技巧或字段配置经验时追加

### community-fix-experience.md
> **一句话描述**：社区源实际修复案例和经验记录

- ✅ 包含：动态验证问题、深度链路问题、403修复模式、实际修复经验、反爬深度分析、E类JS源、B类CSS源、订阅源修复、missing规则修复
- ❌ 不包含：通用分析流程（→ analysis-best-practices.md）、源类型配置陷阱（→ source-type-traps.md）、WebSocket调试问题（→ ../special-scenarios/websocket-debug.md）
- **触发关键词**：修复, 403, CSS选择器, JSON路径, Cookie, 反爬, JS源, 验证, missing, 缺失规则
- **自进化写入规则**：当完成新的源修复案例或发现新的问题分类时追加

### WebSocket/真机调试排查

> 以下问题不属于 troubleshooting 子文档，归入 special-scenarios/websocket-debug.md，此处仅作交叉引用：

| 问题 | 排查方向 | 详见 |
|------|---------|------|
| WebSocket 连接失败/无响应 | WS 端口 1123 不响应 HTTP，需用 WS 协议连接 | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱1 |
| searchBook 全源搜索极慢 | 搜索全部书源（2.4万+），分钟级耗时 | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱2 |
| 真机调试日志无法解析 | 纯文本格式，无 type/state 字段，需关键词匹配 | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱3 |
| Android 模拟器 DNS 解析失败 | 模拟器 DNS 与 PC 不同，UnknownHostException | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱4 |
| getBookSources 超时 | 返回全部源 JSON 50-100MB，需 120s+ timeout | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱5 |
