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

- ✅ 包含：WebFetch限制、curl失败、HTTP/2协议错误、CDN白名单拦截、SPA站点获取、手机UA策略、**Accept-Encoding乱码（§1.1h）**
- ❌ 不包含：JS语法错误（→ rhino-js-traps.md）、加密解密失败（→ crypto-traps.md）
- **触发关键词**：WebFetch, curl, HTTP/2, CDN, 白名单, SPA, Vue, 获取HTML, 无法访问, 连接失败, 手机UA, Accept-Encoding, 乱码, brotli, gzip
- **自进化写入规则**：当发现新的网站获取方式或反爬绕过方法时追加

### crypto-traps.md
> **一句话描述**：加密/解密/编码在Legado JS环境中的常见陷阱

- ✅ 包含：CryptoJS不可用、ZeroPadding不支持、Base64兼容性、JS混淆分析
- ❌ 不包含：JS语法错误（→ rhino-js-traps.md）、加密认证方案设计（→ ../special-scenarios/encryption.md）
- **触发关键词**：CryptoJS, AES, DES, Base64, ZeroPadding, 加密, 解密, 混淆, sojson
- **自进化写入规则**：当发现新的加密/解密陷阱或编码兼容性问题时追加

### rhino-js-traps.md
> **一句话描述**：Rhino JS引擎的语法限制和兼容性陷阱

- ✅ 包含：ES6不可用、正则兼容性、byte数组、字符串转字节、内置方法优先、RSS @js result对象、广告排除、加密图片处理、**NativeJavaObject toString哈希（#79）**、**unwrapRhinoResult 6种类型解包**、**Rhino类型转换陷阱（java.ajax返回Java String，陷阱55）**、**player_data JSON提取平衡括号算法（陷阱56）**、**协程IO线程死锁陷阱（陷阱58，含java.ajax()的JS不能在Dispatchers.IO执行）**
- ❌ 不包含：源类型选择问题（→ source-type-traps.md）、JS技巧模式（→ ../js-patterns/）、视频源URL转换/嗅探（→ video-source-traps.md）、动态域名解析（→ dynamic-domain-traps.md）
- **触发关键词**：Rhino, ES6, let, const, 箭头函数, 正则, byte, 字节, result, Element, 广告排除, NativeJavaObject, unwrap, 仿真器哈希, Java String, 类型转换, 平衡括号, player_data, JSON提取, charAt, length, 协程, 死锁, Dispatchers.IO, ajax死锁, 线程执行器, Executors, 返回的值无效, msg.bad.return, 顶层return, IIFE, String.replace, 选择不明确, split-join
- **自进化写入规则**：当发现新的Rhino语法限制或JS兼容性问题时追加

### source-type-traps.md
> **一句话描述**：书源/订阅源类型选择和配置字段导致的运行时错误

- ✅ 包含：RssSource搜索、type字段选择、视频源、loginCheckJs NPE、webView强制加载、搜索功能配置、**shouldOverrideUrlLoading变量绑定（#4.9）**、**Accept-Encoding乱码（#4.10）**、**CookieStore覆盖header（#4.11）**
- ❌ 不包含：JS语法错误（→ rhino-js-traps.md）、网站分析流程（→ analysis-best-practices.md）
- **触发关键词**：type, loginCheckJs, NPE, StrResponse, webView, enableJs, 搜索, searchUrl, RssSource, BookSource, shouldOverrideUrlLoading, Accept-Encoding, CookieStore覆盖, 时好时不好
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

### video-source-traps.md
> **一句话描述**：视频订阅源（type=2）特有陷阱，含URL转换/嗅探/播放页链路/导入验证/MacCMS解析

- ✅ 包含：`##`字符串替换操作符（陷阱40）、ruleContent为空嗅探模式（陷阱41）、播放页链路验证（陷阱42）、导入源后字段验证（陷阱43）、视频播放URL转换完整链路（陷阱49）
- ❌ 不包含：JS语法错误（→ rhino-js-traps.md）、动态域名解析（→ dynamic-domain-traps.md）、源类型配置陷阱（→ source-type-traps.md）
- **触发关键词**：视频源, type=2, ##, URL转换, 嗅探, ruleContent为空, 播放页, 列表链接, 详情页, 导入验证, DELETE+INSERT, WAL, MacCMS, player_data, m3u8, ExoPlayer
- **自进化写入规则**：当发现新的视频订阅源特有陷阱或播放页解析问题时追加

### dynamic-domain-traps.md
> **一句话描述**：动态域名站点（入口域名固定但实际内容域名动态变化）的陷阱和解决方案

- ✅ 包含：Rhino ES5兼容性（陷阱44）、searchUrl支持`<js>`标签（陷阱45）、多分类搜索实现（陷阱46）、ruleArticles JS影响列表页（陷阱47）、导入脚本DELETE条件（陷阱48）、入口域名+meta refresh跳转（陷阱50）、punycode域名含日期+随机数字（陷阱51）、sortUrl JS动态域名模板（陷阱52）、searchUrl和sortUrl共用cache key（陷阱53）、Phase 3真机验证三步流程（陷阱54）、seededRandom动态域名解析（陷阱57）
- ❌ 不包含：JS语法错误细节（→ rhino-js-traps.md）、视频源URL转换/嗅探（→ video-source-traps.md）、通用网站获取失败（→ html-fetch-traps.md）
- **触发关键词**：动态域名, meta refresh, punycode, seededRandom, sortUrl, searchUrl, cache key, 多分类搜索, ruleArticles, 导入脚本, sourceName, 真机验证, ExoPlayer, 跨日域名, 刷新分类
- **自进化写入规则**：当发现新的动态域名解析模式或域名跳转陷阱时追加

### WebSocket/真机调试排查

> 以下问题不属于 troubleshooting 子文档，归入 special-scenarios/websocket-debug.md，此处仅作交叉引用：

| 问题 | 排查方向 | 详见 |
|------|---------|------|
| WebSocket 连接失败/无响应 | WS 端口 1123 不响应 HTTP，需用 WS 协议连接 | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱1 |
| searchBook 全源搜索极慢 | 搜索全部书源（2.4万+），分钟级耗时 | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱2 |
| 真机调试日志无法解析 | 纯文本格式，无 type/state 字段，需关键词匹配 | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱3 |
| Android 模拟器 DNS 解析失败 | 模拟器 DNS 与 PC 不同，UnknownHostException | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱4 |
| getBookSources 超时 | 返回全部源 JSON 50-100MB，需 120s+ timeout | [websocket-debug.md](../special-scenarios/websocket-debug.md) 陷阱5 |
