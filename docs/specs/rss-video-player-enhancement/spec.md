# spec.md — 订阅源视频播放器增强

## Intent

用户在使用订阅源（RssSource type=2）内置视频播放器时发现 5 类问题：
1. **多集无法选择**：视频网站通常有多集，但内置播放器只取单 URL，无法切换集数
2. **m3u8 播放失败无提示**：同为 m3u8 地址，有的能播有的不能，且失败时无任何错误反馈，用户不知原因
3. **布局不如旧 WebView 方案**：用户原有 WebView 方案的订阅源内容规则布局丰富，内置播放器页面元素单一
4. **使用日志有异常**：基于用户使用日志分析，存在 Mixed Content、CryptoException、SQLiteBlobTooBigException 等异常需优化
5. **内容规则空时无法自动抓取**：用户只填链接规则+type=2 未填内容规则时，系统直接用文章 URL 作为播放地址导致播放失败，应自动从文章页面抓取视频链接

目标：让订阅源内置播放器支持多集选择、显示播放失败原因、学习旧布局样式、优化日志异常、内容规则空时自动抓取视频链接，达到"可用且好用"。

## Scope

### In Scope（本次实施）

| 需求 | 范围 |
|------|------|
| **R1 多集选择** | 扩展 RssSource 内容规则支持返回多集列表；VideoPlay 解析多集；VideoPlayerActivity 显示集数 UI 并支持切换 |
| **R2 调试日志** | Exo2MediaPlayer 添加 onPlayerError 回调；VideoPlayerActivity 添加可切换的调试日志面板，显示 URL/Header/错误类型/错误消息 |
| **R3 布局学习** | 基于 auto-video-player.html 模板学习布局，内置播放器新增订阅源功能区（播放地址展示/快进快退/倍速/调试按钮/多集选择/视频简介/调试面板）；**布局优化**：按钮统一尺寸+圆角样式、视频地址多行换行+复制按钮、title 来源修复（单URL/多行URL模式用 rssArticle.title） |
| **R4 日志优化** | 针对 Mixed Content(HTTP m3u8)、CryptoException、SQLiteBlobTooBigException、SocketException 优化 |
| **R5 自动抓取** | 新建 VideoUrlExtractor，ruleContent 为空且 type=2 时自动从文章 HTML 抓取视频链接（正则+video标签+Meta+JS变量+script JSON 五种方法）；**Header 修复**：修复 Exo2MediaPlayer Header 丢失导致 404 Bug，自动注入 Referer |

### Out of Scope

- 不重构 ExoPlayer 整体架构（仅扩展错误回调和多集支持）
- 不修改 BookSource 视频播放逻辑（书源多集机制已完善，仅扩展 RssSource）
- 不修改 RssSource 数据库表结构（不新增 videoType 字段，多集通过 ruleContent 返回格式区分）
- 不实现 R3 分页控制（HTML 模板的 page-controls），订阅源场景无分页需求

## Approach

### R1 多集选择播放

**现状分析**（源码深度分析结论）：
- `VideoPlay.kt` line 186-249：RssSource 分支只取单个 URL
- `VideoPlayerActivity.kt` line 222-244：`book==null` 时集数/卷 UI 全部隐藏（订阅源 book 必为 null）
- BookSource 通过 `toc/volumes/episodes` 支持多集，RssSource 无此机制

**方案**：扩展 ruleContent 返回格式，支持多集

内容规则写法（三种，向后兼容）：
1. **单 URL（现有）**：`ruleContent` 返回单个 URL 字符串 → 单集播放（向后兼容）
2. **多 URL（每行一个）**：`ruleContent` 返回多行 URL → 自动解析为多集，标题为"第N集"
3. **JSON 数组**：`ruleContent` 返回 `[{"title":"第1集","url":"https://..."},...]` → 解析为带标题的多集

VideoPlay 解析逻辑（RssSource 分支）：
```
content = Rss.getContent(...)
if content 以 "[" 开头 → JSON 数组解析为 rssEpisodes
else if content 含多行(\n) → 按行分割为 rssEpisodes
else → 单 URL（现有逻辑）
```

VideoPlayerActivity 修改：
- `book==null` 时检查 `VideoPlay.rssEpisodes`，不为空则显示集数 UI
- 集数点击切换：调用 `VideoPlay.playRssEpisode(index)`

