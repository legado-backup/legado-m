# 视频/音频地址获取

> 视频播放地址提取、内置播放器调用、m3u8/HLS 流处理、音频地址获取的完整方案。

## 5.1 视频播放地址提取

**方案一：WebView + JS 拦截**

```json
{
  "webView": true,
  "webJs": "setTimeout(function(){ result = document.querySelector('video').src; }, 3000);"
}
```

WebView 渲染页面后，通过 JS 提取 `<video>` 标签的 src。

**方案二：嗅探网络请求**

```javascript
// 在 webJs 中拦截网络请求
// Legado 的 WebView 会自动嗅探 .m3u8/.mp4 等视频地址
```

## 5.2 调用内置视频播放器

```javascript
// JS 规则中
openVideoPlayer(videoUrl, videoTitle, true);  // true=悬浮窗
```

## 5.3 m3u8/HLS 流处理

### 方案一：直接返回 m3u8 地址（简单场景）

直接返回 m3u8 地址，Legado 的 ExoPlayer 原生支持 HLS：
```
result = 'https://example.com/video/index.m3u8';
```

⚠️ **限制**：此方案仅适用于 Legado 内置播放器能直接播放的场景。对于需要自定义播放器界面的视频站，应使用方案二。

### 方案二：自定义 HLS.js 播放器（推荐）

> **已提供完整模板文件，后续开发直接复用！**

**模板位置**：[templates/hls-video-player.html](../../templates/hls-video-player.html)

**完整功能**（V2.20260606.1）：
- 视频标题显示（`{{videoTitle}}` 模板变量）
- HLS.js v1.4.12 稳定版 + 完整缓冲配置
- 进度条系统（播放进度 + 缓冲进度）
- 快进快退（±30s/1m/3m）
- 倍速播放（1x/3x/5x/10x/15x）
- 全屏控制 + 状态监听
- **横竖屏反转（90°/180°/270° 旋转）**
- 上下集切换（多视频源）
- 错误自动重试
- 响应式设计

**使用示例**：
```javascript
// ruleContent 提取视频标题 + 地址 + 拼装播放器

// 步骤1：提取视频标题（可选）
class.video-title@text
<js>
var videoTitle = result;
java.put('videoTitle', videoTitle);
result;
</js>

// 步骤2：提取视频地址
class.player-wrapper@all
<js>
var videoTitle = java.get('videoTitle') || '';
var reg = /[?&]url=([^"&\s]+)/i;
var match = result.match(reg);
var videoUrl = match ? match[1] : '';

// 步骤3：拼装 HTML（粘贴模板内容并替换变量）
var html = '粘贴 templates/hls-video-player.html 的完整内容';
html = html.replace('{{videoTitle}}', videoTitle);
html = html.replace('{{result}}', videoUrl);
result = html;
</js>
```

**模板变量**：
| 变量 | 用途 | 示例提取方式 |
|------|------|--------------|
| `{{videoTitle}}` | 视频标题 | `h1.post-title@text` / `.video-name@text` |
| `{{result}}` | 视频地址 | 正则提取 `/[?&]url=([^"&\s]+)/i` |

**type 必须为 0**：
```json
{
  "sourceType": 0,  // 网页模式，WebView 渲染 HTML 播放器
  "ruleContent": { "content": "...完整模板..." }
}
```

⚠️ **禁止 type=2**：type=2 会尝试用内置播放器直接播放 ruleContent 返回的字符串，导致失败。

**后续开发规范**：
- 新建视频源时，**必须优先使用完整模板**
- 保持所有公共功能不变（进度条、倍速、全屏、上下集）
- 仅调整视频 URL 提取逻辑和 config 配置

### 方案三：自动抓取视频播放器（V1）

> **已提供完整模板文件，适用于视频 URL 可从 HTML 直接提取的场景。**

**模板位置**：[templates/auto-video-player.html](../../templates/auto-video-player.html)

**核心功能**（V1.20260606.1）：
- 四种视频提取方法（DOM提取/正则提取/JS变量提取/XHR拦截）
- 分页加载（列表模式/拼接模式）
- 自动/手动加载模式
- Legado JSBridge 绕过 CORS
- 完整播放器控制（进度条/快进快退/倍速/全屏）

