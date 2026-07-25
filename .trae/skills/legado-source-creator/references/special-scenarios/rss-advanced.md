# RSS 订阅源高级处理

> JS 动态分类、年龄确认页、HLS 播放器、iframe 视频、搜索模式对比、多集视频站、三种视频类型总结。

## 7.6 用 @js: 动态生成分类列表（sortUrl）

> **核心场景**：网站没有传统分类页面，但搜索不同关键词等同于浏览不同分类。用 `@js:` 在 sortUrl 中动态加密关键词生成分类 URL。

### 适用条件

- 网站搜索 URL 包含加密关键词（如 `/search-0-1-{encrypted}.html`）
- 网站有热门搜索关键词列表（如首页"热门搜索"区域）
- 没有独立的分类筛选页面

### 实战示例

```json
{
  "sortUrl": "@js:var cats=['今日热播','今日更新','国产','91大神','麻豆','SWAG','剧情','少妇','萝莉','巨乳','偷拍','丝袜'];var crypto=java.createSymmetricCrypto('AES/CBC/ZeroPadding','your-key','your-iv');var result='';for(var i=0;i<cats.length;i++){var name=cats[i];var url;if(i===0){url='/toplist.html';}else if(i===1){url='/newlist.html';}else{var enc=crypto.encryptBase64(name);url='/search-0-1-'+encodeURIComponent(enc)+'.html';}if(i>0)result+='\\n';result+=name+'::'+url;}result;"
}
```

**生成效果**（Legado 解析 sortUrl 后的等效结果）：
```
今日热播::/toplist.html
今日更新::/newlist.html
国产::/search-0-1-{AES加密后的国产}.html
91大神::/search-0-1-{AES加密后的91大神}.html
麻豆::/search-0-1-{AES加密后的麻豆}.html
...
```

### 关键要点

| 要点 | 说明 |
|------|------|
| `@js:` 前缀 | sortUrl 支持 JS 规则，返回格式与普通 sortUrl 相同（`名称::URL\n名称::URL`） |
| `\\n` 换行 | JSON 中 `\n` 需转义为 `\\n`，JS 中输出 `\n` |
| 加密复用 | 分类 URL 和搜索 URL 使用相同的加密方式，复用 `createSymmetricCrypto` 实例 |
| 混合模式 | 部分分类用固定 URL（如 `/toplist.html`），部分用加密搜索 URL |
| 关键词来源 | 从网站首页"热门搜索"区域提取，或手动整理常见分类关键词 |

## 7.7 年龄确认页处理

> 实战案例：mjv006.com 首页是年龄确认页，需点击"同意"后才可浏览内容。

### 识别年龄确认页

特征：
- 页面很小（<2KB）
- 包含"同意"/"I agree"/"18+"按钮
- 点击后跳转到主站 URL（如 `/zh/chinese_IamOverEighteenYearsOld/19/index.html`）
- 服务器设置确认 Cookie（如 `YES_Eighteen=IamOverEighteenYearsOld`）

### ⚠️ loginUrl 不是简单 URL！

> **这是 #1 常见错误**：`loginUrl` 在 Legado 中是 **JS 代码**，不是 URL。直接放 URL 不会触发 Cookie 设置！

```json
// ❌ 错误：直接放 URL，不会设置 Cookie
"loginUrl": "https://example.com/agree.html"

// ✅ 正确：用 @js: + java.ajax() 发请求，CookieJar 自动保存 Cookie
"loginUrl": "@js:java.ajax('https://example.com/agree.html');"
```

### Legado 订阅源配置（双保险）

```json
{
  "enabledCookieJar": true,
  "header": "{\"User-Agent\":\"...\",\"Cookie\":\"YES_Eighteen=IamOverEighteenYearsOld\"}",
  "loginUrl": "@js:java.ajax('https://mjv006.com/zh/chinese_IamOverEighteenYearsOld/19/index.html');"
}
```

| 字段 | 值 | 说明 |
|------|-----|------|
| `enabledCookieJar` | `true` | 开启 Cookie 管理，保存确认后的登录态 |
| `header` 中 `Cookie` | 确认 Cookie 键值对 | **每次请求自动带上**，最可靠的方式 |
| `loginUrl` | `@js:java.ajax('确认页URL');` | 点击"登录"时触发，CookieJar 自动保存 |

