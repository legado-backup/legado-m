# 社区源常见问题与修复经验

> 基于 yckceo.com 26,583个社区源的分析 + 300个源动态验证 + 60个源深度链路验证

## 动态验证发现的实际问题（比静态分析更真实）

| 问题 | 占比 | 修复方案 |
|------|------|----------|
| 网站已挂（域名失效/服务器关闭） | 12-37% | 无法修复，需寻找替代源 |
| 搜索返回403 | 常见 | 添加header/启用enabledCookieJar/添加loginUrl |
| 搜索返回404 | 常见 | 网站改版，需重新分析页面结构更新规则 |
| 搜索URL含JS模板变量 | 42% | 正常现象，Legado中JS会自动执行 |
| SSL错误 | 5% | 网站证书问题，Legado内置SSL信任可处理 |
| 搜索响应过小(<100B) | 常见 | 可能需要特定header或Cookie |
| 连接被重置(WinError 10054) | 偶发 | 网站反爬，需要设置header或延迟 |

## 深度链路验证发现的问题（规则引擎模拟解析）

> 不只是HTTP状态码，而是真正用Legado规则引擎逻辑解析每个环节

| 问题 | 频率 | 根因 | 修复方案 |
|------|------|------|----------|
| CSS选择器不匹配 | 29次/40源 | 网站改版后HTML结构变化 | 重新curl获取HTML，更新选择器 |
| JSON API字段提取失败 | 4个D级源 | bookList匹配但name/bookUrl提取失败 | 确保字段规则是相对路径（$.title→item.title） |
| JS规则无法外部验证 | 24/40源含JS | Rhino语法Python无法解析 | 只能在Legado环境中验证 |
| 规则模式不匹配 | 偶发 | CSS规则用于JSON响应 | 根据响应类型切换规则模式 |
| bookUrl模板变量未替换 | 常见 | `{{$.bookId}}`需先提取再替换 | Legado内置处理，Python需手动替换 |

## 验证方法学（创建源后必须执行）

### 浅层验证（5步，快速判断）

1. **网站存活检测**：`curl -s -o /dev/null -w "%{http_code}" <sourceUrl>` → 200=OK
2. **搜索功能测试**：用searchUrl搜索"斗罗大陆"，检查返回数据
3. **发现功能测试**：用exploreUrl获取第一个分类，检查返回数据
4. **详情页测试**：从搜索结果取bookUrl，检查详情页
5. **目录测试**：检查chapterList是否返回章节列表

### 深度验证（6步，真正验证规则可用性）

1. **网站存活检测**：HTTP GET sourceUrl
2. **搜索请求+规则解析**：用searchUrl发起搜索，**用ruleSearch.bookList解析结果**
3. **字段级验证**：对每个列表项，**用name/author/coverUrl/bookUrl规则提取并验证非空**
4. **详情页验证**：从搜索结果取bookUrl，访问详情页，**用ruleBookInfo解析每个字段**
5. **目录+正文验证**：从详情页取tocUrl，获取目录，**取第一章验证content非空**
6. **JS依赖分析**：检查java.put/get配对、变量链完整性、语法正确性

> **关键区别**：浅层验证只看"HTTP请求能不能发出去"，深度验证看"规则能不能真正提取到数据"

## 403/404 修复模式

**403 Forbidden**:
1. 添加 `enabledCookieJar: true`
2. 添加 `header: {"User-Agent": "Mozilla/5.0..."}`
3. 添加 `loginUrl` 处理登录/年龄确认
4. 检查是否需要 Referer 头

**404 Not Found**:
1. 网站可能改版，重新分析页面结构
2. bookSourceUrl可能需要更新（如 www.deqibook.com → www.deqixs.co）
3. 搜索URL可能需要更新路径
4. 检查URL中是否有硬编码的过期参数

## 实际修复经验（14个源验证通过）

> 基于对100个社区源分类、14个源实际修复的实战经验

### C类：JSON API路径修复（4个成功）

| 问题 | 修复方案 | 代码示例 |
|------|----------|----------|
| bookList用CSS选择器但响应是JSON | 改为JSONPath | `.novel_cell` → `$.data.list[*]` |
| 字段规则用了绝对路径 | 改为相对路径 | `$.data.list[*].bookName` → `bookName` |
| bookUrl返回id而非完整URL | 用模板拼接 | `https://xxx/book/{{$.id}}` |
| @JSon:与$.混用 | 统一为$. | `@JSon:$.items[*]` → `$.items[*]` |

