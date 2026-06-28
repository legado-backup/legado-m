# 自动抓取视频播放器模式（V1）

> 当视频 URL 可从 HTML 直接提取时，使用 V1 模板自动抓取并播放，无需手动编写提取逻辑。

### 核心思路

1. 从网页 HTML 中自动提取视频 URL（四种方法逐级尝试）
2. 拼装包含 hls.js 的完整 HTML 播放器页面
3. **type 必须为 0**（WebView 渲染），不能用 type=2（内置播放器）

### 适用场景

- 视频 URL 嵌入在 HTML 的 `<video>`/`<source>` 标签中
- 视频 URL 出现在内联 JS 变量中（如 `var url = "https://...m3u8"`）
- 视频 URL 可通过正则从 HTML 源码中匹配
- 视频 URL 通过 XHR/Fetch 动态请求（模板自动拦截）

### 与 V2/V3 的区别对比

| 对比项 | V1 自动抓取 | V2 手动提取 | V3 注入脚本 |
|--------|------------|------------|------------|
| **核心方式** | 模板自动提取视频 URL | 用户编写提取逻辑 | 劫持已有播放器实例 |
| **适用场景** | 视频 URL 可从 HTML 提取 | 复杂提取逻辑需自定义 | 视频 URL 需 JS 运行时生成 |
| **模板类型** | HTML 页面（WebView 渲染） | HTML 页面（WebView 渲染） | JS 脚本（webJs 注入） |
| **播放器** | 自建完整播放器 | 自建完整播放器 | 优化已有播放器 |
| **缓冲优化** | hls.js 配置 | hls.js 配置 | destroy+recreate |
| **广告拦截** | URL 黑名单过滤 | 手动处理 | 事件拦截+元素移除 |
| **使用方式** | ruleContent 返回模板 HTML | ruleContent 返回模板 HTML | webJs 字段注入 |
| **依赖** | hls.js CDN | hls.js CDN | 页面已有播放器 |

### 四种视频提取方法详解

#### 方法1: DOM 提取

从 `<video>`/`<source>` 标签提取 `src`/`data-src` 属性。

```javascript
// 选择器可配置化
var genericSelectors = 'video, source, [src*=".m3u8"], [src*=".mp4"], [data-src*=".m3u8"]';
var siteSpecificSelector = '';  // 可配置覆盖，如 '.playlist.wbox.ffm3u8 li a[title]'

function extractFromDOM(doc) {
    var urls = [];
    var selectors = config.genericSelectors;
    if (config.siteSpecificSelector) {
        selectors = config.siteSpecificSelector + ', ' + selectors;
    }
    var elements = doc.querySelectorAll(selectors);
    for (var i = 0; i < elements.length; i++) {
        var el = elements[i];
        var src = el.getAttribute('src') || el.getAttribute('data-src') || el.getAttribute('data-url') || '';
        if (src && isVideoUrl(src)) {
            urls.push(normalizeUrl(src));
        }
        // 检查 source 子元素
        var sources = el.querySelectorAll('source');
        for (var j = 0; j < sources.length; j++) {
            var sSrc = sources[j].getAttribute('src') || sources[j].getAttribute('data-src') || '';
            if (sSrc && isVideoUrl(sSrc)) {
                urls.push(normalizeUrl(sSrc));
            }
        }
    }
    return urls;
}
```

**适用**：视频 URL 直接写在 HTML 标签属性中，最简单可靠。

#### 方法2: 正则提取

4 级正则从 HTML 源码中匹配视频 URL（严格→宽松）。

```javascript
// 使用非 lookbehind 正则（兼容 Android 5-7）
var regex = /(?:['"=])(https?[^'"]*(?:mp4|m3u8)[^'"]*)/gi;
var match;
while ((match = regex.exec(html)) !== null) {
    if (match[1]) {
        var url = normalizeUrl(match[1]);
        if (isVideoUrl(url)) urls.push(url);
    }
}
```

**适用**：视频 URL 出现在 JS 字符串、JSON 数据、HTML 属性值中。