> **关键**：用 curl -v 分析确认页的 Set-Cookie 头，找到确认 Cookie 的键值对，然后硬编码到 header 中。这是最可靠的方式，因为年龄确认 Cookie 通常是固定值不会过期。

### curl 分析确认 Cookie

```bash
# 访问确认页，查看 Set-Cookie 头
curl -s -L --max-time 15 -v "https://example.com/agree.html" 2>&1 | grep -i "set-cookie"

# 输出示例：
# < set-cookie: YES_Eighteen=IamOverEighteenYearsOld; expires=...; path=/
#                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                                     这就是需要硬编码到 header 中的 Cookie 值
```

## 7.7b ruleContent 核心技术：`<js>` + webViewGetSource + HLS.js

> ⚠️ **这是视频订阅源最核心的三项技术**，必须掌握！

### 1. `<js>` 标签格式（非 `@js:`）

`@js:` 只返回 JS 表达式的值（字符串），无法混合 HTML。
`<js>...</js>` 允许 JS 和 HTML 混合输出——JS 先执行设置 `result` 变量，HTML 中用 `<js>result</js>` 插入 JS 结果。

```json
// ❌ @js: 只返回字符串，无法输出 HTML 播放页
"ruleContent": "@js:var url=...;url"

// ✅ <js>...</js> + HTML 模板，输出完整播放页面
"ruleContent": "<js>\nvar url=java.webViewGetSource(null,baseUrl,null,'.*\\\\.m3u8.*');\nresult=url;\n</js>\n<!DOCTYPE html><html>...<script>var url='<js>result</js>';...</script></html>"
```

### 2. `java.webViewGetSource()` — 获取 JS 渲染后的视频地址

> **这是获取视频地址的最佳方式！** 比 `java.ajax()` + 正则更可靠，因为很多播放页需要 JS 执行才能生成 m3u8 地址。

```javascript
// 参数：html, url, js, regex
// html: null（使用 url 加载）
// url: 页面 URL
// js: null（不注入额外 JS）
// regex: 匹配 m3u8 地址的正则
var videoUrl = java.webViewGetSource(null, baseUrl, null, ".*\\.m3u8.*");
```

**原理**：Legado 用后台 WebView 加载页面，执行所有 JS，然后从渲染后的页面源码中用正则匹配 m3u8 地址。

**对比**：

| 方式 | 适用场景 | 可靠性 |
|------|----------|--------|
| `java.ajax()` + 正则 | 静态 HTML 中的 m3u8 | 中（需页面结构固定） |
| `java.webViewGetSource()` | JS 动态生成的 m3u8 | **高（执行 JS 后再匹配）** |

### 3. HLS.js — m3u8 播放必备

Android WebView 原生不一定支持 m3u8/HLS 播放，**必须引入 HLS.js 库**。

```html
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.4.12"></script>
<script>
function initPlayer(src){
  if(Hls.isSupported()){
    var hls=new Hls();
    hls.loadSource(src);
    hls.attachMedia(document.getElementById('video-element'));
    hls.on(Hls.Events.MANIFEST_PARSED,function(){v.play()});
  }else if(v.canPlayType('application/vnd.apple.mpegurl')){
    v.src=src;v.play(); // iOS Safari 原生支持
  }
}
</script>
```

### 完整 ruleContent 模板（单视频）

```json
"ruleContent": "<js>\nvar videoUrl=java.webViewGetSource(null,baseUrl,null,\".*\\\\.m3u8.*\");\nresult=videoUrl;\n</js>\n<!DOCTYPE html><html><head><meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">\n<script src=\"https://cdn.jsdelivr.net/npm/hls.js@1.4.12\"></script>\n<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#111;color:#fff}video{width:100%;max-height:45vh;background:#000}.bar{padding:8px;background:#1a1a1a;display:flex;flex-wrap:wrap;gap:4px}.bar button,.bar select{padding:4px 8px;background:#333;color:#fff;border:1px solid #555;border-radius:4px;font-size:12px}</style></head><body>\n<video id=\"v\" controls autoplay muted></video>\n<div class=\"bar\"><button onclick=\"sk(-180)\">←3m</button><button onclick=\"sk(-60)\">←1m</button><button onclick=\"sk(-30)\">←30s</button><button onclick=\"sk(30)\">30s→</button><button onclick=\"sk(60)\">1m→</button><button onclick=\"sk(180)\">3m→</button><select onchange=\"v.playbackRate=parseFloat(this.value)\"><option value=\"1\">1x</option><option value=\"3\">3x</option><option value=\"5\">5x</option><option value=\"10\">10x</option></select><button onclick=\"v.requestFullscreen&&v.requestFullscreen()\">全屏</button></div>\n<script>var v=document.getElementById('v'),url='<js>result</js>';function init(s){if(Hls.isSupported()){var h=new Hls();h.loadSource(s);h.attachMedia(v);h.on(Hls.Events.MANIFEST_PARSED,function(){v.play()})}else if(v.canPlayType('application/vnd.apple.mpegurl')){v.src=s;v.play()}}if(url&&url.indexOf('m3u8')>-1)init(url);function sk(s){v.currentTime+=s}</script></body></html>"
```

