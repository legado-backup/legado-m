# 源码分析沉淀索引

> 每次对 Legado 源码的深入分析结果，都必须沉淀到这个目录下。这是让 AI 对 Legado 源码和流程越来越了解的核心机制。

## 为什么需要这个目录？

1. **避免重复分析**：同一个源码文件不需要每次都重新读取分析
2. **知识积累**：每次源码分析的成果都沉淀下来，后续 AI 可以直接引用
3. **偏差修正**：当发现之前的分析结论与源码不符时，可以修正这个目录下的文档
4. **经验验证**：写入 troubleshooting/js-patterns 等文档的"经验"，必须先在这里经过源码验证

## 文档规范

- 每个文档必须标注**源码文件路径**和**行号范围**
- 每个结论必须标注**验证日期**
- 发现源码行为与已有文档不一致时，必须在此记录并修正对应文档
- 文档命名：`{模块名}.md`，如 `rss-source-entity.md`、`analyze-rule-engine.md`

## 文档列表

| 文档 | 分析内容 | 验证日期 |
|------|----------|----------|
| [rss-source-entity.md](rss-source-entity.md) | RssSource 实体字段定义 + RssParserByRule 解析流程 + RssArticle 实体 + searchUrl搜索流程 + loginCheckJs执行环境 | 2026-06-05 |
| [video-play-flow.md](video-play-flow.md) | type=2 视频播放完整链路：ReadRss → VideoPlayerActivity → VideoPlay → ExoPlayer；**R5 自动抓取（ruleContent为空时5种方法提取视频URL）+ 多线路多集按需采集（ruleRoutes/ruleEpisodes，v3.26.072420+）+ R1 多集解析（parseRssEpisodes）+ R3 抖音风格控件显隐（3秒自动隐藏+单击切换）** | 2026-07-24 |
| [rhino-security.md](rhino-security.md) | Rhino 环境安全限制：RhinoClassShutter 禁止类列表 + 可用 Java 类 + JS 绑定对象 | 2026-06-02 |
| [js-extensions-crypto.md](js-extensions-crypto.md) | JsExtensions/JsEncodeUtils 加密 API 完整清单 + 正确用法 + CryptoJS EVP_BytesToKey 差异 + **二进制内容解密流程（图片/视频）** + decrypt() vs decryptStr() + Base64 API选择 | 2026-06-09 |
| [default-syntax.md](default-syntax.md) | Default 语法完整行为：规则前缀解析 + 关键字前缀 + 索引语法 + 提取类型 + 选择器兼容性 | 2026-06-03 |
| [cf-bypass-source.md](cf-bypass-source.md) | CF 绕过源码分析：Cloudflare 检测机制 + 绕过策略 + WebView Cookie 同步 | 2026-06-06 |
| [ajax-diff-analysis.md](ajax-diff-analysis.md) | MockJsExtensions ajax() 差异分析：完整调用链 + 行为差异汇总（Cookie/Header/WebView等） | 2026-06-12 |
| [real-device-image-verification.md](real-device-image-verification.md) | 封面图真机显示验证方法论：content-desc 静态陷阱 + PIL 像素分析 + release R8 日志策略 + Glide 缓存清理要点 | 2026-08-02 |