**核心原则**：bookList定位到数组元素后，字段规则只需相对key名，不需要再写完整路径。

### D类：Cookie/Header修复（4个成功）

| 场景 | Header方案 | 关键配置 |
|------|-----------|----------|
| Cloudflare 403 | `X-Requested-With:mark.via` + `Cache-control:no-store` + `java.getWebViewUA()` | enabledCookieJar:true + loginCheckJs |
| 普通反爬 403 | 标准浏览器三件套：UA + Referer + Accept-Language | enabledCookieJar:true |
| 百度安全验证 | loginCheckJs检测验证页面 | `if(/_cf_\|ge_ua\|verify/ig.test(result.body())){...}` |
| 现代反爬(sec-ch-ua) | 完整浏览器头含sec-ch-ua/sec-fetch-* | enabledCookieJar:true |

**标准反403 Header模板**：
```json
{
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
  "Referer": "https://源站地址/",
  "Accept-Language": "zh-CN,zh;q=0.9",
  "Accept": "text/html,application/xhtml+xml"
}
```

**Cloudflare绕过Header模板**：
```json
{
  "X-Requested-With": "mark.via",
  "Cache-control": "no-store",
  "Referer": "源站地址",
  "User-Agent": "java.getWebViewUA()"
}
```

### B类：CSS选择器修复（3个成功）

| 问题 | 修复方案 | 代码示例 |
|------|----------|----------|
| CSS类名改版 | 用通配选择器 | `.novel_cell` → `div[class*='novel']` |
| AMP页面img标签 | 适配amp-img | `img@src` → `amp-img@src` |
| HTML改为JSON API | 整套规则切换 | bookList+name+author全部从CSS改为JSONPath |

**选择器优先级**：`[property$=xxx]` > 语义标签(h3/h2) > 通配class `div[class*='keyword']` > 精确class

### E类：JS技巧学习（3个深度分析）

**1. API签名三步流程**（阅友小说）：
```
时间戳time → uth=HmacMD5(key+time) → sign=HmacSHA256(path+params+uth) → _p=DES(params+uth+sign) → URL?_p=encodeURI(_p)
```

**2. 凯撒密码内容解密**（阿巴小说）：
```javascript
// 服务端返回加密内容 → 凯撒密码偏移解密 → Base64解码 → 明文
function caesar(e) {
    return e.split("").map(function(c) {
        return c.match(/[A-Za-z]/) ?
            String.fromCharCode((c.toLowerCase().charCodeAt(0) - 83) % 26 + ...) : c
    }).join("")
}
java.base64Decode(caesar(result))
```

**3. AES/CBC + GZIP组合解密**（酷匠网吧）：
```javascript
// 服务端返回 iv@a2o@密文
jm = String(jms.body.content).split("a2o@");
key = "S3VqaWFuZ0FwcDc0NzYwNQ==";  // Base64编码的AES key
iv = jm[0];  // 初始向量
data = jm[1];  // 密文
// AES/CBC/PKCS5Padding解密 → GZIP解压 → 正文
decode(java.aesBase64DecodeToString(data, java.base64Decode(key),
    "AES/CBC/PKCS5Padding", java.base64Decode(iv)))
```

**4. java.put/get变量传递模式**：
```javascript
// 在ruleSearch.bookUrl中put变量
"bookUrl": "$.bid<js>java.put('bid',result);'http://xxx/bid/'+result</js>"

// 在ruleToc.chapterUrl中get变量
"chapterUrl": "<js>url='http://xxx/read?book='+java.get('bid')+'&chapter='+{{$.chapter}}</js>"
```

### 跨类别通用经验