> ⚠️ **Rhino 陷阱**：禁止使用 lookbehind 正则（`(?<=...)`），Android 5-7 的 Rhino 不支持，会导致崩溃。模板已使用 `(?:['"=])` 替代。

#### 方法3: JS 变量提取

从内联 `<script>` 中提取 `domain`+`videos` 等变量赋值。

```javascript
var patterns = [
    /var\s+\w*\s*=\s*["'](https?[^"']*(?:mp4|m3u8)[^"']*)/gi,
    /let\s+\w*\s*=\s*["'](https?[^"']*(?:mp4|m3u8)[^"']*)/gi,
    /const\s+\w*\s*=\s*["'](https?[^"']*(?:mp4|m3u8)[^"']*)/gi,
    /\w+\.url\s*=\s*["'](https?[^"']*(?:mp4|m3u8)[^"']*)/gi,
    /\w+\s*=\s*["'](https?[^"']*\.m3u8[^"']*)/gi,
    /\w+\s*=\s*["'](https?[^"']*\.mp4[^"']*)/gi
];
```

**适用**：网站将视频 URL 存储在 JS 变量中，如 `var playUrl = "https://...m3u8"`。

#### 方法4: XHR/Fetch 拦截

拦截网络请求获取动态加载的 m3u8 URL。

```javascript
// 拦截 XMLHttpRequest
var origXHROpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url) {
    this._url = url;
    return origXHROpen.apply(this, arguments);
};
XMLHttpRequest.prototype.send = function() {
    this.addEventListener('load', function() {
        if (isM3u8Url(this._url)) {
            interceptedVideoUrls.push(this._url);
        }
    });
    return origXHRSend.apply(this, arguments);
};

// 拦截 fetch
var origFetch = window.fetch;
window.fetch = function(input, init) {
    var url = typeof input === 'string' ? input : (input && input.url ? input.url : '');
    if (isM3u8Url(url)) {
        interceptedVideoUrls.push(url);
    }
    return origFetch.apply(this, arguments);
};
```

**适用**：视频 URL 通过 AJAX 动态请求，不在 HTML 中直接出现。

### 模板变量说明

| 变量 | 用途 | 提取方式 |
|------|------|----------|
| `{{@@title@text\|\|h1.0@text\|\|h2.0@text\|\|.title.0@text}}` | 视频标题，显示在播放器顶部 | Legado 规则引擎自动替换 |
| `{{@@.pager@a.-2@textNodes##\n.*}}` | 分页信息（如 "2/5"） | Legado 规则引擎自动替换 |
| `{{@@.chapters@a@href}}` | 章节链接列表（换行分隔） | Legado 规则引擎自动替换 |
| `{{@@.chapters@a@text}}` | 章节标题列表（换行分隔） | Legado 规则引擎自动替换 |
| `{{@@.right@html\|\|.info.0@html\|\|.jianjie@html}}` | 描述信息 | Legado 规则引擎自动替换 |
| `{{baseUrl}}` | 当前页面 URL（用于拼接相对路径） | Legado 规则引擎自动替换 |

> **模板变量原理**：Legado 规则引擎在渲染 HTML 前会自动将 `{{...}}` 替换为对应规则的提取结果。如果规则匹配失败，变量保持原样（模板通过 `indexOf('{{@@') === -1` 检测是否替换成功）。

### config 配置项完整说明