**使用示例**：
```javascript
// ruleContent 中拼装 V1 模板
// 模板中的 Legado 变量会由规则引擎自动替换
let html = '粘贴 templates/auto-video-player.html 的完整内容';
result = html;
```

**type 必须为 0**：
```json
{
  "sourceType": 0,
  "ruleContent": { "content": "...完整模板..." }
}
```

### 方案四：注入式播放器优化脚本（V3）

> **适用于视频 URL 需 JS 运行时生成、播放器带加密参数的场景。**

**模板位置**：[templates/inject-video-player.js](../../templates/inject-video-player.js)

**核心功能**（V3.20260606.1）：
- 6种播放器检测（Video.js/DPlayer/ArtPlayer/XGPlayer/EasyPlayer/Plyr）
- 缓冲优化（destroy+recreate 策略）
- 广告拦截（事件拦截模式，安全无崩溃）
- 净化模式（隐藏非视频元素）
- XHR/Fetch 拦截获取视频 URL
- 卡顿检测+自动降级

**使用方式**：作为 webJs 注入
```json
{
  "sourceType": 0,
  "ruleContent": {
    "webJs": "粘贴 templates/inject-video-player.js 的完整内容"
  }
}
```

⚠️ **V3 是 IIFE 注入脚本**，不是完整 HTML 页面，通过 webJs 注入到目标网页中执行。

## 5.4 音频地址

```json
{
  "bookSourceType": 1,  // 音频类型
  "ruleContent": {
    "content": "audio@src"
  }
}
```

## 5.5 Vue.js SPA 加密视频站特殊处理

> 基于小黄书视频站实测经验。当视频站使用Vue.js SPA + 多层加密时，传统CSS选择器完全不可用。

### 识别特征

| 特征 | 说明 |
|------|------|
| 首页返回空壳HTML | 页面内容通过JS加密渲染（XOR/deflate等） |
| CSS class名随机化 | Vue组件使用 `generateUniqueID()` 生成随机class |
| 视频链接无 `<a href>` | 使用Vue的 `@click="toLink"` 事件处理 |
| API请求参数加密 | AES/CBC等加密请求参数 |
| 详情URL含加密ID | vod_id经DES/ECB加密后拼入URL |

### 解决方案：解密内联数据 + JSONPath

当CSS选择器不可用时，必须解密页面内联数据，用JSONPath提取字段：

```json
{
  "type": 2,
  "ruleArticles": "<js>解密APP.Index('token')...返回JSON数组</js>",
  "ruleTitle": "$.vod_name",
  "ruleLink": "<js>DES加密vod_id拼接详情URL</js>",
  "ruleImage": "<js>补全图片URL前缀</js>",
  "ruleDescription": "$.vod_duration",
  "ruleContent": "<js>正则提取m3u8地址</js>"
}
```

⚠️ **RssSource字段是扁平的**：`ruleArticles`/`ruleTitle`/`ruleLink`/`ruleImage`/`ruleDescription`/`rulePubDate`/`ruleContent` 都是RssSource实体的独立String?字段，不是嵌套在ruleArticles对象中！

### 视频播放地址提取

加密视频站的播放地址通常在WebView渲染后的DPlayer配置中，可通过以下方式提取：

1. **正则匹配m3u8**：`result.match(/https?:\/\/[^\s'"<>]+\.m3u8[^\s'"<>]*/)`
2. **匹配DPlayer配置**：`result.match(/url\s*:\s*['"]([^'"]+\.m3u8[^'"]*)['"]/)`
3. **webJs获取**：从WebView中直接读取DPlayer实例的视频地址

### type=2 视频源的 ruleContent 行为

> 基于源码验证（VideoPlay.kt L161-224）

**type=2 时 ruleContent 的执行逻辑**：