1. **JSON vs HTML判断**：先尝试JSON解析，失败再用HTML解析，避免CSS选择器匹配JSON
2. **enabledCookieJar默认开启**：即使站点不需要Cookie，开启也无副作用
3. **API失效检测**：HTTP 404/503通常意味着API端点已变更
4. **Cloudflare识别**：响应头包含cf-ray或server=cloudflare时需特殊header
5. **AMP页面**：使用amp-img替代img，需在coverUrl规则中处理
6. **bookList通配**：`div[class*='keyword']`比精确class匹配更抗改版
7. **JS签名模式**：大多数APP API签名遵循 参数排序→拼接→加密(HMac/MD5)→URL编码 的流程
8. **java.put/get**：是跨规则传递数据的核心机制，比source.getVariable更轻量
9. **MD5签名必须在原始中文字符串上计算**（非URL编码后），URL编码在HTTP请求层处理
10. **`eval(String(source.loginUrl))`** 实现代码复用——loginUrl既是登录代码也是工具库
11. **`org.jsoup.Jsoup.parse()`** 可在JS中直接调用Java类，比正则更可靠
12. **`try{run}catch{}`** 是Legado JS中实现API版本回退的巧妙技巧
13. **用class选择器替代索引选择器**，HTML结构微调时class更健壮
14. **Legado@tag语法应替换为标准CSS**，兼容性更好
15. **懒加载图片优先用data-original/data-src属性**
16. **搜索无封面图时coverUrl应清空**，不要留错误规则
17. **CF 5秒盾绕过是分阶段的**：WebView可执行JS挑战获取Cookie，但OkHttp因TLS指纹不同可能被CF拦截，启用Cronet可解决
18. **concurrentRate限速至关重要**：过快请求触发CF IP封禁，建议1200-2000ms
19. **搜索结果为空可能是UA歧视**：服务端对非浏览器UA返回空内容，需WebView UA
20. **Next.js SPA+CF双重保护**：最复杂的反爬组合，规则复杂度最高

## 反爬源深度分析经验（5个源实战）

> 按SKILL.md五步流程对5个CF反爬源的分析结果

### 反爬类型识别

| 反爬类型 | 特征 | Python可绕过 | Legado WebView | Legado OkHttp | Legado+Cronet |
|----------|------|-------------|---------------|--------------|---------------|
| CF 5秒盾(JS挑战) | `Just a moment...` + cf-ray头 | ❌ | ✅ 自动完成 | ⚠️ TLS指纹可能被拦截 | ✅ |
| CF Turnstile | 需点击验证 | ❌ | ✅ 需手动点击 | ⚠️ 同上 | ✅ |
| CF自定义403 | `Attention Required!` | ❌ | ✅ | ⚠️ 同上 | ✅ |
| CF Beacon监控 | 正常200但速率限制 | ✅ 慢速 | ✅ | ✅ concurrentRate | ✅ |
| Next.js SPA+CF | 空壳HTML+JS渲染+CF | ❌ | ✅ WebView+webJs | ⚠️ | ✅ |
| UA歧视 | 200但内容为空 | ❌ | ✅ java.getWebViewUA() | ⚠️ | ✅ |

> **核心问题**：WebView获取cf_clearance后，OkHttp因TLS指纹与Chrome不同，CF可能拒绝后续请求。启用Cronet加速（Chromium网络栈）可解决此问题。

### CF标准修复配置详解

**书源 CF 标准配置**（6 个字段缺一不可）：
```json
{
  "enabledCookieJar": true,
  "header": "@js:JSON.stringify({\"X-Requested-With\":\"mark.via\",\"Cache-control\":\"no-store\",\"Referer\":baseUrl,\"User-Agent\":java.getWebViewUA()})",
  "loginCheckJs": "var src=result.body();if(src.includes('Just a moment')||src.includes('Attention Required')||src.includes('_cf_chl_opt')){cookie.removeCookie(baseUrl);java.startBrowserAwait(result.url(),'CF验证',false)};result",
  "concurrentRate": "1200",
  "loginUrl": "",
  "loginUi": ""
}
```

**订阅源 CF 标准配置**（与书源逻辑一致，concurrentRate 建议 1500ms）：
```json
{
  "enabledCookieJar": true,
  "header": "@js:JSON.stringify({\"X-Requested-With\":\"mark.via\",\"Cache-control\":\"no-store\",\"Referer\":baseUrl,\"User-Agent\":java.getWebViewUA()})",
  "loginCheckJs": "var src=result.body();if(src.includes('Just a moment')||src.includes('Attention Required')||src.includes('_cf_chl_opt')){cookie.removeCookie(baseUrl);java.startBrowserAwait(result.url(),'CF验证',false)};result",
  "concurrentRate": "1500"
}
```

**配置说明**：
- `enabledCookieJar: true` — 让 OkHttp/Cronet 自动管理 CF 验证后的 Cookie（cf_clearance）
- `X-Requested-With: mark.via` — CF 识别为合法 APP 请求
- `Cache-control: no-store` — 禁止缓存，确保每次获取最新验证页面
- `Referer: baseUrl` — CF 校验来源，必须与目标站一致
- `java.getWebViewUA()` — 使用 WebView 的 UA，CF 不会拦截（比硬编码 UA 更可靠）
- `loginCheckJs` — 自动检测 CF 验证页，弹出 WebView 让用户通过验证
- `concurrentRate` — 限速，防止过快请求触发 IP 封禁
- `loginUrl` / `loginUi` — 预留登录/手动验证入口