## 7.8 iframe 嵌入视频处理

> 实战案例：mjv006.com 的视频通过 iframe 嵌入播放，URL 格式为 `//mjv006.com/js/player/play.php?numresolution=1080&lo=on&id={encoded}`

### 识别 iframe 视频

详情页 HTML 中包含：
```html
<iframe src="//example.com/js/player/play.php?numresolution=1080&id=xxx"></iframe>
```

### 提取 iframe 播放地址

**方式1：CSS 选择器 + 正则（推荐）**

```json
{
  "ruleContent": "@js:var m=result.match(/play\\.php[^'\"]*/);if(m){'https://example.com'+m[0]}else{''}"
}
```

**方式2：WebView 模式**

如果 iframe 内部还需要 JS 渲染才能获取真实视频地址：

```json
{
  "ruleContent": {
    "webJs": "document.querySelector('iframe').src"
  }
}
```

### 两种视频网站对比

| 类型 | 代表网站 | 视频地址位置 | 提取方式 |
|------|----------|-------------|----------|
| **m3u8 直出** | 机房哥(jfg) | `<a playdata="xxx.m3u8">` | `.playsource a@playdata` |
| **iframe 嵌入** | 18AV(mjv006) | `<iframe src="play.php?id=xxx">` | `@js:` 正则提取 iframe src |
| **JS 动态加载** | 部分网站 | JS 变量中 | `webJs` 模式或 `@js:` 提取 |

## 7.9 两种搜索模式对比

> 基于两个实战网站的搜索机制对比。

| 对比项 | 机房哥(jfg) | 18AV(mjv006) |
|--------|------------|-------------|
| **搜索加密** | AES-128-CBC+ZeroPadding | 无加密 |
| **搜索URL** | `/search-0-1-{AES加密}.html` | `/zh/fc_search/all/{key}/{page}.html` |
| **searchUrl 规则** | `@js:java.createSymmetricCrypto(...)` | 模板语法 `{{key}}` |
| **分类实现** | `@js:` 动态加密关键词 | 固定 URL + `{{page}}` |
| **复杂度** | 高（需逆向加密） | 低（直接拼接） |

**searchUrl 编写决策树**：

```
搜索URL是否包含加密参数？
├── 否 → 使用模板语法：/search?q={{key}}&page={{page}}
└── 是 → 加密方式？
    ├── AES/DES → @js:java.createSymmetricCrypto(algo,key,iv).encryptBase64(key)
    ├── MD5签名 → @js:java.md5Encode(str)
    ├── Base64编码 → @js:java.base64Encode(str)
    └── 自定义 → 分析JS源码，用java内置方法实现
```

## 7.10 多集视频站（BookSource vs RssSource + HTML播放页 vs type=2 内置播放器）

> 实战案例：acgfta.com（饭团动漫），详情页有多条播放线路，每条线路下有多集。

### 方案选择

| 方案 | 源类型 | 优点 | 缺点 |
|------|--------|------|------|
| **A. BookSource 目录规则** | BookSource | Legado 原生目录管理，翻页方便 | 每集需单独进入，无法在页面内切换 |
| **B. RssSource + HTML播放页** | RssSource (type=0) | 一个页面内选择所有集数 | 需要组装 HTML，技术复杂度高 |
| **C. RssSource + type=2 内置播放器（推荐）** | RssSource (type=2) | 原生 ExoPlayer 播放、上下滑动切换文章、3秒自动隐藏控件、JSON数组即多集、ruleRoutes/ruleEpisodes即多线路多集 | 视频URL需可直接提取（非JS动态生成） |

