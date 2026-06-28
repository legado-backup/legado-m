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