1. `ReadRss.kt`：type=2 直接跳转 `VideoPlayerActivity`，不经过 `ReadRssActivity`
2. `VideoPlay.kt`：**会检查 ruleContent 是否为空**
   - ruleContent 为空 → 直接用 `rssArticle.link` 作为视频URL
   - ruleContent 不为空 → 先用 `Rss.getContent()` 解析正文获取真实视频URL

**所以 type=2 + ruleContent 是合法组合**：当视频链接需要从详情页提取时，设置 type=2 + ruleContent。VideoPlay 会先请求详情页，用 ruleContent 提取视频URL，再传给 ExoPlayer 播放。

⚠️ **type=0 + 自定义HLS.js播放器**：使用自定义HTML播放器时确实需要 type=0（WebView渲染HTML），但 type=2 + ruleContent返回m3u8地址也是可行的方案（用内置ExoPlayer播放）。

## 5.6 type=2 内置视频播放器内容规则编写指南

> 当订阅源 `type=2`（视频）且使用内置视频播放器时，`ruleContent` 的编写指南。
> 内置播放器基于 GSY + ExoPlayer，支持 m3u8/HLS、mp4 等格式，无需 WebView。
> 代码实现：`VideoPlay.kt` 的 `parseRssEpisodes()` / ruleRoutes+ruleEpisodes 按需采集 / R5 分支。

### 何时使用 type=2（内置播放器）vs type=0（WebView）

| 对比项 | type=2 内置播放器 | type=0 WebView 播放器 |
|--------|------------------|----------------------|
| 播放引擎 | ExoPlayer（原生） | HLS.js（WebView） |
| ruleContent 返回 | 视频URL/JSON数组 | 完整HTML页面 |
| 多集支持 | ✅ JSON数组/多行URL | ✅ JS数组 |
| 多线路支持 | ✅ ruleRoutes字段(v3.26.072420+) | ❌ 需自行实现 |
| 上下滑动切换文章 | ✅ ViewPager2 | ❌ |
| 3秒自动隐藏控件 | ✅ 单击切换显隐 | ❌ |
| 缓冲进度条 | ✅ 灰色缓冲+白色播放 | ✅ |
| 倍速/快进快退 | ✅ | ✅ |
| 适用场景 | 视频URL可直接提取 | 需自定义播放器界面/复杂JS |

### ruleContent 三种格式 + 多线路多集按需采集字段

#### 格式①：单 URL（最简，100%向后兼容）

ruleContent 返回单个视频 URL 字符串：

```
https://example.com/video/episode1.m3u8
```

CSS 简写：
```
video source@src
```

JS 写法：
```javascript
<js>
result = 'https://example.com/video/episode1.m3u8';
</js>
```

**适用**：单集视频，视频URL可直接从详情页提取。

#### 格式②：多行 URL（简写多集）

ruleContent 返回多行 URL，每行一个视频地址：

```
https://example.com/video/ep1.m3u8
https://example.com/video/ep2.m3u8
https://example.com/video/ep3.m3u8
```

CSS 简写（页面有多个 `<source>` 标签时自动返回多行）：
```
video source@src
```

**判定条件**：每行必须以 `http://`、`https://` 或 `/` 开头（相对路径自动拼接 baseUrl）。

**集数标题**：自动生成"第1集"、"第2集"...

**适用**：多集视频，每集 URL 可通过同一CSS规则批量提取。

#### 格式③：JSON 数组（完整多集，支持自定义标题）

ruleContent 返回 JSON 数组，每个对象代表一集：

```json
[
  {"url": "https://example.com/video/ep1.m3u8", "title": "第1集"},
  {"url": "https://example.com/video/ep2.m3u8", "title": "第2集"},
  {"url": "https://example.com/video/ep3.m3u8", "title": "大结局"}
]
```

JS 写法：
```javascript
<js>
JSON.stringify([
  {url: 'https://example.com/video/ep1.m3u8', title: '第1集'},
  {url: 'https://example.com/video/ep2.m3u8', title: '第2集'},
  {url: 'https://example.com/video/ep3.m3u8', title: '大结局'}
]);
</js>
```

**JSON 对象字段定义**：