> **推荐方案C**：用 RssSource type=2 + ruleContent 返回 JSON 数组（多集）或 ruleRoutes/ruleEpisodes（多线路多集按需采集），内置播放器自动解析，无需组装 HTML，体验最佳。
> 方案B 适用于需要自定义播放器界面的复杂场景（如 HLS.js + 自定义控件）。

### 方案C 核心原理（type=2 内置播放器，推荐）

ruleContent 返回 JSON 数组时，内置播放器（VideoPlay.kt）自动调用 `parseRssEpisodes()` 解析为多集列表，左下角集数选择器切换。多线路多集（v3.26.072420+）改用 `ruleRoutes`/`ruleEpisodes` 独立字段按需采集，替代旧的 ruleContent 嵌套JSON模式。

**单线路多集（JSON 数组）**：
```javascript
<js>
JSON.stringify([
  {url: 'https://example.com/ep1.m3u8', title: '第1集'},
  {url: 'https://example.com/ep2.m3u8', title: '第2集'},
  {url: 'https://example.com/ep3.m3u8', title: '大结局'}
]);
</js>
```

**多线路多集按需采集（v3.26.072420+ ruleRoutes/ruleEpisodes）**：
```json
{
  "ruleRoutes": "@js:<JSON.parse(result).vod_play_from.split('$$$').map(function(name, i){return name||'线路'+(i+1)}).join('\\n')",
  "ruleEpisodes": "@js:var d=JSON.parse(result).vod_play_url.split('$$$')[{routeIndex}];d.split('#').map(function(item){var p=item.split('$');return p[0]+'$'+p[1]}).join('\\n')"
}
```

> 📖 完整字段规范详见 [video-audio.md](video-audio.md) 5.6 节"格式④：多线路多集按需采集"

**ruleContent 为空时**：自动 R5 抓取（五种方法从 HTML 提取视频 URL），无需编写规则。

> **完整编写指南**：字段定义、三种格式+多线路多集按需采集字段、兼容性保证详见 [video-audio.md](video-audio.md) 5.6 节

### 方案B 核心原理

```
ruleContent @js: 流程
1. 从详情页 HTML 正则提取所有集数链接
2. 用 java.ajax() 获取第一集 m3u8 地址
3. 组装 HTML 页面（video标签 + 集数按钮）
4. 集数按钮用 XHR 动态加载对应集的 m3u8（按需加载，无需预获取所有）
```

**关键**：Legado 的 WebView 加载 ruleContent 时，`loadDataWithBaseURL(baseUrl, html, ...)` 的 baseUrl 是文章链接 URL，所以 WebView 内的 XHR 同域请求无跨域问题。

### 方案B ruleContent 完整代码

```javascript
@js:
// 1. 从详情页提取所有集数（正则匹配 a.btn-episode）
var eps = [];
var re = /<a class="btn btn-episode" href="([^"]+)">([^<]+)<\/a>/g;
var m;
while ((m = re.exec(result)) != null) {
    eps.push({u: m[1], n: m[2]});
}

// 2. 如果没有集数（单集视频/剧场版），直接提取 m3u8
if (eps.length == 0) {
    var m2 = result.match(/player_aaaa=({[\s\S]*?})<\/script>/);
    if (m2) { JSON.parse(m2[1]).url } else { result }
} else {
    // 3. 获取第一集 m3u8（用 java.ajax，在 ruleContent JS 中执行）
    var fU = 'https://acgfta.com' + eps[0].u;
    var pH = java.ajax(fU);
    var pM = pH.match(/player_aaaa=({[\s\S]*?})<\/script>/);
    var fV = '';
    if (pM) { fV = JSON.parse(pM[1]).url; }

    // 4. 组装 HTML 播放页面
    var h = '<!DOCTYPE html><html><head><meta charset="utf-8">';
    h += '<meta name="viewport" content="width=device-width,initial-scale=1">';
    h += '<style>*{margin:0;padding:0;box-sizing:border-box}';
    h += 'body{background:#111;color:#fff;font-family:sans-serif}';
    h += 'video{width:100%;max-height:45vh;background:#000}';
    h += '.eps{display:flex;flex-wrap:wrap;gap:6px;padding:10px}';
    h += '.ep{padding:5px 10px;background:#333;color:#fff;border:1px solid #555;';
    h += 'border-radius:4px;cursor:pointer;font-size:13px}';
    h += '.ep.on{background:#e74c3c;border-color:#e74c3c}';
    h += '</style></head><body>';
    h += '<video id="v" controls autoplay playsinline src="' + fV + '"></video>';
    h += '<div class="eps">';
    for (var i = 0; i < eps.length; i++) {
        h += '<a class="ep' + (i === 0 ? ' on' : '') + '" href="#" ';
        h += 'onclick="play(' + i + ');return false;">' + eps[i].n + '</a>';
    }
    h += '</div>';

    // 5. XHR 动态加载集数（按需加载，无需预获取所有 m3u8）
    h += '<script>';
    h += 'var eu=' + JSON.stringify(eps.map(function(e){return e.u})) + ';';
    h += 'function play(i){';
    h += 'var x=new XMLHttpRequest();';
    h += 'x.open("GET","https://acgfta.com"+eu[i],true);';
    h += 'x.onload=function(){';
    h += 'var m=x.responseText.match(/player_aaaa=({[\\s\\S]*?})<\\/script>/);';
    h += 'if(m){document.getElementById("v").src=JSON.parse(m[1]).url}';
    h += '};x.send();';
    h += 'var b=document.querySelectorAll(".ep");';
    h += 'b.forEach(function(e){e.classList.remove("on")});';
    h += 'b[i].classList.add("on")';
    h += '}';
    h += '</script></body></html>';
    h;
}
```

