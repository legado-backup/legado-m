# 注入式视频播放器优化脚本（V3）

> 当视频 URL 需要 JS 运行时生成、播放器带加密参数时，使用 V3 脚本劫持已有播放器实例，优化缓冲+去广告。

### 核心思路

1. 劫持页面已有的播放器实例（Video.js/DPlayer/ArtPlayer 等）
2. 用 destroy+recreate 方式重建 HLS 实例，应用优化缓冲配置
3. 通过事件拦截模式拦截广告请求和弹窗
4. 注入全局控制栏和进度条，增强用户体验

### 适用场景

- 视频 URL 需 JS 运行时动态生成（如加密参数、token 验证）
- 播放器带加密参数，无法直接提取视频 URL
- 页面已有完整播放器，只需优化缓冲和去广告
- 视频网站使用已知播放器框架（Video.js/DPlayer 等）

### 与 V1/V2 的区别对比

| 对比项 | V1 自动抓取 | V2 手动提取 | V3 注入脚本 |
|--------|------------|------------|------------|
| **核心方式** | 模板自动提取视频 URL | 用户编写提取逻辑 | 劫持已有播放器实例 |
| **适用场景** | 视频 URL 可从 HTML 提取 | 复杂提取逻辑需自定义 | 视频 URL 需 JS 运行时生成 |
| **模板类型** | HTML 页面（WebView 渲染） | HTML 页面（WebView 渲染） | JS 脚本（webJs 注入） |
| **播放器** | 自建完整播放器 | 自建完整播放器 | 优化已有播放器 |
| **缓冲优化** | hls.js 配置 | hls.js 配置 | destroy+recreate |
| **广告拦截** | URL 黑名单过滤 | 手动处理 | 事件拦截+元素移除+脚本拦截 |
| **使用方式** | ruleContent 返回模板 HTML | ruleContent 返回模板 HTML | webJs 字段注入 |
| **依赖** | hls.js CDN | hls.js CDN | 页面已有播放器+hls.js |
| **type** | 0（WebView 渲染） | 0（WebView 渲染） | 0（WebView 渲染） |
| **是否替换页面** | 完全替换页面内容 | 完全替换页面内容 | 不替换，在原页面上注入 |

### 支持的播放器类型（6种+原生兜底）

| 播放器 | 全局变量 | 选择器 | HLS 支持 | 缓冲可配 | 获取 HLS 实例方式 |
|--------|----------|--------|----------|----------|-------------------|
| **Video.js** | `videojs` | `.video-js`, `[data-setup]` | ✅ | ✅ | `tech().vhs` / `tech().hls` / `inst.hls` |
| **DPlayer** | `DPlayer` | `.dplayer` | ✅ | ✅ | `plugins.hls` / `inst.hls` |
| **ArtPlayer** | `Artplayer` | `.artplayer-app`, `.artplayer` | ✅ | ✅ | `plugins.hls` / `inst.hls` |
| **XGPlayer** | `Player` | `.xgplayer`, `.xgplayer-container` | ✅ | ✅ | `inst.hls` / `plugins.hls` / `_hls` |
| **EasyPlayer** | `EasyPlayer` | `.easyplayer`, `.easy-player` | ✅ | ✅ | `inst.hls` / `_hls` / `hlsPlayer` |
| **Plyr** | `plyr` | `.plyr` | ❌ | ❌ | 无 |
| **原生兜底** | - | `video` | 视情况 | 视情况 | 通过 DOM 查找 |

**播放器检测算法**：数据驱动框架（`PLAYER_DEFS` 数组），每种播放器定义包含全局变量、选择器、实例属性、HLS 获取方式。检测顺序：全局数组 → DOM 元素属性。

### 缓冲优化原理（destroy+recreate）

V3 采用 destroy+recreate 策略，而非直接修改已有 HLS 实例的 config：

```
1. 获取已有 HLS 实例
2. 记录当前播放源 URL + 播放位置
3. 销毁旧 HLS 实例（oldHls.destroy()）
4. 用优化配置创建新 HLS 实例（new Hls(hlsConfig)）
5. attachMedia + loadSource + 恢复播放位置
6. 更新播放器实例中的 HLS 引用
```

**为什么不直接改 config？**
- HLS.js 的部分配置（如 `maxBufferLength`）在实例创建后修改不会立即生效
- destroy+recreate 确保所有配置项都被正确应用
- 恢复播放位置保证用户无感知切换