**loginCheckJs 四种进阶写法**：

| 版本 | 适用场景 | 代码 |
|------|----------|------|
| 基础版 | 大多数 CF 站点 | `src.includes('Just a moment')\|\|src.includes('Attention Required')` |
| 增强版 | 更多 CF 特征检测 | 增加 `src.includes('_cf_chl_opt')\|\|src.includes('cf-browser-verification')` |
| 带重试版 | 验证后自动重试 | 验证后追加 `result=java.ajax(result.url())` |
| 手动回退版 | 自动验证失败时 | `try{...false}catch{...true}` 第二个参数改 true 让用户手动操作 |

> ⚠️ `java.startBrowserAwait` 第三个参数 `false` 表示验证后**直接从 WebView 提取 HTML**，绕过 TLS 指纹问题。设为 `true`（默认）则用 OkHttp 重新请求，可能因 TLS 指纹被 CF 再次拦截。

**前提条件**：需在 App 中开启 Cronet 加速（设置→其它设置→Cronet），否则 OkHttp 的 TLS 指纹可能被 CF 拦截。Cronet 是全局开关，无法在书源 JSON 中单独控制。

### CF绕过的完整技术链路（基于Legado源码分析）

> 来源：BackstageWebView.kt / WebViewActivity.kt / HttpHelper.kt / CookieManager.kt / SourceVerificationHelp.kt

**1. WebView执行CF JS挑战**
- BackstageWebView在后台加载页面，JS自动启用（`javaScriptEnabled=true`）
- `onPageFinished`后延迟900ms执行JS获取页面内容
- 如果CF挑战成功，页面自动跳转，触发新的`onPageFinished`
- WebViewActivity有内置CF检测：`window._cf_chl_opt`消失后自动保存结果并关闭

**2. Cookie传递链路**
- WebView → CookieStore：`onPageFinished`中`CookieManager.getInstance().getCookie(url)` → `CookieStore.setCookie()`
- CookieStore → OkHttp：`AnalyzeUrl.setCookie()`从CookieStore读取Cookie设置到请求头
- ⚠️ BackstageWebView不会预同步OkHttp的Cookie到WebView（只有WebViewActivity会）

**3. TLS指纹问题（核心障碍）**
- OkHttp使用Java SSL引擎，TLS指纹（JA3/JA4）与Chrome完全不同
- WebView使用Chromium BoringSSL，TLS指纹与Chrome一致
- CF可能同时校验Cookie+TLS指纹，即使cf_clearance有效，OkHttp仍可能被拦截
- **解决方案**：启用Cronet加速（`AppConfig.isCronet`），Cronet使用Chromium网络栈，TLS指纹与Chrome一致

**4. refetchAfterSuccess参数**
- `startBrowserAwait(url, title, false)`：验证通过后直接从WebView提取HTML，**绕过TLS指纹问题**
- `startBrowserAwait(url, title, true)`（默认）：验证通过后用OkHttp重新请求，**可能因TLS指纹被拦截**

### 5个源修复结果

| 源名 | 反爬类型 | 修复评级 | 关键配置 |
|------|----------|---------|---------|
| 太极小说 | CF 5秒盾 | B | CF三件套+WebViewUA(JS)+concurrentRate 1200ms |
| 神凑轻说 | CF 5秒盾 | B | CF三件套+Quark UA+标准JSON header |
| 万通蜡笔 | CF+Next.js SPA | C | CF三件套+WebViewUA(JS)+concurrentRate 2000ms |
| 跑小说网 | CF自定义403 | B- | CF三件套+WebViewUA+Attention Required检测 |
| 幻梦轻说 | CF Beacon监控 | A- | 原源UA+CF三件套(JS)+搜索需WebView渲染 |

## E类JS搜索源修复经验（9个源分析）

> searchUrl含JS的源，按JS模式分为5类

| JS模式 | 代表源 | 可否转非JS | 核心逻辑 |
|--------|--------|-----------|---------|
| MD5签名 | 全免/爱淘/陶越文华 | ❌ | 参数排序+拼接+MD5(key)→sign |
| CSRF令牌 | 风云/车群小说 | ❌ | 从页面提取_token/验证参数 |
| POST重定向 | 天天书吧/新籁 | ❌ | POST→302→Location作为结果URL |
| API回退 | 米读小说 | ✅ | try{run}catch{searchV2} |
| Form Action | 顶点小说 | ✅ | 动态提取form action但值固定 |