| 字段 | 类型 | 必须 | 缺省值 | 说明 |
|------|------|------|--------|------|
| `url` | String | ✅ 必须 | 无（缺失则该集被过滤） | 播放地址（m3u8/mp4/mpd），相对路径自动拼接 baseUrl |
| `title` | String | ❌ 可选 | "第N集" | 集数标题，显示在左下角集数选择器 |
| `duration` | Long | ❌ 可选 | 0（预留） | 时长（毫秒，未来扩充） |
| `cover` | String | ❌ 可选 | ""（预留） | 封面 URL（未来扩充） |

**适用**：需要自定义集数标题的多集视频。

#### 格式④：多线路多集按需采集（v3.26.072420+ 新增）

> ⚠️ v3.26.072420+ 起，多线路多集改用 `ruleRoutes` + `ruleEpisodes` 两个字段实现**按需采集**，不再通过 ruleContent 返回嵌套 JSON 全量采集。

**架构对比**：

| 模式 | 字段 | 采集方式 | 线程压力 |
|------|------|---------|---------|
| 旧模式（已废弃） | ruleContent 嵌套JSON | 一次性全量采集所有线路所有集数的视频地址 | 大 |
| 新模式（推荐） | ruleRoutes + ruleEpisodes | 用户切换线路/集数时按需采集视频地址 | 小 |

**两个字段职责**：

| 字段 | 作用 | 返回格式 | 示例 |
|------|------|---------|------|
| `ruleRoutes` | 从详情页采集线路列表（线路名） | 多行文本，每行一个线路名 | `线路1\n线路2\n线路3` |
| `ruleEpisodes` | 从详情页采集集数列表（集数标题+播放页URL） | 多行文本，每行 `标题$URL` | `第1集$/v_play/xxx.html\n第2集$/v_play/yyy.html` |

**关键区别**：`ruleEpisodes` 采集的是**播放页 URL**（非视频流地址），用户切换集数后由 `VideoUrlExtractor.extractVideoUrlForEpisode` 从播放页按需提取真实视频地址（三层降级：MacCMS播放页解析→DOM解析→WebView抓包）。