**回退机制**：如果 destroy+recreate 失败，回退到直接修改 config 并提示用户刷新页面。

### 广告拦截机制（事件拦截模式）

V3 使用事件拦截替代 `Object.defineProperty(window.location, 'href')`（后者是致命 Bug）：

| 拦截方式 | 拦截目标 | 实现原理 |
|----------|----------|----------|
| **click 事件拦截** | 广告链接 `<a>` 点击 | `document.addEventListener('click', handler, true)` 捕获阶段拦截 |
| **window.open 拦截** | 广告弹窗 | 覆盖 `window.open`，检查 URL 是否为广告 |
| **meta refresh 拦截** | 广告重定向 | 移除 `meta[http-equiv="refresh"]` 中的广告 URL |
| **动态元素拦截** | 动态创建的 script/img/iframe | 覆盖 `document.createElement`，拦截 `setAttribute` 和 `src` 赋值 |
| **广告元素移除** | 广告容器 DOM | 查找并移除常见广告选择器匹配的元素 |
| **MutationObserver** | 动态插入的广告 | 监听 body 直接子元素变化（subtree:false），增量处理 |

**广告 URL 判定逻辑**：
1. 先检查是否为视频 URL（白名单关键词：m3u8/mp4/webm/ogg/...）
2. 视频URL不被拦截
3. 非视频 URL 检查是否包含广告关键词（ad/ads/adv/banner/popup/preroll/...）

### 净化模式说明

| 净化项 | 选择器 | 效果 |
|--------|--------|------|
| 评论区 | `[class*="comment"]`, `[id*="comment"]` | `display:none` |
| 社交分享 | `[class*="share"]`, `[class*="social"]` | `display:none` |
| 推荐视频 | `[class*="related"]`, `[class*="recommend"]` | `display:none` |

净化模式默认启用，通过 `config.cleanMode` 配置开关。

### 使用方式：作为 webJs 注入

在书源/订阅源的 `ruleContent.webJs` 字段中注入脚本：

```json
{
    "sourceType": 0,
    "ruleContent": {
        "webJs": "粘贴 templates/inject-video-player.js 的完整内容"
    }
}
```

或者配合 ruleContent 使用：

```javascript
// ruleContent.content 提取页面内容
class.video-container@html

// ruleContent.webJs 注入优化脚本
// 脚本会在 WebView 加载完成后自动执行
```

> **关键区别**：V1/V2 通过 ruleContent.content **替换**整个页面内容为自定义 HTML；V3 通过 ruleContent.webJs 在**原页面**上注入脚本，不替换页面内容。

### config 配置项完整说明

```javascript
var config = {
    // 缓冲优化配置
    buffer: {
        maxBufferLength: 180,           // 最大缓冲长度（秒）
        maxMaxBufferLength: 600,        // 最大最大缓冲长度（秒）
        maxBufferSize: 200 * 1024 * 1024, // 最大缓冲大小（200MB）
        backBufferLength: 180,          // 后缓冲长度（秒）
        maxBufferHole: 0.5,             // 最大缓冲空洞（秒）
        startFragPrefetch: true,        // 启用片段预加载
        capLevelToPlayerSize: false     // 不根据播放器大小限制码率
    },

    // 广告拦截配置
    adBlocker: {
        enabled: true,
        // 视频URL白名单关键词（路径中包含这些词的URL不被拦截）
        videoWhitelist: [
            'm3u8', 'mp4', 'webm', 'ogg', 'mkv', 'avi',
            'flv', 'ts', 'f4v', 'mov', 'wmv', '3gp',
            'video', 'media', 'play', 'stream', 'hls',
            'dash', 'cdn', 'vod', 'live', 'source'
        ],
        // 广告关键词（URL中包含这些词的请求被拦截）
        adKeywords: [
            'ad', 'ads', 'adv', 'advert', 'advertising',
            'banner', 'popup', 'popunder', 'preroll',
            'midroll', 'postroll', 'tracking', 'analytics',
            'doubleclick', 'googlesyndication', 'adservice',
            'adserver', 'adnxs', 'adsrvr', 'adroll'
        ],
        removePopups: true,             // 移除弹窗
        blockRedirects: true            // 拦截重定向
    },

    // 净化模式
    cleanMode: {
        enabled: true,
        removeComments: true,           // 移除评论区
        removeSocialWidgets: true,      // 移除社交分享
        removeRelatedVideos: true       // 移除推荐视频
    },

    // 自动播放
    autoPlay: {
        enabled: true,
        muted: true,                    // 静音自动播放（浏览器策略要求）
        retryCount: 3,                  // 自动播放重试次数
        retryDelay: 1000                // 重试延迟（毫秒）
    },

    // 调试
    debug: {
        enabled: true,
        maxLogEntries: 200              // 最大日志条数
    },

    // 卡顿检测
    stallDetection: {
        enabled: true,
        threshold: 3,                   // 连续卡顿次数阈值
        windowMs: 5000                  // 卡顿计数窗口（毫秒）
    }
};
```

