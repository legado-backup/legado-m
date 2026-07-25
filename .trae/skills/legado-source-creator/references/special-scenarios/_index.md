# 特殊场景处理指南 — 子文档索引

> ⚠️ **创建新子文档前必须检查**：
> 1. 新主题是否与已有子文档重叠？重叠部分应追加到已有文档，而非新建
> 2. 新文档是否需要在已有文档的 ✅/❌ 包含关系中更新引用？
> 3. 新文档的触发关键词是否与已有文档冲突？冲突时合并或调整关键词
> 4. 新文档创建后，必须在本索引中添加条目，并同步更新相关文档的 ❌ 指向

---

## login.md — 登录处理

- **一句话描述**：标准登录流程（loginUrl/loginUi/loginCheckJs）、Cookie 登录（enabledCookieJar）、详情页初始化 JS（init 字段）
- ✅ 包含：loginUrl、loginUi、loginCheckJs、enabledCookieJar、Cookie 持久化、BookInfoRule.init
- ❌ 不包含：验证码 → [captcha.md](./captcha.md)；加密密码 → [encryption.md](./encryption.md)；Cookie 预置反爬 → [anti-crawl.md](./anti-crawl.md)
- **触发关键词**：登录、login、loginUrl、loginUi、loginCheckJs、Cookie登录、init字段、enabledCookieJar

---

## captcha.md — 验证码处理

- **一句话描述**：图片验证码（getVerificationCode）、滑块/行为验证码（startBrowserAwait）、验证码后 Token 传递
- ✅ 包含：getVerificationCode()、startBrowserAwait()、验证码+Token 组合流程
- ❌ 不包含：登录表单配置 → [login.md](./login.md)；加密签名 → [encryption.md](./encryption.md)
- **触发关键词**：验证码、captcha、getVerificationCode、滑块验证、行为验证、startBrowserAwait、Token传递

---

## encryption.md — 加密认证

- **一句话描述**：MD5/SHA 密码加密、动态签名/Token 生成、AES/DES 对称加密（createSymmetricCrypto）、搜索参数加密实战案例及 API 速查
- ✅ 包含：java.md5Encode、java.base64Encode、java.createSymmetricCrypto()、AES/CBC/ECB、DES/3DES、搜索参数加密实战、API 速查表、Rhino 陷阱避坑
- ❌ 不包含：加密图片解密 → [encrypted-images.md](./encrypted-images.md)；Cookie 登录 → [login.md](./login.md)；反爬 Headers → [anti-crawl.md](./anti-crawl.md)
- **触发关键词**：加密、AES、DES、MD5、SHA、签名、Token、createSymmetricCrypto、encryptBase64、decryptStr、搜索参数加密、ZeroPadding、PKCS5Padding、Rhino陷阱

---

## encrypted-images.md — 加密图片处理

- **一句话描述**：封面图片解密（coverDecodeJs）、正文图片解密/替换（replaceRegex）、图片代理（imageStyle）
- ✅ 包含：coverDecodeJs、java.imageDecode、replaceRegex 图片解密、imageStyle（FULL/WIDE/CENTER/CUSTOM）
- ❌ 不包含：AES/DES 通用加密 → [encryption.md](./encryption.md)；视频地址提取 → [video-audio.md](./video-audio.md)
- **触发关键词**：加密图片、coverDecodeJs、imageDecode、图片解密、图片代理、imageStyle、replaceRegex图片

---

## video-audio.md — 视频/音频地址获取

- **一句话描述**：视频播放地址提取（WebView+JS/嗅探）、**type=2 内置播放器内容规则编写指南（5.6节）**、内置播放器调用、m3u8/HLS 流处理、音频地址获取（bookSourceType=1）、**内置播放器404防盗链修复（5.6节常见问题）**
- ✅ 包含：webView+webJs 提取视频、嗅探网络请求、openVideoPlayer、m3u8/HLS、ExoPlayer、audio@src、bookSourceType=1、**type=2 内置播放器 ruleContent 四种格式（单URL/多行URL/JSON数组/嵌套JSON多线路）、R5 自动抓取、多集/多线路解析、404防盗链Header注入、singleUrl不注入Referer、自定义Headers配置**
- ❌ 不包含：HLS.js 播放器 HTML 模板 → [rss-advanced.md](./rss-advanced.md)；加密图片 → [encrypted-images.md](./encrypted-images.md)；iframe 视频 → [rss-advanced.md](./rss-advanced.md)
- **触发关键词**：视频、video、m3u8、HLS、音频、audio、openVideoPlayer、webView视频、嗅探、ExoPlayer、bookSourceType=1、**type=2、内置播放器、ruleContent、多集、多线路、RssEpisode、RssRoute、JSON数组、404防盗链、Referer、setDefaultHeaders、CDN防盗链、Header注入**

---

## anti-crawl.md — 反爬/Cloudflare 处理