```javascript
var config = {
    // 跳过片头的秒数（0=不跳过）
    skipIntroSeconds: 0,

    // 是否显示描述信息
    showDescription: false,

    // 是否自动加载视频（false=手动选择后播放）
    autoLoad: true,

    // 广告后缀黑名单（mp4是因为某些网站用mp4播放广告，真正视频是m3u8）
    adExtensionBlacklist: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.css', '.js', '.mp4'],

    // 通用选择器（优先级低于 siteSpecificSelector）
    genericSelectors: 'video, source, [src*=".m3u8"], [src*=".mp4"], [data-src*=".m3u8"]',

    // 站点特定选择器（可配置覆盖，如 '.playlist.wbox.ffm3u8 li a[title]'）
    siteSpecificSelector: '',

    // HLS.js 缓冲配置
    hlsJsConfig: {
        maxBufferLength: 180,           // 最大缓冲长度（秒）
        maxMaxBufferLength: 600,        // 最大最大缓冲长度（秒）
        maxBufferSize: 200 * 1024 * 1024, // 最大缓冲大小（200MB）
        startLevel: -1,                 // 起始质量级别（-1=自动）
        maxBufferHole: 0.5,             // 最大缓冲空洞（秒）
        highLatencyMode: false,         // 高延迟模式
        liveSyncDuration: 30,           // 直播同步时长（秒）
        liveMaxLatencyDuration: Infinity, // 直播最大延迟
        enableWorker: true,             // 启用 Web Worker
        enableSoftwareAES: true,        // 启用软件 AES 解密
        backBufferLength: 180,          // 后缓冲长度（秒）
        nudgeOffset: 0.1,               // 微调偏移
        nudgeMaxRetry: 3,               // 微调最大重试
        maxFragLookUpTolerance: 0.25,   // 片段查找容差
        enableWebVtt: true,             // 启用 WebVTT 字幕
        enableCEA708Captions: true,      // 启用 CEA-708 字幕
        stretchShortVideoTrack: true,    // 拉伸短视频轨道
        maxAudioFramesDrift: 1,          // 最大音频帧漂移
        forceKeyFrameOnDiscontinuity: true, // 不连续时强制关键帧
        startFragPrefetch: true,         // 启用片段预加载
        capLevelToPlayerSize: false,     // 不根据播放器大小限制码率
        maxMaxBufferHole: 1,             // 最大最大缓冲空洞
        fragLoadingTimeOut: 20000,       // 片段加载超时（毫秒）
        fragLoadingMaxRetry: 6,          // 片段加载最大重试
        fragLoadingMaxRetryTimeout: 64000, // 片段加载最大重试超时
        fragLoadingRetryDelay: 1000,     // 片段加载重试延迟
        levelLoadingTimeOut: 10000,      // 级别加载超时
        levelLoadingMaxRetry: 4,         // 级别加载最大重试
        levelLoadingRetryDelay: 1000,    // 级别加载重试延迟
        manifestLoadingTimeOut: 10000,   // 清单加载超时
        manifestLoadingMaxRetry: 3,      // 清单加载最大重试
        manifestLoadingRetryDelay: 1000, // 清单加载重试延迟
        abr: {
            maxBitrate: Infinity,        // 最大码率
            minBitrate: 0,               // 最小码率
            defaultBitrate: 2000000,     // 默认码率
            bandwidthUpgradeTarget: 0.6, // 带宽升级目标
            bandwidthDowngradeTarget: 0.3, // 带宽降级目标
            bandwidthDowngradeDelay: 5,  // 带宽降级延迟
            bandwidthUpgradeDelay: 3,    // 带宽升级延迟
            maxStarvationDelay: 2,       // 最大饥饿延迟
            maxLoadingDelay: 2,          // 最大加载延迟
            lowLatencyMode: false        // 低延迟模式
        }
    }
};
```

### 使用示例

在 ruleContent 中引用模板：

```javascript
// 方式1: 直接使用模板（模板自动提取视频URL）
// ruleContent.content 设置为模板 HTML 内容即可
// 模板中的 {{@@...}} 变量由 Legado 规则引擎自动替换

// 方式2: 先提取再注入（需要自定义提取逻辑时）
class.title-area@text
<js>
var videoTitle = result;
java.put('videoTitle', videoTitle);
result;
</js>
class.player-wrapper@all
<js>
var videoTitle = java.get('videoTitle') || '';
var reg = /[?&]url=([^"&\s]+)/i;
var match = result.match(reg);
var videoUrl = match ? match[1] : '';

// 读取模板文件内容并替换变量
var html = '粘贴 templates/auto-video-player.html 的完整内容';
html = html.replace('{{@@title@text||h1.0@text||h2.0@text||.title.0@text}}', videoTitle);
result = html;
</js>
```

### type 必须为 0