### 注入功能清单

| 功能模块 | 实现细节 | 用户价值 |
|----------|----------|----------|
| **播放器检测** | 数据驱动框架（PLAYER_DEFS），6种+原生兜底 | 自动识别并适配各种播放器 |
| **缓冲优化** | destroy+recreate 重建 HLS 实例 | 流畅播放，减少卡顿 |
| **卡顿检测** | waiting 事件计数+自动降级 | 检测到频繁卡顿自动降低质量级别 |
| **广告拦截** | 6种拦截方式（事件+元素+脚本+meta+弹窗+MutationObserver） | 全面去广告 |
| **净化模式** | 评论区+社交分享+推荐视频 | 专注视频内容 |
| **全局控制栏** | fixed 底部，快进快退+倍速+全屏+静音 | 增强播放控制 |
| **进度条** | fixed 顶部，播放+缓冲双进度 | 可视化播放状态 |
| **调试面板** | Debug 按钮切换，显示视频信息+HLS状态+日志 | 排查问题 |
| **XHR/Fetch 拦截** | 拦截网络请求获取 m3u8 URL | 获取动态加载的视频地址 |
| **自动播放** | 静音+重试机制 | 自动开始播放 |
| **消息提示** | fixed 右上角，8秒自动消失 | 实时反馈操作结果 |
| **版权信息** | fixed 左下角 | 标注版本 |

### V3 版本更新日志

**V3.20260606.1** — 13项核心优化：

| # | 优化项 | 说明 |
|---|--------|------|
| 1 | 删除 `Object.defineProperty(window.location,'href')` | 致命Bug，会导致页面导航异常 |
| 2 | 删除 `window.location.replace` 覆盖 | 致命Bug，会导致页面无法正常跳转 |
| 3 | 缓冲优化改为 destroy+recreate | 替代直接改config，确保配置完全生效 |
| 4 | 播放器检测算法重构为数据驱动（PLAYER_DEFS） | 可扩展性更强，新增播放器只需添加定义 |
| 5 | MutationObserver 限制范围（subtree:false） | 减少性能开销，只监听 body 直接子元素 |
| 6 | 移除 `setInterval(blockAdElements, 10000)` | 避免定时全量扫描的性能损耗 |
| 7 | CSS transition 精确化（all→具体属性） | 避免不必要的属性动画 |
| 8 | backdrop-filter 兼容降级（实色+@supports） | 不支持的设备用实色背景 |
| 9 | 白名单 URL 检测增强（路径分析） | 先检查 pathname 再回退到完整 URL |
| 10 | 新增 XHR/Fetch 拦截获取视频 URL | 捕获动态加载的 m3u8 地址 |
| 11 | 新增卡顿检测+自动降级 | 连续卡顿3次自动降低质量级别 |
| 12 | iframe 跨域访问优化（先检查同源） | 避免跨域访问异常 |
| 13 | 动态 meta refresh 处理 | MutationObserver 拦截动态插入的广告重定向 |

### 关键设计要点

| 要素 | 设计 | 原因 |
|------|------|------|
| IIFE 封装 | `(function(){...})()` | 避免全局变量污染，与页面脚本隔离 |
| 事件拦截替代 defineProperty | `addEventListener('click', handler, true)` | defineProperty(window.location) 是致命Bug |
| destroy+recreate | 先销毁旧实例再创建新实例 | 直接改config部分参数不生效 |
| 数据驱动播放器检测 | `PLAYER_DEFS` 数组 | 新增播放器只需添加定义对象 |
| subtree:false | MutationObserver 只监听直接子元素 | 减少性能开销 |
| 白名单优先 | 先判断是否为视频URL，视频URL不拦截 | 避免误拦截视频请求 |
| 卡顿自动降级 | waiting 事件计数+降低 currentLevel | 弱网环境自动适配 |

### 模板位置

**模板文件**：[templates/inject-video-player.js](../../templates/inject-video-player.js)

**版本**：V3.20260606.1