- **一句话描述**：反爬处理概览入口，常见反爬类型速查表、WebView/Headers/Cookie 快速方案
- ✅ 包含：常见反爬类型速查表、webView:true 绕过、header 伪装、java.setCookie 预置、PJAX 空壳 HTML
- ❌ 不包含：CF 详细绕过方案 → [cf-bypass.md](./cf-bypass.md)；登录 Cookie 持久化 → [login.md](./login.md)；加密签名 → [encryption.md](./encryption.md)；年龄确认页 → [rss-advanced.md](./rss-advanced.md)
- **触发关键词**：反爬、Cloudflare、cf_clearance、WebView绕过、Headers伪装、User-Agent、Referer、Cookie预置、JS Challenge、403

---

## cf-bypass.md — Cloudflare 绕过方案

- **一句话描述**：CF 三种验证类型（JS Challenge/Turnstile/Interactive）的绕过策略、Cookie 双向共享机制、loginUrl+loginCheckJs 配置模板
- ✅ 包含：CF JS Challenge 自动绕过（webView）、Turnstile/Interactive 降级方案（startBrowserAwait）、Cookie 双向共享（WebView→CookieStore）、loginUrl+loginCheckJs 配置、CF 检测方法
- ❌ 不包含：反爬概览 → [anti-crawl.md](./anti-crawl.md)；登录流程 → [login.md](./login.md)；加密签名 → [encryption.md](./encryption.md)
- **触发关键词**：Cloudflare、CF绕过、cf_clearance、JS Challenge、Turnstile、Cookie同步、webView绕过CF

---

## rss-basic.md — RSS 基础

- **一句话描述**：标准 RSS 2.0、非标准网页→RSS 规则解析、单URL源（singleUrl）、RSS 搜索功能（searchUrl）、视频订阅源（type=2）
- ✅ 包含：RssSource 基础字段、ruleArticles/ruleTitle/ruleLink/ruleContent/ruleImage/ruleNextPage、singleUrl、searchUrl 模板语法、type=0/1/2、sortUrl 固定格式
- ❌ 不包含：JS 动态分类 → [rss-advanced.md](./rss-advanced.md)；年龄确认页 → [rss-advanced.md](./rss-advanced.md)；HLS 播放器 → [rss-advanced.md](./rss-advanced.md)；iframe 视频 → [rss-advanced.md](./rss-advanced.md)
- **触发关键词**：RSS、RssSource、订阅源、ruleArticles、singleUrl、searchUrl、sortUrl、type=2、视频订阅、RSS搜索

---

## rss-advanced.md — RSS 高级

- **一句话描述**：@js: 动态分类（sortUrl）、年龄确认页处理、ruleContent 核心技术（<js>+webViewGetSource+HLS.js）、iframe 嵌入视频、搜索模式对比、多集视频站三方案对比（BookSource / RssSource+HTML播放页 / **RssSource type=2 内置播放器**）、三种视频网站类型总结与决策树
- ✅ 包含：@js: sortUrl 动态加密分类、loginUrl 年龄确认（@js:java.ajax）、<js>标签格式、java.webViewGetSource()、HLS.js 播放器模板、iframe 提取、搜索加密对比决策树、多集视频 HTML 播放页、XHR 按需加载、BookSource 多集方案、三种视频类型决策树、**方案C type=2 内置播放器（7.10/7.11节：ruleContent JSON数组=多集 / 嵌套JSON=多线路 / R5自动抓取 / 上下滑动切换文章 / 3秒自动隐藏控件）**
- ❌ 不包含：RSS 基础字段 → [rss-basic.md](./rss-basic.md)；AES 加密 API → [encryption.md](./encryption.md)；反爬 Headers → [anti-crawl.md](./anti-crawl.md)；type=2 内置播放器 ruleContent 完整编写指南 → [video-audio.md](./video-audio.md) 5.6节
- **触发关键词**：JS分类、年龄确认、webViewGetSource、HLS.js、iframe视频、多集视频、HTML播放页、XHR按需加载、<js>标签、player_aaaa、视频类型决策树、苹果CMS、**方案C、type=2、内置播放器、ruleContent JSON数组、嵌套JSON多线路、R5自动抓取**

---

## rss-core-diff.md — 订阅源核心差异

- **一句话描述**：订阅源与书源的核心差异（字段扁平/搜索复用/ruleContent扁平/视频播放器），字段对比+构建顺序+相关陷阱
- ✅ 包含：RssSource 字段扁平结构、searchUrl 复用列表规则、ruleContent 扁平 String?、视频播放器模板（type=0）、BookSource vs RssSource 对比
- ❌ 不包含：RSS 基础字段 → [rss-basic.md](./rss-basic.md)；JS 动态分类 → [rss-advanced.md](./rss-advanced.md)；加密 → [encryption.md](./encryption.md)
- **触发关键词**：订阅源差异、rss-core-diff、字段扁平、ruleArticles、RssSource vs BookSource、订阅源构建顺序