### 方案B 关键技术点

| 技术点 | 说明 |
|--------|------|
| `java.ajax()` | 在 ruleContent JS 中获取第一集 m3u8（Rhino 环境可用） |
| `XMLHttpRequest` | WebView 中 JS 发 XHR 获取播放页 HTML（同域无跨域） |
| `loadWithBaseUrl: true` | 必须！设置 WebView baseUrl 为文章 URL，XHR 才能同域请求 |
| 正则提取集数 | `/<a class="btn btn-episode" href="([^"]+)">([^<]+)<\/a>/g` |
| 按需加载 | 只预获取第一集 m3u8，其余集数点击时 XHR 动态加载 |
| 单集兼容 | `eps.length == 0` 时直接提取 m3u8，兼容剧场版等单集视频 |

### 方案A BookSource 配置（备选）

```json
{
    "bookSourceType": 3,
    "ruleToc": {
        "chapterList": "div.anime-episode.active a.btn-episode||div.anime-episode a.btn-episode",
        "chapterName": "@text",
        "chapterUrl": "@href"
    },
    "ruleContent": {
        "content": "@js:var m=result.match(/player_aaaa=({[\\s\\S]*?})<\\/script>/);if(m){JSON.parse(m[1]).url}else{''}"
    }
}
```

## 7.11 三种视频网站类型总结

| 类型 | 代表网站 | 源类型 | 视频地址位置 | 目录规则 |
|------|----------|--------|-------------|----------|
| **单视频型** | 机房哥(jfg) | RssSource | 详情页自定义属性 `playdata` | 无（`"-"`) |
| **iframe嵌入型** | 18AV(mjv006) | RssSource | 详情页 iframe src | 无（`"-"`) |
| **多集动漫型** | 饭团动漫(acgfta) | **RssSource type=2**（推荐）/ BookSource | 播放页 JS 变量 `player_aaaa.url` | type=2 无需目录规则，ruleContent 返回 JSON 数组 |

**源类型选择决策树**：

```
详情页是否有多个视频/集数？
├── 否 → RssSource（type=2 视频，内置播放器）
│   ├── 视频地址在自定义属性 → ruleContent: CSS选择器@属性
│   ├── 视频地址在iframe → ruleContent: @js:正则提取
│   ├── 视频地址需JS渲染 → ruleContent: webJs模式
│   └── 不确定/想省事 → ruleContent 留空（R5 自动抓取五种方法）
└── 是 → 优先 RssSource type=2 内置播放器（JSON数组即多集，ruleRoutes/ruleEpisodes即多线路多集）
    ├── 视频URL可直接提取 → ruleContent: <js>JSON.stringify([{url,title}])</js>
    ├── 多条播放线路 → ruleRoutes/ruleEpisodes 按需采集（v3.26.072420+）
    └── 视频URL需JS动态生成 → BookSource（bookSourceType=3）或 type=0 HTML播放页
```

> **type=2 内置播放器优势**：原生 ExoPlayer 播放（无需 WebView）、上下滑动切换文章、3秒自动隐藏控件、JSON数组即多集、ruleRoutes/ruleEpisodes即多线路多集、ruleContent为空自动R5抓取。完整指南见 [video-audio.md](video-audio.md) 5.6 节。