**陶越文华系三源共用同一套签名**：区别仅在appid和密钥（qmbook/tfbook_free, mibook/mibook_123456, qcbook/qcbook_123456）

## E类JS重度源分析经验（7个源深度分析）

> 多字段含JS的源，学习价值最高

| 源 | JS字段数 | 加密模式 | 变量链完整 | 核心技巧 |
|----|---------|---------|-----------|---------|
| 阅友小说 | 7 | HmacMD5+SHA256+DES | ❌ | 三步签名链+randomUUID临时令牌 |
| 阿巴小说 | 6 | 凯撒密码+Base64+MD5 | ✅ | ROT变体位移+Base64解码 |
| 存档书库 | 11 | JS混淆+URL编码 | ✅ | eval(loginUrl)复用+持久化配置 |
| 鸠摩搜书 | 4 | 无 | ✅ | 两步异步搜索API |
| ARCHIVE配置 | 10 | JS混淆+URL编码 | ✅ | payAction借阅+filter_map动态过滤 |
| 移动阅读 | 7 | DES+MD5+Base64 | ❌ | JavaImporter调用Java加密库 |
| 晋江文学 | 11 | Base64 | ❌ | Cookie依赖+多域名变体 |

**新发现的JS技巧**（js-patterns.md中未覆盖的）：
- `payAction`字段 — 实现借阅/购买逻辑，不限于VIP判断
- `eval(String(source.loginUrl))` — 在各规则中复用loginUrl初始化代码
- `source.getVariable()/setVariable()` — 跨会话持久化配置
- `JavaImporter`模式 — Rhino引擎中直接导入Java加密类
- `java.randomUUID()` — 生成临时令牌
- `source.getLoginInfoMap()` — 从登录界面获取用户输入参数
- `Imgurl()`函数 — 对.jp2图片URL重排参数顺序

## B类CSS选择器修复经验（6个源修复成功）

| 修复模式 | 旧规则 | 新规则 | 说明 |
|----------|--------|--------|------|
| @tag语法→标准CSS | `.u-list@tag.li` | `.u-list li` | @tag语法过时，用标准CSS |
| 索引选择器→class | `a.2@text` | `.bauthor a@text` | 索引选择器不稳定 |
| 负索引→正索引 | `td.-1:-2@text` | `td.5@text` | 负索引语法易出错 |
| 懒加载图片 | `img@src` | `img@data-original` | 懒加载用data属性 |
| 无封面清空 | `img@src`(无效) | 留空 | 搜索无封面时不要留错误规则 |
| @tag语法→标准CSS | `.grid@tbody@tr!0` | `dl` | @tag语法过时，用标准CSS |
| ul>li过于宽泛 | `ul > li` | 更精确的选择器 | 可能匹配导航项而非搜索结果 |
| AMP页面img | `img@src` | `amp-img@src` | AMP页面用amp-img替代img |

## 订阅源修复经验（15个分析，3个修复成功）

> 大多数订阅源不是RSS/Atom格式，而是HTML列表页

| 问题 | 修复方案 | 代码示例 |
|------|----------|----------|
| HTML列表页无articleList | 添加CSS选择器 | `li.close` / `div.card` |
| sortUrl含JS模板变量 | 过滤后使用 | `{{source.getVariable()}}`需Legado环境 |
| 微博系返回空壳HTML | 需JS渲染 | Python无法解析，需Legado WebView |
| feed检测优先级 | 先检测sourceUrl本身 | 再检测HTML中的`<link rel="alternate" type="application/rss+xml">` |

## missing_ruleContent

**描述**: 最常见问题，源有列表规则但无内容规则

**修复方法**: 访问源URL分析HTML结构，提取内容区域CSS选择器

**常见修复规则**:

- `class.content@html (最常见)`
- `class.article-content@html`
- `class.post-content@html`
- `id.content@html`
- `class.entry-content@html`

## missing_sourceIcon

**描述**: 源缺少图标

**修复方法**: 从网站HTML提取favicon链接，或使用默认/favicon.ico

## missing_ruleLink

**描述**: 源缺少链接规则

**修复方法**: 添加默认规则 a@href

## missing_ruleTitle

**描述**: 源缺少标题规则

**修复方法**: 添加默认规则 a@text