---

## search-advanced.md — 搜索高级技巧

- **一句话描述**：搜索规则高级写法，涵盖 Cookie 清理、重定向处理、繁体编码、动态搜索地址、分页 URL、多列表处理
- ✅ 包含：cookie.removeCookie() 清理超时、java.post().header("Location") 重定向、java.s2t(key) 繁体转换、动态搜索地址获取、分页 URL 三种写法、多搜索列表 XPath/CSS 过滤
- ❌ 不包含：搜索基础规则 → [../booksource-schema.md](../booksource-schema.md)；编码完整指南 → [encoding-guide.md](./encoding-guide.md)；反爬处理 → [anti-crawl.md](./anti-crawl.md)
- **触发关键词**：搜索高级、Cookie清理、搜索超时、搜索重定向、繁体搜索、分页URL、多搜索列表、搜索地址动态获取

---

## content-advanced.md — 详情页/正文高级技巧

- **一句话描述**：详情页和正文规则高级写法，涵盖 URL 拼接、去章节名、去重复段落、翻页断句、图片 headers、漫画/听书源、封面计算、onclick 处理
- ✅ 包含：URL 拼接六种方式（##^##/##$##/@js/{{baseUrl}}/{{$.}}）、去章节名五种写法、去重复段落正则、翻页断句拼接、图片修改 headers、漫画源 data-original+imageStyle、听书源 sourceRegex、封面 ID 计算、onclick 提取
- ❌ 不包含：加密图片 → [encrypted-images.md](./encrypted-images.md)；视频/音频 → [video-audio.md](./video-audio.md)；正文替换规则基础 → [../booksource-schema.md](../booksource-schema.md)
- **触发关键词**：URL拼接、去章节名、去重复段落、翻页断句、图片headers、漫画源正文、听书源正文、封面计算、onclick章节

---

## toc-advanced.md — 目录高级技巧

- **一句话描述**：目录规则高级写法，涵盖章节排序、目录与详情页合一、多页目录加载
- ✅ 包含：目录排序三种方法（文本数字/属性ID/data-id）、目录与详情页合一（{{baseUrl}}/tag.html）、目录下一页（option@value/并发加载/JS生成多页URL）
- ❌ 不包含：目录基础规则 → [../booksource-schema.md](../booksource-schema.md)；正文规则 → [content-advanced.md](./content-advanced.md)
- **触发关键词**：目录排序、章节排序、目录合一、目录分页、多页目录、option分页

---

## websocket-debug.md — WebSocket 调试

- **一句话描述**：Legado 真机 WebSocket 调试协议、双端口架构、5大陷阱、真机 vs JAR 差异
- ✅ 包含：HTTP 1122 + WS 1123 双端口、三个 WS 路径（/bookSourceDebug, /rssSourceDebug, /searchBook）、WS不响应HTTP、searchBook全源搜索极慢、真机日志纯文本格式、模拟器DNS问题、getBookSources大数据量、Python/JS连接示例、真机vs JAR差异对比
- ❌ 不包含：反爬处理 → [anti-crawl.md](./anti-crawl.md)；登录流程 → [login.md](./login.md)；加密方案 → [encryption.md](./encryption.md)
- **触发关键词**：WebSocket, WS, 真机调试, bookSourceDebug, rssSourceDebug, searchBook, 1122, 1123, NanoWSD, 模拟器DNS, 调试日志

---

## encoding-guide.md — 编码处理完整指南

- **一句话描述**：编码判断三步法、charset 参数位置、java.encodeURI()、java.s2t()/t2s() 繁简转换、GBK 兼容性
- ✅ 包含：编码判断三步法（HTTP头/meta/乱码特征）、charset 参数必须在 JSON 对象中、java.encodeURI(key,'GBK')、java.s2t(key)/java.t2s(key)、GBK 兼容性说明
- ❌ 不包含：加密编码 → [encryption.md](./encryption.md)；搜索高级 → [search-advanced.md](./search-advanced.md)
- **触发关键词**：编码、charset、encodeURI、GBK、GB2312、Big5、乱码、繁简转换、s2t、t2s

---

## 自进化写入规则

当新增特殊场景内容时，按以下规则自动维护本索引：

1. **定位目标文档**：根据触发关键词匹配，找到最相关的子文档写入
2. **跨文档引用**：如果新内容涉及多个子文档的主题，在主文档写入完整内容，在相关文档的 ❌ 不包含 中添加指向
3. **新增子文档**：仅当新主题无法归入任何已有子文档时才创建，创建后必须在本索引添加条目并更新所有相关 ❌ 指向
4. **关键词去重**：新增触发关键词时，检查是否与已有文档冲突，冲突时调整或合并