```json
{
    "sourceType": 0,
    "ruleContent": {
        "content": "模板HTML内容..."
    }
}
```

⚠️ **禁止使用 type=2**：type=2 会尝试用内置播放器直接播放 ruleContent 返回的字符串（当作视频 URL），导致播放失败。V1 模板返回的是完整 HTML 页面，必须用 WebView 渲染。

### 模板位置

**模板文件**：[templates/auto-video-player.html](../../templates/auto-video-player.html)

**模板功能清单**（1309行）：

| 功能模块 | 实现细节 | 用户价值 |
|----------|----------|----------|
| **视频标题** | `{{@@title@text\|\|...}}` 模板变量 + 自动显示 | 知道当前播放的是什么内容 |
| **四种提取方法** | DOM+正则+JS变量+XHR拦截 | 自动适配各种网站结构 |
| HLS.js 核心 | v1.4.12 稳定版 + 完整缓冲配置 | 流畅播放 m3u8 流 |
| m3u8/mp4 分流 | 根据格式自动选择 HLS.js 或原生播放 | 避免双重加载冲突 |
| 进度条系统 | 播放进度 + 缓冲进度双显示 | 可视化播放状态 |
| 快进快退 | 6 按钮（±30s/1m/3m）+ 消息提示 | 精确定位片段 |
| 倍速播放 | 1x/3x/5x/10x/15x 五档 | 快速浏览长视频 |
| 全屏控制 | requestFullscreen + 状态监听 | 沉浸式观看 |
| **横竖屏反转** | 90°/180°/270° 旋转 + 自适应宽高 | 横屏观看竖屏视频 |
| 上下集切换 | 视频源数组 + 上一集/下一集按钮 | 多集无缝切换 |
| 视频源选择 | select 下拉框 + 动态填充 | 多源自由选择 |
| 分页加载 | 章节列表 + 上一页/下一页 + 自动/手动加载 | 多页视频导航 |
| 错误自动重试 | NETWORK_ERROR → startLoad / MEDIA_ERROR → recoverMediaError | 自动恢复播放 |
| 响应式设计 | @media 768px 断点 + 字体/按钮自适应 | 手机端友好 |
| 显/隐信息 | toggle 按钮 + messages/debug 控制 | 专注视频内容 |
| Legado JSBridge | java.ajax() 优先 + XMLHttpRequest 回退 | 分页加载网络请求 |
| 版权信息 | 与显/隐按钮同行居右 + 字体小一号 | 标注作者版本 |

### V1 版本更新日志

**V1.20260606.1**：
- 移除 jQuery 依赖（87KB），AJAX 改用 Legado JSBridge
- 修复 Lookbehind 正则（Android 5-7 崩溃）
- m3u8/mp4 分流加载
- 事件监听器累积修复
- 删除 srcchange 死代码
- 移除全局 transition
- backdrop-filter 兼容降级
- URL 去重增强
- videoExtensionsToFilter 重命名为 adExtensionBlacklist
- DOM 提取选择器可配置化
- 新增 XHR/Fetch 拦截提取

### 关键设计要点

| 要素 | 设计 | 原因 |
|------|------|------|
| 四种提取方法 | DOM→正则→JS变量→XHR拦截，逐级尝试 | 最大化自动提取成功率 |
| 选择器可配置 | `siteSpecificSelector` 优先于 `genericSelectors` | 不同网站 DOM 结构差异大 |
| 广告后缀黑名单 | 排除 `.jpg/.png/.css/.js/.mp4` 等 | mp4 排除是因为某些网站用 mp4 播广告，真正视频是 m3u8 |
| m3u8/mp4 分流 | m3u8 用 HLS.js，mp4 用原生播放 | 避免双重加载冲突（HLS.js 设 src 又直接设 src） |
| autoplay + muted | 自动播放但静音 | 浏览器策略要求静音才能自动播放 |
| Legado JSBridge | `java.ajax()` 优先 | 分页加载时避免跨域问题 |
| 非lookbehind正则 | `(?:['"=])` 替代 `(?<=['"=])` | Android 5-7 的 Rhino 不支持 lookbehind |