**内容规则编写指南**（用户核心诉求：明确 ruleContent 写法 + 编写便捷性 + 兼容性）：

订阅源 type=2（视频）时，ruleContent 规则返回的内容支持四种格式（向后兼容）：

| 模式 | ruleContent 返回值 | 多集支持 | 编写方式 |
|------|-------------------|---------|---------|
| ① 单 URL（现有兼容） | 单个 URL 字符串 | ❌ 单集 | CSS/XPath/JSONPath/正则/JS 任选，返回单个 URL |
| ② 多行 URL（简写多集） | 多行 URL（每行 http/https 开头） | ✅ 自动多集 | 规则返回多个 URL，用 `\n` 分隔 |
| ③ JSON 数组（完整多集） | `[{"url":"...","title":"..."}]` | ✅ 带标题多集 | JS 规则返回 JSON 数组对象 |
| ④ 嵌套 JSON（多线路多集，R3 新增） | `[{"name":"线路1","episodes":[...]}]` | ✅ 多线路+多集 | JS 规则返回嵌套 JSON 数组 |

> **模式④ R3 多线路格式**：JSON 数组首元素含 `episodes` 字段时判定为多线路格式，解析为 `List<RssRoute>`。详见 [design.md 1.5.1 节](./design.md#151-r3-多线路格式嵌套-json)。
> **完整编写指南**（含 type=2 vs type=0 对比、四种格式详解、R5 自动抓取、功能清单、兼容性保证）：[video-audio.md 5.6 节](../../../.trae/skills/legado-source-creator/references/special-scenarios/video-audio.md)

**JSON 数组对象结构定义**（模式③，JS 编写场景，用户核心诉求 F4/F5/F6）：

```
[
  {
    "url": "https://example.com/ep01.m3u8",   // 必须：播放地址
    "title": "第1集"                            // 可选：集数标题，缺省"第N集"
  },
  {
    "url": "https://example.com/ep02.m3u8",
    "title": "第2集"
  }
]
```

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `url` | String | ✅ 必须 | 播放地址（m3u8/mp4/mpd 等），相对路径自动拼接 baseUrl |
| `title` | String | ❌ 可选 | 集数标题，缺省为"第N集" |

**JS 编写示例**（推荐方式，利用 Legado 内置 Rhino JS 引擎）：

```javascript
// 示例1：从页面解析多个 video source，返回 JSON 数组
var videos = document.querySelectorAll("video source");
var result = [];
for (var i = 0; i < videos.length; i++) {
    result.push({
        url: videos[i].src,
        title: "第" + (i+1) + "集"
    });
}
JSON.stringify(result);

// 示例2：从播放列表解析多集
var playlist = document.querySelectorAll(".playlist a");
var result = [];
for (var i = 0; i < playlist.length; i++) {
    result.push({
        url: playlist[i].href,
        title: playlist[i].innerText
    });
}
JSON.stringify(result);
```

**CSS/XPath 简写示例**（模式②，无需 JS）：

```
// CSS：返回多个 video source 的 src（自动多行）
video source@src

// XPath：返回多个播放链接
//source/@src
```

**兼容性保证**：
- 现有单 URL 订阅源无需修改，自动走模式①（向后兼容）
- 多行 URL 模式②仅当每行都是合法 URL（http/https/相对路径）才触发，HTML 含换行不会误判
- JSON 数组模式③仅当 content 以 `[` 开头才触发，普通 URL 不会误判

### R2 m3u8 播放失败分析+调试日志

**现状分析**（源码深度分析结论）：
- `Exo2MediaPlayer.kt`：`prepareAsyncInternal()` 构建 ExoPlayer 但**无 onPlayerError 回调**
- `ExoPlayerManager.kt` line 95：`catch (e: Exception) { AppLog.put("ExoPlayerManager: init", e) }` → 错误只记 AppLog，用户不可见
- 播放失败时用户只看到"黑屏转圈"，不知原因

**m3u8 播放失败可能原因**（日志分析+源码分析）：
1. **Header 丢失**：AnalyzeUrl 处理后的 header 未正确传入 ExoPlayer
2. **Mixed Content**：HTTP m3u8 在某些场景被阻止（内置播放器非 WebView，理论上不受限，但 ExoPlayer cleartext 需配置）
3. **SSL 证书**：自签名证书导致握手失败
4. **Cookie 丢失**：需要 Cookie 的 m3u8 地址播放失败
5. **URL 编码**：含特殊字符的 URL 未正确编码
6. **m3u8 格式问题**：非标准 m3u8（如加密 m3u8、多码率 m3u8）解析失败

**方案**：
1. `Exo2MediaPlayer` 实现 `Player.Listener.onPlayerErrorChanged` 回调，捕获 PlaybackException
2. 错误信息通过回调链传递到 VideoPlayerActivity
3. VideoPlayerActivity 添加**调试日志面板**（默认隐藏，点击切换显示）：
   - 最终播放 URL（AnalyzeUrl 处理后）
   - 请求 Header
   - 错误类型（PlaybackException errorCode）
   - 错误消息（cause message）
   - HTTP 状态码（如能获取）

### R3 学习旧订阅源布局样式（基于 auto-video-player.html 模板）

**素材来源**：用户旧 WebView 方案模板 `.trae/skills/legado-source-creator/templates/auto-video-player.html`（1308 行），包含完整视频播放器 HTML 布局。

**HTML 模板布局结构**（10 个区块）：①标题 ②播放器 ③播放地址展示 ④功能区(快进快退/倍速/全屏/反转) ⑤视频源切换(多集) ⑥分页控制 ⑦切换按钮 ⑧消息区 ⑨调试信息 ⑩描述区。

**内置播放器现有布局对比**（`activity_video_player.xml`）：TitleBar✅ + VideoPlayer✅ + data区(仅书源) + chapters_container(仅书源)。缺失：③播放地址展示、④功能区、⑤多集选择(订阅源)、⑦调试按钮、⑧⑨调试面板、⑩视频简介(订阅源)。

**方案**：在 VideoPlayer 下方、chapters_container 之前新增**订阅源功能区** `rss_video_panel`（book==null 时显示），包含：
1. ③播放地址展示（`tv_video_url`）：显示当前播放 URL
2. ④功能区（`video_controls_bar`）：←30s/←10s/10s→/30s→ 快进快退按钮 + 倍速 Spinner(1x/3x/5x/10x/15x) + 调试按钮
3. ⑤多集选择（`rss_episodes_container`）：上一集 + 集数 Spinner + 下一集（与 R1 联动）
4. ⑩视频简介（`tv_rss_description`）：订阅源描述
5. ⑧⑨调试面板（`debug_panel`）：与 R2 联动，默认隐藏

**不实现**：⑥分页控制（订阅源场景无分页需求，Out of Scope）、全屏/反转按钮（GSY 播放器已自带全屏，反转非必需）。

详细 XML 布局和样式定义见 design.md 3.3-3.5 节。

### R4 使用日志异常分析优化

**日志深度分析结论**（基于 temp\tmp\Downloadslogs.(2)..zip，logs2/ 目录 46 appLog + logcat + 20 crash，覆盖 07-08~07-10）：

| # | 异常 | 频次/时间 | 状态 | 优化方向 |
|---|------|----------|------|---------|
| 1 | MaterialCardView 崩溃 | 07-08 11:44 | ✅ 已修复 | 前序 spec（CardView 替换） |
| 2 | Room schema 不匹配 | 07-08 12:18 | ✅ 已修复 | version 92→93 |
| 3 | **ForegroundServiceDidNotStartInTimeException** | 07-08 23:39 crash | ⚠️ **P0 新发现** | VideoPlayService.startForegroundNotification 的 try-catch 吞异常未 stopSelf |
| 4 | **NullPointerException (RssSourceAdapter)** | 07-08 20:00 crash | ⚠️ **新发现** | dragSelectCallback.getItemId 空指针 |
| 5 | **SyntaxError: Empty JSON string** | 07-08 23:49 大量 | ⚠️ **新发现** | JS 脚本 JSON.parse 空字符串 |
| 6 | CryptoException 解密失败 | 多处（图片解密） | ⚠️ 待处理 | IllegalBlockSizeException，图片解密错误处理 |
| 7 | SQLiteBlobTooBigException | 07-08 06:35 | ⚠️ 待处理 | Row too big，缓存数据过大 |
| 8 | SocketException Connection reset | 多处（rss+图片） | ⚠️ 待处理 | 网络连接重置，CronetException |
| 9 | Mixed Content | 07-08 22:11 | ⚠️ 待处理 | WebView HTTPS→HTTP m3u8 |
| 10 | JobCancellationException | 多处 | ℹ️ 低优 | 协程取消，需评估是否正常生命周期 |
| 11 | **ExoPlayer 播放错误无日志** | N/A | ⚠️ R2 核心 | 播放失败完全无错误记录（Grep 无匹配） |

### R5 自动视频链接抓取（ruleContent 为空时）

**现状分析**（源码深度分析结论）：
- `VideoPlay.kt` line 199-223：`ruleContent.isNullOrBlank()` 分支直接用 `rssArticle.link`（文章 URL）作为播放地址
- 文章 URL 不是视频 URL（如 `https://example.com/video/123.html`），直接播放必然失败
- 用户旧 WebView 方案用 auto-video-player.html 模板的四种方法自动抓取视频链接，但内置播放器（type=2）走原生 Kotlin 不经 WebView，无此能力

**方案**：新建 `VideoUrlExtractor.kt`，在 ruleContent 为空且 type=2 时自动从文章 HTML 抓取视频链接

提取方法（参考 auto-video-player.html 四种方法，适配 Kotlin 原生环境）：

| 方法 | 实现方式 | 适用场景 |
|------|---------|---------|
| ① 正则提取 | Regex 匹配 `https?://...m3u8/mp4` | 通用，覆盖大多数场景 |
| ② video/source 标签 | jsoup 解析 `<video>`,`<source>` src/data-src | 标准 HTML5 视频页面 |
| ③ OG/Meta 提取 | jsoup 解析 `<meta property="og:video">` content | 支持开放图谱协议的站点 |
| ④ JS 变量提取 | Regex 匹配 `var/let/const xxx = "http...m3u8/mp4"` | 视频地址在 JS 变量中的场景 |

**不实现**：XHR/Fetch 拦截（auto-video-player.html 方法4），因原生 Kotlin 环境无法拦截浏览器网络请求，这是 WebView JS 独有能力。

**VideoPlay.kt 修改逻辑**（`ruleContent.isNullOrBlank()` 分支）：
```
1. 获取文章页面 HTML（AnalyzeUrl.getStrResponseAwait，复用 Rss.getContentAwait 模式）
2. VideoUrlExtractor.extract(html, baseUrl) 综合提取视频 URL（4种方法去重）
3. if (urls.size == 1) → 单 URL 直接播放
   else if (urls.size > 1) → 构建 JSON 数组，走 parseRssEpisodes 多集逻辑（R1 复用）
   else → 回退当前逻辑（用 rssArticle.link）+ AppLog 提示未找到视频 URL
```

**便捷性**：用户只需填写订阅源链接规则+type=2，不填内容规则，系统自动抓取视频链接，降低订阅源编写门槛。

**兼容性**：
- 现有填写了 ruleContent 的订阅源不受影响（走原有分支）
- 现有 type=0/type=1 不受影响
- 仅影响 type=2 且 ruleContent 为空的场景
- 未找到视频 URL 时回退到当前逻辑（向后兼容）

### R5 Header 修复与加密串处理（检查点3用户反馈增强）

**用户反馈三个核心问题**：
1. **加密串视频地址**：之前用网页模式 HTML 播放器模板时，有时获取到视频地址但地址是通过加密串传到页面播放器的，R5 怎么处理？
2. **适配性**：如何确保尽可能抓取到视频播放地址？
3. **内置播放器 404 Bug**：最新版本内置播放器播放不了但网页版模板可以正常播放，错误码 2004 (ERROR_CODE_IO_BAD_HTTP_STATUS)，Response code: 404

**404 Bug 根因分析**（源码深度分析结论）：
- `Exo2MediaPlayer.prepareAsyncInternal()` line 96-101 使用 no-op resolver：`ResolvingDataSource.Factory(cacheDataSourceFactory){ it }`，lambda `{ it }` 不做任何处理
- `ExoPlayerHelper.resolvingDataSource`（line 72-90）才是负责解码 SPLIT_TAG 并通过 `okhttpDataFactory.setDefaultRequestProperties(headers)` 设置 Header 的
- GSY 父类 `IjkExo2MediaPlayer.setDataSource` 接收了 `mapHeadData`，但 `prepareAsyncInternal` 的 no-op resolver 不处理 Header → **Header 丢失**
- WebView 自动发送 Referer（页面 URL）+ 浏览器 UA + Cookie；ExoPlayer Header 丢失 → CDN 防盗链验证失败 → 404

**R5 Header 修复方案**：

| 修改点 | 文件 | 说明 |
|--------|------|------|
| ExoPlayerHelper 暴露 Header 设置 | `help/exoplayer/ExoPlayerHelper.kt` | 新增 `setDefaultHeaders(headers)` 方法，调用 `okhttpDataFactory.setDefaultRequestProperties(headers)` |
| Exo2MediaPlayer 捕获 Header | `help/gsyVideo/Exo2MediaPlayer.kt` | 新增 `playHeaders` 字段；`prepareAsyncInternal` 中调用 `ExoPlayerHelper.setDefaultHeaders(playHeaders)` |
| VideoPlay 自动注入 Referer | `model/VideoPlay.kt` | RssSource 视频播放时，若 headerMap 无 Referer，自动注入 `Referer: <rssArticle.link>`（模拟 WebView 行为） |

**加密串 URL 处理策略**：
- **路径加密 URL**（如 `cdnwb.streamfastpro.com/{hash}/{id}/{token}/xxx.m3u8`）：R5 提取到的完整 URL 直接播放，配合 Header 修复（Referer 注入）解决 404
- **JS 解密 URL**：视频地址需要页面 JS 执行解密逻辑才能获得，原生 Kotlin 无法执行页面 JS → R5 无法处理，回退提示用户用 type=0 WebView 模式或填写 ruleContent
- **动态生成 URL**（XHR/Fetch 拦截型）：同 JS 解密，R5 无法处理，回退提示

**适配性增强**（确保尽可能抓取到视频地址）：

| 方法 | 实现方式 | 适用场景 | 状态 |
|------|---------|---------|------|
| ① 正则提取 | Regex 匹配 m3u8/mp4 URL | 通用 | R5 基础 |
| ② video/source 标签 | jsoup 解析 src/data-src | HTML5 视频 | R5 基础 |
| ③ OG/Meta 提取 | jsoup 解析 og:video content | 开放图谱协议 | R5 基础 |
| ④ JS 变量提取 | Regex 匹配 var/let/const 赋值 | JS 变量中的地址 | R5 基础 |
| ⑤ script JSON 提取 | jsoup 解析 `<script>` 标签内 JSON 数据 | 视频信息在 JSON 中的站点 | **R5 增强** |

**不实现**：iframe 递归提取（复杂度高收益低，YAGNI）、XHR/Fetch 拦截（WebView JS 独有能力）

## Alternatives Considered

### R1 多集方案对比

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| **A. ruleContent 返回多行 URL** | 简单，规则好写 | 无标题，只能"第N集" | ✅ 采用（作为简写模式） |
| **B. ruleContent 返回 JSON 数组** | 支持自定义标题 | 规则稍复杂 | ✅ 采用（作为完整模式） |
| C. 新增 ruleEpisodes 字段 | 结构清晰 | 需改数据库表结构，破坏性大 | ❌ 否决（Out of Scope） |
| D. 复用 BookSource episodes 机制 | 复用现有代码 | RssSource 与 BookSource 结构差异大 | ❌ 否决（耦合度高） |

**最终方案**：A+B 双模式，向后兼容单 URL。

### R2 调试日志方案对比

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| **A. onPlayerError 回调 + 调试面板** | 用户可见错误，可切换 | 需修改播放器链路 | ✅ 采用 |
| B. 只记 AppLog | 改动小 | 用户不可见，不解决问题 | ❌ 否决 |
| C. Toast 提示错误 | 简单 | 信息量不足，无法复制 | ❌ 否决 |

### R3 布局方案对比

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| **A. 新增 rss_video_panel 功能区** | 元素集中，订阅源/书源隔离 | 布局稍紧凑 | ✅ 采用 |
| B. 复用书源 data/chapters_container | 改动小 | 订阅源/书源 UI 耦合，逻辑混乱 | ❌ 否决 |
| C. 全屏覆盖层 overlay | 不占布局空间 | 全屏外不可见，交互复杂 | ❌ 否决 |

**最终方案**：A，新增独立 rss_video_panel，book==null 时显示。

### R5 自动抓取方案对比

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| **A. 原生 Kotlin 四种方法提取** | 不依赖 WebView，性能好，覆盖大多数场景 | 无法处理 JS 动态渲染页面 | ✅ 采用 |
| B. 复用 auto-video-player.html WebView 方案 | 覆盖 JS 动态渲染 | 需走 WebView，违背 type=2 内置播放器初衷 | ❌ 否决（type=2 就是为避免 WebView） |
| C. 仅正则提取 | 实现最简 | 覆盖率低，遗漏 video 标签/Meta/JS变量场景 | ❌ 否决（覆盖率不足） |
| D. 不做自动抓取，要求用户必填 ruleContent | 无需开发 | 用户体验差，违背"便捷性"诉求 | ❌ 否决（用户明确要求自动抓取） |

**最终方案**：A，原生 Kotlin 四种方法综合提取，去重后返回。未找到时回退当前逻辑。

## Drawbacks

1. **R1 多集解析的向后兼容风险**：如果现有 ruleContent 返回的内容恰好含换行（如 HTML），可能被误判为多集。**缓解**：仅当每行都是合法 URL 时才判定为多集；JSON 数组需以 `[` 开头才解析。
2. **R2 调试面板性能影响**：额外 UI 元素增加布局复杂度。**缓解**：默认隐藏，仅用户主动开启时显示。
3. **R3 功能区按钮布局紧凑**：订阅源功能区在非全屏时占用屏幕空间，可能影响播放器可视区域。**缓解**：按钮使用紧凑样式（11sp/48dp minWidth），调试面板默认隐藏。
4. **R4 部分异常无法根治**：SocketException 等网络异常只能加重试，无法根治。**缓解**：增加重试次数和友好提示。
5. **R5 无法处理 JS 动态渲染页面**：原生 HTTP 请求获取的 HTML 可能不含视频 URL（需 JS 执行后才渲染）。**缓解**：未找到时回退当前逻辑+AppLog提示；JS 动态渲染场景用户需自行填写 ruleContent 或用 type=0 WebView 模式。
6. **R5 正则误匹配风险**：正则可能匹配到非视频 URL（如含 m3u8/mp4 字样的文本链接）。**缓解**：isVideoUrl 二次过滤 + 去重；video/source/Meta 标签提取优先于正则（更精确）。

## Requirements

### R1 多集选择播放

- **REQ-1.1**：ruleContent 返回 JSON 数组 `[{"title":..,"url":..}]` 时，解析为多集列表
- **REQ-1.2**：ruleContent 返回多行 URL（每行合法 URL）时，解析为多集，标题为"第N集"
- **REQ-1.3**：ruleContent 返回单个 URL 时，保持现有单集播放逻辑（向后兼容）
- **REQ-1.4**：VideoPlay 新增 `rssEpisodes: List<RssEpisode>?` 字段管理多集
- **REQ-1.5**：VideoPlayerActivity 当 `book==null && rssEpisodes!=null` 时显示集数 UI
- **REQ-1.6**：集数点击切换播放对应集，并记录播放进度
- **REQ-1.7**：多集播放支持上一集/下一集切换
- **REQ-1.8**：内容规则编写说明文档化，明确三种 ruleContent 写法（单URL/多行URL/JSON数组）及兼容性
- **REQ-1.9**：JSON 数组对象结构定义：`url` 为必须字段，`title` 为可选字段（缺省"第N集"），支持未来扩充（duration/cover 等预留）
- **REQ-1.10**：JS 规则返回 JSON 数组对象时，parseRssEpisodes 正确解析为带标题的多集列表

### R2 调试日志

- **REQ-2.1**：Exo2MediaPlayer 实现 onPlayerErrorChanged 回调，捕获 PlaybackException
- **REQ-2.2**：错误信息通过回调链传递到 VideoPlayerActivity
- **REQ-2.3**：VideoPlayerActivity 添加调试日志面板（默认隐藏，可切换）
- **REQ-2.4**：调试面板显示：最终 URL、Header、错误类型、错误消息
- **REQ-2.5**：播放失败时自动弹出调试面板（非全屏模式下）
- **REQ-2.6**：调试面板内容可复制（长按复制）

### R3 布局学习

- **REQ-3.1**：activity_video_player.xml 新增 `rss_video_panel` 订阅源功能区（book==null 时 visible，书源保持 gone）
- **REQ-3.2**：播放地址展示（`tv_video_url`）显示当前播放 URL（AnalyzeUrl 处理后）
- **REQ-3.3**：功能区快进快退按钮（←30s/←10s/10s→/30s→），调用 player.seekTo()
- **REQ-3.4**：倍速 Spinner（1x/3x/5x/10x/15x），调用 Exo2MediaPlayer setSpeed
- **REQ-3.5**：调试按钮切换 debug_panel 显示/隐藏（与 R2 联动）
- **REQ-3.6**：多集选择区（上一集/Spinner/下一集）与 R1 rssEpisodes 联动
- **REQ-3.7**：视频简介（`tv_rss_description`）显示订阅源描述（若有）
- **REQ-3.8**：新增 `VideoCtrlButton` 样式（Widget.AppCompat.Button.Borderless，非 MaterialButton，避免主题崩溃）
- **REQ-3.9**（布局优化）：功能区所有控件（Button + Spinner）统一尺寸（minWidth=48dp, minHeight=36dp, padding=3dp），倍速 Spinner 不再偏大
- **REQ-3.10**（布局优化）：VideoCtrlButton 样式增强，新增圆角背景 `bg_video_ctrl_btn`（主题色淡背景+2dp 圆角），提升视觉一致性
- **REQ-3.11**（布局优化）：播放地址展示改为多行换行（maxLines=3, ellipsize=end），展示完整 URL 而非中间省略
- **REQ-3.12**（布局优化）：播放地址后新增复制按钮 `btn_copy_url`，一键复制 URL 到剪贴板（ClipboardManager + Toast 提示）
- **REQ-3.13**（title 来源修复）：单 URL/多行 URL 模式 TitleBar.title = rssArticle.title（列表标题规则内容）。ReadRss 启动 VideoPlayerActivity 传 videoTitle=rssArticle.title；VideoPlay RssSource 分支 player.setUp 后同步 `videoTitle = rssArticle.title` + `postEvent(VIDEO_SUB_TITLE, rssArticle.title)`

### R4 日志优化

- **REQ-4.1**：确认 ExoPlayer cleartext HTTP 配置，确保 HTTP m3u8 可播放
- **REQ-4.2**：CryptoException 检查 ruleContent 解析异常处理，图片解密失败不静默吞掉
- **REQ-4.3**：SQLiteBlobTooBigException 检查缓存数据大小限制
- **REQ-4.4**：SocketException 增加网络重试机制
- **REQ-4.5**：ForegroundServiceDidNotStartInTimeException 修复 VideoPlayService.startForegroundNotification 的 try-catch，异常时调用 stopSelf 避免超时崩溃
- **REQ-4.6**：NullPointerException 修复 RssSourceAdapter.dragSelectCallback.getItemId 空指针
- **REQ-4.7**：SyntaxError Empty JSON string 检查 JS 脚本 JSON.parse 前的空值判断

### R5 自动视频链接抓取

- **REQ-5.1**：新建 `VideoUrlExtractor.kt`（`help/video/` 目录），提供 `extract(html, baseUrl): List<String>` 方法
- **REQ-5.2**：方法①正则提取：Regex 匹配 `https?://...m3u8/mp4` URL（忽略大小写）
- **REQ-5.3**：方法②video/source 标签提取：jsoup 解析 `<video>`,`<source>` 的 src/data-src 属性
- **REQ-5.4**：方法③OG/Meta 提取：jsoup 解析 `<meta property="og:video">` 等的 content 属性
- **REQ-5.5**：方法④JS 变量提取：Regex 匹配 `var/let/const xxx = "http...m3u8/mp4"` 模式
- **REQ-5.6**：四种方法综合提取后去重（distinct），返回视频 URL 列表
- **REQ-5.7**：isVideoUrl 过滤函数：仅保留含 .m3u8/.mp4/format=m3u8/type=m3u8 的 URL
- **REQ-5.8**：VideoPlay.startPlay 的 `ruleContent.isNullOrBlank()` 分支集成 R5：获取文章 HTML → VideoUrlExtractor.extract → 按结果数量处理
- **REQ-5.9**：提取到单个 URL → 直接播放（复用现有 AnalyzeUrl + setUp + startPlayLogic 模式）
- **REQ-5.10**：提取到多个 URL → 构建 JSON 数组 → 走 parseRssEpisodes 多集逻辑（R1 复用）
- **REQ-5.11**：未提取到 URL → 回退当前逻辑（用 rssArticle.link）+ AppLog 提示"未从文章页面找到视频URL"
- **REQ-5.12**：异常处理：AnalyzeUrl 获取 HTML 失败时 onError 提示，不影响 App 稳定性
- **REQ-5.13**：相对路径处理：所有提取到的 URL 用 NetworkUtils.getAbsoluteURL 转绝对路径
- **REQ-5.14**（Header 修复）：ExoPlayerHelper 新增 `setDefaultHeaders(headers: Map<String, String>)` 方法，暴露 `okhttpDataFactory.setDefaultRequestProperties()`
- **REQ-5.15**（Header 修复）：ExoPlayerManager.initVideoPlayer 中 setDataSource 前调用 `ExoPlayerHelper.setDefaultHeaders(model.getMapHeadData())`，避免 override GSY 父类 setDataSource 签名风险（IjkExo2MediaPlayer 源码不在项目中），确保 Header 到达 HTTP 请求
- **REQ-5.16**（Header 修复）：VideoPlay RssSource 视频播放时，若 headerMap 无 Referer，自动注入 `Referer: <rssArticle.link>`（模拟 WebView 行为，解决 CDN 防盗链 404）
- **REQ-5.17**（Header 修复）：Header 修复适用于所有 type=2 视频播放场景（R5 自动抓取分支 + ruleContent 非空分支 + singleUrl 分支），不仅限于 R5
- **REQ-5.18**（适配性增强）：方法⑤ script JSON 提取：jsoup 解析 `<script>` 标签内 JSON 数据，提取含视频 URL 的字段
- **REQ-5.19**（加密串处理）：路径加密 URL（含 token/hash 的完整 URL）直接播放，配合 Header 修复解决 404
- **REQ-5.20**（加密串处理）：JS 解密 URL 和动态生成 URL 无法提取时，AppLog 提示用户用 type=0 WebView 模式或填写 ruleContent

## Scenarios

### Scenario 1：多集播放（JSON 数组模式）

1. 用户订阅源 ruleContent 用 `<js>` 返回 JSON 数组：`[{title:"第1集",url:"https://...m3u8"},{title:"第2集",url:"..."}]`
2. 用户点击订阅文章 → ReadRss.readRss → type=2 → VideoPlayerActivity
3. VideoPlay 解析 ruleContent → JSON 数组 → rssEpisodes
4. VideoPlayerActivity 显示集数列表
5. 用户点击"第2集" → 切换播放

### Scenario 2：多集播放（多行 URL 模式）

1. 用户订阅源 ruleContent 返回多行 URL（每行一个 m3u8 地址）
2. VideoPlay 解析 → 多行且每行合法 URL → rssEpisodes（标题"第1集""第2集"...）
3. VideoPlayerActivity 显示集数列表

### Scenario 3：m3u8 播放失败调试

1. 用户点击订阅文章 → 内置播放器 → m3u8 地址播放失败
2. Exo2MediaPlayer onPlayerError 回调触发 → 错误信息传到 Activity
3. 调试日志面板自动弹出 → 显示"错误类型: HTTP 403 / 错误消息: Forbidden / URL: https://..."
4. 用户长按复制错误信息 → 反馈给源作者

### Scenario 4：单 URL 向后兼容

1. 用户现有订阅源 ruleContent 返回单个 URL
2. VideoPlay 解析 → 单 URL → 单集播放（现有逻辑不变）

### Scenario 5：R5 自动抓取视频链接（ruleContent 为空）

1. 用户订阅源只填链接规则+type=2，未填内容规则（ruleContent 为空）
2. 用户点击订阅文章 → ReadRss.readRss → type=2 → VideoPlayerActivity
3. VideoPlay.startPlay 进入 `ruleContent.isNullOrBlank()` 分支
4. R5 触发：AnalyzeUrl 获取文章页面 HTML → VideoUrlExtractor.extract 四种方法综合提取
5. 提取到单个 m3u8 URL → 直接播放
6. 提取到多个 URL → 构建 JSON 数组 → parseRssEpisodes → 多集播放（R1 联动）
7. 未提取到 URL → 回退用 rssArticle.link + AppLog 提示

### Scenario 6：R5 JS 动态渲染页面回退

1. 用户订阅源只填链接规则+type=2，未填内容规则
2. 文章页面是 JS 动态渲染（原生 HTTP 获取的 HTML 不含视频 URL）
3. R5 四种方法均未提取到视频 URL
4. 回退当前逻辑 + AppLog 提示"未从文章页面找到视频URL"
5. 用户看到播放失败 → 查看调试面板 → 得知需自行填写 ruleContent 或用 type=0 WebView 模式