**占位符支持**：

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{routeIndex}` | 当前线路索引（0-based） | 用户选择"线路1"时，routeIndex=0 |
| `{routeIndex+1}` | 当前线路索引（1-based） | 用户选择"线路1"时，routeIndex+1=1 |

**MacCMS JSON API 模板标准写法**（vod_play_from / vod_play_url）：

```json
{
  "ruleRoutes": "@js:<JSON.parse(result).vod_play_from.split('$$$').map(function(name, i){return name||'线路'+(i+1)}).join('\\n')",
  "ruleEpisodes": "@js:var d=JSON.parse(result).vod_play_url.split('$$$')[{routeIndex}];d.split('#').map(function(item){var p=item.split('$');return p[0]+'$'+p[1]}).join('\\n')"
}
```

**MacCMS HTML 模板标准写法**（CSS 选择器）：

```json
{
  "ruleRoutes": ".module-player-list .module-player-tab-name@text",
  "ruleEpisodes": ".module-player-list .module-player-list-content:eq({routeIndex}) a@text&&href"
}
```

**使用规范**：
1. 仅 type=2 视频源使用，其他类型源忽略
2. 使用新字段后，`ruleContent` 回归单集视频 URL，不再支持返回嵌套 JSON
3. 用户切换线路时，App 调用 `Rss.getEpisodesAwait(ruleEpisodes, routeIndex)` 重新采集新线路集数
4. 视频地址由 `VideoUrlExtractor.extractVideoUrlForEpisode` 三层降级采集
5. 老源兼容：未配置 `ruleRoutes`/`ruleEpisodes` 的源仍使用 `ruleContent` 模式

**反模式（禁止）**：
- ❌ 在 `ruleContent` JS 中一次性采集所有线路所有集的播放页 URL
- ❌ 在 `ruleEpisodes` 中直接采集视频流地址（m3u8/mp4），应只采集播放页 URL
- ❌ 硬编码镜像站 URL 列表（应由 `ruleRoutes` 动态采集）

**适用**：同一视频有多条播放线路（不同CDN/不同清晰度/备用源），且希望按需采集减少网络消耗。

> 📖 完整字段规范详见 [SKILL.md](../../SKILL.md) "多线路多集按需采集标准写法"章节

### ruleContent 为空时：R5 自动抓取

当 `ruleContent` 为空且 `type=2` 时，系统自动从文章页面 HTML 中抓取视频链接：

1. 请求文章页面 URL（`rssArticle.link`）
2. 用五种方法自动提取视频 URL（按精确度优先级）：
   - ① `<video>`/`<source>` 标签 src 属性（jsoup，最精确）
   - ② OG/Meta 标签（`og:video`，开放图谱协议）
   - ③ `<script>` 标签内 JSON 中的视频 URL（`"url":"...m3u8"`）
   - ④ JS 变量赋值（`var url = "...m3u8"`）
   - ⑤ 正则兜底匹配（`.m3u8`/`.mp4` 结尾的 URL）
3. 播放器页面 URL 自动解析（如 `/player/?url=https%3A%2F%2F...m3u8`）
4. 提取到多个 URL 时自动构建多集列表

**适用**：视频 URL 嵌入在 HTML 中，无需手动编写提取规则。

**限制**：无法提取需要 JS 运行时动态生成的 URL（需用 type=0 WebView 模式）。

**代码实现**：`VideoUrlExtractor.kt` 的 `extract()` 方法。

### 内置视频播放器功能清单

| 功能 | 说明 |
|------|------|
| 抖音风格沉浸式布局 | 竖屏全屏播放，左下角标题+线路/集数选择器，右侧功能按钮列 |
| 上下滑动切换文章 | 从订阅源文章列表进入后，上下滑动切换上一篇/下一篇文章视频 |
| 分页加载 | 滑到最后一个文章时自动异步加载下一页文章列表 |
| 预缓冲 | 当前视频播放到80%时后台预加载下一文章页面HTML |
| 位置记忆 | 退出返回列表时自动滚动到正在看的文章位置 |
| 3秒自动隐藏控件 | 控件显示后3秒无操作自动隐藏进入纯净播放态，单击屏幕重新显示 |
| 缓冲进度条 | 底部进度条显示缓冲进度（灰色）+ 播放进度（白色） |
| 倍速播放 | 1x/2x/3x/5x/10x/15x 六档可选 |
| 快进快退 | 可配置时间（10/30/60/90/120秒，默认60秒） |
| 多线路切换 | 左下角线路选择器（多线路时自动显示） |
| 多集切换 | 左下角集数选择器（多集时自动显示） |
| 调试面板 | 播放失败时显示错误码/原因/建议 |
| 横屏全屏 | 支持横屏全屏播放，双指拉伸触发全屏 |

### 兼容性保证

1. **现有单 URL 订阅源无需修改**：自动走格式①（100%向后兼容）
2. **格式判定优先级**：JSON数组（`[`开头）→ 多行URL（每行合法URL）→ 单URL（多线路多集改用 ruleRoutes/ruleEpisodes 独立字段，不再通过 ruleContent 嵌套JSON判定）
3. **JSON 解析失败回退**：非合法JSON自动回退到多行URL或单URL模式
4. **HTML含换行不会误判**：HTML标签不以 `http://`/`https://` 开头，不会误判为多行URL
5. **相对路径自动拼接**：所有URL支持相对路径，自动拼接文章页面URL作为baseUrl
6. **url 为空的对象被过滤**：JSON数组中 `url` 为空的集数会被自动过滤

### 常见问题

#### 问题1：内置播放器返回 404 错误（CDN 防盗链）

**问题现象**：type=2 内置播放器（ExoPlayer）请求视频 URL 返回 HTTP 404，但同一 URL 在 type=0 WebView 模式（HLS.js 播放器）下可以正常播放。

**根因**：CDN 防盗链验证失败。部分视频 CDN 会校验请求头中的 `Referer` 字段，若 Referer 不匹配文章页面域名则返回 404。内置播放器（ExoPlayer）默认不携带 Referer，而 WebView 模式下浏览器自动携带 Referer。

**修复方案**（已实现，源码验证 2026-07-12）：

系统自动注入 Header 解决防盗链问题，**源开发者无需处理**，但需了解以下机制：

1. **ruleContent 不为空分支**（VideoPlay.kt L219）：
   - Header 来自 `AnalyzeUrl(rssArticle.link).headerMap`
   - 通过 `player.mapHeadData = analyzeUrl.headerMap` 传递给播放器
   - ExoPlayerManager.initVideoPlayer 调用 `ExoPlayerHelper.setDefaultHeaders(headers)` 注入到 `okhttpDataFactory`

2. **R5 自动抓取分支**（VideoPlay.kt L263-268）：
   - 自动注入 `Referer = rssArticle.link`（文章页面 URL），模拟 WebView 行为
   - 判断逻辑：`if (!playAnalyzeUrl.headerMap.any { it.key.equals("Referer", ignoreCase = true) })` 避免覆盖用户已配置的 Referer
   - fallback URL 分支（L300-305）同样注入 Referer

3. **Header 注入实现**（ExoPlayerManager.kt L60-64 → ExoPlayerHelper.kt L130-132）：
   ```kotlin
   // ExoPlayerManager.kt
   model.getMapHeadData()?.takeIf { it.isNotEmpty() }?.let { headers ->
       ExoPlayerHelper.setDefaultHeaders(headers)
   }
   // ExoPlayerHelper.kt
   fun setDefaultHeaders(headers: Map<String, String>) {
       okhttpDataFactory.setDefaultRequestProperties(headers)
   }
   ```

**源开发者需知**：
- 若视频 URL 需要特殊 Header（如自定义 UA/Cookie/Referer），在 RssSource 的 `header` 字段中配置，系统会自动注入
- R5 自动抓取分支会自动注入 `Referer = 文章页面URL`，无需手动配置
- 若仍遇 404，检查 CDN 是否校验其他 Header（如 Origin），在 `header` 字段中补充

#### 问题2：singleUrl 模式不注入 Referer

**现象**：singleUrl 模式（RssSource.singleUrl=true）下，内置播放器不自动注入 Referer。

**原因**：YAGNI 原则。singleUrl 模式下 URL 本身就是视频地址，没有"文章页面 URL"作为 Referer 来源。`rssArticle.link` 在 singleUrl 模式下就是视频 URL 本身，用它作 Referer 无意义。

**解决方案**：若 singleUrl 模式下视频 URL 需要防盗链 Header，在 RssSource 的 `header` 字段中手动配置 `Referer`。

#### 问题3：自定义 Headers 配置方法

**方法1：RssSource header 字段（推荐）**

在 RssSource JSON 中配置 `header` 字段（JSON 字符串），系统自动注入到所有请求（包括内置播放器）：

```json
{
  "header": "{\"Referer\":\"https://example.com/\",\"User-Agent\":\"Mozilla/5.0...\",\"Cookie\":\"session=xxx\"}"
}
```

**方法2：ruleContent 中通过 AnalyzeUrl 传递**

ruleContent 不为空时，系统通过 `AnalyzeUrl(rssArticle.link)` 解析 header，自动传递给播放器。AnalyzeUrl 会处理 URL 中的 Header 参数（如 `,{headers:{...}}` 后缀）。

**方法3：ExoPlayerHelper "🚧" 编码（内部机制，源开发者不直接使用）**

ExoPlayerHelper 内部有 `SPLIT_TAG = "🚧"`（U+1F6A7）编码方式：
- `createMediaItem(url, headers)` 将 URL 和 headers JSON 拼接为 `url + "🚧" + GSON.toJson(headers)`
- `resolvingDataSource` 拦截请求时拆分出真实 URL 和 headers

⚠️ **注意**：Exo2MediaPlayer（type=2 使用的播放器）使用 no-op resolver `{ it }`，**不处理 "🚧" 编码**。实际 Header 注入通过 `setDefaultHeaders` 方法。此编码方式是 ExoPlayerHelper 的内部设计，源开发者不直接使用，了解即可。
